"""
Advanced User Agent rotation for avoiding detection
Includes latest browser versions and realistic configurations
"""
import random
from typing import List, Optional


class UserAgentRotator:
    """Manages user agent rotation with realistic browser signatures"""
    
    def __init__(self):
        # Latest Chrome versions (2024)
        self.chrome_windows = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ]
        
        self.chrome_mac = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ]
        
        self.chrome_linux = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        # Firefox versions
        self.firefox_windows = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        
        self.firefox_mac = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        ]
        
        self.firefox_linux = [
            "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
        ]
        
        # Safari versions
        self.safari = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        ]
        
        # Edge versions
        self.edge = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        ]
        
        # Mobile user agents
        self.mobile_android = [
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
        ]
        
        self.mobile_ios = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        ]
        
        # All desktop user agents
        self.desktop_user_agents = (
            self.chrome_windows + 
            self.chrome_mac + 
            self.chrome_linux +
            self.firefox_windows +
            self.firefox_mac +
            self.firefox_linux +
            self.safari +
            self.edge
        )
        
        # All mobile user agents
        self.mobile_user_agents = self.mobile_android + self.mobile_ios
        
        # All user agents
        self.all_user_agents = self.desktop_user_agents + self.mobile_user_agents
    
    def get_random(self) -> str:
        """Get a random desktop user agent"""
        return random.choice(self.desktop_user_agents)
    
    def get_random_mobile(self) -> str:
        """Get a random mobile user agent"""
        return random.choice(self.mobile_user_agents)
    
    def get_random_any(self) -> str:
        """Get any random user agent (desktop or mobile)"""
        return random.choice(self.all_user_agents)
    
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
    
    def get_by_type(self, browser_type: str = "chrome") -> str:
        """Get user agent by browser type"""
        type_map = {
            "chrome": self.get_chrome,
            "firefox": self.get_firefox,
            "safari": self.get_safari,
            "edge": self.get_edge,
            "mobile": self.get_random_mobile,
            "random": self.get_random,
        }
        
        getter = type_map.get(browser_type.lower(), self.get_random)
        return getter()
    
    def get_for_platform(self, platform: str = "windows") -> str:
        """Get user agent for specific platform"""
        platform_map = {
            "windows": self.chrome_windows + self.firefox_windows + self.edge,
            "mac": self.chrome_mac + self.firefox_mac + self.safari,
            "linux": self.chrome_linux + self.firefox_linux,
            "android": self.mobile_android,
            "ios": self.mobile_ios,
        }
        
        agents = platform_map.get(platform.lower(), self.desktop_user_agents)
        return random.choice(agents)
