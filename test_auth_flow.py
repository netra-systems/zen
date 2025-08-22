#!/usr/bin/env python3
"""
Comprehensive Authentication Flow Test
Tests the complete authentication system including dev login, JWT tokens, and service integration.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import httpx
import pytest


async def test_auth_service_health():
    """Test auth service health endpoint"""
    auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{auth_url}/health")
            print(f"Auth service health: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"Auth service health check failed: {e}")
            return False


async def test_auth_config():
    """Test auth configuration endpoint"""
    auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{auth_url}/auth/config")
            print(f"Auth config: {response.status_code}")
            config = response.json()
            print(f"Config keys: {list(config.keys())}")
            print(f"Endpoints: {config.get('endpoints', {})}")
            return response.status_code == 200
        except Exception as e:
            print(f"Auth config failed: {e}")
            return False


async def test_dev_login():
    """Test dev login flow"""
    auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test dev login
            response = await client.post(f"{auth_url}/auth/dev/login")
            print(f"Dev login: {response.status_code}")
            
            if response.status_code == 200:
                auth_data = response.json()
                print(f"Login successful!")
                print(f"User: {auth_data.get('user', {})}")
                print(f"Token present: {bool(auth_data.get('access_token'))}")
                
                # Test token validation
                token = auth_data.get('access_token')
                if token:
                    headers = {"Authorization": f"Bearer {token}"}
                    validate_response = await client.post(
                        f"{auth_url}/auth/validate",
                        json={"token": token}
                    )
                    print(f"Token validation: {validate_response.status_code}")
                    if validate_response.status_code == 200:
                        print(f"Token valid: {validate_response.json()}")
                    
                return True
            else:
                print(f"Dev login failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Dev login test failed: {e}")
            return False


async def test_backend_token_validation():
    """Test backend service can validate tokens"""
    auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    async with httpx.AsyncClient() as client:
        try:
            # Get token from dev login
            response = await client.post(f"{auth_url}/auth/dev/login")
            if response.status_code != 200:
                print(f"Failed to get token: {response.status_code}")
                return False
                
            auth_data = response.json()
            token = auth_data.get('access_token')
            
            if not token:
                print("No token received from dev login")
                return False
            
            # Test backend endpoint with token
            headers = {"Authorization": f"Bearer {token}"}
            backend_response = await client.get(
                f"{backend_url}/threads",
                headers=headers
            )
            
            print(f"Backend auth test: {backend_response.status_code}")
            if backend_response.status_code == 200:
                print("Backend successfully validated token!")
                return True
            else:
                print(f"Backend auth failed: {backend_response.text}")
                return False
                
        except Exception as e:
            print(f"Backend token validation test failed: {e}")
            return False


async def test_cors_configuration():
    """Test CORS configuration"""
    auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test preflight request
            headers = {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type"
            }
            response = await client.options(
                f"{auth_url}/auth/dev/login",
                headers=headers
            )
            
            print(f"CORS preflight: {response.status_code}")
            print(f"CORS headers: {dict(response.headers)}")
            
            # Check CORS headers
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            print(f"CORS configuration: {cors_headers}")
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"CORS test failed: {e}")
            return False


async def main():
    """Run all authentication tests"""
    print("Authentication Flow Audit")
    print("=" * 50)
    
    tests = [
        ("Auth Service Health", test_auth_service_health),
        ("Auth Configuration", test_auth_config),
        ("Dev Login Flow", test_dev_login),
        ("Backend Token Validation", test_backend_token_validation),
        ("CORS Configuration", test_cors_configuration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\nTesting: {test_name}")
        print("-" * 30)
        try:
            result = await test_func()
            results[test_name] = result
            status = "PASS" if result else "FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"ERROR: {e}")
            results[test_name] = False
    
    print("\nTest Results Summary")
    print("=" * 50)
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("All authentication tests passed!")
        return 0
    else:
        print("Some authentication tests failed. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))