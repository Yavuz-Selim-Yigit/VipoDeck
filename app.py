# app.py — PyQt5 kısayol paneli (500x300, sağ üst, menü + reload, ikon-only, tema + monitör seçimi)
import sys, json, time, threading, subprocess, webbrowser  # standart kütüphaneler: sistem, json, zamanlama, iş parçacığı, proses ve web
from pathlib import Path  # dosya yolu işlemleri için
from PyQt5 import QtCore, QtGui, QtWidgets  # PyQt5 ana modülleri
import pyautogui, keyboard  # tuş simülasyonu ve global kısayollar (opsiyonel)

APP_NAME   = "Kısayol Paneli"  # Uygulama adı (başlık çubuğunda)
ORG        = "ViperaDev"       # QSettings için organizasyon anahtarı
APP        = "ShortcutPanel"    # QSettings için uygulama anahtarı
CONFIG_PATH = Path(__file__).with_name("actions.json")  # actions.json aynı klasörde beklenir

# ---- Tema paletleri ----
LIGHT = {
    "bg": "#f5f7fa", "fg": "#1e293b", "muted": "#64748b",  # arka plan, ana metin, ikincil metin
    "card_bg": "#ffffff", "card_border": "#e2e8f0", "card_hover": "#f1f5f9",  # kart görünümleri
    "menu_bg": "#ffffff", "menu_border": "#e2e8f0", "text_color": "#000000"  # menü ve yazı rengi
}
DARK = {
    "bg": "#0f172a", "fg": "#e2e8f0", "muted": "#94a3b8",  # koyu tema renkleri
    "card_bg": "#1e293b", "card_border": "#334155", "card_hover": "#273449",
    "menu_bg": "#111827", "menu_border": "#334155", "text_color": "#ffffff"
}

GLOBAL_QSS = """
* { font-family: 'Segoe UI','Inter','Roboto',sans-serif; }  /* genel yazı tipleri */
QToolTip { color:#fff; background:#111; border:1px solid #333; }  /* tooltip stili */
QPushButton { outline: 0; }  /* buton focus çizgisini kapat */
"""

# ---- Config yükleme ----
def load_config():  # actions.json dosyasını güvenli şekilde oku
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)  # json içeriğini döndür
    except Exception:
        return {"buttons": [], "hotkeys": {}}  # hata durumunda boş yapı

# ---- Aksiyon çalıştır ----
def open_target(target: str):  # hedefi (URL/uygulama) aç
    if not target:
        return  # boşsa hiçbir şey yapma
    if target.startswith(("http://", "https://")):
        webbrowser.open(target); return  # URL ise varsayılan tarayıcıda aç
    try:
        subprocess.Popen([target], shell=True)  # Windows/uygulama yolu ise çalıştır
    except Exception:
        try: webbrowser.open(target)  # son çare: tarayıcıyla dene
        except Exception: pass

def run_action(a: dict):  # buton eylemini yürüt
    t = (a.get("type") or "").lower()  # eylem tipi (open/keys)
    if t == "open":
        open_target(a.get("target", ""))  # hedefi aç
    elif t == "keys":
        time.sleep(0.03)  # küçük gecikme (pencere odaklanması için iyi olabilir)
        seq = a.get("keys", [])  # tuş dizisi
        if seq:
            try: pyautogui.hotkey(*seq)  # tuş kombinasyonunu gönder
            except Exception: pass  # hata olursa yut

# ---- Kart buton ----
class CardButton(QtWidgets.QPushButton):  # her bir kısayol butonu
    def __init__(self, data: dict, palette: dict):
        super().__init__()
        self.data = data  # actions.json'daki buton verisi
        self.p = palette  # aktif tema paleti
        self.setCursor(QtCore.Qt.PointingHandCursor)  # el işareti imleç
        self.setIconSize(QtCore.QSize(40, 40))  # ikon boyutu
        self.setMinimumSize(72, 72)  # minimum buton boyutu
        self.apply_style()  # temaya göre stil uygula

        icon_path = data.get("icon")  # ikon yolu
        if icon_path and Path(icon_path).exists():
            self.setIcon(QtGui.QIcon(icon_path)); self.setText("")  # sadece ikon göster
        else:
            self.setText(data.get("label", "?"))  # ikon yoksa yazı göster

        self.clicked.connect(lambda: run_action(self.data))  # tıklama → aksiyon

    def apply_style(self):  # stil metodu (tema değişince tekrar çağrılır)
        p = self.p
        self.setStyleSheet(f"""
        QPushButton {{
            background:{p['card_bg']};  /* kart arka planı */
            border:1px solid {p['card_border']};  /* kart kenarlığı */
            border-radius:10px;  /* yuvarlatılmış köşe */
            padding:10px;  /* iç boşluk */
            text-align:center;  /* içeriği ortala */
            color:{p['text_color']};  /* yazı rengi (tema bağlı) */
            font-size:13px;  /* yazı boyutu */
        }}
        QPushButton:hover {{ background:{p['card_hover']}; }}  /* hover rengi */
        """)

