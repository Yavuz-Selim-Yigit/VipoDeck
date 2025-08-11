# app.py — PyQt5 kısayol paneli (500x300, sağ üst, menü + reload, ikon-only, tema + monitör seçimi)
import sys, json, time, threading, subprocess, webbrowser
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
import pyautogui, keyboard

APP_NAME   = "Kısayol Paneli"
ORG        = "ViperaDev"
APP        = "ShortcutPanel"
CONFIG_PATH = Path(__file__).with_name("actions.json")

# ---- Tema paletleri ----
LIGHT = {
    "bg": "#f5f7fa", "fg": "#1e293b", "muted": "#64748b",
    "card_bg": "#ffffff", "card_border": "#e2e8f0", "card_hover": "#f1f5f9",
    "menu_bg": "#ffffff", "menu_border": "#e2e8f0", "text_color": "#000000"
}
DARK = {
    "bg": "#0f172a", "fg": "#e2e8f0", "muted": "#94a3b8",
    "card_bg": "#1e293b", "card_border": "#334155", "card_hover": "#273449",
    "menu_bg": "#111827", "menu_border": "#334155", "text_color": "#ffffff"
}

GLOBAL_QSS = """
* { font-family: 'Segoe UI','Inter','Roboto',sans-serif; }
QToolTip { color:#fff; background:#111; border:1px solid #333; }
QPushButton { outline: 0; }
"""

# ---- Config yükleme ----
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"buttons": [], "hotkeys": {}}

# ---- Aksiyon çalıştır ----
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

# ---- Kart buton ----
class CardButton(QtWidgets.QPushButton):
    def __init__(self, data: dict, palette: dict):
        super().__init__()
        self.data = data
        self.p = palette
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setIconSize(QtCore.QSize(40, 40))
        self.setMinimumSize(72, 72)
        self.apply_style()

        icon_path = data.get("icon")
        if icon_path and Path(icon_path).exists():
            self.setIcon(QtGui.QIcon(icon_path)); self.setText("")
        else:
            self.setText(data.get("label", "?"))

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

