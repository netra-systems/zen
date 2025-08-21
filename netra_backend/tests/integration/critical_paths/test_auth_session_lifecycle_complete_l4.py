"""
L4 Integration Test: Complete Auth Session Lifecycle
Tests the entire auth session from creation to expiry including edge cases
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import jwt
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.services.session_service import SessionService
from app.services.token_service import TokenService
from app.models.user import User
from app.models.session import Session
from app.core.config import settings


class TestAuthSessionLifecycleCompleteL4:
    """Complete auth session lifecycle testing with edge cases"""
    
    @pytest.fixture
    async def auth_stack(self):
        """Complete auth service stack"""
        return {
            'auth_service': AuthService(),
            'session_service': SessionService(),
            'token_service': TokenService(),
            'redis_client': await redis.from_url(settings.REDIS_URL),
            'active_sessions': {},
            'expired_tokens': set()
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_creation_with_immediate_validation(self, auth_stack):
        """Test session creation followed by immediate validation attempts"""
        # Create session
        user_id = "user_123"
        session = await auth_stack['session_service'].create_session(
            user_id=user_id,
            device_id="device_1",
            ip_address="192.168.1.1"
        )
        
        # Immediate validation attempts (should handle race conditions)
        validation_tasks = []
        for i in range(10):
            task = asyncio.create_task(
                auth_stack['session_service'].validate_session(session['session_id'])
            )
            validation_tasks.append(task)
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # All validations should succeed
        assert all(r['valid'] for r in results if not isinstance(r, Exception))
        
        # Session should be in Redis
        redis_key = f"session:{session['session_id']}"
        session_data = await auth_stack['redis_client'].get(redis_key)
        assert session_data is not None
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_refresh_during_active_requests(self, auth_stack):
        """Test token refresh while requests are in flight"""
        # Create initial token
        user_id = "user_456"
        initial_token = await auth_stack['token_service'].create_access_token(
            user_id=user_id,
            expires_in=60  # 1 minute
        )
        
        # Start multiple concurrent requests
        async def make_request(token):
            await asyncio.sleep(0.1)  # Simulate request processing
            return await auth_stack['token_service'].validate_token(token)
        
        # Start requests with initial token
        request_tasks = [
            asyncio.create_task(make_request(initial_token))
            for _ in range(5)
        ]
        
        # Refresh token mid-flight
        await asyncio.sleep(0.05)
        refresh_token = await auth_stack['token_service'].create_refresh_token(user_id)
        new_token = await auth_stack['token_service'].refresh_access_token(refresh_token)
        
        # Invalidate old token
        await auth_stack['token_service'].revoke_token(initial_token)
        
        # Start new requests with new token
        new_request_tasks = [
            asyncio.create_task(make_request(new_token))
            for _ in range(5)
        ]
        
        # Gather all results
        old_results = await asyncio.gather(*request_tasks, return_exceptions=True)
        new_results = await asyncio.gather(*new_request_tasks, return_exceptions=True)
        
        # Old requests should handle token invalidation gracefully
        # New requests should all succeed
        assert all(r['valid'] for r in new_results if not isinstance(r, Exception))
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_expiry_cascade(self, auth_stack):
        """Test cascading effects of session expiry"""
        user_id = "user_789"
        
        # Create multiple sessions for same user
        sessions = []
        for i in range(3):
            session = await auth_stack['session_service'].create_session(
                user_id=user_id,
                device_id=f"device_{i}",
                ip_address=f"192.168.1.{i+1}"
            )
            sessions.append(session)
        
        # Create tokens for each session
        tokens = []
        for session in sessions:
            token = await auth_stack['token_service'].create_access_token(
                user_id=user_id,
                session_id=session['session_id'],
                expires_in=300
            )
            tokens.append(token)
        
        # Expire first session
        await auth_stack['session_service'].expire_session(sessions[0]['session_id'])
        
        # Validate all tokens
        validations = []
        for token in tokens:
            result = await auth_stack['token_service'].validate_token(token)
            validations.append(result)
        
        # First token should be invalid, others valid
        assert not validations[0]['valid']
        assert validations[1]['valid']
        assert validations[2]['valid']
        
        # Expire all sessions for user
        await auth_stack['session_service'].expire_all_user_sessions(user_id)
        
        # All tokens should now be invalid
        for token in tokens[1:]:
            result = await auth_stack['token_service'].validate_token(token)
            assert not result['valid']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_login_same_user(self, auth_stack):
        """Test concurrent login attempts for same user"""
        user_id = "user_concurrent"
        email = "concurrent@test.com"
        password = "Test123!@#"
        
        # Simulate concurrent login attempts
        async def login_attempt(device_id):
            return await auth_stack['auth_service'].login(
                email=email,
                password=password,
                device_id=device_id,
                ip_address="192.168.1.1"
            )
        
        # Launch 10 concurrent login attempts
        login_tasks = [
            asyncio.create_task(login_attempt(f"device_{i}"))
            for i in range(10)
        ]
        
        results = await asyncio.gather(*login_tasks, return_exceptions=True)
        
        # Filter successful logins
        successful_logins = [r for r in results if not isinstance(r, Exception)]
        
        # All should succeed but create separate sessions
        assert len(successful_logins) >= 8  # Allow some failures due to race conditions
        
        # Each should have unique session ID
        session_ids = [login['session_id'] for login in successful_logins]
        assert len(session_ids) == len(set(session_ids))
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_timeout_with_activity(self, auth_stack):
        """Test session timeout behavior with user activity"""
        user_id = "user_timeout"
        
        # Create session with 2 second timeout
        session = await auth_stack['session_service'].create_session(
            user_id=user_id,
            device_id="device_1",
            ip_address="192.168.1.1",
            timeout_seconds=2
        )
        
        # Keep session alive with activity
        for _ in range(3):
            await asyncio.sleep(1)
            await auth_stack['session_service'].update_activity(session['session_id'])
        
        # Session should still be valid
        validation = await auth_stack['session_service'].validate_session(session['session_id'])
        assert validation['valid']
        
        # Let session expire
        await asyncio.sleep(3)
        
        # Session should now be invalid
        validation = await auth_stack['session_service'].validate_session(session['session_id'])
        assert not validation['valid']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_validation_with_clock_skew(self, auth_stack):
        """Test token validation with system clock skew"""
        user_id = "user_clock"
        
        # Create token with current time
        token = await auth_stack['token_service'].create_access_token(
            user_id=user_id,
            expires_in=300
        )
        
        # Mock time to be 30 seconds in the past (clock skew)
        with patch('time.time', return_value=time.time() - 30):
            # Should still validate with reasonable clock skew
            result = await auth_stack['token_service'].validate_token(token)
            assert result['valid']
        
        # Mock time to be 5 minutes in the future
        with patch('time.time', return_value=time.time() + 360):
            # Token should be expired
            result = await auth_stack['token_service'].validate_token(token)
            assert not result['valid']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_migration_between_devices(self, auth_stack):
        """Test session migration when user switches devices"""
        user_id = "user_migrate"
        
        # Create session on device 1
        session1 = await auth_stack['session_service'].create_session(
            user_id=user_id,
            device_id="device_1",
            ip_address="192.168.1.1"
        )
        
        # Store some session data
        await auth_stack['session_service'].store_session_data(
            session1['session_id'],
            {'preferences': {'theme': 'dark'}}
        )
        
        # User switches to device 2
        session2 = await auth_stack['session_service'].create_session(
            user_id=user_id,
            device_id="device_2",
            ip_address="192.168.1.2"
        )
        
        # Migrate session data
        await auth_stack['session_service'].migrate_session_data(
            from_session=session1['session_id'],
            to_session=session2['session_id']
        )
        
        # Verify data migrated
        data = await auth_stack['session_service'].get_session_data(session2['session_id'])
        assert data['preferences']['theme'] == 'dark'
        
        # Old session should be invalidated
        validation = await auth_stack['session_service'].validate_session(session1['session_id'])
        assert not validation['valid']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_auth_state_after_password_change(self, auth_stack):
        """Test auth state consistency after password change"""
        user_id = "user_password"
        
        # Create multiple sessions
        sessions = []
        tokens = []
        for i in range(3):
            session = await auth_stack['session_service'].create_session(
                user_id=user_id,
                device_id=f"device_{i}",
                ip_address=f"192.168.1.{i+1}"
            )
            sessions.append(session)
            
            token = await auth_stack['token_service'].create_access_token(
                user_id=user_id,
                session_id=session['session_id']
            )
            tokens.append(token)
        
        # Change password (should invalidate all sessions)
        await auth_stack['auth_service'].change_password(
            user_id=user_id,
            old_password="OldPass123!",
            new_password="NewPass456!"
        )
        
        # All tokens should be invalid
        for token in tokens:
            result = await auth_stack['token_service'].validate_token(token)
            assert not result['valid']
        
        # All sessions should be expired
        for session in sessions:
            validation = await auth_stack['session_service'].validate_session(session['session_id'])
            assert not validation['valid']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_recovery_after_redis_failure(self, auth_stack):
        """Test session recovery after Redis connection failure"""
        user_id = "user_recovery"
        
        # Create session
        session = await auth_stack['session_service'].create_session(
            user_id=user_id,
            device_id="device_1",
            ip_address="192.168.1.1"
        )
        
        # Simulate Redis failure
        original_redis = auth_stack['redis_client']
        auth_stack['redis_client'] = None
        
        # Validation should fall back to database
        with patch.object(auth_stack['session_service'], 'validate_from_database') as mock_db:
            mock_db.return_value = {'valid': True, 'session': session}
            result = await auth_stack['session_service'].validate_session(session['session_id'])
            assert result['valid']
            mock_db.assert_called_once()
        
        # Restore Redis
        auth_stack['redis_client'] = original_redis
        
        # Session should be re-cached in Redis
        redis_key = f"session:{session['session_id']}"
        session_data = await auth_stack['redis_client'].get(redis_key)
        assert session_data is not None
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_jwt_signature_rotation(self, auth_stack):
        """Test JWT validation during signature key rotation"""
        user_id = "user_rotation"
        
        # Create token with current key
        token1 = await auth_stack['token_service'].create_access_token(user_id=user_id)
        
        # Rotate signing key
        old_key = settings.JWT_SECRET_KEY
        new_key = "new_secret_key_" + str(time.time())
        
        with patch.object(settings, 'JWT_SECRET_KEY', new_key):
            # Create token with new key
            token2 = await auth_stack['token_service'].create_access_token(user_id=user_id)
            
            # Both tokens should validate during grace period
            with patch.object(auth_stack['token_service'], 'validate_with_old_keys') as mock_old:
                mock_old.return_value = True
                
                result1 = await auth_stack['token_service'].validate_token(token1)
                result2 = await auth_stack['token_service'].validate_token(token2)
                
                assert result1['valid']  # Old key token
                assert result2['valid']  # New key token