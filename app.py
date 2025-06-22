from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup
import sqlite3
import threading
import time
from datetime import datetime
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('tesla_status.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS status_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT NOT NULL,
                  has_order_button BOOLEAN,
                  has_availability BOOLEAN,
                  url TEXT)''')
    conn.commit()
    conn.close()

# Tesla URLs to check
TESLA_URLS = [
    'https://www.tesla.com/tr_TR/modely/design#overview',
    'https://www.tesla.com/tr_tr/model-y/design',
    'https://www.tesla.com/tr_TR/modely',
    'https://www.tesla.com/tr_tr/modely',
    'https://www.tesla.com/tr_TR/model-y',
    'https://www.tesla.com/tr_tr/modely/design',
    'https://www.tesla.com/tr_TR/model-y/design',
    'https://www.tesla.com/tr_tr/modely/design#overview',
    'https://www.tesla.com/tr_TR/modely/design#overview',
    'https://www.tesla.com/tr_tr/modely/design#overview'
]

# Global variables
current_status = {'has_order_button': None, 'has_availability': None}
last_check_time = None
driver = None

def setup_selenium():
    """Setup Selenium WebDriver for local use"""
    global driver
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Use webdriver-manager to automatically download and manage ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Selenium WebDriver setup successful")
        return True
    except Exception as e:
        print(f"Selenium setup failed: {e}")
        return False

def fetch_tesla_page_selenium(url):
    """Fetch Tesla page using Selenium"""
    global driver
    try:
        if driver is None:
            if not setup_selenium():
                return None
        
        print(f"Trying URL: {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Get page source
        page_source = driver.page_source
        print(f"Page fetched successfully from {url}")
        return page_source
        
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def analyze_content(html_content, url):
    """Analyze HTML content for order button and availability"""
    if not html_content:
        return False, False
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for order button
    order_button = False
    order_selectors = [
        'button[data-testid="order-button"]',
        'button:contains("Sipariş Ver")',
        'button:contains("Order")',
        'a[href*="order"]',
        '.order-button',
        '[data-testid="order"]'
    ]
    
    for selector in order_selectors:
        if soup.select(selector):
            order_button = True
            break
    
    # Look for availability indicators
    availability = False
    availability_selectors = [
        'text:contains("Stokta")',
        'text:contains("Available")',
        'text:contains("Hemen Teslim")',
        'text:contains("Immediate Delivery")',
        '.availability',
        '[data-testid="availability"]'
    ]
    
    for selector in availability_selectors:
        if soup.find(text=lambda text: text and any(keyword in text.lower() for keyword in ['stokta', 'available', 'hemen teslim', 'immediate delivery'])):
            availability = True
            break
    
    # Check if no availability indicators found (might mean no stock)
    no_availability_indicators = not soup.find(text=lambda text: text and any(keyword in text.lower() for keyword in ['stokta', 'available', 'hemen teslim', 'immediate delivery', 'tükendi', 'out of stock']))
    
    print(f"Content analysis - Order button: {order_button}, Availability: {availability}, No availability indicators: {no_availability_indicators}")
    
    return order_button, availability

def check_for_changes():
    """Check Tesla page for changes"""
    global current_status, last_check_time, driver
    
    print(f"Checking Tesla page at {datetime.now()}")
    
    # Try Selenium first
    print("Trying Tesla URLs with Selenium...")
    for url in TESLA_URLS:
        html_content = fetch_tesla_page_selenium(url)
        if html_content:
            has_order_button, has_availability = analyze_content(html_content, url)
            
            new_status = {
                'has_order_button': has_order_button,
                'has_availability': has_availability
            }
            
            # Check if status changed
            if new_status != current_status:
                print(f"Status changed from {current_status} to {new_status}")
                current_status = new_status
                last_check_time = datetime.now()
                
                # Save to database
                conn = sqlite3.connect('tesla_status.db')
                c = conn.cursor()
                c.execute('''INSERT INTO status_history (timestamp, has_order_button, has_availability, url)
                             VALUES (?, ?, ?, ?)''', 
                         (datetime.now().isoformat(), has_order_button, has_availability, url))
                conn.commit()
                conn.close()
            else:
                print(f"Status unchanged: {current_status}")
            
            return  # Success, exit function
            
    print("All Tesla pages failed to load.")
    print("Connection error in check_for_changes: Could not fetch content from Tesla page")

def background_check():
    """Background thread to check for changes every 5 minutes"""
    while True:
        try:
            check_for_changes()
        except Exception as e:
            print(f"Error in background check: {e}")
        
        time.sleep(300)  # Wait 5 minutes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify({
        'has_order_button': current_status['has_order_button'],
        'has_availability': current_status['has_availability'],
        'last_check': last_check_time.isoformat() if last_check_time else None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/manual_check', methods=['POST'])
def manual_check():
    """Manual check endpoint"""
    print("Manual check requested")
    try:
        check_for_changes()
        return jsonify({
            'success': True,
            'status': current_status,
            'message': 'Manual check completed'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Initialize database
    init_db()
    print("Database initialized")
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5001))
    print(f"TeslaStokTakip starting on port {port}")
    print(f"Tesla URLs: {TESLA_URLS}")
    
    # Start background thread
    background_thread = threading.Thread(target=background_check, daemon=True)
    background_thread.start()
    
    # Run initial check
    check_for_changes()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=port, debug=False) 