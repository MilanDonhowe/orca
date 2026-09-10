from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Phase(str, Enum):
    PAUSED = "PAUSED"
    IMAGE_CAPTURE = "IMAGE CAPTURE"
    OCR_MODEL = "OCR MODEL"
    RULES_CLASSIFIER = "RULES CLASSIFIER"
    MQTT_BROADCAST = "MQTT BROADCAST"
    DELAY = "DELAY"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Rule:
    label: str
    topic: str
    priority: int
    type: str
    content: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Rule":
        rule_type = str(value.get("type", "TEXT")).upper()
        rule = cls(
            label=str(value.get("label", "")).strip(),
            topic=str(value.get("topic", "")).strip(),
            priority=int(value.get("priority", 100)),
            type=rule_type,
            content=str(value.get("content", "")),
        )
        if not rule.label or not rule.content:
            raise ValueError("Each rule requires a label and content")
        if not rule.topic or not rule.topic.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Rule topic must be one word (letters, digits, '-' or '_')")
        if rule.type not in {"TEXT", "REGEX"}:
            raise ValueError("Rule type must be TEXT or REGEX")
        return rule


@dataclass(frozen=True)
class Ruleset:
    version: int = 1
    ruletype: str = "single"
    rules: tuple[Rule, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Ruleset":
        if int(value.get("version", 1)) != 1:
            raise ValueError("Unsupported ruleset version")
        control = value.get("control", {})
        ruletype = str(control.get("ruletype", "single")).lower()
        if ruletype not in {"single", "multi"}:
            raise ValueError("ruletype must be 'single' or 'multi'")
        rules = tuple(Rule.from_dict(item) for item in value.get("rules", []))
        return cls(1, ruletype, rules)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "control": {"ruletype": self.ruletype},
            "rules": [asdict(rule) for rule in self.rules],
        }


@dataclass
class CycleRecord:
    timestamp: str
    text: str
    matches: list[dict[str, Any]]
    phases_ms: dict[str, float]
    total_ms: float
    exceeded: bool
    image: str | None = None
    error: str | None = None


@dataclass
class RuntimeState:
    phase: Phase = Phase.STOPPED
    paused: bool = False
    running: bool = False
    latest: CycleRecord | None = None
    history: list[CycleRecord] = field(default_factory=list)
    mqtt_connected: bool = False
