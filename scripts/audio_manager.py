#!/usr/bin/env python3
"""
Audio Manager for NotebookLM
Generate, download, and play Audio Overview podcasts
"""

import argparse
import sys
import time
import re
import os
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional

from patchright.sync_api import sync_playwright

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from browser_utils import BrowserFactory, StealthUtils
from config import (
    AUDIO_OVERVIEW_TAB_SELECTORS,
    GENERATE_AUDIO_BUTTON_SELECTORS,
    AUDIO_PLAYER_SELECTORS,
    DOWNLOAD_AUDIO_BUTTON_SELECTORS,
    AUDIO_LOADING_SELECTORS,
    PAGE_LOAD_TIMEOUT,
    AUDIO_GENERATION_TIMEOUT,
    DATA_DIR,
)


def find_element(page, selectors: List[str], timeout: int = 5000):
    """Try multiple selectors and return the first matching element"""
    for selector in selectors:
        try:
            element = page.wait_for_selector(selector, timeout=timeout, state="visible")
            if element:
                return element
        except:
            continue
    return None


def generate_audio(
    notebook_url: str,
    headless: bool = True,
    wait_for_completion: bool = True
) -> Dict[str, Any]:
    """
    Trigger Audio Overview generation for a NotebookLM project
    
    Args:
        notebook_url: The NotebookLM project URL
        headless: Run browser in headless mode
        wait_for_completion: Wait for audio generation to complete
        
    Returns:
        {"status": "success/error", "message": "...", "audio_ready": bool}
    """
    auth = AuthManager()
    
    if not auth.is_authenticated():
        return {"status": "error", "message": "Not authenticated. Run: python scripts/run.py auth_manager.py setup"}
    
    print(f"🎙️ Generating Audio Overview")
    print(f"  📚 Notebook: {notebook_url}")
    
    playwright = None
    context = None
    
    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()
        
        # Navigate to notebook
        print("  🌐 Opening notebook...")
        page.goto(notebook_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=10000)
        StealthUtils.random_delay(1500, 2500)
        
        # Click Audio Overview tab
        print("  🎧 Opening Audio Overview...")
        audio_tab = find_element(page, AUDIO_OVERVIEW_TAB_SELECTORS, timeout=10000)
        if not audio_tab:
            return {"status": "error", "message": "Could not find Audio Overview tab"}
        
        audio_tab.click()
        StealthUtils.random_delay(1000, 2000)
        
        # Check if audio already exists
        audio_player = find_element(page, AUDIO_PLAYER_SELECTORS, timeout=3000)
        if audio_player:
            print("  ✅ Audio already exists!")
            return {
                "status": "success",
                "message": "Audio Overview already exists",
                "audio_ready": True
            }
        
        # Click Generate button
        print("  ⏳ Starting audio generation...")
        generate_btn = find_element(page, GENERATE_AUDIO_BUTTON_SELECTORS, timeout=5000)
        if not generate_btn:
            return {"status": "error", "message": "Could not find Generate button"}
        
        generate_btn.click()
        StealthUtils.random_delay(1000, 2000)
        
        if not wait_for_completion:
            return {
                "status": "success",
                "message": "Audio generation started (not waiting for completion)",
                "audio_ready": False
            }
        
        # Wait for generation to complete
        print("  ⏳ Waiting for generation (this may take several minutes)...")
        start_time = time.time()
        
        while time.time() - start_time < AUDIO_GENERATION_TIMEOUT:
            # Check if audio player appears
            audio_player = find_element(page, AUDIO_PLAYER_SELECTORS, timeout=5000)
            if audio_player:
                print("  ✅ Audio generation complete!")
                return {
                    "status": "success",
                    "message": "Audio Overview generated successfully",
                    "audio_ready": True
                }
            
            # Check for loading indicator
            loading = find_element(page, AUDIO_LOADING_SELECTORS, timeout=1000)
            if loading:
                elapsed = int(time.time() - start_time)
                print(f"    Still generating... ({elapsed}s)", end="\r")
            
            time.sleep(10)  # Poll every 10 seconds
        
        return {
            "status": "error",
            "message": f"Audio generation timed out after {AUDIO_GENERATION_TIMEOUT}s",
            "audio_ready": False
        }
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
    
    finally:
        if context:
            try:
                context.close()
            except:
                pass
        if playwright:
            try:
                playwright.stop()
            except:
                pass


