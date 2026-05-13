import sys
import ctypes
import os
import threading

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

# Logging doit être initialisé avant tout import de service
import core.logger as _log_mod
log = _log_mod.setup()

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox, QInputDialog,
)
from PyQt6.QtGui import (
    QPainter, QPixmap, QColor, QIcon, QFont, QAction,
    QPen, QPainterPath, QBrush,
)
from PyQt6.QtCore import Qt, QTimer, QRectF

from ui.pill_widget import PillWidget, PLATFORM_TWITCH, PLATFORM_YOUTUBE, PLATFORM_KICK, PLATFORM_NONE
from ui.setup_dialog import TwitchConnectDialog
from ui.youtube_dialog import YouTubeConnectDialog
from ui.onboarding import OnboardingWizard, should_show as _should_onboard
from services.game_detector import GameDetector
from services.twitch_service import TwitchService
from services.twitch_eventsub import TwitchEventSub
from services.youtube_service import YouTubeService, resolve_channel
from services.kick_service import KickService
from services.cs2_service import CS2GSI
from services.riot_service import RiotService, SUPPORTED_GAMES as RIOT_GAMES
from core.auth import TwitchAuth
from core.config import Config
from core.themes import THEMES
import core.autostart as autostart
from core.constants import YOUTUBE_API_KEY, RIOT_API_KEY

def _dot_icon(hex_color: str, size: int = 12) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(hex_color))
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.end()
    return QIcon(px)


def _platform_icon(hex_color: str, size: int = 16) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(hex_color))
    p.drawRoundedRect(0, 0, size, size, 4, 4)
    p.end()
    return QIcon(px)


_MENU_STYLE = """
QMenu {
    background-color: #1a1a2e;
    border: 1px solid rgba(145, 70, 255, 0.35);
    border-radius: 10px;
    padding: 5px 0px;
    font-family: 'Segoe UI';
    font-size: 10pt;
    color: #ffffff;
}
QMenu::item {
    padding: 8px 18px 8px 12px;
    background: transparent;
    border-radius: 6px;
    margin: 1px 4px;
    min-width: 170px;
    color: #e8e8f0;
}
QMenu::item:selected {
    background: rgba(145, 70, 255, 0.28);
    color: #ffffff;
}
QMenu::item:disabled {
    color: rgba(200, 200, 220, 0.45);
    background: transparent;
}
QMenu::separator {
    height: 1px;
    background: rgba(145, 70, 255, 0.22);
    margin: 4px 10px;
}
QMenu::right-arrow {
    image: none;
    width: 6px;
    height: 6px;
    border-right: 2px solid rgba(145,70,255,0.7);
    border-top: 2px solid rgba(145,70,255,0.7);
    margin-right: 6px;
}
QMenu::indicator {
    width: 14px;
    height: 14px;
    margin-left: 4px;
}
QMenu::indicator:checked {
    background: rgba(145, 70, 255, 0.85);
    border-radius: 3px;
    border: 1px solid rgba(145,70,255,1);
}
QMenu::indicator:unchecked {
    background: rgba(255,255,255,0.07);
    border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.2);
}
"""


