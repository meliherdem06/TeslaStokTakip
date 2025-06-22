from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup
import sqlite3
import schedule
import threading
import time
from datetime import datetime
import os

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

def get_current_status():
    """Get the most recent status from database"""
    conn = sqlite3.connect('tesla_status.db')
    c = conn.cursor()
    c.execute('SELECT has_order_button, has_availability, timestamp FROM status_history ORDER BY id DESC LIMIT 1')
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'has_order_button': result[0],
            'has_availability': result[1],
            'timestamp': result[2]
        }
    return None

def save_status(has_order_button, has_availability, url):
    """Save status to database"""
    conn = sqlite3.connect('tesla_status.db')
    c = conn.cursor()
    c.execute('INSERT INTO status_history (timestamp, has_order_button, has_availability, url) VALUES (?, ?, ?, ?)',
              (datetime.now().isoformat(), has_order_button, has_availability, url))
    conn.commit()
    conn.close()

def check_tesla_page():
    """Check Tesla page for availability"""
    print(f"Checking Tesla page at {datetime.now()}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for url in TESLA_URLS:
        try:
            print(f"Trying URL: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for order button
            order_button = soup.find('button', string=lambda text: text and 'sipariş' in text.lower()) or \
                          soup.find('button', string=lambda text: text and 'order' in text.lower()) or \
                          soup.find('a', string=lambda text: text and 'sipariş' in text.lower()) or \
                          soup.find('a', string=lambda text: text and 'order' in text.lower())
            
            # Check for availability indicators
            availability_text = soup.find(string=lambda text: text and 'stok' in text.lower()) or \
                               soup.find(string=lambda text: text and 'available' in text.lower()) or \
                               soup.find(string=lambda text: text and 'müsait' in text.lower())
            
            has_order_button = order_button is not None
            has_availability = availability_text is not None
            
            print(f"Content analysis - Order button: {has_order_button}, Availability: {has_availability}")
            
            # Save to database
            save_status(has_order_button, has_availability, url)
            return True
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            continue
    
    print("All Tesla pages failed to load.")
    return False

def background_check():
    """Background task to check Tesla page"""
    while True:
        try:
            check_tesla_page()
        except Exception as e:
            print(f"Error in background check: {e}")
        
        time.sleep(300)  # Check every 5 minutes

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    status = get_current_status()
    if status:
        return jsonify(status)
    return jsonify({'error': 'No status available'})

@app.route('/manual_check', methods=['POST'])
def manual_check():
    """Manual check endpoint"""
    print("Manual check requested")
    success = check_tesla_page()
    status = get_current_status()
    return jsonify({'success': success, 'status': status})

# Initialize database and start background thread
if __name__ == '__main__':
    init_db()
    print("Database initialized")
    
    # Start background thread
    background_thread = threading.Thread(target=background_check, daemon=True)
    background_thread.start()
    
    port = int(os.environ.get('PORT', 5001))
    print(f"TeslaStokTakip starting on port {port}")
    print(f"Tesla URLs: {TESLA_URLS}")
    
    app.run(host='0.0.0.0', port=port, debug=False) 