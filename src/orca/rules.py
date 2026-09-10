from __future__ import annotations

import re

from orca.models import Rule, Ruleset


class Classifier:
    def __init__(self, ruleset: Ruleset):
        self.ruleset = ruleset
        self._compiled: dict[Rule, re.Pattern[str]] = {}
        for rule in ruleset.rules:
            if rule.type == "REGEX":
                try:
                    self._compiled[rule] = re.compile(rule.content, re.IGNORECASE | re.MULTILINE)
                except re.error as exc:
                    raise ValueError(f"Invalid regex for '{rule.label}': {exc}") from exc

    def classify(self, text: str) -> list[dict[str, object]]:
        matches: list[dict[str, object]] = []
        for rule in sorted(self.ruleset.rules, key=lambda item: item.priority):
            hit = bool(self._compiled[rule].search(text)) if rule.type == "REGEX" else rule.content.casefold() in text.casefold()
            if hit:
                matches.append({"label": rule.label, "topic": rule.topic, "priority": rule.priority})
                if self.ruleset.ruletype == "single":
                    break
        return matches

