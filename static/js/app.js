// Tesla Model Y Monitor - Frontend Application
class TeslaMonitor {
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
        this.loadInitialData();
        this.setupChart();
    }

    connectWebSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
            this.addNotification('Sistem bağlandı', 'success');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
            this.addNotification('Bağlantı kesildi', 'error');
        });

        this.socket.on('status', (data) => {
            this.addNotification(data.message, 'info');
        });

        this.socket.on('page_change', (data) => {
            this.addNotification(data.message, 'warning');
            this.playNotificationSound();
            this.updateStatus(data);
        });

        this.socket.on('order_available', (data) => {
            this.addNotification('🚗 TESLA MODEL Y SİPARİŞİ MEVCUT! 🚗', 'success');
            this.playNotificationSound();
            this.playNotificationSound(); // Play twice for emphasis
            this.updateOrderStatus(true);
        });

        this.socket.on('stock_change', (data) => {
            this.addNotification('📦 Stok durumu değişti!', 'warning');
            this.playNotificationSound();
            this.updateStockStatus(true);
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
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            this.updateStatus(data);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.addNotification('Veri yüklenirken hata oluştu', 'error');
        }
    }

    async manualCheck() {
        const button = document.getElementById('manualCheck');
        const originalText = button.innerHTML;
        
        button.innerHTML = '<div class="loading"></div> Kontrol Ediliyor...';
        button.disabled = true;

        try {
            const response = await fetch('/api/manual-check', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            
            if (data.success) {
                this.addNotification('Manuel kontrol tamamlandı', 'success');
                // Reload status after manual check
                await this.loadInitialData();
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
        
        if (data.has_order_button) {
            orderStatus.textContent = 'Sipariş Mevcut!';
            orderStatusIcon.classList.add('available');
        } else {
            orderStatus.textContent = 'Sipariş Yok';
            orderStatusIcon.classList.remove('available');
        }

        // Update stock status
        const stockStatus = document.getElementById('stockStatus');
        const stockStatusIcon = document.getElementById('stockStatusIcon');
        
        if (data.has_availability) {
            stockStatus.textContent = 'Stok Mevcut!';
            stockStatusIcon.classList.add('available');
        } else {
            stockStatus.textContent = 'Stok Yok';
            stockStatusIcon.classList.remove('available');
        }

        // Update last check time
        const lastCheck = document.getElementById('lastCheck');
        if (data.last_check) {
            const date = new Date(data.last_check);
            lastCheck.textContent = date.toLocaleString('tr-TR');
        } else {
            lastCheck.textContent = 'Henüz kontrol edilmedi';
        }
    }

    updateOrderStatus(available) {
        const orderStatus = document.getElementById('orderStatus');
        const orderStatusIcon = document.getElementById('orderStatusIcon');
        
        if (available) {
            orderStatus.textContent = 'Sipariş Mevcut!';
            orderStatusIcon.classList.add('available');
        }
    }

    updateStockStatus(available) {
        const stockStatus = document.getElementById('stockStatus');
        const stockStatusIcon = document.getElementById('stockStatusIcon');
        
        if (available) {
            stockStatus.textContent = 'Stok Mevcut!';
            stockStatusIcon.classList.add('available');
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
    new TeslaMonitor();
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