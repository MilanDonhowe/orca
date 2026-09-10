from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone

from .config import RulesetStore
from .models import CycleRecord, Phase, RuntimeState
from .mqtt import MQTTPublisher
from .rules import Classifier
from .vision import Camera, image_data_url

log = logging.getLogger(__name__)


class OrcaEngine:
    def __init__(self, camera: Camera, ocr, store: RulesetStore, mqtt: MQTTPublisher, paused: bool = False):
        self.camera, self.ocr, self.store, self.mqtt = camera, ocr, store, mqtt
        self.state = RuntimeState(paused=paused)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.mqtt.start()
        self.state.running = True
        self._thread = threading.Thread(target=self._run, name="orca-loop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)
        self.camera.close()
        self.mqtt.stop()
        self.state.running = False
        self.state.phase = Phase.STOPPED

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self.state.paused = paused

    def snapshot(self) -> dict:
        with self._lock:
            history = self.state.history[-60:]
            latest = asdict(self.state.latest) if self.state.latest else None
            totals = [item.total_ms for item in history]
            return {
                "running": self.state.running,
                "paused": self.state.paused,
                "phase": self.state.phase.value,
                "mqtt_connected": self.mqtt.connected,
                "latest": latest,
                "history": [asdict(item) | {"image": None} for item in history],
                "average_ms": round(sum(totals) / len(totals), 2) if totals else 0,
                "scanrate": self.store.load().scanrate,
            }

    def _phase(self, phase: Phase) -> None:
        with self._lock:
            self.state.phase = phase

    def _run(self) -> None:
        while not self._stop.is_set():
            started = time.perf_counter()
            timings: dict[str, float] = {}
            try:
                ruleset = self.store.load()
                phase_start = time.perf_counter(); self._phase(Phase.IMAGE_CAPTURE)
                frame = self.camera.read(); timings["capture"] = self._elapsed(phase_start)
                phase_start = time.perf_counter(); self._phase(Phase.OCR_MODEL)
                text = self.ocr.read(frame); timings["ocr"] = self._elapsed(phase_start)
                phase_start = time.perf_counter(); self._phase(Phase.RULES_CLASSIFIER)
                matches = Classifier(ruleset).classify(text); timings["classify"] = self._elapsed(phase_start)
                paused = self.state.paused
                phase_start = time.perf_counter()
                if paused:
                    self._phase(Phase.PAUSED)
                else:
                    self._phase(Phase.MQTT_BROADCAST)
                    result = {"timestamp": datetime.now(timezone.utc).isoformat(), "text": text, "matches": matches}
                    self.mqtt.publish_result(result, matches)
                timings["mqtt"] = self._elapsed(phase_start)
                total = self._elapsed(started)
                record = CycleRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(), text=text, matches=matches,
                    phases_ms={key: round(value, 2) for key, value in timings.items()},
                    total_ms=round(total, 2), exceeded=total > ruleset.scanrate,
                    image=image_data_url(frame),
                )
                with self._lock:
                    self.state.latest = record
                    self.state.history.append(record)
                    self.state.history = self.state.history[-120:]
                if record.exceeded:
                    log.warning("Cycle %.1fms exceeded %dms scan rate", total, ruleset.scanrate)
                if not paused:
                    self.mqtt.publish_diagnostic({"phase": self.state.phase.value, "total_ms": total, "phases_ms": timings, "exceeded": record.exceeded})
                remaining = max(0.0, ruleset.scanrate - total)
                self._phase(Phase.PAUSED if paused else Phase.DELAY)
                self._stop.wait(remaining / 1000)
            except Exception as exc:
                log.exception("ORCA cycle failed")
                with self._lock:
                    self.state.phase = Phase.ERROR
                    self.state.latest = CycleRecord(datetime.now(timezone.utc).isoformat(), "", [], timings, self._elapsed(started), False, error=str(exc))
                self._stop.wait(1)
        self.state.running = False

    @staticmethod
    def _elapsed(start: float) -> float:
        return (time.perf_counter() - start) * 1000

