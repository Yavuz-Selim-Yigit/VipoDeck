# app.py — PyQt5 kısayol paneli (frameless + 1 satır modern üst bar)
import sys, json, time, threading, subprocess, webbrowser
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui, keyboard

APP_NAME   = "Kısayol Paneli"
ORG        = "ViperaDev"
APP        = "ShortcutPanel"
CONFIG_PATH = Path(__file__).with_name("actions.json")

LIGHT = {
    "bg": "#f5f7fa",       # sayfa arka planı (açık)
    "fg": "#1e293b",       # metin rengi
    "muted": "#64748b",
    "card_bg": "#ffffff",  # KARTLAR AÇIK OLMALI
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


# ---------------- helpers ----------------
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"buttons": [], "hotkeys": {}}

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

# ---------------- title bar (one-line modern) ----------------
class TitleBar(QtWidgets.QWidget):
    minimizeRequested = QtCore.pyqtSignal()
    closeRequested = QtCore.pyqtSignal()
    themeToggled = QtCore.pyqtSignal(bool)          # checked
    toprightToggled = QtCore.pyqtSignal(bool)       # checked
    openConfigRequested = QtCore.pyqtSignal()
    reloadRequested = QtCore.pyqtSignal()
    monitorMenuRequested = QtCore.pyqtSignal(QtWidgets.QToolButton)

    def __init__(self, title: str, icon_path: str = None, parent=None):
        super().__init__(parent)
        self._drag = False
        self._drag_offset = QtCore.QPoint()

        self.setFixedHeight(40)

        # left area: app icon + menu icon buttons
        self.leftWrap = QtWidgets.QWidget()
        l = QtWidgets.QHBoxLayout(self.leftWrap)
        l.setContentsMargins(8, 0, 0, 0)
        l.setSpacing(6)

        self.appIcon = QtWidgets.QLabel()
        self.appIcon.setFixedSize(18, 18)
        if icon_path and Path(icon_path).exists():
            self.appIcon.setPixmap(QtGui.QPixmap(icon_path).scaled(18, 18, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        l.addWidget(self.appIcon)

        # theme toggle
        self.btnTheme = self._tool("", tooltip="Tema Değiştir")
        self.btnTheme.setCheckable(True)
        self.btnTheme.toggled.connect(self.themeToggled.emit)
        l.addWidget(self.btnTheme)

        # topright toggle
        self.btnTopRight = self._tool("", tooltip="Pencere Konumu")
        self.btnTopRight.setCheckable(True)
        self.btnTopRight.toggled.connect(self.toprightToggled.emit)
        l.addWidget(self.btnTopRight)

        # monitor menu
        self.btnMonitor = self._tool("icons/screen.png", tooltip="Monitör Seç")
        self.btnMonitor.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnMonitor.setMenu(QtWidgets.QMenu(self))
        l.addWidget(self.btnMonitor)

        # open config
        self.btnCfg = self._tool("icons/jsondocument.png", tooltip="Ayar Dosyasını Aç")
        l.addWidget(self.btnCfg)

        # reload
        self.btnReload = self._tool("icons/reload.png", tooltip="Kısayolları Yeniden Yükle")
        l.addWidget(self.btnReload)

        # center: title
        self.title = QtWidgets.QLabel(title)
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.title.setStyleSheet("font-weight:600;")
        self.title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        # right: minimize + close
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

        # main layout
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self.leftWrap)
        h.addWidget(self.title, 1)
        h.addWidget(self.rightWrap)

        # wire menu actions
        self.btnCfg.clicked.connect(self.openConfigRequested)
        self.btnReload.clicked.connect(self.reloadRequested)
        self.monitorMenuRequested.emit(self.btnMonitor)

    def _tool(self, icon_path: str, tooltip: str):
        b = QtWidgets.QToolButton()
        b.setIcon(QtGui.QIcon(icon_path) if icon_path else QtGui.QIcon())
        b.setIconSize(QtCore.QSize(16, 16))
        b.setFixedSize(28, 24)
        b.setToolTip(tooltip)
        b.setAutoRaise(True)
        return b

    # theming
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

    # dragging (frameless)
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

# ---------------- card button ----------------
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

# ---------------- main window ----------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(500, 330)  # status bar için +30px
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)

        # shortcuts
        QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self, activated=self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+M"), self, activated=self.showMinimized)

        # settings
        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme", "light")
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)
        self.saved_monitor_name = self.settings.value("monitor_name", "", type=str)
        self.palette = DARK if self.theme == "dark" else LIGHT

        # title bar
        self.titleBar = TitleBar(APP_NAME, icon_path="icons/app.ico")
        self.titleBar.themeToggled.connect(self._toggle_theme)
        self.titleBar.toprightToggled.connect(self._toggle_topright)
        self.titleBar.openConfigRequested.connect(self._open_config)
        self.titleBar.reloadRequested.connect(self._reload_config)
        self.titleBar.minimizeRequested.connect(self.showMinimized)
        self.titleBar.closeRequested.connect(self.close)
        # monitor button menu will be built after UI init

        # central UI
        self._build_ui()
        self._build_statusbar()

        # apply theme & icons
        self._apply_theme()
        self._update_toolbar_icons()

        # load items
        self.cfg = load_config()
        self._rebuild_cards()

        # monitor menu
        self._rebuild_monitor_menu()

        # place titlebar as the menu widget (top single row)
        self.setMenuWidget(self.titleBar)

        # move to selected screen/top-right on start
        if self.start_top_right:
            QtCore.QTimer.singleShot(0, self._move_to_selected_screen_top_right)

        # keep monitor list fresh
        QtWidgets.QApplication.instance().screenAdded.connect(lambda s: self._rebuild_monitor_menu())
        QtWidgets.QApplication.instance().screenRemoved.connect(lambda s: self._rebuild_monitor_menu())

        # reflect saved toggles
        self.titleBar.btnTheme.setChecked(self.theme == "dark")
        self.titleBar.btnTopRight.setChecked(self.start_top_right)

    # ----- status bar -----
    def _build_statusbar(self):
        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)
        self._update_statusbar_text()

    def _update_statusbar_text(self):
        self.status.setStyleSheet(f"color:{self.palette['text_color']}; font-size:12px;")
        self.status.showMessage("ViperaDev | v1.0.0")

    # ----- UI -----
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
        self.grid.setHorizontalSpacing(10); self.grid.setVerticalSpacing(10)

        self.scroll.setWidget(self.canvas)
        v.addWidget(self.scroll)

    # ----- theming -----
    def _apply_theme(self):
        dark = (self.theme == "dark")
        self.palette = DARK if dark else LIGHT
        self.titleBar.applyStyle(dark)
        self.setStyleSheet(f"QMainWindow {{ background:{self.palette['bg']}; }}")
        # refresh cards
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CardButton):
                w.p = self.palette
                w.apply_style()
        self._update_statusbar_text()
        self._update_toolbar_icons()

    def _update_toolbar_icons(self):
        # dynamic icons for theme/topright
        theme_icon = "icons/dark-theme.png" if self.theme == "dark" else "icons/light-theme.png"
        self.titleBar.btnTheme.setIcon(QtGui.QIcon(theme_icon))
        pos_icon = "icons/topright.png" if self.start_top_right else "icons/free.png"
        self.titleBar.btnTopRight.setIcon(QtGui.QIcon(pos_icon))

    # ----- monitor menu -----
    def _rebuild_monitor_menu(self):
        m = QtWidgets.QMenu(self)
        group = QtWidgets.QActionGroup(m)
        group.setExclusive(True)

        selected_action = None
        for s in QtWidgets.QApplication.screens():
            geo = s.geometry()
            label = f"{s.name()}  ({geo.width()}×{geo.height()})"
            if s == QtWidgets.QApplication.primaryScreen():
                label = "⭐ " + label
            act = QtWidgets.QAction(label, m, checkable=True)
            act.setData(s.name())
            m.addAction(act)
            group.addAction(act)
            if self.saved_monitor_name and s.name() == self.saved_monitor_name:
                selected_action = act

        m.addSeparator()
        act_auto = QtWidgets.QAction("Otomatik (birincil)", m, checkable=True)
        act_auto.setData("")
        m.addAction(act_auto)
        group.addAction(act_auto)

        if selected_action: selected_action.setChecked(True)
        else: act_auto.setChecked(True)

        group.triggered.connect(self._on_monitor_chosen)

        self.titleBar.btnMonitor.setMenu(m)

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

    # ----- grid -----
    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

    def _rebuild_cards(self):
        self._clear_grid()
        buttons = load_config().get("buttons", [])
        btn_w = 72; gap = 10; inner_w = self.width() - 16
        cols = max(3, min(6, (inner_w + gap) // (btn_w + gap)))
        row = col = 0
        for b in buttons:
            card = CardButton(b, self.palette)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols: col = 0; row += 1
        self.status.showMessage(f"{len(buttons)} öğe yüklendi")

    # ----- actions -----
    def _toggle_theme(self, checked: bool):
        self.theme = "dark" if checked else "light"
        self.settings.setValue("theme", self.theme)
        self._apply_theme()

    def _toggle_topright(self, checked: bool):
        self.start_top_right = checked
        self.settings.setValue("start_top_right", checked)
        if checked:
            self._move_to_selected_screen_top_right()
        self._update_toolbar_icons()

    def _open_config(self):
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    def _reload_config(self):
        self._rebuild_cards()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")

# ---------------- run ----------------
def main():
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORG); app.setApplicationName(APP_NAME)
    app.setWindowIcon(QtGui.QIcon("icons/app.ico"))

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
