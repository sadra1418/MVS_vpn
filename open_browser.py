from playwright.sync_api import sync_playwright
from config import TARGET_URL
import time

def main():
    print(f"Opening {TARGET_URL} on server...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,          # باید headed باشد تا در noVNC دیده شود
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--start-maximized",
                "--window-size=1280,720",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="en-US",
        )
        page = context.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        print(f"Site opened successfully: {TARGET_URL}")

        # نگه داشتن مرورگر باز
        while True:
            time.sleep(3600)

if __name__ == "__main__":
    main()
