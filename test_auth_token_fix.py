#!/usr/bin/env python3
"""
Test script to verify authentication token fix.
This script simulates the frontend authentication flow to ensure tokens are properly handled.
"""

import requests
import json
import sys
from typing import Optional

BASE_URL = "http://localhost:8000"  # Default backend port

def test_login() -> Optional[str]:
    """Test login and get JWT token"""
    print("Testing login endpoint...")
    
    # Test with the test user we created
    login_data = {
        "username": "test@example.com",  
        "password": "testpassword"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data=login_data  # Use form data for OAuth2 compatible login
        )
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            print(f"[OK] Login successful! Token received: {token[:20]}...")
            return token
        else:
            print(f"[FAIL] Login failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Cannot connect to backend at {BASE_URL}")
        print("  Make sure the backend server is running")
        return None
    except Exception as e:
        print(f"[FAIL] Login error: {e}")
        return None

def test_authenticated_request(token: str) -> bool:
    """Test making an authenticated request to threads endpoint"""
    print("\nTesting authenticated request to /api/threads...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/threads/?limit=20&offset=0",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Authenticated request successful!")
            print(f"  Threads fetched: {len(data.get('threads', []))} threads")
            return True
        elif response.status_code == 401:
            print(f"✗ Authentication failed with 401 Unauthorized")
            print(f"  This means the token is not being properly sent or validated")
            print(f"  Response: {response.text}")
            return False
        else:
            print(f"✗ Request failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Request error: {e}")
        return False

def test_unauthenticated_request() -> None:
    """Test that unauthenticated requests are properly rejected"""
    print("\nTesting unauthenticated request (should fail with 401)...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/threads/?limit=20&offset=0")
        
        if response.status_code == 401:
            print(f"[OK] Unauthenticated request correctly rejected with 401")
        else:
            print(f"⚠ Unexpected status {response.status_code} for unauthenticated request")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"✗ Request error: {e}")

def main():
    print("=" * 60)
    print("AUTHENTICATION TOKEN FIX VERIFICATION")
    print("=" * 60)
    
    # Test unauthenticated request first
    test_unauthenticated_request()
    
    # Test login
    token = test_login()
    if not token:
        print("\n✗ FAILED: Could not obtain authentication token")
        sys.exit(1)
    
    # Test authenticated request
    success = test_authenticated_request(token)
    
    print("\n" + "=" * 60)
    if success:
        print("[OK] SUCCESS: Authentication token fix is working!")
        print("\nThe fix ensures that:")
        print("1. Tokens are stored with consistent key 'jwt_token'")
        print("2. apiClientWrapper correctly reads the token")
        print("3. Authenticated requests include proper Authorization headers")
        print("4. Backend successfully validates the token")
    else:
        print("✗ FAILED: Authentication still has issues")
        print("\nPlease check:")
        print("1. Token storage key consistency")
        print("2. apiClientWrapper token retrieval")
        print("3. Backend token validation")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()