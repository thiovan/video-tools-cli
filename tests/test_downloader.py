"""
Unit tests for Downloader with mocked dependencies.
"""
import unittest
from unittest.mock import patch, MagicMock


class TestDownloader(unittest.TestCase):
    def setUp(self):
        with patch('core.ffmpeg_handler.get_binary_path') as mock_gbp, \
             patch('core.ffmpeg_handler.log'), \
             patch('core.downloader.log'):
            mock_gbp.side_effect = lambda x: x
            from core.downloader import Downloader
            self.downloader = Downloader()

    @patch('core.downloader.log')
    @patch('subprocess.run')
    def test_smart_download_success(self, mock_run, mock_log):
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        result = self.downloader.smart_download("http://example.com/video.mp4", "out.mp4")
        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('core.downloader.log')
    @patch('subprocess.run')
    def test_smart_download_failure(self, mock_run, mock_log):
        mock_run.return_value = MagicMock(returncode=1, stderr="Error", stdout="")
        result = self.downloader.smart_download("http://example.com/video.mp4", "out.mp4")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
