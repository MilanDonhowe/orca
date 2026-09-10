# Change log

## 2026-09-10 - FastAPI migration

- Replaced Flask and flask-sock with FastAPI and Uvicorn while preserving the HTTP and WebSocket contracts.
- Migrated the web tests to FastAPI's test client.

## 2026-09-09 - Initial application

- Created the installable `orca-ocr` Python package and `orca`/`orca-monitor` executables.
- Added OpenCV camera capture, demo camera, timed scan loop, pause semantics, versioned JSON rulesets, prioritized text/regex classification, MQTT topics, timing history, and overrun logging.
- Added a Flask SPA with solarized playful styling, status diagnostics, camera preview, live OCR, classifications, rule testing/editing, JSON import/export, and keyboard-operable controls.
- Added Unix setup guidance/script, example rules, tests, and project documentation.

## 2026-09-09 - Model and live-status revision

- Removed RapidOCR from the project dependency and runtime architecture.
- Added an ORCA-owned, sidecar-configured ONNX Runtime backend with optional DBNet detection, CTC recognition, custom tensor names, preprocessing, vocabulary, and provider selection.
- Added OCR region polygons and confidence labels to camera preview images. Backends without location data may return zero regions; recognizer-only mode uses the full frame.
- Changed the web client from recurring `GET /api/status` polling to `/ws/status` WebSocket updates. The read-only GET remains for diagnostics and tests.
- Documented design methodology, module boundaries, limitations, and the ONNX model bundle contract.
