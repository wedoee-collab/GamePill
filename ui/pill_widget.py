import math
import ctypes

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QApplication, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QTimer, QVariantAnimation, QEasingCurve, QPoint, QRectF, QRegion
from PyQt6.QtGui import (
    QPainter, QColor, QPainterPath, QPen, QFont, QLinearGradient, QBrush, QPolygon,
)

from ui.expanded_widget import ExpandedContent
from core.config import Config
from core.themes import GameTheme, THEMES

PLATFORM_TWITCH  = "twitch"
PLATFORM_YOUTUBE = "youtube"
PLATFORM_NONE    = "none"


class PlatformIcon(QWidget):
    """Twitch Glitch logo ou bouton YouTube — aucun fichier image."""

    def __init__(self, platform: str = PLATFORM_NONE):
        super().__init__()
        self._platform = platform
        self.setFixedSize(18, 14)
        self.setStyleSheet("background: transparent;")
        self.setVisible(platform != PLATFORM_NONE)

    def set_platform(self, platform: str):
        self._platform = platform
        self.setVisible(platform != PLATFORM_NONE)
        self.update()

    @staticmethod
    def _rr(x, y, w, h, r) -> QPainterPath:
        p = QPainterPath()
        p.addRoundedRect(QRectF(x, y, w, h), r, r)
        return p

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        W, H = float(self.width()), float(self.height())

        if self._platform == PLATFORM_TWITCH:
            sx, sy = W / 20.0, H / 14.0
            body = QPainterPath()
            body.moveTo(2*sx, 0);   body.lineTo(18*sx, 0)
            body.lineTo(W, 2*sy);   body.lineTo(W, 10*sy)
            body.lineTo(16*sx, 10*sy); body.lineTo(16*sx, H)
            body.lineTo(13*sx, 10*sy); body.lineTo(2*sx, 10*sy)
            body.lineTo(0, 8*sy);   body.lineTo(0, 2*sy)
            body.closeSubpath()
            painter.fillPath(body, QColor("#9146FF"))
            bw, bh = 2.5*sx, 4*sy
            painter.fillPath(self._rr(4.5*sx,  2.5*sy, bw, bh, 1.0), QColor("white"))
            painter.fillPath(self._rr(10.5*sx, 2.5*sy, bw, bh, 1.0), QColor("white"))

        elif self._platform == PLATFORM_YOUTUBE:
            painter.fillPath(self._rr(0, H*0.1, W, H*0.8, 2.5), QColor("#FF0000"))
            tri = QPainterPath()
            tri.moveTo(W*0.34, H*0.22); tri.lineTo(W*0.34, H*0.78)
            tri.lineTo(W*0.76, H*0.50); tri.closeSubpath()
            painter.fillPath(tri, QColor("white"))


# ── Dimensions ────────────────────────────────────────────────────────────────
W_COL = 340
H_COL = 44
W_EXP = 320
H_EXP = 310
TOP_MARGIN = 12
RADIUS = 22          # vrai pill (H_COL / 2 arrondi)
ANIM_MS = 280
AUTO_COLLAPSE_MS = 8_000
RED_LIVE = "#ff3b30"


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _sf(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    return QFont("Segoe UI", size, int(weight))


def _luminance(hex_color: str) -> float:
    r, g, b = (_c / 255 for _c in _hex_rgb(hex_color))
    def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _safe_color(primary: str) -> str:
    return primary if _luminance(primary) > 0.05 else "#ffffff"


class _DotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(7, 7)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)

    def set_opacity(self, v: float):
        self._effect.setOpacity(v)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(RED_LIVE))
        p.drawEllipse(0, 0, 7, 7)


