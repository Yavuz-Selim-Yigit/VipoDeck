# app.py — VipoDeck v1.4.4 (fix: _register_global_hotkey eklendi, küçük temizlik)
# Gereksinimler: PyQt5, PyAutoGUI, keyboard, winshell (opsiyonel: Windows ile başlat)
# pip install PyQt5 pyautogui keyboard winshell

import sys, os, json, time, subprocess, webbrowser, shutil
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui, keyboard

APP_NAME   = "VipoDeck"
ORG        = "ViperaDev"
APP        = "VipoDeck"

ROOT_CONFIG   = Path(__file__).with_name("actions.json")
PROFILES_DIR  = Path(__file__).with_name("profiles")
DEFAULT_PROFILE = "Default"

LIGHT = {
    "bg": "#f5f7fa", "fg": "#1e293b", "muted": "#64748b",
    "card_bg": "#ffffff", "card_border": "#e2e8f0", "card_hover": "#f1f5f9",
    "text_color": "#000000"
}
DARK  = {
    "bg": "#0f172a", "fg": "#e2e8f0", "muted": "#94a3b8",
    "card_bg": "#1b2333", "card_border": "#2a3650", "card_hover": "#25324a",
    "text_color": "#ffffff"
}

# ---- Windows Startup (kısayol) ----
STARTUP_FOLDER = os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)
APP_SHORTCUT = os.path.join(STARTUP_FOLDER, f"{APP_NAME}.lnk")

def _launcher_paths():
    """EXE ise sys.executable; script ise python.exe + 'app.py' argümanı."""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    else:
        return sys.executable, f'"{os.path.abspath(sys.argv[0])}"'

# ---------------- Yardımcılar ----------------
def load_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"buttons": [], "hotkeys": {}}

def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def open_target(target: str):
    if not target: return
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

