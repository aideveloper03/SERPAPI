# Configuration Guide

## Environment Variables

All configuration is done through environment variables. Copy `.env.example` to `.env` and customize.

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `API_WORKERS` | `4` | Number of worker processes |
| `DEBUG` | `false` | Enable debug mode |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_SEARCH_REQUESTS_PER_MINUTE` | `100` | Search request limit |
| `MAX_WEBSITE_REQUESTS_PER_MINUTE` | `60` | Website scrape limit |
| `MAX_CONCURRENT_REQUESTS` | `100` | Concurrent connections |

### Redis (Caching)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_PASSWORD` | `` | Redis password (optional) |

### Proxy Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_PROXY` | `true` | Enable proxy rotation |
| `PROXY_ROTATION` | `true` | Rotate proxies on each request |
| `PROXY_TIMEOUT` | `15` | Proxy connection timeout |
| `AUTO_FETCH_PROXIES` | `true` | Auto-fetch from free sources |

### Request Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REQUEST_TIMEOUT` | `15` | Request timeout in seconds |
| `MAX_RETRIES` | `2` | Maximum retry attempts |
| `RETRY_DELAY` | `0.5` | Delay between retries |

### Search Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_SEARCH_ENGINE` | `google` | Default engine |
| `ENABLE_FALLBACK` | `true` | Fallback to other engines |
| `CACHE_RESULTS` | `true` | Cache search results |
| `CACHE_TTL` | `300` | Cache lifetime in seconds |

### Browser Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `JAVASCRIPT_RENDERING` | `true` | Enable browser rendering |
| `BROWSER_HEADLESS` | `true` | Run browser headless |
| `PAGE_LOAD_TIMEOUT` | `15` | Page load timeout |

### Captcha Solving

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_CAPTCHA_SOLVER` | `true` | Enable captcha solving |
| `CAPTCHA_TIMEOUT` | `120` | Captcha solve timeout |
| `TWOCAPTCHA_API_KEY` | `` | 2Captcha API key |
| `ANTICAPTCHA_API_KEY` | `` | Anti-Captcha API key |
| `CAPMONSTER_API_KEY` | `` | CapMonster API key |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level |
| `LOG_FILE` | `logs/scraper.log` | Log file path |

## Proxy Configuration

### Auto-fetched Proxies

By default, proxies are fetched from these free sources:

- ProxyScrape API
- TheSpeedX Proxy List
- Clarketm Proxy List
- Monosans Proxy List
- And more...

### Custom Proxies

Add custom proxies to `config/proxies.txt`:

```
# HTTP proxies
http://ip:port
http://username:password@ip:port

# SOCKS5 proxies
socks5://ip:port
socks5://username:password@ip:port
```

### Premium Proxy Services

For better performance, use premium proxy services:

1. **Bright Data** (formerly Luminati)
2. **Oxylabs**
3. **SmartProxy**
4. **IPRoyal**

## Captcha Service Setup

### 2Captcha

1. Sign up at https://2captcha.com/
2. Get your API key from dashboard
3. Add to `.env`: `TWOCAPTCHA_API_KEY=your_key`

### Anti-Captcha

1. Sign up at https://anti-captcha.com/
2. Get your API key
3. Add to `.env`: `ANTICAPTCHA_API_KEY=your_key`

### CapMonster

1. Sign up at https://capmonster.cloud/
2. Get your API key
3. Add to `.env`: `CAPMONSTER_API_KEY=your_key`

## Performance Tuning

### For High Throughput (50+ req/min)

```env
MAX_SEARCH_REQUESTS_PER_MINUTE=100
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=10
CACHE_RESULTS=true
USE_PROXY=true
```

### For Low Latency

```env
REQUEST_TIMEOUT=5
MAX_RETRIES=1
CACHE_RESULTS=true
CACHE_TTL=600
```

### For Maximum Reliability

```env
ENABLE_FALLBACK=true
MAX_RETRIES=3
USE_PROXY=true
JAVASCRIPT_RENDERING=true
```

## Docker Configuration

### docker-compose.yml Overrides

Create `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  api:
    environment:
      - MAX_SEARCH_REQUESTS_PER_MINUTE=200
      - USE_PROXY=false
```

### Scaling

```bash
# Scale to 3 API workers
docker-compose up -d --scale api=3
```
