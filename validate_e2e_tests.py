"""
Quick validation that all E2E tests can be imported and are syntactically correct.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

critical_tests = [
    "tests.unified.e2e.test_real_oauth_google_flow",
    "tests.unified.e2e.test_multi_tab_websocket",
    "tests.unified.e2e.test_concurrent_agent_load",
    "tests.unified.e2e.test_real_network_failure",
    "tests.unified.e2e.test_cross_service_transaction",
    "tests.unified.e2e.test_token_expiry_refresh",
    "tests.unified.e2e.test_file_upload_pipeline",
    "tests.unified.e2e.test_real_rate_limiting",
    "tests.unified.e2e.test_error_cascade_prevention",
    "tests.unified.e2e.test_memory_leak_detection",
]

def validate_imports():
    """Validate all test modules can be imported."""
    print("="*60)
    print("E2E TEST IMPORT VALIDATION")
    print("="*60)
    
    success_count = 0
    failed = []
    
    for test_module in critical_tests:
        test_name = test_module.split(".")[-1]
        try:
            __import__(test_module)
            print(f"[OK] {test_name}")
            success_count += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: {str(e)[:50]}")
            failed.append((test_name, str(e)))
    
    print("\n" + "="*60)
    print(f"Results: {success_count}/{len(critical_tests)} tests can be imported")
    
    if failed:
        print("\nFailed imports:")
        for name, error in failed:
            print(f"  - {name}: {error[:100]}")
    else:
        print("\nAll tests imported successfully!")
    
    return success_count == len(critical_tests)

if __name__ == "__main__":
    success = validate_imports()
    sys.exit(0 if success else 1)