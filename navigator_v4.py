"""
Kai_WebNavigator v1
Main navigation script: loads webpage, parses intent, executes action, and logs reasoning.
Enhanced with memory interface for storing successful selector strategies.
"""

import json
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from selector_strategy import SelectorStrategy
from memory_interface import MemoryInterface
from log_writer import LogWriter

# Paths
INTENTS_FILE = Path(__file__).parent / "intents.json"
MEMORY_FILE = Path(__file__).parent / "memory.json"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
LOGS_DIR = Path(__file__).parent / "logs"

# Utility to load JSON
def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def extract_domain(url):
    """Extract domain from URL for memory storage."""
    return urlparse(url).netloc

# Main navigator function
async def main():
    intents = load_json(INTENTS_FILE)
    intent = intents.get("click_gmail")
    if not intent:
        print("❌ No intent found for 'click_gmail'")
        return

    # Initialize memory interface and logging
    memory = MemoryInterface(MEMORY_FILE)
    log = LogWriter(LOGS_DIR)
    target_url = "https://google.com"
    domain = extract_domain(target_url)
    intent_name = "click_gmail"
    
    # Start logging session
    log.start_session(domain, intent_name)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(target_url)

        # Check memory for previously successful strategy
        remembered_strategy = memory.get(domain, intent_name)
        if remembered_strategy:
            print(f"🧠 Found remembered strategy: {remembered_strategy['successful_selector']}")
            log.log_memory_strategy(remembered_strategy['successful_selector'])

        selector_strategy = SelectorStrategy(page, memory)
        
        try:
            element, strategy = await selector_strategy.find_element_by_intent(intent, domain, intent_name)
            log.log_attempt(strategy)

            if element:
                print(f"✅ Found Gmail using strategy: {strategy}")
                log.log_success(strategy)
                
                # Store successful strategy in memory
                memory.store(domain, intent_name, strategy)
                print(f"💾 Stored successful strategy '{strategy}' for {domain}")
                
                await element.click()
                
                # Ensure screenshot directory exists
                SCREENSHOT_DIR.mkdir(exist_ok=True)
                screenshot_path = SCREENSHOT_DIR / f"{intent_name}_result.png"
                await page.screenshot(path=str(screenshot_path))
                print(f"📸 Screenshot saved to {screenshot_path}")
            else:
                print("❌ Failed to locate Gmail link")
                log.log_failure("Element not found with any strategy")
        
        except Exception as e:
            print(f"❌ Navigation failed: {str(e)}")
            log.log_failure(e)
        
        finally:
            # Save log regardless of success/failure
            log.save(domain, intent_name)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())