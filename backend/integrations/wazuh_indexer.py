"""
NETVIGIE — Client Wazuh Indexer (OpenSearch)
Permet des recherches avancées dans les alertes indexées.
"""
from typing import Any, Dict, List, Optional

import requests
import urllib3
from requests.auth import HTTPBasicAuth

from backend.core.config import settings
from backend.core.exceptions import WazuhError
from backend.core.logging_config import setup_logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = setup_logging("netvigie.indexer")


class WazuhIndexerClient:
    """
    Client OpenSearch/Indexer Wazuh.
    Index par défaut : wazuh-alerts-*
    """

    ALERTS_INDEX = "wazuh-alerts-*"

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        timeout: int = 15,
    ):
        self.base_url = (base_url or settings.wazuh_indexer_url).rstrip("/")
        self.username = username or settings.wazuh_indexer_user
        self.password = password or settings.wazuh_indexer_password
        self.verify_ssl = (
            verify_ssl if verify_ssl is not None else settings.wazuh_indexer_verify_ssl
        )
        self.timeout = timeout

        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self.session.auth = HTTPBasicAuth(self.username, self.password)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def ping(self) -> bool:
        try:
            r = self.session.get(f"{self.base_url}/_cluster/health", timeout=5)
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False

    # ------------------------------------------------------------------
    # Recherche
    # ------------------------------------------------------------------
    def search(
        self,
        index: str,
        query: Dict[str, Any],
        size: int = 50,
        sort: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Recherche générique OpenSearch."""
        body: Dict[str, Any] = {"query": query, "size": size}
        if sort:
            body["sort"] = sort
        else:
            body["sort"] = [{"timestamp": {"order": "desc"}}]

        try:
            r = self.session.post(
                f"{self.base_url}/{index}/_search",
                json=body,
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as e:
            raise WazuhError(f"Erreur réseau Indexer : {e}")

        if r.status_code >= 400:
            raise WazuhError(
                f"Indexer HTTP {r.status_code} : {r.text[:300]}"
            )

        return r.json()

def get_recent_alerts(
    self,
    size: int = 50,
    min_level: Optional[int] = None,
    agent_id: Optional[str] = None,
    since_minutes: int = 60,
) -> List[Dict[str, Any]]:
    """Récupère les alertes récentes avec _id inclus."""
    must: List[Dict[str, Any]] = [
        {
            "bool": {
                "should": [
                    {"range": {"@timestamp": {"gte": f"now-{since_minutes}m"}}},
                    {"range": {"timestamp": {"gte": f"now-{since_minutes}m"}}},
                ],
                "minimum_should_match": 1,
            }
        }
    ]
    if min_level is not None:
        must.append({"range": {"rule.level": {"gte": min_level}}})
    if agent_id:
        must.append({"term": {"agent.id": agent_id}})

    query = {"bool": {"must": must}}
    result = self.search(self.ALERTS_INDEX, query, size=size)
    hits = result.get("hits", {}).get("hits", [])
    # Inclure _id dans le résultat
    return [{"_id": h.get("_id"), **h["_source"]} for h in hits]

    def count_alerts(
        self,
        min_level: Optional[int] = None,
        agent_id: Optional[str] = None,
        since_minutes: int = 60,
    ) -> int:
        """Compte les alertes sans récupérer les documents."""
        must: List[Dict[str, Any]] = [
            {"range": {"timestamp": {"gte": f"now-{since_minutes}m"}}}
        ]
        if min_level is not None:
            must.append({"range": {"rule.level": {"gte": min_level}}})
        if agent_id:
            must.append({"term": {"agent.id": agent_id}})

        body = {"query": {"bool": {"must": must}}, "size": 0}
        try:
            r = self.session.post(
                f"{self.base_url}/{self.ALERTS_INDEX}/_count",
                json={"query": body["query"]},
                timeout=self.timeout,
            )
            if r.status_code == 200:
                return r.json().get("count", 0)
        except requests.exceptions.RequestException:
            pass
        return 0

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une alerte par son ID."""
        query = {"term": {"_id": alert_id}}
        try:
            result = self.search(self.ALERTS_INDEX, query, size=1)
            hits = result.get("hits", {}).get("hits", [])
            return hits[0]["_source"] if hits else None
        except WazuhError:
            return None


# ----------------------------------------------------------------------
# Singleton
# ----------------------------------------------------------------------
_indexer: Optional[WazuhIndexerClient] = None


def get_indexer_client() -> WazuhIndexerClient:
    global _indexer
    if _indexer is None:
        _indexer = WazuhIndexerClient()
    return _indexer