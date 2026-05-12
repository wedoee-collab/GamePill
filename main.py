import sys
import ctypes
import os

# Fix Windows DPI blurriness — must be before QApplication
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QPainter, QPixmap, QColor, QIcon, QFont
from PyQt6.QtCore import Qt, QTimer

from ui.pill_widget import PillWidget, PLATFORM_TWITCH, PLATFORM_YOUTUBE
from services.game_detector import GameDetector
from core.themes import THEMES


def _make_tray_icon() -> QIcon:
    px = QPixmap(16, 16)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#ff3b30"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 12, 12)
    p.end()
    return QIcon(px)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 10))

    detector = GameDetector()
    pill = PillWidget(THEMES["default"])

    def on_game_changed(key: str, theme):
        pill.apply_theme(theme, detector.current_kda(), detector.current_history())

    detector.game_changed.connect(on_game_changed)
    pill.show()
    detector.start()

    # Demo: cycle themes every 6s to preview colors
    _keys = ["valorant", "cs2", "fortnite", "apex", "league", "rocket_league", "dbd", "default"]
    _idx = [0]

    _platforms = [PLATFORM_TWITCH, PLATFORM_YOUTUBE, PLATFORM_TWITCH, PLATFORM_TWITCH,
                  PLATFORM_YOUTUBE, PLATFORM_TWITCH, PLATFORM_TWITCH, PLATFORM_TWITCH]

    def _demo_cycle():
        idx = _idx[0] % len(_keys)
        key = _keys[idx]
        _idx[0] += 1
        from services.game_detector import MOCK_KDA, MOCK_HISTORY
        pill.apply_theme(THEMES[key], MOCK_KDA.get(key, MOCK_KDA["default"]),
                         MOCK_HISTORY.get(key, MOCK_HISTORY["default"]))
        pill.set_platform(_platforms[idx % len(_platforms)])

    QTimer.singleShot(200, _demo_cycle)
    demo_timer = QTimer()
    demo_timer.timeout.connect(_demo_cycle)
    demo_timer.start(6_000)

    # Tray
    tray = QSystemTrayIcon(_make_tray_icon(), app)
    tray.setToolTip("GamePill")
    menu = QMenu()
    menu.addAction("Demo alerte sub").triggered.connect(pill.trigger_alert)
    menu.addSeparator()
    menu.addAction("Parametres").triggered.connect(lambda: None)
    menu.addAction("Deconnecter").triggered.connect(lambda: None)
    menu.addSeparator()
    menu.addAction("Quitter").triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
