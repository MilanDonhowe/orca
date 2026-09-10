from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from .config import RulesetStore
from .models import Ruleset


def create_app(engine, store: RulesetStore) -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/status")
    def status():
        return jsonify(engine.snapshot())

    @app.post("/api/control")
    def control():
        action = (request.get_json(silent=True) or {}).get("action")
        if action not in {"pause", "resume"}:
            return jsonify(error="action must be pause or resume"), 400
        engine.set_paused(action == "pause")
        return jsonify(paused=action == "pause")

    @app.get("/api/ruleset")
    def get_ruleset():
        return jsonify(store.load().to_dict())

    @app.put("/api/ruleset")
    def put_ruleset():
        try:
            ruleset = Ruleset.from_dict(request.get_json(force=True))
            store.save(ruleset)
            return jsonify(ruleset.to_dict())
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return jsonify(error=str(exc)), 400

    @app.post("/api/test")
    def test_ruleset():
        from .rules import Classifier

        body = request.get_json(force=True)
        try:
            ruleset = Ruleset.from_dict(body.get("ruleset", store.load().to_dict()))
            return jsonify(matches=Classifier(ruleset).classify(str(body.get("text", ""))))
        except (TypeError, ValueError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get("/api/ruleset/export")
    def export_ruleset():
        content = json.dumps(store.load().to_dict(), indent=2) + "\n"
        return Response(content, mimetype="application/json", headers={"Content-Disposition": "attachment; filename=orca-rules.json"})

    return app

