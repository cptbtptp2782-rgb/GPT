@echo off
setlocal enabledelayedexpansion

cd /d %~dp0

echo [INFO] Working directory: %cd%

set "PY_CMD="
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY_CMD=py -3"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY_CMD=python"
  )
)

if "%PY_CMD%"=="" (
  echo [ERROR] Python not found. Please install Python 3.9+ and add it to PATH.
  goto :fail
)

echo [INFO] Using Python command: %PY_CMD%

if not exist .venv (
  echo [INFO] Creating virtual environment...
  %PY_CMD% -m venv .venv
  if not %errorlevel%==0 (
    echo [ERROR] Failed to create virtual environment.
    goto :fail
  )
) else (
  echo [INFO] Reusing existing .venv
)

call .venv\Scripts\activate
if not %errorlevel%==0 (
  echo [ERROR] Failed to activate virtual environment.
  goto :fail
)

echo [INFO] Installing dependencies...
python -m pip install --upgrade pip
if not %errorlevel%==0 (
  echo [ERROR] Failed to upgrade pip.
  goto :fail
)

pip install -r requirements.txt pyinstaller
if not %errorlevel%==0 (
  echo [ERROR] Failed to install dependencies.
  goto :fail
)

echo [INFO] Building EXE with PyInstaller...
pyinstaller --noconfirm --clean mute_control.spec
if not %errorlevel%==0 (
  echo [ERROR] PyInstaller build failed.
  goto :fail
)

echo.
echo [SUCCESS] Build finished.
echo [SUCCESS] EXE path: dist\Windows静音控制.exe
goto :end

:fail
echo.
echo [FAILED] Build did not complete successfully.

:end
echo.
pause
endlocal
