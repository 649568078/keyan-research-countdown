import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from research_countdown import create_app


HOST = "127.0.0.1"
PORT = 5000
APP_URL = f"http://{HOST}:{PORT}"


def runtime_data_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    return Path(__file__).resolve().parent / "instance"


def acquire_single_instance_lock():
    runtime_data_dir().mkdir(parents=True, exist_ok=True)
    lock_file = (runtime_data_dir() / "app.lock").open("a+b")

    if sys.platform == "win32":
        import msvcrt

        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            lock_file.close()
            return None
    else:
        import fcntl

        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock_file.close()
            return None

    return lock_file


def is_app_running():
    try:
        with urlopen(APP_URL, timeout=0.4):
            return True
    except (URLError, OSError):
        return False


def open_browser_when_ready():
    """等待本地服务可访问后，再用默认浏览器打开页面。"""
    for _ in range(50):
        try:
            with urlopen(APP_URL, timeout=0.3):
                webbrowser.open_new(APP_URL)
                return
        except (URLError, OSError):
            time.sleep(0.1)


def main():
    if is_app_running():
        if "--no-browser" not in sys.argv:
            webbrowser.open_new(APP_URL)
        return

    lock_file = acquire_single_instance_lock()
    if lock_file is None:
        if "--no-browser" not in sys.argv:
            open_browser_when_ready()
        return

    if "--no-browser" not in sys.argv:
        threading.Thread(target=open_browser_when_ready, daemon=True).start()

    app = create_app()
    try:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    finally:
        lock_file.close()


if __name__ == "__main__":
    main()
