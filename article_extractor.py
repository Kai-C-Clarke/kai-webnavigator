"""
article_extractor.py

Extracts article content and metadata from news websites, starting with BBC.
Integrates with Kai_WebNavigator for consent handling and intelligent navigation.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from playwright.async_api import async_playwright

# Import Kai's existing modules
from selector_strategy import SelectorStrategy
from memory_interface import MemoryInterface
from consent_handler import ConsentHandler

@dataclass
class ArticleData:
    """Structured article content and metadata."""
    url: str
    headline: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    timestamp: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    image_caption: Optional[str] = None
    word_count: int = 0
    extraction_time: str = ""
    
    def __post_init__(self):
        self.extraction_time = datetime.utcnow().isoformat() + "Z"
        if self.content and self.content.strip():
            self.word_count = len(self.content.split())
        else:
            self.word_count = 0

class ArticleExtractor:
    """
    Extract articles using Kai_WebNavigator's intelligent navigation system.
    """
    
    def __init__(self, intents_file: Path, headless: bool = True):
        self.intents_file = intents_file
        self.headless = headless
        self.intents = self._load_intents()
        
    def _load_intents(self) -> Dict:
        """Load intents from JSON file."""
        with open(self.intents_file, 'r') as f:
            return json.load(f)
    
    async def extract_article(self, article_url: str) -> ArticleData:
        """
        Extract full article content and metadata from a news URL.
        Uses Kai's consent handling and intelligent navigation.
        """
        
        print(f"📰 Extracting article from: {article_url}")
        
        article_data = ArticleData(url=article_url)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            
            try:
                # Use existing Chrome profile if available (preserves logins)
                try:
                    context = await browser.new_context(
                        user_data_dir="/Users/jonstiles/Library/Application Support/Google/Chrome/Default"
                    )
                    page = await context.new_page()
                    print(f"🏠 Using existing Chrome profile")
                except:
                    page = await browser.new_page()
                    print(f"🌍 Using clean browser session")
                
                # Navigate to article
                await page.goto(article_url)
                print(f"🌐 Navigated to article page")
                
                # Handle consent/popups using Kai's existing system
                await self._handle_consent_and_popups(page, article_url)
                
                # Wait for article content to load
                await self._wait_for_article_content(page)
                
                # Extract article content and metadata
                if self._is_bbc_article(article_url):
                    article_data = await self._extract_bbc_article(page, article_data)
                else:
                    # Future: add other news sources
                    article_data = await self._extract_generic_article(page, article_data)
                
                print(f"✅ Article extraction complete!")
                print(f"📊 Headline: {article_data.headline[:60]}..." if article_data.headline else "📊 No headline found")
                print(f"📊 Content: {article_data.word_count} words")
                
            except Exception as e:
                print(f"❌ Article extraction failed: {e}")
                
            finally:
                await browser.close()
        
        return article_data
    
    async def _handle_consent_and_popups(self, page, url: str):
        """Use Kai's existing consent handling system."""
        
        domain = url.split('/')[2]  # Extract domain
        
        # Initialize Kai's systems
        selector_strategy = SelectorStrategy(page)
        consent_handler = ConsentHandler(page, selector_strategy, self.intents)
        
        # Wait for page stability and handle popups
        await consent_handler.wait_for_stable_page()
        await consent_handler.detect_and_handle_interstitials(domain, "extract_article")
        
        print(f"🛡️ Consent and popups handled")
    
    async def _wait_for_article_content(self, page):
        """Wait for article content to fully load."""
        
        try:
            # Wait for network to be mostly idle
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Wait for main content indicators
            await page.wait_for_function(
                "document.querySelector('article') !== null || " +
                "document.querySelector('[data-component=\"text-block\"]') !== null || " +
                "document.querySelector('.story-body') !== null",
                timeout=5000
            )
            
            # Extra buffer for dynamic content
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"⚠️ Content loading timeout (continuing): {e}")
    
    def _is_bbc_article(self, url: str) -> bool:
        """Check if URL is from BBC."""
        return 'bbc.co.uk' in url or 'bbc.com' in url
    
    async def _extract_bbc_article(self, page, article_data: ArticleData) -> ArticleData:
        """Extract content using BBC-specific selectors."""
        
        print(f"📰 Using BBC extraction strategy")
        
        if "extract_bbc_article" not in self.intents:
            print(f"❌ BBC extraction intent not found")
            return article_data
        
        intent = self.intents["extract_bbc_article"]
        metadata_selectors = intent.get("metadata_selectors", {})
        
        # Extract headline
        headline = await self._safe_extract_text(page, metadata_selectors.get("headline", ""))
        if headline:
            article_data.headline = headline.strip()
        
        # Extract summary/introduction
        summary = await self._safe_extract_text(page, metadata_selectors.get("summary", ""))
        if summary:
            article_data.summary = summary.strip()
        
        # Extract author
        author = await self._safe_extract_text(page, metadata_selectors.get("author", ""))
        if author:
            article_data.author = author.strip()
        
        # Extract timestamp
        timestamp = await self._safe_extract_attribute(page, metadata_selectors.get("timestamp", ""), "datetime")
        if not timestamp:
            timestamp = await self._safe_extract_text(page, metadata_selectors.get("timestamp", ""))
        if timestamp:
            article_data.timestamp = timestamp.strip()
        
        # Extract category/tags
        category = await self._safe_extract_text(page, metadata_selectors.get("category", ""))
        if category:
            article_data.category = category.strip()
        
        # Extract main article content
        content_blocks = await self._extract_article_content_blocks(page, intent)
        if content_blocks:
            article_data.content = self._clean_article_text(content_blocks)
            # Update word count after content is set
            if article_data.content and article_data.content.strip():
                article_data.word_count = len(article_data.content.split())
        
        # Extract image information
        image_url = await self._safe_extract_attribute(page, metadata_selectors.get("image", ""), "src")
        if image_url:
            article_data.image_url = self._resolve_image_url(image_url, article_data.url)
        
        image_caption = await self._safe_extract_text(page, metadata_selectors.get("image_caption", ""))
        if image_caption:
            article_data.image_caption = image_caption.strip()
        
        return article_data
    
    async def _extract_article_content_blocks(self, page, intent: Dict) -> List[str]:
        """Extract main article content using multiple strategies."""
        
        content_blocks = []
        
        # Try primary selector
        try:
            elements = await page.query_selector_all(intent["primary_selector"])
            for element in elements:
                if await element.is_visible():
                    text = await element.text_content()
                    if text and len(text.strip()) > 50:  # Filter out short snippets
                        content_blocks.append(text.strip())
        except Exception as e:
            print(f"⚠️ Primary content selector failed: {e}")
        
        # Try fallback selectors if no content found
        if not content_blocks:
            for fallback in intent.get("fallbacks", []):
                try:
                    if fallback["method"] == "xpath":
                        elements = await page.query_selector_all(f"xpath={fallback['value']}")
                    else:
                        continue  # Skip non-xpath fallbacks for content extraction
                    
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            if text and len(text.strip()) > 50:
                                content_blocks.append(text.strip())
                    
                    if content_blocks:  # Stop if we found content
                        break
                        
                except Exception as e:
                    print(f"⚠️ Fallback selector failed: {e}")
                    continue
        
        return content_blocks
    
    async def _safe_extract_text(self, page, selector: str) -> Optional[str]:
        """Safely extract text content from a selector."""
        if not selector:
            return None
        
        try:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                return await element.text_content()
        except:
            pass
        return None
    
    async def _safe_extract_attribute(self, page, selector: str, attribute: str) -> Optional[str]:
        """Safely extract an attribute value from a selector."""
        if not selector:
            return None
        
        try:
            element = await page.query_selector(selector)
            if element:
                return await element.get_attribute(attribute)
        except:
            pass
        return None
    
    def _clean_article_text(self, content_blocks: List[str]) -> str:
        """Clean and structure article text."""
        
        if not content_blocks:
            return ""
        
        # Join content blocks
        raw_text = "\n\n".join(content_blocks)
        
        # Clean up common issues
        # Remove extra whitespace
        clean_text = re.sub(r'\s+', ' ', raw_text)
        
        # Remove common BBC artifacts
        clean_text = re.sub(r'Share this with.*?Copy this link', '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'Read more.*?Related Topics', '', clean_text, flags=re.IGNORECASE)
        
        # Fix paragraph breaks
        clean_text = re.sub(r'\. ([A-Z])', r'.\n\n\1', clean_text)
        
        # Remove excessive newlines
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        
        return clean_text.strip()
    
    def _resolve_image_url(self, image_url: str, base_url: str) -> str:
        """Resolve relative image URLs to absolute URLs."""
        if image_url.startswith('http'):
            return image_url
        elif image_url.startswith('//'):
            return f"https:{image_url}"
        elif image_url.startswith('/'):
            base_domain = '/'.join(base_url.split('/')[:3])
            return f"{base_domain}{image_url}"
        else:
            return image_url
    
    async def _extract_generic_article(self, page, article_data: ArticleData) -> ArticleData:
        """Generic article extraction for non-BBC sites."""
        
        print(f"📰 Using generic extraction strategy")
        
        # Try common article selectors
        generic_selectors = [
            "article",
            "[role='main'] p",
            ".article-content p",
            ".post-content p",
            ".entry-content p"
        ]
        
        content_blocks = []
        for selector in generic_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.text_content()
                        if text and len(text.strip()) > 30:
                            content_blocks.append(text.strip())
                if content_blocks:
                    break
            except:
                continue
        
        if content_blocks:
            article_data.content = self._clean_article_text(content_blocks)
        
        # Try to extract headline
        headline_selectors = ["h1", ".headline", ".article-title", ".post-title"]
        for selector in headline_selectors:
            headline = await self._safe_extract_text(page, selector)
            if headline:
                article_data.headline = headline.strip()
                break
        
        return article_data
    
    def save_article_json(self, article_data: ArticleData, output_path: Path):
        """Save extracted article as JSON file."""
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(article_data), f, indent=2, ensure_ascii=False)
        
        print(f"💾 Article saved to: {output_path}")