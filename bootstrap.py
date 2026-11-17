#!/usr/bin/env python3
"""
============================================================
NETVIGIE — Bootstrap autonome
============================================================
Détecte l'environnement, vérifie les prérequis, installe les
composants manquants, configure PostgreSQL et Redis, prépare
l'environnement Python et Node.js, génère .env, initialise la
base de données, et produit un rapport.

Usage :
    sudo python3 bootstrap.py
    sudo python3 bootstrap.py --skip-system     # skip apt/dnf
    sudo python3 bootstrap.py --dry-run         # vérification seule

Idempotent : peut être relancé sans casser l'existant.
============================================================
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import secrets
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------
# Constantes
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
BOOTSTRAP_LOG = LOG_DIR / "bootstrap.log"

REPORT = {
    "timestamp": datetime.utcnow().isoformat(),
    "os": None,
    "package_manager": None,
    "steps": [],
}

# ------------------------------------------------------------
# Helpers d'affichage
# ------------------------------------------------------------
def log(msg, level="INFO"):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    symbols = {"INFO": "→", "OK": "✓", "WARN": "⚠", "ERR": "✗", "STEP": "▶"}
    colors = {"INFO": "\033[1;34m", "OK": "\033[1;32m", "WARN": "\033[1;33m",
              "ERR": "\033[1;31m", "STEP": "\033[1;36m"}
    reset = "\033[0m"
    line = f"{colors.get(level, '')}{symbols.get(level, '·')}{reset} [{ts}] {msg}"
    print(line)
    with open(BOOTSTRAP_LOG, "a") as f:
        f.write(f"[{level}] [{ts}] {msg}\n")

def step(name):
    log(f"=== {name} ===", "STEP")
    REPORT["steps"].append({"name": name, "status": "running", "details": []})

def step_ok(detail=""):
    REPORT["steps"][-1]["status"] = "ok"
    if detail:
        REPORT["steps"][-1]["details"].append(detail)
        log(detail, "OK")

def step_err(detail=""):
    REPORT["steps"][-1]["status"] = "error"
    if detail:
        REPORT["steps"][-1]["details"].append(detail)
        log(detail, "ERR")

def run(cmd, check=False, timeout=300):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              check=check, timeout=timeout)
    except Exception as e:
        log(f"Commande échouée : {' '.join(cmd)} — {e}", "ERR")
        return None

def run_shell(cmd, check=False, timeout=600):
    return run(["bash", "-c", cmd], check=check, timeout=timeout)

# ------------------------------------------------------------
# Détection OS
# ------------------------------------------------------------
def detect_os():
    try:
        with open("/etc/os-release") as f:
            data = dict(line.strip().split("=", 1) for line in f if "=" in line)
        os_id = data.get("ID", "unknown").strip('"')
        REPORT["os"] = os_id
        return os_id
    except Exception:
        REPORT["os"] = "unknown"
        return "unknown"

def detect_package_manager():
    for pm in ["apt-get", "dnf", "yum"]:
        if shutil.which(pm):
            REPORT["package_manager"] = pm
            return pm
    return None

# ------------------------------------------------------------
# Vérifications
# ------------------------------------------------------------
def check_python():
    v = sys.version_info
    if (v.major, v.minor) >= (3, 10):
        step_ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    step_err(f"Python {v.major}.{v.minor} < 3.10")
    return False

def check_binary(name):
    return shutil.which(name) is not None

def check_service(name):
    out = run(["systemctl", "is-active", name])
    return out and out.returncode == 0 and out.stdout.strip() == "active"

def check_port(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def check_wazuh():
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        load_dotenv()
        url = os.getenv("WAZUH_API_URL", "https://192.168.1.50:55000")
        user = os.getenv("WAZUH_API_USER", "wazuh")
        pwd = os.getenv("WAZUH_API_PASSWORD", "wazuh")
        verify = os.getenv("WAZUH_API_VERIFY_SSL", "false").lower() == "true"
        r = requests.post(f"{url}/security/user/authenticate",
                          auth=(user, pwd), verify=verify, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def load_dotenv():
    try:
        from dotenv import load_dotenv as _ld
        _ld(PROJECT_ROOT / ".env")
    except ImportError:
        # fallback manuel
        env = PROJECT_ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

# ------------------------------------------------------------
# Étapes du bootstrap
# ------------------------------------------------------------
def step_detect():
    step("Détection de l'OS")
    os_id = detect_os()
    pm = detect_package_manager()
    if pm:
        step_ok(f"OS: {os_id}, package manager: {pm}")
    else:
        step_err(f"OS: {os_id}, aucun package manager détecté")

def step_install_system(skip=False):
    step("Installation des dépendances système")
    if skip:
        step_ok("Ignoré (--skip-system)")
        return
    script = PROJECT_ROOT / "scripts" / "install_system_deps.sh"
    if not script.exists():
        step_err(f"Script introuvable : {script}")
        return
    result = run(["bash", str(script)])
    if result and result.returncode == 0:
        step_ok("Dépendances système installées")
    else:
        stderr = result.stderr[-500:] if result and result.stderr else "?"
        step_err(f"Échec système (code {result.returncode if result else '?'}) : {stderr}")

def step_postgres():
    step("Configuration PostgreSQL")
    # Démarrer le service
    for svc in ["postgresql", "postgresql-server"]:
        if check_service(svc):
            break
        run(["systemctl", "enable", "--now", svc])

    if not check_port("127.0.0.1", 5432):
        step_err("PostgreSQL ne répond pas sur 5432")
        return

    # Créer user + db si absents
    sql = """
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'netvigie') THEN
      CREATE USER netvigie WITH PASSWORD 'Netvigie2026!';
   END IF;
