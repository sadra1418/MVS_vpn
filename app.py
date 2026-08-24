import re
from urllib.parse import urljoin, urlparse
from flask import Flask, request, Response, redirect
import httpx
from config import TARGET_URL, PORT

@@ -10,102 +10,309 @@
parsed_target = urlparse(TARGET_URL)
TARGET_ORIGIN = f"{parsed_target.scheme}://{parsed_target.netloc}"
TARGET_HOST = parsed_target.netloc


































# کلاینت HTTP با هدرهای شبیه مرورگر
client = httpx.Client(
    follow_redirects=True,
    timeout=60.0,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",









    },
)































































def rewrite_url(url: str) -> str:
    """تبدیل لینک‌های سایت هدف به لینک‌های پروکسی"""
    if not url or url.startswith("data:") or url.startswith("javascript:") or url.startswith("#"):













        return url
    if url.startswith("//"):
        url = parsed_target.scheme + ":" + url
    full = urljoin(TARGET_ORIGIN + "/", url)
    parsed = urlparse(full)
    if parsed.netloc == TARGET_HOST or not parsed.netloc:
        path = parsed.path or "/"










        if parsed.query:
            path += "?" + parsed.query








        return path


    return full


def rewrite_html(html: str) -> str:
    """بازنویسی لینک‌ها و اسکریپت‌ها در HTML"""
    # href / src / action

    def repl_attr(match):
        attr = match.group(1)
        quote = match.group(2)
        url = match.group(3)
        return f'{attr}={quote}{rewrite_url(url)}{quote}'

    html = re.sub(
        r'(href|src|action)=(["\'])(.*?)\2',
        repl_attr,
        html,
        flags=re.IGNORECASE,
    )

    # url(...) در CSS






















    def repl_css(match):
        url = match.group(1).strip("'\"")
        return f'url({rewrite_url(url)})'

    html = re.sub(r'url\(([^)]+)\)', repl_css, html, flags=re.IGNORECASE)

    # اضافه کردن base برای مسیرهای نسبی
    base_tag = f'<base href="/">'
    if "<head>" in html.lower():
        html = re.sub(r'(<head[^>]*>)', r'\1' + base_tag, html, count=1, flags=re.IGNORECASE)






    else:
        html = base_tag + html

    return html


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")






















def proxy(path):
    # ساخت URL کامل هدف
    if path:
        target = urljoin(TARGET_ORIGIN + "/", path)
    else:
        target = TARGET_URL

    # حفظ query string
    if request.query_string:
        target += "?" + request.query_string.decode()



    # هدرها



    headers = {
        "User-Agent": request.headers.get("User-Agent", client.headers["User-Agent"]),
        "Accept": request.headers.get("Accept", "*/*"),
        "Accept-Language": request.headers.get("Accept-Language", "en-US,en;q=0.9"),
        "Referer": TARGET_ORIGIN + "/",

    }

    # کوکی‌های درخواست (اگر لازم باشد)




    cookies = {k: v for k, v in request.cookies.items()}

    try:
        if request.method == "GET":
            resp = client.get(target, headers=headers, cookies=cookies)
        elif request.method == "POST":
            resp = client.post(
                target,
                headers=headers,
                cookies=cookies,
                content=request.get_data(),
            )












        else:
            resp = client.request(
                request.method,
@@ -115,46 +322,62 @@ def proxy(path):
                content=request.get_data(),
            )
    except Exception as e:
        return f"خطا در پروکسی: {e}", 502

    content_type = resp.headers.get("content-type", "")
    content = resp.content

    # اگر HTML بود، لینک‌ها را بازنویسی کن
    if "text/html" in content_type:
        try:
            text = content.decode(resp.encoding or "utf-8", errors="replace")
            text = rewrite_html(text)
            content = text.encode("utf-8")
        except Exception:
            pass

    # ساخت پاسخ
    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
        "content-security-policy",
        "x-frame-options",










    }
    response_headers = [
        (k, v) for k, v in resp.headers.items()
        if k.lower() not in excluded_headers
    ]




    flask_resp = Response(content, status=resp.status_code, headers=response_headers)

    # ست کردن کوکی‌ها (اگر سایت هدف کوکی بفرستد)
    for cookie in resp.cookies.jar:
        flask_resp.set_cookie(
            cookie.name,
            cookie.value,
            path=cookie.path or "/",



        )

    return flask_resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
