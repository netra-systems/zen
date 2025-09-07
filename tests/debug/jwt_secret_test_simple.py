"""
Simple JWT secret diagnosis test - Windows compatible (no unicode)
"""

import os
import sys
import jwt
from datetime import datetime, timedelta, timezone
import uuid

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


async def main():  # CRITICAL FIX: Made async
    print("WEBSOCKET JWT SECRET MISMATCH DIAGNOSIS")
    print("=" * 60)
    
    # STEP 1: Get test environment JWT secret
    original_env = os.environ.get("ENVIRONMENT")
    
    try:
        os.environ["ENVIRONMENT"] = "staging"
        from shared.jwt_secret_manager import get_unified_jwt_secret
        test_secret = get_unified_jwt_secret()
        print(f"Test JWT secret (first 20 chars): {test_secret[:20]}...")
        print(f"Test JWT secret length: {len(test_secret)} chars")
        
    except Exception as e:
        print(f"ERROR: Failed to get test JWT secret: {e}")
        test_secret = None
        
    finally:
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)
    
    # STEP 2: Get backend JWT secret
    try:
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        extractor = UserContextExtractor()
        backend_secret = extractor.jwt_secret_key
        print(f"Backend JWT secret (first 20 chars): {backend_secret[:20]}...")
        print(f"Backend JWT secret length: {len(backend_secret)} chars")
        
    except Exception as e:
        print(f"ERROR: Failed to get backend JWT secret: {e}")
        backend_secret = None
    
    # STEP 3: Compare secrets
    if test_secret and backend_secret:
        secrets_match = test_secret == backend_secret
        print(f"\nSecrets match: {secrets_match}")
        
        if not secrets_match:
            print("\nROOT CAUSE CONFIRMED:")
            print("JWT secret mismatch will cause 403 WebSocket errors")
            print(f"Test secret:    {test_secret[:40]}...")
            print(f"Backend secret: {backend_secret[:40]}...")
        
        # STEP 4: Test JWT token creation and validation
        if test_secret:
            # Create test token
            payload = {
                "sub": f"test-user-{uuid.uuid4().hex[:8]}",
                "email": "test@netrasystems.ai",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                "iss": "netra-auth-service",
            }
            
            # Set environment to staging for token creation
            original_env2 = os.environ.get("ENVIRONMENT")
            os.environ["ENVIRONMENT"] = "staging"
            
            try:
                test_token = jwt.encode(payload, test_secret, algorithm="HS256")
                print(f"\nCreated JWT token: {test_token[:50]}...")
                
                # Validate with backend
                decoded_payload = await extractor.validate_and_decode_jwt(test_token)  # CRITICAL FIX: Added await
                if decoded_payload:
                    print("SUCCESS: JWT validation passed")
                    return True
                else:
                    print("FAILED: JWT validation failed - this causes 403 errors")
                    return False
                    
            except Exception as e:
                print(f"ERROR during token test: {e}")
                return False
            finally:
                if original_env2:
                    os.environ["ENVIRONMENT"] = original_env2
                else:
                    os.environ.pop("ENVIRONMENT", None)
    
    else:
        print("ERROR: Could not retrieve JWT secrets for comparison")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())  # CRITICAL FIX: Added asyncio.run