#!/usr/bin/env python3
"""Test staging authentication flow to identify JWT secret mismatches"""

import requests
import json
import sys
from urllib.parse import urlencode, parse_qs, urlparse

# Staging URLs
STAGING_URLS = {
    'api': 'https://api.staging.netrasystems.ai',
    'auth': 'https://auth.staging.netrasystems.ai',
    'app': 'https://app.staging.netrasystems.ai'
}

def test_service_health():
    """Test that all services are responding"""
    print("🏥 Testing service health...")
    
    for service, url in STAGING_URLS.items():
        try:
            response = requests.get(f"{url}/health", timeout=10)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"  {service}: {status} ({response.status_code})")
        except Exception as e:
            print(f"  {service}: ❌ ({e})")

def test_auth_service_endpoints():
    """Test auth service specific endpoints"""
    print("\n🔐 Testing auth service endpoints...")
    
    auth_endpoints = [
        '/health',
        '/auth/config',
        '/auth/providers'
    ]
    
    for endpoint in auth_endpoints:
        try:
            response = requests.get(f"{STAGING_URLS['auth']}{endpoint}", timeout=10)
            status = "✅" if response.status_code in [200, 404] else "❌"
            print(f"  {endpoint}: {status} ({response.status_code})")
            
            # If it's a config endpoint, check the response
            if endpoint == '/auth/config' and response.status_code == 200:
                try:
                    config = response.json()
                    print(f"    Config keys: {list(config.keys())}")
                except:
                    print(f"    Non-JSON response")
                    
        except Exception as e:
            print(f"  {endpoint}: ❌ ({e})")

def test_api_service_endpoints():
    """Test API service specific endpoints"""
    print("\n🌐 Testing API service endpoints...")
    
    api_endpoints = [
        '/health',
        '/docs',
        '/agents'  # This might require auth
    ]
    
    for endpoint in api_endpoints:
        try:
            response = requests.get(f"{STAGING_URLS['api']}{endpoint}", timeout=10)
            status = "✅" if response.status_code in [200, 401, 403] else "❌"
            print(f"  {endpoint}: {status} ({response.status_code})")
            
            # If unauthorized, that's expected for protected endpoints
            if response.status_code == 401:
                print(f"    Requires authentication (expected)")
                
        except Exception as e:
            print(f"  {endpoint}: ❌ ({e})")

def test_cors_configuration():
    """Test CORS configuration between services"""
    print("\n🌍 Testing CORS configuration...")
    
    # Test if auth service allows requests from app domain
    try:
        response = requests.options(
            f"{STAGING_URLS['auth']}/health",
            headers={
                'Origin': STAGING_URLS['app'],
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type,Authorization'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            cors_headers = response.headers
            print(f"  ✅ CORS preflight successful")
            print(f"    Access-Control-Allow-Origin: {cors_headers.get('Access-Control-Allow-Origin', 'Not set')}")
            print(f"    Access-Control-Allow-Methods: {cors_headers.get('Access-Control-Allow-Methods', 'Not set')}")
        else:
            print(f"  ❌ CORS preflight failed ({response.status_code})")
            
    except Exception as e:
        print(f"  ❌ CORS test failed: {e}")

def test_oauth_configuration():
    """Test OAuth configuration"""
    print("\n🔑 Testing OAuth configuration...")
    
    try:
        # Check if we can get OAuth providers
        response = requests.get(f"{STAGING_URLS['auth']}/auth/providers", timeout=10)
        
        if response.status_code == 200:
            providers = response.json()
            print(f"  ✅ OAuth providers available: {list(providers.keys()) if isinstance(providers, dict) else 'Unknown format'}")
        else:
            print(f"  ❌ Cannot get OAuth providers ({response.status_code})")
            
        # Try to initiate OAuth flow (without completing it)
        oauth_url = f"{STAGING_URLS['auth']}/auth/login/google"
        response = requests.get(oauth_url, allow_redirects=False, timeout=10)
        
        if response.status_code in [302, 307]:
            redirect_url = response.headers.get('Location', '')
            if 'accounts.google.com' in redirect_url:
                print(f"  ✅ Google OAuth redirect working")
            else:
                print(f"  ❌ Unexpected OAuth redirect: {redirect_url}")
        else:
            print(f"  ❌ OAuth initiation failed ({response.status_code})")
            
    except Exception as e:
        print(f"  ❌ OAuth test failed: {e}")

def test_inter_service_communication():
    """Test communication between services that might involve JWT validation"""
    print("\n🔗 Testing inter-service communication...")
    
    # This is tricky without actual authentication, but we can look for clues
    # in error messages or response patterns
    
    try:
        # Try to access an endpoint that requires backend-to-auth communication
        response = requests.post(
            f"{STAGING_URLS['api']}/agents/test",
            json={"message": "test"},
            timeout=10
        )
        
        print(f"  API agent endpoint: {response.status_code}")
        
        if response.status_code == 401:
            print(f"    ✅ Properly requires authentication")
        elif response.status_code == 500:
            print(f"    ❌ Server error - possible JWT mismatch")
            try:
                error_data = response.json()
                print(f"    Error details: {error_data}")
            except:
                print(f"    Error response not JSON")
        
    except Exception as e:
        print(f"  ❌ Inter-service test failed: {e}")

def main():
    print("🧪 Staging Authentication Flow Test")
    print("=" * 50)
    print(f"Testing against staging environment:")
    for service, url in STAGING_URLS.items():
        print(f"  {service}: {url}")
    print()
    
    test_service_health()
    test_auth_service_endpoints()
    test_api_service_endpoints()
    test_cors_configuration()
    test_oauth_configuration()
    test_inter_service_communication()
    
    print(f"\n🎯 Summary:")
    print(f"If you see server errors (500) in protected endpoints,")
    print(f"it may indicate JWT secret mismatches between services.")
    print(f"Check the deployment logs for JWT validation errors.")

if __name__ == "__main__":
    main()