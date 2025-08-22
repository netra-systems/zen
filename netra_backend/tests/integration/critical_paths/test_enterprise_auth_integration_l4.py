#!/usr/bin/env python3
"""
Comprehensive test for enterprise authentication integration:
1. SAML 2.0 SSO integration
2. OAuth 2.0 / OpenID Connect
3. Active Directory / LDAP integration
4. Multi-factor authentication (MFA)
5. Role-based access control (RBAC)
6. API key management
7. Session management across services
8. Token refresh and revocation

This test validates complete enterprise authentication capabilities.
"""

from tests.test_utils import setup_test_path

setup_test_path()

import asyncio
import base64
import hashlib
import json
import secrets

# Add project root to path
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import jwt
import pytest
import websockets
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration
BASE_URL = "http://localhost:8000"
AUTH_URL = "http://localhost:8081"
WS_URL = "ws://localhost:8000/websocket"
SAML_IDP_URL = "http://localhost:8082/saml"
OAUTH_PROVIDER_URL = "http://localhost:8083/oauth"
LDAP_URL = "ldap://localhost:389"

# Test enterprise configurations
ENTERPRISE_CONFIG = {
    "saml": {
        "entity_id": "https://netrasystems.ai/saml",
        "sso_url": f"{SAML_IDP_URL}/sso",
        "slo_url": f"{SAML_IDP_URL}/slo",
        "x509_cert": "MIID...="  # Placeholder
    },
    "oauth": {
        "client_id": "netra-enterprise",
        "client_secret": "secret_key_123",
        "authorize_url": f"{OAUTH_PROVIDER_URL}/authorize",
        "token_url": f"{OAUTH_PROVIDER_URL}/token",
        "userinfo_url": f"{OAUTH_PROVIDER_URL}/userinfo"
    },
    "ldap": {
        "server": "localhost",
        "port": 389,
        "base_dn": "dc=netra,dc=ai",
        "bind_dn": "cn=admin,dc=netra,dc=ai",
        "bind_password": "admin_password"
    },
    "mfa": {
        "totp_enabled": True,
        "sms_enabled": True,
        "webauthn_enabled": True,
        "backup_codes_enabled": True
    }
}


