from flask import Flask, render_template, jsonify, request
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
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import subprocess
import random

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
                  url TEXT,
                  source TEXT)''')
    conn.commit()
    conn.close()

# Tesla URLs - using the correct URL provided by user
TESLA_URLS = [
    'https://www.tesla.com/tr_TR/modely/design#overview'
]

# Global variables
current_status = {
    'has_order_button': False,
    'has_availability': False,
    'last_check': None,
    'url': None,
    'source': None
}

last_error_time = None
error_count = 0

def setup_selenium():
    """Setup Selenium WebDriver with proper configuration"""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use system ChromeDriver
        service = Service('/usr/local/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        print(f"Selenium setup failed: {e}")
        return None

def check_tesla_page_selenium(url):
    """Check Tesla page using Selenium"""
    driver = None
    try:
        print(f"Trying URL with Selenium: {url}")
        driver = setup_selenium()
        if not driver:
            return None
            
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        # Navigate to the page
        driver.get(url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Scroll down to load more content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Get page source
        page_source = driver.page_source
        
        # Check for order button
        order_button_selectors = [
            'button[data-testid="order-button"]',
            'button[data-testid="order-now"]',
            'button:contains("Order Now")',
            'button:contains("Sipariş Ver")',
            'a[data-testid="order-button"]',
            'a[data-testid="order-now"]',
            '.order-button',
            '.order-now',
            '[class*="order"]',
            '[class*="Order"]'
        ]
        
        has_order_button = False
        for selector in order_button_selectors:
            try:
                if 'contains' in selector:
                    # Handle text-based selectors
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{selector.split('contains(')[1].split(')')[0]}')]")
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    has_order_button = True
                    break
            except:
                continue
        
        # Check for availability indicators
        availability_selectors = [
            '[data-testid="availability"]',
            '[class*="availability"]',
            '[class*="stock"]',
            '[class*="inventory"]',
            'span:contains("Available")',
            'span:contains("Stokta")',
            'div:contains("Available")',
            'div:contains("Stokta")'
        ]
        
        has_availability = False
        for selector in availability_selectors:
            try:
                if 'contains' in selector:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{selector.split('contains(')[1].split(')')[0]}')]")
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    has_availability = True
                    break
            except:
                continue
        
        print(f"Successfully checked {url}")
        print(f"Order button: {has_order_button}, Availability: {has_availability}")
        
        return {
            'has_order_button': has_order_button,
            'has_availability': has_availability,
            'url': url,
            'source': 'selenium'
        }
        
    except Exception as e:
        print(f"Selenium error for {url}: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def perform_check():
    """Perform a check of Tesla pages"""
    global current_status, last_error_time, error_count
    
    print(f"Checking Tesla page at {datetime.now()}")
    
    # Try Selenium first
    for url in TESLA_URLS:
        result = check_tesla_page_selenium(url)
        if result:
            # Update status if there's a change
            if (result['has_order_button'] != current_status['has_order_button'] or 
                result['has_availability'] != current_status['has_availability']):
                
                current_status = result
                current_status['last_check'] = datetime.now().isoformat()
                
                # Save to database
                conn = sqlite3.connect('tesla_status.db')
                c = conn.cursor()
                c.execute('''INSERT INTO status_history 
                             (timestamp, has_order_button, has_availability, url, source)
                             VALUES (?, ?, ?, ?, ?)''',
                         (current_status['last_check'], 
                          current_status['has_order_button'],
                          current_status['has_availability'],
                          current_status['url'],
                          current_status['source']))
                conn.commit()
                conn.close()
                
                print(f"Status changed: {current_status}")
                return current_status
            else:
                # Update timestamp even if no change
                current_status['last_check'] = datetime.now().isoformat()
                current_status['url'] = result['url']
                current_status['source'] = result['source']
                print(f"Status unchanged: {current_status}")
                return current_status
    
    # If all URLs failed
    print("All Tesla pages failed to load.")
    last_error_time = datetime.now()
    error_count += 1
    return None

def background_check():
    """Background thread to check Tesla pages periodically"""
    while True:
        try:
            perform_check()
        except Exception as e:
            print(f"Error in background check: {e}")
        time.sleep(300)  # Check every 5 minutes

# Initialize database
init_db()

# Start background thread
background_thread = threading.Thread(target=background_check, daemon=True)
background_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify(current_status)

@app.route('/manual_check', methods=['POST'])
def manual_check():
    print("Manual check requested")
    result = perform_check()
    if result:
        return jsonify({'success': True, 'status': result})
    else:
        return jsonify({'success': False, 'error': 'Could not fetch Tesla data'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"TeslaStokTakip starting on port {port}")
    print(f"Tesla URLs: {TESLA_URLS}")
    app.run(host='0.0.0.0', port=port, debug=False) 