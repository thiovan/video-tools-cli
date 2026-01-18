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

![Version](https://img.shields.io/badge/version-1.6.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

A powerful command-line video processing tool with parallel processing support.

## Features

- **Split Video** - Extract segments with parallel processing
- **Join Video** - Concatenate multiple videos
- **Split & Join** - Split segments and merge into one file
- **Compress Video** - Reduce file size with 3 quality levels
- **Telegram Support** - Download from Telegram links
- **Parallel Processing** - Multi-threaded operations based on queue setting
- **Auto-Setup** - Downloads FFmpeg automatically

## Quick Start

### Download Release

[Download latest release](../../releases) and run `video-tools.exe`

### From Source

```bash
git clone https://github.com/yourusername/video-tools-cli.git
cd video-tools-cli
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Usage

### Main Menu

```
? Select action:
> Split Video
  Join Video
  Split & Join Video    ← NEW
  Compress Video
  ─────────────
  Settings
  Exit
```

### Compression Levels

| Level      | Quality  | Speed  | Use Case       |
| ---------- | -------- | ------ | -------------- |
| **Low**    | Lower    | Fast   | Quick previews |
| **Medium** | Balanced | Normal | General use    |
| **High**   | Best     | Slow   | Final output   |

### Parallel Processing

Set **Max Queue** in Settings to control parallel workers:

- Queue = 2: Process 2 files simultaneously
- Queue = 4: Process 4 files simultaneously

### Input Types

- **Single file**: `C:\Videos\video.mp4`
- **Folder**: `C:\Videos\MyFolder` (processes all videos)
- **Multiple files**: Drag & drop multiple files
- **URL**: Direct video links
- **Telegram**: `https://t.me/...` links

## Build

```bash
pip install pyinstaller
python build.py
```

### With Icon

Place `icon.ico` in `assets/` folder before building.

## Configuration

Settings stored in `.env`:

| Variable                  | Default  | Description                 |
| ------------------------- | -------- | --------------------------- |
| `MAX_QUEUE`               | `2`      | Parallel processing workers |
| `DOWNLOAD_MAX_CONNECTION` | `4`      | Download connections        |
| `COMPRESSION_LEVEL`       | `medium` | low/medium/high             |
| `OVERRIDE_ENCODING`       | _(auto)_ | Force encoder               |

## Testing

```bash
# Unit tests
pytest tests/

# Exe integration tests
python tests/test_exe.py dist/video-tools.exe
```

## License

MIT License
