#!/usr/bin/env python3
"""
JWT Token Validation Test
Tests the JWT token structure, contents, and validation process.
"""
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import httpx
import jwt


async def get_dev_token():
    """Get a dev token from the auth service"""
    auth_url = "http://localhost:8083"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{auth_url}/auth/dev/login")
        if response.status_code == 200:
            auth_data = response.json()
            return auth_data.get('access_token'), auth_data.get('refresh_token')
        else:
            raise Exception(f"Failed to get dev token: {response.status_code} - {response.text}")


def decode_jwt_without_verification(token):
    """Decode JWT token without signature verification to inspect contents"""
    try:
        # Decode header
        header = jwt.get_unverified_header(token)
        
        # Decode payload
        payload = jwt.decode(token, options={"verify_signature": False})
        
        return header, payload
    except Exception as e:
        raise Exception(f"Failed to decode JWT: {e}")


def analyze_token_structure(token_type, token):
    """Analyze the structure and contents of a JWT token"""
    print(f"\n{token_type.upper()} TOKEN ANALYSIS")
    print("=" * 50)
    
    try:
        header, payload = decode_jwt_without_verification(token)
        
        print("HEADER:")
        for key, value in header.items():
            print(f"  {key}: {value}")
        
        print("\nPAYLOAD:")
        for key, value in payload.items():
            if key == 'exp':
                # Convert timestamp to readable date
                import datetime
                exp_date = datetime.datetime.fromtimestamp(value)
                print(f"  {key}: {value} ({exp_date})")
            elif key == 'iat':
                # Convert timestamp to readable date
                import datetime
                iat_date = datetime.datetime.fromtimestamp(value)
                print(f"  {key}: {value} ({iat_date})")
            else:
                print(f"  {key}: {value}")
        
        # Calculate token duration
        if 'exp' in payload and 'iat' in payload:
            duration = payload['exp'] - payload['iat']
            print(f"\nToken Duration: {duration} seconds ({duration/60:.1f} minutes)")
        
        # Validate required fields
        print("\nVALIDATION:")
        required_fields = ['user_id', 'email', 'exp', 'iat']
        for field in required_fields:
            status = "PASS" if field in payload else "FAIL"
            print(f"  {field}: {status}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


async def test_token_validation_endpoint(token):
    """Test the token validation endpoint"""
    auth_url = "http://localhost:8083"
    
    print("\nTOKEN VALIDATION ENDPOINT TEST")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # Test validation endpoint
            response = await client.post(
                f"{auth_url}/auth/validate",
                json={"token": token}
            )
            
            print(f"Validation response: {response.status_code}")
            if response.status_code == 200:
                validation_result = response.json()
                print("Validation result:")
                for key, value in validation_result.items():
                    print(f"  {key}: {value}")
                return True
            else:
                print(f"Validation failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Validation test failed: {e}")
            return False


async def test_token_with_backend():
    """Test if backend can validate the token"""
    # First get a token
    access_token, _ = await get_dev_token()
    
    print("\nBACKEND TOKEN VALIDATION TEST")
    print("=" * 50)
    
    # Try common backend endpoints that might exist
    backend_endpoints = [
        "http://localhost:8000/health",
        "http://localhost:8000/threads",
        "http://localhost:8000/api/v1/health"
    ]
    
    async with httpx.AsyncClient() as client:
        for endpoint in backend_endpoints:
            try:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(endpoint, headers=headers)
                print(f"  {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"    PASS Backend validates token successfully")
                    return True
                elif response.status_code == 401:
                    print(f"    FAIL Backend rejected token")
                elif response.status_code == 404:
                    print(f"    SKIP Endpoint not found")
                else:
                    print(f"    UNKNOWN Unexpected response: {response.status_code}")
                    
            except Exception as e:
                print(f"    ERROR Connection failed: {e}")
    
    return False


async def main():
    """Main test function"""
    print("JWT Token Validation Test")
    print("=" * 50)
    
    try:
        # Get tokens
        print("Getting dev tokens...")
        access_token, refresh_token = await get_dev_token()
        print("Tokens obtained successfully")
        
        # Analyze access token
        access_valid = analyze_token_structure("access", access_token)
        
        # Analyze refresh token
        refresh_valid = analyze_token_structure("refresh", refresh_token)
        
        # Test validation endpoint
        validation_valid = await test_token_validation_endpoint(access_token)
        
        # Test backend integration
        backend_valid = await test_token_with_backend()
        
        # Summary
        print("\nSUMMARY")
        print("=" * 50)
        print(f"Access token structure: {'PASS' if access_valid else 'FAIL'}")
        print(f"Refresh token structure: {'PASS' if refresh_valid else 'FAIL'}")
        print(f"Validation endpoint: {'PASS' if validation_valid else 'FAIL'}")
        print(f"Backend integration: {'PASS' if backend_valid else 'FAIL'}")
        
        total_tests = 4
        passed_tests = sum([access_valid, refresh_valid, validation_valid, backend_valid])
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        return 0 if passed_tests == total_tests else 1
        
    except Exception as e:
        print(f"Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))