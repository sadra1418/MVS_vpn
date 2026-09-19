import atexit
import os
import signal
import socket
import subprocess
import time
from urllib.parse import urlparse

from flask import Flask, Response, redirect, request, send_from_directory
from flask_sock import Sock
from playwright.sync_api import sync_playwright

app = Flask(__name__)
sock = Sock(app)

DISPLAY = os.environ.get("DISPLAY", ":99")
VNC_HOST = "127.0.0.1"
VNC_PORT = 5900
SCREEN_WIDTH = 1365
SCREEN_HEIGHT = 768

_playwright = None
_browser = None
_context = None
_page = None
_xvfb = None
_x11vnc = None


def valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def wait_for_port(host, port, timeout=10):
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)

    return False


def start_virtual_display():
    global _xvfb, _x11vnc

    if _xvfb is None:
        _xvfb = subprocess.Popen(
            [
                "Xvfb",
                DISPLAY,
                "-screen",
                "0",
                f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}x24",
                "-ac",
                "+extension",
                "RANDR",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        os.environ["DISPLAY"] = DISPLAY

        if not wait_for_port("127.0.0.1", 6000, timeout=5):
            time.sleep(0.5)

    if _x11vnc is None:
        _x11vnc = subprocess.Popen(
            [
                "x11vnc",
                "-display",
                DISPLAY,
                "-rfbport",
                str(VNC_PORT),
                "-localhost",
                "-forever",
                "-shared",
                "-noxdamage",
                "-wait",
                "5",
                "-defer",
                "5",
                "-threads",
                "-encodings",
                "tight,zrle,hextile",
                "-repeat",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        if not wait_for_port(VNC_HOST, VNC_PORT, timeout=10):
            raise RuntimeError("x11vnc did not start")


def get_browser():
    global _playwright, _browser, _context, _page

    start_virtual_display()

    if _browser is None:
        _playwright = sync_playwright().start()

        browser_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-features=Translate,BackForwardCache",
            "--start-maximized",
        ]

        _browser = _playwright.chromium.launch(
            headless=False,
            args=browser_args,
        )

        _context = _browser.new_context(
            viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),
        )

        _page = _context.new_page()

    return _browser, _page


def cleanup():
    global _playwright, _browser, _context, _page, _x11vnc, _xvfb

    try:
        if _context:
            _context.close()
    except Exception:
        pass

    try:
        if _browser:
            _browser.close()
    except Exception:
        pass

    try:
        if _playwright:
            _playwright.stop()
    except Exception:
        pass

    for process in (_x11vnc, _xvfb):
        try:
            if process and process.poll() is None:
                process.terminate()
        except Exception:
            pass

    _page = None
    _context = None
    _browser = None
    _playwright = None
    _x11vnc = None
    _xvfb = None


atexit.register(cleanup)


GET_URL_HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MVS VPN</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0b1020;
    color: #fff;
    font-family: Arial, sans-serif;
}
.box {
    width: min(620px, 92%);
    padding: 32px;
    border-radius: 18px;
    background: #151b2e;
    box-shadow: 0 20px 70px rgba(0,0,0,.35);
}
h1 { margin: 0 0 10px; }
p { color: #aeb8d0; }
form { margin-top: 24px; }
input {
    width: 100%;
    padding: 15px;
    border: 1px solid #39435f;
    border-radius: 10px;
    background: #0e1425;
    color: #fff;
    font-size: 16px;
    direction: ltr;
}
button {
    margin-top: 12px;
    width: 100%;
    padding: 15px;
    border: 0;
    border-radius: 10px;
    background: #2563eb;
    color: white;
    font-size: 16px;
    cursor: pointer;
}
button:hover { background: #1d4ed8; }
</style>
</head>
<body>
<div class="box">
    <h1>مرورگر زنده MVS</h1>
    <p>آدرس را وارد کن. مرورگر واقعی روی سرور باز می‌شود.</p>
    <form method="post">
        <input type="url" name="url" placeholder="https://example.com" required autofocus>
        <button type="submit">باز کردن مرورگر</button>
    </form>
</div>
</body>
</html>
"""


@app.route("/")
def index():
    return redirect("/get_url")


@app.route("/get_url", methods=["GET", "POST"])
def get_url():
    if request.method == "GET":
        return GET_URL_HTML

    url = request.form.get("url", "").strip()

    if not valid_url(url):
        return "URL نامعتبر است. باید با http:// یا https:// شروع شود.", 400

    try:
        _, page = get_browser()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        return redirect("/browser")

    except Exception as exc:
        return f"<h1>خطا</h1><p>{exc}</p>", 502


@app.route("/browser")
def browser():
    return """<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MVS Live Browser</title>
<style>
html, body {
    margin: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #000;
}
iframe {
    width: 100%;
    height: 100%;
    border: 0;
}
</style>
</head>
<body>
<iframe src="/novnc/vnc.html?autoconnect=true&resize=scale&path=websockify"></iframe>
</body>
</html>
"""


@app.route("/novnc/<path:path>")
def novnc_files(path):
    return send_from_directory("/usr/share/novnc", path)


@sock.route("/websockify")
def websockify(ws):
    upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upstream.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    try:
        upstream.connect((VNC_HOST, VNC_PORT))
        upstream.settimeout(0.2)

        while True:
            try:
                data = ws.receive()
                if data is None:
                    break

                if isinstance(data, str):
                    data = data.encode("latin1")

                if data:
                    upstream.sendall(data)
            except Exception:
                pass

            try:
                data = upstream.recv(65536)
                if data:
                    ws.send(data)
                elif data == b"":
                    break
            except socket.timeout:
                pass
            except Exception:
                break

    finally:
        try:
            upstream.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        upstream.close()


if __name__ == "__main__":
    get_browser()
    app.run(host="0.0.0.0", port=10000, threaded=True)
