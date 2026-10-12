import base64
import contextlib
import hmac
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
import uvicorn

mcp = FastMCP("Forex Guardian GitHub MCP")

# The MCP bearer token is separate from the GitHub token. Fail closed at startup
# so the HTTP service cannot accidentally run without authentication.
MCP_ACCESS_TOKEN = os.getenv("MCP_ACCESS_TOKEN", "").strip()
if len(MCP_ACCESS_TOKEN) < 32:
    raise RuntimeError("MCP_ACCESS_TOKEN must be set to a random value of at least 32 characters.")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
OWNER = os.getenv("GITHUB_OWNER", "farhanx899-cmd").strip()
REPO = os.getenv("GITHUB_REPO", "MYBOT").strip()
BASE = os.getenv("GITHUB_BASE_BRANCH", "main").strip()
ALLOWED = frozenset({
    "app.py",
    "engine.py",
    "README.md",
    "requirements.txt",
    "news_events_template.csv",
    ".gitignore",
    "mcp server/server.py",
    "mcp server/requirements.txt",
})
MAX_BYTES = 150_000


def _csv_setting(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    return [item.strip().lower() for item in value.split(",") if item.strip()]


# Keep the SDK's DNS-rebinding protection enabled. Remote deployments must set
# MCP_ALLOWED_HOSTS to the exact host header(s) served by their HTTPS proxy.
_TRANSPORT_SECURITY = TransportSecuritySettings(
    allowed_hosts=_csv_setting(
        "MCP_ALLOWED_HOSTS",
        ["localhost:*", "127.0.0.1:*", "[::1]:*"],
    ),
    allowed_origins=_csv_setting(
        "MCP_ALLOWED_ORIGINS",
        ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"],
    ),
)


def _validate_repo_config() -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", OWNER):
        raise RuntimeError("GITHUB_OWNER contains unsupported characters.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", REPO):
        raise RuntimeError("GITHUB_REPO contains unsupported characters.")
    if not BASE or ".." in BASE or "\\" in BASE:
        raise RuntimeError("GITHUB_BASE_BRANCH is invalid.")


_validate_repo_config()


def api(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is not configured.")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{REPO}{path}",
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Forex-Guardian-MCP",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        # Do not include request headers or credentials in raised error details.
        detail = error.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"GitHub API HTTP {error.code}: {detail}") from None


def safe_path(path: str) -> str:
    candidate = path.strip().lstrip("/")
    if candidate not in ALLOWED or ".." in candidate or candidate.startswith(".github/"):
        raise ValueError("Path is not allowlisted.")
    return candidate


def _contents_path(path: str) -> str:
    return "/contents/" + urllib.parse.quote(path, safe="/")


@mcp.tool()
def get_project_status() -> dict[str, Any]:
    """Return GitHub repository and configured base-branch status; not app uptime."""
    repository = api("GET", "")
    branch = api("GET", f"/branches/{urllib.parse.quote(BASE, safe='')}")
    return {
        "repository": repository.get("full_name"),
        "private": repository.get("private"),
        "base_branch": BASE,
        "latest_sha": branch.get("commit", {}).get("sha"),
        "note": "GitHub status only; does not verify app uptime or broker connectivity.",
    }


@mcp.tool()
def list_project_files() -> dict[str, Any]:
    """List the files this MCP server may inspect or propose changes to."""
    return {
        "repository": f"{OWNER}/{REPO}",
        "base_branch": BASE,
        "allowed_files": sorted(ALLOWED),
        "policy": "Changes are proposed through pull requests; no direct base-branch writes or auto-merge.",
    }


@mcp.tool()
def read_project_file(path: str) -> dict[str, Any]:
    """Read one allowlisted source/config file; credential-like lines are redacted."""
    safe = safe_path(path)
    item = api("GET", f"{_contents_path(safe)}?ref={urllib.parse.quote(BASE, safe='')}")
    content = base64.b64decode(item["content"]).decode("utf-8", errors="replace")
    if len(content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("File exceeds size limit.")
    content = re.sub(
        r"(?im)^\s*(?:export\s+)?([A-Za-z0-9_.-]*(?:api[_-]?key|token|password|secret|authorization)[A-Za-z0-9_.-]*\s*[:=]\s*).+$",
        r"\1[REDACTED]",
        content,
    )
    return {"path": safe, "sha": item.get("sha"), "content": content}


@mcp.tool()
def propose_file_change(path: str, new_content: str, change_summary: str) -> dict[str, Any]:
    """Create a unique branch and pull request for a proposed file change; never merge it."""
    safe = safe_path(path)
    if len(new_content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Content exceeds size limit.")
    if not change_summary.strip() or len(change_summary) > 180:
        raise ValueError("Summary must be 1–180 characters.")
    if re.search(
        r"(?im)^\s*(?:live_trading|enable_live|auto_merge)\s*=\s*(?:true|1|yes)\b",
        new_content,
    ):
        raise ValueError("Potential live-trading/auto-merge activation blocked.")

    base_branch = api("GET", f"/branches/{urllib.parse.quote(BASE, safe='')}")
    base_sha = base_branch["commit"]["sha"]
    current = api(
        "GET",
        f"{_contents_path(safe)}?ref={urllib.parse.quote(BASE, safe='')}",
    )
    summary_slug = re.sub(r"[^a-z0-9-]+", "-", change_summary.lower()).strip("-")[:32]
    branch_name = f"mcp/proposed-{summary_slug or 'change'}-{base_sha[:7]}-{secrets.token_hex(4)}"

    # The contents API write is explicitly scoped to this newly created branch.
    api("POST", "/git/refs", {"ref": f"refs/heads/{branch_name}", "sha": base_sha})
    api(
        "PUT",
        _contents_path(safe),
        {
            "message": f"Propose: {change_summary}",
            "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
            "branch": branch_name,
            "sha": current["sha"],
        },
    )
    pull_request = api(
        "POST",
        "/pulls",
        {
            "title": f"[MCP proposal] {change_summary}",
            "head": branch_name,
            "base": BASE,
            "body": (
                "AI-proposed change. Review the diff, run checks, and inspect security safeguards. "
                "This server does not merge pull requests or enable live trading."
            ),
        },
    )
    return {
        "status": "pull_request_created",
        "branch": branch_name,
        "pull_request_number": pull_request.get("number"),
        "pull_request_url": pull_request.get("html_url"),
        "merged": False,
    }


async def health(_: Request) -> JSONResponse:
    """Return a minimal liveness response without exposing configuration."""
    return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})


class BearerTokenMiddleware:
    """Require the dedicated MCP_ACCESS_TOKEN on every HTTP route except GET /health."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.expected_token = token.encode("utf-8")

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("method") == "GET" and scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return

        supplied = b""
        for name, value in scope.get("headers", []):
            if name.lower() == b"authorization":
                supplied = value
                break
        scheme, separator, credential = supplied.partition(b" ")
        authorized = (
            bool(separator)
            and scheme.lower() == b"bearer"
            and hmac.compare_digest(credential.strip(), self.expected_token)
        )
        if not authorized:
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"www-authenticate", b"Bearer"),
                        (b"cache-control", b"no-store"),
                        (b"content-length", b"0"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return

        await self.app(scope, receive, send)


mcp_http_app = mcp.streamable_http_app(transport_security=_TRANSPORT_SECURITY)


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    # Mounting the MCP ASGI app requires the parent app to run this manager.
    async with mcp.session_manager.run():
        yield


starlette_app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/", app=mcp_http_app),
    ],
    lifespan=lifespan,
)
app = BearerTokenMiddleware(starlette_app, MCP_ACCESS_TOKEN)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", "8000")),
    )
