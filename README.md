# MVS_vpn

نسخه ساده MVS VPN.

کاربر وارد `/get_url` می‌شود، آدرس سایت را وارد می‌کند و روی «ارسال» می‌زند.

سرور با Playwright یک Chromium واقعی اجرا می‌کند، همان URL را باز می‌کند و محتوای صفحه را برمی‌گرداند.

## اجرا

```bash
docker build -t mvs-vpn .
docker run -p 10000:10000 mvs-vpn
```

بعد:

```
http://localhost:10000/get_url
```
