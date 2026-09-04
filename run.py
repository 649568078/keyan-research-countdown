import sys
import threading
import time
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen

from research_countdown import create_app


app = create_app()
HOST = "127.0.0.1"
PORT = 5000
APP_URL = f"http://{HOST}:{PORT}"


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
    if "--no-browser" not in sys.argv:
        threading.Thread(target=open_browser_when_ready, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
