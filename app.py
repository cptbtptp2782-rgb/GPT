import platform
import socket
import sys
import threading
import tkinter as tk
from ctypes import POINTER, cast
from pathlib import Path
from tkinter import messagebox

import pystray
from PIL import Image, ImageDraw
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

if platform.system() == "Windows":
    import winreg
else:
    winreg = None

STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APP_NAME = "WindowsMuteControlApp"


class WindowsVolumeController:
    """控制 Windows 系统主输出设备静音状态。"""

    def __init__(self) -> None:
        self._volume = self._create_endpoint_volume()

    @staticmethod
    def _create_endpoint_volume():
        device = AudioUtilities.GetSpeakers()

        endpoint_volume = getattr(device, "EndpointVolume", None)
        if endpoint_volume is not None:
            return endpoint_volume

        activate = getattr(device, "Activate", None)
        if callable(activate):
            interface = activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))

        raw_device = getattr(device, "_device", None)
        if raw_device is not None and hasattr(raw_device, "Activate"):
            interface = raw_device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))

        ctl = getattr(device, "_ctl", None)
        if ctl is not None and hasattr(ctl, "QueryInterface"):
            return ctl.QueryInterface(IAudioEndpointVolume)

        raise RuntimeError(
            "当前 pycaw 版本不支持该音量初始化方式。请更新 requirements 后重新打包 EXE。"
        )

    def mute(self) -> None:
        self._volume.SetMute(1, None)

    def unmute(self) -> None:
        self._volume.SetMute(0, None)

    def toggle(self) -> bool:
        current = bool(self._volume.GetMute())
        target = not current
        self._volume.SetMute(1 if target else 0, None)
        return target

    def is_muted(self) -> bool:
        return bool(self._volume.GetMute())


class UdpControlServer:
    def __init__(self, host: str, port: int, handler) -> None:
        self.host = host
        self.port = port
        self._handler = handler
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._sock:
            self._sock.close()

    def _serve(self) -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.host, self.port))
            sock.settimeout(0.5)
            self._sock = sock
        except OSError as err:
            self._handler("_server_error", str(err))
            return

        self._handler("_server_started", f"UDP监听中：{self.host}:{self.port}")

        while not self._stop_event.is_set():
            try:
                data, addr = sock.recvfrom(1024)
            except TimeoutError:
                continue
            except OSError:
                break

            command = data.decode("utf-8", errors="ignore").strip().lower()
            response = self._handler(command)

            try:
                sock.sendto(response.encode("utf-8"), addr)
            except OSError:
                continue

        self._handler("_server_stopped", "UDP服务已停止")


class MuteControlApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Windows 静音控制")
        self.root.resizable(False, False)

        self.status_var = tk.StringVar(value="请选择操作")
        self.udp_port_var = tk.StringVar(value="9999")

        self.controller = self._create_controller()
        self.udp_server: UdpControlServer | None = None

        self.tray_icon: pystray.Icon | None = None
        self.tray_thread: threading.Thread | None = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.after(250, self.start_udp_server)
        self.root.after(500, self.minimize_to_tray)

    def _create_controller(self) -> WindowsVolumeController | None:
        if platform.system() != "Windows":
            messagebox.showerror("系统不支持", "该程序仅支持 Windows 系统。")
            return None

        try:
            return WindowsVolumeController()
        except Exception as err:  # noqa: BLE001
            messagebox.showerror("初始化失败", f"无法初始化音量控制：{err}")
            return None

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=14, pady=14)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Button(frame, text="静音", width=22, command=lambda: self._run_action("mute")).pack(pady=4)
        tk.Button(frame, text="取消静音", width=22, command=lambda: self._run_action("unmute")).pack(pady=4)
        tk.Button(frame, text="切换静音状态", width=22, command=lambda: self._run_action("toggle")).pack(pady=4)

        udp_row = tk.Frame(frame)
        udp_row.pack(fill=tk.X, pady=(8, 4))
        tk.Label(udp_row, text="UDP端口:").pack(side=tk.LEFT)
        tk.Entry(udp_row, textvariable=self.udp_port_var, width=8).pack(side=tk.LEFT, padx=(4, 8))
        tk.Button(udp_row, text="端口修改确认", command=self.confirm_udp_port).pack(side=tk.LEFT)

        startup_row = tk.Frame(frame)
        startup_row.pack(fill=tk.X, pady=(4, 4))
        tk.Button(startup_row, text="开启开机自启动", command=self.enable_startup).pack(side=tk.LEFT)
        tk.Button(startup_row, text="取消开机自启动", command=self.disable_startup).pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(frame, textvariable=self.status_var, fg="#2b7").pack(anchor="w", pady=(8, 0))

        startup_status = "已开启" if self.is_startup_enabled() else "未开启"
        tk.Label(
            frame,
            justify="left",
            fg="#666",
            text=(
                "说明：\n"
                "1) 启动后自动最小化到托盘后台运行。\n"
                "2) UDP 默认自启动，可修改端口后点“端口修改确认”。\n"
                "3) UDP 指令: mute / unmute / toggle / status\n"
                "4) 托盘图标右键可显示主界面或退出。\n"
                f"5) 开机自启动当前状态: {startup_status}"
            ),
        ).pack(anchor="w", pady=(8, 0))

    def _set_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_var.set(text))

    def _run_action(self, action: str) -> str:
        if self.controller is None:
            self._set_status("初始化失败，无法执行")
            return "ERROR: controller_not_ready"

        try:
            if action == "mute":
                self.controller.mute()
                self._set_status("已静音")
                return "OK: muted"
            if action == "unmute":
                self.controller.unmute()
                self._set_status("已取消静音")
                return "OK: unmuted"
            if action == "toggle":
                is_muted = self.controller.toggle()
                self._set_status("已静音" if is_muted else "已取消静音")
                return "OK: muted" if is_muted else "OK: unmuted"
            if action == "status":
                is_muted = self.controller.is_muted()
                return "OK: muted" if is_muted else "OK: unmuted"
            return "ERROR: unknown_command"
        except Exception as err:  # noqa: BLE001
            self._set_status("操作失败")
            return f"ERROR: {err}"

    def _handle_udp_command(self, command: str, payload: str = "") -> str:
        if command == "_server_error":
            self._set_status(f"UDP启动失败: {payload}")
            return "ERROR: udp_start_failed"
        if command == "_server_started":
            self._set_status(payload)
            return "OK"
        if command == "_server_stopped":
            self._set_status(payload)
            return "OK"
        return self._run_action(command)

    def _get_udp_port(self) -> int | None:
        try:
            port = int(self.udp_port_var.get())
            if not (1 <= port <= 65535):
                raise ValueError
            return port
        except ValueError:
            messagebox.showerror("端口错误", "请输入 1-65535 的端口号")
            return None

    def start_udp_server(self) -> None:
        if self.udp_server is not None:
            return

        port = self._get_udp_port()
        if port is None:
            return

        self.udp_server = UdpControlServer("0.0.0.0", port, self._handle_udp_command)
        self.udp_server.start()

    def confirm_udp_port(self) -> None:
        port = self._get_udp_port()
        if port is None:
            return

        if self.udp_server is not None and self.udp_server.port == port:
            self._set_status(f"UDP端口未变化，当前端口：{port}")
            return

        if self.udp_server is not None:
            self.udp_server.stop()
            self.udp_server = None

        self.udp_server = UdpControlServer("0.0.0.0", port, self._handle_udp_command)
        self.udp_server.start()

    def _startup_command(self) -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        python_exe = sys.executable
        script_path = Path(__file__).resolve()
        return f'"{python_exe}" "{script_path}"'

    def is_startup_enabled(self) -> bool:
        if winreg is None:
            return False

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, STARTUP_APP_NAME)
                return bool(value)
        except FileNotFoundError:
            return False
        except OSError:
            return False

    def enable_startup(self) -> None:
        if winreg is None:
            messagebox.showerror("不支持", "仅支持 Windows 开机自启动设置")
            return

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                STARTUP_REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, STARTUP_APP_NAME, 0, winreg.REG_SZ, self._startup_command())
            self._set_status("已开启开机自启动")
        except OSError as err:
            messagebox.showerror("设置失败", f"无法设置开机自启动：{err}")

    def disable_startup(self) -> None:
        if winreg is None:
            messagebox.showerror("不支持", "仅支持 Windows 开机自启动设置")
            return

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                STARTUP_REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, STARTUP_APP_NAME)
            self._set_status("已取消开机自启动")
        except FileNotFoundError:
            self._set_status("开机自启动原本未开启")
        except OSError as err:
            messagebox.showerror("设置失败", f"无法取消开机自启动：{err}")

    @staticmethod
    def _create_tray_image() -> Image.Image:
        image = Image.new("RGB", (64, 64), (30, 30, 30))
        draw = ImageDraw.Draw(image)
        draw.ellipse((12, 12, 52, 52), fill=(0, 180, 120))
        draw.rectangle((28, 20, 36, 44), fill=(255, 255, 255))
        return image

    def _ensure_tray_icon(self) -> None:
        if self.tray_icon is not None:
            return

        menu = pystray.Menu(
            pystray.MenuItem("显示主界面", lambda icon, item: self.show_window()),
            pystray.MenuItem("退出", lambda icon, item: self.exit_app()),
        )
        self.tray_icon = pystray.Icon("windows_mute_control", self._create_tray_image(), "Windows静音控制", menu)

    def _run_tray(self) -> None:
        if self.tray_icon is None:
            return
        self.tray_icon.run()

    def minimize_to_tray(self) -> None:
        self.root.withdraw()
        self._ensure_tray_icon()
        if self.tray_thread is None or not self.tray_thread.is_alive():
            self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
            self.tray_thread.start()
        self._set_status("程序已最小化到系统托盘")

    def show_window(self) -> None:
        self.root.after(0, self._show_window_on_ui)

    def _show_window_on_ui(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def exit_app(self) -> None:
        self.root.after(0, self._exit_app_on_ui)

    def _exit_app_on_ui(self) -> None:
        if self.udp_server is not None:
            self.udp_server.stop()

        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None

        self.root.destroy()

    def on_close(self) -> None:
        self.minimize_to_tray()


def main() -> None:
    root = tk.Tk()
    MuteControlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
