# High-Volume Web Scraping System

A production-ready, high-volume concurrent web scraping system with search engine and generic website scrapers. Built with Python, FastAPI, and advanced scraping techniques.

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🚀 Features

### Core Capabilities

- **High-Volume Scraping**: 60+ search results/min, 30+ websites/min
- **Concurrent Processing**: Handle 50+ simultaneous requests
- **Multiple Fallback Methods**: 2-3 strategies per request for maximum success
- **Proxy Rotation**: Automatic IP rotation with health checking
- **Captcha Solving**: Automatic detection and solving (audio, image recognition)
- **Browser Automation**: Playwright and Selenium for JavaScript-heavy sites
- **Content Categorization**: Intelligent extraction of paragraphs, contacts, metadata
- **Rate Limiting**: Built-in token bucket rate limiting with Redis support
- **RESTful API**: Clean, documented FastAPI endpoints

### Search Engine Scraping

- **Google Search**: All, News, Images, Videos
- **DuckDuckGo Search**: All, News, Images, Videos
- **Batch Processing**: Scrape multiple queries concurrently
- **Combined Search**: Query both engines simultaneously

### Website Scraping

- **Generic Scraping**: Works with any website
- **Content Extraction**:
  - Title and metadata
  - Headings (h1-h6)
  - Paragraphs with context
  - Lists and tables
  - Images and links
  - Structured data (JSON-LD, Open Graph, microdata)
  
- **Contact Extraction**:
  - Email addresses (validated)
  - Phone numbers (international formats)
  - Social media links (Facebook, Twitter, LinkedIn, Instagram, YouTube)
  - Physical addresses
  
