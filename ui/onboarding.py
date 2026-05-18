"""
Wizard de premier lancement — 4 étapes.
Déclenché quand config.json n'existe pas encore.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient, QBrush

_STYLE = """
QDialog {
    background-color: #0e0e1a;
    border-radius: 16px;
}
QLabel {
    color: #e8e8f0;
    background: transparent;
}
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #9146FF, stop:1 #7B2FBE);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 28px;
    font-size: 13px;
    font-weight: 700;
    font-family: 'Segoe UI';
}
QPushButton:hover { background: #a855ff; }
QPushButton#btn_skip {
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.55);
    border: 1px solid rgba(255,255,255,0.12);
    padding: 10px 20px;
}
QPushButton#btn_skip:hover {
    background: rgba(255,255,255,0.10);
    color: rgba(255,255,255,0.8);
}
"""

_PAGES = [
    {
        "icon":  "⚡",
        "title": "Bienvenue dans GamePill",
        "body":  (
            "Une pill discrète en haut de ton écran — inspirée du\n"
            "Dynamic Island d'Apple — qui affiche tes stats en temps réel.\n\n"
            "Twitch · YouTube · Kick · Valorant · LoL · CS2\n"
            "et bien d'autres encore."
        ),
        "hint": "Clique gauche pour développer · Clic droit pour déplacer",
    },
    {
        "icon":  "🟣",
        "title": "Connecte tes plateformes",
        "body":  (
            "Clic droit sur l'icône GamePill dans la barre des tâches\n"
            "pour accéder au menu.\n\n"
            "→ Twitch : connexion OAuth sécurisée en un clic\n"
            "→ YouTube : entre ton @handle de chaîne\n"
            "→ Kick : entre le slug de ta chaîne Kick"
        ),
        "hint": "Tes tokens sont chiffrés localement — rien n'est envoyé",
    },
    {
        "icon":  "🎮",
        "title": "Stats jeu en temps réel",
        "body":  (
            "GamePill détecte automatiquement ton jeu (14 jeux supportés).\n\n"
            "Pour Valorant / League of Legends :\n"
            "→ Configure ton Riot ID dans Menu → Riot\n\n"
            "Pour CS2 — stats GSI temps réel :\n"
            "→ Copie gamepill.cfg dans ton dossier cfg CS2\n"
            "   (Menu → CS2 → Installer le config)"
        ),
        "hint": "Les stats mock sont affichées en attendant les vraies données",
    },
    {
        "icon":  "✅",
        "title": "Tu es prêt !",
        "body":  (
            "La pill est maintenant en haut de ton écran.\n\n"
            "Astuce : active le démarrage automatique dans le menu\n"
            "pour que GamePill soit toujours là.\n\n"
            "Bonne session — gg ez 🎯"
        ),
        "hint": "Alt + Clic droit pour déplacer la pill n'importe où",
    },
]


def _sf(size: int, bold: bool = False) -> QFont:
    f = QFont("Segoe UI", size)
    if bold:
        f.setWeight(QFont.Weight.Bold)
    return f


class _PageWidget(QWidget):
    def __init__(self, page: dict, idx: int, total: int):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 24)
        layout.setSpacing(14)

        # ── Progress dots ─────────────────────────────────────────────
        dots_row = QHBoxLayout()
        dots_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        dots_row.setSpacing(6)
        for i in range(total):
            dot = QLabel("●" if i == idx else "○")
            dot.setFont(_sf(10))
            color = "#9146FF" if i == idx else "rgba(255,255,255,30)"
            dot.setStyleSheet(f"color: {color};")
            dots_row.addWidget(dot)
        dots_row.addStretch()
        layout.addLayout(dots_row)

        # ── Icon ─────────────────────────────────────────────────────
        icon_lbl = QLabel(page["icon"])
        icon_lbl.setFont(_sf(44))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        # ── Title ─────────────────────────────────────────────────────
        title = QLabel(page["title"])
        title.setFont(_sf(20, bold=True))
        title.setStyleSheet("color: #ffffff; letter-spacing: -0.5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── Body ──────────────────────────────────────────────────────
        body = QLabel(page["body"])
        body.setFont(_sf(12))
        body.setStyleSheet("color: rgba(255,255,255,0.72); line-height: 1.6;")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(body)

        layout.addStretch()

        # ── Hint ──────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: rgba(145,70,255,0.18); border: none; margin: 0 -8px;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        hint = QLabel(page["hint"])
        hint.setFont(_sf(10))
        hint.setStyleSheet("color: rgba(255,255,255,0.38); padding-top: 6px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)


class OnboardingWizard(QDialog):
    """Wizard de premier lancement."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bienvenue dans GamePill")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 460)
        self._current = 0
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget(self)
        self._container.setObjectName("container")
        self._container.setStyleSheet(
            "#container { background-color: #0e0e1a;"
            " border-radius: 16px;"
            " border: 1px solid rgba(145,70,255,0.30); }"
        )

        inner = QVBoxLayout(self._container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # ── Stacked pages ─────────────────────────────────────────────
        self._stack = QStackedWidget()
        for i, p in enumerate(_PAGES):
            self._stack.addWidget(_PageWidget(p, i, len(_PAGES)))
        inner.addWidget(self._stack)

        # ── Button row ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(36, 0, 36, 28)
        btn_row.setSpacing(10)

        self._btn_skip = QPushButton("Passer")
        self._btn_skip.setObjectName("btn_skip")
        self._btn_skip.clicked.connect(self.reject)

        self._btn_next = QPushButton("Suivant  →")
        self._btn_next.clicked.connect(self._next)

        btn_row.addWidget(self._btn_skip)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_next)

        inner.addLayout(btn_row)
        outer.addWidget(self._container)

        self.setStyleSheet(_STYLE)

    def _next(self):
        if self._current < len(_PAGES) - 1:
            self._current += 1
            self._stack.setCurrentIndex(self._current)
            if self._current == len(_PAGES) - 1:
                self._btn_next.setText("Commencer ✓")
                self._btn_skip.setVisible(False)
        else:
            self.accept()

    # ── Drag pour déplacer la fenêtre sans barre de titre ─────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)


def should_show(config) -> bool:
    """Renvoie True si c'est le premier lancement (pas de config existante)."""
    return not (
        config.get("twitch_access_token")
        or config.get("youtube_channel_id")
        or config.get("kick_slug")
        or config.get("onboarding_done")
    )
