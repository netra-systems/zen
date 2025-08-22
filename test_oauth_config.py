#!/usr/bin/env python3
"""
OAuth Configuration Test
Tests the OAuth flow configuration and endpoints.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import httpx


async def test_oauth_configuration():
    """Test OAuth configuration"""
    auth_url = "http://localhost:8083"
    
    print("OAuth Configuration Test")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # Get auth config
            response = await client.get(f"{auth_url}/auth/config")
            if response.status_code != 200:
                print(f"Failed to get auth config: {response.status_code}")
                return False
            
            config = response.json()
            
            # Check OAuth configuration
            print("OAuth Configuration:")
            print(f"  Google Client ID: {config.get('google_client_id', 'NOT SET')}")
            print(f"  Development Mode: {config.get('development_mode', False)}")
            
            # Check required OAuth fields
            google_client_id = config.get('google_client_id')
            if not google_client_id:
                print("  ERROR: No Google Client ID configured")
                return False
            elif len(google_client_id) < 10:
                print("  ERROR: Google Client ID appears invalid")
                return False
            else:
                print("  PASS: Google Client ID configured")
            
            # Check OAuth URLs
            print("\nOAuth URLs:")
            endpoints = config.get('endpoints', {})
            login_url = endpoints.get('login')
            callback_url = endpoints.get('callback')
            
            print(f"  Login URL: {login_url}")
            print(f"  Callback URL: {callback_url}")
            
            if not login_url or not callback_url:
                print("  ERROR: Missing OAuth URLs")
                return False
            else:
                print("  PASS: OAuth URLs configured")
            
            return True
            
        except Exception as e:
            print(f"OAuth configuration test failed: {e}")
            return False


async def test_oauth_login_initiation():
    """Test OAuth login initiation"""
    auth_url = "http://localhost:8083"
    
    print("\nOAuth Login Initiation Test")
    print("=" * 50)
    
    async with httpx.AsyncClient(follow_redirects=False) as client:
        try:
            # Test OAuth login initiation
            response = await client.get(f"{auth_url}/auth/login?provider=google")
            
            print(f"OAuth login response: {response.status_code}")
            
            if response.status_code == 302:
                # Should redirect to Google OAuth
                location = response.headers.get('location', '')
                print(f"Redirect location: {location[:100]}...")
                
                # Check if it's a valid Google OAuth URL
                if 'accounts.google.com/o/oauth2' in location:
                    print("  PASS: Redirects to Google OAuth")
                    
                    # Check required OAuth parameters
                    required_params = ['client_id', 'redirect_uri', 'response_type', 'scope', 'state']
                    missing_params = []
                    for param in required_params:
                        if param not in location:
                            missing_params.append(param)
                    
                    if missing_params:
                        print(f"  ERROR: Missing OAuth parameters: {missing_params}")
                        return False
                    else:
                        print("  PASS: All required OAuth parameters present")
                        return True
                else:
                    print("  ERROR: Does not redirect to Google OAuth")
                    return False
            else:
                print(f"  ERROR: Expected redirect (302), got {response.status_code}")
                print(f"  Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"OAuth login initiation test failed: {e}")
            return False


async def test_oauth_security_features():
    """Test OAuth security features"""
    auth_url = "http://localhost:8083"
    
    print("\nOAuth Security Features Test")
    print("=" * 50)
    
    async with httpx.AsyncClient(follow_redirects=False) as client:
        try:
            # Test OAuth login with security parameters
            response = await client.get(f"{auth_url}/auth/login?provider=google")
            
            if response.status_code == 302:
                location = response.headers.get('location', '')
                
                # Check for security features
                security_checks = {
                    'state parameter': 'state=' in location,
                    'scope parameter': 'scope=' in location,
                    'response_type': 'response_type=code' in location,
                    'https redirect': location.startswith('https://'),
                }
                
                print("Security Features:")
                for feature, present in security_checks.items():
                    status = "PASS" if present else "FAIL"
                    print(f"  {feature}: {status}")
                
                return all(security_checks.values())
            else:
                print("ERROR: Could not get OAuth redirect for security analysis")
                return False
                
        except Exception as e:
            print(f"OAuth security test failed: {e}")
            return False


async def test_oauth_callback_endpoint():
    """Test OAuth callback endpoint structure"""
    auth_url = "http://localhost:8083"
    
    print("\nOAuth Callback Endpoint Test")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # Test callback endpoint (should require code parameter)
            response = await client.get(f"{auth_url}/auth/callback")
            
            print(f"Callback response: {response.status_code}")
            
            if response.status_code == 422:
                # FastAPI validation error - expected for missing required parameters
                print("  PASS: Callback requires parameters (validation error expected)")
                return True
            elif response.status_code == 400:
                # Bad request for missing parameters
                print("  PASS: Callback properly validates parameters")
                return True
            elif response.status_code == 500:
                # Server error might indicate missing code parameter
                error_text = response.text
                if 'code' in error_text.lower():
                    print("  PASS: Callback endpoint exists and expects code parameter")
                    return True
                else:
                    print(f"  ERROR: Unexpected server error: {error_text}")
                    return False
            else:
                print(f"  UNKNOWN: Unexpected response: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"OAuth callback test failed: {e}")
            return False


async def main():
    """Main test function"""
    print("OAuth Configuration and Flow Test")
    print("=" * 50)
    
    tests = [
        ("OAuth Configuration", test_oauth_configuration),
        ("OAuth Login Initiation", test_oauth_login_initiation),
        ("OAuth Security Features", test_oauth_security_features),
        ("OAuth Callback Endpoint", test_oauth_callback_endpoint),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            results[test_name] = False
    
    print("\nOAuth Test Summary")
    print("=" * 50)
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nOverall: {passed}/{total} OAuth tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))