// Tesla Stok Takip - Frontend Application
class TeslaStokTakip {
    constructor() {
        this.soundEnabled = true;
        this.notificationSound = document.getElementById('notificationSound');
        this.chart = null;
        this.pollingInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startPolling();
        this.loadHistoryData();
    }

    startPolling() {
        // Poll every 30 seconds for status updates
        this.pollingInterval = setInterval(() => {
            this.loadInitialData();
        }, 30000);
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
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            this.updateConnectionStatus(true);
            this.updateStatus(data.status, data.last_check);
            
            // Check for changes and show notifications
            if (data.status.has_availability) {
                this.addNotification('🚗 TESLA MODEL Y STOKTA! 🚗', 'success');
                this.playNotificationSound();
            } else if (data.status.has_order_button) {
                this.addNotification('🔔 Tesla Model Y için ön sipariş mevcut olabilir!', 'warning');
                this.playNotificationSound();
            }
            
        } catch (error) {
            console.error('Error loading status:', error);
            this.updateConnectionStatus(false);
            this.addNotification('Durum bilgisi alınamadı', 'error');
        }
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
                this.updateStatus(data.status);
                
                // Check for changes and show notifications
                if (data.status.has_availability) {
                    this.addNotification('🚗 TESLA MODEL Y STOKTA! 🚗', 'success');
                    this.playNotificationSound();
                } else if (data.status.has_order_button) {
                    this.addNotification('🔔 Tesla Model Y için ön sipariş mevcut olabilir!', 'warning');
                    this.playNotificationSound();
                }
            } else {
                this.addNotification(`Manuel kontrol hatası: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Manual check error:', error);
            this.addNotification('Manuel kontrol sırasında hata oluştu', 'error');
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    updateStatus(data, lastCheckTime = null) {
        const orderStatus = document.getElementById('orderStatus');
        const orderStatusIcon = document.getElementById('orderStatusIcon');
        
        if (data.has_order_button === null || data.has_order_button === undefined) {
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
        
        if (data.has_availability === null || data.has_availability === undefined) {
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
        if (lastCheckTime) {
            const date = new Date(lastCheckTime);
            lastCheck.textContent = date.toLocaleString('tr-TR');
        } else {
            lastCheck.textContent = 'Henüz kontrol edilmedi';
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
            case 'error': return 'fas fa-exclamation-circle';
            case 'warning': return 'fas fa-exclamation-triangle';
            case 'info': return 'fas fa-info-circle';
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
            this.notificationSound.play().catch(e => console.log('Audio play failed:', e));
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
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1
                }, {
                    label: 'Stok Durumu',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1,
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                return value === 1 ? 'Var' : 'Yok';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                    }
                }
            }
        });
    }

    async loadHistoryData() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            
            if (data.length > 0) {
                this.updateChart(data);
            }
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }

    updateChart(data) {
        if (!this.chart) {
            this.setupChart();
        }

        const labels = data.map(item => {
            const date = new Date(item.timestamp);
            return date.toLocaleString('tr-TR', { 
                month: 'short', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        }).reverse();

        const orderData = data.map(item => item.has_order_button ? 1 : 0).reverse();
        const stockData = data.map(item => item.has_availability ? 1 : 0).reverse();

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