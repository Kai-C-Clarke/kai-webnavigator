#!/usr/bin/env python3
"""
Kai WebNavigator - Caveman Friendly Interface
Just type what you want to do and where!

Usage examples:
  python kai_cli.py
  > What do you want to do? click gmail
  > Where? google.com
  
  python kai_cli.py click search youtube.com
  python kai_cli.py click login github.com
"""

import json
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from selector_strategy import SelectorStrategy
from memory_interface import MemoryInterface
from log_writer import LogWriter
from strategy_scorer import StrategyScorer
from openmemory_sync import OpenMemorySync
from consent_handler import ConsentHandler

# Paths
INTENTS_FILE = Path(__file__).parent / "intents.json"
MEMORY_FILE = Path(__file__).parent / "memory.json"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
LOGS_DIR = Path(__file__).parent / "logs"
STATS_FILE = Path(__file__).parent / "strategy_stats.json"
OPENMEMORY_PATH = Path("/Users/jonstiles/Desktop/Kai_WebNavigator/Kai_OpenMemory")

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def extract_domain(url):
    """Extract domain from URL for memory storage."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return urlparse(url).netloc

def create_intent_from_description(action_description):
    """Convert simple descriptions into intent keys."""
    action_lower = action_description.lower()
    
    # Common action mappings
    if 'gmail' in action_lower:
        return 'click_gmail'
    elif 'search' in action_lower:
        return 'click_search_bar'
    elif 'login' in action_lower or 'sign in' in action_lower:
        return 'click_login'
    elif 'subscribe' in action_lower:
        return 'click_subscribe_button'
    elif 'video' in action_lower:
        return 'click_first_video'
    elif 'menu' in action_lower:
        return 'open_video_menu'
    else:
        # Default to search if we don't recognize it
        return 'click_search_bar'

def get_user_input():
    """Get action and target from user - caveman style!"""
    
    if len(sys.argv) >= 3:
        # Command line arguments provided
        action = sys.argv[1]
        target = sys.argv[2]
        return action, target
    
    print("🤖 Kai WebNavigator - Tell me what to do!")
    print("Examples: 'click gmail', 'click search', 'click login', 'click subscribe'")
    print()
    
    action = input("What do you want to do? ").strip()
    if not action:
        action = "click search"  # Default
    
    target = input("Where? (like google.com, youtube.com): ").strip()
    if not target:
        target = "google.com"  # Default
    
    return action, target

def show_available_intents():
    """Show what actions are available."""
    try:
        intents = load_json(INTENTS_FILE)
        print("\n📋 Available actions:")
        for intent_name in intents.keys():
            print(f"  - {intent_name}")
        print()
    except:
        print("📋 Common actions: click_gmail, click_search_bar, click_login")

async def main():
    print("🚀 Kai WebNavigator - Caveman Edition")
    print("=" * 50)
    
    try:
        action, target = get_user_input()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return
    
    # Convert action to intent
    intent_name = create_intent_from_description(action)
    
    # Ensure URL format
    if not target.startswith(('http://', 'https://')):
        target_url = 'https://' + target
    else:
        target_url = target
    
    domain = extract_domain(target_url)
    
    print(f"\n🎯 Action: {action}")
    print(f"🌐 Target: {target_url}")
    print(f"🔧 Intent: {intent_name}")
    print(f"📍 Domain: {domain}")
    
    # Load intents
    try:
        intents = load_json(INTENTS_FILE)
        intent = intents.get(intent_name)
        
        if not intent:
            print(f"\n❌ Don't know how to '{intent_name}' yet!")
            print("Available actions:")
            show_available_intents()
            
            # Create a basic fallback intent
            intent = {
                "primary_selector": f"text={action}",
                "timeout": 3000,
                "fallbacks": [
                    {"method": "aria-label", "value": action},
                    {"method": "text-contains", "value": action.replace("click ", "")},
                    {"method": "xpath", "value": f"//button[contains(text(),'{action}')]"}
                ]
            }
            print(f"🤖 I'll try my best with a basic strategy...")
            
    except Exception as e:
        print(f"❌ Error loading intents: {e}")
        return
    
    # Initialize all systems
    memory = MemoryInterface(MEMORY_FILE)
    log = LogWriter(LOGS_DIR)
    scorer = StrategyScorer(STATS_FILE)
    sync = OpenMemorySync(OPENMEMORY_PATH, agent_id="kai")
    
    print(f"🧠 Memory loaded, 📊 scorer ready, 🌐 OpenMemory enabled")
    
    # Start logging
    log.start_session(domain, intent_name)
    
    async with async_playwright() as p:
        print(f"\n🌍 Opening browser and navigating to {target_url}...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(target_url)
        
        # Check memory
        remembered_strategy = memory.get(domain, intent_name)
        if remembered_strategy:
            print(f"🧠 I remember this worked before: {remembered_strategy['successful_selector']}")
            log.log_memory_strategy(remembered_strategy['successful_selector'])
        
        # Initialize consent handler
        selector_strategy = SelectorStrategy(page, memory)
        consent_handler = ConsentHandler(page, selector_strategy, intents)
        
        # Wait for page to stabilize and handle any popups
        await consent_handler.wait_for_stable_page()
        
        # Auto-handle consent screens, cookie banners, etc.
        interstitial_handled = await consent_handler.detect_and_handle_interstitials(domain, intent_name)
        if interstitial_handled:
            log.log_event(f"Consent handler: Successfully handled interstitial screen")
            # Wait a bit more after handling interstitials
            await asyncio.sleep(2)
        
        # OpenMemory sync
        try:
            print(f"🌐 Checking if other AIs have learned about {domain}...")
            remote_stats = sync.pull_remote_stats(domain)
            if remote_stats:
                merged_stats = sync.merge_with_local_stats(scorer.stats, remote_stats)
                scorer.stats = merged_stats
                print(f"🔀 Got knowledge from other AIs! Using their experience...")
                log.log_event(f"OpenMemory: Merged remote strategies for {domain}")
            else:
                print(f"🌐 No shared knowledge found for {domain} - I'm on my own!")
                log.log_event(f"OpenMemory: No remote strategies found for {domain}")
        except Exception as e:
            print(f"⚠️ OpenMemory sync failed: {e}")
        
        # Optimize and execute
        optimized_intent = scorer.reorder_fallbacks(intent, domain, intent_name)
        
        try:
            print(f"\n🔍 Looking for something to {action}...")
            element, strategy = await selector_strategy.find_element_by_intent(optimized_intent, domain, intent_name)
            log.log_attempt(strategy)
            
            if element:
                print(f"✅ Found it! Using strategy: {strategy}")
                log.log_success(strategy)
                
                # Record success
                scorer.record_result(domain, intent_name, strategy, success=True)
                memory.store(domain, intent_name, strategy)
                
                # Share knowledge
                try:
                    sync.publish_discoveries(scorer.stats, domain)
                    print(f"📤 Shared my success with other AIs")
                    log.log_event(f"OpenMemory: Published discoveries for {domain}")
                except Exception as e:
                    print(f"⚠️ Couldn't share knowledge: {e}")
                
                # Click it!
                await element.click()
                print(f"🖱️ Clicked! Taking screenshot...")
                
                # Screenshot
                SCREENSHOT_DIR.mkdir(exist_ok=True)
                screenshot_path = SCREENSHOT_DIR / f"{intent_name}_{domain.replace('.', '_')}_result.png"
                await page.screenshot(path=str(screenshot_path))
                print(f"📸 Screenshot saved: {screenshot_path}")
                
                # Wait a moment to see result
                await asyncio.sleep(2)
                
            else:
                print(f"❌ Couldn't find anything to {action} on {domain}")
                print(f"💡 Try a different action or check if the website has changed")
                log.log_failure("Element not found with any strategy")
                scorer.record_result(domain, intent_name, "all_strategies", success=False)
                
        except Exception as e:
            print(f"❌ Something went wrong: {str(e)}")
            log.log_failure(e)
            scorer.record_result(domain, intent_name, "navigation_error", success=False)
        
        finally:
            log.save(domain, intent_name)
            await browser.close()
    
    print(f"\n🏁 Done! Check the logs and screenshots for details.")

if __name__ == "__main__":
    print("Starting Kai WebNavigator...")
    asyncio.run(main())