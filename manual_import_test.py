#!/usr/bin/env python3
"""
Manual Import Test - Execute validation logic directly

This manually executes the import validation without requiring subprocess execution.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("🚀 Manual Import Validation")
print("=" * 50)
print(f"Working Directory: {Path.cwd()}")
print(f"Project Root: {project_root}")
print(f"Python Path: {sys.path[:3]}...")  # Show first 3 entries
print("")

# Test critical imports step by step
critical_imports = [
    'os',
    'sys',
    'pathlib',
    'shared.isolated_environment',
    'netra_backend.app.core.environment_constants',
    'netra_backend.app.schemas.config',
    'netra_backend.app.core.configuration.base',
    'netra_backend.app.config',
]

results = []

for module_name in critical_imports:
    print(f"Testing: {module_name}... ", end="")

    try:
        # Clear module cache
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Test import
        __import__(module_name)
        print("✅ SUCCESS")
        results.append((module_name, True, None))

    except Exception as e:
        print(f"❌ FAILED: {e}")
        results.append((module_name, False, str(e)))
        # Stop at first failure
        break

print("")
print("=" * 50)
print("RESULTS SUMMARY")
print("=" * 50)

success_count = sum(1 for _, success, _ in results if success)
total_count = len(results)

print(f"Successful imports: {success_count}/{total_count}")

if success_count == total_count:
    print("✅ ALL CRITICAL IMPORTS SUCCESSFUL")
else:
    print("❌ IMPORT FAILURES DETECTED")

    for module_name, success, error in results:
        if not success:
            print(f"  - {module_name}: {error}")

print("")
print("RECOMMENDATION:")
if success_count == total_count:
    print("✅ System is ready - all critical imports work")
    print("   → Run comprehensive tests")
    print("   → Deploy to staging")
else:
    print("🚨 CRITICAL ISSUES - System cannot start")
    print("   → Fix missing dependencies")
    print("   → Check project structure")
    print("   → Verify Python environment")

print(f"\nCompleted: {datetime.now().isoformat()}")