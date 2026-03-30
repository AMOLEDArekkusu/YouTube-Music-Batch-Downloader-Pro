import customtkinter as ctk
import yt_dlp
import threading
import os
import json
import datetime
import subprocess
import ctypes
import urllib.request
import zipfile
import shutil
import tempfile
import math
from tkinter import filedialog, messagebox

# Hide the console window on Windows
if os.name == 'nt':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

APP_DATA_FOLDER = os.path.join(os.path.expanduser("~"), ".yt_music_downloader")
os.makedirs(APP_DATA_FOLDER, exist_ok=True)

# Ensure Deno (JS runtime for yt-dlp signature solving) is on PATH
_deno_bin = os.path.join(os.path.expanduser("~"), ".deno", "bin")
if os.path.isdir(_deno_bin) and _deno_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _deno_bin + os.pathsep + os.environ.get("PATH", "")

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
CONFIG_FILE  = os.path.join(APP_DATA_FOLDER, "downloader_config.json")
HISTORY_FILE = os.path.join(APP_DATA_FOLDER, "download_history.json")
ARCHIVE_FILE = os.path.join(APP_DATA_FOLDER, "download_archive.txt")


class YTMusicDownloaderPro(ctk.CTk):
    """
    Collector Pro — YouTube Music Batch Downloader
    Layout matches the modern Collector Pro design mockup.
    """

    # ── Colour tuples (light, dark) ──────────────────────────────────────────
    BG           = ("#f0f2f5", "#1a1d27")    # main background
    SIDEBAR      = ("#ffffff", "#13151f")    # sidebar
    SIDEBAR_BORDER = ("#e3e6eb", "#252836")  # sidebar right border
    CARD         = ("#ffffff", "#1f2235")    # card background
    CARD_BORDER  = ("#e3e6eb", "#2e3149")    # card border
    ACCENT       = ("#2563eb", "#3b74f5")    # primary accent (blue)
    ACCENT_DIM   = ("#1d4ed8", "#2b5ee0")    # darker accent
    ACCENT_GLOW  = ("#60a5fa", "#93c5fd")    # light accent for glow
    TEXT         = ("#111827", "#e8eaf4")    # primary text
    SUBTEXT      = ("#6b7280", "#7c82a0")    # secondary text
    NAV_ACTIVE   = ("#eff6ff", "#1e3a6e")    # active nav item bg
    NAV_ACTIVE_TXT = ("#2563eb", "#60a5fa")  # active nav item text
    LOG_BG       = ("#f8f9fb", "#141622")    # log terminal bg
    LOG_HEADER   = ("#e8eaef", "#0f1120")    # log header bar
    STOP_FG      = ("#374151", "#d1d5e8")    # stop button text
    STOP_BG      = ("#ffffff", "#1f2235")    # stop button bg
    STOP_BORDER  = ("#d1d5db", "#2e3149")    # stop button border
    STAT_CARD    = ("#ffffff", "#1f2235")    # stat card bg
    HIRES_BG     = ("#2563eb", "#3b74f5")    # Hi-Res toggle pill bg
    START_BTN    = ("#2563eb", "#3b74f5")    # start download button
    GREEN_DOT    = ("#16a34a", "#22c55e")    # online/active indicator
    TOPBAR_BG    = ("#ffffff", "#13151f")    # top bar background
    TOPBAR_INPUT = ("#f3f4f6", "#1a1d2e")    # URL input field bg

    def __init__(self):
        super().__init__()
        self.title("Collector Pro  —  YouTube Music Batch Downloader")
        self.geometry("1060x700")
        self.resizable(False, False)
        self.configure(fg_color=self.BG)

        self._is_dark = False

        self.save_path = os.path.join(os.path.expanduser("~"), "Music", "YT Music Downloads")
        os.makedirs(self.save_path, exist_ok=True)

        self.format_var  = ctk.StringVar(value="MP3")
        self.quality_var = ctk.StringVar(value="Highest Quality (320kbps)")
        self.hires_var   = ctk.BooleanVar(value=True)
        self.load_config()

        self.downloading      = False
        self.ffmpeg_available = False
        self._cookie_browser  = "chrome"   # default: extract cookies from Chrome
        self._total_tracks    = self._load_total_tracks()
        self._lib_size_str    = self._calculate_library_size()
        self._avg_speed_str   = "—"
        self._speed_samples   = []

        # Layout: sidebar (col 0) | main+topbar (col 1)
        self.grid_columnconfigure(0, weight=0, minsize=200)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_right_panel()

        self.check_ffmpeg_on_startup()
        self.update_ffmpeg_status_ui()

    # ─────────────────────────────────── Helpers ─────────────────────────────

    def _load_total_tracks(self):
        """Count total tracks from download history."""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return len(json.load(f))
            except Exception:
                pass
        return 0

    def _calculate_library_size(self):
        total_size = 0
        if os.path.exists(self.save_path):
            for dirpath, dirnames, filenames in os.walk(self.save_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        return self._format_size(total_size)

    def _format_size(self, size_bytes):
        if not size_bytes or size_bytes <= 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        if s.is_integer():
            return f"{int(s)} {size_name[i]}"
        return f"{s} {size_name[i]}"

    def _bind_hover(self, widget, enter_cfg, leave_cfg):
        widget.bind("<Enter>", lambda e: widget.configure(**enter_cfg), add="+")
        widget.bind("<Leave>", lambda e: widget.configure(**leave_cfg), add="+")

    def _card(self, parent, **kw):
        defaults = dict(fg_color=self.CARD, corner_radius=12,
                        border_width=1, border_color=self.CARD_BORDER)
        defaults.update(kw)
        return ctk.CTkFrame(parent, **defaults)

    def _label(self, parent, text, size=12, weight="normal", color=None, **kw):
        return ctk.CTkLabel(
            parent, text=text,
            font=("Segoe UI", size, weight),
            text_color=color if color else self.TEXT,
            **kw)

    def _small_label(self, parent, text, **kw):
        return ctk.CTkLabel(
            parent, text=text,
            font=("Segoe UI", 10, "bold"),
            text_color=self.SUBTEXT,
            **kw)

    # ─────────────────────────────────── Sidebar ─────────────────────────────

    def _build_sidebar(self):
        sb = ctk.CTkFrame(
            self,
            fg_color=self.SIDEBAR,
            corner_radius=0,
            width=200,
            border_width=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)

        # ── Logo ─────────────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(sb, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 4))
        logo_frame.grid_columnconfigure(0, weight=1)

        logo_icon = ctk.CTkLabel(
            logo_frame,
            text="▶",
            font=("Segoe UI", 18, "bold"),
            text_color=self.ACCENT,
            width=32, height=32)
        logo_icon.grid(row=0, column=0, sticky="w")

        logo_text_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_text_frame.grid(row=0, column=1, sticky="w", padx=(6, 0))

        ctk.CTkLabel(
            logo_text_frame,
            text="Collector Pro",
            font=("Segoe UI", 14, "bold"),
            text_color=self.TEXT).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            logo_text_frame,
            text="V2.0.4",
            font=("Segoe UI", 9),
            text_color=self.SUBTEXT).grid(row=1, column=0, sticky="w")

        # ── Divider ───────────────────────────────────────────────────────────
        ctk.CTkFrame(sb, height=1, fg_color=self.CARD_BORDER).grid(
            row=1, column=0, sticky="ew", padx=12, pady=(8, 10))

        # ── Nav Items ─────────────────────────────────────────────────────────
        nav_items = [
            ("⊞", "Dashboard",  True, self.show_dashboard),
            ("⇩", "Download History",  False, self.show_history),
            ("♪", "Library",    False, None),
            ("⚙", "Settings",   False, self.show_settings),
        ]
        for i, (icon, label, active, cmd) in enumerate(nav_items):
            self._nav_item(sb, row=2 + i, icon=icon, label=label, active=active, command=cmd)

        # ── Spacer ────────────────────────────────────────────────────────────
        sb.grid_rowconfigure(6, weight=1)

        # ── Theme toggle ──────────────────────────────────────────────────────
        theme_row = ctk.CTkFrame(sb, fg_color="transparent")
        theme_row.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 6))
        theme_row.grid_columnconfigure(0, weight=1)

        self._theme_lbl = ctk.CTkLabel(
            theme_row,
            text="☀  Light Mode",
            font=("Segoe UI", 11),
            text_color=self.SUBTEXT)
        self._theme_lbl.grid(row=0, column=0, sticky="w")

        self._theme_switch = ctk.CTkSwitch(
            theme_row, text="",
            command=self._on_theme_toggle,
            width=40, height=20,
            switch_width=40, switch_height=20,
            progress_color=self.ACCENT,
            button_color=self.ACCENT_DIM,
            button_hover_color=self.ACCENT)
        self._theme_switch.grid(row=0, column=1)

        # ── Start Batch button ────────────────────────────────────────────────
        self.batch_btn = ctk.CTkButton(
            sb,
            text="Start Batch",
            command=self.start_download,
            width=168, height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_DIM,
            text_color="#ffffff",
            corner_radius=10)
        self.batch_btn.grid(row=8, column=0, padx=16, pady=(4, 8))

        # ── FFmpeg status pill ────────────────────────────────────────────────
        self.ffmpeg_pill = ctk.CTkFrame(
            sb,
            fg_color=self.CARD,
            corner_radius=20,
            border_width=1, border_color=self.CARD_BORDER)
        self.ffmpeg_pill.grid(row=9, column=0, padx=16, pady=(0, 16))
        self.ffmpeg_pill.grid_columnconfigure(0, weight=1)

        self.ffmpeg_dot = ctk.CTkLabel(
            self.ffmpeg_pill,
            text="●",
            font=("Segoe UI", 10),
            text_color=self.SUBTEXT)
        self.ffmpeg_dot.grid(row=0, column=0, sticky="w", padx=(10, 0), pady=6)

        self.ffmpeg_status_label = ctk.CTkLabel(
            self.ffmpeg_pill,
            text="FFmpeg Status:  Checking…",
            font=("Segoe UI", 10),
            text_color=self.SUBTEXT)
        self.ffmpeg_status_label.grid(row=0, column=1, padx=(4, 12), pady=6)

    def _nav_item(self, parent, row, icon, label, active=False, command=None):
        bg    = self.NAV_ACTIVE if active else "transparent"
        color = self.NAV_ACTIVE_TXT if active else self.SUBTEXT

        frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=8, height=38)
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=2)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_propagate(False)

        icon_lbl = ctk.CTkLabel(
            frame,
            text=icon,
            font=("Segoe UI", 14),
            text_color=color,
            width=24)
        icon_lbl.grid(row=0, column=0, padx=(10, 4), pady=0, sticky="w")

        text_lbl = ctk.CTkLabel(
            frame,
            text=label,
            font=("Segoe UI", 12, "bold" if active else "normal"),
            text_color=color)
        text_lbl.grid(row=0, column=1, sticky="w", pady=0)

        if not hasattr(self, 'nav_widgets'):
            self.nav_widgets = {}
            self.active_nav = None
            
        self.nav_widgets[label] = (frame, icon_lbl, text_lbl)
        if active:
            self.active_nav = label

        if command:
            # Bind the click event to the frame and its label children
            frame.bind("<Button-1>", lambda e, c=command: c())
            icon_lbl.bind("<Button-1>", lambda e, c=command: c())
            text_lbl.bind("<Button-1>", lambda e, c=command: c())

        def on_enter(e):
            if hasattr(self, 'active_nav') and self.active_nav != label:
                frame.configure(fg_color=self.CARD_BORDER)

        def on_leave(e):
            if hasattr(self, 'active_nav') and self.active_nav != label:
                frame.configure(fg_color="transparent")

        frame.bind("<Enter>", on_enter, add="+")
        frame.bind("<Leave>", on_leave, add="+")

    def _set_active_nav(self, active_label):
        if not hasattr(self, 'nav_widgets'):
            return
        self.active_nav = active_label
        for label, (frame, icon_lbl, text_lbl) in self.nav_widgets.items():
            if label == active_label:
                frame.configure(fg_color=self.NAV_ACTIVE)
                icon_lbl.configure(text_color=self.NAV_ACTIVE_TXT)
                text_lbl.configure(text_color=self.NAV_ACTIVE_TXT, font=("Segoe UI", 12, "bold"))
            else:
                frame.configure(fg_color="transparent")
                icon_lbl.configure(text_color=self.SUBTEXT)
                text_lbl.configure(text_color=self.SUBTEXT, font=("Segoe UI", 12, "normal"))

    # ─────────────────────────────── Right panel ─────────────────────────────

    def _build_right_panel(self):
        right = ctk.CTkFrame(self, fg_color=self.BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self._build_topbar(right)
        self._build_content(right)

    # ── Top bar ───────────────────────────────────────────────────────────────

    def _build_topbar(self, parent):
        topbar = ctk.CTkFrame(
            parent,
            fg_color=self.TOPBAR_BG,
            corner_radius=0,
            height=58,
            border_width=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(topbar, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        inner.grid_columnconfigure(0, weight=1)

        # URL entry
        url_frame = ctk.CTkFrame(
            inner,
            fg_color=self.TOPBAR_INPUT,
            corner_radius=8,
            border_width=1, border_color=self.CARD_BORDER)
        url_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        url_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            url_frame,
            text="⛓",
            font=("Segoe UI", 13),
            text_color=self.SUBTEXT,
            width=24).grid(row=0, column=0, padx=(10, 4), pady=8)

        self.url_text = ctk.CTkEntry(
            url_frame,
            placeholder_text="Paste YouTube Music URL or Playlist link…",
            font=("Segoe UI", 12),
            fg_color="transparent",
            border_width=0,
            text_color=self.TEXT,
            placeholder_text_color=self.SUBTEXT,
            height=34)
        self.url_text.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=4)

        # Import .txt button
        self.import_btn = ctk.CTkButton(
            inner,
            text="📄  Import .txt",
            command=self.import_txt,
            width=120, height=36,
            font=("Segoe UI", 12),
            fg_color=self.CARD,
            hover_color=self.CARD_BORDER,
            text_color=self.TEXT,
            border_width=1, border_color=self.CARD_BORDER,
            corner_radius=8)
        self.import_btn.grid(row=0, column=1, padx=(0, 6))

        # History icon
        hist_btn = ctk.CTkButton(
            inner,
            text="🕐",
            command=self.show_history,
            width=36, height=36,
            font=("Segoe UI", 15),
            fg_color=self.CARD,
            hover_color=self.CARD_BORDER,
            text_color=self.TEXT,
            border_width=1, border_color=self.CARD_BORDER,
            corner_radius=8)
        hist_btn.grid(row=0, column=2, padx=(0, 6))

        # Settings icon
        sett_btn = ctk.CTkButton(
            inner,
            text="⚙",
            command=self.show_settings,
            width=36, height=36,
            font=("Segoe UI", 15),
            fg_color=self.CARD,
            hover_color=self.CARD_BORDER,
            text_color=self.TEXT,
            border_width=1, border_color=self.CARD_BORDER,
            corner_radius=8)
        sett_btn.grid(row=0, column=3, padx=(0, 6))

    # ── Content area ──────────────────────────────────────────────────────────

    def _build_content(self, parent):
        content = ctk.CTkFrame(parent, fg_color=self.BG, corner_radius=0)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1, uniform="col")
        content.grid_columnconfigure(1, weight=1, uniform="col")
        content.grid_rowconfigure(0, weight=1)

        self._build_left_column(content)
        self._build_right_column(content)
        self._build_stats_bar(parent)
        self._build_footer(parent)

    def _build_left_column(self, parent):
        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=(16, 0))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        # ── Configuration card ────────────────────────────────────────────────
        cfg_card = self._card(left)
        cfg_card.grid(row=0, column=0, sticky="ew")
        cfg_card.grid_columnconfigure(0, weight=1)

        # Card header
        hdr = ctk.CTkFrame(cfg_card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="⚙  Configuration",
            font=("Segoe UI", 15, "bold"),
            text_color=self.TEXT).grid(row=0, column=0, sticky="w")

        # Save Destination
        self._small_label(cfg_card, "SAVE DESTINATION").grid(
            row=1, column=0, sticky="w", padx=18, pady=(0, 6))

        dest_row = ctk.CTkFrame(cfg_card, fg_color="transparent")
        dest_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        dest_row.grid_columnconfigure(0, weight=1)

        dest_inner = ctk.CTkFrame(
            dest_row,
            fg_color=self.TOPBAR_INPUT,
            corner_radius=8,
            border_width=1, border_color=self.CARD_BORDER,
            height=36)
        dest_inner.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        dest_inner.grid_columnconfigure(1, weight=1)
        dest_inner.grid_propagate(False)

        ctk.CTkLabel(
            dest_inner,
            text="🗁",
            font=("Segoe UI", 13),
            text_color=self.SUBTEXT,
            width=24).grid(row=0, column=0, padx=(8, 4), pady=0, sticky="w")

        self.path_display = ctk.CTkEntry(
            dest_inner,
            font=("Segoe UI", 11),
            fg_color="transparent",
            border_width=0,
            text_color=self.SUBTEXT,
            height=32)
        self.path_display.insert(0, self.save_path)
        self.path_display.configure(state="readonly")
        self.path_display.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        change_btn = ctk.CTkButton(
            dest_row,
            text="CHANGE",
            command=self.select_path,
            width=70, height=36,
            font=("Segoe UI", 11, "bold"),
            fg_color="transparent",
            hover_color=self.CARD_BORDER,
            text_color=self.ACCENT,
            border_width=0,
            corner_radius=8)
        change_btn.grid(row=0, column=1)

        # Output Quality
        self._small_label(cfg_card, "OUTPUT QUALITY").grid(
            row=3, column=0, sticky="w", padx=18, pady=(0, 6))

        quality_row = ctk.CTkFrame(cfg_card, fg_color="transparent")
        quality_row.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 14))

        self.quality_menu = ctk.CTkOptionMenu(
            quality_row,
            values=["Highest Quality (320kbps)", "192kbps (Medium Quality)", "128kbps (Standard)"],
            variable=self.quality_var,
            width=180, height=34,
            font=("Segoe UI", 11),
            fg_color=self.TOPBAR_INPUT,
            button_color=self.CARD_BORDER,
            button_hover_color=self.CARD_BORDER,
            text_color=self.TEXT,
            dropdown_fg_color=self.CARD,
            dropdown_text_color=self.TEXT,
            dropdown_hover_color=self.CARD_BORDER,
            corner_radius=8)
        self.quality_menu.grid(row=0, column=0, padx=(0, 10))

        # Hi-Res toggle pill
        self.hires_btn = ctk.CTkButton(
            quality_row,
            text="✔  Hi-Res Audio",
            command=self._toggle_hires,
            width=130, height=34,
            font=("Segoe UI", 11, "bold"),
            fg_color=self.HIRES_BG,
            hover_color=self.ACCENT_DIM,
            text_color="#ffffff",
            corner_radius=17)
        self.hires_btn.grid(row=0, column=1)

        # Checkboxes
        chk_frame = ctk.CTkFrame(cfg_card, fg_color="transparent")
        chk_frame.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))

        self.classify_var = ctk.BooleanVar(value=True)
        self.classify_check = ctk.CTkCheckBox(
            chk_frame,
            text="Auto-sort Artist Folder",
            variable=self.classify_var,
            font=("Segoe UI", 12),
            text_color=self.TEXT,
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_DIM,
            checkmark_color="#ffffff",
            border_color=self.CARD_BORDER,
            corner_radius=4)
        self.classify_check.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.increment_var = ctk.BooleanVar(value=False)
        self.increment_check = ctk.CTkCheckBox(
            chk_frame,
            text="Incremental Sync",
            variable=self.increment_var,
            font=("Segoe UI", 12),
            text_color=self.TEXT,
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_DIM,
            checkmark_color="#ffffff",
            border_color=self.CARD_BORDER,
            corner_radius=4)
        self.increment_check.grid(row=1, column=0, sticky="w")

        # ── Premium Access card ───────────────────────────────────────────────
        prem_card = self._card(left)
        prem_card.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        prem_card.grid_columnconfigure(0, weight=1)
        prem_card.grid_rowconfigure(2, weight=1)

        prem_hdr = ctk.CTkFrame(prem_card, fg_color="transparent")
        prem_hdr.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))

        ctk.CTkLabel(
            prem_hdr,
            text="🔑  Premium Access",
            font=("Segoe UI", 14, "bold"),
            text_color=self.TEXT).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            prem_card,
            text="Paste your authentication cookies here to access\nhigh-quality streams and member-only playlists.",
            font=("Segoe UI", 11),
            text_color=self.SUBTEXT,
            justify="left",
            wraplength=280).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        self.cookie_entry = ctk.CTkTextbox(
            prem_card,
            font=("Consolas", 10),
            fg_color=self.TOPBAR_INPUT,
            text_color=self.SUBTEXT,
            border_width=1, border_color=self.CARD_BORDER,
            corner_radius=8,
            height=90)
        self.cookie_entry.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.cookie_entry.insert("1.0", "Paste netscape-formatted cookies...")

    def _toggle_hires(self):
        self.hires_var.set(not self.hires_var.get())
        if self.hires_var.get():
            self.hires_btn.configure(
                text="✔  Hi-Res Audio",
                fg_color=self.HIRES_BG,
                hover_color=self.ACCENT_DIM)
        else:
            self.hires_btn.configure(
                text="Hi-Res Audio",
                fg_color=self.CARD_BORDER,
                hover_color=self.CARD)

    def _build_right_column(self, parent):
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=(16, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        # Process Log card
        log_card = self._card(right)
        log_card.grid(row=0, column=0, sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        # Log card header bar
        log_hdr = ctk.CTkFrame(
            log_card,
            fg_color=self.LOG_HEADER,
            corner_radius=0,
            height=38)
        log_hdr.grid(row=0, column=0, sticky="ew")
        log_hdr.grid_propagate(False)
        log_hdr.grid_columnconfigure(1, weight=1)

        # Traffic light dots
        dots = ctk.CTkFrame(log_hdr, fg_color="transparent")
        dots.grid(row=0, column=0, padx=(14, 8), pady=0, sticky="w")
        for color, col in [("#f87171", 0), ("#fbbf24", 1), ("#34d399", 2)]:
            ctk.CTkLabel(
                dots,
                text="●",
                font=("Segoe UI", 10),
                text_color=color,
                width=14).grid(row=0, column=col, padx=2)

        ctk.CTkLabel(
            log_hdr,
            text="PROCESS LOG",
            font=("Segoe UI", 10, "bold"),
            text_color=self.SUBTEXT).grid(row=0, column=1, sticky="w", padx=4)

        clear_btn = ctk.CTkButton(
            log_hdr,
            text="⊠ Clear",
            command=self._clear_log,
            width=60, height=24,
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color=self.CARD_BORDER,
            text_color=self.SUBTEXT,
            border_width=0,
            corner_radius=6)
        clear_btn.grid(row=0, column=2, padx=(0, 10))

        # Log textbox
        self.log_text = ctk.CTkTextbox(
            log_card,
            font=("Consolas", 11),
            fg_color=self.LOG_BG,
            text_color=self.TEXT,
            scrollbar_button_color=self.CARD_BORDER,
            corner_radius=0,
            border_width=0,
            wrap="word")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.log_text.configure(state="normal")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")

    # ── Stats bar ─────────────────────────────────────────────────────────────

    def _build_stats_bar(self, parent):
        stats_frame = ctk.CTkFrame(parent, fg_color=self.BG, corner_radius=0)
        stats_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 6))
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        stats = [
            ("📊", f"{self._total_tracks:,}", "TOTAL TRACKS COLLECTED"),
            ("≡", self._lib_size_str, "LIBRARY SIZE"),
            ("⚡", self._avg_speed_str, "AVG SYNC SPEED"),
        ]
        self._stat_value_labels = []
        for col, (icon, val, subtitle) in enumerate(stats):
            sc = self._card(stats_frame)
            sc.grid(row=0, column=col, sticky="ew",
                    padx=(0 if col == 0 else 6, 6 if col < 2 else 0))
            sc.grid_columnconfigure(1, weight=1)

            icon_frame = ctk.CTkFrame(sc, fg_color=self.NAV_ACTIVE, corner_radius=10,
                                       width=40, height=40)
            icon_frame.grid(row=0, column=0, padx=(14, 10), pady=14)
            icon_frame.grid_propagate(False)
            ctk.CTkLabel(
                icon_frame,
                text=icon,
                font=("Segoe UI", 16),
                text_color=self.ACCENT,
                width=40, height=40).grid(row=0, column=0)

            val_col = ctk.CTkFrame(sc, fg_color="transparent")
            val_col.grid(row=0, column=1, sticky="w", pady=14)

            val_lbl = ctk.CTkLabel(
                val_col,
                text=val,
                font=("Segoe UI", 20, "bold"),
                text_color=self.TEXT)
            val_lbl.grid(row=0, column=0, sticky="w")
            self._stat_value_labels.append(val_lbl)

            ctk.CTkLabel(
                val_col,
                text=subtitle,
                font=("Segoe UI", 9, "bold"),
                text_color=self.SUBTEXT).grid(row=1, column=0, sticky="w")

    # ── Footer / action bar ───────────────────────────────────────────────────

    def _build_footer(self, parent):
        footer = ctk.CTkFrame(
            parent,
            fg_color=self.CARD,
            corner_radius=0,
            height=60,
            border_width=0)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(3, weight=1)

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.grid(row=0, column=0, padx=16, pady=10, columnspan=10, sticky="w")

        # Start Download
        self.download_btn = ctk.CTkButton(
            inner,
            text="▶  Start Download",
            command=self.start_download,
            width=160, height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=self.START_BTN,
            hover_color=self.ACCENT_DIM,
            text_color="#ffffff",
            corner_radius=10)
        self.download_btn.grid(row=0, column=0, padx=(0, 10))

        # Stop
        self.stop_btn = ctk.CTkButton(
            inner,
            text="⬛  Stop",
            command=self.stop_download,
            width=100, height=40,
            font=("Segoe UI", 12),
            fg_color=self.STOP_BG,
            hover_color=self.CARD_BORDER,
            text_color=self.STOP_FG,
            border_width=1, border_color=self.STOP_BORDER,
            corner_radius=10)
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))
        self.stop_btn.configure(state="disabled")

        # View History
        hist_btn2 = ctk.CTkButton(
            inner,
            text="⊞  View History",
            command=self.show_history,
            width=130, height=40,
            font=("Segoe UI", 12),
            fg_color=self.STOP_BG,
            hover_color=self.CARD_BORDER,
            text_color=self.STOP_FG,
            border_width=1, border_color=self.STOP_BORDER,
            corner_radius=10)
        hist_btn2.grid(row=0, column=2, padx=(0, 16))

        # Core Engine Active indicator
        engine_frame = ctk.CTkFrame(inner, fg_color="transparent")
        engine_frame.grid(row=0, column=3, padx=(20, 0))

        self._engine_dot = ctk.CTkLabel(
            engine_frame,
            text="●",
            font=("Segoe UI", 12),
            text_color=self.GREEN_DOT)
        self._engine_dot.grid(row=0, column=0, padx=(0, 4))

        ctk.CTkLabel(
            engine_frame,
            text="CORE ENGINE ACTIVE",
            font=("Segoe UI", 11, "bold"),
            text_color=self.SUBTEXT).grid(row=0, column=1)

    # ─────────────────────────────────── Theme ────────────────────────────────

    def _on_theme_toggle(self):
        self._is_dark = not self._is_dark
        mode = "dark" if self._is_dark else "light"
        ctk.set_appearance_mode(mode)
        lbl = "☀  Light Mode" if self._is_dark else "🌙  Dark Mode"
        self._theme_lbl.configure(text=lbl)
        self._theme_switch.configure(
            progress_color=self.ACCENT,
            button_color=self.ACCENT_DIM,
            button_hover_color=self.ACCENT)
        self.update_ffmpeg_status_ui()

    # ─────────────────────────────── FFmpeg ──────────────────────────────────

    def is_ffmpeg_installed(self):
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return result.returncode == 0
        except FileNotFoundError:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            local_ffmpeg = os.path.join(script_dir, "ffmpeg.exe")
            if os.path.exists(local_ffmpeg):
                os.environ["PATH"] = script_dir + os.pathsep + os.environ["PATH"]
                return True
            return False

    def install_ffmpeg_windows(self):
        FFMPEG_URL = (
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
            "latest/ffmpeg-master-latest-win64-gpl.zip"
        )
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dest_ffmpeg = os.path.join(script_dir, "ffmpeg.exe")
        tmp_path = None
        try:
            self.after(0, lambda: self.log("Downloading FFmpeg from GitHub..."))
            self.after(0, lambda: self.log(f"  → {FFMPEG_URL}"))
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp_path = tmp.name

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

            with zipfile.ZipFile(tmp_path, 'r') as zf:
                ffmpeg_entry = next(
                    (n for n in zf.namelist()
                     if n.endswith("/bin/ffmpeg.exe") or n.endswith("/ffmpeg.exe")), None)
                if ffmpeg_entry is None:
                    self.after(0, lambda: self.log("❌ Could not locate ffmpeg.exe inside the archive."))
                    return False
                with zf.open(ffmpeg_entry) as src, open(dest_ffmpeg, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

            os.remove(tmp_path)
            os.environ["PATH"] = script_dir + os.pathsep + os.environ.get("PATH", "")
            self.after(0, lambda: self.log(f"✅ FFmpeg extracted to: {dest_ffmpeg}"))
            return True
        except Exception as e:
            self.after(0, lambda err=str(e): self.log(f"❌ FFmpeg download/extract error: {err}"))
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    def _install_ffmpeg_threaded(self):
        def _worker():
            success = self.install_ffmpeg_windows()
            if success:
                self.ffmpeg_available = True
                self.after(0, self.update_ffmpeg_status_ui)
                self.after(0, lambda: messagebox.showinfo(
                    "FFmpeg Ready",
                    "FFmpeg has been downloaded and extracted successfully!\n"
                    "You can start downloading now."))
            else:
                self.after(0, self.show_manual_install_guide)
        threading.Thread(target=_worker, daemon=True).start()

    def check_ffmpeg_on_startup(self):
        self.ffmpeg_available = self.is_ffmpeg_installed()
        if not self.ffmpeg_available:
            if messagebox.askyesno(
                "FFmpeg Required",
                "FFmpeg is required to convert music and embed metadata.\n\n"
                "FFmpeg was not found on this PC.\n"
                "Do you want to download & extract it automatically?\n\n"
                "(ffmpeg.exe will be placed next to this script)"):
                self._install_ffmpeg_threaded()
            else:
                self.show_manual_install_guide()

    def show_manual_install_guide(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        messagebox.showwarning("FFmpeg Installation Required",
            "Manual FFmpeg Installation:\n\n"
            "1. Download FFmpeg (zip):\n"
            "   https://github.com/BtbN/FFmpeg-Builds/releases/latest\n"
            "   (choose: ffmpeg-master-latest-win64-gpl.zip)\n\n"
            "2. Open the zip and go into the 'bin' folder\n\n"
            "3. Copy 'ffmpeg.exe' to the same folder as this script:\n"
            f"   {script_dir}\n\n"
            "4. Restart this application")
        self.ffmpeg_available = False

    def update_ffmpeg_status_ui(self):
        self.ffmpeg_available = self.is_ffmpeg_installed()
        if self.ffmpeg_available:
            self.ffmpeg_dot.configure(text_color="#22c55e")
            self.ffmpeg_status_label.configure(
                text="FFmpeg Status:  Active",
                text_color="#16a34a" if not self._is_dark else "#22c55e")
        else:
            self.ffmpeg_dot.configure(text_color="#f87171")
            self.ffmpeg_status_label.configure(
                text="FFmpeg Status:  Not Found",
                text_color="#c0392b" if not self._is_dark else "#f85149")
            self.download_btn.configure(state="disabled")

    # ─────────────────────────────── Config & Misc ────────────────────────────

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.save_path = config.get("save_path", self.save_path)
                    self.quality_var.set(config.get("audio_quality", "Highest Quality (320kbps)"))
                    self._cookie_browser = config.get("cookie_browser", "chrome")
            except Exception:
                pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "save_path": self.save_path,
                    "output_format": "MP3",
                    "audio_quality": self.quality_var.get(),
                    "cookie_browser": getattr(self, '_cookie_browser', 'chrome')
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def log(self, msg):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}]  {msg}\n")
        self.log_text.see("end")

    def select_path(self):
        path = filedialog.askdirectory(initialdir=self.save_path)
        if path:
            self.save_path = path
            self.path_display.configure(state="normal")
            self.path_display.delete(0, "end")
            self.path_display.insert(0, path)
            self.path_display.configure(state="readonly")
            self.save_config()
            self._lib_size_str = self._calculate_library_size()
            self._refresh_stats()

    def import_txt(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    links = f.read().strip()
                # Put into URL entry (single-line entry)
                self.url_text.delete(0, "end")
                self.url_text.insert(0, links.split("\n")[0])
                self.log(f"Imported {len(links.splitlines())} link(s) from TXT file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import TXT: {str(e)}")

    def progress_hook(self, d):
        if not self.downloading:
            raise yt_dlp.utils.DownloadCancelled("Stopped by user")
        if d['status'] == 'downloading':
            speed_str = d.get('_speed_str', 'N/A')
            speed = d.get('speed')
            if speed:
                self._speed_samples.append(speed)
                if len(self._speed_samples) > 50:
                    self._speed_samples.pop(0)
                avg_speed = sum(self._speed_samples) / len(self._speed_samples)
                self._avg_speed_str = self._format_size(avg_speed) + "/s"
                self.after(0, self._refresh_stats)

            self.log(f"Downloading: {os.path.basename(d.get('filename',''))} "
                     f"| {d.get('_percent_str','N/A')} | {speed_str}")
        elif d['status'] == 'finished':
            filename = d.get('filename', '')
            self.log(f"✅ Processing metadata for: {os.path.basename(filename)}")
            self.add_history(filename)
            # Update track counter
            self._total_tracks += 1
            self._downloads_this_session += 1
            self._lib_size_str = self._calculate_library_size()
            self.after(0, self._refresh_stats)

    def _refresh_stats(self):
        if self._stat_value_labels:
            self._stat_value_labels[0].configure(text=f"{self._total_tracks:,}")
            if len(self._stat_value_labels) > 2:
                self._stat_value_labels[1].configure(text=self._lib_size_str)
                self._stat_value_labels[2].configure(text=self._avg_speed_str)

    def add_history(self, file_path):
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
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
        except Exception:
            pass

    def show_history(self):
        self._set_active_nav("Download History")
        if not hasattr(self, "history_main_frame"):
            self.history_main_frame = ctk.CTkFrame(self, fg_color=self.BG, corner_radius=0)
            self.history_main_frame.grid_columnconfigure(0, weight=1)
            self.history_main_frame.grid_rowconfigure(1, weight=1)

            # Top bar for history
            topbar = ctk.CTkFrame(self.history_main_frame, fg_color=self.TOPBAR_BG, corner_radius=0, height=58, border_width=0)
            topbar.grid(row=0, column=0, sticky="ew")
            topbar.grid_propagate(False)
            topbar.grid_columnconfigure(0, weight=1)

            inner = ctk.CTkFrame(topbar, fg_color="transparent")
            inner.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
            inner.grid_columnconfigure(1, weight=1)
            
            back_btn = ctk.CTkButton(
                inner, text="← Back", command=self.hide_history,
                width=80, height=36, font=("Segoe UI", 12),
                fg_color=self.CARD, hover_color=self.CARD_BORDER,
                text_color=self.TEXT, border_width=1, border_color=self.CARD_BORDER,
                corner_radius=8
            )
            back_btn.grid(row=0, column=0, padx=(0, 16))

            ctk.CTkLabel(
                inner, text="Download History",
                font=("Segoe UI", 16, "bold"), text_color=self.TEXT
            ).grid(row=0, column=1, sticky="w")

            self.history_scroll = ctk.CTkScrollableFrame(self.history_main_frame, fg_color="transparent")
            self.history_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
            self.history_scroll.grid_columnconfigure(0, weight=1)

        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    
                if not history:
                    lbl = ctk.CTkLabel(self.history_scroll, text="No download history yet", font=("Segoe UI", 14), text_color=self.SUBTEXT)
                    lbl.grid(row=0, column=0, pady=20)
                else:
                    for i, item in enumerate(reversed(history)):
                        card = self._card(self.history_scroll)
                        card.grid(row=i, column=0, sticky="ew", pady=(0, 10))
                        card.grid_columnconfigure(1, weight=1)
                        
                        icon_frame = ctk.CTkFrame(card, fg_color=self.NAV_ACTIVE, corner_radius=8, width=36, height=36)
                        icon_frame.grid(row=0, column=0, padx=14, pady=14, rowspan=2)
                        icon_frame.grid_propagate(False)
                        icon_frame.grid_rowconfigure(0, weight=1)
                        icon_frame.grid_columnconfigure(0, weight=1)
                        
                        ctk.CTkLabel(icon_frame, text="♪", font=("Segoe UI", 16), text_color=self.ACCENT).grid(row=0, column=0)
                        
                        filename = os.path.basename(item.get('file_path', 'Unknown File'))
                        
                        title_lbl = ctk.CTkLabel(card, text=filename, font=("Segoe UI", 13, "bold"), text_color=self.TEXT, anchor="w")
                        title_lbl.grid(row=0, column=1, sticky="w", padx=(0, 14), pady=(12, 0))
                        
                        meta_text = f"Saved in: {item.get('save_path', '')}  •  Format: MP3 (Full Metadata)"
                        meta_lbl = ctk.CTkLabel(card, text=meta_text, font=("Segoe UI", 11), text_color=self.SUBTEXT, anchor="w")
                        meta_lbl.grid(row=1, column=1, sticky="w", padx=(0, 14), pady=(0, 12))
                        
                        time_lbl = ctk.CTkLabel(card, text=item.get('time', ''), font=("Segoe UI", 11), text_color=self.SUBTEXT)
                        time_lbl.grid(row=0, column=2, rowspan=2, padx=16)
                        
            except Exception as e:
                lbl = ctk.CTkLabel(self.history_scroll, text=f"Could not load history: {str(e)}", font=("Segoe UI", 12), text_color="#ef4444")
                lbl.grid(row=0, column=0, pady=20)
        else:
            lbl = ctk.CTkLabel(self.history_scroll, text="No download history yet", font=("Segoe UI", 14), text_color=self.SUBTEXT)
            lbl.grid(row=0, column=0, pady=20)

        self.history_main_frame.grid(row=0, column=1, sticky="nsew")
        self.history_main_frame.tkraise()

    def hide_history(self):
        self.show_dashboard()

    def show_dashboard(self):
        self._set_active_nav("Dashboard")
        if hasattr(self, "history_main_frame"):
            self.history_main_frame.grid_forget()
        if hasattr(self, "settings_main_frame"):
            self.settings_main_frame.grid_forget()

    def show_settings(self):
        self._set_active_nav("Settings")
        if not hasattr(self, "settings_main_frame"):
            self.settings_main_frame = ctk.CTkFrame(self, fg_color=self.BG, corner_radius=0)
            self.settings_main_frame.grid_columnconfigure(0, weight=1)
            self.settings_main_frame.grid_rowconfigure(1, weight=1)

            # Top bar for settings
            topbar = ctk.CTkFrame(self.settings_main_frame, fg_color=self.TOPBAR_BG, corner_radius=0, height=58, border_width=0)
            topbar.grid(row=0, column=0, sticky="ew")
            topbar.grid_propagate(False)
            topbar.grid_columnconfigure(0, weight=1)

            inner = ctk.CTkFrame(topbar, fg_color="transparent")
            inner.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
            inner.grid_columnconfigure(1, weight=1)
            
            back_btn = ctk.CTkButton(
                inner, text="← Back", command=self.show_dashboard,
                width=80, height=36, font=("Segoe UI", 12),
                fg_color=self.CARD, hover_color=self.CARD_BORDER,
                text_color=self.TEXT, border_width=1, border_color=self.CARD_BORDER,
                corner_radius=8
            )
            back_btn.grid(row=0, column=0, padx=(0, 16))

            ctk.CTkLabel(
                inner, text="Settings",
                font=("Segoe UI", 16, "bold"), text_color=self.TEXT
            ).grid(row=0, column=1, sticky="w")

            content = ctk.CTkScrollableFrame(self.settings_main_frame, fg_color="transparent")
            content.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
            content.grid_columnconfigure(0, weight=1)
            
            # Application Settings Card
            app_card = self._card(content)
            app_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
            app_card.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(app_card, text="Application Settings", font=("Segoe UI", 14, "bold"), text_color=self.TEXT).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 10))
            
            ctk.CTkLabel(app_card, text="Appearance", font=("Segoe UI", 12), text_color=self.TEXT).grid(row=1, column=0, sticky="w", padx=18, pady=8)
            theme_btn = ctk.CTkButton(app_card, text="Toggle Theme", command=self._on_theme_toggle, width=120, fg_color=self.CARD, hover_color=self.CARD_BORDER, text_color=self.TEXT, border_width=1, border_color=self.CARD_BORDER)
            theme_btn.grid(row=1, column=1, sticky="e", padx=18, pady=8)
            
            ctk.CTkLabel(app_card, text="FFmpeg Engine", font=("Segoe UI", 12), text_color=self.TEXT).grid(row=2, column=0, sticky="w", padx=18, pady=8)
            ffmpeg_btn = ctk.CTkButton(app_card, text="Recheck / Install", command=self.check_ffmpeg_on_startup, width=120, fg_color=self.CARD, hover_color=self.CARD_BORDER, text_color=self.TEXT, border_width=1, border_color=self.CARD_BORDER)
            ffmpeg_btn.grid(row=2, column=1, sticky="e", padx=18, pady=8)

            # Browser Cookies — auto-extract login cookies to bypass bot detection
            ctk.CTkLabel(app_card, text="Browser Cookies", font=("Segoe UI", 12), text_color=self.TEXT).grid(row=3, column=0, sticky="w", padx=18, pady=8)
            self._cookie_browser_var = ctk.StringVar(value=getattr(self, '_cookie_browser', 'chrome'))
            cookie_menu = ctk.CTkOptionMenu(
                app_card,
                values=["chrome", "firefox", "edge", "brave", "opera", "none"],
                variable=self._cookie_browser_var,
                command=self._on_cookie_browser_change,
                width=120,
                fg_color=self.TOPBAR_INPUT,
                button_color=self.CARD_BORDER,
                button_hover_color=self.CARD_BORDER,
                text_color=self.TEXT,
                dropdown_fg_color=self.CARD,
                dropdown_text_color=self.TEXT,
                dropdown_hover_color=self.CARD_BORDER,
                corner_radius=8)
            cookie_menu.grid(row=3, column=1, sticky="e", padx=18, pady=8)
            ctk.CTkLabel(app_card, text="Auto-extract login session to bypass YouTube bot detection",
                         font=("Segoe UI", 10), text_color=self.SUBTEXT).grid(
                row=4, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))

            # Data Management Card
            data_card = self._card(content)
            data_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))
            data_card.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(data_card, text="Data Management", font=("Segoe UI", 14, "bold"), text_color=self.TEXT).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 10))
            
            ctk.CTkLabel(data_card, text="Clear Download History", font=("Segoe UI", 12), text_color=self.TEXT).grid(row=1, column=0, sticky="w", padx=18, pady=8)
            clear_hist_btn = ctk.CTkButton(data_card, text="Clear History", command=self._clear_history, width=120, fg_color="#ef4444", hover_color="#dc2626", text_color="white")
            clear_hist_btn.grid(row=1, column=1, sticky="e", padx=18, pady=8)
            
            ctk.CTkLabel(data_card, text="Reset Configuration", font=("Segoe UI", 12), text_color=self.TEXT).grid(row=2, column=0, sticky="w", padx=18, pady=8)
            reset_cfg_btn = ctk.CTkButton(data_card, text="Reset", command=self._reset_config, width=120, fg_color=self.CARD, hover_color=self.CARD_BORDER, text_color=self.TEXT, border_width=1, border_color=self.CARD_BORDER)
            reset_cfg_btn.grid(row=2, column=1, sticky="e", padx=18, pady=8)

        if hasattr(self, "history_main_frame"):
            self.history_main_frame.grid_forget()
        self.settings_main_frame.grid(row=0, column=1, sticky="nsew")
        self.settings_main_frame.tkraise()

    def _clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear the download history?"):
            if os.path.exists(HISTORY_FILE):
                try:
                    os.remove(HISTORY_FILE)
                except Exception:
                    pass
            self._total_tracks = 0
            self._refresh_stats()
            if hasattr(self, "history_scroll"):
                for widget in self.history_scroll.winfo_children():
                    widget.destroy()
                lbl = ctk.CTkLabel(self.history_scroll, text="No download history yet", font=("Segoe UI", 14), text_color=self.SUBTEXT)
                lbl.grid(row=0, column=0, pady=20)
            messagebox.showinfo("Success", "Download history cleared.")

    def _on_cookie_browser_change(self, choice):
        """Called when the browser cookie dropdown is changed."""
        self._cookie_browser = choice
        self.save_config()
        if choice == "none":
            self.log("🍪 Browser cookies disabled — will use pasted cookies only")
        else:
            self.log(f"🍪 Browser cookies set to: {choice}")

    def _reset_config(self):
        if messagebox.askyesno("Reset Configuration", "Are you sure you want to reset all settings to default?"):
            if os.path.exists(CONFIG_FILE):
                try:
                    os.remove(CONFIG_FILE)
                except Exception:
                    pass
            self.save_path = os.path.join(os.path.expanduser("~"), "Music", "YT Music Downloads")
            os.makedirs(self.save_path, exist_ok=True)
            self.quality_var.set("Highest Quality (320kbps)")
            if not self.hires_var.get():
                self._toggle_hires()
            self.path_display.configure(state="normal")
            self.path_display.delete(0, "end")
            self.path_display.insert(0, self.save_path)
            self.path_display.configure(state="readonly")
            messagebox.showinfo("Success", "Configuration reset to default.")

    def stop_download(self):
        self.downloading = False
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.log("⚠️  Download stopped by user")
        messagebox.showinfo("Stopped", "Download has been stopped.")

    # ─────────────────────────────── Download logic ───────────────────────────

    class _YDLLogger:
        """Route yt-dlp log messages to the app's Process Log."""
        def __init__(self, app):
            self._app = app
            self._consecutive_bot_errors = 0
            self._max_bot_errors = 5
            self.bot_abort = False

        def debug(self, msg):
            # yt-dlp sends info-level messages via debug when quiet=True
            if msg.startswith('[download]'):
                self._app.after(0, lambda m=msg: self._app.log(m))

        def info(self, msg):
            self._app.after(0, lambda m=msg: self._app.log(m))

        def warning(self, msg):
            self._app.after(0, lambda m=msg: self._app.log(f"⚠️  {m}"))

        def error(self, msg):
            self._app.after(0, lambda m=msg: self._app.log(f"❌ {m}"))
            # Detect bot / sign-in errors and abort after too many consecutive ones
            if "Sign in to confirm" in msg or "bot" in msg.lower():
                self._consecutive_bot_errors += 1
                if self._consecutive_bot_errors >= self._max_bot_errors:
                    self.bot_abort = True
                    self._app.downloading = False
                    self._app.after(0, lambda: self._app.log(
                        f"\n🛑 ABORTED: YouTube requires sign-in (bot detection).\n"
                        f"   {self._consecutive_bot_errors} consecutive tracks were blocked.\n"
                        f"\n"
                        f"   ► Fix: Go to Settings → Browser Cookies and select\n"
                        f"     the browser where you're signed in to YouTube.\n"
                        f"   ► Or paste Netscape cookies in the Premium Access box.\n"))
                    self._app.after(0, lambda: messagebox.showerror(
                        "Authentication Required",
                        "YouTube is blocking downloads (bot detection).\n\n"
                        "Go to Settings → Browser Cookies and select the browser\n"
                        "where you are signed in to YouTube / YouTube Music.\n\n"
                        "This lets yt-dlp use your login session."))
            else:
                self._consecutive_bot_errors = 0

    def _get_cookie_opts(self):
        """Build cookie-related yt-dlp options based on user settings."""
        opts = {}
        # 1. Try browser cookies (preferred — most reliable)
        browser = getattr(self, '_cookie_browser', 'edge')
        if browser and browser != 'none':
            opts['cookiesfrombrowser'] = (browser,)
            self.log(f"🍪 Using cookies from browser: {browser}")
            return opts  # browser cookies take priority, no need for cookie file
        # 2. Fall back to pasted Netscape cookies only when browser is 'none'
        cookie_val = self.cookie_entry.get("1.0", "end").strip()
        default_placeholder = "Paste netscape-formatted cookies..."
        if cookie_val and cookie_val != default_placeholder:
            cookie_file = os.path.join(APP_DATA_FOLDER, "cookies.txt")
            try:
                with open(cookie_file, "w", encoding="utf-8") as f:
                    f.write(cookie_val)
                opts['cookiefile'] = cookie_file
                self.log("🍪 Using pasted Netscape cookies")
            except Exception as e:
                self.log(f"⚠️  Could not write cookie file: {e}")
        return opts

    def download_task(self, urls):
        if not self.is_ffmpeg_installed():
            self.after(0, lambda: self.log("❌ ERROR: FFmpeg is required."))
            self.after(0, lambda: messagebox.showerror("Error", "FFmpeg is required. Please install it."))
            self.after(0, self.update_ffmpeg_status_ui)
            return

        quality_map = {
            "Highest Quality (320kbps)": "320",
            "192kbps (Medium Quality)": "192",
            "128kbps (Standard)":       "128"
        }
        selected_bitrate = quality_map.get(self.quality_var.get(), "320")
        hires_on = self.hires_var.get()
        self.save_config()

        outtmpl = os.path.join(
            self.save_path,
            "%(artist)s/%(title)s.%(ext)s" if self.classify_var.get() else "%(title)s.%(ext)s")

        http_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # Create custom logger to show errors in the Process Log
        ydl_logger = self._YDLLogger(self)

        if hires_on:
            ydl_opts = {
                'format': 'bestaudio[ext=opus]/bestaudio[ext=m4a]/bestaudio/best',
                'postprocessors': [
                    {'key': 'FFmpegMetadata', 'add_chapters': True, 'add_metadata': True},
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}
                ],
                'outtmpl': outtmpl,
                'writethumbnail': True,
                'updatetime': False,
                'overwrites': False,
                'noplaylist': False,
                'quiet': True,
                'ignoreerrors': True,
                'no_warnings': False,
                'progress_hooks': [self.progress_hook],
                'http_headers': http_headers,
                'logger': ydl_logger,
            }
        else:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3',
                     'preferredquality': selected_bitrate},
                    {'key': 'FFmpegMetadata', 'add_chapters': True, 'add_metadata': True},
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}
                ],
                'outtmpl': outtmpl,
                'writethumbnail': True,
                'updatetime': False,
                'overwrites': False,
                'noplaylist': False,
                'quiet': True,
                'ignoreerrors': True,
                'no_warnings': False,
                'progress_hooks': [self.progress_hook],
                'http_headers': http_headers,
                'logger': ydl_logger,
                'postprocessor_args': {
                    'FFmpegExtractAudio': ['-id3v2_version', '3', '-write_id3v1', '1']
                }
            }

        # Inject cookie options
        cookie_opts = self._get_cookie_opts()
        ydl_opts.update(cookie_opts)

        if self.increment_var.get():
            ydl_opts['download_archive'] = ARCHIVE_FILE

        if hires_on:
            self.after(0, lambda: self.log("Starting download in Hi-Res mode (native lossless stream — no re-encode)..."))
        else:
            self.after(0, lambda b=selected_bitrate: self.log(f"Starting download with FULL METADATA (MP3, {b}kbps)..."))

        def _do_download(opts):
            """Run yt-dlp download with locked-file workaround for browser cookies."""
            # On Windows, Edge/Chrome lock their cookie DB while running.
            # yt-dlp uses shutil.copy() which fails on locked files.
            # Workaround: temporarily patch shutil.copyfile to use Win32 API
            # with FILE_SHARE_READ|WRITE|DELETE to read locked files.
            _original_copyfile = shutil.copyfile

            if os.name == 'nt':
                def _patched_copyfile(src, dst, *args, **kwargs):
                    try:
                        return _original_copyfile(src, dst, *args, **kwargs)
                    except PermissionError:
                        # Use Win32 CreateFileW with full sharing to read locked files
                        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                        GENERIC_READ    = 0x80000000
                        FILE_SHARE_ALL  = 0x07  # READ | WRITE | DELETE
                        OPEN_EXISTING   = 3
                        INVALID_HANDLE  = ctypes.c_void_p(-1).value

                        h = kernel32.CreateFileW(
                            str(src), GENERIC_READ, FILE_SHARE_ALL,
                            None, OPEN_EXISTING, 0, None)
                        if h == INVALID_HANDLE:
                            raise ctypes.WinError(ctypes.get_last_error())
                        try:
                            buf_size = 65536
                            buf = ctypes.create_string_buffer(buf_size)
                            bytes_read = ctypes.c_ulong()
                            data = bytearray()
                            while True:
                                ok = kernel32.ReadFile(
                                    h, buf, buf_size,
                                    ctypes.byref(bytes_read), None)
                                if bytes_read.value == 0:
                                    break
                                data.extend(buf[:bytes_read.value])
                                if not ok:
                                    break
                        finally:
                            kernel32.CloseHandle(h)
                        with open(dst, 'wb') as f:
                            f.write(data)
                        return dst
                shutil.copyfile = _patched_copyfile

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    self.after(0, lambda: self.log("Parsing links and extracting metadata..."))
                    ydl.download(urls)
            finally:
                shutil.copyfile = _original_copyfile
            return True

        try:
            _do_download(ydl_opts)
            if self.downloading:
                if self._downloads_this_session > 0:
                    if hires_on:
                        self.after(0, lambda: self.log(f"🎉 All tasks completed! {self._downloads_this_session} file(s) saved in native Hi-Res format."))
                    else:
                        self.after(0, lambda n=self._downloads_this_session: self.log(f"🎉 All tasks completed! {n} MP3(s) saved with full metadata."))
                    self.after(0, lambda: messagebox.showinfo(
                        "Completed", f"{self._downloads_this_session} song(s) downloaded with full metadata!"))
                else:
                    self.after(0, lambda: self.log("⚠️ Download finished but no files were saved. Check errors above."))
                    self.after(0, lambda: messagebox.showwarning(
                        "No Downloads", "No files were downloaded. Check the Process Log for errors."))
            elif ydl_logger.bot_abort:
                pass  # Message already shown by the logger
            else:
                self.after(0, lambda: self.log("Download stopped."))
        except yt_dlp.utils.DownloadCancelled:
            self.after(0, lambda: self.log("🛑 Download cancelled by user."))
        except Exception as e:
            err_str = str(e).lower()
            # Cookie extraction failed (browser locked the DB) — retry without browser cookies
            if 'cookie' in err_str and 'cookiesfrombrowser' in ydl_opts:
                browser = ydl_opts['cookiesfrombrowser'][0] if isinstance(ydl_opts.get('cookiesfrombrowser'), tuple) else '?'
                self.after(0, lambda b=browser: self.log(
                    f"\n⚠️  Could not extract cookies from {b} (browser is running and locked).\n"
                    f"   TIP: Close {b}, then retry. Or paste cookies in the Premium Access box.\n"
                    f"   Retrying without browser cookies...\n"))
                # Remove browser cookie option and retry
                ydl_opts.pop('cookiesfrombrowser', None)
                try:
                    _do_download(ydl_opts)
                    if self.downloading:
                        if self._downloads_this_session > 0:
                            if hires_on:
                                self.after(0, lambda: self.log(f"🎉 Completed! {self._downloads_this_session} file(s) saved in Hi-Res format."))
                            else:
                                self.after(0, lambda n=self._downloads_this_session: self.log(f"🎉 Completed! {n} MP3(s) saved with full metadata."))
                            self.after(0, lambda: messagebox.showinfo(
                                "Completed", f"{self._downloads_this_session} song(s) downloaded!"))
                        else:
                            self.after(0, lambda: self.log("⚠️ Download finished but no files were saved. Check errors above."))
                            self.after(0, lambda: messagebox.showwarning(
                                "No Downloads", "No files were downloaded. Check the Process Log for errors."))
                    elif ydl_logger.bot_abort:
                        pass
                    else:
                        self.after(0, lambda: self.log("Download stopped."))
                except yt_dlp.utils.DownloadCancelled:
                    self.after(0, lambda: self.log("🛑 Download cancelled by user."))
                except Exception as e2:
                    import traceback
                    tb2 = traceback.format_exc()
                    if self.downloading:
                        self.after(0, lambda: self.log(f"❌ Error: {str(e2)}"))
                        self.after(0, lambda t=tb2: self.log(f"   Traceback:\n{t}"))
                        self.after(0, lambda: messagebox.showerror("Error", f"Download failed: {str(e2)}"))
            else:
                import traceback
                tb = traceback.format_exc()
                if self.downloading:
                    self.after(0, lambda: self.log(f"❌ Error: {str(e)}"))
                    self.after(0, lambda t=tb: self.log(f"   Traceback:\n{t}"))
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
        url_text = self.url_text.get().strip()
        if not url_text:
            messagebox.showwarning("Notice", "Please enter a download link!")
            return
        urls = [u.strip() for u in url_text.split("\n") if u.strip()]
        self.downloading = True
        self._speed_samples = []
        self._avg_speed_str = "—"
        self._downloads_this_session = 0
        self._refresh_stats()
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log(f"📥 Starting download for {len(urls)} URL(s)...")
        threading.Thread(target=self.download_task, args=(urls,), daemon=True).start()


if __name__ == "__main__":
    app = YTMusicDownloaderPro()
    app.mainloop()