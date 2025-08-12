# 🐍 ViperDeck

ViperDeck, masaüstünüzde sık kullandığınız uygulamalara, web sitelerine ve kısayol tuşlarına hızlıca erişmenizi sağlayan **özelleştirilebilir bir kısayol panelidir**.\
Modern ve minimal tasarımı ile üretkenliğinizi artırır.

---

## ✨ Özellikler

- 🌗 **Karanlık / Aydınlık Tema** desteği
- 📌 **Monitör Seçme** ve pencere konumu ayarlama (sağ üst köşe / serbest mod)
- ⚡ **Hızlı Erişim Kartları** (ikonlu veya metinli)
- 🖱️ **Tooltip Desteği** – fare ile üzerine gelindiğinde açıklama görünür
- 🔄 **Ayar Dosyası Yenileme** (Uygulamayı kapatmadan)
- 📁 **Kolay Yapılandırma** (JSON dosyası ile kısayol ekleme/çıkarma)
- 💻 **Multi-monitor desteği**

---

## 📷 Ekran Görüntüsü

> **Koyu Tema Örneği**\
>

---

## 📦 Kurulum

### 1️⃣ Depoyu Klonla

```bash
git clone https://github.com/Yavuz-Selim-Yigit/ViperDeck.git
cd viperdeck
```

### 2️⃣ Sanal Ortam Oluştur ve Etkinleştir

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac / Linux
source .venv/bin/activate
```

### 3️⃣ Gerekli Paketleri Kur

```bash
pip install -r requirements.txt
```

---

## ⚙️ Kullanım

```bash
python app.py
```

### Kısayollar:

- **ESC** → Uygulamayı kapat
- **Ctrl + M** → Pencereyi küçült

---

## 🛠️ Kısayolları Düzenleme

Tüm kısayollar `actions.json` dosyasında tutulur.

Örnek yapı:

```json
{
    "buttons": [
        {
            "label": "Google",
            "icon": "icons/google.png",
            "type": "open",
            "target": "https://www.google.com"
        },
        {
            "label": "VSCode",
            "icon": "icons/vscode.png",
            "type": "open",
            "target": "C:/Program Files/Microsoft VS Code/Code.exe"
        }
    ]
}
```

`type` alanı:

- `"open"` → Dosya, uygulama veya web sayfası açar
- `"keys"` → Klavye kısayolu çalıştırır (`"keys": ["ctrl", "c"]` gibi)

---

## 📂 Proje Yapısı

```
viperdeck/
│── app.py               # Ana uygulama
│── actions.json         # Kısayol tanımları
│── requirements.txt     # Bağımlılıklar
│── icons/               # Uygulama ikonları
│── docs/                # Ekran görüntüleri vb.
```

---

## 👨‍💻 Geliştirici

- **Yavuz Selim Yiğit** – [LinkedIn](https://www.linkedin.com/in/yavuz-selim-yigit/) | [GitHub](https://github.com/kullaniciadi)

---

## 📜 Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır.\
Daha fazla bilgi için [LICENSE](LICENSE) dosyasına bakın.

