"""
MVS_vpn - Reverse Proxy ساده و بهبودیافته
سایت مشخص‌شده در config.py را از طریق IP سرور سرو می‌کند.
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import re
import urllib.parse
from urllib.parse import urljoin, urlparse
from config import TARGET_URL, PORT

app = FastAPI(title="MVS_vpn")

# دامنهٔ اصلی هدف
PARSED_TARGET = urlparse(TARGET_URL)
TARGET_ORIGIN = f"{PARSED_TARGET.scheme}://{PARSED_TARGET.netloc}"
TARGET_HOST = PARSED_TARGET.netloc

# دامنه‌هایی که باید از طریق /_ext/ پروکسی شوند (CDNها، گوگل، یوتیوب و ...)
EXTRA_DOMAINS = [
    "youtube.com", "youtu.be", "ytimg.com", "googlevideo.com",
    "google.com", "googleapis.com", "gstatic.com", "googleusercontent.com",
    "ggpht.com", "yt3.ggpht.com", "youtube-nocookie.com",
    "doubleclick.net", "googlesyndication.com",
    "facebook.com", "fbcdn.net", "cdninstagram.com",
    "twitter.com", "twimg.com", "x.com",
    "cloudflare.com", "cloudfront.net", "akamaihd.net",
    "jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com",
]

# هدرهایی که نباید به کلاینت برگردند
STRIP_RESPONSE_HEADERS = {
    "content-security-policy",
    "content-security-policy-report-only",
    "x-frame-options",
    "x-content-type-options",
    "strict-transport-security",
    "cross-origin-opener-policy",
    "cross-origin-embedder-policy",
    "cross-origin-resource-policy",
    "permissions-policy",
    "report-to",
    "nel",
    "transfer-encoding",  # httpx خودش مدیریت می‌کند
}

# اسکریپت تزریقی برای فیک کردن navigator.onLine
ONLINE_FIX_SCRIPT = """
<script>
(function(){
    try {
        Object.defineProperty(Navigator.prototype, 'onLine', {
            get: function(){ return true; },
            configurable: true
        });
        window.addEventListener('offline', function(e){
            e.stopImmediatePropagation();
            e.preventDefault();
        }, true);
        // جلوگیری از تشخیص پروکسی در بعضی سایت‌ها
        if (window.chrome) {
            Object.defineProperty(window, 'chrome', {value: window.chrome, writable: false});
        }
    } catch(e){}
})();
</script>
"""


def is_extra_domain(host: str) -> bool:
    if not host:
        return False
    host = host.lower()
    for d in EXTRA_DOMAINS:
        if host == d or host.endswith("." + d):
            return True
    return False


def rewrite_url(url: str, base: str = TARGET_URL) -> str:
    """لینک را به مسیر پروکسی تبدیل می‌کند."""
    if not url or url.startswith(("data:", "blob:", "javascript:", "mailto:", "#")):
        return url

    # absolute URL
    if url.startswith(("http://", "https://")):
        parsed = urlparse(url)
        if parsed.netloc == TARGET_HOST or parsed.netloc.endswith("." + TARGET_HOST.split(":")[0]):
            # همان دامنهٔ هدف → مسیر نسبی از طریق پروکسی
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            return path
        elif is_extra_domain(parsed.netloc):
            # دامنهٔ خارجی مرتبط → /_ext/
            return "/_ext/" + url
        else:
            # دامنهٔ کاملاً خارجی → دست نزن
            return url

    # protocol-relative
    if url.startswith("//"):
        full = "https:" + url
        parsed = urlparse(full)
        if parsed.netloc == TARGET_HOST or is_extra_domain(parsed.netloc):
            return rewrite_url(full, base)
        return url

    # relative
    return url  # مرورگر خودش نسبت به / resolve می‌کند


def rewrite_html(html: str) -> str:
    """بازنویسی href, src, srcset, action, data-src و url() در CSS."""

    def repl_attr(match):
        attr = match.group(1)
        quote = match.group(2)
        value = match.group(3)
        new_value = rewrite_url(value)
        return f'{attr}={quote}{new_value}{quote}'

    # href, src, action, data-src, poster, ...
    html = re.sub(
        r'\b(href|src|action|data-src|data-lazy-src|poster|formaction)=(["\'])([^"\']*)\2',
        repl_attr,
        html,
        flags=re.IGNORECASE,
    )

    # srcset
    def repl_srcset(match):
        quote = match.group(1)
        srcset = match.group(2)
        parts = []
        for part in srcset.split(","):
            part = part.strip()
            if not part:
                continue
            tokens = part.split()
            if tokens:
                tokens[0] = rewrite_url(tokens[0])
            parts.append(" ".join(tokens))
        return f'srcset={quote}{", ".join(parts)}{quote}'

    html = re.sub(
        r'\bsrcset=(["\'])([^"\']*)\1',
        repl_srcset,
        html,
        flags=re.IGNORECASE,
    )

    # url() در style و CSS inline
    def repl_css_url(match):
        quote = match.group(1) or ""
        url = match.group(2)
        return f"url({quote}{rewrite_url(url)}{quote})"

    html = re.sub(
        r'url\(\s*(["\']?)([^"\')]+)\1\s*\)',
        repl_css_url,
        html,
        flags=re.IGNORECASE,
    )

    # تزریق اسکریپت فیک آنلاین قبل از </head> یا </body>
    if re.search(r"</head\s*>", html, re.IGNORECASE):
        html = re.sub(r"</head\s*>", ONLINE_FIX_SCRIPT + "</head>", html, count=1, flags=re.IGNORECASE)
    elif re.search(r"</body\s*>", html, re.IGNORECASE):
        html = re.sub(r"</body\s*>", ONLINE_FIX_SCRIPT + "</body>", html, count=1, flags=re.IGNORECASE)
    else:
        html += ONLINE_FIX_SCRIPT

    return html


def rewrite_css(css: str) -> str:
    def repl(match):
        quote = match.group(1) or ""
        url = match.group(2)
        return f"url({quote}{rewrite_url(url)}{quote})"
    return re.sub(r'url\(\s*(["\']?)([^"\')]+)\1\s*\)', repl, css, flags=re.IGNORECASE)


async def proxy_request(request: Request, target_url: str) -> Response:
    """درخواست را به target_url فوروارد می‌کند و پاسخ را بازنویسی می‌کند."""
    method = request.method
    headers = dict(request.headers)
    # حذف هدرهای هاست و پروکسی
    for h in ("host", "content-length", "transfer-encoding", "connection"):
        headers.pop(h, None)
    headers["host"] = urlparse(target_url).netloc
    # جلوگیری از فشرده‌سازی پیچیده
    headers["accept-encoding"] = "identity"

    body = await request.body()

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0, verify=False) as client:
        try:
            upstream = await client.request(
                method,
                target_url,
                headers=headers,
                content=body if body else None,
            )
        except Exception as e:
            return Response(
                content=f"<h1>Proxy Error</h1><p>{e}</p><p>Target: {target_url}</p>",
                status_code=502,
                media_type="text/html",
            )

    content_type = upstream.headers.get("content-type", "")
    content = upstream.content

    # بازنویسی HTML
    if "text/html" in content_type:
        try:
            text = content.decode(upstream.encoding or "utf-8", errors="replace")
            text = rewrite_html(text)
            content = text.encode("utf-8")
        except Exception:
            pass
    # بازنویسی CSS
    elif "text/css" in content_type:
        try:
            text = content.decode(upstream.encoding or "utf-8", errors="replace")
            text = rewrite_css(text)
            content = text.encode("utf-8")
        except Exception:
            pass

    # ساخت پاسخ
    resp_headers = {}
    for k, v in upstream.headers.items():
        if k.lower() not in STRIP_RESPONSE_HEADERS:
            resp_headers[k] = v

    # پشتیبانی از Range
    if "accept-ranges" not in {h.lower() for h in resp_headers}:
        resp_headers["Accept-Ranges"] = "bytes"

    return Response(
        content=content,
        status_code=upstream.status_code,
        headers=resp_headers,
        media_type=content_type.split(";")[0].strip() if content_type else None,
    )


@app.api_route("/_ext/{full_url:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_external(full_url: str, request: Request):
    """پروکسی منابع خارجی (CDNها و دامنه‌های مرتبط)."""
    # full_url ممکن است شامل https:// باشد
    if not full_url.startswith(("http://", "https://")):
        # ممکن است از مسیر آمده باشد
        full_url = "https://" + full_url.lstrip("/")
    return await proxy_request(request, full_url)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_main(path: str, request: Request):
    """پروکسی اصلی سایت هدف."""
    # ساخت URL کامل
    if path:
        target = urljoin(TARGET_URL, path)
    else:
        target = TARGET_URL

    # اضافه کردن query string
    if request.url.query:
        sep = "&" if "?" in target else "?"
        target = target + sep + request.url.query

    return await proxy_request(request, target)


@app.get("/health")
async def health():
    return {"status": "ok", "target": TARGET_URL}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
