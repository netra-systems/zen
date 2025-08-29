#!/usr/bin/env python3
"""
Protect staging configuration from localhost defaults.
This script ensures ClickHouse configs don't default to localhost.
"""

import sys
import re
from pathlib import Path

def check_config_file(filepath: Path) -> list[str]:
    """Check config.py for localhost defaults in ClickHouse configs."""
    violations = []
    
    if not filepath.exists():
        return violations
    
    content = filepath.read_text()
    
    # Check for localhost defaults in ClickHouse configs
    patterns = [
        (r'class ClickHouseNativeConfig.*?\n.*?host:\s*str\s*=\s*["\']localhost["\']', 
         'ClickHouseNativeConfig must not default to localhost'),
        (r'class ClickHouseHTTPConfig.*?\n.*?host:\s*str\s*=\s*["\']localhost["\']',
         'ClickHouseHTTPConfig must not default to localhost'),
        (r'class ClickHouseHTTPSConfig.*?\n.*?host:\s*str\s*=\s*["\']localhost["\']',
         'ClickHouseHTTPSConfig must not default to localhost'),
    ]
    
    for pattern, message in patterns:
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            violations.append(message)
    
    return violations

def main():
    """Main entry point for config protection."""
    config_path = Path(__file__).parent.parent / "netra_backend" / "app" / "schemas" / "config.py"
    
    violations = check_config_file(config_path)
    
    if violations:
        print("[FAIL] Configuration Protection Failed!")
        print("\nThe following violations were found:")
        for violation in violations:
            print(f"  - {violation}")
        print("\nClickHouse configs must have empty string defaults for staging/production.")
        print("This ensures staging fails fast if CLICKHOUSE_HOST is not configured.")
        return 1
    
    print("[PASS] Configuration protection check passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())