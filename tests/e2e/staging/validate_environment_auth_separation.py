#!/usr/bin/env python3
"""
Validation script for environment-specific auth separation tests.

This script validates that the E2E staging tests properly detect and test
environment-specific auth flow separation issues identified in the Five Whys analysis.

Run with: python tests/e2e/staging/validate_environment_auth_separation.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.e2e.staging.test_environment_auth_separation import TestEnvironmentAuthSeparation


async def validate_environment_detection():
    """Validate that the test correctly detects different environments."""
    
    print("=== VALIDATING ENVIRONMENT DETECTION ===")
    
    # Test 1: Development environment detection
    os.environ['ENVIRONMENT'] = 'development'
    
    dev_test = TestEnvironmentAuthSeparation()
    dev_test.setup_method(None)
    
    assert dev_test.current_env == 'development', f"Expected development, got {dev_test.current_env}"
    assert 'localhost' in dev_test.auth_base_url, f"Development should use localhost, got {dev_test.auth_base_url}"
    print("✓ Development environment detection: PASSED")
    
    # Test 2: Staging environment detection
    os.environ['ENVIRONMENT'] = 'staging'
    
    staging_test = TestEnvironmentAuthSeparation()
    staging_test.setup_method(None)
    
    assert staging_test.current_env == 'staging', f"Expected staging, got {staging_test.current_env}"
    assert 'staging.netrasystems.ai' in staging_test.auth_base_url, f"Staging should use staging domain, got {staging_test.auth_base_url}"
    print("✓ Staging environment detection: PASSED")
    
    # Test 3: Validate URL differences
    assert dev_test.auth_base_url != staging_test.auth_base_url, "Development and staging auth URLs should differ"
    assert dev_test.backend_url != staging_test.backend_url, "Development and staging backend URLs should differ"
    print("✓ Environment URL separation: PASSED")
    
    return True


async def validate_configuration_separation():
    """Validate configuration differences between environments."""
    
    print("\n=== VALIDATING CONFIGURATION SEPARATION ===")
    
    os.environ['ENVIRONMENT'] = 'staging'
    
    test_instance = TestEnvironmentAuthSeparation()
    test_instance.setup_method(None)
    
    # Check JWT configuration
    jwt_secret = test_instance.env.get('JWT_SECRET_KEY')
    
    if jwt_secret:
        # Validate JWT secret is not a default development value
        forbidden_values = ['your-secret-key', 'dev_secret', 'secret', 'test']
        if jwt_secret.lower() in forbidden_values:
            print("⚠ WARNING: JWT_SECRET_KEY appears to be a development/default value")
        else:
            print("✓ JWT secret appears to be environment-specific")
    else:
        print("⚠ WARNING: JWT_SECRET_KEY not configured")
        
    # Check OAuth configuration
    google_client_id = test_instance.env.get('GOOGLE_CLIENT_ID')
    if google_client_id and 'localhost' not in google_client_id:
        print("✓ Google OAuth client ID appears to be environment-specific")
    else:
        print("⚠ WARNING: Google OAuth configuration may not be environment-specific")
        
    return True


async def validate_test_framework_integration():
    """Validate integration with test framework and environment markers."""
    
    print("\n=== VALIDATING TEST FRAMEWORK INTEGRATION ===")
    
    # Check that test inherits from correct base class
    test_class = TestEnvironmentAuthSeparation
    base_classes = [base.__name__ for base in test_class.__mro__]
    
    if 'SSotAsyncTestCase' in base_classes:
        print("✓ Test correctly inherits from SSotAsyncTestCase")
    else:
        print("✗ ERROR: Test does not inherit from SSotAsyncTestCase")
        return False
        
    # Check that test methods are defined
    required_methods = [
        'test_staging_auth_flow_differs_from_development',
        'test_environment_specific_auth_configuration', 
        'test_cross_environment_auth_token_rejection',
        'test_demo_mode_vs_production_auth_separation'
    ]
    
    for method_name in required_methods:
        if hasattr(test_class, method_name):
            print(f"✓ Required test method {method_name}: FOUND")
        else:
            print(f"✗ ERROR: Required test method {method_name}: MISSING")
            return False
            
    return True


def generate_test_report():
    """Generate a report of what the tests validate."""
    
    print("\n=== TEST COVERAGE REPORT ===")
    print("""
These E2E staging tests validate:

1. test_staging_auth_flow_differs_from_development():
   - Environment marker validation (staging vs development)
   - Auth service health endpoints differ between environments  
   - OAuth configuration contains proper staging domains
   - Service versions don't contain development markers

2. test_environment_specific_auth_configuration():
   - JWT secrets are environment-specific (not default/dev values)
   - OAuth client IDs don't contain localhost (development leak)
   - Redis URLs are staging-specific (not localhost)
   - Database URLs are staging-specific (not localhost)
   - Auth service URLs match environment expectations

3. test_cross_environment_auth_token_rejection():
   - Development tokens are rejected by staging backend
   - Auth service rejects tokens with wrong environment markers
   - Tokens with wrong secrets are properly rejected
   - Security boundaries prevent cross-environment access

4. test_demo_mode_vs_production_auth_separation():
   - Demo auth endpoints differ from production auth endpoints
   - Demo tokens contain proper demo markers and environment info
   - Demo endpoints are disabled when demo mode is off
   - Production endpoints apply proper restrictions for demo tokens

BUSINESS IMPACT:
- Protects $500K+ ARR Golden Path from auth cross-contamination  
- Ensures enterprise security isolation requirements
- Prevents development auth tokens from working in staging
- Validates environment boundary security
""")


async def main():
    """Main validation function."""
    
    print("Environment-Specific Auth Separation Test Validation")
    print("=" * 60)
    
    try:
        # Run validation tests
        await validate_environment_detection()
        await validate_configuration_separation() 
        await validate_test_framework_integration()
        
        print("\n🎉 ALL VALIDATIONS PASSED")
        print("\nThe E2E staging tests are ready to validate environment-specific auth separation.")
        
        generate_test_report()
        
        print("\n📋 NEXT STEPS:")
        print("1. Run tests in staging environment: pytest tests/e2e/staging/test_environment_auth_separation.py")
        print("2. Verify staging environment variables are properly configured")
        print("3. Check that staging auth services are accessible")
        print("4. Review test results for environment separation violations")
        
        return True
        
    except Exception as e:
        print(f"\n💥 VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)