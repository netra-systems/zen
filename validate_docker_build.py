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
        print(f"❌ ERROR: Monitoring module not found at {monitoring_path}")
        return False

    init_file = monitoring_path / "__init__.py"
    if not init_file.exists():
        print(f"❌ ERROR: __init__.py not found in monitoring module")
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
            print(f"❌ ERROR: Key monitoring file missing: {file_name}")
            return False

    print(f"✅ Monitoring module validated at {monitoring_path}")
    print(f"✅ Found {len(list(monitoring_path.glob('*.py')))} Python files")
    return True

def validate_dockerignore():
    """Validate .dockerignore configuration."""
    dockerignore_path = Path(".dockerignore")

    if not dockerignore_path.exists():
        print("❌ ERROR: .dockerignore file not found")
        return False

    with open(dockerignore_path, 'r') as f:
        content = f.read()

    # Check for monitoring exclusion override
    if "!netra_backend/app/services/monitoring/" not in content:
        print("❌ ERROR: .dockerignore missing monitoring override")
        return False

    print("✅ .dockerignore properly configured for monitoring module")
    return True

def validate_dockerfile():
    """Validate Dockerfile has explicit monitoring COPY."""
    dockerfile_path = Path("dockerfiles/backend.staging.alpine.Dockerfile")

    if not dockerfile_path.exists():
        print("❌ ERROR: Dockerfile not found")
        return False

    with open(dockerfile_path, 'r') as f:
        content = f.read()

    if "COPY netra_backend/app/services/monitoring/" not in content:
        print("❌ ERROR: Dockerfile missing explicit monitoring COPY command")
        return False

    print("✅ Dockerfile has explicit monitoring COPY command")
    return True

def simulate_build_context():
    """Simulate what files would be included in Docker build context."""
    print("\nBuild Context Simulation:")

    # Check what would be copied by netra_backend/ command
    backend_path = Path("netra_backend")
    if backend_path.exists():
        monitoring_in_backend = backend_path / "app" / "services" / "monitoring"
        if monitoring_in_backend.exists():
            print(f"✅ Monitoring found in netra_backend/ tree")
            file_count = len(list(monitoring_in_backend.glob("*.py")))
            print(f"   - {file_count} Python files would be copied")
        else:
            print(f"❌ Monitoring NOT found in netra_backend/ tree")

    return True

def main():
    """Main validation routine."""
    print("Docker Build Validation for Monitoring Module Fix")
    print("=" * 60)

    os.chdir(Path(__file__).parent)

    checks = [
        ("Local Monitoring Module", validate_monitoring_module_exists),
        (".dockerignore Configuration", validate_dockerignore),
        ("Dockerfile Explicit COPY", validate_dockerfile),
        ("Build Context Simulation", simulate_build_context),
    ]

    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            result = check_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ ERROR during {check_name}: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL VALIDATIONS PASSED - Docker build should include monitoring module")
        print("\nSafe to deploy with fixed Dockerfile")
        return 0
    else:
        print("VALIDATION FAILURES - Docker build may still fail")
        print("\nDO NOT DEPLOY until issues are resolved")
        return 1

if __name__ == "__main__":
    sys.exit(main())