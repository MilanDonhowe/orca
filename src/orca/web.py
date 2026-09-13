from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from orca.config import ConfigStore, MQTTSettings, RulesetStore
from orca.models import Ruleset


PACKAGE_DIR = Path(__file__).resolve().parent


def create_app(engine, store: RulesetStore, config_store: ConfigStore | None = None) -> FastAPI:
    app = FastAPI(title="ORCA", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    config_store = config_store or ConfigStore(store.path.with_name("config.toml"))

    async def json_body(request: Request) -> Any:
        try:
            return await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(str(exc)) from exc

    @app.get("/")
    async def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/docs", include_in_schema=False)
    async def api_docs():
        return get_swagger_ui_html(
            openapi_url="/static/openapi.yaml",
            title="ORCA API documentation",
        )

    @app.get("/api/status")
    async def status():
        return engine.snapshot()

    @app.websocket("/ws/status")
    async def status_socket(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(engine.snapshot())
                await asyncio.sleep(0.5)
        except (WebSocketDisconnect, RuntimeError):
            pass

    @app.post("/api/control")
    async def control(request: Request):
        try:
            body = await json_body(request)
            action = body.get("action") if isinstance(body, dict) else None
        except ValueError:
            action = None
        if action not in {"pause", "resume"}:
            return JSONResponse({"error": "action must be pause or resume"}, status_code=400)
        engine.set_paused(action == "pause")
        return {"paused": action == "pause"}

    @app.get("/api/ruleset")
    async def get_ruleset():
        return store.load().to_dict()

    @app.get("/api/mqtt")
    async def get_mqtt():
        return config_store.load().mqtt.public_dict()

    @app.get("/api/config")
    async def get_config():
        settings = config_store.load()
        return {"camera": settings.camera or "", "scan_rate": settings.scan_rate}

    @app.put("/api/config")
    async def put_config(request: Request):
        try:
            body = await json_body(request)
            current = config_store.load()
            settings = config_store.save_runtime(
                body.get("scan_rate", current.scan_rate),
                body.get("camera", current.camera),
            )
            return {"camera": settings.camera or "", "scan_rate": settings.scan_rate}
        except (AttributeError, TypeError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.put("/api/mqtt")
    async def put_mqtt(request: Request):
        try:
            body = await json_body(request)
            previous = config_store.load().mqtt
            if not body.get("password") and body.get("has_password"):
                body["password"] = previous.password
            settings = MQTTSettings.from_dict(body)
            config_store.save_mqtt(settings)
            engine.configure_mqtt(settings)
            return settings.public_dict()
        except (AttributeError, TypeError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.put("/api/ruleset")
    async def put_ruleset(request: Request):
        try:
            ruleset = Ruleset.from_dict(await json_body(request))
            store.save(ruleset)
            return ruleset.to_dict()
        except (TypeError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.post("/api/test")
    async def test_ruleset(request: Request):
        from .rules import Classifier

        try:
            body = await json_body(request)
            ruleset = Ruleset.from_dict(body.get("ruleset", store.load().to_dict()))
            return {"matches": Classifier(ruleset).classify(str(body.get("text", "")))}
        except (AttributeError, TypeError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/api/ruleset/export")
    async def export_ruleset():
        content = json.dumps(store.load().to_dict(), indent=2) + "\n"
        return Response(
            content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=orca-rules.json"},
        )

    return app
