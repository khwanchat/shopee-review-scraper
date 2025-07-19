import streamlit as st
import pandas as pd
import os
import time
import threading
import queue
import re
from datetime import datetime
from urllib.parse import urlparse

# Import your scraping modules
from shopee_scraper_engine import run_scraper_for_streamlit

# Configure Streamlit page
st.set_page_config(
    page_title="🛍️ Shopee Review Scraper",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #ee4d2d, #ff6b35);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(238, 77, 45, 0.3);
    }
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #ee4d2d;
        margin: 1rem 0;
    }
    .status-good { background-color: #d4edda; border: 1px solid #c3e6cb; padding: 1rem; border-radius: 8px; }
    .status-warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 1rem; border-radius: 8px; }
    .status-error { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 1rem; border-radius: 8px; }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #ddd;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🛍️ Shopee Review Scraper</h1>
    <p>Extract product reviews with advanced filtering and real-time monitoring</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'scraping_active' not in st.session_state:
    st.session_state.scraping_active = False
if 'progress_queue' not in st.session_state:
    st.session_state.progress_queue = None
if 'url_history' not in st.session_state:
    st.session_state.url_history = []
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = datetime.now()
if 'keep_alive_counter' not in st.session_state:
    st.session_state.keep_alive_counter = 0
if 'auto_refresh_enabled' not in st.session_state:
    st.session_state.auto_refresh_enabled = True

# Utility Functions
def validate_shopee_url(url):
    """Validate if URL is a valid Shopee product URL"""
    try:
        parsed = urlparse(url)
        if 'shopee' not in parsed.netloc.lower():
            return False, "URL must be from Shopee"
        if '/product/' not in url:
            return False, "URL must be a product page"
        return True, "Valid Shopee product URL"
    except:
        return False, "Invalid URL format"

def extract_product_name_from_url(url):
    """Extract product name from Shopee URL for filename"""
    try:
        # Simple extraction from URL path
        parts = url.split('/')
        if len(parts) > 2:
            return parts[-2].replace('-', '_')[:50]  # Limit length
        return "shopee_product"
    except:
        return "shopee_product"

def create_filename(product_name, timestamp):
    """Create a smart filename"""
    clean_name = re.sub(r'[^\w\-_]', '_', product_name)
    return f"{clean_name}_{timestamp}.csv"

# Sidebar Configuration
st.sidebar.header("🔧 Configuration")

# URL Input Section
st.sidebar.subheader("📝 Product URL")
url = st.sidebar.text_input(
    "Shopee Product URL",
    placeholder="https://shopee.sg/product/...",
    help="Paste the full Shopee product URL here"
)

# URL Validation
if url:
    is_valid, message = validate_shopee_url(url)
    if is_valid:
        st.sidebar.markdown(f'<div class="status-good">✅ {message}</div>', unsafe_allow_html=True)
        # Add to history if not already there
        if url not in st.session_state.url_history:
            st.session_state.url_history.insert(0, url)
            st.session_state.url_history = st.session_state.url_history[:5]  # Keep last 5
    else:
        st.sidebar.markdown(f'<div class="status-error">❌ {message}</div>', unsafe_allow_html=True)

# URL History
if st.session_state.url_history:
    st.sidebar.subheader("📚 Recent URLs")
    selected_url = st.sidebar.selectbox(
        "Quick select from history",
        options=[""] + st.session_state.url_history,
        format_func=lambda x: "Select from history..." if x == "" else x.split('/')[-2][:30] + "..."
    )
    if selected_url:
        url = selected_url

# Page Limits Configuration
st.sidebar.subheader("📄 Page Limits per Rating")
col1, col2 = st.sidebar.columns(2)

with col1:
    pages_1_star = st.number_input("1⭐ Pages", min_value=0, max_value=50, value=5, key="pages_1")
    pages_2_star = st.number_input("2⭐ Pages", min_value=0, max_value=50, value=5, key="pages_2")
    pages_3_star = st.number_input("3⭐ Pages", min_value=0, max_value=50, value=5, key="pages_3")

with col2:
    pages_4_star = st.number_input("4⭐ Pages", min_value=0, max_value=50, value=3, key="pages_4")
    pages_5_star = st.number_input("5⭐ Pages", min_value=0, max_value=50, value=3, key="pages_5")

