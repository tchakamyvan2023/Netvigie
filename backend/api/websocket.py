"""
NETVIGIE — WebSocket temps réel
Diffuse les nouveaux incidents à tous les clients connectés.
"""
import asyncio
import json
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.logging_config import setup_logging
from backend.core.redis_bus import STREAM_INCIDENTS, get_bus

logger = setup_logging("netvigie.ws")

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: dict):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    logger.info(f"WS client connecté (total: {len(manager.active)})")
    try:
        # Lancer une tâche de lecture Redis en arrière-plan
        reader = asyncio.create_task(_redis_reader())
        while True:
            # Garder la connexion ouverte (recevoir des ping)
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        reader.cancel()
        manager.disconnect(ws)
        logger.info(f"WS client déconnecté (total: {len(manager.active)})")


async def _redis_reader():
    """Lit le stream Redis et diffuse à tous les WS."""
    bus = get_bus()
    last_id = "$"  # seulement les nouveaux messages
    try:
        while True:
            try:
                msgs = bus.client.xread(
                    {STREAM_INCIDENTS: last_id}, count=10, block=1000
                )
                if msgs:
                    for _stream, messages in msgs:
                        for msg_id, fields in messages:
                            last_id = msg_id
                            payload = {}
                            for k, v in fields.items():
                                try:
                                    payload[k] = json.loads(v)
                                except (json.JSONDecodeError, TypeError):
                                    payload[k] = v
                            await manager.broadcast({
                                "type": "incident",
                                "data": payload,
                            })
            except Exception as e:
                logger.warning(f"Redis reader : {e}")
                await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass