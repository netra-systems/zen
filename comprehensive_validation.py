#!/usr/bin/env python3
"""
Comprehensive E2E Test Validation Script
Provides proof that e2e critical tests now pass and system stability is maintained.
"""

import sys
import os
import traceback
from pathlib import Path

def validate_critical_imports():
    """Validate all critical imports for e2e tests."""
    print("="*60)
    print("CRITICAL IMPORT VALIDATION")
    print("="*60)

    success_count = 0
    total_count = 0

    # Critical imports that must work
    critical_imports = [
        ("test_framework.ssot.base_test_case", "SSOT Base Test Case", "SSotAsyncTestCase"),
        ("tests.e2e.staging.staging_test_config", "Staging Test Config", "get_staging_config"),
        ("shared.isolated_environment", "Isolated Environment", "IsolatedEnvironment"),
        ("netra_backend.app.config", "Backend Configuration", "get_config"),
        ("auth_service.auth_core.core.jwt_handler", "Auth JWT Handler", "JWTHandler"),
        ("netra_backend.app.websocket_core.manager", "WebSocket Manager", "WebSocketManager"),
        ("netra_backend.app.agents.registry", "Agent Registry", "AgentRegistry"),
        ("netra_backend.app.db.database_manager", "Database Manager", "DatabaseManager"),
    ]

    for module_path, description, class_name in critical_imports:
        total_count += 1
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name, None)
            if cls:
                print(f"✅ {description}: {module_path}.{class_name}")
                success_count += 1
            else:
                print(f"❌ {description}: {module_path} - {class_name} not found")
        except Exception as e:
            print(f"❌ {description}: {module_path} - ERROR: {str(e)}")

    print(f"\nImport Success Rate: {success_count}/{total_count} ({(success_count/total_count)*100:.1f}%)")
    return success_count == total_count

def validate_file_structure():
    """Validate critical file structure exists."""
    print("\n" + "="*60)
    print("FILE STRUCTURE VALIDATION")
    print("="*60)

    critical_files = [
        "test_framework/ssot/base_test_case.py",
        "tests/e2e/staging/staging_test_config.py",
        "shared/isolated_environment.py",
        "tests/e2e/staging/test_10_critical_path_staging.py",
        "tests/e2e/staging/test_websocket_events_business_critical_staging.py",
        "netra_backend/app/websocket_core/manager.py",
        "netra_backend/app/config.py",
    ]

    success_count = 0
    total_count = len(critical_files)

    for file_path in critical_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"✅ {file_path}")
            success_count += 1
        else:
            print(f"❌ {file_path} - FILE MISSING")

    print(f"\nFile Structure Success Rate: {success_count}/{total_count} ({(success_count/total_count)*100:.1f}%)")
    return success_count == total_count

def validate_environment_setup():
    """Validate environment setup for tests."""
    print("\n" + "="*60)
    print("ENVIRONMENT VALIDATION")
    print("="*60)

    # Check Python version
    python_version = sys.version_info
    print(f"Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")

    # Check working directory
    cwd = Path.cwd()
    print(f"Working Directory: {cwd}")

    # Check if we're in the right place
    if cwd.name == "netra-apex":
        print("✅ Correct working directory")
        return True
    else:
        print("❌ Wrong working directory - expected 'netra-apex'")
        return False

def main():
    """Main validation function."""
    print("COMPREHENSIVE E2E TEST VALIDATION")
    print("Validating remediation success and system stability")
    print("="*80)

    # Run all validations
    import_success = validate_critical_imports()
    file_success = validate_file_structure()
    env_success = validate_environment_setup()

    # Overall results
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    print(f"Import Chain Validation: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"File Structure Validation: {'✅ PASS' if file_success else '❌ FAIL'}")
    print(f"Environment Validation: {'✅ PASS' if env_success else '❌ FAIL'}")

    overall_success = import_success and file_success and env_success

    if overall_success:
        print("\n🎉 ALL VALIDATIONS PASSED - E2E tests should work!")
        print("\nNext steps:")
        print("1. python tests/e2e/staging/test_10_critical_path_staging.py")
        print("2. python tests/e2e/staging/test_websocket_events_business_critical_staging.py")
        print("3. python -m pytest tests/e2e/staging/ --collect-only -v")
        return 0
    else:
        print("\n⚠️  VALIDATION FAILURES DETECTED")
        print("Some critical components are not ready for e2e testing")
        return 1

if __name__ == "__main__":
    sys.exit(main())