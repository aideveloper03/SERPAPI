# 🚀 Quick Start Guide

Get the search scraping system running in under 5 minutes.

## Option 1: Docker (Easiest)

```bash
# Start everything
docker-compose up -d

# Test it works
curl -X POST http://localhost:8000/api/v1/search/fast \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "num_results": 5}'

# View API documentation
open http://localhost:8000/docs
```

## Option 2: Local Python

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install browser for Playwright
playwright install chromium

# 4. Start the API
python -m uvicorn app.main:app --reload

# 5. Test it
curl -X POST http://localhost:8000/api/v1/search/fast \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "num_results": 5}'
```

## Basic Usage Examples

### Python

```python
import requests

# Fast search
response = requests.post("http://localhost:8000/api/v1/search/fast", json={
    "query": "machine learning tutorials",
    "num_results": 10
})
print(response.json())

# Google with fallback
response = requests.post("http://localhost:8000/api/v1/search/google", json={
    "query": "web scraping python",
    "search_type": "all",
    "num_results": 10
})
print(response.json())
```

### cURL

```bash
# Fast search
curl -X POST http://localhost:8000/api/v1/search/fast \
  -H "Content-Type: application/json" \
  -d '{"query": "python web scraping"}'

# Parallel search (all engines)
curl -X POST http://localhost:8000/api/v1/search/parallel \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence", "num_results": 20}'

# Batch search
curl -X POST http://localhost:8000/api/v1/search/batch \
  -H "Content-Type: application/json" \
  -d '{"queries": ["python", "javascript", "rust"]}'
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/v1/search/fast', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'react tutorials', num_results: 10 })
});
const data = await response.json();
console.log(data);
```

## API Endpoints Summary

| Endpoint | Description | Speed |
|----------|-------------|-------|
| `/api/v1/search/fast` | Fastest, uses DDG API | ⚡⚡⚡ |
| `/api/v1/search/unified` | Smart with fallback | ⚡⚡ |
| `/api/v1/search/google` | Google primary | ⚡⚡ |
| `/api/v1/search/parallel` | All engines at once | ⚡ |

## Response Format

```json
{
  "success": true,
  "query": "python programming",
  "search_type": "all",
  "total_results": 10,
  "engine": "duckduckgo",
  "response_time": 0.45,
  "results": [
    {
      "title": "Python.org",
      "url": "https://www.python.org",
      "snippet": "The official home of the Python Programming Language..."
    }
  ]
}
```

## Need Help?

- 📚 Full docs: http://localhost:8000/docs
- 📊 System status: http://localhost:8000/status
- ❤️ Health check: http://localhost:8000/health
