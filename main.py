import sys
import os
import json
import ctypes
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator

from core.config import (
    ensure_config, load_config, get_env, ensure_output_extension, 
    get_output_path, ENV_PATH, COMPRESSION_LEVELS
)
from core.ffmpeg_handler import FFmpegHandler
from core.tdl_handler import TDLHandler
from core.downloader import Downloader
from utils.helpers import time_str_to_seconds
from utils.logger import log
from utils.path_utils import normalize_path, expand_input, get_input_summary
import colorama
from termcolor import colored

# Initialize colorama
colorama.init()

# Application version
VERSION = "1.6.0"


def set_console_title(title: str):
    """Set console window title."""
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetConsoleTitleW(title)


def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    set_console_title(f"Video Tools CLI v{VERSION}")
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
        self.max_queue = int(get_env("MAX_QUEUE", 2))
        self.download_max_connection = int(get_env("DOWNLOAD_MAX_CONNECTION", 4))
        self.override_encoding = get_env("OVERRIDE_ENCODING", "")
        self.compression_level = get_env("COMPRESSION_LEVEL", "medium")
        # Shared instances
        self.ffmpeg = FFmpegHandler()
        self.tdl = TDLHandler()
        self.downloader = Downloader(ffmpeg_handler=self.ffmpeg, max_workers=self.download_max_connection)

    def run(self):
        while True:
            print_banner()
            print(f"Queue: {self.max_queue} | Connections: {self.download_max_connection} | Compression: {self.compression_level}")
            action = inquirer.select(
                message="Select action:",
                choices=[
                    Choice(value="split", name="Split Video"),
                    Choice(value="join", name="Join Video"),
                    Choice(value="split_join", name="Split & Join Video"),
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
            elif action in ["split", "join", "split_join", "compress"]:
                self.handle_action(action)

    def show_settings(self):
        """Show settings menu for editing configuration."""
        while True:
            print_banner()
            log.section("SETTINGS")
            
            log.detail("Max Queue (parallel)", str(self.max_queue))
            log.detail("Download Connections", str(self.download_max_connection))
            log.detail("Compression Level", self.compression_level)
            log.detail("Override Encoding", self.override_encoding or "(auto-detect)")
            
            setting = inquirer.select(
                message="Select setting to modify:",
                choices=[
                    Choice(value="max_queue", name=f"Max Queue [{self.max_queue}]"),
                    Choice(value="connections", name=f"Download Connections [{self.download_max_connection}]"),
                    Choice(value="compression", name=f"Compression Level [{self.compression_level}]"),
                    Choice(value="encoding", name=f"Override Encoding [{self.override_encoding or 'auto'}]"),
                    Separator(),
                    Choice(value="back", name="Back"),
                ],
            ).execute()
            
            if setting == "back":
                break
            elif setting == "max_queue":
                val = inquirer.text(
                    message="Enter Max Queue (1-16):",
                    default=str(self.max_queue)
                ).execute()
                if val.isdigit() and 1 <= int(val) <= 16:
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
            elif setting == "compression":
                val = inquirer.select(
                    message="Select compression level:",
                    choices=[
                        Choice(value="low", name="Low (fast, larger file)"),
                        Choice(value="medium", name="Medium (balanced)"),
                        Choice(value="high", name="High (slow, smaller file)"),
                    ],
                    default=self.compression_level
                ).execute()
                self.compression_level = val
                self._save_env("COMPRESSION_LEVEL", val)
                log.success(f"Compression set to {val}")
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
            env_content = {}
            if ENV_PATH.exists():
                with open(ENV_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            k, v = line.split('=', 1)
                            env_content[k] = v
            
            env_content[key] = value
            
            with open(ENV_PATH, 'w', encoding='utf-8') as f:
                for k, v in env_content.items():
                    f.write(f"{k}={v}\n")
        except Exception as e:
            log.error(f"Failed to save setting: {e}")

    def handle_action(self, action):
        while True:
            print(f"\nQueue: {self.max_queue} | Action: {action}")
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
        elif action == "split_join":
            self.do_split_join_flow()
        elif action == "join":
            raw_input = inquirer.text(
                message="Video path / folder / URL (supports drag & drop):"
            ).execute()
            files = expand_input(raw_input)
            if files:
                self.do_join_flow_multi(files)
        elif action == "compress":
            raw_input = inquirer.text(
                message="Video path / folder / URL (supports drag & drop):"
            ).execute()
            files = expand_input(raw_input)
            if files:
                self.do_compress_flow_parallel(files)

    def do_split_flow(self):
        """Split video into segments."""
        raw_input = inquirer.text(message="Video path / URL:").execute()
        url_or_path = normalize_path(raw_input)
        
        # Get source folder for output
        source_folder = Path(url_or_path).parent if not url_or_path.startswith("http") else Path(".")
        default_output = Path(url_or_path).stem if not url_or_path.startswith("http") else "output"
        
        output_base = inquirer.text(
            message="Output name (empty = source name):",
            default=""
        ).execute()
        
        if not output_base.strip():
            output_base = default_output
        
        segments = self._collect_segments()
        if not segments:
            log.warning("No segments defined.")
            return

        is_url = url_or_path.startswith("http") or TDLHandler.is_telegram_link(url_or_path)
        
        if is_url:
            self._process_url_split(url_or_path, output_base, segments, Path("."))
        else:
            self._process_local_split_parallel(url_or_path, output_base, segments, source_folder)

    def do_split_join_flow(self):
        """Split multiple segments and join them into one video."""
        raw_input = inquirer.text(message="Video path / URL:").execute()
        url_or_path = normalize_path(raw_input)
        
        source_folder = Path(url_or_path).parent if not url_or_path.startswith("http") and not TDLHandler.is_telegram_link(url_or_path) else Path(".")
        default_output = Path(url_or_path).stem if not url_or_path.startswith("http") and not TDLHandler.is_telegram_link(url_or_path) else "output"
        
        output_name = inquirer.text(
            message="Final output name (empty = source_joined):",
            default=""
        ).execute()
        
        if not output_name.strip():
            output_name = f"{default_output}_joined.mp4"
        else:
            output_name = ensure_output_extension(output_name)
        
        # Collect segments
        segments = self._collect_segments()
        if len(segments) < 1:
            log.warning("Need at least 1 segment.")
            return

        log.section("SPLIT & JOIN")
        log.detail("Segments", str(len(segments)))
        log.detail("Output", output_name)
        
        is_url = url_or_path.startswith("http") or TDLHandler.is_telegram_link(url_or_path)
        is_tdl = TDLHandler.is_telegram_link(url_or_path)
        
        # Create temp segments
        temp_files = []
        temp_base = f"_temp_segment_{os.getpid()}"
        final_url = url_or_path
        
        try:
            # Resolve Telegram link if needed
            if is_tdl:
                log.info("Resolving Telegram link...")
                self.tdl.start_serve(url_or_path)
                resolved = self.tdl.get_download_link()
                if not resolved:
                    log.error("Failed to resolve Telegram link.")
                    return
                final_url = resolved
                log.success("Telegram link resolved.")
            
            if is_url:
                # Download segments from URL using parallel chunked download
                for i, (start, end) in enumerate(segments):
                    temp_file = str(source_folder / f"{temp_base}_{i}.mp4")
                    start_sec = time_str_to_seconds(start)
                    end_sec = time_str_to_seconds(end)
                    if end_sec <= start_sec:
                        continue
                    log.info(f"Downloading segment {i+1}/{len(segments)} ({self.download_max_connection} connections)...")
                    try:
                        # Use parallel chunked download
                        if self.downloader.download_segment_parallel(final_url, start_sec, end_sec, temp_file):
                            temp_files.append(temp_file)
                        else:
                            log.error(f"Segment {i+1} download failed")
                    except Exception as e:
                        log.error(f"Segment {i+1} failed", details=str(e))
            else:
                # Split local file in parallel
                def split_segment(args):
                    i, start, end = args
                    temp_file = str(source_folder / f"{temp_base}_{i}.mp4")
                    start_sec = time_str_to_seconds(start)
                    end_sec = time_str_to_seconds(end)
                    if end_sec <= start_sec:
                        return None
                    try:
                        self.ffmpeg.split_video(url_or_path, start_sec, end_sec, temp_file)
                        return (i, temp_file)
                    except Exception as e:
                        log.error(f"Segment {i+1} failed", details=str(e))
                        return None
                
                segment_args = [(i, s, e) for i, (s, e) in enumerate(segments)]
                
                with ThreadPoolExecutor(max_workers=self.max_queue) as executor:
                    futures = {executor.submit(split_segment, args): args[0] for args in segment_args}
                    results = []
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            results.append(result)
                            log.step(len(results), len(segments), "Segment split complete")
                    
                    # Sort by index and extract files
                    results.sort(key=lambda x: x[0])
                    temp_files = [f for _, f in results]
            
            if len(temp_files) < 1:
                log.error("No segments to join.")
                return
            
            # Join segments
            log.info(f"Joining {len(temp_files)} segments...")
            final_output = str(source_folder / output_name)
            self.ffmpeg.join_videos(temp_files, final_output)
            log.success(f"Created {output_name}")
            
        finally:
            # Stop TDL if it was started
            if is_tdl:
                self.tdl.stop_serve()
            # Cleanup temp files
            for f in temp_files:
                try:
                    Path(f).unlink()
                except:
                    pass

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

    def _process_url_split(self, url, output_base, segments, output_folder):
        """Process split from URL."""
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
            download_segments = []
            for i, (start, end) in enumerate(segments):
                start_sec = time_str_to_seconds(start)
                end_sec = time_str_to_seconds(end)
                if end_sec <= start_sec:
                    log.warning(f"Invalid range {start}-{end}, skipping.")
                    continue
                out_file = str(output_folder / ensure_output_extension(f"{output_base}_{i+1}"))
                download_segments.append((start_sec, end_sec, out_file))
            
            if not download_segments:
                log.error("No valid segments to process.")
                return
            
            log.info(f"Processing {len(download_segments)} segment(s)...")
            results = self.downloader.batch_download_segments(final_url, download_segments)
            
            success_count = sum(1 for _, success in results if success)
            log.success(f"Completed: {success_count}/{len(results)} segments")
            
        finally:
            if is_tdl:
                self.tdl.stop_serve()

    def _process_local_split_parallel(self, input_path, output_base, segments, output_folder):
        """Process split from local file with parallel processing."""
        log.info(f"Processing {len(segments)} splits with {self.max_queue} parallel workers...")
        
        def split_task(args):
            i, start, end = args
            start_sec = time_str_to_seconds(start)
            end_sec = time_str_to_seconds(end)
            if end_sec <= start_sec:
                return (i, False, f"Invalid range {start}-{end}")
            out_file = str(output_folder / ensure_output_extension(f"{output_base}_{i+1}"))
            try:
                self.ffmpeg.split_video(input_path, start_sec, end_sec, out_file)
                return (i, True, Path(out_file).name)
            except Exception as e:
                return (i, False, str(e))
        
        segment_args = [(i, s, e) for i, (s, e) in enumerate(segments)]
        
        with ThreadPoolExecutor(max_workers=self.max_queue) as executor:
            futures = {executor.submit(split_task, args): args[0] for args in segment_args}
            completed = 0
            success_count = 0
            
            for future in as_completed(futures):
                completed += 1
                idx, success, msg = future.result()
                if success:
                    success_count += 1
                    log.success(f"[{completed}/{len(segments)}] Created {msg}")
                else:
                    log.error(f"[{completed}/{len(segments)}] Failed: {msg}")
        
        log.success(f"Completed: {success_count}/{len(segments)} segments")

    def handle_download_if_needed(self, path):
        """Checks if input is URL, downloads if so."""
        path = normalize_path(path)
        
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
            output_name = "downloaded_video.mp4"
            if self.downloader.smart_download(path, output_name):
                return output_name
            else:
                log.error("Download failed.")
                return None

    def do_join_flow_multi(self, files: list):
        """Join multiple videos into one."""
        inputs = []
        
        for f in files:
            local_path = self.handle_download_if_needed(f)
            if local_path:
                inputs.append(local_path)
        
        if len(inputs) < 2:
            if len(inputs) == 1:
                log.info(f"First video: {Path(inputs[0]).name}")
            
            second_input = inquirer.text(message="Second video path / URL:").execute()
            second_path = self.handle_download_if_needed(normalize_path(second_input))
            if second_path:
                inputs.append(second_path)
            
            if len(inputs) < 2:
                log.error("Need at least 2 videos to join.")
                return
        
        while True:
            confirm = inquirer.confirm(message=f"Add another video? (current: {len(inputs)})", default=False).execute()
            if not confirm:
                break
            
            additional_input = inquirer.text(message="Video path / URL:").execute()
            local_path = self.handle_download_if_needed(normalize_path(additional_input))
            if local_path:
                inputs.append(local_path)

        first_file = Path(inputs[0])
        source_folder = first_file.parent
        
        output_name = inquirer.text(
            message="Output filename (empty = name_join.mp4):",
            default=""
        ).execute()
        
        if not output_name.strip():
            output_name = f"{first_file.stem}_join.mp4"
        else:
            output_name = ensure_output_extension(output_name)
        
        log.section("JOIN VIDEO")
        log.detail("Input files", str(len(inputs)))
        log.detail("Output", output_name)
        
        final_output = str(source_folder / output_name)
        
        try:
            self.ffmpeg.join_videos(inputs, final_output)
            log.success(f"Created {output_name}")
        except Exception as e:
            log.error(f"Failed to join videos", details=str(e))

    def do_compress_flow_parallel(self, files: list):
        """Compress multiple videos with parallel processing."""
        log.section("COMPRESS VIDEO")
        log.detail("Files to process", str(len(files)))
        log.detail("Parallel workers", str(self.max_queue))
        log.detail("Compression level", self.compression_level)
        
        def compress_task(file_path):
            file_path = normalize_path(file_path)
            local_path = self.handle_download_if_needed(file_path)
            if not local_path:
                return (file_path, False, "Download failed")
            
            input_file = Path(local_path)
            source_folder = input_file.parent
            output_name = f"{input_file.stem}_compressed.mp4"
            output_path = str(source_folder / output_name)
            
            try:
                self.ffmpeg.compress_video(local_path, output_path, compression_level=self.compression_level)
                return (input_file.name, True, output_name)
            except Exception as e:
                return (input_file.name, False, str(e))
        
        # Single file - ask for output name
        if len(files) == 1:
            file_path = normalize_path(files[0])
            local_path = self.handle_download_if_needed(file_path)
            if not local_path:
                return
            
            input_file = Path(local_path)
            source_folder = input_file.parent
            
            output_name = inquirer.text(
                message="Output name (empty = replace source):",
                default=""
            ).execute()
            
            if not output_name.strip():
                output_name = f"{input_file.stem}.mp4"
            else:
                output_name = ensure_output_extension(output_name)
            
            output_path = str(source_folder / output_name)
            
            try:
                self.ffmpeg.compress_video(local_path, output_path, compression_level=self.compression_level)
                log.success(f"Created {output_name}")
            except Exception as e:
                log.error(f"Compression failed", details=str(e))
            return
        
        # Multiple files - process in parallel
        with ThreadPoolExecutor(max_workers=self.max_queue) as executor:
            futures = {executor.submit(compress_task, f): f for f in files}
            completed = 0
            success_count = 0
            
            for future in as_completed(futures):
                completed += 1
                name, success, msg = future.result()
                if success:
                    success_count += 1
                    log.success(f"[{completed}/{len(files)}] Created {msg}")
                else:
                    log.error(f"[{completed}/{len(files)}] Failed: {name} - {msg}")
        
        log.success(f"Batch completed: {success_count}/{len(files)} files")

    def process_json_input(self, action):
        """Process batch operations from JSON file."""
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
        
        input_url = normalize_path(input_url)
            
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
                log.info(f"Processing {len(download_segments)} segments...")
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
