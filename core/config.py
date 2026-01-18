"""
Configuration management for Video Tools CLI.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Define base paths
BASE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = BASE_DIR / "bin"
ENV_PATH = BASE_DIR / ".env"


def ensure_bin_dir():
    """Ensure bin directory exists."""
    if not BIN_DIR.exists():
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created bin directory at {BIN_DIR}")


def ensure_config():
    """Ensure .env file exists with default values."""
    if not ENV_PATH.exists():
        default_config = (
            "MAX_QUEUE=4\n"
            "DOWNLOAD_MAX_CONNECTION=16\n"
            "OVERRIDE_ENCODING=\n"
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
    load_dotenv(ENV_PATH)


def get_binary_path(binary_name: str) -> str:
    """
    Get the absolute path to a binary.
    Prioritizes:
    1. bin/ folder in the project root.
    2. System PATH.
    
    Returns the executable path or just the name if not found in bin/.
    """
    # Ensure bin directory exists
    ensure_bin_dir()
    
    # Check for .exe extension on Windows if not provided
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
    
    # Fallback to system path (return just the name so subprocess can find it)
    return binary_name_with_ext if sys.platform == "win32" else binary_name


def get_env(key: str, default=None):
    """Get environment variable with optional default."""
    return os.getenv(key, default)


def ensure_output_extension(filename: str, extension: str = ".mp4") -> str:
    """
    Ensure filename has the specified extension.
    
    Args:
        filename: The filename to check
        extension: Extension to add if missing (default: .mp4)
    
    Returns:
        Filename with extension
    """
    if not filename:
        return filename
    
    if not filename.lower().endswith(extension.lower()):
        return filename + extension
    
    return filename


def get_output_name(input_path: str, output_name: str, suffix: str = "") -> str:
    """
    Get output filename, handling empty input.
    
    Args:
        input_path: Original input file path
        output_name: User-provided output name (may be empty)
        suffix: Suffix to add before extension (e.g., "_join", "_compressed")
    
    Returns:
        Valid output filename with .mp4 extension
    """
    if output_name and output_name.strip():
        # User provided a name, ensure extension
        return ensure_output_extension(output_name.strip())
    
    # Empty output - derive from input
    input_file = Path(input_path)
    stem = input_file.stem
    
    if suffix:
        return f"{stem}{suffix}.mp4"
    else:
        # Replace original - use same name
        return f"{stem}.mp4"
