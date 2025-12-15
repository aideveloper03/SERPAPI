"""
Content Parser for extracting and categorizing website content
Extracts paragraphs, headings, lists, images, links, metadata, etc.
"""
import re
import json
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Comment
import extruct
from w3lib.html import get_base_url
from loguru import logger

from app.utils.helpers import clean_text, normalize_url
from .contact_extractor import ContactExtractor


class ContentParser:
    """
    Advanced content parser for web pages
    Extracts and categorizes all content types
    """
    
    def __init__(self):
        self.contact_extractor = ContactExtractor()
        self.min_paragraph_length = 50
    
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        """
        Parse HTML and extract all content
        
        Returns:
            Comprehensive dictionary of extracted content
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        self._remove_unwanted_elements(soup)
        
        # Extract all content types
        result = {
            'url': url,
            'title': self._extract_title(soup),
            'meta': self._extract_meta(soup),
            'headings': self._extract_headings(soup),
            'paragraphs': self._extract_paragraphs(soup),
            'lists': self._extract_lists(soup),
            'tables': self._extract_tables(soup),
            'images': self._extract_images(soup, url),
            'links': self._extract_links(soup, url),
            'structured_data': self._extract_structured_data(html, url),
            'contacts': self._extract_contacts(soup, html),
            'main_content': self._extract_main_content(soup),
            'language': self._detect_language(soup),
            'text_content': self._extract_text_content(soup)
        }
        
        return result
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove scripts, styles, and other unwanted elements"""
        unwanted_tags = ['script', 'style', 'noscript', 'iframe', 'nav', 'footer', 'header']
        
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        # Try <title> tag
        if soup.title:
            return clean_text(soup.title.string or "")
        
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return clean_text(h1.get_text())
        
        return ""
    
    def _extract_meta(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta tags"""
        meta_data = {}
        
        # Standard meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            
            if name and content:
                meta_data[name] = content
        
        # Description
        desc_meta = soup.find('meta', attrs={'name': 'description'}) or \
                   soup.find('meta', attrs={'property': 'og:description'})
        if desc_meta:
            meta_data['description'] = desc_meta.get('content', '')
        
        # Keywords
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta:
            meta_data['keywords'] = keywords_meta.get('content', '')
        
        # Author
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta:
            meta_data['author'] = author_meta.get('content', '')
        
        return meta_data
    
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract all headings (h1-h6)"""
        headings = {}
        
        for level in range(1, 7):
            tag = f'h{level}'
            heading_texts = []
            
            for heading in soup.find_all(tag):
                text = clean_text(heading.get_text())
                if text:
                    heading_texts.append(text)
            
            if heading_texts:
                headings[tag] = heading_texts
        
        return headings
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract paragraphs with context"""
        paragraphs = []
        
        for p in soup.find_all('p'):
            text = clean_text(p.get_text())
            
            # Filter out short paragraphs
            if len(text) >= self.min_paragraph_length:
                # Get context (parent heading)
                context = self._get_paragraph_context(p)
                
                paragraphs.append({
                    'text': text,
                    'length': len(text),
                    'context': context
                })
        
        return paragraphs
    
    def _get_paragraph_context(self, element) -> Optional[str]:
        """Get the nearest heading before a paragraph"""
        current = element
        
        while current:
            # Look for previous sibling heading
            for sibling in current.find_previous_siblings():
                if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    return clean_text(sibling.get_text())
            
            # Move up to parent
            current = current.parent
            if not current or current.name == 'body':
                break
        
        return None
    
    def _extract_lists(self, soup: BeautifulSoup) -> Dict[str, List[List[str]]]:
        """Extract ordered and unordered lists"""
        lists = {
            'ordered': [],
            'unordered': []
        }
        
        # Unordered lists
        for ul in soup.find_all('ul'):
            items = [clean_text(li.get_text()) for li in ul.find_all('li', recursive=False)]
            if items:
                lists['unordered'].append(items)
        
        # Ordered lists
        for ol in soup.find_all('ol'):
            items = [clean_text(li.get_text()) for li in ol.find_all('li', recursive=False)]
            if items:
                lists['ordered'].append(items)
        
        return lists
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract tables with headers and rows"""
        tables = []
        
        for table in soup.find_all('table'):
            table_data = {
                'headers': [],
                'rows': []
            }
            
            # Extract headers
            thead = table.find('thead')
            if thead:
                headers = thead.find_all('th')
                table_data['headers'] = [clean_text(th.get_text()) for th in headers]
            
            # Extract rows
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr'):
                cells = tr.find_all(['td', 'th'])
                row = [clean_text(cell.get_text()) for cell in cells]
                if row:
                    table_data['rows'].append(row)
            
            if table_data['rows']:
                tables.append(table_data)
        
        return tables
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract images with metadata"""
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
            
            # Normalize URL
            full_url = normalize_url(src, base_url)
            
            images.append({
                'src': full_url,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            })
        
        return images
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all links"""
        links = []
        seen_urls = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # Skip anchors and javascript
            if href.startswith(('#', 'javascript:', 'mailto:')):
                continue
            
            # Normalize URL
            full_url = normalize_url(href, base_url)
            
            # Avoid duplicates
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            links.append({
                'url': full_url,
                'text': clean_text(a.get_text()),
                'title': a.get('title', '')
            })
        
        return links
    
    def _extract_structured_data(self, html: str, url: str) -> Dict[str, Any]:
        """Extract structured data (JSON-LD, microdata, Open Graph, etc.)"""
        try:
            base_url = get_base_url(html, url)
            structured = extruct.extract(html, base_url=base_url)
            
            # Clean up and simplify
            result = {}
            
            if structured.get('json-ld'):
                result['json_ld'] = structured['json-ld']
            
            if structured.get('microdata'):
                result['microdata'] = structured['microdata']
            
            if structured.get('opengraph'):
                result['opengraph'] = structured['opengraph']
            
            if structured.get('microformat'):
                result['microformat'] = structured['microformat']
            
            return result
            
        except Exception as e:
            logger.debug(f"Structured data extraction error: {e}")
            return {}
    
    def _extract_contacts(self, soup: BeautifulSoup, html: str) -> Dict[str, Any]:
        """Extract contact information"""
        text = soup.get_text()
        
        # Extract from text
        contacts = self.contact_extractor.extract_all(text, html)
        
        # Also check structured data
        try:
            structured = self._extract_structured_data(html, "")
            if structured:
                structured_contacts = self.contact_extractor.extract_from_structured_data(structured)
                
                # Merge results
                contacts['emails'].extend(structured_contacts.get('emails', []))
                contacts['phones'].extend(structured_contacts.get('phones', []))
                
                # Remove duplicates
                contacts['emails'] = list(set(contacts['emails']))
                contacts['phones'] = list(set(contacts['phones']))
        except Exception as e:
            logger.debug(f"Structured contact extraction error: {e}")
        
        return contacts
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content using heuristics
        Looks for <main>, <article>, or largest content block
        """
        # Try semantic tags first
        main = soup.find('main')
        if main:
            return clean_text(main.get_text())
        
        article = soup.find('article')
        if article:
            return clean_text(article.get_text())
        
        # Look for divs with common content class names
        content_classes = ['content', 'main-content', 'article', 'post', 'entry-content']
        for class_name in content_classes:
            content = soup.find(class_=re.compile(class_name, re.I))
            if content:
                return clean_text(content.get_text())
        
        # Fallback: get body text
        body = soup.find('body')
        if body:
            return clean_text(body.get_text())
        
        return clean_text(soup.get_text())
    
    def _detect_language(self, soup: BeautifulSoup) -> str:
        """Detect page language"""
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag['lang']
        
        # Check meta tag
        lang_meta = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if lang_meta:
            return lang_meta.get('content', 'en')
        
        return 'en'  # Default
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract all visible text content"""
        return clean_text(soup.get_text(separator=' ', strip=True))
