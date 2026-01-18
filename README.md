# Video Tools CLI

A powerful command-line video processing tool built with Python, FFmpeg, and TDL (Telegram Downloader).

## Features

- **Split Video** - Extract segments from videos using time ranges (supports HH.MM format)
- **Join Video** - Concatenate multiple video files into one
- **Compress Video** - Reduce video file size with auto-detected hardware acceleration
- **Telegram Support** - Download and process videos directly from Telegram links
- **Parallel Downloads** - Split large downloads into multiple concurrent connections
- **Progress Tracking** - Real-time progress bar with elapsed time and ETA
- **Colorful Logging** - Rich, informative console output with status indicators

## Installation

### Prerequisites

1. **Python 3.8+**
2. **FFmpeg** - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
3. **TDL** (optional) - For Telegram support, download from [iyear/tdl](https://github.com/iyear/tdl)

### Setup

```bash
# Clone or download the project
cd video-tools-cli

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Binary Configuration

Place `ffmpeg.exe`, `ffprobe.exe`, and `tdl.exe` in the `bin/` folder, or set paths in `.env`:

```env
# .env file
FFMPEG_PATH=C:/path/to/ffmpeg.exe
FFPROBE_PATH=C:/path/to/ffprobe.exe
TDL_PATH=C:/path/to/tdl.exe
MAX_QUEUE=4
DOWNLOAD_MAX_CONNECTION=16
OVERRIDE_ENCODING=
```

## Usage

### Starting the Application

```bash
python main.py
```

### Menu Options

```
       _     _             _              _
      (_)   | |           | |            | |
 __   ___  __| | ___  ___  | |_ ___   ___| |___
 \ \ / / |/ _` |/ _ \/ _ \ | __/ _ \ / _ \ / __|
  \ V /| | (_| |  __/ (_) || || (_) | (_) | \__ \
   \_/ |_|\__,_|\___|\___/  \__\___/ \___/|_|___/

? Select action:
> Split Video
  Join Video
  Compress Video
  ─────────────
  Set Max Queue
  Exit
```

### Split Video

Extract specific time ranges from a video:

```
? Video url / path: my_video.mp4
? Output name: clip
? Start Time (HH.MM): 00.05   # 5 minutes
? End Time (HH.MM): 00.10     # 10 minutes
? Add another segment? No

✓ Created clip_1.mp4
```

**Time Format:**

- `00.30` = 30 minutes
- `01.20` = 1 hour 20 minutes
- `120` = 120 seconds

### Join Video

Combine multiple videos:

```
? Video url / path: video1.mp4
? Add another video? Yes
? Video url / path: video2.mp4
? Add another video? No
? Output filename: combined.mp4

✓ Created combined.mp4
```

### Compress Video

Reduce file size with auto-detected hardware acceleration:

```
? Video url / path: large_video.mp4
? Output name: compressed.mp4

● Encoder: hevc_nvenc (Hardware)
● Compressing video (120.5s)...
[████████████████░░░░░░░░░░░░░░] 54.2% | Elapsed: 00:12 | ETA: 00:10 | Speed: 5.2x

✓ Created compressed.mp4
```

**Supported Encoders (auto-detected):**

- NVIDIA: `hevc_nvenc`, `h264_nvenc`
- Intel: `hevc_qsv`, `h264_qsv`
- AMD: `hevc_amf`, `h264_amf`
- Fallback: `libx264` (CPU)

### Batch Processing (JSON)

Create a JSON file for batch operations:

```json
[
  {
    "input": "https://example.com/video.mp4",
    "output": "output_video",
    "segments": [
      { "start": "00.05", "end": "00.10" },
      { "start": "00.15", "end": "00.20" }
    ]
  }
]
```

### Telegram Links

Supports direct Telegram video links:

```
? Video url / path: https://t.me/channel/12345
● Resolving Telegram link...
● Downloading from: http://localhost:8080/video.mp4
✓ Downloaded: downloaded_video.mp4
```

## Configuration

### Environment Variables

| Variable                  | Description                              | Default     |
| ------------------------- | ---------------------------------------- | ----------- |
| `MAX_QUEUE`               | Maximum items in processing queue        | `4`         |
| `DOWNLOAD_MAX_CONNECTION` | Parallel download connections            | `16`        |
| `OVERRIDE_ENCODING`       | Force specific encoder (e.g., `libx264`) | Auto-detect |

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run only unit tests (fast)
python -m pytest tests/test_ffmpeg_handler.py -v

# Run integration tests (requires FFmpeg)
python -m pytest tests/test_integration.py -v

# Skip integration tests
SKIP_INTEGRATION_TESTS=true python -m pytest tests/ -v
```

## Project Structure

```
video-tools-cli/
├── main.py                 # CLI entry point
├── core/
│   ├── config.py          # Configuration management
│   ├── ffmpeg_handler.py  # FFmpeg operations
│   ├── downloader.py      # Download manager
│   └── tdl_handler.py     # Telegram downloader
├── utils/
│   ├── helpers.py         # Time conversion utilities
│   └── logger.py          # Colored logging
├── tests/
│   ├── test_ffmpeg_handler.py
│   ├── test_downloader.py
│   ├── test_cli.py
│   └── test_integration.py
├── bin/                   # Binary executables
└── requirements.txt
```

## License

MIT License

## Credits

- Built with [FFmpeg](https://ffmpeg.org/)
- Telegram support via [TDL](https://github.com/iyear/tdl)
- CLI interface powered by [InquirerPy](https://github.com/kazhala/InquirerPy)
