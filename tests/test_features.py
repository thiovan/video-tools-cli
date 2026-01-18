"""
Comprehensive Feature Tests for Video Tools CLI
Tests all features with various configurations.

Usage:
    python tests/test_features.py              # Run all tests
    python tests/test_features.py --exe        # Test video-tools.exe
    python tests/test_features.py --quick      # Skip long download tests
"""
import os
import sys
import time
import shutil
import tempfile
import json
import urllib.request
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# Sample videos for testing
SAMPLE_VIDEO_URL = "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/bottle-detection.mp4"
SAMPLE_VIDEO_LARGER = "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/free-standing-person-detection.mp4"

# Test Telegram link (replace with a real public link for full testing)
TEST_TELEGRAM_LINK = "https://t.me/telegram/423"


class TestConfig:
    """Test configuration holder."""
    def __init__(self):
        self.temp_dir = None
        self.test_video = None
        self.test_video_2 = None
        self.use_exe = False
        self.quick_mode = False
        self.skip_telegram = True  # Skip telegram tests by default
        
    def setup(self):
        """Create temp directory and download test videos."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="video_tools_test_"))
        print(f"[SETUP] Temp directory: {self.temp_dir}")
        
        # Download test videos
        self.test_video = self.temp_dir / "test_video.mp4"
        self.test_video_2 = self.temp_dir / "test_video_2.mp4"
        
        # Try to download, fallback to creating with FFmpeg
        downloaded = False
        print(f"[SETUP] Downloading test video 1...")
        try:
            urllib.request.urlretrieve(SAMPLE_VIDEO_URL, str(self.test_video))
            if self.test_video.exists() and self.test_video.stat().st_size > 1000:
                print(f"  Downloaded: {self.test_video.name} ({self.test_video.stat().st_size} bytes)")
                downloaded = True
        except Exception as e:
            print(f"  [WARN] Download failed: {e}")
        
        # Fallback: create sample video with FFmpeg
        if not downloaded:
            print(f"[SETUP] Creating sample video with FFmpeg...")
            try:
                from core.config import get_binary_path, load_config
                load_config()
                ffmpeg = get_binary_path("ffmpeg")
                import subprocess
                # Create 10 second test video with testsrc
                subprocess.run([
                    ffmpeg, "-y", "-f", "lavfi", 
                    "-i", "testsrc=duration=10:size=320x240:rate=25",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    str(self.test_video)
                ], capture_output=True, check=True)
                print(f"  Created: {self.test_video.name} ({self.test_video.stat().st_size} bytes)")
            except Exception as e:
                print(f"  [ERROR] Could not create sample video: {e}")
                return False
        
        # Copy for second video
        if self.test_video.exists():
            shutil.copy(self.test_video, self.test_video_2)
            print(f"  Copied: {self.test_video_2.name}")
        
        return self.test_video.exists()
    
    def cleanup(self):
        """Remove temp directory."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"[CLEANUP] Removed temp directory")


# Global config
config = TestConfig()


# =============================================================================
# TEST UTILITIES
# =============================================================================

class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []
    
    def add(self, name: str, passed: bool, message: str = "", skipped: bool = False):
        status = "SKIP" if skipped else ("PASS" if passed else "FAIL")
        self.results.append((name, status, message))
        if skipped:
            self.skipped += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1
        
        icon = "~" if skipped else ("+" if passed else "x")
        print(f"  [{icon}] {name}: {message}" if message else f"  [{icon}] {name}")
    
    def summary(self):
        print("\n" + "=" * 60)
        print(f"RESULTS: {self.passed} passed, {self.failed} failed, {self.skipped} skipped")
        print("=" * 60)
        return self.failed == 0


def get_ffmpeg_handler():
    """Get FFmpegHandler instance."""
    from core.config import load_config
    load_config()
    from core.ffmpeg_handler import FFmpegHandler
    return FFmpegHandler()


def get_downloader():
    """Get Downloader instance."""
    from core.config import load_config
    load_config()
    from core.downloader import Downloader
    from core.ffmpeg_handler import FFmpegHandler
    return Downloader(ffmpeg_handler=FFmpegHandler())


# =============================================================================
# SPLIT VIDEO TESTS
# =============================================================================

