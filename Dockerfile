FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

WORKDIR /app

# نصب وابستگی‌های سیستم برای مرورگر + نمایش مجازی + noVNC
RUN apt-get update && apt-get install -y \
    curl wget git ca-certificates \
    xvfb x11vnc fluxbox \
    novnc websockify \
    fonts-liberation libnss3 libatk-bridge2.0-0 libgtk-3-0 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libasound2 libpangocairo-1.0-0 libcups2 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نصب مرورگر Playwright
RUN playwright install chromium
RUN playwright install-deps chromium || true

COPY . .
RUN chmod +x start.sh

# پورت‌ها: 10000 = صفحه وب ، 6080 = noVNC
EXPOSE 10000 6080

CMD ["bash", "start.sh"]
