import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPainterPath, QLinearGradient, QBrush,
)

from core.themes import GameTheme, THEMES


def _sf(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    return QFont("Segoe UI", size, int(weight))


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class StatCard(QWidget):
    def __init__(self, label: str, value, color: str):
        super().__init__()
        self._color = color
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("StatCard { background-color: rgba(255,255,255,10); border-radius: 8px; }")
        self.setMinimumHeight(54)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        self._val_lbl = QLabel(str(value))
        self._val_lbl.setFont(_sf(18, QFont.Weight.Bold))
        self._val_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._key_lbl = QLabel(label)
        self._key_lbl.setFont(_sf(8))
        self._key_lbl.setStyleSheet("color: rgba(255,255,255,110); background: transparent; letter-spacing: 1px;")
        self._key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._val_lbl)
        layout.addWidget(self._key_lbl)

    def set_value(self, value):
        self._val_lbl.setText(str(value))


class HistoryBar(QWidget):
    """5 last games as colored bars — drawn in paintEvent for crispness."""

    def __init__(self, games: list, theme: GameTheme):
        super().__init__()
        self._games = games
        self._theme = theme
        self.setFixedHeight(52)
        self.setStyleSheet("background: transparent;")

    def set_data(self, games: list, theme: GameTheme):
        self._games = games
        self._theme = theme
        self.update()

    def paintEvent(self, _):
        if not self._games:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        n = len(self._games)
        slot_w = self.width() / n
        bar_area_h = 34
        max_k = max(g["k"] for g in self._games) or 1

        for i, g in enumerate(self._games):
            x = i * slot_w
            pad = 3
            bw = slot_w - pad * 2
            bar_h = max(5.0, g["k"] / max_k * bar_area_h)
            by = bar_area_h - bar_h

            win_color = QColor("#30d158") if g["win"] else QColor("#ff3b30")

            # Gradient bar
            grad = QLinearGradient(x + pad, by, x + pad, by + bar_h)
            c1 = QColor(win_color)
            c1.setAlpha(220)
            c2 = QColor(win_color)
            c2.setAlpha(100)
            grad.setColorAt(0, c1)
            grad.setColorAt(1, c2)

            path = QPainterPath()
            path.addRoundedRect(QRectF(x + pad, by, bw, bar_h), 3, 3)
            painter.fillPath(path, QBrush(grad))

            # KDA text
            kda = f"{g['k']}/{g['d']}/{g['a']}"
            painter.setPen(QColor(180, 180, 180, 140))
            painter.setFont(_sf(8))
            painter.drawText(
                QRectF(x, bar_area_h + 2, slot_w, 16),
                Qt.AlignmentFlag.AlignCenter,
                kda,
            )


