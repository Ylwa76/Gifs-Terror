# gif_cache.py
import os
import json
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import QSize


CACHE_FILE = "gifs_cache.json"


def _get_size_from_movie(path):
    """Открывает гифку, стартует, возвращает (w, h). Закрывает movie."""
    movie = QMovie(path)
    if not movie.isValid():
        return None
    movie.start()
    movie.jumpToFrame(0)
    size = movie.currentPixmap().size()
    if not size.isValid() or size.width() == 0:
        size = movie.frameRect().size()
    if size.width() == 0:
        size = QSize(100, 100)
    movie.stop()
    movie.deleteLater()
    return [size.width(), size.height()]


def load_gif_cache():
    """Читает кэш размеров из JSON. Если файла нет — возвращает {}."""
    if not os.path.isfile(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as e:
        print(f"[cache] ошибка чтения кэша: {e}")
    return {}


def save_gif_cache(cache):
    """Сохраняет кэш на диск."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[cache] ошибка записи кэша: {e}")


def get_size_cached(gif_folder, cache):
    """
    Возвращает dict: {полный_путь: (w, h)}.
    Кэш обновляется по ходу: новые гифки читаются, удалённые выкидываются.
    """
    if not os.path.isdir(gif_folder):
        return {}

    files = [
        f for f in os.listdir(gif_folder)
        if f.lower().endswith(".gif")
    ]

    result = {}
    cache_changed = False

    # 1. Убираем из кэша записи, которых больше нет в папке
    for key in list(cache.keys()):
        if key not in files:
            del cache[key]
            cache_changed = True

    # 2. Проходим по файлам
    for i, fname in enumerate(files, 1):
        full = os.path.join(gif_folder, fname)

        if fname in cache:
            w, h = cache[fname]
            result[full] = (w, h)
        else:
            # читаем размер из QMovie — только для новых
            size = _get_size_from_movie(full)
            if size is None:
                continue
            cache[fname] = size
            result[full] = (size[0], size[1])
            cache_changed = True

            # прогресс в консоли каждые 50 новых
            if i % 50 == 0:
                print(f"[cache] обработано {i}/{len(files)}")

    if cache_changed:
        save_gif_cache(cache)

    return result