def _make_tray_icon() -> QIcon:
    px = QPixmap(32, 16)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 1, 32, 14), 7, 7)
    p.fillPath(path, QColor(10, 10, 12, 240))
    pen = QPen(QColor(145, 70, 255, 120))
    pen.setWidthF(1.0)
    p.setPen(pen)
    p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ff3b30"))
    p.drawEllipse(5, 5, 6, 6)
    p.setPen(QColor(255, 255, 255, 200))
    f = QFont("Segoe UI", 6, int(QFont.Weight.Bold))
    p.setFont(f)
    p.drawText(14, 12, "GP")
    p.end()
    return QIcon(px)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 10))

    config      = Config()
    twitch_auth = TwitchAuth(config)
    twitch      = TwitchService(twitch_auth, config)
    eventsub    = TwitchEventSub(twitch_auth)
    youtube     = YouTubeService(config)
    kick        = KickService(config)
    cs2_gsi     = CS2GSI()
    detector    = GameDetector()
    riot        = RiotService(config)

    pill = PillWidget(THEMES["default"])

    # ── Onboarding premier lancement ─────────────────────────────────
    if _should_onboard(config):
        QTimer.singleShot(800, lambda: _show_onboarding(config))

    def _show_onboarding(cfg):
        dlg = OnboardingWizard()
        dlg.exec()
        cfg.set("onboarding_done", True)

    # ── Game detector ─────────────────────────────────────────────────
    def on_game_changed(key: str, theme):
        pill.apply_theme(theme, detector.current_kda(), detector.current_history())
        riot.on_game_changed(key)
        # Démarrer CS2 GSI quand CS2 est détecté
        if key == "cs2" and not cs2_gsi.is_running:
            QTimer.singleShot(0, cs2_gsi.start)

    detector.game_changed.connect(on_game_changed)

    # ── CS2 GSI stats ─────────────────────────────────────────────────
    def on_cs2_stats(kda: dict):
        pill.apply_theme(THEMES["cs2"], kda, [])

    cs2_gsi.stats_updated.connect(on_cs2_stats)

    # ── Riot API ─────────────────────────────────────────────────────
    def on_riot_data(game_key: str, kda: dict, history: list):
        pill.apply_theme(THEMES.get(game_key, THEMES["default"]), kda, history)

    riot.data_updated.connect(on_riot_data)

    # ── Systray ──────────────────────────────────────────────────────
    tray = QSystemTrayIcon(_make_tray_icon(), app)
    tray.setToolTip("GamePill")

    menu = QMenu()
    menu.setStyleSheet(_MENU_STYLE)

    status_action = QAction("⏸  Non connecté", app)
    status_action.setEnabled(False)
    menu.addAction(status_action)
    menu.addSeparator()

    # ── Twitch ────────────────────────────────────────────────────────
    twitch_menu = QMenu("  Twitch", menu)
    twitch_menu.setStyleSheet(_MENU_STYLE)
    twitch_menu.setIcon(_platform_icon("#9146FF"))
    act_connect_tw    = QAction(_dot_icon("#9146FF"), "  Connecter", app)
    act_disconnect_tw = QAction(_dot_icon("#444455"), "  Déconnecter", app)
    twitch_menu.addAction(act_connect_tw)
    twitch_menu.addAction(act_disconnect_tw)
    menu.addMenu(twitch_menu)

    # ── YouTube ───────────────────────────────────────────────────────
    yt_menu = QMenu("  YouTube", menu)
    yt_menu.setStyleSheet(_MENU_STYLE)
    yt_menu.setIcon(_platform_icon("#FF0000"))
    act_connect_yt    = QAction(_dot_icon("#FF0000"), "  Connecter", app)
    act_disconnect_yt = QAction(_dot_icon("#444455"), "  Déconnecter", app)
    yt_menu.addAction(act_connect_yt)
    yt_menu.addAction(act_disconnect_yt)
    menu.addMenu(yt_menu)

    if not YOUTUBE_API_KEY:
        act_connect_yt.setEnabled(False)
        act_connect_yt.setText("  Connecter  (clé API manquante)")

    # ── Kick ──────────────────────────────────────────────────────────
    kick_menu = QMenu("  Kick", menu)
    kick_menu.setStyleSheet(_MENU_STYLE)
    kick_menu.setIcon(_platform_icon("#53FC18"))
    act_connect_kick    = QAction(_dot_icon("#53FC18"), "  Configurer slug", app)
    act_disconnect_kick = QAction(_dot_icon("#444455"), "  Déconnecter", app)
    kick_menu.addAction(act_connect_kick)
    kick_menu.addAction(act_disconnect_kick)
    menu.addMenu(kick_menu)

    # ── Riot ──────────────────────────────────────────────────────────
    riot_menu = QMenu("  Riot (Val / LoL)", menu)
    riot_menu.setStyleSheet(_MENU_STYLE)
    riot_menu.setIcon(_platform_icon("#C89B3C"))
    act_config_riot = QAction(_dot_icon("#C89B3C"), "  Configurer Riot ID", app)
    act_clear_riot  = QAction(_dot_icon("#444455"), "  Effacer config", app)
    riot_menu.addAction(act_config_riot)
    riot_menu.addAction(act_clear_riot)
    menu.addMenu(riot_menu)

    if not RIOT_API_KEY:
        act_config_riot.setEnabled(False)
        act_config_riot.setText("  Configurer  (RIOT_API_KEY requis)")

    # ── CS2 ───────────────────────────────────────────────────────────
    cs2_menu = QMenu("  CS2 GSI", menu)
    cs2_menu.setStyleSheet(_MENU_STYLE)
    cs2_menu.setIcon(_platform_icon("#F5A623"))
    act_cs2_start   = QAction(_dot_icon("#F5A623"), "  Activer GSI", app)
    act_cs2_install = QAction(_dot_icon("#888899"), "  Installer gamepill.cfg", app)
    cs2_menu.addAction(act_cs2_start)
    cs2_menu.addAction(act_cs2_install)
    menu.addMenu(cs2_menu)

    menu.addSeparator()

    # ── Démarrage automatique ─────────────────────────────────────────
    act_autostart = QAction(app)
    act_autostart.setCheckable(True)

    def _update_autostart_label():
        on = autostart.is_enabled()
        act_autostart.setChecked(on)
        act_autostart.setText("  Démarrer avec Windows")
        act_autostart.setIcon(_dot_icon("#9146FF" if on else "#333344"))

    _update_autostart_label()

    def _toggle_autostart():
        new_state = autostart.toggle()
        _update_autostart_label()
        tray.showMessage("GamePill",
                         "Démarrage auto activé" if new_state else "Démarrage auto désactivé",
                         QSystemTrayIcon.MessageIcon.Information, 2000)

    act_autostart.triggered.connect(_toggle_autostart)
    menu.addAction(act_autostart)

    menu.addSeparator()

    act_demo = QAction(_dot_icon("#D4AF37"), "  Demo alerte sub", app)
    act_demo.triggered.connect(lambda: pill.trigger_alert())
    menu.addAction(act_demo)

    menu.addSeparator()

    act_quit = QAction(_dot_icon("#ff3b30"), "  Quitter", app)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_quit)

    # ── Statut ───────────────────────────────────────────────────────
    def _refresh_status():
        try:
            parts = []
            if twitch_auth.is_connected:
                name = config.get("twitch_display_name") or config.get("twitch_username") or "Twitch"
                td = twitch.data
                if td.is_live:
                    parts.append(f"🟣 {name}  {td.viewers_fmt()} v  ({td.uptime_fmt()})")
                else:
                    parts.append(f"⚫ {name}  (Twitch offline)")
            if youtube.is_configured():
                name = youtube.display_name or "YouTube"
                yd = youtube.data
                if yd.is_live:
                    parts.append(f"🔴 {name}  {yd.viewers_fmt()} v  ({yd.uptime_fmt()})")
                else:
                    parts.append(f"⚫ {name}  (YouTube offline)")
            if kick.is_configured():
                kd = kick.data
                name = kd.slug or "Kick"
                if kd.is_live:
                    parts.append(f"🟢 {name}  {kd.viewers_fmt()} v")
                else:
                    parts.append(f"⚫ {name}  (Kick offline)")
            label = "  |  ".join(parts) if parts else "⏸  Non connecté"
            status_action.setText(label)
            tray.setToolTip(f"GamePill  |  {label}")
        except Exception as e:
            log.warning("_refresh_status : %s", e)

    # ── EventSub callbacks ───────────────────────────────────────────
    def on_follow(username: str):
        log.info("EventSub follow : %s", username)
        twitch.add_follow(username)
        pill.trigger_alert()
        tray.showMessage("GamePill", f"🟣 Nouveau follow — {username}",
                         QSystemTrayIcon.MessageIcon.Information, 3000)

    def on_sub(username: str, is_gift: bool):
        log.info("EventSub sub : %s (gift=%s)", username, is_gift)
        twitch.add_sub(username, is_gift)
        pill.trigger_alert()
        label = f"🎁 Sub offert — {username}" if is_gift else f"⭐ Nouveau sub — {username}"
        tray.showMessage("GamePill", label, QSystemTrayIcon.MessageIcon.Information, 3000)

    def on_raid(from_name: str, viewers: int):
        log.info("EventSub raid : %s avec %d viewers", from_name, viewers)
        twitch.add_raid(from_name, viewers)
        pill.trigger_alert()
        tray.showMessage("GamePill", f"🚀 Raid de {from_name} — {viewers} viewers",
                         QSystemTrayIcon.MessageIcon.Information, 4000)

    eventsub.follow_received.connect(on_follow)
    eventsub.sub_received.connect(on_sub)
    eventsub.raid_received.connect(on_raid)

    def _start_eventsub():
        bid = config.get("twitch_broadcaster_id", "")
        uid = config.get("twitch_user_id", "")
        if bid and uid:
            log.info("Démarrage EventSub — bid=%s", bid)
            eventsub.start(bid, uid)

    # ── Twitch callbacks ─────────────────────────────────────────────
    def on_twitch_data(data):
        session = {
            "follows": data.session_follows,
            "subs":    data.session_subs,
            "raids":   data.session_raids,
        }
        pill.update_live_data(
            PLATFORM_TWITCH, data.viewers_fmt(), data.uptime_fmt(),
            data.last_follower if data.is_live else "", data.is_live,
            peak=data.peak_fmt() if data.is_live else "",
            session=session,
        )
        pill.set_platform(PLATFORM_TWITCH)
        if data.broadcaster_id and not eventsub._running:
            QTimer.singleShot(0, _start_eventsub)
        _refresh_status()

    def on_twitch_lost():
        log.warning("Twitch : connexion perdue")
        if not youtube.is_configured() and not kick.is_configured():
            pill.set_platform(PLATFORM_NONE)
        _refresh_status()
        # Auto-reconnect après 30 s
        QTimer.singleShot(30_000, _try_reconnect_twitch)

    def _try_reconnect_twitch():
        if not twitch_auth.is_connected:
            return
        log.info("Twitch : tentative de reconnexion…")

        def _worker():
            if twitch_auth.ensure_valid():
                QTimer.singleShot(0, twitch.start)
            else:
                QTimer.singleShot(60_000, _try_reconnect_twitch)

        threading.Thread(target=_worker, daemon=True).start()

    twitch.data_updated.connect(on_twitch_data)
    twitch.connection_lost.connect(on_twitch_lost)

    # ── YouTube callbacks ────────────────────────────────────────────
    def on_youtube_data(data):
        pill.update_live_data(PLATFORM_YOUTUBE, data.viewers_fmt(), data.uptime_fmt(),
                              "", data.is_live)
        if not twitch_auth.is_connected:
            pill.set_platform(PLATFORM_YOUTUBE)
        _refresh_status()

    def on_youtube_lost():
        log.warning("YouTube : connexion perdue")
        if not twitch_auth.is_connected and not kick.is_configured():
            pill.set_platform(PLATFORM_NONE)
        _refresh_status()

    youtube.data_updated.connect(on_youtube_data)
    youtube.connection_lost.connect(on_youtube_lost)

    # ── Kick callbacks ───────────────────────────────────────────────
    def on_kick_data(data):
        pill.update_live_data(
            PLATFORM_KICK, data.viewers_fmt(), "--", "", data.is_live,
        )
        if not twitch_auth.is_connected and not youtube.is_configured():
            pill.set_platform(PLATFORM_KICK)
        _refresh_status()

    def on_kick_lost():
        log.warning("Kick : connexion perdue")
        if not twitch_auth.is_connected and not youtube.is_configured():
            pill.set_platform(PLATFORM_NONE)
        _refresh_status()

    kick.data_updated.connect(on_kick_data)
    kick.connection_lost.connect(on_kick_lost)

    menu.aboutToShow.connect(_refresh_status)

    # ── Actions Twitch ───────────────────────────────────────────────
    def connect_twitch():
        dlg = TwitchConnectDialog()
        if dlg.exec() != TwitchConnectDialog.DialogCode.Accepted:
            return

        def _on_success():
            name = config.get("twitch_display_name") or config.get("twitch_username") or "Twitch"
            tray.showMessage("GamePill", f"✅ Twitch connecté — {name} !",
                             QSystemTrayIcon.MessageIcon.Information, 3000)
            pill.set_platform(PLATFORM_TWITCH)
            twitch.start()
            _refresh_status()

        def _on_failure():
            QMessageBox.warning(None, "GamePill",
                                "Connexion Twitch échouée.\nRéessaie dans quelques secondes.")
            _refresh_status()

        twitch_auth.start_oauth(on_success=_on_success, on_failure=_on_failure)
        tray.showMessage("GamePill", "Navigateur ouvert — autorise l'accès Twitch.",
                         QSystemTrayIcon.MessageIcon.Information, 5000)

    def disconnect_twitch():
        twitch.stop()
        eventsub.stop()
        twitch_auth.disconnect()
        if not youtube.is_configured() and not kick.is_configured():
            pill.set_platform(PLATFORM_NONE)
        pill.reset_live_data()
        _refresh_status()
        tray.showMessage("GamePill", "Twitch déconnecté.",
                         QSystemTrayIcon.MessageIcon.Information, 2000)

    act_connect_tw.triggered.connect(connect_twitch)
    act_disconnect_tw.triggered.connect(disconnect_twitch)

    # ── Actions YouTube ──────────────────────────────────────────────
    def connect_youtube():
        if not YOUTUBE_API_KEY:
            QMessageBox.information(None, "GamePill",
                                    "Ajoute YOUTUBE_API_KEY dans core/constants.py.\n\n"
                                    "console.cloud.google.com → YouTube Data API v3\n"
                                    "→ Credentials → Clé API")
            return

        dlg = YouTubeConnectDialog()
        if dlg.exec() != YouTubeConnectDialog.DialogCode.Accepted:
            return

        handle = dlg.handle_value

        def _resolve():
            result = resolve_channel(handle)
            if result:
                channel_id, display_name = result
                config.set("youtube_channel_id",  channel_id)
                config.set("youtube_display_name", display_name)
                log.info("YouTube : %s (%s)", display_name, channel_id)
                QTimer.singleShot(0, _after_resolve_ok)
            else:
                QTimer.singleShot(0, _after_resolve_fail)

        def _after_resolve_ok():
            name = config.get("youtube_display_name") or handle
            tray.showMessage("GamePill", f"✅ YouTube connecté — {name} !",
                             QSystemTrayIcon.MessageIcon.Information, 3000)
            if not twitch_auth.is_connected:
                pill.set_platform(PLATFORM_YOUTUBE)
            youtube.start()
            _refresh_status()

        def _after_resolve_fail():
            QMessageBox.warning(None, "GamePill",
                                f"Handle '@{handle}' introuvable.\n"
                                "Vérifie le nom ou ta clé API YouTube.")

        tray.showMessage("GamePill", f"Recherche de @{handle}…",
                         QSystemTrayIcon.MessageIcon.Information, 2000)
        threading.Thread(target=_resolve, daemon=True).start()

    def disconnect_youtube():
        youtube.stop()
        config.set("youtube_channel_id",  None)
        config.set("youtube_display_name", None)
        if not twitch_auth.is_connected and not kick.is_configured():
            pill.set_platform(PLATFORM_NONE)
        pill.reset_live_data()
        _refresh_status()
        tray.showMessage("GamePill", "YouTube déconnecté.",
                         QSystemTrayIcon.MessageIcon.Information, 2000)

    act_connect_yt.triggered.connect(connect_youtube)
    act_disconnect_yt.triggered.connect(disconnect_youtube)

    # ── Actions Kick ─────────────────────────────────────────────────
    def connect_kick():
        slug, ok = QInputDialog.getText(
            None, "GamePill — Kick",
            "Entre le slug de ta chaîne Kick :\n(ex : sm0ke → kick.com/sm0ke)",
            text=config.get("kick_slug", ""),
        )
        if not ok or not slug.strip():
            return
        slug = slug.strip().lower()
        config.set("kick_slug", slug)
        kick.stop()
        kick.start()
        tray.showMessage("GamePill", f"✅ Kick configuré — {slug}",
                         QSystemTrayIcon.MessageIcon.Information, 3000)
        _refresh_status()

    def disconnect_kick():
        kick.stop()
        config.set("kick_slug", None)
        if not twitch_auth.is_connected and not youtube.is_configured():
            pill.set_platform(PLATFORM_NONE)
        pill.reset_live_data()
        _refresh_status()
        tray.showMessage("GamePill", "Kick déconnecté.",
                         QSystemTrayIcon.MessageIcon.Information, 2000)

    act_connect_kick.triggered.connect(connect_kick)
    act_disconnect_kick.triggered.connect(disconnect_kick)

    # ── Actions Riot ─────────────────────────────────────────────────
    def config_riot():
        regions = ["EUW", "EUNE", "NA", "KR", "BR", "TR", "RU", "JP", "OCE"]

        existing = ""
        if config.get("riot_game_name"):
            existing = f"{config.get('riot_game_name', '')}#{config.get('riot_tag_line', '')}"

        riot_id, ok = QInputDialog.getText(
            None, "GamePill — Riot ID",
            "Entre ton Riot ID (format: NomJoueur#TAG)\nEx: sm0ke#EUW",
            text=existing,
        )
        if not ok or not riot_id:
            return
        if "#" not in riot_id:
            QMessageBox.warning(None, "GamePill", "Format invalide. Utilise NomJoueur#TAG")
            return

        name, tag = riot_id.split("#", 1)
        region, ok2 = QInputDialog.getItem(
            None, "GamePill — Région", "Sélectionne ta région :", regions, 0, False
        )
        if not ok2:
            return

        config.set("riot_game_name", name.strip())
        config.set("riot_tag_line",  tag.strip())
        config.set("riot_region",    region)
        riot._puuid_cache.clear()
        log.info("Riot configuré : %s#%s (%s)", name, tag, region)
        tray.showMessage("GamePill", f"✅ Riot configuré — {name}#{tag} ({region})",
                         QSystemTrayIcon.MessageIcon.Information, 3000)
        if detector.current_theme().name != "default":
            riot.start()

    def clear_riot():
        config.set("riot_game_name", None)
        config.set("riot_tag_line",  None)
        config.set("riot_region",    None)
        riot.stop()
        riot._puuid_cache.clear()
        tray.showMessage("GamePill", "Config Riot effacée.",
                         QSystemTrayIcon.MessageIcon.Information, 2000)

    act_config_riot.triggered.connect(config_riot)
    act_clear_riot.triggered.connect(clear_riot)

    # ── Actions CS2 GSI ──────────────────────────────────────────────
    def cs2_toggle():
        if cs2_gsi.is_running:
            cs2_gsi.stop()
            act_cs2_start.setText("  Activer GSI")
            act_cs2_start.setIcon(_dot_icon("#F5A623"))
        else:
            cs2_gsi.start()
            if cs2_gsi.is_running:
                act_cs2_start.setText("  Désactiver GSI")
                act_cs2_start.setIcon(_dot_icon("#34c759"))

    def cs2_install_cfg():
        cfg_dir = (
            r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\Counter-Strike Global Offensive\game\csgo\cfg"
        )
        cfg_content = (
            '"GamePill"\n'
            '{\n'
            '    "uri"       "http://127.0.0.1:3001"\n'
            '    "timeout"   "5.0"\n'
            '    "buffer"    "0.1"\n'
            '    "throttle"  "0.5"\n'
            '    "heartbeat" "10.0"\n'
            '    "auth"      { "token" "gamepill_secret" }\n'
            '    "output"    { "precision_time" "3" "realtime" "1" }\n'
            '    "data"\n'
            '    {\n'
            '        "provider"           "1"\n'
            '        "round"              "1"\n'
            '        "player_id"          "1"\n'
            '        "player_state"       "1"\n'
            '        "player_match_stats" "1"\n'
            '    }\n'
            '}\n'
        )
        dest = os.path.join(cfg_dir, "gamepill.cfg")
        try:
            os.makedirs(cfg_dir, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(cfg_content)
            log.info("CS2 cfg installé : %s", dest)
            QMessageBox.information(None, "GamePill — CS2 GSI",
                                    f"✅ Fichier installé :\n{dest}\n\n"
                                    "Relance CS2 pour activer les stats temps réel.")
        except PermissionError:
            QMessageBox.warning(None, "GamePill",
                                "Permission refusée.\n"
                                "Lance GamePill en tant qu'administrateur\n"
                                "ou copie manuellement le fichier gamepill.cfg.")
        except Exception as e:
            QMessageBox.warning(None, "GamePill", f"Erreur : {e}")

    act_cs2_start.triggered.connect(cs2_toggle)
    act_cs2_install.triggered.connect(cs2_install_cfg)

    # ── Démarrage ────────────────────────────────────────────────────
    pill.show()
    detector.start()

    if twitch_auth.is_connected:
        pill.set_platform(PLATFORM_TWITCH)
        _refresh_status()

        def _restore_twitch():
            if twitch_auth.ensure_valid():
                QTimer.singleShot(0, twitch.start)
                QTimer.singleShot(500, _start_eventsub)
                QTimer.singleShot(0, _refresh_status)
            else:
                QTimer.singleShot(0, lambda: pill.set_platform(PLATFORM_NONE)
                                  if not youtube.is_configured() and not kick.is_configured()
                                  else None)
                QTimer.singleShot(0, _refresh_status)

        threading.Thread(target=_restore_twitch, daemon=True).start()

    if youtube.is_configured():
        if not twitch_auth.is_connected:
            pill.set_platform(PLATFORM_YOUTUBE)
        _refresh_status()
        QTimer.singleShot(500, youtube.start)

    if kick.is_configured():
        if not twitch_auth.is_connected and not youtube.is_configured():
            pill.set_platform(PLATFORM_KICK)
        _refresh_status()
        QTimer.singleShot(700, kick.start)

    tray.setContextMenu(menu)
    tray.show()

    log.info("GamePill prêt — systray actif")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
