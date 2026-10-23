# YT Downloader

A desktop app for downloading YouTube videos and audio, built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) with a clean CustomTkinter interface.

## Features

- **Three download modes:** video with audio, audio only, or video only
- **Resolution control** from 480p up to 4K, or best available
- **Video containers:** MP4, MKV, WebM, MOV, AVI
- **Audio formats:** MP3, M4A, AAC, FLAC, OGG, WAV, Opus, with selectable bitrate
- **Faster downloads** through parallel fragments, or optional [aria2c](https://aria2.github.io/) with up to 16 connections
- **One-click setup** of ffmpeg and aria2c from inside the app (Windows)
- **Built-in yt-dlp updater** that checks for new versions on launch
- Remembers your settings and save folder between sessions

## Download

Windows builds are published on the [Releases](../../releases) page:

| File | Description |
| --- | --- |
| `YT-Downloader-Setup.exe` | Installer with Start Menu and Desktop shortcuts and an uninstaller |
| `YT Downloader.exe` | Portable single file, no installation needed |

On first launch, click **Install ffmpeg** (needed for HD merging and audio conversion) and optionally **Install aria2c**.

## Running from source

Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
python main.py
```

On Windows you can also run `run.bat`, which installs the dependencies and starts the app.

On macOS and Linux, install `ffmpeg` (and `aria2c` if you want it) with your package manager. The in-app installers are Windows only.

## Building

Releases are built automatically by GitHub Actions when a `v*` tag is pushed. See [`.github/workflows/release.yml`](.github/workflows/release.yml). To build locally on Windows:

```bash
pip install -r requirements.txt pyinstaller
python generate_assets.py
pyinstaller --onefile --windowed --name "YT Downloader" --icon "assets\icon.ico" --collect-all customtkinter --collect-all yt_dlp --hidden-import PIL._tkinter_finder main.py
makensis installer.nsi
```

## Project structure

| Path | Purpose |
| --- | --- |
| `main.py` | The application: UI, download logic, ffmpeg and aria2c setup |
| `generate_assets.py` | Generates the app icon and installer banner |
| `installer.nsi` | NSIS script for the Windows installer |
| `run.bat` | Convenience launcher for Windows |

## License

[MIT](LICENSE.txt)
