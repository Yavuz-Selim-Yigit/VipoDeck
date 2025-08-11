# modern_app.py — PyQt5 ile modern kısayol paneli (düzeltilmiş sürüm)
# Özellikler: kart butonlar (gölge), açık/koyu tema, arama, tray, global hotkeys
# Gerekenler: pip install pyqt5 keyboard pyautogui

import sys, json, time, threading, subprocess, webbrowser
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui
import keyboard

APP_NAME = "Kısayol Paneli (Modern)"
CONFIG_PATH = Path(__file__).with_name("actions.json")
SETTINGS_ORG = "ViperaDev"
SETTINGS_APP = "ShortcutPanelModern"

# ----------------- Yardımcılar -----------------

def load_config():
    if not CONFIG_PATH.exists():
        return {"buttons": [], "hotkeys": {}}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Config error:", e)
        return {"buttons": [], "hotkeys": {}}


def open_target(target: str):
    if not target:
        return
    try:
        if target.startswith(("http://", "https://")):
            webbrowser.open(target)
            return
        p = Path(target)
        if p.exists():
            subprocess.Popen([str(p)], shell=True)
        else:
            webbrowser.open(target)
    except Exception as e:
        QtWidgets.QMessageBox.warning(None, "Açma Hatası", f"{target}{e}")


def press_keys(seq):
    if not seq:
        return
    time.sleep(0.05)
    try:
        pyautogui.hotkey(*seq)
    except Exception as e:
        QtWidgets.QMessageBox.warning(None, "Tuş Gönderme Hatası", str(e))


def run_action(action: dict):
    t = (action.get("type") or "").lower()
    if t == "open":
        open_target(action.get("target", ""))
    elif t == "keys":
        press_keys(action.get("keys", []))

# ----------------- Stil / Tema -----------------

LIGHT_QSS = """
* { font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; }
QWidget { background: #f6f7fb; color: #0f172a; }
QLineEdit { padding:10px 12px; border-radius:12px; border:1px solid #dfe3ea; background:#fff; }
QToolButton, QPushButton#ToolbarBtn { padding:10px 14px; border-radius:12px; border:1px solid #dfe3ea; background:#fff; }
QToolButton:hover, QPushButton#ToolbarBtn:hover { background:#f0f2f6; }
QLabel#hint { color:#6b7280; }
"""

DARK_QSS = """
* { font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; }
QWidget { background: #0b1220; color: #e5e7eb; }
QLineEdit { padding:10px 12px; border-radius:12px; border:1px solid #1f2937; background:#0f172a; color:#e5e7eb; }
QToolButton, QPushButton#ToolbarBtn { padding:10px 14px; border-radius:12px; border:1px solid #1f2937; background:#0f172a; }
QToolButton:hover, QPushButton#ToolbarBtn:hover { background:#111827; }
QLabel#hint { color:#9ca3af; }
"""

# Kart görünümü için basit stil (Qt'de CSS "backdrop-filter" desteklenmediği için sade tutuldu)
CARD_BASE = """
QPushButton {
    border: 1px solid rgba(255,255,255,30);
    background: rgba(255,255,255,0.75);
    border-radius: 16px;
    padding: 14px; text-align: left; font-size: 15px;
}
QPushButton:hover { background: rgba(255,255,255,0.9); }
"""

CARD_BASE_DARK = """
QPushButton {
    border: 1px solid rgba(255,255,255,12);
    background: rgba(15,23,42,0.75);
    border-radius: 16px;
    padding: 14px; text-align: left; font-size: 15px; color:#e5e7eb;
}
QPushButton:hover { background: rgba(30,41,59,0.85); }
"""

# ----------------- UI Bileşenleri -----------------