END
$$;
"""
    # Utilisation de psql en tant que postgres
    check_db = run_shell(
        "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='netvigie'\""
    )
    if check_db and "1" in check_db.stdout:
        step_ok("Base 'netvigie' déjà présente")
    else:
        run_shell("sudo -u postgres psql -c \"CREATE USER netvigie WITH PASSWORD 'Netvigie2026!'\" || true")
        run_shell("sudo -u postgres psql -c \"CREATE DATABASE netvigie OWNER netvigie\" || true")
        run_shell("sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE netvigie TO netvigie\" || true")
        step_ok("Base 'netvigie' créée")

def step_redis():
    step("Configuration Redis")
    for svc in ["redis-server", "redis"]:
        if check_service(svc):
            break
        run(["systemctl", "enable", "--now", svc])

    if not check_port("127.0.0.1", 6379):
        step_err("Redis ne répond pas sur 6379")
        return
    step_ok("Redis actif sur 6379")

def step_python_deps():
    step("Installation des dépendances Python")

    # 1. Vérifier python3-venv
    check_venv = run(["python3", "-m", "venv", "--help"])
    if not check_venv or check_venv.returncode != 0:
        step_err("python3-venv manquant. Installation...")
        pm = REPORT["package_manager"]
        if pm == "apt-get":
            run(["apt-get", "update"])
            run(["apt-get", "install", "-y", "python3-venv", "python3-dev",
                 "libpq-dev", "build-essential"])
        elif pm in ("dnf", "yum"):
            run([pm, "install", "-y", "python3-devel", "postgresql-devel",
                 "gcc", "make"])

        check_venv = run(["python3", "-m", "venv", "--help"])
        if not check_venv or check_venv.returncode != 0:
            step_err("Impossible d'installer python3-venv")
            return

    # 2. Créer le venv
    venv = PROJECT_ROOT / "venv"
    if not (venv / "bin" / "pip").exists():
        if venv.exists():
            shutil.rmtree(venv)
        result = run([sys.executable, "-m", "venv", str(venv)])
        if not result or result.returncode != 0:
            step_err(f"Création du venv échouée : {result.stderr if result else '?'}")
            return

    # 3. Vérifier que pip existe
    pip = venv / "bin" / "pip"
    if not pip.exists():
        step_err("venv/bin/pip introuvable après création")
        return

    # 4. Installer les dépendances
    req = PROJECT_ROOT / "requirements.txt"
    if not req.exists():
        step_err("requirements.txt introuvable")
        return

    run([str(pip), "install", "--upgrade", "pip"], timeout=300)
    result = run([str(pip), "install", "-r", str(req)], timeout=900)
    if result and result.returncode == 0:
        step_ok("Dépendances Python installées")
    else:
        stderr = result.stderr[-500:] if result and result.stderr else "?"
        step_err(f"pip install échoué : {stderr}")

def step_node_deps():
    step("Installation des dépendances Frontend")
    frontend = PROJECT_ROOT / "frontend"
    if not (frontend / "package.json").exists():
        step_err("frontend/package.json introuvable (normal au Module 0)")
        return
    npm = shutil.which("npm")
    if not npm:
        step_err("npm introuvable")
        return
    result = run([npm, "install"], timeout=900)
    if result and result.returncode == 0:
        step_ok("Dépendances Node installées")
    else:
        step_err("npm install échoué")

def step_env():
    step("Génération du fichier .env")
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        step_ok(".env déjà présent")
        return
    example = PROJECT_ROOT / ".env.example"
    if not example.exists():
        step_err(".env.example introuvable")
        return
    content = example.read_text()
    # Génération d'une clé secrète
    secret = secrets.token_urlsafe(64)
    content = content.replace("CHANGEME_AVEC_UNE_CLE_ALEATOIRE_64_CARACTERES", secret)
    env_file.write_text(content)
    step_ok(".env généré")

def step_init_db():
    step("Initialisation de la base de données")
    init_script = PROJECT_ROOT / "scripts" / "init_db.py"
    if not init_script.exists():
        step_ok("scripts/init_db.py pas encore présent (Module 1)")
        return
    venv_py = PROJECT_ROOT / "venv" / "bin" / "python"
    result = run([str(venv_py), str(init_script)], timeout=120)
    if result and result.returncode == 0:
        step_ok("Base initialisée")
    else:
        step_err("Échec de l'initialisation")

def step_test_wazuh():
    step("Test de connectivité Wazuh")
    if not check_wazuh():
        step_err("Wazuh API inaccessible")
        return
    step_ok("Wazuh API accessible")

# ------------------------------------------------------------
# Rapport final
# ------------------------------------------------------------
def print_report():
    print()
    print("=" * 60)
    print("  RAPPORT D'INSTALLATION NETVIGIE")
    print("=" * 60)
    ok = 0
    err = 0
    for s in REPORT["steps"]:
        symbol = "✓" if s["status"] == "ok" else "✗"
        print(f"  {symbol} {s['name']:<45} {s['status']}")
        if s["status"] == "ok":
            ok += 1
        else:
            err += 1
    print("-" * 60)
    print(f"  {ok} étape(s) OK, {err} erreur(s)")
    print(f"  Log complet : {BOOTSTRAP_LOG}")
    print("=" * 60)
    (LOG_DIR / "bootstrap_report.json").write_text(json.dumps(REPORT, indent=2))
    return 0 if err == 0 else 1

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-system", action="store_true",
                        help="Ne pas installer les paquets système (apt/dnf)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Vérification seule, aucune installation")
    args = parser.parse_args()

    if os.geteuid() != 0 and not args.dry_run:
        log("Ce script doit être exécuté en root (sudo).", "ERR")
        return 1

    print("=" * 60)
    print("  NETVIGIE — Bootstrap autonome")
    print("=" * 60)
    print()

    step_detect()

    step("Vérification des prérequis")
    ok = check_python()
    for b in ["pip", "psql", "redis-server", "node", "npm", "git", "curl"]:
        if check_binary(b):
            step_ok(f"{b} présent")
        else:
            log(f"{b} manquant", "WARN")

    if args.dry_run:
        step("Mode --dry-run : arrêt")
        return print_report()

    step_install_system(skip=args.skip_system)
    step_postgres()
    step_redis()
    step_python_deps()
    step_node_deps()
    step_env()
    step_init_db()
    step_test_wazuh()

    return print_report()

if __name__ == "__main__":
    sys.exit(main())