class PillWidget(QWidget):
    def __init__(self, theme: GameTheme = None):
        super().__init__()
        self._theme = theme or THEMES["default"]
        self._config = Config()
        self._expanded = False
        self._drag_origin: QPoint | None = None
        self._pulse_phase = 0.0
        self._pulse_alpha = 1.0
        self._alert_phase = 0.0
        self._alert_active = False
        self._alt_held = False
        self._first_show = True

        self._init_window()
        self._build_ui()
        self._setup_animations()
        self._setup_auto_collapse()
        self._start_pulse()
        self._start_alt_watcher()
        self._restore_position()

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.resize(W_COL, H_COL)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barre compacte ────────────────────────────────────────────
        bar = QWidget()
        bar.setFixedHeight(H_COL)
        bar.setStyleSheet("background: transparent;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 0, 16, 0)
        bl.setSpacing(8)
        bl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Dot + LIVE
        self._dot = _DotWidget()

        self._live_lbl = QLabel("LIVE")
        self._live_lbl.setFont(_sf(8, QFont.Weight.Bold))
        self._live_lbl.setStyleSheet(
            f"color: {RED_LIVE}; background: transparent; letter-spacing: 2px;"
        )

        # Séparateur 1 (avant plateforme) — caché si pas connecté
        self._sep1 = self._vsep()
        self._sep1.setVisible(False)

        # Plateforme + viewers
        self._platform_icon = PlatformIcon(PLATFORM_NONE)

        self._viewers_lbl = QLabel("--")
        self._viewers_lbl.setFont(_sf(11, QFont.Weight.DemiBold))
        self._viewers_lbl.setStyleSheet("color: rgba(255,255,255,210); background: transparent;")
        self._viewers_lbl.setVisible(False)

        # Séparateur 2 (avant jeu)
        self._sep2 = self._vsep()

        # Jeu + KDA
        self._game_lbl = QLabel()
        self._game_lbl.setFont(_sf(11, QFont.Weight.Bold))
        self._game_lbl.setStyleSheet("color: rgba(255,255,255,120); background: transparent;")

        self._kda_lbl = QLabel()
        self._kda_lbl.setFont(_sf(10))
        self._kda_lbl.setStyleSheet("color: rgba(255,255,255,160); background: transparent;")

        bl.addStretch()
        bl.addWidget(self._dot)
        bl.addSpacing(2)
        bl.addWidget(self._live_lbl)
        bl.addWidget(self._sep1)
        bl.addWidget(self._platform_icon)
        bl.addSpacing(2)
        bl.addWidget(self._viewers_lbl)
        bl.addWidget(self._sep2)
        bl.addWidget(self._game_lbl)
        bl.addWidget(self._kda_lbl)
        bl.addStretch()

        # ── Panneau étendu ────────────────────────────────────────────
        self._exp = ExpandedContent(self._theme, {}, [])
        self._exp.setVisible(False)
        self._exp.setStyleSheet("background: transparent;")
        self._opacity_fx = QGraphicsOpacityEffect()
        self._opacity_fx.setOpacity(0.0)
        self._exp.setGraphicsEffect(self._opacity_fx)

        root.addWidget(bar)
        root.addWidget(self._exp)

        self._refresh_bar_text()

    def _vsep(self) -> QFrame:
        s = QFrame()
        s.setFrameShape(QFrame.Shape.VLine)
        s.setFixedSize(1, 12)
        s.setStyleSheet("background-color: rgba(255,255,255,35); border: none;")
        return s

    def _refresh_bar_text(self):
        self._game_lbl.setText("En attente…")
        self._game_lbl.setStyleSheet("color: rgba(255,255,255,80); background: transparent;")
        self._kda_lbl.setText("")

    # ── Animations ────────────────────────────────────────────────────

    def _setup_animations(self):
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_tick)

        self._reveal_timer = QTimer(self)
        self._reveal_timer.setSingleShot(True)
        self._reveal_timer.timeout.connect(self._reveal_expanded)

        self._fade_anim = QVariantAnimation(self)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setDuration(160)
        self._fade_anim.valueChanged.connect(lambda v: self._opacity_fx.setOpacity(v))

        self._entrance_anim = QVariantAnimation(self)
        self._entrance_anim.setDuration(600)
        self._entrance_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._entrance_anim.valueChanged.connect(lambda y: self.move(self.x(), int(y)))

        self._alert_timer = QTimer(self)
        self._alert_timer.timeout.connect(self._tick_alert)

    def _setup_auto_collapse(self):
        self._ac_timer = QTimer(self)
        self._ac_timer.setSingleShot(True)
        self._ac_timer.timeout.connect(lambda: self._expanded and self._toggle())

    def _toggle(self):
        if self._anim.state() == QVariantAnimation.State.Running:
            return
        self._ac_timer.stop()
        if not self._expanded:
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._reveal_timer.start(180)
            self._ac_timer.start(AUTO_COLLAPSE_MS)
        else:
            self._opacity_fx.setOpacity(0.0)
            self._exp.setVisible(False)
            self._anim.setStartValue(1.0)
            self._anim.setEndValue(0.0)
        self._expanded = not self._expanded
        self._anim.start()

    def _on_anim_tick(self, p: float):
        self.resize(int(W_COL + (W_EXP - W_COL) * p), int(H_COL + (H_EXP - H_COL) * p))
        self._apply_mask()

    def _apply_mask(self):
        """Masque pixel-perfect pour supprimer les artefacts de coins."""
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), RADIUS, RADIUS)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _reveal_expanded(self):
        self._exp.setVisible(True)
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_mask()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_mask()
        if self._first_show:
            self._first_show = False
            ty = self.y()
            self.move(self.x(), -H_COL - 20)
            self._entrance_anim.setStartValue(float(-H_COL - 20))
            self._entrance_anim.setEndValue(float(ty))
            QTimer.singleShot(80, self._entrance_anim.start)

    # ── Alert ─────────────────────────────────────────────────────────

    def trigger_alert(self):
        self._alert_phase = 0.0
        self._alert_active = True
        if not self._alert_timer.isActive():
            self._alert_timer.start(20)

    def _tick_alert(self):
        self._alert_phase += 0.10
        if self._alert_phase >= 6 * math.pi:
            self._alert_timer.stop()
            self._alert_active = False
        self.update()

    # ── Alt key watcher ───────────────────────────────────────────────

    def _start_alt_watcher(self):
        t = QTimer(self)
        t.timeout.connect(self._check_alt)
        t.start(16)

    def _check_alt(self):
        try:
            held = bool(ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000)
        except Exception:
            held = False
        if held != self._alt_held:
            self._alt_held = held
            self.update()

    # ── Pulse ─────────────────────────────────────────────────────────

    def _start_pulse(self):
        t = QTimer(self)
        t.timeout.connect(self._tick_pulse)
        t.start(30)

    def _tick_pulse(self):
        self._pulse_phase = (self._pulse_phase + 0.1257) % (2 * math.pi)
        self._pulse_alpha = 0.3 + 0.7 * (math.sin(self._pulse_phase) * 0.5 + 0.5)
        self._dot.set_opacity(self._pulse_alpha)

    # ── Position ──────────────────────────────────────────────────────

    def _restore_position(self):
        saved = self._config.get("position")
        if saved and "screen" in saved:
            screens = QApplication.screens()
            idx = min(saved["screen"], len(screens) - 1)
            sg = screens[idx].geometry()
            self.move(sg.x() + saved.get("lx", (sg.width() - W_COL) // 2),
                      sg.y() + saved.get("ly", TOP_MARGIN))
        elif saved and "x" in saved:
            self.move(saved["x"], saved["y"])
        else:
            sg = QApplication.primaryScreen().geometry()
            self.move(sg.x() + (sg.width() - W_COL) // 2, sg.y() + TOP_MARGIN)

    def _save_position(self):
        pos = self.pos()
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        screens = QApplication.screens()
        idx = screens.index(screen) if screen in screens else 0
        sg = screen.geometry()
        self._config.set("position", {
            "screen": idx,
            "lx": pos.x() - sg.x(),
            "ly": pos.y() - sg.y(),
        })

    # ── Platform ──────────────────────────────────────────────────────

    def set_platform(self, platform: str):
        connected = platform != PLATFORM_NONE
        self._platform_icon.set_platform(platform)
        self._sep1.setVisible(connected)
        self._viewers_lbl.setVisible(connected)

    # ── Live data ─────────────────────────────────────────────────────

    def update_live_data(self, data):
        from services.twitch_service import TwitchData
        if not isinstance(data, TwitchData):
            return
        self._viewers_lbl.setText(data.viewers_fmt() if data.is_live else "Offline")
        self._exp.update_stream_data(
            viewers    = data.viewers_fmt(),
            duration   = data.uptime_fmt(),
            last_event = data.last_follower,
            is_live    = data.is_live,
        )

    def reset_live_data(self):
        self._viewers_lbl.setText("--")
        self._exp.update_stream_data("--", "--", "", False)

    # ── Theme ─────────────────────────────────────────────────────────

    def apply_theme(self, theme: GameTheme, kda: dict, history: list):
        self._theme = theme
        game_color = _safe_color(theme.primary)

        k, d, a = kda.get("k", "--"), kda.get("d", "--"), kda.get("a", "--")
        has_game = str(k) != "--"

        if has_game:
            self._game_lbl.setText(theme.name)
            self._game_lbl.setStyleSheet(f"color: {game_color}; background: transparent;")
            self._kda_lbl.setText(f"  {k} / {d} / {a}")
            self._kda_lbl.setStyleSheet("color: rgba(255,255,255,160); background: transparent;")
            self._sep2.setVisible(True)
        else:
            self._game_lbl.setText("En attente…")
            self._game_lbl.setStyleSheet("color: rgba(255,255,255,80); background: transparent;")
            self._kda_lbl.setText("")
            self._sep2.setVisible(False)

        self._exp.apply_theme(theme, kda, history)
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(0.5, 0.5, w - 1, h - 1)

        path = QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)

        # Fond noir profond
        painter.fillPath(path, QColor(4, 4, 6, 252))

        # Teinture jeu (très subtile)
        tr, tg, tb, ta = self._theme.bg_tint
        painter.fillPath(path, QColor(tr, tg, tb, min(ta, 30)))

        # Reflet de verre en haut
        grad = QLinearGradient(0, 0, 0, H_COL * 0.7)
        grad.setColorAt(0.0, QColor(255, 255, 255, 18))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(path, QBrush(grad))

        # Bordure très fine
        rr, gg, bb = _hex_rgb(self._theme.primary)
        pen = QPen(QColor(rr, gg, bb, 35))
        pen.setWidthF(0.8)
        painter.setPen(pen)
        painter.drawPath(path)

        # Alt → bordure blanche pour signaler le drag
        if self._alt_held:
            p2 = QPen(QColor(255, 255, 255, 140))
            p2.setWidthF(1.2)
            painter.setPen(p2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # Alert → halo vert
        if self._alert_active:
            a = int(max(0.0, math.sin(self._alert_phase)) * 210)
            p3 = QPen(QColor(48, 209, 88, a))
            p3.setWidthF(2.0)
            painter.setPen(p3)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    # ── Mouse ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle()
        elif event.button() == Qt.MouseButton.RightButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self._ac_timer.stop()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.RightButton and self._drag_origin:
            self.move(event.globalPosition().toPoint() - self._drag_origin)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self._drag_origin:
            self._drag_origin = None
            self._save_position()
