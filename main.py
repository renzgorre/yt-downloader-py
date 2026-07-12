#!/usr/bin/env python3
"""YT Downloader v1.2 — aria2c support + redesigned UI."""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import subprocess
import zipfile
import shutil
import json
from io import BytesIO
from pathlib import Path
import urllib.request

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import yt_dlp

# ── Paths ──────────────────────────────────────────────────────────────────────

APP_VERSION = "1.2.0"
APP_DIR    = Path.home() / ".ytdownloader"
FFMPEG_DIR = APP_DIR / "ffmpeg"
ARIA2_DIR  = APP_DIR / "aria2c"
CONFIG_FILE = APP_DIR / "config.json"

for d in (APP_DIR, FFMPEG_DIR, ARIA2_DIR):
    d.mkdir(exist_ok=True)

try:
    YTDLP_VERSION = yt_dlp.version.__version__
except Exception:
    YTDLP_VERSION = "unknown"

# ── Format tables ──────────────────────────────────────────────────────────────

RESOLUTIONS = {
    "Best available": None,
    "4K (2160p)": 2160,
    "2K (1440p)": 1440,
    "1080p":      1080,
    "720p":        720,
    "480p":        480,
    "360p":        360,
    "240p":        240,
    "144p":        144,
}

VIDEO_CONTAINERS   = ["MP4", "MKV", "WebM", "MOV", "AVI"]
AUDIO_FORMATS      = ["MP3", "M4A", "AAC", "FLAC", "OGG", "WAV", "Opus"]
AUDIO_QUALITY_LABELS = ["Best (VBR)", "320 kbps", "256 kbps", "192 kbps",
                         "128 kbps", "96 kbps", "64 kbps"]
AUDIO_QUALITY_VALUES = {
    "Best (VBR)": "0", "320 kbps": "320", "256 kbps": "256",
    "192 kbps": "192", "128 kbps": "128", "96 kbps": "96", "64 kbps": "64",
}
AUDIO_CODEC = {
    "MP3": "mp3", "AAC": "aac", "FLAC": "flac",
    "OGG": "vorbis", "WAV": "wav", "Opus": "opus", "M4A": "m4a",
}
DL_TYPES = ["Video + Audio", "Audio Only", "Video Only"]

# ── Config ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "download_dir":  str(Path.home() / "Downloads"),
        "dl_type":       "Video + Audio",
        "resolution":    "1080p",
        "container":     "MP4",
        "audio_fmt":     "MP3",
        "audio_quality": "Best (VBR)",
        "connections":   "4",
        "use_aria2c":    False,
    }


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _parse_ver(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)

# ── ffmpeg ─────────────────────────────────────────────────────────────────────

def get_ffmpeg_path() -> str | None:
    local = FFMPEG_DIR / "bin" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if local.exists():
        return str(local)
    return shutil.which("ffmpeg")


