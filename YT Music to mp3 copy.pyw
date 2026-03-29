import customtkinter as ctk
import yt_dlp
import threading
import os
import json
import datetime
import subprocess
import sys
import ctypes
import urllib.request
import zipfile
import shutil
import tempfile
from tkinter import filedialog, messagebox

# Hide the console/terminal window on Windows as soon as the script starts
if os.name == 'nt':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Global Configuration: Use AppData folder for config/history (no permission issues)
APP_DATA_FOLDER = os.path.join(os.path.expanduser("~"), ".yt_music_downloader")
os.makedirs(APP_DATA_FOLDER, exist_ok=True)  # Auto-create folder if it doesn't exist

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
CONFIG_FILE = os.path.join(APP_DATA_FOLDER, "downloader_config.json")
HISTORY_FILE = os.path.join(APP_DATA_FOLDER, "download_history.json")
ARCHIVE_FILE = os.path.join(APP_DATA_FOLDER, "download_archive.txt")

class YTMusicDownloaderPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Music Batch Downloader Pro (Full Metadata)")
        self.geometry("800x680")
        self.resizable(False, False)

        # Initialize configuration
        self.save_path = os.path.join(os.path.expanduser("~"), "Music", "YT Music Downloads")
        os.makedirs(self.save_path, exist_ok=True)  # Auto-create default save folder

        # Create StringVars BEFORE calling load_config()
        self.format_var = ctk.StringVar(value="MP3") # Force MP3 for best metadata support
        self.quality_var = ctk.StringVar(value="Highest Quality (320kbps)")
        self.load_config()

        self.downloading = False
        self.ffmpeg_available = False

        # Title
        self.title_label = ctk.CTkLabel(self, text="YouTube Music Batch Downloader Pro", font=("Arial", 22, "bold"))
        self.title_label.pack(pady=15)

        # ========== Link Input Area ==========
        self.link_frame = ctk.CTkFrame(self)
        self.link_frame.pack(pady=5, padx=20, fill="x")

        self.url_label = ctk.CTkLabel(self.link_frame, text="Playlist/Single Track Links (one per line):", font=("Arial", 12))
        self.url_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.import_btn = ctk.CTkButton(self.link_frame, text="Import TXT Links", width=120, command=self.import_txt)
        self.import_btn.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        self.url_text = ctk.CTkTextbox(self.link_frame, width=740, height=80)
        self.url_text.grid(row=1, column=0, columnspan=2, padx=10, pady=5)

        # ========== Save Settings Area ==========
        self.setting_frame = ctk.CTkFrame(self)
        self.setting_frame.pack(pady=5, padx=20, fill="x")

        # Save path selection
        self.path_label = ctk.CTkLabel(self.setting_frame, text=f"Save Path: {self.save_path}", font=("Arial", 12))
        self.path_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.path_btn = ctk.CTkButton(self.setting_frame, text="Select Save Path", width=120, command=self.select_path)
        self.path_btn.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # Audio format selection (Locked to MP3 for Metadata)
        self.format_label = ctk.CTkLabel(self.setting_frame, text="Output Audio Format:", font=("Arial", 12))
        self.format_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.format_menu = ctk.CTkOptionMenu(
            self.setting_frame,
            values=["MP3 (Recommended for Full Metadata)"], # Only MP3 for full metadata
            variable=self.format_var,
            width=250,
            state="disabled" # Disable selection since we need MP3
        )
        self.format_menu.grid(row=1, column=1, padx=10, pady=5, sticky="e")

        # Audio quality selection
        self.quality_label = ctk.CTkLabel(self.setting_frame, text="Audio Quality:", font=("Arial", 12))
        self.quality_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.quality_menu = ctk.CTkOptionMenu(
            self.setting_frame,
            values=["Highest Quality (320kbps)", "High Quality (192kbps)", "Standard Quality (128kbps)"],
            variable=self.quality_var,
            width=180
        )
        self.quality_menu.grid(row=2, column=1, padx=10, pady=5, sticky="e")

        # Feature toggles
        self.classify_var = ctk.BooleanVar(value=True)
        self.classify_check = ctk.CTkCheckBox(self.setting_frame, text="Auto-sort into artist folders", variable=self.classify_var)
        self.classify_check.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.increment_var = ctk.BooleanVar(value=True)
        self.increment_check = ctk.CTkCheckBox(self.setting_frame, text="Incremental Sync (Skip downloaded files)", variable=self.increment_var)
        self.increment_check.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        # ========== Operation Area ==========
        self.operate_frame = ctk.CTkFrame(self)
        self.operate_frame.pack(pady=5, padx=20, fill="x")

        self.download_btn = ctk.CTkButton(self.operate_frame, text="Start Download", width=150, height=35, command=self.start_download, font=("Arial", 12, "bold"))
        self.download_btn.grid(row=0, column=0, padx=10, pady=10)

        self.stop_btn = ctk.CTkButton(self.operate_frame, text="Stop Download", width=150, height=35, command=self.stop_download, fg_color="#d9534f", hover_color="#c9302c")
        self.stop_btn.grid(row=0, column=1, padx=10, pady=10)
        self.stop_btn.configure(state="disabled")

        self.history_btn = ctk.CTkButton(self.operate_frame, text="View Download History", width=150, height=35, command=self.show_history)
        self.history_btn.grid(row=0, column=2, padx=10, pady=10)

        # ========== FFmpeg Status Indicator ==========
        self.ffmpeg_frame = ctk.CTkFrame(self)
        self.ffmpeg_frame.pack(pady=5, padx=20, fill="x")
        self.ffmpeg_status_label = ctk.CTkLabel(self.ffmpeg_frame, text="FFmpeg Status: Checking...", font=("Arial", 12))
        self.ffmpeg_status_label.pack(pady=10)

        # ========== Cookie Setting Area ==========
        self.cookie_frame = ctk.CTkFrame(self)
        self.cookie_frame.pack(pady=5, padx=20, fill="x")
        self.cookie_label = ctk.CTkLabel(self.cookie_frame, text="Cookie for private playlists/premium content (optional):", font=("Arial", 12))
        self.cookie_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.cookie_entry = ctk.CTkEntry(self.cookie_frame, width=580)
        self.cookie_entry.grid(row=0, column=1, padx=10, pady=5)

        # ========== Log Area ==========
        self.log_label = ctk.CTkLabel(self, text="Download Log:", font=("Arial", 12))
        self.log_label.pack(pady=5, padx=20, anchor="w")
        self.log_text = ctk.CTkTextbox(self, width=760, height=180)
        self.log_text.pack(pady=5, padx=20)

        # Check FFmpeg AFTER all UI widgets are created
        self.check_ffmpeg_on_startup()
        self.update_ffmpeg_status_ui()

    # ------------------------------ FFmpeg Management Functions ------------------------------
    def is_ffmpeg_installed(self):
        """Check if FFmpeg is available in system PATH or current directory"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except FileNotFoundError:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            local_ffmpeg = os.path.join(script_dir, "ffmpeg.exe")
            if os.path.exists(local_ffmpeg):
                os.environ["PATH"] = script_dir + os.pathsep + os.environ["PATH"]
                return True
            return False

    def install_ffmpeg_windows(self):
        """Download and extract FFmpeg directly from GitHub releases (BtbN builds).
        Runs in a background thread — call via _install_ffmpeg_threaded() instead.
        Returns True on success, False on failure.
        """
        FFMPEG_URL = (
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
            "latest/ffmpeg-master-latest-win64-gpl.zip"
        )
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dest_ffmpeg = os.path.join(script_dir, "ffmpeg.exe")
        tmp_path = None  # FIX: initialise before try so except can safely reference it
        try:
            self.after(0, lambda: self.log("Downloading FFmpeg from GitHub..."))
            self.after(0, lambda: self.log(f"  → {FFMPEG_URL}"))

            # Download to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp_path = tmp.name

            # FIX: track last logged percentage so we only log every 10 %
            last_logged = [-1]
            def _reporthook(block_num, block_size, total_size):
                if total_size > 0:
                    pct = min(100, int(block_num * block_size * 100 / total_size))
                    milestone = (pct // 10) * 10
                    if milestone > last_logged[0]:
                        last_logged[0] = milestone
                        self.after(0, lambda p=milestone: self.log(f"  Downloading FFmpeg... {p}%"))

            urllib.request.urlretrieve(FFMPEG_URL, tmp_path, _reporthook)
            self.after(0, lambda: self.log("Download complete. Extracting ffmpeg.exe..."))

            # Extract only ffmpeg.exe from the zip
            with zipfile.ZipFile(tmp_path, 'r') as zf:
                ffmpeg_entry = None
                for name in zf.namelist():
                    # Entry lives at: ffmpeg-.../bin/ffmpeg.exe
                    if name.endswith("/bin/ffmpeg.exe") or name.endswith("/ffmpeg.exe"):
                        ffmpeg_entry = name
                        break
                if ffmpeg_entry is None:
                    self.after(0, lambda: self.log("❌ Could not locate ffmpeg.exe inside the archive."))
                    return False
                with zf.open(ffmpeg_entry) as src, open(dest_ffmpeg, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

            os.remove(tmp_path)  # Clean up the zip

            # Add script folder to PATH so ffmpeg.exe is found immediately
            os.environ["PATH"] = script_dir + os.pathsep + os.environ.get("PATH", "")
            self.after(0, lambda: self.log(f"✅ FFmpeg extracted to: {dest_ffmpeg}"))
            return True

        except Exception as e:
            self.after(0, lambda err=str(e): self.log(f"❌ FFmpeg download/extract error: {err}"))
            # Clean up partial download
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    def _install_ffmpeg_threaded(self):
        """Run install_ffmpeg_windows in a background thread, then update UI on completion."""
        def _worker():
            success = self.install_ffmpeg_windows()
            if success:
                self.ffmpeg_available = True
                self.after(0, self.update_ffmpeg_status_ui)
                self.after(0, lambda: messagebox.showinfo(
                    "FFmpeg Ready",
                    "FFmpeg has been downloaded and extracted successfully!\n"
                    "You can start downloading now."
                ))
            else:
                self.after(0, self.show_manual_install_guide)
        threading.Thread(target=_worker, daemon=True).start()

    def check_ffmpeg_on_startup(self):
        self.ffmpeg_available = self.is_ffmpeg_installed()
        if not self.ffmpeg_available:
            response = messagebox.askyesno(
                "FFmpeg Required",
                "FFmpeg is required to convert music and embed metadata.\n\n"
                "FFmpeg was not found on this PC.\n"
                "Do you want to download & extract it automatically?\n\n"
                "(ffmpeg.exe will be placed next to this script)"
            )
            if response:
                # FIX: run download in background thread so UI stays responsive
                self._install_ffmpeg_threaded()
            else:
                self.show_manual_install_guide()

    def show_manual_install_guide(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        guide = (
            "Manual FFmpeg Installation:\n\n"
            "1. Download FFmpeg (zip):\n"
            "   https://github.com/BtbN/FFmpeg-Builds/releases/latest\n"
            "   (choose: ffmpeg-master-latest-win64-gpl.zip)\n\n"
            "2. Open the zip and go into the 'bin' folder\n\n"
            "3. Copy 'ffmpeg.exe' to the same folder as this script:\n"
            f"   {script_dir}\n\n"
            "4. Restart this application"
        )
        messagebox.showwarning("FFmpeg Installation Required", guide)
        self.ffmpeg_available = False

    def update_ffmpeg_status_ui(self):
        self.ffmpeg_available = self.is_ffmpeg_installed()
        if self.ffmpeg_available:
            self.ffmpeg_status_label.configure(text="✅ FFmpeg Status: Installed & Ready", text_color="#5cb85c")
        else:
            self.ffmpeg_status_label.configure(text="❌ FFmpeg Status: Not Installed", text_color="#d9534f")
            self.download_btn.configure(state="disabled")

    # ------------------------------ End FFmpeg Management ------------------------------

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.save_path = config.get("save_path", self.save_path)
                    self.quality_var.set(config.get("audio_quality", "Highest Quality (320kbps)"))
            except Exception as e:
                pass

    def save_config(self):
        try:
            config_data = {
                "save_path": self.save_path,
                "output_format": "MP3",
                "audio_quality": self.quality_var.get()
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def log(self, msg):
        self.log_text.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see("end")

    def select_path(self):
        path = filedialog.askdirectory(initialdir=self.save_path)
        if path:
            self.save_path = path
            self.path_label.configure(text=f"Save Path: {path}")
            self.save_config()

    def import_txt(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    links = f.read().strip()
                    self.url_text.delete("1.0", "end")
                    self.url_text.insert("1.0", links)
                self.log(f"Successfully imported links from TXT file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import TXT: {str(e)}")

    def progress_hook(self, d):
        if not self.downloading:
            # Raise DownloadCancelled so yt-dlp stops ALL queued items immediately
            # (a generic Exception would be swallowed by ignoreerrors=True)
            raise yt_dlp.utils.DownloadCancelled("Stopped by user")
        if d['status'] == 'downloading':
            filename = d.get('filename', '')
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            self.log(f"Downloading: {os.path.basename(filename)} | {percent} | {speed}")
        elif d['status'] == 'finished':
            filename = d.get('filename', '')
            self.log(f"✅ Processing metadata for: {os.path.basename(filename)}")
            self.add_history(filename)  # Record to download history

    def add_history(self, file_path):
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception as e:
                pass
        history.append({
            "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "file_path": file_path,
            "save_path": self.save_path,
            "format": "MP3"
        })
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def show_history(self):
        history_win = ctk.CTkToplevel(self)
        history_win.title("Download History")
        history_win.geometry("600x400")
        history_win.grab_set()
        history_text = ctk.CTkTextbox(history_win, width=560, height=350)
        history_text.pack(pady=10, padx=10)
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    for item in reversed(history):
                        history_text.insert("end", f"[{item['time']}]\nFile: {item['file_path']}\nFormat: MP3 (Full Metadata)\nSave Location: {item['save_path']}\n\n")
            except Exception as e:
                history_text.insert("end", f"Could not load history: {str(e)}")
        else:
            history_text.insert("end", "No download history yet")

    def stop_download(self):
        self.downloading = False
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.log("⚠️ Download stopped by user")
        # Show immediate popup so user gets instant feedback
        messagebox.showinfo("Stopped", "Download has been stopped.")

    # Core download task with FULL METADATA EMBEDDING
    def download_task(self, urls):
        if not self.is_ffmpeg_installed():
            self.log("❌ ERROR: FFmpeg is required.")
            self.after(0, lambda: messagebox.showerror("Error", "FFmpeg is required. Please install it."))
            self.after(0, self.update_ffmpeg_status_ui)
            return

        # Quality mapping
        quality_map = {
            "Highest Quality (320kbps)": "320",
            "High Quality (192kbps)": "192",
            "Standard Quality (128kbps)": "128"
        }
        selected_bitrate = quality_map.get(self.quality_var.get(), "320")
        self.save_config()

        # Output template
        if self.classify_var.get():
            outtmpl = os.path.join(self.save_path, "%(artist)s/%(title)s.%(ext)s")
        else:
            outtmpl = os.path.join(self.save_path, "%(title)s.%(ext)s")

        # --- FULL METADATA CONFIGURATION ---
        postprocessors = [
            # 1. Extract audio to MP3
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': selected_bitrate,
            },
            # 2. Write ALL available metadata (Title, Artist, Album, Year, Track #, etc.)
            {
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
            },
            # 3. Embed Thumbnail as Album Cover (ID3v2 tag for MP3)
            {
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            }
        ]

        # HTTP Headers
        http_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        cookie_val = self.cookie_entry.get().strip()
        if cookie_val:
            http_headers['Cookie'] = cookie_val

        # YT-DLP Options Optimized for Metadata
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': postprocessors,
            'outtmpl': outtmpl,
            
            # --- Metadata & Thumbnail Flags ---
            'writethumbnail': True,             # Download thumbnail for embedding
            
            # --- File Behaviour ---
            'updatetime': False,                # Don't change file modified time
            'overwrites': False,                # Don't overwrite existing files
            
            'noplaylist': False,
            'quiet': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'progress_hooks': [self.progress_hook],
            'http_headers': http_headers,
            
            # --- FFmpeg Arguments for better ID3 tags ---
            'postprocessor_args': {
                'FFmpegExtractAudio': [
                    '-id3v2_version', '3',      # Use ID3v2.3 (most compatible)
                    '-write_id3v1', '1',         # Also write ID3v1 for legacy players
                ]
            }
        }

        if self.increment_var.get():
            ydl_opts['download_archive'] = ARCHIVE_FILE

        self.log(f"Starting download with FULL METADATA (MP3, {selected_bitrate}kbps)...")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log("Parsing links and extracting metadata...")
                ydl.download(urls)
            if self.downloading:  # Only show success if NOT stopped by user
                self.log("🎉 All tasks completed! MP3s have Title, Artist, Album, Year & Cover Art.")
                self.after(0, lambda: messagebox.showinfo("Completed", "All songs downloaded with full metadata!"))
        except yt_dlp.utils.DownloadCancelled:
            # User hit Stop — already notified via stop_download(), just log it
            self.log("🛑 Download cancelled by user.")
        except Exception as e:
            if self.downloading:
                self.log(f"❌ Error: {str(e)}")
                self.after(0, lambda: messagebox.showerror("Error", f"Download failed: {str(e)}"))
        finally:
            self.downloading = False
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            self.after(0, lambda: self.stop_btn.configure(state="disabled"))

    def start_download(self):
        if not self.is_ffmpeg_installed():
            self.update_ffmpeg_status_ui()
            messagebox.showerror("Error", "FFmpeg is not installed.")
            return
        url_text = self.url_text.get("1.0", "end").strip()
        if not url_text:
            messagebox.showwarning("Notice", "Please enter download links!")
            return
        urls = [u.strip() for u in url_text.split("\n") if u.strip()]
        self.downloading = True
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        threading.Thread(target=self.download_task, args=(urls,), daemon=True).start()

if __name__ == "__main__":
    app = YTMusicDownloaderPro()
    app.mainloop()