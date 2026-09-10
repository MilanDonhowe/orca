import pytest

from orca.models import Ruleset
from orca.rules import Classifier


def ruleset(mode="single"):
    return Ruleset.from_dict({
        "version": 1,
        "control": {"ruletype": mode},
        "rules": [
            {"label": "low", "topic": "low", "priority": 20, "type": "TEXT", "content": "orca"},
            {"label": "high", "topic": "high", "priority": 5, "type": "REGEX", "content": r"\b20\b"},
        ],
    })


def test_single_returns_highest_priority_match():
    assert [m["label"] for m in Classifier(ruleset()).classify("ORCA item 20")] == ["high"]


def test_multi_returns_all_matches_in_priority_order():
    assert [m["label"] for m in Classifier(ruleset("multi")).classify("ORCA item 20")] == ["high", "low"]


def test_invalid_match_mode():
    payload = ruleset().to_dict(); payload["control"]["ruletype"] = "many"
    with pytest.raises(ValueError):
        Ruleset.from_dict(payload)


def test_legacy_scanrate_is_removed_when_serialized():
    payload = ruleset().to_dict(); payload["control"]["scanrate"] = 250
    assert "scanrate" not in Ruleset.from_dict(payload).to_dict()["control"]


def test_invalid_regex_is_reported():
    payload = ruleset().to_dict(); payload["rules"][0].update(type="REGEX", content="[")
    with pytest.raises(ValueError, match="Invalid regex"):
        Classifier(Ruleset.from_dict(payload))
