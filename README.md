# MVS_vpn

باز کردن **هر سایتی** روی سرور با Playwright (headless=True) و IP سرور.

## تغییر سایت

فایل `config.py` را ویرایش کن:

```python
TARGET_URL = "https://gemini.google.com"
```

## اجرا با Docker

```bash
docker build -t mvs-vpn .
docker run -p 10000:10000 mvs-vpn
```

وقتی کانتینر بالا آمد، Playwright به صورت headless سایت را روی سرور باز می‌کند (با IP سرور).

برای چک کردن وضعیت برو به:

```
http://IP-سرور:10000
```

یا

```
http://IP-سرور:10000/status
```

## نکته مهم

چون headless است، صفحه را نمی‌بینی، ولی سایت واقعاً روی سرور باز شده و با IP سرور کار می‌کند.

اگر بعداً بخوای صفحه را ببینی و کنترل کنی، باید noVNC یا حالت headed اضافه کنیم.
