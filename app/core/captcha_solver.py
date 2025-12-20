"""
Advanced Captcha Solver - Powerful Local Implementation
Supports: reCAPTCHA v2/v3, Cloudflare Turnstile, Image Captchas
Works without external API dependencies using local ML and audio recognition

Key Features:
1. Captcha Avoidance - Primary strategy to avoid triggering captchas
2. Audio-based reCAPTCHA solving using speech recognition
3. Image captcha solving using advanced OCR with preprocessing
4. Cloudflare Turnstile bypass using browser automation
5. reCAPTCHA v3 token generation through stealth browser
6. Fallback to external APIs if configured
"""
import asyncio
import base64
import re
import os
import random
import time
import hashlib
import json
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

# Core imports
import aiohttp
from aiohttp import ClientTimeout

# Optional imports for local solving
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.debug("OpenCV not available - pip install opencv-python-headless")

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.debug("PIL not available - pip install pillow")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.debug("Tesseract not available - pip install pytesseract")

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logger.debug("SpeechRecognition not available - pip install SpeechRecognition")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.debug("pydub not available - pip install pydub")

# Browser automation
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.debug("Playwright not available - pip install playwright")

# External captcha services (optional fallback)
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


@dataclass
class CaptchaResult:
    """Result of captcha solving attempt"""
    success: bool
    solution: Optional[str] = None
    token: Optional[str] = None
    method: str = "unknown"
    time_taken: float = 0.0
    error: Optional[str] = None
    attempts: int = 1


class CaptchaAvoidance:
    """
    Strategies to avoid triggering captchas in the first place.
    Prevention is better than solving.
    """
    
    def __init__(self):
        self.request_counts: Dict[str, List[float]] = {}
        self.domain_cooldowns: Dict[str, float] = {}
        self.user_agents = self._load_user_agents()
        self.fingerprints = self._generate_fingerprints()
    
    def _load_user_agents(self) -> List[str]:
        """Load diverse user agents"""
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Chrome on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]
    
    def _generate_fingerprints(self) -> List[Dict[str, Any]]:
        """Generate browser fingerprint profiles"""
        return [
            {
                "platform": "Win32",
                "vendor": "Google Inc.",
                "languages": ["en-US", "en"],
                "screen": (1920, 1080),
                "color_depth": 24,
                "timezone": "America/New_York",
                "hardware_concurrency": 8,
                "device_memory": 8,
            },
            {
                "platform": "MacIntel",
                "vendor": "Apple Computer, Inc.",
                "languages": ["en-US", "en"],
                "screen": (2560, 1440),
                "color_depth": 30,
                "timezone": "America/Los_Angeles",
                "hardware_concurrency": 10,
                "device_memory": 16,
            },
            {
                "platform": "Linux x86_64",
                "vendor": "Google Inc.",
                "languages": ["en-US", "en"],
                "screen": (1920, 1080),
                "color_depth": 24,
                "timezone": "Europe/London",
                "hardware_concurrency": 12,
                "device_memory": 32,
            },
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.user_agents)
    
    def get_random_fingerprint(self) -> Dict[str, Any]:
        """Get a random browser fingerprint"""
        return random.choice(self.fingerprints)
    
    def should_delay(self, domain: str) -> Tuple[bool, float]:
        """
        Check if we should add a delay before request
        Returns (should_delay, delay_seconds)
        """
        now = time.time()
        
        # Check cooldown
        if domain in self.domain_cooldowns:
            cooldown_until = self.domain_cooldowns[domain]
            if now < cooldown_until:
                return True, cooldown_until - now
        
        # Check request frequency
        if domain not in self.request_counts:
            self.request_counts[domain] = []
        
        # Clean old entries (last 60 seconds)
        self.request_counts[domain] = [
            t for t in self.request_counts[domain] 
            if now - t < 60
        ]
        
        # If too many requests, add delay
        request_count = len(self.request_counts[domain])
        if request_count > 10:
            delay = min(30, request_count * 0.5)
            return True, delay
        
        return False, 0
    
    def record_request(self, domain: str):
        """Record a request to a domain"""
        if domain not in self.request_counts:
            self.request_counts[domain] = []
        self.request_counts[domain].append(time.time())
    
    def add_cooldown(self, domain: str, seconds: float):
        """Add a cooldown period for a domain"""
        self.domain_cooldowns[domain] = time.time() + seconds
    
    def get_human_like_delay(self) -> float:
        """Get a human-like random delay"""
        # Use beta distribution for more realistic timing
        return random.betavariate(2, 5) * 3 + 0.5


