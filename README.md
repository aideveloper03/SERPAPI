# 🔍 Advanced Search Engine Scraping System

A high-performance, production-ready search engine scraping system with multi-engine support, automatic fallback, and advanced anti-detection capabilities.

## ✨ Features

### 🔎 Multi-Engine Support
- **Google** - Multiple fallback strategies (direct, mobile, browser, library)
- **DuckDuckGo** - Uses native library (fastest, most reliable)
- **Bing** - Full anti-detection support
- **Yahoo** - Complete search support

### 🚀 High Performance
- **50+ requests/minute** throughput
- **< 2 second** response time (average)
- Concurrent batch processing
- Connection pooling
- Async/await architecture

### 🕵️ Anti-Detection Strategies (6+)
1. **Fingerprint Randomization** - Browser fingerprints rotate automatically
2. **User-Agent Rotation** - Realistic browser signatures
3. **Proxy Rotation** - Auto-fetch and rotate proxies
4. **TLS Fingerprint Variation** - Randomized SSL/TLS settings
5. **Request Header Randomization** - Sec-CH-UA, Accept headers, etc.
6. **Stealth Browser Mode** - Playwright/Selenium with anti-detection scripts

### 🌐 Proxy Management
- **Auto-fetch free proxies** from 5+ public sources
- Support for HTTP, HTTPS, SOCKS4, SOCKS5
- Automatic health checking and rotation
- Custom proxy support via environment variables

### 🤖 Captcha Handling
- reCAPTCHA v2 (audio challenge)
- reCAPTCHA v3 (behavior simulation)
- Cloudflare Turnstile bypass
- Image captcha OCR (Tesseract + EasyOCR)
- hCaptcha support

### 🔄 Automatic Fallback
When one search engine fails, automatically tries the next:
```
Google → DuckDuckGo → Bing → Yahoo
```

### 📊 Search Types
- Web search
- News search
- Image search
- Video search

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd search-scraper

# Copy environment file
cp .env.example .env

# Start the services
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📖 API Usage

### Unified Search (Recommended)
The unified endpoint automatically handles fallback between search engines:

```bash
curl -X POST http://localhost:8000/api/v1/search/unified \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python web scraping",
    "num_results": 10,
    "search_type": "all",
    "enable_fallback": true
  }'
```

### Google Search
```bash
curl -X POST http://localhost:8000/api/v1/search/google \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "num_results": 10,
    "search_type": "all"
  }'
```

### DuckDuckGo Search (Fastest)
```bash
curl -X POST http://localhost:8000/api/v1/search/duckduckgo \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "num_results": 10
  }'
```

### Bing Search
```bash
curl -X POST http://localhost:8000/api/v1/search/bing \
  -H "Content-Type: application/json" \
  -d '{
    "query": "data science",
    "num_results": 10
  }'
```

### Yahoo Search
```bash
curl -X POST http://localhost:8000/api/v1/search/yahoo \
  -H "Content-Type: application/json" \
  -d '{
    "query": "web development",
    "num_results": 10
  }'
```

### Batch Search (Multiple Queries)
```bash
curl -X POST http://localhost:8000/api/v1/search/batch \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["python", "javascript", "rust", "go"],
    "num_results": 10,
    "engine": "auto"
  }'
```

### Search All Engines Concurrently
```bash
curl -X POST http://localhost:8000/api/v1/search/all-engines \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cloud computing",
    "num_results": 10
  }'
```

### News Search
```bash
curl -X POST http://localhost:8000/api/v1/search/unified \
  -H "Content-Type: application/json" \
  -d '{
    "query": "technology news",
    "search_type": "news",
    "num_results": 20
  }'
```

### Image Search
```bash
curl -X POST http://localhost:8000/api/v1/search/unified \
  -H "Content-Type: application/json" \
  -d '{
    "query": "nature wallpaper",
    "search_type": "images",
    "num_results": 20
  }'
```

