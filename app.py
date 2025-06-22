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

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tesla_monitor_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60, ping_interval=25)

# Tesla Model Y URL - Try different URLs if one fails
TESLA_URLS = [
    "https://www.tesla.com/tr_TR/modely/design#overview",
    "https://www.tesla.com/tr_tr/model-y/design",
    "https://www.tesla.com/tr_TR/modely",
    "https://www.tesla.com/tr_tr/modely"
]

# Database setup
def init_db():
    conn = sqlite3.connect('tesla_monitor.db')
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

def get_page_content():
    """Fetch Tesla Model Y page content"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    print(f"Trying Tesla URLs: {TESLA_URLS}")
    
    # Try each URL until one works
    for url in TESLA_URLS:
        try:
            print(f"Trying URL: {url}")
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            
            print(f"Page fetched successfully from {url}, content length: {len(response.text)}")
            return response.text
            
        except requests.exceptions.Timeout:
            print(f"Timeout error while fetching Tesla page from {url}")
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error while fetching Tesla page from {url}: {e}")
            continue
        except requests.exceptions.SSLError as e:
            print(f"SSL error while fetching Tesla page from {url}: {e}")
            continue
        except Exception as e:
            print(f"Error fetching page from {url}: {e}")
            continue
    
    print("All Tesla pages failed to load")
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
        'sipariş'
    ]
    
    # Check for availability indicators
    availability_indicators = [
        'stokta',
        'available',
        'mevcut',
        'in stock',
        'teslim',
        'delivery'
    ]
    
    page_text = soup.get_text().lower()
    
    has_order_button = any(indicator in page_text for indicator in order_indicators)
    has_availability = any(indicator in page_text for indicator in availability_indicators)
    
    # Also check for specific button elements
    buttons = soup.find_all(['button', 'a'])
    for button in buttons:
        button_text = button.get_text().lower()
        if any(indicator in button_text for indicator in order_indicators):
            has_order_button = True
        if any(indicator in button_text for indicator in availability_indicators):
            has_availability = True
    
    return has_order_button, has_availability

def save_snapshot(content, has_order_button, has_availability):
    """Save page snapshot to database"""
    content_hash = hashlib.md5(content.encode()).hexdigest()
    content_length = len(content)
    
    conn = sqlite3.connect('tesla_monitor.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO page_snapshots (content_hash, content_length, has_order_button, has_availability, raw_content)
        VALUES (?, ?, ?, ?, ?)
    ''', (content_hash, content_length, has_order_button, has_availability, content))
    conn.commit()
    conn.close()
    
    return content_hash

def perform_check():
    """Perform the actual Tesla page check without WebSocket emissions"""
    try:
        print(f"Checking Tesla page at {datetime.now()}")
        
        content = get_page_content()
        if not content:
            print("No content received from Tesla page")
            return None
        
        has_order_button, has_availability = analyze_content(content)
        content_hash = save_snapshot(content, has_order_button, has_availability)
        
        # Get previous snapshot for comparison
        conn = sqlite3.connect('tesla_monitor.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT content_hash, has_order_button, has_availability 
            FROM page_snapshots 
            ORDER BY timestamp DESC 
            LIMIT 2
        ''')
        results = cursor.fetchall()
        conn.close()
        
        changes = []
        if len(results) >= 2:
            prev_hash, prev_order, prev_availability = results[1]
            
            # Check for changes
            if content_hash != prev_hash:
                changes.append("Sayfa içeriği değişti")
            
            if has_order_button and not prev_order:
                changes.append("Sipariş butonu eklendi!")
            
            if has_availability and not prev_availability:
                changes.append("Stok durumu değişti!")
        
        print(f"Check completed - Order: {has_order_button}, Availability: {has_availability}")
        
        return {
            'has_order_button': has_order_button,
            'has_availability': has_availability,
            'changes': changes,
            'content_hash': content_hash
        }
        
    except Exception as e:
        print(f"Error in perform_check: {e}")
        return None

def check_for_changes():
    """Main monitoring function with WebSocket notifications"""
    try:
        result = perform_check()
        if result is None:
            return
        
        # Send WebSocket notifications
        if result['changes']:
            change_message = " | ".join(result['changes'])
            
            if "Sipariş butonu eklendi!" in result['changes']:
                socketio.emit('order_available', {
                    'message': 'Tesla Model Y siparişi artık mevcut!',
                    'timestamp': datetime.now().isoformat()
                })
            
            if "Stok durumu değişti!" in result['changes']:
                socketio.emit('stock_change', {
                    'message': 'Tesla Model Y stok durumu güncellendi!',
                    'timestamp': datetime.now().isoformat()
                })
            
            socketio.emit('page_change', {
                'message': change_message,
                'timestamp': datetime.now().isoformat(),
                'has_order_button': result['has_order_button'],
                'has_availability': result['has_availability']
            })
            print(f"Changes detected: {change_message}")
        
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

# Setup scheduler for periodic checks
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_for_changes, trigger="interval", minutes=5)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current monitoring status"""
    conn = sqlite3.connect('tesla_monitor.db')
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
        return jsonify({
            'last_check': timestamp,
            'has_order_button': has_order_button,
            'has_availability': has_availability,
            'monitoring_active': scheduler.running
        })
    
    return jsonify({
        'last_check': None,
        'has_order_button': False,
        'has_availability': False,
        'monitoring_active': scheduler.running
    })

@app.route('/api/history')
def get_history():
    """Get monitoring history"""
    conn = sqlite3.connect('tesla_monitor.db')
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
        history.append({
            'timestamp': row[0],
            'has_order_button': row[1],
            'has_availability': row[2]
        })
    
    return jsonify(history)

@app.route('/api/manual-check', methods=['POST'])
def manual_check():
    """Trigger manual check of Tesla page"""
    try:
        print("Manual check triggered")
        result = perform_check()
        
        if result is None:
            return jsonify({
                'success': False,
                'message': 'Tesla sayfasından veri alınamadı',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Manuel kontrol tamamlandı',
            'timestamp': datetime.now().isoformat(),
            'has_order_button': result['has_order_button'],
            'has_availability': result['has_availability'],
            'changes': result['changes']
        })
    except Exception as e:
        print(f"Manual check error: {e}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'message': 'Connected to Tesla Monitor'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Get port from environment variable (for web deployment)
    port = int(os.environ.get('PORT', 5001))
    
    print(f"Teslat starting on port {port}")
    print(f"Tesla URLs: {TESLA_URLS}")
    
    # Start Flask app
    socketio.run(app, debug=False, host='0.0.0.0', port=port, log_output=True) 