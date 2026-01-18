"""
Configuration management for Video Tools CLI.
Handles PyInstaller frozen builds and development mode.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def get_app_dir() -> Path:
    """
    Get the application directory.
    - For PyInstaller frozen builds: directory containing the .exe
    - For development: project root directory
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle - use exe directory
        return Path(sys.executable).parent
    else:
        # Running as script - use project root
        return Path(__file__).resolve().parent.parent


# Define base paths
APP_DIR = get_app_dir()
BIN_DIR = APP_DIR / "bin"
CACHE_DIR = APP_DIR / "cache"
ENV_PATH = APP_DIR / ".env"

# Compression presets (CRF values for x264/x265, lower = better quality, higher file size)
COMPRESSION_LEVELS = {
    "low": {"crf": 28, "preset": "fast", "description": "Low quality, small file"},
    "medium": {"crf": 23, "preset": "medium", "description": "Balanced quality/size"},
    "high": {"crf": 18, "preset": "slow", "description": "High quality, large file"}
}


def ensure_bin_dir():
    """Ensure bin directory exists."""
    if not BIN_DIR.exists():
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created bin directory at {BIN_DIR}")


def ensure_cache_dir():
    """Ensure cache directory exists for temporary processing files."""
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def ensure_config():
    """Ensure .env file exists with default values."""
    if not ENV_PATH.exists():
        default_config = (
            "MAX_QUEUE=2\n"
            "DOWNLOAD_MAX_CONNECTION=4\n"
            "OVERRIDE_ENCODING=\n"
            "COMPRESSION_LEVEL=medium\n"
        )
        try:
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write(default_config)
            print(f"Created default configuration at {ENV_PATH}")
        except Exception as e:
            print(f"Error creating .env file: {e}")


def load_config():
    """Load configuration from .env."""
    ensure_config()
    ensure_bin_dir()
    ensure_cache_dir()
    load_dotenv(ENV_PATH)


def get_binary_path(binary_name: str) -> str:
    """
    Get the absolute path to a binary.
    Prioritizes:
    1. bin/ folder next to the application.
    2. System PATH.
    """
    ensure_bin_dir()
    
    if sys.platform == "win32" and not binary_name.lower().endswith(".exe"):
        binary_name_with_ext = binary_name + ".exe"
    else:
        binary_name_with_ext = binary_name

    local_bin = BIN_DIR / binary_name_with_ext
    if local_bin.exists():
        return str(local_bin)
    
    # Try to auto-download missing binaries
    if binary_name in ["ffmpeg", "ffprobe", "tdl"]:
        try:
            from .binary_downloader import download_binary
            if download_binary(binary_name, BIN_DIR):
                if local_bin.exists():
                    return str(local_bin)
        except Exception as e:
            print(f"Warning: Could not auto-download {binary_name}: {e}")
    
    return binary_name_with_ext if sys.platform == "win32" else binary_name


def get_temp_dir() -> Path:
    """Get temporary directory for video processing chunks."""
    temp_dir = CACHE_DIR / f"temp_{os.getpid()}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_env(key: str, default=None):
    """Get environment variable with optional default."""
    return os.getenv(key, default)


def get_compression_settings(level: str = None) -> dict:
    """Get compression settings for given level."""
    if level is None:
        level = get_env("COMPRESSION_LEVEL", "medium")
    return COMPRESSION_LEVELS.get(level.lower(), COMPRESSION_LEVELS["medium"])


def ensure_output_extension(filename: str, extension: str = ".mp4") -> str:
    """Ensure filename has the specified extension."""
    if not filename:
        return filename
    
    if not filename.lower().endswith(extension.lower()):
        return filename + extension
    
    return filename


def get_output_path(input_path: str, output_name: str, suffix: str = "") -> str:
    """
    Get output path in same folder as input file.
    
    Args:
        input_path: Original input file path
        output_name: User-provided output name (may be empty)
        suffix: Suffix to add before extension
    
    Returns:
        Full output path in source folder
    """
    input_file = Path(input_path).resolve()
    source_folder = input_file.parent
    
    if output_name and output_name.strip():
        # User provided a name, ensure extension
        filename = ensure_output_extension(output_name.strip())
    else:
        # Empty output - derive from input
        stem = input_file.stem
        if suffix:
            filename = f"{stem}{suffix}.mp4"
        else:
            filename = f"{stem}.mp4"
    
    return str(source_folder / filename)


def get_output_name(input_path: str, output_name: str, suffix: str = "") -> str:
    """Legacy function - get just the filename."""
    if output_name and output_name.strip():
        return ensure_output_extension(output_name.strip())
    
    input_file = Path(input_path)
    stem = input_file.stem
    
    if suffix:
        return f"{stem}{suffix}.mp4"
    else:
        return f"{stem}.mp4"
