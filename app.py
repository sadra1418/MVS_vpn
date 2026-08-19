import re
from urllib.parse import urljoin, urlparse, quote, unquote
from flask import Flask, request, Response
import httpx
from config import TARGET_URL, PORT

app = Flask(__name__)

# پارس کردن دامنه هدف
parsed_target = urlparse(TARGET_URL)
TARGET_ORIGIN = f"{parsed_target.scheme}://{parsed_target.netloc}"
TARGET_HOST = parsed_target.netloc
TARGET_SCHEME = parsed_target.scheme

# دامنه‌های مرتبط که باید از طریق پروکسی بروند (برای یوتیوب و سایت‌های مشابه)
# می‌توانید دامنه‌های بیشتر اضافه کنید
RELATED_HOSTS = {
    # YouTube / Google
    "www.youtube.com",
    "youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "googlevideo.com",
    "www.googlevideo.com",
    "yt3.ggpht.com",
    "yt3.googleusercontent.com",
    "i.ytimg.com",
    "i1.ytimg.com",
    "s.ytimg.com",
    "www.gstatic.com",
    "fonts.gstatic.com",
    "fonts.googleapis.com",
    "accounts.google.com",
    "www.google.com",
    "google.com",
    "apis.google.com",
    "play.google.com",
    # DeepSeek / common CDNs
    "chat.deepseek.com",
    "www.deepseek.com",
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
}

# کلاینت HTTP با هدرهای شبیه مرورگر
client = httpx.Client(
    follow_redirects=True,
    timeout=90.0,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    },
)

# اسکریپت تزریقی برای فیک کردن وضعیت آنلاین و جلوگیری از پیام‌های آفلاین
ONLINE_SPOOF_SCRIPT = """
<script>
(function() {
  try {
    Object.defineProperty(Navigator.prototype, 'onLine', {
      get: function() { return true; },
      configurable: true
    });
    Object.defineProperty(navigator, 'onLine', {
      get: function() { return true; },
      configurable: true
    });
  } catch(e) {}

  // جلوگیری از رویداد offline
  window.addEventListener('offline', function(e) {
    e.stopImmediatePropagation();
    e.preventDefault();
  }, true);

  // جلوگیری از نمایش پیام‌های آفلاین رایج
  const observer = new MutationObserver(function(mutations) {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.nodeType === 1) {
          const text = (node.textContent || '').toLowerCase();
          if (text.includes('offline') || text.includes('no internet') ||
              text.includes('not connected') || text.includes('به اینترنت متصل نیستید') ||
              text.includes('اتصال به اینترنت') || text.includes('offline mode')) {
            // مخفی کردن المان‌های مشکوک به پیام آفلاین
            if (node.style) node.style.display = 'none';
            if (node.remove) try { node.remove(); } catch(e) {}
          }
        }
      }
    }
  });
  try {
    observer.observe(document.documentElement, { childList: true, subtree: true });
  } catch(e) {}

  // فیک کردن برخی APIهای تشخیص شبکه
  if (window.NetworkInformation) {
    try {
      Object.defineProperty(navigator, 'connection', {
        get: function() {
          return {
            effectiveType: '4g',
            rtt: 50,
            downlink: 10,
            saveData: false,
            onchange: null
          };
        }
      });
    } catch(e) {}
  }
})();
</script>
"""


def is_related_host(host: str) -> bool:
    if not host:
        return False
    host = host.lower()
    if host == TARGET_HOST.lower():
        return True
    for h in RELATED_HOSTS:
        if host == h or host.endswith('.' + h):
            return True
    return False


def rewrite_url(url: str, base: str = None) -> str:
    """تبدیل لینک‌های سایت هدف و دامنه‌های مرتبط به لینک‌های پروکسی"""
    if not url or url.startswith(('data:', 'javascript:', 'mailto:', 'blob:', '#')):
        return url

    # پروتکل نسبی
    if url.startswith('//'):
        url = TARGET_SCHEME + ':' + url

    try:
        full = urljoin(base or (TARGET_ORIGIN + '/'), url)
        parsed = urlparse(full)
    except Exception:
        return url

    host = parsed.netloc.lower() if parsed.netloc else ''

    # اگر دامنه هدف یا مرتبط بود → از طریق پروکسی
    if is_related_host(host) or not host:
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        if parsed.fragment:
            path += '#' + parsed.fragment

        # اگر دامنه متفاوت از هدف اصلی بود، از مسیر /_ext/ استفاده کن
        if host and host != TARGET_HOST.lower():
            # /_ext/https://host/path
            encoded = quote(full, safe='')
            return f'/_ext/{encoded}'
        return path

    # لینک خارجی غیرمرتبط → دست نزن
    return full


