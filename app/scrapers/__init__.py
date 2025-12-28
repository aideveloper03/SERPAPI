"""
Search Engine Scrapers
Supports: Google, DuckDuckGo, Bing, Yahoo, and Alternative providers
"""
from .google_scraper import GoogleScraper
from .duckduckgo_scraper import DuckDuckGoScraper, DuckDuckGoInstantAnswer
from .bing_scraper import BingScraper
from .yahoo_scraper import YahooScraper
from .generic_scraper import GenericScraper
from .alternative_scraper import AlternativeScraper, alternative_scraper

__all__ = [
    'GoogleScraper',
    'DuckDuckGoScraper',
    'DuckDuckGoInstantAnswer',
    'BingScraper',
    'YahooScraper',
    'GenericScraper',
    'AlternativeScraper',
    'alternative_scraper',
]
