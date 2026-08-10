"""
این اسکریپت مرورگر واقعی را روی سرور باز می‌کند (با IP سرور).
برای استفاده واقعی از IP سرور این را اجرا کن.
"""
import asyncio
from playwright.async_api import async_playwright
from config import TARGET_URL

async def main():
    async with async_playwright() as p:
        # headless=False یعنی مرورگر واقعی باز می‌شود
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(TARGET_URL)
        print(f"باز شد: {TARGET_URL}")
        print("برای بستن، Ctrl+C بزن")
        # نگه داشتن مرورگر باز
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
