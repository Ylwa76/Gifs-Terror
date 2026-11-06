import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton,
                              QLabel, QHBoxLayout, QVBoxLayout, QSizeGrip)
from PyQt5.QtCore import Qt, QPoint, QRectF, QRect
from PyQt5.QtGui import (QPainter, QColor, QLinearGradient, QFont, QPen,
                         QBrush, QPainterPath, QPixmap)
from settings_window import SettingsWindow

class XPButton(QPushButton):
    """Кнопка в стиле Windows XP (свернуть / развернуть / закрыть)"""
    def __init__(self, symbol, parent=None, close=False):
        super().__init__(symbol, parent)
        self.close_btn = close
        self.setFixedSize(21, 21)
        self.setCursor(Qt.ArrowCursor)
        self.hover = False
        self.pressed = False
        self.setFlat(True)
        self.setFocusPolicy(Qt.NoFocus)
        

    def enterEvent(self, e):
        self.hover = True
        self.update()


    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.pressed = True
            self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.pressed = False
        self.update()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        radius = 3.0

        # --- Фон кнопки ---
        if self.close_btn:
            # Красная кнопка закрытия
            if self.pressed:
                c_top, c_mid, c_bot = QColor(170, 40, 25), QColor(200, 60, 40), QColor(150, 30, 20)
            elif self.hover:
                c_top, c_mid, c_bot = QColor(255, 160, 130), QColor(230, 90, 60), QColor(190, 50, 30)
            else:
                c_top, c_mid, c_bot = QColor(240, 130, 100), QColor(210, 80, 55), QColor(175, 50, 30)
        else:
            # Синяя кнопка
            if self.pressed:
                c_top, c_mid, c_bot = QColor(50, 100, 180), QColor(70, 130, 200), QColor(40, 80, 150)
            elif self.hover:
                c_top, c_mid, c_bot = QColor(150, 200, 255), QColor(90, 160, 235), QColor(40, 100, 190)
            else:
                c_top, c_mid, c_bot = QColor(120, 175, 240), QColor(75, 135, 220), QColor(35, 90, 175)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(0.5, c_mid)
        grad.setColorAt(1.0, c_bot)

        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)

        p.fillPath(path, QBrush(grad))

        # Светлый блик сверху (глянец XP)
        highlight = QLinearGradient(0, 0, 0, self.height() * 0.5)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 180))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))

        path_hl = QPainterPath()
        path_hl.addRoundedRect(QRectF(1.5, 1.0, self.width() - 3, self.height() * 0.45),
                               radius - 1, radius - 1)
        p.fillPath(path_hl, QBrush(highlight))

        # Рамка
        border_color = QColor(120, 30, 20) if self.close_btn else QColor(30, 70, 130)
        p.setPen(QPen(border_color, 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # --- Символ ---
        p.setPen(QColor(255, 255, 255))
        font = QFont("Marlett", 8)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignCenter, self.text())

            # --- Символ ---
        p.setPen(QColor(255, 255, 255))
        symbol = self.text()

        # Marlett используем ТОЛЬКО для стандартных символов окна
        if symbol in ("0", "1", "r", "2"):  # minimize, maximize, close, restore
            font = QFont("Marlett", 8)
        else:
            font = QFont("Segoe UI", 10)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignCenter, symbol)
        


