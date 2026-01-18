import subprocess
import time
import requests
import logging
from bs4 import BeautifulSoup
from .config import get_binary_path

class TDLHandler:
    """Handler for Telegram Download (TDL) operations with context manager support."""
    
    def __init__(self, port=8080):
        self.tdl_bin = get_binary_path("tdl")
        self.port = port
        self.process = None
        self._current_url = None

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_serve()
        return False

    def clean_url(self, url):
        """Remove query parameters like ?t=... from Telegram links."""
        return url.split('?')[0]
    
    @staticmethod
    def is_telegram_link(url):
        """Check if URL is a Telegram link."""
        return "t.me/" in url

    def start_serve(self, url, port=None):
        """
        Start 'tdl dl --serve' in background with optimized polling.
        Returns the process object.
        """
        if port:
            self.port = port
            
        # Stop any existing process first
        self.stop_serve()
        
        clean_link = self.clean_url(url)
        self._current_url = url
        cmd = [
            self.tdl_bin,
            "dl",
            "-u", clean_link,
            "--serve",
            "--port", str(self.port)
        ]
        
        logging.info(f"Starting TDL serve: {' '.join(cmd)}")
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Optimized polling instead of fixed sleep
        if not self._wait_for_server(timeout=10):
            logging.warning("TDL server may not be fully ready, proceeding anyway...")
        
        return self.process

    def _wait_for_server(self, timeout=10, poll_interval=0.3):
        """Poll until server is ready or timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.process.poll() is not None:
                logging.error("TDL process terminated during startup.")
                return False
            if self.valid_port():
                logging.info(f"TDL server ready after {time.time() - start_time:.1f}s")
                return True
            time.sleep(poll_interval)
        return False

    def valid_port(self, port=None):
        """Check if port is open/serving."""
        check_port = port or self.port
        try:
            requests.get(f"http://localhost:{check_port}", timeout=0.5)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False

    def get_download_link(self, port=None):
        """Scrape the served page for the raw file link with optimized retries."""
        check_port = port or self.port
        base_url = f"http://localhost:{check_port}"
        max_retries = 5
        
        for i in range(max_retries):
            if self.process and self.process.poll() is not None:
                logging.error("TDL process terminated unexpectedly.")
                return None
                
            try:
                response = requests.get(base_url, timeout=2)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for link in soup.find_all('a'):
                        href = link.get('href')
                        if href and href not in ['/', '#']:
                            return f"{base_url}{href}" if href.startswith('/') else f"{base_url}/{href}"
            except requests.RequestException:
                pass
            
            if i < max_retries - 1:  # Don't log on last iteration
                logging.info(f"Waiting for TDL content... ({i+1}/{max_retries})")
                time.sleep(1)  # Reduced from 2s to 1s
            
        return None

    def resolve_url(self, telegram_url):
        """
        Convenience method: Start serve and get download link in one call.
        Returns (direct_url, is_success) tuple.
        Use with context manager for auto-cleanup.
        """
        try:
            self.start_serve(telegram_url)
            direct_link = self.get_download_link()
            if direct_link:
                return direct_link, True
            return None, False
        except Exception as e:
            logging.error(f"Error resolving Telegram URL: {e}")
            return None, False

    def stop_serve(self):
        """Kill the TDL process safely."""
        if self.process:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            except Exception as e:
                logging.warning(f"Error stopping TDL process: {e}")
            finally:
                self.process = None
                self._current_url = None
            logging.info("TDL server stopped.")
