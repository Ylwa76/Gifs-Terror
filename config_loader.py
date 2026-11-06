# config_loader.py
import os
import json

# config_loader.py
import json
import os


DEFAULT_CONFIG = {
    "gifs_min": 30,
    "gifs_max": 85,
    "music_enabled": True,
    "music_volume": 70,
    "effects": {
        "rotate": True,
        "recolor": True,
        "pulse": True,
        "move": True,
        "disappear": True,
        "jump": True,
        "shake": True,
        "fade_in_out": True,
        "scale_pulse": True,
        "reverse_spin": True,
        "gravity":True,
        "zigzag": True       ,
        "patrol":True
    },
}


def load_config(path="config.json"):
    """
    Загружает config.json. Отсутствующие ключи берёт из DEFAULT_CONFIG.
    """
    if not os.path.isfile(path):
        print(f"[config] {path} не найден — использую дефолт")
        return DEFAULT_CONFIG.copy()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[config] ошибка чтения {path}: {e} — использую дефолт")
        return DEFAULT_CONFIG.copy()

    # мержим с дефолтом, чтобы не падать на отсутствующих ключах
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)

    # секцию effects мержим отдельно
    effects = DEFAULT_CONFIG["effects"].copy()
    effects.update(data.get("effects", {}))
    cfg["effects"] = effects

    print(f"[config] загружено: gifs={cfg['gifs_min']}..{cfg['gifs_max']}, "
          f"music={'on' if cfg['music_enabled'] else 'off'} ({cfg['music_volume']}%), "
          f"effects on: {sum(1 for v in effects.values() if v)}/{len(effects)}")

    return cfg

    # санити-чек
    try:
        cfg["gifs_min"] = max(1, int(cfg["gifs_min"]))
        cfg["gifs_max"] = max(cfg["gifs_min"], int(cfg["gifs_max"]))
    except (TypeError, ValueError):
        print("[config] gifs_min/gifs_max должны быть числами, ставлю дефолт")
        cfg["gifs_min"] = DEFAULT_CONFIG["gifs_min"]
        cfg["gifs_max"] = DEFAULT_CONFIG["gifs_max"]

    try:
        cfg["music_volume"] = max(0, min(100, int(cfg["music_volume"])))
    except (TypeError, ValueError):
        cfg["music_volume"] = DEFAULT_CONFIG["music_volume"]

    cfg["music_enabled"] = bool(cfg["music_enabled"])
    cfg["music_path"] = str(cfg["music_path"])

    print(f"[config] загружено: gifs={cfg['gifs_min']}..{cfg['gifs_max']}, "
          f"music={'on' if cfg['music_enabled'] else 'off'} "
          f"({cfg['music_volume']}%)")
    return cfg