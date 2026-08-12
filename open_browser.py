#!/usr/bin/env python3
"""
مرورگر واقعی روی سرور با IP سرور باز می‌شود.
صفحه را با noVNC می‌بینی و کنترل می‌کنی.
"""
import os
import time
from playwright.sync_api import sync_playwright

TARGET_URL = os.environ.get("TARGET_URL", "https://gemini.google.com")

def main():
    print(f"[MVS_vpn] Starting browser → {TARGET_URL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,          # حتماً headed تا روی Xvfb دیده شود
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--start-maximized",
                "--window-size=1280,800",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        page = context.new_page()

        # تلاش برای باز کردن سایت
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            print(f"[MVS_vpn] Loaded: {TARGET_URL}")
        except Exception as e:
            print(f"[MVS_vpn] goto error (will keep browser open): {e}")

        # مرورگر را زنده نگه می‌داریم
        print("[MVS_vpn] Browser is running. Connect via noVNC on port 6080")
        while True:
            time.sleep(3600)

if __name__ == "__main__":
    main()
