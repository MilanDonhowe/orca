import pytest

from orca.models import Ruleset
from orca.rules import Classifier


def ruleset(mode="single"):
    return Ruleset.from_dict({
        "version": 1,
        "control": {"scanrate": 500, "ruletype": mode},
        "rules": [
            {"label": "low", "topic": "low", "priority": 20, "type": "TEXT", "content": "orca"},
            {"label": "high", "topic": "high", "priority": 5, "type": "REGEX", "content": r"\b20\b"},
        ],
    })


def test_single_returns_highest_priority_match():
    assert [m["label"] for m in Classifier(ruleset()).classify("ORCA item 20")] == ["high"]


def test_multi_returns_all_matches_in_priority_order():
    assert [m["label"] for m in Classifier(ruleset("multi")).classify("ORCA item 20")] == ["high", "low"]


@pytest.mark.parametrize("field,value", [("scanrate", 0), ("ruletype", "many")])
def test_invalid_controls(field, value):
    payload = ruleset().to_dict(); payload["control"][field] = value
    with pytest.raises(ValueError):
        Ruleset.from_dict(payload)


def test_invalid_regex_is_reported():
    payload = ruleset().to_dict(); payload["rules"][0].update(type="REGEX", content="[")
    with pytest.raises(ValueError, match="Invalid regex"):
        Classifier(Ruleset.from_dict(payload))

