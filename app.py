import asyncio
import base64
import json
from collections import deque
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from playwright.async_api import async_playwright

playwright = None
browser = None


@asynccontextmanager
async def lifespan(app):
    global playwright, browser

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ],
    )

    yield

    if browser:
        await browser.close()

    if playwright:
        await playwright.stop()


app = FastAPI(lifespan=lifespan)


def valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


HOME_HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MVS VPN</title>
<style>
* { box-sizing: border-box; }
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
    <form id="form">
        <input id="url" type="url" placeholder="https://example.com" required>
        <button type="submit">ارسال</button>
    </form>
</div>

<script>
document.getElementById("form").addEventListener("submit", (event) => {
    event.preventDefault();
    const url = document.getElementById("url").value.trim();

    if (!/^https?:\/\//i.test(url)) {
        alert("URL باید با http:// یا https:// شروع شود.");
        return;
    }

    window.location.href = "/browser?url=" + encodeURIComponent(url);
});
</script>
</body>
</html>
"""


BROWSER_HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MVS VPN Browser</title>
<style>
html, body {
    margin: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #111;
}
#browser {
    width: 100vw;
    height: 100vh;
    display: block;
    background: #111;
    cursor: default;
}
#status {
    position: fixed;
    left: 12px;
    top: 12px;
    z-index: 10;
    padding: 7px 10px;
    border-radius: 8px;
    background: rgba(0,0,0,.65);
    color: white;
    font: 13px Arial, sans-serif;
    direction: ltr;
}
</style>
</head>
<body>
<div id="status">connecting...</div>
<canvas id="browser" tabindex="0"></canvas>

<script>
const canvas = document.getElementById("browser");
const ctx = canvas.getContext("2d", { alpha: false });
const status = document.getElementById("status");
const params = new URLSearchParams(location.search);
const target = params.get("url");

let ws;
let frameWidth = 1280;
let frameHeight = 720;
let latestFrame = null;
let drawing = false;
let pendingMove = null;
let moveScheduled = false;

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener("resize", resizeCanvas);

function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN && ws.bufferedAmount < 32768) {
        ws.send(JSON.stringify(data));
    }
}

function pointerPosition(event) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: (event.clientX - rect.left) * frameWidth / rect.width,
        y: (event.clientY - rect.top) * frameHeight / rect.height
    };
}

function modifiers(event) {
    let result = 0;
    if (event.altKey) result |= 1;
    if (event.ctrlKey) result |= 2;
    if (event.metaKey) result |= 4;
    if (event.shiftKey) result |= 8;
    return result;
}

function scheduleMove(event) {
    pendingMove = event;

    if (moveScheduled) return;
    moveScheduled = true;

    requestAnimationFrame(() => {
        moveScheduled = false;
        if (!pendingMove) return;

        const current = pendingMove;
        pendingMove = null;
        const p = pointerPosition(current);

        send({
            type: "mouse",
            action: "move",
            x: p.x,
            y: p.y,
            buttons: current.buttons,
            modifiers: modifiers(current)
        });
    });
}

function connect() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(
        protocol + "//" + location.host +
        "/ws?url=" + encodeURIComponent(target)
    );
    ws.binaryType = "blob";

    ws.onopen = () => {
        status.textContent = "connected";
        canvas.focus();
    };

    ws.onclose = () => {
        status.textContent = "disconnected";
    };

    ws.onerror = () => {
        status.textContent = "connection error";
    };

    ws.onmessage = (event) => {
        if (typeof event.data === "string") {
            const message = JSON.parse(event.data);

            if (message.type === "size") {
                frameWidth = message.width;
                frameHeight = message.height;
            }

            if (message.type === "error") {
                status.textContent = message.message;
            }
            return;
        }

        latestFrame = event.data;
        if (!drawing) drawLatestFrame();
    };
}

async function drawLatestFrame() {
    drawing = true;

    try {
        while (latestFrame) {
            const frame = latestFrame;
            latestFrame = null;

            const bitmap = await createImageBitmap(frame);
            frameWidth = bitmap.width;
            frameHeight = bitmap.height;

            ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
            bitmap.close();
        }
    } finally {
        drawing = false;
        if (latestFrame) drawLatestFrame();
    }
}

canvas.addEventListener("mousedown", (event) => {
    const p = pointerPosition(event);

    send({
        type: "mouse",
        action: "down",
        x: p.x,
        y: p.y,
        button: event.button,
        buttons: event.buttons,
        modifiers: modifiers(event)
    });

    canvas.focus();
});

canvas.addEventListener("mouseup", (event) => {
    const p = pointerPosition(event);

    send({
        type: "mouse",
        action: "up",
        x: p.x,
        y: p.y,
        button: event.button,
        buttons: event.buttons,
        modifiers: modifiers(event)
    });
});

canvas.addEventListener("mousemove", scheduleMove);

canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const p = pointerPosition(event);

    send({
        type: "wheel",
        x: p.x,
        y: p.y,
        deltaX: event.deltaX,
        deltaY: event.deltaY,
        modifiers: modifiers(event)
    });
}, {passive: false});

canvas.addEventListener("keydown", (event) => {
    event.preventDefault();

    send({
        type: "key",
        action: "down",
        key: event.key,
        code: event.code,
        text: event.key.length === 1 ? event.key : "",
        modifiers: modifiers(event),
        autoRepeat: event.repeat
    });
});

canvas.addEventListener("keyup", (event) => {
    event.preventDefault();

    send({
        type: "key",
        action: "up",
        key: event.key,
        code: event.code,
        text: "",
        modifiers: modifiers(event),
        autoRepeat: false
    });
});

connect();
</script>
</body>
</html>
"""