class ImageCaptchaSolver:
    """
    Advanced image captcha solver using local OCR with preprocessing
    """
    
    def __init__(self):
        self.ocr_configs = [
            '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
            '--psm 8 --oem 3',
            '--psm 6 --oem 3',
            '--psm 13 --oem 3',
            '--psm 7 --oem 1',
        ]
    
    async def solve(self, image_data: bytes) -> CaptchaResult:
        """Solve image captcha using advanced preprocessing and OCR"""
        start_time = time.time()
        
        if not all([CV2_AVAILABLE, PIL_AVAILABLE, TESSERACT_AVAILABLE]):
            return CaptchaResult(
                success=False,
                error="Required libraries not available (cv2, PIL, pytesseract)",
                method="local_ocr"
            )
        
        try:
            # Load image
            image = Image.open(BytesIO(image_data))
            
            # Apply multiple preprocessing strategies
            preprocessed_images = await self._preprocess_image(image)
            
            # Try OCR on each preprocessed version
            solutions = []
            for processed_img in preprocessed_images:
                for config in self.ocr_configs:
                    try:
                        text = pytesseract.image_to_string(processed_img, config=config)
                        cleaned = self._clean_ocr_result(text)
                        if cleaned and len(cleaned) >= 3:
                            solutions.append(cleaned)
                    except Exception as e:
                        logger.debug(f"OCR attempt failed: {e}")
            
            # Find most common solution
            if solutions:
                best_solution = max(set(solutions), key=solutions.count)
                return CaptchaResult(
                    success=True,
                    solution=best_solution,
                    method="local_ocr",
                    time_taken=time.time() - start_time,
                    attempts=len(solutions)
                )
            
            return CaptchaResult(
                success=False,
                error="Could not extract text from captcha",
                method="local_ocr",
                time_taken=time.time() - start_time
            )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                error=str(e),
                method="local_ocr",
                time_taken=time.time() - start_time
            )
    
    async def _preprocess_image(self, image: Image.Image) -> List[Image.Image]:
        """Apply multiple preprocessing strategies"""
        processed = []
        
        # Convert to numpy array for OpenCV processing
        img_array = np.array(image.convert('RGB'))
        
        # Strategy 1: Basic grayscale + threshold
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed.append(Image.fromarray(thresh1))
        
        # Strategy 2: Adaptive threshold
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        processed.append(Image.fromarray(adaptive))
        
        # Strategy 3: Denoising + threshold
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        _, thresh2 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed.append(Image.fromarray(thresh2))
        
        # Strategy 4: Morphological operations
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(thresh1, kernel, iterations=1)
        eroded = cv2.erode(dilated, kernel, iterations=1)
        processed.append(Image.fromarray(eroded))
        
        # Strategy 5: Scale up for better OCR
        scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, thresh_scaled = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed.append(Image.fromarray(thresh_scaled))
        
        # Strategy 6: Invert colors (for dark backgrounds)
        inverted = cv2.bitwise_not(thresh1)
        processed.append(Image.fromarray(inverted))
        
        # Strategy 7: PIL-based enhancement
        pil_enhanced = image.convert('L')
        pil_enhanced = ImageEnhance.Contrast(pil_enhanced).enhance(2.0)
        pil_enhanced = ImageEnhance.Sharpness(pil_enhanced).enhance(2.0)
        processed.append(pil_enhanced)
        
        return processed
    
    def _clean_ocr_result(self, text: str) -> str:
        """Clean OCR result"""
        # Remove whitespace and special characters
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', text.strip())
        return cleaned


