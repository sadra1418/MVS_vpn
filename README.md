# MVS_vpn

پروکسی شخصی سبک و سریع با **SOCKS5**

همه سایت‌ها (Gemini، DeepSeek، ChatGPT و ...) با IP سرور باز می‌شوند.

## اجرا

```bash
docker build -t mvs-vpn .
docker run -p 1080:1080 -p 10000:10000 mvs-vpn
```

## اطلاعات پروکسی

| مورد | مقدار |
|------|--------|
| نوع | SOCKS5 |
| آدرس | IP سرور |
| پورت | `1080` |
| یوزرنیم / پسورد | ندارد |

## چطور استفاده کنی؟

### روش سریع (مرورگر)
1. افزونه **Proxy SwitchyOmega** یا **FoxyProxy** را نصب کن
2. یک پروفایل SOCKS5 بساز:
   - Protocol: `SOCKS5`
   - Server: `IP-سرور`
   - Port: `1080`
3. پروفایل را فعال کن

### روش سیستم‌عامل
- **Windows**: Settings → Network & Internet → Proxy → Manual → SOCKS
- **macOS**: System Settings → Network → Details → Proxies → SOCKS Proxy
- **Linux**: تنظیمات شبکه یا `export ALL_PROXY=socks5://IP:1080`

## صفحه راهنما

بعد از اجرا برو به:
```
http://IP-سرور:10000
```

اطلاعات کامل و راهنما آنجا نمایش داده می‌شود.
