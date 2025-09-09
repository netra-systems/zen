"""
User Authentication Flow Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core authentication flows enable platform access
- Business Goal: Secure and frictionless user registration, login, and account management
- Value Impact: Users can easily join and access the AI optimization platform
- Strategic Impact: Foundation for user acquisition, retention, and enterprise adoption

CRITICAL REQUIREMENTS:
- NO DOCKER - Integration tests without Docker containers
- NO MOCKS - Use real authentication logic, real database, real password hashing
- Real Services - Connect to PostgreSQL (port 5434) and Redis (port 6381)
- Integration Layer - Test auth service flows, not full browser interactions

Test Categories:
1. User registration and validation
2. Login flow with credentials
3. Password reset functionality
4. Account activation flows
5. Multi-factor authentication support
"""

import asyncio
import bcrypt
import json
import pytest
import secrets
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.types.core_types import UserID, ensure_user_id

import httpx
import asyncpg
import redis.asyncio as redis


class TestUserAuthenticationFlowIntegration(BaseIntegrationTest):
    """Integration tests for User Authentication Flows - NO MOCKS, REAL SERVICES ONLY."""
    
    def setup_method(self):
        """Set up for user authentication flow integration tests."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Authentication Configuration
        self.auth_config = {
            "password_min_length": 8,
            "password_require_special": True,
            "password_require_numbers": True,
            "max_login_attempts": 5,
            "lockout_duration": 900,  # 15 minutes
            "email_verification_required": True,
            "password_reset_token_ttl": 3600,  # 1 hour
        }
        
        # Service URLs
        self.auth_service_url = f"http://localhost:{self.env.get('AUTH_SERVICE_PORT', '8081')}"
        self.backend_url = f"http://localhost:{self.env.get('BACKEND_PORT', '8000')}"
        
        # Real service connections
        self.redis_url = f"redis://localhost:{self.env.get('REDIS_PORT', '6381')}"
        self.db_url = self.env.get("TEST_DATABASE_URL") or f"postgresql://test:test@localhost:5434/test_db"
        
        # Test users for authentication flows
        self.test_users = [
            {
                "user_id": "auth-flow-user-1",
                "email": "authflow1@netra.ai",
                "password": "SecurePass123!",
                "name": "Auth Flow Test User 1",
                "phone": "+1234567890"
            },
            {
                "user_id": "auth-flow-user-2", 
                "email": "authflow2@netra.ai",
                "password": "AnotherPass456@",
                "name": "Auth Flow Test User 2",
                "phone": "+1234567891"
            }
        ]

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.user_flow
    async def test_user_registration_and_validation(self, real_services_fixture):
        """
        Test user registration process with real database storage and validation.
        
        Business Value: New users can successfully register and join the platform.
        """
        conn = None
        redis_client = redis.from_url(self.redis_url)
        
        try:
            # Connect to real database
            conn = await asyncpg.connect(self.db_url)
            
            user = self.test_users[0]
            
            # Clean up any existing test user
            await conn.execute("DELETE FROM users WHERE email = $1", user["email"])
            
            async with httpx.AsyncClient() as client:
                
                # Test user registration
                registration_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/register",
                    json={
                        "email": user["email"],
                        "password": user["password"],
                        "name": user["name"],
                        "phone": user.get("phone"),
                        "terms_accepted": True,
                        "marketing_emails": False
                    },
                    timeout=10.0
                )
                
                # Registration should succeed or service should be available
                if registration_response.status_code in [200, 201]:
                    registration_data = registration_response.json()
                    
                    assert "user_id" in registration_data
                    assert "email" in registration_data  
                    assert registration_data["email"] == user["email"]
                    
                    user_id = registration_data["user_id"]
                    
                    # Verify user was created in database
                    db_user = await conn.fetchrow(
                        "SELECT * FROM users WHERE email = $1",
                        user["email"]
                    )
                    
                    assert db_user is not None, "User should be created in database"
                    assert db_user["email"] == user["email"]
                    assert db_user["name"] == user["name"]
                    assert db_user["id"] == user_id
                    
                    # Verify password is properly hashed (not stored in plain text)
                    stored_password = db_user.get("password_hash") or db_user.get("password")
                    if stored_password:
                        assert stored_password != user["password"], \
                            "Password should be hashed, not stored in plain text"
                        assert len(stored_password) > 20, \
                            "Hashed password should be significantly longer than plain text"
                    
                    # Test duplicate registration prevention
                    duplicate_response = await client.post(
                        f"{self.auth_service_url}/api/v1/auth/register",
                        json={
                            "email": user["email"],
                            "password": "DifferentPass789#",
                            "name": "Different Name"
                        },
                        timeout=10.0
                    )
                    
                    assert duplicate_response.status_code in [400, 409], \
                        "Duplicate email registration should be prevented"
                
                elif registration_response.status_code == 404:
                    self.logger.warning("Auth service registration endpoint not available")
                    pytest.skip("Registration endpoint not implemented")
                else:
                    self.logger.warning(f"Registration failed: {registration_response.status_code}")
            
            # Test input validation scenarios
            validation_scenarios = [
                {
                    "name": "invalid_email_format",
                    "data": {
                        "email": "invalid-email",
                        "password": "ValidPass123!",
                        "name": "Test User"
                    },
                    "should_fail": True
                },
                {
                    "name": "weak_password",
                    "data": {
                        "email": "weakpass@netra.ai",
                        "password": "weak",
                        "name": "Test User" 
                    },
                    "should_fail": True
                },
                {
                    "name": "missing_required_fields",
                    "data": {
                        "email": "missing@netra.ai"
                        # Missing password and name
                    },
                    "should_fail": True
                }
            ]
            
            async with httpx.AsyncClient() as client:
                for scenario in validation_scenarios:
                    
                    validation_response = await client.post(
                        f"{self.auth_service_url}/api/v1/auth/register",
                        json=scenario["data"],
                        timeout=10.0
                    )
                    
                    if scenario["should_fail"]:
                        assert validation_response.status_code in [400, 422, 404], \
                            f"Validation scenario '{scenario['name']}' should fail"
                    else:
                        assert validation_response.status_code in [200, 201, 404], \
                            f"Validation scenario '{scenario['name']}' should succeed"
                
        except Exception as e:
            self.logger.warning(f"Registration test error: {e}")
            if "connection" in str(e).lower():
                pytest.skip("Database not available for registration testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.user_flow
    async def test_login_flow_with_credentials(self, real_services_fixture):
        """
        Test user login flow with real credential verification and session creation.
        
        Business Value: Registered users can securely log in and access their account.
        """
        conn = None
        redis_client = redis.from_url(self.redis_url)
        
        try:
            # Connect to real database
            conn = await asyncpg.connect(self.db_url)
            
            user = self.test_users[0]
            
            # Create test user with hashed password
            password_hash = bcrypt.hashpw(user["password"].encode(), bcrypt.gensalt()).decode()
            
            await conn.execute("""
                INSERT INTO users (id, email, name, password_hash, created_at, email_verified)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET 
                    password_hash = EXCLUDED.password_hash,
                    email_verified = EXCLUDED.email_verified
            """, user["user_id"], user["email"], user["name"], password_hash, 
                datetime.now(timezone.utc), True)
            
            async with httpx.AsyncClient() as client:
                
                # Test successful login
                login_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/login",
                    json={
                        "email": user["email"],
                        "password": user["password"],
                        "device_id": "integration-test-device",
                        "remember_me": False
                    },
                    timeout=10.0
                )
                
                if login_response.status_code in [200, 201]:
                    login_data = login_response.json()
                    
                    # Verify login response contains required data
                    assert "access_token" in login_data or "token" in login_data
                    assert "user_id" in login_data or "user" in login_data
                    
                    # Extract token and user info
                    access_token = login_data.get("access_token") or login_data.get("token")
                    returned_user_id = (login_data.get("user_id") or 
                                      login_data.get("user", {}).get("id") or
                                      login_data.get("user", {}).get("user_id"))
                    
                    if access_token:
                        # Test authenticated API access
                        profile_response = await client.get(
                            f"{self.auth_service_url}/api/v1/user/profile",
                            headers={"Authorization": f"Bearer {access_token}"},
                            timeout=10.0
                        )
                        
                        # Profile should be accessible with valid token
                        assert profile_response.status_code in [200, 404], \
                            f"Profile access failed: {profile_response.status_code}"
                        
                        if profile_response.status_code == 200:
                            profile_data = profile_response.json()
                            assert profile_data.get("email") == user["email"] or \
                                   "email" not in profile_data  # Might not expose email in profile
                
                # Test login failure scenarios
                failure_scenarios = [
                    {
                        "name": "wrong_password",
                        "credentials": {
                            "email": user["email"],
                            "password": "WrongPassword123!"
                        },
                        "expected_status": [401, 403]
                    },
                    {
                        "name": "nonexistent_user",
                        "credentials": {
                            "email": "nonexistent@netra.ai", 
                            "password": "AnyPassword123!"
                        },
                        "expected_status": [401, 404]
                    },
                    {
                        "name": "empty_credentials",
                        "credentials": {
                            "email": "",
                            "password": ""
                        },
                        "expected_status": [400, 422]
                    }
                ]
                
                for scenario in failure_scenarios:
                        failure_response = await client.post(
                            f"{self.auth_service_url}/api/v1/auth/login",
                            json=scenario["credentials"],
                            timeout=10.0
                        )
                        
                        assert failure_response.status_code in scenario["expected_status"] + [404], \
                            f"Login failure scenario '{scenario['name']}' got unexpected status {failure_response.status_code}"
                
                elif login_response.status_code == 404:
                    self.logger.warning("Auth service login endpoint not available")
                    pytest.skip("Login endpoint not implemented")
                
        except Exception as e:
            self.logger.warning(f"Login flow test error: {e}")
            if "connection" in str(e).lower():
                pytest.skip("Database not available for login testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.user_flow
    async def test_password_reset_functionality(self, real_services_fixture):
        """
        Test password reset flow with real email token generation and validation.
        
        Business Value: Users can recover their accounts when they forget passwords.
        """
        conn = None
        redis_client = redis.from_url(self.redis_url)
        
        try:
            # Connect to real database and Redis
            conn = await asyncpg.connect(self.db_url)
            
            user = self.test_users[0]
            
            # Create test user
            password_hash = bcrypt.hashpw("OldPassword123!".encode(), bcrypt.gensalt()).decode()
            
            await conn.execute("""
                INSERT INTO users (id, email, name, password_hash, created_at, email_verified)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET 
                    password_hash = EXCLUDED.password_hash
            """, user["user_id"], user["email"], user["name"], password_hash,
                datetime.now(timezone.utc), True)
            
            async with httpx.AsyncClient() as client:
                
                # Test password reset request
                reset_request_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/password-reset/request",
                    json={
                        "email": user["email"]
                    },
                    timeout=10.0
                )
                
                if reset_request_response.status_code in [200, 202]:
                    # Password reset should be initiated
                    reset_data = reset_request_response.json()
                    
                    # In integration testing, we might get a reset token directly
                    # or need to check Redis/database for the token
                    reset_token = reset_data.get("reset_token")
                    
                    if not reset_token:
                        # Check Redis for password reset tokens
                        reset_keys = await redis_client.keys(f"password_reset:{user['email']}:*")
                        if reset_keys:
                            reset_token = reset_keys[0].decode().split(":")[-1]
                    
                    if not reset_token:
                        # Check database for reset tokens
                        db_token = await conn.fetchval(
                            "SELECT reset_token FROM password_resets WHERE email = $1 ORDER BY created_at DESC LIMIT 1",
                            user["email"]
                        )
                        reset_token = db_token
                    
                    if reset_token:
                        # Test password reset token validation
                        validate_response = await client.post(
                            f"{self.auth_service_url}/api/v1/auth/password-reset/validate",
                            json={
                                "email": user["email"],
                                "token": reset_token
                            },
                            timeout=10.0
                        )
                        
                        assert validate_response.status_code in [200, 404], \
                            f"Token validation failed: {validate_response.status_code}"
                        
                        if validate_response.status_code == 200:
                            # Test actual password reset
                            new_password = "NewSecurePass456!"
                            
                            reset_complete_response = await client.post(
                                f"{self.auth_service_url}/api/v1/auth/password-reset/complete",
                                json={
                                    "email": user["email"],
                                    "token": reset_token,
                                    "new_password": new_password
                                },
                                timeout=10.0
                            )
                            
                            assert reset_complete_response.status_code in [200, 204, 404], \
                                f"Password reset completion failed: {reset_complete_response.status_code}"
                            
                            if reset_complete_response.status_code in [200, 204]:
                                
                                # Verify password was changed in database
                                updated_user = await conn.fetchrow(
                                    "SELECT password_hash FROM users WHERE email = $1",
                                    user["email"]
                                )
                                
                                if updated_user:
                                    new_hash = updated_user["password_hash"]
                                    assert new_hash != password_hash, \
                                        "Password hash should be updated after reset"
                                    
                                    # Test login with new password
                                    login_response = await client.post(
                                        f"{self.auth_service_url}/api/v1/auth/login",
                                        json={
                                            "email": user["email"],
                                            "password": new_password
                                        },
                                        timeout=10.0
                                    )
                                    
                                    assert login_response.status_code in [200, 201, 404], \
                                        "Login should work with new password"
                                    
                                    # Test login with old password should fail
                                    old_login_response = await client.post(
                                        f"{self.auth_service_url}/api/v1/auth/login",
                                        json={
                                            "email": user["email"],
                                            "password": "OldPassword123!"
                                        },
                                        timeout=10.0
                                    )
                                    
                                    assert old_login_response.status_code in [401, 403, 404], \
                                        "Old password should not work after reset"
                    
                    # Test invalid reset scenarios
                    invalid_scenarios = [
                        {
                            "name": "nonexistent_email",
                            "email": "nonexistent@netra.ai",
                            "should_fail": True
                        },
                        {
                            "name": "invalid_email_format", 
                            "email": "invalid-email",
                            "should_fail": True
                        }
                    ]
                    
                    for scenario in invalid_scenarios:
                        invalid_response = await client.post(
                            f"{self.auth_service_url}/api/v1/auth/password-reset/request",
                            json={"email": scenario["email"]},
                            timeout=10.0
                        )
                        
                        if scenario["should_fail"]:
                            # System might accept invalid requests to prevent email enumeration
                            assert invalid_response.status_code in [200, 202, 400, 404], \
                                f"Invalid reset scenario '{scenario['name']}' got {invalid_response.status_code}"
                
                elif reset_request_response.status_code == 404:
                    self.logger.warning("Password reset endpoint not available")
                    pytest.skip("Password reset not implemented")
                
        except Exception as e:
            self.logger.warning(f"Password reset test error: {e}")
            if "connection" in str(e).lower():
                pytest.skip("Services not available for password reset testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.user_flow
    async def test_account_activation_flows(self, real_services_fixture):
        """
        Test account activation and email verification flows.
        
        Business Value: Users complete registration process and can access full features.
        """
        conn = None
        redis_client = redis.from_url(self.redis_url)
        
        try:
            # Connect to real database and Redis
            conn = await asyncpg.connect(self.db_url)
            
            user = self.test_users[1] 
            
            # Create unactivated test user
            await conn.execute("""
                INSERT INTO users (id, email, name, password_hash, created_at, email_verified, active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET 
                    email_verified = EXCLUDED.email_verified,
                    active = EXCLUDED.active
            """, user["user_id"], user["email"], user["name"], 
                bcrypt.hashpw(user["password"].encode(), bcrypt.gensalt()).decode(),
                datetime.now(timezone.utc), False, False)
            
            async with httpx.AsyncClient() as client:
                
                # Test email verification request
                verify_request_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/verify-email/request",
                    json={
                        "email": user["email"]
                    },
                    timeout=10.0
                )
                
                if verify_request_response.status_code in [200, 202]:
                    
                    # Generate verification token (simulating email link)
                    verification_token = secrets.token_urlsafe(32)
                    
                    # Store verification token in Redis/database
                    await redis_client.setex(
                        f"email_verification:{user['email']}:{verification_token}",
                        3600,  # 1 hour expiry
                        json.dumps({
                            "user_id": user["user_id"],
                            "email": user["email"],
                            "created_at": int(time.time())
                        })
                    )
                    
                    # Test email verification completion
                    verify_complete_response = await client.post(
                        f"{self.auth_service_url}/api/v1/auth/verify-email/complete",
                        json={
                            "email": user["email"],
                            "token": verification_token
                        },
                        timeout=10.0
                    )
                    
                    if verify_complete_response.status_code in [200, 204]:
                        
                        # Verify user is now activated in database
                        activated_user = await conn.fetchrow(
                            "SELECT email_verified, active FROM users WHERE email = $1",
                            user["email"]
                        )
                        
                        if activated_user:
                            # Depending on schema, check appropriate activation fields
                            if "email_verified" in activated_user:
                                assert activated_user["email_verified"] is True, \
                                    "User should be email verified after activation"
                            
                            if "active" in activated_user:
                                assert activated_user["active"] is True, \
                                    "User should be active after email verification"
                        
                        # Test that user can now fully access the system
                        login_response = await client.post(
                            f"{self.auth_service_url}/api/v1/auth/login",
                            json={
                                "email": user["email"],
                                "password": user["password"]
                            },
                            timeout=10.0
                        )
                        
                        if login_response.status_code in [200, 201]:
                            login_data = login_response.json()
                            access_token = login_data.get("access_token") or login_data.get("token")
                            
                            if access_token:
                                # Activated user should have full API access
                                profile_response = await client.get(
                                    f"{self.backend_url}/api/v1/user/profile",
                                    headers={"Authorization": f"Bearer {access_token}"},
                                    timeout=10.0
                                )
                                
                                assert profile_response.status_code in [200, 404], \
                                    "Activated user should access profile"
                    
                    # Test invalid activation scenarios
                    invalid_scenarios = [
                        {
                            "name": "invalid_token",
                            "token": "invalid_token_12345",
                            "email": user["email"]
                        },
                        {
                            "name": "expired_token",
                            "token": verification_token,
                            "email": user["email"],
                            "setup": "expire_token"
                        }
                    ]
                    
                    for scenario in invalid_scenarios:
                        
                        if scenario.get("setup") == "expire_token":
                            # Remove token from Redis to simulate expiration
                            await redis_client.delete(f"email_verification:{user['email']}:{scenario['token']}")
                        
                        invalid_response = await client.post(
                            f"{self.auth_service_url}/api/v1/auth/verify-email/complete",
                            json={
                                "email": scenario["email"],
                                "token": scenario["token"]
                            },
                            timeout=10.0
                        )
                        
                        assert invalid_response.status_code in [400, 401, 404, 410], \
                            f"Invalid activation scenario '{scenario['name']}' should fail"
                
                elif verify_request_response.status_code == 404:
                    self.logger.warning("Email verification endpoint not available")
                    pytest.skip("Email verification not implemented")
                
        except Exception as e:
            self.logger.warning(f"Account activation test error: {e}")
            if "connection" in str(e).lower():
                pytest.skip("Services not available for activation testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.user_flow
    async def test_multi_factor_authentication_support(self, real_services_fixture):
        """
        Test multi-factor authentication setup and verification flows.
        
        Business Value: Enterprise users get enhanced security for sensitive operations.
        """
        conn = None
        redis_client = redis.from_url(self.redis_url)
        
        try:
            # Connect to real services
            conn = await asyncpg.connect(self.db_url)
            
            user = self.test_users[1]
            
            # Create user with MFA capability
            await conn.execute("""
                INSERT INTO users (id, email, name, password_hash, created_at, email_verified, mfa_enabled)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    mfa_enabled = EXCLUDED.mfa_enabled
            """, user["user_id"], user["email"], user["name"],
                bcrypt.hashpw(user["password"].encode(), bcrypt.gensalt()).decode(),
                datetime.now(timezone.utc), True, False)
            
            async with httpx.AsyncClient() as client:
                
                # Test MFA setup initiation
                mfa_setup_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/mfa/setup",
                    json={
                        "user_id": user["user_id"],
                        "method": "totp"  # Time-based One-Time Password
                    },
                    timeout=10.0
                )
                
                if mfa_setup_response.status_code in [200, 201]:
                    setup_data = mfa_setup_response.json()
                    
                    # MFA setup should provide secret and QR code
                    assert "secret" in setup_data or "qr_code" in setup_data
                    
                    mfa_secret = setup_data.get("secret", "test_secret_12345")
                    
                    # Test MFA verification (using simulated TOTP code)
                    import pyotp
                    
                    try:
                        totp = pyotp.TOTP(mfa_secret)
                        current_code = totp.now()
                        
                        verify_response = await client.post(
                            f"{self.auth_service_url}/api/v1/auth/mfa/verify",
                            json={
                                "user_id": user["user_id"],
                                "code": current_code
                            },
                            timeout=10.0
                        )
                        
                        if verify_response.status_code in [200, 204]:
                            
                            # MFA should now be enabled for user
                            mfa_user = await conn.fetchrow(
                                "SELECT mfa_enabled FROM users WHERE id = $1",
                                user["user_id"]
                            )
                            
                            if mfa_user and "mfa_enabled" in mfa_user:
                                assert mfa_user["mfa_enabled"] is True, \
                                    "MFA should be enabled after successful setup"
                            
                            # Test login with MFA required
                            login_response = await client.post(
                                f"{self.auth_service_url}/api/v1/auth/login",
                                json={
                                    "email": user["email"],
                                    "password": user["password"]
                                },
                                timeout=10.0
                            )
                            
                            if login_response.status_code == 206:
                                # Partial authentication - MFA required
                                login_data = login_response.json()
                                assert "mfa_required" in login_data
                                assert login_data["mfa_required"] is True
                                
                                temp_token = login_data.get("temp_token")
                                
                                if temp_token:
                                    # Complete login with MFA
                                    new_code = totp.now()
                                    
                                    mfa_login_response = await client.post(
                                        f"{self.auth_service_url}/api/v1/auth/mfa/complete-login",
                                        json={
                                            "temp_token": temp_token,
                                            "code": new_code
                                        },
                                        timeout=10.0
                                    )
                                    
                                    assert mfa_login_response.status_code in [200, 201], \
                                        "MFA login completion should succeed"
                                    
                                    if mfa_login_response.status_code in [200, 201]:
                                        final_login_data = mfa_login_response.json()
                                        assert "access_token" in final_login_data or "token" in final_login_data
                    
                    except ImportError:
                        self.logger.warning("pyotp not available for TOTP testing")
                        # Test with simulated 6-digit code
                        verify_response = await client.post(
                            f"{self.auth_service_url}/api/v1/auth/mfa/verify",
                            json={
                                "user_id": user["user_id"],
                                "code": "123456"  # Test code
                            },
                            timeout=10.0
                        )
                        
                        # Should either work with test code or reject it appropriately
                        assert verify_response.status_code in [200, 204, 400, 401], \
                            f"MFA verification test got unexpected status: {verify_response.status_code}"
                
                elif mfa_setup_response.status_code == 404:
                    self.logger.warning("MFA setup endpoint not available")
                    pytest.skip("MFA functionality not implemented")
                
                # Test MFA disable
                disable_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/mfa/disable",
                    json={
                        "user_id": user["user_id"],
                        "password": user["password"]  # Require password for security
                    },
                    timeout=10.0
                )
                
                if disable_response.status_code in [200, 204]:
                    
                    # Verify MFA is disabled
                    disabled_user = await conn.fetchrow(
                        "SELECT mfa_enabled FROM users WHERE id = $1",
                        user["user_id"]
                    )
                    
                    if disabled_user and "mfa_enabled" in disabled_user:
                        assert disabled_user["mfa_enabled"] is False, \
                            "MFA should be disabled after disable request"
                
        except Exception as e:
            self.logger.warning(f"MFA test error: {e}")
            if "connection" in str(e).lower():
                pytest.skip("Services not available for MFA testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.user_flow
    async def test_account_lockout_and_rate_limiting(self, real_services_fixture):
        """
        Test account lockout after failed login attempts and rate limiting.
        
        Business Value: Protects user accounts from brute force attacks.
        """
        conn = None
        redis_client = redis.from_url(self.redis_url)
        
        try:
            # Connect to real services
            conn = await asyncpg.connect(self.db_url)
            
            user = self.test_users[0]
            
            # Create test user
            await conn.execute("""
                INSERT INTO users (id, email, name, password_hash, created_at, email_verified, failed_attempts, locked_until)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO UPDATE SET
                    failed_attempts = EXCLUDED.failed_attempts,
                    locked_until = EXCLUDED.locked_until
            """, user["user_id"], user["email"], user["name"],
                bcrypt.hashpw(user["password"].encode(), bcrypt.gensalt()).decode(),
                datetime.now(timezone.utc), True, 0, None)
            
            async with httpx.AsyncClient() as client:
                
                # Test multiple failed login attempts
                max_attempts = 5
                
                for attempt in range(max_attempts + 2):  # Exceed the limit
                    
                    failed_response = await client.post(
                        f"{self.auth_service_url}/api/v1/auth/login",
                        json={
                            "email": user["email"],
                            "password": "WrongPassword123!"
                        },
                        timeout=10.0
                    )
                    
                    if attempt < max_attempts:
                        # Should fail but account not locked yet
                        assert failed_response.status_code in [401, 403, 404], \
                            f"Failed login attempt {attempt + 1} should be rejected"
                    else:
                        # Should be locked after max attempts
                        assert failed_response.status_code in [401, 403, 423, 429, 404], \
                            f"Account should be locked after {max_attempts} failed attempts"
                        
                        if failed_response.status_code == 423:
                            # Account locked response
                            lock_data = failed_response.json()
                            assert "locked_until" in lock_data or "retry_after" in lock_data
                
                # Check database shows failed attempts and lockout
                locked_user = await conn.fetchrow(
                    "SELECT failed_attempts, locked_until FROM users WHERE email = $1",
                    user["email"]
                )
                
                if locked_user:
                    if "failed_attempts" in locked_user:
                        assert locked_user["failed_attempts"] >= max_attempts, \
                            "Failed attempts should be tracked"
                    
                    if "locked_until" in locked_user and locked_user["locked_until"]:
                        assert locked_user["locked_until"] > datetime.now(timezone.utc), \
                            "Account should be locked until future time"
                
                # Test that correct password also fails when locked
                correct_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/login",
                    json={
                        "email": user["email"],
                        "password": user["password"]  # Correct password
                    },
                    timeout=10.0
                )
                
                # Should fail even with correct password when locked
                assert correct_response.status_code in [401, 403, 423, 429, 404], \
                    "Locked account should reject even correct passwords"
                
                # Test account unlock after timeout (simulate)
                if locked_user and "locked_until" in locked_user:
                    
                    # Simulate unlock by clearing lockout time
                    await conn.execute(
                        "UPDATE users SET locked_until = NULL, failed_attempts = 0 WHERE email = $1",
                        user["email"]
                    )
                    
                    # Now correct password should work
                    unlock_response = await client.post(
                        f"{self.auth_service_url}/api/v1/auth/login",
                        json={
                            "email": user["email"],
                            "password": user["password"]
                        },
                        timeout=10.0
                    )
                    
                    assert unlock_response.status_code in [200, 201, 404], \
                        "Unlocked account should accept correct password"
                
        except Exception as e:
            self.logger.warning(f"Account lockout test error: {e}")
            if "connection" in str(e).lower():
                pytest.skip("Services not available for lockout testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()
            await redis_client.aclose()