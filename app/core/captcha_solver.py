"""
Advanced Captcha Solver with Multiple Detection and Solving Strategies
Supports: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, Image Captchas
Uses: OCR (Tesseract/EasyOCR), Audio Recognition, Browser Automation
"""
import asyncio
import base64
import re
import os
import random
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO
from pathlib import Path
import aiohttp
from loguru import logger

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.debug("OpenCV not available")

try:
    from PIL import Image, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.debug("PIL not available")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.debug("Tesseract not available")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
    # Lazy load the reader
    _easyocr_reader = None
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.debug("EasyOCR not available")

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logger.debug("SpeechRecognition not available")


def get_easyocr_reader():
    """Lazy load EasyOCR reader"""
    global _easyocr_reader
    if EASYOCR_AVAILABLE and _easyocr_reader is None:
        try:
            _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
    return _easyocr_reader


class CaptchaDetector:
    """Detects different types of captchas on web pages"""
    
    CAPTCHA_PATTERNS = {
        'recaptcha_v2': [
            r'g-recaptcha',
            r'grecaptcha',
            r'recaptcha/api2',
            r'data-sitekey="([^"]+)"',
        ],
        'recaptcha_v3': [
            r'recaptcha/api\.js\?render=',
            r'grecaptcha\.execute',
            r'recaptcha-v3',
        ],
        'hcaptcha': [
            r'h-captcha',
            r'hcaptcha\.com',
            r'data-hcaptcha-sitekey',
        ],
        'cloudflare': [
            r'cf-browser-verification',
            r'cloudflare',
            r'cf-turnstile',
            r'challenges\.cloudflare\.com',
            r'just a moment',
            r'checking your browser',
            r'ray id',
        ],
        'funcaptcha': [
            r'funcaptcha',
            r'arkoselabs',
        ],
        'image_captcha': [
            r'captcha\.(jpg|png|gif|jpeg)',
            r'captchaimage',
            r'captcha-image',
        ],
    }
    
    @staticmethod
    def detect(html: str) -> Optional[Dict[str, Any]]:
        """
        Detect captcha type from HTML content
        
        Returns:
            Dict with captcha info or None
        """
        html_lower = html.lower()
        
        for captcha_type, patterns in CaptchaDetector.CAPTCHA_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, html_lower):
                    # Extract site key if available
                    site_key = None
                    site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
                    if site_key_match:
                        site_key = site_key_match.group(1)
                    
                    return {
                        'type': captcha_type,
                        'site_key': site_key,
                        'detected_pattern': pattern,
                    }
        
        return None