class XPTitleBar(QWidget):
    def __init__(self, parent, title="Окно"):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(30)
        self.drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 3, 4)
        layout.setSpacing(4)

        # --- Иконка окна ---
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setPixmap(self._make_icon())

        # --- Заголовок ---
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Trebuchet MS", 9, QFont.Bold))
        self.title_label.setStyleSheet("color: white; background: transparent;")
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # --- Кнопки ---
        self.btn_min = XPButton("0")
        self.btn_max = XPButton("1")
        self.btn_close = XPButton("r", close=True)

        # ⬇️ НОВАЯ КНОПКА НАСТРОЕК (шестерёнка)
        self.btn_settings = XPButton("⚙", parent=None)   # или "=" / "S"
        self.btn_settings.setToolTip("Настройки")

        self.btn_min.clicked.connect(self.parent_window.showMinimized)
        self.btn_max.clicked.connect(self.toggle_max)
        self.btn_close.clicked.connect(self.parent_window.close)
        self.btn_settings.clicked.connect(self.open_settings)   # ⬅️ новый слот
        

        layout.addWidget(self.icon_label)
        layout.addSpacing(2)
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.btn_settings)   # ⬅️ ДО кнопок окна
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)
# ⬇️ Новый метод

    def open_settings(self):
        from settings_window import SettingsWindow
        win = getattr(self, "_settings_win", None)
        if win is None or not win.isVisible():
            self._settings_win = SettingsWindow("config.json")
            self._settings_win.settings_changed.connect(self._on_settings_saved)
            
            # ⬇️ ПОДКЛЮЧАЕМ КНОПКУ МУЗЫКИ ⬇️
            content = getattr(self.parent_window, "content", None)
            if content is not None and hasattr(content, "next_music"):
                self._settings_win.next_music_requested.connect(content.next_music)
            # ⬆️ ПОДКЛЮЧАЕМ КНОПКУ МУЗЫКИ ⬆️
            
        self._settings_win.show()
        self._settings_win.raise_()

    def _on_settings_saved(self, new_cfg):
        """Применить настройки на лету (если родитель умеет)."""
        print(f"[settings] сохранены: {new_cfg}")
        # Пробуем найти GifContent и применить
        w = self.parent_window
        content = getattr(w, "content", None)
        if content is not None and hasattr(content, "apply_config"):
            content.apply_config(new_cfg)
        else:
            print("[settings] применяю только к следующему запуску")

    def _make_icon(self):
        """Загружает иконку из файла icon.ico."""
        pm = QPixmap("icon.ico")
        if pm.isNull():
            # Если файл не найден или битый — рисуем заглушку
            print("[icon] Не удалось загрузить icon.ico для заголовка")
            pm = QPixmap(16, 16)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setBrush(QColor(100, 150, 255))
            p.drawRect(2, 2, 12, 12)
            p.end()
        return pm

    def toggle_max(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    # --- Перетаскивание ---
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag_pos = e.globalPos() - self.parent_window.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self.drag_pos is not None:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
            self.parent_window.move(e.globalPos() - self.drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self.drag_pos = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.toggle_max()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = 8

        # --- 1. Основной путь заголовка (скруглён сверху) ---
        path = QPainterPath()
        path.moveTo(0, h)
        path.lineTo(0, radius)
        path.quadTo(0, 0, radius, 0)
        path.lineTo(w - radius, 0)
        path.quadTo(w, 0, w, radius)
        path.lineTo(w, h)
        path.closeSubpath()

        # --- 2. Основной синий градиент Luna ---
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.00, QColor(0, 60, 200))
        grad.setColorAt(0.05, QColor(30, 110, 235))
        grad.setColorAt(0.20, QColor(50, 140, 250))
        grad.setColorAt(0.35, QColor(20, 90, 220))
        grad.setColorAt(0.85, QColor(0, 55, 170))
        grad.setColorAt(1.00, QColor(0, 40, 140))

        p.setPen(Qt.NoPen)
        p.fillPath(path, QBrush(grad))

        # --- 3. Верхняя светлая полоса-блик (характерна для XP) ---
        hl_rect = QPainterPath()
        hl_rect.moveTo(1, h)
        hl_rect.lineTo(1, radius)
        hl_rect.quadTo(1, 1, radius, 1)
        hl_rect.lineTo(w - radius, 1)
        hl_rect.quadTo(w - 1, 1, w - 1, radius)
        hl_rect.lineTo(w - 1, 4)
        hl_rect.lineTo(1, 4)
        hl_rect.closeSubpath()

        hl_grad = QLinearGradient(0, 0, 0, 4)
        hl_grad.setColorAt(0, QColor(255, 255, 255, 220))
        hl_grad.setColorAt(1, QColor(255, 255, 255, 60))
        p.fillPath(hl_rect, QBrush(hl_grad))

        # --- 4. Второй блик пониже (имитация "стеклянной" полосы) ---
        glass = QPainterPath()
        glass.addRoundedRect(QRectF(1, h * 0.42, w - 2, h * 0.18), 2, 2)
        glass_grad = QLinearGradient(0, h * 0.42, 0, h * 0.60)
        glass_grad.setColorAt(0, QColor(255, 255, 255, 0))
        glass_grad.setColorAt(0.5, QColor(255, 255, 255, 70))
        glass_grad.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillPath(glass, QBrush(glass_grad))

        # --- 5. Тёмная нижняя кромка (отделяет заголовок от тела) ---
        p.setPen(QPen(QColor(0, 30, 100), 1))
        p.drawLine(1, h - 1, w - 2, h - 1)

        # --- 6. Тень под текстом заголовка ---
        text_rect = self.title_label.geometry()
        # сдвигаем координаты относительно titlebar
        x = text_rect.x() + 1
        y = text_rect.y()
        p.setPen(QColor(0, 20, 70, 180))
        p.setFont(self.title_label.font())
        p.drawText(QRect(x, y, text_rect.width(), text_rect.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.title_label.text())

        # --- 7. Внешняя рамка заголовка ---
        p.setPen(QPen(QColor(0, 30, 90), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)


class XPMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(620, 420)
        self.setMinimumSize(320, 220)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Заголовок
        self.title_bar = XPTitleBar(self, "Моё окно — Windows XP Style")
        main_layout.addWidget(self.title_bar)

        # Контент
        content = QWidget()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        lbl = QLabel("Привет! Это окно в стиле Windows XP.")
        content_layout.addWidget(lbl)
        content_layout.addStretch()
        main_layout.addWidget(content, 1)

        # Нижняя панель с sizegrip
        bottom = QWidget()
        bottom.setFixedHeight(16)
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 2, 2)
        bottom_layout.addStretch()
        grip = QSizeGrip(bottom)
        grip.setFixedSize(14, 14)
        bottom_layout.addWidget(grip)
        main_layout.addWidget(bottom)

        self.setStyleSheet("""
            #central {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f9ff, stop:1 #d6e5fa);
                border: 2px solid #003399;
                border-top: none;
            }
            #content {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #e8f0fb);
                border: 1px solid #99b8dd;
                margin: 6px;
            }
            #content QLabel {
                color: #003399;
                font-family: "Trebuchet MS";
                font-size: 11pt;
                padding: 8px;
                background: transparent;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = XPMainWindow()
    w.show()
    sys.exit(app.exec_())