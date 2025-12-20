# Examples

This directory contains example code for using the Search Engine Scraping API.

## Running Examples

1. Start the API server:
   ```bash
   # Using Docker
   docker-compose up -d

   # Or locally
   python -m uvicorn app.main:app --reload
   ```

2. Run the examples:
   ```bash
   python examples/example_usage.py
   ```

## Example Files

- `example_usage.py` - Complete examples of all API endpoints

## Quick Examples

### Python

```python
import requests

# Fast search
response = requests.post("http://localhost:8000/api/v1/search/fast", json={
    "query": "python tutorial",
    "num_results": 10
})
print(response.json())
```

### cURL

```bash
# Unified search with fallback
curl -X POST http://localhost:8000/api/v1/search/unified \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "preferred_engine": "google",
    "use_fallback": true
  }'
```

### JavaScript

```javascript
const search = async (query) => {
  const response = await fetch('http://localhost:8000/api/v1/search/fast', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, num_results: 10 })
  });
  return response.json();
};

search('web development').then(console.log);
```
