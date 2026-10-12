import base64, json, os, re, urllib.error, urllib.request
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Forex Guardian GitHub MCP")
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
OWNER = os.getenv("GITHUB_OWNER", "farhanx899-cmd").strip()
REPO = os.getenv("GITHUB_REPO", "MYBOT").strip()
BASE = os.getenv("GITHUB_BASE_BRANCH", "main").strip()
ALLOWED = {"app.py", "engine.py", "README.md", "requirements.txt", "news_events_template.csv", ".gitignore"}
MAX_BYTES = 150_000

def api(method, path, payload=None):
    if not TOKEN: raise RuntimeError("GITHUB_TOKEN is not configured.")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{REPO}{path}",
        data=None if payload is None else json.dumps(payload).encode(),
        method=method,
        headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {TOKEN}",
                 "X-GitHub-Api-Version":"2022-11-28","User-Agent":"Forex-Guardian-MCP"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw=r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API HTTP {e.code}: {e.read().decode(errors='replace')[:400]}")

def safe_path(path):
    p=path.strip().lstrip("/")
    if p not in ALLOWED or ".." in p or p.startswith(".github/"):
        raise ValueError("Path is not allowlisted.")
    return p

@mcp.tool()
def get_project_status() -> dict:
    """Return GitHub repository and configured base-branch status; not Streamlit uptime."""
    repo=api("GET","")
    branch=api("GET",f"/branches/{BASE}")
    return {"repository":repo.get("full_name"),"private":repo.get("private"),
            "base_branch":BASE,"latest_sha":branch.get("commit",{}).get("sha"),
            "note":"GitHub status only; does not verify app uptime or broker connectivity."}

@mcp.tool()
def list_project_files() -> dict:
    """List files this MCP server is allowed to inspect or propose changes to."""
    return {"repository":f"{OWNER}/{REPO}","base_branch":BASE,
            "allowed_files":sorted(ALLOWED),
            "policy":"Changes are proposed through pull requests; no direct main writes or auto-merge."}

@mcp.tool()
def read_project_file(path: str) -> dict:
    """Read one allowlisted source/config file; credential-like lines are redacted."""
    p=safe_path(path)
    item=api("GET",f"/contents/{p}?ref={BASE}")
    content=base64.b64decode(item["content"]).decode("utf-8",errors="replace")
    if len(content.encode())>MAX_BYTES: raise ValueError("File exceeds size limit.")
    content=re.sub(r"(?im)^(\s*(?:api[_-]?key|token|password|secret|authorization)\s*[:=]\s*).+$",r"\1[REDACTED]",content)
    return {"path":p,"sha":item.get("sha"),"content":content}

@mcp.tool()
def propose_file_change(path: str, new_content: str, change_summary: str) -> dict:
    """Create a branch and pull request for a proposed file change; never merges it."""
    p=safe_path(path)
    if len(new_content.encode())>MAX_BYTES: raise ValueError("Content exceeds size limit.")
    if not change_summary.strip() or len(change_summary)>180: raise ValueError("Summary must be 1–180 characters.")
    low=new_content.lower()
    if re.search(r"(live_trading\s*=\s*true|enable_live\s*=\s*true|auto_merge)",low):
        raise ValueError("Potential live-trading/auto-merge activation blocked.")
    branch=api("GET",f"/branches/{BASE}")
    base_sha=branch["commit"]["sha"]
    current=api("GET",f"/contents/{p}?ref={BASE}")
    name="mcp/proposed-"+re.sub(r"[^a-z0-9-]+","-",change_summary.lower()).strip("-")[:32]+"-"+base_sha[:7]
    api("POST","/git/refs",{"ref":f"refs/heads/{name}","sha":base_sha})
    api("PUT",f"/contents/{p}",{"message":f"Propose: {change_summary}",
        "content":base64.b64encode(new_content.encode()).decode(),"branch":name,"sha":current["sha"]})
    pr=api("POST","/pulls",{"title":f"[MCP proposal] {change_summary}","head":name,"base":BASE,
        "body":"AI-proposed change. Review the diff, run tests, verify deployment and inspect trading safeguards. This server does not merge pull requests or enable live trading."})
    return {"status":"pull_request_created","branch":name,"pull_request_number":pr.get("number"),
            "pull_request_url":pr.get("html_url"),"merged":False}

if __name__=="__main__":
    # For remote hosting, place behind authenticated HTTPS; this server alone is not an auth gateway.
    mcp.run(transport="streamable-http")
