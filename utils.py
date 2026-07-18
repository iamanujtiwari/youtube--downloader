import streamlit as st
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime


def show_thumbnail(url):
    if not url:
        st.warning("Thumbnail not available.")
        return

    response = requests.get(url)

    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        st.image(image, use_container_width=True)
    else:
        st.error("Unable to load thumbnail.")


from datetime import timedelta

def show_other_details(info):

    st.subheader("📄 Video Details")

    duration = info.get("duration")

    if duration:
        duration = str(timedelta(seconds=duration))
    else:
        duration = "N/A"

    st.write(f"**🎬 Title:** {info.get('title', 'N/A')}")
    st.write(f"**📺 Uploader:** {info.get('uploader', 'N/A')}")
    st.write(f"**⏱ Duration:** {duration}")

    views = info.get("view_count")
    likes = info.get("like_count")

    st.write(f"**👀 Views:** {views:,}" if isinstance(views, int) else "**👀 Views:** N/A")
    st.write(f"**👍 Likes:** {likes:,}" if isinstance(likes, int) else "**👍 Likes:** N/A")

def make_progress_hook(progress_bar, status_text):
    """
    Build a yt-dlp progress_hook function wired to Streamlit widgets,
    so download progress is reflected live in the UI.
    """

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed")
            remaining = d.get("eta")

            if total:
                percent = downloaded / total
                progress_bar.progress(min(percent, 1.0))

                speed_text = (
                    f"{speed / 1024 / 1024:.2f} MB/s"
                    if speed
                    else "--"
                )

                remaining_text = (
                    f"{remaining // 60}:{remaining % 60:02d}"
                    if remaining is not None
                    else "--:--"
                )

                status_text.write(
                    f"📥 Downloading... {percent * 100:.1f}% | "
                    f"{downloaded / 1e6:.1f} MB / {total / 1e6:.1f} MB | "
                    f"🚀 {speed_text} | "
                    f"⏳ Remaining: {remaining_text}"
                )
            else:
                status_text.write("📥 Downloading...")

        elif d["status"] == "finished":
            progress_bar.progress(1.0)
            status_text.write("✅ Download finished. Processing file...")

        elif d["status"] == "error":
            status_text.error("❌ Download failed.")

    return hook