# 🎬 YouTube Downloader

A simple, clean Streamlit web app for fetching YouTube video details and downloading video, video-only, or audio-only (MP3) files — with selectable quality and a live progress bar.

Built with [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and [Streamlit](https://streamlit.io/).

---

## 📸 Screenshots

<!-- Add your screenshots below. Save images in a folder like `screenshots/` in your repo root, then update the paths. -->

| Fetch Video | Download Options |
|---|---|
| ![Fetch video screenshot](screenshots/fetch-video.png) | ![Download options screenshot](screenshots/download-options.png) |

<!-- Add more as needed, e.g.: -->
<!-- ![App demo](screenshots/demo.gif) -->

---

## ✨ Features

- 🔍 Fetch video metadata — title, uploader, duration, views, likes, thumbnail
- ⬇️ Three download modes:
  - **Video + Audio** (merged, best available or capped resolution)
  - **Video only** (no audio track)
  - **Audio only** (extracted as MP3, 192 kbps)
- 🎚️ Quality/resolution picker built dynamically from the actual formats available for that video
- 📊 Live download progress bar
- 🧹 Files are served straight from memory and deleted from the server immediately after — nothing lingers on disk
- 🖥️ Works locally on Windows/Mac/Linux and deploys cleanly to Streamlit Community Cloud

---

## 📁 Project Structure

```
your_project/
├── app.py              # Streamlit UI and app flow
├── downloader.py        # yt-dlp logic: fetch info, list resolutions, download
├── utils.py              # Thumbnail/details rendering + progress hook helper
├── requirements.txt      # Python dependencies
├── packages.txt           # System package for Streamlit Cloud (installs ffmpeg)
├── screenshots/             # App screenshots used in this README
│   ├── fetch-video.png
│   └── download-options.png
└── bin/                    # Optional: bundle a portable ffmpeg binary here
    └── ffmpeg.exe              (Windows) or ffmpeg (Mac/Linux)
```

---

## ⚙️ Requirements

- Python 3.9+
- **ffmpeg** — required for merging video+audio streams and extracting MP3 audio. See setup options below.

---

## 🚀 Local Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Make sure ffmpeg is available.** Pick one:

   **Option A — Install system-wide**
   | OS | Command |
   |---|---|
   | Windows | Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, add the `bin` folder to your System PATH |
   | macOS | `brew install ffmpeg` |
   | Linux | `sudo apt install ffmpeg` |

   **Option B — Bundle a portable binary (no system install needed)**

   Place the executable at:
   ```
   bin/ffmpeg.exe    (Windows)
   bin/ffmpeg        (Mac/Linux)
   ```
   The app automatically detects and uses this before falling back to PATH. On Mac/Linux, make it executable:
   ```bash
   chmod +x bin/ffmpeg
   ```

4. **Run the app**

   ```bash
   streamlit run app.py
   ```

5. Open the URL Streamlit prints (usually `http://localhost:8501`) in your browser.

---

## ☁️ Deploying to Streamlit Community Cloud

Streamlit Cloud runs on Linux and can't install system packages via pip, so `packages.txt` handles ffmpeg for you automatically:

1. Push your repo to GitHub, including `packages.txt` (already included in this repo — just contains `ffmpeg`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo.
3. Deploy — Streamlit Cloud reads `packages.txt`, runs `apt-get install ffmpeg` during the build, and your app works with full audio support out of the box.

No code changes needed between local (Windows) and cloud (Linux) — `downloader.py` automatically detects whichever ffmpeg is available (bundled binary, then system PATH).

---

## 🧠 How It Works

- **Metadata fetch** (`get_video_info`) uses yt-dlp's `extract_info(..., download=False)` to pull details without downloading anything.
- **Quality list** (`get_available_resolutions`) inspects all formats returned for the video and extracts the unique set of video heights (e.g. `[1080, 720, 480, 360]`) to populate the dropdown.
- **Download** (`download_video`) builds a yt-dlp format string based on the chosen mode and resolution cap, then runs the download. For merging or audio extraction, it passes `ffmpeg_location` explicitly if a bundled binary was found.
- **Progress** is streamed via yt-dlp's `progress_hooks`, wired to a live Streamlit progress bar through `make_progress_hook`.
- **Serving the file**: once downloaded, the file is read into memory as bytes, immediately deleted from the server's `downloads/` folder, then handed to `st.download_button` so the user can save it — keeping the server disk clean.

---

## 🛠️ Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Downloaded video has no sound | ffmpeg not found | Install it or bundle it in `bin/` (see setup above) |
| App shows a yellow "ffmpeg not found" warning | Same as above | Same as above |
| Works locally but fails after deploying to Streamlit Cloud | Missing `packages.txt` | Make sure `packages.txt` (containing `ffmpeg`) is in your repo root |
| `RuntimeError: ffmpeg was not found` | Neither `bin/ffmpeg[.exe]` nor system PATH has it | Follow Option A or B in Local Setup |

---

## 📦 Dependencies

```
streamlit
yt-dlp
requests
pillow
```

---

## ⚖️ Disclaimer

This tool is intended for downloading content you own the rights to or have permission to download (e.g. your own uploads, Creative Commons content, or content explicitly allowed for offline use). Respect YouTube's Terms of Service and applicable copyright law in your jurisdiction.

---

## 📄 License

MIT — free to use, modify, and distribute.