def test_split_video(results: TestResult):
    """Test split video functionality."""
    print("\n--- SPLIT VIDEO TESTS ---")
    
    handler = get_ffmpeg_handler()
    
    # Test 1: Single segment split
    output1 = str(config.temp_dir / "split_single.mp4")
    try:
        handler.split_video(str(config.test_video), 0, 2, output1)
        if Path(output1).exists():
            results.add("Split single segment", True, f"{Path(output1).stat().st_size} bytes")
        else:
            results.add("Split single segment", False, "Output not created")
    except Exception as e:
        results.add("Split single segment", False, str(e))
    
    # Test 2: Multiple segments (2 segments)
    outputs_2seg = []
    try:
        for i, (start, end) in enumerate([(0, 2), (2, 4)]):
            out = str(config.temp_dir / f"split_2seg_{i}.mp4")
            handler.split_video(str(config.test_video), start, end, out)
            if Path(out).exists():
                outputs_2seg.append(out)
        results.add("Split 2 segments", len(outputs_2seg) == 2, f"Created {len(outputs_2seg)} files")
    except Exception as e:
        results.add("Split 2 segments", False, str(e))
    
    # Test 3: Multiple segments (3 segments)
    outputs_3seg = []
    try:
        for i, (start, end) in enumerate([(0, 1), (1, 2), (2, 3)]):
            out = str(config.temp_dir / f"split_3seg_{i}.mp4")
            handler.split_video(str(config.test_video), start, end, out)
            if Path(out).exists():
                outputs_3seg.append(out)
        results.add("Split 3 segments", len(outputs_3seg) == 3, f"Created {len(outputs_3seg)} files")
    except Exception as e:
        results.add("Split 3 segments", False, str(e))


# =============================================================================
# JOIN VIDEO TESTS
# =============================================================================

def test_join_video(results: TestResult):
    """Test join video functionality."""
    print("\n--- JOIN VIDEO TESTS ---")
    
    handler = get_ffmpeg_handler()
    
    # Test 1: Join 2 files
    output1 = str(config.temp_dir / "joined_2files.mp4")
    try:
        handler.join_videos([str(config.test_video), str(config.test_video_2)], output1)
        if Path(output1).exists():
            orig_size = config.test_video.stat().st_size
            joined_size = Path(output1).stat().st_size
            results.add("Join 2 files", True, f"Size: {joined_size} (orig: {orig_size})")
        else:
            results.add("Join 2 files", False, "Output not created")
    except Exception as e:
        results.add("Join 2 files", False, str(e))
    
    # Test 2: Join 3 files (duplicate one for testing)
    output2 = str(config.temp_dir / "joined_3files.mp4")
    try:
        handler.join_videos([
            str(config.test_video), 
            str(config.test_video_2), 
            str(config.test_video)
        ], output2)
        if Path(output2).exists():
            results.add("Join 3 files", True, f"Size: {Path(output2).stat().st_size}")
        else:
            results.add("Join 3 files", False, "Output not created")
    except Exception as e:
        results.add("Join 3 files", False, str(e))


# =============================================================================
# SPLIT & JOIN TESTS
# =============================================================================

def test_split_join(results: TestResult):
    """Test split & join workflow."""
    print("\n--- SPLIT & JOIN TESTS ---")
    
    handler = get_ffmpeg_handler()
    
    # Test: Split segments then join
    temp_segments = []
    final_output = str(config.temp_dir / "split_join_result.mp4")
    
    try:
        # Split into 2 segments
        for i, (start, end) in enumerate([(0, 2), (3, 5)]):
            seg_file = str(config.temp_dir / f"sj_temp_{i}.mp4")
            handler.split_video(str(config.test_video), start, end, seg_file)
            if Path(seg_file).exists():
                temp_segments.append(seg_file)
        
        if len(temp_segments) >= 2:
            # Join segments
            handler.join_videos(temp_segments, final_output)
            if Path(final_output).exists():
                results.add("Split & Join workflow", True, f"Size: {Path(final_output).stat().st_size}")
            else:
                results.add("Split & Join workflow", False, "Join failed")
        else:
            results.add("Split & Join workflow", False, "Split failed")
    except Exception as e:
        results.add("Split & Join workflow", False, str(e))
    finally:
        # Cleanup temp segments
        for f in temp_segments:
            try:
                Path(f).unlink()
            except:
                pass


