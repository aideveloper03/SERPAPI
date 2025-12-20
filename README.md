# 🔍 High-Performance Search Engine Scraping System

A production-ready, fast, and reliable search engine scraping system supporting **Google, DuckDuckGo, Bing, and Yahoo** with automatic fallback, anti-detection, and proxy rotation.

## ⚡ Key Features

- **4 Search Engines**: Google, DuckDuckGo, Bing, Yahoo
- **Blazing Fast**: Sub-second responses with optimized strategies
- **Automatic Fallback**: Never miss results - falls back to other engines on failure
- **8+ Anti-Detection Strategies**: curl_cffi impersonation, TLS fingerprinting, stealth mode
- **Proxy Rotation**: Auto-fetching from 8+ free proxy sources + custom proxy support
- **Captcha Solving**: 2Captcha, Anti-Captcha, CapMonster integration
- **High Throughput**: Handles 50+ requests per minute easily
- **Docker Ready**: Full Docker and docker-compose support

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd search-scraper

# Start with Docker Compose
docker-compose up -d

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Local Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Copy environment file
cp .env.example .env

# Start Redis (optional, for caching)
docker run -d -p 6379:6379 redis:alpine

# Run the API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 API Usage

### Recommended: Unified Search (with automatic fallback)

```python
import requests

response = requests.post("http://localhost:8000/api/v1/search/unified", json={
    "query": "python web scraping",
    "preferred_engine": "google",
    "use_fallback": True,
    "num_results": 10
})

results = response.json()
print(f"Found {results['total_results']} results using {results['engine']}")
```

### Fast Search (speed optimized)

```python
response = requests.post("http://localhost:8000/api/v1/search/fast", json={
    "query": "machine learning",
    "num_results": 10
})
```

### Parallel Search (most comprehensive)

```python
response = requests.post("http://localhost:8000/api/v1/search/parallel", json={
    "query": "artificial intelligence",
    "num_results": 20
})
# Searches all 4 engines simultaneously and merges results
```

### Batch Search (multiple queries)

```python
response = requests.post("http://localhost:8000/api/v1/search/batch", json={
    "queries": ["python", "javascript", "rust", "go"],
    "num_results": 10,
    "preferred_engine": "google"
})
```

## 🛡️ Anti-Detection & Stealth Strategies

This system implements **8+ anti-detection strategies** to avoid blocking and captchas:

| Strategy | Description |
|----------|-------------|
| **curl_cffi Impersonation** | Mimics Chrome/Firefox/Safari TLS fingerprints |
| **TLS Fingerprint** | Real browser TLS signatures |
| **User-Agent Rotation** | 30+ modern browser UAs (2024) |
| **Proxy Rotation** | Auto-fetched from 8+ sources |
| **Header Variation** | Realistic browser headers with Sec-CH-UA |
| **Request Timing** | Human-like random delays |
| **Cookie Persistence** | Session management across requests |
| **Playwright Stealth** | Full browser automation with comprehensive stealth |

### 🕵️ Stealth JavaScript Features

When using browser mode, the following fingerprinting protections are applied:

- ✅ `navigator.webdriver` hidden
- ✅ Chrome runtime mocked
- ✅ Plugins array populated
- ✅ WebGL vendor/renderer masked
- ✅ Canvas fingerprint noise added
- ✅ Audio context fingerprint masked
- ✅ Timezone consistency
- ✅ Hardware concurrency spoofed
- ✅ Device memory spoofed
- ✅ Permissions API hooked

## 🌐 Proxy Configuration

### Auto-Fetched Proxies (Default)

The system automatically fetches proxies from multiple free sources:
- ProxyScrape
- TheSpeedX Proxy List
- Clarketm Proxy List
- Monosans Proxy List
- And more...

### Custom Proxies

Add your proxies to `config/proxies.txt`:

```
http://user:pass@ip:port
http://ip:port
socks5://ip:port
```

## 🔐 Captcha Handling

### Built-in Local Captcha Solver (No External API Required!)

