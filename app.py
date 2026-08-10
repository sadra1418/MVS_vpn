from flask import Flask, render_template_string, redirect
from config import TARGET_URL, PORT

app = Flask(__name__)

# صفحه کاملاً خالی که فقط سایت هدف را نشان می‌دهد
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 100%; height: 100%; overflow: hidden; }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
    </style>
</head>
<body>
    <iframe src="{{ url }}" allow="fullscreen" allowfullscreen></iframe>
</body>
</html>
"""

@app.route("/")
def index():
    # اگر سایت iframe را بلاک کند، مستقیم ریدایرکت می‌شود
    return render_template_string(HTML, url=TARGET_URL)

@app.route("/go")
def go():
    return redirect(TARGET_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
