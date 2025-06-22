# Tesla Model Y Stok Takip Sistemi

Tesla Model Y'nin Türkiye'deki stok ve sipariş durumunu gerçek zamanlı olarak takip eden web uygulaması.

## Özellikler

- 🔄 **Gerçek Zamanlı Takip**: Tesla'nın Türkiye sayfasını 5 dakikada bir kontrol eder
- 📊 **Durum Analizi**: Sipariş butonu ve stok durumu analizi
- 🔔 **Bildirimler**: Durum değişikliklerinde sesli ve görsel bildirimler
- 📱 **Responsive Tasarım**: Mobil ve masaüstü uyumlu arayüz
- 🗄️ **Veri Saklama**: SQLite veritabanında geçmiş kayıtları
- 🌐 **Web API**: RESTful API ile durum sorgulama

## Teknolojiler

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: Python, Flask
- **Veritabanı**: SQLite
- **Web Scraping**: BeautifulSoup4, Requests
- **Hosting**: Render (Free Tier)

## Kurulum

### Gereksinimler

- Python 3.9.16
- pip

### Yerel Kurulum

1. Projeyi klonlayın:
```bash
git clone https://github.com/yourusername/tesla-stock-monitor.git
cd tesla-stock-monitor
```

2. Sanal ortam oluşturun:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

3. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

4. Uygulamayı çalıştırın:
```bash
python app.py
```

5. Tarayıcınızda `http://localhost:5001` adresini açın.

## Kullanım

1. **Otomatik Takip**: Uygulama otomatik olarak Tesla sayfasını kontrol eder
2. **Manuel Kontrol**: "Manuel Kontrol" butonuna tıklayarak anlık kontrol yapabilirsiniz
3. **Durum Görüntüleme**: Ana sayfada mevcut durumu görebilirsiniz
4. **Bildirimler**: Durum değişikliklerinde otomatik bildirim alırsınız

## API Endpoints

- `GET /api/status` - Mevcut durumu döndürür
- `POST /manual_check` - Manuel kontrol yapar

## Deployment

### Render'da Deployment

1. GitHub'a projeyi push edin
2. Render'da yeni Web Service oluşturun
3. GitHub repository'nizi bağlayın
4. Build Command: `chmod +x build.sh && ./build.sh`
5. Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --worker-class sync --timeout 120 --preload app:app`

## Konfigürasyon

### Environment Variables

- `PORT`: Uygulama portu (varsayılan: 5001)
- `PYTHON_VERSION`: Python versiyonu (3.9.16)

### Tesla URLs

Uygulama aşağıdaki Tesla URL'lerini kontrol eder:

- https://www.tesla.com/tr_TR/modely/design#overview
- https://www.tesla.com/tr_tr/model-y/design
- https://www.tesla.com/tr_TR/modely
- https://www.tesla.com/tr_tr/modely
- https://www.tesla.com/tr_TR/model-y
- https://www.tesla.com/tr_tr/modely/design
- https://www.tesla.com/tr_TR/model-y/design
- https://www.tesla.com/tr_tr/modely/design#overview
- https://www.tesla.com/tr_TR/modely/design#overview
- https://www.tesla.com/tr_tr/modely/design#overview

## Sorun Giderme

### Port Çakışması
```bash
# Port 5001 kullanımdaysa farklı port kullanın
PORT=5002 python app.py
```

### Bağlantı Sorunları
- Tesla'nın bot koruması nedeniyle bazen bağlantı sorunları yaşanabilir
- Uygulama otomatik olarak farklı URL'leri dener
- Manuel kontrol ile anlık test yapabilirsiniz

### Deployment Sorunları
- Render'da build cache'ini temizleyin
- Python 3.9.16 kullandığınızdan emin olun
- Eventlet/gevent kullanmadığınızdan emin olun

## Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## Teşekkürler

- Tesla Türkiye
- Flask geliştiricileri
- BeautifulSoup4 geliştiricileri
- Render hosting platformu

## WebSocket Events

- `connect` - Bağlantı kurulduğunda
- `disconnect` - Bağlantı kesildiğinde
- `status_update` - Durum güncellendiğinde

## Veritabanı

SQLite veritabanı (`tesla_stok_takip.db`) şu tabloları içerir:

- `page_snapshots`: Sayfa anlık görüntüleri
- `status_changes`: Durum değişiklikleri
