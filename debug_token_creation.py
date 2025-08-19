#!/usr/bin/env python3
"""Debug JWT token creation for WebSocket authentication"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tests.unified.jwt_token_helpers import JWTTestHelper

def test_token_creation():
    """Test JWT token creation process"""
    print("Testing JWT token creation...")
    
    # Create JWT helper
    jwt_helper = JWTTestHelper()
    
    # Create a test user token
    payload = jwt_helper.create_valid_payload()
    print(f"Created payload: {payload}")
    
    # Create the token
    token = jwt_helper.create_token(payload)
    print(f"Created token: {token}")
    
    # Test the authenticated URL
    ws_url = "ws://localhost:8000/ws"
    authenticated_url = f"{ws_url}?token={token}"
    print(f"Authenticated URL: {authenticated_url}")
    
    return token, authenticated_url

if __name__ == "__main__":
    try:
        token, url = test_token_creation()
        print(f"\nSUCCESS: Token created successfully")
        print(f"Token length: {len(token)}")
        print(f"URL length: {len(url)}")
    except Exception as e:
        print(f"ERROR: Failed to create token: {e}")
        sys.exit(1)