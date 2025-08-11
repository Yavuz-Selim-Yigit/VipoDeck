# app.py — PyQt5 kısayol paneli (frameless + özel üst bar + dinamik menü ikonları)
import sys, json, time, threading, subprocess, webbrowser
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui, keyboard

APP_NAME   = "Kısayol Paneli"
ORG        = "ViperaDev"
APP        = "ShortcutPanel"
CONFIG_PATH = Path(__file__).with_name("actions.json")

LIGHT = {"bg": "#f5f7fa", "fg": "#1e293b", "muted": "#64748b",
         "card_bg": "#ffffff", "card_border": "#e2e8f0", "card_hover": "#f1f5f9",
         "menu_bg": "#ffffff", "menu_border": "#e2e8f0", "text_color": "#000000"}
DARK  = {"bg": "#0f172a", "fg": "#e2e8f0", "muted": "#94a3b8",
         "card_bg": "#1e293b", "card_border": "#334155", "card_hover": "#273449",
         "menu_bg": "#111827", "menu_border": "#334155", "text_color": "#ffffff"}

# ---------------- Yardımcılar ----------------
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"buttons": [], "hotkeys": {}}

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

# ---------------- Özel Üst Bar ----------------
class TitleBar(QtWidgets.QWidget):
    minimizeRequested = QtCore.pyqtSignal()
    closeRequested = QtCore.pyqtSignal()

    def __init__(self, title: str, icon_path: str = None, parent=None):
        super().__init__(parent)
        self._drag = False
        self._drag_offset = QtCore.QPoint()

        self.setFixedHeight(36)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # ----- SOL BLOK (ikon alanı) -----
        self.leftWrap = QtWidgets.QWidget()
        left = QtWidgets.QHBoxLayout(self.leftWrap)
        left.setContentsMargins(8, 0, 0, 0)
        left.setSpacing(8)

        self.icon = QtWidgets.QLabel()
        self.icon.setFixedSize(18, 18)
        if icon_path and Path(icon_path).exists():
            self.icon.setPixmap(
                QtGui.QPixmap(icon_path).scaled(
                    18, 18, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
                )
            )
        left.addWidget(self.icon)

        # Dengelemek için sol alanın min. genişliğini sağ butonlara göre ayarlayacağız
        self.leftWrap.setMinimumWidth(0)

        # ----- ORTA BAŞLIK -----
        self.title = QtWidgets.QLabel(title)
        self.title.setObjectName("windowTitleLabel")
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        # ----- SAĞ BUTONLAR (minimize + close) -----
        self.rightWrap = QtWidgets.QWidget()
        btns = QtWidgets.QHBoxLayout(self.rightWrap)
        btns.setContentsMargins(0, 0, 4, 0)
        btns.setSpacing(6)

        self.btnMin = QtWidgets.QToolButton()
        self.btnMin.setToolTip("Küçült")
        self.btnMin.setIcon(QtGui.QIcon("icons/minimize.png"))
        self.btnMin.setIconSize(QtCore.QSize(16, 16))
        self.btnMin.setFixedSize(30, 24)
        self.btnMin.clicked.connect(self.minimizeRequested)

        self.btnClose = QtWidgets.QToolButton()
        self.btnClose.setToolTip("Kapat")
        self.btnClose.setIcon(QtGui.QIcon("icons/exit.png"))
        self.btnClose.setIconSize(QtCore.QSize(16, 16))
        self.btnClose.setFixedSize(30, 24)
        self.btnClose.clicked.connect(self.closeRequested)

        btns.addWidget(self.btnMin)
        btns.addWidget(self.btnClose)

        # ----- ANA YERLEŞİM: sol – ORTA – sağ -----
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self.leftWrap)
        h.addWidget(self.title, 1)  # stretch=1 -> orta alan
        h.addWidget(self.rightWrap)

        self.applyStyle(dark=False)

        # İlk dengeleme
        QtCore.QTimer.singleShot(0, self._balanceSides)

    def _balanceSides(self):
        """Sağdaki butonların genişliği kadar sol bloğun minimum genişliğini ayarla ki başlık gerçek merkezde kalsın."""
        self.leftWrap.setMinimumWidth(self.rightWrap.sizeHint().width())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._balanceSides()

    def applyStyle(self, dark: bool):
        if dark:
            bg = "#0f172a"; fg = "#e2e8f0"; hover = "#1e293b"
        else:
            bg = "#f5f7fa"; fg = "#1e293b"; hover = "#e9eef6"
        self.setStyleSheet(f"""
            TitleBar {{ background:{bg}; border-bottom:1px solid rgba(0,0,0,0.08); }}
            #windowTitleLabel {{ color:{fg}; font-weight:600; }}
            QToolButton {{ border:0; background:transparent; }}
            QToolButton:hover {{ background:{hover}; border-radius:6px; }}
        """)

    # Sürükleme (değişmedi)
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag = True
            self._drag_offset = e.globalPos() - self.window().frameGeometry().topLeft()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
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
                border-radius:10px;
                padding:10px;
                text-align:center;
                color:{p['text_color']};
                font-size:13px;
            }}
            QPushButton:hover {{ background:{p['card_hover']}; }}
        """)

# ---------------- Ana Pencere ----------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(500, 325)  # status bar için biraz yüksek

        # Başlık çubuğunu kaldır (frameless)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)

        # Kısayollar
        QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self, activated=self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+M"), self, activated=self.showMinimized)

        # Ayarlar
        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme", "light")
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)
        self.saved_monitor_name = self.settings.value("monitor_name", "", type=str)

        self.palette = DARK if self.theme == "dark" else LIGHT
        self.enable_hotkeys = False

        # Üst bar + menü bar
        self.titleBar = TitleBar(APP_NAME, icon_path="icons/app.ico")
        self.titleBar.setToolTip("Pencereyi sürüklemek için tutun")
        self.titleBar.minimizeRequested.connect(self.showMinimized)
        self.titleBar.closeRequested.connect(self.close)

        self.menubar = QtWidgets.QMenuBar()
        self._build_menubar(self.menubar)

        top_container = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addWidget(self.titleBar)
        top_layout.addWidget(self.menubar)
        self.setMenuWidget(top_container)

        self._build_ui()
        self._build_statusbar()          # ⬅ status bar oluştur
        self._apply_theme()

        self.cfg = load_config()
        self._rebuild_cards()

        QtWidgets.QApplication.instance().screenAdded.connect(lambda s: self._rebuild_monitor_menu())
        QtWidgets.QApplication.instance().screenRemoved.connect(lambda s: self._rebuild_monitor_menu())
        self._rebuild_monitor_menu()

        if self.start_top_right:
            QtCore.QTimer.singleShot(0, self._move_to_selected_screen_top_right)

    # --------- StatusBar ---------
    def _build_statusbar(self):
        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)
        self._update_statusbar_text()

    def _update_statusbar_text(self):
        text_color = self.palette['text_color']
        self.status.setStyleSheet(f"color: {text_color}; font-size:12px;")
        self.status.showMessage("ViperaDev | v1.0.0")

    # --------- MENÜ ---------
    def _build_menubar(self, mb: QtWidgets.QMenuBar):
        # Tema (dinamik ikon + tooltip)
        self.act_dark = QtWidgets.QAction("", self, checkable=True)
        self.act_dark.setChecked(self.theme == "dark")
        self.act_dark.toggled.connect(self._toggle_theme)
        self.act_dark.setToolTip("Tema Değiştir")
        mb.addAction(self.act_dark)

        # Sağ üst (dinamik ikon + tooltip)
        self.act_topright = QtWidgets.QAction("", self, checkable=True)
        self.act_topright.setChecked(self.start_top_right)
        self.act_topright.toggled.connect(self._toggle_topright)
        self.act_topright.setToolTip("Pencere Konumu")
        mb.addAction(self.act_topright)

        # Monitör menüsü
        self.m_monitors = QtWidgets.QMenu()
        self.m_monitors.setToolTip("Monitör Seç")
        self.m_monitors.setIcon(QtGui.QIcon("icons/screen.png"))
        self.monitor_group = QtWidgets.QActionGroup(self)
        self.monitor_group.setExclusive(True)
        mb.addMenu(self.m_monitors)

        # Config aç
        self.act_open_cfg = QtWidgets.QAction(QtGui.QIcon("icons/jsondocument.png"), "", self)
        self.act_open_cfg.setToolTip("Ayar Dosyasını Aç")
        self.act_open_cfg.triggered.connect(self._open_config)
        mb.addAction(self.act_open_cfg)

        # Yenile
        self.act_reload = QtWidgets.QAction(QtGui.QIcon("icons/reload.png"), "", self)
        self.act_reload.setToolTip("Kısayolları Yeniden Yükle")
        self.act_reload.triggered.connect(self._reload_config)
        mb.addAction(self.act_reload)

        # Çıkış
        self.act_quit = QtWidgets.QAction(QtGui.QIcon("icons/exit.png"), "", self)
        self.act_quit.setToolTip("Uygulamadan Çık")
        self.act_quit.triggered.connect(QtWidgets.qApp.quit)
        mb.addAction(self.act_quit)

        self.status = self.statusBar()
        self.status.showMessage("Hazır")
        self._update_menu_icons()

    def _update_menu_icons(self):
        theme_icon = "icons/dark-theme.png" if self.theme == "dark" else "icons/light-theme.png"
        self.act_dark.setIcon(QtGui.QIcon(theme_icon))
        self.act_dark.setToolTip("Koyu Tema (tıkla: Aydınlık)" if self.theme == "dark" else "Aydınlık Tema (tıkla: Koyu)")

        pos_icon = "icons/topright.png" if self.start_top_right else "icons/free.png"
        self.act_topright.setIcon(QtGui.QIcon(pos_icon))
        self.act_topright.setToolTip("Sağ Üstte Açık (tıkla: Serbest)" if self.start_top_right else "Serbest Konum (tıkla: Sağ Üst)")

    # --------- MONİTÖR ---------
    def _rebuild_monitor_menu(self):
        self.m_monitors.clear()
        self.monitor_group = QtWidgets.QActionGroup(self)
        self.monitor_group.setExclusive(True)

        screens = QtWidgets.QApplication.screens()
        selected_action = None
        for s in screens:
            geo = s.geometry()
            label = f"{s.name()}  ({geo.width()}×{geo.height()})"
            if s == QtWidgets.QApplication.primaryScreen():
                label = "⭐ " + label
            act = QtWidgets.QAction(label, self, checkable=True)
            act.setData(s.name())
            self.monitor_group.addAction(act)
            self.m_monitors.addAction(act)
            if self.saved_monitor_name and s.name() == self.saved_monitor_name:
                selected_action = act

        self.m_monitors.addSeparator()
        act_auto = QtWidgets.QAction("Otomatik (birincil)", self, checkable=True)
        act_auto.setData("")
        self.monitor_group.addAction(act_auto)
        self.m_monitors.addAction(act_auto)

        if selected_action:
            selected_action.setChecked(True)
        else:
            act_auto.setChecked(True)

        self.monitor_group.triggered.connect(self._on_monitor_chosen)

    def _on_monitor_chosen(self, action: QtWidgets.QAction):
        self.saved_monitor_name = action.data() or ""
        self.settings.setValue("monitor_name", self.saved_monitor_name)
        self._move_to_selected_screen_top_right()

    def _move_to_selected_screen_top_right(self):
        target = None
        if self.saved_monitor_name:
            for s in QtWidgets.QApplication.screens():
                if s.name() == self.saved_monitor_name:
                    target = s; break
        if not target:
            target = QtWidgets.QApplication.primaryScreen()
        if not target: return
        avail = target.availableGeometry()
        self.move(avail.right() - self.width(), avail.top())

    # --------- UI ---------
    def _build_ui(self):
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central); v.setContentsMargins(8, 4, 8, 8)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{border:0;background:transparent;} QScrollArea>viewport{background:transparent;}")

        self.canvas = QtWidgets.QWidget(); self.canvas.setStyleSheet("background:transparent;")
        self.grid = QtWidgets.QGridLayout(self.canvas)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(8); self.grid.setVerticalSpacing(8)

        self.scroll.setWidget(self.canvas)
        v.addWidget(self.scroll)

    def _apply_theme(self):
        p = self.palette
        dark = (self.theme == "dark")
        self.titleBar.applyStyle(dark)
        self.setStyleSheet(f"QMainWindow {{ background:{p['bg']}; }} QMenuBar {{ background:transparent; }}")
        # kartların stilini yenile
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CardButton):
                w.p = self.palette
                w.apply_style()
        # statusbar rengi + yazısı
        self._update_statusbar_text()
        self._update_menu_icons()

    # --------- Grid ---------
    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

    def _rebuild_cards(self):
        self._clear_grid()
        buttons = load_config().get("buttons", [])
        btn_w = 72; gap = 8; inner_w = self.width() - 16
        cols = max(3, min(6, (inner_w + gap) // (btn_w + gap)))

        row = col = 0
        for b in buttons:
            card = CardButton(b, self.palette)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols: col = 0; row += 1

        self.status.showMessage(f"{len(buttons)} öğe yüklendi")

    # --------- Ayar Aksiyonları ---------
    def _toggle_theme(self, checked: bool):
        self.theme = "dark" if checked else "light"
        self.settings.setValue("theme", self.theme)
        self.palette = DARK if self.theme == "dark" else LIGHT
        self._apply_theme()

    def _toggle_topright(self, checked: bool):
        self.start_top_right = checked
        self.settings.setValue("start_top_right", checked)
        if checked:
            self._move_to_selected_screen_top_right()
        self._update_menu_icons()

    def _open_config(self):
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    def _reload_config(self):
        self._rebuild_cards()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")

# ---------------- Giriş ----------------
def main():
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORG); app.setApplicationName(APP_NAME)
    app.setWindowIcon(QtGui.QIcon("icons/app.ico"))  # opsiyonel

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
