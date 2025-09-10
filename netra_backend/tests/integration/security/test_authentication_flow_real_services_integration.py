"""
Test Authentication Flow Real Services Integration

Business Value Justification (BVJ):
- Segment: All customer segments (security foundation)
- Business Goal: Ensure secure and reliable user authentication
- Value Impact: Auth failures block customer access and reduce trust
- Strategic Impact: Security compliance enables enterprise sales

CRITICAL REQUIREMENTS:
- Tests real authentication services (JWT, OAuth, Redis sessions)
- Validates security token generation, validation, refresh flows
- Uses real Redis and database connections, NO MOCKS
- Ensures authentication performance and security standards
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.auth_integration import auth
from netra_backend.app.services.session_service import SessionService as SessionManager
from netra_backend.app.services.auth.oauth_integration import OAuthIntegration


class TestAuthenticationFlowRealServicesIntegration(SSotBaseTestCase):
    """Test authentication flows with real services"""
    
    def setup_method(self):
        """Set up test environment"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_prefix = f"auth_test_{uuid.uuid4().hex[:8]}"
        
        # Initialize auth components
        self.jwt_manager = JWTManager()
        self.session_manager = SessionManager()
        self.oauth_integration = OAuthIntegration()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_lifecycle_real_implementation(self):
        """Test complete JWT token lifecycle with real services"""
        # Create test user
        test_user = {
            "user_id": f"{self.test_prefix}_user_001",
            "email": "test@example.com",
            "role": "user",
            "tier": "mid"
        }
        
        # Test token generation
        token_result = await self.jwt_manager.generate_token(
            user_data=test_user,
            expires_in_minutes=60,
            test_prefix=self.test_prefix
        )
        
        assert token_result.success is True
        assert token_result.access_token is not None
        assert token_result.refresh_token is not None
        assert token_result.expires_at > datetime.now(timezone.utc)
        
        # Test token validation
        validation_result = await self.jwt_manager.validate_token(
            token=token_result.access_token,
            test_prefix=self.test_prefix
        )
        
        assert validation_result.is_valid is True
        assert validation_result.user_id == test_user["user_id"]
        assert validation_result.role == test_user["role"]
        
        # Test token refresh
        refresh_result = await self.jwt_manager.refresh_token(
            refresh_token=token_result.refresh_token,
            test_prefix=self.test_prefix
        )
        
        assert refresh_result.success is True
        assert refresh_result.new_access_token is not None
        assert refresh_result.new_refresh_token is not None
        
        # Test token revocation
        revoke_result = await self.jwt_manager.revoke_token(
            token=token_result.access_token,
            test_prefix=self.test_prefix
        )
        
        assert revoke_result.success is True
        
        # Validate revoked token is invalid
        post_revoke_validation = await self.jwt_manager.validate_token(
            token=token_result.access_token,
            test_prefix=self.test_prefix
        )
        
        assert post_revoke_validation.is_valid is False
        assert post_revoke_validation.failure_reason == "token_revoked"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_management_with_redis(self):
        """Test session management with real Redis"""
        # Create test session
        session_data = {
            "user_id": f"{self.test_prefix}_user_002",
            "ip_address": "192.168.1.100",
            "user_agent": "Test Browser/1.0",
            "login_timestamp": datetime.now(timezone.utc),
            "permissions": ["read", "write"]
        }
        
        # Create session
        create_result = await self.session_manager.create_session(
            session_data=session_data,
            ttl_minutes=30,
            test_prefix=self.test_prefix
        )
        
        assert create_result.success is True
        assert create_result.session_id is not None
        assert create_result.session_token is not None
        
        # Retrieve session
        session_id = create_result.session_id
        retrieve_result = await self.session_manager.get_session(
            session_id=session_id,
            test_prefix=self.test_prefix
        )
        
        assert retrieve_result.success is True
        assert retrieve_result.session_data["user_id"] == session_data["user_id"]
        assert retrieve_result.session_data["ip_address"] == session_data["ip_address"]
        
        # Update session activity
        update_result = await self.session_manager.update_session_activity(
            session_id=session_id,
            activity_data={"last_action": "api_call", "timestamp": datetime.now(timezone.utc)},
            test_prefix=self.test_prefix
        )
        
        assert update_result.success is True
        
        # Test session expiration
        await asyncio.sleep(1)
        
        # Manually expire session for testing
        expire_result = await self.session_manager.expire_session(
            session_id=session_id,
            test_prefix=self.test_prefix
        )
        
        assert expire_result.success is True
        
        # Verify expired session cannot be retrieved
        expired_retrieve = await self.session_manager.get_session(
            session_id=session_id,
            test_prefix=self.test_prefix
        )
        
        assert expired_retrieve.success is False
        assert expired_retrieve.error_code == "session_expired"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])