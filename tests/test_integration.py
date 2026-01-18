"""
Integration tests using real video files.
Downloads a small sample video and tests actual FFmpeg operations.
"""
import unittest
import os
import tempfile
import shutil
import urllib.request
from pathlib import Path

# Skip if in CI without FFmpeg
SKIP_INTEGRATION = os.environ.get("SKIP_INTEGRATION_TESTS", "").lower() == "true"

# Sample video URL (public domain, small file)
SAMPLE_VIDEO_URL = "https://sample-videos.com/video321/mp4/240/big_buck_bunny_240p_1mb.mp4"
SAMPLE_VIDEO_DURATION = 5.0  # approximately 5 seconds


class TestIntegration(unittest.TestCase):
    """Integration tests with real video files."""
    
    @classmethod
    def setUpClass(cls):
        """Download sample video once for all tests."""
        if SKIP_INTEGRATION:
            return
        
        cls.temp_dir = tempfile.mkdtemp(prefix="video_test_")
        cls.sample_video = os.path.join(cls.temp_dir, "sample.mp4")
        
        # Download sample video
        try:
            print(f"\nDownloading sample video to {cls.sample_video}...")
            urllib.request.urlretrieve(SAMPLE_VIDEO_URL, cls.sample_video)
            
            if not os.path.exists(cls.sample_video):
                raise RuntimeError("Sample video download failed")
            
            file_size = os.path.getsize(cls.sample_video)
            print(f"Downloaded: {file_size / 1024:.1f} KB")
            
        except Exception as e:
            print(f"Warning: Could not download sample video: {e}")
            cls.sample_video = None
    
    @classmethod
    def tearDownClass(cls):
        """Cleanup temp directory."""
        if hasattr(cls, 'temp_dir') and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def setUp(self):
        """Check if sample video is available."""
        if SKIP_INTEGRATION:
            self.skipTest("Integration tests disabled")
        if not hasattr(self, 'sample_video') or not self.sample_video:
            self.skipTest("Sample video not available")
        # Import here to avoid issues when running without proper setup
        from core.ffmpeg_handler import FFmpegHandler
        with unittest.mock.patch('core.ffmpeg_handler.get_binary_path') as mock:
            mock.side_effect = lambda x: x  # Return binary name as-is
            self.handler = FFmpegHandler()
    
    def test_get_video_info_real_file(self):
        """Test getting video info from real file."""
        info = self.handler.get_video_info(self.sample_video)
        
        self.assertIsNotNone(info)
        self.assertIn('format', info)
        self.assertIn('streams', info)
        
        # Check duration exists
        self.assertIn('duration', info['format'])
        duration = float(info['format']['duration'])
        self.assertGreater(duration, 0)
        print(f"Video duration: {duration:.2f}s")
    
    def test_get_duration_real_file(self):
        """Test getting duration from real file."""
        duration = self.handler.get_duration(self.sample_video)
        
        self.assertGreater(duration, 0)
        self.assertLess(duration, 60)  # Should be a short clip
        print(f"Duration: {duration:.2f}s")
    
    def test_split_video_real_file(self):
        """Test splitting a real video file."""
        output_path = os.path.join(self.temp_dir, "split_output.mp4")
        
        # Split first 2 seconds
        self.handler.split_video(self.sample_video, 0, 2, output_path)
        
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)
        
        # Verify output duration
        output_duration = self.handler.get_duration(output_path)
        self.assertGreater(output_duration, 0)
        self.assertLessEqual(output_duration, 3)  # Allow some tolerance
        print(f"Split output duration: {output_duration:.2f}s")
    
    def test_join_videos_real_files(self):
        """Test joining real video files."""
        # First create two segments
        segment1 = os.path.join(self.temp_dir, "seg1.mp4")
        segment2 = os.path.join(self.temp_dir, "seg2.mp4")
        joined_output = os.path.join(self.temp_dir, "joined.mp4")
        
        # Create segments
        self.handler.split_video(self.sample_video, 0, 1, segment1)
        self.handler.split_video(self.sample_video, 2, 3, segment2)
        
        self.assertTrue(os.path.exists(segment1))
        self.assertTrue(os.path.exists(segment2))
        
        # Join them
        self.handler.join_videos([segment1, segment2], joined_output)
        
        self.assertTrue(os.path.exists(joined_output))
        self.assertGreater(os.path.getsize(joined_output), 0)
        
        # Verify joined duration
        joined_duration = self.handler.get_duration(joined_output)
        print(f"Joined output duration: {joined_duration:.2f}s")
    
    def test_compress_video_real_file(self):
        """Test compressing a real video file."""
        output_path = os.path.join(self.temp_dir, "compressed.mp4")
        
        # Compress
        self.handler.compress_video(self.sample_video, output_path, show_progress=False)
        
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)
        
        # Check output is valid video
        output_duration = self.handler.get_duration(output_path)
        self.assertGreater(output_duration, 0)
        print(f"Compressed output duration: {output_duration:.2f}s")
    
    def test_detect_hw_encoders(self):
        """Test hardware encoder detection."""
        encoders = self.handler.detect_hw_encoders()
        
        # Should return a list (may be empty if no HW encoders)
        self.assertIsInstance(encoders, list)
        print(f"Detected encoders: {encoders if encoders else 'None (software fallback)'}")


class TestDownloaderIntegration(unittest.TestCase):
    """Integration tests for Downloader."""
    
    @classmethod
    def setUpClass(cls):
        """Create temp directory."""
        if SKIP_INTEGRATION:
            return
        cls.temp_dir = tempfile.mkdtemp(prefix="downloader_test_")
    
    @classmethod
    def tearDownClass(cls):
        """Cleanup."""
        if hasattr(cls, 'temp_dir') and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def setUp(self):
        if SKIP_INTEGRATION:
            self.skipTest("Integration tests disabled")
        
        from core.downloader import Downloader
        from core.ffmpeg_handler import FFmpegHandler
        
        with unittest.mock.patch('core.ffmpeg_handler.get_binary_path') as mock:
            mock.side_effect = lambda x: x
            handler = FFmpegHandler()
            self.downloader = Downloader(ffmpeg_handler=handler, max_workers=2)
    
    def test_smart_download_real_url(self):
        """Test downloading from real URL."""
        output_path = os.path.join(self.temp_dir, "downloaded.mp4")
        
        success = self.downloader.smart_download(SAMPLE_VIDEO_URL, output_path)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)
        print(f"Downloaded file size: {os.path.getsize(output_path) / 1024:.1f} KB")


if __name__ == '__main__':
    unittest.main(verbosity=2)
