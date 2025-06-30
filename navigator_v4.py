"""
Kai_WebNavigator v1.4
Main navigation script: loads webpage, parses intent, executes action, and logs reasoning.
Enhanced with memory interface, strategy scoring, and OpenMemory federated learning.
"""

import json
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from selector_strategy import SelectorStrategy
from memory_interface import MemoryInterface
from log_writer import LogWriter
from strategy_scorer import StrategyScorer
from openmemory_sync import OpenMemorySync

# Paths
INTENTS_FILE = Path(__file__).parent / "intents.json"
MEMORY_FILE = Path(__file__).parent / "memory.json"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
LOGS_DIR = Path(__file__).parent / "logs"
STATS_FILE = Path(__file__).parent / "strategy_stats.json"

# OpenMemory Configuration
OPENMEMORY_ENABLED = True  # Toggle federated learning
OPENMEMORY_PATH = Path("/Users/jonstiles/Desktop/Kai_WebNavigator/Kai_OpenMemory")

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
    
    # For testing, you can change this to test different intents
    intent_to_test = "click_gmail"  # Change this to "click_search_bar" for YouTube test
    target_url = "https://google.com"  # Change this to "https://youtube.com" for YouTube test
    
    intent = intents.get(intent_to_test)
    if not intent:
        print(f"❌ No intent found for '{intent_to_test}'")
        return

    # Initialize all systems
    memory = MemoryInterface(MEMORY_FILE)
    log = LogWriter(LOGS_DIR)
    scorer = StrategyScorer(STATS_FILE)
    
    # Initialize OpenMemory sync
    sync = None
    if OPENMEMORY_ENABLED:
        sync = OpenMemorySync(OPENMEMORY_PATH, agent_id="kai")
        print(f"🌐 OpenMemory sync enabled: {OPENMEMORY_PATH}")
    
    domain = extract_domain(target_url)
    intent_name = intent_to_test
    
    # Start logging session
    log.start_session(domain, intent_name)

    async with async_playwright() as p:
        # Use existing Chrome profile to avoid login/consent screens
        browser = await p.chromium.launch(headless=False)
        
        # Try to use existing Chrome profile first (preserves logins/cookies)
        try:
            context = await browser.new_context(
                user_data_dir="/Users/jonstiles/Library/Application Support/Google/Chrome/Default"
            )
            page = await context.new_page()
            print(f"🏠 Using your existing Chrome profile (logins preserved)")
        except Exception as e:
            # Fallback to clean browser if profile access fails
            print(f"⚠️ Chrome profile access failed: {e}")
            print(f"🌍 Using clean browser session")
            page = await browser.new_page()
        
        await page.goto(target_url)

        # Check memory for previously successful strategy
        remembered_strategy = memory.get(domain, intent_name)
        if remembered_strategy:
            print(f"🧠 Found remembered strategy: {remembered_strategy['successful_selector']}")
            log.log_memory_strategy(remembered_strategy['successful_selector'])

        # OpenMemory: Pull and merge remote strategies
        if sync:
            try:
                print(f"🌐 Pulling remote strategies for {domain}...")
                remote_stats = sync.pull_remote_stats(domain)
                if remote_stats:
                    merged_stats = sync.merge_with_local_stats(scorer.stats, remote_stats)
                    scorer.stats = merged_stats
                    log.log_event(f"OpenMemory: Merged remote strategies for {domain}")
                    print(f"🔀 Merged remote knowledge into local strategy database")
                else:
                    log.log_event(f"OpenMemory: No remote strategies found for {domain}")
            except Exception as e:
                print(f"⚠️ OpenMemory sync failed: {e}")
                log.log_event(f"OpenMemory sync error: {str(e)}")

        # Optimize intent fallbacks based on historical performance (now including remote data)
        optimized_intent = scorer.reorder_fallbacks(intent, domain, intent_name)
        log.log_event(f"Strategy reordering applied for {domain}/{intent_name}")

        selector_strategy = SelectorStrategy(page, memory)
        
        try:
            element, strategy = await selector_strategy.find_element_by_intent(optimized_intent, domain, intent_name)
            log.log_attempt(strategy)

            if element:
                print(f"✅ Found element using strategy: {strategy}")
                log.log_success(strategy)
                
                # Record successful strategy in scorer
                scorer.record_result(domain, intent_name, strategy, success=True)
                
                # Store successful strategy in memory
                memory.store(domain, intent_name, strategy)
                print(f"💾 Stored successful strategy '{strategy}' for {domain}")
                
                # OpenMemory: Publish discoveries back to shared repository
                if sync:
                    try:
                        sync.publish_discoveries(scorer.stats, domain)
                        log.log_event(f"OpenMemory: Published discoveries for {domain}")
                        print(f"📤 Shared successful strategies to OpenMemory")
                    except Exception as e:
                        print(f"⚠️ Failed to publish to OpenMemory: {e}")
                        log.log_event(f"OpenMemory publish error: {str(e)}")
                
                await element.click()
                
                # Ensure screenshot directory exists
                SCREENSHOT_DIR.mkdir(exist_ok=True)
                screenshot_path = SCREENSHOT_DIR / f"{intent_name}_result.png"
                await page.screenshot(path=str(screenshot_path))
                print(f"📸 Screenshot saved to {screenshot_path}")
            else:
                print(f"❌ Failed to locate element for '{intent_name}'")
                log.log_failure("Element not found with any strategy")
                
                # Record failure for all attempted strategies
                scorer.record_result(domain, intent_name, "all_strategies", success=False)
        
        except Exception as e:
            print(f"❌ Navigation failed: {str(e)}")
            log.log_failure(e)
            scorer.record_result(domain, intent_name, "navigation_error", success=False)
        
        finally:
            # Save log regardless of success/failure
            log.save(domain, intent_name)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())