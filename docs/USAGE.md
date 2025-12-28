# Usage Guide

## Quick Start

### 1. Start the Service

```bash
# Using Docker (recommended)
docker-compose up -d

# Using Python directly
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Check Health

```bash
curl http://localhost:8000/health
```

### 3. Perform a Search

```bash
curl -X POST http://localhost:8000/api/v1/search/unified \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "num_results": 10}'
```

## API Endpoints

### Unified Search (Recommended)

The unified endpoint provides automatic fallback between search engines:

```bash
POST /api/v1/search/unified
```

**Request Body:**
```json
{
    "query": "search query",
    "search_type": "all",
    "num_results": 10,
    "language": "en",
    "country": "us",
    "engines": ["google", "duckduckgo", "bing", "yahoo"],
    "enable_fallback": true,
    "fast_mode": true
}
```

**Response:**
```json
{
    "success": true,
    "query": "search query",
    "search_type": "all",
    "engine": "duckduckgo",
    "method": "library",
    "total_results": 10,
    "results": [
        {
            "title": "Result Title",
            "url": "https://example.com",
            "snippet": "Description of the result...",
            "displayed_url": "example.com",
            "source": "duckduckgo"
        }
    ]
}
```

### Individual Search Engines

#### Google Search
```bash
POST /api/v1/search/google
```

#### DuckDuckGo Search (Fastest)
```bash
POST /api/v1/search/duckduckgo
```

#### Bing Search
```bash
POST /api/v1/search/bing
```

#### Yahoo Search
```bash
POST /api/v1/search/yahoo
```

### Batch Search

Search multiple queries concurrently:

```bash
POST /api/v1/search/batch
```

**Request Body:**
```json
{
    "queries": ["python", "javascript", "rust", "go"],
    "search_type": "all",
    "num_results": 10,
    "engine": "auto"
}
```

### All Engines Search

Search all engines concurrently and combine results:

```bash
POST /api/v1/search/all-engines
```

### Instant Answer

Get DuckDuckGo instant answer (definitions, facts):

```bash
GET /api/v1/search/instant/{query}
```

## Search Types

### Web Search (default)
```json
{"search_type": "all"}
```

### News Search
```json
{"search_type": "news"}
```

### Image Search
```json
{"search_type": "images"}
```

### Video Search
```json
{"search_type": "videos"}
```

## Examples

### Python

```python
import requests

# Unified search
response = requests.post(
    "http://localhost:8000/api/v1/search/unified",
    json={
        "query": "machine learning",
        "num_results": 10,
        "enable_fallback": True
    }
)

data = response.json()
for result in data['results']:
    print(f"{result['title']}: {result['url']}")
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/v1/search/unified', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        query: 'web development',
        num_results: 10
    })
});

const data = await response.json();
data.results.forEach(result => {
    console.log(`${result.title}: ${result.url}`);
});
```

### cURL

```bash
# Web search
curl -X POST http://localhost:8000/api/v1/search/unified \
  -H "Content-Type: application/json" \
  -d '{"query": "python tutorial", "num_results": 10}'

# News search
curl -X POST http://localhost:8000/api/v1/search/unified \
  -H "Content-Type: application/json" \
  -d '{"query": "technology news", "search_type": "news"}'

# Batch search
curl -X POST http://localhost:8000/api/v1/search/batch \
  -H "Content-Type: application/json" \
  -d '{"queries": ["python", "java", "rust"], "num_results": 5}'
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Detailed Status
```bash
curl http://localhost:8000/status
```

### Proxy Statistics
```bash
curl http://localhost:8000/proxy-stats
```

## Performance Tips

1. **Use DuckDuckGo for speed** - Uses native library, no scraping
2. **Enable fast_mode** - Fewer pages per search
3. **Use batch endpoint** - For multiple queries
4. **Lower num_results** - Faster response times
5. **Monitor proxy health** - Check `/proxy-stats` regularly

## Troubleshooting

### No Results
- Try different search engine
- Check proxy health
- Enable fallback

### Slow Response
- Use DuckDuckGo
- Enable fast_mode
- Lower num_results
- Check proxy latency

### Blocked by Search Engine
- Automatic fallback will try other engines
- Check proxy quality
- Reduce request frequency