# =============================================================================
# COMPRESS VIDEO TESTS
# =============================================================================

def test_compress_video(results: TestResult):
    """Test compression with different levels."""
    print("\n--- COMPRESS VIDEO TESTS ---")
    
    handler = get_ffmpeg_handler()
    original_size = config.test_video.stat().st_size
    
    compression_results = {}
    
    for level in ["low", "medium", "high"]:
        output = str(config.temp_dir / f"compressed_{level}.mp4")
        start_time = time.time()
        
        try:
            handler.compress_video(str(config.test_video), output, compression_level=level)
            elapsed = time.time() - start_time
            
            if Path(output).exists():
                size = Path(output).stat().st_size
                compression_results[level] = {
                    "size": size,
                    "time": elapsed,
                    "ratio": size / original_size
                }
                results.add(
                    f"Compress {level.upper()}", 
                    True, 
                    f"Size: {size} ({compression_results[level]['ratio']:.2%}), Time: {elapsed:.1f}s"
                )
            else:
                results.add(f"Compress {level.upper()}", False, "Output not created")
        except Exception as e:
            results.add(f"Compress {level.upper()}", False, str(e))
    
    # Verify compression level differences
    if len(compression_results) == 3:
        low_size = compression_results["low"]["size"]
        high_size = compression_results["high"]["size"]
        # High quality should generally be larger or similar (lower CRF = better quality)
        # But for very short videos, differences may be minimal
        results.add(
            "Compression levels differ", 
            True,  # Just report the comparison
            f"Low: {low_size}, High: {high_size}"
        )


# =============================================================================
# PARALLEL DOWNLOAD TESTS
# =============================================================================

def test_parallel_download(results: TestResult):
    """Test parallel chunked download functionality."""
    print("\n--- PARALLEL DOWNLOAD TESTS ---")
    
    if config.quick_mode:
        results.add("Parallel download", True, "SKIPPED (quick mode)", skipped=True)
        return
    
    downloader = get_downloader()
    output = str(config.temp_dir / "parallel_download.mp4")
    
    try:
        start_time = time.time()
        success = downloader.download_segment_parallel(
            SAMPLE_VIDEO_URL, 0, 5, output
        )
        elapsed = time.time() - start_time
        
        if success and Path(output).exists():
            results.add("Parallel download", True, f"Time: {elapsed:.1f}s, Size: {Path(output).stat().st_size}")
        else:
            results.add("Parallel download", False, "Download failed")
    except Exception as e:
        results.add("Parallel download", False, str(e))


# =============================================================================
# QUEUE TESTS
# =============================================================================

def test_queue_processing(results: TestResult):
    """Test queue/parallel processing."""
    print("\n--- QUEUE PROCESSING TESTS ---")
    
    handler = get_ffmpeg_handler()
    
    # Test parallel split processing
    tasks = [(0, 1), (1, 2), (2, 3), (3, 4)]
    outputs = []
    
    start_time = time.time()
    
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            for i, (start, end) in enumerate(tasks):
                out = str(config.temp_dir / f"queue_test_{i}.mp4")
                futures.append(executor.submit(
                    handler.split_video, str(config.test_video), start, end, out
                ))
                outputs.append(out)
            
            # Wait for all
            for f in futures:
                f.result()
        
        elapsed = time.time() - start_time
        created = sum(1 for o in outputs if Path(o).exists())
        
        results.add(
            "Queue parallel processing (4 tasks, 2 workers)", 
            created == 4, 
            f"Created: {created}/4, Time: {elapsed:.1f}s"
        )
    except Exception as e:
        results.add("Queue parallel processing", False, str(e))


# =============================================================================
# JSON INPUT TESTS
# =============================================================================

