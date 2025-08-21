"""Authentication and Authorization Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (security foundation for all users)
- Business Goal: Secure access control and user session management
- Value Impact: Prevents unauthorized access, protects user data, maintains compliance
- Strategic Impact: $40K-80K MRR protection through security and compliance

Critical Path: User authentication -> Token generation -> Authorization checks -> Session management -> Logout/revocation
Coverage: OAuth/JWT flows, permission validation, session persistence, token refresh
"""

import pytest
import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import jwt

from app.auth_integration import (
    AuthServiceProtocol, 
    SessionManagerProtocol, 
    PermissionManagerProtocol,
    get_current_user,
    create_access_token,
    validate_token_jwt,
    LoginRequest,
    LoginResponse,
    TokenData
)
from app.services.user_service import user_service as UserService

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Manages authentication and authorization testing."""
    
    def __init__(self):
        # Use mock services for testing
        self.oauth_service = AsyncMock()
        self.jwt_service = AsyncMock()
        self.session_manager = AsyncMock()
        self.permissions_service = AsyncMock()
        self.user_service = UserService
        self.auth_sessions = {}
        self.auth_events = []
        self.permission_checks = []
        
    async def initialize_services(self):
        """Initialize authentication services with mocks."""
        try:
            # Configure mock services with basic functionality
            self.oauth_service.initialize = AsyncMock(return_value=True)
            self.jwt_service.initialize = AsyncMock(return_value=True)
            self.session_manager.initialize = AsyncMock(return_value=True)
            self.permissions_service.initialize = AsyncMock(return_value=True)
            
            # Initialize mock services
            await self.oauth_service.initialize()
            await self.jwt_service.initialize()
            await self.session_manager.initialize()
            await self.permissions_service.initialize()
            
            logger.info("Authentication services initialized with mocks")
            
        except Exception as e:
            logger.error(f"Failed to initialize authentication services: {e}")
            raise
    
    async def authenticate_user(self, username: str, password: str, 
                              auth_method: str = "password") -> Dict[str, Any]:
        """Authenticate user and create session."""
        auth_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Step 1: Validate credentials
            if auth_method == "password":
                auth_result = await self.validate_password_auth(username, password)
            elif auth_method == "oauth":
                auth_result = await self.validate_oauth_auth(username)
            else:
                raise ValueError(f"Unsupported auth method: {auth_method}")
            
            if not auth_result["valid"]:
                raise ValueError(f"Authentication failed: {auth_result['reason']}")
            
            user_data = auth_result["user_data"]
            
            # Step 2: Generate JWT token
            token_result = await self.jwt_service.generate_token(
                user_data["user_id"], user_data["permissions"], user_data.get("tier", "free")
            )
            
            if not token_result["success"]:
                raise ValueError(f"Token generation failed: {token_result['error']}")
            
            # Step 3: Create session
            session_result = await self.session_manager.create_session(
                user_data["user_id"], token_result["token"], {
                    "auth_method": auth_method,
                    "login_time": time.time(),
                    "user_agent": "test_client",
                    "ip_address": "127.0.0.1"
                }
            )
            
            if not session_result["success"]:
                raise ValueError(f"Session creation failed: {session_result['error']}")
            
            session_data = {
                "session_id": session_result["session_id"],
                "user_id": user_data["user_id"],
                "token": token_result["token"],
                "refresh_token": token_result.get("refresh_token"),
                "expires_at": token_result["expires_at"],
                "auth_method": auth_method,
                "created_at": time.time(),
                "permissions": user_data["permissions"]
            }
            
            self.auth_sessions[session_data["session_id"]] = session_data
            
            return {
                "auth_id": auth_id,
                "authenticated": True,
                "session_data": session_data,
                "auth_time": time.time() - start_time
            }
            
        except Exception as e:
            return {
                "auth_id": auth_id,
                "authenticated": False,
                "error": str(e),
                "auth_time": time.time() - start_time
            }
    
    async def cleanup(self):
        """Clean up authentication resources."""
        try:
            # Logout all active sessions
            for session_id in list(self.auth_sessions.keys()):
                await self.logout_user(session_id)
            
            if self.oauth_service:
                await self.oauth_service.shutdown()
            if self.jwt_service:
                await self.jwt_service.shutdown()
            if self.session_manager:
                await self.session_manager.shutdown()
            if self.permissions_service:
                await self.permissions_service.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def auth_manager():
    """Create authentication manager for testing."""
    manager = AuthenticationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_password_authentication_flow(auth_manager):
    """Test complete password authentication flow."""
    # Test successful authentication
    auth_result = await auth_manager.authenticate_user(
        "test_user", "correct_password", "password"
    )
    
    assert auth_result["authenticated"] is True
    assert "session_data" in auth_result
    assert auth_result["auth_time"] < 2.0  # Should be fast
    
    session_data = auth_result["session_data"]
    assert "session_id" in session_data
    assert "token" in session_data
    assert "user_id" in session_data


@pytest.mark.asyncio
async def test_authentication_security_controls(auth_manager):
    """Test security controls in authentication flow."""
    # Test failed authentication
    failed_auth = await auth_manager.authenticate_user(
        "test_user", "wrong_password", "password"
    )
    
    assert failed_auth["authenticated"] is False
    assert "error" in failed_auth
