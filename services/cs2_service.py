"""
CS2 Game State Integration — serveur HTTP local sur :3001.

CS2 envoie des POST JSON à chaque changement d'état de jeu.
Pour activer : copier le fichier gamepill.cfg dans :
  C:\\Program Files (x86)\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\game\\csgo\\cfg\\

Contenu de gamepill.cfg :
  "GamePill"
  {
      "uri"       "http://127.0.0.1:3001"
      "timeout"   "5.0"
      "buffer"    "0.1"
      "throttle"  "0.5"
      "heartbeat" "10.0"
      "auth"      { "token" "gamepill_secret" }
      "output"    { "precision_time" "3" "realtime" "1" }
      "data"
      {
          "provider"           "1"
          "round"              "1"
          "player_id"          "1"
          "player_state"       "1"
          "player_match_stats" "1"
      }
  }
"""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

import core.logger as _log_mod

log = _log_mod.get("cs2gsi")

GSI_PORT = 3001


class _Handler(BaseHTTPRequestHandler):
    callback = None   # set by CS2GSI before starting

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body.decode("utf-8", errors="replace"))
            if callable(self.callback):
                self.callback(data)
        except Exception as e:
            log.debug("Handler POST erreur : %s", e)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_):
        pass  # supprime les logs de requête


def _port_free(port: int) -> bool:
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


class CS2GSI(QObject):
    """Reçoit les POST de CS2 GSI et expose les stats en temps réel."""

    stats_updated = pyqtSignal(dict)   # {"k":int, "d":int, "a":int, "hp":int, ...}
    started       = pyqtSignal()
    stopped       = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server:  HTTPServer | None = None
        self._thread:  threading.Thread  | None = None
        self._running  = False
        self._last_kda: dict = {}

    # ── API publique ──────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        if not _port_free(GSI_PORT):
            log.warning("CS2 GSI : port %d déjà utilisé — service désactivé", GSI_PORT)
            return
        _Handler.callback = self._on_gsi_data
        try:
            self._server  = HTTPServer(("127.0.0.1", GSI_PORT), _Handler)
            self._running = True
            self._thread  = threading.Thread(
                target=self._server.serve_forever, daemon=True, name="cs2-gsi"
            )
            self._thread.start()
            log.info("CS2 GSI démarré sur le port %d", GSI_PORT)
            QTimer.singleShot(0, self.started.emit)
        except OSError as e:
            log.error("CS2 GSI impossible de démarrer : %s", e)

    def stop(self):
        if self._server and self._running:
            self._server.shutdown()
            self._running = False
            log.info("CS2 GSI arrêté")
            QTimer.singleShot(0, self.stopped.emit)

    @property
    def is_running(self) -> bool:
        return self._running

    def last_kda(self) -> dict:
        return dict(self._last_kda)

    # ── Parsing des données GSI ───────────────────────────────────────

    def _on_gsi_data(self, data: dict):
        try:
            player      = data.get("player", {})
            match_stats = player.get("match_stats", {})
            state       = player.get("state", {})
            round_data  = data.get("round", {})

            kda = {
                "k":     match_stats.get("kills",     "--"),
                "d":     match_stats.get("deaths",    "--"),
                "a":     match_stats.get("assists",   "--"),
                "score": match_stats.get("score",     "--"),
                "hs":    match_stats.get("headshots", "--"),
                "hp":    state.get("health",          "--"),
                "armor": state.get("armor",           "--"),
                "money": state.get("money",           "--"),
                "phase": round_data.get("phase",      ""),
                "agent": "CS2",
                "rank":  "",
            }

            # Ne réémettre que si les stats changent réellement
            if kda != self._last_kda:
                self._last_kda = kda
                snapshot = dict(kda)
                QTimer.singleShot(0, lambda: self.stats_updated.emit(snapshot))

        except Exception as e:
            log.debug("CS2 GSI parsing erreur : %s", e)
