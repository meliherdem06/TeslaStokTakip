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

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tesla-stok-takip-secret-key'

# SocketIO setup - NO eventlet, use default
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
    
    # Try only the first URL to avoid complexity
    url = TESLA_URLS[0]
    
    try:
        print(f"Trying URL: {url}")
        
        # Simple request without session
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
            "has_order_button": has_order_button,
            "has_availability": has_availability
        }
        
        # Check if status changed
        if new_status != last_status:
            print(f"Status changed from {last_status} to {new_status}")
            last_status = new_status
            last_check_time = datetime.now()
            consecutive_failures = 0
            return new_status
        else:
            print(f"Status unchanged: {new_status}")
            last_check_time = datetime.now()
            consecutive_failures = 0
            return None
            
    except Exception as e:
        consecutive_failures += 1
        last_failure_time = datetime.now()
        print(f"Connection error in check_for_changes: {e}")
        raise

def get_last_known_status_from_db():
    """Get the last known status from database"""
    try:
        conn = sqlite3.connect('tesla_stok_takip.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT has_order_button, has_availability, timestamp 
            FROM page_snapshots 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "has_order_button": result[0],
                "has_availability": result[1],
                "last_check": result[2]
            }
        return None
    except Exception as e:
        print(f"Error getting last status from DB: {e}")
        return None

def check_for_changes():
    """Background job to check for changes"""
    try:
        result = perform_check()
        if result:
            # Emit to all connected clients
            socketio.emit('status_update', result)
            print(f"Status update sent to clients: {result}")
    except Exception as e:
        print(f"Error in background check: {e}")
        # Emit error to clients
        socketio.emit('error', {"message": str(e)})

# Initialize database
init_db()

# Setup scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_for_changes, trigger="interval", minutes=5)
scheduler.start()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current status"""
    global last_status, last_check_time
    
    # If we have no status, try to get from database
    if last_status["has_order_button"] is None:
        db_status = get_last_known_status_from_db()
        if db_status:
            last_status = {
                "has_order_button": db_status["has_order_button"],
                "has_availability": db_status["has_availability"]
            }
    
    return jsonify({
        "status": last_status,
        "last_check": last_check_time.isoformat() if last_check_time else None
    })

@app.route('/api/history')
def get_history():
    """Get history of checks"""
    try:
        conn = sqlite3.connect('tesla_stok_takip.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, has_order_button, has_availability, content_length
            FROM page_snapshots 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')
        results = cursor.fetchall()
        conn.close()
        
        history = []
        for row in results:
            history.append({
                "timestamp": row[0],
                "has_order_button": row[1],
                "has_availability": row[2],
                "content_length": row[3]
            })
        
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/manual_check', methods=['POST'])
def manual_check():
    """Manual check endpoint"""
    print("Manual check requested")
    try:
        result = perform_check()
        if result:
            socketio.emit('status_update', result)
            return jsonify({"success": True, "status": result})
        else:
            return jsonify({"success": True, "message": "No changes detected"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# SocketIO events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    # Send current status immediately
    if last_status["has_order_button"] is not None:
        socketio.emit('status_update', last_status, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

# Get port from environment or use default
port = int(os.environ.get('PORT', 5001))

if __name__ == '__main__':
    print(f"TeslaStokTakip starting on port {port}")
    print(f"Tesla URLs: {TESLA_URLS}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False) 