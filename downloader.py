from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import functools
import importlib.util
import os
import shutil
import subprocess
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

# Output codec choices for video downloads.
#   auto : whatever YouTube serves best (original behaviour, no re-encode)
#   h264 : MP4 container, H.264/AVC video + AAC audio
#   hevc : MP4 container, HEVC/H.265 video + AAC audio
CODEC_CHOICES = ("auto", "h264", "hevc")


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


def get_ffmpeg_exe():
    """Full path to the ffmpeg executable (bundled first, then PATH), or None."""
    location = get_ffmpeg_location()
    if location == "MISSING":
        return None
    if location:
        exe_name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
        return os.path.join(location, exe_name)
    return shutil.which("ffmpeg")


@functools.lru_cache(maxsize=None)
def ffmpeg_has_encoder(name):
    """True if this ffmpeg build can encode with `name` (e.g. 'libx265')."""
    exe = get_ffmpeg_exe()
    if not exe:
        return False
    try:
        out = subprocess.run(
            [exe, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except Exception:
        return False
    return any(line.split()[1:2] == [name] for line in out.splitlines())


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


# ---------------- Codec handling (H.264 / HEVC + AAC) ---------------- #

def _source_codecs(result):
    """Return (video_codec, audio_codec) yt-dlp actually downloaded."""
    rd = (result.get("requested_downloads") or [result])[0]
    formats = rd.get("requested_formats") or result.get("requested_formats")

    def pick(key, items):
        for f in items:
            val = f.get(key)
            if val and val != "none":
                return val
        return None

    if formats:
        return pick("vcodec", formats), pick("acodec", formats)
    return pick("vcodec", [rd]), pick("acodec", [rd])


def _finalize_mp4(src, result, mode, codec, hook=None):
    """
    Turn the downloaded file into an MP4 with H.264 or HEVC video and AAC audio.
    Streams that already match are copied (fast, lossless); others are re-encoded.
    """
    ffmpeg = get_ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("ffmpeg was not found. It's required for H.264/HEVC output.")

    v_codec, a_codec = _source_codecs(result)
    with_audio = mode == "best"

    v_prefixes = ("avc1",) if codec == "h264" else ("hev1", "hvc1")
    v_ok = bool(v_codec) and v_codec.startswith(v_prefixes)
    a_ok = bool(a_codec) and a_codec.startswith("mp4a")

    dst = os.path.splitext(src)[0] + ".mp4"

    # Already exactly what was asked for, in an MP4 -> nothing to do.
    if src.lower().endswith(".mp4") and v_ok and (a_ok or not with_audio):
        return src

    if v_ok:
        v_args = ["-c:v", "copy"]
    elif codec == "h264":
        if not ffmpeg_has_encoder("libx264"):
            raise RuntimeError("This ffmpeg build has no libx264 encoder.")
        v_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p"]
    else:
        if not ffmpeg_has_encoder("libx265"):
            raise RuntimeError(
                "This ffmpeg build has no libx265 (HEVC) encoder. "
                "Use a full/essentials ffmpeg build."
            )
        v_args = ["-c:v", "libx265", "-preset", "fast", "-crf", "24", "-pix_fmt", "yuv420p"]

    if codec == "hevc":
        v_args += ["-tag:v", "hvc1"]  # lets Apple devices / QuickTime play it

    if not with_audio:
        a_args = ["-an"]
    elif a_ok:
        a_args = ["-c:a", "copy"]
    else:
        a_args = ["-c:a", "aac", "-b:a", "192k"]

    tmp = os.path.splitext(src)[0] + ".converted.mp4"
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", src, "-map", "0:v:0",
        *(["-map", "0:a:0?"] if with_audio else []),
        *v_args, *a_args,
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        tmp,
    ]

    total = result.get("duration")
    if hook:
        hook(0.0)

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    for line in proc.stdout:
        line = line.strip()
        if hook and total and line.startswith(("out_time_us=", "out_time_ms=")):
            try:
                seconds = int(line.split("=", 1)[1]) / 1_000_000  # both keys are microseconds
                hook(min(seconds / total, 1.0))
            except ValueError:
                pass
    proc.wait()
    err = proc.stderr.read()

    if proc.returncode != 0:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f"ffmpeg conversion failed: {err.strip()[-500:]}")

    if os.path.abspath(src) != os.path.abspath(dst) and os.path.exists(src):
        os.remove(src)
    os.replace(tmp, dst)

    if hook:
        hook(1.0)
    return dst


def download_video(url, mode="best", resolution=None, progress_hook=None,
                   codec="auto", transcode_hook=None):
    """
    Download a YouTube video.

    Parameters:
        url (str): YouTube video URL.
        mode (str): "best" (video+audio), "video_only", or "audio_only".
        resolution (int or None): Max height (e.g. 720, 1080). None = best available.
        progress_hook (callable): Optional function called with yt-dlp progress dicts.
        codec (str): "auto", "h264" (MP4: H.264 + AAC) or "hevc" (MP4: HEVC + AAC).
                     Ignored for audio_only.
        transcode_hook (callable): Optional function called with 0.0-1.0 while
                     ffmpeg converts the file to the chosen codec.

    Returns:
        str: Path to the final downloaded file on disk.
    """

    if codec not in CODEC_CHOICES:
        raise ValueError(f"codec must be one of {CODEC_CHOICES}")

    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    ffmpeg_location = get_ffmpeg_location()
    needs_ffmpeg = mode in ("best", "audio_only") or (mode == "video_only" and codec != "auto")
    if needs_ffmpeg and ffmpeg_location == "MISSING":
        raise RuntimeError(
            "ffmpeg was not found (not bundled in ./bin and not on PATH). "
            "It's required to merge video+audio, convert codecs, or extract MP3 audio."
        )

    h = f"[height<={resolution}]" if resolution else ""

    if mode == "best":
        if codec == "auto":
            fmt = f"bestvideo{h}+bestaudio/best{h}"
            merge_fmt = "mp4"
        elif codec == "h264":
            # Prefer YouTube's native H.264 + AAC streams (no re-encode needed).
            fmt = (
                f"bv*[vcodec^=avc1]{h}+ba[acodec^=mp4a]/"
                f"bv*[vcodec^=avc1]{h}+ba/bv*{h}+ba/b{h}"
            )
            merge_fmt = "mkv"  # neutral container; converted to MP4 afterwards
        else:  # hevc: YouTube doesn't serve it, so take the best source and encode
            fmt = f"bv*{h}+ba/b{h}"
            merge_fmt = "mkv"
        ydl_opts = {
            "format": fmt,
            "merge_output_format": merge_fmt,
            "outtmpl": output_path,
        }

    elif mode == "video_only":
        if codec == "auto":
            fmt = f"bestvideo{h}"
        elif codec == "h264":
            fmt = f"bestvideo[vcodec^=avc1]{h}/bestvideo{h}"
        else:
            fmt = f"bestvideo{h}"
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
        return os.path.splitext(filename)[0] + ".mp3"

    if codec != "auto":
        rd = (result.get("requested_downloads") or [{}])[0]
        src = rd.get("filepath") or filename
        return _finalize_mp4(src, result, mode, codec, transcode_hook)

    if mode == "best":
        filename = os.path.splitext(filename)[0] + ".mp4"

    return filename
