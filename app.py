from flask import Flask, render_template_string, redirect
from config import TARGET_URL, PORT

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MVS_vpn</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body, html { height: 100%; background: #0f0f0f; color: #e5e5e5; font-family: system-ui, sans-serif; }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem 1rem;
            text-align: center;
        }
        h1 { color: #4ade80; margin-bottom: 0.5rem; }
        .sub { color: #94a3b8; margin-bottom: 2rem; }
        .btn {
            display: inline-block;
            background: #4ade80;
            color: #000;
            padding: 14px 32px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.1rem;
            margin: 0.5rem;
        }
        .btn:hover { background: #22c55e; }
        .info {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
            text-align: right;
            line-height: 1.8;
        }
        code { background: #222; padding: 2px 6px; border-radius: 4px; color: #fbbf24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>MVS_vpn</h1>
        <p class="sub">سایت روی سرور با IP خارجی باز شده است</p>

        <a class="btn" href="http://{{ host }}:6080/vnc.html" target="_blank">
            باز کردن صفحه سایت (کلیک کن)
        </a>

        <div class="info">
            <p><b>سایت هدف:</b> <code>{{ target }}</code></p>
            <p>بعد از کلیک روی دکمه بالا، صفحه واقعی سایت را می‌بینی و می‌توانی با آن کار کنی (کلیک، تایپ، اسکرول).</p>
            <p>همه درخواست‌ها با <b>IP سرور</b> ارسال می‌شوند.</p>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    # host را از درخواست می‌گیریم تا لینک درست ساخته شود
    from flask import request
    host = request.host.split(":")[0]
    return render_template_string(HTML, target=TARGET_URL, host=host)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
