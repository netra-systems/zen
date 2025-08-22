#!/usr/bin/env python3
"""
Simple Auth System Test
Tests the auth flow between services
"""

import requests
import json
import jwt
from datetime import datetime

def test_auth_flow():
    print("Testing Netra Auth System")
    print("=" * 40)
    
    # Test 1: Auth service dev login
    print("1. Testing auth service dev login...")
    try:
        auth_response = requests.post(
            "http://localhost:8083/auth/dev/login",
            headers={"Content-Type": "application/json"},
            json={},
            timeout=10
        )
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            access_token = auth_data.get("access_token")
            print("   SUCCESS: Got token from auth service")
            print(f"   Token: {access_token[:30]}...")
            print(f"   User: {auth_data.get('user', {}).get('email', 'N/A')}")
        else:
            print(f"   FAILED: Status {auth_response.status_code}")
            print(f"   Error: {auth_response.text}")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False
    
    # Test 2: Token validation by auth service
    print("\n2. Testing token validation by auth service...")
    try:
        validate_response = requests.post(
            "http://localhost:8083/auth/validate",
            headers={"Content-Type": "application/json"},
            json={"token": access_token},
            timeout=10
        )
        
        if validate_response.status_code == 200:
            print("   SUCCESS: Auth service validates its own token")
        else:
            print(f"   FAILED: Status {validate_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False
    
    # Test 3: Backend token validation
    print("\n3. Testing backend token validation...")
    try:
        backend_response = requests.get(
            "http://localhost:8001/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        if backend_response.status_code == 200:
            print("   SUCCESS: Backend accepts auth service token")
            backend_data = backend_response.json()
            print(f"   User ID: {backend_data.get('id', 'N/A')}")
            return True
        else:
            print(f"   FAILED: Status {backend_response.status_code}")
            backend_data = backend_response.json()
            print(f"   Error: {backend_data.get('message', 'Unknown error')}")
            
            # Analyze the JWT
            print("\n   Analyzing JWT token...")
            try:
                decoded = jwt.decode(access_token, options={"verify_signature": False})
                print(f"   Issuer: {decoded.get('iss', 'N/A')}")
                print(f"   Subject: {decoded.get('sub', 'N/A')}")
                print(f"   Email: {decoded.get('email', 'N/A')}")
                
                exp = decoded.get('exp')
                if exp:
                    exp_time = datetime.fromtimestamp(exp)
                    now = datetime.now()
                    print(f"   Expires: {exp_time}")
                    print(f"   Valid: {exp_time > now}")
                    
            except Exception as decode_error:
                print(f"   JWT decode error: {decode_error}")
            
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def test_cors():
    print("\n4. Testing CORS configuration...")
    try:
        cors_response = requests.options(
            "http://localhost:8083/auth/config",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            },
            timeout=10
        )
        
        if cors_response.status_code == 200:
            origin = cors_response.headers.get('Access-Control-Allow-Origin')
            credentials = cors_response.headers.get('Access-Control-Allow-Credentials')
            
            print("   SUCCESS: CORS working")
            print(f"   Allowed origin: {origin}")
            print(f"   Allow credentials: {credentials}")
            
            return origin == "http://localhost:3000" and credentials == "true"
        else:
            print(f"   FAILED: Status {cors_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def test_oauth_config():
    print("\n5. Testing OAuth configuration...")
    try:
        config_response = requests.get(
            "http://localhost:8083/auth/config",
            timeout=10
        )
        
        if config_response.status_code == 200:
            config = config_response.json()
            print("   SUCCESS: Config endpoint working")
            print(f"   Development mode: {config.get('development_mode')}")
            print(f"   Google Client ID set: {bool(config.get('google_client_id'))}")
            
            # Check endpoint URLs
            endpoints = config.get('endpoints', {})
            port_issues = 0
            for key, url in endpoints.items():
                if url and 'localhost:8081' in url:
                    print(f"   WARNING: {key} points to port 8081 (should be 8083)")
                    port_issues += 1
            
            return port_issues == 0
            
        else:
            print(f"   FAILED: Status {config_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Netra Auth System Test Suite")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("Auth Flow", test_auth_flow),
        ("CORS", test_cors),
        ("OAuth Config", test_oauth_config)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"   EXCEPTION in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\nAll tests passed! Auth system is working.")
    else:
        print("\nSome tests failed. Issues detected:")
        print("- JWT secret mismatch between services")
        print("- Auth service URL configuration issues")  
        print("- CORS configuration problems")
    
    exit(0 if all_passed else 1)