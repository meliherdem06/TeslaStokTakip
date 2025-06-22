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
TEST_MODE = True
CURRENT_TEST_SCENARIO = 'no_stock'  # Default scenario

# Database setup
def init_db():
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

def get_test_content():
    """Generate test content when Tesla website is unreachable"""
    global CURRENT_TEST_SCENARIO
    
    # Define test scenarios
    scenarios = {
        'no_stock': {
            'content': '''
            <html>
            <body>
                <h1>Tesla Model Y</h1>
                <p>Şu anda stokta değil</p>
                <div>Bilgi alın</div>
                <span>Stok durumu: Mevcut değil</span>
                <p>Güncellemeleri al</p>
            </body>
            </html>
            ''',
            'has_order': False,
            'has_stock': False,
            'description': 'Stok yok - Sipariş yok (Gerçek durum)'
        },
        'pre_order': {
            'content': '''
            <html>
            <body>
                <h1>Tesla Model Y</h1>
                <p>Ön sipariş</p>
                <div>Rezervasyon yapın</div>
                <span>Stok durumu: Ön sipariş</span>
            </body>
            </html>
            ''',
            'has_order': True,
            'has_stock': False,
            'description': 'Ön sipariş mevcut - Stok yok'
        },
        'stock_available': {
            'content': '''
            <html>
            <body>
                <h1>Tesla Model Y</h1>
                <button>Sipariş Ver</button>
                <p>Stokta mevcut</p>
                <div>Hemen sipariş verin</div>
                <span>Stok durumu: Mevcut</span>
            </body>
            </html>
            ''',
            'has_order': True,
            'has_stock': True,
            'description': 'STOK MEVCUT! - Sipariş mevcut'
        }
    }
    
    # Get the current scenario
    scenario = scenarios.get(CURRENT_TEST_SCENARIO, scenarios['no_stock'])
    
    print(f"Test mode: {scenario['description']}")
    return scenario['content'], scenario['has_order'], scenario['has_stock']

def get_page_content():
    """Fetch Tesla Model Y page content with improved error handling"""
    # If test mode is enabled, return test content
    if TEST_MODE:
        print("Using test mode - generating simulated Tesla page content")
        content, has_order, has_stock = get_test_content()
        return content
    
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
        conn = sqlite3.connect('tesla_stok_takip.db')
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
        if result['changes']:
            change_message = " | ".join(result['changes'])
            
            if "Sipariş butonu eklendi!" in result['changes']:
                socketio.emit('order_available', {
                    'message': '🚗 TESLA MODEL Y SİPARİŞİ MEVCUT! 🚗',
                    'timestamp': datetime.now().isoformat()
                })
            
            if "Stok durumu değişti!" in result['changes']:
                socketio.emit('stock_change', {
                    'message': '📦 Tesla Model Y stok durumu güncellendi!',
                    'timestamp': datetime.now().isoformat()
                })
            
            socketio.emit('page_change', {
                'message': change_message,
                'timestamp': datetime.now().isoformat(),
                'has_order_button': result['has_order_button'],
                'has_availability': result['has_availability']
            })
            print(f"Changes detected: {change_message}")
        else:
            # No changes but successful check
            socketio.emit('status_update', {
                'timestamp': datetime.now().isoformat(),
                'status': 'no_changes',
                'message': 'Kontrol tamamlandı - Değişiklik yok',
                'has_order_button': result['has_order_button'],
                'has_availability': result['has_availability']
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
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current monitoring status"""
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
        history.append({
            'timestamp': row[0],
            'has_order_button': row[1],
            'has_availability': row[2]
        })
    
    return jsonify(history)

@app.route('/api/toggle-test-mode', methods=['POST'])
def toggle_test_mode():
    """Toggle test mode on/off"""
    global TEST_MODE
    try:
        data = request.get_json()
        if data and 'enabled' in data:
            TEST_MODE = data['enabled']
            status = "etkinleştirildi" if TEST_MODE else "devre dışı bırakıldı"
            return jsonify({
                'success': True,
                'message': f'Test modu {status}',
                'test_mode': TEST_MODE,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Geçersiz parametre',
                'timestamp': datetime.now().isoformat()
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/test-mode-status')
def get_test_mode_status():
    """Get current test mode status"""
    return jsonify({
        'test_mode': TEST_MODE,
        'message': 'Test modu etkin' if TEST_MODE else 'Test modu devre dışı'
    })

@app.route('/api/test-scenario', methods=['POST'])
def set_test_scenario():
    """Set specific test scenario for testing"""
    global TEST_MODE, CURRENT_TEST_SCENARIO
    try:
        data = request.get_json()
        if data and 'scenario' in data:
            scenario = data['scenario']
            
            # Force test mode to be enabled
            TEST_MODE = True
            CURRENT_TEST_SCENARIO = scenario
            
            print(f"Test scenario set to: {scenario}")
            
            return jsonify({
                'success': True,
                'message': f'Test senaryosu ayarlandı: {scenario}',
                'test_mode': TEST_MODE,
                'scenario': scenario,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Geçersiz senaryo',
                'timestamp': datetime.now().isoformat()
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/manual-check', methods=['POST'])
def manual_check():
    """Trigger manual check of Tesla page with improved error handling"""
    try:
        print("Manual check triggered")
        
        # Check if we're in test mode
        if TEST_MODE:
            print("Manual check in test mode")
            result = perform_check()
            
            if result is None:
                return jsonify({
                    'success': False,
                    'message': 'Test modunda sayfa içeriği işlenirken hata oluştu',
                    'timestamp': datetime.now().isoformat(),
                    'error_type': 'processing_error'
                }), 500
            
            return jsonify({
                'success': True,
                'message': 'Test modunda manuel kontrol tamamlandı',
                'timestamp': datetime.now().isoformat(),
                'has_order_button': result['has_order_button'],
                'has_availability': result['has_availability'],
                'changes': result['changes'],
                'test_mode': True
            })
        
        # Not in test mode - try to get real Tesla page content
        content = get_page_content()
        
        if not content:
            # Check if we have any previous data to show
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
                return jsonify({
                    'success': False,
                    'message': 'Tesla sayfasına bağlanılamıyor. Son kontrol: ' + timestamp,
                    'timestamp': datetime.now().isoformat(),
                    'last_known_status': {
                        'has_order_button': has_order_button,
                        'has_availability': has_availability,
                        'last_check': timestamp
                    },
                    'error_type': 'connection_timeout'
                }), 503  # Service Unavailable
            else:
                return jsonify({
                    'success': False,
                    'message': 'Tesla sayfasına bağlanılamıyor. Henüz hiç veri toplanmamış.',
                    'timestamp': datetime.now().isoformat(),
                    'error_type': 'connection_timeout'
                }), 503
        
        # If we got content, process it
        result = perform_check()
        
        if result is None:
            return jsonify({
                'success': False,
                'message': 'Sayfa içeriği işlenirken hata oluştu',
                'timestamp': datetime.now().isoformat(),
                'error_type': 'processing_error'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Manuel kontrol tamamlandı',
            'timestamp': datetime.now().isoformat(),
            'has_order_button': result['has_order_button'],
            'has_availability': result['has_availability'],
            'changes': result['changes'],
            'test_mode': False
        })
        
    except Exception as e:
        print(f"Manual check error: {e}")
        return jsonify({
            'success': False,
            'message': f'Beklenmeyen hata: {str(e)}',
            'timestamp': datetime.now().isoformat(),
            'error_type': 'unexpected_error'
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