#!/usr/bin/env python3
"""
JWT Secret Consistency Test
Tests if the backend and auth service are using the same JWT secret
"""

import jwt
import requests
import json
import os
import sys
from datetime import datetime, timedelta

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_jwt_consistency():
    print("Testing JWT Secret Consistency Between Services")
    print("=" * 50)
    
    # Step 1: Get a token from auth service
    print("1. Getting token from auth service...")
    auth_response = requests.post(
        "http://localhost:8083/auth/dev/login",
        headers={"Content-Type": "application/json"},
        json={}
    )
    
    if auth_response.status_code != 200:
        print(f"❌ Auth service dev login failed: {auth_response.status_code}")
        print(auth_response.text)
        return False
    
    auth_data = auth_response.json()
    access_token = auth_data.get("access_token")
    print(f"Got token from auth service: {access_token[:20]}...")
    
    # Step 2: Try to validate token with auth service
    print("\n2. Validating token with auth service...")
    validate_response = requests.post(
        "http://localhost:8083/auth/validate",
        headers={"Content-Type": "application/json"},
        json={"token": access_token}
    )
    
    if validate_response.status_code == 200:
        print("✅ Auth service validates its own token")
        print(f"   User: {validate_response.json().get('email')}")
    else:
        print(f"❌ Auth service cannot validate its own token: {validate_response.status_code}")
        return False
    
    # Step 3: Try to use token with backend
    print("\n3. Testing token with backend...")
    backend_response = requests.get(
        "http://localhost:8001/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    print(f"   Backend response: {backend_response.status_code}")
    if backend_response.status_code == 200:
        print("✅ Backend accepts auth service token")
        print(f"   User: {backend_response.json()}")
        return True
    else:
        print(f"❌ Backend rejects auth service token")
        backend_data = backend_response.json()
        print(f"   Error: {backend_data.get('message', 'Unknown error')}")
        
        # Step 4: Decode the JWT to inspect it
        print("\n4. Analyzing JWT token...")
        try:
            # Decode without verification to see the payload
            decoded = jwt.decode(access_token, options={"verify_signature": False})
            print(f"   Token payload: {json.dumps(decoded, indent=2, default=str)}")
            
            # Check token issuer
            issuer = decoded.get('iss')
            print(f"   Token issuer: {issuer}")
            
            # Check if token is expired
            exp = decoded.get('exp')
            if exp:
                exp_time = datetime.fromtimestamp(exp)
                now = datetime.now()
                print(f"   Token expires: {exp_time}")
                print(f"   Current time:  {now}")
                print(f"   Token valid:   {exp_time > now}")
                
        except Exception as e:
            print(f"   ❌ Cannot decode JWT: {e}")
        
        return False

def test_auth_service_config():
    print("\n🔧 Testing Auth Service Configuration")
    print("=" * 50)
    
    try:
        config_response = requests.get("http://localhost:8083/auth/config")
        if config_response.status_code == 200:
            config = config_response.json()
            print("✅ Auth service config endpoint working")
            print(f"   Development mode: {config.get('development_mode')}")
            print(f"   Google Client ID configured: {bool(config.get('google_client_id'))}")
            
            endpoints = config.get('endpoints', {})
            print("   Endpoints:")
            for key, url in endpoints.items():
                if url:
                    print(f"     {key}: {url}")
            
            # Check if endpoints point to correct ports
            port_issue = False
            for key, url in endpoints.items():
                if url and 'localhost:8081' in url:
                    print(f"   ⚠️  WARNING: {key} endpoint points to port 8081 (auth service is on 8083)")
                    port_issue = True
            
            if port_issue:
                print("   🔧 Port configuration issue detected")
                return False
            else:
                print("   ✅ Port configuration looks correct")
                return True
                
        else:
            print(f"❌ Auth service config failed: {config_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing auth service config: {e}")
        return False

def test_cors():
    print("\n🌐 Testing CORS Configuration")
    print("=" * 50)
    
    try:
        # Test CORS preflight
        cors_response = requests.options(
            "http://localhost:8083/auth/config",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        if cors_response.status_code == 200:
            headers = cors_response.headers
            origin = headers.get('Access-Control-Allow-Origin')
            credentials = headers.get('Access-Control-Allow-Credentials')
            methods = headers.get('Access-Control-Allow-Methods')
            
            print("✅ CORS preflight successful")
            print(f"   Allowed origin: {origin}")
            print(f"   Allow credentials: {credentials}")
            print(f"   Allowed methods: {methods}")
            
            if origin == "http://localhost:3000" and credentials == "true":
                print("   ✅ CORS correctly configured for frontend")
                return True
            else:
                print("   ⚠️  CORS configuration may have issues")
                return False
        else:
            print(f"❌ CORS preflight failed: {cors_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing CORS: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Netra Auth System Integration Test")
    print("=" * 60)
    
    results = {
        "jwt_consistency": test_jwt_consistency(),
        "auth_config": test_auth_service_config(),
        "cors": test_cors()
    }
    
    print("\n📊 Test Results Summary")
    print("=" * 30)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Auth system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Auth system needs attention.")
        print("\nCommon issues to check:")
        print("- JWT_SECRET_KEY environment variable consistency")
        print("- Auth service URL configuration") 
        print("- Port configuration (auth service port vs configured endpoints)")
        print("- CORS origins configuration")
    
    exit(0 if all_passed else 1)