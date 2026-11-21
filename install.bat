@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==== CAI DAT SHORTS MAKER ====

set PY=
where py >nul 2>nul && (py -3.11 --version >nul 2>nul && set PY=py -3.11)
if "%PY%"=="" (where py >nul 2>nul && (py -3.12 --version >nul 2>nul && set PY=py -3.12))
if "%PY%"=="" (where python >nul 2>nul && set PY=python)
if "%PY%"=="" (
  echo [LOI] Chua cai Python. Tai Python 3.11 tai https://www.python.org/downloads/ ^(nho tick "Add python.exe to PATH"^)
  pause & exit /b 1
)
echo Dung Python: %PY%

if not exist .venv (
  %PY% -m venv .venv || (echo [LOI] Khong tao duoc moi truong ao & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo.
echo ==== 1/4 Cai PyTorch ban cho card NVIDIA (CUDA 12.8, ~3GB) ====
pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128 || (echo [LOI] Cai torch that bai & pause & exit /b 1)

echo.
echo ==== 2/4 Cai thu vien (OmniVoice, yt-dlp, ...) ====
pip install -r requirements.txt || (echo [LOI] Cai thu vien that bai & pause & exit /b 1)

echo.
echo ==== Cai trinh duyet chay an cho Google Images (~150MB) ====
python -m playwright install chromium || echo [CANH BAO] Khong cai duoc Chromium - tool se dung Microsoft Edge co san

echo.
echo ==== 3/4 Tai font chu Nhat ====
python scripts\download_font.py

echo.
echo ==== 4/4 Kiem tra FFmpeg va Claude CLI ====
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo Chua co FFmpeg - dang cai bang winget...
  winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
  echo ^>^> Cai xong FFmpeg thi DONG cua so nay va mo lai de nhan PATH moi.
) else (
  echo FFmpeg: OK
)
where claude >nul 2>nul
if errorlevel 1 (
  echo [CAN LAM] Chua co Claude CLI. Mo PowerShell va chay:
  echo     irm https://claude.ai/install.ps1 ^| iex
  echo Sau do go "claude" mot lan de dang nhap tai khoan Claude.
) else (
  echo Claude CLI: OK
)

python -c "import torch;print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'KHONG THAY GPU - kiem tra driver NVIDIA')"
echo.
echo ==== XONG! Chay run.bat de mo tool ====
pause