# ---- Ana pencere ----
class MainWindow(QtWidgets.QMainWindow):  # uygulamanın ana penceresi
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)  # başlık
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DesktopIcon))  # sistem ikonu
        self.setFixedSize(500, 300)  # sabit pencere boyutu

        self.settings = QtCore.QSettings(ORG, APP)  # kalıcı ayarlar depolama
        self.theme = self.settings.value("theme", "light")  # tema (light/dark)
        self.start_top_right = self.settings.value("start_top_right", True, type=bool)  # sağ üstte başla
        self.saved_monitor_name = self.settings.value("monitor_name", "", type=str)  # seçili monitör adı

        self.palette = DARK if self.theme == "dark" else LIGHT  # aktif palet
        self.enable_hotkeys = False  # global kısayollar kapalı (istersen True yap)

        self._build_menu()  # menü çubuğunu oluştur
        self._build_ui()    # içerik alanını kur
        self._apply_theme() # temayı uygula

        self.cfg = load_config()  # actions.json yükle
        self._rebuild_cards()     # butonları çiz

        # Monitör değişikliklerini izle ve menüyü yenile (tak-çıkar senaryosu)
        QtWidgets.QApplication.instance().screenAdded.connect(lambda s: self._rebuild_monitor_menu())
        QtWidgets.QApplication.instance().screenRemoved.connect(lambda s: self._rebuild_monitor_menu())
        self._rebuild_monitor_menu()  # ilk menü kurulumu

        # Açılışta seçili ekranın sağ üstüne taşı
        if self.start_top_right:
            QtCore.QTimer.singleShot(0, self._move_to_selected_screen_top_right)

    # --- Menü ---
    def _build_menu(self):  # menü çubuğu ve ayarlar
        mb = self.menuBar()  # menü çubuğu
        self.m_settings = mb.addMenu("Ayarlar")  # "Ayarlar" ana menü

        self.act_dark = QtWidgets.QAction("Koyu Tema", self, checkable=True)  # tema anahtarı
        self.act_dark.setChecked(self.theme == "dark")  # mevcut durumu yansıt
        self.act_dark.toggled.connect(self._toggle_theme)  # değişince çalıştır
        self.m_settings.addAction(self.act_dark)

        self.act_topright = QtWidgets.QAction("Başlangıçta sağ üstte aç", self, checkable=True)  # konum anahtarı
        self.act_topright.setChecked(self.start_top_right)
        self.act_topright.toggled.connect(self._toggle_topright)
        self.m_settings.addAction(self.act_topright)

        # Monitör alt menüsü
        self.m_settings.addSeparator()  # ayraç çizgisi
        self.m_monitors = self.m_settings.addMenu("Monitör")  # monitör menüsü
        self.monitor_group = QtWidgets.QActionGroup(self)  # tek seçimli grup
        self.monitor_group.setExclusive(True)  # yalnız birini seç

        self.m_settings.addSeparator()  # ayraç
        act_open_cfg = QtWidgets.QAction("actions.json'i aç", self)  # config dosyasını aç
        act_open_cfg.triggered.connect(self._open_config)
        self.m_settings.addAction(act_open_cfg)

        act_reload = QtWidgets.QAction("Yapılandırmayı Yenile", self)  # yeniden yükle
        act_reload.triggered.connect(self._reload_config)
        self.m_settings.addAction(act_reload)

        self.m_settings.addSeparator()  # ayraç
        act_quit = QtWidgets.QAction("Çıkış", self)  # çıkış eylemi
        act_quit.triggered.connect(QtWidgets.qApp.quit)
        self.m_settings.addAction(act_quit)

        self.status = self.statusBar()  # durum çubuğu
        self.status.showMessage("Hazır")  # başlangıç mesajı

    # Monitör menüsünü yeniden kur
    def _rebuild_monitor_menu(self):
        self.m_monitors.clear()  # eski öğeleri sil
        self.monitor_group = QtWidgets.QActionGroup(self)  # grup tazele
        self.monitor_group.setExclusive(True)

        screens = QtWidgets.QApplication.screens()  # tüm ekranlar
        selected_action = None  # önceden seçili olanı işaretlemek için
        for s in screens:
            geo = s.geometry()  # çözünürlük bilgisi
            label = f"{s.name()}  ({geo.width()}×{geo.height()})"  # menü etiketi
            if s == QtWidgets.QApplication.primaryScreen():
                label = "⭐ " + label  # birincil ekranı yıldızla
            act = QtWidgets.QAction(label, self, checkable=True)  # seçim yapılabilir eylem
            act.setData(s.name())  # ekran adını data'ya koy (kalıcı referans)
            self.monitor_group.addAction(act)  # gruba ekle
            self.m_monitors.addAction(act)     # menüye ekle
            if self.saved_monitor_name and s.name() == self.saved_monitor_name:
                selected_action = act  # kayıtlı monitörü bul

        # “Otomatik (birincil ekran)” seçeneği
        self.m_monitors.addSeparator()
        act_auto = QtWidgets.QAction("Otomatik (birincil ekran)", self, checkable=True)
        act_auto.setData("")  # boş data → otomatik mod
        self.monitor_group.addAction(act_auto)
        self.m_monitors.addAction(act_auto)

        # Seçimi ayarla (kayıtlı varsa onu; yoksa otomatik)
        if selected_action:
            selected_action.setChecked(True)
        else:
            act_auto.setChecked(True)

        # Tıklama sinyali: seçim değişince çağrılır
        self.monitor_group.triggered.connect(self._on_monitor_chosen)

    def _on_monitor_chosen(self, action: QtWidgets.QAction):  # monitör seçildiğinde
        self.saved_monitor_name = action.data() or ""  # adı kaydet (boşsa otomatik)
        self.settings.setValue("monitor_name", self.saved_monitor_name)  # QSettings'e yaz
        self._move_to_selected_screen_top_right()  # pencereyi taşı

    def _move_to_selected_screen_top_right(self):  # pencereyi seçili ekranın sağ üstüne konumlandır
        # Hedef ekran: ayarda varsa adıyla, yoksa birincil
        target = None
        if self.saved_monitor_name:
            for s in QtWidgets.QApplication.screens():
                if s.name() == self.saved_monitor_name:
                    target = s; break
        if not target:
            target = QtWidgets.QApplication.primaryScreen()
        if not target:
            return  # ekran bulunamazsa vazgeç
        avail = target.availableGeometry()  # görev çubuğu/dok ile kullanılabilir alan
        x = avail.right() - self.width()    # sağ kenar - pencere genişliği
        y = avail.top()                     # üst kenar
        self.move(x, y)                     # pencereyi taşı

    # --- UI ---
    def _build_ui(self):  # içerik düzeni
        central = QtWidgets.QWidget(); self.setCentralWidget(central)  # merkez widget
        v = QtWidgets.QVBoxLayout(central); v.setContentsMargins(8, 4, 8, 8)  # dikey layout ve kenar boşlukları

        self.scroll = QtWidgets.QScrollArea()  # kaydırılabilir alan
        self.scroll.setWidgetResizable(True)   # içerik genişliğine göre şekillensin
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)  # çerçevesiz
        self.scroll.setStyleSheet(
            "QScrollArea{border:0;background:transparent;} "
            "QScrollArea>viewport{background:transparent;}"
        )  # arka planı şeffaf tut (artefakt oluşmasın)

        self.canvas = QtWidgets.QWidget(); self.canvas.setStyleSheet("background:transparent;")  # içerik taşıyıcı
        self.grid = QtWidgets.QGridLayout(self.canvas)  # ızgara düzeni
        self.grid.setContentsMargins(0, 0, 0, 0)  # iç kenar boşlukları yok
        self.grid.setHorizontalSpacing(8); self.grid.setVerticalSpacing(8)  # ızgara aralıkları

        self.scroll.setWidget(self.canvas); v.addWidget(self.scroll)  # canvas'ı scroll içine koy

    def _apply_theme(self):  # tema QSS'lerini uygula
        p = self.palette
        base_qss = GLOBAL_QSS + f"""
        QMainWindow {{ background:{p['bg']}; }}  /* ana pencere arka planı */
        QMenuBar {{ background:transparent; color:{p['fg']}; }}  /* menü çubuğu */
        QMenuBar::item {{ padding:6px 10px; }}  /* menü çubuğu öğe boşluğu */
        QMenu {{ background:{p['menu_bg']}; border:1px solid {p['menu_border']}; color:{p['text_color']}; }}  /* açılır menü */
        QMenu::item:selected {{ background:{p['card_hover']}; }}  /* menü hover */
        QStatusBar {{ background:transparent; color:{p['muted']}; }}  /* durum çubuğu */
        """
        self.setStyleSheet(base_qss)  # uygulamaya uygula

        # Kartların stilini güncelle (tema değişiminde görünümü yenile)
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if isinstance(w, CardButton):
                w.p = self.palette  # yeni paleti aktar
                w.apply_style()     # stili yeniden kur

    # --- Yardımcılar ---
    def _open_config(self):  # actions.json dosyasını işletim sisteminde aç
        if CONFIG_PATH.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CONFIG_PATH)))
        else:
            QtWidgets.QMessageBox.information(self, "Bilgi", "actions.json bulunamadı.")

    def _clear_grid(self):  # ızgaradaki tüm widget'ları temizle
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

    def _rebuild_cards(self):  # actions.json'a göre butonları yeniden inşa et
        self._clear_grid()
        buttons = self.cfg.get("buttons", [])  # buton listesi
        btn_w = 72; gap = 8; inner_w = self.width() - 16  # içerik genişliği tahmini
        cols = max(3, min(6, (inner_w + gap) // (btn_w + gap)))  # pencere genişliğine göre kolon sayısı

        row = col = 0  # satır/sütun sayaçları
        for b in buttons:
            card = CardButton(b, self.palette)  # kart oluştur
            self.grid.addWidget(card, row, col)  # ızgaraya ekle
            col += 1
            if col >= cols: col = 0; row += 1  # satır sonu -> yeni satıra geç

        self.status.showMessage(f"{len(buttons)} öğe yüklendi")  # durum çubuğu mesajı

    # --- Ayarlar aksiyonları ---
    def _toggle_theme(self, checked: bool):  # koyu/açık tema değiştir
        self.theme = "dark" if checked else "light"  # durumdan temayı belirle
        self.settings.setValue("theme", self.theme)   # kalıcı ayara yaz
        self.palette = DARK if self.theme == "dark" else LIGHT  # aktif paleti güncelle
        self._apply_theme()  # QSS uygula

    def _toggle_topright(self, checked: bool):  # sağ üstte aç ayarı
        self.start_top_right = checked
        self.settings.setValue("start_top_right", checked)
        if checked:
            self._move_to_selected_screen_top_right()  # açıkken hemen sağ üste taşı

    def _reload_config(self):  # actions.json'u yeniden yükle
        self.cfg = load_config()
        self._rebuild_cards()
        if self.enable_hotkeys:  # global kısayollar açıksa yeniden kur
            try: keyboard.unhook_all_hotkeys()
            except Exception: pass
            if not getattr(self, "hk_thread", None) or not self.hk_thread.is_alive():
                self._start_hotkeys()
        QtWidgets.QMessageBox.information(self, "Yenilendi", "actions.json yeniden yüklendi.")

    # --- Global Hotkeys (opsiyonel) ---
    def _start_hotkeys(self):  # hotkey dinleyicisini başlat
        self.hk_thread = threading.Thread(target=self._register_hotkeys, daemon=True)
        self.hk_thread.start()

    def _register_hotkeys(self):  # hotkey kayıtlarını yap
        try: keyboard.unhook_all_hotkeys()
        except Exception: pass
        hk = self.cfg.get("hotkeys", {}); buttons = self.cfg.get("buttons", [])
        for combo, idx in hk.items():
            try:
                idx = int(idx)
                if 0 <= idx < len(buttons):
                    keyboard.add_hotkey(combo, lambda a=buttons[idx]: run_action(a))  # tuş → buton aksiyonu
            except Exception: pass
        try: keyboard.wait(suppress=False)  # dinlemeyi sürdür
        except Exception: pass

    # İlk gösterimde seçilen monitöre taşı
    def showEvent(self, e):  # pencere gösterildiğinde tetiklenir
        super().showEvent(e)
        if self.start_top_right:
            QtCore.QTimer.singleShot(0, self._move_to_selected_screen_top_right)  # UI hazır olduktan sonra taşı

# ---- Uygulama girişi ----
def main():  # programın giriş noktası
    if hasattr(QtWidgets.QApplication, "setAttribute"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)   # yüksek DPI ölçekleme
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)      # yüksek DPI ikonlar

    app = QtWidgets.QApplication(sys.argv)  # uygulama nesnesi
    app.setOrganizationName(ORG); app.setApplicationName(APP_NAME)  # QSettings kimliği

    w = MainWindow(); w.show()  # ana pencereyi oluştur ve göster
    sys.exit(app.exec_())  # olay döngüsünü çalıştır ve çıkış kodunu döndür

if __name__ == "__main__":  # doğrudan çalıştırıldıysa
    main()  # main fonksiyonunu çağır
