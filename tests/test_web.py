from pathlib import Path

from fastapi.testclient import TestClient

from orca.config import ConfigStore, RulesetStore
from orca.web import create_app


class Engine:
    def __init__(self): self.paused = False
    def snapshot(self): return {"running": True, "paused": self.paused, "phase": "DELAY", "history": []}
    def set_paused(self, value): self.paused = value
    def configure_mqtt(self, settings): self.mqtt_settings = settings


def test_api_rules_and_control(tmp_path: Path):
    engine = Engine(); store = RulesetStore(tmp_path / "rules.json")
    client = TestClient(create_app(engine, store))
    assert client.get("/api/status").status_code == 200
    assert client.post("/api/control", json={"action": "pause"}).json()["paused"] is True
    data = client.get("/api/ruleset").json()
    assert client.put("/api/ruleset", json=data).status_code == 200
    assert store.load().ruletype == "single"


def test_rule_test_endpoint(tmp_path: Path):
    client = TestClient(create_app(Engine(), RulesetStore(tmp_path / "rules.json")))
    result = client.post("/api/test", json={"text": "label 20"}).json()
    assert result["matches"][0]["topic"] == "twenty"


def test_index_and_status_websocket(tmp_path: Path):
    client = TestClient(create_app(Engine(), RulesetStore(tmp_path / "rules.json")))
    response = client.get("/")
    assert response.status_code == 200
    assert "/static/app.js" in response.text
    assert 'href="/docs"' in response.text

    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "SwaggerUIBundle" in docs.text
    assert "ORCA API documentation" in docs.text
    assert "/static/openapi.yaml" in docs.text

    specification = client.get("/static/openapi.yaml")
    assert specification.status_code == 200
    assert "openapi: 3.0.3" in specification.text
    assert "  /api/ruleset:" in specification.text
    assert "  /api/mqtt:" in specification.text
    assert "  /api/control:" in specification.text

    with client.websocket_connect("/ws/status") as websocket:
        assert websocket.receive_json()["phase"] == "DELAY"


def test_mqtt_configuration_is_saved_and_password_is_hidden(tmp_path: Path):
    engine = Engine()
    config = ConfigStore(tmp_path / "config.toml")
    client = TestClient(create_app(engine, RulesetStore(tmp_path / "rules.json"), config))
    response = client.put("/api/mqtt", json={
        "enabled": True, "host": "broker.local", "port": 8883, "tls": True,
        "username": "orca", "password": "secret", "client_id": "line-one", "keepalive": 30,
    })
    assert response.status_code == 200
    assert response.json()["password"] == ""
    assert response.json()["has_password"] is True
    assert engine.mqtt_settings.host == "broker.local"
    assert client.get("/api/mqtt").json()["password"] == ""
    assert config.load().mqtt.password == "secret"
    assert config.load().scan_rate == 1000


def test_camera_configuration_can_be_set_and_cleared(tmp_path: Path):
    config = ConfigStore(tmp_path / "config.toml")
    client = TestClient(create_app(Engine(), RulesetStore(tmp_path / "rules.json"), config))

    assert client.get("/api/config").json() == {"camera": "", "scan_rate": 1000}
    assert client.put("/api/config", json={"camera": "2", "scan_rate": 250}).json() == {"camera": "2", "scan_rate": 250}
    assert config.load().camera == "2"
    assert config.load().scan_rate == 250
    assert client.put("/api/config", json={"camera": ""}).json() == {"camera": "", "scan_rate": 250}
    assert config.load().camera is None

    response = client.put("/api/config", json={"scan_rate": 0})
    assert response.status_code == 400
    assert "positive integer" in response.json()["error"]
