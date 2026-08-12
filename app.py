from flask import Flask, render_template_string
from config import PORT
import socket

app = Flask(__name__)

def get_server_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "IP-سرور"

HTML = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MVS_vpn - پروکسی شخصی</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: #0b0f19;
            color: #e2e8f0;
            min-height: 100vh;
            padding: 2rem 1rem;
            line-height: 1.7;
        }
        .container {
            max-width: 680px;
            margin: 0 auto;
        }
        h1 {
            color: #4ade80;
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }
        .subtitle { color: #94a3b8; margin-bottom: 2rem; }
        .card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.25rem;
        }
        .card h2 {
            color: #60a5fa;
            font-size: 1.1rem;
            margin-bottom: 0.75rem;
        }
        code, .ip {
            background: #1e293b;
            color: #fbbf24;
            padding: 3px 8px;
            border-radius: 6px;
            font-family: ui-monospace, monospace;
            font-size: 0.95rem;
        }
        .step {
            background: #0f172a;
            border-right: 3px solid #4ade80;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
            border-radius: 0 8px 8px 0;
        }
        .ok { color: #4ade80; }
        .warn { color: #fbbf24; }
        ul { padding-right: 1.2rem; }
        li { margin: 0.4rem 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>MVS_vpn</h1>
        <p class="subtitle">پروکسی شخصی با IP سرور — سریع و پایدار</p>

        <div class="card">
            <h2>اطلاعات پروکسی</h2>
            <p>نوع: <code>SOCKS5</code></p>
            <p>آدرس: <span class="ip">{{ ip }}</span></p>
            <p>پورت: <code>1080</code></p>
            <p style="margin-top:0.8rem;color:#94a3b8;font-size:0.9rem;">
                هیچ نام کاربری و رمزی نیاز نیست.
            </p>
        </div>

        <div class="card">
            <h2>چطور استفاده کنی؟</h2>
            
            <p style="margin-bottom:0.8rem;"><b>روش ۱ — مرورگر (ساده‌ترین)</b></p>
            <div class="step">
                ۱. افزونه <b>SwitchyOmega</b> یا <b>FoxyProxy</b> را نصب کن
            </div>
            <div class="step">
                ۲. یک پروفایل SOCKS5 بساز با آدرس <code>{{ ip }}</code> و پورت <code>1080</code>
            </div>
            <div class="step">
                ۳. آن را فعال کن → حالا همه سایت‌ها با IP سرور باز می‌شوند
            </div>

            <p style="margin:1.2rem 0 0.8rem;"><b>روش ۲ — کل سیستم (Windows / macOS / Linux)</b></p>
            <div class="step">
                تنظیمات سیستم → Network → Proxy → SOCKS5 → <code>{{ ip }}:1080</code>
            </div>
        </div>

        <div class="card">
            <h2>نکته مهم</h2>
            <ul>
                <li class="ok">این روش برای Gemini، DeepSeek، ChatGPT و همه سایت‌ها کار می‌کند</li>
                <li class="ok">سرعت بالا و مصرف منابع خیلی کم</li>
                <li class="warn">اگر سرورت IP ایران باشد، ممکن است بعضی سایت‌ها هنوز محدود باشند</li>
            </ul>
        </div>

        <p style="text-align:center;color:#64748b;font-size:0.85rem;margin-top:2rem;">
            سرویس فعال است • پورت پروکسی: 1080
        </p>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, ip=get_server_ip())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
