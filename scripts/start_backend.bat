@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "CONDA_BAT="
if exist "D:\Users\%USERNAME%\anaconda3\condabin\conda.bat" set "CONDA_BAT=D:\Users\%USERNAME%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "D:\Users\%USERNAME%\miniconda3\condabin\conda.bat" set "CONDA_BAT=D:\Users\%USERNAME%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "C:\ProgramData\anaconda3\condabin\conda.bat" set "CONDA_BAT=C:\ProgramData\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT (
    for /f "delims=" %%I in ('where conda.bat 2^>nul') do if not defined CONDA_BAT set "CONDA_BAT=%%I"
)

if not defined CONDA_BAT (
    echo [ERROR] Cannot find conda.bat. Edit scripts\start_backend.bat and scripts\start_frontend.bat.
    exit /b 1
)

cd /d "%ROOT%\DjangoProject" || exit /b 1
call "%CONDA_BAT%" activate CGCNN || exit /b 1

echo [%date% %time%] Starting Django backend...
python manage.py migrate || exit /b 1
python manage.py runserver 0.0.0.0:8000
