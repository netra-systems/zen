#!/usr/bin/env python3
"""Helper for preparing community telemetry credentials.

Reads a service-account JSON key and prints a base64 string suitable for
`ZEN_COMMUNITY_TELEMETRY_B64`. The file itself is never modified, so secrets
stay outside version control.
"""

import argparse
import base64
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Encode a service-account key for telemetry")
    parser.add_argument("key_path", type=Path, help="Path to the service-account JSON file")
    args = parser.parse_args()

    key_path = args.key_path.expanduser()
    if not key_path.exists():
        parser.error(f"File not found: {key_path}")

    data = key_path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    print(encoded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
