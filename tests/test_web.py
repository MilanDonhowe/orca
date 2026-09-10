from pathlib import Path

from orca.config import RulesetStore
from orca.web import create_app


class Engine:
    def __init__(self): self.paused = False
    def snapshot(self): return {"running": True, "paused": self.paused, "phase": "DELAY", "history": []}
    def set_paused(self, value): self.paused = value


def test_api_rules_and_control(tmp_path: Path):
    engine = Engine(); store = RulesetStore(tmp_path / "rules.json")
    client = create_app(engine, store).test_client()
    assert client.get("/api/status").status_code == 200
    assert client.post("/api/control", json={"action": "pause"}).get_json()["paused"] is True
    data = client.get("/api/ruleset").get_json()
    data["control"]["scanrate"] = 250
    assert client.put("/api/ruleset", json=data).status_code == 200
    assert store.load().scanrate == 250


def test_rule_test_endpoint(tmp_path: Path):
    client = create_app(Engine(), RulesetStore(tmp_path / "rules.json")).test_client()
    result = client.post("/api/test", json={"text": "label 20"}).get_json()
    assert result["matches"][0]["topic"] == "twenty"

