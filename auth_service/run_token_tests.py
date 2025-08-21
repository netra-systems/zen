#!/usr/bin/env python3
"""
JWT Token Validation Test Runner
Standalone runner for JWT token tests without complex pytest setup
"""
import os
import sys
import unittest
from datetime import datetime, timezone

# Add auth_service to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set test environment
os.environ.update({
    "ENVIRONMENT": "test",
    "JWT_SECRET": "test-jwt-secret-key-that-is-long-enough-for-testing-purposes-32-chars",
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_EXPIRY_MINUTES": "15",
    "JWT_REFRESH_EXPIRY_DAYS": "7",
    "JWT_SERVICE_EXPIRY_MINUTES": "5"
})

# Import test classes
from netra_backend.tests.test_token_validation import (
    TestJWTTokenGeneration,
    TestJWTTokenValidation,
    TestJWTTokenExpiry,
    TestJWTRefreshFlow,
    TestJWTClaimsExtraction,
    TestJWTSignatureVerification,
    TestJWTTokenRevocation,
    TestJWTKeyRotation,
    TestJWTSecurityTampering
)


def run_test_class(test_class, class_name):
    """Run all tests in a test class"""
    print(f"\n{'='*60}")
    print(f"Running {class_name}")
    print(f"{'='*60}")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    return result.wasSuccessful(), len(result.failures), len(result.errors)


def main():
    """Run all JWT token validation tests"""
    print("JWT Token Validation Test Suite")
    print("=" * 60)
    
    test_classes = [
        (TestJWTTokenGeneration, "JWT Token Generation Tests"),
        (TestJWTTokenValidation, "JWT Token Validation Tests"),
        (TestJWTTokenExpiry, "JWT Token Expiry Tests"),
        (TestJWTRefreshFlow, "JWT Refresh Flow Tests"),
        (TestJWTClaimsExtraction, "JWT Claims Extraction Tests"),
        (TestJWTSignatureVerification, "JWT Signature Verification Tests"),
        (TestJWTTokenRevocation, "JWT Token Revocation Tests"),
        (TestJWTKeyRotation, "JWT Key Rotation Tests"),
        (TestJWTSecurityTampering, "JWT Security & Tampering Tests")
    ]
    
    total_success = True
    total_failures = 0
    total_errors = 0
    
    for test_class, class_name in test_classes:
        try:
            success, failures, errors = run_test_class(test_class, class_name)
            total_success = total_success and success
            total_failures += failures
            total_errors += errors
        except Exception as e:
            print(f"Error running {class_name}: {e}")
            total_success = False
            total_errors += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Overall Success: {'PASS' if total_success else 'FAIL'}")
    print(f"Total Failures: {total_failures}")
    print(f"Total Errors: {total_errors}")
    
    if total_success:
        print("\nAll JWT token validation tests passed!")
        return 0
    else:
        print(f"\nTests failed with {total_failures} failures and {total_errors} errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())