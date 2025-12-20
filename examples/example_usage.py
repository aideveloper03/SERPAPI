#!/usr/bin/env python3
"""
Example usage of the Search Engine Scraping API
Run this after starting the API server
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def print_result(title: str, result: Dict[str, Any]):
    """Pretty print a result"""
    print(f"\n{'='*60}")
    print(f"📌 {title}")
    print(f"{'='*60}")
    
    if result.get('success'):
        print(f"✅ Success | Engine: {result.get('engine', 'N/A')}")
        print(f"📊 Results: {result.get('total_results', 0)}")
        print(f"⏱️ Time: {result.get('response_time', 'N/A'):.2f}s")
        
        if result.get('fallback_used'):
            print(f"🔄 Fallback was used")
        
        # Print first 3 results
        for i, r in enumerate(result.get('results', [])[:3], 1):
            print(f"\n  [{i}] {r.get('title', 'No title')[:60]}")
            print(f"      URL: {r.get('url', '')[:60]}")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")


def example_fast_search():
    """Example: Fast search (speed optimized)"""
    response = requests.post(f"{BASE_URL}/api/v1/search/fast", json={
        "query": "python web scraping tutorial",
        "num_results": 5
    })
    print_result("Fast Search", response.json())


def example_unified_search():
    """Example: Unified search with fallback"""
    response = requests.post(f"{BASE_URL}/api/v1/search/unified", json={
        "query": "machine learning frameworks",
        "preferred_engine": "google",
        "use_fallback": True,
        "num_results": 10
    })
    print_result("Unified Search (Google with fallback)", response.json())


def example_parallel_search():
    """Example: Parallel search across all engines"""
    response = requests.post(f"{BASE_URL}/api/v1/search/parallel", json={
        "query": "artificial intelligence applications",
        "num_results": 15
    })
    print_result("Parallel Search (All Engines)", response.json())


def example_batch_search():
    """Example: Batch search for multiple queries"""
    response = requests.post(f"{BASE_URL}/api/v1/search/batch", json={
        "queries": ["python", "javascript", "rust", "golang"],
        "num_results": 3,
        "preferred_engine": "duckduckgo"
    })
    
    result = response.json()
    print(f"\n{'='*60}")
    print(f"📌 Batch Search ({result.get('total_queries', 0)} queries)")
    print(f"{'='*60}")
    
    for item in result.get('results', []):
        status = "✅" if item.get('success') else "❌"
        print(f"  {status} '{item.get('query')}': {item.get('total_results', 0)} results")


def example_news_search():
    """Example: News search"""
    response = requests.post(f"{BASE_URL}/api/v1/search/unified", json={
        "query": "technology news today",
        "search_type": "news",
        "num_results": 5
    })
    print_result("News Search", response.json())


def example_individual_engines():
    """Example: Search specific engines"""
    engines = ['google', 'duckduckgo', 'bing', 'yahoo']
    
    for engine in engines:
        response = requests.post(f"{BASE_URL}/api/v1/search/{engine}", json={
            "query": "web development",
            "num_results": 3
        })
        print_result(f"{engine.title()} Direct Search", response.json())


def example_get_stats():
    """Example: Get engine statistics"""
    response = requests.get(f"{BASE_URL}/api/v1/search/stats")
    stats = response.json()
    
    print(f"\n{'='*60}")
    print(f"📊 Engine Statistics")
    print(f"{'='*60}")
    
    for engine, data in stats.get('engine_stats', {}).items():
        print(f"  {engine}: {data.get('success_rate', 0)}% success ({data.get('successes', 0)}/{data.get('successes', 0) + data.get('failures', 0)})")


def check_health():
    """Check if API is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running and healthy")
            return True
    except:
        pass
    
    print("❌ API is not running. Start it with:")
    print("   docker-compose up -d")
    print("   or")
    print("   python -m uvicorn app.main:app --reload")
    return False


def main():
    """Run all examples"""
    print("\n🔍 Search Engine Scraping API - Examples")
    print("="*60)
    
    if not check_health():
        return
    
    # Run examples
    example_fast_search()
    example_unified_search()
    example_parallel_search()
    example_batch_search()
    example_news_search()
    example_get_stats()
    
    print("\n" + "="*60)
    print("✨ All examples completed!")
    print("📚 View API docs at: http://localhost:8000/docs")
    print("="*60)


if __name__ == "__main__":
    main()
