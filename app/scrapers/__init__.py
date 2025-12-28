"""
Search Engine Scrapers
Supports: Google, DuckDuckGo, Bing, Yahoo
"""
from .google_scraper import GoogleScraper
from .duckduckgo_scraper import DuckDuckGoScraper, DuckDuckGoInstantAnswer
from .bing_scraper import BingScraper
from .yahoo_scraper import YahooScraper
from .generic_scraper import GenericScraper

__all__ = [
    'GoogleScraper',
    'DuckDuckGoScraper',
    'DuckDuckGoInstantAnswer',
    'BingScraper',
    'YahooScraper',
    'GenericScraper',
]