- **Advanced Features**:
  - Deep scraping (follow links)
  - Batch scraping (multiple URLs)
  - Quick extract endpoints (contacts, content, metadata only)

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Docker Deployment](#-docker-deployment)
- [Performance](#-performance)
- [Architecture](#-architecture)
- [Contributing](#-contributing)
- [License](#-license)

## ⚡ Quick Start

### Using Docker (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd web-scraping-system

# Start services
docker-compose up -d

# Check status
curl http://localhost:8000/health
```

### Manual Setup

```bash
# Clone repository
git clone <repository-url>
cd web-scraping-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (optional)
playwright install chromium

# Configure
cp .env.example .env
# Edit .env with your settings

# Run application
python app/main.py
```

### First Request

```bash
# Search Google
curl -X POST http://localhost:8000/api/v1/search/google \
  -H "Content-Type: application/json" \
  -d '{"query": "python web scraping", "num_results": 5}'

# Scrape website
curl -X POST http://localhost:8000/api/v1/website/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Redis (optional, for distributed rate limiting)
- Tesseract OCR (optional, for captcha solving)

### Step-by-Step Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd web-scraping-system
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

4. **Install optional components**

```bash
# Playwright (for JavaScript-heavy sites)
playwright install chromium

# Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Tesseract OCR (Ubuntu/Debian)
sudo apt-get install tesseract-ocr
```

5. **Configure the application**

```bash
cp .env.example .env
# Edit .env with your settings
```

6. **Run the application**

```bash
python app/main.py
```

See [docs/SETUP.md](docs/SETUP.md) for detailed installation instructions.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Rate Limiting
MAX_SEARCH_REQUESTS_PER_MINUTE=60
MAX_WEBSITE_REQUESTS_PER_MINUTE=30
MAX_CONCURRENT_REQUESTS=50

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379

# Proxy (optional)
USE_PROXY=True
PROXY_ROTATION=True

# Scraping
JAVASCRIPT_RENDERING=True
BROWSER_HEADLESS=True
REQUEST_TIMEOUT=30
MAX_RETRIES=3
```

### Proxy Configuration

Add proxies to `config/proxies.txt`:

```
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:3128
socks5://proxy3.example.com:1080
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for detailed configuration options.

## 📖 Usage

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Google Search
response = requests.post(
    f"{BASE_URL}/api/v1/search/google",
    json={
        "query": "python web scraping",
        "search_type": "all",
        "num_results": 10
    }
)
results = response.json()
print(f"Found {results['total_results']} results")

# Scrape Website
response = requests.post(
    f"{BASE_URL}/api/v1/website/scrape",
    json={
        "url": "https://example.com",
        "extract_contacts": True
    }
)
data = response.json()
print(f"Title: {data['title']}")
print(f"Emails: {data['contacts']['emails']}")

# Batch Scrape
response = requests.post(
    f"{BASE_URL}/api/v1/website/scrape/batch",
    json={
        "urls": [
            "https://example.com",
            "https://example.org",
            "https://example.net"
        ],
        "max_concurrent": 10
    }
)
batch_data = response.json()
print(f"Scraped {batch_data['successful']}/{batch_data['total_urls']} sites")
```

### cURL Examples

```bash
# Google Search - All Results
curl -X POST http://localhost:8000/api/v1/search/google \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "num_results": 10}'

# Google Search - News
curl -X POST http://localhost:8000/api/v1/search/google \
  -H "Content-Type: application/json" \
  -d '{"query": "latest news", "search_type": "news", "num_results": 20}'

# DuckDuckGo Search
curl -X POST http://localhost:8000/api/v1/search/duckduckgo \
  -H "Content-Type: application/json" \
  -d '{"query": "python tutorial", "num_results": 15}'

# Website Scrape
curl -X POST http://localhost:8000/api/v1/website/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "extract_contacts": true}'

# Extract Contacts Only
curl "http://localhost:8000/api/v1/website/extract/contacts?url=https://example.com"

# Deep Scrape (Follow Links)
curl -X POST http://localhost:8000/api/v1/website/scrape/deep \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_depth": 2,
    "max_pages": 50
  }'
```

See [docs/USAGE.md](docs/USAGE.md) for comprehensive usage examples.

## 📚 API Documentation

### Interactive Documentation

Once the application is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

#### Search Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search/google` | POST | Google search |
| `/api/v1/search/duckduckgo` | POST | DuckDuckGo search |
| `/api/v1/search/combined` | POST | Both engines simultaneously |
| `/api/v1/search/google/batch` | POST | Batch Google search |
| `/api/v1/search/duckduckgo/batch` | POST | Batch DuckDuckGo search |

#### Website Scraping Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/website/scrape` | POST | Scrape single website |
| `/api/v1/website/scrape/batch` | POST | Scrape multiple websites |
| `/api/v1/website/scrape/deep` | POST | Deep scrape (follow links) |
| `/api/v1/website/extract/contacts` | GET | Extract contacts only |
| `/api/v1/website/extract/content` | GET | Extract content only |
| `/api/v1/website/extract/metadata` | GET | Extract metadata only |

#### System Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/status` | GET | Detailed system status |

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Start services (API + Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Start with Nginx (production)
docker-compose --profile production up -d
```

### Using Docker

```bash
# Build image
docker build -t web-scraper .

# Run container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  --name scraper-api \
  web-scraper

# View logs
docker logs -f scraper-api

# Stop container
docker stop scraper-api
```

### Production Deployment

```bash
# With Nginx reverse proxy
docker-compose --profile production up -d

# Scale API instances
docker-compose up -d --scale api=3
```

## ⚡ Performance

### Benchmarks

- **Search Scraping**: 60+ requests/minute
- **Website Scraping**: 30+ requests/minute
- **Concurrent Requests**: 50+ simultaneous
- **Success Rate**: 95%+ (with proxies and fallbacks)

### Performance Tuning

```env
# High-performance configuration
MAX_CONCURRENT_REQUESTS=100
API_WORKERS=8
MAX_SEARCH_REQUESTS_PER_MINUTE=120
MAX_WEBSITE_REQUESTS_PER_MINUTE=60
```

### Resource Requirements

| Setup | CPU | RAM | Throughput |
|-------|-----|-----|------------|
| Minimal | 1-2 cores | 2GB | 20 req/min |
| Standard | 4 cores | 8GB | 60 req/min |
| High | 8+ cores | 16GB | 120+ req/min |

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Application                   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  Search Scrapers │        │ Website Scraper  │          │
│  │  - Google        │        │  - Generic       │          │
│  │  - DuckDuckGo    │        │  - Deep Scrape   │          │
│  └──────────────────┘        └──────────────────┘          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │ Content Parsers  │        │ Request Handler  │          │
│  │  - HTML Parser   │        │  - aiohttp       │          │
│  │  - Contact Extr. │        │  - Playwright    │          │
│  │  - Metadata Extr.│        │  - Selenium      │          │
│  └──────────────────┘        └──────────────────┘          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Proxy Manager   │  │Rate Limiter  │  │Captcha Solver│ │
│  │  - Rotation      │  │- Token Bucket│  │- Audio/Image │ │
│  │  - Health Check  │  │- Redis/Memory│  │- Automation  │ │
│  └──────────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────┐
                    │      Redis       │
                    │ (Rate Limiting)  │
                    └──────────────────┘
```

### Request Flow

```
1. Client Request → FastAPI Endpoint
2. Rate Limiting Check (Redis/Memory)
3. Request Handler → Strategy Selection:
   ├─ Strategy 1: aiohttp + Proxy
   ├─ Strategy 2: aiohttp + Different Headers
   ├─ Strategy 3: Playwright (Browser)
   └─ Strategy 4: Selenium (Browser)
4. Content Parser → Extract & Categorize
5. Response → Client
```

### Technologies

- **Framework**: FastAPI (async)
- **HTTP Client**: aiohttp (async)
- **HTML Parsing**: BeautifulSoup4, lxml
- **Browser Automation**: Playwright, Selenium
- **Rate Limiting**: Redis, in-memory fallback
- **Proxy Support**: HTTP, HTTPS, SOCKS5
- **Captcha**: Tesseract OCR, browser automation
- **Contact Extraction**: phonenumbers, email-validator
- **Structured Data**: extruct

## 🔧 Advanced Features

### 1. Multiple Fallback Methods

Each request tries 2-3 different methods automatically:
- aiohttp with proxy rotation
- aiohttp with different headers/user agents
- Playwright browser automation
- Selenium browser automation

### 2. Proxy Management

- Automatic proxy rotation
- Health checking every 5 minutes
- Failure tracking and auto-disable
- Support for HTTP, HTTPS, SOCKS5

### 3. Rate Limiting

- Token bucket algorithm
- Per-endpoint limits
- Redis-backed (distributed)
- Automatic queueing

### 4. Content Extraction

- Intelligent paragraph detection
- Contact information extraction
- Structured data parsing (JSON-LD, Open Graph)
- Image and link extraction
- Table parsing

### 5. Error Handling

- Automatic retries with exponential backoff
- Multiple fallback strategies
- Detailed error logging
- Graceful degradation

## 📁 Project Structure

```
web-scraping-system/
├── app/
│   ├── api/                    # API endpoints
│   │   ├── search_scraper.py   # Search API
│   │   └── website_scraper.py  # Website API
│   ├── core/                   # Core utilities
│   │   ├── proxy_manager.py    # Proxy rotation
│   │   ├── request_handler.py  # HTTP requests
│   │   ├── rate_limiter.py     # Rate limiting
│   │   └── captcha_solver.py   # Captcha solving
│   ├── scrapers/               # Scraper implementations
│   │   ├── google_scraper.py   # Google scraper
│   │   ├── duckduckgo_scraper.py # DuckDuckGo scraper
│   │   └── generic_scraper.py  # Generic scraper
│   ├── parsers/                # Content parsers
│   │   ├── content_parser.py   # HTML parser
│   │   └── contact_extractor.py # Contact extractor
│   ├── config/                 # Configuration
│   │   └── settings.py         # Settings manager
│   ├── utils/                  # Utilities
│   │   ├── user_agents.py      # User agent rotation
│   │   └── helpers.py          # Helper functions
│   └── main.py                 # FastAPI application
├── config/                     # Configuration files
│   ├── config.yaml             # Main config
│   ├── proxies.txt             # HTTP proxies
│   └── socks_proxies.txt       # SOCKS5 proxies
├── docs/                       # Documentation
│   ├── SETUP.md                # Setup guide
│   ├── USAGE.md                # Usage guide
│   └── CONFIGURATION.md        # Config guide
├── logs/                       # Log files
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image
├── docker-compose.yml          # Docker Compose
├── .env.example                # Environment template
└── README.md                   # This file
```

## 🛡️ Security

### Best Practices

1. **Use environment variables** for sensitive data
2. **Enable authentication** for production (not included)
3. **Use HTTPS** with reverse proxy (Nginx)
4. **Restrict CORS origins** in production
5. **Keep proxies private** (don't commit to Git)
6. **Regular security updates** for dependencies

### Rate Limiting

Built-in rate limiting protects against abuse:
- 60 search requests/minute
- 30 website scrapes/minute
- Configurable per endpoint

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Legal Disclaimer

This tool is for educational and legitimate use only. Users are responsible for:

1. **Respecting robots.txt** and website terms of service
2. **Complying with applicable laws** in their jurisdiction
3. **Respecting rate limits** and not overloading servers
4. **Using appropriate authorization** when required
5. **Handling personal data** in compliance with privacy laws (GDPR, CCPA, etc.)

The authors assume no liability for misuse of this software.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Playwright and Selenium for browser automation
- BeautifulSoup4 for HTML parsing
- All open-source contributors

## 📞 Support

- **Documentation**: See `/docs` folder
- **API Docs**: http://localhost:8000/docs
- **Issues**: GitHub Issues (if applicable)
- **Logs**: Check `logs/scraper.log`

## 🗺️ Roadmap

- [ ] API authentication and authorization
- [ ] Webhook support for async scraping
- [ ] Database integration for result storage
- [ ] Advanced scheduling and cron jobs
- [ ] More search engines (Bing, Yahoo, etc.)
- [ ] PDF and document parsing
- [ ] Machine learning for content classification
- [ ] Distributed scraping cluster support

---

**Built with ❤️ using Python and FastAPI**
