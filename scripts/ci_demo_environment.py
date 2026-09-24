"""Create disposable secrets only inside a GitHub-hosted CI workspace."""
import base64
import os
from pathlib import Path
import secrets

if os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("CI only: do not run against a development or production copy.")

root = Path.cwd().resolve()
workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
if root != workspace or not str(workspace).startswith("/home/runner/work/"):
    raise SystemExit("Expected an isolated GitHub-hosted Linux workspace.")

template = (root / ".env.example").read_text(encoding="utf-8")
db_password = secrets.token_urlsafe(32)
values = {
    "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
    "FERNET_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    "MYSQL_ROOT_PASSWORD": db_password,
    "MYSQL_PASSWORD": db_password,
    "MYSQL_DB": "labops_ci",
    "LABOPS_DEMO_ADMIN_PASSWORD": secrets.token_urlsafe(32),
}
for value in values.values():
    print(f"::add-mask::{value}")

lines = [
    line for line in template.splitlines()
    if line.split("=", 1)[0] not in values
]
lines.extend(f"{key}={value}" for key, value in values.items())
target = root / ".env"
with target.open("x", encoding="utf-8") as stream:
    stream.write("\n".join(lines) + "\n")
target.chmod(0o600)
print("Disposable CI configuration created; no real credentials are used.")
