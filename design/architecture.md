# ORCA architecture and design methodology

## Goals

ORCA is a simple OCR based classifier.  The goal is to make a simple, easy to deploy and configure inspection solution for OCR use-cases.

## Runtime flow

```text
OpenCV camera
    -> RapidOCR
    -> annotated preview + extracted text
    -> prioritized Classifier
    -> MQTT result topics (unless paused)
    -> measured delay to the configured scan rate (alert if scan rate exceeded)
```

The loop reloads the JSON ruleset and TOML application configuration at each cycle. Ruleset files contain only classification behavior; scan timing, camera source, web-server port, and MQTT connection settings live in `config.toml`. Saves are atomic (new save files written to `<file>.tmp` then replaced), so the loop observes either the old or new complete document. Paused mode still captures, runs OCR, classifies, annotates, and reports diagnostics; it only suppresses MQTT results.

Each completed cycle records capture, OCR, classification, and MQTT time plus total time. The bounded in-memory history prevents indefinite growth. If execution exceeds the scan-rate setpoint, delay is zero and a warning is logged.

## Web and protocol design

FastAPI serves the static, build-free client and low-frequency command/configuration endpoints through Uvicorn. Live runtime state uses `/ws/status`, a WebSocket that sends a bounded snapshot twice per second. There exists a status HTTP GET route for diagnostics and integrations but is not used by the browser client.

Mutating endpoints remain ordinary HTTP because save, pause, resume, and test operations are discrete commands where request/response errors are useful. Browser input is validated through the same `Ruleset.from_dict` path used for files.

## Modules

- `models.py`: versioned rule and runtime value types.
- `config.py`: JSON ruleset and TOML application configuration stores.
- `rules.py`: deterministic priority and matching behavior.
- `vision.py`: cameras, model-spec loading, ONNX inference, DBNet/CTC decoding, preview annotations.
- `engine.py`: scan scheduling, pause semantics, metrics, and bounded state.
- `mqtt.py`: connection lifecycle and ORCA topic layout.
- `web.py`: FastAPI routes and WebSocket status feed.
- `cli.py`: deployment composition and command-line interface.
- `monitor.py`: standalone MQTT observer.
