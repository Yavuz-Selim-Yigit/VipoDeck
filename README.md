# 🐍 VipoDeck

VipoDeck; Windows üzerinde sık kullandığınız uygulamalara, web sitelerine ve klavye kısayollarına tek tıkla ulaşmanızı sağlayan, **frameless (çerçevesiz)**, **tek satır modern üst barlı** bir **kısayol paneli**dir. Tasarım minimaldir; ikon odaklı kullanım ve tema/konum kontrolleri üst bardan sağlanır.

---

## ✨ Özellikler

* 🌗 **Tema Değişimi**: Aydınlık / Karanlık (buton ikonu dinamik: `light-theme.png` ⇄ `dark-theme.png`)
* 📍 **Pencere Konumu Modu**: Sağ üst köşe veya serbest (dinamik ikon: `topright.png` ⇄ `free.png`)
* 🖥️ **Monitör Seçimi**: Üst bardaki ekran butonundan açılan menü ile hedef monitörü seçme
* 🧹 **Kısayol Kartları**: [`actions.json`](https://github.com/Yavuz-Selim-Yigit/VipoDeck/blob/main/actions.json) ile tanımlanan ikonlu kartlar (web, uygulama, dosya, tuş kombinasyonu)
* 💚 **Tooltip**: Kartların ve üst bar ikonlarının üzerine gelince açıklama
* 🔁 **Yeniden Yükle**: [`actions.json`](https://github.com/Yavuz-Selim-Yigit/VipoDeck/blob/main/actions.json) değişikliklerini uygulama açıkken yükleme
* 🧱 **Konumlandırma**: Sağ üst modda seçili ekranın sağ üstüne; serbest modda seçili ekranın merkezine taşır ve istenilen yöne hareket ettirilebilir
* 🤗 **Kısayol Tuşları**: `Esc` (kapat), `Ctrl+M` (küçült)

## ⬇️ İndirip Kullanmak İçin
* [İndir](https://github.com/Yavuz-Selim-Yigit/VipoDeck/releases/download/VipoDeck/VipoDeck-v1_3_2.rar)

---

## 📦 Kurulum

### 1) Depoyu Klonla

```bash
git clone https://github.com/Yavuz-Selim-Yigit/VipoDeck.git
cd VipoDeck
```

### 2) Bağımlılıklar

```bash

pip install -r requirements.txt

```

`requirements.txt` içeriği:
[requirements.txt](https://github.com/Yavuz-Selim-Yigit/VipoDeck/blob/main/requirements.txt)

```text
PyQt5>=5.15.9
PyAutoGUI>=0.9.54
keyboard>=0.13.5
```

### 3) Çalıştır

```bash
python app.py
```

> **Not (Windows):** Yüksek DPI ekranlarda net görüntü için uygulama, Qt’nin `AA_EnableHighDpiScaling` ve `AA_UseHighDpiPixmaps` özniteliklerini etkinleştirir.

---

## ⚙️ Yapılandırma: [`actions.json`](https://github.com/Yavuz-Selim-Yigit/VipoDeck/blob/main/actions.json)

Uygulamada görünen kartlar bu dosyadan yüklenir. Örnek şema:

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
      "label": "VS Code",
      "icon": "icons/vscode.png",
      "type": "open",
      "target": "C:/Program Files/Microsoft VS Code/Code.exe"
    },
    {
      "label": "Kopyala",
      "icon": "icons/copy.png",
      "type": "keys",
      "keys": ["ctrl", "c"]
    }
  ]
}
```


## 👤 Geliştirici

**ViperaDev**
Yavuz Selim Yiğit — [GitHub](https://github.com/Yavuz-Selim-Yigit) · [LinkedIn](https://www.linkedin.com/in/yavuz-selim-yigit/)

