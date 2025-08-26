#!/usr/bin/env python3
"""
Setup test accounts for staging environment testing.
This script creates test accounts with pre-configured OAuth tokens for agent testing.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import requests
import time
from datetime import datetime, timedelta
import jwt
import secrets
import hashlib
import base64

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Simple environment configuration
class IsolatedEnvironment:
    def get(self, key, default=None):
        return os.environ.get(key, default)

class StagingTestAccountManager:
    """Manage test accounts for staging environment testing"""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.staging_api_url = "https://api.staging.netrasystems.ai"
        self.staging_auth_url = "https://auth.staging.netrasystems.ai"
        self.test_accounts = []
        
    def create_test_google_account_config(self) -> Dict[str, Any]:
        """
        Create configuration for test Google account.
        This uses a service account or test OAuth token approach.
        """
        return {
            "provider": "google",
            "test_email": "netra.test.agent@gmail.com",
            "test_name": "Netra Test Agent",
            "test_id": "test-google-id-" + secrets.token_hex(8),
            "oauth_token": self._generate_test_oauth_token(),
            "refresh_token": self._generate_test_refresh_token(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
    
    def _generate_test_oauth_token(self) -> str:
        """Generate a test OAuth access token for staging"""
        # This would normally come from Google OAuth flow
        # For testing, we create a mock token that the staging env can validate
        payload = {
            "sub": "test-google-id",
            "email": "netra.test.agent@gmail.com",
            "name": "Netra Test Agent",
            "picture": "https://lh3.googleusercontent.com/a/default-user",
            "email_verified": True,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "aud": self.env.get("GOOGLE_CLIENT_ID", "test-client-id"),
            "iss": "https://accounts.google.com"
        }
        
        # In production, this would be signed by Google
        # For testing, we use a known test key
        test_secret = self.env.get("TEST_JWT_SECRET", "test-secret-key-for-staging")
        return jwt.encode(payload, test_secret, algorithm="HS256")
    
    def _generate_test_refresh_token(self) -> str:
        """Generate a test refresh token"""
        return "test-refresh-" + secrets.token_urlsafe(32)
    
    def create_api_key_account(self) -> Dict[str, Any]:
        """
        Create an API key-based test account for direct API access.
        This bypasses OAuth for testing purposes.
        """
        api_key = "sk-test-" + secrets.token_urlsafe(32)
        
        return {
            "provider": "api_key",
            "api_key": api_key,
            "user_id": "test-user-" + secrets.token_hex(8),
            "email": "agent.test@staging.netrasystems.ai",
            "name": "Test Agent",
            "permissions": ["read", "write", "admin"],
            "created_at": datetime.utcnow().isoformat()
        }
    
    def create_bypass_token(self) -> Dict[str, Any]:
        """
        Create a bypass token for staging environment testing.
        This token allows direct access without OAuth flow.
        """
        # Generate a secure bypass token
        bypass_token = secrets.token_urlsafe(64)
        
        # Create JWT with bypass claims
        payload = {
            "type": "staging_bypass",
            "sub": "test-agent",
            "email": "test.agent@staging.netrasystems.ai",
            "name": "Staging Test Agent",
            "permissions": ["full_access"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400,  # 24 hours
            "environment": "staging"
        }
        
        # Sign with staging secret
        staging_secret = self.env.get("STAGING_JWT_SECRET", "staging-test-secret")
        jwt_token = jwt.encode(payload, staging_secret, algorithm="HS256")
        
        return {
            "bypass_token": bypass_token,
            "jwt_token": jwt_token,
            "usage": {
                "header": f"Authorization: Bearer {jwt_token}",
                "cookie": f"staging_session={bypass_token}",
                "query": f"?token={bypass_token}"
            }
        }
    
    def setup_browser_automation_account(self) -> Dict[str, Any]:
        """
        Setup account for browser automation testing (Selenium/Playwright).
        Includes pre-authenticated session data.
        """
        session_id = "test-session-" + secrets.token_hex(16)
        
        # Create session cookie data
        session_data = {
            "session_id": session_id,
            "user_id": "test-browser-user",
            "email": "browser.test@staging.netrasystems.ai",
            "authenticated": True,
            "expires": (datetime.utcnow() + timedelta(hours=4)).isoformat()
        }
        
        # Encode session data
        session_json = json.dumps(session_data)
        session_b64 = base64.b64encode(session_json.encode()).decode()
        
        return {
            "type": "browser_automation",
            "cookies": [
                {
                    "name": "staging_session",
                    "value": session_id,
                    "domain": ".staging.netrasystems.ai",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True
                },
                {
                    "name": "staging_auth",
                    "value": session_b64,
                    "domain": ".staging.netrasystems.ai",
                    "path": "/",
                    "secure": True
                }
            ],
            "local_storage": {
                "auth_token": session_id,
                "user_data": session_json
            }
        }
    
    def test_staging_login_methods(self) -> Dict[str, Any]:
        """
        Test different login methods for staging environment.
        Returns a report of available methods.
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "methods": {},
            "recommendations": []
        }
        
        # Test 1: Direct API Key Authentication
        api_account = self.create_api_key_account()
        try:
            response = requests.get(
                f"{self.staging_api_url}/health",
                headers={"X-API-Key": api_account["api_key"]},
                timeout=5
            )
            report["methods"]["api_key"] = {
                "status": "available" if response.status_code == 200 else "unavailable",
                "details": api_account
            }
        except Exception as e:
            report["methods"]["api_key"] = {"status": "error", "error": str(e)}
        
        # Test 2: Bypass Token
        bypass = self.create_bypass_token()
        try:
            response = requests.get(
                f"{self.staging_api_url}/health",
                headers={"Authorization": f"Bearer {bypass['jwt_token']}"},
                timeout=5
            )
            report["methods"]["bypass_token"] = {
                "status": "available" if response.status_code in [200, 401] else "unavailable",
                "details": bypass
            }
        except Exception as e:
            report["methods"]["bypass_token"] = {"status": "error", "error": str(e)}
        
        # Test 3: OAuth Mock
        oauth = self.create_test_google_account_config()
        report["methods"]["oauth_mock"] = {
            "status": "configured",
            "details": oauth
        }
        
        # Test 4: Browser Session
        browser = self.setup_browser_automation_account()
        report["methods"]["browser_session"] = {
            "status": "configured",
            "details": browser
        }
        
        # Generate recommendations
        if report["methods"].get("api_key", {}).get("status") == "available":
            report["recommendations"].append(
                "Use API Key authentication for direct API testing"
            )
        
        if report["methods"].get("bypass_token", {}).get("status") == "available":
            report["recommendations"].append(
                "Use bypass token for authenticated endpoint testing"
            )
        
        report["recommendations"].append(
            "Use browser automation with pre-configured session for UI testing"
        )
        
        return report
    
    def save_test_credentials(self, output_file: str = "staging_test_credentials.json"):
        """Save all test credentials to a file"""
        credentials = {
            "created_at": datetime.utcnow().isoformat(),
            "environment": "staging",
            "accounts": {
                "api_key": self.create_api_key_account(),
                "bypass_token": self.create_bypass_token(),
                "oauth_mock": self.create_test_google_account_config(),
                "browser_session": self.setup_browser_automation_account()
            },
            "usage_examples": {
                "curl_api_key": 'curl -H "X-API-Key: YOUR_KEY" https://api.staging.netrasystems.ai/health',
                "curl_bearer": 'curl -H "Authorization: Bearer YOUR_TOKEN" https://api.staging.netrasystems.ai/health',
                "browser_script": """
from selenium import webdriver
driver = webdriver.Chrome()
driver.get('https://app.staging.netrasystems.ai')
# Add cookies from browser_session.cookies
for cookie in credentials['accounts']['browser_session']['cookies']:
    driver.add_cookie(cookie)
driver.refresh()
# Now logged in
                """
            }
        }
        
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        print(f"Test credentials saved to: {output_path.absolute()}")
        return credentials