def download_audio(
    notebook_url: str,
    output_path: Optional[str] = None,
    headless: bool = True
) -> Dict[str, Any]:
    """
    Download the Audio Overview as MP3
    
    Args:
        notebook_url: The NotebookLM project URL
        output_path: Output file path (default: data/audio/<notebook_id>.mp3)
        headless: Run browser in headless mode
        
    Returns:
        {"status": "success/error", "file_path": "...", "message": "..."}
    """
    auth = AuthManager()
    
    if not auth.is_authenticated():
        return {"status": "error", "message": "Not authenticated"}
    
    print(f"📥 Downloading Audio Overview")
    print(f"  📚 Notebook: {notebook_url}")
    
    # Prepare output directory
    audio_dir = DATA_DIR / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    if not output_path:
        # Extract notebook ID from URL
        match = re.search(r'notebook/([a-zA-Z0-9_-]+)', notebook_url)
        notebook_id = match.group(1) if match else "audio"
        output_path = str(audio_dir / f"{notebook_id}.mp3")
    
    playwright = None
    context = None
    
    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()
        
        # Set up download handler
        download_path = None
        
        def handle_download(download):
            nonlocal download_path
            download_path = output_path
            download.save_as(output_path)
        
        page.on("download", handle_download)
        
        # Navigate to notebook
        print("  🌐 Opening notebook...")
        page.goto(notebook_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=10000)
        StealthUtils.random_delay(1500, 2500)
        
        # Click Audio Overview tab
        print("  🎧 Opening Audio Overview...")
        audio_tab = find_element(page, AUDIO_OVERVIEW_TAB_SELECTORS, timeout=10000)
        if not audio_tab:
            return {"status": "error", "message": "Could not find Audio Overview tab"}
        
        audio_tab.click()
        StealthUtils.random_delay(1000, 2000)
        
        # Check if audio exists
        audio_player = find_element(page, AUDIO_PLAYER_SELECTORS, timeout=5000)
        if not audio_player:
            return {"status": "error", "message": "No audio found. Generate audio first."}
        
        # Click download button
        print("  📥 Downloading...")
        download_btn = find_element(page, DOWNLOAD_AUDIO_BUTTON_SELECTORS, timeout=5000)
        if not download_btn:
            # Try to get audio src directly from player
            audio_src = audio_player.get_attribute("src")
            if audio_src:
                # Download via fetch
                print(f"  🔗 Getting audio from: {audio_src[:50]}...")
                # Use page to download
                response = page.request.get(audio_src)
                if response.ok:
                    with open(output_path, 'wb') as f:
                        f.write(response.body())
                    print(f"  ✅ Downloaded to: {output_path}")
                    return {
                        "status": "success",
                        "file_path": output_path,
                        "message": "Audio downloaded successfully"
                    }
            return {"status": "error", "message": "Could not find download button or audio source"}
        
        download_btn.click()
        
        # Wait for download
        StealthUtils.random_delay(3000, 5000)
        
        if download_path and Path(download_path).exists():
            print(f"  ✅ Downloaded to: {download_path}")
            return {
                "status": "success",
                "file_path": download_path,
                "message": "Audio downloaded successfully"
            }
        else:
            return {"status": "error", "message": "Download may have failed"}
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
    
    finally:
        if context:
            try:
                context.close()
            except:
                pass
        if playwright:
            try:
                playwright.stop()
            except:
                pass


def play_audio(file_path: str) -> Dict[str, Any]:
    """
    Play audio file using system default player
    
    Args:
        file_path: Path to audio file
        
    Returns:
        {"status": "success/error", "message": "..."}
    """
    if not Path(file_path).exists():
        return {"status": "error", "message": f"File not found: {file_path}"}
    
    print(f"🔊 Playing: {file_path}")
    
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            subprocess.Popen(["afplay", file_path])
        elif system == "Windows":
            os.startfile(file_path)
        else:  # Linux
            subprocess.Popen(["xdg-open", file_path])
        
        return {"status": "success", "message": "Audio playback started"}
        
    except Exception as e:
        return {"status": "error", "message": f"Could not play audio: {e}"}


def main():
    parser = argparse.ArgumentParser(description='NotebookLM Audio Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate Audio Overview')
    generate_parser.add_argument('--notebook-url', help='NotebookLM notebook URL')
    generate_parser.add_argument('--notebook-id', help='Notebook ID from library')
    generate_parser.add_argument('--show-browser', action='store_true', help='Show browser')
    generate_parser.add_argument('--no-wait', action='store_true', help='Do not wait for generation')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download Audio Overview')
    download_parser.add_argument('--notebook-url', help='NotebookLM notebook URL')
    download_parser.add_argument('--notebook-id', help='Notebook ID from library')
    download_parser.add_argument('--output', '-o', help='Output file path')
    download_parser.add_argument('--show-browser', action='store_true', help='Show browser')
    
    # Play command
    play_parser = subparsers.add_parser('play', help='Play audio file')
    play_parser.add_argument('--file', '-f', required=True, help='Audio file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Resolve notebook URL for generate/download commands
    notebook_url = None
    if args.command in ['generate', 'download']:
        notebook_url = getattr(args, 'notebook_url', None)
        
        if not notebook_url and getattr(args, 'notebook_id', None):
            library = NotebookLibrary()
            notebook = library.get_notebook(args.notebook_id)
            if notebook:
                notebook_url = notebook['url']
            else:
                print(f"❌ Notebook '{args.notebook_id}' not found")
                return 1
        
        if not notebook_url:
            library = NotebookLibrary()
            active = library.get_active_notebook()
            if active:
                notebook_url = active['url']
                print(f"📚 Using active notebook: {active['name']}")
            else:
                print("❌ No notebook specified")
                return 1
    
    if args.command == 'generate':
        result = generate_audio(
            notebook_url=notebook_url,
            headless=not args.show_browser,
            wait_for_completion=not args.no_wait
        )
        
    elif args.command == 'download':
        result = download_audio(
            notebook_url=notebook_url,
            output_path=args.output,
            headless=not args.show_browser
        )
        
    elif args.command == 'play':
        result = play_audio(args.file)
    
    print(f"\n{result}")
    return 0 if result['status'] == 'success' else 1


if __name__ == "__main__":
    sys.exit(main())
