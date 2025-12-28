# Quick Start Guide

Get up and running with the Web Scraping System in 5 minutes.

## 🚀 Fastest Setup (Docker)

```bash
# 1. Clone and enter directory
git clone <repository-url>
cd web-scraping-system

# 2. Start with Docker Compose
docker-compose up -d

# 3. Check status
curl http://localhost:8000/health

# 4. Open documentation
# Visit: http://localhost:8000/docs
```

**Done!** The API is now running at `http://localhost:8000`

## 🐍 Python Setup (Alternative)

```bash
# 1. Clone repository
git clone <repository-url>
cd web-scraping-system

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env if needed (defaults work fine)

# 5. Run
python run.py

# Or use make
make dev
```

## 📝 First API Calls

### Search Google

```bash
curl -X POST http://localhost:8000/api/v1/search/google \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "num_results": 5}'
```

### Scrape a Website

```bash
curl -X POST http://localhost:8000/api/v1/website/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Extract Contacts

```bash
curl "http://localhost:8000/api/v1/website/extract/contacts?url=https://example.com"
```

## 🐍 Python Client

```python
import requests

# Search Google
response = requests.post(
    "http://localhost:8000/api/v1/search/google",
    json={"query": "python", "num_results": 10}
)
results = response.json()
print(f"Found {results['total_results']} results")

# Scrape website
response = requests.post(
    "http://localhost:8000/api/v1/website/scrape",
    json={"url": "https://example.com"}
)
data = response.json()
print(f"Title: {data['title']}")
print(f"Emails: {data['contacts']['emails']}")
```

Run the example client:

```bash
python examples/example_usage.py
```

## 📚 Interactive Documentation

Open your browser:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Try the API directly in your browser!

## ⚙️ Optional Configuration

### Add Proxies (Optional)

Edit `config/proxies.txt`:

```
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:3128
```

### Install Redis (Optional, Recommended)

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

Then update `.env`:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 🎯 Common Use Cases

### 1. Search Google News

```bash
curl -X POST http://localhost:8000/api/v1/search/google \
  -H "Content-Type: application/json" \
  -d '{
    "query": "technology news",
    "search_type": "news",
    "num_results": 20
  }'
```

### 2. Batch Scrape Multiple Sites

```bash
curl -X POST http://localhost:8000/api/v1/website/scrape/batch \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com",
      "https://example.org",
      "https://example.net"
    ]
  }'
```

### 3. Search Both Engines

```bash
curl -X POST http://localhost:8000/api/v1/search/combined \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "num_results": 10}'
```

### 4. Deep Scrape (Follow Links)

```bash
curl -X POST http://localhost:8000/api/v1/website/scrape/deep \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_depth": 2,
    "max_pages": 20
  }'
```

## 📊 Check System Status

```bash
# Health check
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/status

# Proxy statistics (if configured)
curl http://localhost:8000/status | python -m json.tool
```

## 🛠️ Useful Commands

```bash
# Run with auto-reload (development)
make dev

# Run in production
make run

# Check configuration
make check

# View logs
make logs

# Clean temporary files
make clean

# Docker commands
make docker-run
make docker-stop
make docker-logs
```

## 📈 Performance Tips

1. **Use batch endpoints** for multiple requests
2. **Add proxies** to avoid rate limiting
3. **Install Redis** for better performance
4. **Increase workers** in `.env` for more throughput
5. **Use specific extract endpoints** (contacts, content, metadata) when you don't need everything

## 🔧 Troubleshooting

### API Won't Start

```bash
# Check if port 8000 is in use
lsof -i :8000

# Try different port
python run.py --port 8001
```

### Redis Connection Error

Redis is optional. System will work without it using in-memory rate limiting.

```bash
# Check if Redis is running
redis-cli ping

# Start Redis (if installed)
redis-server
```

### Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Playwright Errors

```bash
# Install browsers
playwright install chromium
```

## 📖 Next Steps

- **Full Documentation**: See [README.md](README.md)
- **Setup Guide**: [docs/SETUP.md](docs/SETUP.md)
- **Usage Guide**: [docs/USAGE.md](docs/USAGE.md)
- **Configuration**: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- **Examples**: [examples/example_usage.py](examples/example_usage.py)

## 🎉 You're Ready!

The Web Scraping System is now running and ready to use.

Try the examples or start building your application!

---

**Need help?** Check the logs at `logs/scraper.log`
