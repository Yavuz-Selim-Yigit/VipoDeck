# app.py — VipoDeck v1.5.0 (Profil Sistemi + Sol Menü) 
# Önceki özellikler: Her zaman üstte, Tam ekran, System Tray, Windows ile başlat, Global kısayol (Ctrl+V+D), Tema, Monitör seçimi, Sağ üst/Serbest konum
# Gereksinimler: PyQt5, PyAutoGUI, keyboard, winshell (opsiyonel, "Windows ile başlat" için)
# pip install PyQt5 pyautogui keyboard winshell

import sys, os, json, time, subprocess, webbrowser, shutil
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui, keyboard

APP_NAME   = "VipoDeck"
ORG        = "ViperaDev"
APP        = "VipoDeck"
ROOT_DIR   = Path(__file__).parent
CONFIG_PATH = ROOT_DIR / "actions.json"   # ilk ayar (Default profili üretirken kullanılabilir)
PROFILES_DIR = ROOT_DIR / "profiles"      # her profil için ayrı klasör
VERSION    = "v1.5.0"

LIGHT = {
    "bg": "#f5f7fa",
    "fg": "#1e293b",
    "muted": "#64748b",
    "card_bg": "#ffffff",
    "card_border": "#e2e8f0",
    "card_hover": "#f1f5f9",
    "text_color": "#000000"
}
DARK  = {
    "bg": "#0f172a",
    "fg": "#e2e8f0",
    "muted": "#94a3b8",
    "card_bg": "#1b2333",
    "card_border": "#2a3650",
    "card_hover": "#25324a",
    "text_color": "#ffffff"
}

# ---- Windows Startup (kısayol) sabitleri ----
STARTUP_FOLDER = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
APP_SHORTCUT = os.path.join(STARTUP_FOLDER, f"{APP_NAME}.lnk")

# ---------------- Yardımcılar ----------------
def _launcher_paths():
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    else:
        return sys.executable, f'"{os.path.abspath(sys.argv[0])}"'

def safe_read_json(path: Path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def safe_write_json(path: Path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def open_target(target: str):
    if not target:
        return
    if target.startswith(("http://", "https://")):
        webbrowser.open(target); return
    try:
        subprocess.Popen([target], shell=True)
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

# --- winshell yoksa otomatik kurma (Windows ile başlat için) ---
def ensure_winshell_installed(parent=None) -> bool:
    try:
        import winshell  # noqa: F401
        return True
    except Exception:
        pass

    ret = QtWidgets.QMessageBox.question(
        parent, "Gerekli Paket",
        "'Windows ile başlat' için 'winshell' gerekiyor.\nŞimdi kurulsun mu?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes,
    )
    if ret != QtWidgets.QMessageBox.Yes:
        return False

    try:
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "winshell"])
    except Exception as e:
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QMessageBox.warning(parent, "Kurulum Hatası", f"'winshell' kurulamadı:\n{e}\n\nElle kur:\n  pip install winshell")
        return False
    finally:
        try: QtWidgets.QApplication.restoreOverrideCursor()
        except Exception: pass

    try:
        import winshell  # noqa: F401
        return True
    except Exception:
        return False

