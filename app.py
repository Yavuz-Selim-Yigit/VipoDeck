# modern_app_with_menu.py — PyQt5 kısayol paneli (500x300, sağ üstte açılır, üst bar + Ayarlar menüsü, ikonlu butonlar)
# Kurulum: pip install pyqt5 keyboard pyautogui

import sys, json, time, threading, subprocess, webbrowser
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui, keyboard

APP_NAME = "Kısayol Paneli"
CONFIG_PATH = Path(__file__).with_name("actions.json")
ORG = "ViperaDev"
APP = "ShortcutPanel"

LIGHT = {
    "bg": "#f5f7fa", "fg": "#1e293b", "muted": "#64748b",
    "card_bg": "#ffffff", "card_border": "#e2e8f0", "card_hover": "#f1f5f9",
    "input_bg": "#ffffff", "input_border": "#cbd5e1"
}
DARK = {
    "bg": "#0f172a", "fg": "#e2e8f0", "muted": "#94a3b8",
    "card_bg": "#1e293b", "card_border": "#334155", "card_hover": "#273449",
    "input_bg": "#1e293b", "input_border": "#334155"
}

GLOBAL_QSS = """
* { font-family: 'Segoe UI','Inter','Roboto',sans-serif; }
QPushButton { outline:0; }
QToolTip { color:#fff; background:#111; border:1px solid #333; }
"""

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"buttons": [], "hotkeys": {}}

def run_action(a: dict):
    t = (a.get("type") or "").lower()
    if t == "open":
        tgt = a.get("target", "")
        if tgt.startswith("http"):
            webbrowser.open(tgt)
        else:
            p = Path(tgt)
            try:
                subprocess.Popen([str(p)], shell=True) if p.exists() else webbrowser.open(tgt)
            except Exception:
                pass
    elif t == "keys":
        time.sleep(0.04)
        try:
            pyautogui.hotkey(*a.get("keys", []))
        except Exception:
            pass

