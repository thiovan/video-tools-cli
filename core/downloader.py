"""
Downloader with parallel chunked downloads and colored logging.
Uses application cache folder for temporary files.
"""
import subprocess
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, TYPE_CHECKING
from pathlib import Path
from utils.logger import log
from .config import CACHE_DIR

if TYPE_CHECKING:
    from .ffmpeg_handler import FFmpegHandler


class Downloader:
    """Downloader with support for parallel chunked downloads."""
    
    def __init__(self, ffmpeg_handler: Optional["FFmpegHandler"] = None, max_workers: int = 4):
        """
        Initialize downloader.
        
        Args:
            ffmpeg_handler: Inject existing FFmpegHandler or None to create new one.
            max_workers: Max concurrent connections for parallel downloads.
        """
        if ffmpeg_handler:
            self.ffmpeg_handler = ffmpeg_handler
        else:
            from .ffmpeg_handler import FFmpegHandler
            self.ffmpeg_handler = FFmpegHandler()
        
        self.max_workers = max_workers

    def _safe_path(self, path) -> str:
        """Convert to safe absolute path string."""
        return str(Path(path).resolve())

    def _get_temp_dir(self) -> Path:
        """Get temporary directory for video chunks in cache folder."""
        temp_dir = CACHE_DIR / f"chunks_{os.getpid()}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def smart_download(self, url: str, output_name: str) -> bool:
        """
        Simple download using FFmpeg.
        For complex splitting logic, use ffmpeg_handler directly.
        """
        safe_output = self._safe_path(output_name)
        log.info(f"Downloading: {output_name}")
        
        cmd = [
            self.ffmpeg_handler.ffmpeg,
            "-hide_banner", "-v", "warning", "-stats",
            "-y",
            "-i", url,
            "-c", "copy",
            safe_output
        ]
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                error = result.stderr.strip() if result.stderr else f"Exit code: {result.returncode}"
                log.error("Download failed", details=error)
                return False
            log.success(f"Downloaded: {output_name}")
            return True
        except subprocess.SubprocessError as e:
            log.error(f"FFmpeg download failed: {e}")
            return False

    def _download_chunk(self, url: str, start_time: float, duration: float, output_path: str) -> bool:
        """Download a single chunk."""
        cmd = [
            self.ffmpeg_handler.ffmpeg,
            "-hide_banner", "-v", "warning",
            "-y",
            "-ss", str(start_time),
            "-i", url,
            "-t", str(duration),
            "-c", "copy",
            output_path
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                log.error(f"Chunk {start_time:.1f}s failed", 
                         details=result.stderr[:200] if result.stderr else None)
                return False
            return True
        except subprocess.SubprocessError as e:
            log.error(f"Chunk download error: {e}")
            return False

    def _merge_chunks(self, chunk_files: List[str], output_path: str) -> bool:
        """Merge multiple chunks into one file using ffmpeg concat."""
        list_file = CACHE_DIR / f"concat_list_{os.getpid()}.txt"
        try:
            with open(list_file, "w", encoding="utf-8") as f:
                for chunk in chunk_files:
                    safe_path = self._safe_path(chunk).replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")
            
            cmd = [
                self.ffmpeg_handler.ffmpeg,
                "-hide_banner", "-v", "warning",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                log.error("Merge failed", details=result.stderr[:200] if result.stderr else None)
                return False
            return True
        except Exception as e:
            log.error(f"Merge error: {e}")
            return False
        finally:
            if list_file.exists():
                list_file.unlink()

    def download_segment_parallel(self, url: str, start_time: float, end_time: float, output_name: str) -> bool:
        """
        Download a segment by splitting it into multiple chunks and downloading in parallel.
        """
        total_duration = end_time - start_time
        safe_output = self._safe_path(output_name)
        
        # If duration is very short or max_workers is 1, do single download
        if total_duration < 30 or self.max_workers <= 1:
            log.info(f"Short segment, single download: {output_name}")
            try:
                self.ffmpeg_handler.download_segment(url, start_time, end_time, output_name)
                return True
            except Exception as e:
                log.error(f"Download failed: {e}")
                return False
        
        # Calculate chunk size
        chunk_duration = total_duration / self.max_workers
        
        # Use application cache directory for temp files
        temp_dir = self._get_temp_dir()
        
        try:
            # Prepare chunk tasks
            chunks = []
            for i in range(self.max_workers):
                chunk_start = start_time + (i * chunk_duration)
                chunk_file = str(temp_dir / f"chunk_{i:03d}.mp4")
                chunks.append((chunk_start, chunk_duration, chunk_file))
            
            log.info(f"Splitting into {self.max_workers} parallel downloads...")
            
            # Download chunks in parallel
            chunk_files = []
            success = True
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                for i, (chunk_start, chunk_dur, chunk_file) in enumerate(chunks):
                    future = executor.submit(self._download_chunk, url, chunk_start, chunk_dur, chunk_file)
                    futures[future] = (i, chunk_file)
                
                for future in as_completed(futures):
                    idx, chunk_file = futures[future]
                    try:
                        if future.result():
                            chunk_files.append((idx, chunk_file))
                            log.step(idx + 1, self.max_workers, f"Chunk completed")
                        else:
                            success = False
                            log.error(f"Chunk {idx + 1}/{self.max_workers} failed")
                    except Exception as e:
                        log.error(f"Chunk {idx} error: {e}")
                        success = False
            
            if not success or len(chunk_files) != self.max_workers:
                log.error("Not all chunks downloaded successfully")
                return False
            
            # Sort by index to ensure correct order
            chunk_files.sort(key=lambda x: x[0])
            ordered_files = [f for _, f in chunk_files]
            
            # Merge chunks
            log.info(f"Merging {len(ordered_files)} chunks...")
            if self._merge_chunks(ordered_files, safe_output):
                log.success(f"Created: {output_name}")
                return True
            else:
                return False
                
        finally:
            # Cleanup temp files
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def download_segment(self, url: str, start_time: float, end_time: float, output_name: str) -> bool:
        """Download a specific segment from URL using parallel chunked download."""
        return self.download_segment_parallel(url, start_time, end_time, output_name)

    def batch_download_segments(
        self, 
        url: str, 
        segments: List[Tuple[float, float, str]]
    ) -> List[Tuple[str, bool]]:
        """
        Download multiple segments sequentially (each segment uses parallel chunk download).
        """
        results = []
        
        for i, (start, end, output) in enumerate(segments):
            log.section(f"Segment {i+1}/{len(segments)}: {output}")
            success = self.download_segment_parallel(url, start, end, output)
            results.append((output, success))
        
        return results
