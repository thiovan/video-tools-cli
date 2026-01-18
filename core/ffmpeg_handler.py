"""
FFmpeg Handler with improved error handling, progress tracking, and colored logging.
"""
import subprocess
import json
import re
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Tuple
from .config import get_binary_path, get_env, get_compression_settings
from utils.logger import log


class FFmpegHandler:
    """Handler for FFmpeg operations with progress tracking and error handling."""
    
    # Hardware encoder identifiers
    HARDWARE_ENCODERS = {
        "h264_nvenc", "hevc_nvenc",  # NVIDIA
        "h264_qsv", "hevc_qsv",       # Intel QuickSync
        "h264_amf", "hevc_amf"        # AMD
    }
    
    def __init__(self):
        self.ffmpeg = get_binary_path("ffmpeg")
        self.ffprobe = get_binary_path("ffprobe")
        self._detected_encoders = None

    def _safe_path(self, path) -> str:
        """Convert path to safe absolute path string for FFmpeg on Windows."""
        return str(Path(path).resolve())

    def _run_ffmpeg(self, cmd: list, progress_callback: Optional[Callable] = None, 
                    total_duration: float = 0.0) -> Tuple[bool, str]:
        """
        Run FFmpeg command with proper error handling and optional progress tracking.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if progress_callback and total_duration > 0:
                # Use progress pipe for real-time updates
                progress_cmd = cmd.copy()
                # Replace -stats with -progress
                if "-stats" in progress_cmd:
                    idx = progress_cmd.index("-stats")
                    progress_cmd[idx:idx+1] = ["-progress", "pipe:1"]
                else:
                    # Insert after -hide_banner
                    try:
                        idx = progress_cmd.index("-hide_banner")
                        progress_cmd.insert(idx + 1, "-progress")
                        progress_cmd.insert(idx + 2, "pipe:1")
                    except ValueError:
                        progress_cmd = [progress_cmd[0], "-progress", "pipe:1"] + progress_cmd[1:]
                
                return self._run_with_progress(progress_cmd, progress_callback, total_duration)
            else:
                # Standard run with error capture
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else f"Exit code: {result.returncode}"
                    return False, error_msg
                
                return True, ""
                
        except subprocess.SubprocessError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def _run_with_progress(self, cmd: list, callback: Callable, 
                           total_duration: float) -> Tuple[bool, str]:
        """Run FFmpeg with progress parsing and callback."""
        start_time = time.time()
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        current_time = 0.0
        speed = 0.0
        
        def read_stderr():
            """Read stderr in background to prevent blocking."""
            try:
                process.stderr.read()
            except:
                pass
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        try:
            while process.poll() is None:
                line = process.stdout.readline()
                if not line:
                    continue
                
                # Parse progress output
                if line.startswith("out_time_ms="):
                    try:
                        ms = int(line.split("=")[1].strip())
                        current_time = ms / 1_000_000.0
                    except:
                        pass
                elif line.startswith("speed="):
                    try:
                        speed_str = line.split("=")[1].strip().rstrip("x")
                        if speed_str and speed_str != "N/A":
                            speed = float(speed_str)
                    except:
                        pass
                elif line.startswith("progress="):
                    # Update progress
                    elapsed = time.time() - start_time
                    callback(current_time, total_duration, elapsed, speed)
            
            # Final check
            if process.returncode != 0:
                return False, f"FFmpeg exited with code {process.returncode}"
            
            return True, ""
            
        except Exception as e:
            process.kill()
            return False, str(e)

    def get_video_info(self, path) -> Optional[dict]:
        """Get video metadata using ffprobe."""
        safe_path = self._safe_path(path)
        cmd = [
            self.ffprobe,
            "-hide_banner",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            safe_path
        ]
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                log.warning(f"ffprobe failed: {result.stderr[:200] if result.stderr else 'Unknown error'}")
                return None
        except subprocess.CalledProcessError as e:
            log.error(f"Error checking video info", details=str(e))
            return None
        except json.JSONDecodeError:
            log.error("Invalid JSON from ffprobe")
            return None

    def get_duration(self, path) -> float:
        """Get video duration in seconds."""
        info = self.get_video_info(path)
        if info:
            try:
                return float(info['format']['duration'])
            except (KeyError, ValueError):
                pass
        return 0.0

    def split_video(self, input_path, start_time, end_time, output_path):
        """Split video using stream copy (fast, accurate at keyframes)."""
        safe_input = self._safe_path(input_path)
        safe_output = self._safe_path(output_path)
        
        cmd = [
            self.ffmpeg,
            "-hide_banner", "-v", "warning", "-stats",
            "-y",
            "-i", safe_input,
            "-ss", str(start_time),
            "-to", str(end_time),
            "-c", "copy",
            safe_output
        ]
        
        log.info(f"Splitting: {start_time}s → {end_time}s")
        success, error = self._run_ffmpeg(cmd)
        
        if not success:
            raise RuntimeError(f"Split failed: {error}")

    def download_segment(self, url, start_time, end_time, output_path):
        """Download a specific segment from URL using ffmpeg seeking."""
        safe_output = self._safe_path(output_path)
        duration = end_time - start_time
        
        cmd = [
            self.ffmpeg,
            "-hide_banner", "-v", "warning", "-stats",
            "-y",
            "-ss", str(start_time),
            "-i", url,
            "-t", str(duration),
            "-c", "copy",
            safe_output
        ]
        
        log.info(f"Downloading segment: {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)")
        success, error = self._run_ffmpeg(cmd)
        
        if not success:
            raise RuntimeError(f"Download failed: {error}")

    def join_videos(self, input_paths: list, output_path: str):
        """Join videos using concat demuxer."""
        safe_output = self._safe_path(output_path)
        list_file = Path("join_list.txt")
        
        try:
            # Create concat file with safe paths
            with open(list_file, "w", encoding="utf-8") as f:
                for path in input_paths:
                    safe_path = self._safe_path(path).replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")
            
            cmd = [
                self.ffmpeg,
                "-hide_banner", "-v", "warning", "-stats",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                safe_output
            ]
            
            log.info(f"Joining {len(input_paths)} videos...")
            success, error = self._run_ffmpeg(cmd)
            
            if not success:
                raise RuntimeError(f"Join failed: {error}")
                
        finally:
            if list_file.exists():
                list_file.unlink()

    def detect_hw_encoders(self) -> list:
        """Detect available hardware encoders (cached)."""
        if self._detected_encoders is not None:
            return self._detected_encoders
        
        cmd = [self.ffmpeg, "-hide_banner", "-v", "quiet", "-encoders"]
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            output = result.stdout
            
            encoders = []
            # Prioritize NVENC and QSV
            if "h264_nvenc" in output: encoders.append("h264_nvenc")
            if "hevc_nvenc" in output: encoders.append("hevc_nvenc")
            if "h264_qsv" in output: encoders.append("h264_qsv")
            if "hevc_qsv" in output: encoders.append("hevc_qsv")
            if "h264_amf" in output: encoders.append("h264_amf")
            if "hevc_amf" in output: encoders.append("hevc_amf")
            
            self._detected_encoders = encoders
            return encoders
        except subprocess.SubprocessError:
            self._detected_encoders = []
            return []

    def compress_video(self, input_path: str, output_path: str, 
                       show_progress: bool = True, compression_level: str = None):
        """
        Compress video with auto-detected hardware acceleration.
        Shows encoding info and progress bar.
        
        Args:
            compression_level: 'low', 'medium', or 'high'. If None, reads from config.
        """
        safe_input = self._safe_path(input_path)
        safe_output = self._safe_path(output_path)
        
        encoders = self.detect_hw_encoders()
        
        # Get source info
        info = self.get_video_info(input_path)
        width = 1920
        height = 1080
        duration = 0.0
        
        if info:
            try:
                duration = float(info.get('format', {}).get('duration', 0))
            except:
                pass
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = int(stream.get('width', 1920))
                    height = int(stream.get('height', 1080))
                    break
        # Get compression settings
        comp_settings = get_compression_settings(compression_level)
        crf = comp_settings["crf"]
        preset = comp_settings["preset"]
        level_name = compression_level if compression_level else get_env("COMPRESSION_LEVEL", "medium")
        log.detail("Compression Level", level_name.upper())
        
        # Determine resize filter
        scale_filter = ""
        if width > 1920 or height > 1080:
            scale_filter = "scale='min(1920,iw)':-2"
            log.detail("Resize", f"{width}x{height} → 1920p max")
        
        # Build command
        cmd = [self.ffmpeg, "-hide_banner", "-v", "warning", "-stats", "-y", 
               "-i", safe_input]
        
        # Select encoder
        override_enc = get_env("OVERRIDE_ENCODING")
        selected_encoder = ""
        is_hardware = False
        
        if override_enc:
            selected_encoder = override_enc
            is_hardware = override_enc in self.HARDWARE_ENCODERS
            cmd.extend(["-c:v", override_enc])
        elif "hevc_nvenc" in encoders:
            selected_encoder = "hevc_nvenc"
            is_hardware = True
            # Map CRF to NVENC CQ (approximate)
            nvenc_cq = min(51, max(0, crf + 5))
            cmd.extend(["-c:v", "hevc_nvenc", "-preset", "p4", "-cq", str(nvenc_cq)])
        elif "h264_nvenc" in encoders:
            selected_encoder = "h264_nvenc"
            is_hardware = True
            nvenc_cq = min(51, max(0, crf + 3))
            cmd.extend(["-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(nvenc_cq)])
        elif "hevc_qsv" in encoders:
            selected_encoder = "hevc_qsv"
            is_hardware = True
            cmd.extend(["-c:v", "hevc_qsv", "-global_quality", str(crf + 5)])
        elif "h264_qsv" in encoders:
            selected_encoder = "h264_qsv"
            is_hardware = True
            cmd.extend(["-c:v", "h264_qsv", "-global_quality", str(crf + 3)])
        else:
            selected_encoder = "libx264"
            is_hardware = False
            cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", preset])
        
        # Log encoder info
        log.encoding(selected_encoder, is_hardware)
        
        # Add scale filter if needed
        if scale_filter:
            cmd.extend(["-vf", scale_filter])
        
        # Copy audio
        cmd.extend(["-c:a", "copy"])
        cmd.append(safe_output)
        
        # Run with progress if duration is known
        if show_progress and duration > 0:
            log.info(f"Compressing video ({duration:.1f}s)...")
            success, error = self._run_ffmpeg(
                cmd, 
                progress_callback=log.progress,
                total_duration=duration
            )
            log.progress_done()
        else:
            log.info("Compressing video...")
            success, error = self._run_ffmpeg(cmd)
        
        if not success:
            raise RuntimeError(f"Compression failed: {error}")
