#!/usr/bin/env python3
"""
Research Manager for NotebookLM
Integrate web search with NotebookLM project creation
Supports multiple search providers: Tavily, Perplexity, Serper
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from project_manager import create_project
from config import DATA_DIR

# Try to load dotenv for API keys
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


class SearchProvider:
    """Base class for search providers"""
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Search for content
        
        Returns:
            List of {"title": "...", "url": "...", "snippet": "..."}
        """
        raise NotImplementedError


class TavilySearch(SearchProvider):
    """Tavily AI Search API"""
    
    def __init__(self):
        self.api_key = os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not set. Add it to .env file.")
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        try:
            from tavily import TavilyClient
        except ImportError:
            raise ImportError("tavily-python not installed. Run: pip install tavily-python")
        
        client = TavilyClient(api_key=self.api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            include_answer=False,
            search_depth="advanced"
        )
        
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:200]
            })
        
        return results


class PerplexitySearch(SearchProvider):
    """Perplexity AI Search API"""
    
    def __init__(self):
        self.api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not set. Add it to .env file.")
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        import requests
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": f"Find {max_results} relevant articles/papers about the topic. Return ONLY a JSON array with objects containing 'title', 'url', and 'snippet' fields. No other text."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "return_citations": True
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Perplexity API error: {response.text}")
        
        data = response.json()
        citations = data.get("citations", [])
        
        results = []
        for url in citations[:max_results]:
            domain = urlparse(url).netloc
            results.append({
                "title": domain,
                "url": url,
                "snippet": ""
            })
        
        return results


class SerperSearch(SearchProvider):
    """Serper Google Search API"""
    
    def __init__(self):
        self.api_key = os.environ.get("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not set. Add it to .env file.")
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        import requests
        
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            },
            json={
                "q": query,
                "num": max_results
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Serper API error: {response.text}")
        
        data = response.json()
        
        results = []
        for r in data.get("organic", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", "")[:200]
            })
        
        return results


def get_search_provider(provider_name: str) -> SearchProvider:
    """Get search provider instance"""
    providers = {
        "tavily": TavilySearch,
        "perplexity": PerplexitySearch,
        "serper": SerperSearch
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Supported: {list(providers.keys())}")
    
    return providers[provider_name]()


def research_and_create(
    query: str,
    project_name: Optional[str] = None,
    max_sources: int = 5,
    provider: str = "tavily",
    headless: bool = True
) -> Dict[str, Any]:
    """
    1. Search for relevant content
    2. Create new NotebookLM project
    3. Add search results as sources
    
    Args:
        query: Search query
        project_name: Optional project name (default: generated from query)
        max_sources: Maximum number of sources to add
        provider: Search provider to use
        headless: Run browser in headless mode
        
    Returns:
        {"status": "...", "project_url": "...", "sources_added": [...]}
    """
    print(f"🔍 Deep Research: {query}")
    print(f"  🔎 Provider: {provider}")
    print(f"  📊 Max sources: {max_sources}")
    
    # Step 1: Search
    print("\n📡 Searching for relevant content...")
    try:
        search = get_search_provider(provider)
        results = search.search(query, max_results=max_sources)
    except Exception as e:
        return {"status": "error", "message": f"Search failed: {e}"}
    
    if not results:
        return {"status": "error", "message": "No search results found"}
    
    print(f"  ✅ Found {len(results)} result(s):")
    for i, r in enumerate(results, 1):
        print(f"    {i}. {r['title'][:50]}...")
        print(f"       {r['url']}")
    
    # Step 2: Extract URLs
    source_urls = [r['url'] for r in results if r.get('url')]
    
    if not source_urls:
        return {"status": "error", "message": "No valid URLs found in search results"}
    
    # Step 3: Create project with sources
    if not project_name:
        # Generate name from query
        project_name = f"Research: {query[:50]}"
    
    print(f"\n📂 Creating project: {project_name}")
    result = create_project(
        name=project_name,
        sources=source_urls,
        headless=headless,
        add_to_library=True
    )
    
    if result['status'] == 'success':
        # Save research metadata
        research_log = DATA_DIR / "research_log.json"
        try:
            if research_log.exists():
                with open(research_log, 'r') as f:
                    log = json.load(f)
            else:
                log = []
            
            log.append({
                "query": query,
                "project_name": project_name,
                "project_url": result.get('project_url'),
                "sources": results,
                "provider": provider,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            })
            
            with open(research_log, 'w') as f:
                json.dump(log, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    return {
        "status": result['status'],
        "project_url": result.get('project_url'),
        "project_name": project_name,
        "query": query,
        "sources_found": results,
        "sources_added": result.get('sources_added', []),
        "message": result.get('message')
    }


def list_research_history() -> List[Dict[str, Any]]:
    """List previous research sessions"""
    research_log = DATA_DIR / "research_log.json"
    
    if not research_log.exists():
        return []
    
    try:
        with open(research_log, 'r') as f:
            return json.load(f)
    except:
        return []


def main():
    parser = argparse.ArgumentParser(description='NotebookLM Research Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Research command
    research_parser = subparsers.add_parser('research', help='Research and create project')
    research_parser.add_argument('--query', '-q', required=True, help='Search query')
    research_parser.add_argument('--name', help='Project name')
    research_parser.add_argument('--max-sources', type=int, default=5, help='Max sources to add')
    research_parser.add_argument('--provider', default='tavily', 
                                 choices=['tavily', 'perplexity', 'serper'],
                                 help='Search provider')
    research_parser.add_argument('--show-browser', action='store_true', help='Show browser')
    
    # Search-only command (for testing)
    search_parser = subparsers.add_parser('search', help='Search only (no project creation)')
    search_parser.add_argument('--query', '-q', required=True, help='Search query')
    search_parser.add_argument('--max-results', type=int, default=5, help='Max results')
    search_parser.add_argument('--provider', default='tavily',
                               choices=['tavily', 'perplexity', 'serper'],
                               help='Search provider')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show research history')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'research':
        result = research_and_create(
            query=args.query,
            project_name=args.name,
            max_sources=args.max_sources,
            provider=args.provider,
            headless=not args.show_browser
        )
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        return 0 if result['status'] == 'success' else 1
    
    elif args.command == 'search':
        try:
            search = get_search_provider(args.provider)
            results = search.search(args.query, max_results=args.max_results)
            
            print(f"\n🔍 Search results for: {args.query}\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['title']}")
                print(f"   {r['url']}")
                if r['snippet']:
                    print(f"   {r['snippet'][:100]}...")
                print()
            
            return 0
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    elif args.command == 'history':
        history = list_research_history()
        if not history:
            print("📜 No research history found")
            return 0
        
        print("📜 Research History:\n")
        for i, entry in enumerate(history[-10:], 1):  # Last 10
            print(f"{i}. {entry.get('project_name', 'Untitled')}")
            print(f"   Query: {entry.get('query', '')}")
            print(f"   URL: {entry.get('project_url', 'N/A')}")
            print(f"   Date: {entry.get('timestamp', '')[:10]}")
            print()
        
        return 0


if __name__ == "__main__":
    sys.exit(main())
