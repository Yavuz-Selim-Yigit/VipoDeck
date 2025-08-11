# modern_app.py — PyQt5 ile modern kısayol paneli (arka plan düzeltildi)
# Kurulum: pip install pyqt5 keyboard pyautogui

import sys, json, time, threading, subprocess, webbrowser
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui, keyboard

APP_NAME = "Kısayol Paneli (Modern)"
CONFIG_PATH = Path(__file__).with_name("actions.json")
ORG = "ViperaDev"
APP = "ShortcutPanelModern"

# ---- Tema ----
LIGHT = {
    "bg":"#f6f7fb","fg":"#0f172a","muted":"#64748b",
    "card_bg":"#ffffff","card_border":"#e6e8ee","card_hover":"#f0f2f6",
    "input_bg":"#ffffff","input_border":"#e5e7eb"
}
DARK = {
    "bg":"#0b1220","fg":"#e6e9ef","muted":"#9aa4b2",
    "card_bg":"#0f172a","card_border":"#1f2937","card_hover":"#111827",
    "input_bg":"#0f172a","input_border":"#1f2937"
}

GLOBAL_QSS = """
* { font-family: 'Segoe UI','Inter','Roboto',sans-serif; }
QToolTip { color:#fff; background:#111; border:1px solid #333; }
QPushButton { outline:0; }
"""

# ---- Config ----
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"buttons": [], "hotkeys": {}}

# ---- Aksiyon ----
def run_action(a: dict):
    t = (a.get("type") or "").lower()
    if t == "open":
        tgt = a.get("target", "")
        if tgt.startswith("http"): webbrowser.open(tgt)
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

# ---- Kart Buton ----
class CardButton(QtWidgets.QPushButton):
    def __init__(self, data: dict, palette: dict):
        super().__init__()
        self.data = data
        self.p = palette
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMinimumHeight(84)
        self.setStyleSheet(self._style())
        self.setIconSize(QtCore.QSize(22,22))

        # İkon isteğe bağlı
        icon = data.get("icon")
        if icon and Path(icon).exists():
            self.setIcon(QtGui.QIcon(icon))

        # Başlık + Alt başlık
        title = data.get("label","—")
        sub = self._subtitle(data)
        self.setText(f"{title}\n{sub}")
        self.clicked.connect(lambda: run_action(self.data))

    def enterEvent(self, e):
        self.setProperty("hover", True)
        self.setStyleSheet(self._style())
        super().enterEvent(e)
    def leaveEvent(self, e):
        self.setProperty("hover", False)
        self.setStyleSheet(self._style())
        super().leaveEvent(e)

    def _subtitle(self, d):
        t = (d.get("type") or "").lower()
        if t == "open":
            tgt = d.get("target","")
            if tgt.startswith("http"):
                return QtCore.QUrl(tgt).host() or tgt
            return Path(tgt).name
        if t == "keys":
            return "+".join(k.upper() for k in d.get("keys", []))
        return ""

    def _style(self):
        p = self.p
        hover = self.property("hover") is True
        bg = p['card_hover'] if hover else p['card_bg']
        return f"""
        QPushButton {{
            background:{bg}; border:1px solid {p['card_border']};
            border-radius:16px; padding:12px; text-align:left;
            color:{p['fg']}; font-size:15px;
        }}
        """

