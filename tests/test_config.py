from pathlib import Path

import pytest

from orca.config import AppSettings, ConfigStore, MQTTSettings


def test_config_store_round_trip(tmp_path: Path):
    store = ConfigStore(tmp_path / "config.toml")
    expected = AppSettings(250, 9090, "2", MQTTSettings(True, "broker.local", 8883, True, "orca", "secret"))
    store.save(expected)

    assert store.load() == expected
    assert "[runtime]" in store.path.read_text(encoding="utf-8")
    assert "scan_rate = 250" in store.path.read_text(encoding="utf-8")
    assert 'camera = "2"' in store.path.read_text(encoding="utf-8")


@pytest.mark.parametrize("value", [
    {"runtime": {"scan_rate": 0}},
    {"web": {"port": 70000}},
])
def test_invalid_application_settings(value):
    with pytest.raises(ValueError):
        AppSettings.from_dict(value)


def test_camera_is_optional_and_blank_removes_it(tmp_path: Path):
    store = ConfigStore(tmp_path / "config.toml")
    assert store.load().camera is None

    store.save_camera("demo")
    assert store.load().camera == "demo"

    store.save_camera("  ")
    assert store.load().camera is None
    assert "camera =" not in store.path.read_text(encoding="utf-8")