@app.get("/")
async def index():
    return HTMLResponse(HOME_HTML)


@app.get("/get_url")
async def get_url():
    return HTMLResponse(HOME_HTML)


@app.get("/browser")
async def browser_page():
    return HTMLResponse(BROWSER_HTML)


async def send_mouse(cdp, message):
    action = message.get("action")

    if action == "move":
        params = {
            "type": "mouseMoved",
            "x": float(message.get("x", 0)),
            "y": float(message.get("y", 0)),
            "buttons": int(message.get("buttons", 0)),
            "modifiers": int(message.get("modifiers", 0)),
        }
    else:
        button_map = {0: "left", 1: "middle", 2: "right"}
        params = {
            "type": "mousePressed" if action == "down" else "mouseReleased",
            "x": float(message.get("x", 0)),
            "y": float(message.get("y", 0)),
            "button": button_map.get(message.get("button", 0), "left"),
            "buttons": int(message.get("buttons", 0)),
            "clickCount": 1,
            "modifiers": int(message.get("modifiers", 0)),
        }

    await cdp.send("Input.dispatchMouseEvent", params)


async def send_key(cdp, message):
    action = message.get("action")
    params = {
        "type": "keyDown" if action == "down" else "keyUp",
        "key": message.get("key", ""),
        "code": message.get("code", ""),
        "modifiers": int(message.get("modifiers", 0)),
        "autoRepeat": bool(message.get("autoRepeat", False)),
    }

    text = message.get("text", "")
    if action == "down" and text:
        params["text"] = text

    await cdp.send("Input.dispatchKeyEvent", params)


async def handle_input(cdp, message):
    message_type = message.get("type")

    if message_type == "mouse":
        await send_mouse(cdp, message)

    elif message_type == "wheel":
        await cdp.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseWheel",
                "x": float(message.get("x", 0)),
                "y": float(message.get("y", 0)),
                "deltaX": float(message.get("deltaX", 0)),
                "deltaY": float(message.get("deltaY", 0)),
                "modifiers": int(message.get("modifiers", 0)),
            },
        )

    elif message_type == "key":
        await send_key(cdp, message)


@app.websocket("/ws")
async def websocket_browser(websocket: WebSocket):
    await websocket.accept()

    target = websocket.query_params.get("url", "").strip()

    if not valid_url(target):
        await websocket.send_json({
            "type": "error",
            "message": "Invalid URL"
        })
        await websocket.close(code=1008)
        return

    context = None
    page = None
    cdp = None

    try:
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        page = await context.new_page()
        cdp = await context.new_cdp_session(page)

        latest_frame = None
        frame_lock = asyncio.Lock()
        frame_event = asyncio.Event()

        async def on_frame(params):
            nonlocal latest_frame

            await cdp.send(
                "Page.screencastFrameAck",
                {"sessionId": params["sessionId"]},
            )

            frame = base64.b64decode(params["data"])

            async with frame_lock:
                latest_frame = frame
                frame_event.set()

        cdp.on("Page.screencastFrame", on_frame)

        await cdp.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": 60,
                "maxWidth": 1280,
                "maxHeight": 720,
                "everyNthFrame": 1,
            },
        )

        await page.goto(
            target,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        await websocket.send_json({
            "type": "size",
            "width": 1280,
            "height": 720,
        })

        async def send_latest_frame():
            nonlocal latest_frame

            while True:
                await frame_event.wait()

                async with frame_lock:
                    frame = latest_frame
                    latest_frame = None
                    frame_event.clear()

                if frame is None:
                    continue

                try:
                    await websocket.send_bytes(frame)
                except Exception:
                    return

        frame_task = asyncio.create_task(send_latest_frame())

        try:
            while True:
                raw = await websocket.receive_text()
                message = json.loads(raw)
                await handle_input(cdp, message)
        finally:
            frame_task.cancel()
            try:
                await frame_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        pass

    except Exception as exc:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(exc),
            })
        except Exception:
            pass

    finally:
        if cdp:
            try:
                await cdp.send("Page.stopScreencast")
            except Exception:
                pass

        if context:
            try:
                await context.close()
            except Exception:
                pass
