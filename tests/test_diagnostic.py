"""
NETVIGIE — Tests unitaires du Diagnostic
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from backend.core.network import PingResult, ping
from backend.services.diagnostic_service import (
    STATUS_ANOMALY,
    STATUS_NORMAL,
    STATUS_UNREACHABLE,
    is_anomaly,
)


def test_ping_localhost():
    """Ping localhost doit toujours répondre."""
    r = ping("127.0.0.1", count=2, timeout_s=1)
    assert isinstance(r, PingResult)
    assert r.reachable is True
    assert r.packets_received >= 1
    assert r.latency_ms is not None


def test_ping_unreachable():
    """Ping une IP inexistante doit échouer."""
    r = ping("192.0.2.1", count=1, timeout_s=1)  # TEST-NET-1
    assert r.reachable is False or r.packet_loss_percent > 0


def test_is_anomaly():
    assert is_anomaly({"status": STATUS_ANOMALY}) is True
    assert is_anomaly({"status": STATUS_UNREACHABLE}) is True
    assert is_anomaly({"status": STATUS_NORMAL}) is False