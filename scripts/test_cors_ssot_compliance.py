#!/usr/bin/env python
"""Test script to verify CORS SSOT compliance across all services.

This script verifies that:
1. All services follow SSOT for CORS configuration
2. Dev environment is permissive (allows localhost with any port)
3. Staging/Production have explicit origins set
4. No legacy CORS code remains
"""

import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.cors_config_builder import get_cors_origins, is_origin_allowed


def test_development_cors():
    """Test that development CORS is permissive."""
    print("\n=== Testing Development CORS Configuration ===")
    
    dev_origins = get_cors_origins("development")
    
    # Test that various localhost ports are allowed
    test_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        # Test dynamic port - should be allowed in dev
        "http://localhost:9999",
        "http://127.0.0.1:12345",
    ]
    
    all_passed = True
    for origin in test_origins:
        is_allowed = is_origin_allowed(origin, dev_origins, "development")
        status = "PASS" if is_allowed else "FAIL"
        print(f"  [{status}] {origin}: {'ALLOWED' if is_allowed else 'BLOCKED'}")
        if not is_allowed:
            all_passed = False
    
    print(f"\nDevelopment CORS: {'PASSED - Permissive as expected' if all_passed else 'FAILED - Not permissive enough'}")
    return all_passed


def test_staging_cors():
    """Test that staging CORS has explicit origins."""
    print("\n=== Testing Staging CORS Configuration ===")
    
    staging_origins = get_cors_origins("staging")
    
    # These should be allowed
    allowed_test_origins = [
        "https://app.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai",
        "https://api.staging.netrasystems.ai",
        "http://localhost:3000",  # Dev support
        "http://localhost:8000",
    ]
    
    # These should be blocked
    blocked_test_origins = [
        "http://malicious-site.com",
        "https://random-domain.com",
        "http://localhost:9999",  # Not in explicit list for staging
    ]
    
    all_passed = True
    
    print("  Should be ALLOWED:")
    for origin in allowed_test_origins:
        is_allowed = is_origin_allowed(origin, staging_origins, "staging")
        status = "PASS" if is_allowed else "FAIL"
        print(f"    [{status}] {origin}: {'ALLOWED' if is_allowed else 'BLOCKED'}")
        if not is_allowed:
            all_passed = False
    
    print("  Should be BLOCKED:")
    for origin in blocked_test_origins:
        is_allowed = is_origin_allowed(origin, staging_origins, "staging")
        status = "PASS" if not is_allowed else "FAIL"
        print(f"    [{status}] {origin}: {'BLOCKED' if not is_allowed else 'ALLOWED'}")
        if is_allowed:
            all_passed = False
    
    print(f"\nStaging CORS: {'PASSED - Explicit origins set correctly' if all_passed else 'FAILED - Check origin configuration'}")
    return all_passed


def test_production_cors():
    """Test that production CORS has strict explicit origins."""
    print("\n=== Testing Production CORS Configuration ===")
    
    prod_origins = get_cors_origins("production")
    
    # Only these should be allowed
    allowed_test_origins = [
        "https://netrasystems.ai",
        "https://www.netrasystems.ai",
        "https://app.netrasystems.ai",
        "https://api.netrasystems.ai",
        "https://auth.netrasystems.ai",
    ]
    
    # Everything else should be blocked
    blocked_test_origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://malicious-site.com",
        "https://random-domain.com",
        "http://netrasystems.ai",  # Non-HTTPS should be blocked
    ]
    
    all_passed = True
    
    print("  Should be ALLOWED:")
    for origin in allowed_test_origins:
        is_allowed = is_origin_allowed(origin, prod_origins, "production")
        status = "PASS" if is_allowed else "FAIL"
        print(f"    [{status}] {origin}: {'ALLOWED' if is_allowed else 'BLOCKED'}")
        if not is_allowed:
            all_passed = False
    
    print("  Should be BLOCKED:")
    for origin in blocked_test_origins:
        is_allowed = is_origin_allowed(origin, prod_origins, "production")
        status = "PASS" if not is_allowed else "FAIL"
        print(f"    [{status}] {origin}: {'BLOCKED' if not is_allowed else 'ALLOWED'}")
        if is_allowed:
            all_passed = False
    
    print(f"\nProduction CORS: {'PASSED - Strict origins enforced' if all_passed else 'FAILED - Security issue detected'}")
    return all_passed


def check_ssot_compliance():
    """Check that all services use the shared CORS config."""
    print("\n=== Checking SSOT Compliance ===")
    
    # Check that services import from shared.cors_config_builder
    services_to_check = [
        ("netra_backend/app/core/middleware_setup.py", "from shared.cors_config_builder import get_fastapi_cors_config"),
        ("auth_service/main.py", "from shared.cors_config_builder import get_fastapi_cors_config"),
        ("netra_backend/app/core/websocket_cors.py", "from shared.cors_config_builder import get_websocket_cors_origins"),
    ]
    
    all_compliant = True
    for file_path, expected_import in services_to_check:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if expected_import in content:
                    print(f"  [PASS] {file_path}: Uses shared CORS config")
                else:
                    print(f"  [FAIL] {file_path}: NOT using shared CORS config")
                    all_compliant = False
        except Exception as e:
            print(f"  [FAIL] {file_path}: Could not check ({e})")
            all_compliant = False
    
    # Check for legacy CORS functions that should not exist
    legacy_patterns = [
        "CustomCORSMiddleware",
        "def get_allowed_origins",
        "def _get_cors_origins",
    ]
    
    print("\n  Checking for legacy CORS code:")
    for file_path, _ in services_to_check:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in legacy_patterns:
                    if pattern in content and "# Legacy" not in content and "# CustomCORSMiddleware removed" not in content:
                        print(f"  [FAIL] {file_path}: Contains legacy pattern '{pattern}'")
                        all_compliant = False
        except:
            pass
    
    if all_compliant:
        print("  [PASS] No legacy CORS code found")
    
    print(f"\nSSOT Compliance: {'PASSED - All services use shared config' if all_compliant else 'FAILED - Legacy code detected'}")
    return all_compliant


def main():
    """Run all CORS compliance tests."""
    print("=" * 60)
    print("CORS SSOT Compliance Test")
    print("=" * 60)
    
    results = {
        "Development": test_development_cors(),
        "Staging": test_staging_cors(),
        "Production": test_production_cors(),
        "SSOT Compliance": check_ssot_compliance(),
    }
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("[SUCCESS] ALL TESTS PASSED" if all_passed else "[FAILURE] SOME TESTS FAILED"))
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())