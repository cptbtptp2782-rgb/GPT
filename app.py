import json
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

try:
    import pyautogui
except ImportError:
    pyautogui = None

CONFIG_PATH = Path(__file__).with_name("click_config.json")


class DelayedClickApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("延迟点击器")
        self.root.resizable(False, False)

        self.status_var = tk.StringVar(value="请输入参数后点击“保存并执行”")

        self.delay_var = tk.StringVar(value="3")
        self.x_var = tk.StringVar(value="500")
        self.y_var = tk.StringVar(value="300")

        self._build_ui()
        self.root.after(200, self._load_and_maybe_autorun)

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=12, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="延迟时间（秒）").grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(container, textvariable=self.delay_var, width=18).grid(row=0, column=1, sticky="ew", pady=4)

        tk.Label(container, text="点击 X 坐标").grid(row=1, column=0, sticky="w", pady=4)
        tk.Entry(container, textvariable=self.x_var, width=18).grid(row=1, column=1, sticky="ew", pady=4)

        tk.Label(container, text="点击 Y 坐标").grid(row=2, column=0, sticky="w", pady=4)
        tk.Entry(container, textvariable=self.y_var, width=18).grid(row=2, column=1, sticky="ew", pady=4)

        tk.Button(container, text="保存并执行", command=self.save_and_start_click).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(10, 6)
        )

        tk.Button(container, text="仅执行（不保存）", command=self.start_click).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(0, 6)
        )

        tk.Label(container, textvariable=self.status_var, fg="#2d5").grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

        tips = (
            "提示：\n"
            "1) 首次点击“保存并执行”后，后续启动会自动执行。\n"
            "2) 坐标原点在屏幕左上角。\n"
            "3) 若要获取坐标，可运行: python -m pyautogui"
        )
        tk.Label(container, text=tips, justify="left", fg="#555").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

    def _update_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_var.set(text))

    def _validate_inputs(self) -> tuple[float, int, int] | None:
        try:
            delay = float(self.delay_var.get())
            x = int(self.x_var.get())
            y = int(self.y_var.get())
            if delay < 0:
                raise ValueError("延迟时间不能小于0")
            return delay, x, y
        except ValueError as err:
            messagebox.showerror("输入错误", f"参数不正确：{err}")
            return None

    def _save_config(self, delay: float, x: int, y: int) -> None:
        config = {"delay": delay, "x": x, "y": y, "auto_run": True}
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_and_maybe_autorun(self) -> None:
        if not CONFIG_PATH.exists():
            return

        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            delay = float(config["delay"])
            x = int(config["x"])
            y = int(config["y"])
            auto_run = bool(config.get("auto_run", True))
        except (ValueError, KeyError, json.JSONDecodeError) as err:
            self._update_status(f"配置读取失败：{err}")
            return

        self.delay_var.set(str(delay))
        self.x_var.set(str(x))
        self.y_var.set(str(y))

        if auto_run:
            self._update_status("检测到已保存参数，程序启动后将自动执行")
            self.start_click()

    def save_and_start_click(self) -> None:
        if pyautogui is None:
            messagebox.showerror(
                "缺少依赖",
                "未安装 pyautogui。请执行: pip install -r requirements.txt",
            )
            return

        values = self._validate_inputs()
        if values is None:
            return

        delay, x, y = values
        try:
            self._save_config(delay, x, y)
        except OSError as err:
            messagebox.showerror("保存失败", f"无法保存配置：{err}")
            return

        self._update_status("配置已保存，后续启动将自动执行")
        self._run_click_worker(delay, x, y)

    def start_click(self) -> None:
        if pyautogui is None:
            messagebox.showerror(
                "缺少依赖",
                "未安装 pyautogui。请执行: pip install -r requirements.txt",
            )
            return

        values = self._validate_inputs()
        if values is None:
            return

        delay, x, y = values
        self._run_click_worker(delay, x, y)

    def _run_click_worker(self, delay: float, x: int, y: int) -> None:
        worker = threading.Thread(target=self._do_click, args=(delay, x, y), daemon=True)
        worker.start()

    def _do_click(self, delay: float, x: int, y: int) -> None:
        self._update_status(f"将在 {delay:.2f} 秒后点击 ({x}, {y})")
        time.sleep(delay)

        try:
            pyautogui.click(x=x, y=y, button="left")
            self._update_status(f"已完成点击：({x}, {y})")
        except Exception as err:  # noqa: BLE001
            self._update_status("点击失败，请检查坐标或权限")
            self.root.after(0, lambda: messagebox.showerror("执行失败", str(err)))


def main() -> None:
    root = tk.Tk()
    DelayedClickApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