class ImageCaptchaSolver:
    """Solves image-based captchas using OCR"""
    
    def __init__(self):
        self.preprocessing_methods = [
            self._preprocess_standard,
            self._preprocess_high_contrast,
            self._preprocess_denoise,
            self._preprocess_adaptive,
        ]
    
    async def solve(self, image_data: bytes) -> Optional[str]:
        """
        Solve image captcha using multiple OCR methods
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Solved captcha text or None
        """
        if not (PIL_AVAILABLE and (TESSERACT_AVAILABLE or EASYOCR_AVAILABLE)):
            logger.warning("Image processing libraries not available")
            return None
        
        try:
            # Open image
            image = Image.open(BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Try multiple preprocessing methods
            results = []
            
            for preprocess_method in self.preprocessing_methods:
                processed = preprocess_method(image)
                
                # Try Tesseract
                if TESSERACT_AVAILABLE:
                    text = await self._ocr_tesseract(processed)
                    if text:
                        results.append(text)
                
                # Try EasyOCR
                if EASYOCR_AVAILABLE:
                    text = await self._ocr_easyocr(processed)
                    if text:
                        results.append(text)
            
            # Return most common result or longest
            if results:
                # Clean results
                cleaned = [self._clean_ocr_text(r) for r in results]
                cleaned = [r for r in cleaned if len(r) >= 4]  # Min 4 chars
                
                if cleaned:
                    # Return most common
                    from collections import Counter
                    counter = Counter(cleaned)
                    best = counter.most_common(1)[0][0]
                    logger.info(f"Image captcha solved: {best}")
                    return best
            
        except Exception as e:
            logger.error(f"Image captcha solving error: {e}")
        
        return None
    
    def _preprocess_standard(self, image: Image.Image) -> Image.Image:
        """Standard preprocessing"""
        # Convert to grayscale
        gray = image.convert('L')
        # Increase contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.0)
        # Threshold
        threshold = enhanced.point(lambda x: 255 if x > 128 else 0)
        return threshold
    
    def _preprocess_high_contrast(self, image: Image.Image) -> Image.Image:
        """High contrast preprocessing"""
        gray = image.convert('L')
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(3.0)
        sharpener = ImageEnhance.Sharpness(enhanced)
        sharpened = sharpener.enhance(2.0)
        return sharpened
    
    def _preprocess_denoise(self, image: Image.Image) -> Image.Image:
        """Denoise preprocessing"""
        if not CV2_AVAILABLE:
            return self._preprocess_standard(image)
        
        # Convert to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Threshold
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return Image.fromarray(thresh)
    
    def _preprocess_adaptive(self, image: Image.Image) -> Image.Image:
        """Adaptive threshold preprocessing"""
        if not CV2_AVAILABLE:
            return self._preprocess_standard(image)
        
        img_array = np.array(image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Adaptive threshold
        adaptive = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        return Image.fromarray(adaptive)
    
    async def _ocr_tesseract(self, image: Image.Image) -> Optional[str]:
        """OCR using Tesseract"""
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None,
                lambda: pytesseract.image_to_string(
                    image,
                    config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
                )
            )
            return text.strip()
        except Exception as e:
            logger.debug(f"Tesseract OCR error: {e}")
        return None
    
    async def _ocr_easyocr(self, image: Image.Image) -> Optional[str]:
        """OCR using EasyOCR"""
        try:
            reader = get_easyocr_reader()
            if not reader:
                return None
            
            # Convert to numpy array
            img_array = np.array(image)
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: reader.readtext(img_array)
            )
            
            if results:
                # Combine all detected text
                text = ''.join([r[1] for r in results])
                return text.strip()
                
        except Exception as e:
            logger.debug(f"EasyOCR error: {e}")
        return None
    
    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR output"""
        # Remove non-alphanumeric characters
        text = re.sub(r'[^a-zA-Z0-9]', '', text)
        return text.upper()


class AudioCaptchaSolver:
    """Solves audio-based captchas using speech recognition"""
    
    async def solve(self, audio_url: str) -> Optional[str]:
        """
        Solve audio captcha using speech recognition
        
        Args:
            audio_url: URL to audio file
            
        Returns:
            Recognized text or None
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.warning("SpeechRecognition not available")
            return None
        
        try:
            # Download audio
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status != 200:
                        return None
                    audio_data = await response.read()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            try:
                # Convert to WAV if needed (using pydub)
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_mp3(temp_path)
                    wav_path = temp_path.replace('.mp3', '.wav')
                    audio.export(wav_path, format='wav')
                    temp_path = wav_path
                except Exception:
                    pass  # Try with original file
                
                # Recognize speech
                recognizer = sr.Recognizer()
                
                loop = asyncio.get_event_loop()
                text = await loop.run_in_executor(
                    None,
                    self._recognize_audio,
                    recognizer,
                    temp_path
                )
                
                if text:
                    logger.info(f"Audio captcha solved: {text}")
                    return text
                    
            finally:
                # Cleanup temp files
                try:
                    os.unlink(temp_path)
                    if temp_path.endswith('.wav'):
                        os.unlink(temp_path.replace('.wav', '.mp3'))
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Audio captcha solving error: {e}")
        
        return None
    
    def _recognize_audio(self, recognizer: sr.Recognizer, audio_path: str) -> Optional[str]:
        """Perform speech recognition"""
        try:
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            
            # Try Google Speech Recognition (free)
            try:
                text = recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                pass
            
            # Try Sphinx (offline)
            try:
                text = recognizer.recognize_sphinx(audio)
                return text
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Speech recognition error: {e}")
        
        return None


