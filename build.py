"""
Build script for Video Tools CLI.
Creates standalone executable using PyInstaller.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Fix encoding for Windows CI environments
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Project paths
PROJECT_DIR = Path(__file__).parent
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"
BIN_DIR = PROJECT_DIR / "bin"
ASSETS_DIR = PROJECT_DIR / "assets"

# Application info
APP_NAME = "video-tools"
MAIN_SCRIPT = "main.py"
VERSION = "1.6.0"


def clean_build():
    """Clean previous build artifacts."""
    print("Cleaning previous build...")
    for folder in [DIST_DIR, BUILD_DIR]:
        if folder.exists():
            shutil.rmtree(folder)
    
    spec_file = PROJECT_DIR / f"{APP_NAME}.spec"
    if spec_file.exists():
        spec_file.unlink()


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True


def build_exe():
    """Build the executable using PyInstaller."""
    check_pyinstaller()
    clean_build()
    
    print(f"Building {APP_NAME}.exe v{VERSION}...")
    
    # Build arguments
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--console",
        "--noconfirm",
        "--clean",
        
        # Hidden imports
        "--hidden-import", "colorama",
        "--hidden-import", "termcolor",
        "--hidden-import", "InquirerPy",
        "--hidden-import", "prompt_toolkit",
        "--hidden-import", "requests",
        "--hidden-import", "bs4",
        "--hidden-import", "dotenv",
        "--hidden-import", "tqdm",
        
        # Add data files
        "--add-data", f"requirements.txt{os.pathsep}.",
    ]
    
    # Add icon if exists
    icon_path = (ASSETS_DIR / "icon.ico").resolve()
    if icon_path.exists():
        args.extend(["--icon", str(icon_path)])
        print(f"  Using icon: {icon_path}")
    
    args.append(MAIN_SCRIPT)
    
    # Run PyInstaller
    result = subprocess.run(args, cwd=PROJECT_DIR)
    
    if result.returncode == 0:
        exe_path = DIST_DIR / f"{APP_NAME}.exe"
        if exe_path.exists():
            print("")
            print("[OK] Build successful!")
            print(f"  Executable: {exe_path}")
            print(f"  Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
            
            # Copy bin folder to dist
            dist_bin = DIST_DIR / "bin"
            if BIN_DIR.exists():
                print("  Copying bin folder...")
                shutil.copytree(BIN_DIR, dist_bin, dirs_exist_ok=True)
            
            # Create cache folder
            cache_dir = DIST_DIR / "cache"
            cache_dir.mkdir(exist_ok=True)
            
            print(f"\n  To run: {exe_path}")
            return True
    
    print(f"\n[FAIL] Build failed with code {result.returncode}")
    return False


def create_release_package():
    """Create a ZIP package for release."""
    import zipfile
    
    if not (DIST_DIR / f"{APP_NAME}.exe").exists():
        print("Executable not found. Run build first.")
        return False
    
    zip_name = f"{APP_NAME}-v{VERSION}-win64.zip"
    zip_path = DIST_DIR / zip_name
    
    print(f"Creating release package: {zip_name}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        exe_path = DIST_DIR / f"{APP_NAME}.exe"
        zf.write(exe_path, f"{APP_NAME}.exe")
        
        dist_bin = DIST_DIR / "bin"
        if dist_bin.exists():
            for file in dist_bin.iterdir():
                zf.write(file, f"bin/{file.name}")
        
        readme = PROJECT_DIR / "README.md"
        if readme.exists():
            zf.write(readme, "README.md")
    
    print(f"[OK] Created: {zip_path}")
    print(f"  Size: {zip_path.stat().st_size / (1024*1024):.1f} MB")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Video Tools CLI")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts only")
    parser.add_argument("--package", action="store_true", help="Create release package after build")
    
    args = parser.parse_args()
    
    if args.clean:
        clean_build()
        print("[OK] Cleaned build artifacts")
    else:
        if build_exe():
            if args.package:
                create_release_package()
