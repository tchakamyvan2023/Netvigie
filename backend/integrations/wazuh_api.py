"""
NETVIGIE — Client API Wazuh
Gère l'authentification JWT, le refresh automatique, la pagination,
et les principales ressources : agents, syscollector, alerts.
"""
import time
import threading
from typing import Any, Dict, List, Optional

import requests
import urllib3
from requests.auth import HTTPBasicAuth

from backend.core.config import settings
from backend.core.exceptions import WazuhError
from backend.core.logging_config import setup_logging

# Désactiver les warnings SSL (certificat auto-signé Wazuh)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = setup_logging("netvigie.wazuh")


class WazuhClient:
    """Client API Wazuh avec gestion automatique du token JWT."""

    # Wazuh limite par défaut à 500 items par requête
    MAX_LIMIT = 500

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        timeout: int = 15,
    ):
        self.base_url = (base_url or settings.wazuh_api_url).rstrip("/")
        self.username = username or settings.wazuh_api_user
        self.password = password or settings.wazuh_api_password
        self.verify_ssl = (
            verify_ssl if verify_ssl is not None else settings.wazuh_api_verify_ssl
        )
        self.timeout = timeout

        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._lock = threading.Lock()

        self.session = requests.Session()
        self.session.verify = self.verify_ssl

    # ------------------------------------------------------------------
    # Authentification
    # ------------------------------------------------------------------
    def _authenticate(self) -> str:
        """Obtient un nouveau token JWT depuis Wazuh."""
        url = f"{self.base_url}/security/user/authenticate"
        try:
            r = self.session.post(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as e:
            raise WazuhError(f"Impossible de joindre Wazuh ({url}) : {e}")

        if r.status_code != 200:
            raise WazuhError(
                f"Authentification Wazuh échouée (HTTP {r.status_code}) : {r.text[:300]}"
            )

        data = r.json()
        token = data.get("data", {}).get("token")
        if not token:
            raise WazuhError(f"Pas de token dans la réponse Wazuh : {data}")

        # Wazuh retourne un token valable ~15 min. On prend une marge de 60s.
        self._token = token
        self._token_expiry = time.time() + (15 * 60) - 60
        logger.info("Token Wazuh obtenu (valide ~14 min)")
        return token

    def _get_token(self) -> str:
        """Retourne un token valide, en renouvelle un si expiré."""
        with self._lock:
            if not self._token or time.time() >= self._token_expiry:
                self._authenticate()
            return self._token

    def invalidate_token(self) -> None:
        """Force le renouvellement au prochain appel."""
        with self._lock:
            self._token = None
            self._token_expiry = 0

    # ------------------------------------------------------------------
    # Requête générique avec retry sur 401
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        retry_auth: bool = True,
    ) -> Dict[str, Any]:
        token = self._get_token()
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            r = self.session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as e:
            raise WazuhError(f"Erreur réseau Wazuh ({url}) : {e}")

        # Token expiré -> on renouvelle et on retente une fois
        if r.status_code == 401 and retry_auth:
            logger.warning("Token Wazuh expiré, renouvellement...")
            self.invalidate_token()
            return self._request(
                method, endpoint, params, json_body, retry_auth=False
            )

        if r.status_code >= 400:
            raise WazuhError(
                f"Wazuh HTTP {r.status_code} sur {method} {endpoint} : {r.text[:300]}"
            )

        try:
            return r.json()
        except ValueError:
            raise WazuhError(f"Réponse Wazuh non-JSON sur {endpoint}")

    # ------------------------------------------------------------------
    # Health / Info
    # ------------------------------------------------------------------
    def ping(self) -> bool:
        """Test rapide d'authentification."""
        try:
            self._authenticate()
            return True
        except WazuhError:
            return False

    def get_manager_info(self) -> Dict[str, Any]:
        """GET /manager/info"""
        return self._request("GET", "/manager/info").get("data", {}).get(
            "affected_items", [{}]
        )[0]

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------
    def list_agents(
        self,
        status: Optional[str] = None,
        limit: int = MAX_LIMIT,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        GET /agents
        status : 'active', 'disconnected', 'pending', 'never_connected'
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status

        data = self._request("GET", "/agents", params=params)
        return data.get("data", {}).get("affected_items", [])

    def list_all_agents(self) -> List[Dict[str, Any]]:
        """Récupère TOUS les agents (pagination automatique)."""
        all_agents: List[Dict[str, Any]] = []
        offset = 0
        while True:
            batch = self.list_agents(limit=self.MAX_LIMIT, offset=offset)
            if not batch:
                break
            all_agents.extend(batch)
            if len(batch) < self.MAX_LIMIT:
                break
            offset += self.MAX_LIMIT
        return all_agents

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """GET /agents?agents_list={id}"""
        data = self._request("GET", "/agents", params={"agents_list": agent_id})
        items = data.get("data", {}).get("affected_items", [])
        if not items:
            raise WazuhError(f"Agent {agent_id} introuvable")
        return items[0]

    # ------------------------------------------------------------------
    # Syscollector (données collectées par l'agent)
    # ------------------------------------------------------------------
    def get_syscollector_hardware(self, agent_id: str) -> Dict[str, Any]:
        """GET /syscollector/{agent_id}/hardware"""
        data = self._request("GET", f"/syscollector/{agent_id}/hardware")
        items = data.get("data", {}).get("affected_items", [])
        return items[0] if items else {}

    def get_syscollector_os(self, agent_id: str) -> Dict[str, Any]:
        """GET /syscollector/{agent_id}/os"""
        data = self._request("GET", f"/syscollector/{agent_id}/os")
        items = data.get("data", {}).get("affected_items", [])
        return items[0] if items else {}

    def get_syscollector_network_iface(self, agent_id: str) -> List[Dict[str, Any]]:
        """GET /syscollector/{agent_id}/netiface"""
        data = self._request("GET", f"/syscollector/{agent_id}/netiface")
        return data.get("data", {}).get("affected_items", [])

    def get_syscollector_network_addr(self, agent_id: str) -> List[Dict[str, Any]]:
        """GET /syscollector/{agent_id}/netaddr"""
        data = self._request("GET", f"/syscollector/{agent_id}/netaddr")
        return data.get("data", {}).get("affected_items", [])

    def get_syscollector_ports(self, agent_id: str) -> List[Dict[str, Any]]:
        """GET /syscollector/{agent_id}/ports"""
        data = self._request("GET", f"/syscollector/{agent_id}/ports")
        return data.get("data", {}).get("affected_items", [])

    def get_syscollector_processes(self, agent_id: str) -> List[Dict[str, Any]]:
        """GET /syscollector/{agent_id}/processes"""
        data = self._request("GET", f"/syscollector/{agent_id}/processes")
        return data.get("data", {}).get("affected_items", [])

    def get_full_syscollector(self, agent_id: str) -> Dict[str, Any]:
        """
        Récupère tout le syscollector d'un agent en un seul appel.
        Tolère les erreurs individuelles (retourne {} pour la section en échec).
        """
        result: Dict[str, Any] = {"agent_id": agent_id}
        for key, method in [
            ("hardware", self.get_syscollector_hardware),
            ("os", self.get_syscollector_os),
            ("network_iface", self.get_syscollector_network_iface),
            ("network_addr", self.get_syscollector_network_addr),
            ("ports", self.get_syscollector_ports),
            ("processes", self.get_syscollector_processes),
        ]:
            try:
                result[key] = method(agent_id)
            except WazuhError as e:
                logger.warning(f"syscollector {key} agent {agent_id} : {e}")
                result[key] = {} if key in ("hardware", "os") else []
        return result

    # ------------------------------------------------------------------
    # Alertes
    # ------------------------------------------------------------------
    def get_alerts(
        self,
        limit: int = MAX_LIMIT,
        offset: int = 0,
        min_level: Optional[int] = None,
        agent_id: Optional[str] = None,
        since_seconds: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        GET /alerts (récupère les alertes récentes).
        Filtres : niveau minimum, agent, période.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset, "sort": "-timestamp"}
        q_parts: List[str] = []
        if min_level is not None:
            q_parts.append(f"rule.level>={min_level}")
        if agent_id:
            q_parts.append(f"agent.id={agent_id}")
        if since_seconds:
            # Wazuh accepte une query temporelle via 'q' si le champ existe
            # Alternative : filtrer côté client après récupération
            pass
        if q_parts:
            params["q"] = " AND ".join(q_parts)

        try:
            data = self._request("GET", "/alerts", params=params)
        except WazuhError as e:
            # Endpoint /alerts peut ne pas être exposé sur toutes les versions
            logger.warning(f"/alerts indisponible : {e}")
            return []

        return data.get("data", {}).get("affected_items", [])

    def get_recent_alerts(
        self,
        since_seconds: int = 300,
        min_level: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Récupère les alertes des N dernières secondes."""
        cutoff = time.time() - since_seconds
        alerts = self.get_alerts(min_level=min_level)
        filtered = []
        for a in alerts:
            ts_str = a.get("timestamp", "")
            try:
                # Wazuh : "2026-11-13T12:00:00.000+0000"
                from datetime import datetime, timezone
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts.timestamp() >= cutoff:
                    filtered.append(a)
            except Exception:
                filtered.append(a)  # en cas de doute, on garde
        return filtered


# ----------------------------------------------------------------------
# Singleton
# ----------------------------------------------------------------------
_client: Optional[WazuhClient] = None


def get_wazuh_client() -> WazuhClient:
    global _client
    if _client is None:
        _client = WazuhClient()
    return _client