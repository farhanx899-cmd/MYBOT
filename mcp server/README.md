# Forex Guardian AI — GitHub MCP starter

A code-maintenance MCP server for the existing `farhanx899-cmd/MYBOT` repository. It can report GitHub branch status, list/read allowlisted files, and propose changes as pull requests. It **does not trade**, connect to a broker, merge PRs, or verify Streamlit uptime.

## Tools
- `get_project_status`
- `list_project_files`
- `read_project_file`
- `propose_file_change` (new branch + pull request; no merge)

## Setup
Requires Python 3.11+. Install with `pip install -r requirements.txt`, set environment variables from `.env.example` (never commit secrets), then run `python server.py`.

The server uses MCP Streamable HTTP. For remote use, deploy behind an authenticated HTTPS gateway. Do not expose an unauthenticated MCP endpoint publicly. Use a fine-grained GitHub token limited to this repository with only Contents read/write and Pull Requests read/write permissions as needed. Protect `main` with required reviews/checks.

This is a starter, not a production security boundary: review every diff, add CI tests and audit logging, and never store broker credentials in GitHub. Keep broker execution and persistent risk controls in a separate service. Start with demo trading only; do not allow AI code changes to silently enable live trading.
