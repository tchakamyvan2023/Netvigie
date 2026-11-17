"""
NETVIGIE — Tests unitaires de la Corrélation
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.correlation_service import (
    VERDICT_NORMAL,
    VERDICT_TECHNICAL_ANOMALY,
    VERDICT_NETWORK_FAILURE,
    VERDICT_SECURITY_ALERT,
    VERDICT_SUSPECTED_ATTACK,
    VERDICT_MIXED_INCIDENT,
    VERDICT_INVESTIGATION_REQUIRED,
    decide_verdict,
)


def test_all_normal():
    v = decide_verdict(None, None)
    assert v["verdict"] == VERDICT_NORMAL
    assert v["confidence"] == 1.0


def test_network_anomaly_only():
    diag = {"status": "ANOMALY", "ts": 1000.0}
    v = decide_verdict(diag, None)
    assert v["verdict"] == VERDICT_TECHNICAL_ANOMALY
    assert v["severity"] == "high"


def test_network_unreachable():
    diag = {"status": "UNREACHABLE", "ts": 1000.0}
    v = decide_verdict(diag, None)
    assert v["verdict"] == VERDICT_NETWORK_FAILURE
    assert v["confidence"] >= 0.85


def test_security_alert_low_level():
    assess = {"category": "PAM", "rule_level": 3, "alert_ts": 1000.0}
    v = decide_verdict(None, assess)
    assert v["verdict"] == VERDICT_SECURITY_ALERT
    assert v["severity"] == "high"


def test_suspected_attack_high_level():
    assess = {"category": "SSH_BRUTE_FORCE", "rule_level": 12, "alert_ts": 1000.0, "is_brute_force": True}
    v = decide_verdict(None, assess)
    assert v["verdict"] == VERDICT_SUSPECTED_ATTACK
    assert v["severity"] == "critical"


def test_mixed_incident_security_first():
    diag = {"status": "ANOMALY", "ts": 2000.0}
    assess = {"category": "SSH_BRUTE_FORCE", "rule_level": 12, "alert_ts": 1999.5, "is_brute_force": True}
    v = decide_verdict(diag, assess)
    assert v["verdict"] == VERDICT_MIXED_INCIDENT
    assert v["severity"] == "critical"


def test_investigation_required_network_first():
    diag = {"status": "ANOMALY", "ts": 2000.0}
    assess = {"category": "SSH_BRUTE_FORCE", "rule_level": 12, "alert_ts": 2005.0, "is_brute_force": True}
    v = decide_verdict(diag, assess)
    assert v["verdict"] == VERDICT_INVESTIGATION_REQUIRED
    assert v["confidence"] <= 0.5