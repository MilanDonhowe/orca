from __future__ import annotations

import argparse
import json
import time
from urllib.parse import urlparse

import paho.mqtt.client as mqtt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orca-monitor", description="Observe ORCA MQTT messages")
    parser.add_argument("broker", nargs="?", default="mqtt://localhost:1883")
    parser.add_argument("--topic", default="orca.#")
    args = parser.parse_args(argv)
    parsed = urlparse(args.broker if "://" in args.broker else "mqtt://" + args.broker)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if parsed.username:
        client.username_pw_set(parsed.username, parsed.password)
    if parsed.scheme == "mqtts":
        client.tls_set()
    client.on_connect = lambda c, u, f, reason, properties: c.subscribe(args.topic)
    def display(client, userdata, message):
        raw = message.payload.decode(errors="replace")
        try: raw = json.dumps(json.loads(raw), indent=2)
        except json.JSONDecodeError: pass
        print(f"\n[{message.topic}]\n{raw}")
    client.on_message = display
    client.connect(parsed.hostname or "localhost", parsed.port or 1883)
    print(f"Watching {args.topic} on {parsed.hostname or 'localhost'} (Ctrl-C to stop)")
    try: client.loop_forever()
    except KeyboardInterrupt: client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

