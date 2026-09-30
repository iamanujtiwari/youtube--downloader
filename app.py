import streamlit as st
import shutil
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_PATH = os.path.join(BASE_DIR, "bin", "node.exe")
from downloader import (
    DOWNLOAD_DIR, get_video_info, get_available_resolutions,
    download_video, check_ffmpeg, get_js_support_problem, ffmpeg_has_encoder,
)
from utils import (
    show_thumbnail, show_other_details, make_progress_hook, make_transcode_hook,
)
from heartbeat import inject_close_watcher

# ---------------- Page Config ---------------- #

st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="ico1.ico",
    layout="wide"
)

# Tells the desktop launcher (if running as the packaged .exe) to shut
# the whole app down when this browser tab is closed. No-op otherwise.
inject_close_watcher()

# ---------------- Title ---------------- #

st.image("ico1.png", width=80) 
st.title("YouTube Downloader")
st.write("Paste a YouTube URL to view video details and download it.")

if not check_ffmpeg():
    st.warning(
        "⚠️ ffmpeg was not found (checked ./bin and system PATH). Video+Audio "
        "and Audio-only downloads will fail until it's installed or bundled."
    )

js_problem = get_js_support_problem()
if js_problem:
    st.warning(
        f"⚠️ Missing {js_problem}. YouTube now requires it, and without it "
        "downloads often fail with HTTP 403. Run `pip install -U \"yt-dlp[default]\"` "
        "and install Node.js 22+ (https://nodejs.org) or Deno, or put node.exe in ./bin."
    )

st.divider()

# ---------------- Session State ---------------- #

if "info" not in st.session_state:
    st.session_state.info = None

# ---------------- URL Input ---------------- #

# A form lets the Enter key submit the URL, same as clicking the button.
with st.form("fetch_form", border=False):
    url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=xxxxxxxx"
    )
    fetch_clicked = st.form_submit_button("🔍 Fetch Video", use_container_width=True)

# ---------------- Fetch ---------------- #

if fetch_clicked:

    if not url.strip():
        st.warning("Please enter a YouTube URL.")
        st.stop()

    try:
        with st.spinner("Fetching video information..."):
            st.session_state.info = get_video_info(url)
            st.session_state.url = url

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

    col1, col2, col3 = st.columns(3)

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

    with col3:
        codec = "auto"

        if mode in ("best", "video_only"):
            codec_map = {
                "Auto (fastest, no re-encode)": "auto",
                "MP4 · H.264/AVC + AAC (most compatible)": "h264",
                "MP4 · HEVC/H.265 + AAC (smaller files)": "hevc",
            }
            codec_label = st.selectbox("Format / codec", options=list(codec_map))
            codec = codec_map[codec_label]

            if codec == "h264":
                st.caption(
                    "Uses YouTube's native H.264/AAC when available. "
                    "Higher resolutions (e.g. 4K) are re-encoded."
                )
            elif codec == "hevc":
                st.caption(
                    "YouTube doesn't serve HEVC, so the video is re-encoded "
                    "with ffmpeg. This is slower than a normal download."
                )
                if not ffmpeg_has_encoder("libx265"):
                    st.warning(
                        "⚠️ Your ffmpeg build has no libx265 encoder, so HEVC "
                        "will fail. Use a full/essentials ffmpeg build."
                    )
        else:
            st.write("Format: MP3")

    if st.button("⬇️ Download", use_container_width=True):
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        hook = make_progress_hook(progress_bar, status_text)
        codec_names = {"h264": "Converting to H.264 + AAC", "hevc": "Encoding HEVC + AAC"}
        convert_hook = make_transcode_hook(
            progress_bar, status_text, codec_names.get(codec, "Converting")
        )

        try:
            with st.spinner("Preparing download..."):
                filepath = download_video(
                    st.session_state.get("url", url), mode=mode, resolution=resolution, progress_hook=hook,
                    codec=codec, transcode_hook=convert_hook,
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
                "(needed to merge video+audio or extract MP3 audio). "
                "If it mentions HTTP 403, update yt-dlp and make sure Node.js 22+ (or Deno) is installed."
            )