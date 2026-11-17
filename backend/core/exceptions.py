"""NETVIGIE — Exceptions métier."""


class NetvigieError(Exception):
    """Exception de base."""


class WazuhError(NetvigieError):
    """Erreur de communication avec Wazuh."""


class ConfigurationError(NetvigieError):
    """Erreur de configuration."""


class NotFoundError(NetvigieError):
    """Ressource introuvable."""


class PermissionDenied(NetvigieError):
    """Permission refusée."""