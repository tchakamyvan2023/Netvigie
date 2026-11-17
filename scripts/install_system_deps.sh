#!/usr/bin/env bash
# ============================================================
# NETVIGIE — Installation des dépendances système
# Supporte : Ubuntu, Debian, Amazon Linux, RHEL, Fedora
# Usage    : sudo bash scripts/install_system_deps.sh
# ============================================================

set -euo pipefail

LOG_FILE="${LOG_FILE:-/var/log/netvigie-install.log}"
mkdir -p "$(dirname "$LOG_FILE")"

log()  { echo -e "\033[1;34m[NETVIGIE]\033[0m $*" | tee -a "$LOG_FILE"; }
ok()   { echo -e "\033[1;32m[OK]\033[0m $*"       | tee -a "$LOG_FILE"; }
err()  { echo -e "\033[1;31m[ERR]\033[0m $*"      | tee -a "$LOG_FILE"; }

if [[ $EUID -ne 0 ]]; then
    err "Ce script doit être exécuté en root (sudo)."
    exit 1
fi

# --- Détection de la distribution ---
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
log "Distribution détectée : $DISTRO"

install_apt() {
    log "Mise à jour apt..."
    apt-get update -y

    log "Installation des paquets via apt..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        postgresql \
        postgresql-contrib \
        redis-server \
        curl \
        wget \
        git \
        jq \
        net-tools \
        iputils-ping \
        build-essential \
        libpq-dev \
        ca-certificates
    ok "Paquets apt installés."
}

install_dnf() {
    log "Mise à jour dnf..."
    dnf -y makecache

    log "Installation des paquets via dnf..."
    dnf install -y \
        python3 \
        python3-pip \
        postgresql-server \
        postgresql-contrib \
        redis \
        curl \
        wget \
        git \
        jq \
        net-tools \
        iputils \
        gcc \
        gcc-c++ \
        make \
        postgresql-devel \
        ca-certificates

    # Initialisation de PostgreSQL si nécessaire (Amazon Linux / RHEL)
    if command -v postgresql-setup >/dev/null 2>&1; then
        postgresql-setup --initdb || true
    fi

    ok "Paquets dnf installés."
}

case "$DISTRO" in
    ubuntu|debian)
        install_apt
        ;;
    amzn|rhel|fedora|centos)
        install_dnf
        ;;
    *)
        err "Distribution non supportée : $DISTRO"
        exit 1
        ;;
esac

# --- Node.js >= 18 si absent ou trop ancien ---
install_node_if_needed() {
    local need_install=0
    if ! command -v node >/dev/null 2>&1; then
        need_install=1
    else
        local major
        major=$(node --version | sed 's/v//' | cut -d. -f1)
        if [[ "$major" -lt 18 ]]; then
            need_install=1
        fi
    fi

    if [[ $need_install -eq 1 ]]; then
        log "Installation de Node.js 20 via NodeSource..."
        case "$DISTRO" in
            ubuntu|debian)
                curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
                apt-get install -y nodejs
                ;;
            amzn|rhel|fedora|centos)
                curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
                dnf install -y nodejs
                ;;
        esac
        ok "Node.js installé : $(node --version)"
    else
        ok "Node.js déjà présent : $(node --version)"
    fi
}

install_node_if_needed

# --- Démarrage des services ---
log "Démarrage de PostgreSQL et Redis..."
systemctl enable --now postgresql 2>/dev/null || systemctl enable --now postgresql-server 2>/dev/null || true
systemctl enable --now redis 2>/dev/null || systemctl enable --now redis-server 2>/dev/null || true

ok "Installation système terminée."