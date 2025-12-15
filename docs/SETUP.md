# Setup Guide

Complete setup instructions for the High-Volume Web Scraping System.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Dependencies](#dependencies)
5. [Optional Components](#optional-components)
6. [Running the Application](#running-the-application)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.9+**
- **pip** (Python package manager)
- **Git**

### Optional (for enhanced features)

- **Redis** (for distributed rate limiting and caching)
- **Tesseract OCR** (for captcha solving)
- **Chrome/Chromium** (for Selenium/Playwright browser automation)

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers (Optional but Recommended)

For JavaScript-heavy websites that require browser rendering:

```bash
playwright install chromium
```

### 5. Install Tesseract OCR (Optional)

For captcha solving capabilities:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### 6. Install Redis (Optional but Recommended)

For distributed rate limiting and better performance:

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Docker:**
```bash
docker run -d -p 6379:6379 redis:alpine
```

---

## Configuration

### 1. Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
DEBUG=False

# Rate Limiting
MAX_SEARCH_REQUESTS_PER_MINUTE=60
MAX_WEBSITE_REQUESTS_PER_MINUTE=30
MAX_CONCURRENT_REQUESTS=50

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Proxy Configuration
USE_PROXY=True
PROXY_ROTATION=True
PROXY_TIMEOUT=30

# Captcha Solving
ENABLE_CAPTCHA_SOLVER=True
CAPTCHA_TIMEOUT=60

# Request Configuration
REQUEST_TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=2

# Scraping Configuration
JAVASCRIPT_RENDERING=True
BROWSER_HEADLESS=True
PAGE_LOAD_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/scraper.log
```

### 2. Configuration File

Edit `config/config.yaml` for advanced settings:

```yaml
scraping:
  max_concurrent_requests: 50
  max_search_per_minute: 60
  max_website_per_minute: 30
  timeout: 30
  max_retries: 3

proxy:
  enabled: true
  rotation: true
  timeout: 30

# ... see config/config.yaml for full options
```

### 3. Proxy Configuration

Add your proxies to the proxy files:

**HTTP/HTTPS Proxies** (`config/proxies.txt`):
```
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:3128
https://proxy3.example.com:8080
```

**SOCKS5 Proxies** (`config/socks_proxies.txt`):
```
socks5://proxy1.example.com:1080
socks5://user:pass@proxy2.example.com:1080
```

---

## Dependencies

### Core Dependencies

- **FastAPI**: Web framework
- **aiohttp**: Async HTTP client
- **BeautifulSoup4**: HTML parsing
- **lxml**: XML/HTML parser
- **Playwright**: Browser automation
- **Redis**: Caching and rate limiting

### Full List

See `requirements.txt` for complete dependency list.

---

## Optional Components

### 1. Browser Automation (Playwright)

For JavaScript-heavy sites:

```bash
# Install Playwright
pip install playwright

# Install browsers
playwright install chromium
```

### 2. Selenium (Alternative Browser Automation)

```bash
pip install selenium

# Download ChromeDriver
# Place in PATH or specify location
```

### 3. Redis (Recommended for Production)

Install and run Redis server for:
- Distributed rate limiting
- Request caching
- Better scalability

### 4. Tesseract OCR (For Captcha Solving)

Install Tesseract for image captcha solving capabilities.

---

## Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or using the main script
python app/main.py
```

### Using Docker

```bash
# Build image
docker build -t web-scraper .

# Run container
docker run -d -p 8000:8000 --env-file .env web-scraper
```

### Using Docker Compose

```bash
# Start all services (API + Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Verification

### 1. Check API Status

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "proxy_manager": "operational",
    "request_handler": "operational",
    "rate_limiters": "operational"
  }
}
```

### 2. Access API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Test Search Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/search/google \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "num_results": 5}'
```

### 4. Test Website Scraper

```bash
curl -X POST http://localhost:8000/api/v1/website/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

---

## Troubleshooting

### Issue: Import Errors

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Redis Connection Error

**Solution:**
- Check Redis is running: `redis-cli ping`
- Verify Redis host/port in `.env`
- System will fallback to in-memory rate limiting

### Issue: Playwright Browser Not Found

**Solution:**
```bash
playwright install chromium
```

### Issue: Proxy Not Working

**Solution:**
- Verify proxy format in `config/proxies.txt`
- Test proxy manually
- Check proxy credentials
- Set `USE_PROXY=False` to disable

### Issue: Rate Limiting Too Aggressive

**Solution:**
Edit `.env`:
```env
MAX_SEARCH_REQUESTS_PER_MINUTE=120
MAX_WEBSITE_REQUESTS_PER_MINUTE=60
```

### Issue: Captcha Detection

**Solution:**
- Install Tesseract OCR
- Use browser rendering: `"use_browser": true`
- Add delays between requests
- Use residential proxies

### Logs

Check logs for detailed error information:
```bash
tail -f logs/scraper.log
```

---

## Performance Tuning

### 1. Increase Concurrency

Edit `.env`:
```env
MAX_CONCURRENT_REQUESTS=100
API_WORKERS=8
```

### 2. Add More Proxies

Add proxies to `config/proxies.txt` for better rotation.

### 3. Use Redis

Install and configure Redis for better performance.

### 4. Optimize Rate Limits

Adjust rate limits based on your needs and proxy quality.

---

## Security Considerations

1. **Keep proxies private** - Don't commit proxy files to Git
2. **Use environment variables** - Never hardcode credentials
3. **Enable authentication** - Add API authentication in production
4. **Rate limiting** - Respect target websites' rate limits
5. **Legal compliance** - Ensure scraping is legal for your use case

---

## Next Steps

- Read [USAGE.md](USAGE.md) for API usage examples
- Read [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration options
- Check API documentation at `/docs` endpoint
- Set up monitoring and alerting for production

---

## Support

For issues or questions:
1. Check logs: `logs/scraper.log`
2. Review error messages
3. Verify configuration
4. Test with minimal settings

---

## Quick Start Checklist

- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured
- [ ] Proxies added (optional)
- [ ] Redis installed and running (optional)
- [ ] Playwright browsers installed (optional)
- [ ] Application runs without errors
- [ ] Health check passes
- [ ] API documentation accessible
- [ ] Test requests successful
