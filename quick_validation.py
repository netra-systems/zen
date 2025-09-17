#!/usr/bin/env python3
"""
Quick System Validation Script
Validates that critical system components can be imported and basic functionality works.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def validate_imports():
    """Test critical imports"""
    results = {}

    test_imports = [
        ("unified_test_runner", "tests.unified_test_runner"),
        ("websocket_manager", "netra_backend.app.websocket_core.manager"),
        ("config", "netra_backend.app.config"),
        ("database_manager", "netra_backend.app.db.database_manager"),
        ("auth_integration", "netra_backend.app.auth_integration.auth"),
        ("agent_registry", "netra_backend.app.agents.supervisor.agent_registry"),
    ]

    for name, module_path in test_imports:
        try:
            __import__(module_path)
            results[name] = "✅ SUCCESS"
            print(f"✅ {name}: Import successful")
        except Exception as e:
            results[name] = f"❌ FAILED: {str(e)}"
            print(f"❌ {name}: Import failed - {str(e)}")

    return results

def validate_basic_functionality():
    """Test basic functionality without external dependencies"""
    results = {}

    # Test 1: Config loading
    try:
        from netra_backend.app.config import get_config
        config = get_config()
        results["config_loading"] = "✅ SUCCESS"
        print(f"✅ Config loading: Environment = {getattr(config, 'environment', 'unknown')}")
    except Exception as e:
        results["config_loading"] = f"❌ FAILED: {str(e)}"
        print(f"❌ Config loading failed: {str(e)}")

    # Test 2: Test runner basic functionality
    try:
        import tests.unified_test_runner as test_runner
        # Just check if main structures exist
        if hasattr(test_runner, 'main'):
            results["test_runner"] = "✅ SUCCESS"
            print("✅ Test runner: Basic structure available")
        else:
            results["test_runner"] = "❌ FAILED: Missing main function"
            print("❌ Test runner: Missing main function")
    except Exception as e:
        results["test_runner"] = f"❌ FAILED: {str(e)}"
        print(f"❌ Test runner failed: {str(e)}")

    return results

def validate_test_infrastructure():
    """Validate test infrastructure without running tests"""
    results = {}

    # Check if key test files exist
    test_files = [
        "tests/smoke/test_startup_wiring_smoke.py",
        "tests/mission_critical/test_websocket_agent_events_suite.py",
        "tests/golden_path/run_golden_path_validation.py",
        "netra_backend/tests/startup/test_configuration_drift_detection.py"
    ]

    for test_file in test_files:
        file_path = PROJECT_ROOT / test_file
        if file_path.exists():
            results[test_file] = "✅ EXISTS"
            print(f"✅ {test_file}: File exists")
        else:
            results[test_file] = "❌ MISSING"
            print(f"❌ {test_file}: File missing")

    return results

def main():
    """Run quick validation"""
    print("🔍 QUICK SYSTEM VALIDATION")
    print("=" * 50)

    print("\n📦 IMPORT VALIDATION")
    print("-" * 30)
    import_results = validate_imports()

    print("\n⚙️ BASIC FUNCTIONALITY")
    print("-" * 30)
    func_results = validate_basic_functionality()

    print("\n🧪 TEST INFRASTRUCTURE")
    print("-" * 30)
    test_results = validate_test_infrastructure()

    # Summary
    print("\n📊 SUMMARY")
    print("=" * 50)

    all_results = {**import_results, **func_results, **test_results}
    success_count = sum(1 for v in all_results.values() if v.startswith("✅"))
    total_count = len(all_results)

    print(f"✅ Successful: {success_count}/{total_count}")
    print(f"❌ Failed: {total_count - success_count}/{total_count}")

    if success_count == total_count:
        print("\n🎉 ALL VALIDATIONS PASSED - System appears ready for testing")
        return 0
    else:
        print("\n⚠️ SOME VALIDATIONS FAILED - Issues detected")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        traceback.print_exc()
        sys.exit(1)