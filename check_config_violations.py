#!/usr/bin/env python3
"""Quick script to check configuration SSOT violations."""

import os
import re
from pathlib import Path

def check_configuration_ssot_violations():
    """Check for configuration SSOT violations."""

    # Pattern to find: from netra_backend.app.core.configuration.base import
    violation_pattern = re.compile(r'from\s+netra_backend\.app\.core\.configuration\.base\s+import')

    violations = []

    # Search in netra_backend directory
    backend_dir = Path("netra_backend")
    if backend_dir.exists():
        for py_file in backend_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if violation_pattern.search(content):
                        violations.append(str(py_file))
            except Exception as e:
                print(f"Error reading {py_file}: {e}")

    return violations

if __name__ == "__main__":
    os.chdir("/c/netra-apex")
    violations = check_configuration_ssot_violations()

    print(f"Configuration SSOT violations found: {len(violations)}")
    for violation in violations:
        print(f"  - {violation}")

    if not violations:
        print("✅ No configuration SSOT violations found!")