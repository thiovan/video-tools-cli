import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import requests
import requests_mock
from core.tdl_handler import TDLHandler

class TestTDLHandler(unittest.TestCase):
    def setUp(self):
        with patch('core.tdl_handler.get_binary_path') as mock_gbp:
            mock_gbp.side_effect = lambda x: x
            self.handler = TDLHandler()

    def test_clean_url(self):
        url = "https://t.me/c/12345/678?t=10"
        cleaned = self.handler.clean_url(url)
        self.assertEqual(cleaned, "https://t.me/c/12345/678")

    @patch('subprocess.Popen')
    def test_start_serve(self, mock_popen):
        mock_popen.return_value = MagicMock()
        self.handler.start_serve("https://t.me/video", port=8888)
        mock_popen.assert_called_once()
        args, _ = mock_popen.call_args
        cmd = args[0]
        self.assertIn("--port", cmd)
        self.assertIn("8888", cmd)

    @requests_mock.Mocker()
    def test_valid_port(self, m):
        m.get("http://localhost:8080", text="ok")
        self.assertTrue(self.handler.valid_port(8080))
        
        m.get("http://localhost:8081", exc=requests.exceptions.ConnectionError)
        self.assertFalse(self.handler.valid_port(8081))

    @patch('time.sleep', return_value=None)
    @requests_mock.Mocker()
    def test_get_download_link(self, mock_sleep, m):
        self.handler.process = MagicMock()
        self.handler.process.poll.return_value = None
        
        m.get("http://localhost:8080", text='<html><body><a href="/file.mp4">File</a></body></html>')
        
        link = self.handler.get_download_link(8080)
        self.assertEqual(link, "http://localhost:8080/file.mp4")

if __name__ == '__main__':
    unittest.main()
