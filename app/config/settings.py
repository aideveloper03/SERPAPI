"""
Configuration management using Pydantic settings
High-performance settings for production scraping
"""
import os
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings optimized for high-volume scraping"""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=4)
    debug: bool = Field(default=False)
    
    # Rate Limiting (optimized for 50+ requests/minute)
    max_search_requests_per_minute: int = Field(default=100)
    max_website_requests_per_minute: int = Field(default=60)
    max_concurrent_requests: int = Field(default=100)
    
    # Redis Configuration
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    
    # Proxy Configuration
    use_proxy: bool = Field(default=True)
    proxy_rotation: bool = Field(default=True)
    proxy_timeout: int = Field(default=15)
    auto_fetch_proxies: bool = Field(default=True)
    
    # Captcha Solving (optional API keys)
    enable_captcha_solver: bool = Field(default=True)
    captcha_timeout: int = Field(default=120)
    twocaptcha_api_key: Optional[str] = Field(default=None)
    anticaptcha_api_key: Optional[str] = Field(default=None)
    capmonster_api_key: Optional[str] = Field(default=None)
    
    # Request Configuration (optimized for speed)
    request_timeout: int = Field(default=15)
    max_retries: int = Field(default=2)
    retry_delay: float = Field(default=0.5)
    
    # Scraping Configuration
    javascript_rendering: bool = Field(default=True)
    browser_headless: bool = Field(default=True)
    page_load_timeout: int = Field(default=15)
    
    # Search Configuration
    default_search_engine: str = Field(default="google")
    enable_fallback: bool = Field(default=True)
    cache_results: bool = Field(default=True)
    cache_ttl: int = Field(default=300)  # 5 minutes
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/scraper.log")
    
    # Paths (computed, not from env)
    base_dir: Path = Field(default=Path(__file__).resolve().parent.parent.parent)
    config_dir: Path = Field(default=None)
    logs_dir: Path = Field(default=None)
    
    @field_validator('retry_delay', mode='before')
    @classmethod
    def parse_retry_delay(cls, v):
        """Parse retry_delay as float from string or number"""
        if isinstance(v, str):
            return float(v)
        return v
    
    @field_validator('debug', 'use_proxy', 'proxy_rotation', 'auto_fetch_proxies', 
                     'enable_captcha_solver', 'javascript_rendering', 'browser_headless',
                     'enable_fallback', 'cache_results', mode='before')
    @classmethod
    def parse_bool(cls, v):
        """Parse boolean from various string formats"""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "env_prefix": "",
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set computed paths
        if self.config_dir is None:
            object.__setattr__(self, 'config_dir', self.base_dir / "config")
        if self.logs_dir is None:
            object.__setattr__(self, 'logs_dir', self.base_dir / "logs")
        
        # Ensure directories exist
        try:
            self.logs_dir.mkdir(exist_ok=True)
        except Exception:
            pass
        
        # Set captcha API keys as environment variables
        if self.twocaptcha_api_key:
            os.environ['TWOCAPTCHA_API_KEY'] = self.twocaptcha_api_key
        if self.anticaptcha_api_key:
            os.environ['ANTICAPTCHA_API_KEY'] = self.anticaptcha_api_key
        if self.capmonster_api_key:
            os.environ['CAPMONSTER_API_KEY'] = self.capmonster_api_key
        
    def load_yaml_config(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        config_file = self.config_dir / "config.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                return yaml.safe_load(f)
        return {}
    
    def load_proxies(self, filename: str = "proxies.txt") -> List[str]:
        """Load proxies from file"""
        proxy_file = self.config_dir / filename
        if not proxy_file.exists():
            return []
        
        proxies = []
        with open(proxy_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        return proxies
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()
