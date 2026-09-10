# ORCA

ORCA turns camera text into automation events: it captures a frame, reads it with PaddleOCR models running through ONNX Runtime, classifies the text with prioritized text or regular-expression rules, and publishes matches over MQTT. A small Flask console provides the live image, OCR text, rule editor, pause control, and timing diagnostics.

## Quick start

Python 3.10+ is required. The included setup script uses the repository's `.venv` and can optionally install Mosquitto on supported Unix systems:

```sh
./scripts/setup.sh
./.venv/bin/orca --camera demo
```

Open <http://127.0.0.1:8080>. Demo mode is a complete dry run with a generated frame and deterministic OCR text, so it needs neither camera hardware nor an MQTT broker.

For a real camera, run:

```sh
./.venv/bin/orca --camera 0 --mqtt mqtt://localhost:1883
```

When `--camera` is omitted in an interactive terminal, ORCA scans for cameras and prompts for one. If there are none, it falls back to demo mode. OCR model files bundled by `rapidocr-onnxruntime` are derived from PaddleOCR and executed locally through ONNX Runtime; no PaddlePaddle API or cloud service is used.

## CLI

```text
orca [--headless] [--camera SOURCE] [--ruleset PATH] [--scan-rate MS]
     [--non-interactive] [--pause] [--mqtt URL] [--self-host] [--port PORT]
```

- `--headless` omits the web server but keeps the scan loop running.
- `--camera` accepts an OpenCV camera index, video/stream path, or `demo`.
- `--ruleset` defaults to `data/rules.json`; a starter file is created when absent.
- `--scan-rate` updates the ruleset's target cycle time.
- `--pause` starts OCR and live preview while suppressing MQTT result broadcasts.
- `--self-host` binds the console to `0.0.0.0`; use only on a trusted network. There is no authentication in this initial local-first release.

## Rulesets

Rulesets use schema version 1. Lower priority numbers win. In `single` mode ORCA returns only the highest-priority match; `multi` returns every match.

```json
{
  "version": 1,
  "control": {"scanrate": 1000, "ruletype": "single"},
  "rules": [
    {"label": "Twenty", "topic": "twenty", "priority": 10, "type": "REGEX", "content": "\\b(20|twenty)\\b"}
  ]
}
```

The UI can edit, validate, test, import, and export this format. Changes are written atomically and are picked up by the next scan.

## MQTT

Every unpaused inspection is published as JSON to `orca.results`, and once more to each matched class topic such as `orca.results.twenty`. Timing and loop data are sent to `orca.diagnostic`. Watch all ORCA traffic with:

```sh
./.venv/bin/orca-monitor mqtt://localhost:1883
```

## Development

```sh
./.venv/bin/python -m pip install -e '.[dev]'
./.venv/bin/pytest
```

The runtime is split into deliberately small modules: `vision.py` owns OpenCV/ONNX adapters, `rules.py` is pure classification logic, `engine.py` owns scheduling and timings, `mqtt.py` owns topics, and `web.py` exposes the Flask API.

