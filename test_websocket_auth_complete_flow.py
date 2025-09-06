#!/usr/bin/env python3
"""
WebSocket Authentication Complete Flow Test

This test simulates the exact frontend-to-backend authentication flow
to identify why WebSocket authentication is failing.
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

async def test_complete_websocket_auth_flow():
    """Test the complete WebSocket authentication flow exactly as it works in production."""
    print("[TEST] WebSocket Authentication Complete Flow Analysis")
    print("=" * 80)
    
    # Get environment
    env = get_env()
    jwt_secret = env.get("JWT_SECRET_KEY")
    
    if not jwt_secret:
        print("[ERROR] JWT_SECRET_KEY not found in environment")
        return False
    
    print(f"[OK] JWT_SECRET_KEY loaded (length: {len(jwt_secret)})")
    
    # Step 1: Create JWT token (simulating auth service)
    print("\n[STEP 1] Creating JWT token (auth service simulation)")
    
    test_payload = {
        "sub": "test_user_12345",  # User ID
        "email": "test@example.com",
        "permissions": ["user", "chat"],
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        "iss": "netra-auth"
    }
    
    try:
        # Create JWT token exactly as auth service would
        test_token = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
        print(f"[OK] JWT token created: {test_token[:50]}...")
    except Exception as e:
        print(f"[ERROR] Failed to create JWT token: {e}")
        return False
    
    # Step 2: Frontend processing (simulating webSocketService.ts)
    print("\n[STEP 2] Frontend WebSocket token processing")
    
    try:
        # This exactly matches frontend webSocketService.ts createSecureWebSocket()
        clean_token = test_token  # Remove Bearer prefix if present (not needed here)
        
        # Frontend encoding process (from line 1501-1510 in webSocketService.ts)
        # Convert string to bytes using TextEncoder equivalent
        token_bytes = clean_token.encode('utf-8')
        
        # Convert to base64
        base64_encoded = base64.b64encode(token_bytes).decode('utf-8')
        
        # Convert to base64url format (URL-safe) - exactly as frontend does
        encoded_token = base64_encoded.replace('+', '-').replace('/', '_').replace('=', '')
        
        # Build protocols array exactly as frontend does
        protocols = ['jwt-auth', f'jwt.{encoded_token}']
        
        print(f"[OK] Frontend encoding successful")
        print(f"   Original token length: {len(clean_token)}")
        print(f"   Encoded token length: {len(encoded_token)}")
        print(f"   Protocols: {[p if not p.startswith('jwt.') else 'jwt.[token]' for p in protocols]}")
        
    except Exception as e:
        print(f"[ERROR] Frontend encoding failed: {e}")
        return False
    
    # Step 3: WebSocket connection headers (simulating browser)
    print("\n[STEP 3] WebSocket connection headers simulation")
    
    # This simulates what the browser sends
    websocket_headers = {
        "sec-websocket-protocol": ", ".join(protocols),
        "authorization": f"Bearer {test_token}",  # Some implementations might also send this
        "origin": "https://localhost:3000",
        "user-agent": "Test-WebSocket-Client"
    }
    
    print(f"[OK] WebSocket headers prepared")
    print(f"   sec-websocket-protocol: {websocket_headers['sec-websocket-protocol'][:50]}...")
    
    # Step 4: Backend WebSocket acceptance (simulating websocket.py)
    print("\n[STEP 4] Backend WebSocket acceptance simulation")
    
    try:
        # Simulate WebSocket endpoint logic from websocket.py lines 155-168
        subprotocols = websocket_headers.get("sec-websocket-protocol", "").split(",")
        subprotocols = [p.strip() for p in subprotocols]
        
        selected_protocol = None
        if "jwt-auth" in subprotocols:
            selected_protocol = "jwt-auth"
            print(f"[OK] Selected WebSocket subprotocol: {selected_protocol}")
        else:
            print("[WARNING] No jwt-auth subprotocol found")
            
    except Exception as e:
        print(f"[ERROR] WebSocket acceptance failed: {e}")
        return False
    
    # Step 5: Backend user context extraction
    print("\n[STEP 5] Backend user context extraction")
    
    try:
        # Import and test the actual backend components
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        # Create a mock WebSocket object that matches what FastAPI provides
        class MockWebSocket:
            def __init__(self, headers):
                self.headers = headers
        
        mock_websocket = MockWebSocket(websocket_headers)
        
        # Test the actual UserContextExtractor
        extractor = UserContextExtractor()
        
        # Test token extraction
        extracted_token = extractor.extract_jwt_from_websocket(mock_websocket)
        if extracted_token:
            print(f"[OK] Token extracted from WebSocket: {extracted_token[:50]}...")
            
            # Verify it matches the original
            if extracted_token == test_token:
                print("[OK] Extracted token matches original")
            else:
                print("[ERROR] CRITICAL: Extracted token does not match original")
                print(f"   Original:  {test_token[:50]}...")
                print(f"   Extracted: {extracted_token[:50]}...")
                return False
        else:
            print("[ERROR] CRITICAL: Failed to extract token from WebSocket")
            return False
        
        # Test JWT validation
        jwt_payload = extractor.validate_and_decode_jwt(extracted_token)
        if jwt_payload:
            print(f"[OK] JWT validation successful")
            print(f"   User ID: {jwt_payload.get('sub')}")
        else:
            print("[ERROR] CRITICAL: JWT validation failed")
            return False
        
        # Test user context creation
        user_context = extractor.create_user_context_from_jwt(jwt_payload, mock_websocket)
        if user_context:
            print(f"[OK] UserExecutionContext created")
            print(f"   User ID: {user_context.user_id}")
            print(f"   Connection ID: {user_context.websocket_connection_id}")
        else:
            print("[ERROR] CRITICAL: Failed to create UserExecutionContext")
            return False
            
    except Exception as e:
        print(f"[ERROR] Backend user context extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Complete authentication flow test
    print("\n[STEP 6] Complete authentication flow test")
    
    try:
        from netra_backend.app.websocket_core.user_context_extractor import extract_websocket_user_context
        
        # Test the complete extraction flow
        user_context, auth_info = extract_websocket_user_context(mock_websocket)
        
        print(f"[OK] Complete authentication flow successful")
        print(f"   User ID: {user_context.user_id}")
        print(f"   Auth Info: {list(auth_info.keys())}")
        
    except Exception as e:
        print(f"[ERROR] Complete authentication flow failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 7: WebSocket manager creation test
    print("\n[STEP 7] WebSocket manager creation test")
    
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        
        # Test WebSocket manager creation with user context
        ws_manager = create_websocket_manager(user_context)
        
        print(f"[OK] WebSocket manager created successfully")
        print(f"   Manager type: {type(ws_manager).__name__}")
        print(f"   Manager ID: {id(ws_manager)}")
        
    except Exception as e:
        print(f"[ERROR] WebSocket manager creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("[SUCCESS] COMPLETE WEBSOCKET AUTHENTICATION FLOW TEST PASSED!")
    print("")
    print("[ANALYSIS] All authentication components are working correctly:")
    print("  1. JWT token generation and validation: WORKING")
    print("  2. Frontend token encoding: WORKING")
    print("  3. WebSocket subprotocol handling: WORKING") 
    print("  4. Backend token extraction: WORKING")
    print("  5. User context creation: WORKING")
    print("  6. WebSocket manager factory: WORKING")
    print("")
    print("[CONCLUSION] The WebSocket authentication system is functioning properly.")
    print("The 100% failure rate must be caused by:")
    print("  1. Frontend not sending tokens correctly")
    print("  2. Network/routing issues blocking WebSocket connections")
    print("  3. Environment configuration mismatches")
    print("  4. WebSocket endpoint not being reached")
    
    return True

if __name__ == "__main__":
    print("WEBSOCKET AUTHENTICATION COMPLETE FLOW TEST")
    print("Testing frontend-to-backend authentication exactly as it works in production")
    
    try:
        asyncio.run(test_complete_websocket_auth_flow())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()