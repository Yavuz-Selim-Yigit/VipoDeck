import sys, os, json, time, subprocess, webbrowser  # Sistem, dosya, JSON, zaman, dış süreç ve tarayıcı
from pathlib import Path                             # Yol işlemleri için Path
from PyQt5 import QtCore, QtGui, QtWidgets           # PyQt5 ana modülleri
import pyautogui, keyboard                           # Tuş simülasyonu ve global kısayol

APP_NAME   = "ViperaDeck"                            # Uygulama görünen adı
ORG        = "ViperaDev"                             # QSettings için organizasyon
APP        = "ViperaDeck"                            # QSettings için uygulama kimliği
CONFIG_PATH = Path(__file__).with_name("actions.json") # Çalıştırılan dosyayla aynı klasörde actions.json

# -------------------- Tema Paletleri --------------------
LIGHT = {                                           # Açık tema renkleri
    "bg": "#f5f7fa",                                # Pencere arka planı
    "fg": "#1e293b",                                # Başlık/ön plan metin
    "muted": "#64748b",                             # Sönük metin
    "card_bg": "#ffffff",                           # Kart arka planı
    "card_border": "#e2e8f0",                       # Kart kenarlık
    "card_hover": "#eef2f7",                        # Kart hover rengi
    "text_color": "#0b1220",                        # Kart içi metin
    "sidebar_bg": "rgba(0,0,0,0.03)",               # Sol menü arka plan
    "sidebar_border": "rgba(0,0,0,0.08)"            # Sol menü ayırıcı
}
DARK = {                                            # Koyu tema renkleri
    "bg": "#0e1726",
    "fg": "#e2e8f0",
    "muted": "#94a3b8",
    "card_bg": "#111827",
    "card_border": "#334155",
    "card_hover": "#1f2a44",
    "text_color": "#ffffff",
    "sidebar_bg": "rgba(255,255,255,0.04)",
    "sidebar_border": "rgba(255,255,255,0.10)"
}

# -------------------- Windows Başlangıç Kısayolu --------------------
STARTUP_FOLDER = os.path.join(                      # Kullanıcının başlangıç klasörü
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)
APP_SHORTCUT = os.path.join(STARTUP_FOLDER, f"{APP_NAME}.lnk")  # .lnk kısayol yolu

# -------------------- Yardımcılar --------------------
def _launcher_paths():
    """Exe ve argümanlarını döndür (frozen exe ya da .py)."""
    if getattr(sys, "frozen", False):               # PyInstaller vb. ile paketli mi?
        return sys.executable, ""                   # Yalnızca exe
    else:
        return sys.executable, f'"{os.path.abspath(sys.argv[0])}"'  # Python + script

def _load_raw_config():
    """actions.json'u oku, yoksa boş dict dön."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)                     # JSON yükle
    except Exception:
        return {}                                   # Hata/eksikse boş

def _save_config(data: dict):
    """Konfigürasyonu diske yaz."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)  # Türkçe karakterler için ensure_ascii=False
    except Exception:
        pass                                        # Yazma hatasını sessiz geç

def _as_list_categories(v):
    """'categories' alanını güvenle listeye çevir."""
    if not v: return []                             # None/boş ise boş liste
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []                     # Dolu düz string ise tek elemanlı liste
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]  # Liste ise temizle
    return []                                       # Aksi durumda boş

def _normalize_config():
    """Eski biçimden yeni profil yapısına dönüştür; categories'i listeleştir."""
    raw = _load_raw_config()
    if "profiles" not in raw or "active_profile" not in raw:  # Eski format mı?
        buttons = raw.get("buttons", [])           # Eski key
        store = {"active_profile": "Default", "profiles": {"Default": {"buttons": buttons}}}
    else:
        store = raw
    # Her buton için categories alanını liste yap
    for prof in store.get("profiles", {}).values():
        for b in prof.get("buttons", []):
            b["categories"] = _as_list_categories(b.get("categories"))
    _save_config(store)                             # Normalize edilmiş halini kaydet
    return store

def load_config():
    """Kullanım fonksiyonu: normalize edilmiş konfigürü döndür."""
    return _normalize_config()

def open_target(target: str):
    """Dosya/URL aç."""
    if not target: return
    if target.startswith(("http://", "https://")):  # URL ise tarayıcıda aç
        webbrowser.open(target); return
    try:
        subprocess.Popen([target], shell=True)      # Uygulama/exec yolu
    except Exception:
        try: webbrowser.open(target)                # Olmazsa tarayıcıya ver
        except Exception: pass

def run_action(a: dict):
    """Kart tıklandığında davranış."""
    t = (a.get("type") or "").lower()               # 'open' / 'keys'
    if t == "open":
        open_target(a.get("target", ""))            # Hedefi aç
    elif t == "keys":
        time.sleep(0.03)                            # Küçük gecikme
        seq = a.get("keys", [])                     # ["ctrl","c"] gibi
        if seq:
            try: pyautogui.hotkey(*seq)             # Kombinasyonu gönder
            except Exception: pass

