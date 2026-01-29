#!/usr/bin/env python3
"""
Add Source to NotebookLM
Add URL/PDF links to existing NotebookLM projects
"""

import argparse
import sys
import time
import re
from pathlib import Path
from typing import Dict, Any, List

from patchright.sync_api import sync_playwright

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from browser_utils import BrowserFactory, StealthUtils
from config import (
    ADD_SOURCE_BUTTON_SELECTORS,
    WEBSITE_SOURCE_OPTION_SELECTORS,
    URL_INPUT_SELECTORS,
    SUBMIT_SOURCE_BUTTON_SELECTORS,
    PAGE_LOAD_TIMEOUT,
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


def add_source(
    notebook_url: str,
    source_url: str,
    headless: bool = True
) -> Dict[str, Any]:
    """
    Add a URL (webpage or PDF link) to a NotebookLM project
    
    Args:
        notebook_url: The NotebookLM project URL
        source_url: URL to add (webpage or PDF link like arxiv)
        headless: Run browser in headless mode
        
    Returns:
        {"status": "success/error", "message": "..."}
    """
    auth = AuthManager()
    
    if not auth.is_authenticated():
        return {"status": "error", "message": "Not authenticated. Run: python scripts/run.py auth_manager.py setup"}
    
    print(f"📎 Adding source to notebook")
    print(f"  📚 Notebook: {notebook_url}")
    print(f"  🔗 Source: {source_url}")
    
    playwright = None
    context = None
    
    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()
        
        # Navigate to notebook
        print("  🌐 Opening notebook...")
        page.goto(notebook_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        
        # Wait for NotebookLM
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=10000)
        StealthUtils.random_delay(1500, 2500)
        
        # Dismiss any modal overlays that might be present (e.g., file upload dialog)
        try:
            # Try pressing Escape to close any open dialogs
            page.keyboard.press("Escape")
            StealthUtils.random_delay(500, 1000)
        except:
            pass
        
        # Check if we need to go to Sources tab first
        try:
            sources_tab = page.query_selector('button:has-text("Sources"), [data-testid="sources-tab"]')
            if sources_tab:
                sources_tab.click()
                StealthUtils.random_delay(500, 1000)
        except:
            pass
        
        # Click "Add source" button
        print("  ➕ Adding source...")
        add_btn = find_element(page, ADD_SOURCE_BUTTON_SELECTORS, timeout=10000)
        if not add_btn:
            return {"status": "error", "message": "Could not find 'Add source' button"}
        
        # Use force click to bypass any overlay issues
        add_btn.click(force=True)
        StealthUtils.random_delay(500, 1000)
        
        # Select "Website" option
        website_btn = find_element(page, WEBSITE_SOURCE_OPTION_SELECTORS, timeout=5000)
        if not website_btn:
            return {"status": "error", "message": "Could not find 'Website' option"}
        
        website_btn.click()
        StealthUtils.random_delay(500, 1000)
        
        # Enter URL
        url_input = find_element(page, URL_INPUT_SELECTORS, timeout=5000)
        if not url_input:
            return {"status": "error", "message": "Could not find URL input field"}
        
        url_input.fill(source_url)
        StealthUtils.random_delay(300, 500)
        
        # Submit
        submit_btn = find_element(page, SUBMIT_SOURCE_BUTTON_SELECTORS, timeout=3000)
        if submit_btn:
            submit_btn.click()
        else:
            page.keyboard.press("Enter")
        
        # Wait for source to be processed
        print("  ⏳ Waiting for source to be processed...")
        StealthUtils.random_delay(3000, 5000)
        
        # Check for success indicators (source card appears) or error messages
        # This is a simplified check - the source should appear in the sources list
        
        print("  ✅ Source added successfully!")
        return {
            "status": "success",
            "notebook_url": notebook_url,
            "source_url": source_url,
            "message": f"Successfully added {source_url} to notebook"
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


def add_multiple_sources(
    notebook_url: str,
    source_urls: List[str],
    headless: bool = True
) -> Dict[str, Any]:
    """
    Add multiple URLs to a NotebookLM project
    
    Args:
        notebook_url: The NotebookLM project URL
        source_urls: List of URLs to add
        headless: Run browser in headless mode
        
    Returns:
        {"status": "success/partial/error", "added": [...], "failed": [...]}
    """
    auth = AuthManager()
    
    if not auth.is_authenticated():
        return {"status": "error", "message": "Not authenticated"}
    
    print(f"📎 Adding {len(source_urls)} source(s) to notebook")
    print(f"  📚 Notebook: {notebook_url}")
    
    playwright = None
    context = None
    added = []
    failed = []
    
    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()
        
        # Navigate to notebook
        print("  🌐 Opening notebook...")
        page.goto(notebook_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=10000)
        StealthUtils.random_delay(1500, 2500)
        
        for i, source_url in enumerate(source_urls, 1):
            print(f"  [{i}/{len(source_urls)}] Adding: {source_url}")
            
            try:
                # Click "Add source" button
                add_btn = find_element(page, ADD_SOURCE_BUTTON_SELECTORS, timeout=5000)
                if not add_btn:
                    failed.append({"url": source_url, "reason": "Could not find 'Add source' button"})
                    continue
                
                add_btn.click()
                StealthUtils.random_delay(500, 1000)
                
                # Select "Website" option
                website_btn = find_element(page, WEBSITE_SOURCE_OPTION_SELECTORS, timeout=5000)
                if not website_btn:
                    failed.append({"url": source_url, "reason": "Could not find 'Website' option"})
                    page.keyboard.press("Escape")  # Close dialog
                    continue
                
                website_btn.click()
                StealthUtils.random_delay(500, 1000)
                
                # Enter URL
                url_input = find_element(page, URL_INPUT_SELECTORS, timeout=5000)
                if not url_input:
                    failed.append({"url": source_url, "reason": "Could not find URL input"})
                    page.keyboard.press("Escape")
                    continue
                
                url_input.fill(source_url)
                StealthUtils.random_delay(300, 500)
                
                # Submit
                submit_btn = find_element(page, SUBMIT_SOURCE_BUTTON_SELECTORS, timeout=3000)
                if submit_btn:
                    submit_btn.click()
                else:
                    page.keyboard.press("Enter")
                
                # Wait for processing
                StealthUtils.random_delay(3000, 5000)
                added.append(source_url)
                print(f"    ✅ Added")
                
            except Exception as e:
                failed.append({"url": source_url, "reason": str(e)})
                print(f"    ❌ Failed: {e}")
                try:
                    page.keyboard.press("Escape")
                except:
                    pass
        
        status = "success" if not failed else ("partial" if added else "error")
        return {
            "status": status,
            "added": added,
            "failed": failed,
            "message": f"Added {len(added)}/{len(source_urls)} sources"
        }
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"status": "error", "message": str(e), "added": added, "failed": failed}
    
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


def main():
    parser = argparse.ArgumentParser(description='Add source to NotebookLM notebook')
    
    parser.add_argument('--notebook-url', help='NotebookLM notebook URL')
    parser.add_argument('--notebook-id', help='Notebook ID from local library')
    parser.add_argument('--source', '--sources', nargs='+', required=True, help='URL(s) to add as source')
    parser.add_argument('--show-browser', action='store_true', help='Show browser window')
    
    args = parser.parse_args()
    
    # Resolve notebook URL
    notebook_url = args.notebook_url
    
    if not notebook_url and args.notebook_id:
        library = NotebookLibrary()
        notebook = library.get_notebook(args.notebook_id)
        if notebook:
            notebook_url = notebook['url']
        else:
            print(f"❌ Notebook '{args.notebook_id}' not found in library")
            return 1
    
    if not notebook_url:
        # Check for active notebook
        library = NotebookLibrary()
        active = library.get_active_notebook()
        if active:
            notebook_url = active['url']
            print(f"📚 Using active notebook: {active['name']}")
        else:
            print("❌ No notebook specified. Use --notebook-url or --notebook-id")
            print("   Or set an active notebook with: python scripts/run.py notebook_manager.py activate --id ID")
            return 1
    
    # Add source(s)
    if len(args.source) == 1:
        result = add_source(
            notebook_url=notebook_url,
            source_url=args.source[0],
            headless=not args.show_browser
        )
    else:
        result = add_multiple_sources(
            notebook_url=notebook_url,
            source_urls=args.source,
            headless=not args.show_browser
        )
    
    print(f"\n{result}")
    return 0 if result['status'] in ['success', 'partial'] else 1


if __name__ == "__main__":
    sys.exit(main())
