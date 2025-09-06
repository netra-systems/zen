#!/usr/bin/env python3
"""
WebSocket Authentication Failure Debug Script

This script tests the complete WebSocket authentication flow to identify the root cause
of the 100% authentication failure rate.

We will test:
1. JWT token generation and validation
2. Frontend token encoding
3. Backend token extraction and decoding  
4. WebSocket subprotocol authentication
5. User context creation
"""
import asyncio
import base64
import json
import jwt
import sys
import os
from datetime import datetime, timedelta, timezone

# Add project path
sys.path.insert(0, os.path.dirname(__file__))

from shared.isolated_environment import get_env

async def test_jwt_flow():
    """Test the complete JWT authentication flow."""
    print("[DEBUG] TESTING WEBSOCKET JWT AUTHENTICATION FLOW")
    print("=" * 60)
    
    # Get environment
    env = get_env()
    jwt_secret = env.get("JWT_SECRET_KEY")
    
    if not jwt_secret:
        print("[ERROR] CRITICAL: JWT_SECRET_KEY not found in environment")
        return False
    
    print(f"[OK] JWT_SECRET_KEY found (length: {len(jwt_secret)})")
    
    # 1. Generate a test JWT token (simulating frontend)
    print("\n1. [TOKEN] Generating test JWT token...")
    
    test_payload = {
        "sub": "test_user_12345",  # User ID
        "email": "test@example.com",
        "permissions": ["user", "chat"],
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        "iss": "netra-auth"
    }
    
    try:
        test_token = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
        print(f"[OK] JWT token generated successfully")
        print(f"   Token preview: {test_token[:50]}...")
        print(f"   Payload: {test_payload}")
    except Exception as e:
        print(f"[ERROR] Failed to generate JWT token: {e}")
        return False
    
    # 2. Test JWT token validation (simulating backend)
    print("\n2. [DEBUG] Testing JWT token validation...")
    
    try:
        decoded_payload = jwt.decode(test_token, jwt_secret, algorithms=["HS256"])
        print(f"[OK] JWT token decoded successfully")
        print(f"   Decoded payload: {decoded_payload}")
        
        # Verify required fields
        if not decoded_payload.get("sub"):
            print("[ERROR] CRITICAL: Missing 'sub' (user_id) in JWT payload")
            return False
            
        print(f"[OK] User ID extracted: {decoded_payload.get('sub')}")
        
    except jwt.ExpiredSignatureError:
        print("[ERROR] JWT token expired")
        return False
    except jwt.InvalidTokenError as e:
        print(f"[ERROR] Invalid JWT token: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] JWT validation error: {e}")
        return False
    
    # 3. Test WebSocket subprotocol encoding (simulating frontend)
    print("\n3. [WEBSOCKET] Testing WebSocket subprotocol encoding...")
    
    try:
        # This is how the frontend encodes the token
        encoder = TextEncoder()
        data = encoder.encode(test_token)
        base64_encoded = base64.b64encode(data).decode('utf-8')
        # Convert to base64url format (URL-safe)
        base64url_encoded = base64_encoded.replace('+', '-').replace('/', '_').replace('=', '')
        
        print(f"[OK] Token encoded for WebSocket subprotocol")
        print(f"   Original token length: {len(test_token)}")
        print(f"   Base64URL encoded length: {len(base64url_encoded)}")
        print(f"   Encoded preview: {base64url_encoded[:50]}...")
        
        # Test the subprotocol format
        subprotocol = f"jwt.{base64url_encoded}"
        print(f"[OK] WebSocket subprotocol: jwt.[{len(base64url_encoded)} chars]")
        
    except Exception as e:
        print(f"[ERROR] Failed to encode token for WebSocket: {e}")
        return False
    
    # 4. Test WebSocket subprotocol decoding (simulating backend)
    print("\n4. [DECODE] Testing WebSocket subprotocol decoding...")
    
    try:
        # This simulates the backend extraction from UserContextExtractor
        if subprotocol.startswith("jwt."):
            encoded_token = subprotocol[4:]  # Remove "jwt." prefix
            
            # Add padding if needed
            missing_padding = len(encoded_token) % 4
            if missing_padding:
                encoded_token += '=' * (4 - missing_padding)
            
            # Convert back from base64url to regular base64
            base64_token = encoded_token.replace('-', '+').replace('_', '/')
            decoded_token = base64.b64decode(base64_token).decode('utf-8')
            
            print(f"[OK] Token extracted from subprotocol")
            print(f"   Decoded token length: {len(decoded_token)}")
            print(f"   Decoded token preview: {decoded_token[:50]}...")
            
            # Verify it matches the original
            if decoded_token == test_token:
                print("[OK] Token matches original - encoding/decoding successful")
            else:
                print("[ERROR] CRITICAL: Decoded token does not match original")
                print(f"   Original:  {test_token[:50]}...")
                print(f"   Decoded:   {decoded_token[:50]}...")
                return False
        else:
            print("[ERROR] Invalid subprotocol format")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to decode token from WebSocket subprotocol: {e}")
        return False
    
    # 5. Test UserContextExtractor flow
    print("\n5. [USER] Testing UserContextExtractor flow...")
    
    try:
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        extractor = UserContextExtractor()
        print(f"[OK] UserContextExtractor initialized")
        print(f"   JWT secret configured: {bool(extractor.jwt_secret_key)}")
        print(f"   JWT algorithm: {extractor.jwt_algorithm}")
        
        # Test JWT validation
        jwt_payload = extractor.validate_and_decode_jwt(test_token)
        if jwt_payload:
            print(f"[OK] JWT validation successful via UserContextExtractor")
            print(f"   User ID: {jwt_payload.get('sub')}")
            print(f"   Email: {jwt_payload.get('email')}")
            print(f"   Permissions: {jwt_payload.get('permissions')}")
        else:
            print("[ERROR] CRITICAL: JWT validation failed via UserContextExtractor")
            return False
            
    except Exception as e:
        print(f"[ERROR] UserContextExtractor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Test complete authentication flow
    print("\n6. [AUTH] Testing complete authentication flow...")
    
    try:
        from netra_backend.app.models.user_execution_context import UserExecutionContext
        
        # Simulate WebSocket connection mock
        class MockWebSocket:
            def __init__(self, token):
                self.headers = {
                    "sec-websocket-protocol": f"jwt.{base64url_encoded}"
                }
        
        mock_websocket = MockWebSocket(test_token)
        
        # Test token extraction
        extracted_token = extractor.extract_jwt_from_websocket(mock_websocket)
        if extracted_token:
            print(f"[OK] Token extracted from mock WebSocket")
            if extracted_token == test_token:
                print("[OK] Extracted token matches original")
            else:
                print("[ERROR] CRITICAL: Extracted token does not match")
                return False
        else:
            print("[ERROR] CRITICAL: Failed to extract token from WebSocket")
            return False
        
        # Test user context creation
        user_context = extractor.create_user_context_from_jwt(
            jwt_payload, mock_websocket
        )
        
        if user_context:
            print(f"[OK] UserExecutionContext created successfully")
            print(f"   User ID: {user_context.user_id}")
            print(f"   Thread ID: {user_context.thread_id}")
            print(f"   Request ID: {user_context.request_id}")
            print(f"   WebSocket Connection ID: {user_context.websocket_connection_id}")
        else:
            print("[ERROR] CRITICAL: Failed to create UserExecutionContext")
            return False
            
    except Exception as e:
        print(f"[ERROR] Complete authentication flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL WEBSOCKET AUTHENTICATION TESTS PASSED!")
    print("[OK] JWT generation, validation, encoding, and extraction working correctly")
    print("[OK] UserContextExtractor functioning properly")
    print("[OK] WebSocket authentication flow is intact")
    print("\n[NEXT] NEXT STEPS:")
    print("1. Check if the frontend is sending tokens correctly")
    print("2. Verify WebSocket route is using the correct authentication")
    print("3. Check for any middleware blocking authentication")
    print("4. Verify environment variables are loaded in the WebSocket service")
    
    return True

class TextEncoder:
    """Mock TextEncoder for Python (browser TextEncoder equivalent)"""
    def encode(self, text):
        return text.encode('utf-8')

if __name__ == "__main__":
    print("[CRITICAL] WEBSOCKET AUTHENTICATION FAILURE DIAGNOSTIC")
    print("Testing complete authentication flow to find root cause...")
    
    try:
        asyncio.run(test_jwt_flow())
    except KeyboardInterrupt:
        print("\n[WARNING] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Test failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()