# ---------------- Özel Üst Bar (tek satır) ----------------
class TitleBar(QtWidgets.QWidget):
    minimizeRequested = QtCore.pyqtSignal()
    closeRequested = QtCore.pyqtSignal()
    themeToggled = QtCore.pyqtSignal(bool)
    toprightToggled = QtCore.pyqtSignal(bool)
    openConfigRequested = QtCore.pyqtSignal()
    reloadRequested = QtCore.pyqtSignal()

    def __init__(self, title: str, icon_path: str = None, parent=None):
        super().__init__(parent)
        self._drag = False
        self._drag_offset = QtCore.QPoint()
        self.setFixedHeight(40)

        self.leftWrap = QtWidgets.QWidget()
        l = QtWidgets.QHBoxLayout(self.leftWrap)
        l.setContentsMargins(8, 0, 0, 0)
        l.setSpacing(6)

        self.appIcon = QtWidgets.QLabel()
        self.appIcon.setFixedSize(18, 18)
        if icon_path and Path(icon_path).exists():
            self.appIcon.setPixmap(QtGui.QPixmap(icon_path).scaled(18, 18, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        l.addWidget(self.appIcon)

        self.btnTheme = self._tool("", tooltip="Tema Değiştir")
        self.btnTheme.setCheckable(True)
        self.btnTheme.toggled.connect(self.themeToggled.emit)
        l.addWidget(self.btnTheme)

        self.btnTopRight = self._tool("", tooltip="Pencere Konumu")
        self.btnTopRight.setCheckable(True)
        self.btnTopRight.toggled.connect(self.toprightToggled.emit)
        l.addWidget(self.btnTopRight)

        self.btnMonitor = self._tool("icons/screen.png", tooltip="Monitör Seç")
        self.btnMonitor.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnMonitor.setMenu(QtWidgets.QMenu(self))
        l.addWidget(self.btnMonitor)

        self.btnSettings = self._tool("icons/settings.png", tooltip="Ayarlar")
        self.btnSettings.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnSettings.setMenu(QtWidgets.QMenu(self))
        l.addWidget(self.btnSettings)

        self.btnCfg = self._tool("icons/jsondocument.png", tooltip="Ayar Dosyasını Aç")
        l.addWidget(self.btnCfg)

        self.btnReload = self._tool("icons/reload.png", tooltip="Kısayolları Yeniden Yükle")
        l.addWidget(self.btnReload)

        self.title = QtWidgets.QLabel(title)
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.title.setStyleSheet("font-weight:600;")
        self.title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        self.rightWrap = QtWidgets.QWidget()
        r = QtWidgets.QHBoxLayout(self.rightWrap)
        r.setContentsMargins(0, 0, 6, 0)
        r.setSpacing(6)

        self.btnMin = self._tool("icons/minimize.png", tooltip="Küçült")
        self.btnMin.clicked.connect(self.minimizeRequested)
        r.addWidget(self.btnMin)

        self.btnClose = self._tool("icons/exit.png", tooltip="Kapat")
        self.btnClose.clicked.connect(self.closeRequested)
        r.addWidget(self.btnClose)

        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self.leftWrap)
        h.addWidget(self.title, 1)
        h.addWidget(self.rightWrap)

        self.btnCfg.clicked.connect(self.openConfigRequested)
        self.btnReload.clicked.connect(self.reloadRequested)

    def _tool(self, icon_path: str, tooltip: str):
        b = QtWidgets.QToolButton()
        b.setIcon(QtGui.QIcon(icon_path) if icon_path else QtGui.QIcon())
        b.setIconSize(QtCore.QSize(16, 16))
        b.setFixedSize(28, 24)
        b.setToolTip(tooltip)
        b.setAutoRaise(True)
        return b

    def applyStyle(self, dark: bool):
        if dark:
            bg = "#0f172a"; fg = "#e2e8f0"; hover = "#1f2a44"
        else:
            bg = "#f5f7fa"; fg = "#1e293b"; hover = "#e9eef6"
        self.setStyleSheet(f"""
            TitleBar {{ background:{bg}; border-bottom:1px solid rgba(0,0,0,0.08); }}
            QLabel {{ color:{fg}; }}
            QToolButton {{ border:0; background:transparent; }}
            QToolButton:hover {{ background:{hover}; border-radius:6px; }}
        """)

    # frameless drag — fullscreen'de devre dışı
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if self.window().isFullScreen():
            e.ignore(); return
        if e.button() == QtCore.Qt.LeftButton:
            self._drag = True
            self._drag_offset = e.globalPos() - self.window().frameGeometry().topLeft()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self.window().isFullScreen():
            e.ignore(); return
        if self._drag and e.buttons() & QtCore.Qt.LeftButton:
            self.window().move(e.globalPos() - self._drag_offset)
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        self._drag = False
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        e.ignore()

# ---------------- Kart Buton ----------------
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

# ---------------- Ana Pencere (Profil + Sol Menü) ----------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(640, 360)  # biraz yatay genişlettik (sol menü için)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)

        # Kısayollar
        QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self, activated=self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+M"), self, activated=self.showMinimized)

        # Ayarlar
        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme", "light")
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)
        self.saved_monitor_name = self.settings.value("monitor_name", "", type=str)
        self.minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)
        self.enable_global_hotkey = self.settings.value("enable_global_hotkey", True, type=bool)
        self.fullscreen_mode = self.settings.value("fullscreen_mode", False, type=bool)
        self.always_on_top = self.settings.value("always_on_top", False, type=bool)
        self.current_profile = self.settings.value("current_profile", "Default", type=str)

        self.palette = DARK if self.theme == "dark" else LIGHT

        # Üst bar
        self.titleBar = TitleBar(APP_NAME, icon_path=str(ROOT_DIR / "icons/app.ico"))
        self.titleBar.themeToggled.connect(self._toggle_theme)
        self.titleBar.toprightToggled.connect(self._toggle_topright)
        self.titleBar.openConfigRequested.connect(self._open_active_config)
        self.titleBar.reloadRequested.connect(self._reload_config)
        self.titleBar.minimizeRequested.connect(self.showMinimized)
        self.titleBar.closeRequested.connect(self.close)

        # UI
        self._build_ui()            # (sol panel + sağ içerik)
        self._build_statusbar()

        # Tray
        self._allow_close = False
        self._tray_tip_shown = False
        self._setup_tray()

        # Tema & ikonlar
        self._apply_theme()
        self._update_toolbar_icons()

        # Profil altyapısı
        self._ensure_profiles_bootstrap()
        self._refresh_profile_list()

        # İçerik yükle
        self._rebuild_cards()

        # Menü ve monitör/ayarlar
        self._rebuild_monitor_menu()
        self._build_settings_menu()

        # Üst barı yerleştir
        self.setMenuWidget(self.titleBar)

        # Konum
        if self.start_top_right:
            QtCore.QTimer.singleShot(0, self._move_to_selected_screen_top_right)
        else:
            QtCore.QTimer.singleShot(0, self._center_on_selected_screen)

        # Always on top
        self._apply_always_on_top(self.always_on_top)

        # Global hotkey (Ctrl+V+D)
        self._hotkey_registered = False
        if self.enable_global_hotkey:
            self._register_global_hotkey()

        # Fullscreen başlangıç
        if self.fullscreen_mode:
            self._enter_fullscreen()

        # Ekran listesi güncel kalsın
        QtWidgets.QApplication.instance().screenAdded.connect(lambda s: self._rebuild_monitor_menu())
        QtWidgets.QApplication.instance().screenRemoved.connect(lambda s: self._rebuild_monitor_menu())

        self.titleBar.btnTheme.setChecked(self.theme == "dark")
        self.titleBar.btnTopRight.setChecked(self.start_top_right)

    # ----- Profil Yardımcıları -----
    def _profiles(self):
        PROFILES_DIR.mkdir(exist_ok=True)
        return sorted([p.name for p in PROFILES_DIR.iterdir() if p.is_dir()])

    def _active_profile_dir(self) -> Path:
        return PROFILES_DIR / self.current_profile

    def _active_actions_path(self) -> Path:
        return self._active_profile_dir() / "actions.json"

    def _ensure_profiles_bootstrap(self):
        """profiles/Default/actions.json yoksa oluştur. Varsa dokunma."""
        default_dir = PROFILES_DIR / "Default"
        default_cfg = default_dir / "actions.json"
        if not default_cfg.exists():
            default_dir.mkdir(parents=True, exist_ok=True)
            # kökte actions.json varsa onu kopyala yoksa boş şablon yaz
            if CONFIG_PATH.exists():
                try: shutil.copyfile(CONFIG_PATH, default_cfg)
                except Exception:
                    safe_write_json(default_cfg, {"buttons": [], "hotkeys": {}})
            else:
                safe_write_json(default_cfg, {"buttons": [], "hotkeys": {}})

        # seçili profil yoksa "Default" yap
        if not self.current_profile or not (PROFILES_DIR / self.current_profile).exists():
            self.current_profile = "Default"
            self.settings.setValue("current_profile", self.current_profile)

    # ----- Sol Profil Paneli -----
    def _build_profile_panel(self):
        panel = QtWidgets.QFrame()
        panel.setFixedWidth(180)
        panel.setObjectName("profilePanel")

        title = QtWidgets.QLabel("Profiller")
        title.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        title.setStyleSheet("font-weight:600;")

        self.listProfiles = QtWidgets.QListWidget()
        self.listProfiles.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.listProfiles.itemDoubleClicked.connect(self._switch_profile_from_item)

        btnAdd = QtWidgets.QPushButton("Yeni")
        btnRename = QtWidgets.QPushButton("Yeniden Adlandır")
        btnDelete = QtWidgets.QPushButton("Sil")
        btnOpen = QtWidgets.QPushButton("Klasörü Aç")

        btnAdd.clicked.connect(self._add_profile)
        btnRename.clicked.connect(self._rename_profile)
        btnDelete.clicked.connect(self._delete_profile)
        btnOpen.clicked.connect(self._open_profile_folder)

        # alt: aktif profile ait actions.json'i aç
        btnOpenCfg = QtWidgets.QPushButton("actions.json’i Aç")
        btnOpenCfg.clicked.connect(self._open_active_config)

        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(self.listProfiles, 1)
        layout.addWidget(btnAdd)
        layout.addWidget(btnRename)
        layout.addWidget(btnDelete)
        layout.addSpacing(6)
        layout.addWidget(btnOpen)
        layout.addWidget(btnOpenCfg)

        return panel

    def _refresh_profile_list(self):
        self.listProfiles.clear()
        for name in self._profiles():
            self.listProfiles.addItem(name)
        # seçimi güncelle
        items = self.listProfiles.findItems(self.current_profile, QtCore.Qt.MatchExactly)
        if items:
            self.listProfiles.setCurrentItem(items[0])

    def _switch_profile_from_item(self, item: QtWidgets.QListWidgetItem):
        self._switch_profile(item.text())

    def _switch_profile(self, name: str):
        if not name:
            return
        if not (PROFILES_DIR / name).exists():
            QtWidgets.QMessageBox.warning(self, "Profil Yok", f"'{name}' profili bulunamadı.")
            return
        self.current_profile = name
        self.settings.setValue("current_profile", name)
        self._refresh_profile_list()
        self._rebuild_cards()
        # aktif profil değişince uygun konuma da taşıyabiliriz (dokunmuyoruz)

    def _add_profile(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Yeni Profil", "Profil adı:")
        name = (name or "").strip()
        if not ok or not name:
            return
        # isim doğrulama
        invalid = set(r'<>:"/\|?*')
        if any(ch in invalid for ch in name):
            QtWidgets.QMessageBox.warning(self, "Geçersiz Ad", 'Adda şu karakterler olamaz: <>:"/\\|?*')
            return
        dest = PROFILES_DIR / name
        if dest.exists():
            QtWidgets.QMessageBox.information(self, "Var", "Bu isimde profil zaten var.")
            return
        dest.mkdir(parents=True, exist_ok=True)
        safe_write_json(dest / "actions.json", {"buttons": [], "hotkeys": {}})
        self._refresh_profile_list()

    def _rename_profile(self):
        cur = self.listProfiles.currentItem()
        if not cur:
            return
        old = cur.text()
        if old == "Default":
            QtWidgets.QMessageBox.information(self, "İzin Yok", "'Default' profili yeniden adlandırılamaz.")
            return
        new, ok = QtWidgets.QInputDialog.getText(self, "Yeniden Adlandır", "Yeni ad:", text=old)
        new = (new or "").strip()
        if not ok or not new or new == old:
            return
        invalid = set(r'<>:"/\|?*')
        if any(ch in invalid for ch in new):
            QtWidgets.QMessageBox.warning(self, "Geçersiz Ad", 'Adda şu karakterler olamaz: <>:"/\\|?*')
            return
        src = PROFILES_DIR / old
        dst = PROFILES_DIR / new
        if dst.exists():
            QtWidgets.QMessageBox.information(self, "Var", "Bu isimde profil zaten var.")
            return
        try:
            os.rename(src, dst)
            if self.current_profile == old:
                self.current_profile = new
                self.settings.setValue("current_profile", new)
            self._refresh_profile_list()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Hata", f"Yeniden adlandırılamadı:\n{e}")

    def _delete_profile(self):
        cur = self.listProfiles.currentItem()
        if not cur:
            return
        name = cur.text()
        if name == "Default":
            QtWidgets.QMessageBox.information(self, "İzin Yok", "'Default' profili silinemez.")
            return
        if QtWidgets.QMessageBox.question(self, "Silinsin mi?", f"'{name}' profilini silmek istediğine emin misin?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            shutil.rmtree(PROFILES_DIR / name)
            if self.current_profile == name:
                self.current_profile = "Default"
                self.settings.setValue("current_profile", self.current_profile)
            self._refresh_profile_list()
            self._rebuild_cards()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Hata", f"Profil silinemedi:\n{e}")

    def _open_profile_folder(self):
        path = self._active_profile_dir()
        if path.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "Profil klasörü bulunamadı.")

    def _open_active_config(self):
        cfg = self._active_actions_path()
        if cfg.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(cfg)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "Profil için actions.json bulunamadı.")

    # ----- Status bar -----
    def _build_statusbar(self):
        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)
        self._update_statusbar_text()

    def _update_statusbar_text(self):
        self.status.setStyleSheet(f"color:{self.palette['text_color']}; font-size:12px;")
        self.status.showMessage(f"ViperaDev | {VERSION} | Profil: {self.current_profile}")

    # ----- UI -----
    def _build_ui(self):
        # merkezi alan: yatayda sol profil paneli + sağ içerik
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)

        # sol panel
        self.profilePanel = self._build_profile_panel()
        h.addWidget(self.profilePanel)

        # sağ içerik kabı
        rightWrap = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(rightWrap); rv.setContentsMargins(8, 4, 8, 8); rv.setSpacing(8)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{border:0;background:transparent;} QScrollArea>viewport{background:transparent;}")

        self.canvas = QtWidgets.QWidget(); self.canvas.setStyleSheet("background:transparent;")
        self.grid = QtWidgets.QGridLayout(self.canvas)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10); self.grid.setVerticalSpacing(10)

        self.scroll.setWidget(self.canvas)
        rv.addWidget(self.scroll)

        h.addWidget(rightWrap, 1)

    # ----- Tray -----
    def _setup_tray(self):
        icon_path = str(ROOT_DIR / "icons/app.ico")
        self.tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon(icon_path), self)
        self.tray.setToolTip(f"{APP_NAME} arka planda çalışıyor")

        menu = QtWidgets.QMenu()
        act_show = menu.addAction("Göster"); act_show.triggered.connect(self._restore_from_tray)
        menu.addSeparator()
        act_quit = menu.addAction("Çıkış");  act_quit.triggered.connect(self._quit_from_tray)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.show(); self.raise_(); self.activateWindow()

    def _quit_from_tray(self):
        self._allow_close = True
        QtWidgets.qApp.quit()

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self._allow_close:
            return super().closeEvent(event)
        if self.minimize_to_tray:
            event.ignore()
            self.hide()
            if not self._tray_tip_shown and self.tray.isVisible():
                try:
                    self.tray.showMessage(APP_NAME, "Arka planda çalışmaya devam ediyor.\nTepsideki simgeye çift tıklayarak geri getirebilirsiniz.",
                                          QtWidgets.QSystemTrayIcon.Information, 3500)
                except Exception:
                    pass
                self._tray_tip_shown = True
        else:
            self._allow_close = True
            QtWidgets.qApp.quit()

    # ----- Tema -----
    def _apply_theme(self):
        dark = (self.theme == "dark")
        self.palette = DARK if dark else LIGHT
        self.titleBar.applyStyle(dark)
        # sol panel stili
        self.profilePanel.setStyleSheet(
            f"#profilePanel {{ background:{self.palette['bg']}; border-right:1px solid {self.palette['card_border']}; }} "
            f"QListWidget {{ background: transparent; color: {self.palette['fg']}; }}"
        )
        self.setStyleSheet(f"QMainWindow {{ background:{self.palette['bg']}; }}")

        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CardButton):
                w.p = self.palette
                w.apply_style()
        self._update_statusbar_text()
        self._update_toolbar_icons()

    def _update_toolbar_icons(self):
        theme_icon = str(ROOT_DIR / ("icons/dark-theme.png" if self.theme == "dark" else "icons/light-theme.png"))
        self.titleBar.btnTheme.setIcon(QtGui.QIcon(theme_icon))
        pos_icon = str(ROOT_DIR / ("icons/topright.png" if self.start_top_right else "icons/free.png"))
        self.titleBar.btnTopRight.setIcon(QtGui.QIcon(pos_icon))

    # ----- Monitör & Ayarlar Menüsü -----
    def _rebuild_monitor_menu(self):
        m = QtWidgets.QMenu(self)
        group = QtWidgets.QActionGroup(m); group.setExclusive(True)
        selected_action = None
        for s in QtWidgets.QApplication.screens():
            geo = s.geometry()
            label = f"{s.name()}  ({geo.width()}×{geo.height()})"
            if s == QtWidgets.QApplication.primaryScreen():
                label = "⭐ " + label
            act = QtWidgets.QAction(label, m, checkable=True)
            act.setData(s.name())
            m.addAction(act); group.addAction(act)
            if self.saved_monitor_name and s.name() == self.saved_monitor_name:
                selected_action = act
        m.addSeparator()
        act_auto = QtWidgets.QAction("Otomatik (birincil)", m, checkable=True)
        act_auto.setData(""); m.addAction(act_auto); group.addAction(act_auto)
        if selected_action: selected_action.setChecked(True)
        else: act_auto.setChecked(True)
        group.triggered.connect(self._on_monitor_chosen)
        self.titleBar.btnMonitor.setMenu(m)

    def _build_settings_menu(self):
        m = QtWidgets.QMenu(self)

        act_min_to_tray = QtWidgets.QAction("Kapatınca tepsiye gizle", m, checkable=True)
        act_min_to_tray.setChecked(self.minimize_to_tray)
        act_min_to_tray.toggled.connect(self._toggle_minimize_to_tray)
        m.addAction(act_min_to_tray)

        act_startup = QtWidgets.QAction("Windows ile başlat", m, checkable=True)
        act_startup.setChecked(self._is_startup_enabled())
        act_startup.toggled.connect(lambda checked: self._set_startup(checked))
        m.addAction(act_startup)

        act_hotkey = QtWidgets.QAction("Kısayol ile aç (Ctrl+V+D)", m, checkable=True)
        act_hotkey.setChecked(self.enable_global_hotkey)
        act_hotkey.toggled.connect(self._toggle_global_hotkey)
        m.addAction(act_hotkey)

        act_fullscreen = QtWidgets.QAction("Tam ekran modu", m, checkable=True)
        act_fullscreen.setChecked(self.fullscreen_mode)
        act_fullscreen.toggled.connect(self._toggle_fullscreen)
        m.addAction(act_fullscreen)

        act_always_top = QtWidgets.QAction("Her zaman üstte", m, checkable=True)
        act_always_top.setChecked(self.always_on_top)
        act_always_top.toggled.connect(self._toggle_always_on_top)
        m.addAction(act_always_top)

        self.titleBar.btnSettings.setMenu(m)

    def _toggle_minimize_to_tray(self, checked: bool):
        self.minimize_to_tray = checked
        self.settings.setValue("minimize_to_tray", checked)

    # Startup
    def _is_startup_enabled(self):
        try:
            return os.path.exists(APP_SHORTCUT)
        except Exception:
            return False

    def _set_startup(self, enable: bool):
        try:
            if enable:
                if not ensure_winshell_installed(self):
                    self._build_settings_menu(); return
                import winshell  # noqa: F401
                os.makedirs(STARTUP_FOLDER, exist_ok=True)
                exe_path, args = _launcher_paths()
                icon_loc = (str(ROOT_DIR / "icons/app.ico"), 0) if (ROOT_DIR / "icons/app.ico").exists() else (exe_path, 0)
                with winshell.shortcut(APP_SHORTCUT) as link:
                    link.path = exe_path
                    link.arguments = args
                    link.description = f"{APP_NAME} - Masaüstü Paneli"
                    link.icon_location = icon_loc
            else:
                if os.path.exists(APP_SHORTCUT):
                    os.remove(APP_SHORTCUT)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Hata", f"Başlangıç ayarı değiştirilemedi:\n{e}")
        finally:
            self._build_settings_menu()

    # Global Hotkey (Ctrl+V+D)
    def _toggle_global_hotkey(self, checked: bool):
        self.enable_global_hotkey = checked
        self.settings.setValue("enable_global_hotkey", checked)
        if checked:
            self._register_global_hotkey()
        else:
            try:
                if getattr(self, "_hotkey_registered", False):
                    keyboard.remove_hotkey(self._hotkey_handle)
                    self._hotkey_registered = False
            except Exception:
                pass

    def _register_global_hotkey(self):
        try:
            def toggle_show():
                if self.isHidden():
                    self.show(); self.raise_(); self.activateWindow()
                else:
                    self.hide()
            self._hotkey_handle = keyboard.add_hotkey("ctrl+v+d", toggle_show, suppress=False, trigger_on_release=True)
            self._hotkey_registered = True
        except Exception:
            self._hotkey_registered = False

    # Fullscreen
    def _toggle_fullscreen(self, checked: bool):
        self.fullscreen_mode = checked
        self.settings.setValue("fullscreen_mode", checked)
        if checked: self._enter_fullscreen()
        else:       self._leave_fullscreen()

    def _enter_fullscreen(self):
        self.showFullScreen()

    def _leave_fullscreen(self):
        self.showNormal()

    # Always on top
    def _toggle_always_on_top(self, checked: bool):
        self.always_on_top = checked
        self.settings.setValue("always_on_top", checked)
        self._apply_always_on_top(checked)

    def _apply_always_on_top(self, enabled: bool):
        flags = self.windowFlags()
        if enabled:
            flags |= QtCore.Qt.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    # Monitör seçimi
    def _on_monitor_chosen(self, action: QtWidgets.QAction):
        self.saved_monitor_name = action.data() or ""
        self.settings.setValue("monitor_name", self.saved_monitor_name)
        if self.start_top_right: self._move_to_selected_screen_top_right()
        else:                     self._center_on_selected_screen()

    # Konum
    def _screen_geometry(self):
        target = None
        if self.saved_monitor_name:
            for s in QtWidgets.QApplication.screens():
                if s.name() == self.saved_monitor_name:
                    target = s; break
        if not target:
            target = QtWidgets.QApplication.primaryScreen()
        return target.availableGeometry() if target else None

    def _move_to_selected_screen_top_right(self):
        avail = self._screen_geometry()
        if not avail: return
        self.move(avail.right() - self.width(), avail.top())

    def _center_on_selected_screen(self):
        avail = self._screen_geometry()
        if not avail: return
        cx = avail.center().x() - self.width() // 2
        cy = avail.center().y() - self.height() // 2
        self.move(cx, cy)

    # Grid
    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

    def _rebuild_cards(self):
        self._clear_grid()
        buttons = safe_read_json(self._active_actions_path(), {"buttons": [], "hotkeys": {}}).get("buttons", [])
        btn_w = 72; gap = 10; inner_w = max(0, self.width() - self.profilePanel.width() - 16)
        cols = max(2, min(6, (inner_w + gap) // (btn_w + gap)))
        row = col = 0
        for b in buttons:
            card = CardButton(b, self.palette)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols: col = 0; row += 1
        self.status.showMessage(f"{len(buttons)} öğe yüklendi — Profil: {self.current_profile}")

    # Tema/Konum
    def _toggle_theme(self, checked: bool):
        self.theme = "dark" if checked else "light"
        self.settings.setValue("theme", self.theme)
        self._apply_theme()

    def _toggle_topright(self, checked: bool):
        self.start_top_right = checked
        self.settings.setValue("start_top_right", checked)
        if checked: self._move_to_selected_screen_top_right()
        else:       self._center_on_selected_screen()
        self._update_toolbar_icons()

    def _reload_config(self):
        self._rebuild_cards()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "Aktif profilin actions.json dosyası yeniden yüklendi.")

# ---------------- Çalıştır ----------------
def main():
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORG); app.setApplicationName(APP_NAME)
    app.setWindowIcon(QtGui.QIcon(str(ROOT_DIR / "icons/app.ico")))

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
