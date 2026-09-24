#!/usr/bin/env bash
set -euo pipefail

SESSION="lab_management_system"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
STATUS_DIR="$LOG_DIR/tmux-status"

mkdir -p "$LOG_DIR"

if ! command -v tmux >/dev/null 2>&1; then
    echo "[ERROR] tmux is not installed in WSL."
    exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[INFO] Sending Ctrl-C to tmux session '$SESSION'..."
    tmux send-keys -t "$SESSION:frontend" C-c 2>/dev/null || true
    tmux send-keys -t "$SESSION:backend" C-c 2>/dev/null || true
    sleep 1
    tmux send-keys -t "$SESSION:frontend" y Enter 2>/dev/null || true
    tmux send-keys -t "$SESSION:backend" y Enter 2>/dev/null || true
    sleep 3
    tmux kill-session -t "$SESSION" 2>/dev/null || true
else
    echo "[INFO] tmux session '$SESSION' is not running."
fi

POWERSHELL_EXE="${LAB_WINDOWS_POWERSHELL_EXE:-}"
if [ -z "$POWERSHELL_EXE" ]; then
    if command -v powershell.exe >/dev/null 2>&1; then
        POWERSHELL_EXE="$(command -v powershell.exe)"
    elif [ -x /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe ]; then
        POWERSHELL_EXE="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    fi
fi

if [ -n "$POWERSHELL_EXE" ] && command -v wslpath >/dev/null 2>&1; then
    WIN_ROOT="$(wslpath -w "$ROOT")"
    STOP_PS1="$(wslpath -w "$ROOT/scripts/stop_windows_processes.ps1")"
    "$POWERSHELL_EXE" -NoProfile -ExecutionPolicy Bypass -File "$STOP_PS1" -Root "$WIN_ROOT" >/dev/null 2>&1 || true
fi

echo "[$(date '+%F %T')] Stopped tmux session '$SESSION'." >> "$LOG_DIR/tmux-stop.log"
rm -f "$STATUS_DIR/backend.status" "$STATUS_DIR/frontend.status" 2>/dev/null || true
echo "[INFO] Stopped lab management system."
