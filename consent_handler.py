"""
consent_handler.py

Smart consent and popup handler for Kai_WebNavigator.
Automatically detects and handles cookie banners, age verification, 
login prompts, and other common website interstitials.
Enhanced with BBC-specific handling for complex consent banners.
"""

import asyncio
from typing import Optional, List, Dict

class ConsentHandler:
    def __init__(self, page, selector_strategy, intents):
        self.page = page
        self.selector_strategy = selector_strategy
        self.intents = intents
        
        # Common consent patterns to detect
        self.consent_patterns = [
            "cookies",
            "gdpr", 
            "privacy",
            "accept all",
            "before you continue",
            "we use cookies",
            "consent",
            "terms and conditions"
        ]
        
        # Age verification patterns
        self.age_patterns = [
            "age verification",
            "confirm your age", 
            "are you over",
            "18+",
            "adult content"
        ]
        
        # Login/signup patterns
        self.auth_patterns = [
            "sign in to continue",
            "create account",
            "login required",
            "sign up"
        ]

    async def detect_and_handle_interstitials(self, domain: str, intent_name: str) -> bool:
        """
        Automatically detect and handle common website interstitials.
        Returns True if an interstitial was handled, False otherwise.
        """
        
        print(f"🔍 Checking for popups and consent screens...")
        
        # BBC-specific handling first (they have complex banners)
        if 'bbc.co.uk' in domain or 'bbc.com' in domain:
            if await self._handle_bbc_specific_consent():
                return True
        
        # Wait a moment for page to fully load
        await asyncio.sleep(1)
        
        page_content = await self.page.content()
        page_content_lower = page_content.lower()
        
        # Check for consent/cookie banners
        if any(pattern in page_content_lower for pattern in self.consent_patterns):
            print(f"🍪 Detected cookie/consent banner")
            if await self._handle_consent_banner():
                return True
        
        # Check for age verification
        if any(pattern in page_content_lower for pattern in self.age_patterns):
            print(f"🔞 Detected age verification screen")
            if await self._handle_age_verification():
                return True
        
        # Check for login walls
        if any(pattern in page_content_lower for pattern in self.auth_patterns):
            print(f"🔐 Detected login requirement")
            if await self._handle_login_wall():
                return True
        
        # Check for generic popups/overlays
        if await self._detect_overlay():
            print(f"📱 Detected popup overlay")
            if await self._handle_generic_popup():
                return True
        
        print(f"✅ No interstitials detected, proceeding with main intent")
        return False

    async def _handle_consent_banner(self) -> bool:
        """Handle cookie consent banners."""
        
        # Try to accept cookies first (most permissive)
        if "accept_cookies" in self.intents:
            print(f"🍪 Attempting to accept cookies...")
            try:
                element, strategy = await self.selector_strategy.find_element_by_intent(
                    self.intents["accept_cookies"], "generic", "accept_cookies"
                )
                if element:
                    await element.click()
                    print(f"✅ Accepted cookies using: {strategy}")
                    await asyncio.sleep(1)  # Wait for banner to disappear
                    return True
            except Exception as e:
                print(f"⚠️ Failed to accept cookies: {e}")
        
        # Fallback: try to reject cookies
        if "reject_cookies" in self.intents:
            print(f"🚫 Attempting to reject cookies...")
            try:
                element, strategy = await self.selector_strategy.find_element_by_intent(
                    self.intents["reject_cookies"], "generic", "reject_cookies"
                )
                if element:
                    await element.click()
                    print(f"✅ Rejected cookies using: {strategy}")
                    await asyncio.sleep(1)
                    return True
            except Exception as e:
                print(f"⚠️ Failed to reject cookies: {e}")
        
        return False

    async def _handle_age_verification(self) -> bool:
        """Handle age verification screens."""
        
        # Look for common age verification buttons
        age_selectors = [
            "button:has-text('Yes')",
            "button:has-text('I am over 18')", 
            "button:has-text('Enter')",
            "button:has-text('Continue')",
            "[data-age='yes']"
        ]
        
        for selector in age_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    await element.click()
                    print(f"✅ Passed age verification using: {selector}")
                    await asyncio.sleep(1)
                    return True
            except:
                continue
        
        return False

    async def _handle_login_wall(self) -> bool:
        """Handle login requirement screens."""
        
        # Look for skip/continue without login options first
        skip_selectors = [
            "button:has-text('Skip')",
            "button:has-text('No thanks')",
            "button:has-text('Continue without')",
            "a:has-text('Browse without')",
            "[data-testid='close']"
        ]
        
        for selector in skip_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    await element.click()
                    print(f"✅ Skipped login using: {selector}")
                    await asyncio.sleep(1)
                    return True
            except:
                continue
        
        print(f"ℹ️ Login required but no skip option found")
        return False

    async def _detect_overlay(self) -> bool:
        """Detect if there's a modal overlay blocking interaction."""
        
        overlay_selectors = [
            "[role='dialog']",
            ".modal",
            ".overlay", 
            ".popup",
            "[data-testid='modal']",
            ".cookie-banner"
        ]
        
        for selector in overlay_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    is_visible = await element.is_visible()
                    if is_visible:
                        return True
            except:
                continue
        
        return False

    async def _handle_generic_popup(self) -> bool:
        """Handle generic popups using close button."""
        
        if "close_popup" in self.intents:
            try:
                element, strategy = await self.selector_strategy.find_element_by_intent(
                    self.intents["close_popup"], "generic", "close_popup"
                )
                if element:
                    await element.click()
                    print(f"✅ Closed popup using: {strategy}")
                    await asyncio.sleep(1)
                    return True
            except Exception as e:
                print(f"⚠️ Failed to close popup: {e}")
        
        return False

    async def wait_for_stable_page(self, timeout: int = 5000):
        """Wait for page to become stable (no more popups loading)."""
        
        print(f"⏱️ Waiting for page to stabilize...")
        
        try:
            # Wait for network to be mostly idle
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            
            # Additional wait for any delayed popups
            await asyncio.sleep(2)
            
            print(f"✅ Page appears stable")
            return True
            
        except Exception as e:
            print(f"⚠️ Page stabilization timeout: {e}")
            return False

    async def _handle_bbc_specific_consent(self) -> bool:
        """
        BBC-specific consent handler with multiple fallback strategies.
        Returns True if consent was handled, False otherwise.
        """
        
        print(f"🍪 BBC-specific consent handler activated")
        
        # BBC-specific selectors (ordered by reliability)
        bbc_selectors = [
            # Most specific BBC selectors first
            {
                "name": "bbc_primary_accept",
                "selector": "button[data-testid='banner-accept-all']",
                "timeout": 3000
            },
            {
                "name": "bbc_cta_accept", 
                "selector": "button[class*='gel-cta'][class*='gel-cta--primary']",
                "timeout": 3000
            },
            {
                "name": "bbc_consent_form",
                "selector": "form[id*='consent'] button[type='submit']",
                "timeout": 3000
            },
            # Generic but BBC-context selectors
            {
                "name": "bbc_text_accept_all",
                "selector": "button:has-text('Accept all')",
                "timeout": 3000
            },
            {
                "name": "bbc_text_agree",
                "selector": "button:has-text('I Agree')",
                "timeout": 3000
            },
            {
                "name": "bbc_text_continue",
                "selector": "button:has-text('Continue')",
                "timeout": 3000
            },
            # XPath fallbacks for complex scenarios
            {
                "name": "bbc_xpath_accept",
                "selector": "xpath=//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
                "timeout": 3000
            }
        ]
        
        # Wait for BBC page to stabilize (they load consent async)
        await self._wait_for_bbc_stability()
        
        # Detect if BBC consent banner is present
        if not await self._detect_bbc_consent_banner():
            print(f"🍪 No BBC consent banner detected")
            return False
        
        print(f"🍪 BBC consent banner detected - attempting automation")
        
        # First try the dedicated BBC intent if available
        if "accept_cookies_bbc" in self.intents:
            print(f"🎯 Using dedicated BBC cookie intent")
            try:
                element, strategy = await self.selector_strategy.find_element_by_intent(
                    self.intents["accept_cookies_bbc"], "bbc.co.uk", "accept_cookies_bbc"
                )
                if element:
                    await element.click()
                    print(f"✅ BBC consent handled using dedicated intent: {strategy}")
                    await asyncio.sleep(2)
                    return True
            except Exception as e:
                print(f"⚠️ BBC dedicated intent failed: {e}")
        
        # Try each BBC selector strategy as fallback
        for strategy in bbc_selectors:
            if await self._try_bbc_consent_strategy(strategy):
                await asyncio.sleep(2)  # Wait for banner to disappear
                print(f"✅ BBC consent successfully handled")
                return True
        
        # If all specific selectors fail, try smart detection
        if await self._bbc_smart_button_detection():
            await asyncio.sleep(2)
            print(f"✅ BBC consent handled via smart detection")
            return True
        
        print(f"❌ All BBC consent strategies failed")
        return False

    async def _wait_for_bbc_stability(self):
        """Wait for BBC page to finish loading dynamic content."""
        try:
            # Wait for network to settle
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            
            # BBC-specific: wait for their consent script to load
            await self.page.wait_for_function(
                "window.bbccookies !== undefined || document.querySelector('[data-testid]') !== null",
                timeout=3000
            )
            
            # Extra buffer for banner animation
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"⚠️ BBC page stability timeout (continuing anyway): {e}")

    async def _detect_bbc_consent_banner(self) -> bool:
        """Detect if BBC consent banner is visible."""
        
        detection_selectors = [
            "[data-testid*='banner']",
            "[class*='cookie']",
            "[class*='consent']", 
            "[id*='privacy']",
            "text=cookies",
            "text=privacy"
        ]
        
        for selector in detection_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        # Additional check: ensure it's actually a consent banner
                        text = await element.text_content()
                        if any(word in text.lower() for word in ['cookie', 'consent', 'privacy', 'accept', 'agree']):
                            return True
            except:
                continue
        
        return False

    async def _try_bbc_consent_strategy(self, strategy: Dict) -> bool:
        """Try a specific BBC consent acceptance strategy with extra safety."""
        
        print(f"🎯 Trying BBC strategy: {strategy['name']}")
        
        try:
            # Safety check: make sure we're not about to click a reject button
            if await self._is_reject_button(strategy['selector']):
                print(f"🚫 Skipping {strategy['name']} - appears to be reject button")
                return False
            
            # Find the element with shorter timeout to avoid hanging
            element = await self.page.wait_for_selector(
                strategy['selector'], 
                timeout=min(strategy['timeout'], 2000)  # Cap timeout at 2 seconds
            )
            
            if not element:
                print(f"⚠️ Element not found: {strategy['name']}")
                return False
                
            if not await element.is_visible():
                print(f"⚠️ Element found but not visible: {strategy['name']}")
                return False
            
            # Get button text for verification (with error handling)
            try:
                button_text = await element.text_content()
                button_text = button_text.strip() if button_text else "Unknown"
            except:
                button_text = "Unknown"
                
            print(f"🔍 Found BBC button: '{button_text}'")
            
            # Final safety check on button text
            if any(word in button_text.lower() for word in ['reject', 'decline', 'manage', 'settings']):
                print(f"🚫 Refusing to click suspicious BBC button: '{button_text}'")
                return False
            
            # Extra safety: check if button is actually clickable
            try:
                is_enabled = await element.is_enabled()
                if not is_enabled:
                    print(f"⚠️ Button found but disabled: {strategy['name']}")
                    return False
            except:
                pass  # Continue if we can't check enabled state
            
            # Click it with error handling!
            try:
                await element.click()
                print(f"✅ Successfully clicked BBC button: {strategy['name']} ('{button_text}')")
                return True
            except Exception as click_error:
                print(f"⚠️ Click failed for {strategy['name']}: {click_error}")
                return False
            
        except Exception as e:
            print(f"⚠️ BBC strategy {strategy['name']} failed gracefully: {str(e)[:100]}...")
            return False

    async def _bbc_smart_button_detection(self) -> bool:
        """Smart detection of BBC accept buttons - stone axe resistant version."""
        
        print(f"🧠 Attempting BBC smart button detection (caveman-safe)...")
        
        try:
            # Find all buttons on the page with timeout protection
            try:
                buttons = await self.page.query_selector_all("button")
            except Exception as e:
                print(f"⚠️ Failed to find buttons: {e}")
                return False
            
            if not buttons:
                print(f"⚠️ No buttons found on page")
                return False
            
            scored_buttons = []
            
            for button in buttons[:20]:  # Limit to first 20 buttons to avoid hanging
                try:
                    if not await button.is_visible():
                        continue
                    
                    # Safe text extraction
                    try:
                        text = await button.text_content()
                        text = text.strip() if text else ""
                    except:
                        continue
                    
                    if not text:  # Skip empty text buttons
                        continue
                        
                    text_lower = text.lower()
                    
                    # Score buttons based on likelihood of being "accept"
                    score = 0
                    
                    # Positive indicators
                    if 'accept' in text_lower: score += 10
                    if 'agree' in text_lower: score += 10
                    if 'continue' in text_lower: score += 5
                    if 'ok' in text_lower: score += 3
                    if 'all' in text_lower: score += 2
                    
                    # Negative indicators
                    if 'reject' in text_lower: score -= 20
                    if 'decline' in text_lower: score -= 20
                    if 'manage' in text_lower: score -= 10
                    if 'settings' in text_lower: score -= 10
                    if 'customize' in text_lower: score -= 10
                    
                    # Button styling clues (safely)
                    try:
                        classes = await button.get_attribute('class') or ''
                        if 'primary' in classes: score += 3
                        if 'cta' in classes: score += 2
                        if 'secondary' in classes: score -= 2
                    except:
                        pass
                    
                    if score > 5:  # Threshold for consideration
                        scored_buttons.append((button, score, text))
                        
                except Exception as button_error:
                    # Skip problematic buttons instead of crashing
                    continue
            
            # Sort by score and try the best candidates
            scored_buttons.sort(key=lambda x: x[1], reverse=True)
            
            for button, score, text in scored_buttons[:3]:  # Try top 3 only
                print(f"🎯 BBC smart detection trying: '{text[:30]}...' (score: {score})")
                try:
                    # Extra safety check before clicking
                    if await button.is_enabled() and await button.is_visible():
                        await button.click()
                        print(f"✅ Smart detection successful!")
                        return True
                except Exception as click_error:
                    print(f"⚠️ Smart click failed: {str(click_error)[:50]}...")
                    continue
            
            print(f"⚠️ Smart detection found no suitable buttons")
            return False
            
        except Exception as e:
            print(f"⚠️ BBC smart detection failed safely: {str(e)[:100]}...")
            return False

    async def _is_reject_button(self, selector: str) -> bool:
        """Check if selector would match a reject/decline button."""
        
        try:
            elements = await self.page.query_selector_all(selector)
            for element in elements:
                text = await element.text_content()
                if any(word in text.lower() for word in ['reject', 'decline', 'manage', 'settings', 'customize']):
                    return True
        except:
            pass
        
        return False