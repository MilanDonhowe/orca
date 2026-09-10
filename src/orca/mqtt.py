from __future__ import annotations

import json
import threading
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from orca.config import MQTTSettings


class MQTTPublisher:
    def __init__(self, connection: str | None = None, settings: MQTTSettings | None = None):
        self.settings = settings or self._from_url(connection)
        self.client: mqtt.Client | None = None
        self.connected = False
        self._lock = threading.RLock()

    @staticmethod
    def _from_url(connection: str | None) -> MQTTSettings:
        if not connection:
            return MQTTSettings()
        parsed = urlparse(connection if "://" in connection else "mqtt://" + connection)
        return MQTTSettings(True, parsed.hostname or "localhost", parsed.port or (8883 if parsed.scheme == "mqtts" else 1883),
                            parsed.scheme == "mqtts", parsed.username or "", parsed.password or "")

    def start(self) -> None:
        with self._lock:
            if not self.settings.enabled:
                return
            cfg = self.settings
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg.client_id)
            if cfg.username:
                self.client.username_pw_set(cfg.username, cfg.password or None)
            if cfg.tls:
                self.client.tls_set()
            self.client.on_connect = lambda client, userdata, flags, reason_code, properties: setattr(self, "connected", reason_code == 0)
            self.client.on_disconnect = lambda client, userdata, flags, reason_code, properties: setattr(self, "connected", False)
            self.client.connect_async(cfg.host, cfg.port, cfg.keepalive)
            self.client.loop_start()

    def configure(self, settings: MQTTSettings) -> None:
        self.stop()
        self.settings = settings
        self.start()

    def publish_result(self, payload: dict, matches: list[dict]) -> None:
        if not self.client:
            return
        body = json.dumps(payload, separators=(",", ":"))
        self.client.publish("orca/results", body)
        for match in matches:
            self.client.publish(f"orca/results/{match['topic']}", body)

    def publish_diagnostic(self, payload: dict) -> None:
        if self.client:
            self.client.publish("orca/diagnostic", json.dumps(payload, separators=(",", ":")))

    def stop(self) -> None:
        with self._lock:
            client, self.client = self.client, None
            self.connected = False
            if client:
                client.disconnect()
                client.loop_stop()
