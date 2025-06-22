# Tesla Model Y Stok Takip Sistemi - Local Mod

Tesla Model Y'nin Türkiye'deki stok ve sipariş durumunu **sadece local bilgisayarınızda** gerçek zamanlı olarak takip eden web uygulaması.

## 🎯 Özellikler

- 🔄 **Gerçek Zamanlı Takip**: Tesla'nın Türkiye sayfasını 5 dakikada bir kontrol eder
- 🌐 **Selenium WebDriver**: Gerçek tarayıcı gibi davranarak Tesla'nın sitesine erişir
- 📊 **Durum Analizi**: Sipariş butonu ve stok durumu analizi
- 🔔 **Bildirimler**: Durum değişikliklerinde görsel bildirimler
- 📱 **Responsive Tasarım**: Mobil ve masaüstü uyumlu arayüz
- 🗄️ **Veri Saklama**: SQLite veritabanında geçmiş kayıtları
- 🌐 **Web API**: RESTful API ile durum sorgulama

## ⚠️ Önemli Not

Bu uygulama **sadece local bilgisayarınızda** çalışır. Render, Heroku gibi bulut platformlarında çalışmaz çünkü:
- Tesla, bulut IP'lerini engelliyor
- Selenium WebDriver bulut ortamlarında sorunlu çalışıyor
- Local IP adresiniz Tesla tarafından daha güvenilir kabul ediliyor

## 🛠️ Teknolojiler

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: Python, Flask
- **Web Scraping**: Selenium WebDriver, BeautifulSoup4
- **Veritabanı**: SQLite
- **Browser Automation**: Chrome WebDriver

## 📋 Gereksinimler

- Python 3.9+
- Google Chrome tarayıcısı
- pip

## 🚀 Kurulum

### 1. Projeyi Klonlayın
```bash
git clone https://github.com/meliherdem06/TeslaStokTakip.git
cd TeslaStokTakip
```

### 2. Virtual Environment Oluşturun
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# veya
venv\Scripts\activate  # Windows
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Uygulamayı Başlatın
```bash
python app.py
```

Uygulama `http://localhost:5001` adresinde çalışmaya başlayacak.

## 🎮 Kullanım

1. **Otomatik Kontrol**: Uygulama her 5 dakikada bir Tesla sitesini otomatik kontrol eder
2. **Manuel Kontrol**: "Manuel Kontrol" butonuna tıklayarak anında kontrol yapabilirsiniz
3. **Durum Görüntüleme**: Ana sayfada mevcut durumu görebilirsiniz
4. **API Kullanımı**: `/api/status` endpoint'i ile programatik erişim

## 📡 API Endpoints

### GET /api/status
Mevcut durumu döndürür:
```json
{
  "has_order_button": true/false/null,
  "has_availability": true/false/null,
  "last_check": "2025-06-22T21:13:15.195624",
  "timestamp": "2025-06-22T21:13:15.195624"
}
```

### POST /manual_check
Manuel kontrol başlatır:
```json
{
  "success": true,
  "status": {
    "has_order_button": true/false/null,
    "has_availability": true/false/null
  },
  "message": "Manual check completed"
}
```

## 🔧 Konfigürasyon

### Port Değiştirme
```bash
PORT=8080 python app.py
```

### Kontrol Sıklığını Değiştirme
`app.py` dosyasında `time.sleep(300)` değerini değiştirin (saniye cinsinden).

## 🐛 Sorun Giderme

### Chrome WebDriver Sorunu
Eğer Chrome WebDriver ile ilgili sorun yaşıyorsanız:
1. Google Chrome'un güncel olduğundan emin olun
2. `webdriver-manager` otomatik olarak uygun driver'ı indirecektir
3. İlk çalıştırmada biraz zaman alabilir

### Port Çakışması
Port 5001 kullanımdaysa:
```bash
PORT=5002 python app.py
```

### SSL Uyarıları
macOS'ta SSL uyarıları görülebilir, bu normaldir ve uygulamayı etkilemez.

## 📊 Veritabanı

SQLite veritabanı (`tesla_status.db`) otomatik olarak oluşturulur ve şu bilgileri saklar:
- Kontrol zamanı
- Sipariş butonu durumu
- Stok durumu
- Kontrol edilen URL

## 🔒 Güvenlik

- Uygulama sadece localhost'ta çalışır
- Dış bağlantılara açık değildir
- Tesla'nın sitesine sadece okuma amaçlı erişir

## 📝 Lisans

Bu proje eğitim amaçlıdır. Tesla'nın kullanım şartlarına uygun kullanın.

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📞 İletişim

Sorularınız için GitHub Issues kullanabilirsiniz.

---

**Not**: Bu uygulama Tesla'nın resmi bir ürünü değildir ve Tesla ile hiçbir bağlantısı yoktur.
