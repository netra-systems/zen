#!/usr/bin/env python3
"""
JWT Secret Consistency Validation Script

This script validates that both the auth service and backend service
use the same JWT secret for token validation consistency.

Usage:
    python scripts/validate_jwt_consistency.py
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Add paths for imports
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env file
env_file = os.path.join(project_root, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded environment from: {env_file}")
else:
    print(f"Warning: No .env file found at {env_file}")

try:
    from auth_service.auth_core.core.jwt_handler import JWTHandler
    from auth_service.auth_core.secret_loader import AuthSecretLoader
    from netra_backend.app.core.configuration.secrets import SecretManager
    from netra_backend.app.schemas.Config import AppConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


def validate_jwt_secret_consistency():
    """Validate that both services use the same JWT secret."""
    print("VALIDATING JWT SECRET CONSISTENCY between Auth Service and Backend Service")
    print("=" * 80)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0
        }
    }
    
    # Test 1: Basic secret loading consistency
    print("\nTest 1: Basic Secret Loading Consistency")
    try:
        # Get secret from auth service
        auth_secret = AuthSecretLoader.get_jwt_secret()
        print(f"   Auth service secret: {auth_secret[:10]}...{auth_secret[-4:]}")
        
        # Get secret from backend service
        config = AppConfig()
        secret_manager = SecretManager()
        secret_manager.populate_secrets(config)
        backend_secret = config.jwt_secret_key
        print(f"   Backend service secret: {backend_secret[:10]}...{backend_secret[-4:]}")
        
        # Check consistency
        if auth_secret == backend_secret:
            print("   PASS: Both services use the same JWT secret")
            results["tests"].append({
                "name": "Basic Secret Loading Consistency",
                "status": "PASS",
                "message": "Both services use the same JWT secret"
            })
            results["summary"]["passed"] += 1
        else:
            print("   FAIL: Services use different JWT secrets")
            results["tests"].append({
                "name": "Basic Secret Loading Consistency", 
                "status": "FAIL",
                "message": f"Auth: {auth_secret[:10]}... vs Backend: {backend_secret[:10]}..."
            })
            results["summary"]["failed"] += 1
        
        results["summary"]["total"] += 1
        
    except Exception as e:
        print(f"   ERROR: {e}")
        results["tests"].append({
            "name": "Basic Secret Loading Consistency",
            "status": "ERROR", 
            "message": str(e)
        })
        results["summary"]["failed"] += 1
        results["summary"]["total"] += 1
    
    # Test 2: Token creation and validation consistency
    print("\nTest 2: Token Creation and Validation")
    try:
        jwt_handler = JWTHandler()
        
        # Create a test token
        user_id = "test-user-123"
        email = "test@example.com"
        permissions = ["read", "write"]
        
        token = jwt_handler.create_access_token(user_id, email, permissions)
        print(f"   Created token: {token[:20]}...{token[-10:]}")
        
        # Validate the token
        payload = jwt_handler.validate_token(token, "access")
        
        if payload and payload.get("sub") == user_id and payload.get("email") == email:
            print("   PASS: Token creation and validation works")
            results["tests"].append({
                "name": "Token Creation and Validation",
                "status": "PASS",
                "message": "Token successfully created and validated"
            })
            results["summary"]["passed"] += 1
        else:
            print("   FAIL: Token validation failed")
            results["tests"].append({
                "name": "Token Creation and Validation",
                "status": "FAIL", 
                "message": f"Validation result: {payload}"
            })
            results["summary"]["failed"] += 1
        
        results["summary"]["total"] += 1
        
    except Exception as e:
        print(f"   ERROR: {e}")
        results["tests"].append({
            "name": "Token Creation and Validation",
            "status": "ERROR",
            "message": str(e)
        })
        results["summary"]["failed"] += 1
        results["summary"]["total"] += 1
    
    # Test 3: Environment variable priority
    print("\nTest 3: Environment Variable Priority")
    try:
        jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        jwt_secret = os.getenv("JWT_SECRET")
        
        print(f"   JWT_SECRET_KEY: {'SET' if jwt_secret_key else 'NOT SET'}")
        print(f"   JWT_SECRET: {'SET' if jwt_secret else 'NOT SET'}")
        
        # Auth service should prioritize JWT_SECRET_KEY over JWT_SECRET
        auth_secret = AuthSecretLoader.get_jwt_secret()
        
        if jwt_secret_key and auth_secret == jwt_secret_key:
            print("   PASS: Auth service correctly uses JWT_SECRET_KEY")
            results["tests"].append({
                "name": "Environment Variable Priority",
                "status": "PASS",
                "message": "Auth service correctly prioritizes JWT_SECRET_KEY"
            })
            results["summary"]["passed"] += 1
        elif not jwt_secret_key and jwt_secret and auth_secret == jwt_secret:
            print("   PASS: Auth service correctly falls back to JWT_SECRET")
            results["tests"].append({
                "name": "Environment Variable Priority", 
                "status": "PASS",
                "message": "Auth service correctly falls back to JWT_SECRET"
            })
            results["summary"]["passed"] += 1
        else:
            print("   FAIL: Unexpected secret priority behavior")
            results["tests"].append({
                "name": "Environment Variable Priority",
                "status": "FAIL",
                "message": "Unexpected secret priority behavior"
            })
            results["summary"]["failed"] += 1
        
        results["summary"]["total"] += 1
        
    except Exception as e:
        print(f"   ERROR: {e}")
        results["tests"].append({
            "name": "Environment Variable Priority",
            "status": "ERROR",
            "message": str(e)
        })
        results["summary"]["failed"] += 1
        results["summary"]["total"] += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print(f"   Total Tests: {results['summary']['total']}")
    print(f"   Passed: {results['summary']['passed']}")
    print(f"   Failed: {results['summary']['failed']}")
    
    if results["summary"]["failed"] == 0:
        print("\nSUCCESS: All JWT secret consistency tests passed!")
        print("   Both services are now synchronized and will validate tokens consistently.")
    else:
        print(f"\nWARNING: {results['summary']['failed']} test(s) failed!")
        print("   JWT secret synchronization may have issues.")
    
    # Save results to file
    results_file = os.path.join(project_root, "jwt_consistency_validation.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    return results["summary"]["failed"] == 0


if __name__ == "__main__":
    success = validate_jwt_secret_consistency()
    sys.exit(0 if success else 1)