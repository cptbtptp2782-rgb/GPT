# Windows 静音/取消静音工具（支持 UDP 控制）

一个干净、简单的 Python 桌面程序，用于控制 **Windows** 电脑声音：

- 静音
- 取消静音
- 切换静音状态
- UDP 远程指令控制（启动后自动开启）
- 开机自启动 / 取消开机自启动

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

## UDP 控制说明

程序启动后会自动开启 UDP 监听（默认端口 `9999`，可在界面修改）。

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

在仓库根目录双击或执行：

```bat
build_windows_exe.bat
```

打包完成后可执行文件位置：

- `dist\Windows静音控制.exe`

### 方式 2：手动打包

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean mute_control.spec
```
