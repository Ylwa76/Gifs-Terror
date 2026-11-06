# settings_window.py
import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QSlider, QSpinBox, QPushButton,
    QGroupBox, QScrollArea, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal,QTimer
import os

class SettingsWindow(QWidget):
    """Окно настроек, читает и сохраняет config.json."""
    settings_changed = pyqtSignal(dict)
    next_music_requested = pyqtSignal() # ⬅️ Новый сигнал

    def __init__(self, config_path="config.json", parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.setWindowTitle("Настройки")
        self.setFixedSize(500, 600)

        self.cfg = self._load_config()
        self._build_ui()
        self._load_values()

    def _load_config(self):
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        # --- Гифки ---
        gif_group = QGroupBox("Гифки")
        gif_layout = QVBoxLayout(gif_group)

        self.gifs_min = QSpinBox()
        self.gifs_min.setRange(1, 500)
        self.gifs_max = QSpinBox()
        self.gifs_max.setRange(1, 500)
                # Минимум не может быть больше максимума
        self.gifs_min.valueChanged.connect(lambda v: self.gifs_max.setMinimum(v))
        # Максимум не может быть меньше минимума
        self.gifs_max.valueChanged.connect(lambda v: self.gifs_min.setMaximum(v))

                # --- Статус сохранения ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        main_layout.addWidget(self.status_label)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Мин. гифок:"))
        row1.addWidget(self.gifs_min)
        row1.addWidget(QLabel("Макс. гифок:"))
        row1.addWidget(self.gifs_max)
        gif_layout.addLayout(row1)

        self.gif_speed = QSlider(Qt.Horizontal)
        self.gif_speed.setRange(10, 200)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Скорость гифок:"))
        row2.addWidget(self.gif_speed)
        gif_layout.addLayout(row2)

        layout.addWidget(gif_group)

        # --- Музыка ---
        music_group = QGroupBox("Музыка")
        music_layout = QVBoxLayout(music_group)

        self.music_enabled = QCheckBox("Включить музыку")
        music_layout.addWidget(self.music_enabled)

        self.music_volume = QSlider(Qt.Horizontal)
        self.music_volume.setRange(0, 100)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Громкость:"))
        row3.addWidget(self.music_volume)
        music_layout.addLayout(row3)

        layout.addWidget(music_group)

        # --- Эффекты ---
        effects_group = QGroupBox("Эффекты")
        effects_layout = QVBoxLayout(effects_group)

        self.effect_checkboxes = {}
        effect_keys = [
            "rotate", "recolor", "pulse", "move", "disappear",
            "jump", "shake", "fade_in_out", "scale_pulse",
            "reverse_spin", "gravity", "zigzag", "patrol"
        ]
        for key in effect_keys:
            cb = QCheckBox(key)
            self.effect_checkboxes[key] = cb
            effects_layout.addWidget(cb)

        layout.addWidget(effects_group)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
        help_btn = QPushButton("Пояснялка (прочитать)")
        help_btn.clicked.connect(self._open_help)
        layout.addWidget(help_btn)
        self.next_music_btn = QPushButton("Следующий трек")
        self.next_music_btn.clicked.connect(self._skip_music)
        music_layout.addWidget(self.next_music_btn)
        

    def _load_values(self):
        cfg = self.cfg
        self.gifs_min.setValue(cfg.get("gifs_min", 50))
        self.gifs_max.setValue(cfg.get("gifs_max", 100))
        self.gif_speed.setValue(cfg.get("gif_speed", 100))
        self.music_enabled.setChecked(cfg.get("music_enabled", True))
        self.music_volume.setValue(cfg.get("music_volume", 20))

        effects = cfg.get("effects", {})
        for key, cb in self.effect_checkboxes.items():
            cb.setChecked(effects.get(key, True))

    def _save(self):
        cfg = self.cfg
        lo = self.gifs_min.value()
        hi = self.gifs_max.value()
        if lo > hi:
            lo, hi = hi, lo  # меняем местами

        cfg["gifs_min"] = lo
        cfg["gifs_max"] = hi
        cfg["gif_speed"] = self.gif_speed.value()
        cfg["music_enabled"] = self.music_enabled.isChecked()
        cfg["music_volume"] = self.music_volume.value()
        cfg["effects"] = {
            key: cb.isChecked()
            for key, cb in self.effect_checkboxes.items()
        }

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            
            # Отправляем сигнал главному окну
            self.settings_changed.emit(cfg)
            
            # Зелёная надпись, исчезает через 2 сек
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.status_label.setText("✔ Настройки сохранены")
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))
            
            # УБРАН self.close() — окно остаётся открытым
        except Exception as e:
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.status_label.setText(f"Ошибка: {e}")

    def _skip_music(self):
        self.next_music_requested.emit()

    def _open_help(self):
        """Открывает файл Пояснялка(прочитать) системной программой."""
        # Ищем файл в той же папке, откуда запущена программа
        help_file = os.path.abspath("Пояснялка(прочитать)")
        
        if not os.path.exists(help_file):
            # Если расширение .txt скрыто системой, попробуем найти с ним
            help_file_txt = help_file + ".txt"
            if os.path.exists(help_file_txt):
                help_file = help_file_txt
            else:
                QMessageBox.warning(self, "Файл не найден", 
                                    f"Не удалось найти файл:\n{help_file}")
                return

        try:
            os.startfile(help_file)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")