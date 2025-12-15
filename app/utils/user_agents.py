"""
User Agent rotation for avoiding detection
"""
import random
from typing import List, Optional
from fake_useragent import UserAgent


class UserAgentRotator:
    """Manages user agent rotation"""
    
    def __init__(self):
        self.ua = UserAgent()
        
        # Predefined user agents for reliability
        self.user_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]
    
    def get_random(self) -> str:
        """Get a random user agent"""
        return random.choice(self.user_agents)
    
    def get_chrome(self) -> str:
        """Get a Chrome user agent"""
        try:
            return self.ua.chrome
        except:
            return self.user_agents[0]
    
    def get_firefox(self) -> str:
        """Get a Firefox user agent"""
        try:
            return self.ua.firefox
        except:
            return self.user_agents[2]
    
    def get_safari(self) -> str:
        """Get a Safari user agent"""
        try:
            return self.ua.safari
        except:
            return self.user_agents[6]
    
    def get_by_type(self, browser_type: str = "chrome") -> str:
        """Get user agent by browser type"""
        type_map = {
            "chrome": self.get_chrome,
            "firefox": self.get_firefox,
            "safari": self.get_safari,
            "random": self.get_random
        }
        
        getter = type_map.get(browser_type.lower(), self.get_random)
        return getter()
