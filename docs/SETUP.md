# Setup Guide

## Prerequisites

- Python 3.10+ or Docker
- Redis (optional, for caching)
- Chromium/Chrome (for browser automation)

## Installation Methods

### Method 1: Docker (Recommended for Production)

```bash
# Clone repository
git clone <repo-url>
cd search-scraper

# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f api
```

### Method 2: Local Python

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Optional: Install Tesseract for captcha OCR
# Ubuntu: sudo apt install tesseract-ocr
# macOS: brew install tesseract
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

# Copy environment file
cp .env.example .env

# Start Redis (optional)
docker run -d -p 6379:6379 redis:alpine

# Run the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: Development Setup

```bash
# Clone and setup
git clone <repo-url>
cd search-scraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Start with development profile
docker-compose --profile dev up api-dev

# Or run directly with hot reload
python -m uvicorn app.main:app --reload --log-level debug
```

## Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_PROXY` | true | Enable proxy rotation |
| `ENABLE_FALLBACK` | true | Fallback to other engines |
| `REQUEST_TIMEOUT` | 15 | Request timeout in seconds |
| `MAX_SEARCH_REQUESTS_PER_MINUTE` | 100 | Rate limit |

### Proxy Configuration

#### Auto-fetched Proxies (Default)

Proxies are automatically fetched from free sources. No configuration needed.

#### Custom Proxies

Add to `config/proxies.txt`:

```
# HTTP proxies
http://ip:port
http://user:pass@ip:port

# SOCKS5 proxies
socks5://ip:port
```

### Captcha Solving

For automatic captcha solving, add API keys:

```bash
# .env file
TWOCAPTCHA_API_KEY=your_key_here
ANTICAPTCHA_API_KEY=your_key_here
CAPMONSTER_API_KEY=your_key_here
```

## Verification

After setup, verify the system is working:

```bash
# Health check
curl http://localhost:8000/health

# Quick search test
curl -X POST http://localhost:8000/api/v1/search/fast \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'

# View documentation
open http://localhost:8000/docs
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000
# Kill it or use a different port
API_PORT=8001 python -m uvicorn app.main:app --port 8001
```

### Playwright Issues

```bash
# Reinstall browsers
playwright install chromium --with-deps

# For Docker, browsers are pre-installed
```

### Redis Connection Failed

The system works without Redis (uses in-memory caching):

```bash
# Disable Redis in .env
REDIS_HOST=
```

### SSL/Certificate Errors

```bash
# Usually fixed by updating certificates
pip install --upgrade certifi
```
