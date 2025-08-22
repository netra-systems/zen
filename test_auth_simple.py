#!/usr/bin/env python3
"""
Simple Authentication Test Script for Netra Platform

Tests dev login endpoint and JWT token generation without Unicode characters.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

import httpx

# Service URLs from running services
BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8083"

async def test_auth_flow():
    """Test authentication flow."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests_passed": 0,
        "tests_failed": 0,
        "auth_token": None,
        "errors": []
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Starting Authentication Tests")
        
        # Test Backend Health
        try:
            response = await client.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                print("PASS: Backend Health")
                results["tests_passed"] += 1
            else:
                print(f"FAIL: Backend Health - Status {response.status_code}")
                results["tests_failed"] += 1
        except Exception as e:
            print(f"FAIL: Backend Health - {str(e)}")
            results["tests_failed"] += 1
        
        # Test Auth Service Health
        try:
            response = await client.get(f"{AUTH_SERVICE_URL}/health")
            if response.status_code == 200:
                print("PASS: Auth Service Health")
                results["tests_passed"] += 1
            else:
                print(f"FAIL: Auth Service Health - Status {response.status_code}")
                results["tests_failed"] += 1
        except Exception as e:
            print(f"FAIL: Auth Service Health - {str(e)}")
            results["tests_failed"] += 1
        
        # Test Dev Login
        auth_token = None
        try:
            # Try backend first
            response = await client.post(
                f"{BACKEND_URL}/api/auth/dev/login",
                json={"email": "test@netra.ai"}
            )
            
            if response.status_code == 200:
                data = response.json()
                auth_token = data.get("access_token")
                if auth_token:
                    results["auth_token"] = auth_token
                    print(f"PASS: Dev Login - Token: {auth_token[:20]}...")
                    results["tests_passed"] += 1
                else:
                    print("FAIL: Dev Login - No token in response")
                    results["tests_failed"] += 1
            else:
                # Try auth service directly
                response = await client.post(
                    f"{AUTH_SERVICE_URL}/auth/dev/login",
                    json={}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    auth_token = data.get("access_token")
                    if auth_token:
                        results["auth_token"] = auth_token
                        print(f"PASS: Dev Login (Auth Service) - Token: {auth_token[:20]}...")
                        results["tests_passed"] += 1
                    else:
                        print("FAIL: Dev Login - No token from auth service")
                        results["tests_failed"] += 1
                else:
                    print(f"FAIL: Dev Login - Backend: {response.status_code}")
                    results["tests_failed"] += 1
        except Exception as e:
            print(f"FAIL: Dev Login - {str(e)}")
            results["tests_failed"] += 1
        
        # Test Token Validation
        if auth_token:
            try:
                import jwt
                decoded = jwt.decode(auth_token, options={"verify_signature": False})
                print("PASS: Token Validation - Valid JWT structure")
                results["tests_passed"] += 1
            except Exception as e:
                print(f"FAIL: Token Validation - {str(e)}")
                results["tests_failed"] += 1
        
        # Test Authenticated Request
        if auth_token:
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                response = await client.get(f"{BACKEND_URL}/api/threads/", headers=headers)
                
                if response.status_code == 200:
                    print("PASS: Authenticated Request")
                    results["tests_passed"] += 1
                else:
                    print(f"FAIL: Authenticated Request - Status {response.status_code}")
                    results["tests_failed"] += 1
            except Exception as e:
                print(f"FAIL: Authenticated Request - {str(e)}")
                results["tests_failed"] += 1
    
    return results

async def main():
    """Main test execution."""
    results = await test_auth_flow()
    
    print(f"\nAuthentication Test Results:")
    print(f"   Passed: {results['tests_passed']}")
    print(f"   Failed: {results['tests_failed']}")
    
    if results.get("auth_token"):
        print(f"   JWT Token: Available ({len(results['auth_token'])} chars)")
    
    # Save results to file
    with open("auth_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to auth_test_results.json")
    
    # Return success if all tests passed
    success = results["tests_failed"] == 0 and results["tests_passed"] > 0
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)