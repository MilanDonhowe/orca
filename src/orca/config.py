from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
import tomllib
from orca.models import Ruleset

DEFAULT_RULESET = {
    "version": 1,
    "control": {"ruletype": "single"},
    "rules": [
        {"label": "Example twenty", "topic": "twenty", "priority": 10, "type": "TEXT", "content": "20"}
    ],
}


class RulesetStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        if not self.path.exists():
            self.save(Ruleset.from_dict(DEFAULT_RULESET))

    def load(self) -> Ruleset:
        with self._lock:
            return Ruleset.from_dict(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, ruleset: Ruleset) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(self.path.suffix + ".tmp")
            temp.write_text(json.dumps(ruleset.to_dict(), indent=2) + "\n", encoding="utf-8")
            temp.replace(self.path)


@dataclass(frozen=True)
class MQTTSettings:
    enabled: bool = False
    host: str = "localhost"
    port: int = 1883
    tls: bool = False
    username: str = ""
    password: str = ""
    client_id: str = ""
    keepalive: int = 60

    @classmethod
    def from_dict(cls, value: dict) -> "MQTTSettings":
        if not isinstance(value, dict):
            raise ValueError("MQTT configuration must be an object")
        host = str(value.get("host", "localhost")).strip()
        if not host:
            raise ValueError("Broker host is required")
        port, keepalive = int(value.get("port", 1883)), int(value.get("keepalive", 60))
        if not 1 <= port <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        if not 1 <= keepalive <= 65535:
            raise ValueError("Keepalive must be between 1 and 65535 seconds")
        return cls(bool(value.get("enabled", False)), host, port, bool(value.get("tls", False)),
                   str(value.get("username", "")), str(value.get("password", "")),
                   str(value.get("client_id", "")).strip(), keepalive)

    def public_dict(self) -> dict:
        result = asdict(self)
        result["password"] = ""
        result["has_password"] = bool(self.password)
        return result


@dataclass(frozen=True)
class AppSettings:
    scan_rate: int = 1000
    web_port: int = 8080
    camera: str | None = None
    mqtt: MQTTSettings = MQTTSettings()

    @classmethod
    def from_dict(cls, value: dict) -> "AppSettings":
        if not isinstance(value, dict):
            raise ValueError("Configuration must be a TOML table")
        runtime, web = value.get("runtime", {}), value.get("web", {})
        scan_rate = int(runtime.get("scan_rate", 1000))
        camera_value = runtime.get("camera")
        camera = str(camera_value).strip() if camera_value is not None else None
        web_port = int(web.get("port", 8080))
        if scan_rate <= 0:
            raise ValueError("runtime.scan_rate must be a positive integer")
        if not 1 <= web_port <= 65535:
            raise ValueError("web.port must be between 1 and 65535")
        camera = camera or None
        return cls(scan_rate, web_port, camera, MQTTSettings.from_dict(value.get("mqtt", {})))


class ConfigStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.RLock()

    def load(self) -> AppSettings:
        with self._lock:
            if not self.path.exists():
                settings = AppSettings()
                self.save(settings)
                return settings
            return AppSettings.from_dict(tomllib.loads(self.path.read_text(encoding="utf-8")))

    def save(self, settings: AppSettings) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(self.path.suffix + ".tmp")
            mqtt = settings.mqtt
            quote = json.dumps
            camera_line = f"camera = {quote(settings.camera)}\n" if settings.camera is not None else ""
            content = (
                f"[runtime]\nscan_rate = {settings.scan_rate}\n{camera_line}\n"
                f"[web]\nport = {settings.web_port}\n\n"
                f"[mqtt]\nenabled = {str(mqtt.enabled).lower()}\nhost = {quote(mqtt.host)}\n"
                f"port = {mqtt.port}\ntls = {str(mqtt.tls).lower()}\nusername = {quote(mqtt.username)}\n"
                f"password = {quote(mqtt.password)}\nclient_id = {quote(mqtt.client_id)}\nkeepalive = {mqtt.keepalive}\n"
            )
            temp.write_text(content, encoding="utf-8")
            temp.replace(self.path)

    def save_mqtt(self, mqtt: MQTTSettings) -> AppSettings:
        current = self.load()
        updated = AppSettings(current.scan_rate, current.web_port, current.camera, mqtt)
        self.save(updated)
        return updated

    def save_camera(self, camera: str | None) -> AppSettings:
        current = self.load()
        normalized = str(camera).strip() if camera is not None else None
        updated = AppSettings(current.scan_rate, current.web_port, normalized or None, current.mqtt)
        self.save(updated)
        return updated
