# Configuration Guide

## Environment Variables

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Host address to bind the API |
| `API_PORT` | `8000` | Port number for the API |
| `API_WORKERS` | `4` | Number of uvicorn worker processes |
| `DEBUG` | `False` | Enable debug mode with auto-reload |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_SEARCH_REQUESTS_PER_MINUTE` | `120` | Maximum search requests per minute |
| `MAX_WEBSITE_REQUESTS_PER_MINUTE` | `60` | Maximum website scrape requests per minute |
| `MAX_CONCURRENT_REQUESTS` | `100` | Maximum concurrent connections |
| `CONNECTION_POOL_SIZE` | `100` | Size of the connection pool |

### Redis Configuration (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_REDIS` | `false` | Enable Redis for rate limiting |
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_PASSWORD` | `` | Redis password (if required) |

### Proxy Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_PROXY` | `true` | Enable proxy rotation |
| `PROXY_ROTATION` | `true` | Enable round-robin proxy rotation |
| `PROXY_TIMEOUT` | `10` | Timeout for proxy connections (seconds) |
| `AUTO_FETCH_PROXIES` | `true` | Automatically fetch free proxies |
| `PROXY_FETCH_INTERVAL` | `300` | Interval between proxy fetches (seconds) |
| `MIN_WORKING_PROXIES` | `10` | Minimum working proxies to maintain |
| `CUSTOM_PROXIES` | `` | Comma-separated list of custom proxies |

### Captcha Solving

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_CAPTCHA_SOLVER` | `true` | Enable automatic captcha solving |
| `CAPTCHA_TIMEOUT` | `30` | Timeout for captcha solving (seconds) |
| `CAPTCHA_MAX_RETRIES` | `3` | Maximum captcha solving attempts |

### Request Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REQUEST_TIMEOUT` | `15` | Timeout for HTTP requests (seconds) |
| `MAX_RETRIES` | `2` | Maximum retry attempts per request |
| `RETRY_DELAY` | `0.5` | Delay between retries (seconds) |

### Browser Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JAVASCRIPT_RENDERING` | `true` | Enable browser-based rendering |
| `BROWSER_HEADLESS` | `true` | Run browser in headless mode |
| `PAGE_LOAD_TIMEOUT` | `15` | Page load timeout (seconds) |

### Search Engine Fallback

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_FALLBACK` | `true` | Enable automatic fallback |
| `FALLBACK_ORDER` | `google,duckduckgo,bing,yahoo` | Order of engines to try |

### Anti-Detection

| Variable | Default | Description |
|----------|---------|-------------|
| `RANDOMIZE_FINGERPRINT` | `true` | Randomize browser fingerprints |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `logs/scraper.log` | Log file path |

## Configuration Files

### config/proxies.txt

Add HTTP/HTTPS proxies, one per line:

```
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:3128
https://proxy3.example.com:8080
```

### config/socks_proxies.txt

Add SOCKS proxies, one per line:

```
socks4://proxy1.example.com:1080
socks5://proxy2.example.com:1080
socks5://user:pass@proxy3.example.com:1080
```

### config/config.yaml

Additional YAML configuration (optional):

```yaml
search:
  default_engine: google
  results_per_page: 10
  max_pages: 5

proxy:
  check_interval: 300
  max_failures: 3

scraping:
  user_agent_rotation: true
  fingerprint_rotation: true
```

## Docker Configuration

### docker-compose.yml

The default `docker-compose.yml` includes:

- **api**: Main scraping API service
- **redis**: Rate limiting cache (optional)
- **nginx**: Reverse proxy for production (optional)

### Profiles

- Default: Runs api + redis
- `dev`: Development mode with hot-reload
- `production`: Includes nginx reverse proxy

```bash
# Development mode
docker-compose --profile dev up

# Production mode
docker-compose --profile production up
```

## Best Practices

1. **Rate Limiting**: Keep rate limits reasonable to avoid blocks
2. **Proxy Quality**: Use high-quality proxies for better results
3. **Monitoring**: Check `/proxy-stats` endpoint regularly
4. **Fallback**: Enable fallback for higher success rates
5. **Logging**: Use DEBUG level when troubleshooting