# --- winshell yoksa otomatik kurma ---
def ensure_winshell_installed(parent=None) -> bool:
    try:
        import winshell  # noqa
        return True
    except Exception:
        pass

    ret = QtWidgets.QMessageBox.question(
        parent, "Gerekli Paket",
        "Windows ile başlat özelliği için 'winshell' paketi gerekiyor.\n"
        "Şimdi otomatik kurulsun mu?",
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
        QtWidgets.QMessageBox.warning(
            parent, "Kurulum Hatası",
            f"'winshell' kurulamadı.\n\nHata:\n{e}\n\n"
            "Elle kurmak için:\n  pip install winshell"
        )
        return False
    finally:
        try: QtWidgets.QApplication.restoreOverrideCursor()
        except Exception: pass

    try:
        import winshell  # noqa
        return True
    except Exception:
        return False

# ---------------- Title Bar ----------------
class TitleBar(QtWidgets.QWidget):
    minimizeRequested = QtCore.pyqtSignal()
    closeRequested    = QtCore.pyqtSignal()
    themeToggled      = QtCore.pyqtSignal(bool)
    toprightToggled   = QtCore.pyqtSignal(bool)
    openConfigRequested = QtCore.pyqtSignal()
    reloadRequested     = QtCore.pyqtSignal()

    def __init__(self, title: str, icon_path: str = None, parent=None):
        super().__init__(parent)
        self._drag = False
        self._drag_offset = QtCore.QPoint()
        self.setFixedHeight(40)

        # left: icon + toolbar
        self.leftWrap = QtWidgets.QWidget()
        l = QtWidgets.QHBoxLayout(self.leftWrap)
        l.setContentsMargins(8, 0, 0, 0); l.setSpacing(6)

        self.appIcon = QtWidgets.QLabel(); self.appIcon.setFixedSize(18, 18)
        if icon_path and Path(icon_path).exists():
            self.appIcon.setPixmap(QtGui.QPixmap(icon_path).scaled(18, 18, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        l.addWidget(self.appIcon)

        self.btnTheme = self._tool("", "Tema Değiştir"); self.btnTheme.setCheckable(True)
        self.btnTheme.toggled.connect(self.themeToggled.emit); l.addWidget(self.btnTheme)

        self.btnTopRight = self._tool("", "Pencere Konumu"); self.btnTopRight.setCheckable(True)
        self.btnTopRight.toggled.connect(self.toprightToggled.emit); l.addWidget(self.btnTopRight)

        self.btnMonitor = self._tool("icons/DefaultPack/screen.png", "Monitör Seç")
        self.btnMonitor.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnMonitor.setMenu(QtWidgets.QMenu(self)); l.addWidget(self.btnMonitor)

        self.btnSettings = self._tool("icons/DefaultPack/settings.png", "Ayarlar")
        self.btnSettings.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnSettings.setMenu(QtWidgets.QMenu(self)); l.addWidget(self.btnSettings)

        self.btnCfg = self._tool("icons/DefaultPack/jsondocument.png", "Ayar Dosyasını Aç")
        l.addWidget(self.btnCfg)

        self.btnReload = self._tool("icons/DefaultPack/reload.png", "Kısayolları Yeniden Yükle")
        l.addWidget(self.btnReload)

        # center: title
        self.title = QtWidgets.QLabel(title)
        self.title.setAlignment(QtCore.Qt.AlignCenter)
               # kalın görünüm
        self.title.setStyleSheet("font-weight:600;")
        self.title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        # right: min/close
        self.rightWrap = QtWidgets.QWidget()
        r = QtWidgets.QHBoxLayout(self.rightWrap)
        r.setContentsMargins(0, 0, 6, 0); r.setSpacing(6)
        self.btnMin = self._tool("icons/DefaultPack/minimize.png", "Küçült"); self.btnMin.clicked.connect(self.minimizeRequested); r.addWidget(self.btnMin)
        self.btnClose = self._tool("icons/DefaultPack/exit.png", "Kapat"); self.btnClose.clicked.connect(self.closeRequested); r.addWidget(self.btnClose)

        h = QtWidgets.QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        h.addWidget(self.leftWrap); h.addWidget(self.title, 1); h.addWidget(self.rightWrap)

        self.btnCfg.clicked.connect(self.openConfigRequested)
        self.btnReload.clicked.connect(self.reloadRequested)

    def _tool(self, icon_path: str, tooltip: str):
        b = QtWidgets.QToolButton()
        b.setIcon(QtGui.QIcon(icon_path) if icon_path else QtGui.QIcon())
        b.setIconSize(QtCore.QSize(16, 16)); b.setFixedSize(28, 24)
        b.setToolTip(tooltip); b.setAutoRaise(True)
        return b

    def applyStyle(self, dark: bool):
        if dark: bg, fg, hover = "#0f172a", "#e2e8f0", "#1f2a44"
        else:    bg, fg, hover = "#f5f7fa", "#1e293b", "#e9eef6"
        self.setStyleSheet(f"""
            TitleBar {{ background:{bg}; border-bottom:1px solid rgba(0,0,0,0.08); }}
            QLabel {{ color:{fg}; }}
            QToolButton {{ border:0; background:transparent; }}
            QToolButton:hover {{ background:{hover}; border-radius:6px; }}
        """)

    # frameless sürükleme (tam ekranda yok)
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if self.window().isFullScreen(): e.ignore(); return
        if e.button() == QtCore.Qt.LeftButton:
            self._drag = True
            self._drag_offset = e.globalPos() - self.window().frameGeometry().topLeft()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self.window().isFullScreen(): e.ignore(); return
        if self._drag and e.buttons() & QtCore.Qt.LeftButton:
            self.window().move(e.globalPos() - self._drag_offset); e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        self._drag = False; super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        e.ignore()

# ---------------- Kart Buton ----------------
class CardButton(QtWidgets.QPushButton):
    def __init__(self, data, palette):
        super().__init__()
        self.data = data; self.p = palette
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setIconSize(QtCore.QSize(40, 40))
        self.setMinimumSize(72, 72)
        self.apply_style()

        label_text = data.get("label", "?")
        self.setToolTip(label_text)
        icon_path = data.get("icon")
        if icon_path and Path(icon_path).exists(): self.setIcon(QtGui.QIcon(icon_path)); self.setText("")
        else: self.setText(label_text)

        self.clicked.connect(lambda: run_action(self.data))

    def apply_style(self):
        p = self.p
        self.setStyleSheet(f"""
            QPushButton {{
                background:{p['card_bg']};
                border:1px solid {p['card_border']};
                border-radius:12px;
                padding:12px; text-align:center;
                color:{p['text_color']}; font-size:13px;
            }}
            QPushButton:hover {{ background:{p['card_hover']}; }}
        """)

# ---------------- Ana Pencere ----------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(700, 360)  # yan panel için daha geniş
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)

        # ---- Ayarlar / Durumlar
        self._allow_close = False
        self._hotkey_registered = False
        self._hotkey_handle = None

        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme", "light")
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)
        self.saved_monitor_name = self.settings.value("monitor_name", "", type=str)
        self.minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)
        self.enable_global_hotkey = self.settings.value("enable_global_hotkey", True, type=bool)
        self.fullscreen_mode = self.settings.value("fullscreen_mode", False, type=bool)
        self.always_on_top = self.settings.value("always_on_top", False, type=bool)
        self.current_profile = self.settings.value("profile_name", DEFAULT_PROFILE, type=str)
        self.palette = DARK if self.theme == "dark" else LIGHT

        # ---- Üst bar
        self.titleBar = TitleBar(APP_NAME, icon_path="icons/DefaultPack/app.ico")
        self.titleBar.themeToggled.connect(self._toggle_theme)
        self.titleBar.toprightToggled.connect(self._toggle_topright)
        self.titleBar.openConfigRequested.connect(self._open_active_config)
        self.titleBar.reloadRequested.connect(self._reload_config)
        self.titleBar.minimizeRequested.connect(self._on_minimize_clicked)
        self.titleBar.closeRequested.connect(self.close)

        # ---- UI
        self._build_ui()
        self._build_statusbar()

        # ---- Tray
        self._setup_tray()

        # ---- Tema & ikonlar
        self._apply_theme()
        self._update_toolbar_icons()

        # ---- Profilleri hazırla/yükle
        self._ensure_default_profile()
        self._load_profiles()
        self._select_profile(self.current_profile, first_time=True)

        # ---- Menü ve monitör
        self._rebuild_monitor_menu()
        self._build_settings_menu()

        # ---- Üst barı yerleştir
        self.setMenuWidget(self.titleBar)

        # ---- Başlangıç konumu
        if self.start_top_right: QtCore.QTimer.singleShot(0, self._move_to_selected_screen_top_right)
        else:                    QtCore.QTimer.singleShot(0, self._center_on_selected_screen)

        # ---- Always on top
        self._apply_always_on_top(self.always_on_top)

        # ---- Global hotkey (Ctrl+V+D) — HATA BURADAYDI: eksik metot -> eklendi
        if self.enable_global_hotkey:
            self._register_global_hotkey()

        # ---- Fullscreen başlangıç
        if self.fullscreen_mode:
            self._enter_fullscreen()

        # ---- Ekran listesi tazeleme
        QtWidgets.QApplication.instance().screenAdded.connect(lambda s: self._rebuild_monitor_menu())
        QtWidgets.QApplication.instance().screenRemoved.connect(lambda s: self._rebuild_monitor_menu())

        # ---- Toggle görünümleri
        self.titleBar.btnTheme.setChecked(self.theme == "dark")
        self.titleBar.btnTopRight.setChecked(self.start_top_right)

    # ----- Status bar -----
    def _build_statusbar(self):
        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)
        self._update_statusbar_text()

    def _update_statusbar_text(self):
        self.status.setStyleSheet(f"color:{self.palette['text_color']}; font-size:12px;")
        self.status.showMessage("ViperaDev | v1.4.4")

    # ----- UI (sol profil paneli + sağ kart alanı) -----
    def _build_ui(self):
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central); root.setContentsMargins(8, 4, 8, 8); root.setSpacing(8)

        # --- Sol: Profiller ---
        self.profilePanel = QtWidgets.QFrame()
        self.profilePanel.setFixedWidth(200)
        self.profilePanel.setStyleSheet("QFrame{border:1px solid rgba(0,0,0,0.12); border-radius:8px;}")

        v = QtWidgets.QVBoxLayout(self.profilePanel); v.setContentsMargins(8,8,8,8); v.setSpacing(8)

        self.lstProfiles = QtWidgets.QListWidget()
        self.lstProfiles.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.lstProfiles.itemSelectionChanged.connect(self._on_profile_selected_from_list)
        v.addWidget(self.lstProfiles, 1)

        iconRow = QtWidgets.QHBoxLayout(); iconRow.setSpacing(6)

        def ib(path, tip, slot):
            btn = QtWidgets.QToolButton()
            if Path(path).exists(): btn.setIcon(QtGui.QIcon(path))
            btn.setIconSize(QtCore.QSize(18,18)); btn.setFixedSize(30,26)
            btn.setToolTip(tip); btn.clicked.connect(slot); btn.setAutoRaise(True)
            iconRow.addWidget(btn); return btn

        self.btnProfNew   = ib("icons/DefaultPack/add.png",    "Yeni profil",           self._profile_new)
        self.btnProfRen   = ib("icons/DefaultPack/edit.png",   "Yeniden adlandır",      self._profile_rename)
        self.btnProfDel   = ib("icons/DefaultPack/delete.png", "Sil",                    self._profile_delete)
        self.btnProfOpen  = ib("icons/DefaultPack/folder.png", "Profil klasörünü aç",   self._profile_open_folder)
        self.btnProfJson  = ib("icons/DefaultPack/jsondocument.png","actions.json'u aç",self._open_active_config)

        v.addLayout(iconRow)

        # --- Sağ: Kart alanı ---
        rightWrap = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(rightWrap); rv.setContentsMargins(0,0,0,0); rv.setSpacing(8)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{border:0;background:transparent;} QScrollArea>viewport{background:transparent;}")

        self.canvas = QtWidgets.QWidget(); self.canvas.setStyleSheet("background:transparent;")
        self.grid = QtWidgets.QGridLayout(self.canvas)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10); self.grid.setVerticalSpacing(10)
        self.scroll.setWidget(self.canvas); rv.addWidget(self.scroll)

        root.addWidget(self.profilePanel)
        root.addWidget(rightWrap, 1)

    # ----- Tray -----
    def _setup_tray(self):
        icon_path = "icons/DefaultPack/app.ico"
        self.tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon(icon_path), self)
        self.tray.setToolTip(f"{APP_NAME} arka planda çalışıyor")

        menu = QtWidgets.QMenu()
        act_show = menu.addAction("Göster"); act_show.triggered.connect(self._restore_from_tray)
        menu.addSeparator()
        act_quit = menu.addAction("Çıkış"); act_quit.triggered.connect(self._quit_from_tray)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.show(); self.raise_(); self.activateWindow()

    def _quit_from_tray(self):
        self._allow_close = True; QtWidgets.qApp.quit()

    def _on_minimize_clicked(self):
        self.showMinimized()

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self._allow_close:
            return super().closeEvent(event)
        if self.minimize_to_tray:
            event.ignore(); self.hide()
            if not hasattr(self, "_tray_tip_shown") or not self._tray_tip_shown:
                if self.tray.isVisible():
                    try:
                        self.tray.showMessage(
                            APP_NAME,
                            "Arka planda çalışmaya devam ediyor.\nTepsideki simgeye çift tıklayarak geri getirebilirsiniz.",
                            QtWidgets.QSystemTrayIcon.Information, 3500
                        )
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
        self.setStyleSheet(f"QMainWindow {{ background:{self.palette['bg']}; }}")
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CardButton):
                w.p = self.palette; w.apply_style()
        self._update_statusbar_text(); self._update_toolbar_icons()

    def _update_toolbar_icons(self):
        self.titleBar.btnTheme.setIcon(QtGui.QIcon("icons/DefaultPack/dark-theme.png" if self.theme=="dark" else "icons/DefaultPack/light-theme.png"))
        self.titleBar.btnTopRight.setIcon(QtGui.QIcon("icons/DefaultPack/topright.png" if self.start_top_right else "icons/DefaultPack/free.png"))

    # ----- Profiller -----
    def _profile_dir(self, name: str) -> Path:
        return PROFILES_DIR / name

    def _profile_config_path(self, name: str) -> Path:
        return self._profile_dir(name) / "actions.json"

    def _ensure_default_profile(self):
        PROFILES_DIR.mkdir(exist_ok=True)
        d = self._profile_dir(DEFAULT_PROFILE)
        cfg = self._profile_config_path(DEFAULT_PROFILE)
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
        if not cfg.exists():
            data = load_json(ROOT_CONFIG) if ROOT_CONFIG.exists() else {"buttons": [], "hotkeys": {}}
            save_json(cfg, data)

    def _load_profiles(self):
        self.lstProfiles.clear()
        if not PROFILES_DIR.exists(): self._ensure_default_profile()
        for p in sorted([d.name for d in PROFILES_DIR.iterdir() if d.is_dir()]):
            self.lstProfiles.addItem(p)

    def _select_profile(self, name: str, first_time=False):
        if not name or not (self._profile_dir(name)).exists():
            name = DEFAULT_PROFILE
        self.current_profile = name
        self.settings.setValue("profile_name", name)
        matches = self.lstProfiles.findItems(name, QtCore.Qt.MatchExactly)
        if matches: self.lstProfiles.setCurrentItem(matches[0])
        self._rebuild_cards()
        if not first_time:
            self.status.showMessage(f"Profil: {name}")

    def _on_profile_selected_from_list(self):
        it = self.lstProfiles.currentItem()
        if it: self._select_profile(it.text())

    def _profile_new(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Yeni Profil", "Ad:")
        if not ok or not name.strip(): return
        name = name.strip()
        d = self._profile_dir(name)
        if d.exists():
            QtWidgets.QMessageBox.information(self, "Bilgi", "Bu isimde bir profil zaten var."); return
        d.mkdir(parents=True, exist_ok=True)
        tpl = self._profile_config_path(self.current_profile)
        data = load_json(tpl) if tpl.exists() else {"buttons": [], "hotkeys": {}}
        save_json(self._profile_config_path(name), data)
        self._load_profiles(); self._select_profile(name)

    def _profile_rename(self):
        it = self.lstProfiles.currentItem()
        if not it: return
        old = it.text()
        if old == DEFAULT_PROFILE:
            QtWidgets.QMessageBox.information(self, "Bilgi", "Varsayılan profil yeniden adlandırılamaz."); return
        new, ok = QtWidgets.QInputDialog.getText(self, "Yeniden Adlandır", "Yeni ad:", text=old)
        if not ok or not new.strip(): return
        new = new.strip()
        if new == old: return
        nd = self._profile_dir(new)
        if nd.exists():
            QtWidgets.QMessageBox.information(self, "Bilgi", "Bu isimde bir profil zaten var."); return
        os.rename(self._profile_dir(old), nd)
        self._load_profiles(); self._select_profile(new)

    def _profile_delete(self):
        it = self.lstProfiles.currentItem()
        if not it: return
        name = it.text()
        if name == DEFAULT_PROFILE:
            QtWidgets.QMessageBox.information(self, "Bilgi", "Varsayılan profil silinemez."); return
        ret = QtWidgets.QMessageBox.question(self, "Sil", f"‘{name}’ profili silinsin mi?",
                                             QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if ret != QtWidgets.QMessageBox.Yes: return
        shutil.rmtree(self._profile_dir(name), ignore_errors=True)
        self._load_profiles()
        if self.current_profile == name:
            self._select_profile(DEFAULT_PROFILE)

    def _profile_open_folder(self):
        d = self._profile_dir(self.current_profile)
        if d.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(d)))

    def _open_active_config(self):
        cfg = self._profile_config_path(self.current_profile)
        if cfg.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(cfg)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    # ----- Monitör / Ayarlar Menüsü -----
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
            if self.saved_monitor_name and s.name() == self.saved_monitor_name:
                selected_action = act
        m.addSeparator()
        act_auto = QtWidgets.QAction("Otomatik (birincil)", m, checkable=True); act_auto.setData("")
        m.addAction(act_auto); group.addAction(act_auto)
        (selected_action or act_auto).setChecked(True)
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

    # ----- Settings handlers -----
    def _toggle_minimize_to_tray(self, checked: bool):
        self.minimize_to_tray = checked
        self.settings.setValue("minimize_to_tray", checked)

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
                icon_loc = (os.path.abspath("icons/DefaultPack/app.ico"), 0) if os.path.exists("icons/DefaultPack/app.ico") else (exe_path, 0)
                with winshell.shortcut(APP_SHORTCUT) as link:
                    link.path = exe_path; link.arguments = args
                    link.description = f"{APP_NAME} - Masaüstü Paneli"
                    link.icon_location = icon_loc
            else:
                if os.path.exists(APP_SHORTCUT): os.remove(APP_SHORTCUT)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Hata", f"Başlangıç ayarı değiştirilemedi:\n{e}")
        finally:
            self._build_settings_menu()

    # >>> EKLENDİ: eksik olan metot
    def _register_global_hotkey(self):
        """Ctrl+V+D ile göster/gizle global kısayolunu kaydet."""
        try:
            def toggle_show():
                if self.isHidden(): self.show(); self.raise_(); self.activateWindow()
                else: self.hide()
            self._hotkey_handle = keyboard.add_hotkey(
                "ctrl+v+d", toggle_show, suppress=False, trigger_on_release=True
            )
            self._hotkey_registered = True
        except Exception:
            self._hotkey_registered = False
            self._hotkey_handle = None

    def _toggle_global_hotkey(self, checked: bool):
        self.enable_global_hotkey = checked
        self.settings.setValue("enable_global_hotkey", checked)
        try:
            if checked:
                self._register_global_hotkey()
            else:
                if self._hotkey_registered and self._hotkey_handle is not None:
                    keyboard.remove_hotkey(self._hotkey_handle)
                self._hotkey_registered = False
                self._hotkey_handle = None
        except Exception:
            pass

    def _toggle_fullscreen(self, checked: bool):
        self.fullscreen_mode = checked
        self.settings.setValue("fullscreen_mode", checked)
        if checked: self._enter_fullscreen()
        else: self._leave_fullscreen()

    def _enter_fullscreen(self): self.showFullScreen()
    def _leave_fullscreen(self): self.showNormal()

    def _toggle_always_on_top(self, checked: bool):
        self.always_on_top = checked
        self.settings.setValue("always_on_top", checked)
        self._apply_always_on_top(checked)

    def _apply_always_on_top(self, enabled: bool):
        flags = self.windowFlags()
        if enabled: flags |= QtCore.Qt.WindowStaysOnTopHint
        else:       flags &= ~QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags); self.show()

    # ----- Monitör / Konum -----
    def _on_monitor_chosen(self, action: QtWidgets.QAction):
        self.saved_monitor_name = action.data() or ""
        self.settings.setValue("monitor_name", self.saved_monitor_name)
        if self.start_top_right: self._move_to_selected_screen_top_right()
        else: self._center_on_selected_screen()

    def _screen_geometry(self):
        target = None
        if self.saved_monitor_name:
            for s in QtWidgets.QApplication.screens():
                if s.name() == self.saved_monitor_name: target = s; break
        if not target: target = QtWidgets.QApplication.primaryScreen()
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

    # ----- Grid -----
    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0); w = item.widget()
            if w: w.deleteLater()

    def _rebuild_cards(self):
        self._clear_grid()
        cfg_path = self._profile_config_path(self.current_profile)
        cfg = load_json(cfg_path)
        buttons = cfg.get("buttons", [])
        btn_w = 72; gap = 10; inner_w = self.width() - 16 - self.profilePanel.width()
        cols = max(3, min(7, (inner_w + gap) // (btn_w + gap)))
        row = col = 0
        for b in buttons:
            card = CardButton(b, self.palette)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols: col = 0; row += 1
        self.status.showMessage(f"{len(buttons)} öğe yüklendi")

    # ----- Tema / Konum aksiyonları -----
    def _toggle_theme(self, checked: bool):
        self.theme = "dark" if checked else "light"
               # kaydet + uygula
        self.settings.setValue("theme", self.theme)
        self._apply_theme()

    def _toggle_topright(self, checked: bool):
        self.start_top_right = checked
        self.settings.setValue("start_top_right", checked)
        if checked: self._move_to_selected_screen_top_right()
        else: self._center_on_selected_screen()
        self._update_toolbar_icons()

    def _reload_config(self):
        self._rebuild_cards()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")

# ---------------- Çalıştır ----------------
def main():
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORG); app.setApplicationName(APP_NAME)
    app.setWindowIcon(QtGui.QIcon("icons/DefaultPack/app.ico"))

    w = MainWindow(); w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
