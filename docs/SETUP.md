# Setup Guide

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.11+ with pip

## Quick Setup with Docker

### 1. Clone the Repository

```bash
git clone <repository-url>
cd search-scraper
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env as needed
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Verify Installation

```bash
curl http://localhost:8000/health
```

## Manual Setup (Python)

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
playwright install-deps chromium
```

### 4. Install Tesseract OCR (for captcha solving)

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### 5. Configure Environment

```bash
cp .env.example .env
# Edit .env as needed
```

### 6. Run the Application

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Production Setup

### Using Docker Compose with Nginx

1. Configure SSL certificates in `ssl/` directory
2. Update `nginx.conf` with your domain
3. Start with production profile:

```bash
docker-compose --profile production up -d
```

### Systemd Service (Linux)

Create `/etc/systemd/system/search-scraper.service`:

```ini
[Unit]
Description=Search Scraper API
After=network.target

[Service]
Type=simple
User=scraper
WorkingDirectory=/opt/search-scraper
Environment=PATH=/opt/search-scraper/venv/bin
ExecStart=/opt/search-scraper/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable search-scraper
sudo systemctl start search-scraper
```

## Adding Custom Proxies

### Via Environment Variable

```bash
CUSTOM_PROXIES=http://proxy1:8080,socks5://proxy2:1080
```

### Via Configuration Files

Create `config/proxies.txt`:
```
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:3128
```

Create `config/socks_proxies.txt`:
```
socks5://proxy1.example.com:1080
socks5://user:pass@proxy2.example.com:1080
```

## Troubleshooting Setup

### Playwright Not Working

```bash
# Install dependencies
playwright install chromium
playwright install-deps chromium
```

### Brotli Encoding Error

```bash
pip install Brotli brotlicffi
```

### Permission Denied on Logs

```bash
mkdir -p logs
chmod 755 logs
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000
# Kill if needed
kill -9 <PID>
```

## Verification

After setup, verify all components:

```bash
# Health check
curl http://localhost:8000/health

# Expected response
{
    "status": "healthy",
    "version": "2.0.0",
    "components": {
        "proxy_manager": "operational",
        "request_handler": "operational",
        "rate_limiters": "operational",
        "captcha_solver": "operational"
    },
    "search_engines": {
        "google": "available",
        "duckduckgo": "available",
        "bing": "available",
        "yahoo": "available"
    }
}
```

## Next Steps

1. Read [USAGE.md](USAGE.md) for API documentation
2. Read [CONFIGURATION.md](CONFIGURATION.md) for configuration options
3. Test with a simple search request
4. Monitor via `/proxy-stats` endpoint
