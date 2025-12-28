"""
Advanced Captcha Solver with Multiple Service Integration
Supports: Image captchas, reCAPTCHA v2/v3, hCaptcha, Cloudflare, FunCaptcha
Integrates with: 2Captcha, Anti-Captcha, CapMonster, and local OCR
"""
import asyncio
import base64
import re
import os
from typing import Optional, Dict, Any
from io import BytesIO
from loguru import logger
import aiohttp

# Optional imports for local solving
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Captcha service integrations
try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False

try:
    from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless
    from anticaptchaofficial.hcaptchaproxyless import hCaptchaProxyless
    from anticaptchaofficial.imagecaptcha import imagecaptcha
    ANTICAPTCHA_AVAILABLE = True
except ImportError:
    ANTICAPTCHA_AVAILABLE = False


class CaptchaSolver:
    """
    Advanced captcha solver with multiple strategies:
    1. 2Captcha service integration
    2. Anti-Captcha service integration
    3. CapMonster Cloud API
    4. Local OCR with Tesseract
    5. Cloudflare bypass
    6. Browser-based solving
    """
    
    def __init__(self):
        self.enabled = True
        self.timeout = 120  # Maximum wait time for captcha solving
        self.max_retries = 3
        
        # API keys from environment
        self.twocaptcha_key = os.environ.get('TWOCAPTCHA_API_KEY', '')
        self.anticaptcha_key = os.environ.get('ANTICAPTCHA_API_KEY', '')
        self.capmonster_key = os.environ.get('CAPMONSTER_API_KEY', '')
        
        # Service priority (in order of preference)
        self.service_priority = ['2captcha', 'anticaptcha', 'capmonster', 'local']
        
        # Initialize services
        self._init_services()
    
    def _init_services(self):
        """Initialize captcha solving services"""
        self.twocaptcha_solver = None
        if TWOCAPTCHA_AVAILABLE and self.twocaptcha_key:
            try:
                self.twocaptcha_solver = TwoCaptcha(self.twocaptcha_key)
                logger.info("2Captcha service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize 2Captcha: {e}")
        
        self.anticaptcha_available = ANTICAPTCHA_AVAILABLE and bool(self.anticaptcha_key)
        if self.anticaptcha_available:
            logger.info("Anti-Captcha service available")
    
    async def solve(
        self,
        captcha_type: str,
        captcha_data: Any,
        page: Any = None,
        site_key: str = "",
        url: str = ""
    ) -> Optional[str]:
        """
        Solve captcha using available services
        
        Args:
            captcha_type: Type of captcha (image, recaptcha, hcaptcha, funcaptcha)
            captcha_data: Captcha data (image bytes, site key, etc.)
            page: Browser page object if available
            site_key: Site key for reCAPTCHA/hCaptcha
            url: Page URL for context
            
        Returns:
            Solved captcha token/text or None if failed
        """
        if not self.enabled:
            return None
        
        logger.info(f"Attempting to solve {captcha_type} captcha")
        
        for attempt in range(self.max_retries):
            try:
                if captcha_type == "image":
                    result = await self._solve_image(captcha_data)
                elif captcha_type == "recaptcha" or captcha_type == "recaptcha_v2":
                    result = await self._solve_recaptcha_v2(site_key, url)
                elif captcha_type == "recaptcha_v3":
                    result = await self._solve_recaptcha_v3(site_key, url)
                elif captcha_type == "hcaptcha":
                    result = await self._solve_hcaptcha(site_key, url)
                elif captcha_type == "funcaptcha":
                    result = await self._solve_funcaptcha(site_key, url)
                elif captcha_type == "cloudflare":
                    result = await self._bypass_cloudflare(page)
                else:
                    logger.warning(f"Unknown captcha type: {captcha_type}")
                    return None
                
                if result:
                    logger.info(f"Captcha solved successfully on attempt {attempt + 1}")
                    return result
                    
            except Exception as e:
                logger.warning(f"Captcha solving attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2)
        
        logger.error(f"Failed to solve {captcha_type} captcha after {self.max_retries} attempts")
        return None
    
    async def _solve_image(self, image_data: bytes) -> Optional[str]:
        """Solve image captcha using available services"""
        
        # Try 2Captcha first
        if self.twocaptcha_solver:
            try:
                result = await self._solve_image_2captcha(image_data)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"2Captcha image solving failed: {e}")
        
        # Try Anti-Captcha
        if self.anticaptcha_available:
            try:
                result = await self._solve_image_anticaptcha(image_data)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Anti-Captcha image solving failed: {e}")
        
        # Try CapMonster
        if self.capmonster_key:
            try:
                result = await self._solve_image_capmonster(image_data)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"CapMonster image solving failed: {e}")
        
        # Fallback to local OCR
        if TESSERACT_AVAILABLE and CV2_AVAILABLE and PIL_AVAILABLE:
            return await self._solve_image_local(image_data)
        
        return None
    
    async def _solve_image_2captcha(self, image_data: bytes) -> Optional[str]:
        """Solve image captcha with 2Captcha"""
        try:
            loop = asyncio.get_event_loop()
            
            def solve():
                return self.twocaptcha_solver.normal(
                    base64.b64encode(image_data).decode('utf-8')
                )
            
            result = await loop.run_in_executor(None, solve)
            return result.get('code') if result else None
            
        except Exception as e:
            logger.debug(f"2Captcha error: {e}")
            return None
    
    async def _solve_image_anticaptcha(self, image_data: bytes) -> Optional[str]:
        """Solve image captcha with Anti-Captcha"""
        try:
            loop = asyncio.get_event_loop()
            
            def solve():
                solver = imagecaptcha()
                solver.set_key(self.anticaptcha_key)
                return solver.solve_and_return_solution(
                    base64.b64encode(image_data).decode('utf-8')
                )
            
            result = await loop.run_in_executor(None, solve)
            return result if result != 0 else None
            
        except Exception as e:
            logger.debug(f"Anti-Captcha error: {e}")
            return None
    
    async def _solve_image_capmonster(self, image_data: bytes) -> Optional[str]:
        """Solve image captcha with CapMonster Cloud"""
        try:
            # Create task
            async with aiohttp.ClientSession() as session:
                create_task = {
                    "clientKey": self.capmonster_key,
                    "task": {
                        "type": "ImageToTextTask",
                        "body": base64.b64encode(image_data).decode('utf-8')
                    }
                }
                
                async with session.post(
                    "https://api.capmonster.cloud/createTask",
                    json=create_task
                ) as resp:
                    result = await resp.json()
                    task_id = result.get('taskId')
                
                if not task_id:
                    return None
                
                # Wait for result
                for _ in range(60):  # Wait up to 60 seconds
                    await asyncio.sleep(1)
                    
                    async with session.post(
                        "https://api.capmonster.cloud/getTaskResult",
                        json={"clientKey": self.capmonster_key, "taskId": task_id}
                    ) as resp:
                        result = await resp.json()
                        
                        if result.get('status') == 'ready':
                            return result.get('solution', {}).get('text')
                        elif result.get('status') == 'failed':
                            return None
                
        except Exception as e:
            logger.debug(f"CapMonster error: {e}")
        return None
    
    async def _solve_image_local(self, image_data: bytes) -> Optional[str]:
        """Solve image captcha using local OCR"""
        try:
            # Load image
            image = Image.open(BytesIO(image_data))
            image_array = np.array(image)
            
            # Convert to grayscale
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            # Apply image processing for better OCR
            # Thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoising
            denoised = cv2.fastNlMeansDenoising(thresh)
            
            # Scale up for better recognition
            scaled = cv2.resize(denoised, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            # OCR with multiple configurations
            configs = [
                '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                '--psm 8 --oem 3',
                '--psm 6 --oem 3',
            ]
            
            for config in configs:
                text = pytesseract.image_to_string(scaled, config=config)
                result = re.sub(r'[^a-zA-Z0-9]', '', text.strip())
                
                if result and len(result) >= 4:
                    logger.info(f"Local OCR solved: {result}")
                    return result
            
        except Exception as e:
            logger.debug(f"Local OCR error: {e}")
        
        return None
    
    async def _solve_recaptcha_v2(self, site_key: str, url: str) -> Optional[str]:
        """Solve reCAPTCHA v2"""
        
        # Try 2Captcha
        if self.twocaptcha_solver:
            try:
                loop = asyncio.get_event_loop()
                
                def solve():
                    return self.twocaptcha_solver.recaptcha(
                        sitekey=site_key,
                        url=url
                    )
                
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                return result.get('code') if result else None
                
            except Exception as e:
                logger.debug(f"2Captcha reCAPTCHA error: {e}")
        
        # Try Anti-Captcha
        if self.anticaptcha_available:
            try:
                loop = asyncio.get_event_loop()
                
                def solve():
                    solver = recaptchaV2Proxyless()
                    solver.set_key(self.anticaptcha_key)
                    solver.set_website_url(url)
                    solver.set_website_key(site_key)
                    return solver.solve_and_return_solution()
                
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                return result if result != 0 else None
                
            except Exception as e:
                logger.debug(f"Anti-Captcha reCAPTCHA error: {e}")
        
        # Try CapMonster
        if self.capmonster_key:
            return await self._solve_recaptcha_capmonster(site_key, url, "RecaptchaV2TaskProxyless")
        
        return None
    
    async def _solve_recaptcha_v3(self, site_key: str, url: str, action: str = "verify") -> Optional[str]:
        """Solve reCAPTCHA v3"""
        
        # Try 2Captcha
        if self.twocaptcha_solver:
            try:
                loop = asyncio.get_event_loop()
                
                def solve():
                    return self.twocaptcha_solver.recaptcha(
                        sitekey=site_key,
                        url=url,
                        version='v3',
                        action=action,
                        score=0.9
                    )
                
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                return result.get('code') if result else None
                
            except Exception as e:
                logger.debug(f"2Captcha reCAPTCHA v3 error: {e}")
        
        # Try CapMonster
        if self.capmonster_key:
            return await self._solve_recaptcha_capmonster(
                site_key, url, "RecaptchaV3TaskProxyless",
                min_score=0.9, page_action=action
            )
        
        return None
    
    async def _solve_recaptcha_capmonster(
        self,
        site_key: str,
        url: str,
        task_type: str,
        **kwargs
    ) -> Optional[str]:
        """Solve reCAPTCHA with CapMonster"""
        try:
            async with aiohttp.ClientSession() as session:
                task = {
                    "type": task_type,
                    "websiteURL": url,
                    "websiteKey": site_key,
                    **kwargs
                }
                
                create_task = {
                    "clientKey": self.capmonster_key,
                    "task": task
                }
                
                async with session.post(
                    "https://api.capmonster.cloud/createTask",
                    json=create_task
                ) as resp:
                    result = await resp.json()
                    task_id = result.get('taskId')
                
                if not task_id:
                    return None
                
                # Wait for result
                for _ in range(120):
                    await asyncio.sleep(2)
                    
                    async with session.post(
                        "https://api.capmonster.cloud/getTaskResult",
                        json={"clientKey": self.capmonster_key, "taskId": task_id}
                    ) as resp:
                        result = await resp.json()
                        
                        if result.get('status') == 'ready':
                            return result.get('solution', {}).get('gRecaptchaResponse')
                        elif result.get('status') == 'failed':
                            return None
                
        except Exception as e:
            logger.debug(f"CapMonster reCAPTCHA error: {e}")
        return None
    
    async def _solve_hcaptcha(self, site_key: str, url: str) -> Optional[str]:
        """Solve hCaptcha"""
        
        # Try 2Captcha
        if self.twocaptcha_solver:
            try:
                loop = asyncio.get_event_loop()
                
                def solve():
                    return self.twocaptcha_solver.hcaptcha(
                        sitekey=site_key,
                        url=url
                    )
                
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                return result.get('code') if result else None
                
            except Exception as e:
                logger.debug(f"2Captcha hCaptcha error: {e}")
        
        # Try Anti-Captcha
        if self.anticaptcha_available:
            try:
                loop = asyncio.get_event_loop()
                
                def solve():
                    solver = hCaptchaProxyless()
                    solver.set_key(self.anticaptcha_key)
                    solver.set_website_url(url)
                    solver.set_website_key(site_key)
                    return solver.solve_and_return_solution()
                
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                return result if result != 0 else None
                
            except Exception as e:
                logger.debug(f"Anti-Captcha hCaptcha error: {e}")
        
        return None
    
    async def _solve_funcaptcha(self, site_key: str, url: str) -> Optional[str]:
        """Solve FunCaptcha/Arkose Labs"""
        
        if self.twocaptcha_solver:
            try:
                loop = asyncio.get_event_loop()
                
                def solve():
                    return self.twocaptcha_solver.funcaptcha(
                        sitekey=site_key,
                        url=url
                    )
                
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                return result.get('code') if result else None
                
            except Exception as e:
                logger.debug(f"2Captcha FunCaptcha error: {e}")
        
        return None
    
    async def _bypass_cloudflare(self, page: Any) -> bool:
        """Bypass Cloudflare challenge page"""
        if not page:
            logger.warning("Browser page required for Cloudflare bypass")
            return False
        
        try:
            logger.info("Attempting Cloudflare bypass...")
            
            # Wait for challenge to load
            await asyncio.sleep(3)
            
            # Check for Cloudflare
            content = await page.content()
            
            if "checking your browser" in content.lower() or "cloudflare" in content.lower():
                # Wait for automatic challenge completion
                for _ in range(30):
                    await asyncio.sleep(2)
                    
                    try:
                        # Check for turnstile checkbox
                        turnstile = await page.query_selector('input[type="checkbox"]')
                        if turnstile:
                            await turnstile.click()
                            await asyncio.sleep(2)
                    except:
                        pass
                    
                    # Check if challenge passed
                    current_content = await page.content()
                    if "cloudflare" not in current_content.lower() and "checking" not in current_content.lower():
                        logger.info("Cloudflare challenge passed")
                        return True
                
                logger.warning("Cloudflare bypass timeout")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Cloudflare bypass error: {e}")
            return False
    
    async def detect_captcha(self, html: str, page: Any = None) -> Optional[Dict[str, Any]]:
        """
        Detect captcha type in page content
        
        Returns:
            Dict with captcha info or None
        """
        captcha_info = None
        
        # Check for reCAPTCHA v2/v3
        if "recaptcha" in html.lower() or "g-recaptcha" in html:
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            
            # Detect v3 by render parameter
            is_v3 = "render=" in html or "recaptcha/api.js?render=" in html
            
            captcha_info = {
                "type": "recaptcha_v3" if is_v3 else "recaptcha_v2",
                "site_key": site_key_match.group(1) if site_key_match else None
            }
        
        # Check for hCaptcha
        elif "hcaptcha" in html.lower() or "h-captcha" in html:
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            captcha_info = {
                "type": "hcaptcha",
                "site_key": site_key_match.group(1) if site_key_match else None
            }
        
        # Check for Cloudflare
        elif "cf-browser-verification" in html or "cloudflare" in html.lower():
            if "checking your browser" in html.lower() or "_cf_chl" in html:
                captcha_info = {
                    "type": "cloudflare",
                    "site_key": None
                }
        
        # Check for FunCaptcha
        elif "funcaptcha" in html.lower() or "arkoselabs" in html.lower():
            captcha_info = {
                "type": "funcaptcha",
                "site_key": None
            }
        
        # Check for simple image captcha
        elif re.search(r'captcha.*\.(jpg|png|gif)', html.lower()):
            captcha_info = {
                "type": "image",
                "site_key": None
            }
        
        if captcha_info:
            logger.info(f"Captcha detected: {captcha_info['type']}")
        
        return captcha_info
    
    def get_balance(self) -> Dict[str, float]:
        """Get balance from captcha services"""
        balances = {}
        
        if self.twocaptcha_solver:
            try:
                balance = self.twocaptcha_solver.balance()
                balances['2captcha'] = float(balance)
            except:
                pass
        
        return balances


# Global captcha solver instance
captcha_solver = CaptchaSolver()
