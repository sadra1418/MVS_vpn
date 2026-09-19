# MVS_vpn

پروکسی به شکل **Remote Browser**.

در این نسخه، صفحه‌ای که کاربر می‌بیند دیگر HTML سایت هدف نیست. سرور یک Chromium واقعی با Playwright اجرا می‌کند، سایت هدف را داخل همان مرورگر باز می‌کند و تصویر آن مرورگر را برای کاربر نمایش می‌دهد.

## معماری

```
Browser user
    |
    | screenshot + mouse/keyboard events
    v
Flask
    |
    v
Playwright Chromium
    |
    v
Target website
```

در نتیجه JavaScript، fetch/XHR، cookie، localStorage و state سمت مرورگر داخل Chromium واقعی سرور اجرا می‌شوند. این با نسخه قبلی که HTML را با httpx می‌گرفت و فقط کلیک‌ها را replay می‌کرد تفاوت اساسی دارد.

## اجرا با Docker

```bash
docker build -t mvs-vpn .
docker run -p 10000:10000 mvs-vpn
```

## تغییر سایت هدف

در `config.py`:

```python
TARGET_URL = "https://www.youtube.com/"
```

## نکته مهم

این یک **prototype remote browser** است، نه یک proxy HTTP عمومی.

کاربر تصویر Chromium را می‌بیند و eventهای اصلی را به Chromium می‌فرستد. بنابراین برای سایت‌های JavaScript-heavy از مدل قبلی مناسب‌تر است.

در این نسخه هنوز audio/video واقعی از Chromium به مرورگر کاربر stream نمی‌شود. تصویر با screenshotهای متوالی نمایش داده می‌شود. بنابراین برای YouTube، خود صفحه و تعاملات باید بهتر از proxy قبلی کار کنند، اما پخش ویدیو و صدا هنوز محدودیت دارد.

همچنین برای هر session یک Chromium context ساخته می‌شود، پس تعداد sessionهای هم‌زمان روی یک instance محدود است.
