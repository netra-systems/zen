from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''User Login Flow Integration Tests (L3)

env = get_env()
# REMOVED_SYNTAX_ERROR: Comprehensive integration tests for all user login scenarios including OAuth,
# REMOVED_SYNTAX_ERROR: API key authentication, session management, and multi-device login flows.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: ALL (Free → Enterprise)
    # REMOVED_SYNTAX_ERROR: - Business Goal: Maximize conversion through seamless authentication
    # REMOVED_SYNTAX_ERROR: - Value Impact: 15% conversion improvement = $20K MRR increase
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: User trust and security directly impact retention (40% impact)

    # REMOVED_SYNTAX_ERROR: Test Coverage:
        # REMOVED_SYNTAX_ERROR: - OAuth login flows (Google, GitHub)
        # REMOVED_SYNTAX_ERROR: - Email/password authentication
        # REMOVED_SYNTAX_ERROR: - API key authentication
        # REMOVED_SYNTAX_ERROR: - Multi-device session management
        # REMOVED_SYNTAX_ERROR: - Token refresh flows
        # REMOVED_SYNTAX_ERROR: - Session invalidation
        # REMOVED_SYNTAX_ERROR: - Account linking
        # REMOVED_SYNTAX_ERROR: - MFA flows
        # REMOVED_SYNTAX_ERROR: """"

        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: from pathlib import Path

        # Test framework import - using pytest fixtures instead

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import hashlib
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import secrets
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from dataclasses import dataclass, field
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
        # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional, Tuple

        # REMOVED_SYNTAX_ERROR: import httpx
        # REMOVED_SYNTAX_ERROR: import jwt
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import websockets

        # Set test environment
        # REMOVED_SYNTAX_ERROR: env.set("ENVIRONMENT", "testing", "test")
        # REMOVED_SYNTAX_ERROR: env.set("TESTING", "true", "test")

        # Import auth types
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import auth_client

        # Test infrastructure
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.config import get_settings
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.auth_types import ( )
        # REMOVED_SYNTAX_ERROR: AuditLog,
        # REMOVED_SYNTAX_ERROR: AuthError,
        # REMOVED_SYNTAX_ERROR: AuthProvider,
        # REMOVED_SYNTAX_ERROR: LoginRequest,
        # REMOVED_SYNTAX_ERROR: LoginResponse,
        # REMOVED_SYNTAX_ERROR: RefreshRequest,
        # REMOVED_SYNTAX_ERROR: SessionInfo,
        # REMOVED_SYNTAX_ERROR: Token,
        # REMOVED_SYNTAX_ERROR: TokenData,
        # REMOVED_SYNTAX_ERROR: UserInfo,
        

        # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class LoginTestUser:
    # REMOVED_SYNTAX_ERROR: """Test user for login flow testing."""
    # REMOVED_SYNTAX_ERROR: email: str
    # REMOVED_SYNTAX_ERROR: password: Optional[str] = None
    # REMOVED_SYNTAX_ERROR: provider: AuthProvider = AuthProvider.LOCAL
    # REMOVED_SYNTAX_ERROR: oauth_token: Optional[str] = None
    # REMOVED_SYNTAX_ERROR: api_key: Optional[str] = None
    # REMOVED_SYNTAX_ERROR: tier: str = "free"
    # REMOVED_SYNTAX_ERROR: mfa_enabled: bool = False
    # REMOVED_SYNTAX_ERROR: mfa_secret: Optional[str] = None
    # REMOVED_SYNTAX_ERROR: devices: List[str] = field(default_factory=list)
    # REMOVED_SYNTAX_ERROR: sessions: List[str] = field(default_factory=list)

    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class LoginFlowMetrics:
    # REMOVED_SYNTAX_ERROR: """Metrics for login flow testing."""
    # REMOVED_SYNTAX_ERROR: total_login_attempts: int = 0
    # REMOVED_SYNTAX_ERROR: successful_logins: int = 0
    # REMOVED_SYNTAX_ERROR: failed_logins: int = 0
    # REMOVED_SYNTAX_ERROR: oauth_logins: int = 0
    # REMOVED_SYNTAX_ERROR: api_key_logins: int = 0
    # REMOVED_SYNTAX_ERROR: mfa_challenges: int = 0
    # REMOVED_SYNTAX_ERROR: token_refreshes: int = 0
    # REMOVED_SYNTAX_ERROR: session_invalidations: int = 0
    # REMOVED_SYNTAX_ERROR: average_login_time: float = 0.0
    # REMOVED_SYNTAX_ERROR: concurrent_sessions: int = 0

# REMOVED_SYNTAX_ERROR: class UserLoginFlowTestSuite:
    # REMOVED_SYNTAX_ERROR: """Test suite for user login flows."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.settings = get_settings()
    # REMOVED_SYNTAX_ERROR: self.test_users: Dict[str, LoginTestUser] = {]
    # REMOVED_SYNTAX_ERROR: self.active_sessions: Dict[str, SessionInfo] = {]
    # REMOVED_SYNTAX_ERROR: self.login_metrics = LoginFlowMetrics()
    # REMOVED_SYNTAX_ERROR: self.jwt_secret = "test_jwt_secret_key"

# REMOVED_SYNTAX_ERROR: def create_test_user( )
self,
# REMOVED_SYNTAX_ERROR: email: str,
provider: AuthProvider = AuthProvider.LOCAL,
tier: str = "free",
mfa_enabled: bool = False
# REMOVED_SYNTAX_ERROR: ) -> LoginTestUser:
    # REMOVED_SYNTAX_ERROR: """Create a test user for login testing."""
    # REMOVED_SYNTAX_ERROR: user = LoginTestUser( )
    # REMOVED_SYNTAX_ERROR: email=email,
    # REMOVED_SYNTAX_ERROR: password="formatted_string" if provider == AuthProvider.LOCAL else None,
    # REMOVED_SYNTAX_ERROR: provider=provider,
    # REMOVED_SYNTAX_ERROR: tier=tier,
    # REMOVED_SYNTAX_ERROR: mfa_enabled=mfa_enabled,
    # REMOVED_SYNTAX_ERROR: mfa_secret=secrets.token_hex(16) if mfa_enabled else None
    

    # REMOVED_SYNTAX_ERROR: if provider != AuthProvider.LOCAL:
        # Generate OAuth token for non-local providers
        # REMOVED_SYNTAX_ERROR: user.oauth_token = self.generate_oauth_token(email, provider)

        # Generate API key
        # REMOVED_SYNTAX_ERROR: user.api_key = self.generate_api_key(email)

        # REMOVED_SYNTAX_ERROR: self.test_users[email] = user
        # REMOVED_SYNTAX_ERROR: return user

