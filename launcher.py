"""
Entry point for the packaged .exe.

- Runs the Streamlit server *in-process* (not as a subprocess) so this
  works cleanly once frozen with PyInstaller — spawning a subprocess of
  a frozen exe re-triggers the exe itself, which is a classic PyInstaller
  + Streamlit trap. Calling streamlit's own CLI function avoids that.
- Opens the default browser to the app once the server is up.
- Runs a tiny local heartbeat HTTP server. The page (see heartbeat.py)
  pings it every 2s and sends an instant "closing" beacon on unload.
  If pings stop (tab closed, browser killed) or a closing beacon isn't
  followed by a fresh ping (real close vs. just a page refresh), the
  whole process exits — which takes the Streamlit server down with it.
"""

import os
import sys
import time
import socket
import threading
import webbrowser
import http.server
import socketserver


def resource_path(rel_path):
    """Resolve a path both in dev and inside a PyInstaller onefile bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


HEARTBEAT_TIMEOUT = 6   # seconds of silence = assume the tab is gone
CLOSING_GRACE = 3       # wait this long after a "closing" beacon before exiting
                         # (covers a plain page refresh, which re-pings fast)
STARTUP_GRACE = 45      # seconds to wait for the very first ping

_lock = threading.Lock()
_last_heartbeat = None
_closing_since = None


class _Handler(http.server.BaseHTTPRequestHandler):
    def _ok(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_POST(self):
        global _last_heartbeat, _closing_since
        now = time.time()
        if self.path == "/heartbeat":
            with _lock:
                _last_heartbeat = now
                _closing_since = None  # fresh ping cancels any pending close
            self._ok()
        elif self.path == "/closing":
            with _lock:
                _closing_since = now
            self._ok()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass  # keep stdout clean


def _run_heartbeat_server(port):
    with socketserver.TCPServer(("127.0.0.1", port), _Handler) as httpd:
        httpd.serve_forever()


def _watchdog():
    start = time.time()
    while True:
        with _lock:
            if _last_heartbeat is not None:
                break
        if time.time() - start > STARTUP_GRACE:
            return  # app never loaded in a browser; don't force-kill it
        time.sleep(1)

    while True:
        time.sleep(1)
        with _lock:
            last, closing = _last_heartbeat, _closing_since
        now = time.time()
        if closing is not None and now - closing > CLOSING_GRACE:
            os._exit(0)
        if last is not None and now - last > HEARTBEAT_TIMEOUT:
            os._exit(0)


def main():
    streamlit_port = find_free_port()
    heartbeat_port = find_free_port()
    os.environ["APP_HEARTBEAT_PORT"] = str(heartbeat_port)

    threading.Thread(target=_run_heartbeat_server, args=(heartbeat_port,), daemon=True).start()
    threading.Thread(target=_watchdog, daemon=True).start()

    def _open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{streamlit_port}")

    threading.Thread(target=_open_browser, daemon=True).start()

    sys.argv = [
        "streamlit", "run", resource_path("app.py"),
        "--server.port", str(streamlit_port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
    ]

    from streamlit.web import cli as stcli
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
