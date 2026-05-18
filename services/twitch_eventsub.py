"""
Twitch EventSub — transport WebSocket.
Écoute les follows, subs, raids en temps réel sans polling.
"""

import json
import threading

import httpx
import websocket
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

import core.logger as _log_mod
log = _log_mod.get("eventsub")

EVENTSUB_WS  = "wss://eventsub.twitch.tv/ws"
HELIX_SUBS   = "https://api.twitch.tv/helix/eventsub/subscriptions"


class TwitchEventSub(QObject):
    follow_received = pyqtSignal(str)        # follower_name
    sub_received    = pyqtSignal(str, bool)  # subscriber_name, is_gift
    raid_received   = pyqtSignal(str, int)   # from_broadcaster_name, viewer_count

    def __init__(self, auth, parent=None):
        super().__init__(parent)
        self._auth    = auth
        self._ws      = None
        self._running = False
        self._thread  = None
        self._broadcaster_id = ""
        self._user_id        = ""

    def start(self, broadcaster_id: str, user_id: str):
        if self._running:
            return
        self._broadcaster_id = broadcaster_id
        self._user_id        = user_id
        self._running        = True
        self._thread = threading.Thread(target=self._connect_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    # ── Boucle de connexion avec reconnexion ─────────────────────────

    def _connect_loop(self):
        url = EVENTSUB_WS
        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self._ws.run_forever(
                    ping_interval=30,
                    ping_timeout=10,
                )
            except Exception as e:
                log.error("Erreur WebSocket : %s", e)
            if self._running:
                import time; time.sleep(5)  # reconnexion après 5s

    def _on_open(self, ws):
        log.info("Connecté")

    def _on_close(self, ws, code, msg):
        if self._running:
            log.warning("Connexion fermée (%s) — reconnexion…", code)

    def _on_error(self, ws, error):
        log.error("Erreur : %s", error)

    # ── Traitement des messages ───────────────────────────────────────

    def _on_message(self, ws, raw: str):
        try:
            data     = json.loads(raw)
            metadata = data.get("metadata", {})
            msg_type = metadata.get("message_type", "")
            payload  = data.get("payload", {})

            if msg_type == "session_welcome":
                session_id = payload["session"]["id"]
                threading.Thread(
                    target=self._subscribe,
                    args=(session_id,),
                    daemon=True,
                ).start()

            elif msg_type == "session_reconnect":
                reconnect_url = payload["session"].get("reconnect_url", EVENTSUB_WS)
                log.info("Reconnexion demandée → %s", reconnect_url)
                # La boucle _connect_loop se reconnectera automatiquement
                ws.close()

            elif msg_type == "notification":
                self._handle_event(
                    metadata.get("subscription_type", ""),
                    payload.get("event", {}),
                )

        except Exception as e:
            log.error("Erreur parsing message : %s", e)

    def _handle_event(self, event_type: str, event: dict):
        if event_type == "channel.follow":
            name = event.get("user_name", "?")
            QTimer.singleShot(0, lambda: self.follow_received.emit(name))

        elif event_type == "channel.subscribe":
            name = event.get("user_name", "?")
            QTimer.singleShot(0, lambda: self.sub_received.emit(name, False))

        elif event_type == "channel.subscription.gift":
            name = event.get("user_name", "?")
            QTimer.singleShot(0, lambda: self.sub_received.emit(name, True))

        elif event_type == "channel.raid":
            name    = event.get("from_broadcaster_user_name", "?")
            viewers = int(event.get("viewers", 0))
            QTimer.singleShot(0, lambda: self.raid_received.emit(name, viewers))

    # ── Souscriptions Helix ───────────────────────────────────────────

    def _subscribe(self, session_id: str):
        token = self._auth.get_access_token()
        if not token:
            log.warning("Pas de token — impossible de souscrire")
            return

        headers = {
            "Authorization":  f"Bearer {token}",
            "Client-Id":      self._auth.client_id,
            "Content-Type":   "application/json",
        }
        transport = {"method": "websocket", "session_id": session_id}
        bid, uid  = self._broadcaster_id, self._user_id

        subscriptions = [
            {
                "type": "channel.follow", "version": "2",
                "condition": {"broadcaster_user_id": bid, "moderator_user_id": uid},
                "transport": transport,
            },
            {
                "type": "channel.subscribe", "version": "1",
                "condition": {"broadcaster_user_id": bid},
                "transport": transport,
            },
            {
                "type": "channel.subscription.gift", "version": "1",
                "condition": {"broadcaster_user_id": bid},
                "transport": transport,
            },
            {
                "type": "channel.raid", "version": "1",
                "condition": {"to_broadcaster_user_id": bid},
                "transport": transport,
            },
        ]

        for sub in subscriptions:
            try:
                r = httpx.post(HELIX_SUBS, json=sub, headers=headers,
                               timeout=8)
                if r.status_code not in (200, 202):
                    log.warning("Souscription %s échouée : HTTP %d — %s",
                                sub["type"], r.status_code, r.text[:200])
            except Exception as e:
                log.error("Erreur souscription %s : %s", sub["type"], e)
