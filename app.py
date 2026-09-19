import re
import threading
import uuid
from urllib.parse import urljoin, urlparse

import httpx
from flask import Flask, request, Response, jsonify, make_response
from playwright.sync_api import sync_playwright

from config import TARGET_URL, PORT

app = Flask(__name__)

parsed_target = urlparse(TARGET_URL)
TARGET_ORIGIN = f"{parsed_target.scheme}://{parsed_target.netloc}"
TARGET_HOST = parsed_target.netloc

client = httpx.Client(
    follow_redirects=True,
    timeout=60.0,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    },
)

# A real Chromium page is kept per proxy session.
# The visible browser still uses the normal proxy, while every click is
# replayed on this server-side page at the same coordinates.
_playwright = None
_browser = None
_sessions = {}
_sessions_lock = threading.Lock()


def get_browser():
    global _playwright, _browser
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
    return _browser


def get_session(session_id, viewport=None):
    with _sessions_lock:
        session = _sessions.get(session_id)
        if session is not None:
            return session

        browser = get_browser()
        width = int((viewport or {}).get("width") or 1280)
        height = int((viewport or {}).get("height") or 720)
        width = max(320, min(width, 3840))
        height = max(240, min(height, 2160))

        context = browser.new_context(
            viewport={"width": width, "height": height},
            user_agent=client.headers["User-Agent"],
        )
        page = context.new_page()
        session = {"context": context, "page": page, "url": None}
        _sessions[session_id] = session
        return session


def rewrite_url(url: str) -> str:
    if not url or url.startswith(("data:", "javascript:", "#")):
        return url
    if url.startswith("//"):
        url = parsed_target.scheme + ":" + url

    full = urljoin(TARGET_ORIGIN + "/", url)
    parsed = urlparse(full)

    if parsed.netloc == TARGET_HOST or not parsed.netloc:
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        return path

    return full


CLICK_SCRIPT = r"""
<script>
(() => {
    if (window.__mvsClickReplayInstalled) return;
    window.__mvsClickReplayInstalled = true;

    document.addEventListener("click", (event) => {
        if (event.button !== 0) return;

        const payload = {
            x: event.clientX,
            y: event.clientY,
            scroll_x: window.scrollX,
            scroll_y: window.scrollY,
            width: window.innerWidth,
            height: window.innerHeight,
            url: window.location.pathname + window.location.search,
            button: event.button,
            timestamp: Date.now()
        };

        fetch("/_mvs/click", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "same-origin",
            body: JSON.stringify(payload),
            keepalive: true
        }).catch(() => {});
    }, true);
})();
</script>
"""


def rewrite_html(html: str) -> str:
    def repl_attr(match):
        attr = match.group(1)
        quote = match.group(2)
        url = match.group(3)
        return f"{attr}={quote}{rewrite_url(url)}{quote}"

    html = re.sub(
        r'(href|src|action)=(["\'])(.*?)\2',
        repl_attr,
        html,
        flags=re.IGNORECASE,
    )

    def repl_css(match):
        url = match.group(1).strip(" \'\"")
        return f"url({rewrite_url(url)})"

    html = re.sub(r"url\(([^)]+)\)", repl_css, html, flags=re.IGNORECASE)

    base_tag = '<base href="/">'
    if "<head" in html.lower():
        html = re.sub(
            r"(<head[^>]*>)",
            r"\1" + base_tag,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html = base_tag + html

    if "</body>" in html.lower():
        html = re.sub(
            r"</body>",
            CLICK_SCRIPT + "</body>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html += CLICK_SCRIPT

    return html


def proxy_path_to_target(path: str, query_string: str = "") -> str:
    target = urljoin(TARGET_ORIGIN + "/", path or "")
    if query_string:
        target += "?" + query_string
    return target


@app.post("/_mvs/click")
def replay_click():
    data = request.get_json(silent=True) or {}

    try:
        x = float(data["x"])
        y = float(data["y"])
        scroll_x = float(data.get("scroll_x", 0))
        scroll_y = float(data.get("scroll_y", 0))
        width = int(data.get("width", 1280))
        height = int(data.get("height", 720))
        clicked_path = str(data.get("url", "/"))
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "invalid click payload"}), 400

    if not (0 <= x <= width and 0 <= y <= height):
        return jsonify({"ok": False, "error": "click is outside viewport"}), 400

    session_id = request.cookies.get("mvs_session")
    if not session_id:
        session_id = uuid.uuid4().hex

    try:
        session = get_session(
            session_id,
            {"width": width, "height": height},
        )
        page = session["page"]

        target_url = proxy_path_to_target(clicked_path)

        # First click starts the real browser at the same page the user sees.
        # Later clicks keep the real browser's JS state unless the URL changed.
        current_location = (urlparse(page.url).path + "?" + urlparse(page.url).query) if page.url else None
        target_location = urlparse(target_url).path + ("?" + urlparse(target_url).query if urlparse(target_url).query else "")

        if not page.url or current_location != target_location:
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

        page.evaluate(
            "(p) => window.scrollTo(p.x, p.y)",
            {"x": scroll_x, "y": scroll_y},
        )
        page.mouse.click(x, y)
        page.wait_for_timeout(150)

        session["url"] = page.url

        response = make_response(jsonify({
            "ok": True,
            "url": page.url,
            "x": x,
            "y": y,
            "replayed": True,
        }))
        response.set_cookie(
            "mvs_session",
            session_id,
            httponly=True,
            samesite="Lax",
        )
        return response

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "replayed": False,
        }), 502


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    # The internal click endpoint must not be sent to the target site.
    if path == "_mvs/click":
        return jsonify({"error": "use POST"}), 405

    target = proxy_path_to_target(
        path,
        request.query_string.decode(),
    )

    headers = {
        "User-Agent": request.headers.get(
            "User-Agent",
            client.headers["User-Agent"],
        ),
        "Accept": request.headers.get("Accept", "*/*"),
        "Accept-Language": request.headers.get(
            "Accept-Language",
            "en-US,en;q=0.9",
        ),
        "Referer": TARGET_ORIGIN + "/",
    }

    cookies = {k: v for k, v in request.cookies.items() if k != "mvs_session"}

    try:
        if request.method == "GET":
            resp = client.get(target, headers=headers, cookies=cookies)
        elif request.method == "POST":
            resp = client.post(
                target,
                headers=headers,
                cookies=cookies,
                content=request.get_data(),
            )
        else:
            resp = client.request(
                request.method,
                target,
                headers=headers,
                cookies=cookies,
                content=request.get_data(),
            )
    except Exception as exc:
        return f"خطا در پروکسی: {exc}", 502

    content_type = resp.headers.get("content-type", "")
    content = resp.content

    if "text/html" in content_type:
        try:
            text = content.decode(
                resp.encoding or "utf-8",
                errors="replace",
            )
            content = rewrite_html(text).encode("utf-8")
        except Exception:
            pass

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
        "content-security-policy",
        "x-frame-options",
    }
    response_headers = [
        (k, v)
        for k, v in resp.headers.items()
        if k.lower() not in excluded_headers
    ]

    flask_resp = Response(
        content,
        status=resp.status_code,
        headers=response_headers,
    )

    for cookie in resp.cookies.jar:
        flask_resp.set_cookie(
            cookie.name,
            cookie.value,
            path=cookie.path or "/",
        )

    return flask_resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
