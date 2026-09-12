# ORCA: OCR -> Regex -> Classification

ORCA is a relatively small python application allowing for easy OCR based classification solutions.

It collects image frames from your selected web camera (via opencv), runs it through RapidOCR, then runs the collected text through a set of "rules" to determine which class to be assigned and broadcasts the result over MQTT.

ORCA comes with an optional FastAPI powered web UI to configure and view the classification loop.



## Disclaimer: AI
This application is pretty much entirely vibe-coded.  There's some human touch ups here and there, but for the most part this is all AI made and thus should be treated with some healthy skepticism on the performance and stability of the app.  I tried when possible to keep it as simple and self-contained as possible, but there still might be some odd ball bugs here and there.

## Integrations
- 

## Quick start

Python 3.12+ is required. The included setup script uses the repository's `.venv` and can optionally install Mosquitto on supported Unix systems:

```sh
./scripts/setup.sh
./.venv/bin/orca
```

The orca cli will prompt the user to select a camera available via the openCV API--if none exists it falls back to a "demo" mode.

The web console's **API docs** link opens an interactive Swagger UI describing the HTTP API and status payloads. The underlying OpenAPI 3.0 file remains available at <http://127.0.0.1:8080/static/openapi.yaml> for importing into code generators, API clients, and other systems.



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

The optional `camera` setting accepts an OpenCV device index, stream URL, video path, or `demo`. Omit it (or clear it in the web console) to retain the interactive CLI camera chooser. The `--camera` CLI option overrides it for one run. Scan-rate changes are picked up by the next cycle; camera and web-port changes require restarting ORCA. Camera and MQTT settings can also be saved from the web console.

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
