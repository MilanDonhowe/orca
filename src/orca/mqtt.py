from __future__ import annotations

import json
from urllib.parse import urlparse

import paho.mqtt.client as mqtt


class MQTTPublisher:
    def __init__(self, connection: str | None):
        self.connection = connection
        self.client: mqtt.Client | None = None
        self.connected = False

    def start(self) -> None:
        if not self.connection:
            return
        parsed = urlparse(self.connection if "://" in self.connection else "mqtt://" + self.connection)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if parsed.username:
            self.client.username_pw_set(parsed.username, parsed.password)
        if parsed.scheme == "mqtts":
            self.client.tls_set()
        self.client.on_connect = lambda client, userdata, flags, reason_code, properties: setattr(self, "connected", reason_code == 0)
        self.client.on_disconnect = lambda client, userdata, flags, reason_code, properties: setattr(self, "connected", False)
        self.client.connect_async(parsed.hostname or "localhost", parsed.port or (8883 if parsed.scheme == "mqtts" else 1883))
        self.client.loop_start()

    def publish_result(self, payload: dict, matches: list[dict]) -> None:
        if not self.client:
            return
        body = json.dumps(payload, separators=(",", ":"))
        self.client.publish("orca.results", body)
        for match in matches:
            self.client.publish(f"orca.results.{match['topic']}", body)

    def publish_diagnostic(self, payload: dict) -> None:
        if self.client:
            self.client.publish("orca.diagnostic", json.dumps(payload, separators=(",", ":")))

    def stop(self) -> None:
        if self.client:
            self.client.disconnect()
            self.client.loop_stop()

