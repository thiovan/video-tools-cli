# Video Tools CLI

```text
       _      _             _             _
      (_)    | |           | |           | |
 __   ___  __| | ___  ___  | |_ ___   ___| |___
 \ \ / / |/ _` |/ _ \/ _ \ | __/ _ \ / _ \ / __|
  \ V /| | (_| |  __/ (_) || || (_) | (_) | \__ \
   \_/ |_|\__,_|\___|\___/  \__\___/ \___/|_|___/

        Video Processing Made Easy
```

![Version](https://img.shields.io/badge/version-1.7.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

A powerful command-line video processing tool with parallel processing support. 

> **Important Dependencies:** This project relies on the following external binaries to function:
> - **[FFmpeg](https://ffmpeg.org/)** for core video processing, splitting, joining, and compression.
> - **[TDL (Telegram Downloader)](https://github.com/iyear/tdl)** for resolving and downloading videos directly from Telegram links.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Input Types](#input-types)
  - [Compression Levels](#compression-levels)
  - [Parallel Processing](#parallel-processing)
  - [Advanced JSON Configurations](#advanced-json-configurations-optional)
- [Build](#build)
- [Testing](#testing)
- [Configuration](#configuration)
- [License](#license)

## Features

| Feature               | Description                               |
| --------------------- | ----------------------------------------- |
| **Split Video**       | Extract segments with parallel processing |
| **Join Video**        | Concatenate multiple videos               |
| **Split & Join**      | Split segments and merge into one file    |
| **Compress Video**    | 3 quality levels (low/medium/high)        |
| **Telegram**          | Download from Telegram links via TDL      |
| **Multi-Session**     | Distribute Telegram downloads across accounts |
| **Parallel Download** | Multi-threaded chunked downloads          |
| **Folder Input**      | Process all videos in a folder            |

## Quick Start

### Download Release

[Download latest release](../../releases) → Extract → Run `video-tools.exe`

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

### Input Types

- **File**: `C:\Videos\video.mp4`
- **Folder**: `C:\Videos\MyFolder` (all videos)
- **Multiple**: Drag & drop multiple files
- **URL**: Direct video links
- **Telegram**: `https://t.me/...`
- **JSON Batch Engine**: Supports massively parallel execution matrices.

### Compression Levels

| Level  | CRF | Speed  | Quality  |
| ------ | --- | ------ | -------- |
| Low    | 28  | Fast   | Lower    |
| Medium | 23  | Normal | Balanced |
| High   | 18  | Slow   | Best     |

### Parallel Processing

| Setting                   | Description                                         |
| ------------------------- | --------------------------------------------------- |
| `MAX_QUEUE`               | Parallel workers for processing (default: 2)        |
| `DOWNLOAD_MAX_CONNECTION` | Parallel download chunks (default: 4)               |
| `TDL_SESSIONS`            | Comma-separated TDL sessions for Telegram batch load balancing (e.g., `default,second_account`) |

### Multi-Session TDL Batching

To prevent Telegram from rate-limiting your downloads during heavy parallel processing, you can distribute the load across multiple Telegram accounts using TDL namespaces.

1. **Login to a new session:**
   Open your terminal and login using a new namespace:
   ```bash
   tdl login -n second_account
   ```
2. **Update your `.env`:**
   Add the new session to the `TDL_SESSIONS` configuration:
   ```env
   TDL_SESSIONS=default,second_account
   ```
   
The CLI will automatically use Round-Robin load balancing and dynamically assign free ports to distribute concurrent chunk downloads evenly across your accounts.

### Advanced JSON Configurations (Optional)

When processing `.json` streams, the CLI natively injects security overrides:

- `"referer"`: Safely bypass referer-locked CDNs.
- `"user_agent"`: Hijack default FFmpeg agents to emulate browsers.
- `"headers"`: Inject multi-line specific headers (e.g. `Authorization`).

**Example `test_input.json`:**

```json
[
  {
    "input": "https://dummy-url.com/video1",
    "output": "test output 1",
    "segments": [
      {
        "start": "00.00",
        "end": "01.00"
      }
    ]
  },
  {
    "input": "https://dummy-url.com/video2",
    "referer": "https://dummy-url.com",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "headers": "Authorization: Bearer token123\r\nAccept-Language: en-US,en;q=0.9",
    "output": "test output 2",
    "segments": [
      {
        "start": "00.16",
        "end": "00.40"
      }
    ]
  }
]
```

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

### Automated Test Coverage

The project includes an extensive test suite verifying:

- ✅ End-to-end Split & Join accuracy (1, 2, 3 segments).
- ✅ Join Video (2, 3 files).
- ✅ Hardware-accelerated and fallback CPU compression (low, medium, high).
- ✅ JSON batch parsing, error mapping, and missing parameter fail-safes.
- ✅ Multithreaded chunk downloads and parallel download verification.
- ✅ JSON parallel `max_queue` concurrency safety tests (UUID WinError prevention).
- ✅ Single segment JSON renaming outputs & Split & Join single segment logic.
- ✅ Robust global application cache sweeping.
- ✅ `.m3u8` HLS parameter injection logic & protections versus progressive JSON links.
- ✅ Folder input detection & multiple files parsing.

## Configuration

The `.env` file is auto-created. Alternatively, copy `.env.example` to `.env` to start with default values:

```env
MAX_QUEUE=2
DOWNLOAD_MAX_CONNECTION=4
COMPRESSION_LEVEL=medium
OVERRIDE_ENCODING=
TDL_SESSIONS=default
```

## License

MIT License
