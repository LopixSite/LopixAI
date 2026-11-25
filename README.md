# ✦ LopixAI - Windows Kişisel Yapay Zeka Asistanı

LopixAI, Windows 10/11 x64 üzerinde çalışan, kullanıcıdan hiçbir teknik kurulum (Python, pip, Ollama, Llama, CUDA, özel GPU vb.) istemeyen, Gemini API tabanlı ve internet/API kesintilerinde kesintisiz Offline Mode çalışabilen kişisel masaüstü AI asistanıdır.

---

## 🚀 Hızlı Başlangıç

### Geliştirme Ortamında Çalıştırma
```powershell
# Uygulama dizinine geçin
cd c:\Users\FALCON\Desktop\Projelerim\LopixAI

# Çift tıklayarak veya komut satırından çalıştırın:
.\run.bat
# veya
python main.py
```

### Testleri Çalıştırma
```powershell
python tests/run_tests.py
```
*(11/11 test %100 başarıyla doğrulanmıştır.)*

---

## 📁 Kullanıcı Veri Yapısı (`%APPDATA%\.lopixai\`)

LopixAI kullanıcı verilerini program kurulum klasöründen tamamen ayrı tutar. Program güncellense dahi verileriniz asla silinmez.

```
%APPDATA%\.lopixai\
│
├── chats.db                  # SQLite sohbet ve mesaj geçmişi veritabanı
├── memory.db                 # SQLite kalıcı kullanıcı hafızası
├── settings.json             # Arayüz ve model ayarları
├── secrets.dat               # Windows DPAPI ile şifrelenmiş API anahtarları
│
├── logs/
│   ├── lopixai.log           # Genel operasyon ve bilgi logları (Rotasyonlu 5MB)
│   └── errors.log            # Hata ve kritik istisna logları
│
├── cache/                    # Geçici çalışma önbelleği
│
├── voice/
│   ├── cache/                # Ses sentez ve kayıt önbelleği
│   └── settings.json         # Ses giriş/çıkış ayarları
│
├── security/
│   ├── settings.json         # İşlem onay izinleri
│   └── events/               # Güvenlik olay denetim kayıtları
│
└── agent/
    ├── workspace/            # Bilgisayar görev çalışma alanı
    └── history/              # Ajan eylem geçmişi
```

---

## 🛡️ Güvenlik ve Windows DPAPI

Gemini API anahtarları ve Telegram Bot Tokenları `settings.json` içine düz metin olarak **asla yazılmaz**.
Windows Data Protection API (`CryptProtectData` & `CryptUnprotectData`) ile şifrelenerek `secrets.dat` dosyasında tutulur. Dosya Not Defteri ile açıldığında sadece şifreli ikili veri görünür.

---

## 🛠️ Tamamlanan Özellikler (Faz 0)

1. **Çekirdek Dizin ve Dosya Altyapısı**: `%APPDATA%\.lopixai\` klasör ve alt dizinlerinin ilk açılışta otomatik oluşturulması.
2. **Windows DPAPI Şifreleme Kasası**: `secrets.dat` üzerinden şifreli API anahtarı yönetimi.
3. **SQLite Veritabanı ve Migrasyon**: `chats.db` ve `memory.db` için WAL modu, PRAGMA ayarları ve şema yönetimi.
4. **Çift Kanallı Loglama**: `lopixai.log` ve `errors.log` rotasyonlu hata takip mekanizması.
5. **Açılış Sistem Kontrol Ekranı (Splash)**: Python/Runtime, Mikrofon, Hoparlör, Kamera, İnternet, Veritabanı ve Gemini API kontrolleri (eksik donanımda kontrollü durum, asla çökme yok).
6. **ChatGPT Benzeri Modern Arayüz (PyQt6)**:
   - Sol Sidebar: Logo, Sürüm rozeti, `＋ Yeni sohbet` butonu, `🔍 Sohbetlerde ara` arama kutusu.
   - Zaman gruplamalı sohbet listesi (📌 Sabitlenenler, Bugün, Dün, Daha Eski).
   - Sohbet Üç Nokta Menüsü (`⋮`): ✏️ Yeniden adlandır, 📌 Sabitle/Kaldır, 🗑️ Onaylı sil.
   - Silme Onay Modalı: *"“{başlık}” sohbeti silinsin mi? [İptal] [Sil]"*.
   - Sağ Sohbet Alanı: Kullanıcı (sağda) ve LopixAI (solda) mesaj balonları, markdown/kod desteği.
   - Giriş Alanı: Enter ile gönder, Shift+Enter ile alt satır.
   - Otomatik Başlık Türetme: İlk mesajdan anlamlı başlık oluşturma.
7. **Modüler Gemini API Servisi**: Streaming/Sync ve sliding window context yönetimi.
8. **Akıllı Çevrimdışı Mod (Offline Mode)**:
   - Gemini anahtarı veya internet yokken uygulamanın kesintisiz çalışması.
   - Yerel komutlar: `/durum` (RAM, CPU, Disk), `/saat`, `/tarih`, `/hatirla`, `/hatirlananlar`, `/unut`, `/yardim`.
9. **Modüler Telegram Köprüsü**: `chats.db` veritabanını masaüstü ile paylaşan servis iskeleti.
10. **Güvenlik ve Olay Denetimi**: `.lopixai/security/events/` denetim loglaması.
11. **Packaging Altyapısı**: `LopixAI.spec` ve `build_exe.py` ile tek tıkla `LopixAI.exe` oluşturma yapılandırması.

---

## 🔮 Sonraki Fazlar (Gelecek Yol Haritası)

- **Faz 1**: Telegram Bot canlı polling/webhook servisinin arka planda çalıştırılması, sesli etkileşim (yerel TTS / STT modülleri).
- **Faz 2**: PC Kontrol ajan özellikleri (onay modalı eşliğinde dosya açma, uygulama başlatma, web araması).
- **Faz 3**: Inno Setup / NSIS ile `LopixAI-Setup.exe` kurulum sihirbazı ve otomatik güncelleme (Updater) sistemi.
