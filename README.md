# Tesla Stok Takip

Tesla Model Y stok ve sipariş durumunu takip eden web uygulaması.

## 🚗 Özellikler

- **Gerçek Zamanlı Takip**: Tesla Türkiye web sitesinden otomatik veri çekme
- **Anlık Bildirimler**: Sesli bildirimler
- **Manuel Kontrol**: Manuel kontrol butonu
- **Geçmiş Takibi**: Geçmiş verileri görüntüleme
- **Responsive Tasarım**: Mobil uyumlu arayüz

## 🛠️ Teknolojiler

- **Backend**: Python, Flask, Flask-SocketIO
- **Frontend**: HTML, CSS, JavaScript
- **Veritabanı**: SQLite
- **Web Scraping**: BeautifulSoup, Requests
- **Deployment**: Render

## 📦 Kurulum

1. **Gereksinimler**:
   ```
   Flask==3.0.0
   Flask-SocketIO==5.3.6
   requests==2.31.0
   BeautifulSoup4==4.12.3
   APScheduler==3.10.4
   urllib3==2.2.1
   gunicorn==22.0.0
   ```

2. **Çalıştırma**:
   ```bash
   python app.py
   ```

3. **Tarayıcıda açın**: `http://localhost:5001`

## 🌐 Canlı Demo

Uygulama şu adreste canlı olarak çalışmaktadır:
[https://teslastoktakip.onrender.com](https://teslastoktakip.onrender.com)

## 📊 Nasıl Çalışır?

1. **Otomatik Kontrol**: Uygulama her 5 dakikada bir Tesla Türkiye sayfasını kontrol eder
2. **Stok Analizi**: Sayfa içeriğinde sipariş butonu ve stok durumu arar
3. **Değişiklik Tespiti**: Önceki kontrolle karşılaştırarak değişiklikleri tespit eder
4. **Bildirim Gönderme**: Değişiklik varsa WebSocket ile frontend'e bildirim gönderir
5. **Sesli Uyarı**: Stok mevcudiyeti durumunda sesli uyarı çalar

## 🔧 API Endpoints

- `GET /` - Ana sayfa
- `GET /api/status` - Mevcut durum
- `POST /manual_check` - Manuel kontrol
- `GET /api/history` - Geçmiş veriler

## 🚀 Deployment (Render)

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `gunicorn -w 1 app:app`
3. **Python Version**: 3.9.16

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Push edin (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## 📞 İletişim

- **Proje Sahibi**: [meliherdem06]
- **Email**: [meliherddem@gmail.com]

## 🙏 Teşekkürler

- Tesla Türkiye
- Flask ve Flask-SocketIO geliştiricileri
- Render hosting platformu 

## WebSocket Events

- `connect` - Bağlantı kurulduğunda
- `disconnect` - Bağlantı kesildiğinde
- `status_update` - Durum güncellendiğinde

## Veritabanı

SQLite veritabanı (`tesla_stok_takip.db`) şu tabloları içerir:

- `page_snapshots`: Sayfa anlık görüntüleri
- `status_changes`: Durum değişiklikleri
