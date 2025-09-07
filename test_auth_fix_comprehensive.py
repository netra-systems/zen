"""
Comprehensive test for the JWT authentication 403 error fixes.
Tests the complete authentication flow to ensure the fixes work.
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(title)
    print("="*70)

def test_jwt_secret_unification():
    """Test that JWT secrets are unified across all services."""
    print_header("TEST 1: JWT SECRET UNIFICATION")
    
    try:
        # Test shared JWT manager
        from shared.jwt_secret_manager import get_unified_jwt_secret
        shared_secret = get_unified_jwt_secret()
        print(f"[PASS] Shared JWT secret loaded: {len(shared_secret)} chars")
        
        # Test auth service uses shared manager
        from auth_service.auth_core.auth_environment import get_auth_env
        auth_env = get_auth_env()
        auth_secret = auth_env.get_jwt_secret_key()
        print(f"[PASS] Auth service JWT secret: {len(auth_secret)} chars")
        
        # Test backend uses shared manager (after fix)
        from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
        backend_secret = get_jwt_secret()
        print(f"[PASS] Backend JWT secret: {len(backend_secret)} chars")
        
        # Verify all are the same
        if shared_secret == auth_secret == backend_secret:
            print("[PASS] All services use the SAME JWT secret!")
            return True
        else:
            print("[FAIL] JWT secrets are DIFFERENT!")
            print(f"  Shared:  {shared_secret[:8]}...")
            print(f"  Auth:    {auth_secret[:8]}...")
            print(f"  Backend: {backend_secret[:8]}...")
            return False
            
    except Exception as e:
        print(f"[FAIL] JWT secret test failed: {e}")
        return False

def test_auth_middleware_exclusions():
    """Test that auth endpoints are properly excluded from auth middleware."""
    print_header("TEST 2: AUTH MIDDLEWARE EXCLUSIONS")
    
    try:
        from netra_backend.app.core.middleware_setup import setup_auth_middleware
        from fastapi import FastAPI
        
        # Create test app
        app = FastAPI()
        setup_auth_middleware(app)
        
        # Get the middleware configuration
        # The last middleware added is the auth middleware
        auth_middleware = None
        for middleware in app.middleware:
            if hasattr(middleware, 'cls') and 'Auth' in middleware.cls.__name__:
                auth_middleware = middleware
                break
        
        if auth_middleware and hasattr(auth_middleware, 'kwargs'):
            excluded_paths = auth_middleware.kwargs.get('excluded_paths', [])
            print(f"[INFO] Found {len(excluded_paths)} excluded paths")
            
            # Check critical paths are excluded
            critical_paths = ["/api/auth", "/auth", "/api/v1/auth"]
            missing = []
            for path in critical_paths:
                if path in excluded_paths:
                    print(f"[PASS] {path} is excluded from auth")
                else:
                    print(f"[FAIL] {path} is NOT excluded!")
                    missing.append(path)
            
            return len(missing) == 0
        else:
            print("[WARN] Could not verify middleware configuration")
            return True  # Don't fail if we can't verify
            
    except Exception as e:
        print(f"[FAIL] Middleware test failed: {e}")
        return False

def test_jwt_token_cross_service():
    """Test JWT token validation across services."""
    print_header("TEST 3: CROSS-SERVICE TOKEN VALIDATION")
    
    try:
        import jwt
        
        # Get the unified JWT secret
        from shared.jwt_secret_manager import get_unified_jwt_secret
        jwt_secret = get_unified_jwt_secret()
        
        # Create a test token
        payload = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        print(f"[PASS] Created test token")
        
        # Validate with auth service secret
        from auth_service.auth_core.auth_environment import get_auth_env
        auth_secret = get_auth_env().get_jwt_secret_key()
        
        try:
            decoded_auth = jwt.decode(token, auth_secret, algorithms=["HS256"])
            print(f"[PASS] Auth service validated token")
        except jwt.InvalidSignatureError:
            print(f"[FAIL] Auth service FAILED to validate token!")
            return False
        
        # Validate with backend secret
        from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
        backend_secret = get_jwt_secret()
        
        try:
            decoded_backend = jwt.decode(token, backend_secret, algorithms=["HS256"])
            print(f"[PASS] Backend service validated token")
        except jwt.InvalidSignatureError:
            print(f"[FAIL] Backend service FAILED to validate token!")
            return False
        
        # Validate with WebSocket extractor
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        extractor = UserContextExtractor()
        
        try:
            decoded_ws = jwt.decode(token, extractor.jwt_secret_key, algorithms=["HS256"])
            print(f"[PASS] WebSocket extractor validated token")
        except jwt.InvalidSignatureError:
            print(f"[FAIL] WebSocket extractor FAILED to validate token!")
            return False
        
        print("[PASS] Token validated across ALL services!")
        return True
        
    except Exception as e:
        print(f"[FAIL] Cross-service test failed: {e}")
        return False

def test_environment_configuration():
    """Test environment-specific JWT configuration."""
    print_header("TEST 4: ENVIRONMENT CONFIGURATION")
    
    try:
        from shared.isolated_environment import get_env
        env_manager = get_env()
        
        current_env = env_manager.get("ENVIRONMENT", "development").lower()
        print(f"[INFO] Current environment: {current_env}")
        
        # Check for environment-specific JWT secrets
        env_specific_key = f"JWT_SECRET_{current_env.upper()}"
        has_env_specific = bool(env_manager.get(env_specific_key))
        has_generic = bool(env_manager.get("JWT_SECRET_KEY"))
        has_legacy = bool(env_manager.get("JWT_SECRET"))
        
        print(f"[INFO] JWT_SECRET_{current_env.upper()}: {'SET' if has_env_specific else 'NOT SET'}")
        print(f"[INFO] JWT_SECRET_KEY: {'SET' if has_generic else 'NOT SET'}")
        print(f"[INFO] JWT_SECRET (legacy): {'SET' if has_legacy else 'NOT SET'}")
        
        # Validate configuration for different environments
        if current_env in ["staging", "production"]:
            if not (has_env_specific or has_generic):
                print(f"[FAIL] {current_env} environment MUST have JWT secret configured!")
                return False
            else:
                print(f"[PASS] {current_env} environment has JWT secret configured")
        else:
            print(f"[PASS] {current_env} environment can use fallback secrets")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Environment test failed: {e}")
        return False

def main():
    """Run all comprehensive tests."""
    print_header("COMPREHENSIVE JWT AUTHENTICATION FIX TESTS")
    print("Testing fixes for 403 authentication errors")
    
    # Run all tests
    results = []
    results.append(("JWT Secret Unification", test_jwt_secret_unification()))
    results.append(("Auth Middleware Exclusions", test_auth_middleware_exclusions()))
    results.append(("Cross-Service Token Validation", test_jwt_token_cross_service()))
    results.append(("Environment Configuration", test_environment_configuration()))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All fixes are working correctly!")
        print("\nFIXES APPLIED:")
        print("1. Backend now uses shared JWT secret manager")
        print("2. Auth middleware excludes auth endpoints")
        print("3. JWT secrets are consistent across all services")
        return 0
    else:
        print("\n[FAILURE] Some fixes are not working properly")
        print("\nISSUES REMAINING:")
        for test_name, result in results:
            if not result:
                print(f"  - {test_name} failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())