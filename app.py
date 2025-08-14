# app.py — VipoDeck v1.4.5
# Tema: Karanlık + Aydınlık tam destek (kalıcı). Enter=Tamam düzeltmesi korunur.
# Diğerleri: Sol menü, profil yönetimi, kısayol CRUD, arama+kategori, tray, startup,
# global hotkey (Ctrl+V+D), tam ekran, her zaman üstte, monitör seçimi.

import sys, os, json, time, subprocess, webbrowser
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui, keyboard

APP_NAME   = "VipoDeck"
ORG        = "ViperaDev"
APP        = "VipoDeck"
CONFIG_PATH = Path(__file__).with_name("actions.json")

# Paletler (uyumlu ve yüksek kontrast)
LIGHT = {
    "bg": "#f5f7fa",
    "fg": "#1e293b",
    "muted": "#64748b",
    "card_bg": "#ffffff",
    "card_border": "#e2e8f0",
    "card_hover": "#eef2f7",
    "text_color": "#0b1220",
    "sidebar_bg": "rgba(0,0,0,0.03)",
    "sidebar_border": "rgba(0,0,0,0.08)"
}
DARK = {
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

STARTUP_FOLDER = os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)
APP_SHORTCUT = os.path.join(STARTUP_FOLDER, f"{APP_NAME}.lnk")

# ---------- helpers ----------
def _launcher_paths():
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    else:
        return sys.executable, f'"{os.path.abspath(sys.argv[0])}"'

def _load_raw_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_config(data: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _as_list_categories(v):
    if not v: return []
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return []

def _normalize_config():
    raw = _load_raw_config()
    if "profiles" not in raw or "active_profile" not in raw:
        buttons = raw.get("buttons", [])
        store = {"active_profile": "Default", "profiles": {"Default": {"buttons": buttons}}}
    else:
        store = raw
    # categories'i listeleştir
    for prof in store.get("profiles", {}).values():
        for b in prof.get("buttons", []):
            b["categories"] = _as_list_categories(b.get("categories"))
    _save_config(store)
    return store

def load_config():
    return _normalize_config()

def open_target(target: str):
    if not target: return
    if target.startswith(("http://", "https://")):
        webbrowser.open(target); return
    try: subprocess.Popen([target], shell=True)
    except Exception:
        try: webbrowser.open(target)
        except Exception: pass

def run_action(a: dict):
    t = (a.get("type") or "").lower()
    if t == "open":
        open_target(a.get("target", ""))
    elif t == "keys":
        time.sleep(0.03)
        seq = a.get("keys", [])
        if seq:
            try: pyautogui.hotkey(*seq)
            except Exception: pass

def ensure_winshell_installed(parent=None) -> bool:
    try:
        import winshell  # noqa
        return True
    except Exception:
        pass
    ret = QtWidgets.QMessageBox.question(
        parent, "Gerekli Paket",
        "Windows ile başlat için 'winshell' paketi gerekli. Kurulsun mu?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes
    )
    if ret != QtWidgets.QMessageBox.Yes:
        return False
    try:
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "winshell"])
    except Exception as e:
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QMessageBox.warning(parent, "Kurulum Hatası", f"winshell kurulamadı:\n{e}")
        return False
    finally:
        try: QtWidgets.QApplication.restoreOverrideCursor()
        except Exception: pass
    try:
        import winshell  # noqa
        return True
    except Exception:
        return False

