# app.py
import os
import sys
import json
import time
import threading
import subprocess
import webbrowser
from pathlib import Path

# --- 3rd party ---
# pip install pyqt5 keyboard pyautogui
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui
import keyboard

APP_NAME = "Kısayol Paneli"
CONFIG_PATH = Path(__file__).with_name("actions.json")
SETTINGS_ORG = "ViperaDev"
SETTINGS_APP = "ShortcutPanel"

# ---------- Yardımcılar ----------

def load_config():
    if not CONFIG_PATH.exists():
        return {"buttons": [], "hotkeys": {}}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        QtWidgets.QMessageBox.warning(None, "Yapılandırma Hatası", str(e))
        return {"buttons": [], "hotkeys": {}}

def open_target(target: str):
    """Uygulama/URL aç."""
    if not target:
        return
    try:
        if target.startswith(("http://", "https://")):
            webbrowser.open(target)
            return
        p = Path(target)
        if p.exists():
            # .exe veya kısayol olabilir
            subprocess.Popen([str(p)], shell=True)
        else:
            # dosya yoksa URL gibi dene
            webbrowser.open(target)
    except Exception as e:
        QtWidgets.QMessageBox.warning(None, "Açma Hatası", f"{target}\n\n{e}")

def press_keys(seq):
    """Ardışık hotkey gönder (örn: ['win','shift','s'])."""
    if not seq:
        return
    # odak problemlerine karşı çok küçük gecikme
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

# ---------- UI Bileşenleri ----------

class ShortcutButton(QtWidgets.QPushButton):
    def __init__(self, data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setMinimumHeight(64)
        self.setCheckable(False)
        self.setStyleSheet("""
            QPushButton {
                font-size: 15px;
                padding: 12px;
                border-radius: 14px;
                border: 1px solid #d9d9d9;
                background: #ffffff;
                text-align: left;
            }
            QPushButton:hover { background: #f6f7f9; }
            QPushButton:pressed { background: #eef0f3; }
        """)
        label = data.get("label", "—")
        self.setText(label)

        # Opsiyonel ikon desteği (data["icon"] = "icons/youtube.png")
        icon_path = data.get("icon")
        if icon_path:
            p = Path(icon_path)
            if p.exists():
                self.setIcon(QtGui.QIcon(str(p)))
                self.setIconSize(QtCore.QSize(22, 22))

        self.clicked.connect(lambda: run_action(self.data))

class ShortcutPanel(QtWidgets.QWidget):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        self.resize(720, 420)

        self.settings = QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.restore_geometry()

        self.grid = QtWidgets.QGridLayout()
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(12, 12, 12, 12)

        # Üst bar
        top = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Filtrele…")
        self.search.textChanged.connect(self.rebuild_buttons)
        reload_btn = QtWidgets.QToolButton()
        reload_btn.setText("Yenile")
        reload_btn.clicked.connect(self.reload_config)
        top.addWidget(self.search)
        top.addWidget(reload_btn)

        # Alt bilgi
        self.status = QtWidgets.QLabel("Hazır")
        self.status.setStyleSheet("color:#666;")

        # Ana layout
        root = QtWidgets.QVBoxLayout(self)
        root.addLayout(top)
        root.addLayout(self.grid)
        root.addWidget(self.status)

        self.buttons_cache = []  # (widget, data)
        self.rebuild_buttons()
        self.make_tray()
        self.start_hotkey_thread()

    # --- Pencere konumu/ebat kaydet ---
    def closeEvent(self, e):
        self.save_geometry()
        super().closeEvent(e)

    def save_geometry(self):
        self.settings.setValue("geometry", self.saveGeometry())

    def restore_geometry(self):
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)

    # --- Tray menüsü ---
    def make_tray(self):
        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))

        menu = QtWidgets.QMenu()
        act_show = menu.addAction("Göster")
        act_show.triggered.connect(self.showNormal)

        act_hide = menu.addAction("Gizle")
        act_hide.triggered.connect(self.hide)

        act_open_cfg = menu.addAction("actions.json'i Aç")
        act_open_cfg.triggered.connect(self.open_config_file)

        act_reload = menu.addAction("Yapılandırmayı Yenile")
        act_reload.triggered.connect(self.reload_config)

        menu.addSeparator()
        act_quit = menu.addAction("Çıkış")
        act_quit.triggered.connect(QtWidgets.qApp.quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.showNormal()
                self.activateWindow()
            else:
                self.hide()

    def open_config_file(self):
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    # --- Butonları kur ---
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
        query = (self.search.text() or "").strip().lower()
        # Basit filtre
        if query:
            buttons = [b for b in buttons if query in (b.get("label","").lower())]

        # Kolon sayısını pencere genişliğine göre ayarla
        cols = max(3, self.width() // 220)
        for i, bdata in enumerate(buttons):
            btn = ShortcutButton(bdata)
            r, c = divmod(i, cols)
            self.grid.addWidget(btn, r, c)
            self.buttons_cache.append((btn, bdata))

        self.status.setText(f"{len(buttons)} öğe")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Responsive grid
        self.rebuild_buttons()

    # --- Hotkeys ---
    def start_hotkey_thread(self):
        self.hk_thread = threading.Thread(target=self.register_hotkeys, daemon=True)
        self.hk_thread.start()

    def register_hotkeys(self):
        # Önce eski hotkey’leri sıfırla (aynı süreç içinde tekrar çağrılırsa)
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        hk = self.cfg.get("hotkeys", {})
        buttons = self.cfg.get("buttons", [])
        count_registered = 0

        for combo, index in hk.items():
            try:
                idx = int(index)
            except Exception:
                continue
            if 0 <= idx < len(buttons):
                action = buttons[idx]
                try:
                    keyboard.add_hotkey(combo, lambda a=action: run_action(a))
                    count_registered += 1
                except Exception:
                    # Yönetici izni yoksa veya başka app engelliyorsa hata verebilir
                    pass

        # Dinleyiciyi canlı tut
        try:
            keyboard.wait(suppress=False)
        except Exception:
            pass

        # Bilgi amaçlı (UI thread değil)
        self.status.setText(f"{count_registered} global kısayol yüklendi.")

    # --- Config yenile ---
    def reload_config(self):
        self.cfg = load_config()
        self.rebuild_buttons()
        # Hotkey thread’i yeniden başlatmak için:
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        if not getattr(self, "hk_thread", None) or not self.hk_thread.is_alive():
            self.start_hotkey_thread()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")

# ---------- Uygulama Girişi ----------

def main():
    # Windows’ta DPI bulanıklığını azalt
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(SETTINGS_ORG)
    app.setApplicationDisplayName(APP_NAME)

    cfg = load_config()
    w = ShortcutPanel(cfg)
    w.show()

    # keyboard modülü yönetici izni isterse kullanıcıyı bilgilendir
    try:
        # Basit kontrol: hotkey ekleyip kaldırmayı dener
        keyboard.add_hotkey("ctrl+shift+0", lambda: None)
        keyboard.remove_hotkey("ctrl+shift+0")
    except Exception:
        QtWidgets.QMessageBox.information(
            w,
            "Bilgi",
            "Global kısayollar için yönetici izni gerekebilir.\n"
            "Uygulamayı 'Yönetici olarak çalıştır'mayı deneyebilirsin."
        )

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