class AudioCaptchaSolver:
    """
    Solve audio captchas using speech recognition
    Primarily for reCAPTCHA v2 audio challenges
    """
    
    def __init__(self):
        self.recognizer = None
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = False
    
    async def solve(self, audio_data: bytes, audio_format: str = "mp3") -> CaptchaResult:
        """Solve audio captcha using speech recognition"""
        start_time = time.time()
        
        if not SPEECH_RECOGNITION_AVAILABLE:
            return CaptchaResult(
                success=False,
                error="SpeechRecognition library not available",
                method="audio_recognition"
            )
        
        if not PYDUB_AVAILABLE:
            return CaptchaResult(
                success=False,
                error="pydub library not available",
                method="audio_recognition"
            )
        
        try:
            # Convert audio to WAV format
            with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            try:
                # Load audio and convert to WAV
                audio = AudioSegment.from_file(temp_path, format=audio_format)
                wav_path = temp_path.replace(f".{audio_format}", ".wav")
                audio.export(wav_path, format="wav")
                
                # Use speech recognition
                with sr.AudioFile(wav_path) as source:
                    audio_data = self.recognizer.record(source)
                
                # Try multiple recognition services
                solution = None
                errors = []
                
                # Try Google (free, no API key needed)
                try:
                    solution = self.recognizer.recognize_google(audio_data)
                except Exception as e:
                    errors.append(f"Google: {e}")
                
                # Try Sphinx (offline, less accurate)
                if not solution:
                    try:
                        solution = self.recognizer.recognize_sphinx(audio_data)
                    except Exception as e:
                        errors.append(f"Sphinx: {e}")
                
                # Clean up temp files
                os.unlink(temp_path)
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
                
                if solution:
                    # Clean the solution (remove spaces, lowercase)
                    cleaned = re.sub(r'[^a-zA-Z0-9]', '', solution.lower())
                    return CaptchaResult(
                        success=True,
                        solution=cleaned,
                        method="audio_recognition",
                        time_taken=time.time() - start_time
                    )
                
                return CaptchaResult(
                    success=False,
                    error=f"Recognition failed: {'; '.join(errors)}",
                    method="audio_recognition",
                    time_taken=time.time() - start_time
                )
                
            finally:
                # Cleanup
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            return CaptchaResult(
                success=False,
                error=str(e),
                method="audio_recognition",
                time_taken=time.time() - start_time
            )