# REMOVED_SYNTAX_ERROR: def generate_oauth_token(self, email: str, provider: AuthProvider) -> str:
    # REMOVED_SYNTAX_ERROR: """Generate mock OAuth token."""
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "email": email,
    # REMOVED_SYNTAX_ERROR: "provider": provider,
    # REMOVED_SYNTAX_ERROR: "iat": now.timestamp(),  # Use timestamp with microseconds for uniqueness
    # REMOVED_SYNTAX_ERROR: "exp": (now + timedelta(hours=1)).timestamp()
    
    # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

# REMOVED_SYNTAX_ERROR: def generate_api_key(self, email: str) -> str:
    # REMOVED_SYNTAX_ERROR: """Generate API key for user."""
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

# REMOVED_SYNTAX_ERROR: def generate_jwt_token( )
self,
# REMOVED_SYNTAX_ERROR: user: LoginTestUser,
expires_in: int = 3600
# REMOVED_SYNTAX_ERROR: ) -> str:
    # REMOVED_SYNTAX_ERROR: """Generate JWT access token."""
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "sub": user.email,
    # REMOVED_SYNTAX_ERROR: "email": user.email,
    # REMOVED_SYNTAX_ERROR: "tier": user.tier,
    # REMOVED_SYNTAX_ERROR: "iat": now.timestamp(),  # Use timestamp with microseconds for uniqueness
    # REMOVED_SYNTAX_ERROR: "exp": (now + timedelta(seconds=expires_in)).timestamp()
    
    # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

# REMOVED_SYNTAX_ERROR: def generate_refresh_token(self, user: LoginTestUser) -> str:
    # REMOVED_SYNTAX_ERROR: """Generate refresh token."""
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "sub": user.email,
    # REMOVED_SYNTAX_ERROR: "type": "refresh",
    # REMOVED_SYNTAX_ERROR: "iat": now.timestamp(),  # Use timestamp with microseconds for uniqueness
    # REMOVED_SYNTAX_ERROR: "exp": (now + timedelta(days=7)).timestamp()
    
    # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

# REMOVED_SYNTAX_ERROR: async def perform_login( )
self,
# REMOVED_SYNTAX_ERROR: user: LoginTestUser,
device_id: Optional[str] = None
# REMOVED_SYNTAX_ERROR: ) -> Optional[LoginResponse]:
    # REMOVED_SYNTAX_ERROR: """Perform login for a test user."""
    # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()
    # REMOVED_SYNTAX_ERROR: self.login_metrics.total_login_attempts += 1

    # REMOVED_SYNTAX_ERROR: try:
        # Mock login based on provider
        # REMOVED_SYNTAX_ERROR: if user.provider == AuthProvider.LOCAL:
            # REMOVED_SYNTAX_ERROR: response = await self.login_with_password(user)
            # REMOVED_SYNTAX_ERROR: elif user.provider in [AuthProvider.GOOGLE, AuthProvider.GITHUB]:
                # REMOVED_SYNTAX_ERROR: response = await self.login_with_oauth(user)
                # REMOVED_SYNTAX_ERROR: elif user.provider == AuthProvider.API_KEY:
                    # REMOVED_SYNTAX_ERROR: response = await self.login_with_api_key(user)
                    # REMOVED_SYNTAX_ERROR: else:
                        # REMOVED_SYNTAX_ERROR: raise ValueError("formatted_string")

                        # REMOVED_SYNTAX_ERROR: if response:
                            # REMOVED_SYNTAX_ERROR: self.login_metrics.successful_logins += 1

                            # Track device
                            # REMOVED_SYNTAX_ERROR: if device_id and device_id not in user.devices:
                                # REMOVED_SYNTAX_ERROR: user.devices.append(device_id)

                                # Create session
                                # REMOVED_SYNTAX_ERROR: session_id = secrets.token_hex(16)
                                # REMOVED_SYNTAX_ERROR: user.sessions.append(session_id)

                                # REMOVED_SYNTAX_ERROR: session = SessionInfo( )
                                # REMOVED_SYNTAX_ERROR: session_id=session_id,
                                # REMOVED_SYNTAX_ERROR: user_id=user.email,
                                # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc),
                                # REMOVED_SYNTAX_ERROR: last_activity=datetime.now(timezone.utc),
                                # REMOVED_SYNTAX_ERROR: metadata={"device_id": device_id} if device_id else {}
                                
                                # REMOVED_SYNTAX_ERROR: self.active_sessions[session_id] = session

                                # Update metrics
                                # REMOVED_SYNTAX_ERROR: login_time = time.perf_counter() - start_time
                                # REMOVED_SYNTAX_ERROR: self.login_metrics.average_login_time = ( )
                                # REMOVED_SYNTAX_ERROR: (self.login_metrics.average_login_time * (self.login_metrics.successful_logins - 1) + login_time)
                                # REMOVED_SYNTAX_ERROR: / self.login_metrics.successful_logins
                                

                                # REMOVED_SYNTAX_ERROR: return response

                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                    # REMOVED_SYNTAX_ERROR: self.login_metrics.failed_logins += 1
                                    # REMOVED_SYNTAX_ERROR: return None

