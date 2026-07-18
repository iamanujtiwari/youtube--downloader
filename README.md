



# 🎬 YouTube Downloader

A simple, clean Streamlit web app for fetching YouTube video details and downloading video, video-only, or audio-only (MP3) files — with selectable quality and a live progress bar.

Built with [`yt-dlp`] and [`Streamlit`]
---

## 📸 Screenshots

<!-- Add your screenshots below. Save images in a folder like `screenshots/` in your repo root, then update the paths. -->

|                                                                          Fetch Video 
|                                                     ![Fetch video screenshot]https://github.com/user-attachments/assets/7bb27c68-f726-438a-8543-d15c5937c8bd  


---

## ✨ Features

- 🔍 Fetch video metadata — title, uploader, duration, views, likes, thumbnail
- ⬇️ Three download modes:
  - **Video + Audio** (merged, best available or capped resolution)
  - **Video only** (no audio track)
  - **Audio only** (extracted as MP3, 192 kbps)
- 📺 Quality/resolution picker built dynamically from the actual formats available for that video
- 📊 Live download progress bar
- 🧹 Files are served straight from memory and deleted from the server immediately after — nothing lingers on disk
- 🖥️ Works locally on Windows/Mac/Linux and deploys cleanly to Streamlit Community Cloud

---

# 📥 Download the Windows App

Don't want to install Python? Download the ready-to-use Windows application.

1. Open the **Releases** page on this repository.
2. Download the latest **YouTubeDownloader.exe** from the **Assets** section.
3. Double-click **YouTubeDownloader.exe**.
4. Wait a few seconds while the application starts.
5. Your default web browser will open automatically.
6. Paste a YouTube URL, click **Fetch Video**, choose the download type and quality, then click **Download**.

> No Python installation or ffmpeg setup is required. Everything is bundled into a single executable.

### 📸 Download Steps

| GitHub Release | Release Assets |
|---|---|

---

# 🖥️ Using the Windows App (`YouTubeDownloader.exe`)

Once you've downloaded the application:

1. Double-click **YouTubeDownloader.exe**.
2. A console window may briefly appear while the application starts.
3. Your browser will automatically open the app.
4. Paste the YouTube URL.
5. Click **Fetch Video**.
6. Select:
   - Download Type
   - Video Quality
7. Click **Download**.
8. After the download finishes, click **💾 Save File** and choose where to save it.

### Closing the Application

Simply close the browser tab.

The application will automatically stop running in the background after a few seconds.

Refreshing the page is safe and will not close the application.

---

### Troubleshooting

| Problem | Solution |
|---|---|
| Nothing happens after opening the EXE | Wait a few seconds during the first launch. |
| Windows SmartScreen warning | Click **More Info → Run Anyway** if you trust the application. |
| Browser doesn't open | Open the address shown in the console window (usually `http://localhost:8501`). |
| App is still running after closing | Wait about 10 seconds or close **YouTubeDownloader.exe** from Task Manager. |
| Fetch Video doesn't return results | Temporary YouTube IP rate limit or request block  Wait a few seconds and click **Fetch Video** again. It usually works on the next attempt. |

---

## 📁 Project Structure

```
your_project/
├── app.py              # Streamlit UI and app flow
├── downloader.py        # yt-dlp logic: fetch info, list resolutions, download
├── utils.py              # Thumbnail/details rendering + progress hook helper
├── requirements.txt      # Python dependencies
├── packages.txt           # System package for Streamlit Cloud (installs ffmpeg)
└── screenshots/             # App screenshots used in this README
    ├── fetch-video.png
    └── download-options.png
```

---

## ⚙️ Requirements

- Python 3.9+ (only needed if running from source — not needed to use the `.exe`)
- **ffmpeg** — required for merging video+audio streams and extracting MP3 audio when running from source. Already bundled into the `.exe`, so no setup needed there.

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

4. Open the URL Streamlit prints (usually `http://localhost:8501`) in your browser.


## 🧠 How It Works

- **Metadata fetch** (`get_video_info`) uses yt-dlp's `extract_info(..., download=False)` to pull details without downloading anything.
- **Quality list** (`get_available_resolutions`) inspects all formats returned for the video and extracts the unique set of video heights (e.g. `[1080, 720, 480, 360]`) to populate the dropdown.
- **Download** (`download_video`) builds a yt-dlp format string based on the chosen mode and resolution cap, then runs the download.
- **Progress** is streamed via yt-dlp's `progress_hooks`, wired to a live Streamlit progress bar through `make_progress_hook`.
- **Serving the file**: once downloaded, the file is read into memory as bytes, immediately deleted from the server's `downloads/` folder, then handed to `st.download_button` so the user can save it — keeping the server disk clean.

---

## 🛠️ Troubleshooting (running from source)

| Symptom | Likely Cause | Fix |
|---|---|---|
| Downloaded video has no sound | ffmpeg not found | Install ffmpeg and make sure it's on your system PATH |
| App shows a yellow "ffmpeg not found" warning | Same as above | Same as above |
| Works locally but fails after deploying to Streamlit Cloud | Missing `packages.txt` | Make sure `packages.txt` (containing `ffmpeg`) is in your repo root |
| `RuntimeError: ffmpeg was not found` | ffmpeg not on system PATH | Install ffmpeg for your OS |

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
