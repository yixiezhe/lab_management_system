#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups/db_auto}"
MYSQL_DB="${MYSQL_DB:-new_lab_system}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
RETENTION_DAYS="${RETENTION_DAYS:-180}"

if [[ -z "$MYSQL_PASSWORD" ]]; then
  echo "[ERROR] MYSQL_PASSWORD is required. Set it in your shell or .env before running this script." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
sql_file="$BACKUP_DIR/${MYSQL_DB}_${timestamp}.sql"
zip_file="$BACKUP_DIR/${MYSQL_DB}_${timestamp}.zip"

cleanup_on_error() {
  if [[ -f "$sql_file" ]]; then
    rm -f "$sql_file"
  fi
}
trap cleanup_on_error ERR

echo "[INFO] $(date '+%F %T') start backup: db=$MYSQL_DB host=$MYSQL_HOST port=$MYSQL_PORT"

MYSQL_PWD="$MYSQL_PASSWORD" mysqldump \
  --protocol=TCP \
  --host="$MYSQL_HOST" \
  --port="$MYSQL_PORT" \
  --user="$MYSQL_USER" \
  --single-transaction \
  --no-tablespaces \
  --routines \
  --events \
  --triggers \
  "$MYSQL_DB" > "$sql_file"

if command -v zip >/dev/null 2>&1; then
  zip -j -q "$zip_file" "$sql_file"
else
  python3 - "$sql_file" "$zip_file" <<'PY'
import pathlib
import sys
import zipfile

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])

with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.write(src, arcname=src.name)
PY
fi

rm -f "$sql_file"

find "$BACKUP_DIR" -type f -name "${MYSQL_DB}_*.zip" -mtime +"$RETENTION_DAYS" -delete || true

echo "[INFO] $(date '+%F %T') backup created: $zip_file"
