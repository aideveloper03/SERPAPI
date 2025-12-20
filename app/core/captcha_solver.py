"""
Advanced Captcha Solver & Avoider
Powerful local captcha solving without external APIs
Implements multiple bypass and solving strategies
"""
import asyncio
import base64
import random
import re
import os
import time
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO
from loguru import logger

# Optional imports with graceful fallback
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class CaptchaAvoider:
    """
    Strategies to AVOID captchas before they appear
    Prevention is better than solving
    """
    
    # Stealth JavaScript to inject before page load
    STEALTH_SCRIPTS = '''
    // Comprehensive stealth mode - avoid detection
    
    // 1. Override navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    
    // 2. Override chrome runtime
    window.chrome = {
        runtime: {},
        loadTimes: function() { return {}; },
        csi: function() { return {}; },
        app: { isInstalled: false }
    };
    
    // 3. Override permissions API
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    
    // 4. Mock realistic plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
            ];
            plugins.length = 3;
            return plugins;
        },
        configurable: true
    });
    
    // 5. Mock languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en', 'es'],
        configurable: true
    });
    
    // 6. Mock platform
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32',
        configurable: true
    });
    
    // 7. Mock hardware concurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
        configurable: true
    });
    
    // 8. Mock device memory
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
        configurable: true
    });
    
    // 9. Mock connection
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            rtt: 50,
            downlink: 10,
            saveData: false
        }),
        configurable: true
    });
    
    // 10. WebGL fingerprint masking
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            // UNMASKED_VENDOR_WEBGL
            if (param === 37445) {
                return 'Intel Inc.';
            }
            // UNMASKED_RENDERER_WEBGL
            if (param === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return Reflect.apply(target, thisArg, args);
        }
    };
    
    try {
        WebGLRenderingContext.prototype.getParameter = new Proxy(
            WebGLRenderingContext.prototype.getParameter,
            getParameterProxyHandler
        );
        WebGL2RenderingContext.prototype.getParameter = new Proxy(
            WebGL2RenderingContext.prototype.getParameter,
            getParameterProxyHandler
        );
    } catch(e) {}
    
    // 11. Canvas fingerprint noise
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        if (type === 'image/png' && this.width > 16 && this.height > 16) {
            const context = this.getContext('2d');
            if (context) {
                const imageData = context.getImageData(0, 0, this.width, this.height);
                // Add minimal noise
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] ^= 1;
                }
                context.putImageData(imageData, 0, 0);
            }
        }
        return originalToDataURL.apply(this, arguments);
    };
    
    // 12. Audio fingerprint masking
    const originalCreateOscillator = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function() {
        const oscillator = originalCreateOscillator.apply(this, arguments);
        oscillator.frequency.value += Math.random() * 0.0001;
        return oscillator;
    };
    
    // 13. Hide automation indicators
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    
    // 14. Override date to look consistent
    const originalDateGetTimezoneOffset = Date.prototype.getTimezoneOffset;
    Date.prototype.getTimezoneOffset = function() {
        return -300; // EST
    };
    
    // 15. Mimic human-like mouse movements stored
    window.__mouseMovements = [];
    document.addEventListener('mousemove', (e) => {
        window.__mouseMovements.push({x: e.clientX, y: e.clientY, t: Date.now()});
        if (window.__mouseMovements.length > 100) {
            window.__mouseMovements.shift();
        }
    });
    '''
    
    @staticmethod
    def get_stealth_scripts() -> str:
        """Get stealth JavaScript to inject"""
        return CaptchaAvoider.STEALTH_SCRIPTS
    
    @staticmethod
    async def human_like_delay(min_ms: int = 100, max_ms: int = 500):
        """Add human-like random delay"""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)
    
    @staticmethod
    async def simulate_human_behavior(page) -> None:
        """Simulate human-like behavior on page"""
        try:
            # Random scroll
            await page.evaluate('''
                () => {
                    window.scrollBy({
                        top: Math.random() * 300 + 100,
                        left: 0,
                        behavior: 'smooth'
                    });
                }
            ''')
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Random mouse movement simulation
            viewport = await page.viewport_size()
            if viewport:
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            logger.debug(f"Human behavior simulation error: {e}")