def ensure_winshell_installed(parent=None) -> bool:
    """winshell kurulu mu? değilse kullanıcı onayıyla kur."""
    try:
        import winshell  # noqa                      # Varsa True
        return True
    except Exception:
        pass
    # Kullanıcıya sor
    ret = QtWidgets.QMessageBox.question(
        parent, "Gerekli Paket",
        "Windows ile başlat için 'winshell' paketi gerekli. Kurulsun mu?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes
    )
    if ret != QtWidgets.QMessageBox.Yes:
        return False
    try:
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)  # İmleç bekleme
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])  # Pip güncelle
        subprocess.check_call([sys.executable, "-m", "pip", "install", "winshell"])          # winshell kur
    except Exception as e:
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QMessageBox.warning(parent, "Kurulum Hatası", f"winshell kurulamadı:\n{e}")
        return False
    finally:
        try: QtWidgets.QApplication.restoreOverrideCursor()
        except Exception: pass
    try:
        import winshell  # noqa                      # Tekrar dene
        return True
    except Exception:
        return False

# -------------------- Dialoglar: Kısayol Düzenleyici --------------------
class ShortcutEditor(QtWidgets.QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Kısayol")              # Dialog başlığı
        self.setModal(True)                         # Modal olsun
        self.resize(420, 320)                       # Başlangıç boyutu
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)  # ? butonunu kaldır

        # Alanlar
        self.le_label = QtWidgets.QLineEdit()       # Ad/Tooltip
        self.le_icon  = QtWidgets.QLineEdit()       # İkon yolu
        self.btn_browse_icon = QtWidgets.QToolButton(text="...");  # Dosya seç butonu
        self.btn_browse_icon.clicked.connect(self._pick_icon)

        top_icon = QtWidgets.QHBoxLayout()          # İkon satırı: yol + ...
        top_icon.addWidget(self.le_icon, 1)
        top_icon.addWidget(self.btn_browse_icon)

        self.cb_type = QtWidgets.QComboBox(); self.cb_type.addItems(["open", "keys"])  # Tür seçimi
        self.le_target = QtWidgets.QLineEdit()      # open için hedef
        self.le_keys   = QtWidgets.QLineEdit()      # keys için kombinasyonlar
        self.le_categories = QtWidgets.QLineEdit()  # Virgüllü kategori
        cat_help = QtWidgets.QLabel("Kategoriler (virgülle ayırın): Örn: Dev,Sosyal")  # Yardım metni

        # Form yerleşimi
        form = QtWidgets.QFormLayout()
        form.addRow("Ad / Tooltip:", self.le_label)
        form.addRow("İkon yolu:", top_icon)
        form.addRow("Tip:", self.cb_type)
        form.addRow("Target (open):", self.le_target)
        form.addRow("Keys (keys):", self.le_keys)
        form.addRow(cat_help)
        form.addRow("Kategoriler:", self.le_categories)

        # Butonlar
        self.btn_ok = QtWidgets.QPushButton("Kaydet")
        self.btn_cancel = QtWidgets.QPushButton("Vazgeç")
        self.btn_ok.setDefault(True); self.btn_ok.setAutoDefault(True)     # Enter = Kaydet
        self.btn_cancel.setAutoDefault(False)                              # Enter'ı çalmaz
        # Metin alanlarında Enter'a basınca accept çalışsın
        for w in (self.le_label, self.le_icon, self.le_target, self.le_keys, self.le_categories):
            w.returnPressed.connect(self.accept)
        self.btn_ok.clicked.connect(self.accept)       # Kaydet -> accept
        self.btn_cancel.clicked.connect(self.reject)   # Vazgeç -> reject

        btns = QtWidgets.QHBoxLayout()                 # Alt buton barı
        btns.addStretch(1); btns.addWidget(self.btn_cancel); btns.addWidget(self.btn_ok)

        lay = QtWidgets.QVBoxLayout(self)              # Ana layout
        lay.addLayout(form); lay.addStretch(1); lay.addLayout(btns)

        if data:                                       # Düzenleme modunda alanları doldur
            self.le_label.setText(data.get("label", ""))
            self.le_icon.setText(data.get("icon", ""))
            self.cb_type.setCurrentText((data.get("type") or "open"))
            self.le_target.setText(data.get("target",""))
            self.le_keys.setText(",".join(data.get("keys", [])))
            self.le_categories.setText(",".join(data.get("categories", [])))

        self.cb_type.currentTextChanged.connect(self._toggle_fields)  # Tür değişince alanları aç/kapat
        self._toggle_fields()                                         # Başlangıçta uygula

    def _toggle_fields(self):
        """Tür 'open' ise target alanı açık, 'keys' ise keys alanı açık."""
        t = self.cb_type.currentText()
        self.le_target.setEnabled(t == "open")
        self.le_keys.setEnabled(t == "keys")

    def _pick_icon(self):
        """İkon dosyası seçici."""
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "İkon Seç", "", "Resimler (*.png *.ico *.jpg *.jpeg *.bmp)")
        if fn:
            self.le_icon.setText(fn)

    def data(self):
        """Dialogdan toplanan veriyi dict olarak döndür."""
        t = self.cb_type.currentText()
        cats = [c.strip() for c in self.le_categories.text().split(",") if c.strip()]
        keys = [k.strip() for k in self.le_keys.text().split(",") if k.strip()]
        d = {"label": self.le_label.text().strip(), "icon": self.le_icon.text().strip(),
             "type": t, "categories": cats}
        if t == "open": d["target"] = self.le_target.text().strip()
        else:           d["keys"]   = keys
        return d