# ---------- Dialoglar ----------
class ShortcutEditor(QtWidgets.QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Kısayol")
        self.setModal(True)
        self.resize(420, 320)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.le_label = QtWidgets.QLineEdit()
        self.le_icon  = QtWidgets.QLineEdit()
        self.btn_browse_icon = QtWidgets.QToolButton(text="..."); 
        self.btn_browse_icon.clicked.connect(self._pick_icon)

        top_icon = QtWidgets.QHBoxLayout()
        top_icon.addWidget(self.le_icon, 1)
        top_icon.addWidget(self.btn_browse_icon)

        self.cb_type = QtWidgets.QComboBox(); self.cb_type.addItems(["open", "keys"])
        self.le_target = QtWidgets.QLineEdit()
        self.le_keys   = QtWidgets.QLineEdit()
        self.le_categories = QtWidgets.QLineEdit()
        cat_help = QtWidgets.QLabel("Kategoriler (virgülle ayırın): Örn: Dev,Sosyal")

        form = QtWidgets.QFormLayout()
        form.addRow("Ad / Tooltip:", self.le_label)
        form.addRow("İkon yolu:", top_icon)
        form.addRow("Tip:", self.cb_type)
        form.addRow("Target (open):", self.le_target)
        form.addRow("Keys (keys):", self.le_keys)
        form.addRow(cat_help)
        form.addRow("Kategoriler:", self.le_categories)

        self.btn_ok = QtWidgets.QPushButton("Kaydet")
        self.btn_cancel = QtWidgets.QPushButton("Vazgeç")
        # Enter = Kaydet
        self.btn_ok.setDefault(True); self.btn_ok.setAutoDefault(True)
        self.btn_cancel.setAutoDefault(False)
        for w in (self.le_label, self.le_icon, self.le_target, self.le_keys, self.le_categories):
            w.returnPressed.connect(self.accept)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1); btns.addWidget(self.btn_cancel); btns.addWidget(self.btn_ok)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(form); lay.addStretch(1); lay.addLayout(btns)

        if data:
            self.le_label.setText(data.get("label", ""))
            self.le_icon.setText(data.get("icon", ""))
            self.cb_type.setCurrentText((data.get("type") or "open"))
            self.le_target.setText(data.get("target",""))
            self.le_keys.setText(",".join(data.get("keys", [])))
            self.le_categories.setText(",".join(data.get("categories", [])))

        self.cb_type.currentTextChanged.connect(self._toggle_fields)
        self._toggle_fields()

    def _toggle_fields(self):
        t = self.cb_type.currentText()
        self.le_target.setEnabled(t == "open")
        self.le_keys.setEnabled(t == "keys")

    def _pick_icon(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "İkon Seç", "", "Resimler (*.png *.ico *.jpg *.jpeg *.bmp)")
        if fn:
            self.le_icon.setText(fn)

    def data(self):
        t = self.cb_type.currentText()
        cats = [c.strip() for c in self.le_categories.text().split(",") if c.strip()]
        keys = [k.strip() for k in self.le_keys.text().split(",") if k.strip()]
        d = {"label": self.le_label.text().strip(), "icon": self.le_icon.text().strip(),
             "type": t, "categories": cats}
        if t == "open": d["target"] = self.le_target.text().strip()
        else:           d["keys"]   = keys
        return d

class ProfileNameDialog(QtWidgets.QDialog):
    def __init__(self, title="Profil", initial=""):
        super().__init__()
        self.setWindowTitle(title); self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.le = QtWidgets.QLineEdit(); self.le.setText(initial)
        self.le.returnPressed.connect(self.accept)  # Enter = Tamam
        self.btn_ok = QtWidgets.QPushButton("Tamam"); self.btn_ok.setDefault(True); self.btn_ok.setAutoDefault(True)
        self.btn_cancel = QtWidgets.QPushButton("Vazgeç"); self.btn_cancel.setAutoDefault(False)
        self.btn_ok.clicked.connect(self.accept); self.btn_cancel.clicked.connect(self.reject)

        form = QtWidgets.QFormLayout(); form.addRow("Profil Adı:", self.le)
        h = QtWidgets.QHBoxLayout(); h.addStretch(1); h.addWidget(self.btn_cancel); h.addWidget(self.btn_ok)
        lay = QtWidgets.QVBoxLayout(self); lay.addLayout(form); lay.addLayout(h)

    def text(self): return self.le.text().strip()

# ---------- Kart ----------
class CardButton(QtWidgets.QPushButton):
    def __init__(self, data, palette):
        super().__init__()
        self.data = data
        self.p = palette
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setIconSize(QtCore.QSize(40, 40))
        self.setMinimumSize(72, 72)
        self.apply_style()
        label_text = data.get("label", "?")
        self.setToolTip(label_text)
        icon_path = data.get("icon")
        if icon_path and Path(icon_path).exists():
            self.setIcon(QtGui.QIcon(icon_path)); self.setText("")
        else:
            self.setText(label_text)
        self.clicked.connect(lambda: run_action(self.data))

    def apply_style(self):
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
        m = QtWidgets.QMenu(self)
        act_edit = m.addAction("Düzenle")
        act_del  = m.addAction("Sil")
        a = m.exec_(e.globalPos())
        mw = self.window()
        if a == act_edit and hasattr(mw, "edit_card"): mw.edit_card(self)
        elif a == act_del and hasattr(mw, "delete_card"): mw.delete_card(self)

