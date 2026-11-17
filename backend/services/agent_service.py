"""NETVIGIE — Service Agents NETVIGIE (heartbeat)."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.agent_netvigie import AgentNetvigie


def get_agent(db: Session, name: str) -> Optional[AgentNetvigie]:
    return db.query(AgentNetvigie).filter(AgentNetvigie.name == name).first()


def list_agents(db: Session) -> List[AgentNetvigie]:
    return db.query(AgentNetvigie).order_by(AgentNetvigie.name).all()


def mark_running(db: Session, name: str) -> None:
    agent = get_agent(db, name)
    if agent:
        agent.status = "running"
        agent.last_heartbeat = datetime.now(timezone.utc)
        db.commit()