# -------------------- Dialoglar: Profil Adı --------------------
class ProfileNameDialog(QtWidgets.QDialog):
    def __init__(self, title="Profil", initial=""):
        super().__init__()
        self.setWindowTitle(title); self.setModal(True)                           # Modal dialog
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)  # ? butonu yok

        self.le = QtWidgets.QLineEdit(); self.le.setText(initial)                 # İsim alanı
        self.le.returnPressed.connect(self.accept)                                 # Enter = Tamam
        self.btn_ok = QtWidgets.QPushButton("Tamam"); self.btn_ok.setDefault(True); self.btn_ok.setAutoDefault(True)
        self.btn_cancel = QtWidgets.QPushButton("Vazgeç"); self.btn_cancel.setAutoDefault(False)
        self.btn_ok.clicked.connect(self.accept); self.btn_cancel.clicked.connect(self.reject)

        form = QtWidgets.QFormLayout(); form.addRow("Profil Adı:", self.le)       # Form yerleşimi
        h = QtWidgets.QHBoxLayout(); h.addStretch(1); h.addWidget(self.btn_cancel); h.addWidget(self.btn_ok)
        lay = QtWidgets.QVBoxLayout(self); lay.addLayout(form); lay.addLayout(h)  # Ana yerleşim

    def text(self): return self.le.text().strip()                                 # Girilen metni döndür

# -------------------- Kart Bileşeni --------------------
class CardButton(QtWidgets.QPushButton):
    def __init__(self, data, palette):
        super().__init__()
        self.data = data                                  # Kartın bağlandığı action dict
        self.p = palette                                  # Tema paleti
        self.setCursor(QtCore.Qt.PointingHandCursor)      # El imleci
        self.setIconSize(QtCore.QSize(40, 40))            # İkon boyutu
        self.setMinimumSize(72, 72)                       # Minimum kart boyutu
        self.apply_style()                                 # Stil uygula
        label_text = data.get("label", "?")               # Tooltip/ad
        self.setToolTip(label_text)
        icon_path = data.get("icon")
        if icon_path and Path(icon_path).exists():
            self.setIcon(QtGui.QIcon(icon_path)); self.setText("")  # İkon varsa yazı yok
        else:
            self.setText(label_text)                                   # İkon yoksa yazıyı göster
        self.clicked.connect(lambda: run_action(self.data))            # Tıklanınca aksiyonu çalıştır

    def apply_style(self):
        """Kartın QSS stili (tema renkleriyle)."""
        p = self.p
        self.setStyleSheet(f"""
            QPushButton {{
                background:{p['card_bg']};
                border:1px solid {p['card_border']};
                border-radius:12px;
                padding:12px;
                text-align:center;
                color:{p['text_color']};
                font-size:13px;
            }}
            QPushButton:hover {{ background:{p['card_hover']}; }}
        """)

    def contextMenuEvent(self, e: QtGui.QContextMenuEvent):
        """Sağ tık menüsü: Düzenle / Sil."""
        m = QtWidgets.QMenu(self)
        act_edit = m.addAction("Düzenle")
        act_del  = m.addAction("Sil")
        a = m.exec_(e.globalPos())
        mw = self.window()
        if a == act_edit and hasattr(mw, "edit_card"): mw.edit_card(self)   # Ana penceredeki metotlar
        elif a == act_del and hasattr(mw, "delete_card"): mw.delete_card(self)

