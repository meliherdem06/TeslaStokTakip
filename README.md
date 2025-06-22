# Tesla Stok Takip

Tesla Model Y araçlarının Türkiye'deki stok durumunu gerçek zamanlı olarak takip eden web uygulaması.

## 🚗 Özellikler

- **Gerçek Zamanlı Takip**: Tesla Türkiye sayfasını 5 dakikada bir kontrol eder
- **Anlık Bildirimler**: Stok durumu değiştiğinde sesli ve görsel bildirimler
- **Manuel Kontrol**: İsteğe bağlı manuel kontrol butonu
- **Geçmiş Takibi**: Stok durumu geçmişini görüntüleme
- **WebSocket Bağlantısı**: Gerçek zamanlı güncellemeler
- **Responsive Tasarım**: Mobil ve masaüstü uyumlu

## 🛠️ Teknolojiler

- **Backend**: Python Flask, Flask-SocketIO
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js
- **Veritabanı**: SQLite
- **Web Scraping**: BeautifulSoup, Requests
- **Deployment**: Render

## 📦 Kurulum

### Gereksinimler
- Python 3.9+
- pip

### Adımlar

1. **Projeyi klonlayın:**
   ```bash
   git clone https://github.com/kullaniciadi/TeslaStokTakip.git
   cd TeslaStokTakip
   ```

2. **Sanal ortam oluşturun:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # veya
   venv\Scripts\activate  # Windows
   ```

3. **Bağımlılıkları yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Uygulamayı çalıştırın:**
   ```bash
   python app.py
   ```

5. **Tarayıcıda açın:**
   ```
   http://localhost:5001
   ```

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
- `GET /api/status` - Mevcut durum bilgisi
- `GET /api/history` - Geçmiş veriler
- `POST /api/manual-check` - Manuel kontrol

## 🚀 Deployment

### Render'da Deploy Etme

1. **Render hesabı oluşturun** ve GitHub reponuzu bağlayın
2. **Yeni Web Service** oluşturun
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn --worker-class eventlet -w 1 app:app`
5. **Environment Variables**:
   - `PORT`: `10000`

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
