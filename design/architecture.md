# ORCA architecture and design methodology

## Goals

ORCA is a local-first camera classification service. It should remain useful across different cameras, OCR models, rule collections, brokers, and deployment shapes. The core therefore coordinates capabilities rather than embedding vendor behavior.

The implementation follows four working principles:

1. Keep domain logic pure. Ruleset validation and classification have no camera, web, model, or broker dependencies and can be tested with plain strings.
2. Put hardware and protocols behind narrow boundaries. A camera returns an image, an OCR backend returns text regions, and an MQTT publisher accepts event payloads.
3. Make expensive or vendor-specific assumptions data. ONNX paths, tensor names, dimensions, normalization, thresholds, and vocabulary belong in a model sidecar rather than Python constants.
4. Make the application useful without infrastructure. Demo mode exercises capture, annotated preview, classification, timing, WebSocket delivery, and UI controls without a physical camera or MQTT broker.

## Runtime flow

```text
OpenCV camera
    -> OCRBackend (ONNX detector -> crops -> ONNX recognizer)
    -> annotated preview + extracted text
    -> prioritized Classifier
    -> MQTT result topics (unless paused)
    -> measured delay to the configured scan rate
```

The loop reloads the JSON ruleset and TOML application configuration at each cycle. Ruleset files contain only classification behavior; scan timing, camera source, web-server port, and MQTT connection settings live in `config.toml`. Saves are atomic (`.tmp` plus replace), so the loop observes either the old or new complete document. Paused mode still captures, runs OCR, classifies, annotates, and reports diagnostics; it only suppresses MQTT results.

Each completed cycle records capture, OCR, classification, and MQTT time plus total time. The bounded in-memory history prevents indefinite growth. If execution exceeds the scan-rate setpoint, delay is zero and a warning is logged.

## Model boundary

`OCRBackend.read(image)` returns an `OCRResult`, containing combined text and zero or more `TextRegion` values. Each region includes text, confidence, and a four-point polygon. This boundary supports annotation in the web preview without coupling the engine to a particular OCR library.

`OnnxOCR` is ORCA-owned and calls `onnxruntime.InferenceSession` directly. Its current configurable pipeline supports an optional DBNet detector and a CTC recognizer. A recognizer-only model treats the full image as one text region. Supporting another postprocessing family means adding a backend or decoder behind the same interface; it does not change the engine, rules, MQTT, or web UI.

“Drop in any ONNX model” cannot safely mean zero metadata: ONNX describes a computation graph but does not standardize image normalization, output semantics, text detection geometry, blank-token placement, or vocabulary. ORCA's sidecar schema supplies those missing semantics and makes compatibility testable. See `model-spec.md`.

## Web and protocol design

FastAPI serves the static, build-free client and low-frequency command/configuration endpoints through Uvicorn. Live runtime state uses `/ws/status`, a WebSocket that sends a bounded snapshot twice per second. This avoids repeated `/api/status` requests in the access log. The status GET remains available for diagnostics and integrations but is not used by the browser client.

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

## Known extension points

- Add detector/recognizer postprocessors through new `OCRBackend` implementations.
- Replace in-memory diagnostic history with persistent metrics without changing the UI payload.
- Add authentication before exposing `--self-host` outside a trusted network.
- Add broker reconnect/backpressure telemetry for production MQTT deployments.
