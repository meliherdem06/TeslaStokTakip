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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tesla_monitor_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Tesla Model Y URL
TESLA_URL = "https://www.tesla.com/tr_TR/modely/design#overview"

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
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(TESLA_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching page: {e}")
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

def check_for_changes():
    """Main monitoring function"""
    print(f"Checking Tesla page at {datetime.now()}")
    
    content = get_page_content()
    if not content:
        return
    
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
    
    if len(results) >= 2:
        prev_hash, prev_order, prev_availability = results[1]
        
        # Check for changes
        changes = []
        
        if content_hash != prev_hash:
            changes.append("Sayfa içeriği değişti")
        
        if has_order_button and not prev_order:
            changes.append("Sipariş butonu eklendi!")
            socketio.emit('order_available', {
                'message': 'Tesla Model Y siparişi artık mevcut!',
                'timestamp': datetime.now().isoformat()
            })
        
        if has_availability and not prev_availability:
            changes.append("Stok durumu değişti!")
            socketio.emit('stock_change', {
                'message': 'Tesla Model Y stok durumu güncellendi!',
                'timestamp': datetime.now().isoformat()
            })
        
        if changes:
            change_message = " | ".join(changes)
            socketio.emit('page_change', {
                'message': change_message,
                'timestamp': datetime.now().isoformat(),
                'has_order_button': has_order_button,
                'has_availability': has_availability
            })
            print(f"Changes detected: {change_message}")

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

@app.route('/api/manual-check')
def manual_check():
    """Trigger manual check of Tesla page"""
    try:
        check_for_changes()
        return jsonify({
            'success': True,
            'message': 'Manuel kontrol tamamlandı',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
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
    
    # Start Flask app
    socketio.run(app, debug=False, host='0.0.0.0', port=port) 