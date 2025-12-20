# Usage Guide

## API Overview

The system provides multiple search endpoints optimized for different use cases.

## Endpoint Reference

### 1. Unified Search (Recommended)

**POST** `/api/v1/search/unified`

Smart search with automatic fallback. Best balance of reliability and speed.

```python
import requests

response = requests.post("http://localhost:8000/api/v1/search/unified", json={
    "query": "python web scraping",
    "preferred_engine": "google",  # google, duckduckgo, bing, yahoo
    "use_fallback": True,          # Fallback on failure
    "num_results": 10,
    "search_type": "all",          # all, news, images, videos
    "language": "en"
})

result = response.json()
print(f"Engine used: {result['engine']}")
print(f"Fallback: {result['fallback_used']}")
print(f"Results: {result['total_results']}")
```

### 2. Fast Search

**POST** `/api/v1/search/fast`

Speed-optimized search using DuckDuckGo API.

```python
response = requests.post("http://localhost:8000/api/v1/search/fast", json={
    "query": "machine learning",
    "num_results": 10
})
```

### 3. Parallel Search

**POST** `/api/v1/search/parallel`

Searches all engines simultaneously and merges results.

```python
response = requests.post("http://localhost:8000/api/v1/search/parallel", json={
    "query": "artificial intelligence",
    "search_type": "all",
    "num_results": 20
})

# Results from multiple engines
result = response.json()
print(f"Engines used: {result['engine']}")  # e.g., "google,duckduckgo,bing"
```

### 4. Batch Search

**POST** `/api/v1/search/batch`

Process multiple queries concurrently.

```python
response = requests.post("http://localhost:8000/api/v1/search/batch", json={
    "queries": ["python", "javascript", "rust", "golang"],
    "num_results": 5,
    "preferred_engine": "google"
})

results = response.json()
for item in results['results']:
    print(f"{item['query']}: {item['total_results']} results")
```

### 5. Individual Engine Endpoints

Direct access to specific engines:

```python
# Google (with fallback)
requests.post("/api/v1/search/google", json={"query": "..."})

# DuckDuckGo
requests.post("/api/v1/search/duckduckgo", json={"query": "..."})

# Bing
requests.post("/api/v1/search/bing", json={"query": "..."})

# Yahoo
requests.post("/api/v1/search/yahoo", json={"query": "..."})
```

## Search Types

All endpoints support different search types:

| Type | Description |
|------|-------------|
| `all` | Web search (default) |
| `news` | News articles |
| `images` | Image search |
| `videos` | Video search |

```python
# News search
response = requests.post("/api/v1/search/unified", json={
    "query": "technology news",
    "search_type": "news",
    "num_results": 10
})
```

## Response Format

### Success Response

```json
{
    "success": true,
    "query": "python programming",
    "search_type": "all",
    "total_results": 10,
    "engine": "google",
    "response_time": 1.23,
    "fallback_used": false,
    "results": [
        {
            "title": "Welcome to Python.org",
            "url": "https://www.python.org/",
            "snippet": "The official home of the Python Programming Language",
            "displayed_url": "https://www.python.org"
        }
    ]
}
```

### Error Response

```json
{
    "success": false,
    "query": "test query",
    "error": "All search engines failed",
    "results": []
}
```

## Rate Limiting

Default limits:
- 100 search requests per minute
- 100 concurrent connections

If rate limited, wait or increase limits in `.env`.

## Caching

Results are cached for 5 minutes by default.

To bypass cache:
```python
response = requests.post("/api/v1/search/unified", json={
    "query": "...",
    "use_cache": False
})
```

To clear cache:
```python
requests.post("/api/v1/search/cache/clear")
```

## Statistics

Get engine performance stats:

```python
response = requests.get("/api/v1/search/stats")
stats = response.json()
# {
#     "google": {"successes": 50, "failures": 2, "success_rate": 96.2},
#     "duckduckgo": {"successes": 30, "failures": 0, "success_rate": 100.0},
#     ...
# }
```

## Best Practices

1. **Use unified search** for most cases - it handles failures gracefully
2. **Use fast search** when speed is critical
3. **Use parallel search** for comprehensive results
4. **Enable caching** to reduce load and speed up repeated queries
5. **Use batch search** for multiple queries to maximize throughput
