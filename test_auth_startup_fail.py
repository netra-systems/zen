#!/usr/bin/env python3
"""
Test that the system fails to start with invalid auth configuration.
This verifies the auth startup validation is working correctly.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_startup_with_missing_jwt_secret():
    """Test that system fails to start without JWT_SECRET."""
    print("=" * 60)
    print("Testing startup with missing JWT_SECRET...")
    print("=" * 60)
    
    # Clear JWT secrets from environment
    os.environ.pop('JWT_SECRET', None)
    os.environ.pop('JWT_SECRET_KEY', None)
    
    # Set minimal config to isolate JWT secret validation
    os.environ['ENVIRONMENT'] = 'development'
    os.environ['AUTH_SERVICE_URL'] = 'http://localhost:8001'
    os.environ['SERVICE_ID'] = 'netra-backend'
    os.environ['SERVICE_SECRET'] = 'test-service-secret-long-enough'
    
    try:
        from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
        
        print("\nAttempting to validate auth configuration...")
        await validate_auth_at_startup()
        
        print("\n❌ ERROR: Auth validation should have failed!")
        print("System would have started with missing JWT secret - CRITICAL BUG!")
        return False
        
    except Exception as e:
        print(f"\n✅ GOOD: Auth validation failed as expected!")
        print(f"Error: {e}")
        
        # Verify it's the right error
        if "JWT secret" in str(e) or "jwt_secret" in str(e):
            print("✅ Correct error: JWT secret validation failure detected")
            return True
        else:
            print(f"⚠️ Unexpected error type: {e}")
            return False


async def test_startup_with_invalid_auth_service_url():
    """Test that system fails with invalid AUTH_SERVICE_URL in production."""
    print("\n" + "=" * 60)
    print("Testing startup with HTTP auth URL in production...")
    print("=" * 60)
    
    # Set production environment with HTTP URL (should fail)
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['JWT_SECRET'] = 'valid-jwt-secret-that-is-long-enough-for-validation'
    os.environ['AUTH_SERVICE_URL'] = 'http://localhost:8001'  # HTTP in production should fail!
    os.environ['SERVICE_ID'] = 'netra-backend'
    os.environ['SERVICE_SECRET'] = 'test-service-secret-long-enough'
    
    try:
        from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
        
        print("\nAttempting to validate auth configuration in production...")
        await validate_auth_at_startup()
        
        print("\n❌ ERROR: Auth validation should have failed!")
        print("System would have started with HTTP in production - SECURITY BUG!")
        return False
        
    except Exception as e:
        print(f"\n✅ GOOD: Auth validation failed as expected!")
        print(f"Error: {e}")
        
        # Verify it's the right error
        if "HTTPS" in str(e):
            print("✅ Correct error: HTTPS requirement enforced in production")
            return True
        else:
            print(f"⚠️ Unexpected error type: {e}")
            return False


async def test_startup_orchestrator_integration():
    """Test that the startup orchestrator properly calls auth validation."""
    print("\n" + "=" * 60)
    print("Testing startup orchestrator integration...")
    print("=" * 60)
    
    # Clear critical config
    os.environ.pop('JWT_SECRET', None)
    os.environ.pop('JWT_SECRET_KEY', None)
    os.environ['ENVIRONMENT'] = 'development'
    
    try:
        # Import the startup orchestrator
        from netra_backend.app.smd import StartupOrchestrator
        from fastapi import FastAPI
        
        app = FastAPI()
        orchestrator = StartupOrchestrator(app)
        
        print("\nChecking if _validate_auth_configuration method exists...")
        if not hasattr(orchestrator, '_validate_auth_configuration'):
            print("❌ ERROR: _validate_auth_configuration method not found!")
            return False
        
        print("✅ Method exists")
        
        print("\nAttempting to run auth validation through orchestrator...")
        await orchestrator._validate_auth_configuration()
        
        print("\n❌ ERROR: Auth validation should have failed!")
        print("Orchestrator would start system without auth validation!")
        return False
        
    except Exception as e:
        print(f"\n✅ GOOD: Orchestrator auth validation failed as expected!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        
        # Check for DeterministicStartupError
        if "DeterministicStartupError" in str(type(e)):
            print("✅ Correct error type: DeterministicStartupError prevents startup")
            return True
        elif "validation failed" in str(e).lower():
            print("✅ Auth validation error properly raised")
            return True
        else:
            print(f"⚠️ Unexpected error: {e}")
            return False


async def main():
    """Run all auth startup validation tests."""
    print("AUTH STARTUP VALIDATION TESTS")
    print("Testing that system CANNOT start with bad auth configuration")
    print()
    
    results = []
    
    # Test 1: Missing JWT secret
    result1 = await test_startup_with_missing_jwt_secret()
    results.append(("Missing JWT_SECRET", result1))
    
    # Test 2: Invalid auth URL in production
    result2 = await test_startup_with_invalid_auth_service_url()
    results.append(("HTTP in production", result2))
    
    # Test 3: Orchestrator integration
    result3 = await test_startup_orchestrator_integration()
    results.append(("Orchestrator integration", result3))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 SUCCESS: Auth validation is properly preventing insecure startups!")
        print("The system correctly refuses to start with invalid auth configuration.")
    else:
        print("\n⚠️ WARNING: Some auth validation tests failed!")
        print("The system might start with invalid auth configuration.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)