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
    Simplified function for Streamlit Cloud (no Selenium)
    """
    try:
        progress_queue.put(("progress", "🚀 Initializing scraper...", 0.1))
        time.sleep(2)
        
        progress_queue.put(("warning", "⚠️ Selenium not supported on Streamlit Cloud", None))
        progress_queue.put(("progress", "📊 Generating demo data instead...", 0.5))
        time.sleep(2)
        
        # Create demo data for now
        demo_data = []
        for rating in rating_limits:
            if rating_limits[rating] > 0:
                for page in range(1, min(rating_limits[rating] + 1, 3)):  # Max 2 pages demo
                    for review_num in range(1, 6):  # 5 reviews per page
                        demo_data.append({
                            'star_filter': rating,
                            'actual_rating': rating,
                            'page': page,
                            'date_time': f"2024-{rating:02d}-{review_num:02d} 1{page}:{review_num}0",
                            'comment': f"Demo review {review_num} for {rating} stars - This is sample data since Selenium is not available on Streamlit Cloud."
                        })
        
        if demo_data:
            df = pd.DataFrame(demo_data)
            progress_queue.put(("data", "📈 Demo data generated!", df))
            progress_queue.put(("complete", f"🎉 Generated {len(df)} demo reviews! (Selenium not available on cloud)", None))
            return df
        else:
            progress_queue.put(("error", "❌ No demo data generated", None))
            return None
            
    except Exception as e:
        progress_queue.put(("error", f"❌ Error: {str(e)}", None))
        return None