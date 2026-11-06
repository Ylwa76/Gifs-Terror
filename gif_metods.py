# gif_effects.py
"""
Модуль визуальных эффектов для GIF-меток.
Эффекты работают БЕССРОЧНО, пока их не снимут повторным кликом.
"""

import os
import math
import random

from PyQt5.QtWidgets import (
    QLabel, QGraphicsOpacityEffect, QGraphicsColorizeEffect
)
from PyQt5.QtGui import QMovie, QColor, QPainter, QCursor
from PyQt5.QtCore import (
    Qt, QTimer, QSize, QRect,
    QPropertyAnimation, QEasingCurve, QPoint
)
from config_loader import load_config


# ============================================================
#                     БЕЗОПАСНЫЙ ВЫЗОВ
# ============================================================
def safe_call(obj, method_name, *args):
    try:
        method = getattr(obj, method_name, None)
        if method is None:
            return False
        method(*args)
        return True
    except RuntimeError:
        return False


# ============================================================
#                 КЛИКАБЕЛЬНАЯ GIF-МЕТКА
# ============================================================
class ClickableGif(QLabel):
    def __init__(self, parent, on_click, on_right_click=None,
                 on_alt_click=None, on_alt_right_click=None,
                 on_drag_start=None, on_drag_move=None, on_drag_end=None,
                 on_grab_all=None, on_release_all=None,
                 on_middle_click=None):
        super().__init__(parent)
        self._on_click = on_click
        self._on_right_click = on_right_click
        self._on_alt_click = on_alt_click
        self._on_alt_right_click = on_alt_right_click
        self._on_drag_start = on_drag_start
        self._on_drag_move = on_drag_move
        self._on_drag_end = on_drag_end
        self._on_grab_all = on_grab_all
        self._on_release_all = on_release_all
        self._on_middle_click = on_middle_click

        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.angle = 0.0
        self.gif_path = None
        self._movie = None
        self._stop_active_effect = None
        self._main_stop = None
        self._follow_stop = None
        self._active_effect_name = None

        # состояние перетаскивания
        self._dragging = False
        self._drag_offset = None

    def setMovie(self, movie):
        self._movie = movie
        try:
            movie.frameChanged.connect(self.update)
        except Exception:
            pass
        super().setMovie(movie)

    def wheelEvent(self, event):
        mods = event.modifiers()
        delta = event.angleDelta().y()

        if delta == 0:
            delta = event.pixelDelta().y()
        if delta == 0:
            delta = event.angleDelta().x()
        if delta == 0:
            delta = event.pixelDelta().x()

        if delta == 0:
            event.ignore()
            return

        alt = bool(mods & Qt.AltModifier)

        # === Поворот: Alt + ЛКМ (схвачена) + колесо ===
        if self._dragging and alt:
            # ⬇️ на время вращения «замораживаем» перетаскивание
            self._drag_offset = None
            angle_step = 15 if delta > 0 else -15
            self.angle = (self.angle + angle_step) % 360
            self.update()
            event.accept()
            return

        # === Масштаб: схвачена ИЛИ зажат Alt ===
        if self._dragging or alt:
            step = 1.1 if delta > 0 else 0.9
            self._scale_by(step)
            event.accept()
            return

        event.ignore()

    def _scale_by(self, factor):
        try:
            start_geo = self.geometry()
        except RuntimeError:
            return

        old_w = start_geo.width()
        old_h = start_geo.height()

        center = start_geo.center()
        w = max(20, int(old_w * factor))
        h = max(20, int(old_h * factor))

        MAX_PX = 1200
        w = min(w, MAX_PX)
        h = min(h, MAX_PX)

        # 1. сначала меняем размер label
        new_geo = QRect(0, 0, w, h)
        new_geo.moveCenter(center)
        self.setFixedSize(w, h)       # ⬅️ setFixedSize вместо setGeometry
        self.move(new_geo.topLeft())

        # 2. потом говорим movie, какой у него размер
        movie = getattr(self, "_movie", None)
        if movie is not None:
            try:
                movie.setScaledSize(QSize(w, h))
            except RuntimeError:
                pass

        self.update()

        print(f"[scale] {old_w}x{old_h} → {w}x{h} (×{factor})")

    def mousePressEvent(self, event):
        alt = bool(event.modifiers() & Qt.AltModifier)

        # === Средняя кнопка: удалить гифку ===
        if event.button() == Qt.MiddleButton:
            if self._on_middle_click is not None:
                self._on_middle_click(self)
            event.accept()
            return

        # === Alt + ЛКМ: захват одной гифки ===
        if event.button() == Qt.LeftButton and alt:
            self._dragging = True
            self._drag_offset = event.pos()
            if self._on_drag_start is not None:
                self._on_drag_start(self)
            event.accept()
            return

        # === Alt + ПКМ: захват всех ===
        if event.button() == Qt.RightButton and alt:
            if self._on_grab_all is not None:
                self._on_grab_all(self, event.globalPos())
            event.accept()
            return

        # === обычный ПКМ: если что-то было захвачено — отменяем ===
        if event.button() == Qt.RightButton and not alt:
            em = self._find_effect_manager()
            if em is not None:
                em.cancel_grab_all()

        # === обычное поведение ===
        if event.button() == Qt.LeftButton and self._on_click is not None:
            self._on_click(self)
        elif event.button() == Qt.RightButton and self._on_right_click is not None:
            self._on_right_click(self)

        super().mousePressEvent(event)

    def _find_effect_manager(self):
        """Ищет EffectManager вверх по иерархии родителей."""
        p = self.parent()
        while p is not None:
            em = getattr(p, "effect_manager", None)
            if em is not None:
                return em
            p = p.parent()
        return None

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            if self._on_drag_move is not None:
                self._on_drag_move(self, event.globalPos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        alt = bool(event.modifiers() & Qt.AltModifier)

        # === Alt + ЛКМ отпустил ===
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            if self._on_drag_end is not None:
                self._on_drag_end(self)
            event.accept()
            return

        # === Alt + ПКМ отпустил: взрыв ===
        if event.button() == Qt.RightButton and alt:
            if self._on_release_all is not None:
                self._on_release_all(self, event.globalPos())
            event.accept()
            return

        # === ПКМ отпустил без Alt: если захват активен — отменяем ===
        if event.button() == Qt.RightButton and not alt:
            em = self._find_effect_manager()
            if em is not None:
                em.cancel_grab_all()

        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        if self._movie is None:
            return
        try:
            pixmap = self._movie.currentPixmap()
        except RuntimeError:
            return
        if pixmap is None or pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        painter.translate(-self.width() / 2, -self.height() / 2)

        scaled = pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


# ============================================================
#                      МЕНЕДЖЕР ЭФФЕКТОВ
# ============================================================
class EffectManager:
    ALL_EFFECTS = None

    def __init__(self, window, config=None):
        self.window = window
        self.cfg = config or {}
        self._grabbed = []
        self._grab_timer = None
        self._mass_running = False
        self._mass_follow_active = False

        effect_map = {
            "rotate":        self.effect_rotate,
            "recolor":       self.effect_recolor,
            "pulse":         self.effect_pulse,
            "move":          self.effect_move,
            "disappear":     self.effect_disappear,
            "jump":          self.effect_jump,
            "shake":         self.effect_shake,
            "fade_in_out":   self.effect_fade_in_out,
            "scale_pulse":   self.effect_scale_pulse,
            "reverse_spin":  self.effect_reverse_spin,
            "gravity":       self.effect_gravity,
            "zigzag":        self.effect_zigzag,
            "patrol":        self.effect_patrol,
        }
        self._effect_map = effect_map

        # используем уже переданный cfg, не перезагружаем
        enabled = self.cfg.get("effects", {})
        self.effects = []
        for key, func in effect_map.items():
            if enabled.get(key, True):
                self.effects.append(func)
            else:
                print(f"[effects] отключён: {key}")

        print(f"[effects] активно: {len(self.effects)}/{len(effect_map)}")

    # -------- публичное API --------
    def apply_random(self, label):
        if getattr(label, "_stop_active_effect", None) is not None:
            print(f"[effects] заменяю {label._active_effect_name} → новый")
            try:
                label._stop_active_effect()
            except Exception:
                pass
            label._stop_active_effect = None
            label._main_stop = None
            label._follow_stop = None
            label._active_effect_name = None

        if not self.effects:
            print("[effects] нет активных эффектов")
            return

        effect = random.choice(self.effects)
        path = getattr(label, 'gif_path', None) or '?'
        print(f"[effects] {effect.__name__} → {os.path.basename(path)} (бессрочно)")

        stop_func = effect(label)
        label._main_stop = stop_func
        label._active_effect_name = effect.__name__
        self._rebuild_combined_stop(label)

    def clear_effects(self, label):
        if getattr(label, "_stop_active_effect", None) is not None:
            print(f"[effects] clear {label._active_effect_name}")
            try:
                label._stop_active_effect()
            except Exception:
                pass
            label._stop_active_effect = None
            label._active_effect_name = None

    def register(self, effect_func):
        self.effects.append(effect_func)

    def _get_gif_files(self):
        getter = getattr(self.window, "get_gif_files", None)
        if callable(getter):
            return getter()
        return []

    def _rebuild_combined_stop(self, label):
        main_stop = getattr(label, "_main_stop", None)
        follow_stop = getattr(label, "_follow_stop", None)

        stops = []
        if main_stop is not None:
            stops.append(main_stop)
        if follow_stop is not None:
            stops.append(follow_stop)

        if not stops:
            label._stop_active_effect = None
            label._active_effect_name = None
            return

        def combined():
            for s in stops:
                try:
                    s()
                except Exception:
                    pass

        label._stop_active_effect = combined

        names = []
        if main_stop is not None and getattr(label, "_active_effect_name", None):
            names.append(label._active_effect_name)
        if follow_stop is not None:
            names.append("follow_mouse")
        label._active_effect_name = " + ".join(names) if names else None

    # ============================================================
    #                        ЭФФЕКТЫ
    # ============================================================
    def effect_rotate(self, label):
        speed = random.uniform(1.0, 8.0) * random.choice([-1, 1])
        timer = QTimer(label)
        state = {"alive": True}

        def tick():
            if not state["alive"]:
                return
            try:
                label.angle = (label.angle + speed) % 360
                label.update()
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(30)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")
            try:
                label.angle = 0.0
                label.update()
            except RuntimeError:
                pass

        return stop

    def effect_recolor(self, label):
        try:
            label.setGraphicsEffect(None)
        except RuntimeError:
            return None

        effect = QGraphicsColorizeEffect(label)
        effect.setStrength(1.0)
        effect.setColor(QColor(random.randint(0, 255),
                               random.randint(0, 255),
                               random.randint(0, 255)))
        label.setGraphicsEffect(effect)

        timer = QTimer(label)
        state = {"alive": True}

        def tick():
            if not state["alive"]:
                return
            try:
                color = QColor(random.randint(0, 255),
                               random.randint(0, 255),
                               random.randint(0, 255))
                anim = QPropertyAnimation(effect, b"color", label)
                anim.setDuration(500)
                anim.setStartValue(effect.color())
                anim.setEndValue(color)
                anim.start(QPropertyAnimation.DeleteWhenStopped)
                label._recolor_anim = anim
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(600)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")
            try:
                if label.graphicsEffect() is effect:
                    label.setGraphicsEffect(None)
            except RuntimeError:
                pass

        return stop

    def effect_pulse(self, label):
        try:
            start_geo = label.geometry()
        except RuntimeError:
            return None

        start_size = start_geo.size()
        center = start_geo.center()

        big = random.uniform(1.5, 2.5)
        small = random.uniform(0.4, 0.7)

        big_size = QSize(int(start_size.width() * big),
                         int(start_size.height() * big))
        small_size = QSize(max(20, int(start_size.width() * small)),
                           max(20, int(start_size.height() * small)))

        state = {"alive": True}

        def make_geo(size):
            g = QRect(0, 0, size.width(), size.height())
            g.moveCenter(center)
            return g

        def animate_to(target_size, duration, on_done=None):
            if not state["alive"]:
                return
            try:
                anim = QPropertyAnimation(label, b"geometry", label)
            except RuntimeError:
                return
            anim.setDuration(duration)
            anim.setStartValue(label.geometry())
            anim.setEndValue(make_geo(target_size))
            anim.setEasingCurve(QEasingCurve.InOutSine)
            if on_done is not None:
                anim.finished.connect(on_done)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
            label._pulse_anim = anim

        def phase2():
            animate_to(small_size, 600, phase3)

        def phase3():
            animate_to(start_size, 600, phase1)

        def phase1():
            animate_to(big_size, 600, phase2)

        phase1()

        def stop():
            state["alive"] = False
            try:
                label.setGeometry(start_geo)
            except RuntimeError:
                pass

        return stop

    def effect_move(self, label):
        timer = QTimer(label)
        state = {"alive": True}
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 12)

        def tick():
            nonlocal angle, speed
            if not state["alive"]:
                return
            try:
                if random.random() < 0.15:
                    angle += random.uniform(-1.5, 1.5)
                    speed = random.uniform(3, 12)

                dx = speed * math.cos(angle)
                dy = speed * math.sin(angle)

                x = label.x() + dx
                y = label.y() + dy

                if x < 0 or x + label.width() > self.window.width():
                    angle = math.pi - angle
                    x = max(0, min(x, self.window.width() - label.width()))
                if y < 0 or y + label.height() > self.window.height():
                    angle = -angle
                    y = max(0, min(y, self.window.height() - label.height()))

                label.move(int(x), int(y))
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(30)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")

        return stop

    def effect_disappear(self, label, duration_ms=500):
        try:
            effect = QGraphicsOpacityEffect(label)
            effect.setOpacity(1.0)
            label.setGraphicsEffect(effect)
        except RuntimeError:
            return None

        anim = QPropertyAnimation(effect, b"opacity", label)
        anim.setDuration(duration_ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)

        def on_finished():
            try:
                if label.graphicsEffect() is effect:
                    movie = getattr(label, "_movie", None)
                    if movie is not None:
                        try:
                            movie.stop()
                        except Exception:
                            pass

                    for child in label.findChildren(QTimer):
                        try:
                            child.stop()
                            child.deleteLater()
                        except Exception:
                            pass

                    self._remove_label(label)
            except RuntimeError:
                pass

        anim.finished.connect(on_finished)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        label._disappear_anim = anim

        return None

    def _remove_label(self, label):
        lst = getattr(self.window, "labels", None)
        if isinstance(lst, list) and label in lst:
            lst.remove(label)
        label.deleteLater()

    def effect_jump(self, label):
        try:
            start_pos = label.pos()
        except RuntimeError:
            return None

        height = random.randint(60, 150)
        state = {"alive": True}

        def make_anim():
            if not state["alive"]:
                return
            try:
                anim = QPropertyAnimation(label, b"pos", label)
            except RuntimeError:
                return
            anim.setDuration(700)
            anim.setStartValue(start_pos)
            anim.setKeyValueAt(0.5, start_pos - QPoint(0, height))
            anim.setEndValue(start_pos)
            anim.setEasingCurve(QEasingCurve.OutBounce)
            anim.finished.connect(make_anim)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
            label._jump_anim = anim

        make_anim()

        def stop():
            state["alive"] = False
            try:
                label.move(start_pos)
            except RuntimeError:
                pass

        return stop

    def effect_shake(self, label):
        try:
            origin = label.pos()
        except RuntimeError:
            return None

        timer = QTimer(label)
        state = {"alive": True, "t": 0}

        def tick():
            if not state["alive"]:
                return
            try:
                state["t"] += 1
                amp = max(1, 10 - state["t"] // 2) if state["t"] < 40 else 10
                dx = random.randint(-amp, amp)
                dy = random.randint(-amp, amp)
                label.move(origin.x() + dx, origin.y() + dy)
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(30)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")
            try:
                label.move(origin)
            except RuntimeError:
                pass

        return stop

    def effect_fade_in_out(self, label):
        try:
            effect = QGraphicsOpacityEffect(label)
            effect.setOpacity(1.0)
            label.setGraphicsEffect(effect)
        except RuntimeError:
            return None

        state = {"alive": True}
        cycle_ms = 700

        def start_opacity_anim():
            if not state["alive"]:
                return
            try:
                anim = QPropertyAnimation(effect, b"opacity", label)
                anim.setDuration(cycle_ms)
                anim.setStartValue(1.0)
                anim.setKeyValueAt(0.5, 0.1)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.InOutSine)
                anim.finished.connect(start_opacity_anim)
                anim.start(QPropertyAnimation.DeleteWhenStopped)
                label._fade_anim = anim
            except RuntimeError:
                pass

        start_opacity_anim()

        def stop():
            state["alive"] = False
            try:
                if label.graphicsEffect() is effect:
                    label.setGraphicsEffect(None)
            except RuntimeError:
                pass

        return stop

    def remove_gif(self, label):
        path = getattr(label, "gif_path", "?")
        print(f"[remove] удаляю {os.path.basename(path)}")

        if getattr(label, "_stop_active_effect", None) is not None:
            try:
                label._stop_active_effect()
            except Exception:
                pass
            label._stop_active_effect = None
            label._main_stop = None
            label._follow_stop = None
            label._active_effect_name = None

        if getattr(self, "_grabbed", None):
            self._grabbed = [
                item for item in self._grabbed
                if item[0] is not label
            ]

        self.effect_disappear(label)

    def effect_scale_pulse(self, label):
        try:
            start_geo = label.geometry()
            center = start_geo.center()
            base = start_geo.size()
        except RuntimeError:
            return None

        timer = QTimer(label)
        state = {"alive": True}

        def tick():
            if not state["alive"]:
                return
            try:
                k = random.uniform(0.93, 1.07)
                w = max(20, int(base.width() * k))
                h = max(20, int(base.height() * k))
                g = QRect(0, 0, w, h)
                g.moveCenter(center)
                label.setGeometry(g)
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(40)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")
            try:
                label.setGeometry(start_geo)
            except RuntimeError:
                pass

        return stop

    def effect_reverse_spin(self, label):
        try:
            start_angle = label.angle
        except RuntimeError:
            return None

        state = {"alive": True}
        direction = random.choice([-1, 1])
        speed = random.uniform(2, 8)

        timer = QTimer(label)

        def tick():
            if not state["alive"]:
                return
            try:
                label.angle = (label.angle + speed * direction) % 360
                label.update()
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(30)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")
            try:
                label.angle = start_angle
                label.update()
            except RuntimeError:
                pass

        return stop

    def effect_gravity(self, label):
        try:
            win_w = self.window.width()
            win_h = self.window.height()
        except RuntimeError:
            return None

        state = {
            "alive": True,
            "vx": random.uniform(-6, 6),
            "vy": random.uniform(-2, 2),
        }
        gravity = 0.6
        damping = 0.85
        friction = 0.995

        timer = QTimer(label)

        def tick():
            if not state["alive"]:
                return
            try:
                state["vy"] += gravity
                x = label.x() + state["vx"]
                y = label.y() + state["vy"]

                if x < 0:
                    x = 0
                    state["vx"] = -state["vx"] * damping
                elif x + label.width() > win_w:
                    x = win_w - label.width()
                    state["vx"] = -state["vx"] * damping

                if y < 0:
                    y = 0
                    state["vy"] = -state["vy"] * damping
                elif y + label.height() > win_h:
                    y = win_h - label.height()
                    state["vy"] = -state["vy"] * damping
                    state["vx"] *= friction

                    if abs(state["vy"]) < 1.5:
                        state["vy"] = random.uniform(-12, -7)
                        state["vx"] = random.uniform(-5, 5)

                label.move(int(x), int(y))
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(20)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")

        return stop

    def effect_zigzag(self, label):
        try:
            win_w = self.window.width()
            win_h = self.window.height()
        except RuntimeError:
            return None

        timer = QTimer(label)
        state = {
            "alive": True,
            "vx": random.choice([-1, 1]) * random.uniform(4, 9),
            "vy": random.choice([-1, 1]) * random.uniform(3, 7),
            "phase": 0.0,
        }
        amplitude = random.randint(5, 15)

        def tick():
            if not state["alive"]:
                return
            try:
                state["phase"] += 0.3
                vy = state["vy"] + math.sin(state["phase"]) * amplitude
                x = label.x() + state["vx"]
                y = label.y() + vy

                if x < 0:
                    x = 0
                    state["vx"] = -state["vx"]
                elif x + label.width() > win_w:
                    x = win_w - label.width()
                    state["vx"] = -state["vx"]

                if y < 0:
                    y = 0
                    state["vy"] = abs(state["vy"])
                elif y + label.height() > win_h:
                    y = win_h - label.height()
                    state["vy"] = -abs(state["vy"])

                label.move(int(x), int(y))
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(30)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")

        return stop

    def effect_patrol(self, label):
        try:
            win_w = self.window.width()
            win_h = self.window.height()
        except RuntimeError:
            return None

        timer = QTimer(label)
        state = {
            "alive": True,
            "target": None,
            "waypoints": [
                (0, 0),
                (win_w - label.width(), 0),
                (win_w - label.width(), win_h - label.height()),
                (0, win_h - label.height()),
            ],
            "idx": 0,
        }
        speed = random.uniform(3, 8)

        def tick():
            if not state["alive"]:
                return
            try:
                if state["target"] is None:
                    state["target"] = state["waypoints"][state["idx"]]

                tx, ty = state["target"]
                x, y = label.x(), label.y()

                dx = tx - x
                dy = ty - y
                dist = math.hypot(dx, dy)

                if dist < speed:
                    label.move(tx, ty)
                    state["idx"] = (state["idx"] + 1) % len(state["waypoints"])
                    state["target"] = state["waypoints"][state["idx"]]
                else:
                    label.move(int(x + dx / dist * speed),
                               int(y + dy / dist * speed))
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(20)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")

        return stop

    def effect_follow_mouse(self, label):
        speed = random.uniform(0.05, 0.15)
        timer = QTimer(label)
        state = {"alive": True}

        def tick():
            if not state["alive"]:
                return
            try:
                cursor = QCursor.pos()
                local = self.window.mapFromGlobal(cursor)

                target_x = local.x() - label.width() // 2
                target_y = local.y() - label.height() // 2

                dx = (target_x - label.x()) * speed
                dy = (target_y - label.y()) * speed

                label.move(int(label.x() + dx), int(label.y() + dy))
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(20)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")

        return stop

    # ============================================================
    #                    DRAG & DROP
    # ============================================================
    def drag_one_start(self, label):
        print(f"[drag] схватил {os.path.basename(getattr(label, 'gif_path', '?'))}")
        label.raise_()
        label.repaint()

        if getattr(label, "_stop_active_effect", None) is not None:
            try:
                label._stop_active_effect()
            except Exception:
                pass
            label._stop_active_effect = None
            label._main_stop = None
            label._follow_stop = None
            label._active_effect_name = None

    def drag_one_move(self, label, global_pos):
        offset = getattr(label, "_drag_offset", None)
        if offset is None:
            return   # ⬅️ перетаскивание «заморожено» — не двигаем
        try:
            local = self.window.mapFromGlobal(global_pos)
        except RuntimeError:
            return
        x = local.x() - offset.x()
        y = local.y() - offset.y()
        x = max(0, min(x, self.window.width() - label.width()))
        y = max(0, min(y, self.window.height() - label.height()))
        label.move(int(x), int(y))

    def drag_one_end(self, label):
        print(f"[drag] отпустил {os.path.basename(getattr(label, 'gif_path', '?'))}")

    def grab_all(self, label, global_pos):
        labels = getattr(self.window, "labels", None)
        if not isinstance(labels, list) or not labels:
            return

        print(f"[grab-all] схватил {len(labels)} гифок")

        self._grabbed = []
        for lbl in list(labels):
            try:
                lbl.raise_()
            except RuntimeError:
                pass

            if getattr(lbl, "_stop_active_effect", None) is not None:
                try:
                    lbl._stop_active_effect()
                except Exception:
                    pass
                lbl._stop_active_effect = None
                lbl._main_stop = None
                lbl._follow_stop = None
                lbl._active_effect_name = None

            start_x = lbl.x()
            start_y = lbl.y()
            self._grabbed.append((lbl, start_x, start_y))

        self._cursor_history = []
        self._last_cursor_pos = None

        self._grab_timer = QTimer(self.window)
        self._grab_timer.timeout.connect(self._tick_grab_all)
        self._grab_timer.start(16)

    def _tick_grab_all(self):
        if not getattr(self, "_grabbed", None):
            return
        try:
            cursor_global = QCursor.pos()
            local = self.window.mapFromGlobal(cursor_global)
            win_w = self.window.width()
            win_h = self.window.height()
        except RuntimeError:
            return

        self._last_cursor_pos = QPoint(local.x(), local.y())
        self._cursor_history.append((local.x(), local.y()))
        if len(self._cursor_history) > 10:
            self._cursor_history.pop(0)

        attraction = 0.15
        for item in self._grabbed:
            lbl, _, _ = item
            try:
                target_x = local.x() - lbl.width() // 2 + random.randint(-40, 40)
                target_y = local.y() - lbl.height() // 2 + random.randint(-40, 40)

                dx = (target_x - lbl.x()) * attraction
                dy = (target_y - lbl.y()) * attraction

                x = max(0, min(lbl.x() + dx, win_w - lbl.width()))
                y = max(0, min(lbl.y() + dy, win_h - lbl.height()))

                lbl.move(int(x), int(y))
            except RuntimeError:
                continue

    def release_all(self, label, global_pos):
        if getattr(self, "_grab_timer", None) is not None:
            try:
                self._grab_timer.stop()
            except Exception:
                pass
            self._grab_timer = None

        if not getattr(self, "_grabbed", None):
            return

        try:
            origin = self.window.mapFromGlobal(global_pos)
        except RuntimeError:
            origin = QPoint(self.window.width() // 2,
                            self.window.height() // 2)

        direction = self._compute_cursor_direction(origin)
        print(f"[release-all] ВЗРЫВ × {len(self._grabbed)} "
              f"от ({origin.x()},{origin.y()}), "
              f"направление=({direction.x()},{direction.y()})")

        for item in self._grabbed:
            lbl, start_x, start_y = item
            try:
                stop_func = self.effect_explode(
                    lbl,
                    origin=origin,
                    base_speed=40,
                    start_pos=(start_x, start_y),
                    direction=direction,
                )
                lbl._main_stop = stop_func
                lbl._active_effect_name = "explode"
                self._rebuild_combined_stop(lbl)
            except RuntimeError:
                continue

        self._grabbed = []
        self._cursor_history = []
        self._last_cursor_pos = None

    def _compute_cursor_direction(self, current_pos):
        history = getattr(self, "_cursor_history", None)
        if not history or len(history) < 3:
            return QPoint(0, 0)

        old_x, old_y = history[0]
        new_x, new_y = current_pos.x(), current_pos.y()

        dx = new_x - old_x
        dy = new_y - old_y
        dist = math.hypot(dx, dy)

        MIN_MOVE = 15
        if dist < MIN_MOVE:
            return QPoint(0, 0)

        return QPoint(int(dx / dist * 100), int(dy / dist * 100))

    def cancel_grab_all(self):
        if getattr(self, "_grab_timer", None) is None and not getattr(self, "_grabbed", None):
            return

        print("[grab-all] отмена захвата (Alt отпущен)")

        if getattr(self, "_grab_timer", None) is not None:
            try:
                self._grab_timer.stop()
            except Exception:
                pass
            self._grab_timer = None

        self._grabbed = []
        self._cursor_history = []
        self._last_cursor_pos = None

    def stop_all_effects(self):
        if getattr(self, "_grab_timer", None) is not None:
            try:
                self._grab_timer.stop()
            except Exception:
                pass
            self._grab_timer = None
        self._grabbed = []
        self._cursor_history = []
        self._last_cursor_pos = None

        labels = getattr(self.window, "labels", None)
        if isinstance(labels, list):
            for lbl in list(labels):
                stop_func = getattr(lbl, "_stop_active_effect", None)
                if stop_func is not None:
                    try:
                        stop_func()
                    except Exception:
                        pass
                    lbl._stop_active_effect = None
                    lbl._main_stop = None
                    lbl._follow_stop = None
                    lbl._active_effect_name = None

                movie = getattr(lbl, "_movie", None)
                if movie is not None:
                    try:
                        movie.stop()
                    except Exception:
                        pass

                try:
                    lbl.setGraphicsEffect(None)
                except RuntimeError:
                    pass

                for child in lbl.findChildren(QTimer):
                    try:
                        child.stop()
                        child.deleteLater()
                    except Exception:
                        pass

        self._mass_running = False
        self._mass_follow_active = False

        print("[effects] все таймеры остановлены")

    def effect_explode(self, label, origin=None, base_speed=40,
                       start_pos=None, direction=None):
        try:
            win_w = self.window.width()
            win_h = self.window.height()
        except RuntimeError:
            return None

        if origin is None:
            origin = QPoint(win_w // 2, win_h // 2)

        if direction is not None and (direction.x() != 0 or direction.y() != 0):
            base_angle = math.atan2(direction.y(), direction.x())
            angle = base_angle + random.uniform(-math.pi / 6, math.pi / 6)
            speed = base_speed * random.uniform(0.8, 1.3)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
        else:
            if start_pos is not None:
                sx, sy = start_pos
                cx = sx + label.width() // 2
                cy = sy + label.height() // 2
            else:
                cx = label.x() + label.width() // 2
                cy = label.y() + label.height() // 2

            dx = cx - origin.x()
            dy = cy - origin.y()
            dist = math.hypot(dx, dy)

            if dist < 5:
                angle = random.uniform(0, 2 * math.pi)
                vx = math.cos(angle) * base_speed
                vy = math.sin(angle) * base_speed
            else:
                vx = dx / dist * base_speed
                vy = dy / dist * base_speed

            k = random.uniform(0.7, 1.4)
            vx *= k
            vy *= k

        state = {"alive": True, "vx": vx, "vy": vy}
        damping = 0.92
        friction = 0.995

        timer = QTimer(label)

        def tick():
            if not state["alive"]:
                return
            try:
                x = label.x() + state["vx"]
                y = label.y() + state["vy"]

                if x < 0:
                    x = 0
                    state["vx"] = -state["vx"] * damping
                elif x + label.width() > win_w:
                    x = win_w - label.width()
                    state["vx"] = -state["vx"] * damping

                if y < 0:
                    y = 0
                    state["vy"] = -state["vy"] * damping
                elif y + label.height() > win_h:
                    y = win_h - label.height()
                    state["vy"] = -state["vy"] * damping

                state["vx"] *= friction
                state["vy"] *= friction

                if abs(state["vx"]) < 0.5 and abs(state["vy"]) < 0.5:
                    state["vx"] = random.uniform(-6, 6)
                    state["vy"] = random.uniform(-6, 6)

                label.move(int(x), int(y))
            except RuntimeError:
                state["alive"] = False
                safe_call(timer, "stop")

        timer.timeout.connect(tick)
        timer.start(16)

        def stop():
            state["alive"] = False
            safe_call(timer, "stop")

        return stop

    # ============================================================
    #                    МАССОВЫЙ ЭФФЕКТ (ПКМ)
    # ============================================================
    def effect_mass_random(self, label=None):
        if getattr(self, '_mass_running', False):
            print("[mass] уже выполняется")
            return
        self._mass_running = True

        labels = getattr(self.window, "labels", None)
        if not isinstance(labels, list) or not labels:
            print("[mass] нет гифок на экране")
            QTimer.singleShot(3000, lambda: setattr(self, '_mass_running', False))
            return

        candidates = [e for e in self.effects if e is not self.effect_mass_random]
        if not candidates:
            QTimer.singleShot(3000, lambda: setattr(self, '_mass_running', False))
            return

        print(f"[mass] случайный набор × {len(labels)} гифок (у каждой свой)")

        snapshot = list(labels)

        for lbl in snapshot:
            if getattr(lbl, "_stop_active_effect", None) is not None:
                try:
                    lbl._stop_active_effect()
                except Exception:
                    pass
                lbl._stop_active_effect = None
                lbl._main_stop = None
                lbl._follow_stop = None
                lbl._active_effect_name = None

            mass_effect = self.cfg.get("mass_effect", 3)
            chosen = random.sample(candidates, min(mass_effect, len(candidates)))
            names = ", ".join(e.__name__ for e in chosen)

            stops = []
            for eff in chosen:
                try:
                    s = eff(lbl)
                    if s is not None:
                        stops.append(s)
                except RuntimeError:
                    break

            if stops:
                def make_combined(stops_list):
                    def combined():
                        for s in stops_list:
                            try:
                                s()
                            except Exception:
                                pass
                    return combined

                lbl._main_stop = make_combined(stops)
                lbl._active_effect_name = names
                self._rebuild_combined_stop(lbl)

        QTimer.singleShot(3000, lambda: setattr(self, '_mass_running', False))

    def clear_all_effects(self):
        labels = getattr(self.window, "labels", None)
        if not isinstance(labels, list):
            return
        for lbl in list(labels):
            self.clear_effects(lbl)


# ============================================================
#                    ПОДКЛЮЧЕНИЕ К ОКНУ
# ============================================================
def attach_effects(window, config=None):
    manager = EffectManager(window, config=config)
    window.effect_manager = manager

    def make_gif_label(on_click=None, on_right_click=None,
                       on_alt_click=None, on_alt_right_click=None,
                       on_middle_click=None):
        cb_left = on_click if on_click is not None else manager.apply_random
        cb_right = on_right_click if on_right_click is not None else manager.effect_mass_random
        cb_alt = on_alt_click if on_alt_click is not None else None
        cb_alt_right = on_alt_right_click if on_alt_right_click is not None else None
        cb_middle = on_middle_click if on_middle_click is not None else manager.remove_gif

        return ClickableGif(
            window,
            cb_left, cb_right, cb_alt, cb_alt_right,
            on_drag_start=manager.drag_one_start,
            on_drag_move=manager.drag_one_move,
            on_drag_end=manager.drag_one_end,
            on_grab_all=manager.grab_all,
            on_release_all=manager.release_all,
            on_middle_click=cb_middle,
        )

    window.make_gif_label = make_gif_label
    return manager