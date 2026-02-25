# 延迟定点左键点击工具

这是一个简单的桌面应用：首次输入延迟时间与坐标并“保存并执行”后，会持久化配置；后续再次启动程序会自动按该配置执行一次鼠标左键点击。

## 功能

- 自定义延迟秒数。
- 自定义点击坐标（X/Y）。
- 首次保存后自动持久化配置到本地文件。
- 程序后续启动时自动读取配置并执行点击。

## 运行环境

- Python 3.9+
- Windows / macOS / Linux（需允许自动化控制鼠标权限）

## 安装与启动

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 请使用 .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 使用说明

1. 首次运行，输入延迟时间（秒）和目标坐标 X/Y。
2. 点击“保存并执行”。
3. 程序会把参数保存到 `click_config.json`。
4. 下次运行 `python app.py` 时，会自动读取并执行，无需重复输入。

> 小技巧：如果你不清楚坐标，可在终端运行 `python -m pyautogui` 查看当前鼠标位置。
