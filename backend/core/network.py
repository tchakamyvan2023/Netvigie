"""
NETVIGIE — Utilitaires réseau (ping ICMP)
Utilise la commande `ping` système pour mesurer latence et pertes.
"""
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from backend.core.logging_config import setup_logging

logger = setup_logging("netvigie.network")


@dataclass
class PingResult:
    host: str
    reachable: bool
    latency_ms: Optional[float]
    packet_loss_percent: float
    packets_sent: int
    packets_received: int


def ping(
    host: str,
    count: int = 4,
    timeout_s: int = 2,
    interval_s: float = 0.2,
) -> PingResult:
    """
    Ping ICMP via la commande système `ping`.
    Retourne un PingResult avec latence moyenne et % de pertes.
    """
    cmd = [
        "ping",
        "-c", str(count),
        "-W", str(timeout_s),
        "-i", str(interval_s),
        "-q",  # quiet : seulement le résumé
        host,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=count * (timeout_s + 1) + 5,
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"Ping timeout vers {host}")
        return PingResult(host, False, None, 100.0, count, 0)
    except FileNotFoundError:
        logger.error("Commande `ping` introuvable")
        return PingResult(host, False, None, 100.0, count, 0)
    except Exception as e:
        logger.error(f"Ping {host} échoué : {e}")
        return PingResult(host, False, None, 100.0, count, 0)

    stdout = result.stdout

    # Parse : "4 packets transmitted, 4 received, 0% packet loss, time 3004ms"
    m_loss = re.search(r"(\d+) packets transmitted, (\d+) received.*?(\d+(?:\.\d+)?)% packet loss", stdout)
    if m_loss:
        sent = int(m_loss.group(1))
        received = int(m_loss.group(2))
        loss = float(m_loss.group(3))
    else:
        sent = count
        received = 0
        loss = 100.0

    # Parse : "rtt min/avg/max/mdev = 0.123/0.456/0.789/0.123 ms"
    m_rtt = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/", stdout)
    latency = float(m_rtt.group(1)) if m_rtt else None

    reachable = received > 0

    return PingResult(
        host=host,
        reachable=reachable,
        latency_ms=latency,
        packet_loss_percent=loss,
        packets_sent=sent,
        packets_received=received,
    )