"""
Example usage of the Web Scraping System API
Demonstrates all major features and endpoints
"""
import requests
import json
from typing import List, Dict, Any


class WebScraperClient:
    """Client for Web Scraping System API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    # ==================== Search Methods ====================
    
    def google_search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search Google
        
        Args:
            query: Search query
            search_type: all, news, images, or videos
            num_results: Number of results to return
            
        Returns:
            Search results dictionary
        """
        response = self.session.post(
            f"{self.base_url}/api/v1/search/google",
            json={
                "query": query,
                "search_type": search_type,
                "num_results": num_results
            }
        )
        response.raise_for_status()
        return response.json()
    
    def duckduckgo_search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10
    ) -> Dict[str, Any]:
        """Search DuckDuckGo"""
        response = self.session.post(
            f"{self.base_url}/api/v1/search/duckduckgo",
            json={
                "query": query,
                "search_type": search_type,
                "num_results": num_results
            }
        )
        response.raise_for_status()
        return response.json()
    
    def combined_search(
        self,
        query: str,
        num_results: int = 10
    ) -> Dict[str, Any]:
        """Search both Google and DuckDuckGo"""
        response = self.session.post(
            f"{self.base_url}/api/v1/search/combined",
            json={
                "query": query,
                "num_results": num_results
            }
        )
        response.raise_for_status()
        return response.json()
    
    def batch_google_search(
        self,
        queries: List[str],
        num_results: int = 10
    ) -> Dict[str, Any]:
        """Batch Google search"""
        response = self.session.post(
            f"{self.base_url}/api/v1/search/google/batch",
            json={
                "queries": queries,
                "num_results": num_results
            }
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== Website Scraping Methods ====================
    
    def scrape_website(
        self,
        url: str,
        extract_contacts: bool = True,
        extract_links: bool = True,
        extract_images: bool = True,
        use_browser: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape a website
        
        Args:
            url: Website URL
            extract_contacts: Extract contact information
            extract_links: Extract all links
            extract_images: Extract all images
            use_browser: Force browser rendering
            
        Returns:
            Scraped content dictionary
        """
        response = self.session.post(
            f"{self.base_url}/api/v1/website/scrape",
            json={
                "url": url,
                "extract_contacts": extract_contacts,
                "extract_links": extract_links,
                "extract_images": extract_images,
                "use_browser": use_browser
            }
        )
        response.raise_for_status()
        return response.json()
    
    def batch_scrape(
        self,
        urls: List[str],
        extract_contacts: bool = True,
        max_concurrent: int = 10
    ) -> Dict[str, Any]:
        """Scrape multiple websites concurrently"""
        response = self.session.post(
            f"{self.base_url}/api/v1/website/scrape/batch",
            json={
                "urls": urls,
                "extract_contacts": extract_contacts,
                "max_concurrent": max_concurrent
            }
        )
        response.raise_for_status()
        return response.json()
    
    def deep_scrape(
        self,
        url: str,
        max_depth: int = 2,
        max_pages: int = 50
    ) -> Dict[str, Any]:
        """Deep scrape (follow links)"""
        response = self.session.post(
            f"{self.base_url}/api/v1/website/scrape/deep",
            json={
                "url": url,
                "max_depth": max_depth,
                "max_pages": max_pages
            }
        )
        response.raise_for_status()
        return response.json()
    
    def extract_contacts(self, url: str) -> Dict[str, Any]:
        """Extract contacts only"""
        response = self.session.get(
            f"{self.base_url}/api/v1/website/extract/contacts",
            params={"url": url}
        )
        response.raise_for_status()
        return response.json()
    
    def extract_content(self, url: str) -> Dict[str, Any]:
        """Extract content only"""
        response = self.session.get(
            f"{self.base_url}/api/v1/website/extract/content",
            params={"url": url}
        )
        response.raise_for_status()
        return response.json()
    
    def extract_metadata(self, url: str) -> Dict[str, Any]:
        """Extract metadata only"""
        response = self.session.get(
            f"{self.base_url}/api/v1/website/extract/metadata",
            params={"url": url}
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== System Methods ====================
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def status(self) -> Dict[str, Any]:
        """Get system status"""
        response = self.session.get(f"{self.base_url}/status")
        response.raise_for_status()
        return response.json()


# ==================== Example Usage ====================

def example_search():
    """Example: Search engines"""
    print("\n=== SEARCH ENGINE EXAMPLES ===\n")
    
    client = WebScraperClient()
    
    # Google search
    print("1. Google Search:")
    results = client.google_search("python web scraping", num_results=5)
    print(f"   Found {results['total_results']} results")
    for i, result in enumerate(results['results'][:3], 1):
        print(f"   {i}. {result['title']}")
        print(f"      {result['url']}")
    
    # DuckDuckGo search
    print("\n2. DuckDuckGo Search:")
    results = client.duckduckgo_search("machine learning", num_results=5)
    print(f"   Found {results['total_results']} results")
    
    # Combined search
    print("\n3. Combined Search (Google + DuckDuckGo):")
    results = client.combined_search("artificial intelligence", num_results=5)
    print(f"   Google results: {len(results['google'].get('results', []))}")
    print(f"   DuckDuckGo results: {len(results['duckduckgo'].get('results', []))}")
    
    # Batch search
    print("\n4. Batch Google Search:")
    queries = ["python", "javascript", "java"]
    results = client.batch_google_search(queries, num_results=3)
    print(f"   Searched {results['total_queries']} queries")
    for result in results['results']:
        print(f"   - {result['query']}: {result['total_results']} results")


def example_website_scraping():
    """Example: Website scraping"""
    print("\n=== WEBSITE SCRAPING EXAMPLES ===\n")
    
    client = WebScraperClient()
    
    # Single website scrape
    print("1. Single Website Scrape:")
    data = client.scrape_website("https://example.com")
    print(f"   Title: {data['title']}")
    print(f"   Paragraphs: {len(data['paragraphs'])}")
    print(f"   Images: {len(data['images'])}")
    print(f"   Links: {len(data['links'])}")
    if data['contacts']['emails']:
        print(f"   Emails: {data['contacts']['emails']}")
    
    # Extract contacts only
    print("\n2. Extract Contacts Only:")
    contacts = client.extract_contacts("https://example.com")
    print(f"   Emails: {contacts['contacts'].get('emails', [])}")
    print(f"   Phones: {contacts['contacts'].get('phones', [])}")
    
    # Batch scrape
    print("\n3. Batch Scrape (Multiple URLs):")
    urls = [
        "https://example.com",
        "https://example.org"
    ]
    results = client.batch_scrape(urls)
    print(f"   Total URLs: {results['total_urls']}")
    print(f"   Successful: {results['successful']}")
    print(f"   Failed: {results['failed']}")


def example_advanced():
    """Example: Advanced features"""
    print("\n=== ADVANCED EXAMPLES ===\n")
    
    client = WebScraperClient()
    
    # Deep scrape (follow links)
    print("1. Deep Scrape (Follow Links):")
    print("   Warning: This may take a while...")
    # Uncomment to run:
    # data = client.deep_scrape("https://example.com", max_depth=2, max_pages=10)
    # print(f"   Total pages scraped: {data['total_pages']}")
    
    # Search news
    print("\n2. Search News:")
    results = client.google_search("latest technology", search_type="news", num_results=5)
    print(f"   Found {results['total_results']} news articles")
    
    # Search images
    print("\n3. Search Images:")
    results = client.google_search("python logo", search_type="images", num_results=10)
    print(f"   Found {results['total_results']} images")


def example_system():
    """Example: System status"""
    print("\n=== SYSTEM STATUS ===\n")
    
    client = WebScraperClient()
    
    # Health check
    print("1. Health Check:")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Components: {health['components']}")
    
    # Detailed status
    print("\n2. Detailed Status:")
    status = client.status()
    print(f"   Version: {status['version']}")
    print(f"   Max concurrent requests: {status['configuration']['max_concurrent_requests']}")
    print(f"   Proxy enabled: {status['configuration']['proxy_enabled']}")
    print(f"   Proxy stats: {status['proxy_stats']}")


def main():
    """Run all examples"""
    print("=" * 60)
    print("Web Scraping System - Usage Examples")
    print("=" * 60)
    
    try:
        # Check if API is running
        client = WebScraperClient()
        health = client.health_check()
        print(f"\n✓ API is running (status: {health['status']})")
        
        # Run examples
        example_system()
        example_search()
        example_website_scraping()
        example_advanced()
        
        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to API")
        print("  Make sure the API is running: python run.py")
        print("  Default URL: http://localhost:8000")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


if __name__ == "__main__":
    main()
