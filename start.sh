#!/bin/bash
set -e

echo "[1/4] Starting virtual display..."
Xvfb :99 -screen 0 1280x720x24 &
sleep 1

echo "[2/4] Starting window manager..."
fluxbox &
sleep 1

echo "[3/4] Starting VNC + noVNC..."
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw &
sleep 1
websockify --web=/usr/share/novnc 6080 localhost:5900 &
sleep 1

echo "[4/4] Opening target site with Playwright..."
python open_browser.py &

echo "Starting web UI on port 10000..."
python app.py
