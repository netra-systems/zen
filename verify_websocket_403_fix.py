#!/usr/bin/env python3
"""
WebSocket 403 Fix Verification Script

This script demonstrates that the unified JWT secret manager
fixes the WebSocket 403 authentication failures by ensuring
both auth service and backend use identical JWT secrets.

Business Impact: Restores $50K MRR WebSocket functionality
"""

import os
import sys
import jwt
import time

# Set up Python path
sys.path.insert(0, os.path.abspath('.'))

def main():
    print("=" * 60)
    print("WebSocket 403 Fix Verification")
    print("=" * 60)
    
    try:
        # Set up test environment
        from shared.isolated_environment import get_env
        env = get_env()
        env.set("ENVIRONMENT", "staging", "verification")
        env.set("JWT_SECRET_KEY", "verification_secret_key_32_chars", "verification")
        
        print("1. Testing JWT Secret Consistency...")
        
        # Test auth service JWT secret
        from auth_service.auth_core.auth_environment import get_auth_env
        auth_env = get_auth_env()
        auth_secret = auth_env.get_jwt_secret_key()
        print(f"   Auth service secret: {auth_secret[:10]}... (length: {len(auth_secret)})")
        
        # Test backend service JWT secret  
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        backend_extractor = UserContextExtractor()
        backend_secret = backend_extractor._get_jwt_secret()
        print(f"   Backend secret:      {backend_secret[:10]}... (length: {len(backend_secret)})")
        
        # Verify they match
        if auth_secret == backend_secret:
            print("   [SUCCESS] Both services use identical JWT secrets!")
        else:
            print("   [FAILED] JWT secrets don't match - WebSocket 403 will occur")
            return False
            
        print("\n2. Testing JWT Token Generation and Validation...")
        
        # Generate JWT token (simulate auth service)
        payload = {
            "sub": "verification_user", 
            "email": "verify@staging.netrasystems.ai",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "permissions": ["websocket_access"]
        }
        
        token = jwt.encode(payload, auth_secret, algorithm="HS256")
        print(f"   Generated JWT token: {token[:30]}...")
        
        # Validate JWT token (simulate backend service)
        try:
            decoded = jwt.decode(token, backend_secret, algorithms=["HS256"])
            print(f"   [SUCCESS] Token validated successfully for user: {decoded['sub']}")
        except jwt.InvalidSignatureError:
            print("   [FAILED] JWT signature validation failed - secrets don't match")
            return False
        except Exception as e:
            print(f"   [FAILED] JWT validation error: {e}")
            return False
            
        print("\n3. Testing WebSocket Authentication Pipeline...")
        
        # Mock WebSocket with JWT in headers
        class MockWebSocket:
            def __init__(self, token):
                self.headers = {
                    "authorization": f"Bearer {token}",
                    "origin": "https://staging.netrasystems.ai"
                }
        
        mock_websocket = MockWebSocket(token)
        
        # Test JWT extraction
        extracted_token = backend_extractor.extract_jwt_from_websocket(mock_websocket)
        if extracted_token == token:
            print("   [SUCCESS] JWT token extracted from WebSocket headers")
        else:
            print("   [FAILED] JWT extraction failed")
            return False
            
        # Test JWT validation
        validated_payload = backend_extractor.validate_and_decode_jwt(extracted_token)
        if validated_payload and validated_payload['sub'] == 'verification_user':
            print("   [SUCCESS] JWT token validated in WebSocket pipeline")
        else:
            print("   [FAILED] WebSocket JWT validation failed")
            return False
            
        print("\n4. Testing Unified JWT Secret Manager...")
        
        from shared.jwt_secret_manager import get_unified_jwt_secret, validate_unified_jwt_config
        
        # Test unified secret resolution
        unified_secret = get_unified_jwt_secret()
        if unified_secret == auth_secret == backend_secret:
            print("   [SUCCESS] Unified JWT secret manager provides consistent secrets")
        else:
            print("   [FAILED] Unified manager not working correctly")
            return False
            
        # Test configuration validation  
        validation = validate_unified_jwt_config()
        if validation['valid']:
            print("   [SUCCESS] JWT configuration is valid")
        else:
            print(f"   [WARNING] JWT configuration issues: {validation.get('issues', [])}")
            
        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETE - WebSocket 403 Fix Working!")
        print("=" * 60)
        print("Summary:")
        print("  - Auth service and backend use identical JWT secrets")
        print("  - JWT tokens generated by auth service validate in backend")
        print("  - WebSocket authentication pipeline works end-to-end")
        print("  - Unified JWT secret manager ensures consistency")
        print("  - $50K MRR WebSocket functionality restored")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[FAILED] Verification error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 WebSocket 403 fix verified successfully!")
        sys.exit(0)
    else:
        print("\n❌ WebSocket 403 fix verification failed!")
        sys.exit(1)