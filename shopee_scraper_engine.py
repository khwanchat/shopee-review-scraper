# shopee_scraper_engine.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import pandas as pd
from bs4 import BeautifulSoup
import re
from datetime import datetime

class ShopeeReviewScraper:
    def __init__(self, progress_queue=None, headless=False, scroll_delay=2):
        self.progress_queue = progress_queue
        self.headless = headless
        self.scroll_delay = scroll_delay
        self.driver = None
        
    def log_progress(self, msg_type, message, extra_data=None):
        """Send progress updates to the queue"""
        if self.progress_queue:
            self.progress_queue.put((msg_type, message, extra_data))
        else:
            print(f"[{msg_type.upper()}] {message}")
    
    def setup_driver(self):
        """Initialize the Chrome driver"""
        try:
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.log_progress("success", "✅ Browser initialized successfully")
            return True
            
        except Exception as e:
            self.log_progress("error", f"❌ Failed to initialize browser: {str(e)}")
            return False

def run_scraper_for_streamlit(url, rating_limits, progress_queue, headless=False, scroll_speed="Medium"):
    """
    Fast demo function for Streamlit Cloud
    """
    try:
        progress_queue.put(("progress", "🚀 Initializing demo scraper...", 0.1))
        time.sleep(1)
        
        progress_queue.put(("warning", "⚠️ Note: This is demo mode (Selenium not supported on cloud)", None))
        time.sleep(1)
        
        # Create demo data quickly
        demo_data = []
        total_ratings = len([r for r in rating_limits.values() if r > 0])
        current_rating = 0
        
        for rating in range(1, 6):
            if rating not in rating_limits or rating_limits[rating] == 0:
                continue
                
            current_rating += 1
            base_progress = 0.2 + (current_rating / total_ratings) * 0.6
            
            progress_queue.put(("progress", f"🌟 Generating {rating}-star demo reviews...", base_progress))
            time.sleep(0.5)  # Short delay
            
            max_pages = min(rating_limits[rating], 2)  # Limit to 2 pages for demo
            
            for page in range(1, max_pages + 1):
                progress_queue.put(("progress", f"📄 Demo page {page}/{max_pages} for {rating}⭐", base_progress + 0.1))
                
                # Generate 3-5 demo reviews per page
                for review_num in range(1, 4):  # 3 reviews per page
                    demo_data.append({
                        'star_filter': rating,
                        'actual_rating': rating,
                        'page': page,
                        'date_time': f"2024-{rating:02d}-{page:02d} 1{review_num}:30",
                        'comment': f"Demo review {review_num} for {rating} stars on page {page}. This product meets expectations and delivery was prompt."
                    })
                
                time.sleep(0.3)  # Small delay between pages
        
        progress_queue.put(("progress", "📊 Finalizing demo results...", 0.9))
        time.sleep(0.5)
        
        if demo_data:
            df = pd.DataFrame(demo_data)
            progress_queue.put(("data", "📈 Demo data ready!", df))
            progress_queue.put(("complete", f"🎉 Generated {len(df)} demo reviews in {len(demo_data)//3} pages! (Demo mode)", None))
            return df
        else:
            progress_queue.put(("error", "❌ No demo data generated", None))
            return None
            
    except Exception as e:
        progress_queue.put(("error", f"❌ Demo error: {str(e)}", None))
        return None
