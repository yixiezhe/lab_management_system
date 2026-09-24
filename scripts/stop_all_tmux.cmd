@echo off
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/d/Projects/lab_management_system && ./scripts/stop_tmux.sh"