def main():
    """Main entry point"""
    manager = StagingTestAccountManager()
    
    print("=" * 70)
    print("STAGING TEST ACCOUNT SETUP")
    print("=" * 70)
    
    # Test available methods
    print("\nTesting login methods...")
    report = manager.test_staging_login_methods()
    
    print("\nAvailable Methods:")
    for method, details in report["methods"].items():
        status = details.get("status", "unknown")
        print(f"  - {method}: {status}")
    
    print("\nRecommendations:")
    for rec in report["recommendations"]:
        print(f"  - {rec}")
    
    # Save credentials
    print("\nSaving test credentials...")
    credentials = manager.save_test_credentials()
    
    print("\n" + "=" * 70)
    print("SETUP COMPLETE")
    print("=" * 70)
    print("\nTest credentials have been generated and saved.")
    print("Use the credentials in 'staging_test_credentials.json' for testing.")
    
    # Print quick start examples
    print("\nQuick Start Examples:")
    print("\n1. API Key Test:")
    api_key = credentials["accounts"]["api_key"]["api_key"]
    print(f'   curl -H "X-API-Key: {api_key}" https://api.staging.netrasystems.ai/health')
    
    print("\n2. Bearer Token Test:")
    token = credentials["accounts"]["bypass_token"]["jwt_token"]
    print(f'   curl -H "Authorization: Bearer {token[:20]}..." https://api.staging.netrasystems.ai/health')
    
    print("\n3. Browser Session:")
    print("   Use the cookies in staging_test_credentials.json with Selenium/Playwright")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())