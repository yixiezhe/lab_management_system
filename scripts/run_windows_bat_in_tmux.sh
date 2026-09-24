#!/usr/bin/env bash
set -u

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <service-name> <windows-bat-path>"
    exit 2
fi

SERVICE="$1"
BAT_PATH="$2"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
STATUS_DIR="$LOG_DIR/tmux-status"
LOG_FILE="$LOG_DIR/${SERVICE}.tmux.log"
STATUS_FILE="$STATUS_DIR/${SERVICE}.status"
MAX_ATTEMPTS="${LAB_SERVICE_START_MAX_ATTEMPTS:-12}"
RETRY_DELAY_SECONDS="${LAB_SERVICE_START_RETRY_DELAY_SECONDS:-15}"
INTEROP_CHECK_ATTEMPTS="${LAB_WINDOWS_INTEROP_CHECK_ATTEMPTS:-24}"
INTEROP_CHECK_DELAY_SECONDS="${LAB_WINDOWS_INTEROP_CHECK_DELAY_SECONDS:-5}"
INTEROP_CHECK_TIMEOUT_SECONDS="${LAB_WINDOWS_INTEROP_CHECK_TIMEOUT_SECONDS:-10}"
CMD_EXE="${LAB_WINDOWS_CMD_EXE:-}"

mkdir -p "$LOG_DIR" "$STATUS_DIR"

if [ -z "$CMD_EXE" ]; then
    if command -v cmd.exe >/dev/null 2>&1; then
        CMD_EXE="$(command -v cmd.exe)"
    elif [ -x /mnt/c/Windows/System32/cmd.exe ]; then
        CMD_EXE="/mnt/c/Windows/System32/cmd.exe"
    else
        echo "[ERROR] Cannot find cmd.exe. Set LAB_WINDOWS_CMD_EXE to the full path."
        exit 1
    fi
fi

wait_for_windows_interop() {
    local attempt=1

    while [ "$attempt" -le "$INTEROP_CHECK_ATTEMPTS" ]; do
        if timeout "${INTEROP_CHECK_TIMEOUT_SECONDS}s" "$CMD_EXE" /c ver >/dev/null 2>&1; then
            return 0
        fi

        echo "[$(date '+%F %T')] Windows interop is not ready for $SERVICE (check $attempt/$INTEROP_CHECK_ATTEMPTS); retrying in ${INTEROP_CHECK_DELAY_SECONDS}s."
        sleep "$INTEROP_CHECK_DELAY_SECONDS"
        attempt=$((attempt + 1))
    done

    return 1
}

{
    ATTEMPT=1
    STATUS=1

    while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
        echo "[$(date '+%F %T')] Starting $SERVICE via $BAT_PATH (attempt $ATTEMPT/$MAX_ATTEMPTS)"
        echo "starting attempt=$ATTEMPT $(date '+%F %T')" > "$STATUS_FILE"

        if wait_for_windows_interop; then
            echo "running $(date '+%F %T')" > "$STATUS_FILE"
            "$CMD_EXE" /c "$BAT_PATH"
            STATUS=$?
        else
            STATUS=1
            echo "[$(date '+%F %T')] Windows interop did not become ready for $SERVICE."
        fi

        echo "exited $STATUS $(date '+%F %T')" > "$STATUS_FILE"
        echo "[$(date '+%F %T')] $SERVICE exited with status $STATUS"

        if [ "$STATUS" -eq 0 ]; then
            break
        fi

        if [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; then
            echo "[$(date '+%F %T')] Restarting $SERVICE in ${RETRY_DELAY_SECONDS}s."
            sleep "$RETRY_DELAY_SECONDS"
        fi

        ATTEMPT=$((ATTEMPT + 1))
    done

    echo "[$(date '+%F %T')] Keeping tmux pane open for inspection."
} 2>&1 | tee -a "$LOG_FILE"

while true; do
    sleep 3600
done
