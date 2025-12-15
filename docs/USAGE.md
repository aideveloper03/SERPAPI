# API Usage Guide

Comprehensive guide for using the Web Scraping System API.

## Table of Contents

1. [Introduction](#introduction)
2. [API Overview](#api-overview)
3. [Search Engine Scraping](#search-engine-scraping)
4. [Website Scraping](#website-scraping)
5. [Advanced Features](#advanced-features)
6. [Code Examples](#code-examples)
7. [Best Practices](#best-practices)
8. [Error Handling](#error-handling)

---

## Introduction

The Web Scraping System provides RESTful APIs for:
- **Search Engine Scraping**: Google and DuckDuckGo
- **Website Scraping**: Any website with content extraction
- **High Volume**: 60+ search results/min, 30+ websites/min
- **Concurrent Processing**: Multiple requests simultaneously
- **Automatic Retries**: 2-3 fallback methods per request

---

## API Overview

### Base URL

```
http://localhost:8000
```

### Authentication

Current version doesn't require authentication (add as needed for production).

### Response Format

All responses are in JSON format:

**Success Response:**
```json
{
  "success": true,
  "data": {...},
  ...
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  ...
}
```

### Rate Limits

- Search endpoints: 60 requests/minute (configurable)
- Website endpoints: 30 requests/minute (configurable)
- Concurrent: Up to 50 simultaneous requests (configurable)

---

## Search Engine Scraping

### 1. Google Search

#### Endpoint

```
POST /api/v1/search/google
```

#### Request Body

```json
{
  "query": "python web scraping",
  "search_type": "all",
  "num_results": 10,
  "language": "en"
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | Yes | - | Search query |
| search_type | string | No | "all" | Type: all, news, images, videos |
| num_results | integer | No | 10 | Number of results (1-100) |
| language | string | No | "en" | Language code |

#### Response

```json
{
  "success": true,
  "query": "python web scraping",
  "search_type": "all",
  "total_results": 10,
  "results": [
    {
      "title": "Web Scraping with Python",
      "url": "https://example.com/article",
      "snippet": "Learn how to scrape websites...",
      "displayed_url": "example.com"
    }
  ]
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/v1/search/google \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python web scraping",
    "search_type": "all",
    "num_results": 10
  }'
```

#### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/search/google",
    json={
        "query": "python web scraping",
        "search_type": "all",
        "num_results": 10
    }
)

data = response.json()
for result in data['results']:
    print(f"{result['title']}: {result['url']}")
```

### 2. DuckDuckGo Search

#### Endpoint

```
POST /api/v1/search/duckduckgo
```

#### Request/Response

Same format as Google search.

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/v1/search/duckduckgo \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "num_results": 15}'
```

### 3. Combined Search

Search both Google and DuckDuckGo simultaneously.

#### Endpoint

```
POST /api/v1/search/combined
```

#### Response

```json
{
  "success": true,
  "query": "python",
  "search_type": "all",
  "google": {
    "success": true,
    "results": [...]
  },
  "duckduckgo": {
    "success": true,
    "results": [...]
  }
}
```

### 4. Batch Search

Scrape multiple queries concurrently.

#### Endpoint

```
POST /api/v1/search/google/batch
```

#### Request Body

```json
{
  "queries": ["python", "javascript", "java"],
  "search_type": "all",
  "num_results": 10
}
```

#### Response

```json
{
  "success": true,
  "total_queries": 3,
  "results": [
    {
      "success": true,
      "query": "python",
      "results": [...]
    },
    ...
  ]
}
```

#### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/search/google/batch",
    json={
        "queries": ["python", "javascript", "java"],
        "num_results": 5
    }
)

data = response.json()
for result in data['results']:
    print(f"Query: {result['query']}")
    print(f"Results: {result['total_results']}")
```

### 5. Search Types

#### All Results (default)

```json
{"search_type": "all"}
```

#### News

```json
{"search_type": "news"}
```

Response includes source and date.

#### Images

```json
{"search_type": "images"}
```

Response includes image URLs and page URLs.

#### Videos

```json
{"search_type": "videos"}
```

Response includes video URLs and duration.

---

## Website Scraping

### 1. Single Website Scrape

#### Endpoint

```
POST /api/v1/website/scrape
```

#### Request Body

```json
{
  "url": "https://example.com",
  "extract_contacts": true,
  "extract_links": true,
  "extract_images": true,
  "use_browser": false
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Target URL |
| extract_contacts | boolean | No | true | Extract emails, phones, etc. |
| extract_links | boolean | No | true | Extract all links |
| extract_images | boolean | No | true | Extract all images |
| use_browser | boolean | No | false | Force browser rendering |

#### Response

```json
{
  "success": true,
  "url": "https://example.com",
  "status_code": 200,
  "title": "Example Domain",
  "meta": {
    "description": "Example description",
    "keywords": "example, domain"
  },
  "headings": {
    "h1": ["Example Domain"],
    "h2": ["Subheading 1", "Subheading 2"]
  },
  "paragraphs": [
    {
      "text": "This is a paragraph...",
      "length": 100,
      "context": "Subheading 1"
    }
  ],
  "contacts": {
    "emails": ["info@example.com"],
    "phones": ["+1-555-1234"],
    "social_media": {
      "facebook": ["https://facebook.com/example"],
      "twitter": ["https://twitter.com/example"]
    },
    "addresses": []
  },
  "images": [
    {
      "src": "https://example.com/image.jpg",
      "alt": "Image description",
      "title": ""
    }
  ],
  "links": [
    {
      "url": "https://example.com/page",
      "text": "Link text",
      "title": ""
    }
  ],
  "structured_data": {
    "json_ld": [...],
    "opengraph": {...}
  },
  "main_content": "Main content text...",
  "text_content": "All visible text...",
  "language": "en",
  "statistics": {
    "total_paragraphs": 10,
    "total_headings": 5,
    "total_images": 8,
    "total_links": 20,
    "has_contacts": true,
    "email_count": 2,
    "phone_count": 1,
    "content_length": 5000
  }
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/v1/website/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "extract_contacts": true
  }'
```

#### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/website/scrape",
    json={
        "url": "https://example.com",
        "extract_contacts": True,
        "extract_links": True,
        "extract_images": True
    }
)

data = response.json()
print(f"Title: {data['title']}")
print(f"Emails: {data['contacts']['emails']}")
print(f"Paragraphs: {len(data['paragraphs'])}")
```

### 2. Batch Website Scrape

Scrape multiple websites concurrently.

#### Endpoint

```
POST /api/v1/website/scrape/batch
```

#### Request Body

```json
{
  "urls": [
    "https://example.com",
    "https://example.org",
    "https://example.net"
  ],
  "extract_contacts": true,
  "extract_links": false,
  "extract_images": false,
  "max_concurrent": 10
}
```

#### Response

```json
{
  "success": true,
  "total_urls": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "success": true,
      "url": "https://example.com",
      "title": "Example",
      ...
    },
    ...
  ]
}
```

#### Python Example

```python
import requests

urls = [
    "https://example.com",
    "https://example.org",
    "https://example.net"
]

response = requests.post(
    "http://localhost:8000/api/v1/website/scrape/batch",
    json={
        "urls": urls,
        "extract_contacts": True,
        "max_concurrent": 10
    }
)

data = response.json()
print(f"Successful: {data['successful']}/{data['total_urls']}")

for result in data['results']:
    if result['success']:
        print(f"{result['url']}: {result['title']}")
```

### 3. Deep Scrape (Follow Links)

Recursively scrape a website by following links.

#### Endpoint

```
POST /api/v1/website/scrape/deep
```

#### Request Body

```json
{
  "url": "https://example.com",
  "max_depth": 2,
  "max_pages": 50,
  "same_domain_only": true
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Starting URL |
| max_depth | integer | No | 2 | Maximum link depth (1-5) |
| max_pages | integer | No | 50 | Maximum pages to scrape (1-200) |
| same_domain_only | boolean | No | true | Only follow same domain links |

#### Response

```json
{
  "success": true,
  "start_url": "https://example.com",
  "total_pages": 25,
  "max_depth": 2,
  "pages": [
    {
      "success": true,
      "url": "https://example.com",
      "title": "Home",
      ...
    },
    ...
  ]
}
```

### 4. Quick Extract Endpoints

Extract specific content types only.

#### Extract Contacts Only

```
GET /api/v1/website/extract/contacts?url=https://example.com
```

Response:
```json
{
  "success": true,
  "url": "https://example.com",
  "contacts": {
    "emails": ["info@example.com"],
    "phones": ["+1-555-1234"],
    "social_media": {...}
  }
}
```

#### Extract Content Only

```
GET /api/v1/website/extract/content?url=https://example.com
```

Response:
```json
{
  "success": true,
  "url": "https://example.com",
  "title": "Example",
  "headings": {...},
  "paragraphs": [...],
  "main_content": "...",
  "text_content": "..."
}
```

#### Extract Metadata Only

```
GET /api/v1/website/extract/metadata?url=https://example.com
```

Response:
```json
{
  "success": true,
  "url": "https://example.com",
  "title": "Example",
  "meta": {...},
  "structured_data": {...},
  "language": "en"
}
```

---

## Advanced Features

### 1. Browser Rendering

For JavaScript-heavy websites, force browser rendering:

```json
{
  "url": "https://javascript-heavy-site.com",
  "use_browser": true
}
```

### 2. Handling Redirects

Redirects are followed automatically. Final URL is in response:

```json
{
  "url": "https://original.com",
  "final_url": "https://redirected.com"
}
```

### 3. Proxy Rotation

Proxies rotate automatically (if configured). No API changes needed.

### 4. Captcha Handling

Captchas are detected and solved automatically when possible.

### 5. Rate Limiting

Built-in rate limiting prevents overload:
- 60 search requests/minute
- 30 website scrapes/minute

Requests queue automatically when limit reached.

---

## Code Examples

### Python Full Example

```python
import requests
import json

BASE_URL = "http://localhost:8000"

class WebScraperAPI:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
    
    def google_search(self, query, num_results=10):
        """Search Google"""
        response = requests.post(
            f"{self.base_url}/api/v1/search/google",
            json={
                "query": query,
                "num_results": num_results
            }
        )
        return response.json()
    
    def scrape_website(self, url, extract_contacts=True):
        """Scrape a website"""
        response = requests.post(
            f"{self.base_url}/api/v1/website/scrape",
            json={
                "url": url,
                "extract_contacts": extract_contacts
            }
        )
        return response.json()
    
    def batch_scrape(self, urls, max_concurrent=10):
        """Scrape multiple websites"""
        response = requests.post(
            f"{self.base_url}/api/v1/website/scrape/batch",
            json={
                "urls": urls,
                "max_concurrent": max_concurrent
            }
        )
        return response.json()

# Usage
api = WebScraperAPI()

# Search Google
results = api.google_search("python web scraping", num_results=5)
print(f"Found {results['total_results']} results")

# Scrape website
data = api.scrape_website("https://example.com")
print(f"Title: {data['title']}")
print(f"Emails: {data['contacts']['emails']}")

# Batch scrape
urls = ["https://example.com", "https://example.org"]
batch_data = api.batch_scrape(urls)
print(f"Scraped {batch_data['successful']} of {batch_data['total_urls']} sites")
```

### JavaScript Example

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

class WebScraperAPI {
  async googleSearch(query, numResults = 10) {
    const response = await axios.post(
      `${BASE_URL}/api/v1/search/google`,
      {
        query: query,
        num_results: numResults
      }
    );
    return response.data;
  }
  
  async scrapeWebsite(url, extractContacts = true) {
    const response = await axios.post(
      `${BASE_URL}/api/v1/website/scrape`,
      {
        url: url,
        extract_contacts: extractContacts
      }
    );
    return response.data;
  }
}

// Usage
(async () => {
  const api = new WebScraperAPI();
  
  // Search
  const results = await api.googleSearch('python', 5);
  console.log(`Found ${results.total_results} results`);
  
  // Scrape
  const data = await api.scrapeWebsite('https://example.com');
  console.log(`Title: ${data.title}`);
})();
```

---

## Best Practices

### 1. Use Batch Endpoints

For multiple requests, use batch endpoints for better performance:

```python
# Good
batch_scrape(["url1", "url2", "url3"])

# Less efficient
for url in urls:
    scrape(url)
```

### 2. Extract Only What You Need

Disable unnecessary extractions:

```json
{
  "url": "https://example.com",
  "extract_contacts": true,
  "extract_links": false,
  "extract_images": false
}
```

### 3. Handle Errors Gracefully

```python
try:
    result = api.scrape_website(url)
    if not result['success']:
        print(f"Error: {result['error']}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

### 4. Respect Rate Limits

The API handles rate limiting automatically, but avoid overwhelming it:

```python
import time

for url in large_url_list:
    result = api.scrape_website(url)
    time.sleep(0.1)  # Small delay between requests
```

### 5. Use Browser Rendering Sparingly

Only use `use_browser=true` when necessary (slower):

```python
# For static sites (fast)
result = api.scrape_website(url, use_browser=False)

# For JavaScript-heavy sites (slower but necessary)
result = api.scrape_website(spa_url, use_browser=True)
```

---

## Error Handling

### Common Errors

#### 1. Invalid URL

```json
{
  "success": false,
  "error": "Invalid URL"
}
```

#### 2. Timeout

```json
{
  "success": false,
  "error": "Request timeout after 30 seconds"
}
```

#### 3. Rate Limit

```json
{
  "success": false,
  "error": "Rate limit exceeded"
}
```

#### 4. Blocked/Captcha

```json
{
  "success": false,
  "error": "All request strategies failed"
}
```

### Error Handling Example

```python
def safe_scrape(url):
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/website/scrape",
            json={"url": url},
            timeout=60
        )
        
        data = response.json()
        
        if not data.get('success'):
            print(f"Scraping failed: {data.get('error')}")
            return None
        
        return data
        
    except requests.exceptions.Timeout:
        print("Request timed out")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return None
```

---

## API Reference

For complete API reference, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Support

For issues or questions, refer to:
- Setup guide: [SETUP.md](SETUP.md)
- Configuration guide: [CONFIGURATION.md](CONFIGURATION.md)
- API documentation: http://localhost:8000/docs
- Logs: `logs/scraper.log`
