@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"

set "BACKEND_LOG=%ROOT%\logs\backend.log"
set "FRONTEND_LOG=%ROOT%\logs\frontend.log"

echo [%date% %time%] Starting lab management system...
start "Lab Management Backend" cmd /c call "%~dp0start_backend.bat" ^>^> "%BACKEND_LOG%" 2^>^&1
timeout /t 5 /nobreak >nul
start "Lab Management Frontend" cmd /c call "%~dp0start_frontend.bat" ^>^> "%FRONTEND_LOG%" 2^>^&1

echo Backend log:  "%BACKEND_LOG%"
echo Frontend log: "%FRONTEND_LOG%"
