"""
Captcha Solver using multiple detection and solving strategies
Implements audio captcha, image recognition, and automated solving
"""
import asyncio
import base64
import re
from typing import Optional, Dict, Any
from io import BytesIO
import cv2
import numpy as np
from PIL import Image
from loguru import logger

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class CaptchaSolver:
    """
    Multi-strategy captcha solver
    Attempts multiple methods in order of preference
    """
    
    def __init__(self):
        self.enabled = True
        self.timeout = 60
        self.max_retries = 3
        
    async def solve(self, captcha_type: str, captcha_data: Any, page: Any = None) -> Optional[str]:
        """
        Solve captcha based on type
        
        Args:
            captcha_type: Type of captcha (image, audio, recaptcha, hcaptcha)
            captcha_data: Captcha data (image bytes, audio url, etc.)
            page: Browser page object if available
            
        Returns:
            Solved captcha text or None if failed
        """
        if not self.enabled:
            return None
        
        try:
            if captcha_type == "image":
                return await self._solve_image_captcha(captcha_data)
            elif captcha_type == "audio":
                return await self._solve_audio_captcha(captcha_data)
            elif captcha_type == "recaptcha":
                return await self._solve_recaptcha(captcha_data, page)
            elif captcha_type == "hcaptcha":
                return await self._solve_hcaptcha(captcha_data, page)
            else:
                logger.warning(f"Unknown captcha type: {captcha_type}")
                return None
                
        except Exception as e:
            logger.error(f"Captcha solving error: {str(e)}")
            return None
    
    async def _solve_image_captcha(self, image_data: bytes) -> Optional[str]:
        """
        Solve image-based captcha using OCR
        """
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract not available for OCR")
            return None
        
        try:
            # Convert bytes to image
            image = Image.open(BytesIO(image_data))
            
            # Preprocess image
            image_array = np.array(image)
            
            # Convert to grayscale
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            # Apply thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)
            
            # OCR
            text = pytesseract.image_to_string(
                denoised,
                config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            )
            
            # Clean result
            result = re.sub(r'[^a-zA-Z0-9]', '', text.strip())
            
            if result:
                logger.info(f"Image captcha solved: {result}")
                return result
            
        except Exception as e:
            logger.error(f"Image captcha solving error: {str(e)}")
        
        return None
    
    async def _solve_audio_captcha(self, audio_url: str) -> Optional[str]:
        """
        Solve audio captcha using speech recognition
        This is a placeholder - would need speech recognition library
        """
        logger.info("Audio captcha solving not fully implemented")
        # Would implement with speech_recognition library or similar
        return None
    
    async def _solve_recaptcha(self, site_key: str, page: Any) -> Optional[str]:
        """
        Solve reCAPTCHA v2/v3
        Uses browser automation to click audio challenge and solve
        """
        if not page:
            logger.warning("Browser page required for reCAPTCHA solving")
            return None
        
        try:
            # Strategy 1: Try audio challenge
            logger.info("Attempting reCAPTCHA audio challenge")
            
            # Switch to audio challenge
            audio_button = await page.query_selector("#recaptcha-audio-button")
            if audio_button:
                await audio_button.click()
                await asyncio.sleep(2)
                
                # Get audio URL
                audio_source = await page.query_selector(".rc-audiochallenge-tdownload-link")
                if audio_source:
                    audio_url = await audio_source.get_attribute("href")
                    result = await self._solve_audio_captcha(audio_url)
                    
                    if result:
                        # Enter result
                        input_field = await page.query_selector("#audio-response")
                        if input_field:
                            await input_field.fill(result)
                            
                            # Submit
                            verify_button = await page.query_selector("#recaptcha-verify-button")
                            if verify_button:
                                await verify_button.click()
                                await asyncio.sleep(2)
                                return result
            
            # Strategy 2: Check for automatic bypass (v3)
            # reCAPTCHA v3 may pass automatically with good reputation
            
        except Exception as e:
            logger.error(f"reCAPTCHA solving error: {str(e)}")
        
        return None
    
    async def _solve_hcaptcha(self, site_key: str, page: Any) -> Optional[str]:
        """
        Solve hCaptcha
        Similar approach to reCAPTCHA
        """
        logger.info("hCaptcha solving not fully implemented")
        # Would implement similar to reCAPTCHA
        return None
    
    async def detect_captcha(self, html: str, page: Any = None) -> Optional[Dict[str, Any]]:
        """
        Detect if page contains captcha
        
        Returns:
            Dict with captcha info or None
        """
        captcha_info = None
        
        # Check for reCAPTCHA
        if "recaptcha" in html.lower() or "g-recaptcha" in html:
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            captcha_info = {
                "type": "recaptcha",
                "site_key": site_key_match.group(1) if site_key_match else None
            }
        
        # Check for hCaptcha
        elif "hcaptcha" in html.lower() or "h-captcha" in html:
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            captcha_info = {
                "type": "hcaptcha",
                "site_key": site_key_match.group(1) if site_key_match else None
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
    
    async def bypass_cloudflare(self, page: Any) -> bool:
        """
        Bypass Cloudflare challenge
        Waits for automatic challenge completion
        """
        try:
            # Wait for Cloudflare challenge
            logger.info("Waiting for Cloudflare challenge...")
            
            # Check for Cloudflare
            content = await page.content()
            if "cloudflare" in content.lower() or "cf-browser-verification" in content:
                # Wait for challenge to complete (up to 30 seconds)
                for _ in range(30):
                    await asyncio.sleep(1)
                    
                    # Check if challenge passed
                    current_content = await page.content()
                    if "cloudflare" not in current_content.lower():
                        logger.info("Cloudflare challenge passed")
                        return True
                
                logger.warning("Cloudflare challenge timeout")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Cloudflare bypass error: {str(e)}")
            return False


# Global captcha solver instance
captcha_solver = CaptchaSolver()
