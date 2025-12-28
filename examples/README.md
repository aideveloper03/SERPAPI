# Usage Examples

This directory contains example code demonstrating how to use the Web Scraping System API.

## Files

- **example_usage.py**: Comprehensive Python examples for all API endpoints

## Running Examples

### Prerequisites

Make sure the API is running:

```bash
# Start the API
python run.py

# Or with Docker
docker-compose up -d
```

### Run Examples

```bash
# Run all examples
python examples/example_usage.py
```

### Individual Examples

```python
from examples.example_usage import WebScraperClient

client = WebScraperClient()

# Search Google
results = client.google_search("python programming", num_results=10)
print(f"Found {results['total_results']} results")

# Scrape website
data = client.scrape_website("https://example.com")
print(f"Title: {data['title']}")
print(f"Emails: {data['contacts']['emails']}")

# Batch scrape
urls = ["https://example.com", "https://example.org"]
results = client.batch_scrape(urls)
print(f"Scraped {results['successful']}/{results['total_urls']} sites")
```

## Example Categories

### 1. Search Engine Examples

- Google search (all, news, images, videos)
- DuckDuckGo search
- Combined search (both engines)
- Batch search (multiple queries)

### 2. Website Scraping Examples

- Single website scrape
- Batch scrape (multiple URLs)
- Deep scrape (follow links)
- Extract contacts only
- Extract content only
- Extract metadata only

### 3. Advanced Examples

- Deep scraping with link following
- JavaScript-heavy site scraping
- Proxy usage
- Rate limiting handling

### 4. System Examples

- Health check
- System status
- Configuration check

## Code Examples

### Basic Search

```python
from examples.example_usage import WebScraperClient

client = WebScraperClient()

# Search
results = client.google_search("python tutorial", num_results=10)

# Display results
for result in results['results']:
    print(f"{result['title']}: {result['url']}")
```

### Website Scraping

```python
from examples.example_usage import WebScraperClient

client = WebScraperClient()

# Scrape website
data = client.scrape_website("https://example.com")

# Access extracted data
print(f"Title: {data['title']}")
print(f"Emails: {data['contacts']['emails']}")
print(f"Phones: {data['contacts']['phones']}")
print(f"Paragraphs: {len(data['paragraphs'])}")
```

### Batch Processing

```python
from examples.example_usage import WebScraperClient

client = WebScraperClient()

# Batch search
queries = ["python", "javascript", "java"]
results = client.batch_google_search(queries, num_results=5)

for result in results['results']:
    print(f"{result['query']}: {result['total_results']} results")

# Batch scrape
urls = ["https://example.com", "https://example.org"]
results = client.batch_scrape(urls)

for site in results['results']:
    if site['success']:
        print(f"{site['url']}: {site['title']}")
```

## Error Handling

```python
from examples.example_usage import WebScraperClient
import requests

client = WebScraperClient()

try:
    data = client.scrape_website("https://example.com")
    
    if not data['success']:
        print(f"Scraping failed: {data.get('error')}")
    else:
        print(f"Success! Title: {data['title']}")
        
except requests.exceptions.RequestException as e:
    print(f"Request error: {e}")
except Exception as e:
    print(f"Error: {e}")
```

## Tips

1. **Start Simple**: Begin with basic examples before trying advanced features
2. **Check API Status**: Always verify the API is running first
3. **Handle Errors**: Implement proper error handling in production code
4. **Rate Limiting**: Be aware of rate limits (60 search/min, 30 website/min)
5. **Use Batch Endpoints**: More efficient for multiple requests

## Next Steps

- Read the full [API documentation](http://localhost:8000/docs)
- Check [USAGE.md](../docs/USAGE.md) for detailed API reference
- Explore [CONFIGURATION.md](../docs/CONFIGURATION.md) for tuning options
