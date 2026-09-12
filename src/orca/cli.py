from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
import webbrowser

import uvicorn

from orca.config import ConfigStore, RulesetStore
from orca.engine import OrcaEngine
from orca.mqtt import MQTTPublisher
from orca.vision import DemoCamera, DemoOCR, OCR, OpenCVCamera, list_cameras
from orca.web import create_app


ADVERT='''
===========================================================================               
 ▗▄▖ ▗▄▄▖  ▗▄▄▖ ▗▄▖ 
▐▌ ▐▌▐▌ ▐▌▐▌   ▐▌ ▐▌
▐▌ ▐▌▐▛▀▚▖▐▌   ▐▛▀▜▌
▝▚▄▞▘▐▌ ▐▌▝▚▄▄▖▐▌ ▐▌
===========================================================================
'''



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orca", description="OCR and regex classification automation")
    parser.add_argument("--headless", action="store_true", help="run without the web UI")
    parser.add_argument("--camera", help="camera index, stream URL, video file, or 'demo'")
    parser.add_argument("--ruleset", default="data/rules.json", help="path to a JSON ruleset")
    parser.add_argument("--config", default="config.toml", help="path to application TOML configuration")
    parser.add_argument("--non-interactive", action="store_true", help="do not prompt for a camera")
    parser.add_argument("--pause", action="store_true", help="start with result broadcasts paused")
    parser.add_argument("--self-host", action="store_true", help="listen on all network interfaces")
    parser.add_argument("--debug", action="store_true")
    return parser


def choose_camera() -> str:
    cameras = list_cameras()
    if not cameras:
        print("No cameras detected; using the demo camera.")
        return "demo"
    print("Connected cameras:")
    for i, camera in enumerate(cameras):
        print(f"  [{i}] Camera {camera}")
    value = input("Select camera [0]: ").strip() or "0"
    return str(cameras[int(value)])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    store = RulesetStore(args.ruleset)
    config_store = ConfigStore(args.config)
    settings = config_store.load()
    source = args.camera or settings.camera
    if source is None and not args.non_interactive and sys.stdin.isatty():
        source = choose_camera()
    source = source or "0"
    demo = source.lower() == "demo"
    camera = DemoCamera() if demo else OpenCVCamera(int(source) if source.isdigit() else source)
    ocr = DemoOCR() if demo else OCR()
    publisher = MQTTPublisher(settings=settings.mqtt)
    engine = OrcaEngine(camera, ocr, store, publisher, config_store, paused=args.pause)
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
    url = f"http://127.0.0.1:{settings.web_port}"
    if not os.environ.get("ORCA_NO_BROWSER"):
        import threading
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        print(ADVERT)
        uvicorn.run(
            create_app(engine, store, config_store),
            host=host,
            port=settings.web_port,
            log_level="debug" if args.debug else "info",
        )
    finally:
        engine.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
