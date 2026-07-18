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


def get_video_info(url):
    """Fetch metadata (title, thumbnail, formats, etc.) without downloading."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True
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