class CardButton(QtWidgets.QPushButton):
    clickedWithData = QtCore.pyqtSignal(dict)

    def __init__(self, data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setMinimumHeight(84)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.setLayoutDirection(QtCore.Qt.LeftToRight)

        # İçerik düzeni (ikon + metin)
        wrapper = QtWidgets.QWidget(self)
        h = QtWidgets.QHBoxLayout(wrapper)
        h.setContentsMargins(6, 2, 6, 2)
        h.setSpacing(12)

        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(28, 28)
        icon_path = data.get("icon")
        if icon_path and Path(icon_path).exists():
            icon_label.setPixmap(QtGui.QPixmap(icon_path).scaled(28, 28, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            icon_label.setText("🔗" if data.get("type") == "open" else "⌨️")
            icon_label.setAlignment(QtCore.Qt.AlignCenter)

        text_box = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel(data.get("label", "—"))
        title.setStyleSheet("font-size:16px; font-weight:600;")
        subtitle = QtWidgets.QLabel(self._subtitle_text(data))
        subtitle.setObjectName("hint")
        subtitle.setStyleSheet("font-size:12px;")
        text_box.addWidget(title)
        text_box.addWidget(subtitle)

        h.addWidget(icon_label)
        h.addLayout(text_box)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.addWidget(wrapper)

        # Gölge efekti
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QtGui.QColor(0, 0, 0, 55))
        self.setGraphicsEffect(shadow)

        self.clicked.connect(lambda: self.clickedWithData.emit(self.data))

    def _subtitle_text(self, d):
        t = d.get("type")
        if t == "open":
            tgt = d.get("target", "")
            if tgt.startswith("http"):
                return tgt.split("//", 1)[-1]
            return Path(tgt).name or tgt
        if t == "keys":
            keys = d.get("keys", [])
            # Kısa tuş isimlerini büyük harf göster
            return "+".join(k.upper() if len(k) == 1 else k.title() for k in keys)
        return ""


class Header(QtWidgets.QWidget):
    themeToggled = QtCore.pyqtSignal()
    searchChanged = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        title = QtWidgets.QLabel("🚀 Kısayol Paneli")
        title.setStyleSheet("font-size:20px; font-weight:700;")
        lay.addWidget(title)
        lay.addStretch(1)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Ara: Gmail, VS Code, Win+V…")
        self.search.textChanged.connect(self.searchChanged)

        self.themeBtn = QtWidgets.QToolButton()
        self.themeBtn.setText("🌗")
        self.themeBtn.setToolTip("Tema değiştir")
        self.themeBtn.clicked.connect(self.themeToggled)

        self.reloadBtn = QtWidgets.QToolButton()
        self.reloadBtn.setText("Yenile")

        lay.addWidget(self.search, 2)
        lay.addWidget(self.themeBtn)
        lay.addWidget(self.reloadBtn)


class ModernPanel(QtWidgets.QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        self.resize(900, 580)

        self.settings = QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._dark = self.settings.value("theme", "light") == "dark"

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Header
        self.header = Header()
        self.header.themeToggled.connect(self.toggle_theme)
        self.header.searchChanged.connect(self.on_search)
        self.header.reloadBtn.clicked.connect(self.reload_config)
        root.addWidget(self.header)

        # Scroll alanı + grid
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        wrap = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(wrap)
        self.grid.setSpacing(14)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(wrap)
        root.addWidget(self.scroll, 1)

        # Alt bilgi
        self.status = QtWidgets.QLabel()
        self.status.setObjectName("hint")
        root.addWidget(self.status)

        # Tray
        self.make_tray()

        # Butonlar ve hotkeys
        self.buttons_cache = []
        self.query = ""
        self.apply_theme()  # önce tema uygula
        self.rebuild_buttons()
        self.start_hotkey_thread()

    # ---------- Tema ----------
    def apply_theme(self):
        self.setStyleSheet(DARK_QSS if self._dark else LIGHT_QSS)
        self.card_css = CARD_BASE_DARK if self._dark else CARD_BASE

    def toggle_theme(self):
        self._dark = not self._dark
        self.settings.setValue("theme", "dark" if self._dark else "light")
        self.apply_theme()
        self.rebuild_buttons()

    # ---------- Tray ----------
    def make_tray(self):
        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        menu = QtWidgets.QMenu()
        a_show = menu.addAction("Göster")
        a_show.triggered.connect(self.showNormal)
        a_hide = menu.addAction("Gizle")
        a_hide.triggered.connect(self.hide)
        a_cfg = menu.addAction("actions.json'i Aç")
        a_cfg.triggered.connect(self.open_config)
        a_reload = menu.addAction("Yenile")
        a_reload.triggered.connect(self.reload_config)
        menu.addSeparator()
        a_quit = menu.addAction("Çıkış")
        a_quit.triggered.connect(QtWidgets.qApp.quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def open_config(self):
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    # ---------- Grid ----------
    def clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.buttons_cache.clear()

    def rebuild_buttons(self):
        self.clear_grid()
        buttons = self.cfg.get("buttons", [])

        # Filtre
        q = (self.query or "").strip().lower()
        if q:
            buttons = [b for b in buttons if q in b.get("label", "").lower()]

        # Responsive kolon sayısı
        cols = max(3, self.width() // 260)
        for i, data in enumerate(buttons):
            btn = CardButton(data)
            btn.setStyleSheet(self.card_css)
            btn.clickedWithData.connect(run_action)
            r, c = divmod(i, cols)
            self.grid.addWidget(btn, r, c)
            self.buttons_cache.append(btn)

        self.status.setText(f"{len(buttons)} öğe • Tema: {'Koyu' if self._dark else 'Açık'}")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.rebuild_buttons()

    def on_search(self, text):
        self.query = text
        self.rebuild_buttons()

    # ---------- Hotkeys ----------
    def start_hotkey_thread(self):
        self.hk_thread = threading.Thread(target=self.register_hotkeys, daemon=True)
        self.hk_thread.start()

    def register_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        hk = self.cfg.get("hotkeys", {})
        buttons = self.cfg.get("buttons", [])
        for combo, index in hk.items():
            try:
                idx = int(index)
            except Exception:
                continue
            if 0 <= idx < len(buttons):
                action = buttons[idx]
                try:
                    keyboard.add_hotkey(combo, lambda a=action: run_action(a))
                except Exception:
                    pass
        try:
            keyboard.wait(suppress=False)
        except Exception:
            pass

    # ---------- Config ----------
    def reload_config(self):
        self.cfg = load_config()
        self.rebuild_buttons()
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        if not getattr(self, "hk_thread", None) or not self.hk_thread.is_alive():
            self.start_hotkey_thread()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")


# ----------------- Uygulama Girişi -----------------

def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(SETTINGS_ORG)

    w = ModernPanel(load_config())
    w.show()

    # Global hotkey izni uyarısı
    try:
        keyboard.add_hotkey("ctrl+shift+0", lambda: None)
        keyboard.remove_hotkey("ctrl+shift+0")
    except Exception:
        QtWidgets.QMessageBox.information(
            w,
            "Bilgi",
            "Global kısayollar için yönetici izni gerekebilir.Uygulamayı 'Yönetici olarak çalıştır' ile başlatmayı deneyebilirsin.")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
