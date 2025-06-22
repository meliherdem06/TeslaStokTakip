// Tesla Stok Takip - Frontend Application
class TeslaStokTakip {
    constructor() {
        this.socket = null;
        this.soundEnabled = true;
        this.notificationSound = document.getElementById('notificationSound');
        this.chart = null;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.loadHistoryData();
    }

    connectWebSocket() {
        this.socket = io({
            transports: ['websocket'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: Infinity
        });

        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
            this.addNotification('Sisteme bağlandı, ilk durum kontrol ediliyor...', 'info');
        });

        this.socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            this.addNotification('Sistemle bağlantı kesildi', 'warning');
        });

        this.socket.on('status_update', (data) => {
            console.log('Status update received:', data);
            this.addNotification(data.message, 'info');
            this.updateStatus(data);
            
            if (data.has_availability) {
                this.addNotification('🚗 TESLA MODEL Y STOKTA! 🚗', 'success');
                this.playNotificationSound();
            } else if (data.has_order_button) {
                 this.addNotification('🔔 Tesla Model Y için ön sipariş mevcut olabilir!', 'warning');
                 this.playNotificationSound();
            }
        });
        
        this.socket.on('check_complete', (data) => {
            console.log('Check complete received:', data);
            this.addNotification(data.message, 'info');
            this.updateStatus(data);
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection Error:', error);
            this.updateConnectionStatus(false);
            this.addNotification('Bağlantı hatası: ' + error.message, 'error');
        });
    }

    setupEventListeners() {
        // Manual check button
        document.getElementById('manualCheck').addEventListener('click', () => {
            this.manualCheck();
        });

        // Toggle sound button
        document.getElementById('toggleSound').addEventListener('click', () => {
            this.toggleSound();
        });

        // Open Tesla page button
        document.getElementById('openTesla').addEventListener('click', () => {
            window.open('https://www.tesla.com/tr_TR/modely/design#overview', '_blank');
        });

        // Clear notifications button
        document.getElementById('clearNotifications').addEventListener('click', () => {
            this.clearNotifications();
        });
    }

    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        if (connected) {
            statusDot.className = 'status-dot connected';
            statusText.textContent = 'Bağlı';
        } else {
            statusDot.className = 'status-dot disconnected';
            statusText.textContent = 'Bağlantı Yok';
        }
    }

    async loadInitialData() {
        // This is now only for the history chart or as a fallback.
        // The primary status update comes from the 'status_update' websocket event.
    }

    async manualCheck() {
        const button = document.getElementById('manualCheck');
        const originalText = button.innerHTML;
        
        try {
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Kontrol Ediliyor...';
            button.disabled = true;
            
            const response = await fetch('/manual_check', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addNotification(data.message, 'success');
                // The backend will push the update via WebSocket, so no need to call updateStatus here.
            } else {
                this.addNotification(`Manuel kontrol hatası: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('Manual check error:', error);
            this.addNotification('Manuel kontrol sırasında hata oluştu', 'error');
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    updateStatus(data) {
        // Update order status
        const orderStatus = document.getElementById('orderStatus');
        const orderStatusIcon = document.getElementById('orderStatusIcon');
        
        if (data.has_order_button === null) {
            orderStatus.textContent = 'Bilinmiyor';
            orderStatusIcon.className = 'status-icon order-status';
        } else if (data.has_order_button) {
            orderStatus.textContent = 'Sipariş Mevcut';
            orderStatusIcon.className = 'status-icon order-status available';
        } else {
            orderStatus.textContent = 'Sipariş Yok';
            orderStatusIcon.className = 'status-icon order-status';
        }

        // Update stock status
        const stockStatus = document.getElementById('stockStatus');
        const stockStatusIcon = document.getElementById('stockStatusIcon');
        
        if (data.has_availability === null) {
            stockStatus.textContent = 'Bilinmiyor';
            stockStatusIcon.className = 'status-icon stock-status';
        } else if (data.has_availability) {
            stockStatus.textContent = 'Stok Mevcut';
            stockStatusIcon.className = 'status-icon stock-status available';
        } else {
            stockStatus.textContent = 'Stok Yok';
            stockStatusIcon.className = 'status-icon stock-status';
        }

        // Update last check time
        const lastCheck = document.getElementById('lastCheck');
        if (data.last_check_time) {
            const date = new Date(data.last_check_time);
            lastCheck.textContent = date.toLocaleString('tr-TR');
        }
    }

    addNotification(message, type = 'info') {
        const notificationsList = document.getElementById('notificationsList');
        const notification = document.createElement('div');
        notification.className = `notification-item ${type}`;
        
        const icon = this.getNotificationIcon(type);
        notification.innerHTML = `
            <i class="${icon}"></i>
            <span>${message}</span>
        `;
        
        notificationsList.insertBefore(notification, notificationsList.firstChild);
        
        // Limit notifications to 20
        const notifications = notificationsList.querySelectorAll('.notification-item');
        if (notifications.length > 20) {
            notifications[notifications.length - 1].remove();
        }
    }

    getNotificationIcon(type) {
        switch (type) {
            case 'success': return 'fas fa-check-circle';
            case 'warning': return 'fas fa-exclamation-triangle';
            case 'error': return 'fas fa-times-circle';
            default: return 'fas fa-info-circle';
        }
    }

    clearNotifications() {
        const notificationsList = document.getElementById('notificationsList');
        notificationsList.innerHTML = `
            <div class="notification-item info">
                <i class="fas fa-info-circle"></i>
                <span>Bildirimler temizlendi</span>
            </div>
        `;
    }

    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        const button = document.getElementById('toggleSound');
        
        if (this.soundEnabled) {
            button.innerHTML = '<i class="fas fa-volume-up"></i> Ses Açık';
            this.addNotification('Ses bildirimleri açıldı', 'info');
        } else {
            button.innerHTML = '<i class="fas fa-volume-mute"></i> Ses Kapalı';
            this.addNotification('Ses bildirimleri kapatıldı', 'info');
        }
    }

    playNotificationSound() {
        if (this.soundEnabled && this.notificationSound) {
            this.notificationSound.currentTime = 0;
            this.notificationSound.play().catch(error => {
                console.log('Audio play failed:', error);
            });
        }
    }

    setupChart() {
        const ctx = document.getElementById('historyChart');
        if (!ctx) return;

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Sipariş Durumu',
                    data: [],
                    borderColor: '#3e6ae1',
                    backgroundColor: 'rgba(62, 106, 225, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Stok Durumu',
                    data: [],
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#ffffff'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#b0b0b0',
                            stepSize: 1
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });

        this.loadHistoryData();
    }

    async loadHistoryData() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            this.updateChart(data);
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }

    updateChart(data) {
        if (!this.chart || data.length === 0) return;

        const labels = [];
        const orderData = [];
        const stockData = [];

        data.reverse().forEach(item => {
            const date = new Date(item.timestamp);
            labels.push(date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }));
            orderData.push(item.has_order_button ? 1 : 0);
            stockData.push(item.has_availability ? 1 : 0);
        });

        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = orderData;
        this.chart.data.datasets[1].data = stockData;
        this.chart.update();
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TeslaStokTakip();
});

// Service Worker for offline functionality
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
} 