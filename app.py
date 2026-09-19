import asyncio
from urllib.parse import urlparse

from flask import Flask, request, Response
from playwright.sync_api import sync_playwright

app = Flask(__name__)

_playwright = None
_browser = None


def get_browser():
    global _playwright, _browser

    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

    return _browser


def valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


GET_URL_HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MVS VPN</title>
<style>
body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f4f4f5;
    font-family: Arial, sans-serif;
}
.box {
    width: min(600px, 90%);
    background: white;
    padding: 30px;
    border-radius: 14px;
    box-shadow: 0 10px 35px rgba(0,0,0,.12);
}
h1 { margin-top: 0; }
input {
    width: 100%;
    padding: 13px;
    border: 1px solid #ccc;
    border-radius: 8px;
    font-size: 16px;
    box-sizing: border-box;
}
button {
    margin-top: 12px;
    width: 100%;
    padding: 13px;
    border: 0;
    border-radius: 8px;
    background: #111827;
    color: white;
    font-size: 16px;
    cursor: pointer;
}
</style>
</head>
<body>
<div class="box">
    <h1>باز کردن سایت</h1>
    <form method="post">
        <input
            type="url"
            name="url"
            placeholder="https://example.com"
            required
        >
        <button type="submit">ارسال</button>
    </form>
</div>
</body>
</html>
"""


@app.route("/get_url", methods=["GET", "POST"])
def get_url():
    if request.method == "GET":
        return GET_URL_HTML

    url = request.form.get("url", "").strip()

    if not valid_url(url):
        return "URL نامعتبر است. باید با http:// یا https:// شروع شود.", 400

    try:
        browser = get_browser()
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # کمی فرصت برای اجرای JavaScript اولیه صفحه
        page.wait_for_timeout(2000)

        result = page.content()
        context.close()

        return Response(result, mimetype="text/html")

    except Exception as exc:
        return f"<h1>خطا</h1><p>{exc}</p>", 502


@app.route("/")
def index():
    return '<meta http-equiv="refresh" content="0; url=/get_url">'


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
