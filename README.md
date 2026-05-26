# Rotary Aerospace | Thrust Logger Control Center

Endüstriyel BLDC motor ve ESC performans testleri için geliştirilmiş, yüksek hassasiyetli bir veri toplama (Data Acquisition - DAQ) ve canlı analiz masaüstü arayüzüdür. STM32 tabanlı gömülü sistem donanımıyla USB-CDC (Sanal COM Port) protokolü üzerinden 115200 baud hızında haberleşerek; anlık voltaj, akım, güç, itki (loadcell) ve motor devri (eRPM) verilerini görselleştirir, güvenliği denetler ve test verilerini kayıt altına alır.

## 🚀 Öne Çıkan Özellikler

* **Canlı Grafik Motoru:** `pyqtgraph` altyapısı kullanılarak 10 Hz hızında parazitsiz, pürüzsüz ve gerçek zamanlı 5 farklı sensör grafiği (eRPM, İtki, Voltaj, Akım, Güç).
* **Akıllı Veri Kayıt Sistemi (Toggle Record):** Tek bir akıllı buton üzerinden mikro saniye hassasiyetinde zaman damgalı CSV/Excel uyumlu log kaydı başlatma ve durdurma.
* **Gelişmiş Geçmiş Analiz Modülü (Log Viewer):** Kaydedilen geçmiş test verilerini tek tıkla açarak, **Uygulanan PWM Sinyali** dahil olmak üzere 6 farklı grafikte eş zamanlı ve senkronize analiz edebilme yeteneği.
* **Entegre Loadcell Kalibrasyon Aracı:** NAU7802 sinyal dönüştürücü için arayüz üzerinden tek tıkla dara (Tare) alma ve bilinen ağırlıklar üzerinden hassas çarpan (Divider) kalibrasyonu yapabilme.
* **Çift Aşamalı Güvenlik Kilidi (Interlock):**
    * Arayüz üzerinden anlık olarak set edilebilen Maksimum Akım ve Minimum Voltaj limitleri.
    * Okuma durdurulduğu veya acil stop tetiklendiği an motor sinyalini anında güvenli rölanti noktasına (1000 PWM) çeken gömülü koruma mekanizması.
* **Profesyonel Kullanıcı Deneyimi (UX):** Dinamik terminal günlüğü, otomatik tam ekran (Maximized) yerleşimi ve şık bir açılış ekranı (Splash Screen) mimarisi.

## 📊 Sistem Mimarisi ve Veri Akışı

Yazılım, gömülü taraftan gelen spesifik veri paketlerini asenkron olarak ayrıştırır. STM32 terminalinden gelen veri paketi formatı şu şekildedir:
```text
PWM:1150 V:24.12 I:12.45 P:300.29 T:1540.5 eRPM:8450