#!/usr/bin/env python3
"""Embed community telemetry credentials for release builds.

During packaging we want the wheel to contain a baked-in service account so
end users get telemetry automatically, but we never commit that secret. This
script rewrites ``zen/telemetry/embedded_credentials.py`` with an embedded
payload derived from ``COMMUNITY_CREDENTIALS`` (base64-encoded JSON).

Usage:
    COMMUNITY_CREDENTIALS="..." python scripts/embed_release_credentials.py

Run this immediately before ``python -m build`` and restore the file afterwards
with ``git checkout -- zen/telemetry/embedded_credentials.py``.
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

    generated = f'''"""Embedded community telemetry credentials.

    AUTO-GENERATED DURING RELEASE PACKAGING. DO NOT COMMIT THIS FILE.
    """

import base64
import json
from google.oauth2 import service_account

_EMBEDDED_CREDENTIALS_B64 = {encoded_literal}
_CREDENTIALS_DICT = json.loads(
    base64.b64decode(_EMBEDDED_CREDENTIALS_B64.encode("utf-8"))
)


def get_embedded_credentials():
    """Return service-account credentials for community telemetry."""
    try:
        return service_account.Credentials.from_service_account_info(
            _CREDENTIALS_DICT,
            scopes=["https://www.googleapis.com/auth/trace.append"],
        )
    except Exception:  # pragma: no cover - defensive guard
        return None


def get_project_id() -> str:
    """Return the project ID baked into the release credentials."""
    return _CREDENTIALS_DICT.get("project_id", {project_id!r})
'''

    TARGET_FILE.write_text(generated)
    print(f"Embedded release credentials written to {TARGET_FILE.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
