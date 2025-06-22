from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import hashlib
import time
from datetime import datetime
import threading
import os
import urllib3
import random

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tesla_stok_takip_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Tesla Model Y URL - Try different URLs if one fails
TESLA_URLS = [
    "https://www.tesla.com/tr_TR/modely/design#overview",
    "https://www.tesla.com/tr_tr/model-y/design",
    "https://www.tesla.com/tr_TR/modely",
    "https://www.tesla.com/tr_tr/modely",
    "https://www.tesla.com/tr_TR/model-y",
    "https://www.tesla.com/tr_tr/modely/design",
    "https://www.tesla.com/tr_TR/model-y/design",
    "https://www.tesla.com/tr_tr/modely/design#overview",
    "https://www.tesla.com/tr_TR/modely/design#overview",
    "https://www.tesla.com/tr_tr/model-y/design#overview"
]

# Test mode - when Tesla website is unreachable
TEST_MODE = False

# Database setup
def init_db():
    """Initialize database with tables"""
    conn = sqlite3.connect('tesla_stok_takip.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS page_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            content_hash TEXT,
            content_length INTEGER,
            has_order_button BOOLEAN,
            has_availability BOOLEAN,
            raw_content TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized")

def get_page_content():
    """Fetch Tesla Model Y page content with improved error handling"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'no-cache'
    }
    
    print(f"Trying Tesla URLs: {TESLA_URLS}")
    
    # Try each URL with different timeouts
    timeouts = [10, 15, 20, 30]
    
    for url in TESLA_URLS:
        for timeout in timeouts:
            try:
                print(f"Trying URL: {url} with timeout: {timeout}s")
                
                # Use session for better connection handling
                session = requests.Session()
                session.headers.update(headers)
                
                response = session.get(url, timeout=timeout, verify=False, allow_redirects=True)
                response.raise_for_status()
                
                print(f"Page fetched successfully from {url}, content length: {len(response.text)}")
                return response.text
                
            except requests.exceptions.Timeout:
                print(f"Timeout error ({timeout}s) while fetching Tesla page from {url}")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error while fetching Tesla page from {url}: {e}")
                continue
            except requests.exceptions.SSLError as e:
                print(f"SSL error while fetching Tesla page from {url}: {e}")
                continue
            except requests.exceptions.HTTPError as e:
                print(f"HTTP error while fetching Tesla page from {url}: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error fetching page from {url}: {e}")
                continue
    
    print("All Tesla pages failed to load after trying all URLs and timeouts")
    return None

def analyze_content(content):
    """Analyze page content for order button and availability"""
    soup = BeautifulSoup(content, 'html.parser')
    
    # Check for order button (common patterns)
    order_indicators = [
        'sipariş ver',
        'order now',
        'rezervasyon',
        'reservation',
        'satın al',
        'buy now',
        'order',
        'sipariş',
        'purchase'
    ]
    
    # Check for availability indicators (positive)
    availability_indicators = [
        'stokta',
        'available',
        'mevcut',
        'in stock',
        'teslim',
        'delivery',
        'hazır',
        'ready'
    ]
    
    # Check for NO availability indicators (negative)
    no_availability_indicators = [
        'güncellemeleri al',
        'get updates',
        'stokta değil',
        'not available',
        'out of stock',
        'bekleme listesi',
        'waitlist',
        'ön sipariş',
        'pre-order',
        'bilgi al',
        'get info'
    ]
    
    page_text = soup.get_text().lower()
    
    # Check for order button
    has_order_button = any(indicator in page_text for indicator in order_indicators)
    
    # Check for availability - prioritize negative indicators
    has_availability = False
    has_no_availability = any(indicator in page_text for indicator in no_availability_indicators)
    
    if has_no_availability:
        has_availability = False
    else:
        has_availability = any(indicator in page_text for indicator in availability_indicators)
    
    # Also check for specific button elements
    buttons = soup.find_all(['button', 'a', 'div'])
    for button in buttons:
        button_text = button.get_text().lower()
        
        # Check for order buttons
        if any(indicator in button_text for indicator in order_indicators):
            has_order_button = True
        
        # Check for availability buttons
        if any(indicator in button_text for indicator in availability_indicators):
            if not has_no_availability:  # Only if no negative indicators found
                has_availability = True
        
        # Check for NO availability buttons (these override positive indicators)
        if any(indicator in button_text for indicator in no_availability_indicators):
            has_availability = False
            has_no_availability = True
    
    print(f"Content analysis - Order button: {has_order_button}, Availability: {has_availability}, No availability indicators: {has_no_availability}")
    
    return has_order_button, has_availability

def save_snapshot(content, has_order_button, has_availability):
    """Save page snapshot to database"""
    content_hash = hashlib.md5(content.encode()).hexdigest()
    content_length = len(content)
    
    conn = sqlite3.connect('tesla_stok_takip.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO page_snapshots (content_hash, content_length, has_order_button, has_availability, raw_content)
        VALUES (?, ?, ?, ?, ?)
    ''', (content_hash, content_length, has_order_button, has_availability, content))
    conn.commit()
    conn.close()
    
    return content_hash

def perform_check():
    """Perform the actual check without WebSocket emissions"""
    global last_check_time, last_status
    
    try:
        print(f"Checking Tesla page at {datetime.now()}")
        
        # Try multiple Tesla URLs
        content = None
        for url in TESLA_URLS:
            try:
                response = requests.get(url, headers=HEADERS, timeout=30, verify=False)
                if response.status_code == 200:
                    content = response.text
                    print(f"Successfully fetched content from {url}")
                    break
                else:
                    print(f"Failed to fetch {url}, status code: {response.status_code}")
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                continue
        
        if not content:
            print("Could not fetch content from any Tesla URL")
            return
        
        # Analyze content
        has_order_button, has_availability = analyze_content(content)
        
        # Determine status
        if has_order_button and has_availability:
            status = "Stock Available"
        elif has_order_button and not has_availability:
            status = "Pre-order Available"
        else:
            status = "No Stock"
        
        # Update last check time
        last_check_time = datetime.now()
        
        # Check if status changed
        if last_status != status:
            print(f"Status changed from '{last_status}' to '{status}'")
            last_status = status
            return status
        else:
            print(f"Status unchanged: {status}")
            return None
            
    except Exception as e:
        print(f"Error in perform_check: {e}")
        return None

def check_for_changes():
    """Main monitoring function with WebSocket notifications and improved error handling"""
    try:
        result = perform_check()
        
        if result is None:
            # Connection failed - notify frontend
            socketio.emit('status_update', {
                'timestamp': datetime.now().isoformat(),
                'status': 'connection_error',
                'message': 'Tesla sayfasına bağlanılamıyor. Ağ bağlantısı kontrol ediliyor...'
            })
            
            # Get last known status to show
            conn = sqlite3.connect('tesla_stok_takip.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, has_order_button, has_availability 
                FROM page_snapshots 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''')
            result = cursor.fetchone()
            conn.close()
            
            if result:
                timestamp, has_order_button, has_availability = result
                socketio.emit('status_update', {
                    'timestamp': datetime.now().isoformat(),
                    'status': 'last_known',
                    'message': f'Son bilinen durum ({timestamp}): Sipariş {"Mevcut" if has_order_button else "Yok"}, Stok {"Mevcut" if has_availability else "Yok"}',
                    'has_order_button': has_order_button,
                    'has_availability': has_availability
                })
            return
        
        # Send WebSocket notifications for successful checks
        if result:
            socketio.emit('status_update', {
                'timestamp': datetime.now().isoformat(),
                'status': result,
                'message': f'Tesla Model Y stok durumu güncellendi!',
                'has_order_button': has_order_button,
                'has_availability': has_availability
            })
            print(f"Status changed: {result}")
        else:
            # No changes but successful check
            socketio.emit('status_update', {
                'timestamp': datetime.now().isoformat(),
                'status': 'no_changes',
                'message': 'Kontrol tamamlandı - Değişiklik yok',
                'has_order_button': has_order_button,
                'has_availability': has_availability
            })
        
    except Exception as e:
        print(f"Error in check_for_changes: {e}")
        # Emit error to frontend
        socketio.emit('status_update', {
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'message': f'Kontrol hatası: {str(e)}'
        })

# Initialize database
init_db()

# Setup scheduler for periodic checks with retry mechanism
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_for_changes, trigger="interval", minutes=5, id="main_check")

# Add a retry job that runs more frequently when there are connection issues
def retry_check():
    """Retry check with shorter interval when main check fails"""
    try:
        result = perform_check()
        if result is not None:
            # If successful, remove the retry job
            try:
                scheduler.remove_job("retry_check")
            except:
                pass
    except Exception as e:
        print(f"Retry check error: {e}")

# Add retry job (will be added/removed dynamically)
scheduler.add_job(func=retry_check, trigger="interval", minutes=1, id="retry_check")
scheduler.start()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current status"""
    return jsonify({
        'last_check_time': last_check_time.isoformat() if last_check_time else None,
        'last_status': last_status
    })

@app.route('/api/history')
def get_history():
    """Get monitoring history"""
    conn = sqlite3.connect('tesla_stok_takip.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, has_order_button, has_availability 
        FROM page_snapshots 
        ORDER BY timestamp DESC 
        LIMIT 50
    ''')
    results = cursor.fetchall()
    conn.close()
    
    history = []
    for row in results:
        timestamp, has_order_button, has_availability = row
        history.append({
            'timestamp': timestamp,
            'has_order_button': has_order_button,
            'has_availability': has_availability
        })
    
    return jsonify(history)

@app.route('/manual_check', methods=['POST'])
def manual_check():
    """Manual check endpoint"""
    try:
        print("Manual check requested")
        
        # Perform the check
        result = perform_check()
        
        if result:
            # Status changed
            socketio.emit('status_update', {
                'timestamp': datetime.now().isoformat(),
                'status': result,
                'message': f'Tesla Model Y stok durumu güncellendi!'
            })
            return jsonify({
                'success': True,
                'message': f'Manuel kontrol tamamlandı - Durum: {result}',
                'status': result
            })
        else:
            # No change
            socketio.emit('manual_check_complete', {
                'status': 'no_changes',
                'message': 'Manuel kontrol tamamlandı - Değişiklik yok'
            })
            return jsonify({
                'success': True,
                'message': 'Manuel kontrol tamamlandı - Değişiklik yok'
            })
            
    except Exception as e:
        print(f"Error in manual check: {e}")
        return jsonify({
            'success': False,
            'message': f'Manuel kontrol hatası: {str(e)}'
        }), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'message': 'Connected to Tesla Stok Takip'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Get port from environment variable (for web deployment)
    port = int(os.environ.get('PORT', 5001))
    
    print(f"TeslaStokTakip starting on port {port}")
    print(f"Tesla URLs: {TESLA_URLS}")
    
    # Start Flask app
    socketio.run(app, debug=False, host='0.0.0.0', port=port, log_output=True) 