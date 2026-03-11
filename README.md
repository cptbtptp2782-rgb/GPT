# Windows 静音/取消静音工具（支持 UDP 控制）

一个干净、简单的 Python 桌面程序，用于控制 **Windows** 电脑声音：

- 静音
- 取消静音
- 切换静音状态
- UDP 远程指令控制（启动后自动开启）
- 开机自启动 / 取消开机自启动
- 启动后自动最小化到系统托盘后台运行

## 运行环境

- Windows 10/11
- Python 3.9+

## 开发环境启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 托盘运行说明

- 程序启动后会自动最小化到系统托盘后台运行。
- 关闭窗口（右上角 X）不会退出程序，而是最小化到托盘。
- 右键托盘图标可选择：
  - `显示主界面`
  - `退出`

## UDP 控制说明

程序启动后会自动开启 UDP 监听（默认端口 `9999`）。

如需修改端口，在界面输入新端口后点击 `端口修改确认`，程序会自动重启 UDP 监听到新端口，并保存该端口供下次启动自动使用。

支持以下指令（UTF-8 文本）：

- `mute`：静音
- `unmute`：取消静音
- `toggle`：切换静音
- `status`：查询当前状态

本机测试示例：

```bash
python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(b'mute', ('127.0.0.1', 9999)); print(s.recvfrom(1024)[0].decode())"
```

返回示例：`OK: muted` / `OK: unmuted` / `ERROR: ...`

## 开机自启动

界面提供两个按钮：

- `开启开机自启动`
- `取消开机自启动`

实现方式为写入/删除当前用户注册表项：

- `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`

## 打包为 EXE（Windows）

### 方式 1：一键打包（推荐）

在仓库根目录双击或执行（推荐 PowerShell）：

```powershell
PowerShell -ExecutionPolicy Bypass -File .\build_windows_exe.ps1
```

或继续使用 bat：

```bat
build_windows_exe.bat
```

打包完成后可执行文件位置：

- `dist\Windows静音控制.exe`

### 常见问题：双击 bat 没反应

已在脚本中增加日志和 `pause`，现在会显示执行步骤与错误原因。

另外提供了 `build_windows_exe.ps1`，通常在 Windows 上提示更清晰，建议优先使用。

如果仍失败，请重点检查：

1. 是否已安装 Python 3.9+。
2. `py` 或 `python` 是否在 PATH 中（在 `cmd` 执行 `py --version` 或 `python --version`）。
3. 是否被杀毒软件拦截了 `pyinstaller`。
4. 若提示“`AudioDevice` 没有 `Activate`”，请先执行 `pip install -U pycaw comtypes` 后重新打包 EXE；当前版本已兼容 `EndpointVolume / Activate / _ctl.QueryInterface` 多种路径。

### 方式 2：手动打包

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean mute_control.spec
```