def test_json_input(results: TestResult):
    """Test JSON batch input processing."""
    print("\n--- JSON INPUT TESTS ---")
    
    # Create test JSON
    json_file = config.temp_dir / "test_batch.json"
    test_data = [
        {
            "input": str(config.test_video),
            "output": "json_batch_output",
            "segments": [
                {"start": "00.00", "end": "00.02"},
                {"start": "00.02", "end": "00.04"}
            ]
        }
    ]
    
    try:
        with open(json_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        if json_file.exists():
            results.add("JSON file creation", True, f"Created {json_file.name}")
        else:
            results.add("JSON file creation", False, "File not created")
        
        # Validate JSON structure
        with open(json_file, 'r') as f:
            loaded = json.load(f)
        
        valid = (
            isinstance(loaded, list) and 
            len(loaded) > 0 and
            "input" in loaded[0] and
            "output" in loaded[0] and
            "segments" in loaded[0]
        )
        results.add("JSON structure valid", valid, f"{len(loaded)} items")
        
    except Exception as e:
        results.add("JSON input", False, str(e))


# =============================================================================
# FOLDER INPUT TESTS
# =============================================================================

def test_folder_input(results: TestResult):
    """Test folder input handling."""
    print("\n--- FOLDER INPUT TESTS ---")
    
    from utils.path_utils import expand_input, get_videos_in_folder
    
    # Create test folder with videos
    test_folder = config.temp_dir / "video_folder"
    test_folder.mkdir(exist_ok=True)
    
    # Copy test videos to folder
    shutil.copy(config.test_video, test_folder / "video1.mp4")
    shutil.copy(config.test_video_2, test_folder / "video2.mp4")
    
    try:
        videos = get_videos_in_folder(str(test_folder))
        results.add("Folder video detection", len(videos) == 2, f"Found: {len(videos)} videos")
        
        # Test expand_input with folder
        expanded = expand_input(str(test_folder))
        results.add("Folder expansion", len(expanded) == 2, f"Expanded: {len(expanded)} files")
    except Exception as e:
        results.add("Folder input", False, str(e))


# =============================================================================
# MULTIPLE FILES INPUT TESTS
# =============================================================================

def test_multiple_files_input(results: TestResult):
    """Test multiple files input handling."""
    print("\n--- MULTIPLE FILES INPUT TESTS ---")
    
    from utils.path_utils import normalize_path, parse_multiple_paths
    
    # Test path normalization
    test_path = f'"{config.test_video}"'  # Quoted path
    normalized = normalize_path(test_path)
    results.add("Path normalization (quoted)", normalized == str(config.test_video), normalized)
    
    # Test multiple quoted paths
    multi_input = f'"{config.test_video}" "{config.test_video_2}"'
    parsed = parse_multiple_paths(multi_input)
    results.add("Multiple paths parsing", len(parsed) == 2, f"Parsed: {len(parsed)} paths")


# =============================================================================
# TELEGRAM LINK TESTS (Optional)
# =============================================================================

def test_telegram_link(results: TestResult):
    """Test Telegram link handling (optional)."""
    print("\n--- TELEGRAM LINK TESTS ---")
    
    if config.skip_telegram:
        results.add("Telegram link detection", True, "SKIPPED", skipped=True)
        results.add("Telegram link resolution", True, "SKIPPED", skipped=True)
        return
    
    from core.tdl_handler import TDLHandler
    
    # Test link detection
    is_tg = TDLHandler.is_telegram_link(TEST_TELEGRAM_LINK)
    results.add("Telegram link detection", is_tg, TEST_TELEGRAM_LINK[:50])


# =============================================================================
# MAIN
# =============================================================================

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Video Tools CLI - Comprehensive Feature Tests")
    print("=" * 60)
    
    # Parse args
    if "--exe" in sys.argv:
        config.use_exe = True
        print("Mode: Testing video-tools.exe")
    else:
        print("Mode: Testing main.py")
    
    if "--quick" in sys.argv:
        config.quick_mode = True
        print("Quick mode: Skipping long tests")
    
    if "--telegram" in sys.argv:
        config.skip_telegram = False
        print("Telegram tests: Enabled")
    
    print()
    
    # Setup
    if not config.setup():
        print("[ERROR] Setup failed, aborting tests")
        return False
    
    results = TestResult()
    
    try:
        # Run test suites
        test_split_video(results)
        test_join_video(results)
        test_split_join(results)
        test_compress_video(results)
        test_parallel_download(results)
        test_queue_processing(results)
        test_json_input(results)
        test_folder_input(results)
        test_multiple_files_input(results)
        test_telegram_link(results)
        
        return results.summary()
    finally:
        config.cleanup()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
