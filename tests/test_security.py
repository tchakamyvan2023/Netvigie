"""
NETVIGIE — Tests unitaires du Security Analyst
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import MagicMock
from datetime import datetime, timezone

from backend.services.security_service import (
    CAT_SSH_BRUTE_FORCE,
    CAT_SSH_AUTH_FAILURE,
    CAT_PORT_SCAN,
    CAT_PRIVILEGE_ESCALATION,
    CAT_PAM,
    CAT_OTHER,
    classify_alert,
    compute_risk_score,
)


def _make_alert(description="", groups="", log="", level=5, mitre=None):
    a = MagicMock()
    a.rule_description = description
    a.rule_groups = groups
    a.full_log = log
    a.rule_level = level
    a.mitre_ids = mitre
    a.severity = "medium"
    a.src_ip = "192.168.1.30"
    a.alert_ts = datetime.now(timezone.utc)
    return a


def test_classify_brute_force():
    a = _make_alert(description="Multiple authentication failures")
    assert classify_alert(a) == CAT_SSH_BRUTE_FORCE


def test_classify_ssh_failure():
    a = _make_alert(description="Failed password for invalid user")
    assert classify_alert(a) == CAT_SSH_AUTH_FAILURE


def test_classify_port_scan():
    a = _make_alert(description="Port scan detected from 192.168.1.30")
    assert classify_alert(a) == CAT_PORT_SCAN


def test_classify_privilege():
    a = _make_alert(description="sudo to root executed")
    assert classify_alert(a) == CAT_PRIVILEGE_ESCALATION


def test_classify_pam():
    a = _make_alert(description="PAM: session opened")
    assert classify_alert(a) == CAT_PAM


def test_classify_other():
    a = _make_alert(description="something unrelated")
    assert classify_alert(a) == CAT_OTHER


def test_risk_score_ssh_brute_force():
    a = _make_alert(description="brute force", level=12, mitre="T1110")
    score = compute_risk_score(a, CAT_SSH_BRUTE_FORCE)
    assert score >= 80


def test_risk_score_pam():
    a = _make_alert(description="pam", level=3)
    score = compute_risk_score(a, CAT_PAM)
    assert score < 50


def test_risk_score_max_100():
    a = _make_alert(description="malware", level=15, mitre="T1190")
    score = compute_risk_score(a, CAT_PRIVILEGE_ESCALATION)
    assert score <= 100