# -------------------- Ana Pencere --------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)                        # Başlık
        self.resize(760, 480)                                # Pencere boyutu
        self.setMinimumSize(600, 380)                        # Minimum boyut
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)  # Çerçevesiz pencere

        # Ayarlar (QSettings)
        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme", "dark")    # "dark" | "light" varsayılan dark
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)  # Sağ üst başla
        self.saved_monitor_name = self.settings.value("monitor_name", "", type=str)     # Tercih edilen ekran
        self.minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool) # Kapatınca tepsiye
        self.enable_global_hotkey = self.settings.value("enable_global_hotkey", True, type=bool)  # Global hotkey
        self.fullscreen_mode = self.settings.value("fullscreen_mode", False, type=bool) # Tam ekran modu
        self.always_on_top = self.settings.value("always_on_top", False, type=bool)     # Üstte tut

        self.palette = DARK if self.theme == "dark" else LIGHT   # Geçerli palet
        self.store = load_config()                                # actions.json yükle
        self.active_profile = self.store.get("active_profile") or "Default"             # Aktif profil adı
        if self.active_profile not in self.store.get("profiles", {}):                   # Yoksa ilk profil
            self.active_profile = next(iter(self.store.get("profiles", {"Default":{}}).keys()))

        self._build_topbar()                         # Üst çubuk
        self._build_central()                        # Sol menü + içerik

        self._allow_close = False                    # Tepsiye gizleme kontrolü
        self._tray_tip_shown = False
        self._setup_tray()                           # Sistem tepsisi

        self._apply_theme()                          # Tema uygula
        self._update_toolbar_icons()                 # Tema/pozisyon ikonlarını güncelle
        self._rebuild_cards()                        # Kartları çiz

        self._rebuild_monitor_menu()                 # Monitör menüsü
        self._build_settings_menu()                  # Ayarlar menüsü
        self._build_profile_menu()                   # Profil menüsü

        QtCore.QTimer.singleShot(0, self._place_on_start)  # İlk konumlandırma
        self._apply_always_on_top(self.always_on_top)      # Üstte tut ayarı

        self._hotkey_registered = False
        if self.enable_global_hotkey:
            self._register_global_hotkey()          # Ctrl+V+D
        if self.fullscreen_mode:
            self._enter_fullscreen()                # Tam ekran aç

        # Ekranlar değişince menüyü güncel tut
        QtWidgets.QApplication.instance().screenAdded.connect(lambda s: self._rebuild_monitor_menu())
        QtWidgets.QApplication.instance().screenRemoved.connect(lambda s: self._rebuild_monitor_menu())

        # Toggle başlangıç durumları
        self.btn_theme.setChecked(self.theme == "dark")
        self.btn_pos.setChecked(self.start_top_right)

    # -------- Üst Bar (başlık + logo + butonlar) --------
    def _build_topbar(self):
        self.titleBar = QtWidgets.QWidget()          # Özel başlık alanı
        self.titleBar.setFixedHeight(40)
        h = QtWidgets.QHBoxLayout(self.titleBar); h.setContentsMargins(8,0,8,0); h.setSpacing(6)

        self.logo_label = QtWidgets.QLabel(); self.logo_label.setFixedSize(22, 22)  # Logo
        app_icon = QtGui.QIcon("icons/app.ico")
        if not app_icon.isNull(): self.logo_label.setPixmap(app_icon.pixmap(22, 22))
        h.addWidget(self.logo_label)

        self.lbl_title = QtWidgets.QLabel(APP_NAME)  # Uygulama adı
        self.lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-weight:600;")
        self.lbl_title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.btn_min = QtWidgets.QToolButton()       # Küçült
        self.btn_min.setIcon(QtGui.QIcon("icons/minimize.png")); self.btn_min.setIconSize(QtCore.QSize(16,16))
        self.btn_min.setToolTip("Küçült"); self.btn_min.clicked.connect(self.showMinimized)

        self.btn_close = QtWidgets.QToolButton()     # Kapat
        self.btn_close.setIcon(QtGui.QIcon("icons/exit.png")); self.btn_close.setIconSize(QtCore.QSize(16,16))
        self.btn_close.setToolTip("Kapat"); self.btn_close.clicked.connect(self.close)

        h.addWidget(self.lbl_title, 1)               # Başlığı ortala
        h.addWidget(self.btn_min)                    # Sağdaki butonlar
        h.addWidget(self.btn_close)

        self._drag = False; self._drag_offset = QtCore.QPoint()  # Sürükleme için değişkenler
        self.titleBar.installEventFilter(self)       # Event filter ile sürükleme

        self.status = self.statusBar(); self.status.setSizeGripEnabled(False)  # Status bar
        self._update_statusbar_text()

    def eventFilter(self, obj, ev):
        """Üst çubuğu fare ile sürükleyebilmek için event filter."""
        if obj is self.titleBar:
            if self.isFullScreen(): return False
            if ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.LeftButton:
                self._drag = True; self._drag_offset = ev.globalPos() - self.frameGeometry().topLeft(); return True
            elif ev.type() == QtCore.QEvent.MouseMove and self._drag and (ev.buttons() & QtCore.Qt.LeftButton):
                self.move(ev.globalPos() - self._drag_offset); return True
            elif ev.type() == QtCore.QEvent.MouseButtonRelease:
                self._drag = False; return True
        return super().eventFilter(obj, ev)

    def _update_statusbar_text(self):
        """Status bar bilgisini ve rengini ayarla."""
        self.status.setStyleSheet(f"color:{self.palette['text_color']}; font-size:12px;")
        self.status.showMessage("ViperaDev | v1.4.5")

    # -------- Orta Alan (sol menü + sağ içerik) --------
    def _build_central(self):
        root = QtWidgets.QWidget(); self.setCentralWidget(root)   # Kök widget
        h = QtWidgets.QVBoxLayout(root); h.setContentsMargins(0,0,0,0); h.setSpacing(0)
        h.addWidget(self.titleBar)                                 # En üstte başlık

        content = QtWidgets.QWidget(); h2 = QtWidgets.QHBoxLayout(content)  # Yatay: sol menü + içerik
        h2.setContentsMargins(0,0,0,0); h2.setSpacing(0)

        self.sidebar = QtWidgets.QFrame(); self.sidebar.setFixedWidth(56)   # Sol ikon menü
        v = QtWidgets.QVBoxLayout(self.sidebar); v.setContentsMargins(6,6,6,6); v.setSpacing(6)

        # Sol menü butonları (ikon-only). Aşağıdakiler aynı yapıda; her biri tooltip + işlev.
        self.btn_profile = self._sbtn("icons/user.png", "Profiller"); self.btn_profile.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_profile.setMenu(QtWidgets.QMenu(self)); v.addWidget(self.btn_profile)

        self.btn_theme = self._sbtn("", "Tema (Aç/Kapa)"); self.btn_theme.setCheckable(True)
        self.btn_theme.toggled.connect(self._toggle_theme); v.addWidget(self.btn_theme)

        self.btn_pos = self._sbtn("", "Pencere Konumu"); self.btn_pos.setCheckable(True)
        self.btn_pos.toggled.connect(self._toggle_topright); v.addWidget(self.btn_pos)

        self.btn_monitor = self._sbtn("icons/screen.png", "Monitör"); self.btn_monitor.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_monitor.setMenu(QtWidgets.QMenu(self)); v.addWidget(self.btn_monitor)

        self.btn_settings = self._sbtn("icons/settings.png", "Ayarlar"); self.btn_settings.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_settings.setMenu(QtWidgets.QMenu(self)); v.addWidget(self.btn_settings)

        self.btn_reload = self._sbtn("icons/reload.png", "Yeniden Yükle"); self.btn_reload.clicked.connect(self._reload_config); v.addWidget(self.btn_reload)
        self.btn_cfg = self._sbtn("icons/jsondocument.png", "actions.json'i Aç"); self.btn_cfg.clicked.connect(self._open_config); v.addWidget(self.btn_cfg)
        self.btn_add = self._sbtn("icons/plus.png", "Yeni Kısayol"); self.btn_add.clicked.connect(self.add_shortcut); v.addWidget(self.btn_add)

        v.addStretch(1)                                            # Alta it

        right = QtWidgets.QWidget(); right.setObjectName("RightArea")  # Sağ taraf: arama + grid
        vr = QtWidgets.QVBoxLayout(right); vr.setContentsMargins(8,6,8,8); vr.setSpacing(6)

        top_tools = QtWidgets.QHBoxLayout()                        # Üst araçlar
        self.search = QtWidgets.QLineEdit(); self.search.setPlaceholderText("Ara...")  # Arama kutusu
        self.search.textChanged.connect(self._rebuild_cards)       # Yazdıkça filtrele
        self.category = QtWidgets.QComboBox(); self.category.addItem("Tümü")           # Kategori seçici
        self.category.currentTextChanged.connect(self._rebuild_cards)
        top_tools.addWidget(self.search, 2); top_tools.addWidget(self.category, 1)     # Yerleşim oranları
        vr.addLayout(top_tools)

        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)  # Kaydırma alanı
        self.canvas = QtWidgets.QWidget(); self.canvas.setObjectName("Canvas")        # Grid taşıyıcısı
        self.grid = QtWidgets.QGridLayout(self.canvas); self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setHorizontalSpacing(10); self.grid.setVerticalSpacing(10)
        self.scroll.setWidget(self.canvas); vr.addWidget(self.scroll, 1)               # Scroll içine yerleştir

        h2.addWidget(self.sidebar); h2.addWidget(right, 1)         # Sol menü + sağ içerik
        h.addWidget(content, 1)                                     # İçeriği ekle

    def _sbtn(self, icon_path: str, tip: str):
        """Sol menüde kullanılan küçük ikon buton üretici."""
        b = QtWidgets.QToolButton()
        b.setIcon(QtGui.QIcon(icon_path) if icon_path else QtGui.QIcon())
        b.setIconSize(QtCore.QSize(18,18))
        b.setFixedSize(44, 36)
        b.setToolTip(tip)
        b.setAutoRaise(True)                                        # Düz görünüm
        return b

    # -------------------- Sistem Tepsisi --------------------
    def _setup_tray(self):
        icon_path = "icons/app.ico"
        self.tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon(icon_path), self)   # Tray ikonu
        self.tray.setToolTip(f"{APP_NAME} arka planda çalışıyor")
        menu = QtWidgets.QMenu()                                              # Tray menüsü
        act_show = menu.addAction("Göster"); act_show.triggered.connect(self._restore_from_tray)
        menu.addSeparator(); act_quit = menu.addAction("Çıkış");  act_quit.triggered.connect(self._quit_from_tray)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated); self.tray.show()

    def _tray_activated(self, reason):
        """Tepsi simgesine çift tıklayınca pencereyi göster."""
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick: self._restore_from_tray()
    def _restore_from_tray(self): self.show(); self.raise_(); self.activateWindow()  # Göster ve odak
    def _quit_from_tray(self): self._allow_close = True; QtWidgets.qApp.quit()       # Çıkış
    def closeEvent(self, event: QtGui.QCloseEvent):
        """Kapatınca tepsiye gizle / tamamen çık."""
        if hasattr(self, "_allow_close") and self._allow_close:
            return super().closeEvent(event)
        if self.minimize_to_tray:
            event.ignore(); self.hide()
            if not getattr(self, "_tray_tip_shown", False) and self.tray.isVisible():
                try:
                    self.tray.showMessage(APP_NAME,"Arka planda çalışmayı sürdürüyor.",QtWidgets.QSystemTrayIcon.Information, 3000)
                except Exception: pass
                self._tray_tip_shown = True
        else:
            self._allow_close = True; QtWidgets.qApp.quit()

    # -------------------- Tema Uygulama (QSS) --------------------
    def _apply_theme(self):
        self.palette = DARK if self.theme == "dark" else LIGHT      # Paleti seç

        # Üst bar ve sidebar renkleri
        self.titleBar.setStyleSheet(f"background:{self.palette['bg']};")
        self.lbl_title.setStyleSheet(f"color:{self.palette['fg']}; font-weight:600;")
        self.sidebar.setStyleSheet(f"QFrame {{ background: {self.palette['sidebar_bg']}; border-right:1px solid {self.palette['sidebar_border']}; }}")

        base_bg    = self.palette['card_bg']        # Giriş/kutu arka planı
        base_fg    = self.palette['text_color']     # Yazı rengi
        border_col = self.palette['card_border']    # Kenarlık
        hover_bg   = self.palette['card_hover']     # Hover
        win_bg     = self.palette['bg']             # Pencere arka planı

        # Uygulama geneli QSS
        app_qss = f"""
        QMainWindow {{ background:{win_bg}; }}
        #RightArea {{ background:{win_bg}; }}
        #Canvas {{ background: transparent; }}
        QScrollArea {{ background: transparent; border: 0; }}
        QScrollArea > viewport {{ background: transparent; }}

        QLineEdit {{
            background: {base_bg};
            color: {base_fg};
            border: 1px solid {border_col};
            border-radius: 6px;
            padding: 6px 8px;
            selection-background-color: {hover_bg};
            selection-color: {base_fg};
        }}

        QComboBox {{
            background: {base_bg};
            color: {base_fg};
            border: 1px solid {border_col};
            border-radius: 6px;
            padding: 4px 8px;
        }}
        QComboBox::drop-down {{ width: 24px; border-left: 1px solid {border_col}; }}
        QComboBox QAbstractItemView {{
            background: {base_bg};
            color: {base_fg};
            border: 1px solid {border_col};
            selection-background-color: {hover_bg};
            selection-color: {base_fg};
            outline: none;
        }}

        QPushButton {{
            background: {base_bg};
            color: {base_fg};
            border: 1px solid {border_col};
            border-radius: 8px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{ background: {hover_bg}; }}
        QPushButton:default {{ border: 1px solid #60a5fa; }}

        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {border_col}; min-height: 24px; border-radius: 4px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """
        QtWidgets.QApplication.instance().setStyleSheet(app_qss)    # QSS uygula

        # Kart stillerini güncelle
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CardButton):
                w.p = self.palette; w.apply_style()

        self._update_statusbar_text()
        self._update_toolbar_icons()

    def _update_toolbar_icons(self):
        """Tema ve pozisyon ikonlarını temaya göre ayarla."""
        theme_icon = "icons/dark-theme.png" if self.theme == "dark" else "icons/light-theme.png"
        self.btn_theme.setIcon(QtGui.QIcon(theme_icon))
        pos_icon = "icons/topright.png" if self.start_top_right else "icons/free.png"
        self.btn_pos.setIcon(QtGui.QIcon(pos_icon))

    # -------------------- Menüler --------------------
    def _rebuild_monitor_menu(self):
        """Monitör seçim menüsünü yeniden oluştur."""
        m = QtWidgets.QMenu(self)
        group = QtWidgets.QActionGroup(m); group.setExclusive(True)
        selected_action = None
        for s in QtWidgets.QApplication.screens():               # Tüm ekranlar
            geo = s.geometry()
            label = f"{s.name()}  ({geo.width()}×{geo.height()})"
            if s == QtWidgets.QApplication.primaryScreen(): label = "⭐ " + label
            act = QtWidgets.QAction(label, m, checkable=True); act.setData(s.name())
            m.addAction(act); group.addAction(act)
            if self.saved_monitor_name and s.name() == self.saved_monitor_name: selected_action = act
        m.addSeparator()
        act_auto = QtWidgets.QAction("Otomatik (birincil)", m, checkable=True); act_auto.setData("")
        m.addAction(act_auto); group.addAction(act_auto)
        (selected_action or act_auto).setChecked(True)           # Seçili aksiyon
        group.triggered.connect(self._on_monitor_chosen)
        self.btn_monitor.setMenu(m)

    def _build_settings_menu(self):
        """Ayarlar menüsü (tepsi, başlangıç, hotkey, tam ekran, üstte)."""
        m = QtWidgets.QMenu(self)
        act_min_to_tray = QtWidgets.QAction("Kapatınca tepsiye gizle", m, checkable=True)
        act_min_to_tray.setChecked(self.minimize_to_tray)
        act_min_to_tray.toggled.connect(self._toggle_minimize_to_tray); m.addAction(act_min_to_tray)

        act_startup = QtWidgets.QAction("Windows ile başlat", m, checkable=True)
        act_startup.setChecked(self._is_startup_enabled())
        act_startup.toggled.connect(lambda c: self._set_startup(c)); m.addAction(act_startup)

        act_hotkey = QtWidgets.QAction("Kısayol ile aç (Ctrl+V+D)", m, checkable=True)
        act_hotkey.setChecked(self.enable_global_hotkey)
        act_hotkey.toggled.connect(self._toggle_global_hotkey); m.addAction(act_hotkey)

        act_fullscreen = QtWidgets.QAction("Tam ekran modu", m, checkable=True)
        act_fullscreen.setChecked(self.fullscreen_mode)
        act_fullscreen.toggled.connect(self._toggle_fullscreen); m.addAction(act_fullscreen)

        act_top = QtWidgets.QAction("Her zaman üstte", m, checkable=True)
        act_top.setChecked(self.always_on_top)
        act_top.toggled.connect(self._toggle_always_on_top); m.addAction(act_top)
        self.btn_settings.setMenu(m)

    def _build_profile_menu(self):
        """Profil seçimi/oluşturma/yeniden adlandır/sil menüsü."""
        m = QtWidgets.QMenu(self)
        group = QtWidgets.QActionGroup(m); group.setExclusive(True)
        selected = None
        for name in self.store.get("profiles", {}).keys():
            act = QtWidgets.QAction(name, m, checkable=True); act.setData(name)
            if name == self.active_profile: selected = act
            m.addAction(act); group.addAction(act)
        if selected: selected.setChecked(True)
        group.triggered.connect(self._on_profile_chosen)
        m.addSeparator()
        m.addAction("Yeni Profil Oluştur", self._new_profile)
        m.addAction("Profili Yeniden Adlandır", self._rename_profile)
        m.addAction("Profili Sil", self._delete_profile)
        self.btn_profile.setMenu(m)

    # -------------------- Profil İşlemleri --------------------
    def _on_profile_chosen(self, act: QtWidgets.QAction):
        """Menüden başka profil seçilince."""
        name = act.data()
        if name and name in self.store.get("profiles", {}):
            self.active_profile = name; self.store["active_profile"] = name
            _save_config(self.store); self._rebuild_cards()

    def _new_profile(self):
        """Yeni profil oluştur."""
        dlg = ProfileNameDialog("Yeni Profil")
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            name = dlg.text()
            if not name: return
            if name in self.store.get("profiles", {}):
                QtWidgets.QMessageBox.information(self, "Bilgi", "Bu isimde profil zaten var."); return
            self.store["profiles"][name] = {"buttons": []}
            self.store["active_profile"] = name; self.active_profile = name
            _save_config(self.store); self._build_profile_menu(); self._rebuild_cards()

    def _rename_profile(self):
        """Aktif profili yeniden adlandır."""
        cur = self.active_profile
        dlg = ProfileNameDialog("Profili Yeniden Adlandır", cur)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            new = dlg.text()
            if not new or new == cur: return
            if new in self.store["profiles"]:
                QtWidgets.QMessageBox.information(self, "Bilgi", "Bu isimde profil zaten var."); return
            self.store["profiles"][new] = self.store["profiles"].pop(cur)
            self.active_profile = new; self.store["active_profile"] = new
            _save_config(self.store); self._build_profile_menu(); self._rebuild_cards()

    def _delete_profile(self):
        """Aktif profili sil (en az bir profil kalmalı)."""
        if len(self.store.get("profiles", {})) <= 1:
            QtWidgets.QMessageBox.information(self, "Bilgi", "Son profili silemezsiniz."); return
        ret = QtWidgets.QMessageBox.question(self, "Onay", f"'{self.active_profile}' profilini silmek istiyor musunuz?")
        if ret != QtWidgets.QMessageBox.Yes: return
        self.store["profiles"].pop(self.active_profile, None)
        self.active_profile = next(iter(self.store["profiles"].keys()))
        self.store["active_profile"] = self.active_profile
        _save_config(self.store); self._build_profile_menu(); self._rebuild_cards()

    # -------------------- Kısayol CRUD --------------------
    def add_shortcut(self):
        """Yeni kart ekle (dialog)."""
        dlg = ShortcutEditor(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            data = dlg.data()
            self.store["profiles"][self.active_profile]["buttons"].append(data)
            _save_config(self.store); self._rebuild_cards()

    def edit_card(self, card_btn: CardButton):
        """Kart verisini düzenle (dialog)."""
        data = card_btn.data
        dlg = ShortcutEditor(self, data)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            newdata = dlg.data()
            arr = self.store["profiles"][self.active_profile]["buttons"]
            for i, b in enumerate(arr):
                if b is data: arr[i] = newdata; break
            _save_config(self.store); self._rebuild_cards()

    def delete_card(self, card_btn: CardButton):
        """Kartı sil."""
        arr = self.store["profiles"][self.active_profile]["buttons"]
        for i, b in enumerate(arr):
            if b is card_btn.data: arr.pop(i); break
        _save_config(self.store); self._rebuild_cards()

    # -------------------- Pencere Konumu --------------------
    def _place_on_start(self):
        """Açılışta konumlandırma (sağ üst veya merkez)."""
        (self._move_to_selected_screen_top_right if self.start_top_right else self._center_on_selected_screen)()

    def _screen_geom(self):
        """Seçili/varsayılan ekranın geometri bilgisini al."""
        target = None
        if self.saved_monitor_name:
            for s in QtWidgets.QApplication.screens():
                if s.name() == self.saved_monitor_name: target = s; break
        if not target: target = QtWidgets.QApplication.primaryScreen()
        return target.availableGeometry() if target else None

    def _move_to_selected_screen_top_right(self):
        """Seçili ekranın sağ üstüne taşı."""
        g = self._screen_geom()
        if not g: return
        self.move(g.right() - self.width(), g.top())

    def _center_on_selected_screen(self):
        """Seçili ekranın ortasına yerleştir."""
        g = self._screen_geom()
        if not g: return
        cx = g.center().x() - self.width()//2; cy = g.center().y() - self.height()//2
        self.move(cx, cy)

    # -------------------- Grid & Filtreleme --------------------
    def _clear_grid(self):
        """Grid içindeki tüm kartları kaldır."""
        while self.grid.count():
            item = self.grid.takeAt(0); w = item.widget()
            if w: w.deleteLater()

    def _gather_categories(self, buttons):
        """Butonlardan benzersiz kategori listesi üret."""
        cats = set()
        for b in buttons:
            for c in b.get("categories", []):
                if c: cats.add(c)
        return sorted(list(cats))

    def _rebuild_cards(self):
        """Arama ve kategoriye göre kartları yeniden oluştur."""
        self._clear_grid()
        buttons = self.store["profiles"].get(self.active_profile, {}).get("buttons", [])

        # Kategori combobox'ını mevcut seçimi koruyarak yenile
        sel_prev = self.category.currentText() if self.category.count() else "Tümü"
        self.category.blockSignals(True); self.category.clear(); self.category.addItem("Tümü")
        for c in self._gather_categories(buttons): self.category.addItem(c)
        idx = self.category.findText(sel_prev); self.category.setCurrentIndex(idx if idx >= 0 else 0)
        self.category.blockSignals(False)

        # Filtreleme
        q = (self.search.text() or "").lower()
        cat = self.category.currentText()
        filtered = []
        for b in buttons:
            if q:
                txt = (b.get("label","") + " " + b.get("target","") + " " + " ".join(b.get("categories",[]))).lower()
                if q not in txt: continue
            if cat != "Tümü" and cat not in b.get("categories", []): continue
            filtered.append(b)

        # Grid'e yerleştir (dinamik kolon sayısı)
        btn_w = 90; gap = 12
        inner_w = max(300, self.width() - self.sidebar.width() - 60)
        cols = max(3, min(8, (inner_w + gap) // (btn_w + gap)))
        row = col = 0
        for b in filtered:
            card = CardButton(b, self.palette)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols: col = 0; row += 1

        self.status.showMessage(f"{len(filtered)} / {len(buttons)} öğe")  # Bilgi ver

    # -------------------- Tema & Diğer Ayarlar --------------------
    def _toggle_theme(self, checked: bool):
        """Tema değiştir (toggle)."""
        self.theme = "dark" if checked else "light"
        self.settings.setValue("theme", self.theme)
        self._apply_theme()

    def _toggle_topright(self, checked: bool):
        """Başlangıç konum modunu değiştir ve anında uygula."""
        self.start_top_right = checked; self.settings.setValue("start_top_right", checked)
        (self._move_to_selected_screen_top_right if checked else self._center_on_selected_screen)()
        self._update_toolbar_icons()

    def _toggle_minimize_to_tray(self, checked: bool):
        """Kapatınca tepsiye gizleme ayarı."""
        self.minimize_to_tray = checked; self.settings.setValue("minimize_to_tray", checked)

    def _is_startup_enabled(self):
        """Windows başlangıçta çalışıyor mu? (.lnk var mı)."""
        try: return os.path.exists(APP_SHORTCUT)
        except Exception: return False

    def _set_startup(self, enable: bool):
        """Başlangıca ekle/çıkar (winshell ile .lnk oluştur)."""
        try:
            if enable:
                if not ensure_winshell_installed(self):
                    self._build_settings_menu(); return
                import winshell  # noqa
                os.makedirs(STARTUP_FOLDER, exist_ok=True)
                exe_path, args = _launcher_paths()
                icon_loc = (os.path.abspath("icons/app.ico"), 0) if os.path.exists("icons/app.ico") else (exe_path, 0)
                with winshell.shortcut(APP_SHORTCUT) as link:
                    link.path = exe_path; link.arguments = args
                    link.description = f"{APP_NAME} - Masaüstü Paneli"; link.icon_location = icon_loc
            else:
                if os.path.exists(APP_SHORTCUT): os.remove(APP_SHORTCUT)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Hata", f"Başlangıç ayarı değiştirilemedi:\n{e}")
        finally:
            self._build_settings_menu()

    def _toggle_global_hotkey(self, checked: bool):
        """Ctrl+V+D global kısayolunu aç/kapat."""
        self.enable_global_hotkey = checked; self.settings.setValue("enable_global_hotkey", checked)
        if checked: self._register_global_hotkey()
        else:
            try:
                if getattr(self, "_hotkey_registered", False):
                    keyboard.remove_hotkey(self._hotkey_handle); self._hotkey_registered = False
            except Exception: pass

    def _register_global_hotkey(self):
        """Kısayolu kayıt et ve pencereyi gizle/göster yap."""
        try:
            def toggle_show():
                if self.isHidden(): self.show(); self.raise_(); self.activateWindow()
                else: self.hide()
            self._hotkey_handle = keyboard.add_hotkey("ctrl+v+d", toggle_show, suppress=False, trigger_on_release=True)
            self._hotkey_registered = True
        except Exception:
            self._hotkey_registered = False

    def _toggle_fullscreen(self, checked: bool):
        """Tam ekran modunu aç/kapat."""
        self.fullscreen_mode = checked; self.settings.setValue("fullscreen_mode", checked)
        self._enter_fullscreen() if checked else self._leave_fullscreen()

    def _enter_fullscreen(self): self.showFullScreen()   # Tam ekran
    def _leave_fullscreen(self): self.showNormal()       # Normal pencere

    def _toggle_always_on_top(self, checked: bool):
        """Her zaman üstte ayarı."""
        self.always_on_top = checked; self.settings.setValue("always_on_top", checked)
        self._apply_always_on_top(checked)

    def _apply_always_on_top(self, enabled: bool):
        """Üstte tut bayrağını pencere bayraklarına uygula."""
        flags = self.windowFlags()
        flags = (flags | QtCore.Qt.WindowStaysOnTopHint) if enabled else (flags & ~QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlags(flags); self.show()

    def _on_monitor_chosen(self, action: QtWidgets.QAction):
        """Monitör menüsünden seçim yapıldığında kayıt ve yeniden konumlandır."""
        self.saved_monitor_name = action.data() or ""
        self.settings.setValue("monitor_name", self.saved_monitor_name)
        (self._move_to_selected_screen_top_right if self.start_top_right else self._center_on_selected_screen)()

    def _open_config(self):
        """actions.json dosyasını sistemde aç."""
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    def _reload_config(self):
        """JSON'u tekrar yükle ve UI'ı güncelle."""
        self.store = load_config()
        ap = self.store.get("active_profile", "Default")
        self.active_profile = ap if ap in self.store.get("profiles", {}) else next(iter(self.store.get("profiles", {"Default":{}}).keys()))
        self._build_profile_menu(); self._rebuild_cards()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")

# -------------------- Çalıştırma --------------------
def main():
    """Uygulama giriş noktası."""
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)  # Yüksek DPI ölçekleme
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)     # Yüksek DPI ikonlar

    app = QtWidgets.QApplication(sys.argv)                     # QApplication
    app.setOrganizationName(ORG); app.setApplicationName(APP_NAME)  # QSettings bağlamı
    app.setWindowIcon(QtGui.QIcon("icons/app.ico"))            # Uygulama ikonu

    w = MainWindow(); w.show()                                 # Ana pencereyi göster
    sys.exit(app.exec_())                                      # Event loop

if __name__ == "__main__":
    main()                                                     # Script doğrudan çalıştırıldıysa başlat
