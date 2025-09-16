#!/usr/bin/env python3
"""Issue #1264 runtime configuration audit.

Validates that the staging backend service is wired to the expected Cloud SQL
PostgreSQL instance and that DatabaseURLBuilder still emits asyncpg URLs.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

PROJECT = "netra-staging"
SERVICE = "netra-backend-staging"
REGION = "us-central1"
POSTGRES_SECRET_MAP = {
    "POSTGRES_HOST": "postgres-host-staging",
    "POSTGRES_PORT": "postgres-port-staging",
    "POSTGRES_DB": "postgres-db-staging",
    "POSTGRES_USER": "postgres-user-staging",
    "POSTGRES_PASSWORD": "postgres-password-staging",
}


def run_gcloud(args: list[str]) -> str:
    import os
    executable = "gcloud.cmd" if os.name == "nt" else "gcloud"
    cmd = [executable, *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gcloud {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


@dataclass
class SecretSnapshot:
    host: str
    port: str
    database: str
    user: str
    password: str

    def as_env(self) -> Dict[str, str]:
        return {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": self.host,
            "POSTGRES_PORT": self.port,
            "POSTGRES_DB": self.database,
            "POSTGRES_USER": self.user,
            "POSTGRES_PASSWORD": self.password,
        }


def fetch_backend_env() -> Dict[str, str]:
    raw = run_gcloud([
        "run",
        "services",
        "describe",
        SERVICE,
        "--region",
        REGION,
        "--project",
        PROJECT,
        "--format",
        "json",
    ])
    data = json.loads(raw)
    env_list = data["spec"]["template"]["spec"]["containers"][0]["env"]
    return {item["name"]: item.get("value") for item in env_list if "value" in item}


def fetch_postgres_secrets() -> SecretSnapshot:
    values: Dict[str, str] = {}
    for env_name, secret_name in POSTGRES_SECRET_MAP.items():
        value = run_gcloud([
            "secrets",
            "versions",
            "access",
            "latest",
            "--secret",
            secret_name,
            "--project",
            PROJECT,
        ])
        values[env_name] = value
    return SecretSnapshot(
        host=values["POSTGRES_HOST"],
        port=values["POSTGRES_PORT"],
        database=values["POSTGRES_DB"],
        user=values["POSTGRES_USER"],
        password=values["POSTGRES_PASSWORD"],
    )


def mask_secret(value: str, keep: int = 2) -> str:
    if not value:
        return "<empty>"
    visible = value[:keep]
    return f"{visible}{'*' * max(len(value) - keep, 0)}"


def validate_snapshot(snapshot: SecretSnapshot) -> Tuple[bool, list[str]]:
    issues: list[str] = []
    if not snapshot.host.startswith("/cloudsql/"):
        issues.append("POSTGRES_HOST missing /cloudsql/ prefix")
    if "staging-shared-postgres" not in snapshot.host:
        issues.append("POSTGRES_HOST does not target staging-shared-postgres instance")
    if snapshot.port != "5432":
        issues.append(f"POSTGRES_PORT expected 5432, got {snapshot.port}")
    if not snapshot.database:
        issues.append("POSTGRES_DB is empty")
    if not snapshot.user:
        issues.append("POSTGRES_USER is empty")
    if not snapshot.password:
        issues.append("POSTGRES_PASSWORD is empty")
    return (not issues, issues)


def verify_database_url(snapshot: SecretSnapshot) -> Tuple[bool, str]:
    from shared.database_url_builder import DatabaseURLBuilder

    builder = DatabaseURLBuilder(snapshot.as_env())
    url = builder.get_url_for_environment(sync=False)
    if not url:
        return False, "DatabaseURLBuilder produced empty URL"
    if not url.startswith("postgresql+asyncpg://"):
        return False, f"Unexpected driver: {url.split('://', 1)[0]}"
    return True, url


def main() -> int:
    try:
        env_vars = fetch_backend_env()
        snapshot = fetch_postgres_secrets()
    except RuntimeError as err:
        print(f"ERROR: {err}")
        return 1

    ok, issues = validate_snapshot(snapshot)
    try:
        url_ok, url_value = verify_database_url(snapshot)
    except Exception as exc:  # pylint: disable=broad-except
        url_ok = False
        url_value = f"failed to build URL: {exc}"

    print("=== Issue #1264 Staging Database Audit ===")
    print(f"Service env (cached values):")
    for key in ("ENVIRONMENT", "DATABASE_URL", "SQLALCHEMY_DATABASE_URI"):
        if key in env_vars:
            print(f"  {key}: {env_vars[key]}")
    print("Secrets snapshot:")
    print(f"  POSTGRES_HOST: {snapshot.host}")
    print(f"  POSTGRES_PORT: {snapshot.port}")
    print(f"  POSTGRES_DB: {snapshot.database}")
    print(f"  POSTGRES_USER: {snapshot.user}")
    print(f"  POSTGRES_PASSWORD: {mask_secret(snapshot.password)}")

    if issues:
        print("Configuration issues detected:")
        for item in issues:
            print(f"  - {item}")
    else:
        print("Configuration snapshot looks consistent with expected staging settings.")

    if url_ok:
        from shared.database_url_builder import DatabaseURLBuilder as _Builder
        masked_url = _Builder.mask_url_for_logging(url_value)
        print(f"DatabaseURLBuilder output: {masked_url}")
    else:
        print(f"DatabaseURLBuilder validation FAILED: {url_value}")

    if ok and url_ok:
        print("Audit result: PASS")
        return 0
    print("Audit result: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