# Advanced Settings
with st.sidebar.expander("⚙️ Advanced Settings"):
    scroll_speed = st.selectbox(
        "Scroll Speed",
        options=["Fast", "Medium", "Slow"],
        index=1,
        help="Faster = quicker but might miss content, Slower = more reliable"
    )
    
    headless_mode = st.checkbox("🕶️ Headless Mode", value=False, help="Run browser in background")
    
    custom_filename = st.text_input(
        "📄 Custom Filename (optional)",
        placeholder="my_reviews",
        help="Leave empty for auto-generated name"
    )

# Export Options
with st.sidebar.expander("📊 Export Options"):
    include_timestamps = st.checkbox("📅 Include Timestamps", value=True)
    clean_text = st.checkbox("🧹 Clean Text", value=True, help="Remove extra spaces and normalize text")
    
# Main Interface
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🎯 Scraping Dashboard")
    
    # URL Preview Section
    if url and validate_shopee_url(url)[0]:
        st.markdown('<div class="feature-card">', unsafe_allow_html=True)
        st.subheader("📦 Product Preview")
        product_name = extract_product_name_from_url(url)
        st.write(f"**Product ID:** {product_name}")
        st.write(f"**URL:** {url}")
        
        # Generate filename preview
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if custom_filename:
            filename = f"{custom_filename}_{timestamp}.csv"
        else:
            filename = create_filename(product_name, timestamp)
        st.write(f"**Output File:** {filename}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick Stats Card
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("📊 Quick Stats")
    
    # Progress Section
    if st.session_state.scraping_active:
        st.subheader("📊 Scraping Progress")
        
        # Progress containers
        progress_container = st.container()
        log_container = st.container()
        
        # Update progress in real-time
        if st.session_state.progress_queue:
            messages = []
            while not st.session_state.progress_queue.empty():
                try:
                    msg_type, message, extra_data = st.session_state.progress_queue.get_nowait()
                    messages.append((msg_type, message, extra_data))
                except:
                    break
            
            if messages:
                for msg_type, message, extra_data in messages[-10:]:  # Show last 10 messages
                    if msg_type == "progress":
                        with progress_container:
                            if isinstance(extra_data, (int, float)) and 0 <= extra_data <= 1:
                                st.progress(extra_data, text=message)
                            else:
                                st.info(message)
                    elif msg_type == "success":
                        st.success(message)
                    elif msg_type == "error":
                        st.error(message)
                    elif msg_type == "warning":
                        st.warning(message)
                    elif msg_type == "complete":
                        st.session_state.scraping_active = False
                        st.balloons()
                        st.success(message)
                    elif msg_type == "data":
                        st.session_state.results_df = extra_data
                
                # Auto-refresh
                time.sleep(2)
                st.rerun()
    
    # Results Section
    if st.session_state.results_df is not None:
        st.header("📈 Scraping Results")
        
        df = st.session_state.results_df
        
        # Summary Metrics
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
        
        with col_metric1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Reviews", len(df))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_metric2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            avg_rating = df['actual_rating'].mean() if 'actual_rating' in df.columns else 0
            st.metric("Average Rating", f"{avg_rating:.1f}⭐")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_metric3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            unique_ratings = df['star_filter'].nunique() if 'star_filter' in df.columns else 0
            st.metric("Ratings Scraped", unique_ratings)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_metric4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            date_range = ""
            if 'date_time' in df.columns and df['date_time'].notna().any():
                min_date = df['date_time'].min()
                max_date = df['date_time'].max()
                date_range = f"{min_date} to {max_date}"
            st.metric("Date Range", date_range[:20] + "..." if len(date_range) > 20 else date_range)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Rating Distribution Chart
        if 'star_filter' in df.columns:
            st.subheader("📊 Rating Distribution")
            rating_counts = df.groupby('star_filter').size()
            st.bar_chart(rating_counts)
        
        # Data Preview
        st.subheader("📋 Data Preview")
        
        # Filters for data preview
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            if 'star_filter' in df.columns:
                selected_ratings = st.multiselect(
                    "Filter by Rating",
                    options=sorted(df['star_filter'].unique()),
                    default=sorted(df['star_filter'].unique())
                )
                df_filtered = df[df['star_filter'].isin(selected_ratings)]
            else:
                df_filtered = df
        
        with col_filter2:
            show_rows = st.slider("Rows to display", 10, 100, 20)
        
        st.dataframe(df_filtered.head(show_rows), use_container_width=True)
        
        # Download Section
        st.subheader("📥 Download Results")
        st.info("💡 Files will download to your browser's Downloads folder")
        
        col_download1, col_download2 = st.columns(2)
        
        with col_download1:
            # Generate filename
            if custom_filename:
                final_filename = f"{custom_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            else:
                product_name = extract_product_name_from_url(url) if url else "shopee_reviews"
                final_filename = create_filename(product_name, datetime.now().strftime('%Y%m%d_%H%M%S'))
            
            # CSV Download
            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=final_filename,
                mime="text/csv",
                use_container_width=True
            )
        
        with col_download2:
            # Excel Download
            excel_filename = final_filename.replace('.csv', '.xlsx')
            
            # Create Excel file in memory
            from io import BytesIO
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Reviews')
            excel_buffer.seek(0)
            
            st.download_button(
                label="📊 Download as Excel",
                data=excel_buffer.read(),
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

with col2:
    st.header("🚀 Control Panel")
    
    # Keep-Alive Status Card
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("💓 App Status")
    
    # Calculate time since last activity
    time_since_activity = datetime.now() - st.session_state.last_activity
    minutes_idle = int(time_since_activity.total_seconds() / 60)
    
    if st.session_state.scraping_active:
        st.write("🔄 **Status:** Actively Scraping")
        st.write("💓 **Heartbeat:** Active")
    elif st.session_state.auto_refresh_enabled:
        st.write("😴 **Status:** Idle (Keep-Alive ON)")
        st.write(f"⏰ **Idle Time:** {minutes_idle} minutes")
        st.write(f"💓 **Heartbeat:** {st.session_state.keep_alive_counter}")
    else:
        st.write("💤 **Status:** Idle (Keep-Alive OFF)")
        st.write(f"⏰ **Idle Time:** {minutes_idle} minutes")
    
    st.write(f"🕐 **Last Activity:** {st.session_state.last_activity.strftime('%H:%M:%S')}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if url and validate_shopee_url(url)[0]:
        total_pages = sum([pages_1_star, pages_2_star, pages_3_star, pages_4_star, pages_5_star])
        estimated_time = total_pages * 30  # Rough estimate: 30 seconds per page
        
        st.write(f"**Total Pages:** {total_pages}")
        st.write(f"**Est. Time:** {estimated_time // 60}m {estimated_time % 60}s")
        st.write(f"**Scroll Speed:** {scroll_speed}")
        st.write(f"**Headless Mode:** {'Yes' if headless_mode else 'No'}")
    else:
        st.write("Enter a valid URL to see stats")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Control Buttons
    if not st.session_state.scraping_active:
        if st.button("🚀 Start Scraping", type="primary", use_container_width=True):
            if not url:
                st.error("Please enter a Shopee product URL")
            elif not validate_shopee_url(url)[0]:
                st.error("Please enter a valid Shopee product URL")
            else:
                # Start scraping
                st.session_state.scraping_active = True
                st.session_state.progress_queue = queue.Queue()
                st.session_state.last_activity = datetime.now()  # Update activity
                
                # Prepare scraping parameters
                rating_limits = {
                    1: pages_1_star if pages_1_star > 0 else None,
                    2: pages_2_star if pages_2_star > 0 else None,
                    3: pages_3_star if pages_3_star > 0 else None,
                    4: pages_4_star if pages_4_star > 0 else None,
                    5: pages_5_star if pages_5_star > 0 else None
                }
                
                # Remove ratings with 0 pages
                rating_limits = {k: v for k, v in rating_limits.items() if v is not None}
                
                scroll_delays = {"Fast": 1, "Medium": 2, "Slow": 3}
                scroll_delay = scroll_delays[scroll_speed]
                
                # Start scraping thread
                def run_scraper():
                    try:
                        result_df = run_scraper_for_streamlit(
                            url=url,
                            rating_limits=rating_limits,
                            progress_queue=st.session_state.progress_queue,
                            headless=headless_mode,
                            scroll_speed=scroll_speed
                        )
                        
                        if result_df is not None:
                            st.session_state.progress_queue.put(("data", "📊 Results ready for download", result_df))
                        else:
                            st.session_state.progress_queue.put(("error", "❌ No reviews were scraped", None))
                        
                    except Exception as e:
                        st.session_state.progress_queue.put(("error", f"❌ Scraping failed: {str(e)}", None))
                        st.session_state.scraping_active = False
                
                thread = threading.Thread(target=run_scraper)
                thread.daemon = True
                thread.start()
                
                st.rerun()
    else:
        if st.button("⏹️ Stop Scraping", type="secondary", use_container_width=True):
            st.session_state.scraping_active = False
            st.session_state.last_activity = datetime.now()  # Update activity
            st.warning("Scraping stopped by user")
    
    # Clear Results
    if st.session_state.results_df is not None:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.results_df = None
            st.session_state.last_activity = datetime.now()  # Update activity
            st.success("Results cleared")
    
    # Sample URLs for testing
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("🔗 Sample URLs")
    st.write("For testing purposes:")
    sample_urls = [
        "https://shopee.sg/product/180958533/13913101975",
        "https://shopee.sg/product/123456789/987654321"
    ]
    
    for i, sample_url in enumerate(sample_urls):
        if st.button(f"Load Sample {i+1}", key=f"sample_{i}"):
            st.session_state.last_activity = datetime.now()  # Update activity
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
col_footer1, col_footer2 = st.columns([2, 1])

with col_footer1:
    st.markdown("🛍️ **Shopee Review Scraper** - Professional grade scraping tool")
    st.caption("⚠️ Use responsibly and respect website terms of service")

with col_footer2:
    if st.session_state.scraping_active:
        st.markdown("🔄 **Status:** Scraping Active")
    elif st.session_state.auto_refresh_enabled:
        st.markdown("💓 **Status:** Keep-Alive ON")
    else:
        st.markdown("💤 **Status:** Keep-Alive OFF")

# Keep-Alive Auto-Refresh Logic
if st.session_state.auto_refresh_enabled:
    time_since_activity = datetime.now() - st.session_state.last_activity
    minutes_since_activity = time_since_activity.total_seconds() / 60
    
    # Auto-refresh every 5 minutes (or user-defined interval) when idle
    refresh_interval_minutes = 5  # You can get this from the sidebar slider if you want
    
    if not st.session_state.scraping_active and minutes_since_activity >= refresh_interval_minutes:
        st.session_state.keep_alive_counter += 1
        st.session_state.last_activity = datetime.now()
        
        # Show subtle keep-alive indicator
        st.info(f"🔄 Auto-refresh #{st.session_state.keep_alive_counter} - Keeping app awake")
        time.sleep(2)
        st.rerun()

# Auto-refresh while scraping (existing logic)
if st.session_state.scraping_active:
    time.sleep(1)
    st.rerun()

# JavaScript keep-alive injection
if st.session_state.auto_refresh_enabled:
    st.markdown("""
    <script>
        // Prevent browser from going to sleep
        setInterval(function() {
            console.log('Keep-alive ping - App is awake');
            // Send a small request to keep connection alive
            fetch(window.location.href, {method: 'HEAD'}).catch(() => {});
        }, 120000); // Every 2 minutes
        
        // Page visibility API to detect tab switching
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                console.log('Tab hidden - maintaining connection');
            } else {
                console.log('Tab visible - app is active');
            }
        });
        
        // Prevent idle timeout
        let idleTimer;
        function resetIdleTimer() {
            clearTimeout(idleTimer);
            idleTimer = setTimeout(() => {
                console.log('Preventing idle timeout');
            }, 300000); // 5 minutes
        }
        
        // Reset timer on user activity
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(function(name) {
            document.addEventListener(name, resetIdleTimer, true);
        });
        
        resetIdleTimer();
    </script>
    """, unsafe_allow_html=True)

# KEEP - at the bottom of the file
if st.session_state.auto_refresh_enabled:
    time_since_activity = datetime.now() - st.session_state.last_activity
    minutes_since_activity = time_since_activity.total_seconds() / 60
    
    # Auto-refresh every 5 minutes when idle
    if not st.session_state.scraping_active and minutes_since_activity >= 5:
        st.session_state.keep_alive_counter += 1
        st.session_state.last_activity = datetime.now()
        st.rerun()
