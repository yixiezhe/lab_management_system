#!/usr/bin/env bash
set -euo pipefail

SESSION="lab_management_system"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
STATUS_DIR="$LOG_DIR/tmux-status"

mkdir -p "$LOG_DIR" "$STATUS_DIR"

if ! command -v tmux >/dev/null 2>&1; then
    echo "[ERROR] tmux is not installed in WSL."
    exit 1
fi

if ! command -v wslpath >/dev/null 2>&1; then
    echo "[ERROR] wslpath is not available. Run this script inside WSL."
    exit 1
fi

WIN_ROOT="$(wslpath -w "$ROOT")"
BACKEND_BAT="${WIN_ROOT}\\scripts\\start_backend.bat"
FRONTEND_BAT="${WIN_ROOT}\\scripts\\start_frontend.bat"

window_exists() {
    tmux list-windows -t "$SESSION" -F '#W' 2>/dev/null | grep -Fxq "$1"
}

service_running() {
    local status_file="$STATUS_DIR/$1.status"
    [ -f "$status_file" ] && grep -q '^running ' "$status_file"
}

start_service_window() {
    local service="$1"
    local bat_path="$2"
    local shell_script="$ROOT/scripts/run_windows_bat_in_tmux.sh"

    tmux new-window -d -t "$SESSION" -n "$service" "$shell_script '$service' '$bat_path'"
    echo "[$(date '+%F %T')] Started $service window." >> "$LOG_DIR/tmux-start.log"
}

ensure_service_window() {
    local service="$1"
    local bat_path="$2"

    if window_exists "$service" && service_running "$service"; then
        echo "[INFO] $service is already running."
        return
    fi

    if window_exists "$service"; then
        echo "[INFO] $service window exists but is not running; recreating it."
        tmux kill-window -t "$SESSION:$service" 2>/dev/null || true
    else
        echo "[INFO] $service window is missing; creating it."
    fi

    rm -f "$STATUS_DIR/$service.status"
    start_service_window "$service" "$bat_path"
}

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[$(date '+%F %T')] Starting tmux session '$SESSION'..." >> "$LOG_DIR/tmux-start.log"
    tmux new-session -d -s "$SESSION" -n bootstrap "sleep 3600"
    tmux set-option -t "$SESSION" remain-on-exit on >/dev/null
fi

ensure_service_window backend "$BACKEND_BAT"
ensure_service_window frontend "$FRONTEND_BAT"

if window_exists bootstrap; then
    tmux kill-window -t "$SESSION:bootstrap" 2>/dev/null || true
fi

echo "[INFO] Started tmux session '$SESSION'."
echo "[INFO] View: wsl -d ${WSL_DISTRO_NAME:-Ubuntu} -- tmux attach -t $SESSION"
echo "[INFO] Stop: scripts\\stop_all_tmux.cmd"
