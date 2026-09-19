# MVS_vpn

پروکسی شخصی بهبودیافته برای باز کردن سایت هدف از طریق IP سرور.

## قابلیت جدید: replay کردن کلیک‌ها

در نسخه جدید، فقط صفحه از طریق httpx گرفته نمی‌شود. روی HTML پروکسی یک listener کلیک تزریق می‌شود و برای هر کلیک این اطلاعات ارسال می‌شود:

- مختصات x/y داخل viewport
- مقدار scrollX/scrollY
- اندازه viewport
- URL همان لحظه
- زمان کلیک

سرور برای هر کاربر یک Chromium headless با Playwright نگه می‌دارد و همان کلیک را روی صفحه واقعی سایت هدف در همان مختصات replay می‌کند.

این مدل عمداً **shadow browser** است: کلیک اصلی همچنان در صفحه کاربر انجام می‌شود و هم‌زمان همان action روی مرورگر واقعی سرور هم اجرا می‌شود. بنابراین رفتار فعلی proxy خراب نمی‌شود و یک مسیر واقعی Playwright هم برای سایت‌های dynamic داریم.

## اجرا با Docker

```bash
docker build -t mvs-vpn .
docker run -p 10000:10000 mvs-vpn
```

بعد:

```
http://IP-سرور:10000/
```

Docker در زمان build، Chromium و dependencyهای لازم Playwright را نصب می‌کند.

## تغییر سایت

در config.py:

```python
TARGET_URL = "https://ourdream.ai/"
```

## معماری

```
Browser user
    |
    | GET page
    v
Flask + httpx  ----->  Target website
    |
    | injected click event: x/y + scroll + URL
    v
/_mvs/click
    |
    v
Playwright Chromium
    |
    | page.mouse.click(x, y)
    v
Target website
```

## محدودیت فعلی

این نسخه state مرورگر کاربر را به طور کامل mirror نمی‌کند. یعنی فعلاً کلیک‌ها replay می‌شوند، اما typing/input و بعضی stateهای کاملاً client-side جداگانه sync نمی‌شوند.

همچنین برای پایداری sessionهای Playwright، Gunicorn با یک worker اجرا می‌شود. اگر بعداً sessionهای زیاد لازم شد، باید session store و browser pool جدا اضافه شود.

مرحله بعدی می‌تواند تبدیل این معماری به **full remote browser** باشد، یعنی به جای shadow browser، خود Chromium سرور منبع اصلی صفحه باشد و تعاملات کاربر مستقیماً روی همان browser انجام شوند.
