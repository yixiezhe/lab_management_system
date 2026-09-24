# Win11 开机自启动设置

当前配置使用 WSL 里的 `tmux` 常驻运行前后端，不再弹出多个终端窗口。

## 已设置好的开机入口

启动入口位于：

```text
C:\Users\land1\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Lab Management System.vbs
```

Win11 登录用户 `land1` 后会静默执行：

```text
D:\Projects\lab_management_system\scripts\start_all_tmux.cmd
```

然后在 WSL 的 tmux session `lab_management_system` 中启动：

- backend：`D:\Projects\lab_management_system\scripts\start_backend.bat`
- frontend：`D:\Projects\lab_management_system\scripts\start_frontend.bat`

关闭普通终端窗口不会停止系统，因为前后端已经挂在 tmux session 里。

## 手动启动

双击：

```text
D:\Projects\lab_management_system\scripts\start_all_tmux.cmd
```

## 手动停止

双击：

```text
D:\Projects\lab_management_system\scripts\stop_all_tmux.cmd
```

这个脚本会先给 tmux 里的前后端发送 `Ctrl-C`，然后结束 tmux session，并清理由本项目启动脚本拉起的 Windows 子进程。

## 查看运行状态

在 PowerShell 里执行：

```powershell
wsl -d Ubuntu -- tmux ls
```

如果看到 `lab_management_system`，说明系统正在 tmux 中运行。

## 进入后台终端查看输出

在 PowerShell 里执行：

```powershell
wsl -d Ubuntu -- tmux attach -t lab_management_system
```

退出查看但不停止服务：按 `Ctrl+B`，松开后按 `D`。

不要直接在 tmux 里按 `Ctrl+C`，除非你就是想停止当前 pane 里的服务。

## 日志

日志会写到：

```text
D:\Projects\lab_management_system\logs\backend.tmux.log
D:\Projects\lab_management_system\logs\frontend.tmux.log
D:\Projects\lab_management_system\logs\tmux-start.log
D:\Projects\lab_management_system\logs\tmux-stop.log
```

旧的 `start_all.bat`、`start_backend.bat`、`start_frontend.bat` 仍然保留，其中后两个会被 tmux 启动脚本复用。
