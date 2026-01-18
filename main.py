import sys
import os
import json
from pathlib import Path
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator

from core.config import ensure_config, load_config, get_env, ensure_output_extension, get_output_name, ENV_PATH
from core.ffmpeg_handler import FFmpegHandler
from core.tdl_handler import TDLHandler
from core.downloader import Downloader
from utils.helpers import time_str_to_seconds
from utils.logger import log
import colorama
from termcolor import colored

# Initialize colorama
colorama.init()

# Application version
VERSION = "1.4.0"


def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = r"""
       _      _             _             _     
      (_)    | |           | |           | |    
 __   ___  __| | ___  ___  | |_ ___   ___| |___ 
 \ \ / / |/ _` |/ _ \/ _ \ | __/ _ \ / _ \ / __|
  \ V /| | (_| |  __/ (_) || || (_) | (_) | \__ \
   \_/ |_|\__,_|\___|\___/  \__\___/ \___/|_|___/
"""
    print(colored(banner, 'cyan', attrs=['bold']))
    print(colored(f"Version: {VERSION}", 'yellow'))
    print(colored("Crafted by: thio", 'magenta'))
    print("\n")


# Ensure config is loaded
ensure_config()
load_config()


class VideoCLI:
    def __init__(self):
        self.max_queue = int(get_env("MAX_QUEUE", 4))
        self.download_max_connection = int(get_env("DOWNLOAD_MAX_CONNECTION", 16))
        self.override_encoding = get_env("OVERRIDE_ENCODING", "")
        # Shared instances for better resource management
        self.ffmpeg = FFmpegHandler()
        self.tdl = TDLHandler()
        # Inject shared ffmpeg handler into downloader with DOWNLOAD_MAX_CONNECTION
        self.downloader = Downloader(ffmpeg_handler=self.ffmpeg, max_workers=self.download_max_connection)

    def run(self):
        while True:
            print_banner()
            print(f"Max Queue: {self.max_queue} | Connections: {self.download_max_connection}")
            action = inquirer.select(
                message="Select action:",
                choices=[
                    Choice(value="split", name="Split Video"),
                    Choice(value="join", name="Join Video"),
                    Choice(value="compress", name="Compress Video"),
                    Separator(),
                    Choice(value="settings", name="Settings"),
                    Choice(value="exit", name="Exit"),
                ],
                default="split",
            ).execute()

            if action == "exit":
                sys.exit(0)
            elif action == "settings":
                self.show_settings()
            elif action in ["split", "join", "compress"]:
                self.handle_action(action)

    def show_settings(self):
        """Show settings menu for editing .env configuration."""
        while True:
            print_banner()
            log.section("SETTINGS")
            
            # Display current values
            log.detail("Max Queue", str(self.max_queue))
            log.detail("Download Connections", str(self.download_max_connection))
            log.detail("Override Encoding", self.override_encoding or "(auto-detect)")
            
            setting = inquirer.select(
                message="Select setting to modify:",
                choices=[
                    Choice(value="max_queue", name=f"Max Queue [{self.max_queue}]"),
                    Choice(value="connections", name=f"Download Connections [{self.download_max_connection}]"),
                    Choice(value="encoding", name=f"Override Encoding [{self.override_encoding or 'auto'}]"),
                    Separator(),
                    Choice(value="back", name="Back"),
                ],
            ).execute()
            
            if setting == "back":
                break
            elif setting == "max_queue":
                val = inquirer.text(
                    message="Enter Max Queue (1-100):",
                    default=str(self.max_queue)
                ).execute()
                if val.isdigit() and 1 <= int(val) <= 100:
                    self.max_queue = int(val)
                    self._save_env("MAX_QUEUE", val)
                    log.success(f"Max Queue set to {val}")
            elif setting == "connections":
                val = inquirer.text(
                    message="Enter Download Connections (1-64):",
                    default=str(self.download_max_connection)
                ).execute()
                if val.isdigit() and 1 <= int(val) <= 64:
                    self.download_max_connection = int(val)
                    self.downloader.max_workers = int(val)
                    self._save_env("DOWNLOAD_MAX_CONNECTION", val)
                    log.success(f"Download Connections set to {val}")
            elif setting == "encoding":
                encoders = self.ffmpeg.detect_hw_encoders()
                choices = [Choice(value="", name="Auto-detect (recommended)")]
                for enc in encoders:
                    choices.append(Choice(value=enc, name=enc))
                choices.append(Choice(value="libx264", name="libx264 (CPU)"))
                choices.append(Choice(value="libx265", name="libx265 (CPU)"))
                
                val = inquirer.select(
                    message="Select encoder:",
                    choices=choices,
                    default=self.override_encoding or ""
                ).execute()
                
                self.override_encoding = val
                self._save_env("OVERRIDE_ENCODING", val)
                log.success(f"Encoder set to {val or 'auto-detect'}")

    def _save_env(self, key: str, value: str):
        """Save a setting to .env file."""
        try:
            # Read current .env
            env_content = {}
            if ENV_PATH.exists():
                with open(ENV_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            k, v = line.split('=', 1)
                            env_content[k] = v
            
            # Update value
            env_content[key] = value
            
            # Write back
            with open(ENV_PATH, 'w', encoding='utf-8') as f:
                for k, v in env_content.items():
                    f.write(f"{k}={v}\n")
        except Exception as e:
            log.error(f"Failed to save setting: {e}")

    def handle_action(self, action):
        while True:
            print(f"\nMax Queue: {self.max_queue} | Action: {action}")
            source = inquirer.select(
                message="Select source:",
                choices=[
                    Choice(value="manual", name="Manual Input"),
                    Choice(value="json", name="JSON File"),
                    Choice(value="back", name="Back"),
                ],
            ).execute()

            if source == "back":
                break
            
            if source == "manual":
                self.process_manual_input(action)
            elif source == "json":
                self.process_json_input(action)

    def process_manual_input(self, action):
        log.section(f"Action: {action.upper()}")
        
        if action == "split":
            self.do_split_flow()
            return
            
        url_or_path = inquirer.text(message="Video URL / path:").execute()
        
        local_path = self.handle_download_if_needed(url_or_path)
        if not local_path:
            return

        if action == "join":
            self.do_join_flow(url_or_path)
        elif action == "compress":
            self.do_compress_flow(local_path)

    def do_split_flow(self):
        """Unified split flow for both local files and URLs with concurrent processing."""
        # 1. Get input
        url_or_path = inquirer.text(message="Video URL / path:").execute()
        
        # 2. Get output base name (with smart default)
        default_output = Path(url_or_path).stem if not url_or_path.startswith("http") else "output"
        output_base = inquirer.text(
            message="Output name (empty = replace source):",
            default=""
        ).execute()
        
        # Handle empty output - use source name
        if not output_base.strip():
            output_base = default_output
        
        # 3. Collect segments
        segments = self._collect_segments()
        if not segments:
            log.warning("No segments defined.")
            return

        # 4. Process based on input type
        is_url = url_or_path.startswith("http") or TDLHandler.is_telegram_link(url_or_path)
        
        if is_url:
            self._process_url_split(url_or_path, output_base, segments)
        else:
            self._process_local_split(url_or_path, output_base, segments)

    def _collect_segments(self):
        """Collect time segments from user input."""
        segments = []
        while True:
            start = inquirer.text(message="Start Time (HH.MM):").execute()
            end = inquirer.text(message="End Time (HH.MM):").execute()
            segments.append((start, end))
            
            confirm = inquirer.confirm(message="Add another segment?", default=False).execute()
            if not confirm:
                break
        return segments

    def _process_url_split(self, url, output_base, segments):
        """Process split from URL with concurrent downloading."""
        is_tdl = TDLHandler.is_telegram_link(url)
        final_url = url
        
        if is_tdl:
            log.info("Resolving Telegram link...")
            self.tdl.start_serve(url)
            resolved = self.tdl.get_download_link()
            if not resolved:
                log.error("Failed to resolve Telegram link.")
                self.tdl.stop_serve()
                return
            final_url = resolved
        
        try:
            # Prepare segments for batch processing
            download_segments = []
            for i, (start, end) in enumerate(segments):
                start_sec = time_str_to_seconds(start)
                end_sec = time_str_to_seconds(end)
                if end_sec <= start_sec:
                    log.warning(f"Invalid range {start}-{end}, skipping.")
                    continue
                out_file = ensure_output_extension(f"{output_base}_{i+1}")
                download_segments.append((start_sec, end_sec, out_file))
            
            if not download_segments:
                log.error("No valid segments to process.")
                return
            
            # Use parallel chunked download
            log.info(f"Processing {len(download_segments)} segment(s) with {self.download_max_connection} parallel connections...")
            results = self.downloader.batch_download_segments(final_url, download_segments)
            
            # Summary
            success_count = sum(1 for _, success in results if success)
            log.success(f"Completed: {success_count}/{len(results)} segments")
            
        finally:
            if is_tdl:
                self.tdl.stop_serve()

    def _process_local_split(self, input_path, output_base, segments):
        """Process split from local file."""
        log.info("Processing splits from local file...")
        for i, (start, end) in enumerate(segments):
            start_sec = time_str_to_seconds(start)
            end_sec = time_str_to_seconds(end)
            if end_sec <= start_sec:
                log.warning(f"Invalid range {start}-{end}, skipping.")
                continue
            out_file = ensure_output_extension(f"{output_base}_{i+1}")
            try:
                self.ffmpeg.split_video(input_path, start_sec, end_sec, out_file)
                log.success(f"Created {out_file}")
            except Exception as e:
                log.error(f"Failed to create {out_file}", details=str(e))

    def handle_download_if_needed(self, path):
        """Checks if input is URL, downloads if so."""
        if not (path.startswith("http") or TDLHandler.is_telegram_link(path)):
            return path
        
        if TDLHandler.is_telegram_link(path):
            log.info("Detected Telegram link...")
            self.tdl.start_serve(path)
            try:
                direct_link = self.tdl.get_download_link()
                if not direct_link:
                    log.error("Failed to retrieve download link from TDL.")
                    return None
                
                output_name = "downloaded_video.mp4"
                log.info(f"Downloading from: {direct_link}")
                if self.downloader.smart_download(direct_link, output_name):
                    return output_name
                else:
                    log.error("Download failed.")
                    return None
            finally:
                self.tdl.stop_serve()
        else:
            # Standard URL
            output_name = "downloaded_video.mp4"
            if self.downloader.smart_download(path, output_name):
                return output_name
            else:
                log.error("Download failed.")
                return None

    def do_join_flow(self, first_input):
        """Join multiple videos into one."""
        inputs = []
        
        # 1. Add first video
        local_path = self.handle_download_if_needed(first_input)
        if local_path:
            inputs.append(local_path)
        else:
            log.error("First video is invalid.")
            return
        
        # 2. Always ask for second video (required for join)
        second_input = inquirer.text(message="Second video URL / path:").execute()
        local_path = self.handle_download_if_needed(second_input)
        if local_path:
            inputs.append(local_path)
        else:
            log.error("Second video is invalid.")
            return
        
        # 3. Ask for additional videos (3rd+)
        while True:
            confirm = inquirer.confirm(message="Add another video?", default=False).execute()
            if not confirm:
                break
            
            additional_input = inquirer.text(message="Video URL / path:").execute()
            local_path = self.handle_download_if_needed(additional_input)
            if local_path:
                inputs.append(local_path)

        # 4. Get output filename
        first_file_stem = Path(inputs[0]).stem
        output_name = inquirer.text(
            message="Output filename (empty = name_join.mp4):",
            default=""
        ).execute()
        
        # Handle empty output - use first file + _join
        if not output_name.strip():
            output_name = f"{first_file_stem}_join.mp4"
        else:
            output_name = ensure_output_extension(output_name)
        
        log.section("JOIN VIDEO")
        log.detail("Input files", str(len(inputs)))
        log.detail("Output", output_name)
        
        try:
            self.ffmpeg.join_videos(inputs, output_name)
            log.success(f"Created {output_name}")
        except Exception as e:
            log.error(f"Failed to join videos", details=str(e))

    def do_compress_flow(self, input_path):
        """Compress video with auto-detected hardware acceleration."""
        input_stem = Path(input_path).stem
        
        output_name = inquirer.text(
            message="Output name (empty = replace source):",
            default=""
        ).execute()
        
        # Handle empty output - use same name as source (overwrite)
        if not output_name.strip():
            output_name = f"{input_stem}.mp4"
        else:
            output_name = ensure_output_extension(output_name)
        
        log.section("COMPRESS VIDEO")
        log.detail("Input", input_path)
        log.detail("Output", output_name)
        
        try:
            self.ffmpeg.compress_video(input_path, output_name)
            log.success(f"Created {output_name}")
        except Exception as e:
            log.error(f"Compression failed", details=str(e))

    def process_json_input(self, action):
        """Process batch operations from JSON file with concurrent downloading."""
        json_files = [f for f in os.listdir('.') if f.endswith('.json')]
        if not json_files:
            log.warning("No JSON files found in current directory.")
            return
            
        queue_file = inquirer.select(
            message="Select queue file:",
            choices=json_files
        ).execute()
        
        try:
            with open(queue_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            log.info(f"Processing {len(data)} items from {queue_file}...")
            
            for item in data:
                self._process_json_item(item)
                        
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON format", details=str(e))
        except Exception as e:
            log.error(f"Error processing JSON", details=str(e))

    def _process_json_item(self, item):
        """Process a single item from JSON batch."""
        input_url = item.get("input")
        output_base = item.get("output")
        segments = item.get("segments", [])
        
        if not input_url or not output_base:
            log.warning("Skipping invalid item (missing input or output).")
            return
            
        log.section(f"Processing: {output_base}")
        
        final_url = input_url
        is_tdl = TDLHandler.is_telegram_link(input_url)
        
        if is_tdl:
            log.info("Resolving Telegram link...")
            self.tdl.start_serve(input_url)
            resolved = self.tdl.get_download_link()
            if not resolved:
                log.error("Failed to resolve TDL link.")
                self.tdl.stop_serve()
                return
            final_url = resolved
        
        try:
            # Prepare segments for batch processing
            download_segments = []
            for i, seg in enumerate(segments):
                start = seg.get("start")
                end = seg.get("end")
                if not start or not end:
                    continue
                
                start_sec = time_str_to_seconds(str(start))
                end_sec = time_str_to_seconds(str(end))
                out_file = ensure_output_extension(f"{output_base}_{i+1}")
                download_segments.append((start_sec, end_sec, out_file))
            
            if download_segments:
                log.info(f"Processing {len(download_segments)} segments concurrently...")
                results = self.downloader.batch_download_segments(final_url, download_segments)
                success_count = sum(1 for _, success in results if success)
                log.success(f"Completed: {success_count}/{len(results)} segments")
            
        except Exception as e:
            log.error(f"Error processing item", details=str(e))
        finally:
            if is_tdl:
                self.tdl.stop_serve()


if __name__ == "__main__":
    try:
        cli = VideoCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
