"""Live oracle WS — /api/ws/oracle"""
import asyncio
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from core import db

_ws_clients: List[WebSocket] = []


def register(app: FastAPI) -> None:
    @app.websocket("/api/ws/oracle")
    async def oracle_ws(ws: WebSocket):
        await ws.accept()
        _ws_clients.append(ws)
        try:
            while True:
                await asyncio.sleep(15)
                try:
                    await ws.send_json({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "fragments": await db.swarm_fragments.count_documents({}),
                        "pending": await db.signals.count_documents({"status": "pending"}),
                    })
                except Exception:
                    break
        except WebSocketDisconnect:
            pass
        finally:
            if ws in _ws_clients:
                _ws_clients.remove(ws)
