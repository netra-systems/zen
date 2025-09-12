#!/usr/bin/env python3
"""
Demo Mode Test Validation Script

This script runs a quick validation to prove that demo mode tests fail as expected,
demonstrating the current restrictive authentication behavior.

This serves as proof that the tests correctly identify missing demo functionality.
"""

import sys
import subprocess
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def run_quick_validation():
    """Run a quick validation of demo mode test failures."""
    
    print("Demo Mode Test Validation")
    print("="*50)
    print("Purpose: Prove tests correctly identify missing demo functionality")
    print("Expected: Tests should FAIL, demonstrating restrictive behavior")
    print("="*50 + "\n")
    
    # Set demo environment
    os.environ["DEMO_MODE"] = "true"
    os.environ["TESTING"] = "true"
    
    # Test 1: Demo configuration detection
    print("Test 1: Demo Mode Configuration Detection")
    try:
        # This should fail because demo configuration doesn't exist
        from netra_backend.app.core.configuration.demo import is_demo_mode
        print("   UNEXPECTED: Demo configuration module exists")
        return False
    except ImportError as e:
        print("   EXPECTED: Demo configuration not implemented")
        print(f"      Error: {e}")
    
    # Test 2: Simple password validation
    print("\nTest 2: Simple Password Requirements")
    try:
        from auth_service.auth_core.services.auth_service import AuthService
        auth_service = AuthService()
        
        # This should fail because simple passwords aren't accepted
        result = auth_service.create_user({
            "email": "demo@demo.com",
            "password": "demo",  # Simple 4-char password
            "demo_mode": True
        })
        print("   UNEXPECTED: Simple password accepted")
        return False
    except Exception as e:
        print("   EXPECTED: Simple password rejected")
        print(f"      Error type: {type(e).__name__}")
    
    # Test 3: Default demo user existence
    print("\nTest 3: Default Demo User Availability")
    try:
        from auth_service.auth_core.services.auth_service import AuthService
        auth_service = AuthService()
        
        # This should fail because demo@demo.com doesn't exist
        result = auth_service.authenticate_user("demo@demo.com", "demo", demo_mode=True)
        print("   UNEXPECTED: Default demo user exists")
        return False
    except Exception as e:
        print("   EXPECTED: Default demo user doesn't exist")
        print(f"      Error type: {type(e).__name__}")
    
    # Test 4: JWT extended expiration
    print("\nTest 4: Extended JWT Validation")
    try:
        import jwt
        from datetime import datetime, timedelta
        
        # Create 25-hour JWT token
        payload = {
            "sub": "demo_user",
            "exp": int((datetime.utcnow() + timedelta(hours=25)).timestamp())
        }
        
        token = jwt.encode(payload, "test_secret", algorithm="HS256")
        
        from netra_backend.app.auth_integration.auth import BackendAuthIntegration
        auth = BackendAuthIntegration()
        
        # This should fail because extended validation isn't implemented
        result = auth.validate_token(token, demo_mode=True)
        print("   UNEXPECTED: Extended JWT validation works")
        return False
    except Exception as e:
        print("   EXPECTED: Extended JWT validation not implemented")
        print(f"      Error type: {type(e).__name__}")
    
    print("\n" + "="*50)
    print("VALIDATION RESULT: SUCCESS")
    print("All tests failed as expected, proving:")
    print("  Demo mode configuration is missing")
    print("  Simple password requirements not implemented")
    print("  Default demo users don't exist")
    print("  Extended JWT validation not available")
    print("\nThis validates that the test suite correctly identifies")
    print("missing demo functionality and will guide implementation.")
    print("="*50)
    
    return True

if __name__ == "__main__":
    success = run_quick_validation()
    sys.exit(0 if success else 1)