"""
Path and input utilities for Video Tools CLI.
Handles path normalization, multi-file input, and folder expansion.
"""
import os
from pathlib import Path
from typing import List, Optional


# Supported video extensions
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.mts'}


def normalize_path(path: str) -> str:
    """
    Normalize a path string:
    - Remove surrounding quotes
    - Strip whitespace
    - Resolve to absolute path
    """
    if not path:
        return path
    
    # Strip whitespace
    path = path.strip()
    
    # Remove surrounding quotes (from drag-and-drop)
    if (path.startswith('"') and path.endswith('"')) or \
       (path.startswith("'") and path.endswith("'")):
        path = path[1:-1]
    
    # Handle paths with spaces that might have extra quotes
    path = path.replace('"', '').replace("'", "")
    
    return path


def is_video_file(path: str) -> bool:
    """Check if path is a video file."""
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def expand_input(raw_input: str) -> List[str]:
    """
    Expand input to list of video files.
    
    Handles:
    - Single file path
    - Folder path (returns all video files in folder)
    - Multiple files (space or newline separated, handles quoted paths)
    
    Returns:
        List of normalized file paths
    """
    if not raw_input:
        return []
    
    raw_input = raw_input.strip()
    
    # Check if it's a URL
    if raw_input.startswith("http") or "t.me/" in raw_input:
        return [raw_input]
    
    # Try to parse as single path first
    single_path = normalize_path(raw_input)
    
    if os.path.isdir(single_path):
        # It's a folder - get all video files
        return get_videos_in_folder(single_path)
    
    if os.path.isfile(single_path):
        # It's a single file
        return [single_path]
    
    # Try to parse as multiple paths (drag-and-drop often produces this)
    paths = parse_multiple_paths(raw_input)
    
    if paths:
        return paths
    
    # Return as-is (might be a URL or invalid path)
    return [single_path]


def get_videos_in_folder(folder_path: str) -> List[str]:
    """Get all video files in a folder (non-recursive)."""
    folder = Path(folder_path)
    videos = []
    
    for file in sorted(folder.iterdir()):
        if file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS:
            videos.append(str(file.resolve()))
    
    return videos


def parse_multiple_paths(raw_input: str) -> List[str]:
    """
    Parse multiple file paths from drag-and-drop input.
    Handles:
    - "path1" "path2" "path3"
    - path1
      path2
      path3
    """
    paths = []
    
    # First try newline-separated
    if '\n' in raw_input:
        for line in raw_input.split('\n'):
            line = normalize_path(line)
            if line and os.path.exists(line):
                paths.append(line)
        if paths:
            return paths
    
    # Try to extract quoted paths
    import re
    quoted = re.findall(r'"([^"]+)"', raw_input)
    if quoted:
        for p in quoted:
            if os.path.exists(p):
                paths.append(str(Path(p).resolve()))
        if paths:
            return paths
    
    return paths


def get_input_summary(paths: List[str]) -> str:
    """Get a summary of input files for display."""
    if not paths:
        return "No files"
    
    if len(paths) == 1:
        return Path(paths[0]).name
    
    return f"{len(paths)} files"
