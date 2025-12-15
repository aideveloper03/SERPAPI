"""
Helper utility functions
"""
import re
import uuid
from typing import Optional
from urllib.parse import urlparse, urljoin
import tldextract


def sanitize_url(url: str) -> str:
    """Sanitize and validate URL"""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}"


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalize URL (handle relative URLs)"""
    if base_url and not url.startswith(("http://", "https://", "//")):
        return urljoin(base_url, url)
    return url


def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def generate_request_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())


def clean_text(text: str) -> str:
    """Clean extracted text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?;:()\-\'"@]', '', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
