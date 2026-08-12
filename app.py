from flask import Flask, request, render_template_string, jsonify
from playwright.sync_api import sync_playwright
import os
import time

app = Flask(__name__)

# تنظیم از config.py (هر سایتی که می‌خوای)
TARGET_URL = os.getenv("TARGET_URL", "https://gemini.google.com")
app.config['TARGET_URL'] = TARGET_URL

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Browser</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body, html { margin:0; padding:0; height:100vh; overflow:hidden; background:#000; }
        iframe { width:100vw; height:100vh; border:none; display:block; }
    </style>
</head>
<body>
    <iframe id="browser" src="{TARGET_URL}" frameborder="0"></iframe>
    <script>
        const iframe = document.getElementById('browser');
        iframe.onload = () => console.log('سایت کامل بارگذاری شد با IP سرور');
        // هر حرکتی که بخوای ادامه پیدا می‌کنه (مثلاً کلیک یا تایپ)
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, TARGET_URL=TARGET_URL)

@app.route("/status")
def status():
    return jsonify({"browser_opened": True, "target_url": TARGET_URL, "status": "running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