class ExpandedContent(QWidget):
    def __init__(self, theme: GameTheme = None, kda: dict = None, history: list = None):
        super().__init__()
        self._theme = theme or THEMES["default"]
        self._kda = kda or {}
        self._history = history or []
        self._pulse_phase = 0.0
        self._build_ui()
        self._start_pulse()

    def _build_ui(self):
        d = self._kda
        t = self._theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 12)
        layout.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 2, 0, 0)

        section_lbl = QLabel("Partie en cours")
        section_lbl.setFont(_sf(12, QFont.Weight.Bold))
        section_lbl.setStyleSheet("color: white; background: transparent;")

        rank = d.get("rank", "")
        mode = "Competitive"
        self._rank_lbl = QLabel(f"{mode} · {rank}" if rank else mode)
        self._rank_lbl.setFont(_sf(10))
        self._rank_lbl.setStyleSheet("color: rgba(255,255,255,130); background: transparent;")
        self._rank_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        hdr.addWidget(section_lbl)
        hdr.addStretch()
        hdr.addWidget(self._rank_lbl)
        layout.addLayout(hdr)

        # ── Accent line ───────────────────────────────────────────────
        accent_line = QFrame()
        accent_line.setFixedHeight(1)
        r, g, b = _hex_rgb(t.primary)
        accent_line.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 rgba({r},{g},{b},160), stop:0.6 rgba({r},{g},{b},40), stop:1 rgba({r},{g},{b},0));"
            " border: none;"
        )
        layout.addWidget(accent_line)
        self._accent_line = accent_line

        # ── Stats grid 3×2 ────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(5)
        grid.setContentsMargins(0, 0, 0, 0)

        agent = d.get("agent") or "—"
        self._cards: dict[str, StatCard] = {}
        stats = [
            ("Kills",    d.get("k", 0),  "#34c759"),
            ("Deaths",   d.get("d", 0),  "#ff3b30"),
            ("Assists",  d.get("a", 0),  t.secondary),
            ("Score",    "4 820",         "white"),
            ("HS rate",  "72%",           "#ff9f0a"),
            ("Agent",    agent,           t.primary),
        ]
        for i, (label, val, color) in enumerate(stats):
            card = StatCard(label, val, color)
            self._cards[label] = card
            grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(grid)

        # ── Stream row ────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255,255,255,28); border: none;")
        layout.addWidget(sep)

        stream_row = QHBoxLayout()
        stream_row.setContentsMargins(0, 0, 0, 0)
        stream_row.setSpacing(6)

        self._sdot = QLabel("●")
        self._sdot.setFont(_sf(9))
        self._sdot.setStyleSheet("color: #ff3b30; background: transparent;")

        viewers_lbl = QLabel("1 247 viewers")
        viewers_lbl.setFont(_sf(11, QFont.Weight.DemiBold))
        viewers_lbl.setStyleSheet("color: rgba(255,255,255,200); background: transparent;")

        dur_lbl = QLabel("2h 14m")
        dur_lbl.setFont(_sf(11))
        dur_lbl.setStyleSheet("color: rgba(255,255,255,120); background: transparent;")

        stream_row.addWidget(self._sdot)
        stream_row.addWidget(viewers_lbl)
        stream_row.addStretch()
        stream_row.addWidget(dur_lbl)
        layout.addLayout(stream_row)

        # ── Sub / follow banner ───────────────────────────────────────
        self._banner = QWidget()
        self._banner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._banner.setStyleSheet(
            "QWidget { background-color: rgba(48,209,88,30);"
            " border-radius: 6px; border: 1px solid rgba(48,209,88,60); }"
        )
        banner_layout = QHBoxLayout(self._banner)
        banner_layout.setContentsMargins(10, 5, 10, 5)
        banner_layout.setSpacing(8)

        star = QLabel("★")
        star.setFont(_sf(12))
        star.setStyleSheet("color: #30d158; background: transparent; border: none;")

        self._banner_text = QLabel("Nouveau sub — xX_Shadow_Xx")
        self._banner_text.setFont(_sf(10, QFont.Weight.DemiBold))
        self._banner_text.setStyleSheet("color: #30d158; background: transparent; border: none;")

        banner_layout.addWidget(star)
        banner_layout.addWidget(self._banner_text)
        banner_layout.addStretch()
        layout.addWidget(self._banner)

    def _start_pulse(self):
        t = QTimer(self)
        t.timeout.connect(self._tick_pulse)
        t.start(30)

    def _tick_pulse(self):
        self._pulse_phase = (self._pulse_phase + 0.1257) % (2 * math.pi)
        a = int((0.4 + 0.6 * (math.sin(self._pulse_phase) * 0.5 + 0.5)) * 255)
        self._sdot.setStyleSheet(f"color: rgba(255,59,48,{a}); background: transparent;")

    def apply_theme(self, theme: GameTheme, kda: dict, history: list):
        self._theme = theme
        self._kda = kda
        self._history = history

        rank = kda.get("rank", "")
        self._rank_lbl.setText(f"Competitive · {rank}" if rank else "Competitive")

        r, g, b = _hex_rgb(theme.primary)
        self._accent_line.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 rgba({r},{g},{b},160), stop:0.6 rgba({r},{g},{b},40), stop:1 rgba({r},{g},{b},0));"
            " border: none;"
        )

        agent = kda.get("agent") or "—"
        updates = {
            "Kills":   kda.get("k", 0),
            "Deaths":  kda.get("d", 0),
            "Assists": kda.get("a", 0),
            "Agent":   agent,
        }
        for label, val in updates.items():
            if label in self._cards:
                self._cards[label].set_value(val)

        assist_card = self._cards.get("Assists")
        if assist_card:
            assist_card._val_lbl.setStyleSheet(f"color: {theme.secondary}; background: transparent;")
        agent_card = self._cards.get("Agent")
        if agent_card:
            agent_card._val_lbl.setStyleSheet(f"color: {theme.primary}; background: transparent;")

