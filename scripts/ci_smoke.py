"""HTTP smoke checks against the disposable CI demo; never production."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

if os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("CI only.")
root = Path.cwd().resolve()
if (
    root != Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    or not str(root).startswith("/home/runner/work/")
):
    raise SystemExit("Expected an isolated GitHub-hosted Linux workspace.")

values = dict(
    line.split("=", 1)
    for line in (root / ".env").read_text(encoding="utf-8").splitlines()
    if "=" in line and not line.startswith("#")
)
base = "http://127.0.0.1:5173"

def request(path, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if payload is None else json.dumps(payload).encode()
    req = Request(base + path, data=body, headers=headers)
    try:
        with urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, None

def require(condition, label):
    if not condition:
        raise SystemExit(f"Smoke check failed: {label}")
    print(f"PASS: {label}")

status, _ = request("/api/users/me/")
require(status in (401, 403), "anonymous access to user profile is denied")
status, login = request(
    "/api/token/",
    {"username": "localadmin", "password": values["LABOPS_DEMO_ADMIN_PASSWORD"]},
)
require(status == 200 and bool(login.get("access")), "synthetic admin can log in")
token = login["access"]
status, user = request("/api/users/me/", token=token)
require(
    status == 200 and user.get("username") == "localadmin",
    "authenticated profile through frontend reverse proxy",
)
status, equipment = request("/api/equipment/equipments/", token=token)
rows = equipment if isinstance(equipment, list) else (equipment or {}).get("results", [])
require(status == 200 and len(rows) == 2, "two synthetic instruments are available")
status, purchases = request("/api/procurement/public-purchase-requests/", token=token)
rows = purchases if isinstance(purchases, list) else (purchases or {}).get("results", [])
require(status == 200 and rows == [], "no real procurement records in the demo")
print("No model provider, RAG service, remote desktop, or production endpoint was contacted.")
