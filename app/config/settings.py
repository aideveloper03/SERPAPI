"""
Configuration management using Pydantic settings
Loads from environment variables and config files
"""
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Rate Limiting
    max_search_requests_per_minute: int = Field(default=60, env="MAX_SEARCH_REQUESTS_PER_MINUTE")
    max_website_requests_per_minute: int = Field(default=30, env="MAX_WEBSITE_REQUESTS_PER_MINUTE")
    max_concurrent_requests: int = Field(default=50, env="MAX_CONCURRENT_REQUESTS")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Proxy Configuration
    use_proxy: bool = Field(default=True, env="USE_PROXY")
    proxy_rotation: bool = Field(default=True, env="PROXY_ROTATION")
    proxy_timeout: int = Field(default=30, env="PROXY_TIMEOUT")
    
    # Captcha Solving
    enable_captcha_solver: bool = Field(default=True, env="ENABLE_CAPTCHA_SOLVER")
    captcha_timeout: int = Field(default=60, env="CAPTCHA_TIMEOUT")
    
    # Request Configuration
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay: int = Field(default=2, env="RETRY_DELAY")
    
    # Scraping Configuration
    javascript_rendering: bool = Field(default=True, env="JAVASCRIPT_RENDERING")
    browser_headless: bool = Field(default=True, env="BROWSER_HEADLESS")
    page_load_timeout: int = Field(default=30, env="PAGE_LOAD_TIMEOUT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/scraper.log", env="LOG_FILE")
    
    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    config_dir: Path = base_dir / "config"
    logs_dir: Path = base_dir / "logs"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.logs_dir.mkdir(exist_ok=True)
        
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
