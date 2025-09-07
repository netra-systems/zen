#!/usr/bin/env python3
"""
Simple test to validate JWT staging authentication fix.
"""

import os
import sys
import asyncio
import hashlib

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("=" * 60)
    print("JWT STAGING AUTHENTICATION FIX VALIDATION")
    print("=" * 60)
    
    # Test the fixed JWT token creation
    try:
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        
        helper = JWTTestHelper(environment="staging")
        token = await helper.get_staging_jwt_token("fix-test-user", "test@netrasystems.ai")
        
        if token:
            print("[SUCCESS] STAGING TOKEN CREATION: SUCCESS")
            print(f"   Token length: {len(token)}")
            print(f"   Token prefix: {token[:50]}...")
            
            # Verify it uses the correct secret
            expected_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
            expected_hash = hashlib.md5(expected_secret.encode()).hexdigest()[:16]
            
            # Try to validate the token with the expected secret
            import jwt as jwt_lib
            try:
                payload = jwt_lib.decode(token, expected_secret, algorithms=["HS256"])
                print(f"[SUCCESS] TOKEN VALIDATION: SUCCESS with staging secret (hash: {expected_hash})")
                print(f"   User: {payload.get('sub', 'unknown')}")
                print(f"   Email: {payload.get('email', 'unknown')}")
                print("[SUCCESS] FIX VERIFIED: Test tokens now use correct staging secret")
            except Exception as e:
                print(f"[FAILED] TOKEN VALIDATION: FAILED - {e}")
                print("[FAILED] Fix may not be working correctly")
                
        else:
            print("[FAILED] STAGING TOKEN CREATION: FAILED")
            
    except Exception as e:
        print(f"[FAILED] JWT HELPER TEST: FAILED - {e}")
    
    # Test the staging config token creation too
    print("\n" + "-" * 40)
    try:
        from tests.e2e.staging_test_config import get_staging_config
        
        config = get_staging_config()
        token = config.create_test_jwt_token()
        
        if token:
            print("[SUCCESS] STAGING CONFIG TOKEN: SUCCESS")
            print(f"   Token length: {len(token)}")
            
            # Verify it also uses the correct secret
            expected_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
            expected_hash = hashlib.md5(expected_secret.encode()).hexdigest()[:16]
            
            import jwt as jwt_lib
            try:
                payload = jwt_lib.decode(token, expected_secret, algorithms=["HS256"])
                print(f"[SUCCESS] CONFIG TOKEN VALIDATION: SUCCESS with staging secret (hash: {expected_hash})")
                print(f"   User: {payload.get('sub', 'unknown')}")
                print("[SUCCESS] BOTH TOKEN SOURCES NOW USE CORRECT STAGING SECRET")
            except Exception as e:
                print(f"[FAILED] CONFIG TOKEN VALIDATION: FAILED - {e}")
                
        else:
            print("[FAILED] STAGING CONFIG TOKEN: FAILED")
            
    except Exception as e:
        print(f"[FAILED] STAGING CONFIG TEST: FAILED - {e}")
    
    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())