"""
NETVIGIE — Service Machines
Synchronise les agents Wazuh + syscollector vers la table `machines`.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.core.config import netvigie_config
from backend.core.logging_config import setup_logging
from backend.models.machine import Machine

logger = setup_logging("netvigie.service.machine")


def _mb_from_kb(value: Optional[int]) -> Optional[int]:
    """Wazuh retourne les RAM en Ko, on convertit en Mo."""
    if value is None:
        return None
    try:
        return int(value) // 1024
    except (ValueError, TypeError):
        return None


def _extract_ip(syscollector: Dict[str, Any], fallback: str = "") -> str:
    """
    Extrait la première IPv4 non-loopback et non-link-local depuis netaddr.
    Ignore les IPv6 et les adresses de type fe80::/10, 169.254.x.x, 127.0.0.1.
    """
    netaddr = syscollector.get("network_addr", [])
    ipv4_candidates: List[str] = []
    ipv6_candidates: List[str] = []

    for addr in netaddr:
        ip = (addr.get("address") or "").strip()
        if not ip:
            continue
        # IPv4 ?
        if ":" not in ip:
            if ip == "127.0.0.1" or ip.startswith("169.254."):
                continue
            ipv4_candidates.append(ip)
        else:
            # IPv6 : ignorer loopback et link-local
            if ip in ("::1",) or ip.lower().startswith("fe80:"):
                continue
            ipv6_candidates.append(ip)

    if ipv4_candidates:
        return ipv4_candidates[0]
    if ipv6_candidates:
        return ipv6_candidates[0]
    return fallback or "0.0.0.0"


def _build_machine_from_syscollector(
    agent: Dict[str, Any],
    syscollector: Dict[str, Any],
) -> Dict[str, Any]:
    """Transforme un agent Wazuh + syscollector en dict pour la table machines."""
    hw = syscollector.get("hardware", {}) or {}
    os_info = syscollector.get("os", {}) or {}
    cpu = hw.get("cpu", {}) or {}
    ram = hw.get("ram", {}) or {}

    ip = _extract_ip(syscollector, fallback=agent.get("ip", ""))
    hostname = agent.get("name", "unknown")

    # Exclusions
    is_excluded = netvigie_config.is_excluded(ip=ip, name=hostname)

    # Métadonnées optionnelles
    meta = netvigie_config.machines_metadata.get(ip, {})

    return {
        "agent_id": str(agent.get("id", "")),
        "hostname": hostname,
        "ip": ip,
        "os_name": (os_info.get("os", {}) or {}).get("name"),
        "os_version": (os_info.get("os", {}) or {}).get("version"),
        "kernel": (os_info.get("os", {}) or {}).get("kernel", {}).get("release")
                  if isinstance(os_info.get("os", {}).get("kernel"), dict)
                  else os_info.get("os", {}).get("kernel"),
        "cpu_name": cpu.get("name"),
        "cpu_cores": cpu.get("cores"),
        "cpu_mhz": cpu.get("mhz"),
        "ram_total_mb": _mb_from_kb(ram.get("total")),
        "ram_free_mb": _mb_from_kb(ram.get("free")),
        "ram_usage_percent": ram.get("usage"),
        "status": agent.get("status", "unknown"),
        "is_excluded": is_excluded,
        "role": meta.get("role"),
        "criticality": meta.get("criticality"),
        "display_name": meta.get("display_name") or hostname,
        "last_seen": datetime.now(timezone.utc)
                    if agent.get("status") == "active"
                    else None,
        "last_sync": datetime.now(timezone.utc),
        "raw_json": json.dumps(syscollector, default=str)[:60000],
    }


def upsert_machine(db: Session, data: Dict[str, Any]) -> Machine:
    """Crée ou met à jour une machine (clé : agent_id)."""
    machine = (
        db.query(Machine)
        .filter(Machine.agent_id == data["agent_id"])
        .first()
    )
    if machine:
        for k, v in data.items():
            setattr(machine, k, v)
        return machine
    machine = Machine(**data)
    db.add(machine)
    return machine


def sync_machines(
    db: Session,
    agents: List[Dict[str, Any]],
    get_syscollector,
) -> Dict[str, Any]:
    """
    Synchronise les machines depuis la liste d'agents Wazuh.
    `get_syscollector(agent_id)` est une fonction qui retourne le syscollector.
    Retourne {"created": int, "updated": int, "excluded": int, "errors": int, "machines": [...]}
    """
    created = 0
    updated = 0
    excluded = 0
    errors = 0
    synced_machines: List[Machine] = []

    for agent in agents:
        agent_id = str(agent.get("id", ""))
        # Skip le manager Wazuh (id 000, local)
        if agent_id == "000":
            continue
        # Skip les agents non actifs
        if agent.get("status") != "active":
            continue

        try:
            syscollector = get_syscollector(agent_id)
            data = _build_machine_from_syscollector(agent, syscollector)

            if data["is_excluded"]:
                excluded += 1
                logger.info(f"Machine exclue ignorée : {data['hostname']} ({data['ip']})")
                # On l'enregistre quand même en base avec is_excluded=True
                # pour ne pas la confondre avec "indisponible"
                existing = (
                    db.query(Machine)
                    .filter(Machine.agent_id == agent_id)
                    .first()
                )
                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(Machine(**data))
                continue

            existing = (
                db.query(Machine)
                .filter(Machine.agent_id == agent_id)
                .first()
            )
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                updated += 1
                synced_machines.append(existing)
            else:
                m = Machine(**data)
                db.add(m)
                created += 1
                synced_machines.append(m)

        except Exception as e:
            errors += 1
            logger.warning(f"Sync machine agent {agent_id} échoué : {e}")

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "excluded": excluded,
        "errors": errors,
        "machines": synced_machines,
    }


def get_machine_by_agent_id(db: Session, agent_id: str) -> Optional[Machine]:
    return db.query(Machine).filter(Machine.agent_id == agent_id).first()


def get_active_machines(db: Session) -> List[Machine]:
    return (
        db.query(Machine)
        .filter(Machine.status == "active", Machine.is_excluded == False)  # noqa: E712
        .all()
    )