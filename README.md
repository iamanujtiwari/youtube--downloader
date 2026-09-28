# 🎬 YouTube Downloader

A simple, clean Streamlit web app for fetching YouTube video details and downloading video, video-only, or audio-only (MP3) files, with selectable quality and a live progress bar.

Built with [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and [`Streamlit`](https://streamlit.io).

---

## 📸 Screenshots

<!-- Add your screenshots below. Save images in a folder like `screenshots/` in your repo root, then update the paths. -->

https://github.com/user-attachments/assets/9f1d2cf7-ec6d-44dc-bd6c-d4ad91d80804

---

## ✨ Features

- 🔍 Fetch video metadata: title, uploader, duration, views, likes, thumbnail
- ⬇️ Three download modes:
  - **Video + Audio** (merged, best available or capped resolution)
  - **Video only** (no audio track)
  - **Audio only** (extracted as MP3, 192 kbps)
- 📺 Quality picker built dynamically from the formats actually available for that video
- 📊 Live download progress bar with speed and time remaining
- 🔁 Automatic retries with fresh stream URLs when YouTube returns HTTP 403
- 🧹 Files are served from memory and deleted from disk right after, so nothing lingers
- 🖥️ Packaged Windows app that closes itself when you close the browser tab
- 🌐 Runs locally on Windows/Mac/Linux and deploys to Streamlit Community Cloud

---

## 📥 Download the Windows App

Don't want to install Python? Download the ready-to-use Windows application.

1. Open the **Releases** page of this repository.
2. Download the latest **YouTubeDownloader.exe** from the **Assets** section.
3. Double-click **YouTubeDownloader.exe** and wait a few seconds.
4. Your default browser opens the app automatically.
5. Paste a YouTube URL, click **Fetch Video**, choose the download type and quality, then click **Download**.
6. When it finishes, click **💾 Save file** and choose where to save it.

> No Python, ffmpeg or Node.js installation is required. Everything is bundled into the executable.

### Closing the Application

Just close the browser tab. The app stops itself a few seconds later. Refreshing the page is safe and does not close it.

### Troubleshooting (Windows app)

| Problem | Solution |
|---|---|
| Nothing happens after opening the EXE | Wait a few seconds; the first launch is slower. |
| Windows SmartScreen warning | Click **More info → Run anyway** if you trust the application. |
| Browser doesn't open | Open the address shown in the console window (a `http://localhost:<port>` link). |
| App still running after closing the tab | Wait about 10 seconds, or end **YouTubeDownloader.exe** in Task Manager. |
| Fetch Video returns nothing | Likely a temporary YouTube rate limit. Wait a few seconds and click **Fetch Video** again. |
| Download fails with HTTP 403 | The app retries automatically. If it still fails, try again later or update yt-dlp (see below). |

---

## 📁 Project Structure

```
your_project/
├── app.py                   # Streamlit UI and app flow
├── downloader.py            # yt-dlp logic: fetch info, resolutions, download, ffmpeg/JS runtime detection
├── utils.py                 # Thumbnail/details rendering + progress hook helper
├── heartbeat.py             # Tab-close watcher (used by the packaged exe)
├── launcher.py              # Entry point for the packaged exe
├── ico1.ico / ico1.png      # App icons
├── requirements.txt         # Python dependencies
├── packages.txt             # System packages for Streamlit Cloud (ffmpeg)
├── YouTubeDownloader.spec   # PyInstaller build config
└── bin/
    ├── ffmpeg.exe           # Bundled ffmpeg (Windows exe build)
    └── node.exe             # Bundled Node.js (JavaScript runtime for YouTube)
```

---

## ⚙️ Requirements (running from source)

- Python 3.9+ (3.10 or 3.11 recommended)
- **ffmpeg**: needed to merge video+audio and extract MP3. Put `ffmpeg` in `./bin` or on your system PATH.
- **A JavaScript runtime (Node.js 22+ or Deno)**: YouTube now requires one for yt-dlp to solve its signature challenges. Without it, downloads often fail with HTTP 403. Put `node.exe` (or `deno.exe`) in `./bin`, or install it system-wide.
- The `yt-dlp-ejs` package, installed automatically by `yt-dlp[default]`.

---

## 🚀 Local Setup (running from source)

1. **Clone the repo**

   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**

   ```bash
   streamlit run app.py
   ```

4. Open the URL Streamlit prints (usually `http://localhost:8501`).

To keep yt-dlp current (recommended, since YouTube changes often):

```bash
pip install -U "yt-dlp[default]"
```
## 🧠 How It Works

- **Metadata fetch** (`get_video_info`) uses yt-dlp's `extract_info(..., download=False)` to pull details without downloading.
- **Quality list** (`get_available_resolutions`) collects the unique video heights (e.g. `[1080, 720, 480, 360]`) for the dropdown.
- **Download** (`download_video`) builds a yt-dlp format string from the chosen mode and resolution cap, retrying up to 3 times on HTTP 403.
- **Tool detection** (`get_ffmpeg_location`, `get_js_runtimes`) prefers binaries bundled in `./bin`, then falls back to the system PATH.
- **Progress** is streamed through yt-dlp's `progress_hooks` into a live Streamlit progress bar (`make_progress_hook`).
- **Serving the file**: the finished file is read into memory, deleted from `downloads/`, then handed to `st.download_button`.
- **Desktop launcher** (`launcher.py`) runs Streamlit in-process, opens the browser, and watches a heartbeat sent by `heartbeat.py`. When the tab closes, the whole process exits.

---

## 🛠️ Troubleshooting (running from source)

| Symptom | Likely Cause | Fix |
|---|---|---|
| Yellow "Missing a JavaScript runtime" warning | No Node.js/Deno found | Put `node.exe` in `./bin`, or install Node.js 22+ or Deno. Restart the app fully. |
| Yellow warning mentions `yt-dlp-ejs` | Package missing | `pip install -U "yt-dlp[default]"` |
| HTTP 403 during download | Missing JS runtime or outdated yt-dlp | Fix the two items above and update yt-dlp |
| Downloaded video has no sound | ffmpeg not found | Install ffmpeg or place it in `./bin` |
| Yellow "ffmpeg not found" warning | Same as above | Same as above |
| `RuntimeError: ffmpeg was not found` | ffmpeg missing | Install ffmpeg for your OS |
| Works locally but fails on Streamlit Cloud | Missing `packages.txt` | Add `packages.txt` containing `ffmpeg` to the repo root |

---

## 📦 Dependencies

```
streamlit
yt-dlp[default]
requests
pillow
```

---

## ⚖️ Disclaimer

This tool is intended for downloading content you own the rights to or have permission to download (e.g. your own uploads, Creative Commons content, or content explicitly allowed for offline use). Respect YouTube's Terms of Service and applicable copyright law in your jurisdiction.

---

## 📄 License

MIT: free to use, modify, and distribute.
