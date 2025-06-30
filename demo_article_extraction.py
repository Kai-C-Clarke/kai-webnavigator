#!/usr/bin/env python3
"""
demo_article_extraction.py

Demo script to test BBC article extraction capabilities.
Shows how to extract and display article content and metadata.
"""

import asyncio
import json
from pathlib import Path
from article_extractor import ArticleExtractor, ArticleData

# Demo BBC article URLs for testing
DEMO_ARTICLES = [
    "https://www.bbc.co.uk/news",  # Will need to pick a specific article
    # Add more URLs here for testing
]

def print_article_summary(article: ArticleData):
    """Print a nicely formatted article summary."""
    
    print("\n" + "="*80)
    print("📰 ARTICLE EXTRACTION RESULTS")
    print("="*80)
    
    print(f"🔗 URL: {article.url}")
    
    if article.headline:
        print(f"📰 HEADLINE: {article.headline}")
    
    if article.author:
        print(f"✍️  AUTHOR: {article.author}")
    
    if article.timestamp:
        print(f"🕐 PUBLISHED: {article.timestamp}")
    
    if article.category:
        print(f"🏷️  CATEGORY: {article.category}")
    
    if article.summary:
        print(f"\n📝 SUMMARY:")
        print(f"   {article.summary}")
    
    if article.content:
        print(f"\n📄 CONTENT ({article.word_count} words):")
        # Show first 500 characters of content
        content_preview = article.content[:500]
        if len(article.content) > 500:
            content_preview += "..."
        print(f"   {content_preview}")
    
    if article.image_url:
        print(f"\n🖼️  IMAGE: {article.image_url}")
        if article.image_caption:
            print(f"   Caption: {article.image_caption}")
    
    print(f"\n📊 EXTRACTION STATS:")
    print(f"   • Word count: {article.word_count}")
    print(f"   • Extracted at: {article.extraction_time}")
    
    print("="*80)

async def demo_single_article(extractor: ArticleExtractor, url: str):
    """Extract and display a single article."""
    
    print(f"\n🚀 Testing article extraction...")
    print(f"📰 Target URL: {url}")
    
    try:
        # Extract the article
        article = await extractor.extract_article(url)
        
        # Display results
        print_article_summary(article)
        
        # Save to JSON for inspection
        output_file = Path("extracted_articles") / f"article_{len(url)}.json"
        extractor.save_article_json(article, output_file)
        
        return article
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return None

async def interactive_demo():
    """Interactive demo where user can input article URLs."""
    
    print("🚀 Kai WebNavigator - Article Extraction Demo")
    print("=" * 60)
    
    # Initialize extractor
    intents_file = Path(__file__).parent / "intents.json"
    if not intents_file.exists():
        print(f"❌ intents.json not found at: {intents_file}")
        return
    
    extractor = ArticleExtractor(intents_file, headless=False)  # Show browser for demo
    
    while True:
        print(f"\n📰 Article Extraction Options:")
        print(f"1. Extract from BBC News URL")
        print(f"2. Extract from any news URL") 
        print(f"3. Test with demo BBC article")
        print(f"4. Exit")
        
        choice = input(f"\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            url = input(f"Enter BBC article URL: ").strip()
            if url:
                await demo_single_article(extractor, url)
            
        elif choice == "2":
            url = input(f"Enter any news article URL: ").strip()
            if url:
                await demo_single_article(extractor, url)
                
        elif choice == "3":
            # For demo purposes - you'll need to replace with a real BBC article URL
            demo_url = "https://www.bbc.co.uk/news/technology"  # Replace with specific article
            print(f"⚠️  Please replace demo_url with a real BBC article URL first!")
            print(f"Current demo URL: {demo_url}")
            
            proceed = input(f"Continue with demo URL? (y/n): ").strip().lower()
            if proceed == 'y':
                await demo_single_article(extractor, demo_url)
                
        elif choice == "4":
            print(f"👋 Goodbye!")
            break
            
        else:
            print(f"❌ Invalid choice. Please try again.")

def batch_demo():
    """Demo script for batch processing multiple articles."""
    
    print("🚀 Batch Article Extraction Demo")
    print("=" * 50)
    
    # Example usage for batch processing
    urls = [
        # Add real BBC article URLs here for testing
        "https://www.bbc.co.uk/news/example-1",
        "https://www.bbc.co.uk/news/example-2",
    ]
    
    print(f"📰 Add real article URLs to the batch_demo() function to test!")
    print(f"Current URLs: {urls}")

async def quick_test():
    """Quick test with a single article - modify URL as needed."""
    
    # ⚠️ REPLACE WITH REAL BBC ARTICLE URL
    test_url = "https://www.bbc.co.uk/news"  
    
    print(f"🧪 Quick Test - Article Extraction")
    print(f"⚠️  Please update test_url with a real BBC article URL")
    print(f"Current URL: {test_url}")
    
    intents_file = Path(__file__).parent / "intents.json"
    extractor = ArticleExtractor(intents_file, headless=False)
    
    # Extract article
    article = await extractor.extract_article(test_url)
    print_article_summary(article)

if __name__ == "__main__":
    print("📰 Kai WebNavigator - Article Extraction System")
    print("=" * 60)
    print("Choose demo mode:")
    print("1. Interactive demo (recommended)")
    print("2. Quick test")
    print("3. Batch processing info")
    
    mode = input("Enter choice (1-3): ").strip()
    
    if mode == "1":
        asyncio.run(interactive_demo())
    elif mode == "2":
        asyncio.run(quick_test())
    elif mode == "3":
        batch_demo()
    else:
        print("Running interactive demo by default...")
        asyncio.run(interactive_demo())