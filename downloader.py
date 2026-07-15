from yt_dlp import YoutubeDL
import os
import shutil
import sys

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Folder where a bundled ffmpeg binary can live, relative to this file.
# Put the executable at:  bin/ffmpeg        (Mac/Linux)
#                         bin/ffmpeg.exe    (Windows)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLED_FFMPEG_DIR = os.path.join(BASE_DIR, "bin")


def get_ffmpeg_location():
    """
    Decide which ffmpeg to use, in order of preference:
      1. A binary bundled inside ./bin in the project folder
      2. Whatever is discoverable on the system PATH
    Returns the folder to pass as ffmpeg_location, or None if nothing found.
    """
    exe_name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
    bundled_path = os.path.join(BUNDLED_FFMPEG_DIR, exe_name)

    if os.path.isfile(bundled_path):
        return BUNDLED_FFMPEG_DIR

    if shutil.which("ffmpeg"):
        return None  # yt-dlp will find it on PATH automatically

    return "MISSING"


def check_ffmpeg():
    """Return True if ffmpeg is available, either bundled or on PATH."""
    return get_ffmpeg_location() != "MISSING"


# Shared options to reduce YouTube 403 Forbidden errors.
# Forces yt-dlp to try the Android client (less restricted) alongside the
# normal web client, sets a standard browser user-agent, and prevents
# accidentally pulling an entire playlist from a single video link.
COMMON_YDL_OPTS = {
    "noplaylist": True,
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "web"],
        }
    },
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/138.0 Safari/537.36"
        )
    },
}


def get_extra_ydl_opts():
    """
    Optional proxy / cookies support, mainly to work around YouTube blocking
    datacenter IPs (e.g. Streamlit Community Cloud) more aggressively than
    residential ones. Configure via Streamlit secrets or environment variables;
    both are entirely optional and ignored if not set.

    Streamlit secrets.toml example:
        YT_PROXY_URL = "http://user:pass@proxy-host:port"
        YT_COOKIES_FILE = "cookies.txt"
    """
    extra = {}

    proxy_url = None
    cookies_file = None

    try:
        import streamlit as st
        proxy_url = st.secrets.get("YT_PROXY_URL", None)
        cookies_file = st.secrets.get("YT_COOKIES_FILE", None)
    except Exception:
        pass  # not running in Streamlit, or no secrets configured

    proxy_url = proxy_url or os.environ.get("YT_PROXY_URL")
    cookies_file = cookies_file or os.environ.get("YT_COOKIES_FILE")

    if proxy_url:
        extra["proxy"] = proxy_url

    if cookies_file and os.path.isfile(cookies_file):
        extra["cookiefile"] = cookies_file

    return extra


def get_video_info(url):
    """Fetch metadata (title, thumbnail, formats, etc.) without downloading."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        **COMMON_YDL_OPTS,
        **get_extra_ydl_opts(),
    }
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def get_available_resolutions(info):
    """Return a sorted (high -> low) list of unique video heights (e.g. [1080, 720, 480])."""
    heights = set()
    for f in info.get("formats", []):
        h = f.get("height")
        if h:
            heights.add(h)
    return sorted(heights, reverse=True)


def download_video(url, mode="best", resolution=None, progress_hook=None):
    """
    Download a YouTube video.

    Parameters:
        url (str): YouTube video URL.
        mode (str): "best" (video+audio), "video_only", or "audio_only".
        resolution (int or None): Max height (e.g. 720, 1080). None = best available.
        progress_hook (callable): Optional function called with yt-dlp progress dicts.

    Returns:
        str: Path to the final downloaded file on disk.
    """

    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    ffmpeg_location = get_ffmpeg_location()
    if mode in ("best", "audio_only") and ffmpeg_location == "MISSING":
        raise RuntimeError(
            "ffmpeg was not found (not bundled in ./bin and not on PATH). "
            "It's required to merge video+audio or extract MP3 audio."
        )

    if mode == "best":
        fmt = (
            f"bv*[height<={resolution}]+ba/b[height<={resolution}]"
            if resolution else "bv*+ba/b"
        )
        ydl_opts = {
            "format": fmt,
            "merge_output_format": "mp4",
            "outtmpl": output_path,
            **COMMON_YDL_OPTS,
            **get_extra_ydl_opts(),
        }

    elif mode == "video_only":
        fmt = f"bv*[height<={resolution}]" if resolution else "bv*"
        ydl_opts = {
            "format": fmt,
            "outtmpl": output_path,
            **COMMON_YDL_OPTS,
            **get_extra_ydl_opts(),
        }

    elif mode == "audio_only":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_path,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            **COMMON_YDL_OPTS,
            **get_extra_ydl_opts(),
        }

    else:
        raise ValueError("mode must be 'best', 'video_only', or 'audio_only'")

    if progress_hook:
        ydl_opts["progress_hooks"] = [progress_hook]

    if ffmpeg_location and ffmpeg_location != "MISSING":
        ydl_opts["ffmpeg_location"] = ffmpeg_location

    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(result)

        # Correct the extension based on post-processing outcome
        if mode == "audio_only":
            filename = os.path.splitext(filename)[0] + ".mp3"
        elif mode == "best":
            filename = os.path.splitext(filename)[0] + ".mp4"

        return filename
