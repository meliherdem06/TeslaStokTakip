import os
import sqlite3
import hashlib
import requests
import urllib3
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
import warnings
import random

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tesla-stok-takip-secret-key'

# SocketIO setup
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Global variables
last_check_time = None
last_status = {"has_order_button": None, "has_availability": None}
last_failure_time = None
consecutive_failures = 0
MAX_CONSECUTIVE_FAILURES = 3
FAILURE_COOLDOWN_MINUTES = 15

# Tesla URLs to try
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
    """Fetch Tesla Model Y page content with requests."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    print(f"Trying Tesla URLs with requests...")
    url = TESLA_URLS[0]
    try:
        print(f"Trying URL: {url}")
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True, verify=False)
        response.raise_for_status()
        print(f"Page fetched successfully from {url}")
        return response.text
    except Exception as e:
        print(f"Failed to fetch {url}. Error: {e}")
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
    """Perform the actual check. Returns a status dict if changed, None if no change, and raises exception on error."""
    global last_check_time, last_status, last_failure_time, consecutive_failures
    
    print(f"Checking Tesla page at {datetime.now()}")
    
    # Check if we're in cooldown period
    if last_failure_time and datetime.now() - last_failure_time < timedelta(minutes=FAILURE_COOLDOWN_MINUTES):
        print(f"Tesla sayfasına bağlanılamıyor. Son hata: {last_failure_time}")
        raise ConnectionError("Tesla sayfasına bağlanılamıyor. Lütfen daha sonra tekrar deneyin.")
    
    try:
        content = get_page_content()
        
        if not content:
            raise ConnectionError("Could not fetch content from Tesla page")

        has_order_button, has_availability = analyze_content(content)
        
        save_snapshot(content, has_order_button, has_availability)
        
        new_status = {
            'has_order_button': has_order_button,
            'has_availability': has_availability
        }
        
        last_check_time = datetime.now()
        consecutive_failures = 0  # Reset failure counter on success
        
        if last_status['has_order_button'] != new_status['has_order_button'] or last_status['has_availability'] != new_status['has_availability']:
            print(f"Status changed from {last_status} to {new_status}")
            last_status = new_status
            return last_status 
        else:
            print(f"Status unchanged: {last_status}")
            return None
            
    except ConnectionError as e:
        print(f"Connection error in perform_check: {e}")
        last_failure_time = datetime.now()
        consecutive_failures += 1
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            print(f"Tesla sayfasına bağlanılamıyor. Çok sayıda ardışık bağlantı hatası. Lütfen daha sonra tekrar deneyin.")
        raise e
    except Exception as e:
        print(f"Error in perform_check: {e}")
        last_failure_time = datetime.now()
        consecutive_failures += 1
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            print(f"Tesla sayfasına bağlanılamıyor. Çok sayıda ardışık bağlantı hatası. Lütfen daha sonra tekrar deneyin.")
        raise e

def get_last_known_status_from_db():
    """Fetches the most recent successful snapshot from the database."""
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
        timestamp, has_order, has_avail = result
        return {
            'last_check_time': timestamp,
            'has_order_button': has_order,
            'has_availability': has_avail
        }
    return None

def check_for_changes():
    """Main monitoring function. Emits status via WebSocket."""
    try:
        new_status = perform_check()
        if new_status:
            socketio.emit('status_update', {
                'message': 'Tesla Model Y durumunda değişiklik tespit edildi!',
                'last_check_time': last_check_time.isoformat(),
                **new_status
            })
        else:
            socketio.emit('check_complete', {
                'message': 'Kontrol tamamlandı - Değişiklik yok.',
                'last_check_time': last_check_time.isoformat(),
                **last_status
            })
    except ConnectionError as e:
        print(f"Connection error in check_for_changes: {e}")
        last_known = get_last_known_status_from_db()
        if last_known:
            socketio.emit('status_update', {
                'message': f"Yeni veri alınamıyor. Son başarılı kontrol: {last_known['last_check_time']}",
                **last_known
            })
        else:
            socketio.emit('status_update', {'message': 'Tesla sayfasına bağlanılamıyor ve veritabanında eski kayıt bulunamadı.'})
    except Exception as e:
        print(f"Error in check_for_changes: {e}")
        socketio.emit('status_update', {
            'message': f'Kontrol sırasında bir hata oluştu: {e}',
            'last_check_time': datetime.now().isoformat(),
            'has_order_button': None,
            'has_availability': None
        })

# Initialize database
init_db()

# Setup scheduler for periodic checks
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_for_changes, trigger="interval", minutes=5)
scheduler.start()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current status for initial page load"""
    return jsonify({
        'last_check_time': last_check_time.isoformat() if last_check_time else None,
        **last_status
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
    """Manual check endpoint."""
    try:
        print("Manual check requested")
        new_status = perform_check()
        
        if new_status:
            socketio.emit('status_update', {
                'message': 'Manuel kontrol sonucu durum değişti!',
                'last_check_time': last_check_time.isoformat(),
                **new_status
            })
            return jsonify({'success': True, 'message': 'Manuel kontrol tamamlandı, durum değişti.', **new_status})
        else:
            socketio.emit('check_complete', {
                'message': 'Manuel kontrol tamamlandı - Değişiklik yok.',
                'last_check_time': last_check_time.isoformat() if last_check_time else datetime.now().isoformat(),
                **last_status
            })
            return jsonify({'success': True, 'message': 'Manuel kontrol tamamlandı, değişiklik yok.', **last_status})
            
    except ConnectionError as e:
        print(f"Connection error in manual_check: {e}")
        last_known = get_last_known_status_from_db()
        if last_known:
             socketio.emit('status_update', {
                'message': f"Yeni veri alınamıyor. Son başarılı kontrol: {last_known['last_check_time']}",
                **last_known
            })
             return jsonify({'success': False, 'message': 'Tesla sayfasına bağlanılamıyor. Son bilinen durum gösteriliyor.'}), 503
        else:
            return jsonify({'success': False, 'message': 'Tesla sayfasına bağlanılamıyor ve veritabanında eski kayıt bulunamadı.'}), 503
    except Exception as e:
        print(f"Error in manual check: {e}")
        return jsonify({'success': False, 'message': f'Manuel kontrol hatası: {str(e)}'}), 500

@socketio.on('connect')
def handle_connect():
    """Send initial status to a newly connected client."""
    print('Client connected. Sending initial status.')
    # Perform an initial check for the new client in a background task
    socketio.start_background_task(check_for_changes)

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