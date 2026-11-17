#!/usr/bin/env python3
"""
NETVIGIE — Vérification de l'environnement
Vérifie la présence des composants requis sans rien installer.
Utilisable seul : python3 scripts/check_env.py
"""
import os
import sys
import shutil
import subprocess
import json

REQUIRED = {
    "python": {"min_version": (3, 10)},
    "pip": {},
    "node": {"min_version": (18, 0)},
    "npm": {},
    "psql": {},
    "redis-server": {},
    "systemctl": {},
}

def run(cmd, check=False):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=10)
    except Exception:
        return None

def get_version(cmd):
    out = run(cmd)
    if out and out.returncode == 0:
        return out.stdout.strip().split("\n")[0]
    return None

def check_python_version():
    v = sys.version_info
    return (v.major, v.minor) >= REQUIRED["python"]["min_version"]

def check_binary(name):
    return shutil.which(name) is not None

def check_os():
    try:
        with open("/etc/os-release") as f:
            data = f.read()
        for line in data.split("\n"):
            if line.startswith("ID="):
                return line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    return "unknown"

def check_package_manager():
    if shutil.which("apt"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("yum"):
        return "yum"
    return None

def check_service(name):
    out = run(["systemctl", "is-active", name])
    if out and out.returncode == 0:
        return out.stdout.strip() == "active"
    return False

def check_port(host, port, timeout=2):
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def main():
    report = {
        "os": check_os(),
        "package_manager": check_package_manager(),
        "python": {
            "ok": check_python_version(),
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        "binaries": {},
        "services": {
            "postgresql": check_service("postgresql"),
            "redis-server": check_service("redis-server") or check_service("redis"),
        },
        "ports": {
            "postgresql_5432": check_port("127.0.0.1", 5432),
            "redis_6379": check_port("127.0.0.1", 6379),
        },
    }

    for bin_name in ["pip", "pip3", "node", "npm", "psql", "redis-server", "systemctl", "git", "curl"]:
        report["binaries"][bin_name] = check_binary(bin_name)

    # Node version
    if report["binaries"]["node"]:
        v = get_version(["node", "--version"])
        report["node_version"] = v
        try:
            major = int(v.lstrip("v").split(".")[0])
            report["node_ok"] = major >= 18
        except Exception:
            report["node_ok"] = False
    else:
        report["node_version"] = None
        report["node_ok"] = False

    report["ok"] = (
        report["python"]["ok"]
        and report["package_manager"] is not None
        and report["binaries"]["psql"]
        and report["binaries"]["redis-server"]
        and report["services"]["postgresql"]
        and report["services"]["redis-server"]
        and report["node_ok"]
    )

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    sys.exit(main())