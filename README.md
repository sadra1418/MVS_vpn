# MVS_vpn

مرورگر واقعی روی سرور با **IP سرور**  
تو از طریق مرورگر خودت (noVNC) آن را می‌بینی و کنترل می‌کنی.

## اجرا

```bash
docker build -t mvs-vpn .

docker run -d \
  --name mvs-vpn \
  --ipc=host \
  --shm-size=2g \
  -p 6080:6080 \
  -e TARGET_URL=https://gemini.google.com \
  mvs-vpn
```

سپس برو به:

```
http://IP-سرور:6080
```

روی **Connect** کلیک کن. مرورگر سرور را می‌بینی.

## تغییر سایت

```bash
docker run -d --name mvs-vpn --ipc=host --shm-size=2g -p 6080:6080 \
  -e TARGET_URL=https://chat.deepseek.com \
  mvs-vpn
```

یا فایل `config.py` را تغییر بده و دوباره build کن.

## نکات سرعت

- اولین بار کمی طول می‌کشد (دانلود image + نصب)
- بعد از بالا آمدن، سرعت تعامل خوب است (VNC مستقیم)
- `--ipc=host` و `--shm-size=2g` حتماً بگذار تا کروم کرش نکند

## توقف

```bash
docker stop mvs-vpn && docker rm mvs-vpn
```
