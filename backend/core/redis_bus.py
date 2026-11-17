"""
NETVIGIE — Bus d'événements Redis Streams
Fournit publish/subscribe avec consumer groups.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

import redis

from backend.core.config import settings

# Noms des streams
STREAM_MACHINE_UPDATES = "netvigie:machine_updates"
STREAM_DIAGNOSTICS = "netvigie:diagnostics"
STREAM_SECURITY_ASSESSMENTS = "netvigie:security_assessments"
STREAM_INCIDENTS = "netvigie:incidents"
STREAM_AGENT_HEARTBEATS = "netvigie:agent_heartbeats"

ALL_STREAMS = [
    STREAM_MACHINE_UPDATES,
    STREAM_DIAGNOSTICS,
    STREAM_SECURITY_ASSESSMENTS,
    STREAM_INCIDENTS,
    STREAM_AGENT_HEARTBEATS,
]


class RedisBus:
    def __init__(self):
        self.client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

    # --- Health ---
    def ping(self) -> bool:
        try:
            return self.client.ping()
        except Exception:
            return False

    # --- Publish ---
    def publish(self, stream: str, payload: Dict[str, Any]) -> str:
        """Publie un événement dans un stream. Retourne l'ID du message."""
        data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v))
                for k, v in payload.items()}
        return self.client.xadd(stream, data, maxlen=10000, approximate=True)

    # --- Consumer group ---
    def ensure_group(self, stream: str, group: str) -> None:
        try:
            self.client.xgroup_create(stream, group, id="0", mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Lit les nouveaux messages d'un consumer group."""
        try:
            resp = self.client.xreadgroup(
                group, consumer, {stream: ">"}, count=count, block=block_ms
            )
        except Exception:
            return []
        results = []
        for _stream, messages in resp:
            for msg_id, fields in messages:
                parsed = {}
                for k, v in fields.items():
                    try:
                        parsed[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        parsed[k] = v
                results.append((msg_id, parsed))
        return results

    def ack(self, stream: str, group: str, msg_id: str) -> None:
        self.client.xack(stream, group, msg_id)

    def stream_length(self, stream: str) -> int:
        try:
            return self.client.xlen(stream)
        except Exception:
            return 0

    def get_last(self, stream: str, count: int = 10) -> List[Dict[str, Any]]:
        """Récupère les N derniers messages d'un stream."""
        try:
            msgs = self.client.xrevrange(stream, count=count)
        except Exception:
            return []
        out = []
        for msg_id, fields in msgs:
            parsed = {"_id": msg_id}
            for k, v in fields.items():
                try:
                    parsed[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    parsed[k] = v
            out.append(parsed)
        return out


_bus: Optional[RedisBus] = None


def get_bus() -> RedisBus:
    global _bus
    if _bus is None:
        _bus = RedisBus()
    return _bus