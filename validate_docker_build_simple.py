#!/usr/bin/env python3
"""
Docker Build Validation Script for Monitoring Module Fix
Validates that the monitoring module will be included in Docker builds.
"""

import os
import subprocess
import sys
from pathlib import Path

def validate_monitoring_module_exists():
    """Validate that monitoring module exists locally."""
    monitoring_path = Path("netra_backend/app/services/monitoring")

    if not monitoring_path.exists():
        print(f"ERROR: Monitoring module not found at {monitoring_path}")
        return False

    init_file = monitoring_path / "__init__.py"
    if not init_file.exists():
        print(f"ERROR: __init__.py not found in monitoring module")
        return False

    # Check for key monitoring files
    key_files = [
        "gcp_error_reporter.py",
        "error_tracker.py",
        "gcp_error_service.py",
        "metrics_service.py"
    ]

    for file_name in key_files:
        file_path = monitoring_path / file_name
        if not file_path.exists():
            print(f"ERROR: Key monitoring file missing: {file_name}")
            return False

    print(f"PASS: Monitoring module validated at {monitoring_path}")
    print(f"PASS: Found {len(list(monitoring_path.glob('*.py')))} Python files")
    return True

def validate_dockerfile():
    """Validate Dockerfile has explicit monitoring COPY."""
    dockerfile_path = Path("dockerfiles/backend.staging.alpine.Dockerfile")

    if not dockerfile_path.exists():
        print("ERROR: Dockerfile not found")
        return False

    with open(dockerfile_path, 'r') as f:
        content = f.read()

    if "COPY netra_backend/app/services/monitoring/" not in content:
        print("ERROR: Dockerfile missing explicit monitoring COPY command")
        return False

    print("PASS: Dockerfile has explicit monitoring COPY command")
    return True

def main():
    """Main validation routine."""
    print("Docker Build Validation for Monitoring Module Fix")
    print("=" * 60)

    os.chdir(Path(__file__).parent)

    print("\nStep 1: Validate monitoring module exists locally")
    if not validate_monitoring_module_exists():
        print("FAIL: Local monitoring module validation failed")
        return 1

    print("\nStep 2: Validate Dockerfile has explicit COPY")
    if not validate_dockerfile():
        print("FAIL: Dockerfile validation failed")
        return 1

    print("\n" + "=" * 60)
    print("SUCCESS: All validations passed - monitoring module should be included")
    print("READY: Safe to deploy with fixed Dockerfile")
    return 0

if __name__ == "__main__":
    sys.exit(main())