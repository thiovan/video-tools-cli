"""
Unit tests for VideoCLI with mocked dependencies.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys


class TestVideoCLI(unittest.TestCase):
    def setUp(self):
        # Mock all dependencies
        with patch('core.ffmpeg_handler.get_binary_path'), \
             patch('core.tdl_handler.get_binary_path'), \
             patch('core.config.load_dotenv'), \
             patch('core.ffmpeg_handler.log'), \
             patch('core.downloader.log'), \
             patch('utils.logger.log'):
            from main import VideoCLI
            self.cli = VideoCLI()

    @patch('main.log')
    @patch('main.normalize_path', side_effect=lambda x: x)
    @patch('InquirerPy.inquirer.text')
    @patch('InquirerPy.inquirer.confirm')
    def test_do_split_flow_local(self, mock_confirm, mock_text, mock_normalize, mock_log):
        # Test do_split_flow for local file
        mock_text.return_value.execute.side_effect = ["local_video.mp4", "", "00.10", "00.20"]
        mock_confirm.return_value.execute.return_value = False  # No more segments
        
        with patch.object(self.cli.ffmpeg, 'split_video') as mock_split:
            self.cli.do_split_flow()
            mock_split.assert_called_once()
            args, _ = mock_split.call_args
            self.assertEqual(args[1], 600.0)
            self.assertEqual(args[2], 1200.0)

    @patch('main.log')
    @patch('main.normalize_path', side_effect=lambda x: x)
    @patch('InquirerPy.inquirer.text')
    @patch('InquirerPy.inquirer.confirm')
    def test_do_join_flow_multi(self, mock_confirm, mock_text, mock_normalize, mock_log):
        # Test join flow with multiple files
        mock_text.return_value.execute.return_value = "joined.mp4"
        mock_confirm.return_value.execute.return_value = False  # Don't add more
        
        with patch.object(self.cli.ffmpeg, 'join_videos') as mock_join:
            with patch.object(self.cli, 'handle_download_if_needed', side_effect=lambda x: x):
                self.cli.do_join_flow_multi(["video1.mp4", "video2.mp4"])
                mock_join.assert_called_once()
                self.assertEqual(len(mock_join.call_args[0][0]), 2)

    @patch('main.log')
    @patch('main.normalize_path', side_effect=lambda x: x)
    @patch('InquirerPy.inquirer.text')
    def test_do_compress_flow_multi_single(self, mock_text, mock_normalize, mock_log):
        mock_text.return_value.execute.return_value = "compressed_out.mp4"
        
        with patch.object(self.cli.ffmpeg, 'compress_video') as mock_compress:
            with patch.object(self.cli, 'handle_download_if_needed', side_effect=lambda x: x):
                self.cli.do_compress_flow_multi(["input.mp4"])
                mock_compress.assert_called_once()

    @patch('main.log')
    @patch('InquirerPy.inquirer.select')
    def test_show_settings_back(self, mock_select, mock_log):
        """Test settings menu returns on 'back'."""
        mock_select.return_value.execute.return_value = "back"
        self.cli.show_settings()


if __name__ == '__main__':
    unittest.main()
