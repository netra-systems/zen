#!/usr/bin/env python3
"""Test which JWT secret the staging environment is using"""

import requests
import jwt
import json
from datetime import datetime, timedelta
from shared.isolated_environment import IsolatedEnvironment

# Test JWT secrets
JWT_SECRETS = {
    'staging': '7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A',
    'root': 'rsWwwvq8X6mCSuNv-TMXHDCfb96Xc-Dbay9MZy6EDCU'
}

STAGING_API_URL = 'https://api.staging.netrasystems.ai'

def test_jwt_secret(secret_name, secret_value):
    """Test if a JWT secret works with the staging environment"""
    print(f"\n🔍 Testing {secret_name} JWT secret...")
    
    # Create a test token
    payload = {
        'sub': 'test-user',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow(),
        'iss': 'netra-test'
    }
    
    try:
        token = jwt.encode(payload, secret_value, algorithm='HS256')
        print(f"✅ Generated test JWT token: {token[:50]}...")
        
        # Try to make an authenticated request
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Test with a simple endpoint that might validate JWT
        response = requests.get(f'{STAGING_API_URL}/health', headers=headers, timeout=10)
        print(f"📡 Health endpoint response: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ {secret_name} secret may be correct (or endpoint doesn't validate JWT)")
        else:
            print(f"❌ {secret_name} secret test inconclusive: {response.status_code}")
            
        return response.status_code == 200
        
    except jwt.InvalidTokenError as e:
        print(f"❌ JWT encoding failed with {secret_name} secret: {e}")
        return False
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    print("🔐 Staging JWT Secret Verification")
    print("=" * 50)
    
    print(f"Testing against: {STAGING_API_URL}")
    
    results = {}
    for name, secret in JWT_SECRETS.items():
        results[name] = test_jwt_secret(name, secret)
    
    print("\n📊 Results Summary:")
    print("-" * 30)
    for name, success in results.items():
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{name}: {status}")
    
    # Also test without authentication to establish baseline
    print(f"\n🌐 Testing unauthenticated access...")
    try:
        response = requests.get(f'{STAGING_API_URL}/health', timeout=10)
        print(f"Unauthenticated health check: {response.status_code}")
    except Exception as e:
        print(f"Unauthenticated request failed: {e}")

if __name__ == "__main__":
    main()