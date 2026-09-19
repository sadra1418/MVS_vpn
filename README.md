# MVS_vpn

MVS VPN now uses a real remote Chromium desktop instead of returning a snapshot of HTML.

## Architecture

`Browser -> noVNC/WebSocket -> Flask -> x11vnc -> Xvfb -> Chromium -> target website`

The target website stays alive inside Chromium. JavaScript, navigation, clicks, scrolling, forms and other browser interactions happen in the real browser process.

## Run

```bash
docker build -t mvs-vpn .
docker run -p 10000:10000 mvs-vpn
```

Open:

http://localhost:10000/get_url

After submitting a URL, the server opens it in Chromium and redirects to the live noVNC browser.

## Important

This is a VNC-based live browser, not an HTML proxy. noVNC uses WebSockets to communicate with the VNC server, while x11vnc shares the X display containing Chromium. This keeps the page dynamic instead of repeatedly generating screenshots.

For a public deployment, add authentication/session isolation before allowing multiple users.
