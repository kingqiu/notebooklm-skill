#!/usr/bin/env python3
"""
Project Manager for NotebookLM
Create, list, and delete NotebookLM projects via browser automation
"""

import argparse
import sys
import time
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from patchright.sync_api import sync_playwright

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from browser_utils import BrowserFactory, StealthUtils
from config import (
    NOTEBOOKLM_HOME,
    CREATE_NOTEBOOK_BUTTON_SELECTORS,
    NOTEBOOK_TITLE_INPUT_SELECTORS,
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


def create_project(
    name: str,
    sources: List[str] = None,
    headless: bool = True,
    add_to_library: bool = True
) -> Dict[str, Any]:
    """
    Create a new NotebookLM project
    
    Args:
        name: Project display name
        sources: Optional list of URLs to add immediately
        headless: Run browser in headless mode
        add_to_library: Add project to local library after creation
        
    Returns:
        {"status": "success/error", "project_url": "...", "message": "..."}
    """
    auth = AuthManager()
    
    if not auth.is_authenticated():
        return {"status": "error", "message": "Not authenticated. Run: python scripts/run.py auth_manager.py setup"}
    
    print(f"📂 Creating new project: {name}")
    if sources:
        print(f"📎 Will add {len(sources)} source(s)")
    
    playwright = None
    context = None
    project_url = None
    
    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()
        
        # Navigate to NotebookLM home
        print("  🌐 Opening NotebookLM...")
        page.goto(NOTEBOOKLM_HOME, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        
        # Wait for page to load
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com"), timeout=10000)
        StealthUtils.random_delay(1000, 2000)
        
        # Click "Create new notebook" button
        print("  ➕ Creating new notebook...")
        create_btn = find_element(page, CREATE_NOTEBOOK_BUTTON_SELECTORS, timeout=10000)
        if not create_btn:
            return {"status": "error", "message": "Could not find 'Create notebook' button"}
        
        create_btn.click()
        StealthUtils.random_delay(1500, 2500)
        
        # Wait for new notebook page to load
        page.wait_for_url(re.compile(r"notebook/[a-zA-Z0-9_-]+"), timeout=15000)
        project_url = page.url
        print(f"  ✅ Created: {project_url}")
        
        # Rename notebook if title input is available
        StealthUtils.random_delay(500, 1000)
        title_input = find_element(page, NOTEBOOK_TITLE_INPUT_SELECTORS, timeout=3000)
        if title_input:
            print(f"  📝 Renaming to: {name}")
            title_input.click()
            title_input.fill("")
            StealthUtils.human_type(page, NOTEBOOK_TITLE_INPUT_SELECTORS[0], name)
            page.keyboard.press("Enter")
            StealthUtils.random_delay(500, 1000)
        
        # Add sources if provided
        sources_added = []
        if sources:
            for source_url in sources:
                result = _add_source_to_page(page, source_url)
                if result["status"] == "success":
                    sources_added.append(source_url)
                    print(f"  📎 Added: {source_url}")
                else:
                    print(f"  ⚠️ Failed to add: {source_url}")
        
        # Add to local library
        if add_to_library and project_url:
            library = NotebookLibrary()
            topics = ["auto-created"]
            if sources:
                topics.append("with-sources")
            
            library.add_notebook(
                url=project_url,
                name=name,
                description=f"Auto-created project with {len(sources_added)} source(s)" if sources_added else "Auto-created empty project",
                topics=topics
            )
            print("  📚 Added to local library")
        
        return {
            "status": "success",
            "project_url": project_url,
            "name": name,
            "sources_added": sources_added,
            "message": f"Created project '{name}' with {len(sources_added)} source(s)"
        }
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e), "project_url": project_url}
    
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


def _add_source_to_page(page, source_url: str) -> Dict[str, Any]:
    """Internal: Add a single source to the current notebook page"""
    try:
        # Click "Add source" button
        add_btn = find_element(page, ADD_SOURCE_BUTTON_SELECTORS, timeout=5000)
        if not add_btn:
            return {"status": "error", "message": "Could not find 'Add source' button"}
        
        add_btn.click()
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
        StealthUtils.random_delay(2000, 4000)
        
        return {"status": "success", "source_url": source_url}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


