"""
Unit tests for FFmpegHandler with mocked dependencies.
"""
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import json
from pathlib import Path


class TestFFmpegHandler(unittest.TestCase):
    def setUp(self):
        with patch('core.ffmpeg_handler.get_binary_path') as mock_gbp, \
             patch('core.ffmpeg_handler.log'):  # Mock logger
            mock_gbp.side_effect = lambda x: x
            from core.ffmpeg_handler import FFmpegHandler
            self.handler = FFmpegHandler()

    @patch('subprocess.run')
    def test_get_video_info_success(self, mock_run):
        mock_output = {
            "format": {"duration": "60.0"},
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_output), 
            returncode=0,
            stderr=""
        )
        
        info = self.handler.get_video_info("dummy.mp4")
        self.assertEqual(info, mock_output)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_get_duration(self, mock_run):
        mock_output = {"format": {"duration": "120.5"}}
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_output), 
            returncode=0,
            stderr=""
        )
        
        duration = self.handler.get_duration("dummy.mp4")
        self.assertEqual(duration, 120.5)

    @patch('core.ffmpeg_handler.log')
    @patch('subprocess.run')
    def test_split_video(self, mock_run, mock_log):
        # Configure mock to return success
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        
        self.handler.split_video("in.mp4", 0, 10, "out.mp4")
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        cmd = args[0]
        self.assertIn("-ss", cmd)
        self.assertIn("0", cmd)
        self.assertIn("-to", cmd)
        self.assertIn("10", cmd)

    @patch('subprocess.run')
    def test_detect_hw_encoders(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="h264_nvenc hevc_nvenc libx264", 
            returncode=0
        )
        # Clear cache
        self.handler._detected_encoders = None
        
        encoders = self.handler.detect_hw_encoders()
        self.assertIn("h264_nvenc", encoders)
        self.assertIn("hevc_nvenc", encoders)

    @patch('core.ffmpeg_handler.log')
    @patch('core.ffmpeg_handler.FFmpegHandler.get_video_info')
    @patch('core.ffmpeg_handler.FFmpegHandler.detect_hw_encoders')
    @patch('subprocess.run')
    def test_compress_video_nvenc(self, mock_run, mock_detect, mock_info, mock_log):
        mock_info.return_value = {
            "format": {"duration": "10.0"},
            "streams": [{"codec_type": "video", "width": 3840, "height": 2160}]
        }
        mock_detect.return_value = ["hevc_nvenc"]
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        
        self.handler.compress_video("large.mp4", "compressed.mp4", show_progress=False)
        
        # Verify subprocess.run was called
        mock_run.assert_called()
        args, _ = mock_run.call_args
        cmd = args[0]
        self.assertIn("hevc_nvenc", cmd)
        # Check scale filter is present
        self.assertIn("-vf", cmd)

    @patch('core.ffmpeg_handler.log')
    @patch('subprocess.run')
    def test_join_videos(self, mock_run, mock_log):
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        
        # Clean up any existing join_list.txt
        list_file = Path("join_list.txt")
        if list_file.exists():
            list_file.unlink()
        
        self.handler.join_videos(["video1.mp4", "video2.mp4"], "output.mp4")
        
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        cmd = args[0]
        self.assertIn("-f", cmd)
        self.assertIn("concat", cmd)


if __name__ == '__main__':
    unittest.main()
