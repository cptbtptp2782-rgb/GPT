@echo off
setlocal

cd /d %~dp0

if not exist .venv (
  py -3 -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean mute_control.spec

echo.
echo Build finished. EXE: dist\Windows静音控制.exe
endlocal
