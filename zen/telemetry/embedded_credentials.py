"""Runtime loader for optional community telemetry credentials.

No secrets should live in version control. This module looks for credentials
delivered at runtime (environment variables, mounted files, etc.) and returns
``None`` when nothing is provided so the caller can fall back gracefully.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account

_ENV_B64 = "COMMUNITY_CREDENTIALS"
_ENV_PATH = "ZEN_COMMUNITY_TELEMETRY_FILE"
_ENV_PROJECT = "ZEN_COMMUNITY_TELEMETRY_PROJECT"
_DEFAULT_PROJECT = "netra-telemetry-public"


def _load_service_account_dict() -> Optional[dict]:
    """Resolve service-account JSON payload provided at runtime."""
    encoded = os.getenv(_ENV_B64)
    if encoded:
        try:
            raw = base64.b64decode(encoded)
            return json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            return None

    path = os.getenv(_ENV_PATH)
    if path:
        candidate = Path(path).expanduser()
        if candidate.exists():
            try:
                return json.loads(candidate.read_text())
            except json.JSONDecodeError:
                return None
    return None


def get_embedded_credentials():
    """Return credentials built from runtime-provided service-account JSON."""
    info = _load_service_account_dict()
    if not info:
        return None
    try:
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/trace.append"],
        )
    except Exception:
        return None


def get_project_id() -> str:
    """Return the telemetry project configured for community analytics."""
    info = _load_service_account_dict()
    if info and "project_id" in info:
        return info["project_id"]
    return os.getenv(_ENV_PROJECT, _DEFAULT_PROJECT)
