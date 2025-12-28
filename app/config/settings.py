"""
Configuration management using Pydantic settings
High-performance settings for production scraping
"""
import os
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import yaml
from pydantic import Field, field_validator, BeforeValidator
from pydantic_settings import BaseSettings
from typing_extensions import Annotated


def parse_float(v: Any) -> float:
    """Parse a value to float, handling strings from environment variables"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return 0.0
        try:
            return float(v)
        except ValueError:
            return 0.0
    return 0.0


def parse_int(v: Any) -> int:
    """Parse a value to int, handling strings and floats from environment variables"""
    if v is None:
        return 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return 0
        try:
            # Handle float strings like "0.5" by converting to float first
            return int(float(v))
        except ValueError:
            return 0
    return 0


def parse_bool(v: Any) -> bool:
    """Parse a value to bool, handling strings from environment variables"""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        v = v.strip().lower()
        if v in ('true', '1', 'yes', 'on', 'enabled'):
            return True
        if v in ('false', '0', 'no', 'off', 'disabled', ''):
            return False
        return False
    return False


# Annotated types for proper validation
FlexibleFloat = Annotated[float, BeforeValidator(parse_float)]
FlexibleInt = Annotated[int, BeforeValidator(parse_int)]
FlexibleBool = Annotated[bool, BeforeValidator(parse_bool)]


class Settings(BaseSettings):
    """Application settings optimized for high-volume scraping"""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: FlexibleInt = Field(default=8000)
    api_workers: FlexibleInt = Field(default=4)
    debug: FlexibleBool = Field(default=False)
    
    # Rate Limiting (optimized for 50+ requests/minute)
    max_search_requests_per_minute: FlexibleInt = Field(default=100)
    max_website_requests_per_minute: FlexibleInt = Field(default=60)
    max_concurrent_requests: FlexibleInt = Field(default=100)
    
    # Redis Configuration
    redis_host: str = Field(default="localhost")
    redis_port: FlexibleInt = Field(default=6379)
    redis_db: FlexibleInt = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    
    # Proxy Configuration
    use_proxy: FlexibleBool = Field(default=True)
    proxy_rotation: FlexibleBool = Field(default=True)
    proxy_timeout: FlexibleInt = Field(default=15)
    auto_fetch_proxies: FlexibleBool = Field(default=True)
    
    # Captcha Solving (optional API keys)
    enable_captcha_solver: FlexibleBool = Field(default=True)
    captcha_timeout: FlexibleInt = Field(default=120)
    twocaptcha_api_key: Optional[str] = Field(default=None)
    anticaptcha_api_key: Optional[str] = Field(default=None)
    capmonster_api_key: Optional[str] = Field(default=None)
    
    # Request Configuration (optimized for speed)
    request_timeout: FlexibleInt = Field(default=15)
    max_retries: FlexibleInt = Field(default=2)
    retry_delay: FlexibleFloat = Field(default=0.5)
    
    # Scraping Configuration
    javascript_rendering: FlexibleBool = Field(default=True)
    browser_headless: FlexibleBool = Field(default=True)
    page_load_timeout: FlexibleInt = Field(default=15)
    
    # Search Configuration
    default_search_engine: str = Field(default="google")
    enable_fallback: FlexibleBool = Field(default=True)
    cache_results: FlexibleBool = Field(default=True)
    cache_ttl: FlexibleInt = Field(default=300)  # 5 minutes
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/scraper.log")
    
    # Captcha avoidance settings
    captcha_avoidance_enabled: FlexibleBool = Field(default=True)
    use_stealth_mode: FlexibleBool = Field(default=True)
    randomize_request_timing: FlexibleBool = Field(default=True)
    min_request_delay: FlexibleFloat = Field(default=0.5)
    max_request_delay: FlexibleFloat = Field(default=2.0)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "env_prefix": "",
        "arbitrary_types_allowed": True,
    }
    
    @property
    def base_dir(self) -> Path:
        """Base directory of the project"""
        return Path(__file__).resolve().parent.parent.parent
    
    @property
    def config_dir(self) -> Path:
        """Configuration directory"""
        return self.base_dir / "config"
    
    @property
    def logs_dir(self) -> Path:
        """Logs directory"""
        logs_path = self.base_dir / "logs"
        logs_path.mkdir(exist_ok=True)
        return logs_path
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
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
