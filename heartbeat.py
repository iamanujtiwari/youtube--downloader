import os
import streamlit.components.v1 as components


def inject_close_watcher():
    """
    Injects invisible JS that pings the local launcher process every 2s
    ("I'm still open") and sends an instant "closing" beacon on tab
    close/reload, so the desktop launcher can shut the whole app down
    the moment the browser tab goes away.

    No-ops if APP_HEARTBEAT_PORT isn't set — e.g. when you run the app
    the normal way with `streamlit run app.py` during development.
    """
    port = os.environ.get("APP_HEARTBEAT_PORT")
    if not port:
        return

    components.html(
        f"""
        <script>
        const BASE = "http://127.0.0.1:{port}";

        function ping() {{
            fetch(BASE + "/heartbeat", {{ method: "POST", mode: "cors" }}).catch(() => {{}});
        }}

        ping();
        setInterval(ping, 2000);

        window.addEventListener("beforeunload", function () {{
            navigator.sendBeacon(BASE + "/closing");
        }});
        </script>
        """,
        height=0,
        width=0,
    )
