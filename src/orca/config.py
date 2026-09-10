from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import Ruleset

DEFAULT_RULESET = {
    "version": 1,
    "control": {"scanrate": 1000, "ruletype": "single"},
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

