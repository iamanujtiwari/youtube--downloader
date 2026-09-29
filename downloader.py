from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import importlib.util
import os
import shutil
import sys
import time

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Folder where bundled helper binaries can live, relative to this file.
# Put the executables at:  bin/ffmpeg, bin/deno        (Mac/Linux)
#                          bin/ffmpeg.exe, bin/deno.exe (Windows)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLED_FFMPEG_DIR = os.path.join(BASE_DIR, "bin")
BUNDLED_BIN_DIR = BUNDLED_FFMPEG_DIR

# YouTube sometimes answers a valid-looking stream URL with HTTP 403. A fresh
# extraction (which produces fresh signed URLs) usually fixes it, so we retry.
MAX_DOWNLOAD_ATTEMPTS = 3


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


def get_js_runtimes():
    """
    Preference order:
      1. deno / node bundled inside ./bin
      2. deno / node / bun found on the system PATH
    Returns a dict in the format yt-dlp's `js_runtimes` option expects,
    or None if no runtime was found.
    """
    ext = ".exe" if sys.platform.startswith("win") else ""

    # 1. Bundled binaries
    for name in ("deno", "node"):
        bundled_path = os.path.join(BUNDLED_BIN_DIR, name + ext)
        if os.path.isfile(bundled_path):
            return {name: {"path": bundled_path}}

    # 2. System PATH
    for name in ("deno", "node", "bun"):
        if shutil.which(name):
            return {name: {}}

    return None

def get_js_support_problem():
    """
    Return a human-readable description of what's missing for reliable
    YouTube downloads, or None if everything needed is present.
    """
    missing = []
    if get_js_runtimes() is None:
        missing.append("a JavaScript runtime (Deno)")
    if importlib.util.find_spec("yt_dlp_ejs") is None:
        missing.append("the yt-dlp-ejs package")

    if not missing:
        return None
    return " and ".join(missing)


def _base_opts():
    """Options shared by every yt-dlp call in this app."""
    opts = {
        "color": "never",          # no ANSI codes like [0;31m in error text
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
    }
    js_runtimes = get_js_runtimes()
    if js_runtimes:
        opts["js_runtimes"] = js_runtimes
    return opts


def get_video_info(url):
    """Fetch metadata (title, thumbnail, formats, etc.) without downloading."""
    ydl_opts = {
        **_base_opts(),
        "quiet": True,
        "skip_download": True,
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
            f"bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]"
            if resolution else "bestvideo+bestaudio/best"
        )
        ydl_opts = {
            "format": fmt,
            "merge_output_format": "mp4",
            "outtmpl": output_path,
        }

    elif mode == "video_only":
        fmt = f"bestvideo[height<={resolution}]" if resolution else "bestvideo"
        ydl_opts = {
            "format": fmt,
            "outtmpl": output_path,
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
        }

    else:
        raise ValueError("mode must be 'best', 'video_only', or 'audio_only'")

    ydl_opts.update(_base_opts())

    if progress_hook:
        ydl_opts["progress_hooks"] = [progress_hook]

    if ffmpeg_location and ffmpeg_location != "MISSING":
        ydl_opts["ffmpeg_location"] = ffmpeg_location

    last_error = None
    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        try:
            # A brand-new YoutubeDL each attempt = a fresh extraction and
            # fresh signed stream URLs, which is what fixes most 403s.
            with YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(result)
            break

        except DownloadError as e:
            if "403" not in str(e):
                raise
            last_error = e
            if attempt < MAX_DOWNLOAD_ATTEMPTS:
                time.sleep(2 * attempt)
    else:
        problem = get_js_support_problem()
        hint = (
            f"Missing: {problem}. Install it and try again."
            if problem else
            "Update yt-dlp (pip install -U \"yt-dlp[default]\") and try again."
        )
        raise RuntimeError(
            f"YouTube rejected the download (HTTP 403) after "
            f"{MAX_DOWNLOAD_ATTEMPTS} attempts. {hint}"
        ) from last_error

    # Correct the extension based on post-processing outcome
    if mode == "audio_only":
        filename = os.path.splitext(filename)[0] + ".mp3"
    elif mode == "best":
        filename = os.path.splitext(filename)[0] + ".mp4"

    return filename
