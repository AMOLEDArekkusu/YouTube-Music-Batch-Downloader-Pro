# 🎵 Collector Pro — YouTube Music Batch Downloader

> A powerful, modern desktop GUI application for downloading YouTube music in high-quality **MP3** or **Hi-Res native formats** (Opus/M4A) with **full embedded metadata** — title, artist, album, year, track number, and album cover art.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-informational?logo=windows)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📋 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [FFmpeg Auto-Setup](#-ffmpeg-auto-setup)
- [Download History & Archive](#-download-history--archive)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎧 **MP3 & Hi-Res Option** | Standard MP3 (128-320 kbps) or switch to **Hi-Res Audio** for native lossless streams (Opus/M4A) |
| 🏷️ **Full Metadata** | Embeds Title, Artist, Album, Year, Track # via ID3v2.3 |
| 🖼️ **Album Art** | Embeds YouTube thumbnail as album cover |
| 📂 **Auto-Sort** | Organises files into `Artist/Song.ext` folder structure |
| 📋 **Batch Download** | Paste multiple URLs or click **Import .txt** to load links |
| 🔄 **Incremental Sync** | Skips already-downloaded tracks via archive file |
| 🍪 **Premium Access** | In-app entry for authentication cookies to access private/premium content |
| 🔧 **FFmpeg Auto-Install** | Downloads & extracts FFmpeg automatically if missing |
| 🌓 **Theme Toggle** | Switch between Light and Dark mode |
| 📊 **Live Statistics** | Real-time monitoring of Total Tracks, Library Size, and Sync Speed |
| ⚙️ **In-App Management** | Dedicated tabs to view **Download History** and manage **Settings** |
| 🛑 **Stop Anytime** | Cancel in-progress downloads instantly |
| 📜 **Process Log** | Live in-app log of every download and status |

---

## 📦 Requirements

### Python Packages

```bash
pip install customtkinter yt-dlp
```

| Package | Purpose |
|---|---|
| `customtkinter` | Modern dark-themed GUI framework |
| `yt-dlp` | YouTube / playlist downloading engine |

### External Dependency

| Tool | Notes |
|---|---|
| **FFmpeg** | Required for MP3 conversion & metadata embedding. Auto-downloaded if missing. |

> **Tip:** FFmpeg is auto-downloaded on first run if it's not found on your system PATH. No manual setup needed.

---

## 🚀 Installation

1. **Clone or download** this repository:

   ```bash
   git clone https://github.com/your-username/yt-music-downloader.git
   cd yt-music-downloader
   ```

2. **Install Python dependencies:**

   ```bash
   pip install customtkinter yt-dlp
   ```

3. **Run the app:**

   ```bash
   python "YT Music to mp3.pyw"
   ```

   > On Windows, you can also **double-click** the `.pyw` file to launch it without a console window.

---

## 🖥️ Usage

1. **Paste YouTube links** into the top text box — one URL per line.
   - Supports: single tracks, playlists, and YouTube Music links.
2. *(Optional)* Click **📄 Import .txt** to load URLs from a text file.
3. **Select Save Destination** in the Configuration panel (defaults to `~/Music/YT Music Downloads/`).
4. **Choose Output Quality**: 320 kbps / 192 kbps / 128 kbps.
5. *(Optional)* Toggle **✔ Hi-Res Audio** to download native streams (Opus/M4A) rather than re-encoding to MP3.
6. Toggle **Auto-sort Artist Folder** and **Incremental Sync** as needed.
7. Click **▶ Start Download** and monitor progress in the Process Log panel.
8. Click **⬛ Stop** at any time to cancel immediately.

---

## ⚙️ Configuration

App configurations and data are saved to `~/.yt_music_downloader/`. You can quickly manage application settings from the built-in **Settings** menu.

| System File | Description |
|---|---|
| `downloader_config.json` | Saves user preferences like save path and audio quality |
| `download_history.json` | Stores the user's download history |
| `download_archive.txt` | yt-dlp archive used for Incremental Sync |

From the **Settings** menu, you can toggle themes, reinstall FFmpeg, clear history, or reset the configuration.

---

## 🔧 FFmpeg Auto-Setup

On first launch, the app checks if **FFmpeg** is available:

```
FFmpeg not found → Prompt shown → User accepts → Auto-download from GitHub
```

- Source: [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) (`ffmpeg-master-latest-win64-gpl.zip`)
- Only `ffmpeg.exe` is extracted and placed **next to the script**.
- Download progress is shown live in the app log (every 10%).
- If auto-download fails, a **manual installation guide** is shown.

> **Manual install:** Download `ffmpeg-master-latest-win64-gpl.zip`, extract `ffmpeg.exe` from the `bin/` folder, and place it in the same directory as `YT Music to mp3.pyw`.

---

## 📜 Download History & Archive

All historical data and tracker files are saved in `~/.yt_music_downloader/`.

Click the **⊞ View History** button on the dashboard or use the sidebar's **Download History** tab to browse all your past downloads right within the app.

---

## 📁 Project Structure

```
YouTube to MP3/
├── YT Music to mp3.pyw     # Main application entry point
├── ffmpeg.exe               # Auto-downloaded FFmpeg binary (Windows)
└── README.md                # This file
```

App data (config, history, archive) is stored separately in:

```
~/.yt_music_downloader/
├── downloader_config.json
├── download_history.json
└── download_archive.txt
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `FFmpeg not found` | Let the app auto-download it, or place `ffmpeg.exe` next to the script |
| `Download fails silently` | Enable cookies for age-restricted or private content |
| `File already exists, skipped` | Disable **Incremental Sync** or delete `download_archive.txt` |
| `No metadata embedded` | Ensure FFmpeg is installed — it handles all post-processing |
| App window does not open | Run via `python "YT Music to mp3.pyw"` in terminal to see errors |

---

## 📄 License

This project is licensed under the **MIT License**.  
Feel free to use, modify, and distribute with attribution.

---

> Built with ❤️ using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).
