# Video Tools CLI

```
       _      _             _             _
      (_)    | |           | |           | |
 __   ___  __| | ___  ___  | |_ ___   ___| |___
 \ \ / / |/ _` |/ _ \/ _ \ | __/ _ \ / _ \ / __|
  \ V /| | (_| |  __/ (_) || || (_) | (_) | \__ \
   \_/ |_|\__,_|\___|\___/  \__\___/ \___/|_|___/

        Video Processing Made Easy
```

![Version](https://img.shields.io/badge/version-1.4.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

A powerful command-line video processing tool built with Python, FFmpeg, and TDL (Telegram Downloader).

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

Download the latest release from [Releases](../../releases):

```
video-tools-v1.4.0-win64.zip
├── video-tools.exe
├── bin/
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── tdl.exe
└── README.md
```

Just extract and run `video-tools.exe`!

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

```
? Video URL / path: video.mp4
? Output name: clip
? Start Time (HH.MM): 00.05   → 5 minutes
? End Time (HH.MM): 00.10     → 10 minutes
```

### Join Video

```
? Video URL / path: video1.mp4
? Second video URL / path: video2.mp4
? Add another video? No
? Output filename: combined.mp4
```

### Compress Video

```
? Video URL / path: large_video.mp4
? Output name: compressed.mp4

→ Encoder: hevc_nvenc (Hardware)
● Compressing video...
[████████████████░░░░] 80% | Elapsed: 00:45 | ETA: 00:11
```

## Build Executable

```bash
pip install pyinstaller
python build.py
```

Output: `dist/video-tools.exe` (~10MB)

## Configuration

Settings stored in `.env` (created automatically):

| Variable                  | Description          | Default  |
| ------------------------- | -------------------- | -------- |
| `MAX_QUEUE`               | Max items in queue   | `4`      |
| `DOWNLOAD_MAX_CONNECTION` | Parallel connections | `16`     |
| `OVERRIDE_ENCODING`       | Force encoder        | `(auto)` |

## Project Structure

```
video-tools-cli/
├── video-tools.exe      # Built executable
├── bin/                 # FFmpeg, TDL binaries
├── cache/               # Temporary processing files
├── .env                 # Configuration
├── main.py
├── build.py
├── core/
│   ├── config.py
│   ├── ffmpeg_handler.py
│   ├── downloader.py
│   └── tdl_handler.py
└── utils/
    ├── helpers.py
    └── logger.py
```

## License

MIT License
