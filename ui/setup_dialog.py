"""
Dialog de connexion Twitch — style GamePill (identique au site).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget,
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QLinearGradient,
    QBrush, QPen, QRadialGradient,
)


# ── Couleurs site ──────────────────────────────────────────────────────────────
BLACK   = "#08080f"
DARK    = "#10101c"
CARD    = "#16162a"
CARD2   = "#1c1c32"
PURPLE  = "#9146FF"
PURPLE2 = "#7B2FBE"
GOLD    = "#D4AF37"
GOLD2   = "#F0D060"
RED     = "#ff3b30"
MUTED   = "rgba(255,255,255,0.6)"
DIM     = "rgba(255,255,255,0.35)"


def _font(size: int, weight: int = 400) -> QFont:
    f = QFont("Segoe UI", size)
    f.setWeight(QFont.Weight(weight))
    return f


# ── Dot LIVE animé ─────────────────────────────────────────────────────────────
class _PulseDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._alpha = 255
        self._growing = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(25)

    def _tick(self):
        self._alpha += -5 if not self._growing else 5
        if self._alpha <= 50:  self._growing = True
        if self._alpha >= 255: self._growing = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        c = QColor(RED)
        c.setAlpha(self._alpha)
        p.setBrush(c)
        p.drawEllipse(1, 1, 6, 6)


# ── Séparateur dégradé or ──────────────────────────────────────────────────────
class _GoldLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0,   QColor(212, 175, 55, 220))
        g.setColorAt(0.4, QColor(145,  70, 255, 80))
        g.setColorAt(1,   QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(g))


# ── Fond du header avec glow radial ───────────────────────────────────────────
class _HeaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Fond dégradé sombre
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0, QColor(30, 10, 70))
        g.setColorAt(0.6, QColor(16, 8, 40))
        g.setColorAt(1, QColor(8, 8, 15))
        p.fillRect(self.rect(), QBrush(g))

        # Glow violet en haut à gauche
        rg = QRadialGradient(w * 0.2, 0, w * 0.7)
        rg.setColorAt(0, QColor(145, 70, 255, 60))
        rg.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(rg))

        # Grille subtile (comme le site)
        pen = QPen(QColor(145, 70, 255, 12))
        pen.setWidthF(0.5)
        p.setPen(pen)
        step = 32
        for x in range(0, w, step):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            p.drawLine(0, y, w, y)


# ── Badge pill "LIVE" ──────────────────────────────────────────────────────────
class _LiveBadge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 14, 0)
        lay.setSpacing(7)

        self._dot = _PulseDot()
        lay.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel("LIVE")
        lbl.setFont(_font(8, 700))
        lbl.setStyleSheet(f"color: {RED}; letter-spacing: 2px; background: transparent;")
        lay.addWidget(lbl)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        p.fillPath(path, QColor(145, 70, 255, 25))
        pen = QPen(QColor(145, 70, 255, 70))
        pen.setWidthF(0.8)
        p.setPen(pen)
        p.drawPath(path)


# ── Permission row ─────────────────────────────────────────────────────────────
class _PermRow(QWidget):
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(14)

        ic = QLabel(icon)
        ic.setFont(_font(15))
        ic.setFixedWidth(26)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setStyleSheet("background: transparent;")

        tx = QLabel(text)
        tx.setFont(_font(10))
        tx.setStyleSheet("color: rgba(255,255,255,0.85); background: transparent;")

        lay.addWidget(ic)
        lay.addWidget(tx)
        lay.addStretch()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, self.width()-1, self.height()-1), 10, 10)
        p.fillPath(path, QColor(255, 255, 255, 5))
        pen = QPen(QColor(145, 70, 255, 20))
        pen.setWidthF(0.8)
        p.setPen(pen)
        p.drawPath(path)


# ── Dialog principal ───────────────────────────────────────────────────────────
class TwitchConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GamePill — Connexion Twitch")
        self.setFixedSize(460, 520)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BLACK};
            }}
            QLabel {{ background: transparent; }}
        """)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header avec fond peint ────────────────────────────────────
        header = _HeaderWidget()
        header.setFixedHeight(150)

        hl = QVBoxLayout(header)
        hl.setContentsMargins(30, 22, 30, 22)
        hl.setSpacing(10)

        # Ligne : badge LIVE + badge TWITCH
        badge_row = QHBoxLayout()
        badge_row.setSpacing(10)

        live_badge = _LiveBadge()
        badge_row.addWidget(live_badge)

        twitch_badge = QLabel("  TWITCH  ")
        twitch_badge.setFont(_font(8, 700))
        twitch_badge.setStyleSheet(f"""
            color: white;
            background: {PURPLE};
            border-radius: 5px;
            padding: 4px 6px;
            letter-spacing: 1px;
        """)
        badge_row.addWidget(twitch_badge)
        badge_row.addStretch()
        hl.addLayout(badge_row)

        title = QLabel("Connexion à ton compte")
        title.setFont(_font(20, 700))
        title.setStyleSheet("color: white;")
        hl.addWidget(title)

        sub = QLabel("GamePill accède à tes stats en lecture seule.")
        sub.setFont(_font(10))
        sub.setStyleSheet(f"color: {MUTED};")
        hl.addWidget(sub)

        root.addWidget(header)

        # Séparateur or
        root.addWidget(_GoldLine())

        # ── Corps ─────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background: {DARK};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(30, 26, 30, 30)
        bl.setSpacing(0)

        # Titre section en or
        sec_label = QLabel("CE QUE TU OBTIENS")
        sec_label.setFont(_font(8, 700))
        sec_label.setStyleSheet(f"color: {GOLD}; letter-spacing: 3px;")
        bl.addWidget(sec_label)
        bl.addSpacing(14)

        # Fonctionnalités
        perms = [
            ("📊",  "Viewers en direct sur ta pill"),
            ("⚡",  "Connexion instantanée, sans mot de passe"),
            ("🔒",  "Lecture seule · Jamais de modification"),
        ]
        for icon, text in perms:
            bl.addWidget(_PermRow(icon, text))
            bl.addSpacing(6)

        bl.addSpacing(10)

        # Ligne séparateur fin
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: rgba(145,70,255,0.15); border: none;")
        bl.addWidget(sep)
        bl.addSpacing(14)

        # Vie privée
        priv = QLabel("🔒  Données 100% locales · Aucun serveur externe")
        priv.setFont(_font(9))
        priv.setStyleSheet(f"color: {DIM};")
        bl.addWidget(priv)

        bl.addStretch()
        bl.addSpacing(20)

        # ── Boutons ───────────────────────────────────────────────────
        btns = QHBoxLayout()
        btns.setSpacing(12)

        cancel = QPushButton("Annuler")
        cancel.setFixedHeight(48)
        cancel.setFont(_font(10))
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05);
                color: {MUTED};
                border-radius: 24px;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.09);
                color: white;
                border-color: rgba(255,255,255,0.2);
            }}
            QPushButton:pressed {{ background: rgba(255,255,255,0.03); }}
        """)
        cancel.clicked.connect(self.reject)

        connect = QPushButton("Connecter avec Twitch  →")
        connect.setFixedHeight(48)
        connect.setFont(_font(11, 700))
        connect.setDefault(True)
        connect.setCursor(Qt.CursorShape.PointingHandCursor)
        connect.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {PURPLE}, stop:1 {PURPLE2});
                color: white;
                border-radius: 24px;
                border: 1px solid rgba(212,175,55,0.3);
                padding: 0 26px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #a855ff, stop:1 {PURPLE});
                border-color: rgba(212,175,55,0.55);
            }}
            QPushButton:pressed {{
                background: {PURPLE2};
            }}
        """)
        connect.clicked.connect(self.accept)

        btns.addWidget(cancel, 1)
        btns.addWidget(connect, 2)
        bl.addLayout(btns)

        root.addWidget(body, 1)
