#!/usr/bin/env python3
"""
Debug script for JWT staging authentication issue.

This script diagnoses the JWT secret resolution differences between 
test token creation and staging WebSocket validation.
"""

import os
import sys
import asyncio
import hashlib
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("=" * 80)
    print("JWT STAGING AUTHENTICATION DEBUG")
    print("=" * 80)
    
    # Test 1: Check environment variable resolution
    print("\n1. ENVIRONMENT VARIABLE ANALYSIS")
    print("-" * 40)
    
    # Save original environment
    original_env = os.environ.get("ENVIRONMENT")
    
    # Check current environment
    current_env = os.environ.get("ENVIRONMENT", "unknown")
    print(f"Current ENVIRONMENT: {current_env}")
    
    # Check for staging JWT secrets
    staging_secrets = {
        "JWT_SECRET_STAGING": os.environ.get("JWT_SECRET_STAGING"),
        "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY"),
        "JWT_SECRET": os.environ.get("JWT_SECRET"),
        "SECRET_KEY": os.environ.get("SECRET_KEY")
    }
    
    for key, value in staging_secrets.items():
        if value:
            value_hash = hashlib.md5(value.encode()).hexdigest()[:16]
            print(f"  {key}: Present (hash: {value_hash}, length: {len(value)})")
        else:
            print(f"  {key}: MISSING")
    
    # Test 2: Unified JWT Secret Manager Resolution
    print("\n2. UNIFIED JWT SECRET MANAGER ANALYSIS")
    print("-" * 40)
    
    try:
        # Test with current environment
        from shared.jwt_secret_manager import get_unified_jwt_secret, get_jwt_secret_manager
        
        manager = get_jwt_secret_manager()
        debug_info = manager.get_debug_info()
        
        print(f"Environment detected: {debug_info['environment']}")
        print(f"Environment-specific key: {debug_info['environment_specific_key']}")
        print(f"Has env-specific secret: {debug_info['has_env_specific']}")
        print(f"Has generic JWT_SECRET_KEY: {debug_info['has_generic_key']}")
        print(f"Has legacy JWT_SECRET: {debug_info['has_legacy_key']}")
        print(f"Available keys: {debug_info['available_keys']}")
        print(f"Algorithm: {debug_info['algorithm']}")
        
        # Get the actual secret
        secret = get_unified_jwt_secret()
        secret_hash = hashlib.md5(secret.encode()).hexdigest()[:16]
        print(f"Resolved secret hash: {secret_hash}")
        print(f"Resolved secret length: {len(secret)}")
        
    except Exception as e:
        print(f"FAILED to use unified JWT secret manager: {e}")
    
    # Test 3: Test with staging environment explicitly set
    print("\n3. STAGING ENVIRONMENT SIMULATION")
    print("-" * 40)
    
    try:
        # Temporarily set environment to staging
        os.environ["ENVIRONMENT"] = "staging"
        
        # Clear any cached secrets
        if 'shared.jwt_secret_manager' in sys.modules:
            from shared.jwt_secret_manager import get_jwt_secret_manager
            manager = get_jwt_secret_manager()
            manager.clear_cache()
        
        # Re-import to get fresh resolution
        import importlib
        if 'shared.jwt_secret_manager' in sys.modules:
            importlib.reload(sys.modules['shared.jwt_secret_manager'])
        
        from shared.jwt_secret_manager import get_unified_jwt_secret, get_jwt_secret_manager
        
        manager = get_jwt_secret_manager()
        debug_info = manager.get_debug_info()
        
        print(f"Environment detected: {debug_info['environment']}")
        print(f"Environment-specific key: {debug_info['environment_specific_key']}")
        print(f"Has env-specific secret: {debug_info['has_env_specific']}")
        print(f"Available keys: {debug_info['available_keys']}")
        
        # Get the actual secret in staging mode
        secret = get_unified_jwt_secret()
        secret_hash = hashlib.md5(secret.encode()).hexdigest()[:16]
        print(f"Staging secret hash: {secret_hash}")
        print(f"Staging secret length: {len(secret)}")
        
        # Compare with hardcoded staging secret
        hardcoded_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
        hardcoded_hash = hashlib.md5(hardcoded_secret.encode()).hexdigest()[:16]
        print(f"Hardcoded staging secret hash: {hardcoded_hash}")
        print(f"Secrets match: {secret == hardcoded_secret}")
        
    except Exception as e:
        print(f"FAILED staging simulation: {e}")
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)
    
    # Test 4: JWT Token Creation Test
    print("\n4. JWT TOKEN CREATION TEST")
    print("-" * 40)
    
    try:
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        
        # Test current token creation
        helper = JWTTestHelper(environment="staging")
        token = await helper.get_staging_jwt_token("debug-user", "debug@test.com")
        
        if token:
            print(f"Token created successfully")
            print(f"Token length: {len(token)}")
            print(f"Token prefix: {token[:50]}...")
            
            # Try to decode it
            import jwt as jwt_lib
            
            # Try with unified secret
            try:
                from shared.jwt_secret_manager import get_unified_jwt_secret
                os.environ["ENVIRONMENT"] = "staging"
                unified_secret = get_unified_jwt_secret()
                payload = jwt_lib.decode(token, unified_secret, algorithms=["HS256"])
                print(f"Token validation SUCCESS with unified secret")
                print(f"User: {payload.get('sub', 'unknown')}")
            except Exception as e:
                print(f"Token validation FAILED with unified secret: {e}")
            
            # Try with hardcoded secret
            try:
                hardcoded_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
                payload = jwt_lib.decode(token, hardcoded_secret, algorithms=["HS256"])
                print(f"Token validation SUCCESS with hardcoded secret")
                print(f"User: {payload.get('sub', 'unknown')}")
            except Exception as e:
                print(f"Token validation FAILED with hardcoded secret: {e}")
                
        else:
            print("FAILED to create staging token")
            
    except Exception as e:
        print(f"Token creation test failed: {e}")
    
    # Test 5: UserContextExtractor Test
    print("\n5. USER CONTEXT EXTRACTOR TEST")
    print("-" * 40)
    
    try:
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        # Create extractor instance
        extractor = UserContextExtractor()
        
        # Check what secret it's using
        extractor_secret = extractor.jwt_secret_key
        extractor_hash = hashlib.md5(extractor_secret.encode()).hexdigest()[:16]
        print(f"UserContextExtractor secret hash: {extractor_hash}")
        print(f"UserContextExtractor secret length: {len(extractor_secret)}")
        
        # Test token validation
        if 'token' in locals() and token:
            jwt_payload = extractor.validate_and_decode_jwt(token)
            if jwt_payload:
                print(f"UserContextExtractor validation: SUCCESS")
                print(f"Decoded user: {jwt_payload.get('sub', 'unknown')}")
            else:
                print(f"UserContextExtractor validation: FAILED")
        else:
            print("No token available for UserContextExtractor test")
            
    except Exception as e:
        print(f"UserContextExtractor test failed: {e}")
    
    print("\n" + "=" * 80)
    print("DEBUG ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())