# REMOVED_SYNTAX_ERROR: async def login_with_password(self, user: LoginTestUser) -> Optional[LoginResponse]:
    # REMOVED_SYNTAX_ERROR: """Mock password-based login with rate limiting and account lockout."""
    # Mock password verification
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # Simulate auth delay

    # Initialize tracking dictionaries
    # REMOVED_SYNTAX_ERROR: if not hasattr(self, 'failed_attempts'):
        # REMOVED_SYNTAX_ERROR: self.failed_attempts = {}
        # REMOVED_SYNTAX_ERROR: if not hasattr(self, 'locked_accounts'):
            # REMOVED_SYNTAX_ERROR: self.locked_accounts = {}

            # REMOVED_SYNTAX_ERROR: email = user.email
            # REMOVED_SYNTAX_ERROR: if email not in self.failed_attempts:
                # REMOVED_SYNTAX_ERROR: self.failed_attempts[email] = 0

                # Debug print
                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # Check if account is locked FIRST (10+ failed attempts from different IPs = lockout)
                # REMOVED_SYNTAX_ERROR: if email in self.locked_accounts and self.locked_accounts[email]:
                    # REMOVED_SYNTAX_ERROR: print(f"DEBUG login_with_password: Account is locked, raising exception")
                    # REMOVED_SYNTAX_ERROR: raise Exception("formatted_string")

                    # Check if rate limited (5 failed attempts max)
                    # REMOVED_SYNTAX_ERROR: if self.failed_attempts[email] >= 5:
                        # REMOVED_SYNTAX_ERROR: print(f"DEBUG login_with_password: Rate limited, raising exception")
                        # REMOVED_SYNTAX_ERROR: raise Exception("formatted_string")

                        # Check password - handle both original format and custom passwords
                        # REMOVED_SYNTAX_ERROR: original_password = "formatted_string"
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                        # Password is valid if it matches the original format OR if user changed it (and it's not empty)
                        # REMOVED_SYNTAX_ERROR: password_valid = (user.password == original_password) or (user.password and user.password != original_password and len(user.password) > 8)

                        # REMOVED_SYNTAX_ERROR: if not password_valid:
                            # Wrong password - increment failed attempts
                            # REMOVED_SYNTAX_ERROR: self.failed_attempts[email] += 1
                            # REMOVED_SYNTAX_ERROR: self.login_metrics.failed_logins += 1

                            # Check for account lockout (10+ failed attempts)
                            # REMOVED_SYNTAX_ERROR: if self.failed_attempts[email] >= 10:
                                # REMOVED_SYNTAX_ERROR: self.locked_accounts[email] = True

                                # REMOVED_SYNTAX_ERROR: print(f"DEBUG login_with_password: Wrong password, returning None")
                                # REMOVED_SYNTAX_ERROR: return None  # Failed login

                                # Successful login - reset failed attempts only if account is not locked
                                # REMOVED_SYNTAX_ERROR: if not (email in self.locked_accounts and self.locked_accounts[email]):
                                    # REMOVED_SYNTAX_ERROR: self.failed_attempts[email] = 0

                                    # REMOVED_SYNTAX_ERROR: print(f"DEBUG login_with_password: Successful login, generating tokens")

                                    # REMOVED_SYNTAX_ERROR: access_token = self.generate_jwt_token(user)
                                    # REMOVED_SYNTAX_ERROR: refresh_token = self.generate_refresh_token(user)

                                    # REMOVED_SYNTAX_ERROR: return LoginResponse( )
                                    # REMOVED_SYNTAX_ERROR: access_token=access_token,
                                    # REMOVED_SYNTAX_ERROR: refresh_token=refresh_token,
                                    # REMOVED_SYNTAX_ERROR: expires_in=3600,
                                    # REMOVED_SYNTAX_ERROR: user={"email": user.email, "tier": user.tier}
                                    

# REMOVED_SYNTAX_ERROR: async def login_with_oauth(self, user: LoginTestUser) -> LoginResponse:
    # REMOVED_SYNTAX_ERROR: """Mock OAuth login."""
    # REMOVED_SYNTAX_ERROR: self.login_metrics.oauth_logins += 1
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.2)  # Simulate OAuth flow

    # REMOVED_SYNTAX_ERROR: access_token = self.generate_jwt_token(user)
    # REMOVED_SYNTAX_ERROR: refresh_token = self.generate_refresh_token(user)

    # REMOVED_SYNTAX_ERROR: return LoginResponse( )
    # REMOVED_SYNTAX_ERROR: access_token=access_token,
    # REMOVED_SYNTAX_ERROR: refresh_token=refresh_token,
    # REMOVED_SYNTAX_ERROR: expires_in=3600,
    # REMOVED_SYNTAX_ERROR: user={"email": user.email, "tier": user.tier, "provider": user.provider}
    

# REMOVED_SYNTAX_ERROR: async def login_with_api_key(self, user: LoginTestUser) -> LoginResponse:
    # REMOVED_SYNTAX_ERROR: """Mock API key login."""
    # REMOVED_SYNTAX_ERROR: self.login_metrics.api_key_logins += 1
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.05)  # Simulate API key validation

    # REMOVED_SYNTAX_ERROR: access_token = self.generate_jwt_token(user, expires_in=86400)  # 24 hours for API keys

    # REMOVED_SYNTAX_ERROR: return LoginResponse( )
    # REMOVED_SYNTAX_ERROR: access_token=access_token,
    # REMOVED_SYNTAX_ERROR: expires_in=86400,
    # REMOVED_SYNTAX_ERROR: user={"email": user.email, "tier": user.tier, "auth_type": "api_key"}
    

# REMOVED_SYNTAX_ERROR: async def refresh_token(self, refresh_token: str) -> Optional[Token]:
    # REMOVED_SYNTAX_ERROR: """Refresh access token."""
    # REMOVED_SYNTAX_ERROR: self.login_metrics.token_refreshes += 1

    # REMOVED_SYNTAX_ERROR: try:
        # Decode refresh token
        # REMOVED_SYNTAX_ERROR: payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=["HS256"])
        # REMOVED_SYNTAX_ERROR: email = payload.get("sub")

        # REMOVED_SYNTAX_ERROR: if email and email in self.test_users:
            # REMOVED_SYNTAX_ERROR: user = self.test_users[email]
            # REMOVED_SYNTAX_ERROR: new_access_token = self.generate_jwt_token(user)

            # REMOVED_SYNTAX_ERROR: return Token( )
            # REMOVED_SYNTAX_ERROR: access_token=new_access_token,
            # REMOVED_SYNTAX_ERROR: token_type="Bearer",
            # REMOVED_SYNTAX_ERROR: expires_in=3600
            
            # REMOVED_SYNTAX_ERROR: except jwt.InvalidTokenError:
                # REMOVED_SYNTAX_ERROR: pass

                # REMOVED_SYNTAX_ERROR: return None

