import asyncio
from flask import Flask, jsonify
from playwright.async_api import async_playwright
from config import TARGET_URL, PORT
import threading

app = Flask(__name__)

# وضعیت مرورگر
browser_status = {"opened": False, "url": TARGET_URL, "error": None}
playwright_instance = None
browser = None
page = None

async def open_site_headless():
    global playwright_instance, browser, page, browser_status
    try:
        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        browser_status["opened"] = True
        browser_status["error"] = None
        print(f"[OK] سایت با موفقیت روی سرور باز شد (headless): {TARGET_URL}")
        # نگه داشتن صفحه باز
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        browser_status["opened"] = False
        browser_status["error"] = str(e)
        print(f"[ERROR] {e}")

def start_browser_in_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(open_site_headless())

# شروع مرورگر در پس‌زمینه هنگام استارت اپ
threading.Thread(target=start_browser_in_background, daemon=True).start()

@app.route("/")
def index():
    return jsonify({
        "status": "running",
        "target_url": TARGET_URL,
        "browser_opened": browser_status["opened"],
        "error": browser_status["error"],
        "message": "سایت با Playwright headless روی سرور باز شده است (با IP سرور)"
    })

@app.route("/status")
def status():
    return jsonify(browser_status)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
