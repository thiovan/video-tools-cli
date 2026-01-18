# Video Tools CLI

A powerful command-line video processing tool built with Python, FFmpeg, and TDL (Telegram Downloader).

![Version](https://img.shields.io/badge/version-1.4.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

## Features

- **Split Video** - Extract segments from videos using time ranges
- **Join Video** - Concatenate multiple video files into one
- **Compress Video** - Reduce file size with hardware acceleration (NVENC, QSV, AMF)
- **Telegram Support** - Download videos directly from Telegram links
- **Parallel Downloads** - Multi-threaded download for faster speeds
- **Progress Tracking** - Real-time progress bar with ETA
- **Auto-Setup** - Automatically downloads FFmpeg if missing

## Quick Start

### Download Release

Download the latest release from [Releases](../../releases) and run `video-tools.exe`.

### From Source

```bash
# Clone repository
git clone https://github.com/yourusername/video-tools-cli.git
cd video-tools-cli

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Usage

### Main Menu

```
? Select action:
> Split Video
  Join Video
  Compress Video
  ─────────────
  Settings
  Exit
```

### Split Video

Extract time ranges from a video:

```
? Video URL / path: video.mp4
? Output name: clip
? Start Time (HH.MM): 00.05
? End Time (HH.MM): 00.10
```

**Time Format:** `00.30` = 30 minutes, `01.20` = 1 hour 20 minutes

### Join Video

Combine multiple videos:

```
? Video URL / path: video1.mp4
? Second video URL / path: video2.mp4
? Add another video? No
? Output filename: combined.mp4
```

### Compress Video

Reduce file size with auto-detected hardware acceleration:

```
? Video URL / path: large_video.mp4
? Output name: compressed.mp4

→ Encoder: hevc_nvenc (Hardware)
● Compressing video...
[████████████████░░░░] 80% | Elapsed: 00:45 | ETA: 00:11
```

### Settings

Configure application settings:

- **Max Queue** - Maximum items in processing queue
- **Download Connections** - Parallel download connections (1-64)
- **Override Encoding** - Force specific encoder or auto-detect

## Build Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build
python build.py

# Build with release package
python build.py --package
```

Output: `dist/video-tools.exe`

## Configuration

Settings are stored in `.env`:

```env
MAX_QUEUE=4
DOWNLOAD_MAX_CONNECTION=16
OVERRIDE_ENCODING=
```

## Project Structure

```
video-tools-cli/
├── main.py              # CLI entry point
├── build.py             # PyInstaller build script
├── core/
│   ├── config.py        # Configuration
│   ├── ffmpeg_handler.py
│   ├── downloader.py
│   ├── tdl_handler.py
│   └── binary_downloader.py
├── utils/
│   ├── helpers.py
│   └── logger.py
├── tests/
└── .github/workflows/
    └── release.yml      # GitHub Actions
```

## License

MIT License
