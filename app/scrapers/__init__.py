"""
Search Engine Scrapers
Provides fast, reliable scraping for multiple search engines with automatic fallback
"""

from .google_scraper import GoogleScraper
from .duckduckgo_scraper import DuckDuckGoScraper
from .bing_scraper import BingScraper
from .yahoo_scraper import YahooScraper
from .unified_search import UnifiedSearch, unified_search, SearchEngine, SearchResult
from .generic_scraper import GenericScraper

__all__ = [
    'GoogleScraper',
    'DuckDuckGoScraper',
    'BingScraper',
    'YahooScraper',
    'UnifiedSearch',
    'unified_search',
    'SearchEngine',
    'SearchResult',
    'GenericScraper',
]
