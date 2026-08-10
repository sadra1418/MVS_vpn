# MVS_vpn

پروکسی شخصی: هر سایتی که در `config.py` بگذاری، با **IP سرور** در مسیر اصلی (`/`) باز می‌شود.

## تغییر سایت

فایل `config.py`:

```python
TARGET_URL = "https://chat.deepseek.com/"
# یا
# TARGET_URL = "https://gemini.google.com"
```

## اجرا با Docker

```bash
docker build -t mvs-vpn .
docker run -p 10000:10000 mvs-vpn
```

بعد برو به:

```
http://IP-سرور:10000/
```

سایت هدف مستقیماً در همان صفحه باز می‌شود و درخواست‌ها از IP سرور می‌روند.

## نکته

- این یک **reverse proxy** است.
- برای سایت‌های ساده خوب کار می‌کند.
- سایت‌های خیلی پیچیده (مثل Gemini با لاگین گوگل و WebSocket) ممکن است کامل کار نکنند.
- اگر نیاز به کنترل کامل مرورگر داشتی، بعداً می‌توانیم noVNC اضافه کنیم.
