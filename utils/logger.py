"""
Custom colored logging system for Video Tools CLI.
Provides rich, informative console output with colors and symbols.
"""
import sys
import time
import threading
from typing import Optional
import colorama
from termcolor import colored

# Ensure colorama works on Windows
colorama.init()


class ColorLogger:
    """Colored logger with status symbols and progress support."""
    
    # Status symbols
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    INFO = "●"
    ARROW = "→"
    PROGRESS = "◐"
    
    def __init__(self, name: str = "VideoTools"):
        self.name = name
        self._spinner_stop = threading.Event()
        self._spinner_thread: Optional[threading.Thread] = None
    
    def _format_prefix(self, level: str, symbol: str, color: str) -> str:
        """Format colored prefix with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        return f"{colored(timestamp, 'white', attrs=['dark'])} {colored(symbol, color)} "
    
    def info(self, message: str, **kwargs):
        """Log info message in cyan."""
        prefix = self._format_prefix("INFO", self.INFO, "cyan")
        print(f"{prefix}{message}", **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message in green."""
        prefix = self._format_prefix("SUCCESS", self.SUCCESS, "green")
        print(f"{prefix}{colored(message, 'green')}", **kwargs)
    
    def error(self, message: str, details: Optional[str] = None, **kwargs):
        """Log error message in red with optional details."""
        prefix = self._format_prefix("ERROR", self.ERROR, "red")
        print(f"{prefix}{colored(message, 'red')}", **kwargs)
        if details:
            # Print indented details
            for line in details.strip().split('\n'):
                print(f"         {colored(line, 'red', attrs=['dark'])}")
    
    def warning(self, message: str, **kwargs):
        """Log warning message in yellow."""
        prefix = self._format_prefix("WARNING", self.WARNING, "yellow")
        print(f"{prefix}{colored(message, 'yellow')}", **kwargs)
    
    def step(self, step_num: int, total: int, message: str, **kwargs):
        """Log numbered step."""
        step_str = colored(f"[{step_num}/{total}]", "magenta", attrs=["bold"])
        print(f"         {step_str} {message}", **kwargs)
    
    def encoding(self, encoder: str, is_hardware: bool = False):
        """Log encoding information with highlighting."""
        prefix = self._format_prefix("INFO", self.ARROW, "cyan")
        enc_type = colored("Hardware", "green", attrs=["bold"]) if is_hardware else colored("Software", "yellow")
        enc_name = colored(encoder, "white", attrs=["bold"])
        print(f"{prefix}Encoder: {enc_name} ({enc_type})")
    
    def progress(self, current: float, total: float, elapsed: float, speed: float = 0.0):
        """Display progress bar with time info."""
        if total <= 0:
            return
        
        pct = min(current / total, 1.0) * 100
        bar_width = 30
        filled = int(bar_width * current / total)
        bar = colored("█" * filled, "cyan") + colored("░" * (bar_width - filled), "white", attrs=["dark"])
        
        # Calculate ETA
        if speed > 0:
            remaining = (total - current) / speed
            eta_str = self._format_time(remaining)
        else:
            eta_str = "--:--"
        
        elapsed_str = self._format_time(elapsed)
        
        # Format: [████████░░░░░░] 45.2% | Elapsed: 00:32 | ETA: 00:38 | Speed: 1.2x
        speed_str = f"{speed:.1f}x" if speed > 0 else "--"
        status = f"\r         {bar} {pct:5.1f}% | {colored('Elapsed:', attrs=['dark'])} {elapsed_str} | {colored('ETA:', attrs=['dark'])} {eta_str} | {colored('Speed:', attrs=['dark'])} {speed_str}"
        
        print(status, end="", flush=True)
    
    def progress_done(self):
        """Clear progress line and print newline."""
        print()  # New line after progress bar
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS."""
        if seconds < 0:
            return "--:--"
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    
    def start_spinner(self, message: str = "Processing"):
        """Start animated spinner in background thread."""
        self._spinner_stop.clear()
        
        def spin():
            chars = "◐◓◑◒"
            idx = 0
            while not self._spinner_stop.is_set():
                char = colored(chars[idx % len(chars)], "cyan")
                print(f"\r         {char} {message}...", end="", flush=True)
                idx += 1
                time.sleep(0.1)
        
        self._spinner_thread = threading.Thread(target=spin, daemon=True)
        self._spinner_thread.start()
    
    def stop_spinner(self, final_message: str = "", success: bool = True):
        """Stop spinner and optionally print final message."""
        self._spinner_stop.set()
        if self._spinner_thread:
            self._spinner_thread.join(timeout=0.5)
        print("\r" + " " * 60 + "\r", end="")  # Clear line
        if final_message:
            if success:
                self.success(final_message)
            else:
                self.error(final_message)
    
    def section(self, title: str):
        """Print section header."""
        print()
        print(colored(f"  ═══ {title} ═══", "white", attrs=["bold"]))
        print()
    
    def detail(self, label: str, value: str):
        """Print labeled detail line."""
        print(f"         {colored(label + ':', attrs=['dark'])} {value}")


# Global logger instance
log = ColorLogger()
