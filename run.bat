@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist .venv (
  echo Chua cai dat. Hay chay install.bat truoc.
  pause & exit /b 1
)
call .venv\Scripts\activate.bat
python -m app.main %*
pause
