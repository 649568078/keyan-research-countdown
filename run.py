import json
import os
import socket
import sys
import threading
import time
import traceback
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path

from werkzeug.serving import make_server

from research_countdown import create_app


HOST = "127.0.0.1"
DEFAULT_PORT = 5000
READY_TIMEOUT_SECONDS = 12
APP_TITLE = "科研倒计时"


def runtime_data_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    return Path(__file__).resolve().parent / "instance"


def app_url(port):
    return f"http://{HOST}:{port}"


def log_message(message):
    try:
        runtime_data_dir().mkdir(parents=True, exist_ok=True)
        with (runtime_data_dir() / "startup.log").open("a", encoding="utf-8") as log:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"[{now}] {message}\n")
    except OSError:
        pass


def port_file_path():
    return runtime_data_dir() / "app.port"


def write_port_file(port):
    try:
        port_file_path().write_text(json.dumps({"port": port}), encoding="utf-8")
    except OSError as exc:
        log_message(f"Failed to write port file: {exc}")


def read_port_file():
    try:
        data = json.loads(port_file_path().read_text(encoding="utf-8"))
        return int(data["port"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return DEFAULT_PORT


def acquire_single_instance_lock():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateMutexW(None, False, "Local\\ResearchCountdownSingleInstance")
        if not handle:
            log_message(f"CreateMutexW failed: {ctypes.get_last_error()}")
            return None

        if ctypes.get_last_error() == 183:
            kernel32.CloseHandle(handle)
            return None

        class WindowsMutex:
            def close(self):
                kernel32.CloseHandle(handle)

        return WindowsMutex()

    runtime_data_dir().mkdir(parents=True, exist_ok=True)
    lock_file = (runtime_data_dir() / "app.lock").open("a+b")

    import fcntl

    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        return None

    class FileLock:
        def close(self):
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()

    return FileLock()


def probe_app(port):
    try:
        with socket.create_connection((HOST, port), timeout=0.5) as connection:
            request = f"GET /health HTTP/1.1\r\nHost: {HOST}:{port}\r\nConnection: close\r\n\r\n"
            connection.sendall(request.encode("ascii"))
            response = connection.recv(128)
            return response.startswith(b"HTTP/1.1 200") or response.startswith(b"HTTP/1.0 200")
    except (OSError, TypeError, ValueError):
        return False


def open_browser(url):
    log_message(f"Opening browser: {url}")
    try:
        if sys.platform == "win32":
            os.startfile(url)
        else:
            webbrowser.open_new(url)
    except OSError as exc:
        log_message(f"Failed to open browser: {exc}")


def open_browser_when_ready(port=None):
    deadline = time.time() + READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        current_port = port or read_port_file()
        if probe_app(current_port):
            open_browser(app_url(current_port))
            return
        time.sleep(0.2)
    log_message(f"Server was not ready in {READY_TIMEOUT_SECONDS}s")


def should_auto_open_browser():
    return "--auto-browser" in sys.argv and "--no-browser" not in sys.argv


def bind_server(app):
    try:
        server = make_server(HOST, DEFAULT_PORT, app, threaded=True)
        return server, DEFAULT_PORT
    except OSError as exc:
        log_message(f"Port {DEFAULT_PORT} unavailable, choosing a free port: {exc}")

    server = make_server(HOST, 0, app, threaded=True)
    return server, server.server_port


def show_control_panel(port, server):
    url = app_url(port)
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("420x220")
    root.resizable(False, False)

    is_closing = {"value": False}
    status_var = tk.StringVar(value="服务已启动，可以打开网页")

    def set_status():
        if is_closing["value"]:
            return
        if probe_app(port):
            status_var.set("服务已启动，可以打开网页")
            return
        status_var.set("正在确认服务状态，仍可尝试打开网页")
        root.after(500, set_status)

    def open_current_page():
        open_browser(url)

    def copy_url():
        root.clipboard_clear()
        root.clipboard_append(url)
        status_var.set("地址已复制")

    def close_app():
        is_closing["value"] = True
        log_message("Closing app from control panel")
        try:
            server.shutdown()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", close_app)

    frame = tk.Frame(root, padx=24, pady=22)
    frame.pack(fill="both", expand=True)

    title = tk.Label(frame, text=APP_TITLE, font=("Microsoft YaHei UI", 16, "bold"))
    title.pack(anchor="w")

    status = tk.Label(frame, textvariable=status_var, fg="#475569", font=("Microsoft YaHei UI", 10))
    status.pack(anchor="w", pady=(8, 0))

    url_label = tk.Label(frame, text=url, fg="#2563eb", font=("Consolas", 10))
    url_label.pack(anchor="w", pady=(10, 18))

    buttons = tk.Frame(frame)
    buttons.pack(anchor="w")

    open_button = tk.Button(buttons, text="打开网页", width=12, command=open_current_page)
    open_button.pack(side="left")

    copy_button = tk.Button(buttons, text="复制地址", width=12, command=copy_url)
    copy_button.pack(side="left", padx=(10, 0))

    quit_button = tk.Button(buttons, text="退出程序", width=12, command=close_app)
    quit_button.pack(side="left", padx=(10, 0))

    root.after(100, set_status)
    root.mainloop()


def show_existing_instance_panel(port):
    url = app_url(port)
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("420x180")
    root.resizable(False, False)

    def open_current_page():
        open_browser(url)

    def copy_url():
        root.clipboard_clear()
        root.clipboard_append(url)

    frame = tk.Frame(root, padx=24, pady=22)
    frame.pack(fill="both", expand=True)

    title = tk.Label(frame, text="程序已经在运行", font=("Microsoft YaHei UI", 15, "bold"))
    title.pack(anchor="w")

    url_label = tk.Label(frame, text=url, fg="#2563eb", font=("Consolas", 10))
    url_label.pack(anchor="w", pady=(12, 18))

    buttons = tk.Frame(frame)
    buttons.pack(anchor="w")

    tk.Button(buttons, text="打开网页", width=12, command=open_current_page).pack(side="left")
    tk.Button(buttons, text="复制地址", width=12, command=copy_url).pack(side="left", padx=(10, 0))
    tk.Button(buttons, text="关闭", width=12, command=root.destroy).pack(side="left", padx=(10, 0))

    root.mainloop()


def main():
    try:
        existing_port = read_port_file()
        if probe_app(existing_port):
            if "--no-gui" in sys.argv and should_auto_open_browser():
                open_browser(app_url(existing_port))
            elif "--no-gui" not in sys.argv:
                show_existing_instance_panel(existing_port)
            return

        lock_file = acquire_single_instance_lock()
        if lock_file is None:
            if "--no-gui" not in sys.argv:
                show_existing_instance_panel(read_port_file())
            elif should_auto_open_browser():
                open_browser_when_ready()
            return

        app = create_app()
        server, port = bind_server(app)
        write_port_file(port)
        log_message(f"Server started: {app_url(port)}")

        if should_auto_open_browser():
            threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            if "--no-gui" in sys.argv:
                server_thread.join()
            else:
                show_control_panel(port, server)
        finally:
            server.server_close()
            lock_file.close()
    except Exception:
        log_message(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