# ---------- Main ----------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(760, 480)
        self.setMinimumSize(600, 380)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)

        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme", "dark")  # "dark" | "light"
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)
        self.saved_monitor_name = self.settings.value("monitor_name", "", type=str)
        self.minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)
        self.enable_global_hotkey = self.settings.value("enable_global_hotkey", True, type=bool)
        self.fullscreen_mode = self.settings.value("fullscreen_mode", False, type=bool)
        self.always_on_top = self.settings.value("always_on_top", False, type=bool)

        self.palette = DARK if self.theme == "dark" else LIGHT
        self.store = load_config()
        self.active_profile = self.store.get("active_profile") or "Default"
        if self.active_profile not in self.store.get("profiles", {}):
            self.active_profile = next(iter(self.store.get("profiles", {"Default":{}}).keys()))

        self._build_topbar()
        self._build_central()

        self._allow_close = False
        self._tray_tip_shown = False
        self._setup_tray()

        self._apply_theme()
        self._update_toolbar_icons()
        self._rebuild_cards()

        self._rebuild_monitor_menu()
        self._build_settings_menu()
        self._build_profile_menu()

        QtCore.QTimer.singleShot(0, self._place_on_start)
        self._apply_always_on_top(self.always_on_top)

        self._hotkey_registered = False
        if self.enable_global_hotkey:
            self._register_global_hotkey()
        if self.fullscreen_mode:
            self._enter_fullscreen()

        QtWidgets.QApplication.instance().screenAdded.connect(lambda s: self._rebuild_monitor_menu())
        QtWidgets.QApplication.instance().screenRemoved.connect(lambda s: self._rebuild_monitor_menu())

        self.btn_theme.setChecked(self.theme == "dark")
        self.btn_pos.setChecked(self.start_top_right)

    # ---- ÜST BAR ----
    def _build_topbar(self):
        self.titleBar = QtWidgets.QWidget()
        self.titleBar.setFixedHeight(40)
        h = QtWidgets.QHBoxLayout(self.titleBar); h.setContentsMargins(8,0,8,0); h.setSpacing(6)

        self.logo_label = QtWidgets.QLabel(); self.logo_label.setFixedSize(22, 22)
        app_icon = QtGui.QIcon("icons/app.ico")
        if not app_icon.isNull(): self.logo_label.setPixmap(app_icon.pixmap(22, 22))
        h.addWidget(self.logo_label)

        self.lbl_title = QtWidgets.QLabel(APP_NAME)
        self.lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-weight:600;")
        self.lbl_title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.btn_min = QtWidgets.QToolButton()
        self.btn_min.setIcon(QtGui.QIcon("icons/minimize.png")); self.btn_min.setIconSize(QtCore.QSize(16,16))
        self.btn_min.setToolTip("Küçült"); self.btn_min.clicked.connect(self.showMinimized)

        self.btn_close = QtWidgets.QToolButton()
        self.btn_close.setIcon(QtGui.QIcon("icons/exit.png")); self.btn_close.setIconSize(QtCore.QSize(16,16))
        self.btn_close.setToolTip("Kapat"); self.btn_close.clicked.connect(self.close)

        h.addWidget(self.lbl_title, 1)
        h.addWidget(self.btn_min)
        h.addWidget(self.btn_close)

        self._drag = False; self._drag_offset = QtCore.QPoint()
        self.titleBar.installEventFilter(self)

        self.status = self.statusBar(); self.status.setSizeGripEnabled(False)
        self._update_statusbar_text()

    def eventFilter(self, obj, ev):
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
        self.status.setStyleSheet(f"color:{self.palette['text_color']}; font-size:12px;")
        self.status.showMessage("ViperaDev | v1.4.5")

    # ---- MERKEZ ----
    def _build_central(self):
        root = QtWidgets.QWidget(); self.setCentralWidget(root)
        h = QtWidgets.QVBoxLayout(root); h.setContentsMargins(0,0,0,0); h.setSpacing(0)
        h.addWidget(self.titleBar)

        content = QtWidgets.QWidget(); h2 = QtWidgets.QHBoxLayout(content)
        h2.setContentsMargins(0,0,0,0); h2.setSpacing(0)

        self.sidebar = QtWidgets.QFrame(); self.sidebar.setFixedWidth(56)
        v = QtWidgets.QVBoxLayout(self.sidebar); v.setContentsMargins(6,6,6,6); v.setSpacing(6)

        self.btn_profile = self._sbtn("icons/user.png", "Profiller")
        self.btn_profile.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_profile.setMenu(QtWidgets.QMenu(self)); v.addWidget(self.btn_profile)

        self.btn_theme = self._sbtn("", "Tema (Aç/Kapa)")
        self.btn_theme.setCheckable(True)
        self.btn_theme.toggled.connect(self._toggle_theme); v.addWidget(self.btn_theme)

        self.btn_pos = self._sbtn("", "Pencere Konumu")
        self.btn_pos.setCheckable(True)
        self.btn_pos.toggled.connect(self._toggle_topright); v.addWidget(self.btn_pos)

        self.btn_monitor = self._sbtn("icons/screen.png", "Monitör")
        self.btn_monitor.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_monitor.setMenu(QtWidgets.QMenu(self)); v.addWidget(self.btn_monitor)

        self.btn_settings = self._sbtn("icons/settings.png", "Ayarlar")
        self.btn_settings.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_settings.setMenu(QtWidgets.QMenu(self)); v.addWidget(self.btn_settings)

        self.btn_reload = self._sbtn("icons/reload.png", "Yeniden Yükle")
        self.btn_reload.clicked.connect(self._reload_config); v.addWidget(self.btn_reload)

        self.btn_cfg = self._sbtn("icons/jsondocument.png", "actions.json'i Aç")
        self.btn_cfg.clicked.connect(self._open_config); v.addWidget(self.btn_cfg)

        self.btn_add = self._sbtn("icons/plus.png", "Yeni Kısayol")
        self.btn_add.clicked.connect(self.add_shortcut); v.addWidget(self.btn_add)

        v.addStretch(1)

        right = QtWidgets.QWidget(); right.setObjectName("RightArea")
        vr = QtWidgets.QVBoxLayout(right); vr.setContentsMargins(8,6,8,8); vr.setSpacing(6)

        top_tools = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit(); self.search.setPlaceholderText("Ara...")
        self.search.textChanged.connect(self._rebuild_cards)
        self.category = QtWidgets.QComboBox(); self.category.addItem("Tümü")
        self.category.currentTextChanged.connect(self._rebuild_cards)
        top_tools.addWidget(self.search, 2); top_tools.addWidget(self.category, 1)
        vr.addLayout(top_tools)

        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.canvas = QtWidgets.QWidget(); self.canvas.setObjectName("Canvas")
        self.grid = QtWidgets.QGridLayout(self.canvas); self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setHorizontalSpacing(10); self.grid.setVerticalSpacing(10)
        self.scroll.setWidget(self.canvas); vr.addWidget(self.scroll, 1)

        h2.addWidget(self.sidebar); h2.addWidget(right, 1)
        h.addWidget(content, 1)

    def _sbtn(self, icon_path: str, tip: str):
        b = QtWidgets.QToolButton()
        b.setIcon(QtGui.QIcon(icon_path) if icon_path else QtGui.QIcon())
        b.setIconSize(QtCore.QSize(18,18))
        b.setFixedSize(44, 36)
        b.setToolTip(tip)
        b.setAutoRaise(True)
        return b

    # ---- Tray ----
    def _setup_tray(self):
        icon_path = "icons/app.ico"
        self.tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon(icon_path), self)
        self.tray.setToolTip(f"{APP_NAME} arka planda çalışıyor")
        menu = QtWidgets.QMenu()
        act_show = menu.addAction("Göster"); act_show.triggered.connect(self._restore_from_tray)
        menu.addSeparator(); act_quit = menu.addAction("Çıkış");  act_quit.triggered.connect(self._quit_from_tray)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated); self.tray.show()

    def _tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick: self._restore_from_tray()
    def _restore_from_tray(self): self.show(); self.raise_(); self.activateWindow()
    def _quit_from_tray(self): self._allow_close = True; QtWidgets.qApp.quit()
    def closeEvent(self, event: QtGui.QCloseEvent):
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

    # ---- Tema (UYGULAMA GENELİ QSS) ----
    def _apply_theme(self):
        self.palette = DARK if self.theme == "dark" else LIGHT

        # üst bar ve sidebar
        self.titleBar.setStyleSheet(f"background:{self.palette['bg']};")
        self.lbl_title.setStyleSheet(f"color:{self.palette['fg']}; font-weight:600;")
        self.sidebar.setStyleSheet(f"QFrame {{ background: {self.palette['sidebar_bg']}; border-right:1px solid {self.palette['sidebar_border']}; }}")

        base_bg    = self.palette['card_bg']
        base_fg    = self.palette['text_color']
        border_col = self.palette['card_border']
        hover_bg   = self.palette['card_hover']
        win_bg     = self.palette['bg']

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
        QtWidgets.QApplication.instance().setStyleSheet(app_qss)

        # kartları yenile
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CardButton):
                w.p = self.palette; w.apply_style()

        self._update_statusbar_text()
        self._update_toolbar_icons()

    def _update_toolbar_icons(self):
        theme_icon = "icons/dark-theme.png" if self.theme == "dark" else "icons/light-theme.png"
        self.btn_theme.setIcon(QtGui.QIcon(theme_icon))
        pos_icon = "icons/topright.png" if self.start_top_right else "icons/free.png"
        self.btn_pos.setIcon(QtGui.QIcon(pos_icon))

    # ---- Menüler ----
    def _rebuild_monitor_menu(self):
        m = QtWidgets.QMenu(self)
        group = QtWidgets.QActionGroup(m); group.setExclusive(True)
        selected_action = None
        for s in QtWidgets.QApplication.screens():
            geo = s.geometry()
            label = f"{s.name()}  ({geo.width()}×{geo.height()})"
            if s == QtWidgets.QApplication.primaryScreen(): label = "⭐ " + label
            act = QtWidgets.QAction(label, m, checkable=True); act.setData(s.name())
            m.addAction(act); group.addAction(act)
            if self.saved_monitor_name and s.name() == self.saved_monitor_name: selected_action = act
        m.addSeparator()
        act_auto = QtWidgets.QAction("Otomatik (birincil)", m, checkable=True); act_auto.setData("")
        m.addAction(act_auto); group.addAction(act_auto)
        (selected_action or act_auto).setChecked(True)
        group.triggered.connect(self._on_monitor_chosen)
        self.btn_monitor.setMenu(m)

    def _build_settings_menu(self):
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

    # ---- Profiller ----
    def _on_profile_chosen(self, act: QtWidgets.QAction):
        name = act.data()
        if name and name in self.store.get("profiles", {}):
            self.active_profile = name; self.store["active_profile"] = name
            _save_config(self.store); self._rebuild_cards()

    def _new_profile(self):
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
        if len(self.store.get("profiles", {})) <= 1:
            QtWidgets.QMessageBox.information(self, "Bilgi", "Son profili silemezsiniz."); return
        ret = QtWidgets.QMessageBox.question(self, "Onay", f"'{self.active_profile}' profilini silmek istiyor musunuz?")
        if ret != QtWidgets.QMessageBox.Yes: return
        self.store["profiles"].pop(self.active_profile, None)
        self.active_profile = next(iter(self.store["profiles"].keys()))
        self.store["active_profile"] = self.active_profile
        _save_config(self.store); self._build_profile_menu(); self._rebuild_cards()

    # ---- Kısayol CRUD ----
    def add_shortcut(self):
        dlg = ShortcutEditor(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            data = dlg.data()
            self.store["profiles"][self.active_profile]["buttons"].append(data)
            _save_config(self.store); self._rebuild_cards()

    def edit_card(self, card_btn: CardButton):
        data = card_btn.data
        dlg = ShortcutEditor(self, data)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            newdata = dlg.data()
            arr = self.store["profiles"][self.active_profile]["buttons"]
            for i, b in enumerate(arr):
                if b is data: arr[i] = newdata; break
            _save_config(self.store); self._rebuild_cards()

    def delete_card(self, card_btn: CardButton):
        arr = self.store["profiles"][self.active_profile]["buttons"]
        for i, b in enumerate(arr):
            if b is card_btn.data: arr.pop(i); break
        _save_config(self.store); self._rebuild_cards()

    # ---- Konum & pencere ----
    def _place_on_start(self):
        (self._move_to_selected_screen_top_right if self.start_top_right else self._center_on_selected_screen)()

    def _screen_geom(self):
        target = None
        if self.saved_monitor_name:
            for s in QtWidgets.QApplication.screens():
                if s.name() == self.saved_monitor_name: target = s; break
        if not target: target = QtWidgets.QApplication.primaryScreen()
        return target.availableGeometry() if target else None

    def _move_to_selected_screen_top_right(self):
        g = self._screen_geom()
        if not g: return
        self.move(g.right() - self.width(), g.top())

    def _center_on_selected_screen(self):
        g = self._screen_geom()
        if not g: return
        cx = g.center().x() - self.width()//2; cy = g.center().y() - self.height()//2
        self.move(cx, cy)

    # ---- Grid & filtre ----
    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0); w = item.widget()
            if w: w.deleteLater()

    def _gather_categories(self, buttons):
        cats = set()
        for b in buttons:
            for c in b.get("categories", []):
                if c: cats.add(c)
        return sorted(list(cats))

    def _rebuild_cards(self):
        self._clear_grid()
        buttons = self.store["profiles"].get(self.active_profile, {}).get("buttons", [])

        sel_prev = self.category.currentText() if self.category.count() else "Tümü"
        self.category.blockSignals(True); self.category.clear(); self.category.addItem("Tümü")
        for c in self._gather_categories(buttons): self.category.addItem(c)
        idx = self.category.findText(sel_prev); self.category.setCurrentIndex(idx if idx >= 0 else 0)
        self.category.blockSignals(False)

        q = (self.search.text() or "").lower()
        cat = self.category.currentText()
        filtered = []
        for b in buttons:
            if q:
                txt = (b.get("label","") + " " + b.get("target","") + " " + " ".join(b.get("categories",[]))).lower()
                if q not in txt: continue
            if cat != "Tümü" and cat not in b.get("categories", []): continue
            filtered.append(b)

        btn_w = 90; gap = 12
        inner_w = max(300, self.width() - self.sidebar.width() - 60)
        cols = max(3, min(8, (inner_w + gap) // (btn_w + gap)))
        row = col = 0
        for b in filtered:
            card = CardButton(b, self.palette)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols: col = 0; row += 1

        self.status.showMessage(f"{len(filtered)} / {len(buttons)} öğe")

    # ---- Tema & ayarlar ----
    def _toggle_theme(self, checked: bool):
        self.theme = "dark" if checked else "light"
        self.settings.setValue("theme", self.theme)
        self._apply_theme()

    def _toggle_topright(self, checked: bool):
        self.start_top_right = checked; self.settings.setValue("start_top_right", checked)
        (self._move_to_selected_screen_top_right if checked else self._center_on_selected_screen)()
        self._update_toolbar_icons()

    def _toggle_minimize_to_tray(self, checked: bool):
        self.minimize_to_tray = checked; self.settings.setValue("minimize_to_tray", checked)

    def _is_startup_enabled(self):
        try: return os.path.exists(APP_SHORTCUT)
        except Exception: return False

    def _set_startup(self, enable: bool):
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
        self.enable_global_hotkey = checked; self.settings.setValue("enable_global_hotkey", checked)
        if checked: self._register_global_hotkey()
        else:
            try:
                if getattr(self, "_hotkey_registered", False):
                    keyboard.remove_hotkey(self._hotkey_handle); self._hotkey_registered = False
            except Exception: pass

    def _register_global_hotkey(self):
        try:
            def toggle_show():
                if self.isHidden(): self.show(); self.raise_(); self.activateWindow()
                else: self.hide()
            self._hotkey_handle = keyboard.add_hotkey("ctrl+v+d", toggle_show, suppress=False, trigger_on_release=True)
            self._hotkey_registered = True
        except Exception:
            self._hotkey_registered = False

    def _toggle_fullscreen(self, checked: bool):
        self.fullscreen_mode = checked; self.settings.setValue("fullscreen_mode", checked)
        self._enter_fullscreen() if checked else self._leave_fullscreen()

    def _enter_fullscreen(self): self.showFullScreen()
    def _leave_fullscreen(self): self.showNormal()

    def _toggle_always_on_top(self, checked: bool):
        self.always_on_top = checked; self.settings.setValue("always_on_top", checked)
        self._apply_always_on_top(checked)

    def _apply_always_on_top(self, enabled: bool):
        flags = self.windowFlags()
        flags = (flags | QtCore.Qt.WindowStaysOnTopHint) if enabled else (flags & ~QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlags(flags); self.show()

    def _on_monitor_chosen(self, action: QtWidgets.QAction):
        self.saved_monitor_name = action.data() or ""
        self.settings.setValue("monitor_name", self.saved_monitor_name)
        (self._move_to_selected_screen_top_right if self.start_top_right else self._center_on_selected_screen)()

    def _open_config(self):
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    def _reload_config(self):
        self.store = load_config()
        ap = self.store.get("active_profile", "Default")
        self.active_profile = ap if ap in self.store.get("profiles", {}) else next(iter(self.store.get("profiles", {"Default":{}}).keys()))
        self._build_profile_menu(); self._rebuild_cards()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")

# ---------- run ----------
def main():
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORG); app.setApplicationName(APP_NAME)
    app.setWindowIcon(QtGui.QIcon("icons/app.ico"))

    w = MainWindow(); w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
