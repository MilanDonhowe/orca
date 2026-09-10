# ORCA: OCR -> Regex -> Classification

ORCA is a relatively small python application allowing for easy OCR based classification solutions.

It collects image frames from your selected web camera (via opencv), runs it through RapidOCR, then runs the collected text through a set of "rules" to determine which class to be assigned and broadcasts the result over MQTT.


ORCA comes with an optional FastAPI powered web UI to configure and view the classification loop.

## Disclaimer:
This application is pretty much entirely vibe-coded.  There's some human touch ups here and there, but for the most part this is all AI made and thus should be treated with some healthy skepticism on the performance and stability of the app.  I tried when possible to keep it as simple and self-contained as possible, but there still might be some odd ball bugs here and there.

## Quick start

Python 3.12+ is required. The included setup script uses the repository's `.venv` and can optionally install Mosquitto on supported Unix systems:

```sh
./scripts/setup.sh
./.venv/bin/orca --camera demo
```

Open <http://127.0.0.1:8080>. Demo mode is a complete dry run with a generated frame and deterministic OCR text, so it needs neither camera hardware nor an MQTT broker.

For a real camera and ONNX model bundle, run:

```sh
./.venv/bin/orca --camera 0 --model-config models/my-ocr/orca-model.json
```

When `--camera` is omitted in an interactive terminal, ORCA scans for cameras and prompts for one. If there are none, it falls back to demo mode. Real OCR uses plain ONNX Runtime. Models, tensor names, preprocessing, vocabulary, and postprocessing parameters live in a sidecar JSON file, so model bundles can be swapped without changing ORCA. The initial built-in postprocessors support DBNet text detection and CTC text recognition; new graph families implement the small `OCRBackend` interface. See [the model specification](design/model-spec.md).

## CLI

```text
orca [--headless] [--camera SOURCE] [--model-config PATH] [--ruleset PATH]
     [--config PATH] [--non-interactive] [--pause] [--self-host]
```

- `--headless` omits the web server but keeps the scan loop running.
- `--camera` accepts an OpenCV camera index, video/stream path, or `demo`.
- `--ruleset` defaults to `data/rules.json`; a starter file is created when absent.
- `--config` defaults to `config.toml` and contains scan timing, web, and MQTT settings.
- `--pause` starts OCR and live preview while suppressing MQTT result broadcasts.
- `--self-host` binds the console to `0.0.0.0`; use only on a trusted network. There is no authentication in this initial local-first release.

## Rulesets

Rulesets use schema version 1. Lower priority numbers win. In `single` mode ORCA returns only the highest-priority match; `multi` returns every match.

```json
{
  "version": 1,
  "control": {"ruletype": "single"},
  "rules": [
    {"label": "Twenty", "topic": "twenty", "priority": 10, "type": "REGEX", "content": "\\b(20|twenty)\\b"}
  ]
}
```

The UI can edit, validate, test, import, and export this format. Changes are written atomically and are picked up by the next scan.

## Application configuration

Runtime and connection settings live in `config.toml`:

```toml
[runtime]
scan_rate = 1000
camera = "0"

[web]
port = 8080

[mqtt]
enabled = false
host = "localhost"
port = 1883
tls = false
username = ""
password = ""
client_id = ""
keepalive = 60
```

`camera` accepts an OpenCV device index, stream URL, video path, or `demo`. The `--camera` CLI option overrides it for one run. Scan-rate changes are picked up by the next cycle; camera and web-port changes require restarting ORCA. MQTT settings can also be saved from the web console.

## MQTT

Every unpaused inspection is published as JSON to `orca/results`, and once more to each matched class topic such as `orca/results/twenty`. Timing and loop data are sent to `orca/diagnostic`. Watch all ORCA traffic with:

```sh
./.venv/bin/orca-monitor mqtt://localhost:1883
```

## Development

```sh
./.venv/bin/python -m pip install -e '.[dev]'
./.venv/bin/pytest
```

The runtime is split into deliberately small modules: `vision.py` owns OpenCV/ONNX adapters, `rules.py` is pure classification logic, `engine.py` owns scheduling and timings, `mqtt.py` owns topics, and `web.py` exposes the FastAPI API and WebSocket stream. Design decisions and a change log are maintained in [`design/`](design/architecture.md).
