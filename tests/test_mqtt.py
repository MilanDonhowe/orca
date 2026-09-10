import json

from orca.mqtt import MQTTPublisher


class RecordingClient:
    def __init__(self):
        self.messages = []

    def publish(self, topic, payload):
        self.messages.append((topic, json.loads(payload)))


def test_mqtt_topics_use_slash_hierarchy():
    publisher = MQTTPublisher()
    publisher.client = RecordingClient()

    publisher.publish_result({"text": "20"}, [{"topic": "twenty"}])
    publisher.publish_diagnostic({"phase": "DELAY"})

    assert [topic for topic, _ in publisher.client.messages] == [
        "orca/results",
        "orca/results/twenty",
        "orca/diagnostic",
    ]
