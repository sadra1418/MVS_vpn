from flask import Flask, jsonify, render_template_string
from config import TARGET_URL, PORT

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MVS_vpn</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            text-align: center;
        }
        h1 { color: #4ade80; margin-bottom: 1rem; }
        .box {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 2rem;
            max-width: 600px;
            width: 100%;
        }
        code {
            background: #222;
            padding: 2px 6px;
            border-radius: 4px;
            color: #fbbf24;
        }
        .warn { color: #f87171; margin-top: 1.5rem; line-height: 1.6; }
        a { color: #60a5fa; }
    </style>
</head>
<body>
    <div class="box">
        <h1>MVS_vpn</h1>
        <p>هدف فعلی: <code>{{ target }}</code></p>
        <p class="warn">
            صفحه سیاه بود چون سایت‌هایی مثل Gemini و DeepSeek اجازه نمی‌دهند داخل iframe باز شوند.<br><br>
            برای دیدن سایت با <b>IP سرور</b> باید یکی از این دو کار را انجام دهی:
        </p>
        <ol style="text-align:right; margin-top:1.5rem; line-height:1.8;">
            <li>روی سرور یک پروکسی واقعی (SOCKS5) راه بیندازی و مرورگر خودت را از آن رد کنی</li>
            <li>از حالت remote browser + noVNC استفاده کنی (می‌توانم برات اضافه کنم)</li>
        </ol>
        <p style="margin-top:1.5rem; font-size:0.9rem; color:#888;">
            وضعیت سرویس: <span style="color:#4ade80">فعال</span>
        </p>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, target=TARGET_URL)

@app.route("/status")
def status():
    return jsonify({
        "status": "running",
        "target_url": TARGET_URL,
        "message": "iframe blocked by target site. Use real proxy or remote browser."
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
