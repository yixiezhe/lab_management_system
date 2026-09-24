param(
    [Parameter(Mandatory = $true)]
    [string]$Root
)

$ErrorActionPreference = 'SilentlyContinue'

$backend = Join-Path $Root 'scripts\start_backend.bat'
$frontend = Join-Path $Root 'scripts\start_frontend.bat'
$frontendNodeModules = Join-Path $Root 'frontend\node_modules'

$targets = Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -like "*$backend*" -or
            $_.CommandLine -like "*$frontend*" -or
            $_.CommandLine -like "*$frontendNodeModules*" -or
            $_.CommandLine -like "*manage.py runserver 0.0.0.0:8000*"
        )
    } |
    Select-Object -ExpandProperty ProcessId -Unique

foreach ($processId in $targets) {
    & taskkill.exe /PID $processId /T /F | Out-Null
}
