import streamlit as st
import shutil
import os
from downloader import DOWNLOAD_DIR, get_video_info, get_available_resolutions, download_video, check_ffmpeg
from utils import show_thumbnail, show_other_details, make_progress_hook
from heartbeat import inject_close_watcher

# ---------------- Page Config ---------------- #

st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="🎬",
    layout="wide"
)

# Tells the desktop launcher (if running as the packaged .exe) to shut
# the whole app down when this browser tab is closed. No-op otherwise.
inject_close_watcher()

# ---------------- Title ---------------- #

st.title("🎬 YouTube Downloader")
st.write("Paste a YouTube URL to view video details and download it.")

if not check_ffmpeg():
    st.warning(
        "⚠️ ffmpeg was not found (checked ./bin and system PATH). Video+Audio "
        "and Audio-only downloads will fail until it's installed or bundled."
    )

st.divider()

# ---------------- Session State ---------------- #

if "info" not in st.session_state:
    st.session_state.info = None

# ---------------- URL Input ---------------- #

url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=xxxxxxxx"
)

# ---------------- Fetch Button ---------------- #

if st.button("🔍 Fetch Video", use_container_width=True):

    if not url.strip():
        st.warning("Please enter a YouTube URL.")
        st.stop()

    try:
        with st.spinner("Fetching video information..."):
            st.session_state.info = get_video_info(url)

    except Exception as e:
        st.error(f"Error fetching video: {e}")
        st.session_state.info = None

# ---------------- Show Details + Download Options ---------------- #

if st.session_state.info:
    info = st.session_state.info

    left, right = st.columns([1, 2], gap="large")

    with left:
        show_thumbnail(info.get("thumbnail"))

    with right:
        show_other_details(info)

    st.divider()
    st.subheader("⬇️ Download Options")

    col1, col2 = st.columns(2)

    with col1:
        mode_label = st.selectbox(
            "Download type",
            options=["Video + Audio (best)", "Video only", "Audio only (MP3)"]
        )
        mode_map = {
            "Video + Audio (best)": "best",
            "Video only": "video_only",
            "Audio only (MP3)": "audio_only",
        }
        mode = mode_map[mode_label]

    with col2:
        resolution = None

        if mode in ("best", "video_only"):
            resolutions = get_available_resolutions(info)
            if resolutions:
                res_options = ["Best available"] + [f"{h}p" for h in resolutions]
                res_choice = st.selectbox("Quality", options=res_options)
                if res_choice != "Best available":
                    resolution = int(res_choice.replace("p", ""))
            else:
                st.write("Quality: Best available")
        else:
            st.write("Quality: Best available (audio, 192 kbps MP3)")

    if st.button("⬇️ Download", use_container_width=True):
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        hook = make_progress_hook(progress_bar, status_text)

        try:
            with st.spinner("Preparing download..."):
                filepath = download_video(
                    url, mode=mode, resolution=resolution, progress_hook=hook
                )

            st.success("✅ Download complete!")

            # Read the file into memory, then remove it from the server's disk right
            # away — st.download_button only needs the bytes, not the file itself.
            with open(filepath, "rb") as f:
                file_bytes = f.read()

            try:
               if os.path.exists(DOWNLOAD_DIR):
                   shutil.rmtree(DOWNLOAD_DIR)  

            except Exception:
                pass # file already gone or in use; not critical

            st.download_button(
                label="💾 Save file",
                data=file_bytes,
                file_name=os.path.basename(filepath),
                use_container_width=True,
            )

        except Exception as e:
            st.error(f"Error downloading video: {e}")
            st.info(
                "If this mentions ffmpeg, make sure it's installed and on your PATH "
                "(needed to merge video+audio or extract MP3 audio)."
            )