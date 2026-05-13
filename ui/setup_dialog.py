"""
Dialog de connexion Twitch — dark mode, style Gaming premium.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QLinearGradient,
    QBrush, QPen, QPolygonF,
)


def _sf(size: int, bold: bool = False, light: bool = False) -> QFont:
    f = QFont("Segoe UI", size)
    if bold:
        f.setWeight(QFont.Weight.Bold)
    elif light:
        f.setWeight(QFont.Weight.Light)
    return f


class _PillButton(QPushButton):
    """Bouton pill violet avec hover animé."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(44)
        self.setFont(_sf(11, bold=True))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #9146FF, stop:1 #7B2FBE);
                color: white;
                border-radius: 22px;
                border: none;
                padding: 0 28px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #A970FF, stop:1 #9146FF);
            }
            QPushButton:pressed {
                background: #6A0DAD;
            }
        """)


class _PermRow(QWidget):
    """Une ligne de permission avec icône et texte."""
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(_sf(15))
        icon_lbl.setFixedWidth(26)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")

        txt = QLabel(text)
        txt.setFont(_sf(10))
        txt.setStyleSheet("color: rgba(255,255,255,170); background: transparent;")

        row.addWidget(icon_lbl)
        row.addWidget(txt)
        row.addStretch()


class TwitchConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GamePill — Connexion Twitch")
        self.setFixedSize(420, 480)
        self.setModal(True)
        # Dark frameless style
        self.setStyleSheet("QDialog { background: #0e0e10; border-radius: 16px; }")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Zone header violette ──────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(110)
        header.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1f0a3a, stop:1 #0e0e10);
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        """)

        hl = QVBoxLayout(header)
        hl.setContentsMargins(28, 20, 28, 16)
        hl.setSpacing(6)

        badge_row = QHBoxLayout()
        badge = QLabel("  TWITCH  ")
        badge.setFont(_sf(9, bold=True))
        badge.setStyleSheet(
            "color: white; background: #9146FF; border-radius: 4px; padding: 3px 0px;"
        )
        badge.setFixedHeight(22)
        badge_row.addWidget(badge)
        badge_row.addStretch()
        hl.addLayout(badge_row)

        title = QLabel("Connexion à ton compte")
        title.setFont(_sf(17, bold=True))
        title.setStyleSheet("color: white; background: transparent;")
        hl.addWidget(title)

        sub = QLabel("GamePill va accéder à tes stats de stream en lecture seule.")
        sub.setFont(_sf(9))
        sub.setStyleSheet("color: rgba(255,255,255,120); background: transparent;")
        sub.setWordWrap(True)
        hl.addWidget(sub)

        layout.addWidget(header)

        # ── Corps ─────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background: #0e0e10;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 24)
        bl.setSpacing(0)

        # Titre section
        perms_title = QLabel("Accès demandés")
        perms_title.setFont(_sf(8, bold=True))
        perms_title.setStyleSheet(
            "color: rgba(255,255,255,50); background: transparent; letter-spacing: 2px;"
        )
        bl.addWidget(perms_title)
        bl.addSpacing(14)

        # Permissions
        perms = [
            ("👁", "Nombre de viewers en direct"),
            ("🔔", "Nouveaux follows et abonnés"),
            ("⚡", "Pseudo récupéré automatiquement"),
        ]
        for icon, text in perms:
            bl.addWidget(_PermRow(icon, text))
            bl.addSpacing(12)

        bl.addSpacing(8)

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,12); border: none;")
        sep.setFixedHeight(1)
        bl.addWidget(sep)
        bl.addSpacing(18)

        # Vie privée
        privacy = QLabel("🔒  Tes données restent sur ton PC. Aucun serveur externe.")
        privacy.setFont(_sf(9))
        privacy.setStyleSheet("color: rgba(255,255,255,60); background: transparent;")
        privacy.setWordWrap(True)
        bl.addWidget(privacy)

        bl.addStretch()
        bl.addSpacing(24)

        # Boutons
        btns = QHBoxLayout()
        btns.setSpacing(12)

        cancel = QPushButton("Annuler")
        cancel.setFixedHeight(44)
        cancel.setFont(_sf(10))
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,8);
                color: rgba(255,255,255,150);
                border-radius: 22px;
                border: 1px solid rgba(255,255,255,15);
                padding: 0 20px;
            }
            QPushButton:hover { background: rgba(255,255,255,14); }
            QPushButton:pressed { background: rgba(255,255,255,6); }
        """)
        cancel.clicked.connect(self.reject)

        connect = _PillButton("  Connecter avec Twitch  →")
        connect.setDefault(True)
        connect.clicked.connect(self.accept)

        btns.addWidget(cancel)
        btns.addWidget(connect, 1)
        bl.addLayout(btns)

        layout.addWidget(body)