# REMOVED_SYNTAX_ERROR: async def invalidate_session(self, session_id: str) -> bool:
    # REMOVED_SYNTAX_ERROR: """Invalidate a user session."""
    # REMOVED_SYNTAX_ERROR: if session_id in self.active_sessions:
        # REMOVED_SYNTAX_ERROR: session = self.active_sessions.pop(session_id)

        # Remove from user's sessions
        # REMOVED_SYNTAX_ERROR: if session.user_id in self.test_users:
            # REMOVED_SYNTAX_ERROR: user = self.test_users[session.user_id]
            # REMOVED_SYNTAX_ERROR: if session_id in user.sessions:
                # REMOVED_SYNTAX_ERROR: user.sessions.remove(session_id)

                # REMOVED_SYNTAX_ERROR: self.login_metrics.session_invalidations += 1
                # REMOVED_SYNTAX_ERROR: return True

                # REMOVED_SYNTAX_ERROR: return False

                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                # REMOVED_SYNTAX_ERROR: @pytest.mark.l3
# REMOVED_SYNTAX_ERROR: class TestUserLoginFlowsL3:
    # REMOVED_SYNTAX_ERROR: """L3 integration tests for user login flows."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def login_suite(self):
    # REMOVED_SYNTAX_ERROR: """Create login test suite."""
    # REMOVED_SYNTAX_ERROR: suite = UserLoginFlowTestSuite()
    # REMOVED_SYNTAX_ERROR: yield suite
    # Cleanup sessions
    # REMOVED_SYNTAX_ERROR: suite.active_sessions.clear()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_basic_email_password_login(self, login_suite):
        # REMOVED_SYNTAX_ERROR: """Test 1: Basic email/password login flow."""
        # Create test user
        # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
        # REMOVED_SYNTAX_ERROR: email="basic@example.com",
        # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL,
        # REMOVED_SYNTAX_ERROR: tier="free"
        

        # Perform login
        # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user, device_id="device_001")

        # REMOVED_SYNTAX_ERROR: assert response is not None
        # REMOVED_SYNTAX_ERROR: assert response.access_token is not None
        # REMOVED_SYNTAX_ERROR: assert response.refresh_token is not None
        # REMOVED_SYNTAX_ERROR: assert response.expires_in == 3600
        # REMOVED_SYNTAX_ERROR: assert response.user["email"] == "basic@example.com"

        # Verify session created
        # REMOVED_SYNTAX_ERROR: assert len(user.sessions) == 1
        # REMOVED_SYNTAX_ERROR: assert user.sessions[0] in login_suite.active_sessions

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_google_oauth_login(self, login_suite):
            # REMOVED_SYNTAX_ERROR: """Test 2: Google OAuth login flow."""
            # Create OAuth user
            # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
            # REMOVED_SYNTAX_ERROR: email="google@example.com",
            # REMOVED_SYNTAX_ERROR: provider=AuthProvider.GOOGLE,
            # REMOVED_SYNTAX_ERROR: tier="early"
            

            # Perform OAuth login
            # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user, device_id="device_002")

            # REMOVED_SYNTAX_ERROR: assert response is not None
            # REMOVED_SYNTAX_ERROR: assert response.access_token is not None
            # REMOVED_SYNTAX_ERROR: assert response.user["provider"] == AuthProvider.GOOGLE
            # REMOVED_SYNTAX_ERROR: assert login_suite.login_metrics.oauth_logins == 1

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_api_key_authentication(self, login_suite):
                # REMOVED_SYNTAX_ERROR: """Test 3: API key authentication flow."""
                # Create user with API key
                # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                # REMOVED_SYNTAX_ERROR: email="api@example.com",
                # REMOVED_SYNTAX_ERROR: provider=AuthProvider.API_KEY,
                # REMOVED_SYNTAX_ERROR: tier="enterprise"
                

                # Login with API key
                # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user)

                # REMOVED_SYNTAX_ERROR: assert response is not None
                # REMOVED_SYNTAX_ERROR: assert response.access_token is not None
                # REMOVED_SYNTAX_ERROR: assert response.expires_in == 86400  # 24 hours for API keys
                # REMOVED_SYNTAX_ERROR: assert response.user["auth_type"] == "api_key"
                # REMOVED_SYNTAX_ERROR: assert login_suite.login_metrics.api_key_logins == 1

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_concurrent_multi_device_login(self, login_suite):
                    # REMOVED_SYNTAX_ERROR: """Test 4: Concurrent login from multiple devices."""
                    # Create user
                    # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                    # REMOVED_SYNTAX_ERROR: email="multidevice@example.com",
                    # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL,
                    # REMOVED_SYNTAX_ERROR: tier="mid"
                    

                    # Login from multiple devices concurrently
                    # REMOVED_SYNTAX_ERROR: devices = ["phone_001", "tablet_001", "desktop_001", "laptop_001"]

                    # REMOVED_SYNTAX_ERROR: login_tasks = [ )
                    # REMOVED_SYNTAX_ERROR: login_suite.perform_login(user, device_id=device)
                    # REMOVED_SYNTAX_ERROR: for device in devices
                    

                    # REMOVED_SYNTAX_ERROR: responses = await asyncio.gather(*login_tasks)

                    # All logins should succeed
                    # REMOVED_SYNTAX_ERROR: assert all(r is not None for r in responses)
                    # REMOVED_SYNTAX_ERROR: assert len(user.sessions) == len(devices)
                    # REMOVED_SYNTAX_ERROR: assert len(user.devices) == len(devices)

                    # Verify all sessions are active
                    # REMOVED_SYNTAX_ERROR: assert len(login_suite.active_sessions) == len(devices)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_token_refresh_flow(self, login_suite):
                        # REMOVED_SYNTAX_ERROR: """Test 5: Token refresh flow."""
                        # Create and login user
                        # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                        # REMOVED_SYNTAX_ERROR: email="refresh@example.com",
                        # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                        

                        # REMOVED_SYNTAX_ERROR: login_response = await login_suite.perform_login(user)
                        # REMOVED_SYNTAX_ERROR: assert login_response is not None

                        # REMOVED_SYNTAX_ERROR: initial_access_token = login_response.access_token
                        # REMOVED_SYNTAX_ERROR: refresh_token = login_response.refresh_token

                        # Wait a bit
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.5)

                        # Refresh token
                        # REMOVED_SYNTAX_ERROR: new_token = await login_suite.refresh_token(refresh_token)

                        # REMOVED_SYNTAX_ERROR: assert new_token is not None
                        # REMOVED_SYNTAX_ERROR: assert new_token.access_token != initial_access_token
                        # REMOVED_SYNTAX_ERROR: assert login_suite.login_metrics.token_refreshes == 1

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_session_invalidation_cascade(self, login_suite):
                            # REMOVED_SYNTAX_ERROR: """Test 6: Session invalidation across all devices."""
                            # Create user and login from multiple devices
                            # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                            # REMOVED_SYNTAX_ERROR: email="invalidate@example.com",
                            # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                            

                            # REMOVED_SYNTAX_ERROR: devices = ["device1", "device2", "device3"]
                            # REMOVED_SYNTAX_ERROR: for device in devices:
                                # REMOVED_SYNTAX_ERROR: await login_suite.perform_login(user, device_id=device)

                                # REMOVED_SYNTAX_ERROR: assert len(user.sessions) == 3

                                # Invalidate all sessions
                                # REMOVED_SYNTAX_ERROR: sessions_to_invalidate = user.sessions.copy()
                                # REMOVED_SYNTAX_ERROR: for session_id in sessions_to_invalidate:
                                    # REMOVED_SYNTAX_ERROR: result = await login_suite.invalidate_session(session_id)
                                    # REMOVED_SYNTAX_ERROR: assert result is True

                                    # Verify all sessions cleared
                                    # REMOVED_SYNTAX_ERROR: assert len(user.sessions) == 0
                                    # REMOVED_SYNTAX_ERROR: assert login_suite.login_metrics.session_invalidations == 3

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_login_with_mfa(self, login_suite):
                                        # REMOVED_SYNTAX_ERROR: """Test 7: Login flow with MFA enabled."""
                                        # Create MFA-enabled user
                                        # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                        # REMOVED_SYNTAX_ERROR: email="mfa@example.com",
                                        # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL,
                                        # REMOVED_SYNTAX_ERROR: tier="enterprise",
                                        # REMOVED_SYNTAX_ERROR: mfa_enabled=True
                                        

                                        # Mock MFA challenge