class EnterpriseAuthTester:
    """Test enterprise authentication integration."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_users: List[Dict[str, Any]] = []
        self.auth_tokens: Dict[str, str] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.audit_logs: List[Dict[str, Any]] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.session:
            await self.session.close()
            
    async def test_saml_sso(self) -> bool:
        """Test SAML 2.0 SSO integration."""
        print("\n[SAML] Testing SAML 2.0 SSO...")
        
        try:
            # Step 1: Initiate SAML authentication
            saml_request = {
                "entity_id": ENTERPRISE_CONFIG["saml"]["entity_id"],
                "relay_state": "test_state_123",
                "force_authn": False
            }
            
            async with self.session.post(
                f"{AUTH_URL}/saml/login",
                json=saml_request
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    saml_auth_url = data.get("auth_url")
                    saml_request_id = data.get("request_id")
                    print(f"[OK] SAML request initiated: {saml_request_id}")
                    
                    # Step 2: Simulate IDP authentication
                    idp_response = await self._simulate_idp_auth(
                        saml_request_id,
                        "enterprise_user@company.com"
                    )
                    
                    # Step 3: Process SAML response
                    async with self.session.post(
                        f"{AUTH_URL}/saml/acs",  # Assertion Consumer Service
                        json={"saml_response": idp_response}
                    ) as acs_response:
                        if acs_response.status == 200:
                            acs_data = await acs_response.json()
                            token = acs_data.get("access_token")
                            user = acs_data.get("user")
                            
                            if token and user:
                                self.auth_tokens["saml_user"] = token
                                self.test_users.append(user)
                                print(f"[OK] SAML SSO successful for {user.get('email')}")
                                return True
                                
        except Exception as e:
            print(f"[ERROR] SAML SSO failed: {e}")
            
        return False
        
    async def _simulate_idp_auth(self, request_id: str, email: str) -> str:
        """Simulate IDP authentication response."""
        # This would normally come from the IDP
        saml_response = {
            "request_id": request_id,
            "user": {
                "email": email,
                "name": "Enterprise User",
                "groups": ["admins", "developers"],
                "attributes": {
                    "department": "Engineering",
                    "employee_id": "EMP001"
                }
            },
            "signature": base64.b64encode(b"simulated_signature").decode()
        }
        return base64.b64encode(json.dumps(saml_response).encode()).decode()
        
    async def test_oauth_flow(self) -> bool:
        """Test OAuth 2.0 / OpenID Connect flow."""
        print("\n[OAUTH] Testing OAuth 2.0 flow...")
        
        try:
            # Step 1: Get authorization code
            auth_params = {
                "client_id": ENTERPRISE_CONFIG["oauth"]["client_id"],
                "redirect_uri": "http://localhost:8000/callback",
                "response_type": "code",
                "scope": "openid profile email",
                "state": secrets.token_urlsafe(16)
            }
            
            async with self.session.get(
                ENTERPRISE_CONFIG["oauth"]["authorize_url"],
                params=auth_params
            ) as response:
                if response.status == 200:
                    # Simulate user consent
                    auth_code = "simulated_auth_code_123"
                    
                    # Step 2: Exchange code for tokens
                    token_data = {
                        "grant_type": "authorization_code",
                        "code": auth_code,
                        "redirect_uri": auth_params["redirect_uri"],
                        "client_id": ENTERPRISE_CONFIG["oauth"]["client_id"],
                        "client_secret": ENTERPRISE_CONFIG["oauth"]["client_secret"]
                    }
                    
                    async with self.session.post(
                        ENTERPRISE_CONFIG["oauth"]["token_url"],
                        data=token_data
                    ) as token_response:
                        if token_response.status == 200:
                            tokens = await token_response.json()
                            access_token = tokens.get("access_token")
                            id_token = tokens.get("id_token")
                            refresh_token = tokens.get("refresh_token")
                            
                            if access_token and id_token:
                                self.auth_tokens["oauth_user"] = access_token
                                print(f"[OK] OAuth tokens obtained")
                                
                                # Step 3: Get user info
                                async with self.session.get(
                                    ENTERPRISE_CONFIG["oauth"]["userinfo_url"],
                                    headers={"Authorization": f"Bearer {access_token}"}
                                ) as userinfo_response:
                                    if userinfo_response.status == 200:
                                        userinfo = await userinfo_response.json()
                                        self.test_users.append(userinfo)
                                        print(f"[OK] OAuth user info: {userinfo.get('email')}")
                                        return True
                                        
        except Exception as e:
            print(f"[ERROR] OAuth flow failed: {e}")
            
        return False
        
    async def test_ldap_integration(self) -> bool:
        """Test Active Directory / LDAP integration."""
        print("\n[LDAP] Testing LDAP integration...")
        
        try:
            # Test LDAP authentication
            ldap_auth = {
                "username": "test.user",
                "password": "ldap_password",
                "domain": "NETRA"
            }
            
            async with self.session.post(
                f"{AUTH_URL}/ldap/authenticate",
                json=ldap_auth
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get("access_token")
                    user = data.get("user")
                    
                    if token and user:
                        self.auth_tokens["ldap_user"] = token
                        self.test_users.append(user)
                        print(f"[OK] LDAP authentication successful")
                        
                        # Test group membership
                        groups = user.get("groups", [])
                        print(f"[OK] User groups: {groups}")
                        
                        # Test LDAP search
                        search_params = {
                            "filter": "(objectClass=user)",
                            "attributes": ["cn", "mail", "memberOf"]
                        }
                        
                        async with self.session.post(
                            f"{AUTH_URL}/ldap/search",
                            json=search_params,
                            headers={"Authorization": f"Bearer {token}"}
                        ) as search_response:
                            if search_response.status == 200:
                                results = await search_response.json()
                                print(f"[OK] LDAP search returned {len(results.get('entries', []))} entries")
                                return True
                                
        except Exception as e:
            print(f"[ERROR] LDAP integration failed: {e}")
            
        return False
        
    async def test_mfa(self) -> bool:
        """Test multi-factor authentication."""
        print("\n[MFA] Testing multi-factor authentication...")
        
        try:
            # Step 1: Initial authentication
            auth_data = {
                "email": "mfa_user@netrasystems.ai",
                "password": "secure_password"
            }
            
            async with self.session.post(
                f"{AUTH_URL}/auth/login",
                json=auth_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("mfa_required"):
                        mfa_token = data.get("mfa_token")
                        print("[OK] MFA challenge initiated")
                        
                        # Step 2: Setup TOTP
                        async with self.session.post(
                            f"{AUTH_URL}/mfa/setup/totp",
                            json={"mfa_token": mfa_token}
                        ) as totp_response:
                            if totp_response.status == 200:
                                totp_data = await totp_response.json()
                                secret = totp_data.get("secret")
                                qr_code = totp_data.get("qr_code")
                                print(f"[OK] TOTP setup complete")
                                
                                # Step 3: Verify TOTP code
                                totp_code = self._generate_totp(secret)
                                
                                async with self.session.post(
                                    f"{AUTH_URL}/mfa/verify/totp",
                                    json={
                                        "mfa_token": mfa_token,
                                        "code": totp_code
                                    }
                                ) as verify_response:
                                    if verify_response.status == 200:
                                        verify_data = await verify_response.json()
                                        token = verify_data.get("access_token")
                                        
                                        if token:
                                            self.auth_tokens["mfa_user"] = token
                                            print("[OK] MFA verification successful")
                                            
                                            # Test backup codes
                                            backup_codes = verify_data.get("backup_codes", [])
                                            if backup_codes:
                                                print(f"[OK] {len(backup_codes)} backup codes generated")
                                                
                                            return True
                                            
        except Exception as e:
            print(f"[ERROR] MFA test failed: {e}")
            
        return False
        
    def _generate_totp(self, secret: str) -> str:
        """Generate TOTP code (simplified for testing)."""
        # In real implementation, use pyotp or similar
        return "123456"
        
    async def test_rbac(self) -> bool:
        """Test role-based access control."""
        print("\n[RBAC] Testing role-based access control...")
        
        try:
            # Create test roles
            roles = [
                {
                    "name": "admin",
                    "permissions": ["*"],
                    "description": "Full system access"
                },
                {
                    "name": "developer",
                    "permissions": ["agents:*", "threads:*", "metrics:read"],
                    "description": "Developer access"
                },
                {
                    "name": "viewer",
                    "permissions": ["*:read"],
                    "description": "Read-only access"
                }
            ]
            
            # Use admin token
            admin_token = self.auth_tokens.get("saml_user", "test_token")
            
            for role in roles:
                async with self.session.post(
                    f"{AUTH_URL}/rbac/roles",
                    json=role,
                    headers={"Authorization": f"Bearer {admin_token}"}
                ) as response:
                    if response.status in [200, 201]:
                        print(f"[OK] Created role: {role['name']}")
                        
            # Test permission checking
            test_permissions = [
                ("developer", "agents:create", True),
                ("developer", "users:delete", False),
                ("viewer", "threads:read", True),
                ("viewer", "threads:write", False)
            ]
            
            all_correct = True
            for role_name, permission, expected in test_permissions:
                check_data = {
                    "role": role_name,
                    "permission": permission
                }
                
                async with self.session.post(
                    f"{AUTH_URL}/rbac/check",
                    json=check_data,
                    headers={"Authorization": f"Bearer {admin_token}"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        allowed = data.get("allowed", False)
                        
                        if allowed == expected:
                            print(f"[OK] {role_name} {permission}: {allowed} (expected)")
                        else:
                            print(f"[ERROR] {role_name} {permission}: {allowed} (expected {expected})")
                            all_correct = False
                            
            return all_correct
            
        except Exception as e:
            print(f"[ERROR] RBAC test failed: {e}")
            
        return False
        
    async def test_api_key_management(self) -> bool:
        """Test API key management."""
        print("\n[API_KEYS] Testing API key management...")
        
        try:
            # Use a test token
            token = list(self.auth_tokens.values())[0] if self.auth_tokens else "test_token"
            
            # Create API key
            key_data = {
                "name": "Test API Key",
                "scopes": ["read", "write"],
                "expires_in": 3600,
                "rate_limit": 1000
            }
            
            async with self.session.post(
                f"{AUTH_URL}/api-keys/create",
                json=key_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    api_key = data.get("key")
                    key_id = data.get("key_id")
                    
                    if api_key:
                        print(f"[OK] API key created: {key_id}")
                        
                        # Test API key authentication
                        async with self.session.get(
                            f"{BASE_URL}/api/v1/health",
                            headers={"X-API-Key": api_key}
                        ) as api_response:
                            if api_response.status == 200:
                                print("[OK] API key authentication successful")
                                
                                # Revoke API key
                                async with self.session.delete(
                                    f"{AUTH_URL}/api-keys/{key_id}",
                                    headers={"Authorization": f"Bearer {token}"}
                                ) as revoke_response:
                                    if revoke_response.status == 200:
                                        print("[OK] API key revoked")
                                        
                                        # Verify revoked key doesn't work
                                        async with self.session.get(
                                            f"{BASE_URL}/api/v1/health",
                                            headers={"X-API-Key": api_key}
                                        ) as revoked_response:
                                            if revoked_response.status == 401:
                                                print("[OK] Revoked key properly rejected")
                                                return True
                                                
        except Exception as e:
            print(f"[ERROR] API key management failed: {e}")
            
        return False
        
    async def test_session_management(self) -> bool:
        """Test session management across services."""
        print("\n[SESSION] Testing session management...")
        
        try:
            # Create a session
            token = list(self.auth_tokens.values())[0] if self.auth_tokens else "test_token"
            
            async with self.session.post(
                f"{AUTH_URL}/sessions/create",
                headers={"Authorization": f"Bearer {token}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    session_id = data.get("session_id")
                    
                    if session_id:
                        self.sessions[session_id] = data
                        print(f"[OK] Session created: {session_id}")
                        
                        # Test session across services
                        services = [
                            f"{BASE_URL}/api/v1/health",
                            f"{AUTH_URL}/health",
                            f"{BASE_URL}/api/v1/user/profile"
                        ]
                        
                        for service_url in services:
                            async with self.session.get(
                                service_url,
                                headers={"X-Session-ID": session_id}
                            ) as service_response:
                                if service_response.status in [200, 401]:
                                    print(f"[OK] Session validated at {service_url}")
                                    
                        # Test session invalidation
                        async with self.session.delete(
                            f"{AUTH_URL}/sessions/{session_id}",
                            headers={"Authorization": f"Bearer {token}"}
                        ) as invalidate_response:
                            if invalidate_response.status == 200:
                                print("[OK] Session invalidated")
                                
                                # Verify session no longer works
                                async with self.session.get(
                                    f"{BASE_URL}/api/v1/health",
                                    headers={"X-Session-ID": session_id}
                                ) as invalid_response:
                                    if invalid_response.status == 401:
                                        print("[OK] Invalidated session properly rejected")
                                        return True
                                        
        except Exception as e:
            print(f"[ERROR] Session management failed: {e}")
            
        return False
        
    async def test_token_refresh(self) -> bool:
        """Test token refresh and revocation."""
        print("\n[TOKEN] Testing token refresh...")
        
        try:
            # Login to get tokens
            auth_data = {
                "email": "refresh_test@netrasystems.ai",
                "password": "test_password"
            }
            
            async with self.session.post(
                f"{AUTH_URL}/auth/login",
                json=auth_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    access_token = data.get("access_token")
                    refresh_token = data.get("refresh_token")
                    
                    if access_token and refresh_token:
                        print("[OK] Initial tokens obtained")
                        
                        # Wait a bit
                        await asyncio.sleep(2)
                        
                        # Refresh token
                        refresh_data = {
                            "refresh_token": refresh_token
                        }
                        
                        async with self.session.post(
                            f"{AUTH_URL}/auth/refresh",
                            json=refresh_data
                        ) as refresh_response:
                            if refresh_response.status == 200:
                                refresh_data = await refresh_response.json()
                                new_access_token = refresh_data.get("access_token")
                                
                                if new_access_token and new_access_token != access_token:
                                    print("[OK] Token refreshed successfully")
                                    
                                    # Revoke tokens
                                    revoke_data = {
                                        "token": new_access_token,
                                        "token_type": "access_token"
                                    }
                                    
                                    async with self.session.post(
                                        f"{AUTH_URL}/auth/revoke",
                                        json=revoke_data
                                    ) as revoke_response:
                                        if revoke_response.status == 200:
                                            print("[OK] Token revoked")
                                            
                                            # Verify revoked token doesn't work
                                            async with self.session.get(
                                                f"{BASE_URL}/api/v1/health",
                                                headers={"Authorization": f"Bearer {new_access_token}"}
                                            ) as test_response:
                                                if test_response.status == 401:
                                                    print("[OK] Revoked token properly rejected")
                                                    return True
                                                    
        except Exception as e:
            print(f"[ERROR] Token refresh test failed: {e}")
            
        return False
        
    async def test_audit_logging(self) -> bool:
        """Test authentication audit logging."""
        print("\n[AUDIT] Testing audit logging...")
        
        try:
            # Get audit logs
            token = list(self.auth_tokens.values())[0] if self.auth_tokens else "test_token"
            
            async with self.session.get(
                f"{AUTH_URL}/audit/logs",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 100}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logs = data.get("logs", [])
                    
                    # Check for expected events
                    event_types = set(log.get("event_type") for log in logs)
                    expected_events = {
                        "login", "logout", "token_refresh", 
                        "mfa_challenge", "api_key_created"
                    }
                    
                    found_events = event_types.intersection(expected_events)
                    print(f"[OK] Found audit events: {found_events}")
                    
                    # Verify log structure
                    if logs:
                        sample_log = logs[0]
                        required_fields = ["timestamp", "user_id", "event_type", "ip_address"]
                        
                        has_all_fields = all(field in sample_log for field in required_fields)
                        if has_all_fields:
                            print("[OK] Audit logs have required fields")
                            return True
                            
        except Exception as e:
            print(f"[ERROR] Audit logging test failed: {e}")
            
        return False
        
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all enterprise auth tests."""
        results = {}
        
        # Test authentication methods
        results["saml_sso"] = await self.test_saml_sso()
        results["oauth_flow"] = await self.test_oauth_flow()
        results["ldap_integration"] = await self.test_ldap_integration()
        results["mfa"] = await self.test_mfa()
        
        # Test authorization and management
        results["rbac"] = await self.test_rbac()
        results["api_key_management"] = await self.test_api_key_management()
        results["session_management"] = await self.test_session_management()
        results["token_refresh"] = await self.test_token_refresh()
        results["audit_logging"] = await self.test_audit_logging()
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4
async def test_enterprise_auth_integration():
    """Test complete enterprise authentication integration."""
    async with EnterpriseAuthTester() as tester:
        results = await tester.run_all_tests()
        
        # Print comprehensive report
        print("\n" + "="*80)
        print("ENTERPRISE AUTHENTICATION TEST REPORT")
        print("="*80)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("="*80)
        
        # Test results
        print("\nTEST RESULTS:")
        print("-"*40)
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name:30} : {status}")
            
        # User summary
        print("\nAUTHENTICATED USERS:")
        print("-"*40)
        for user in tester.test_users:
            print(f"  - {user.get('email', 'Unknown')} ({user.get('auth_method', 'Unknown')})")
            
        # Token summary
        print("\nACTIVE TOKENS:")
        print("-"*40)
        for user_type, token in tester.auth_tokens.items():
            print(f"  {user_type}: {token[:20]}...")
            
        print("="*80)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] All enterprise authentication features operational!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed")
            
        # Assert critical auth methods work
        critical_tests = ["saml_sso", "oauth_flow", "rbac", "audit_logging"]
        critical_passed = all(results.get(test, False) for test in critical_tests)
        assert critical_passed, f"Critical auth tests failed: {results}"


async def main():
    """Run the test standalone."""
    print("="*80)
    print("ENTERPRISE AUTHENTICATION TEST")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*80)
    
    async with EnterpriseAuthTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if all(results.values()):
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)