def rewrite_html(html: str) -> str:
    """بازنویسی لینک‌ها در HTML + تزریق اسکریپت آنلاین"""

    # 1. ویژگی‌های رایج
    def repl_attr(match):
        attr = match.group(1)
        quote = match.group(2)
        url = match.group(3)
        return f'{attr}={quote}{rewrite_url(url)}{quote}'

    html = re.sub(
        r'(href|src|action|data-src|data-href|poster|srcset)=(["\'])(.*?)\2',
        repl_attr,
        html,
        flags=re.IGNORECASE,
    )

    # 2. srcset (چند URL)
    def repl_srcset(match):
        quote = match.group(1)
        value = match.group(2)
        parts = []
        for part in value.split(','):
            part = part.strip()
            if not part:
                continue
            tokens = part.split()
            if tokens:
                tokens[0] = rewrite_url(tokens[0])
                parts.append(' '.join(tokens))
        return f'srcset={quote}{", ".join(parts)}{quote}'

    html = re.sub(
        r'srcset=(["\'])(.*?)\1',
        repl_srcset,
        html,
        flags=re.IGNORECASE,
    )

    # 3. url(...) در CSS داخل استایل
    def repl_css(match):
        raw = match.group(1).strip(' \'"')
        return f'url({rewrite_url(raw)})'

    html = re.sub(r'url\(([^)]+)\)', repl_css, html, flags=re.IGNORECASE)

    # 4. تزریق base + اسکریپت آنلاین در ابتدای head
    inject = f'<base href="/">\n{ONLINE_SPOOF_SCRIPT}'
    if re.search(r'<head[^>]*>', html, re.IGNORECASE):
        html = re.sub(
            r'(<head[^>]*>)',
            r'\1' + inject,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html = inject + html

    return html


def rewrite_css(css: str) -> str:
    """بازنویسی url() در فایل‌های CSS"""
    def repl(match):
        raw = match.group(1).strip(' \'"')
        return f'url({rewrite_url(raw)})'
    return re.sub(r'url\(([^)]+)\)', repl, css, flags=re.IGNORECASE)


@app.route('/_ext/<path:encoded_url>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy_external(encoded_url):
    """پروکسی کردن دامنه‌های خارجی مرتبط"""
    try:
        target = unquote(encoded_url)
        # امنیت ساده: فقط http/https
        if not target.startswith(('http://', 'https://')):
            return 'Invalid URL', 400
    except Exception:
        return 'Bad request', 400

    return _do_proxy(target)


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    if path:
        target = urljoin(TARGET_ORIGIN + '/', path)
    else:
        target = TARGET_URL

    if request.query_string:
        target += '?' + request.query_string.decode()

    return _do_proxy(target)


def _do_proxy(target: str):
    """منطق اصلی پروکسی"""
    # هدرهای درخواست
    headers = {
        'User-Agent': request.headers.get('User-Agent', client.headers['User-Agent']),
        'Accept': request.headers.get('Accept', '*/*'),
        'Accept-Language': request.headers.get('Accept-Language', 'en-US,en;q=0.9'),
        'Referer': TARGET_ORIGIN + '/',
        'Origin': TARGET_ORIGIN,
    }

    # انتقال برخی هدرهای مهم
    for h in ('Content-Type', 'Range', 'If-None-Match', 'If-Modified-Since'):
        if h in request.headers:
            headers[h] = request.headers[h]

    cookies = {k: v for k, v in request.cookies.items()}

    try:
        if request.method == 'GET':
            resp = client.get(target, headers=headers, cookies=cookies)
        elif request.method == 'POST':
            resp = client.post(
                target,
                headers=headers,
                cookies=cookies,
                content=request.get_data(),
            )
        elif request.method == 'OPTIONS':
            # پاسخ ساده به preflight
            return Response(
                '',
                status=204,
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, DELETE',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Max-Age': '86400',
                },
            )
        else:
            resp = client.request(
                request.method,
                target,
                headers=headers,
                cookies=cookies,
                content=request.get_data(),
            )
    except Exception as e:
        return f'خطا در پروکسی: {e}', 502

    content_type = resp.headers.get('content-type', '')
    content = resp.content

    # بازنویسی محتوا
    try:
        if 'text/html' in content_type:
            text = content.decode(resp.encoding or 'utf-8', errors='replace')
            text = rewrite_html(text)
            content = text.encode('utf-8')
        elif 'text/css' in content_type:
            text = content.decode(resp.encoding or 'utf-8', errors='replace')
            text = rewrite_css(text)
            content = text.encode('utf-8')
    except Exception:
        pass

    # حذف هدرهای مشکل‌ساز
    excluded = {
        'content-encoding',
        'content-length',
        'transfer-encoding',
        'connection',
        'content-security-policy',
        'content-security-policy-report-only',
        'x-frame-options',
        'x-content-type-options',
        'strict-transport-security',
        'report-to',
        'nel',
        'clear-site-data',
    }
    response_headers = [
        (k, v) for k, v in resp.headers.items()
        if k.lower() not in excluded
    ]

    # اضافه کردن CORS ساده برای منابع
    response_headers.append(('Access-Control-Allow-Origin', '*'))

    flask_resp = Response(content, status=resp.status_code, headers=response_headers)

    # ست کردن کوکی‌ها (بدون domain تا روی دامنه پروکسی کار کنند)
    for cookie in resp.cookies.jar:
        flask_resp.set_cookie(
            cookie.name,
            cookie.value,
            path=cookie.path or '/',
            # domain را عمداً ست نمی‌کنیم
            secure=False,  # چون ممکن است روی http اجرا شود
            httponly=cookie.has_nonstandard_attr('HttpOnly') if hasattr(cookie, 'has_nonstandard_attr') else False,
        )

    return flask_resp


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
