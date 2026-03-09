$ErrorActionPreference = 'Stop'

Set-Location -Path $PSScriptRoot
Write-Host "[INFO] Working directory: $PWD"

$pythonLauncher = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonLauncher = @{ Cmd = 'py'; Args = @('-3') }
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonLauncher = @{ Cmd = 'python'; Args = @() }
} else {
    Write-Host ''
    Write-Host '[FAILED] Python 未找到。请安装 Python 3.9+ 并加入 PATH。' -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Using Python command: $($pythonLauncher.Cmd) $($pythonLauncher.Args -join ' ')"

try {
    if (-not (Test-Path '.venv')) {
        Write-Host '[INFO] Creating virtual environment...'
        & $pythonLauncher.Cmd @($pythonLauncher.Args + @('-m', 'venv', '.venv'))
    } else {
        Write-Host '[INFO] Reusing existing .venv'
    }

    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPython)) {
        throw '虚拟环境 Python 不存在，创建 .venv 失败。'
    }

    Write-Host '[INFO] Installing dependencies...'
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt pyinstaller

    Write-Host '[INFO] Building EXE with PyInstaller...'
    & $venvPython -m PyInstaller --noconfirm --clean mute_control.spec

    Write-Host ''
    Write-Host '[SUCCESS] Build finished.'
    Write-Host '[SUCCESS] EXE path: dist\Windows静音控制.exe'
} catch {
    Write-Host ''
    Write-Host "[FAILED] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
