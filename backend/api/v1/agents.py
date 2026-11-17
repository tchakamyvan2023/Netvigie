"""
NETVIGIE — Endpoints Agents
GET /agents (état des 4 agents NETVIGIE), GET /agents/wazuh
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.core.database import get_db
from backend.models.agent_netvigie import AgentNetvigie
from backend.models.agent_wazuh import AgentWazuh
from backend.models.user import User
from backend.schemas.agent import AgentNetvigieRead, AgentWazuhRead

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentNetvigieRead])
def list_netvigie_agents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(AgentNetvigie).order_by(AgentNetvigie.name).all()


@router.get("/wazuh", response_model=list[AgentWazuhRead])
def list_wazuh_agents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(AgentWazuh).order_by(AgentWazuh.wazuh_id).all()