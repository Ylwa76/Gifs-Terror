import sys
import os
import random
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QSizeGrip)
from PyQt5.QtGui import QMovie,QIcon
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl,QEvent
from gif_cache import load_gif_cache, get_size_cached

from xp_window import XPTitleBar
import math

from gif_metods import attach_effects, ClickableGif
from config_loader import load_config
import ctypes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# эталонный размер окна — при нём гифки имеют "нормальный" размер
REF_WIN_W = 800
REF_WIN_H = 600

# диапазон случайного разброса (как было)
GIF_SCALE_MIN = 0.4
GIF_SCALE_MAX = 1

# ограничения итогового размера (чтобы не улететь в космос)
GIF_MIN_PX = 30
GIF_MAX_PX = 600
icon_path = os.path.join(SCRIPT_DIR, "icon.ico")
class GifContent(QWidget):
    """
    Контейнер с гифками. Вставляется внутрь XP-окна (под заголовок).
    Вся ваша прежняя логика гифок и музыки — здесь.
    """

    def __init__(self, gif_folder_path):
        super().__init__()
        self.gif_folder_path = gif_folder_path
        self.movies = []
        self.labels = []
        self._initialized = False
        
        self.cfg = load_config("config.json")
        attach_effects(self, config=self.cfg)

        # ⬇️ КЭШ РАЗМЕРОВ
        print("[cache] загружаю кэш размеров...")
        self.size_cache = load_gif_cache()
        self.sizes = get_size_cached(self.gif_folder_path, self.size_cache)
        print(f"[cache] размеров в кэше: {len(self.sizes)}")

        if self.cfg["music_enabled"]:
            self._init_music()
        else:
            print("[music] отключена в config.json")
            self.player = None

        self.setStyleSheet("background-color: #ffffff;")
        QTimer.singleShot(100, self.spawn_gifs)

        QApplication.instance().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        # ловим отпускание Alt где угодно
        if event.type() == QEvent.KeyRelease and event.key() == Qt.Key_Alt:
            em = getattr(self, "effect_manager", None)
            if em is not None:
                em.cancel_grab_all()
        return super().eventFilter(obj, event)


    def get_gif_files(self):
        if not os.path.isdir(self.gif_folder_path):
            print(f"Папка не найдена: {self.gif_folder_path}")
            return []
        return [
            os.path.join(self.gif_folder_path, f)
            for f in os.listdir(self.gif_folder_path)
            if f.lower().endswith('.gif')
        ]

    def clear_gifs(self):
        for label in self.labels:
            label.deleteLater()
        self.labels.clear()
        self.movies.clear()

    def spawn_gifs(self):

        em = getattr(self, "effect_manager", None)
        if em is not None:
            em.stop_all_effects()

        # сбрасываем флаг массового follow
        if em is not None:
            em._mass_follow_active = False

        self.clear_gifs()

        gif_files = self.get_gif_files()
        print(f"Найдено GIF: {len(gif_files)}")


        if not gif_files:
            lbl = QLabel("GIF-файлы не найдены", self)
            lbl.setStyleSheet("color: red; font-size: 20px;")
            lbl.move(20, 20)
            lbl.show()
            self.labels.append(lbl)
            self._initialized = True
            return
        
        lo = self.cfg["gifs_min"]
        hi = self.cfg["gifs_max"]
        if lo > hi:
            lo, hi = hi, lo  # меняем местами, чтобы не было ошибки
        count = min(random.randint(lo, hi), len(gif_files))

        chosen = random.sample(gif_files, count)

        w, h = self.width(), self.height()

        for path in chosen:
            self._add_gif(path, w, h)

        self._initialized = True

    def _add_gif(self, gif_path, win_w, win_h):
        # 1. Размер из кэша
        base_size = self.sizes.get(gif_path, (100, 100))
        size_w, size_h = base_size

        # 2. Читаем настройки масштаба из конфига
        gs = self.cfg.get("gif_scale", {})
        ref_w     = gs.get("ref_w", 800)
        ref_h     = gs.get("ref_h", 600)
        scale_min = gs.get("min", 0.4)
        scale_max = gs.get("max", 1.2)
        px_min    = gs.get("px_min", 30)
        px_max    = gs.get("px_max", 600)

        # 3. Коэффициент масштаба окна (sqrt от площади)
        area_now = max(1, win_w * win_h)
        area_ref = ref_w * ref_h
        window_scale = math.sqrt(area_now / area_ref)

        # 4. Случайный разброс
        rand_scale = random.uniform(scale_min, scale_max)

        # 5. Итоговый масштаб
        scale = window_scale * rand_scale

        new_w = int(size_w * scale)
        new_h = int(size_h * scale)

        # 6. Ограничения размера
        new_w = max(px_min, min(new_w, px_max))
        new_h = max(px_min, min(new_h, px_max))

        # 7. Создаём movie
        movie = QMovie(gif_path)
        if not movie.isValid():
            print(f"Невалидный GIF: {gif_path}")
            return
        movie.setScaledSize(QSize(new_w, new_h))
        movie.setSpeed(self.cfg.get("gif_speed", 100))
        movie.start()

        # 8. Создаём метку
        label = self.make_gif_label()
        label.setMovie(movie)
        label.setAttribute(Qt.WA_TranslucentBackground)
        label.setFixedSize(new_w, new_h)
        label.gif_path = gif_path
        label.angle = 0.0

        # 9. Случайная позиция
        max_x = max(0, win_w - new_w)
        max_y = max(0, win_h - new_h)
        label.move(random.randint(0, max_x), random.randint(0, max_y))
        label.show()

        # 10. Регистрируем
        self.movies.append(movie)
        self.labels.append(label)


    def _on_gif_clicked(self, gif_label):
        """Что делать при клике на гифку — придумайте сами."""
        print(f"[click] Кликнули на: {getattr(gif_label, 'gif_path', '?')}")
        # Например: перемешать все гифки
        # self.spawn_gifs()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initialized:
            return
        if event.oldSize().width() < 0:
            return
        QTimer.singleShot(150, self.spawn_gifs)

    def _init_music(self):
        """Выбирает случайный трек из папки и запускает с случайной позиции."""
        self.player = None
        self.music_path = None
        self.tracks = []          # ⬅️ список всех треков

        music_dir = os.path.join( 'music')
        print(f"[music] ищу треки в: {music_dir}")

        if not os.path.isdir(music_dir):
            print(f"[music] папка не найдена: {music_dir}")
            return

        exts = ('.mp3', '.ogg', '.wav', '.flac', '.m4a')
        self.tracks = [
            os.path.join(music_dir, f)
            for f in os.listdir(music_dir)
            if f.lower().endswith(exts)
        ]

        if not self.tracks:
            print(f"[music] в папке нет музыкальных файлов")
            return

        self.music_path = random.choice(self.tracks)
        print(f"[music] выбран трек: {os.path.basename(self.music_path)}")

        self.player = QMediaPlayer()
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(self.music_path)))
        self.player.setVolume(self.cfg["music_volume"])
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.mediaStatusChanged.connect(self._loop_on_end)

    def next_music(self):
        """Принудительно включает следующий случайный трек."""
        if not getattr(self, "tracks", None):
            print("[music] нет треков для переключения")
            return

        if len(self.tracks) > 1:
            candidates = [t for t in self.tracks if t != self.music_path]
            next_track = random.choice(candidates)
        else:
            next_track = self.tracks[0]

        self.music_path = next_track
        print(f"[music] ручное переключение на: {os.path.basename(next_track)}")
        
        if self.player is not None:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(next_track)))
            # play() вызовется автоматически в _on_media_status

    def _on_media_status(self, status):
        if status == QMediaPlayer.LoadedMedia and self.player is not None:
            duration = self.player.duration()
            if duration > 0:
                start_pos = random.randint(0, max(0, duration - 5000))
                self.player.setPosition(start_pos)
                print(f"[music] старт с {start_pos / 1000:.1f} сек "
                    f"из {duration / 1000:.1f} сек "
                    f"({os.path.basename(self.music_path)})")
            self.player.play()

    def _loop_on_end(self, status):
        """Когда трек закончился — включаем следующий случайный."""
        if status != QMediaPlayer.EndOfMedia:
            return

        if not self.tracks:
            print("[music] список треков пуст, повторяю текущий")
            self.player.setPosition(0)
            self.player.play()
            return

        # выбираем новый трек, не тот же самый, если возможно
        if len(self.tracks) > 1:
            candidates = [t for t in self.tracks if t != self.music_path]
            next_track = random.choice(candidates)
        else:
            next_track = self.tracks[0]

        self.music_path = next_track
        print(f"[music] следующий трек: {os.path.basename(next_track)}")

        # загружаем и играем
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(next_track)))
        # старт произойдёт через _on_media_status (LoadedMedia)

    def apply_config(self, new_cfg):
        """Применяет новые настройки на лету."""
        self.cfg = new_cfg
        print("[gif] применяю настройки:", new_cfg)

        # обновляем эффекты
        em = getattr(self, "effect_manager", None)
        if em is not None:
            # пересоздать список эффектов по новому конфигу
            # проще всего — пересоздать менеджер заново
            
            attach_effects(self, config=new_cfg)

        # пересоздать гифки
        self.spawn_gifs()

        # музыка
        if new_cfg.get("music_enabled", True):
            if self.player is None:
                self._init_music()
            else:
                self.player.setVolume(new_cfg.get("music_volume", 70))
        else:
            if self.player is not None:
                self.player.stop()
                self.player = None


