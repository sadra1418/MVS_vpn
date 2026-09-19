import base64
import threading
import time
import uuid
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, make_response, request
from playwright.sync_api import sync_playwright

from config import TARGET_URL, PORT

app = Flask(__name__)

_playwright = None
_browser = None
_sessions = {}
_sessions_lock = threading.Lock()

SESSION_TTL = 30 * 60
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720


def get_browser():
    global _playwright, _browser

    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

    return _browser


def cleanup_sessions():
    now = time.time()
    expired = []

    with _sessions_lock:
        for session_id, session in _sessions.items():
            if now - session["last_seen"] > SESSION_TTL:
                expired.append((session_id, session))

        for session_id, _ in expired:
            _sessions.pop(session_id, None)

    for _, session in expired:
        try:
            session["context"].close()
        except Exception:
            pass


def get_session(session_id):
    cleanup_sessions()

    with _sessions_lock:
        existing = _sessions.get(session_id)
        if existing:
            existing["last_seen"] = time.time()
            return existing

        browser = get_browser()
        context = browser.new_context(
            viewport={
                "width": VIEWPORT_WIDTH,
                "height": VIEWPORT_HEIGHT,
            },
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        session = {
            "context": context,
            "page": page,
            "lock": threading.RLock(),
            "last_seen": time.time(),
            "started": False,
        }
        _sessions[session_id] = session
        return session


def session_id_from_request():
    return request.cookies.get("mvs_session") or uuid.uuid4().hex


def set_session_cookie(response, session_id):
    response.set_cookie(
        "mvs_session",
        session_id,
        httponly=True,
        samesite="Lax",
        max_age=SESSION_TTL,
    )
    return response


def ensure_started(session):
    page = session["page"]

    if session["started"] and not page.is_closed():
        return

    page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
    session["started"] = True


def screenshot_response(session):
    with session["lock"]:
        ensure_started(session)
        image = session["page"].screenshot(
            type="jpeg",
            quality=65,
            animations="disabled",
        )

    response = Response(image, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


BROWSER_HTML = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MVS Remote Browser</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    min-height: 100vh;
    background: #0b0d10;
    color: #fff;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.topbar {
    height: 56px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 14px;
    background: #15181d;
    border-bottom: 1px solid #292e36;
}
.title { font-weight: 700; white-space: nowrap; }
.status {
    font-size: 13px;
    color: #9aa4b2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.viewer-wrap {
    width: min(1280px, 100vw);
    margin: 0 auto;
    padding: 10px;
}
.viewer {
    position: relative;
    width: 100%;
    background: #000;
    border: 1px solid #292e36;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 12px 40px rgba(0,0,0,.35);
}
#screen {
    display: block;
    width: 100%;
    height: auto;
    user-select: none;
    -webkit-user-drag: none;
    cursor: default;
}
#inputLayer {
    position: absolute;
    inset: 0;
    outline: none;
}
.help {
    padding: 8px 4px;
    color: #8e98a7;
    font-size: 12px;
}
button {
    border: 1px solid #39414d;
    background: #20252d;
    color: white;
    border-radius: 6px;
    padding: 7px 10px;
    cursor: pointer;
}
button:hover { background: #292f38; }
</style>
</head>
<body>
<div class="topbar">
    <div class="title">MVS Remote Browser</div>
    <button id="refresh">بازخوانی</button>
    <div class="status" id="status">در حال اتصال به مرورگر سرور...</div>
</div>

<div class="viewer-wrap">
    <div class="viewer">
        <img id="screen" draggable="false" alt="Remote browser">
        <div id="inputLayer" tabindex="0"></div>
    </div>
    <div class="help">
        این تصویر، صفحه Chromium روی سرور است. کلیک، اسکرول و کیبورد به همان مرورگر ارسال می‌شود.
    </div>
</div>

<script>
const screen = document.getElementById("screen");
const layer = document.getElementById("inputLayer");
const statusEl = document.getElementById("status");
let running = false;
let timer = null;

function setStatus(text) {
    statusEl.textContent = text;
}

async function start() {
    setStatus("در حال اجرای Chromium روی سرور...");
    const r = await fetch("/_mvs/start", {method: "POST"});
    const data = await r.json();

    if (!r.ok || !data.ok) {
        throw new Error(data.error || "browser start failed");
    }

    running = true;
    setStatus("متصل");
    refreshScreen();
    schedule();
}

function refreshScreen() {
    if (!running) return;
    screen.src = "/_mvs/screen?t=" + Date.now();
}

function schedule() {
    clearTimeout(timer);
    timer = setTimeout(() => {
        refreshScreen();
        schedule();
    }, 600);
}

function pointFromEvent(event) {
    const rect = screen.getBoundingClientRect();
    const scaleX = 1280 / rect.width;
    const scaleY = 720 / rect.height;

    return {
        x: Math.max(0, Math.min(1279, (event.clientX - rect.left) * scaleX)),
        y: Math.max(0, Math.min(719, (event.clientY - rect.top) * scaleY))
    };
}

async function sendEvent(type, payload = {}) {
    const r = await fetch("/_mvs/event", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({type, ...payload})
    });
    const data = await r.json();

    if (!r.ok || !data.ok) {
        setStatus(data.error || "خطا");
    }

    refreshScreen();
}