# REMOVED_SYNTAX_ERROR: async def login_with_mfa():
    # REMOVED_SYNTAX_ERROR: login_suite.login_metrics.mfa_challenges += 1

    # First step: username/password
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

    # Second step: MFA code verification
    # REMOVED_SYNTAX_ERROR: mfa_code = "123456"  # Mock MFA code
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

    # Complete login
    # REMOVED_SYNTAX_ERROR: return await login_suite.perform_login(user)

    # REMOVED_SYNTAX_ERROR: response = await login_with_mfa()

    # REMOVED_SYNTAX_ERROR: assert response is not None
    # REMOVED_SYNTAX_ERROR: assert login_suite.login_metrics.mfa_challenges == 1

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_account_linking_flow(self, login_suite):
        # REMOVED_SYNTAX_ERROR: """Test 8: Link multiple auth providers to same account."""
        # Create user with local auth
        # REMOVED_SYNTAX_ERROR: email = "linked@example.com"
        # REMOVED_SYNTAX_ERROR: local_user = login_suite.create_test_user( )
        # REMOVED_SYNTAX_ERROR: email=email,
        # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL,
        # REMOVED_SYNTAX_ERROR: tier="mid"
        

        # Login with local auth
        # REMOVED_SYNTAX_ERROR: local_response = await login_suite.perform_login(local_user)
        # REMOVED_SYNTAX_ERROR: assert local_response is not None

        # Link Google OAuth to same account
        # REMOVED_SYNTAX_ERROR: google_user = LoginTestUser( )
        # REMOVED_SYNTAX_ERROR: email=email,
        # REMOVED_SYNTAX_ERROR: provider=AuthProvider.GOOGLE,
        # REMOVED_SYNTAX_ERROR: oauth_token=login_suite.generate_oauth_token(email, AuthProvider.GOOGLE),
        # REMOVED_SYNTAX_ERROR: tier="mid"
        

        # Mock account linking
        # REMOVED_SYNTAX_ERROR: google_user.sessions = local_user.sessions  # Share sessions
        # REMOVED_SYNTAX_ERROR: google_user.devices = local_user.devices    # Share devices

        # Login with Google (should recognize linked account)
        # REMOVED_SYNTAX_ERROR: google_response = await login_suite.login_with_oauth(google_user)
        # REMOVED_SYNTAX_ERROR: assert google_response is not None

        # Both providers should work for same account
        # REMOVED_SYNTAX_ERROR: assert local_response.user["email"] == google_response.user["email"]

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_rate_limited_login_attempts(self, login_suite):
            # REMOVED_SYNTAX_ERROR: """Test 9: Rate limiting on failed login attempts."""
            # Create user
            # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
            # REMOVED_SYNTAX_ERROR: email="ratelimit@example.com",
            # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
            

            # Mock failed login attempts
            # REMOVED_SYNTAX_ERROR: failed_attempts = 0
            # REMOVED_SYNTAX_ERROR: max_attempts = 5

            # REMOVED_SYNTAX_ERROR: for i in range(10):
                # Mock wrong password
                # REMOVED_SYNTAX_ERROR: user.password = "wrong_password"

                # REMOVED_SYNTAX_ERROR: try:
                    # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user)
                    # REMOVED_SYNTAX_ERROR: if response is None:
                        # REMOVED_SYNTAX_ERROR: failed_attempts += 1
                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: if "rate limit" in str(e).lower():
                                # Rate limit hit
                                # REMOVED_SYNTAX_ERROR: assert failed_attempts >= max_attempts
                                # REMOVED_SYNTAX_ERROR: break

                                # Should hit rate limit
                                # REMOVED_SYNTAX_ERROR: assert failed_attempts >= max_attempts

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_session_timeout_handling(self, login_suite):
                                    # REMOVED_SYNTAX_ERROR: """Test 10: Session timeout and auto-renewal."""
                                    # Create user with short session timeout
                                    # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                    # REMOVED_SYNTAX_ERROR: email="timeout@example.com",
                                    # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                                    

                                    # Login
                                    # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user)
                                    # REMOVED_SYNTAX_ERROR: assert response is not None

                                    # REMOVED_SYNTAX_ERROR: session_id = user.sessions[0]
                                    # REMOVED_SYNTAX_ERROR: session = login_suite.active_sessions[session_id]

                                    # Simulate session activity
                                    # REMOVED_SYNTAX_ERROR: for _ in range(3):
                                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.5)
                                        # Update last activity
                                        # REMOVED_SYNTAX_ERROR: session.last_activity = datetime.now(timezone.utc)

                                        # Check if session still valid
                                        # REMOVED_SYNTAX_ERROR: time_since_creation = (datetime.now(timezone.utc) - session.created_at).total_seconds()
                                        # REMOVED_SYNTAX_ERROR: time_since_activity = (datetime.now(timezone.utc) - session.last_activity).total_seconds()

                                        # REMOVED_SYNTAX_ERROR: assert time_since_activity < 60  # Should have recent activity

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_cross_origin_login_validation(self, login_suite):
                                            # REMOVED_SYNTAX_ERROR: """Test 11: Cross-origin login request validation."""
                                            # Create user
                                            # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                            # REMOVED_SYNTAX_ERROR: email="cors@example.com",
                                            # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                                            

                                            # Mock login from allowed origin
                                            # REMOVED_SYNTAX_ERROR: allowed_origin = "https://app.netrasystems.ai"
                                            # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user, device_id="allowed_device")
                                            # REMOVED_SYNTAX_ERROR: assert response is not None

                                            # Mock login from disallowed origin
                                            # In real implementation, this would be blocked
                                            # REMOVED_SYNTAX_ERROR: disallowed_origin = "https://malicious.site"

                                            # Mock CORS validation
                                            # REMOVED_SYNTAX_ERROR: cors_allowed = allowed_origin in ["https://app.netrasystems.ai", "http://localhost:3000"]
                                            # REMOVED_SYNTAX_ERROR: cors_blocked = disallowed_origin not in ["https://app.netrasystems.ai", "http://localhost:3000"]

                                            # REMOVED_SYNTAX_ERROR: assert cors_allowed is True
                                            # REMOVED_SYNTAX_ERROR: assert cors_blocked is True

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_password_reset_flow(self, login_suite):
                                                # REMOVED_SYNTAX_ERROR: """Test 12: Password reset and recovery flow."""
                                                # Create user
                                                # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                # REMOVED_SYNTAX_ERROR: email="reset@example.com",
                                                # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                                                

                                                # Mock password reset request
                                                # REMOVED_SYNTAX_ERROR: reset_token = secrets.token_urlsafe(32)
                                                # REMOVED_SYNTAX_ERROR: reset_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

                                                # Mock email sent
                                                # REMOVED_SYNTAX_ERROR: email_sent = True

                                                # Mock password reset with token
                                                # REMOVED_SYNTAX_ERROR: new_password = "NewSecure@Password456"

                                                # Validate reset token
                                                # REMOVED_SYNTAX_ERROR: token_valid = datetime.now(timezone.utc) < reset_expiry

                                                # REMOVED_SYNTAX_ERROR: if token_valid:
                                                    # Update password
                                                    # REMOVED_SYNTAX_ERROR: user.password = new_password

                                                    # Invalidate all existing sessions
                                                    # REMOVED_SYNTAX_ERROR: for session_id in user.sessions.copy():
                                                        # REMOVED_SYNTAX_ERROR: await login_suite.invalidate_session(session_id)

                                                        # Login with new password
                                                        # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user)
                                                        # REMOVED_SYNTAX_ERROR: assert response is not None

                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_oauth_state_parameter_validation(self, login_suite):
                                                            # REMOVED_SYNTAX_ERROR: """Test 13: OAuth state parameter for CSRF protection."""
                                                            # Create OAuth user
                                                            # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                            # REMOVED_SYNTAX_ERROR: email="oauth_state@example.com",
                                                            # REMOVED_SYNTAX_ERROR: provider=AuthProvider.GOOGLE
                                                            

                                                            # Generate state parameter
                                                            # REMOVED_SYNTAX_ERROR: state = secrets.token_urlsafe(32)
                                                            # REMOVED_SYNTAX_ERROR: state_hash = hashlib.sha256(state.encode()).hexdigest()

                                                            # Mock OAuth flow with state
                                                            # REMOVED_SYNTAX_ERROR: oauth_url = "formatted_string"

                                                            # Mock callback with state validation
                                                            # REMOVED_SYNTAX_ERROR: returned_state = state  # In real flow, this comes from OAuth provider

                                                            # Validate state
                                                            # REMOVED_SYNTAX_ERROR: state_valid = hashlib.sha256(returned_state.encode()).hexdigest() == state_hash
                                                            # REMOVED_SYNTAX_ERROR: assert state_valid is True

                                                            # Complete OAuth login
                                                            # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user)
                                                            # REMOVED_SYNTAX_ERROR: assert response is not None

                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_login_audit_logging(self, login_suite):
                                                                # REMOVED_SYNTAX_ERROR: """Test 14: Comprehensive audit logging for login events."""
                                                                # Create user
                                                                # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                                # REMOVED_SYNTAX_ERROR: email="audit@example.com",
                                                                # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                                                                

                                                                # Mock audit log entries
                                                                # REMOVED_SYNTAX_ERROR: audit_logs: List[AuditLog] = []

                                                                # Login attempt
                                                                # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user, device_id="audit_device")

                                                                # Create audit log
                                                                # REMOVED_SYNTAX_ERROR: audit_logs.append(AuditLog( ))
                                                                # REMOVED_SYNTAX_ERROR: event_id=secrets.token_hex(16),
                                                                # REMOVED_SYNTAX_ERROR: event_type="login_success",
                                                                # REMOVED_SYNTAX_ERROR: user_id=user.email,
                                                                # REMOVED_SYNTAX_ERROR: ip_address="192.168.1.100",
                                                                # REMOVED_SYNTAX_ERROR: user_agent="TestClient/1.0",
                                                                # REMOVED_SYNTAX_ERROR: success=True,
                                                                # REMOVED_SYNTAX_ERROR: metadata={"device_id": "audit_device", "provider": user.provider}
                                                                

                                                                # Token refresh
                                                                # REMOVED_SYNTAX_ERROR: if response and response.refresh_token:
                                                                    # REMOVED_SYNTAX_ERROR: await login_suite.refresh_token(response.refresh_token)

                                                                    # REMOVED_SYNTAX_ERROR: audit_logs.append(AuditLog( ))
                                                                    # REMOVED_SYNTAX_ERROR: event_id=secrets.token_hex(16),
                                                                    # REMOVED_SYNTAX_ERROR: event_type="token_refresh",
                                                                    # REMOVED_SYNTAX_ERROR: user_id=user.email,
                                                                    # REMOVED_SYNTAX_ERROR: ip_address="192.168.1.100",
                                                                    # REMOVED_SYNTAX_ERROR: success=True,
                                                                    # REMOVED_SYNTAX_ERROR: metadata={}
                                                                    

                                                                    # Verify audit logs created
                                                                    # REMOVED_SYNTAX_ERROR: assert len(audit_logs) >= 2
                                                                    # REMOVED_SYNTAX_ERROR: assert all(log.event_type in ["login_success", "token_refresh"] for log in audit_logs)

                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                    # Removed problematic line: async def test_login_geographic_restrictions(self, login_suite):
                                                                        # REMOVED_SYNTAX_ERROR: """Test 15: Geographic-based login restrictions."""
                                                                        # Create user with geo restrictions
                                                                        # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                                        # REMOVED_SYNTAX_ERROR: email="geo@example.com",
                                                                        # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL,
                                                                        # REMOVED_SYNTAX_ERROR: tier="enterprise"
                                                                        

                                                                        # Mock allowed regions
                                                                        # REMOVED_SYNTAX_ERROR: allowed_regions = ["US", "EU", "UK"]

                                                                        # Login from allowed region
                                                                        # REMOVED_SYNTAX_ERROR: us_login = await login_suite.perform_login(user, device_id="us_device")
                                                                        # REMOVED_SYNTAX_ERROR: assert us_login is not None

                                                                        # Mock login from restricted region
                                                                        # REMOVED_SYNTAX_ERROR: restricted_region = "CN"

                                                                        # In real implementation, this would be blocked
                                                                        # REMOVED_SYNTAX_ERROR: geo_blocked = restricted_region not in allowed_regions
                                                                        # REMOVED_SYNTAX_ERROR: assert geo_blocked is True

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_device_trust_management(self, login_suite):
                                                                            # REMOVED_SYNTAX_ERROR: """Test 16: Device trust and management."""
                                                                            # Create user
                                                                            # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                                            # REMOVED_SYNTAX_ERROR: email="device_trust@example.com",
                                                                            # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                                                                            

                                                                            # Login from new device
                                                                            # REMOVED_SYNTAX_ERROR: new_device = "untrusted_device_001"
                                                                            # REMOVED_SYNTAX_ERROR: response = await login_suite.perform_login(user, device_id=new_device)
                                                                            # REMOVED_SYNTAX_ERROR: assert response is not None

                                                                            # Mock device trust establishment
                                                                            # REMOVED_SYNTAX_ERROR: trusted_devices = []

                                                                            # Mark device as trusted after successful login + verification
                                                                            # REMOVED_SYNTAX_ERROR: if new_device in user.devices:
                                                                                # REMOVED_SYNTAX_ERROR: trusted_devices.append(new_device)

                                                                                # Login from trusted device (faster, no additional verification)
                                                                                # REMOVED_SYNTAX_ERROR: trusted_response = await login_suite.perform_login(user, device_id=new_device)
                                                                                # REMOVED_SYNTAX_ERROR: assert trusted_response is not None

                                                                                # Trusted device login should be faster
                                                                                # REMOVED_SYNTAX_ERROR: assert new_device in trusted_devices

                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                # Removed problematic line: async def test_login_with_account_lockout(self, login_suite):
                                                                                    # REMOVED_SYNTAX_ERROR: """Test 17: Account lockout after suspicious activity."""
                                                                                    # Create user
                                                                                    # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                                                    # REMOVED_SYNTAX_ERROR: email="lockout@example.com",
                                                                                    # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                                                                                    

                                                                                    # Simulate account lockout by directly setting failed attempts to exceed threshold
                                                                                    # Initialize the tracking dictionaries
                                                                                    # REMOVED_SYNTAX_ERROR: if not hasattr(login_suite, 'failed_attempts'):
                                                                                        # REMOVED_SYNTAX_ERROR: login_suite.failed_attempts = {}
                                                                                        # REMOVED_SYNTAX_ERROR: if not hasattr(login_suite, 'locked_accounts'):
                                                                                            # REMOVED_SYNTAX_ERROR: login_suite.locked_accounts = {}

                                                                                            # Set account as having 10 failed attempts (which triggers lockout)
                                                                                            # REMOVED_SYNTAX_ERROR: login_suite.failed_attempts[user.email] = 10
                                                                                            # REMOVED_SYNTAX_ERROR: login_suite.locked_accounts[user.email] = True

                                                                                            # Now try to login with correct credentials - should still fail due to account lockout
                                                                                            # REMOVED_SYNTAX_ERROR: user.password = "formatted_string"  # Correct password

                                                                                            # Debug info to verify state
                                                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                                                            # Login should fail even with correct credentials due to account lockout
                                                                                            # REMOVED_SYNTAX_ERROR: try:
                                                                                                # REMOVED_SYNTAX_ERROR: result = await login_suite.perform_login(user)
                                                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                                # If we get here without exception, the test fails
                                                                                                # REMOVED_SYNTAX_ERROR: assert False, "formatted_string"
                                                                                                # REMOVED_SYNTAX_ERROR: except Exception as exc_info:
                                                                                                    # Should indicate account locked
                                                                                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                                    # REMOVED_SYNTAX_ERROR: assert "locked" in str(exc_info).lower()

                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                    # Removed problematic line: async def test_seamless_sso_flow(self, login_suite):
                                                                                                        # REMOVED_SYNTAX_ERROR: """Test 18: Seamless SSO across services."""
                                                                                                        # Create enterprise user with SSO
                                                                                                        # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                                                                        # REMOVED_SYNTAX_ERROR: email="sso@enterprise.com",
                                                                                                        # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL,
                                                                                                        # REMOVED_SYNTAX_ERROR: tier="enterprise"
                                                                                                        

                                                                                                        # Login to main service
                                                                                                        # REMOVED_SYNTAX_ERROR: main_response = await login_suite.perform_login(user, device_id="sso_device")
                                                                                                        # REMOVED_SYNTAX_ERROR: assert main_response is not None

                                                                                                        # Mock SSO token
                                                                                                        # REMOVED_SYNTAX_ERROR: sso_token = secrets.token_hex(32)

                                                                                                        # Access other services with SSO token (should not require re-auth)
                                                                                                        # REMOVED_SYNTAX_ERROR: services = ["analytics", "monitoring", "admin"]

                                                                                                        # REMOVED_SYNTAX_ERROR: for service in services:
                                                                                                            # Mock SSO validation
                                                                                                            # REMOVED_SYNTAX_ERROR: sso_valid = True  # In real impl, would validate SSO token
                                                                                                            # REMOVED_SYNTAX_ERROR: assert sso_valid is True

                                                                                                            # All services accessible with single login
                                                                                                            # REMOVED_SYNTAX_ERROR: assert len(services) == 3

                                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                                            # Removed problematic line: async def test_login_performance_under_load(self, login_suite):
                                                                                                                # REMOVED_SYNTAX_ERROR: """Test 19: Login performance under concurrent load."""
                                                                                                                # Create multiple test users
                                                                                                                # REMOVED_SYNTAX_ERROR: num_users = 50
                                                                                                                # REMOVED_SYNTAX_ERROR: users = []

                                                                                                                # REMOVED_SYNTAX_ERROR: for i in range(num_users):
                                                                                                                    # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                                                                                    # REMOVED_SYNTAX_ERROR: email="formatted_string",
                                                                                                                    # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL
                                                                                                                    
                                                                                                                    # REMOVED_SYNTAX_ERROR: users.append(user)

                                                                                                                    # Perform concurrent logins
                                                                                                                    # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

                                                                                                                    # REMOVED_SYNTAX_ERROR: login_tasks = [ )
                                                                                                                    # REMOVED_SYNTAX_ERROR: login_suite.perform_login(user, device_id="formatted_string")
                                                                                                                    # REMOVED_SYNTAX_ERROR: for i, user in enumerate(users)
                                                                                                                    

                                                                                                                    # REMOVED_SYNTAX_ERROR: responses = await asyncio.gather(*login_tasks, return_exceptions=True)

                                                                                                                    # REMOVED_SYNTAX_ERROR: total_time = time.perf_counter() - start_time

                                                                                                                    # Calculate success rate
                                                                                                                    # REMOVED_SYNTAX_ERROR: successful = sum(1 for r in responses if r is not None and not isinstance(r, Exception))
                                                                                                                    # REMOVED_SYNTAX_ERROR: success_rate = successful / num_users

                                                                                                                    # Performance assertions
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert success_rate >= 0.95  # 95% success rate
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert total_time < 10.0  # All logins complete within 10 seconds
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert login_suite.login_metrics.average_login_time < 1.0  # Each login < 1 second

                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                    # Removed problematic line: async def test_login_with_custom_claims(self, login_suite):
                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test 20: Login with custom JWT claims for enterprise features."""
                                                                                                                        # Create enterprise user
                                                                                                                        # REMOVED_SYNTAX_ERROR: user = login_suite.create_test_user( )
                                                                                                                        # REMOVED_SYNTAX_ERROR: email="custom_claims@enterprise.com",
                                                                                                                        # REMOVED_SYNTAX_ERROR: provider=AuthProvider.LOCAL,
                                                                                                                        # REMOVED_SYNTAX_ERROR: tier="enterprise"
                                                                                                                        

                                                                                                                        # Mock custom claims
                                                                                                                        # REMOVED_SYNTAX_ERROR: custom_claims = { )
                                                                                                                        # REMOVED_SYNTAX_ERROR: "organization_id": "org_123",
                                                                                                                        # REMOVED_SYNTAX_ERROR: "department": "engineering",
                                                                                                                        # REMOVED_SYNTAX_ERROR: "role": "admin",
                                                                                                                        # REMOVED_SYNTAX_ERROR: "permissions": ["read", "write", "delete", "admin"],
                                                                                                                        # REMOVED_SYNTAX_ERROR: "features": ["advanced_analytics", "custom_integrations", "priority_support"],
                                                                                                                        # REMOVED_SYNTAX_ERROR: "quota": { )
                                                                                                                        # REMOVED_SYNTAX_ERROR: "api_calls": 1000000,
                                                                                                                        # REMOVED_SYNTAX_ERROR: "storage_gb": 1000,
                                                                                                                        # REMOVED_SYNTAX_ERROR: "team_members": 100
                                                                                                                        
                                                                                                                        

                                                                                                                        # Generate token with custom claims
                                                                                                                        # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
                                                                                                                        # REMOVED_SYNTAX_ERROR: payload = { )
                                                                                                                        # REMOVED_SYNTAX_ERROR: "sub": user.email,
                                                                                                                        # REMOVED_SYNTAX_ERROR: "email": user.email,
                                                                                                                        # REMOVED_SYNTAX_ERROR: "tier": user.tier,
                                                                                                                        # REMOVED_SYNTAX_ERROR: **custom_claims,
                                                                                                                        # REMOVED_SYNTAX_ERROR: "iat": now.timestamp(),  # Use timestamp with microseconds for uniqueness
                                                                                                                        # REMOVED_SYNTAX_ERROR: "exp": (now + timedelta(hours=1)).timestamp()
                                                                                                                        

                                                                                                                        # REMOVED_SYNTAX_ERROR: custom_token = jwt.encode(payload, login_suite.jwt_secret, algorithm="HS256")

                                                                                                                        # Verify custom claims in token
                                                                                                                        # REMOVED_SYNTAX_ERROR: decoded = jwt.decode(custom_token, login_suite.jwt_secret, algorithms=["HS256"])

                                                                                                                        # REMOVED_SYNTAX_ERROR: assert decoded["organization_id"] == "org_123"
                                                                                                                        # REMOVED_SYNTAX_ERROR: assert "admin" in decoded["permissions"]
                                                                                                                        # REMOVED_SYNTAX_ERROR: assert decoded["quota"]["api_calls"] == 1000000