class GifChaosWindow(QWidget):
    """
    Внешнее XP-окно: рисует заголовок XPTitleBar + рамку,
    внутри — контейнер GifContent.
    """

    def __init__(self, gif_folder_path):
        super().__init__()

        # Убираем системную рамку
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setWindowTitle("GIFS_TERROR")
        self.resize(550, 550)
        
        # === Основной layout ===
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Заголовок XP
        self.title_bar = XPTitleBar(self, "GIFS_TERROR")
        main_layout.addWidget(self.title_bar)
        self.setWindowIcon(QIcon(icon_path))
        # Контент с гифками
        self.content = GifContent(gif_folder_path)
        main_layout.addWidget(self.content, 1)

        # Нижняя панель с SizeGrip для ресайза
        bottom = QWidget()
        bottom.setFixedHeight(14)
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 2, 2)
        bottom_layout.addStretch()
        grip = QSizeGrip(bottom)
        grip.setFixedSize(12, 12)
        bottom_layout.addWidget(grip)
        main_layout.addWidget(bottom)
        
        # Немного XP-рамки вокруг тела окна
        self.setStyleSheet("""
            GifChaosWindow {
                background: #f0f5ff;
                border: 2px solid #003399;
                border-top: none;
            }
        """)

    def keyPressEvent(self, event):
        # Прокидываем пробел в контент
        if event.key() == Qt.Key_Space:
            self.content.spawn_gifs()
        else:
            super().keyPressEvent(event)


def resource_path(relative_path):
    """Возвращает путь к ресурсу, работает и в .py, и в .exe"""
    try:
        base_path = sys._MEIPASS  # папка, куда PyInstaller распаковывает файлы
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def main_gif():
    if sys.platform == "win32":
        myappid = "com.pcworkshop.gifterror.1.0"  # любая уникальная строка
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")


    icon_file = resource_path("icon.ico")
    if os.path.exists(icon_file):
        app.setWindowIcon(QIcon(icon_file))
        print(f"[icon] Загружена иконка: {icon_file}")
    else:
        print(f"[icon] Файл не найден: {icon_file}")

    gif_folder = os.path.join('gifs')
    print(f"Папка с гифками: {gif_folder}")
    print(f"Существует: {os.path.isdir(gif_folder)}")
    
    window = GifChaosWindow(gif_folder)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main_gif()