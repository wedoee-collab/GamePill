"""
Écran de bienvenue — affiché à l'ouverture manuelle de GamePill.
Style épuré, cohérent avec la fenêtre de réglages.
Pas affiché au premier lancement (onboarding) ni au démarrage Windows.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QCheckBox, QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

_QSS = """
QDialog { background: transparent; }
QLabel  { color:#ececf2; background:transparent; }
#card {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #17121f, stop:0.5 #0c0c14, stop:1 #0a0a11);
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.07);
}
#title { color:#ffffff; }
#body  { color:rgba(236,236,242,0.62); }
#tip   { color:rgba(236,236,242,0.40); }
#hair  { background: rgba(255,255,255,0.07); }
QCheckBox { color:rgba(236,236,242,0.46); font-size:9.5pt; spacing:8px; }
QCheckBox::indicator {
    width:16px; height:16px; border-radius:5px;
    border:1px solid rgba(255,255,255,0.22); background:rgba(255,255,255,0.05);
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #a45dff, stop:1 #7d2fd6);
    border:1px solid #9146FF;
}
QPushButton#btn {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 11px; padding: 11px 22px;
    color:#f3f3f7; font-size:10.5pt; font-weight:600;
}
QPushButton#btn:hover   { background: rgba(255,255,255,0.12); }
QPushButton#btn:pressed { background: rgba(255,255,255,0.05); }
QPushButton#btnAccent {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #9146FF, stop:1 #7d2fd6);
    border: 1px solid rgba(212,175,55,0.30);
    border-radius: 11px; padding: 11px 22px;
    color:#ffffff; font-size:10.5pt; font-weight:700;
}
QPushButton#btnAccent:hover   { background:#a45dff; }
QPushButton#btnAccent:pressed { background:#7d2fd6; }
"""


def _sf(size: float, weight: int = 400) -> QFont:
    f = QFont("Segoe UI")
    f.setPointSizeF(size)
    f.setWeight(QFont.Weight(weight))
    return f


class WelcomeWindow(QDialog):
    """Écran d'accueil. `wants_settings` indique si l'utilisateur a
    demandé à ouvrir les réglages."""

    def __init__(self, config, app_icon: QIcon = None, parent=None):
        super().__init__(parent)
        self._config = config
        self._app_icon = app_icon
        self.wants_settings = False
        self.setWindowTitle("Bienvenue dans GamePill")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(460, 432)
        self.setStyleSheet(_QSS)
        self._build()
        self._center()

    def _center(self):
        scr = QApplication.primaryScreen().geometry()
        self.move(scr.center().x() - self.width() // 2,
                  scr.center().y() - self.height() // 2)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(40, 36, 40, 26)
        lay.setSpacing(0)

        # Logo
        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self._app_icon and not self._app_icon.isNull():
            icon.setPixmap(self._app_icon.pixmap(60, 60))
        else:
            icon.setText("⚡")
            icon.setFont(_sf(34))
        lay.addWidget(icon)
        lay.addSpacing(16)

        # Accent
        accent = QFrame()
        accent.setFixedSize(46, 3)
        accent.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #D4AF37, stop:1 #9146FF); border-radius:1px;"
        )
        lay.addWidget(accent, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(18)

        title = QLabel("Bienvenue dans GamePill")
        title.setObjectName("title")
        title.setFont(_sf(18, 800))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        lay.addSpacing(11)

        body = QLabel(
            "Ta pill est affichée tout en haut de ton écran.\n"
            "Lève les yeux quand tu veux tes infos, puis\n"
            "replonge dans le jeu."
        )
        body.setObjectName("body")
        body.setFont(_sf(10.5))
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(body)
        lay.addSpacing(20)

        hair = QFrame()
        hair.setObjectName("hair")
        hair.setFixedHeight(1)
        lay.addWidget(hair)
        lay.addSpacing(16)

        tip = QLabel(
            "Double-clic sur l'icône GamePill, en bas à droite\n"
            "de l'écran, pour ouvrir les réglages à tout moment."
        )
        tip.setObjectName("tip")
        tip.setFont(_sf(9.5))
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(tip)

        lay.addStretch()

        self._dont_show = QCheckBox("Ne plus afficher au démarrage")
        lay.addWidget(self._dont_show, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(16)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        b_set = QPushButton("Réglages")
        b_set.setObjectName("btn")
        b_set.setCursor(Qt.CursorShape.PointingHandCursor)
        b_set.clicked.connect(self._open_settings)
        b_go = QPushButton("C'est parti")
        b_go.setObjectName("btnAccent")
        b_go.setCursor(Qt.CursorShape.PointingHandCursor)
        b_go.setDefault(True)
        b_go.clicked.connect(self._dismiss)
        btns.addWidget(b_set)
        btns.addWidget(b_go, 1)
        lay.addLayout(btns)

        outer.addWidget(card)

    # ── Actions ───────────────────────────────────────────────────────

    def _save_pref(self):
        if self._dont_show.isChecked():
            self._config.set("welcome_enabled", False)

    def _open_settings(self):
        self.wants_settings = True
        self._save_pref()
        self.accept()

    def _dismiss(self):
        self._save_pref()
        self.accept()

    # ── Déplacement (fenêtre sans bordure) ────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag"):
            self.move(event.globalPosition().toPoint() - self._drag)