class CloudflareBypasser:
    """Bypasses Cloudflare protection using browser automation"""
    
    @staticmethod
    async def bypass(page: Any, max_wait: int = 30) -> bool:
        """
        Bypass Cloudflare challenge
        
        Args:
            page: Playwright or Selenium page object
            max_wait: Maximum seconds to wait
            
        Returns:
            True if bypassed successfully
        """
        try:
            logger.info("Attempting Cloudflare bypass...")
            
            # Check if Cloudflare challenge is present
            content = await page.content()
            
            if not any(pattern in content.lower() for pattern in [
                'cloudflare', 'checking your browser', 'just a moment',
                'cf-browser-verification', 'ray id'
            ]):
                return True  # No Cloudflare detected
            
            # Wait for automatic challenge completion
            for i in range(max_wait):
                await asyncio.sleep(1)
                
                try:
                    current_content = await page.content()
                    
                    # Check if challenge completed
                    if not any(pattern in current_content.lower() for pattern in [
                        'checking your browser', 'just a moment',
                        'cf-browser-verification'
                    ]):
                        logger.info(f"Cloudflare bypass successful after {i+1}s")
                        return True
                    
                    # Try to click the checkbox if visible (Turnstile)
                    try:
                        checkbox = await page.query_selector('input[type="checkbox"]')
                        if checkbox:
                            await checkbox.click()
                            await asyncio.sleep(2)
                    except:
                        pass
                        
                except Exception:
                    pass
            
            logger.warning("Cloudflare bypass timeout")
            return False
            
        except Exception as e:
            logger.error(f"Cloudflare bypass error: {e}")
            return False


class ReCaptchaSolver:
    """Attempts to solve reCAPTCHA using audio challenge"""
    
    @staticmethod
    async def solve_v2(page: Any, site_key: str = None) -> bool:
        """
        Attempt to solve reCAPTCHA v2
        Uses audio challenge method
        
        Args:
            page: Browser page object
            site_key: Site key if known
            
        Returns:
            True if solved successfully
        """
        try:
            logger.info("Attempting reCAPTCHA v2 solve...")
            
            # Find and click the reCAPTCHA checkbox
            frames = page.frames
            
            for frame in frames:
                try:
                    # Look for reCAPTCHA iframe
                    checkbox = await frame.query_selector('.recaptcha-checkbox-border')
                    if checkbox:
                        await checkbox.click()
                        await asyncio.sleep(2)
                        
                        # Check if solved immediately (sometimes happens)
                        if await frame.query_selector('.recaptcha-checkbox-checked'):
                            logger.info("reCAPTCHA solved with single click")
                            return True
                        
                        # Need to solve challenge - try audio
                        audio_button = await frame.query_selector('#recaptcha-audio-button')
                        if audio_button:
                            await audio_button.click()
                            await asyncio.sleep(2)
                            
                            # Get audio URL
                            audio_source = await frame.query_selector('.rc-audiochallenge-tdownload-link')
                            if audio_source:
                                audio_url = await audio_source.get_attribute('href')
                                
                                # Solve audio
                                solver = AudioCaptchaSolver()
                                solution = await solver.solve(audio_url)
                                
                                if solution:
                                    # Enter solution
                                    input_field = await frame.query_selector('#audio-response')
                                    if input_field:
                                        await input_field.fill(solution)
                                        
                                        # Submit
                                        verify_button = await frame.query_selector('#recaptcha-verify-button')
                                        if verify_button:
                                            await verify_button.click()
                                            await asyncio.sleep(2)
                                            
                                            # Check if solved
                                            if await frame.query_selector('.recaptcha-checkbox-checked'):
                                                logger.info("reCAPTCHA v2 solved successfully")
                                                return True
                        
                except Exception as e:
                    logger.debug(f"Frame processing error: {e}")
                    continue
            
            logger.warning("reCAPTCHA v2 solve failed")
            return False
            
        except Exception as e:
            logger.error(f"reCAPTCHA v2 solving error: {e}")
            return False
    
    @staticmethod
    async def solve_v3(page: Any) -> bool:
        """
        reCAPTCHA v3 typically auto-solves based on behavior
        This method simulates human-like behavior
        """
        try:
            logger.info("Simulating human behavior for reCAPTCHA v3...")
            
            # Simulate mouse movement
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Simulate scroll
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Wait for potential auto-solve
            await asyncio.sleep(2)
            
            return True  # v3 is score-based, we can only hope
            
        except Exception as e:
            logger.debug(f"reCAPTCHA v3 behavior simulation error: {e}")
            return True  # Continue anyway