# ---- Ana pencere ----
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DesktopIcon))
        self.setFixedSize(500, 300)

        self.settings = QtCore.QSettings(ORG, APP)
        self.theme = self.settings.value("theme", "light")
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)
        self.saved_monitor_name = self.settings.value("monitor_name", "", type=str)

        self.palette = DARK if self.theme == "dark" else LIGHT
        self.enable_hotkeys = False

        self._build_menu()
        self._build_ui()
        self._apply_theme()

        self.cfg = load_config()
        self._rebuild_cards()

        # Monitör değişikliklerini izle ve menüyü yenile
        QtWidgets.QApplication.instance().screenAdded.connect(lambda s: self._rebuild_monitor_menu())
        QtWidgets.QApplication.instance().screenRemoved.connect(lambda s: self._rebuild_monitor_menu())
        self._rebuild_monitor_menu()

        # Açılışta sağ üst
        if self.start_top_right:
            QtCore.QTimer.singleShot(0, self._move_to_selected_screen_top_right)

    # --- Menü ---
    def _build_menu(self):
        mb = self.menuBar()
        self.m_settings = mb.addMenu("Ayarlar")

        self.act_dark = QtWidgets.QAction("Koyu Tema", self, checkable=True)
        self.act_dark.setChecked(self.theme == "dark")
        self.act_dark.toggled.connect(self._toggle_theme)
        self.m_settings.addAction(self.act_dark)

        self.act_topright = QtWidgets.QAction("Başlangıçta sağ üstte aç", self, checkable=True)
        self.act_topright.setChecked(self.start_top_right)
        self.act_topright.toggled.connect(self._toggle_topright)
        self.m_settings.addAction(self.act_topright)

        # Monitör alt menüsü
        self.m_settings.addSeparator()
        self.m_monitors = self.m_settings.addMenu("Monitör")
        self.monitor_group = QtWidgets.QActionGroup(self)
        self.monitor_group.setExclusive(True)

        self.m_settings.addSeparator()
        act_open_cfg = QtWidgets.QAction("actions.json'i aç", self)
        act_open_cfg.triggered.connect(self._open_config)
        self.m_settings.addAction(act_open_cfg)

        act_reload = QtWidgets.QAction("Yapılandırmayı Yenile", self)
        act_reload.triggered.connect(self._reload_config)
        self.m_settings.addAction(act_reload)

        self.m_settings.addSeparator()
        act_quit = QtWidgets.QAction("Çıkış", self)
        act_quit.triggered.connect(QtWidgets.qApp.quit)
        self.m_settings.addAction(act_quit)

        self.status = self.statusBar()
        self.status.showMessage("Hazır")

    # Monitör menüsünü yeniden kur
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
            act.setData(s.name())  # kalıcı isim
            self.monitor_group.addAction(act)
            self.m_monitors.addAction(act)
            if self.saved_monitor_name and s.name() == self.saved_monitor_name:
                selected_action = act

        # “Otomatik (birincil ekran)” seçeneği
        self.m_monitors.addSeparator()
        act_auto = QtWidgets.QAction("Otomatik (birincil ekran)", self, checkable=True)
        act_auto.setData("")
        self.monitor_group.addAction(act_auto)
        self.m_monitors.addAction(act_auto)

        # Seçimi ayarla
        if selected_action:
            selected_action.setChecked(True)
        else:
            act_auto.setChecked(True)

        # Sinyal
        self.monitor_group.triggered.connect(self._on_monitor_chosen)

    def _on_monitor_chosen(self, action: QtWidgets.QAction):
        self.saved_monitor_name = action.data() or ""
        self.settings.setValue("monitor_name", self.saved_monitor_name)
        self._move_to_selected_screen_top_right()

    def _move_to_selected_screen_top_right(self):
        # Hedef ekran: ayarda varsa adıyla, yoksa birincil
        target = None
        if self.saved_monitor_name:
            for s in QtWidgets.QApplication.screens():
                if s.name() == self.saved_monitor_name:
                    target = s; break
        if not target:
            target = QtWidgets.QApplication.primaryScreen()
        if not target:
            return
        avail = target.availableGeometry()
        x = avail.right() - self.width()
        y = avail.top()
        self.move(x, y)

    # --- UI ---
    def _build_ui(self):
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central); v.setContentsMargins(8, 4, 8, 8)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setStyleSheet(
            "QScrollArea{border:0;background:transparent;} "
            "QScrollArea>viewport{background:transparent;}"
        )

        self.canvas = QtWidgets.QWidget(); self.canvas.setStyleSheet("background:transparent;")
        self.grid = QtWidgets.QGridLayout(self.canvas)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(8); self.grid.setVerticalSpacing(8)

        self.scroll.setWidget(self.canvas); v.addWidget(self.scroll)

    def _apply_theme(self):
        p = self.palette
        base_qss = GLOBAL_QSS + f"""
        QMainWindow {{ background:{p['bg']}; }}
        QMenuBar {{ background:transparent; color:{p['fg']}; }}
        QMenuBar::item {{ padding:6px 10px; }}
        QMenu {{ background:{p['menu_bg']}; border:1px solid {p['menu_border']}; color:{p['text_color']}; }}
        QMenu::item:selected {{ background:{p['card_hover']}; }}
        QStatusBar {{ background:transparent; color:{p['muted']}; }}
        """
        self.setStyleSheet(base_qss)

        # Kartların stilini güncelle
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CardButton):
                w.p = self.palette
                w.apply_style()

    # --- Yardımcılar ---
    def _open_config(self):
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

    def _rebuild_cards(self):
        self._clear_grid()
        buttons = self.cfg.get("buttons", [])
        btn_w = 72; gap = 8; inner_w = self.width() - 16
        cols = max(3, min(6, (inner_w + gap) // (btn_w + gap)))

        row = col = 0
        for b in buttons:
            card = CardButton(b, self.palette)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols: col = 0; row += 1

        self.status.showMessage(f"{len(buttons)} öğe yüklendi")

    # --- Ayarlar aksiyonları ---
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

    def _reload_config(self):
        self.cfg = load_config()
        self._rebuild_cards()
        if self.enable_hotkeys:
            try: keyboard.unhook_all_hotkeys()
            except Exception: pass
            if not getattr(self, "hk_thread", None) or not self.hk_thread.is_alive():
                self._start_hotkeys()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")

    # --- Global Hotkeys (opsiyonel) ---
    def _start_hotkeys(self):
        self.hk_thread = threading.Thread(target=self._register_hotkeys, daemon=True)
        self.hk_thread.start()

    def _register_hotkeys(self):
        try: keyboard.unhook_all_hotkeys()
        except Exception: pass
        hk = self.cfg.get("hotkeys", {}); buttons = self.cfg.get("buttons", [])
        for combo, idx in hk.items():
            try:
                idx = int(idx)
                if 0 <= idx < len(buttons):
                    keyboard.add_hotkey(combo, lambda a=buttons[idx]: run_action(a))
            except Exception: pass
        try: keyboard.wait(suppress=False)
        except Exception: pass

    # İlk gösterimde seçilen monitöre taşı
    def showEvent(self, e):
        super().showEvent(e)
        if self.start_top_right:
            QtCore.QTimer.singleShot(0, self._move_to_selected_screen_top_right)

# ---- Uygulama girişi ----
def main():
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORG); app.setApplicationName(APP_NAME)

    w = MainWindow(); w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