### DuckDuckGo Instant Answer
```bash
curl http://localhost:8000/api/v1/search/instant/python%20programming
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API host address |
| `API_PORT` | `8000` | API port |
| `API_WORKERS` | `4` | Number of worker processes |
| `DEBUG` | `False` | Enable debug mode |
| `MAX_SEARCH_REQUESTS_PER_MINUTE` | `120` | Rate limit for searches |
| `MAX_CONCURRENT_REQUESTS` | `100` | Max concurrent connections |
| `USE_PROXY` | `True` | Enable proxy rotation |
| `AUTO_FETCH_PROXIES` | `True` | Auto-fetch free proxies |
| `CUSTOM_PROXIES` | `` | Comma-separated custom proxies |
| `ENABLE_CAPTCHA_SOLVER` | `True` | Enable captcha solving |
| `ENABLE_FALLBACK` | `True` | Enable search engine fallback |
| `FALLBACK_ORDER` | `google,duckduckgo,bing,yahoo` | Fallback order |
| `REQUEST_TIMEOUT` | `15` | Request timeout in seconds |
| `PAGE_LOAD_TIMEOUT` | `15` | Browser page load timeout |

### Custom Proxies

Add your own proxies via environment variable:

```bash
CUSTOM_PROXIES=http://proxy1:8080,socks5://user:pass@proxy2:1080,http://proxy3:3128
```

Supported formats:
- `http://host:port`
- `https://host:port`
- `socks4://host:port`
- `socks5://host:port`
- `socks5://user:pass@host:port`

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│                     Unified Search Engine                     │
│  ┌─────────┐ ┌─────────────┐ ┌──────┐ ┌───────┐            │
│  │ Google  │ │ DuckDuckGo  │ │ Bing │ │ Yahoo │            │
│  └────┬────┘ └──────┬──────┘ └──┬───┘ └───┬───┘            │
│       └──────────────┴──────────┴─────────┘                  │
│                         ▼                                     │
│              ┌─────────────────────┐                         │
│              │   Request Handler   │                         │
│              │  (6+ strategies)    │                         │
│              └──────────┬──────────┘                         │
│                         ▼                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  Anti-Detection Layer                │    │
│  │  • Fingerprint Randomization  • TLS Variation       │    │
│  │  • User-Agent Rotation        • Header Randomization │    │
│  │  • Proxy Rotation             • Stealth Browser      │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ▼                                     │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │ Proxy Manager  │  │ Captcha Solver │  │ Rate Limiter │   │
│  │ (auto-fetch)   │  │ (multi-type)   │  │ (token bucket)│   │
│  └────────────────┘  └────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   ├── search_scraper.py   # Search API endpoints
│   │   └── website_scraper.py  # Website scraping endpoints
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # Configuration management
│   ├── core/
│   │   ├── __init__.py
│   │   ├── captcha_solver.py   # Captcha detection & solving
│   │   ├── proxy_manager.py    # Proxy fetching & rotation
│   │   ├── rate_limiter.py     # Rate limiting
│   │   └── request_handler.py  # Request handling with anti-detection
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── google_scraper.py   # Google search scraper
│   │   ├── duckduckgo_scraper.py # DuckDuckGo scraper
│   │   ├── bing_scraper.py     # Bing search scraper
│   │   ├── yahoo_scraper.py    # Yahoo search scraper
│   │   └── generic_scraper.py  # Generic website scraper
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── contact_extractor.py
│   │   └── content_parser.py
│   └── utils/
│       ├── __init__.py
│       ├── helpers.py
│       └── user_agents.py
├── config/
│   ├── config.yaml
│   ├── proxies.txt             # HTTP proxies (optional)
│   └── socks_proxies.txt       # SOCKS proxies (optional)
├── logs/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 Advanced Usage

### Python SDK

```python
import asyncio
from app.scrapers import GoogleScraper, DuckDuckGoScraper, BingScraper, YahooScraper

async def main():
    # Initialize scrapers
    google = GoogleScraper()
    ddg = DuckDuckGoScraper()
    bing = BingScraper()
    yahoo = YahooScraper()
    
    # Google search with fallback
    result = await google.search(
        query="python web scraping",
        num_results=10,
        search_type="all",
        fast_mode=True
    )
    
    if result['success']:
        for item in result['results']:
            print(f"{item['title']}: {item['url']}")
    
    # DuckDuckGo (fastest)
    result = await ddg.search(
        query="machine learning",
        num_results=20
    )
    
    # Batch search
    queries = ["python", "javascript", "rust"]
    tasks = [ddg.search(q, num_results=5) for q in queries]
    results = await asyncio.gather(*tasks)

asyncio.run(main())
```

### Custom Proxy Configuration

```python
from app.core.proxy_manager import proxy_manager

# Add custom proxies at runtime
proxy_manager._add_proxy("http://myproxy:8080", source="custom")
proxy_manager._add_proxy("socks5://user:pass@socks.example.com:1080", source="custom")
```

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Start with development mode
docker-compose --profile dev up -d

# Start with nginx (production)
docker-compose --profile production up -d

# Rebuild without cache
docker-compose build --no-cache
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/status` | GET | Detailed status |
| `/proxy-stats` | GET | Proxy statistics |
| `/api/v1/search/unified` | POST | Unified search with fallback |
| `/api/v1/search/all-engines` | POST | Search all engines concurrently |
| `/api/v1/search/google` | POST | Google search |
| `/api/v1/search/duckduckgo` | POST | DuckDuckGo search |
| `/api/v1/search/bing` | POST | Bing search |
| `/api/v1/search/yahoo` | POST | Yahoo search |
| `/api/v1/search/batch` | POST | Batch search |
| `/api/v1/search/instant/{query}` | GET | DuckDuckGo instant answer |
| `/docs` | GET | Swagger UI documentation |
| `/redoc` | GET | ReDoc documentation |

## 🔒 Security Considerations

- Never expose the API directly to the internet without authentication
- Use a reverse proxy (nginx) with rate limiting in production
- Monitor proxy health and rotate frequently
- Be respectful of search engines' terms of service
- Implement proper error handling and logging

## 📈 Performance Tips

1. **Use DuckDuckGo for speed** - It uses a native library, no scraping needed
2. **Enable fast_mode** - Reduces pages fetched per search
3. **Use batch endpoint** - For multiple queries
4. **Configure proper timeouts** - Lower values = faster failures
5. **Monitor proxy health** - Remove slow/dead proxies
6. **Use Redis** - For distributed rate limiting

## 🐛 Troubleshooting

### Common Issues

**1. Brotli encoding error**
```bash
pip install Brotli brotlicffi
```

**2. Playwright not working**
```bash
playwright install chromium
playwright install-deps chromium
```

**3. No results from Google**
- Google is heavily blocked; use unified search with fallback
- DuckDuckGo is most reliable

**4. Slow response times**
- Enable proxy rotation
- Use fast_mode=true
- Reduce num_results

**5. Captcha detected**
- System will attempt to solve automatically
- Try different search engine
- Use more proxies

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines first.

## 📞 Support

For issues and feature requests, please use the GitHub issue tracker.
