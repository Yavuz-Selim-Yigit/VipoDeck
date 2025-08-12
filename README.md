# 🐍 ViperDeck

> **Not:** Kaynak kodda `APP_NAME = "VipoDeck "` ve `APP = "VipoDeck "` olarak geçiyor. Repoda uygulama adını **ViperDeck** olarak kullanıyorsan, bu iki sabiti de `"ViperDeck"` yapmanı öneririm.

ViperDeck; Windows üzerinde sık kullandığınız uygulamalara, web sitelerine ve klavye kısayollarına tek tıkla ulaşmanızı sağlayan, **frameless (çerçevesiz)**, **tek satır modern üst barlı** bir **kısayol paneli**dir. Tasarım minimaldir; ikon odaklı kullanım ve tema/konum kontrolleri üst bardan sağlanır.

---

## ✨ Özellikler

- 🌗 **Tema Değişimi**: Aydınlık / Karanlık (buton ikonu dinamik: `light-theme.png` ⇄ `dark-theme.png`)
- 📍 **Pencere Konumu Modu**: Sağ üst köşe veya serbest (dinamik ikon: `topright.png` ⇄ `free.png`)
- 🖥️ **Monitör Seçimi**: Üst bardaki ekran butonundan açılan menü ile hedef monitörü seçme
- 🧩 **Kısayol Kartları**: `actions.json` ile tanımlanan ikonlu kartlar (web, uygulama, dosya, tuş kombinasyonu)
- 🛈 **Tooltip**: Kartların ve üst bar ikonlarının üzerine gelince açıklama
- 🔁 **Yeniden Yükle**: `actions.json` değişikliklerini uygulama açıkken yükleme
- 🧭 **Konumlandırma**: Sağ üst modda seçili ekranın sağ üstüne; serbest modda seçili ekranın merkezine taşır
- 📋 **Durum Çubuğu**: Alt kısımda `ViperaDev | v1.3.2` metni
- 🖱️ **Kısayol Tuşları**: `Esc` (kapat), `Ctrl+M` (küçült)

---

## 📦 Kurulum

### 1) Depoyu Klonla

```bash
git clone https://github.com/Yavuz-Selim-Yigit/ViperDeck.git
cd viperdeck
```

### 2) Sanal Ortam ve Bağımlılıklar

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt` içeriği:

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

## ⚙️ Yapılandırma: `actions.json`

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

Alanlar:

- `type: "open"` → URL, dosya veya uygulama açar (`target` gerekli)
- `type: "keys"` → Tuş kombinasyonu gönderir (`keys` dizisi gerekli)
- `icon` yolu varsa, kart **ikon-only** görünür; yoksa `label` metni gösterilir.

Değişiklikleri kaydettikten sonra üst bardaki **Yenile** (`reload.png`) ikonuna basarak kartları güncelleyebilirsiniz.

---

## 🧭 Üst Bar İkonları

Aşağıdaki ikon adları proje içindeki `icons/` klasöründen yüklenir:

- Tema: `light-theme.png` / `dark-theme.png`
- Konum modu: `topright.png` / `free.png`
- Monitör menüsü: `screen.png`
- Ayar dosyasını aç: `jsondocument.png`
- Yeniden yükle: `reload.png`
- Küçült: `minimize.png`
- Kapat: `exit.png`
- Uygulama simgesi: `app.ico`

> **İpucu:** İkon yolları doğrudan görece kullanılıyor. Eğer ileride paketlemeyi düşünürsen, bu yolları `resource_path()` deseniyle ayarlaman önerilir.

---

## 🧱 Mimari Notlar

- Uygulama frameless çalışır; penceresi **özel TitleBar** ile sürüklenir.
- **TitleBar** sinyalleri: tema toggled, konum toggled, minimize/close, config aç, reload, monitör menüsü.
- **Konumlandırma**
  - Sağ üst modunda: seçili ekran `availableGeometry().right() - width(), top()`
  - Serbest modda: seçili ekran merkezine `(cx - w/2, cy - h/2)`
- Alt durum çubuğu metni `_update_statusbar_text()` ile güncellenir: `ViperaDev | v1.3.2`.

---

## 🧪 Sorun Giderme

- **İkonlar görünmüyor**: `icons/` yolunun proje kökünde olduğundan ve dosya adlarının README’dekiyle aynı olduğundan emin olun.
- **VS Code gibi uygulamalar açılmıyor**: `target`’a tam `exe` yolu yazın (boşluk içeren yollarda kaçış gerekmiyor).
- **Tuş kombinasyonu çalışmıyor**: `keyboard` ve `pyautogui` yönetici izinleri gerekebilir; antivirüs/koruma araçları girişe engel olabilir.

---

## 📂 Proje Yapısı

```
viperdeck/
├─ app.py                 # Ana uygulama (frameless + custom title bar)
├─ actions.json           # Kart tanımları
├─ requirements.txt       # Bağımlılıklar
├─ icons/                 # Uygulama ve menü ikonları
│  ├─ app.ico
│  ├─ dark-theme.png
│  ├─ light-theme.png
│  ├─ topright.png
│  ├─ free.png
│  ├─ screen.png
│  ├─ jsondocument.png
│  ├─ reload.png
│  ├─ minimize.png
│  └─ exit.png
└─ docs/                  # Ekran görüntüleri (opsiyonel)
   ├─ screenshot_light.png
   └─ screenshot_dark.png
```

---

## 👤 Geliştirici

**ViperaDev**\
Yavuz Selim Yiğit — [GitHub](https://github.com/kullaniciadi) · [LinkedIn](https://www.linkedin.com/in/yavuz-selim-yigit/)

---

## 📜 Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.