class CardButton(QtWidgets.QPushButton):
    def __init__(self, data: dict, palette: dict):
        super().__init__()
        self.data = data
        self.p = palette
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMinimumHeight(60)
        self.setIconSize(QtCore.QSize(40, 40))
        self.setStyleSheet(self._style())

        icon_path = data.get("icon")
        if icon_path and Path(icon_path).exists():
            self.setIcon(QtGui.QIcon(icon_path))
            self.setText("")  # ikon-only
        else:
            # İkon yoksa label göster
            self.setText(data.get("label", "?"))

        self.clicked.connect(lambda: run_action(self.data))

    def _style(self):
        p = self.p
        return f"""
        QPushButton {{
            background:{p['card_bg']};
            border:1px solid {p['card_border']};
            border-radius:10px;
            padding:10px;
            text-align:center;
            color:{p['fg']};
            font-size:13px;
        }}
        QPushButton:hover {{
            background:{p['card_hover']};
        }}
        """

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DesktopIcon))
        self.setFixedSize(500, 300)

        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme", "light")
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)
        self.palette = DARK if self.theme == "dark" else LIGHT

        # Konum: sağ üst (isteğe bağlı)
        if self.start_top_right:
            screen_geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
            x = screen_geo.width() - self.width()
            y = 0
            self.move(x, y)

        self._build_ui()
        self._apply_theme()
        self._load_and_build()
        self._start_hotkeys()

    # --- Menü ve toolbar ---
    def _build_ui(self):
        # Menü Çubuğu
        mb = self.menuBar()
        menu_settings = mb.addMenu("Ayarlar")

        # Tema toggle
        self.act_theme_dark = QtWidgets.QAction("Koyu Tema", self, checkable=True)
        self.act_theme_dark.setChecked(self.theme == "dark")
        self.act_theme_dark.toggled.connect(self._toggle_theme_from_menu)
        menu_settings.addAction(self.act_theme_dark)

        # Başlangıç konumu
        self.act_top_right = QtWidgets.QAction("Başlangıçta sağ üstte aç", self, checkable=True)
        self.act_top_right.setChecked(self.start_top_right)
        self.act_top_right.toggled.connect(self._toggle_top_right)
        menu_settings.addAction(self.act_top_right)

        menu_settings.addSeparator()

        # Config işlemleri
        act_open_cfg = QtWidgets.QAction("actions.json'i aç", self)
        act_open_cfg.triggered.connect(self._open_config)
        menu_settings.addAction(act_open_cfg)

        act_reload = QtWidgets.QAction("Yapılandırmayı Yenile", self)
        act_reload.triggered.connect(self._reload_config)
        menu_settings.addAction(act_reload)

        menu_settings.addSeparator()

        act_quit = QtWidgets.QAction("Çıkış", self)
        act_quit.triggered.connect(QtWidgets.qApp.quit)
        menu_settings.addAction(act_quit)

        # Merkez içerik
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central)
        v.setContentsMargins(8, 4, 8, 8)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{border:0;background:transparent;} QScrollArea>viewport{background:transparent;}")

        self.canvas = QtWidgets.QWidget()
        self.canvas.setStyleSheet("background:transparent;")
        self.grid = QtWidgets.QGridLayout(self.canvas)
        self.grid.setContentsMargins(0,0,0,0)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(8)

        self.scroll.setWidget(self.canvas)
        v.addWidget(self.scroll)

        # StatusBar (isteğe bağlı, minimal)
        self.status = self.statusBar()
        self.status.showMessage("Hazır")

    def _apply_theme(self):
        p = self.palette
        base_qss = GLOBAL_QSS + f"""
        QMainWindow {{ background:{p['bg']}; }}
        QMenuBar {{ background:transparent; }}
        QMenuBar::item {{ padding: 6px 10px; color:{p['fg']}; }}
        QMenu {{ background:{p['card_bg']}; border:1px solid {p['card_border']}; }}
        QMenu::item:selected {{ background:{p['card_hover']}; }}
        QStatusBar {{ background:transparent; color:{p['muted']}; }}
        """
        self.setStyleSheet(base_qss)

    def _open_config(self):
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    def _load_and_build(self):
        self.cfg = load_config()
        self._rebuild_cards()

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _rebuild_cards(self):
        self._clear_grid()
        items = self.cfg.get("buttons", [])
        # 500x300 pencerede makul kolon sayısı (ikonlu küçük kartlar)
        cols = 5  # 5 sütun, 2-3 satır sığar
        row = col = 0
        for b in items:
            card = CardButton(b, self.palette)
            # küçük ikon ızgara görünümü için min boyut
            card.setMinimumSize(80, 80)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols:
                col = 0; row += 1

    # --- Menü aksiyonları ---
    def _toggle_theme_from_menu(self, checked: bool):
        self.theme = "dark" if checked else "light"
        self.settings.setValue("theme", self.theme)
        self.palette = DARK if self.theme == "dark" else LIGHT
        self._apply_theme()
        self._rebuild_cards()

    def _toggle_top_right(self, checked: bool):
        self.start_top_right = checked
        self.settings.setValue("start_top_right", checked)

    # --- Hotkeys ---
    def _start_hotkeys(self):
        self.hk_thread = threading.Thread(target=self._register_hotkeys, daemon=True)
        self.hk_thread.start()

    def _register_hotkeys(self):
        try: keyboard.unhook_all_hotkeys()
        except Exception: pass
        hk = self.cfg.get("hotkeys", {})
        btns = self.cfg.get("buttons", [])
        for combo, idx in hk.items():
            try:
                idx = int(idx)
                if 0 <= idx < len(btns):
                    keyboard.add_hotkey(combo, lambda a=btns[idx]: run_action(a))
            except Exception:
                pass
        try: keyboard.wait(suppress=False)
        except Exception: pass


def main():
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORG)
    app.setApplicationName(APP_NAME)

    w = MainWindow()
    w.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
