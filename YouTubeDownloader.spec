import sys

# Fix PyInstaller recursion error
sys.setrecursionlimit(sys.getrecursionlimit() * 5)

from PyInstaller.utils.hooks import collect_all


# ============================================================
# COLLECT STREAMLIT
# ============================================================

streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all(
    "streamlit"
)


# ============================================================
# COLLECT YT-DLP
# ============================================================

ytdlp_datas, ytdlp_binaries, ytdlp_hiddenimports = collect_all(
    "yt_dlp"
)


# ============================================================
# COLLECT YT-DLP-EJS
# ============================================================

try:
    ejs_datas, ejs_binaries, ejs_hiddenimports = collect_all(
        "yt_dlp_ejs"
    )
except Exception:
    ejs_datas = []
    ejs_binaries = []
    ejs_hiddenimports = []


# ============================================================
# HIDDEN IMPORTS
# ============================================================

hiddenimports = (
    streamlit_hiddenimports
    + ytdlp_hiddenimports
    + ejs_hiddenimports
    + [
        "requests",
        "PIL",

        # Streamlit
        "streamlit.runtime",
        "streamlit.runtime.scriptrunner",
        "streamlit.runtime.scriptrunner.magic_funcs",
        "streamlit.runtime.scriptrunner.script_run_context",

        # yt-dlp
        "yt_dlp",
        "yt_dlp.extractor",
        "yt_dlp.downloader",

        # yt-dlp JavaScript support
        "yt_dlp_ejs",
    ]
)


# ============================================================
# DATA FILES
# ============================================================

datas = (
    streamlit_datas
    + ytdlp_datas
    + ejs_datas
    + [
        # Application icons
        ("ico1.ico", "."),
        ("ico1.png", "."),

        # JavaScript runtime + FFmpeg
        ("bin/node.exe", "bin"),
        ("bin/ffmpeg.exe", "bin"),
    ]
)


# ============================================================
# BINARIES
# ============================================================

binaries = (
    streamlit_binaries
    + ytdlp_binaries
    + ejs_binaries
)


# ============================================================
# ANALYSIS
# ============================================================

a = Analysis(
    ["launcher.py"],

    pathex=[],

    binaries=binaries,

    datas=datas,

    hiddenimports=hiddenimports,

    hookspath=[],

    hooksconfig={},

    runtime_hooks=[],

    excludes=[],

    noarchive=False,
)


# ============================================================
# PYZ
# ============================================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
)


# ============================================================
# EXE
# ============================================================

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],

    name="YouTubeDownloader",

    debug=False,

    bootloader_ignore_signals=False,

    strip=False,

    upx=True,

    console=True,

    icon="ico1.ico",
)