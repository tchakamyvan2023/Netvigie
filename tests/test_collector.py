"""
NETVIGIE — Tests unitaires du Collector
Lancer : ./venv/bin/pytest tests/test_collector.py -v
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from backend.services.machine_service import (
    _mb_from_kb,
    _extract_ip,
)
from backend.services.alert_service import _severity_from_level


def test_mb_from_kb():
    assert _mb_from_kb(1024) == 1
    assert _mb_from_kb(1024 * 1024) == 1024
    assert _mb_from_kb(None) is None
    assert _mb_from_kb("invalid") is None


def test_extract_ip():
    syscollector = {
        "network_addr": [
            {"address": "127.0.0.1"},
            {"address": "192.168.1.10"},
            {"address": "169.254.1.1"},
        ]
    }
    assert _extract_ip(syscollector) == "192.168.1.10"


def test_extract_ip_fallback():
    assert _extract_ip({}, fallback="10.0.0.1") == "10.0.0.1"
    assert _extract_ip({"network_addr": []}) == "0.0.0.0"


def test_severity_mapping():
    assert _severity_from_level(0) == "info"
    assert _severity_from_level(3) == "info"
    assert _severity_from_level(5) == "low"
    assert _severity_from_level(8) == "medium"
    assert _severity_from_level(11) == "high"
    assert _severity_from_level(14) == "critical"
    assert _severity_from_level(20) == "critical"