def list_projects(headless: bool = True) -> List[Dict[str, Any]]:
    """
    List all projects visible on the NotebookLM home page
    
    Returns:
        List of {"name": "...", "url": "...", "last_modified": "..."}
    """
    auth = AuthManager()
    
    if not auth.is_authenticated():
        print("⚠️ Not authenticated")
        return []
    
    print("📂 Fetching projects from NotebookLM...")
    
    playwright = None
    context = None
    
    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()
        
        page.goto(NOTEBOOKLM_HOME, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com"), timeout=10000)
        StealthUtils.random_delay(2000, 3000)
        
        # Find notebook cards on the page
        projects = []
        
        # Try to find notebook list items
        notebook_cards = page.query_selector_all('[data-testid="notebook-card"], .notebook-card, [role="listitem"]')
        
        for card in notebook_cards:
            try:
                # Extract name
                name_el = card.query_selector('h3, .title, [data-testid="notebook-title"]')
                name = name_el.inner_text().strip() if name_el else "Untitled"
                
                # Extract link
                link_el = card.query_selector('a[href*="/notebook/"]')
                url = link_el.get_attribute('href') if link_el else None
                if url and not url.startswith('http'):
                    url = f"https://notebooklm.google.com{url}"
                
                if url:
                    projects.append({
                        "name": name,
                        "url": url
                    })
            except:
                continue
        
        print(f"  ✅ Found {len(projects)} project(s)")
        return projects
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []
    
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


def delete_project(project_url: str, headless: bool = True) -> Dict[str, Any]:
    """
    Delete a NotebookLM project
    
    Args:
        project_url: The NotebookLM project URL to delete
        headless: Run browser in headless mode
        
    Returns:
        {"status": "success/error", "message": "..."}
    """
    auth = AuthManager()
    
    if not auth.is_authenticated():
        return {"status": "error", "message": "Not authenticated"}
    
    print(f"🗑️ Deleting project: {project_url}")
    
    playwright = None
    context = None
    
    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()
        
        # Navigate to project
        page.goto(project_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        StealthUtils.random_delay(1000, 2000)
        
        # Look for settings/menu button
        menu_btn = page.query_selector('button[aria-label="More options"], button[aria-label="Settings"], [data-testid="notebook-menu"]')
        if not menu_btn:
            return {"status": "error", "message": "Could not find notebook menu"}
        
        menu_btn.click()
        StealthUtils.random_delay(500, 1000)
        
        # Look for delete option
        delete_btn = page.query_selector('button:has-text("Delete"), [data-testid="delete-notebook"]')
        if not delete_btn:
            return {"status": "error", "message": "Could not find delete option"}
        
        delete_btn.click()
        StealthUtils.random_delay(500, 1000)
        
        # Confirm deletion
        confirm_btn = page.query_selector('button:has-text("Delete"), button:has-text("Confirm")')
        if confirm_btn:
            confirm_btn.click()
        
        StealthUtils.random_delay(1000, 2000)
        
        # Remove from local library
        library = NotebookLibrary()
        notebooks = library.list_notebooks()
        for nb in notebooks:
            if nb.get('url') == project_url:
                library.remove_notebook(nb['id'])
                print("  📚 Removed from local library")
                break
        
        print("  ✅ Project deleted")
        return {"status": "success", "message": "Project deleted successfully"}
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
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


def main():
    parser = argparse.ArgumentParser(description='NotebookLM Project Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new project')
    create_parser.add_argument('--name', required=True, help='Project name')
    create_parser.add_argument('--sources', nargs='*', help='URLs to add as sources')
    create_parser.add_argument('--show-browser', action='store_true', help='Show browser window')
    create_parser.add_argument('--no-library', action='store_true', help='Do not add to local library')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all projects')
    list_parser.add_argument('--show-browser', action='store_true', help='Show browser window')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a project')
    delete_parser.add_argument('--url', required=True, help='Project URL to delete')
    delete_parser.add_argument('--show-browser', action='store_true', help='Show browser window')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'create':
        result = create_project(
            name=args.name,
            sources=args.sources,
            headless=not args.show_browser,
            add_to_library=not args.no_library
        )
        print(f"\n{result}")
        return 0 if result['status'] == 'success' else 1
    
    elif args.command == 'list':
        projects = list_projects(headless=not args.show_browser)
        if projects:
            print("\n📂 Projects on NotebookLM:")
            for p in projects:
                print(f"  • {p['name']}")
                print(f"    {p['url']}")
        else:
            print("\n📂 No projects found")
        return 0
    
    elif args.command == 'delete':
        result = delete_project(
            project_url=args.url,
            headless=not args.show_browser
        )
        print(f"\n{result}")
        return 0 if result['status'] == 'success' else 1


if __name__ == "__main__":
    sys.exit(main())