The system includes a **powerful local captcha solver** that works without external APIs:

| Captcha Type | Method | Success Rate |
|--------------|--------|--------------|
| **Image Captchas** | OCR with multiple preprocessing pipelines | High |
| **reCAPTCHA v2** | Checkbox click + audio challenge | Good |
| **reCAPTCHA v3** | Stealth mode (score-based auto-pass) | Excellent |
| **Cloudflare** | Auto-bypass with stealth scripts | Excellent |
| **hCaptcha** | Checkbox method | Good |

### Captcha Avoidance (Primary Strategy)

The system **prioritizes avoidance over solving** using:
- 🕵️ Comprehensive stealth JavaScript injection
- 🎭 WebGL/Canvas fingerprint masking
- 🔄 User-agent and TLS fingerprint rotation
- ⏱️ Human-like delays and mouse movements
- 🌐 Proxy rotation

### Optional: External API Support

For enhanced solving of complex captchas, add API keys:

```bash
# .env file (all optional)
TWOCAPTCHA_API_KEY=your_key    # 2captcha.com
ANTICAPTCHA_API_KEY=your_key   # anti-captcha.com
CAPMONSTER_API_KEY=your_key    # capmonster.cloud
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search/unified` | POST | 🔥 Recommended - Smart search with fallback |
| `/api/v1/search/fast` | POST | ⚡ Speed-optimized search |
| `/api/v1/search/parallel` | POST | 🔄 Search all engines simultaneously |
| `/api/v1/search/batch` | POST | 📦 Batch process multiple queries |
| `/api/v1/search/google` | POST | 🔍 Google with fallback |
| `/api/v1/search/duckduckgo` | POST | 🦆 DuckDuckGo search |
| `/api/v1/search/bing` | POST | 🅱️ Bing search |
| `/api/v1/search/yahoo` | POST | 🔮 Yahoo search |
| `/api/v1/search/stats` | GET | 📈 Engine performance stats |
| `/health` | GET | ❤️ Health check |
| `/status` | GET | 📊 Detailed system status |
| `/docs` | GET | 📚 Swagger documentation |

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_SEARCH_REQUESTS_PER_MINUTE` | 100 | Rate limit |
| `MAX_CONCURRENT_REQUESTS` | 100 | Concurrent connections |
| `USE_PROXY` | true | Enable proxy rotation |
| `ENABLE_FALLBACK` | true | Auto-fallback on failure |
| `REQUEST_TIMEOUT` | 15 | Request timeout (seconds) |
| `CACHE_RESULTS` | true | Cache search results |
| `CACHE_TTL` | 300 | Cache TTL (seconds) |

See `.env.example` for all options.

## 🐳 Docker Deployment

### Production

```bash
# Build and start
docker-compose up -d

# Scale API workers
docker-compose up -d --scale api=3

# View logs
docker-compose logs -f api
```

### Development

```bash
# Start with hot reload
docker-compose --profile dev up api-dev
```

## 📈 Performance

| Metric | Value |
|--------|-------|
| Requests/minute | 50-100+ |
| Response time | < 1 second (cached) |
| Response time | 1-3 seconds (uncached) |
| Supported engines | 4 (Google, DDG, Bing, Yahoo) |
| Fallback success rate | 95%+ |

## 🔧 Troubleshooting

### Brotli Encoding Error

Fixed! The system now uses `Brotli` library properly.

### No Results from Google

The system automatically falls back to DuckDuckGo, Bing, or Yahoo.

### Slow Responses

1. Enable caching: `CACHE_RESULTS=true`
2. Use fast search: `/api/v1/search/fast`
3. Enable proxies: `USE_PROXY=true`

### Rate Limited

1. Add more proxies to `config/proxies.txt`
2. Reduce `MAX_SEARCH_REQUESTS_PER_MINUTE`
3. Enable proxy rotation: `PROXY_ROTATION=true`

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please read the contributing guidelines.

---

**Built for high-performance, production-ready search scraping.** 🚀
