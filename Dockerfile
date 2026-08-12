FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# نصب ابزارهای لازم + microsocks (پروکسی سبک و سریع)
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# نصب microsocks (SOCKS5 فوق‌العاده سبک)
RUN git clone --depth 1 https://github.com/rofl0r/microsocks.git /tmp/microsocks \
    && cd /tmp/microsocks \
    && make \
    && cp microsocks /usr/local/bin/ \
    && rm -rf /tmp/microsocks

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# پورت پروکسی + پورت صفحه راهنما
EXPOSE 1080 10000

# همزمان پروکسی و صفحه راهنما را اجرا می‌کند
CMD ["bash", "-c", "microsocks -p 1080 -i 0.0.0.0 & python app.py"]