layer.addEventListener("click", event => {
    event.preventDefault();
    layer.focus();

    const p = pointFromEvent(event);
    sendEvent("click", p);
});

layer.addEventListener("wheel", event => {
    event.preventDefault();
    layer.focus();
    sendEvent("wheel", {delta_x: event.deltaX, delta_y: event.deltaY});
}, {passive: false});

layer.addEventListener("keydown", event => {
    event.preventDefault();

    let key = event.key;
    if (event.ctrlKey && key.length === 1) key = "Control+" + key.toUpperCase();
    if (event.altKey && key.length === 1) key = "Alt+" + key;
    if (event.shiftKey && key.length === 1) key = "Shift+" + key;

    sendEvent("key", {key});
});

document.getElementById("refresh").addEventListener("click", () => {
    refreshScreen();
});

start().catch(error => {
    setStatus("خطا: " + error.message);
});
</script>
</body>
</html>
"""


@app.get("/")
def index():
    return BROWSER_HTML


@app.post("/_mvs/start")
def start_browser():
    session_id = session_id_from_request()

    try:
        session = get_session(session_id)
        with session["lock"]:
            ensure_started(session)

        response = make_response(jsonify({
            "ok": True,
            "url": session["page"].url,
        }))
        return set_session_cookie(response, session_id)

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 502


@app.get("/_mvs/screen")
def screen():
    session_id = request.cookies.get("mvs_session")

    if not session_id:
        return jsonify({"ok": False, "error": "session not started"}), 400

    try:
        session = get_session(session_id)
        response = screenshot_response(session)
        response.set_cookie(
            "mvs_session",
            session_id,
            httponly=True,
            samesite="Lax",
            max_age=SESSION_TTL,
        )
        return response
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 502


@app.post("/_mvs/event")
def browser_event():
    session_id = request.cookies.get("mvs_session")

    if not session_id:
        return jsonify({"ok": False, "error": "session not started"}), 400

    data = request.get_json(silent=True) or {}
    event_type = data.get("type")

    try:
        session = get_session(session_id)

        with session["lock"]:
            ensure_started(session)
            page = session["page"]

            if event_type == "click":
                x = float(data["x"])
                y = float(data["y"])
                page.mouse.click(x, y)

            elif event_type == "wheel":
                page.mouse.wheel(
                    float(data.get("delta_x", 0)),
                    float(data.get("delta_y", 0)),
                )

            elif event_type == "key":
                page.keyboard.press(str(data["key"]))

            else:
                return jsonify({
                    "ok": False,
                    "error": "unknown event",
                }), 400

            session["last_seen"] = time.time()

            response = jsonify({
                "ok": True,
                "url": page.url,
            })
            return set_session_cookie(response, session_id)

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