def download_ffmpeg(log_cb=None) -> bool:
    if sys.platform != "win32":
        return False
    try:
        if log_cb:
            log_cb("Fetching latest ffmpeg release from GitHub...")
        req = urllib.request.Request(
            "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest",
            headers={"User-Agent": "YTDownloader/1.2"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            release = json.loads(r.read())

        asset_url = next(
            (a["browser_download_url"] for a in release.get("assets", [])
             if "win64-gpl.zip" in a.get("name", "") and "shared" not in a.get("name", "")),
            None,
        )
        if not asset_url:
            if log_cb:
                log_cb("✗ Could not find ffmpeg download link.")
            return False

        if log_cb:
            log_cb("Downloading ffmpeg (~80 MB)...")
        req2 = urllib.request.Request(asset_url, headers={"User-Agent": "YTDownloader/1.2"})
        with urllib.request.urlopen(req2, timeout=180) as r:
            data = r.read()

        if log_cb:
            log_cb("Extracting...")
        bin_dir = FFMPEG_DIR / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(BytesIO(data)) as z:
            for member in z.namelist():
                fname = Path(member).name
                if fname in ("ffmpeg.exe", "ffprobe.exe"):
                    (bin_dir / fname).write_bytes(z.read(member))

        if log_cb:
            log_cb("✓ ffmpeg installed.")
        return True
    except Exception as e:
        if log_cb:
            log_cb(f"✗ ffmpeg failed: {e}")
        return False

# ── aria2c ─────────────────────────────────────────────────────────────────────

def get_aria2c_path() -> str | None:
    local = ARIA2_DIR / ("aria2c.exe" if sys.platform == "win32" else "aria2c")
    if local.exists():
        return str(local)
    return shutil.which("aria2c")


def download_aria2c(log_cb=None) -> bool:
    if sys.platform != "win32":
        return False
    try:
        if log_cb:
            log_cb("Fetching latest aria2c release from GitHub...")
        req = urllib.request.Request(
            "https://api.github.com/repos/aria2/aria2/releases/latest",
            headers={"User-Agent": "YTDownloader/1.2"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            release = json.loads(r.read())

        asset_url = next(
            (a["browser_download_url"] for a in release.get("assets", [])
             if "win-64bit" in a.get("name", "") and a["name"].endswith(".zip")),
            None,
        )
        if not asset_url:
            if log_cb:
                log_cb("✗ Could not find aria2c download link.")
            return False

        if log_cb:
            log_cb("Downloading aria2c (~3 MB)...")
        req2 = urllib.request.Request(asset_url, headers={"User-Agent": "YTDownloader/1.2"})
        with urllib.request.urlopen(req2, timeout=60) as r:
            data = r.read()

        if log_cb:
            log_cb("Extracting aria2c.exe...")
        with zipfile.ZipFile(BytesIO(data)) as z:
            for member in z.namelist():
                if Path(member).name == "aria2c.exe":
                    (ARIA2_DIR / "aria2c.exe").write_bytes(z.read(member))
                    break

        if log_cb:
            log_cb("✓ aria2c installed.")
        return True
    except Exception as e:
        if log_cb:
            log_cb(f"✗ aria2c failed: {e}")
        return False

# ── yt-dlp update ──────────────────────────────────────────────────────────────

def get_ytdlp_latest() -> str | None:
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/yt-dlp/json",
            headers={"User-Agent": "YTDownloader/1.2"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())["info"]["version"]
    except Exception:
        return None


def run_ytdlp_update(log_cb=None) -> bool:
    try:
        if log_cb:
            log_cb("Running pip install -U yt-dlp ...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "--quiet"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            if log_cb:
                log_cb("✓ yt-dlp updated. Restart to apply.")
            return True
        if log_cb:
            log_cb(f"✗ {result.stderr.strip()[:300]}")
        return False
    except Exception as e:
        if log_cb:
            log_cb(f"✗ {e}")
        return False

# ── yt-dlp opts builder ────────────────────────────────────────────────────────

def build_ydl_opts(
    dl_type: str, resolution: str, container: str,
    audio_fmt: str, audio_quality: str,
    output_dir: str, ffmpeg_path: str | None,
    connections: int = 4,
    use_aria2c: bool = False, aria2c_path: str | None = None,
) -> dict:
    height = RESOLUTIONS.get(resolution)

    opts: dict = {
        "outtmpl":    str(Path(output_dir) / "%(title)s.%(ext)s"),
        "quiet":      True,
        "no_warnings": True,
    }
    if ffmpeg_path:
        opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)

    # Downloader
    if use_aria2c and aria2c_path:
        # Must be the literal name "aria2c" so yt-dlp activates Aria2cFD,
        # which handles cookie/header forwarding. The binary is found via PATH
        # (we prepend the directory in Downloader.download before calling yt-dlp).
        opts["external_downloader"] = "aria2c"
        opts["external_downloader_args"] = {
            "aria2c": [
                f"-x{connections}",  # max connections per server
                "-k", "1M",          # min split size per piece
                "--retry-wait=3",
                "--max-tries=5",
            ]
        }
    else:
        opts["concurrent_fragment_downloads"] = connections
        opts["http_chunk_size"] = 10 * 1024 * 1024

    # Format
    if dl_type == "Video + Audio":
        if height:
            opts["format"] = (
                f"bestvideo[height<={height}]+bestaudio"
                f"/bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            )
        else:
            opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = container.lower()

    elif dl_type == "Audio Only":
        if audio_fmt == "M4A":
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        else:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": AUDIO_CODEC.get(audio_fmt, "mp3"),
                "preferredquality": AUDIO_QUALITY_VALUES.get(audio_quality, "0"),
            }]

    elif dl_type == "Video Only":
        opts["format"] = f"bestvideo[height<={height}]" if height else "bestvideo"
        opts["merge_output_format"] = container.lower()

    return opts

# ── Downloader ─────────────────────────────────────────────────────────────────

class Downloader:
    def __init__(self):
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def get_info(self, url: str, ffmpeg_path: str | None) -> dict:
        opts: dict = {"quiet": True, "no_warnings": True, "skip_download": True}
        if ffmpeg_path:
            opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def download(self, url: str, ydl_opts: dict, progress_cb=None, done_cb=None,
                 aria2c_path: str | None = None):
        self._cancelled.clear()

        # Inject aria2c's directory into PATH so yt-dlp's Aria2cFD can find it
        _old_path = None
        if aria2c_path and ydl_opts.get("external_downloader") == "aria2c":
            aria2c_dir = str(Path(aria2c_path).parent)
            _old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = aria2c_dir + os.pathsep + _old_path

        def hook(d):
            if self._cancelled.is_set():
                raise yt_dlp.utils.DownloadError("Cancelled")
            if d["status"] == "downloading" and progress_cb:
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done  = d.get("downloaded_bytes", 0)
                speed = d.get("speed") or 0
                eta   = d.get("eta") or 0
                pct   = (done / total * 100) if total else 0
                spd   = f"{speed / 1048576:.1f} MB/s" if speed else "—"
                progress_cb(pct, f"{pct:.0f}%  ·  {spd}  ·  ETA {eta}s")
            elif d["status"] == "finished" and progress_cb:
                progress_cb(99, "Merging / converting...")

        try:
            with yt_dlp.YoutubeDL({**ydl_opts, "progress_hooks": [hook]}) as ydl:
                ydl.download([url])
            if not self._cancelled.is_set():
                if done_cb:
                    done_cb(True, "Download complete!")
            else:
                if done_cb:
                    done_cb(False, "Cancelled.")
        except Exception as e:
            msg = str(e)
            if done_cb:
                done_cb(False, "Cancelled." if "Cancelled" in msg else f"Error: {msg[:180]}")
        finally:
            if _old_path is not None:
                os.environ["PATH"] = _old_path

# ── Theme ──────────────────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

C_RED   = "#e74c3c";  C_RED_H  = "#c0392b"
C_ORG   = "#e67e22";  C_ORG_H  = "#ca6f1e"
C_GRN   = "#27ae60";  C_GRN_H  = "#1e8449"
C_SURF  = ("gray92", "#2b2b2b")
C_BORDER = ("gray80", "#3a3a3a")
C_DIM   = ("gray50", "gray55")


def _label(parent, text, size=12, weight="normal", color=None, **kw):
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(size=size, weight=weight),
        text_color=color or ("gray10", "gray90"), **kw,
    )


def _ghost_btn(parent, text, command, width=None, height=32, **kw):
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width or 0, height=height,
        fg_color="transparent", border_width=1, border_color=C_BORDER,
        text_color=("gray20", "gray85"), hover_color=("gray85", "#383838"),
        corner_radius=8, **kw,
    )


def _solid_btn(parent, text, command, color=C_RED, hover=C_RED_H,
               width=None, height=36, font_size=13, **kw):
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width or 0, height=height,
        fg_color=color, hover_color=hover,
        corner_radius=8, font=ctk.CTkFont(size=font_size, weight="bold"), **kw,
    )

