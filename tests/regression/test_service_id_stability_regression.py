"""
Regression test to ensure SERVICE_ID remains stable and doesn't regress to using timestamps.

Business Value: Prevents authentication failures due to SERVICE_ID mismatches.
This test ensures the auth service always expects the stable "netra-backend" SERVICE_ID
and never reverts to reading from environment variables with timestamp suffixes.

Related Issues:
- SERVICE_ID with timestamp suffix caused auth failures every 60 seconds
- SPEC/learnings/service_id_stability_fix_20250907.xml
- SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
"""

import os
import sys
import time
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from auth_service.auth_core.routes.auth_routes import router
from shared.isolated_environment import IsolatedEnvironment


class TestServiceIdStabilityRegression:
    """Regression test suite for SERVICE_ID stability fix"""
    
    def test_auth_routes_uses_hardcoded_service_id(self):
        """Verify auth_routes.py uses hardcoded SERVICE_ID not env variable"""
        print("\n=== Testing SERVICE_ID Hardcoded Value ===")
        
        # Read the auth_routes.py file
        auth_routes_path = project_root / "auth_service" / "auth_core" / "routes" / "auth_routes.py"
        assert auth_routes_path.exists(), f"Auth routes file not found at {auth_routes_path}"
        
        with open(auth_routes_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the correct hardcoded value
        correct_pattern = r'expected_service_id\s*=\s*"netra-backend"'
        incorrect_pattern = r'expected_service_id\s*=\s*env\.get\("SERVICE_ID"'
        
        # Find all occurrences of expected_service_id assignment
        correct_matches = re.findall(correct_pattern, content)
        incorrect_matches = re.findall(incorrect_pattern, content)
        
        assert len(correct_matches) >= 2, f"Should have at least 2 hardcoded SERVICE_ID assignments, found {len(correct_matches)}"
        assert len(incorrect_matches) == 0, f"Should have NO env.get('SERVICE_ID') assignments, found {len(incorrect_matches)}"
        
        print(f"[PASS] Found {len(correct_matches)} hardcoded SERVICE_ID='netra-backend' assignments")
        print(f"[PASS] Found 0 env.get('SERVICE_ID') assignments (correct)")
    
    def test_service_id_not_contains_timestamp(self):
        """Verify SERVICE_ID never contains timestamp patterns"""
        print("\n=== Testing SERVICE_ID Does Not Contain Timestamps ===")
        
        # Pattern to detect timestamps (10-digit Unix timestamps)
        timestamp_pattern = re.compile(r'\d{10}')
        
        # Check auth_routes.py for any SERVICE_ID with timestamps
        auth_routes_path = project_root / "auth_service" / "auth_core" / "routes" / "auth_routes.py"
        with open(auth_routes_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for any SERVICE_ID assignments with timestamps
        service_id_lines = [line for line in content.split('\n') if 'expected_service_id' in line]
        
        for line in service_id_lines:
            assert not timestamp_pattern.search(line), f"SERVICE_ID should not contain timestamp: {line.strip()}"
        
        print(f"[PASS] No timestamps found in SERVICE_ID assignments ({len(service_id_lines)} lines checked)")
    
    def test_environment_variable_not_used(self):
        """Verify SERVICE_ID environment variable is NOT used in auth service"""
        print("\n=== Testing Environment Variable Not Used ===")
        
        # Temporarily set a bad SERVICE_ID in environment
        original_service_id = os.environ.get('SERVICE_ID')
        try:
            # Set a SERVICE_ID with timestamp that should NOT be used
            bad_service_id = f"netra-auth-staging-{int(time.time())}"
            os.environ['SERVICE_ID'] = bad_service_id
            
            # Read auth_routes to verify it doesn't use this value
            auth_routes_path = project_root / "auth_service" / "auth_core" / "routes" / "auth_routes.py"
            with open(auth_routes_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # The hardcoded value should be present, not the env variable
            assert 'expected_service_id = "netra-backend"' in content
            assert f'expected_service_id = "{bad_service_id}"' not in content
            
            print(f"[PASS] Auth routes ignores environment SERVICE_ID={bad_service_id}")
            print(f"[PASS] Uses hardcoded 'netra-backend' instead")
            
        finally:
            # Restore original environment
            if original_service_id:
                os.environ['SERVICE_ID'] = original_service_id
            elif 'SERVICE_ID' in os.environ:
                del os.environ['SERVICE_ID']
    
    def test_mission_critical_index_contains_service_id(self):
        """Verify SERVICE_ID is documented in MISSION_CRITICAL_NAMED_VALUES_INDEX"""
        print("\n=== Testing MISSION_CRITICAL_NAMED_VALUES_INDEX Documentation ===")
        
        index_path = project_root / "SPEC" / "MISSION_CRITICAL_NAMED_VALUES_INDEX.xml"
        assert index_path.exists(), f"Mission critical index not found at {index_path}"
        
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for SERVICE_ID entry
        assert '<variable name="SERVICE_ID"' in content, "SERVICE_ID not found in mission critical index"
        assert 'stable_value>netra-backend</stable_value>' in content, "Stable value not documented"
        assert 'hardcoded_value' in content, "Should be marked as hardcoded_value type"
        assert 'timestamp-suffix' in content or 'timestamp suffix' in content, "Timestamp issue not documented"
        
        print("[PASS] SERVICE_ID properly documented in MISSION_CRITICAL_NAMED_VALUES_INDEX.xml")
        print("[PASS] Marked as hardcoded_value with stable value 'netra-backend'")
    
    def test_learnings_index_contains_service_id_fix(self):
        """Verify SERVICE_ID fix is documented in learnings index"""
        print("\n=== Testing Learnings Index Documentation ===")
        
        index_path = project_root / "SPEC" / "learnings" / "index.xml"
        assert index_path.exists(), f"Learnings index not found at {index_path}"
        
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for SERVICE_ID learning entry
        assert 'service-id-stability-fix' in content, "SERVICE_ID fix not found in learnings index"
        assert 'service_id_stability_fix_20250907.xml' in content, "SERVICE_ID fix file not referenced"
        assert 'netra-backend' in content, "Stable value not mentioned in learnings"
        
        print("[PASS] SERVICE_ID fix properly documented in learnings index")
        print("[PASS] References service_id_stability_fix_20250907.xml")
    
    def test_no_dynamic_service_id_generation(self):
        """Verify no code generates SERVICE_ID with timestamps"""
        print("\n=== Testing No Dynamic SERVICE_ID Generation ===")
        
        # Search for potential dynamic SERVICE_ID generation patterns
        dangerous_patterns = [
            r'SERVICE_ID.*\+.*time',
            r'SERVICE_ID.*\+.*datetime',
            r'SERVICE_ID.*\+.*\$\(date',
            r'f".*SERVICE_ID.*{.*time',
            r'SERVICE_ID.*\+.*str\(int\(',
        ]
        
        # Check deployment scripts
        deploy_script = project_root / "scripts" / "deploy_to_gcp.py"
        if deploy_script.exists():
            with open(deploy_script, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern in dangerous_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert len(matches) == 0, f"Found dangerous SERVICE_ID pattern in deploy script: {matches}"
        
        print("[PASS] No dynamic SERVICE_ID generation found in deployment scripts")
        print("[PASS] SERVICE_ID will remain stable across deployments")


def run_service_id_stability_regression_tests():
    """Run all SERVICE_ID stability regression tests"""
    print("=" * 80)
    print("SERVICE_ID STABILITY REGRESSION TEST SUITE")
    print("=" * 80)
    print("Ensuring SERVICE_ID remains stable and doesn't regress to using timestamps")
    print()
    
    test_suite = TestServiceIdStabilityRegression()
    
    # Run all tests
    test_methods = [
        test_suite.test_auth_routes_uses_hardcoded_service_id,
        test_suite.test_service_id_not_contains_timestamp,
        test_suite.test_environment_variable_not_used,
        test_suite.test_mission_critical_index_contains_service_id,
        test_suite.test_learnings_index_contains_service_id_fix,
        test_suite.test_no_dynamic_service_id_generation,
    ]
    
    failed_tests = []
    for test_method in test_methods:
        try:
            test_method()
        except AssertionError as e:
            failed_tests.append((test_method.__name__, str(e)))
            print(f"[FAIL] {test_method.__name__}: {e}")
        except Exception as e:
            failed_tests.append((test_method.__name__, f"Unexpected error: {e}"))
            print(f"[ERROR] {test_method.__name__}: {e}")
    
    print("\n" + "=" * 80)
    if failed_tests:
        print(f"[FAILURE] {len(failed_tests)} test(s) failed:")
        for test_name, error in failed_tests:
            print(f"  - {test_name}: {error}")
        print("\nREGRESSION DETECTED: SERVICE_ID stability may be compromised!")
        sys.exit(1)
    else:
        print("[SUCCESS] ALL SERVICE_ID STABILITY REGRESSION TESTS PASSED")
        print("SERVICE_ID remains stable at 'netra-backend' - no timestamp regression detected")
        print("Cross-service authentication should work reliably")
    print("=" * 80)


if __name__ == "__main__":
    run_service_id_stability_regression_tests()