# ---- Ana Pencere ----
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DesktopIcon))
        self.resize(1000, 640)

        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme","light")
        self.palette = DARK if self.theme == "dark" else LIGHT

        self._build_ui()
        self._apply_theme()
        self._load_and_build()
        self._start_hotkeys()

    # --- UI ---
    def _build_ui(self):
        top = QtWidgets.QToolBar()
        top.setMovable(False)
        self.addToolBar(QtCore.Qt.TopToolBarArea, top)

        title = QtWidgets.QLabel("🚀 Kısayol Paneli")
        title.setStyleSheet("font-size:18px;font-weight:700;margin-right:8px;")
        top.addWidget(title)

        top.addSeparator()
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Ara: Gmail, VS Code, Win+V…")
        self.search.textChanged.connect(self._rebuild_cards)
        self.search.setFixedWidth(360)
        top.addWidget(self.search)

        top.addSeparator()
        self.theme_btn = QtWidgets.QPushButton("🌙" if self.theme=="light" else "☀️")
        self.theme_btn.setToolTip("Tema değiştir")
        self.theme_btn.clicked.connect(self._toggle_theme)
        top.addWidget(self.theme_btn)

        top.addSeparator()
        reload_btn = QtWidgets.QPushButton("Yenile")
        reload_btn.clicked.connect(self._reload_config)
        top.addWidget(reload_btn)

        # Orta alan: scroll + canvas
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central)
        v.setContentsMargins(12, 8, 12, 12)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        # KRİTİK: Viewport'u şeffaf yap, çerçeveyi kaldır → arkadaki koyu blok sorununu çözer
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{border:0;background:transparent;} QScrollArea>viewport{background:transparent;}")

        self.canvas = QtWidgets.QWidget()
        self.canvas.setObjectName("Canvas")
        self.canvas.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.canvas.setStyleSheet("background:transparent;")

        self.grid = QtWidgets.QGridLayout(self.canvas)
        self.grid.setContentsMargins(0,0,0,0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)

        self.scroll.setWidget(self.canvas)
        v.addWidget(self.scroll)

        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)

    def _apply_theme(self):
        p = self.palette
        base_qss = GLOBAL_QSS + f"""
        QMainWindow {{ background:{p['bg']}; }}
        QToolBar {{ background:transparent; border:none; padding:6px; }}
        QLineEdit {{ background:{p['input_bg']}; color:{p['fg']}; border:1px solid {p['input_border']}; border-radius:10px; }}
        QStatusBar {{ background:transparent; color:{p['muted']}; }}
        """
        self.setStyleSheet(base_qss)

    # --- Veri yükle & kartları oluştur ---
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
        q = (self.search.text() or "").strip().lower()
        items = [b for b in self.cfg.get("buttons", []) if q in b.get("label"," ").lower()]
        cols = max(3, self.width() // 260)
        row = col = 0
        for b in items:
            card = CardButton(b, self.palette)
            r, c = row, col
            self.grid.addWidget(card, r, c)
            col += 1
            if col >= cols:
                col = 0; row += 1
        self.status.showMessage(f"{len(items)} öğe • Tema: {'Koyu' if self.palette is DARK else 'Açık'}")

    # --- Tema ---
    def _toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.settings.setValue("theme", self.theme)
        self.palette = DARK if self.theme == "dark" else LIGHT
        self._apply_theme()
        self._rebuild_cards()
        self.theme_btn.setText("🌙" if self.theme=="light" else "☀️")

    # --- Hotkeys ---
    def _start_hotkeys(self):
        self.hk_thread = threading.Thread(target=self._register_hotkeys, daemon=True)
        self.hk_thread.start()

    def _register_hotkeys(self):
        try: keyboard.unhook_all_hotkeys()
        except Exception: pass
        hk = self.cfg.get("hotkeys", {})
        btns = self.cfg.get("buttons", [])
        reg = 0
        for combo, idx in hk.items():
            try:
                idx = int(idx)
                if 0 <= idx < len(btns):
                    keyboard.add_hotkey(combo, lambda a=btns[idx]: run_action(a))
                    reg += 1
            except Exception:
                pass
        try: keyboard.wait(suppress=False)
        except Exception: pass
        self.status.showMessage(self.status.currentMessage() + f" • {reg} global kısayol")

    # --- Config ---
    def _reload_config(self):
        self._load_and_build()
        try: keyboard.unhook_all_hotkeys()
        except Exception: pass
        if not getattr(self, "hk_thread", None) or not self.hk_thread.is_alive():
            self._start_hotkeys()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")


def main():
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORG)
    app.setApplicationName(APP_NAME)

    w = MainWindow()
    w.show()

    # Yönetici uyarısı (global hotkey)
    try:
        keyboard.add_hotkey("ctrl+shift+0", lambda: None)
        keyboard.remove_hotkey("ctrl+shift+0")
    except Exception:
        QtWidgets.QMessageBox.information(w, "Bilgi", "Global kısayollar için yönetici izni gerekebilir.\nUygulamayı 'Yönetici olarak çalıştır' ile başlatmayı deneyebilirsin.")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
