"""
Advanced User Agent Rotation with 2024 Browser Fingerprints
Provides realistic user agents for anti-detection
"""
import random
from typing import List, Optional


class UserAgentRotator:
    """
    Advanced user agent rotation with:
    - 2024 browser versions
    - OS variety (Windows, macOS, Linux)
    - Browser variety (Chrome, Firefox, Safari, Edge)
    - Mobile user agents
    """
    
    def __init__(self):
        # Latest 2024 Chrome user agents
        self.chrome_windows = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ]
        
        self.chrome_mac = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ]
        
        self.chrome_linux = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ]
        
        # Firefox user agents
        self.firefox_windows = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        ]
        
        self.firefox_mac = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
        ]
        
        self.firefox_linux = [
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        ]
        
        # Safari user agents
        self.safari = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
        
        # Edge user agents
        self.edge = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        ]
        
        # Mobile user agents
        self.mobile = [
            # iPhone
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
            # Android
            "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        ]
        
        # Combined list of all desktop user agents (weighted towards Chrome)
        self.all_desktop = (
            self.chrome_windows * 4 +  # Chrome Windows most common
            self.chrome_mac * 2 +
            self.chrome_linux +
            self.firefox_windows +
            self.firefox_mac +
            self.firefox_linux +
            self.safari +
            self.edge
        )
        
        # All user agents including mobile
        self.all_agents = self.all_desktop + self.mobile
    
    def get_random(self) -> str:
        """Get a random desktop user agent (most common scenario)"""
        return random.choice(self.all_desktop)
    
    def get_random_any(self) -> str:
        """Get a random user agent including mobile"""
        return random.choice(self.all_agents)
    
    def get_chrome(self) -> str:
        """Get a Chrome user agent"""
        return random.choice(self.chrome_windows + self.chrome_mac + self.chrome_linux)
    
    def get_firefox(self) -> str:
        """Get a Firefox user agent"""
        return random.choice(self.firefox_windows + self.firefox_mac + self.firefox_linux)
    
    def get_safari(self) -> str:
        """Get a Safari user agent"""
        return random.choice(self.safari)
    
    def get_edge(self) -> str:
        """Get an Edge user agent"""
        return random.choice(self.edge)
    
    def get_mobile(self) -> str:
        """Get a mobile user agent"""
        return random.choice(self.mobile)
    
    def get_by_type(self, browser_type: str = "chrome") -> str:
        """Get user agent by browser type"""
        type_map = {
            "chrome": self.get_chrome,
            "firefox": self.get_firefox,
            "safari": self.get_safari,
            "edge": self.get_edge,
            "mobile": self.get_mobile,
            "random": self.get_random
        }
        
        getter = type_map.get(browser_type.lower(), self.get_random)
        return getter()
    
    def get_with_platform(self, platform: str = "windows") -> str:
        """Get user agent for specific platform"""
        platform_map = {
            "windows": self.chrome_windows + self.firefox_windows + self.edge,
            "mac": self.chrome_mac + self.firefox_mac + self.safari,
            "macos": self.chrome_mac + self.firefox_mac + self.safari,
            "linux": self.chrome_linux + self.firefox_linux,
            "mobile": self.mobile,
            "ios": [ua for ua in self.mobile if "iPhone" in ua],
            "android": [ua for ua in self.mobile if "Android" in ua],
        }
        
        agents = platform_map.get(platform.lower(), self.all_desktop)
        return random.choice(agents)


# Singleton instance
_rotator_instance = None

def get_user_agent_rotator() -> UserAgentRotator:
    """Get singleton instance of UserAgentRotator"""
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = UserAgentRotator()
    return _rotator_instance
