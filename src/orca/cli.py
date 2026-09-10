from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
import webbrowser
from pathlib import Path

from .config import RulesetStore
from .engine import OrcaEngine
from .mqtt import MQTTPublisher
from .models import Ruleset
from .vision import DemoCamera, DemoOCR, OCR, OpenCVCamera, list_cameras
from .web import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orca", description="OCR and regex classification automation")
    parser.add_argument("--headless", action="store_true", help="run without the web UI")
    parser.add_argument("--camera", help="camera index, stream URL, video file, or 'demo'")
    parser.add_argument("--ruleset", default="data/rules.json", help="path to a JSON ruleset")
    parser.add_argument("--scan-rate", type=int, help="override scan rate in milliseconds")
    parser.add_argument("--non-interactive", action="store_true", help="do not prompt for a camera")
    parser.add_argument("--pause", action="store_true", help="start with result broadcasts paused")
    parser.add_argument("--mqtt", help="MQTT URL, for example mqtt://localhost:1883")
    parser.add_argument("--self-host", action="store_true", help="listen on all network interfaces")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--debug", action="store_true")
    return parser


def choose_camera() -> str:
    cameras = list_cameras()
    if not cameras:
        print("No cameras detected; using the demo camera.")
        return "demo"
    try:
        from InquirerPy import inquirer
        return str(inquirer.select(message="Select a camera:", choices=[str(item) for item in cameras], default=str(cameras[0])).execute())
    except ImportError:
        print("Connected cameras:")
        for i, camera in enumerate(cameras):
            print(f"  [{i}] Camera {camera}")
        value = input("Select camera [0]: ").strip() or "0"
        return str(cameras[int(value)])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    source = args.camera
    if source is None and not args.non_interactive and sys.stdin.isatty():
        source = choose_camera()
    source = source or "0"
    store = RulesetStore(args.ruleset)
    if args.scan_rate is not None:
        current = store.load().to_dict(); current["control"]["scanrate"] = args.scan_rate
        store.save(Ruleset.from_dict(current))
    demo = source.lower() == "demo"
    camera = DemoCamera() if demo else OpenCVCamera(int(source) if source.isdigit() else source)
    ocr = DemoOCR() if demo else OCR()
    engine = OrcaEngine(camera, ocr, store, MQTTPublisher(args.mqtt), paused=args.pause)
    engine.start()

    def shutdown(*_):
        engine.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    if args.headless:
        try:
            while True:
                time.sleep(1)
        finally:
            engine.stop()
        return 0
    host = "0.0.0.0" if args.self_host else "127.0.0.1"
    url = f"http://127.0.0.1:{args.port}"
    if not os.environ.get("ORCA_NO_BROWSER"):
        import threading
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        create_app(engine, store).run(host=host, port=args.port, threaded=True, use_reloader=False)
    finally:
        engine.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
