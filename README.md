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

| Feature               | Description                               |
| --------------------- | ----------------------------------------- |
| **Split Video**       | Extract segments with parallel processing |
| **Join Video**        | Concatenate multiple videos               |
| **Split & Join**      | Split segments and merge into one file    |
| **Compress Video**    | 3 quality levels (low/medium/high)        |
| **Telegram**          | Download from Telegram links              |
| **Parallel Download** | Multi-threaded chunked downloads          |
| **Folder Input**      | Process all videos in a folder            |

## Quick Start

### Download Release

[Download latest release](../../releases) → Extract → Run `video-tools.exe`

### From Source

```bash
git clone https://github.com/yourusername/video-tools-cli.git
cd video-tools-cli
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Usage

### Input Types

- **File**: `C:\Videos\video.mp4`
- **Folder**: `C:\Videos\MyFolder` (all videos)
- **Multiple**: Drag & drop multiple files
- **URL**: Direct video links
- **Telegram**: `https://t.me/...`

### Compression Levels

| Level  | CRF | Speed  | Quality  |
| ------ | --- | ------ | -------- |
| Low    | 28  | Fast   | Lower    |
| Medium | 23  | Normal | Balanced |
| High   | 18  | Slow   | Best     |

### Parallel Processing

| Setting                   | Description                                  |
| ------------------------- | -------------------------------------------- |
| `MAX_QUEUE`               | Parallel workers for processing (default: 2) |
| `DOWNLOAD_MAX_CONNECTION` | Parallel download chunks (default: 4)        |

## Build

```bash
pip install pyinstaller
python build.py
python build.py --package  # Create release ZIP
```

## Testing

```bash

# Feature tests
python tests/test_features.py

# Options
python tests/test_features.py --quick      # Skip long tests
python tests/test_features.py --telegram   # Include Telegram tests
```

### Test Coverage

- ✅ Split Video (1, 2, 3 segments)
- ✅ Join Video (2, 3 files)
- ✅ Split & Join workflow
- ✅ Compress (low, medium, high)
- ✅ Parallel download verification
- ✅ Queue parallel processing
- ✅ JSON batch input
- ✅ Folder input detection
- ✅ Multiple files parsing

## Configuration

`.env` file (auto-created):

```env
MAX_QUEUE=2
DOWNLOAD_MAX_CONNECTION=4
COMPRESSION_LEVEL=medium
OVERRIDE_ENCODING=
```

## License

MIT License