# ── App ────────────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg         = load_config()
        self.ffmpeg_path = get_ffmpeg_path()
        self.aria2c_path = get_aria2c_path()
        self.dl          = Downloader()
        self._thumb_ref  = None

        self.title(f"YT Downloader  v{APP_VERSION}")
        self.geometry("740x820")
        self.minsize(660, 700)
        self._build()
        self.after(500, lambda: threading.Thread(target=self._startup, daemon=True).start())

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        ctk.CTkLabel(f, text="▶", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C_RED).pack(side="left")
        ctk.CTkLabel(f, text=" YT Downloader",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkLabel(f, text=f"  v{APP_VERSION}",
                     font=ctk.CTkFont(size=11), text_color=C_DIM).pack(side="left", pady=(4, 0))

    def _build_body(self):
        body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                       scrollbar_button_color=C_BORDER)
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        body.grid_columnconfigure(0, weight=1)
        self._build_url_section(body)
        self._build_info_card(body)
        self._build_options_section(body)
        self._build_saveto(body)
        self._build_progress(body)
        self._build_dl_buttons(body)
        self._build_log(body)

    # ── URL ────────────────────────────────────────────────────────────────────

    def _build_url_section(self, parent):
        card = self._card(parent, pady=(0, 10))
        _label(card, "YouTube URL", size=12, weight="bold").pack(anchor="w", padx=14, pady=(12, 4))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 14))
        row.grid_columnconfigure(0, weight=1)

        self.url_var = tk.StringVar()
        self.url_entry = ctk.CTkEntry(
            row, textvariable=self.url_var, height=40, corner_radius=8,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=ctk.CTkFont(size=12),
        )
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self.url_entry.bind("<Return>", lambda _: self._fetch())

        _ghost_btn(row, "Paste", self._paste, width=70, height=40).grid(row=0, column=1, padx=(6, 0))
        self.fetch_btn = _solid_btn(row, "Fetch  ▶", self._fetch, width=96, height=40, font_size=12)
        self.fetch_btn.grid(row=0, column=2, padx=(6, 0))

    # ── Video info ─────────────────────────────────────────────────────────────

    def _build_info_card(self, parent):
        card = self._card(parent, pady=(0, 10))
        card.grid_columnconfigure(1, weight=1)

        self.thumb = ctk.CTkLabel(
            card, text="No video\nloaded yet", width=160, height=90,
            fg_color=("#ddd", "#333"), corner_radius=8,
            text_color=C_DIM, font=ctk.CTkFont(size=11),
        )
        self.thumb.grid(row=0, column=0, rowspan=2, padx=14, pady=14)

        self.v_title = ctk.CTkLabel(
            card, text="—", anchor="w", justify="left", wraplength=430,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.v_title.grid(row=0, column=1, sticky="sw", padx=(4, 14), pady=(16, 2))

        self.v_meta = ctk.CTkLabel(
            card, text="", anchor="w", justify="left",
            font=ctk.CTkFont(size=11), text_color=C_DIM,
        )
        self.v_meta.grid(row=1, column=1, sticky="nw", padx=(4, 14), pady=(0, 16))

    # ── Options ────────────────────────────────────────────────────────────────

    def _build_options_section(self, parent):
        card = self._card(parent, pady=(0, 10))
        _label(card, "Download Options", size=12, weight="bold").pack(anchor="w", padx=14, pady=(12, 8))

        # Row 1: type + connections + aria2c toggle
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=14, pady=(0, 10))

        _label(r1, "Type", size=11, color=C_DIM).pack(side="left", padx=(0, 8))
        self.dl_type_var = tk.StringVar(value=self.cfg.get("dl_type", "Video + Audio"))
        self.type_seg = ctk.CTkSegmentedButton(
            r1, values=DL_TYPES, variable=self.dl_type_var,
            command=self._on_type_change,
            height=34, font=ctk.CTkFont(size=12), corner_radius=8,
        )
        self.type_seg.pack(side="left")

        _label(r1, "Connections", size=11, color=C_DIM).pack(side="left", padx=(20, 8))
        self.conn_var = tk.StringVar(value=self.cfg.get("connections", "4"))
        ctk.CTkOptionMenu(
            r1, variable=self.conn_var,
            values=["1", "2", "4", "8", "16"],
            width=72, height=34, corner_radius=8,
        ).pack(side="left")

        # aria2c switch
        _label(r1, "aria2c", size=11, color=C_DIM).pack(side="left", padx=(20, 6))
        self.aria2c_var = tk.BooleanVar(value=self.cfg.get("use_aria2c", False))
        self.aria2c_switch = ctk.CTkSwitch(
            r1, text="", variable=self.aria2c_var,
            width=44, height=22,
            state="normal" if self.aria2c_path else "disabled",
        )
        self.aria2c_switch.pack(side="left")

        # show status badge next to switch
        self.aria2c_badge = _label(
            r1,
            "installed" if self.aria2c_path else "not installed",
            size=10,
            color=C_GRN if self.aria2c_path else C_DIM,
        )
        self.aria2c_badge.pack(side="left", padx=(4, 0))

        # Row 2: video opts (resolution + container)
        self.video_opts = ctk.CTkFrame(card, fg_color="transparent")
        _label(self.video_opts, "Resolution", size=11, color=C_DIM).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.res_var = tk.StringVar(value=self.cfg.get("resolution", "1080p"))
        ctk.CTkOptionMenu(
            self.video_opts, variable=self.res_var,
            values=list(RESOLUTIONS.keys()), width=180, height=34, corner_radius=8,
        ).grid(row=0, column=1, padx=(0, 24))
        _label(self.video_opts, "Container", size=11, color=C_DIM).grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.container_var = tk.StringVar(value=self.cfg.get("container", "MP4"))
        ctk.CTkOptionMenu(
            self.video_opts, variable=self.container_var,
            values=VIDEO_CONTAINERS, width=120, height=34, corner_radius=8,
        ).grid(row=0, column=3)

        # Row 2 (alt): audio opts (format + quality)
        self.audio_opts = ctk.CTkFrame(card, fg_color="transparent")
        _label(self.audio_opts, "Format", size=11, color=C_DIM).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.audio_fmt_var = tk.StringVar(value=self.cfg.get("audio_fmt", "MP3"))
        ctk.CTkOptionMenu(
            self.audio_opts, variable=self.audio_fmt_var,
            values=AUDIO_FORMATS, width=130, height=34, corner_radius=8,
        ).grid(row=0, column=1, padx=(0, 24))
        _label(self.audio_opts, "Quality", size=11, color=C_DIM).grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.audio_quality_var = tk.StringVar(value=self.cfg.get("audio_quality", "Best (VBR)"))
        ctk.CTkOptionMenu(
            self.audio_opts, variable=self.audio_quality_var,
            values=AUDIO_QUALITY_LABELS, width=150, height=34, corner_radius=8,
        ).grid(row=0, column=3)

        ctk.CTkFrame(card, fg_color="transparent", height=10).pack()
        self._on_type_change(self.dl_type_var.get())

    def _on_type_change(self, val: str):
        if val == "Audio Only":
            self.video_opts.pack_forget()
            self.audio_opts.pack(fill="x", padx=14, pady=(0, 4))
        else:
            self.audio_opts.pack_forget()
            self.video_opts.pack(fill="x", padx=14, pady=(0, 4))

    # ── Save-to ────────────────────────────────────────────────────────────────

    def _build_saveto(self, parent):
        card = self._card(parent, pady=(0, 10))
        _label(card, "Save To", size=12, weight="bold").pack(anchor="w", padx=14, pady=(12, 6))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 14))
        row.grid_columnconfigure(0, weight=1)

        self.dir_var = tk.StringVar(value=self.cfg.get("download_dir", str(Path.home() / "Downloads")))
        ctk.CTkEntry(row, textvariable=self.dir_var, height=36, corner_radius=8,
                     font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="ew")
        _ghost_btn(row, "Browse", self._pick_dir, width=80, height=36).grid(row=0, column=1, padx=(8, 0))
        _ghost_btn(row, "Open ↗", lambda: os.startfile(self.dir_var.get()),
                   width=76, height=36).grid(row=0, column=2, padx=(6, 0))

    # ── Progress ───────────────────────────────────────────────────────────────

    def _build_progress(self, parent):
        card = self._card(parent, pady=(0, 10))
        self.progress = ctk.CTkProgressBar(card, height=10, corner_radius=5)
        self.progress.pack(fill="x", padx=14, pady=(14, 4))
        self.progress.set(0)
        self.prog_lbl = ctk.CTkLabel(card, text="Ready",
                                      font=ctk.CTkFont(size=11), text_color=C_DIM)
        self.prog_lbl.pack(anchor="w", padx=14, pady=(0, 12))

    # ── Buttons ────────────────────────────────────────────────────────────────

    def _build_dl_buttons(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))
        row.grid_columnconfigure(0, weight=1)

        self.dl_btn = _solid_btn(row, "  ⬇   Download", self._start_dl,
                                  height=48, font_size=15)
        self.dl_btn.grid(row=0, column=0, sticky="ew")

        self.cancel_btn = _ghost_btn(row, "✕  Cancel", self._cancel_dl,
                                      width=110, height=48)
        self.cancel_btn.configure(state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(10, 0))

    # ── Log ────────────────────────────────────────────────────────────────────

    def _build_log(self, parent):
        _label(parent, "Activity log", size=11, color=C_DIM).pack(anchor="w", pady=(0, 4))
        self.log_box = ctk.CTkTextbox(
            parent, height=130, corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled", wrap="word",
            border_width=1, border_color=C_BORDER,
        )
        self.log_box.pack(fill="both", expand=True)

    # ── Footer ─────────────────────────────────────────────────────────────────

    def _build_footer(self):
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 14))
        foot.grid_columnconfigure(3, weight=1)

        self.ytdlp_btn = _ghost_btn(foot, "Update yt-dlp", self._do_update_ytdlp,
                                     width=140, height=30)
        self.ytdlp_btn.grid(row=0, column=0)

        self.ffmpeg_btn = _ghost_btn(foot, "ffmpeg  ✓" if self.ffmpeg_path else "Install ffmpeg",
                                      self._do_install_ffmpeg, width=140, height=30)
        if self.ffmpeg_path:
            self.ffmpeg_btn.configure(fg_color=C_GRN, hover_color=C_GRN_H,
                                       border_width=0, text_color="white")
        self.ffmpeg_btn.grid(row=0, column=1, padx=(8, 0))

        self.aria2c_btn = _ghost_btn(foot, "aria2c  ✓" if self.aria2c_path else "Install aria2c",
                                      self._do_install_aria2c, width=140, height=30)
        if self.aria2c_path:
            self.aria2c_btn.configure(fg_color=C_GRN, hover_color=C_GRN_H,
                                       border_width=0, text_color="white")
        self.aria2c_btn.grid(row=0, column=2, padx=(8, 0))

        ctk.CTkLabel(foot, text=f"yt-dlp  {YTDLP_VERSION}",
                     font=ctk.CTkFont(size=10), text_color=C_DIM).grid(row=0, column=4, sticky="e")

    # ── Card helper ────────────────────────────────────────────────────────────

    def _card(self, parent, pady=(0, 0)):
        return ctk.CTkFrame(parent, corner_radius=10, border_width=1, border_color=C_BORDER,
                            **{"pack_propagate": False} if False else {})

    # Actually need to pack the card, not return unpacked
    def _card(self, parent, pady=(0, 0)):
        f = ctk.CTkFrame(parent, corner_radius=10, border_width=1, border_color=C_BORDER)
        f.pack(fill="x", pady=pady)
        return f

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        def _do():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _do)

    def _paste(self):
        try:
            self.url_var.set(self.clipboard_get().strip())
        except Exception:
            pass

    def _pick_dir(self):
        path = filedialog.askdirectory(initialdir=self.dir_var.get())
        if path:
            self.dir_var.set(path)

    def _save_prefs(self):
        self.cfg.update({
            "download_dir":  self.dir_var.get(),
            "dl_type":       self.dl_type_var.get(),
            "resolution":    self.res_var.get(),
            "container":     self.container_var.get(),
            "audio_fmt":     self.audio_fmt_var.get(),
            "audio_quality": self.audio_quality_var.get(),
            "connections":   self.conn_var.get(),
            "use_aria2c":    self.aria2c_var.get(),
        })
        save_config(self.cfg)

    # ── Startup checks ─────────────────────────────────────────────────────────

    def _startup(self):
        if self.ffmpeg_path:
            self._log(f"✓ ffmpeg: {Path(self.ffmpeg_path).parent}")
        else:
            self._log("⚠  ffmpeg not found — HD video and MP3 export require it.")
            self.after(0, lambda: self.ffmpeg_btn.configure(
                fg_color=C_ORG, hover_color=C_ORG_H, border_width=0, text_color="white"))

        if self.aria2c_path:
            self._log(f"✓ aria2c: {self.aria2c_path}")
        else:
            self._log("ℹ  aria2c not installed — click 'Install aria2c' for faster downloads.")

        latest = get_ytdlp_latest()
        if latest and _parse_ver(latest) > _parse_ver(YTDLP_VERSION):
            self._log(f"ℹ  yt-dlp update available: {YTDLP_VERSION} → {latest}")
            self.after(0, lambda: self.ytdlp_btn.configure(
                fg_color=C_ORG, hover_color=C_ORG_H, border_width=0,
                text_color="white", text=f"Update yt-dlp  ({latest})"))
        else:
            self._log(f"✓ yt-dlp {YTDLP_VERSION} is up to date")
            self.after(0, lambda: self.ytdlp_btn.configure(
                text=f"yt-dlp  ✓  up to date",
                fg_color=C_GRN, hover_color=C_GRN_H,
                border_width=0, text_color="white"))

    # ── Fetch ──────────────────────────────────────────────────────────────────

    def _fetch(self):
        url = self.url_var.get().strip()
        if not url:
            return
        self._log(f"Fetching: {url}")
        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.thumb.configure(image=None, text="Loading...", fg_color=("#ddd", "#333"))

        def run():
            try:
                info = self.dl.get_info(url, self.ffmpeg_path)
                title    = info.get("title", "Unknown")
                uploader = info.get("uploader") or info.get("channel", "")
                dur      = int(info.get("duration") or 0)
                h, rem   = divmod(dur, 3600)
                m, s     = divmod(rem, 60)
                dur_str  = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                views    = info.get("view_count")
                parts    = [p for p in [uploader, dur_str, f"{views:,} views" if views else ""] if p]

                self.after(0, lambda: self.v_title.configure(text=title))
                self.after(0, lambda: self.v_meta.configure(text="  ·  ".join(parts)))
                self._log(f"✓ {title}")

                thumbs    = info.get("thumbnails") or []
                thumb_url = next((t["url"] for t in reversed(thumbs) if t.get("url")), None)
                if thumb_url and PIL_AVAILABLE:
                    try:
                        req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=10) as r:
                            data = r.read()
                        img  = Image.open(BytesIO(data)).resize((160, 90), Image.LANCZOS)
                        cimg = ctk.CTkImage(img, img, size=(160, 90))
                        self._thumb_ref = cimg
                        self.after(0, lambda: self.thumb.configure(image=cimg, text="",
                                                                    fg_color="transparent"))
                    except Exception:
                        self.after(0, lambda: self.thumb.configure(text="No preview",
                                                                    fg_color=("#ddd", "#333")))
                else:
                    self.after(0, lambda: self.thumb.configure(text="No preview",
                                                                fg_color=("#ddd", "#333")))
            except Exception as e:
                self._log(f"✗ {e}")
                self.after(0, lambda: self.thumb.configure(text="Error", fg_color=("#ddd", "#333")))
            finally:
                self.after(0, lambda: self.fetch_btn.configure(state="normal", text="Fetch  ▶"))

        threading.Thread(target=run, daemon=True).start()

    # ── Download ───────────────────────────────────────────────────────────────

    def _start_dl(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("Paste a URL first.")
            return
        out = self.dir_var.get()
        if not os.path.isdir(out):
            self._log(f"Folder not found: {out}")
            return

        self._save_prefs()
        dl_type    = self.dl_type_var.get()
        res        = self.res_var.get()
        cont       = self.container_var.get()
        afmt       = self.audio_fmt_var.get()
        aqual      = self.audio_quality_var.get()
        conns      = int(self.conn_var.get())
        use_aria2c = self.aria2c_var.get() and bool(self.aria2c_path)

        ydl_opts = build_ydl_opts(
            dl_type, res, cont, afmt, aqual, out,
            self.ffmpeg_path, conns, use_aria2c, self.aria2c_path,
        )

        downloader_tag = f"aria2c  x{conns}" if use_aria2c else f"yt-dlp  x{conns}"
        desc = (f"{dl_type}  ·  {afmt} {aqual}" if dl_type == "Audio Only"
                else f"{dl_type}  ·  {res}  ·  {cont}")
        self._log(f"Starting: {desc}  [{downloader_tag}]")

        self.dl_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")

        if use_aria2c:
            # aria2c runs as an opaque subprocess — yt-dlp gives no per-fragment
            # progress events, so use an animated indeterminate bar instead.
            self.progress.configure(mode="indeterminate")
            self.progress.start()
            self.prog_lbl.configure(text="Downloading via aria2c…")
        else:
            self.progress.set(0)
            self.prog_lbl.configure(text="Starting…")

        def on_prog(pct, msg):
            if not use_aria2c:
                self.after(0, lambda: self.progress.set(pct / 100))
                self.after(0, lambda: self.prog_lbl.configure(text=msg))

        def on_done(ok, msg):
            def _restore():
                self.progress.stop()
                self.progress.configure(mode="determinate")
                self.progress.set(1.0 if ok else 0)
                self.prog_lbl.configure(text=msg)
                self.dl_btn.configure(state="normal")
                self.cancel_btn.configure(state="disabled")
            self.after(0, _restore)
            self._log(("✓ " if ok else "✗ ") + msg)

        threading.Thread(
            target=self.dl.download,
            args=(url, ydl_opts, on_prog, on_done),
            kwargs={"aria2c_path": self.aria2c_path if use_aria2c else None},
            daemon=True,
        ).start()

    def _cancel_dl(self):
        self.dl.cancel()
        self._log("Cancelling...")
        self.cancel_btn.configure(state="disabled")

    # ── yt-dlp update ──────────────────────────────────────────────────────────

    def _do_update_ytdlp(self):
        self.ytdlp_btn.configure(state="disabled", text="Updating...")
        def run():
            run_ytdlp_update(self._log)
            # Restore button to default ghost style regardless of update outcome
            self.after(0, lambda: self.ytdlp_btn.configure(
                state="normal", text="yt-dlp  ✓  (restart to apply)",
                fg_color="transparent",
                border_width=1, border_color=C_BORDER,
                text_color=("gray20", "gray85"),
                hover_color=("gray85", "#383838"),
            ))
        threading.Thread(target=run, daemon=True).start()

    # ── ffmpeg install ─────────────────────────────────────────────────────────

    def _do_install_ffmpeg(self):
        if sys.platform != "win32":
            messagebox.showinfo("Install ffmpeg",
                "macOS:   brew install ffmpeg\nUbuntu:  sudo apt install ffmpeg")
            return
        self.ffmpeg_btn.configure(state="disabled", text="Downloading...")
        def run():
            ok = download_ffmpeg(self._log)
            if ok:
                self.ffmpeg_path = get_ffmpeg_path()
                self.after(0, lambda: self.ffmpeg_btn.configure(
                    state="normal", text="ffmpeg  ✓",
                    fg_color=C_GRN, hover_color=C_GRN_H, border_width=0, text_color="white"))
            else:
                self.after(0, lambda: self.ffmpeg_btn.configure(
                    state="normal", text="Install ffmpeg"))
        threading.Thread(target=run, daemon=True).start()

    # ── aria2c install ─────────────────────────────────────────────────────────

    def _do_install_aria2c(self):
        if sys.platform != "win32":
            messagebox.showinfo("Install aria2c",
                "macOS:   brew install aria2\nUbuntu:  sudo apt install aria2")
            return
        self.aria2c_btn.configure(state="disabled", text="Downloading...")
        def run():
            ok = download_aria2c(self._log)
            if ok:
                self.aria2c_path = get_aria2c_path()
                self.after(0, lambda: self.aria2c_btn.configure(
                    state="normal", text="aria2c  ✓",
                    fg_color=C_GRN, hover_color=C_GRN_H, border_width=0, text_color="white"))
                self.after(0, lambda: self.aria2c_switch.configure(state="normal"))
                self.after(0, lambda: self.aria2c_badge.configure(
                    text="installed", text_color=C_GRN))
            else:
                self.after(0, lambda: self.aria2c_btn.configure(
                    state="normal", text="Install aria2c"))
        threading.Thread(target=run, daemon=True).start()


# ── Entry ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    App().mainloop()