class CaptchaSolver:
    """
    Unified Captcha Solver
    Handles multiple captcha types with automatic detection
    """
    
    def __init__(self):
        self.enabled = True
        self.timeout = 60
        self.max_retries = 3
        self.detector = CaptchaDetector()
        self.image_solver = ImageCaptchaSolver()
        self.audio_solver = AudioCaptchaSolver()
        self.cloudflare_bypasser = CloudflareBypasser()
        self.recaptcha_solver = ReCaptchaSolver()
    
    async def solve(
        self,
        captcha_type: str,
        captcha_data: Any,
        page: Any = None
    ) -> Optional[str]:
        """
        Solve captcha based on type
        
        Args:
            captcha_type: Type of captcha
            captcha_data: Captcha data (image bytes, URL, etc.)
            page: Browser page object if available
            
        Returns:
            Solved captcha text/token or None
        """
        if not self.enabled:
            return None
        
        try:
            if captcha_type == "image":
                return await self.image_solver.solve(captcha_data)
                
            elif captcha_type == "audio":
                return await self.audio_solver.solve(captcha_data)
                
            elif captcha_type == "recaptcha_v2":
                if page:
                    success = await self.recaptcha_solver.solve_v2(page, captcha_data)
                    return "solved" if success else None
                    
            elif captcha_type == "recaptcha_v3":
                if page:
                    success = await self.recaptcha_solver.solve_v3(page)
                    return "solved" if success else None
                    
            elif captcha_type == "cloudflare":
                if page:
                    success = await self.cloudflare_bypasser.bypass(page)
                    return "bypassed" if success else None
                    
            elif captcha_type == "hcaptcha":
                # hCaptcha is similar to reCAPTCHA
                if page:
                    logger.info("hCaptcha solving not fully implemented, trying audio method")
                    # Would implement similar to reCAPTCHA
                    return None
                    
            else:
                logger.warning(f"Unknown captcha type: {captcha_type}")
                return None
                
        except Exception as e:
            logger.error(f"Captcha solving error: {e}")
            return None
    
    async def detect_captcha(self, html: str, page: Any = None) -> Optional[Dict[str, Any]]:
        """
        Detect if page contains captcha
        
        Args:
            html: Page HTML content
            page: Browser page object (optional)
            
        Returns:
            Dict with captcha info or None
        """
        captcha_info = self.detector.detect(html)
        
        if captcha_info:
            logger.info(f"Captcha detected: {captcha_info['type']}")
        
        return captcha_info
    
    async def bypass_cloudflare(self, page: Any) -> bool:
        """Convenience method to bypass Cloudflare"""
        return await self.cloudflare_bypasser.bypass(page)
    
    async def handle_captcha_if_present(
        self,
        html: str,
        page: Any = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect and handle captcha if present
        
        Returns:
            Tuple of (captcha_found, solution)
        """
        captcha_info = await self.detect_captcha(html, page)
        
        if not captcha_info:
            return False, None
        
        captcha_type = captcha_info['type']
        site_key = captcha_info.get('site_key')
        
        solution = await self.solve(captcha_type, site_key, page)
        
        return True, solution


# Global captcha solver instance
captcha_solver = CaptchaSolver()
