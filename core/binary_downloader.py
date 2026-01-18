"""
Binary downloader - Auto-downloads FFmpeg, FFprobe, and TDL if missing.
"""
import os
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path
from urllib.request import urlretrieve
from utils.logger import log

# Download URLs (Windows x64)
BINARY_URLS = {
    "ffmpeg": {
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "zip_path": "ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe",
        "filename": "ffmpeg.exe"
    },
    "ffprobe": {
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "zip_path": "ffmpeg-master-latest-win64-gpl/bin/ffprobe.exe",
        "filename": "ffprobe.exe"
    },
    "tdl": {
        "url": "https://github.com/iyear/tdl/releases/latest/download/tdl_Windows_64bit.zip",
        "zip_path": "tdl.exe",
        "filename": "tdl.exe"
    }
}


def download_with_progress(url: str, dest: str, name: str) -> bool:
    """Download file with progress indication."""
    try:
        log.info(f"Downloading {name}...")
        log.detail("URL", url[:80] + "..." if len(url) > 80 else url)
        
        def reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(downloaded / total_size * 100, 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r         Downloading: {mb_downloaded:.1f}/{mb_total:.1f} MB ({pct:.0f}%)", end="", flush=True)
        
        urlretrieve(url, dest, reporthook)
        print()  # New line after progress
        return True
    except Exception as e:
        log.error(f"Download failed: {e}")
        return False


def extract_from_zip(zip_path: str, internal_path: str, dest_path: str) -> bool:
    """Extract specific file from ZIP archive."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Try exact path first
            if internal_path in zf.namelist():
                with zf.open(internal_path) as src, open(dest_path, 'wb') as dst:
                    dst.write(src.read())
                return True
            
            # Search for filename in any subfolder
            filename = os.path.basename(internal_path)
            for name in zf.namelist():
                if name.endswith(filename):
                    with zf.open(name) as src, open(dest_path, 'wb') as dst:
                        dst.write(src.read())
                    return True
        
        log.error(f"File not found in archive: {internal_path}")
        return False
    except Exception as e:
        log.error(f"Extraction failed: {e}")
        return False


def download_binary(binary_name: str, bin_dir: Path) -> bool:
    """Download a specific binary to the bin directory."""
    if binary_name not in BINARY_URLS:
        log.error(f"Unknown binary: {binary_name}")
        return False
    
    config = BINARY_URLS[binary_name]
    dest_path = bin_dir / config["filename"]
    
    # Skip if already exists
    if dest_path.exists():
        return True
    
    log.section(f"Installing {binary_name.upper()}")
    
    # Download to temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix="video_tools_"))
    zip_path = temp_dir / "download.zip"
    
    try:
        # Check if we need to download (ffmpeg and ffprobe share same ZIP)
        if binary_name in ["ffmpeg", "ffprobe"]:
            # Check if we already downloaded for ffmpeg
            ffmpeg_config = BINARY_URLS["ffmpeg"]
            ffprobe_config = BINARY_URLS["ffprobe"]
            
            if not download_with_progress(config["url"], str(zip_path), binary_name):
                return False
            
            # Extract both ffmpeg and ffprobe from same zip
            ffmpeg_dest = bin_dir / ffmpeg_config["filename"]
            ffprobe_dest = bin_dir / ffprobe_config["filename"]
            
            if not ffmpeg_dest.exists():
                if extract_from_zip(str(zip_path), ffmpeg_config["zip_path"], str(ffmpeg_dest)):
                    log.success(f"Installed: {ffmpeg_config['filename']}")
            
            if not ffprobe_dest.exists():
                if extract_from_zip(str(zip_path), ffprobe_config["zip_path"], str(ffprobe_dest)):
                    log.success(f"Installed: {ffprobe_config['filename']}")
            
            return dest_path.exists()
        else:
            # TDL or other binaries
            if not download_with_progress(config["url"], str(zip_path), binary_name):
                return False
            
            if extract_from_zip(str(zip_path), config["zip_path"], str(dest_path)):
                log.success(f"Installed: {config['filename']}")
                return True
            return False
            
    finally:
        # Cleanup temp files
        shutil.rmtree(temp_dir, ignore_errors=True)


def ensure_binaries(bin_dir: Path, required: list = None) -> bool:
    """
    Ensure all required binaries are available.
    Downloads missing ones automatically.
    
    Args:
        bin_dir: Path to bin directory
        required: List of required binaries (default: ffmpeg, ffprobe)
    
    Returns:
        True if all binaries are available
    """
    if required is None:
        required = ["ffmpeg", "ffprobe"]  # TDL is optional
    
    # Create bin directory if missing
    if not bin_dir.exists():
        log.info("Creating bin directory...")
        bin_dir.mkdir(parents=True, exist_ok=True)
    
    all_present = True
    for binary in required:
        filename = BINARY_URLS.get(binary, {}).get("filename", f"{binary}.exe")
        binary_path = bin_dir / filename
        
        if not binary_path.exists():
            log.warning(f"{binary} not found, downloading...")
            if not download_binary(binary, bin_dir):
                all_present = False
    
    return all_present
