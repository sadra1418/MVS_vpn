#!/bin/bash
set -e

export DISPLAY=:99
export TARGET_URL=${TARGET_URL:-https://gemini.google.com}

echo "[MVS_vpn] Starting services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