class ImageCaptchaSolver:
    """
    Local image captcha solver using OCR and image processing
    No external API required
    """
    
    def __init__(self):
        self.ocr_configs = [
            # Different tesseract configurations for various captcha types
            '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
            '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            '--psm 6 --oem 3',
            '--psm 13 --oem 3',
            '--psm 7 --oem 1',
        ]
        
        # Character corrections for common OCR mistakes
        self.char_corrections = {
            '0': ['O', 'o', 'Q', 'D'],
            'O': ['0', 'Q', 'D'],
            '1': ['l', 'I', 'i', '|'],
            'l': ['1', 'I', 'i'],
            'I': ['1', 'l', 'i'],
            '5': ['S', 's'],
            'S': ['5'],
            '8': ['B'],
            'B': ['8'],
            '2': ['Z', 'z'],
            'Z': ['2'],
        }
    
    async def solve(self, image_data: bytes) -> Optional[str]:
        """
        Solve image captcha using multiple processing techniques
        """
        if not (PIL_AVAILABLE and TESSERACT_AVAILABLE):
            logger.warning("PIL or Tesseract not available for image captcha solving")
            return None
        
        try:
            # Load image
            image = Image.open(BytesIO(image_data))
            
            # Try multiple processing pipelines
            processing_methods = [
                self._process_standard,
                self._process_threshold,
                self._process_adaptive,
                self._process_denoise,
                self._process_edge_enhanced,
            ]
            
            results = []
            for method in processing_methods:
                try:
                    processed = method(image)
                    for config in self.ocr_configs[:3]:  # Try top 3 configs
                        text = pytesseract.image_to_string(processed, config=config)
                        cleaned = self._clean_result(text)
                        if cleaned and len(cleaned) >= 4:
                            results.append(cleaned)
                except Exception as e:
                    logger.debug(f"Processing method failed: {e}")
                    continue
            
            # Return most common result
            if results:
                from collections import Counter
                most_common = Counter(results).most_common(1)[0][0]
                logger.info(f"Image captcha solved: {most_common}")
                return most_common
            
        except Exception as e:
            logger.error(f"Image captcha solving error: {e}")
        
        return None
    
    def _process_standard(self, image: Image.Image) -> Image.Image:
        """Standard grayscale processing"""
        gray = image.convert('L')
        return gray
    
    def _process_threshold(self, image: Image.Image) -> Image.Image:
        """Binary threshold processing"""
        gray = image.convert('L')
        threshold = 128
        return gray.point(lambda x: 255 if x > threshold else 0)
    
    def _process_adaptive(self, image: Image.Image) -> Image.Image:
        """Adaptive threshold using OpenCV"""
        if not CV2_AVAILABLE:
            return self._process_threshold(image)
        
        # Convert to OpenCV format
        img_array = np.array(image.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply adaptive threshold
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return Image.fromarray(processed)
    
    def _process_denoise(self, image: Image.Image) -> Image.Image:
        """Denoise and enhance"""
        if not CV2_AVAILABLE:
            return self._process_threshold(image)
        
        img_array = np.array(image.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Threshold
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return Image.fromarray(thresh)
    
    def _process_edge_enhanced(self, image: Image.Image) -> Image.Image:
        """Edge enhancement processing"""
        gray = image.convert('L')
        
        # Enhance edges
        enhanced = gray.filter(ImageFilter.EDGE_ENHANCE_MORE)
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = enhancer.enhance(2.0)
        
        # Threshold
        return enhanced.point(lambda x: 255 if x > 128 else 0)
    
    def _clean_result(self, text: str) -> str:
        """Clean OCR result"""
        # Remove whitespace and special characters
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', text.strip())
        return cleaned


class RecaptchaSolver:
    """
    reCAPTCHA bypass strategies without external API
    Uses browser automation and audio challenge
    """
    
    def __init__(self):
        self.max_attempts = 3
    
    async def solve_v2(self, page, site_key: str = None) -> Optional[str]:
        """
        Attempt to solve reCAPTCHA v2
        Uses multiple bypass strategies
        """
        try:
            # Strategy 1: Check if already solved (invisible reCAPTCHA)
            token = await self._check_existing_token(page)
            if token:
                logger.info("reCAPTCHA already solved (invisible)")
                return token
            
            # Strategy 2: Try to find and click the checkbox
            solved = await self._click_checkbox(page)
            if solved:
                token = await self._check_existing_token(page)
                if token:
                    logger.info("reCAPTCHA solved via checkbox")
                    return token
            
            # Strategy 3: Audio challenge (if available)
            token = await self._try_audio_challenge(page)
            if token:
                logger.info("reCAPTCHA solved via audio challenge")
                return token
            
            # Strategy 4: Wait for auto-solve (reCAPTCHA v3 behavior)
            await asyncio.sleep(3)
            token = await self._check_existing_token(page)
            if token:
                return token
            
            logger.warning("reCAPTCHA could not be solved locally")
            return None
            
        except Exception as e:
            logger.error(f"reCAPTCHA solving error: {e}")
            return None
    
    async def solve_v3(self, page, site_key: str = None, action: str = "submit") -> Optional[str]:
        """
        reCAPTCHA v3 handling
        V3 is score-based and usually auto-passes with good browser fingerprint
        """
        try:
            # Wait for reCAPTCHA v3 to generate token
            await asyncio.sleep(2)
            
            # Check for existing token
            token = await self._check_existing_token(page)
            if token:
                return token
            
            # Try to trigger v3 execution
            await page.evaluate(f'''
                () => {{
                    if (typeof grecaptcha !== 'undefined' && grecaptcha.execute) {{
                        grecaptcha.execute('{site_key or ""}', {{action: '{action}'}});
                    }}
                }}
            ''')
            
            await asyncio.sleep(2)
            return await self._check_existing_token(page)
            
        except Exception as e:
            logger.debug(f"reCAPTCHA v3 error: {e}")
            return None
    
    async def _check_existing_token(self, page) -> Optional[str]:
        """Check if reCAPTCHA token already exists"""
        try:
            # Check textarea response
            token = await page.evaluate('''
                () => {
                    const textarea = document.querySelector('[name="g-recaptcha-response"]');
                    if (textarea && textarea.value) {
                        return textarea.value;
                    }
                    
                    // Check for invisible reCAPTCHA callback
                    if (window.___grecaptcha_cfg && window.___grecaptcha_cfg.clients) {
                        for (let client of Object.values(window.___grecaptcha_cfg.clients)) {
                            if (client && client.callback && typeof client.callback === 'function') {
                                // Token might be passed to callback
                            }
                        }
                    }
                    
                    return null;
                }
            ''')
            return token
        except:
            return None
    
    async def _click_checkbox(self, page) -> bool:
        """Click reCAPTCHA checkbox"""
        try:
            # Find reCAPTCHA iframe
            frames = page.frames
            
            for frame in frames:
                try:
                    # Look for checkbox
                    checkbox = await frame.query_selector('.recaptcha-checkbox-border')
                    if not checkbox:
                        checkbox = await frame.query_selector('#recaptcha-anchor')
                    
                    if checkbox:
                        # Human-like click
                        await CaptchaAvoider.human_like_delay(200, 500)
                        await checkbox.click()
                        await asyncio.sleep(2)
                        
                        # Check if solved (green checkmark)
                        is_checked = await frame.evaluate('''
                            () => {
                                const anchor = document.querySelector('#recaptcha-anchor');
                                return anchor && anchor.getAttribute('aria-checked') === 'true';
                            }
                        ''')
                        
                        if is_checked:
                            return True
                            
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Checkbox click error: {e}")
            return False
    
    async def _try_audio_challenge(self, page) -> Optional[str]:
        """Try audio challenge (requires speech recognition)"""
        # Note: Full audio solving requires speech recognition API
        # This is a placeholder for the audio challenge flow
        try:
            frames = page.frames
            
            for frame in frames:
                try:
                    # Look for audio button
                    audio_btn = await frame.query_selector('#recaptcha-audio-button')
                    if audio_btn:
                        await audio_btn.click()
                        await asyncio.sleep(2)
                        
                        # Audio challenge is complex to solve without external APIs
                        # Would need local speech recognition
                        logger.debug("Audio challenge detected - requires speech recognition")
                        break
                        
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Audio challenge error: {e}")
            return None


class CloudflareSolver:
    """
    Cloudflare challenge bypass
    Handles various Cloudflare protection types
    """
    
    def __init__(self):
        self.max_wait = 30
    
    async def bypass(self, page) -> bool:
        """
        Bypass Cloudflare challenge
        """
        try:
            content = await page.content()
            
            # Check if Cloudflare challenge
            if not self._is_cloudflare_challenge(content):
                return True
            
            logger.info("Cloudflare challenge detected, attempting bypass...")
            
            # Inject stealth scripts
            await page.add_init_script(CaptchaAvoider.get_stealth_scripts())
            
            # Strategy 1: Wait for auto-solve (JS challenge)
            for i in range(self.max_wait):
                await asyncio.sleep(1)
                content = await page.content()
                
                if not self._is_cloudflare_challenge(content):
                    logger.info("Cloudflare JS challenge passed")
                    return True
                
                # Check for Turnstile widget
                turnstile = await page.query_selector('.cf-turnstile')
                if turnstile:
                    return await self._solve_turnstile(page)
            
            # Strategy 2: Try clicking any challenge checkbox
            await self._try_click_challenge(page)
            
            await asyncio.sleep(3)
            content = await page.content()
            return not self._is_cloudflare_challenge(content)
            
        except Exception as e:
            logger.error(f"Cloudflare bypass error: {e}")
            return False
    
    def _is_cloudflare_challenge(self, content: str) -> bool:
        """Check if page contains Cloudflare challenge"""
        indicators = [
            'cf-browser-verification',
            'checking your browser',
            'cf_chl_',
            'cloudflare',
            'just a moment',
            'challenge-platform',
            'turnstile',
        ]
        content_lower = content.lower()
        return any(ind in content_lower for ind in indicators)
    
    async def _solve_turnstile(self, page) -> bool:
        """Solve Cloudflare Turnstile widget"""
        try:
            logger.info("Attempting Turnstile bypass...")
            
            # Find Turnstile iframe
            frames = page.frames
            for frame in frames:
                try:
                    # Look for checkbox
                    checkbox = await frame.query_selector('input[type="checkbox"]')
                    if checkbox:
                        await CaptchaAvoider.human_like_delay(500, 1000)
                        await checkbox.click()
                        await asyncio.sleep(3)
                        
                        # Verify
                        content = await page.content()
                        if not self._is_cloudflare_challenge(content):
                            logger.info("Turnstile challenge passed")
                            return True
                            
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Turnstile error: {e}")
            return False
    
    async def _try_click_challenge(self, page) -> None:
        """Try to click any challenge elements"""
        try:
            selectors = [
                'input[type="checkbox"]',
                '.challenge-button',
                '#challenge-stage',
                'button[type="submit"]',
            ]
            
            for selector in selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        await CaptchaAvoider.human_like_delay(300, 700)
                        await elem.click()
                        await asyncio.sleep(2)
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Challenge click error: {e}")


class CaptchaSolver:
    """
    Main Captcha Solver - Unified interface for all captcha types
    Prioritizes AVOIDANCE over solving
    """
    
    def __init__(self):
        self.enabled = True
        self.avoider = CaptchaAvoider()
        self.image_solver = ImageCaptchaSolver()
        self.recaptcha_solver = RecaptchaSolver()
        self.cloudflare_solver = CloudflareSolver()
        
        # External API keys (optional fallback)
        self.twocaptcha_key = os.environ.get('TWOCAPTCHA_API_KEY', '')
        self.anticaptcha_key = os.environ.get('ANTICAPTCHA_API_KEY', '')
    
    async def solve(
        self,
        captcha_type: str,
        captcha_data: Any = None,
        page: Any = None,
        site_key: str = "",
        url: str = ""
    ) -> Optional[str]:
        """
        Solve captcha using local methods first, then external APIs as fallback
        """
        if not self.enabled:
            return None
        
        logger.info(f"Solving {captcha_type} captcha...")
        
        try:
            if captcha_type == "image":
                return await self.image_solver.solve(captcha_data)
            
            elif captcha_type in ("recaptcha", "recaptcha_v2"):
                return await self.recaptcha_solver.solve_v2(page, site_key)
            
            elif captcha_type == "recaptcha_v3":
                return await self.recaptcha_solver.solve_v3(page, site_key)
            
            elif captcha_type == "cloudflare":
                success = await self.cloudflare_solver.bypass(page)
                return "bypassed" if success else None
            
            elif captcha_type == "hcaptcha":
                # hCaptcha is similar to reCAPTCHA v2
                return await self._solve_hcaptcha(page, site_key)
            
            else:
                logger.warning(f"Unknown captcha type: {captcha_type}")
                return None
                
        except Exception as e:
            logger.error(f"Captcha solving error: {e}")
            return None
    
    async def _solve_hcaptcha(self, page, site_key: str = None) -> Optional[str]:
        """Solve hCaptcha using checkbox strategy"""
        try:
            frames = page.frames
            
            for frame in frames:
                try:
                    # Look for hCaptcha checkbox
                    checkbox = await frame.query_selector('#checkbox')
                    if checkbox:
                        await CaptchaAvoider.human_like_delay(300, 600)
                        await checkbox.click()
                        await asyncio.sleep(2)
                        
                        # Check for token
                        token = await page.evaluate('''
                            () => {
                                const input = document.querySelector('[name="h-captcha-response"]');
                                return input ? input.value : null;
                            }
                        ''')
                        
                        if token:
                            return token
                            
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"hCaptcha error: {e}")
            return None
    
    async def detect_captcha(self, html: str, page: Any = None) -> Optional[Dict[str, Any]]:
        """
        Detect captcha type in page content
        """
        captcha_info = None
        html_lower = html.lower()
        
        # Check for reCAPTCHA
        if "recaptcha" in html_lower or "g-recaptcha" in html:
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            is_v3 = "render=" in html or "recaptcha/api.js?render=" in html
            
            captcha_info = {
                "type": "recaptcha_v3" if is_v3 else "recaptcha_v2",
                "site_key": site_key_match.group(1) if site_key_match else None
            }
        
        # Check for hCaptcha
        elif "hcaptcha" in html_lower or "h-captcha" in html:
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            captcha_info = {
                "type": "hcaptcha",
                "site_key": site_key_match.group(1) if site_key_match else None
            }
        
        # Check for Cloudflare
        elif any(x in html_lower for x in ['cloudflare', 'cf-browser-verification', 'turnstile', 'checking your browser']):
            captcha_info = {
                "type": "cloudflare",
                "site_key": None
            }
        
        # Check for image captcha
        elif re.search(r'captcha.*\.(jpg|png|gif|jpeg)', html_lower):
            captcha_info = {
                "type": "image",
                "site_key": None
            }
        
        if captcha_info:
            logger.info(f"Captcha detected: {captcha_info['type']}")
        
        return captcha_info
    
    async def bypass_cloudflare(self, page) -> bool:
        """Convenience method for Cloudflare bypass"""
        return await self.cloudflare_solver.bypass(page)
    
    @staticmethod
    def get_stealth_scripts() -> str:
        """Get stealth JavaScript for page injection"""
        return CaptchaAvoider.get_stealth_scripts()
    
    @staticmethod
    async def add_stealth_to_page(page) -> None:
        """Add stealth scripts to a Playwright page"""
        await page.add_init_script(CaptchaAvoider.get_stealth_scripts())
    
    @staticmethod
    async def simulate_human(page) -> None:
        """Simulate human behavior on page"""
        await CaptchaAvoider.simulate_human_behavior(page)


# Global captcha solver instance
captcha_solver = CaptchaSolver()
