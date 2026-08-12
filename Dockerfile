FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV SCREEN_WIDTH=1280
ENV SCREEN_HEIGHT=800
ENV SCREEN_DEPTH=24
ENV TARGET_URL=https://gemini.google.com
ENV HOME=/home/pwuser

USER root

# ابزارهای لازم برای نمایش مجازی + VNC + noVNC
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    supervisor \
    curl \
    ca-certificates \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# لینک راحت به صفحه اصلی noVNC
RUN ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py open_browser.py start.sh ./
RUN chmod +x start.sh

# سوپروایزر برای مدیریت چند پروسه
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 6080

# توصیه: موقع اجرا --ipc=host و --shm-size=2g بده
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
