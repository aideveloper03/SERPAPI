# Configuration Guide

Detailed configuration reference for the Web Scraping System.

## Table of Contents

1. [Configuration Files](#configuration-files)
2. [Environment Variables](#environment-variables)
3. [YAML Configuration](#yaml-configuration)
4. [Proxy Configuration](#proxy-configuration)
5. [Rate Limiting](#rate-limiting)
6. [Performance Tuning](#performance-tuning)
7. [Security Settings](#security-settings)
8. [Logging Configuration](#logging-configuration)

---

## Configuration Files

The system uses multiple configuration files:

1. **`.env`** - Environment variables (API, database, secrets)
2. **`config/config.yaml`** - Main configuration file
3. **`config/proxies.txt`** - HTTP/HTTPS proxy list
4. **`config/socks_proxies.txt`** - SOCKS5 proxy list

---

## Environment Variables

### API Configuration

```env
# Server settings
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
DEBUG=False
```

**Parameters:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| API_HOST | string | 0.0.0.0 | Host to bind API server |
| API_PORT | integer | 8000 | Port for API server |
| API_WORKERS | integer | 4 | Number of worker processes |
| DEBUG | boolean | False | Enable debug mode |

**Debug Mode:**
- Enables auto-reload
- Shows detailed error messages
- Uses single worker
- More verbose logging

### Rate Limiting

```env
# Rate limits (requests per minute)
MAX_SEARCH_REQUESTS_PER_MINUTE=60
MAX_WEBSITE_REQUESTS_PER_MINUTE=30
MAX_CONCURRENT_REQUESTS=50
```

**Parameters:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| MAX_SEARCH_REQUESTS_PER_MINUTE | integer | 60 | Search API rate limit |
| MAX_WEBSITE_REQUESTS_PER_MINUTE | integer | 30 | Website API rate limit |
| MAX_CONCURRENT_REQUESTS | integer | 50 | Max simultaneous requests |

**Recommendations:**

- **Low traffic**: 30 search, 15 website, 25 concurrent
- **Medium traffic**: 60 search, 30 website, 50 concurrent (default)
- **High traffic**: 120 search, 60 website, 100 concurrent
- **Very high traffic**: 200+ search, 100+ website, 150+ concurrent

### Redis Configuration

```env
# Redis for rate limiting and caching
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

**Parameters:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| REDIS_HOST | string | localhost | Redis server host |
| REDIS_PORT | integer | 6379 | Redis server port |
| REDIS_DB | integer | 0 | Redis database number |
| REDIS_PASSWORD | string | - | Redis password (if required) |

**Note:** Redis is optional. System falls back to in-memory rate limiting if Redis unavailable.

### Proxy Configuration

```env
# Proxy settings
USE_PROXY=True
PROXY_ROTATION=True
PROXY_TIMEOUT=30
```

**Parameters:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| USE_PROXY | boolean | True | Enable proxy usage |
| PROXY_ROTATION | boolean | True | Rotate proxies (vs random) |
| PROXY_TIMEOUT | integer | 30 | Proxy connection timeout (seconds) |

**Proxy Rotation:**
- **True**: Round-robin rotation
- **False**: Random selection

### Captcha Configuration

```env
# Captcha solving
ENABLE_CAPTCHA_SOLVER=True
CAPTCHA_TIMEOUT=60
```

**Parameters:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| ENABLE_CAPTCHA_SOLVER | boolean | True | Enable captcha detection/solving |
| CAPTCHA_TIMEOUT | integer | 60 | Captcha solving timeout (seconds) |

### Request Configuration

```env
# Request settings
REQUEST_TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=2
```

**Parameters:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| REQUEST_TIMEOUT | integer | 30 | Request timeout (seconds) |
| MAX_RETRIES | integer | 3 | Maximum retry attempts |
| RETRY_DELAY | integer | 2 | Delay between retries (seconds) |

**Timeout Recommendations:**

- **Fast sites**: 15 seconds
- **Normal sites**: 30 seconds (default)
- **Slow sites**: 60 seconds
- **Very slow sites**: 120 seconds

### Browser Configuration

```env
# Browser automation
JAVASCRIPT_RENDERING=True
BROWSER_HEADLESS=True
PAGE_LOAD_TIMEOUT=30
```

**Parameters:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| JAVASCRIPT_RENDERING | boolean | True | Enable Playwright/Selenium |
| BROWSER_HEADLESS | boolean | True | Run browser in headless mode |
| PAGE_LOAD_TIMEOUT | integer | 30 | Page load timeout (seconds) |

**Headless Mode:**
- **True**: No GUI (faster, less resources)
- **False**: Show browser (for debugging)

### Logging Configuration

```env
# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/scraper.log
```

**Log Levels:**

- **DEBUG**: Detailed debugging information
- **INFO**: General information (default)
- **WARNING**: Warning messages only
- **ERROR**: Error messages only
- **CRITICAL**: Critical errors only

---

## YAML Configuration

### Main Configuration File

**File:** `config/config.yaml`

### Scraping Settings

```yaml
scraping:
  # Concurrency
  max_concurrent_requests: 50
  max_search_per_minute: 60
  max_website_per_minute: 30
  
  # Request settings
  timeout: 30
  max_retries: 3
  retry_delay: 2
  backoff_factor: 2
  
  # Browser settings
  browser:
    headless: true
    timeout: 30000
    wait_until: networkidle
    viewport:
      width: 1920
      height: 1080
```

**Browser Wait Options:**

- `load`: Wait for load event
- `domcontentloaded`: Wait for DOM
- `networkidle`: Wait for network idle (recommended)

### Proxy Settings

```yaml
proxy:
  enabled: true
  rotation: true
  timeout: 30
  max_failures: 3
  
  sources:
    - type: http
      list_file: config/proxies.txt
    - type: socks5
      list_file: config/socks_proxies.txt
```

**Max Failures:**

Number of failures before marking proxy as dead. Lower = stricter, Higher = more forgiving.

### Captcha Settings

```yaml
captcha:
  enabled: true
  timeout: 60
  max_retries: 3
  
  solvers:
    - type: audio
    - type: image_recognition
    - type: browser_automation
```

**Solver Order:**

Solvers are tried in order. First successful method is used.

### User Agent Settings

```yaml
user_agents:
  rotation: true
  types:
    - chrome
    - firefox
    - safari
    - edge
```

**Types:**

- **chrome**: Chrome user agents
- **firefox**: Firefox user agents
- **safari**: Safari user agents
- **edge**: Edge user agents
- **random**: Random from all types

### Header Settings

```yaml
headers:
  accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
  accept_language: "en-US,en;q=0.9"
  accept_encoding: "gzip, deflate, br"
  dnt: "1"
  upgrade_insecure_requests: "1"
  sec_fetch_dest: "document"
  sec_fetch_mode: "navigate"
  sec_fetch_site: "none"
```

These headers help avoid detection by mimicking real browsers.

### Search Engine Settings

```yaml
search_engines:
  google:
    base_url: "https://www.google.com/search"
    results_per_page: 10
    max_pages: 5
    delay_between_requests: 2
    
  duckduckgo:
    base_url: "https://html.duckduckgo.com/html/"
    results_per_page: 10
    max_pages: 5
    delay_between_requests: 1
```

**Delay Between Requests:**

Add delay to avoid rate limiting. Higher = safer, Lower = faster.

### Content Extraction Settings

```yaml
content_extraction:
  min_paragraph_length: 50
  extract_metadata: true
  extract_links: true
  extract_images: true
  extract_contacts: true
  
  phone_patterns:
    - international
    - us
    - uk
    
  email_validation: true
```

**Min Paragraph Length:**

Minimum characters to consider text as a paragraph. Filters out short snippets.

### Redis Settings

```yaml
redis:
  host: localhost
  port: 6379
  db: 0
  password: null
  key_prefix: "scraper:"
  ttl: 3600
```

**TTL (Time To Live):**

Cache expiration time in seconds. 3600 = 1 hour.

### Logging Settings

```yaml
logging:
  level: INFO
  format: "json"
  file: "logs/scraper.log"
  rotation: "500 MB"
  retention: "10 days"
```

**Log Rotation:**

- `"500 MB"`: Rotate when file reaches 500MB
- `"1 GB"`: Rotate at 1GB
- `"daily"`: Rotate daily

**Log Retention:**

- `"10 days"`: Keep logs for 10 days
- `"30 days"`: Keep for 30 days
- `"never"`: Keep forever

---

## Proxy Configuration

### Proxy File Format

#### HTTP/HTTPS Proxies

**File:** `config/proxies.txt`

```
http://proxy1.example.com:8080
http://proxy2.example.com:3128
http://user:pass@proxy3.example.com:8080
https://proxy4.example.com:8080
```

#### SOCKS5 Proxies

**File:** `config/socks_proxies.txt`

```
socks5://proxy1.example.com:1080
socks5://user:pass@proxy2.example.com:1080
```

### Proxy Formats

**Without Authentication:**
```
http://hostname:port
https://hostname:port
socks5://hostname:port
```

**With Authentication:**
```
http://username:password@hostname:port
https://username:password@hostname:port
socks5://username:password@hostname:port
```

### Proxy Sources

Popular proxy sources (not affiliated):

1. **Free Proxies** (unreliable):
   - Free Proxy Lists
   - Public proxy databases

2. **Premium Proxies** (recommended):
   - Residential proxies
   - Datacenter proxies
   - Rotating proxies

3. **Self-hosted**:
   - Your own proxy servers
   - VPN servers
   - Cloud proxies

### Proxy Health Checking

Proxies are automatically health-checked every 5 minutes:

- Working proxies are used
- Failed proxies are retried
- Dead proxies are removed after 3 failures

### Proxy Selection

**Round-robin (PROXY_ROTATION=True):**
```
Request 1 -> Proxy A
Request 2 -> Proxy B
Request 3 -> Proxy C
Request 4 -> Proxy A (cycle repeats)
```

**Random (PROXY_ROTATION=False):**
```
Request 1 -> Proxy B (random)
Request 2 -> Proxy A (random)
Request 3 -> Proxy B (random)
```

---

## Rate Limiting

### How It Works

Rate limiting uses **token bucket algorithm**:

1. Bucket has maximum capacity (requests per minute)
2. Tokens refill at constant rate
3. Each request consumes one token
4. Request waits if no tokens available

### Configuration

**Per-endpoint limits:**

```env
MAX_SEARCH_REQUESTS_PER_MINUTE=60
MAX_WEBSITE_REQUESTS_PER_MINUTE=30
```

**Global limit:**

```env
MAX_CONCURRENT_REQUESTS=50
```

### Calculating Limits

**Example 1: Search Scraping**

- Goal: 1000 searches per hour
- Calculation: 1000 / 60 = 16.67 per minute
- Setting: `MAX_SEARCH_REQUESTS_PER_MINUTE=20` (with buffer)

**Example 2: Website Scraping**

- Goal: 500 websites per hour
- Calculation: 500 / 60 = 8.33 per minute
- Setting: `MAX_WEBSITE_REQUESTS_PER_MINUTE=10` (with buffer)

### Redis vs In-Memory

**Redis (recommended for production):**
- Distributed rate limiting
- Survives restarts
- Works across multiple instances

**In-Memory (fallback):**
- Local to process
- Lost on restart
- Doesn't scale across instances

---

## Performance Tuning

### 1. Increase Concurrency

```env
MAX_CONCURRENT_REQUESTS=100
API_WORKERS=8
```

**CPU Recommendation:**
- 1-2 cores: 4 workers, 25 concurrent
- 4 cores: 8 workers, 50 concurrent
- 8+ cores: 16 workers, 100 concurrent

### 2. Optimize Timeouts

```env
REQUEST_TIMEOUT=20
PAGE_LOAD_TIMEOUT=20
```

Lower timeouts = faster failures = higher throughput.

### 3. Add More Proxies

More proxies = better rotation = less blocking.

### 4. Use Redis

Redis is significantly faster than in-memory for rate limiting.

### 5. Disable Unnecessary Features

```yaml
content_extraction:
  extract_links: false  # If not needed
  extract_images: false  # If not needed
```

### 6. Browser Rendering

Only use when absolutely necessary:

```env
JAVASCRIPT_RENDERING=False  # Disable globally
```

Then enable per-request:
```json
{"use_browser": true}  # Only when needed
```

### 7. Tune Worker Count

**Formula:**
```
Workers = (2 × CPU cores) + 1
```

**Examples:**
- 2 cores: 5 workers
- 4 cores: 9 workers
- 8 cores: 17 workers

---

## Security Settings

### 1. API Authentication

Add authentication middleware (not included by default):

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = "your-secret-key"
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
```

### 2. CORS Configuration

Edit `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Limit methods
    allow_headers=["*"],
)
```

### 3. Rate Limiting

Aggressive rate limiting for public APIs:

```env
MAX_SEARCH_REQUESTS_PER_MINUTE=30
MAX_WEBSITE_REQUESTS_PER_MINUTE=15
```

### 4. Firewall Rules

Restrict access to specific IPs:

```bash
# Allow specific IP
sudo ufw allow from 192.168.1.100 to any port 8000

# Block all others
sudo ufw deny 8000
```

### 5. HTTPS/TLS

Use reverse proxy (Nginx/Caddy) for HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

### 6. Environment Variables

Never commit sensitive data:

```bash
# Add to .gitignore
.env
config/proxies.txt
config/socks_proxies.txt
```

---

## Logging Configuration

### Log Levels

```env
LOG_LEVEL=INFO
```

**When to use:**

- **DEBUG**: Development and troubleshooting
- **INFO**: Production (default)
- **WARNING**: Only important issues
- **ERROR**: Critical errors only

### Log Format

**Human-readable (console):**
```
2024-01-15 10:30:45 | INFO | app.main:startup - Starting Web Scraping System...
```

**JSON (file):**
```json
{
  "timestamp": "2024-01-15T10:30:45",
  "level": "INFO",
  "module": "app.main",
  "function": "startup",
  "message": "Starting Web Scraping System..."
}
```

### Log Rotation

```yaml
logging:
  rotation: "500 MB"  # Rotate at 500MB
  retention: "10 days"  # Keep for 10 days
```

### Log Locations

- **Console**: stderr (real-time)
- **File**: `logs/scraper.log`
- **Rotated**: `logs/scraper.log.1`, `scraper.log.2`, etc.

### Viewing Logs

```bash
# Tail logs
tail -f logs/scraper.log

# Search logs
grep "ERROR" logs/scraper.log

# Count errors
grep -c "ERROR" logs/scraper.log

# View recent errors
grep "ERROR" logs/scraper.log | tail -n 20
```

---

## Configuration Examples

### Low-Resource Setup

Minimal resources (1-2 cores, 2GB RAM):

```env
API_WORKERS=2
MAX_CONCURRENT_REQUESTS=10
MAX_SEARCH_REQUESTS_PER_MINUTE=20
MAX_WEBSITE_REQUESTS_PER_MINUTE=10
REQUEST_TIMEOUT=20
USE_PROXY=False
JAVASCRIPT_RENDERING=False
```

### Standard Setup

Medium resources (4 cores, 8GB RAM):

```env
API_WORKERS=4
MAX_CONCURRENT_REQUESTS=50
MAX_SEARCH_REQUESTS_PER_MINUTE=60
MAX_WEBSITE_REQUESTS_PER_MINUTE=30
REQUEST_TIMEOUT=30
USE_PROXY=True
JAVASCRIPT_RENDERING=True
```

### High-Performance Setup

High resources (8+ cores, 16GB+ RAM):

```env
API_WORKERS=8
MAX_CONCURRENT_REQUESTS=100
MAX_SEARCH_REQUESTS_PER_MINUTE=120
MAX_WEBSITE_REQUESTS_PER_MINUTE=60
REQUEST_TIMEOUT=30
USE_PROXY=True
JAVASCRIPT_RENDERING=True
```

### Production Setup

Secure production configuration:

```env
DEBUG=False
LOG_LEVEL=WARNING
API_WORKERS=8
MAX_CONCURRENT_REQUESTS=100
USE_PROXY=True
ENABLE_CAPTCHA_SOLVER=True
REDIS_HOST=redis.internal
REDIS_PASSWORD=your-secure-password
```

---

## Troubleshooting Configuration

### Issue: Slow Performance

**Solution:**
1. Increase concurrency
2. Lower timeouts
3. Add more proxies
4. Disable browser rendering

### Issue: Too Many Errors

**Solution:**
1. Increase timeouts
2. Increase max retries
3. Check proxy quality
4. Enable browser rendering

### Issue: Rate Limiting

**Solution:**
1. Increase rate limits
2. Use Redis
3. Add more workers

### Issue: Memory Usage

**Solution:**
1. Decrease concurrency
2. Decrease workers
3. Disable browser rendering
4. Reduce log retention

---

## Best Practices

1. **Start conservative**: Begin with default settings
2. **Monitor metrics**: Watch CPU, memory, error rates
3. **Tune gradually**: Adjust one setting at a time
4. **Test changes**: Verify before deploying to production
5. **Use Redis**: Essential for production
6. **Quality proxies**: Better than quantity
7. **Log appropriately**: INFO for production, DEBUG for development
8. **Secure secrets**: Use environment variables
9. **Regular backups**: Back up configuration files
10. **Document changes**: Comment custom configurations

---

## Configuration Validation

### Validate Configuration

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Check environment variables
python -c "from app.config import settings; print(settings.dict())"

# Test Redis connection
redis-cli ping

# Test proxy
curl -x http://proxy:port http://httpbin.org/ip
```

### Configuration Checklist

- [ ] `.env` file created and configured
- [ ] `config/config.yaml` reviewed
- [ ] Proxies added (if using)
- [ ] Redis configured (if using)
- [ ] Log directory writable
- [ ] Timeouts appropriate for use case
- [ ] Rate limits set
- [ ] Worker count optimized for CPU
- [ ] Security settings reviewed
- [ ] CORS configured
- [ ] Logging level appropriate

---

For additional help, see:
- Setup guide: [SETUP.md](SETUP.md)
- Usage guide: [USAGE.md](USAGE.md)