class RecaptchaSolver:
    """
    Solve reCAPTCHA v2 and v3 using browser automation
    """
    
    def __init__(self):
        self.audio_solver = AudioCaptchaSolver()
        self.playwright = None
        self.browser = None
    
    async def initialize(self):
        """Initialize browser if needed"""
        if not PLAYWRIGHT_AVAILABLE:
            return
        
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-gpu',
                ]
            )
    
    async def solve_v2(self, url: str, site_key: str) -> CaptchaResult:
        """
        Solve reCAPTCHA v2 using audio challenge
        """
        start_time = time.time()
        
        if not PLAYWRIGHT_AVAILABLE:
            return CaptchaResult(
                success=False,
                error="Playwright not available for reCAPTCHA solving",
                method="recaptcha_v2_audio"
            )
        
        try:
            await self.initialize()
            
            context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
            )
            
            page = await context.new_page()
            
            # Inject stealth scripts
            await self._inject_stealth(page)
            
            # Create a simple page with reCAPTCHA
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://www.google.com/recaptcha/api.js" async defer></script>
            </head>
            <body>
                <div class="g-recaptcha" data-sitekey="{site_key}"></div>
                <script>
                    function getRecaptchaResponse() {{
                        return grecaptcha.getResponse();
                    }}
                </script>
            </body>
            </html>
            """
            
            await page.set_content(html_content)
            await asyncio.sleep(2)
            
            # Click on reCAPTCHA checkbox
            recaptcha_frame = page.frame_locator('iframe[src*="recaptcha"]').first
            await recaptcha_frame.locator('.recaptcha-checkbox-border').click()
            await asyncio.sleep(2)
            
            # Check if solved immediately (no challenge)
            try:
                token = await page.evaluate('grecaptcha.getResponse()')
                if token:
                    await context.close()
                    return CaptchaResult(
                        success=True,
                        token=token,
                        method="recaptcha_v2_auto",
                        time_taken=time.time() - start_time
                    )
            except:
                pass
            
            # Find challenge iframe and switch to audio
            challenge_frame = page.frame_locator('iframe[src*="recaptcha"][src*="bframe"]').first
            
            # Click audio button
            try:
                await challenge_frame.locator('#recaptcha-audio-button').click()
                await asyncio.sleep(2)
            except:
                await context.close()
                return CaptchaResult(
                    success=False,
                    error="Could not find audio challenge button",
                    method="recaptcha_v2_audio",
                    time_taken=time.time() - start_time
                )
            
            # Get audio URL
            try:
                audio_source = await challenge_frame.locator('#audio-source').get_attribute('src')
                if not audio_source:
                    raise Exception("No audio source found")
            except:
                await context.close()
                return CaptchaResult(
                    success=False,
                    error="Could not get audio challenge URL",
                    method="recaptcha_v2_audio",
                    time_taken=time.time() - start_time
                )
            
            # Download and solve audio
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_source) as resp:
                    audio_data = await resp.read()
            
            audio_result = await self.audio_solver.solve(audio_data, "mp3")
            
            if not audio_result.success:
                await context.close()
                return CaptchaResult(
                    success=False,
                    error=f"Audio solving failed: {audio_result.error}",
                    method="recaptcha_v2_audio",
                    time_taken=time.time() - start_time
                )
            
            # Enter solution
            await challenge_frame.locator('#audio-response').fill(audio_result.solution)
            await challenge_frame.locator('#recaptcha-verify-button').click()
            await asyncio.sleep(3)
            
            # Get token
            try:
                token = await page.evaluate('grecaptcha.getResponse()')
                if token:
                    await context.close()
                    return CaptchaResult(
                        success=True,
                        token=token,
                        method="recaptcha_v2_audio",
                        time_taken=time.time() - start_time
                    )
            except:
                pass
            
            await context.close()
            return CaptchaResult(
                success=False,
                error="Failed to get reCAPTCHA token after solving",
                method="recaptcha_v2_audio",
                time_taken=time.time() - start_time
            )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                error=str(e),
                method="recaptcha_v2_audio",
                time_taken=time.time() - start_time
            )
    
    async def solve_v3(self, url: str, site_key: str, action: str = "submit") -> CaptchaResult:
        """
        Solve reCAPTCHA v3 by executing with high score through stealth browser
        """
        start_time = time.time()
        
        if not PLAYWRIGHT_AVAILABLE:
            return CaptchaResult(
                success=False,
                error="Playwright not available for reCAPTCHA v3",
                method="recaptcha_v3"
            )
        
        try:
            await self.initialize()
            
            context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
            )
            
            page = await context.new_page()
            await self._inject_stealth(page)
            
            # Navigate to the actual URL
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Simulate human-like behavior to improve score
            await self._simulate_human_behavior(page)
            
            # Execute reCAPTCHA v3
            token = await page.evaluate(f"""
                async () => {{
                    return new Promise((resolve, reject) => {{
                        if (typeof grecaptcha !== 'undefined') {{
                            grecaptcha.ready(async () => {{
                                try {{
                                    const token = await grecaptcha.execute('{site_key}', {{action: '{action}'}});
                                    resolve(token);
                                }} catch (e) {{
                                    reject(e);
                                }}
                            }});
                        }} else {{
                            reject('grecaptcha not loaded');
                        }}
                    }});
                }}
            """)
            
            await context.close()
            
            if token:
                return CaptchaResult(
                    success=True,
                    token=token,
                    method="recaptcha_v3",
                    time_taken=time.time() - start_time
                )
            
            return CaptchaResult(
                success=False,
                error="Failed to get reCAPTCHA v3 token",
                method="recaptcha_v3",
                time_taken=time.time() - start_time
            )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                error=str(e),
                method="recaptcha_v3",
                time_taken=time.time() - start_time
            )
    
    async def _inject_stealth(self, page):
        """Inject stealth scripts to avoid detection"""
        await page.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome property
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.apply(this, arguments);
            };
        """)
    
    async def _simulate_human_behavior(self, page):
        """Simulate human-like behavior to improve reCAPTCHA v3 score"""
        # Random mouse movements
        for _ in range(random.randint(3, 7)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Random scrolling
        for _ in range(random.randint(1, 3)):
            scroll_amount = random.randint(100, 300)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Wait with some activity
        await asyncio.sleep(random.uniform(1, 2))
    
    async def close(self):
        """Close browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class CloudflareSolver:
    """
    Bypass Cloudflare challenges (Turnstile, Under Attack Mode)
    """
    
    def __init__(self):
        self.playwright = None
        self.browser = None
    
    async def initialize(self):
        """Initialize browser"""
        if not PLAYWRIGHT_AVAILABLE:
            return
        
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
    
    async def bypass(self, url: str, page: Any = None) -> CaptchaResult:
        """
        Bypass Cloudflare protection
        """
        start_time = time.time()
        
        if not PLAYWRIGHT_AVAILABLE:
            return CaptchaResult(
                success=False,
                error="Playwright not available for Cloudflare bypass",
                method="cloudflare_bypass"
            )
        
        try:
            await self.initialize()
            
            should_close = False
            context = None
            
            if not page:
                context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                )
                page = await context.new_page()
                should_close = True
                
                # Inject stealth
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                """)
                
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for Cloudflare challenge
            logger.info("Waiting for Cloudflare challenge...")
            
            max_attempts = 30
            for attempt in range(max_attempts):
                content = await page.content()
                
                # Check if challenge is complete
                if not any(indicator in content.lower() for indicator in [
                    'checking your browser',
                    'cloudflare',
                    'cf-browser-verification',
                    'just a moment',
                    '_cf_chl'
                ]):
                    logger.info("Cloudflare challenge passed")
                    
                    # Get cookies for future requests
                    cookies = await page.context.cookies()
                    
                    if should_close and context:
                        await context.close()
                    
                    return CaptchaResult(
                        success=True,
                        solution=json.dumps(cookies),
                        method="cloudflare_bypass",
                        time_taken=time.time() - start_time
                    )
                
                # Try to click Turnstile checkbox if present
                try:
                    turnstile = await page.query_selector('input[type="checkbox"]')
                    if turnstile:
                        await turnstile.click()
                        await asyncio.sleep(1)
                except:
                    pass
                
                # Try clicking verify button
                try:
                    verify_button = await page.query_selector('button:has-text("Verify")')
                    if verify_button:
                        await verify_button.click()
                        await asyncio.sleep(1)
                except:
                    pass
                
                await asyncio.sleep(2)
            
            if should_close and context:
                await context.close()
            
            return CaptchaResult(
                success=False,
                error="Cloudflare challenge timeout",
                method="cloudflare_bypass",
                time_taken=time.time() - start_time
            )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                error=str(e),
                method="cloudflare_bypass",
                time_taken=time.time() - start_time
            )
    
    async def close(self):
        """Close browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class CaptchaSolver:
    """
    Advanced captcha solver with multiple strategies:
    1. Captcha avoidance (primary)
    2. Local image OCR
    3. Audio recognition for reCAPTCHA
    4. Browser automation for reCAPTCHA v2/v3
    5. Cloudflare bypass
    6. Fallback to external APIs (2Captcha, Anti-Captcha, CapMonster)
    """
    
    def __init__(self):
        self.enabled = True
        self.timeout = 120
        self.max_retries = 3
        
        # Initialize solvers
        self.avoidance = CaptchaAvoidance()
        self.image_solver = ImageCaptchaSolver()
        self.audio_solver = AudioCaptchaSolver()
        self.recaptcha_solver = RecaptchaSolver()
        self.cloudflare_solver = CloudflareSolver()
        
        # External API keys (optional fallback)
        self.twocaptcha_key = os.environ.get('TWOCAPTCHA_API_KEY', '')
        self.anticaptcha_key = os.environ.get('ANTICAPTCHA_API_KEY', '')
        self.capmonster_key = os.environ.get('CAPMONSTER_API_KEY', '')
        
        # Initialize external services
        self._init_external_services()
        
        # Statistics
        self.stats = {
            'attempts': 0,
            'successes': 0,
            'failures': 0,
            'methods_used': {}
        }
    
    def _init_external_services(self):
        """Initialize external captcha services as fallback"""
        self.twocaptcha_solver = None
        if TWOCAPTCHA_AVAILABLE and self.twocaptcha_key:
            try:
                self.twocaptcha_solver = TwoCaptcha(self.twocaptcha_key)
                logger.info("2Captcha fallback service initialized")
            except Exception as e:
                logger.debug(f"Failed to initialize 2Captcha: {e}")
        
        self.anticaptcha_available = ANTICAPTCHA_AVAILABLE and bool(self.anticaptcha_key)
    
    async def solve(
        self,
        captcha_type: str,
        captcha_data: Any = None,
        page: Any = None,
        site_key: str = "",
        url: str = "",
        action: str = "submit"
    ) -> Optional[str]:
        """
        Solve captcha using the best available method
        
        Args:
            captcha_type: Type of captcha (image, recaptcha_v2, recaptcha_v3, cloudflare, hcaptcha)
            captcha_data: Raw captcha data (image bytes for image captchas)
            page: Browser page object if available
            site_key: Site key for reCAPTCHA/hCaptcha
            url: Page URL
            action: Action for reCAPTCHA v3
            
        Returns:
            Solved captcha token/text or None if failed
        """
        if not self.enabled:
            return None
        
        self.stats['attempts'] += 1
        logger.info(f"Attempting to solve {captcha_type} captcha")
        
        for attempt in range(self.max_retries):
            try:
                result = None
                
                if captcha_type == "image":
                    result = await self._solve_image(captcha_data)
                    
                elif captcha_type in ("recaptcha", "recaptcha_v2"):
                    result = await self._solve_recaptcha_v2(site_key, url)
                    
                elif captcha_type == "recaptcha_v3":
                    result = await self._solve_recaptcha_v3(site_key, url, action)
                    
                elif captcha_type == "cloudflare":
                    result = await self._solve_cloudflare(url, page)
                    
                elif captcha_type == "hcaptcha":
                    result = await self._solve_hcaptcha(site_key, url)
                    
                else:
                    logger.warning(f"Unknown captcha type: {captcha_type}")
                    return None
                
                if result and result.success:
                    self.stats['successes'] += 1
                    method = result.method
                    self.stats['methods_used'][method] = self.stats['methods_used'].get(method, 0) + 1
                    logger.info(f"Captcha solved via {method} in {result.time_taken:.2f}s")
                    return result.token or result.solution
                
            except Exception as e:
                logger.warning(f"Captcha solving attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2)
        
        self.stats['failures'] += 1
        logger.error(f"Failed to solve {captcha_type} captcha after {self.max_retries} attempts")
        return None
    
    async def _solve_image(self, image_data: bytes) -> CaptchaResult:
        """Solve image captcha"""
        # Try local OCR first
        result = await self.image_solver.solve(image_data)
        if result.success:
            return result
        
        # Fallback to external services
        if self.twocaptcha_solver:
            try:
                result = await self._solve_image_2captcha(image_data)
                if result.success:
                    return result
            except Exception as e:
                logger.debug(f"2Captcha fallback failed: {e}")
        
        if self.capmonster_key:
            try:
                result = await self._solve_image_capmonster(image_data)
                if result.success:
                    return result
            except Exception as e:
                logger.debug(f"CapMonster fallback failed: {e}")
        
        return CaptchaResult(success=False, error="All image solving methods failed")
    
    async def _solve_recaptcha_v2(self, site_key: str, url: str) -> CaptchaResult:
        """Solve reCAPTCHA v2"""
        # Try local audio solving first
        result = await self.recaptcha_solver.solve_v2(url, site_key)
        if result.success:
            return result
        
        # Fallback to external services
        if self.twocaptcha_solver:
            try:
                loop = asyncio.get_event_loop()
                
                def solve():
                    return self.twocaptcha_solver.recaptcha(sitekey=site_key, url=url)
                
                ext_result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                
                if ext_result and ext_result.get('code'):
                    return CaptchaResult(
                        success=True,
                        token=ext_result.get('code'),
                        method="2captcha_fallback"
                    )
            except Exception as e:
                logger.debug(f"2Captcha fallback failed: {e}")
        
        return CaptchaResult(success=False, error="All reCAPTCHA v2 methods failed")
    
    async def _solve_recaptcha_v3(self, site_key: str, url: str, action: str) -> CaptchaResult:
        """Solve reCAPTCHA v3"""
        # Try local browser automation first
        result = await self.recaptcha_solver.solve_v3(url, site_key, action)
        if result.success:
            return result
        
        # Fallback to external services
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
                
                ext_result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                
                if ext_result and ext_result.get('code'):
                    return CaptchaResult(
                        success=True,
                        token=ext_result.get('code'),
                        method="2captcha_fallback"
                    )
            except Exception as e:
                logger.debug(f"2Captcha fallback failed: {e}")
        
        return CaptchaResult(success=False, error="All reCAPTCHA v3 methods failed")
    
    async def _solve_cloudflare(self, url: str, page: Any = None) -> CaptchaResult:
        """Bypass Cloudflare protection"""
        return await self.cloudflare_solver.bypass(url, page)
    
    async def _solve_hcaptcha(self, site_key: str, url: str) -> CaptchaResult:
        """Solve hCaptcha"""
        # hCaptcha is harder to solve locally, use external services
        if self.twocaptcha_solver:
            try:
                loop = asyncio.get_event_loop()
                
                def solve():
                    return self.twocaptcha_solver.hcaptcha(sitekey=site_key, url=url)
                
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, solve),
                    timeout=self.timeout
                )
                
                if result and result.get('code'):
                    return CaptchaResult(
                        success=True,
                        token=result.get('code'),
                        method="2captcha_hcaptcha"
                    )
            except Exception as e:
                logger.debug(f"2Captcha hCaptcha failed: {e}")
        
        return CaptchaResult(success=False, error="hCaptcha solving not available locally")
    
    async def _solve_image_2captcha(self, image_data: bytes) -> CaptchaResult:
        """Solve image captcha with 2Captcha"""
        try:
            loop = asyncio.get_event_loop()
            
            def solve():
                return self.twocaptcha_solver.normal(
                    base64.b64encode(image_data).decode('utf-8')
                )
            
            result = await loop.run_in_executor(None, solve)
            
            if result and result.get('code'):
                return CaptchaResult(
                    success=True,
                    solution=result.get('code'),
                    method="2captcha_image"
                )
        except Exception as e:
            logger.debug(f"2Captcha image error: {e}")
        
        return CaptchaResult(success=False, error="2Captcha failed")
    
    async def _solve_image_capmonster(self, image_data: bytes) -> CaptchaResult:
        """Solve image captcha with CapMonster"""
        try:
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
                    return CaptchaResult(success=False, error="CapMonster task creation failed")
                
                for _ in range(60):
                    await asyncio.sleep(1)
                    
                    async with session.post(
                        "https://api.capmonster.cloud/getTaskResult",
                        json={"clientKey": self.capmonster_key, "taskId": task_id}
                    ) as resp:
                        result = await resp.json()
                        
                        if result.get('status') == 'ready':
                            return CaptchaResult(
                                success=True,
                                solution=result.get('solution', {}).get('text'),
                                method="capmonster_image"
                            )
                        elif result.get('status') == 'failed':
                            return CaptchaResult(success=False, error="CapMonster task failed")
                
        except Exception as e:
            logger.debug(f"CapMonster error: {e}")
        
        return CaptchaResult(success=False, error="CapMonster timeout")
    
    async def detect_captcha(self, html: str, page: Any = None) -> Optional[Dict[str, Any]]:
        """
        Detect captcha type in page content
        """
        captcha_info = None
        
        # Check for reCAPTCHA
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
        elif any(indicator in html.lower() for indicator in [
            "cf-browser-verification",
            "cloudflare",
            "checking your browser",
            "_cf_chl",
            "turnstile"
        ]):
            captcha_info = {
                "type": "cloudflare",
                "site_key": None
            }
        
        # Check for FunCaptcha/Arkose
        elif "funcaptcha" in html.lower() or "arkoselabs" in html.lower():
            captcha_info = {
                "type": "funcaptcha",
                "site_key": None
            }
        
        # Check for image captcha
        elif re.search(r'captcha.*\.(jpg|png|gif)', html.lower()):
            captcha_info = {
                "type": "image",
                "site_key": None
            }
        
        if captcha_info:
            logger.info(f"Captcha detected: {captcha_info['type']}")
        
        return captcha_info
    
    def should_avoid_captcha(self, domain: str) -> Tuple[bool, float]:
        """Check if we should delay to avoid captcha"""
        return self.avoidance.should_delay(domain)
    
    def record_request(self, domain: str):
        """Record a request for captcha avoidance"""
        self.avoidance.record_request(domain)
    
    def get_human_like_delay(self) -> float:
        """Get a human-like delay"""
        return self.avoidance.get_human_like_delay()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get solver statistics"""
        return {
            **self.stats,
            'success_rate': self.stats['successes'] / max(self.stats['attempts'], 1) * 100,
            'external_apis_available': {
                '2captcha': bool(self.twocaptcha_solver),
                'anticaptcha': self.anticaptcha_available,
                'capmonster': bool(self.capmonster_key)
            },
            'local_solvers_available': {
                'image_ocr': all([CV2_AVAILABLE, PIL_AVAILABLE, TESSERACT_AVAILABLE]),
                'audio_recognition': SPEECH_RECOGNITION_AVAILABLE and PYDUB_AVAILABLE,
                'browser_automation': PLAYWRIGHT_AVAILABLE
            }
        }
    
    def get_balance(self) -> Dict[str, float]:
        """Get balance from external captcha services"""
        balances = {}
        
        if self.twocaptcha_solver:
            try:
                balance = self.twocaptcha_solver.balance()
                balances['2captcha'] = float(balance)
            except:
                pass
        
        return balances
    
    async def close(self):
        """Cleanup resources"""
        await self.recaptcha_solver.close()
        await self.cloudflare_solver.close()


# Global captcha solver instance
captcha_solver = CaptchaSolver()
