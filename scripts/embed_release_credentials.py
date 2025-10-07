#!/usr/bin/env python3
"""Embed telemetry credentials for release builds.

Usage:
    COMMUNITY_CREDENTIALS="<base64-json>" python scripts/embed_release_credentials.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_FILE = PROJECT_ROOT / "zen" / "telemetry" / "embedded_credentials.py"


def main() -> int:
    encoded = os.getenv("COMMUNITY_CREDENTIALS", "").strip()
    if not encoded:
        print(
            "COMMUNITY_CREDENTIALS is not set. Set the base64-encoded "
            "service-account JSON before running this script.",
            file=sys.stderr,
        )
        return 1

    try:
        decoded = base64.b64decode(encoded)
        info = json.loads(decoded)
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Failed to decode telemetry credentials: {exc}", file=sys.stderr)
        return 2

    project_id = info.get("project_id", "netra-telemetry-public")
    encoded_literal = repr(encoded)

    generated = f'''"""Embedded telemetry credentials. AUTO-GENERATED - DO NOT COMMIT."""

import base64
import json
from google.oauth2 import service_account

_EMBEDDED_CREDENTIALS_B64 = {encoded_literal}
_CREDENTIALS_DICT = json.loads(
    base64.b64decode(_EMBEDDED_CREDENTIALS_B64.encode("utf-8"))
)


def get_embedded_credentials():
    """Return service account credentials."""
    try:
        return service_account.Credentials.from_service_account_info(
            _CREDENTIALS_DICT,
            scopes=["https://www.googleapis.com/auth/trace.append"],
        )
    except Exception:
        return None


def get_project_id() -> str:
    """Return GCP project ID."""
    return _CREDENTIALS_DICT.get("project_id", {project_id!r})
'''

    TARGET_FILE.write_text(generated)
    print(f"Embedded release credentials written to {TARGET_FILE.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
