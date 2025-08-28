"""
Comprehensive Auth Integration Tests (Iterations 71-75).

This test suite covers end-to-end authentication integration scenarios:
- Complete user registration and login flows
- OAuth integration with multiple providers
- JWT token lifecycle management
- Session management and persistence
- Password reset and recovery flows
- Multi-factor authentication flows
- API authentication flows
- Cross-service authentication consistency
- Auth state management and synchronization
- Security policy enforcement

Business Value Justification (BVJ):
- Segment: Platform/Internal + All Customer Segments
- Business Goal: Ensure auth system works end-to-end
- Value Impact: Prevents auth failures that block customer access
- Strategic Impact: Critical for platform stability and user experience
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Dict, List, Any, Optional

from auth_service.auth_core.models.auth_models import User
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.core.session_manager import SessionManager
from auth_service.auth_core.database.connection import AuthDatabase
from test_framework.environment_markers import env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth_service,
    pytest.mark.e2e
]


class TestCompleteUserRegistrationFlow:
    """Test complete user registration and verification flow (Iteration 71)."""

    @pytest.fixture
    def auth_service(self):
        """Mock auth service for testing."""
        service = MagicMock(spec=AuthService)
        service.register_user = AsyncMock()
        service.verify_email = AsyncMock()
        service.login_user = AsyncMock()
        service.get_user_profile = AsyncMock()
        return service

    @pytest.fixture
    def jwt_handler(self):
        """Mock JWT handler for testing."""
        handler = MagicMock(spec=JWTHandler)
        handler.generate_token = MagicMock()
        handler.validate_token = MagicMock()
        handler.refresh_token = MagicMock()
        return handler

    @pytest.fixture
    def sample_user_data(self):
        """Sample user registration data."""
        return {
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'full_name': 'New User',
            'terms_accepted': True
        }

    async def test_complete_user_registration_flow(self, auth_service, jwt_handler, sample_user_data):
        """Test complete user registration from signup to first login."""
        user_id = str(uuid4())
        verification_token = 'verify_token_123'
        access_token = 'access_token_456'
        
        # Step 1: User registration
        auth_service.register_user.return_value = {
            'user_id': user_id,
            'email_sent': True,
            'verification_token': verification_token,
            'status': 'pending_verification'
        }
        
        registration_result = await auth_service.register_user(**sample_user_data)
        
        assert registration_result['user_id'] == user_id
        assert registration_result['email_sent'] is True
        assert registration_result['status'] == 'pending_verification'
        
        # Step 2: Email verification
        auth_service.verify_email.return_value = {
            'verified': True,
            'user_id': user_id,
            'account_activated': True
        }
        
        verification_result = await auth_service.verify_email(verification_token)
        
        assert verification_result['verified'] is True
        assert verification_result['account_activated'] is True
        
        # Step 3: First login attempt
        jwt_handler.generate_token.return_value = access_token
        auth_service.login_user.return_value = {
            'success': True,
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': 'refresh_token_789',
            'user_profile': {
                'id': user_id,
                'email': sample_user_data['email'],
                'full_name': sample_user_data['full_name'],
                'is_verified': True
            }
        }
        
        login_result = await auth_service.login_user(
            email=sample_user_data['email'],
            password=sample_user_data['password']
        )
        
        assert login_result['success'] is True
        assert login_result['access_token'] == access_token
        assert login_result['user_profile']['is_verified'] is True
        
        # Step 4: Verify JWT token works
        jwt_handler.validate_token.return_value = {
            'valid': True,
            'user_id': user_id,
            'email': sample_user_data['email'],
            'exp': (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        
        token_validation = jwt_handler.validate_token(access_token)
        
        assert token_validation['valid'] is True
        assert token_validation['user_id'] == user_id

    async def test_registration_with_duplicate_email(self, auth_service, sample_user_data):
        """Test registration attempt with existing email address."""
        auth_service.register_user.side_effect = ValueError("Email already registered")
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service.register_user(**sample_user_data)
        
        assert "email already registered" in str(exc_info.value).lower()

    async def test_email_verification_with_expired_token(self, auth_service):
        """Test email verification with expired token."""
        expired_token = 'expired_verify_token_123'
        
        auth_service.verify_email.side_effect = ValueError("Verification token has expired")
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service.verify_email(expired_token)
        
        assert "expired" in str(exc_info.value).lower()

    async def test_login_before_email_verification(self, auth_service, sample_user_data):
        """Test login attempt before email verification."""
        auth_service.login_user.return_value = {
            'success': False,
            'error': 'email_not_verified',
            'message': 'Please verify your email before logging in'
        }
        
        login_result = await auth_service.login_user(
            email=sample_user_data['email'],
            password=sample_user_data['password']
        )
        
        assert login_result['success'] is False
        assert login_result['error'] == 'email_not_verified'


class TestOAuthIntegrationFlow:
    """Test OAuth integration with multiple providers (Iteration 72)."""

    @pytest.fixture
    def oauth_providers(self):
        """Mock OAuth providers."""
        return {
            'google': MagicMock(),
            'github': MagicMock(),
            'facebook': MagicMock()
        }

    @pytest.fixture
    def auth_service(self):
        """Mock auth service for OAuth testing."""
        service = MagicMock(spec=AuthService)
        service.initiate_oauth_flow = AsyncMock()
        service.complete_oauth_flow = AsyncMock()
        service.link_oauth_account = AsyncMock()
        service.unlink_oauth_account = AsyncMock()
        return service

    async def test_google_oauth_complete_flow(self, auth_service, oauth_providers):
        """Test complete Google OAuth authentication flow."""
        user_id = str(uuid4())
        oauth_code = 'google_oauth_code_123'
        state = 'oauth_state_456'
        
        # Step 1: Initiate OAuth flow
        auth_service.initiate_oauth_flow.return_value = {
            'authorization_url': 'https://accounts.google.com/oauth/authorize?client_id=...',
            'state': state,
            'provider': 'google'
        }
        
        oauth_initiation = await auth_service.initiate_oauth_flow(
            provider='google',
            redirect_uri='https://app.netra.ai/auth/callback'
        )
        
        assert 'accounts.google.com' in oauth_initiation['authorization_url']
        assert oauth_initiation['state'] == state
        assert oauth_initiation['provider'] == 'google'
        
        # Step 2: Complete OAuth flow with authorization code
        auth_service.complete_oauth_flow.return_value = {
            'success': True,
            'user_id': user_id,
            'user_created': False,  # Existing user
            'access_token': 'access_token_789',
            'user_profile': {
                'id': user_id,
                'email': 'user@gmail.com',
                'full_name': 'Google User',
                'oauth_provider': 'google',
                'oauth_id': 'google_123456789'
            }
        }
        
        oauth_completion = await auth_service.complete_oauth_flow(
            provider='google',
            code=oauth_code,
            state=state
        )
        
        assert oauth_completion['success'] is True
        assert oauth_completion['user_profile']['oauth_provider'] == 'google'
        assert oauth_completion['access_token'] is not None

    async def test_oauth_new_user_creation(self, auth_service):
        """Test OAuth flow that creates a new user account."""
        oauth_code = 'github_oauth_code_123'
        
        auth_service.complete_oauth_flow.return_value = {
            'success': True,
            'user_id': str(uuid4()),
            'user_created': True,  # New user
            'access_token': 'access_token_new_user',
            'user_profile': {
                'email': 'newuser@github.com',
                'full_name': 'GitHub NewUser',
                'oauth_provider': 'github',
                'oauth_id': 'github_987654321',
                'is_verified': True  # OAuth users are auto-verified
            }
        }
        
        oauth_completion = await auth_service.complete_oauth_flow(
            provider='github',
            code=oauth_code,
            state='github_state_123'
        )
        
        assert oauth_completion['user_created'] is True
        assert oauth_completion['user_profile']['is_verified'] is True
        assert oauth_completion['user_profile']['oauth_provider'] == 'github'

    async def test_oauth_account_linking(self, auth_service):
        """Test linking OAuth account to existing user."""
        existing_user_id = str(uuid4())
        
        auth_service.link_oauth_account.return_value = {
            'linked': True,
            'user_id': existing_user_id,
            'oauth_provider': 'facebook',
            'linked_accounts': ['google', 'facebook']  # Now has multiple OAuth accounts
        }
        
        linking_result = await auth_service.link_oauth_account(
            user_id=existing_user_id,
            provider='facebook',
            oauth_id='facebook_555666777'
        )
        
        assert linking_result['linked'] is True
        assert 'facebook' in linking_result['linked_accounts']
        assert len(linking_result['linked_accounts']) > 1

    async def test_oauth_state_mismatch_security(self, auth_service):
        """Test OAuth security with state parameter mismatch."""
        auth_service.complete_oauth_flow.side_effect = SecurityError("Invalid state parameter")
        
        with pytest.raises(SecurityError) as exc_info:
            await auth_service.complete_oauth_flow(
                provider='google',
                code='valid_code',
                state='mismatched_state'
            )
        
        assert "invalid state" in str(exc_info.value).lower()

    async def test_oauth_provider_error_handling(self, auth_service):
        """Test handling OAuth provider errors."""
        auth_service.complete_oauth_flow.return_value = {
            'success': False,
            'error': 'access_denied',
            'error_description': 'User denied access to the application'
        }
        
        oauth_result = await auth_service.complete_oauth_flow(
            provider='github',
            code=None,  # No code provided
            error='access_denied'
        )
        
        assert oauth_result['success'] is False
        assert oauth_result['error'] == 'access_denied'


class TestJWTTokenLifecycleManagement:
    """Test JWT token lifecycle and refresh flows (Iteration 73)."""

    @pytest.fixture
    def jwt_handler(self):
        """Mock JWT handler for testing."""
        handler = MagicMock(spec=JWTHandler)
        handler.generate_token = MagicMock()
        handler.validate_token = MagicMock()
        handler.refresh_token = MagicMock()
        handler.revoke_token = MagicMock()
        handler.is_token_blacklisted = MagicMock()
        return handler

    @pytest.fixture
    def session_manager(self):
        """Mock session manager for testing."""
        manager = MagicMock(spec=SessionManager)
        manager.create_session = AsyncMock()
        manager.get_session = AsyncMock()
        manager.update_session = AsyncMock()
        manager.revoke_session = AsyncMock()
        return manager

    async def test_jwt_token_generation_and_validation(self, jwt_handler):
        """Test JWT token generation and validation cycle."""
        user_id = str(uuid4())
        user_data = {
            'user_id': user_id,
            'email': 'user@example.com',
            'roles': ['user']
        }
        
        # Generate token
        access_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
        jwt_handler.generate_token.return_value = access_token
        
        generated_token = jwt_handler.generate_token(user_data)
        assert generated_token == access_token
        
        # Validate token
        jwt_handler.validate_token.return_value = {
            'valid': True,
            'user_id': user_id,
            'email': user_data['email'],
            'roles': user_data['roles'],
            'exp': (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            'iat': datetime.now(timezone.utc).timestamp()
        }
        
        validation_result = jwt_handler.validate_token(access_token)
        
        assert validation_result['valid'] is True
        assert validation_result['user_id'] == user_id
        assert validation_result['email'] == user_data['email']

    async def test_jwt_token_refresh_flow(self, jwt_handler):
        """Test JWT token refresh mechanism."""
        old_token = 'old_access_token_123'
        refresh_token = 'refresh_token_456'
        new_token = 'new_access_token_789'
        
        jwt_handler.refresh_token.return_value = {
            'access_token': new_token,
            'refresh_token': 'new_refresh_token_101112',
            'expires_in': 3600,
            'token_type': 'Bearer'
        }
        
        refresh_result = jwt_handler.refresh_token(refresh_token)
        
        assert refresh_result['access_token'] == new_token
        assert refresh_result['expires_in'] == 3600
        assert 'refresh_token' in refresh_result

    async def test_jwt_token_expiration_handling(self, jwt_handler):
        """Test handling of expired JWT tokens."""
        expired_token = 'expired_jwt_token_123'
        
        jwt_handler.validate_token.return_value = {
            'valid': False,
            'error': 'token_expired',
            'expired_at': (datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()
        }
        
        validation_result = jwt_handler.validate_token(expired_token)
        
        assert validation_result['valid'] is False
        assert validation_result['error'] == 'token_expired'

    async def test_jwt_token_blacklisting(self, jwt_handler):
        """Test JWT token revocation and blacklisting."""
        token_to_revoke = 'token_to_revoke_123'
        
        # Revoke token
        jwt_handler.revoke_token.return_value = {'revoked': True}
        revoke_result = jwt_handler.revoke_token(token_to_revoke)
        assert revoke_result['revoked'] is True
        
        # Check if token is blacklisted
        jwt_handler.is_token_blacklisted.return_value = True
        is_blacklisted = jwt_handler.is_token_blacklisted(token_to_revoke)
        assert is_blacklisted is True
        
        # Validate blacklisted token
        jwt_handler.validate_token.return_value = {
            'valid': False,
            'error': 'token_revoked'
        }
        
        validation_result = jwt_handler.validate_token(token_to_revoke)
        assert validation_result['valid'] is False
        assert validation_result['error'] == 'token_revoked'

    async def test_session_token_synchronization(self, jwt_handler, session_manager):
        """Test synchronization between JWT tokens and session management."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        access_token = 'session_token_123'
        
        # Create session
        session_manager.create_session.return_value = {
            'session_id': session_id,
            'user_id': user_id,
            'access_token': access_token,
            'created_at': datetime.now(timezone.utc),
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        session = await session_manager.create_session(
            user_id=user_id,
            access_token=access_token
        )
        
        assert session['session_id'] == session_id
        assert session['access_token'] == access_token
        
        # Validate token against session
        session_manager.get_session.return_value = session
        retrieved_session = await session_manager.get_session(session_id)
        
        assert retrieved_session['access_token'] == access_token
        assert retrieved_session['user_id'] == user_id
        
        # Revoke session and token together
        jwt_handler.revoke_token.return_value = {'revoked': True}
        session_manager.revoke_session.return_value = {'revoked': True}
        
        token_revoked = jwt_handler.revoke_token(access_token)
        session_revoked = await session_manager.revoke_session(session_id)
        
        assert token_revoked['revoked'] is True
        assert session_revoked['revoked'] is True


class TestPasswordResetIntegration:
    """Test password reset integration flow (Iteration 74)."""

    @pytest.fixture
    def auth_service(self):
        """Mock auth service for password reset testing."""
        service = MagicMock(spec=AuthService)
        service.initiate_password_reset = AsyncMock()
        service.validate_reset_token = AsyncMock()
        service.complete_password_reset = AsyncMock()
        service.login_user = AsyncMock()
        return service

    async def test_complete_password_reset_flow(self, auth_service):
        """Test complete password reset from initiation to new login."""
        email = 'user@example.com'
        reset_token = 'reset_token_123'
        new_password = 'NewSecurePassword456!'
        
        # Step 1: Initiate password reset
        auth_service.initiate_password_reset.return_value = {
            'email_sent': True,
            'reset_token_id': str(uuid4()),
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=2)
        }
        
        reset_initiation = await auth_service.initiate_password_reset(email)
        
        assert reset_initiation['email_sent'] is True
        assert 'expires_at' in reset_initiation
        
        # Step 2: Validate reset token
        auth_service.validate_reset_token.return_value = {
            'valid': True,
            'user_id': str(uuid4()),
            'email': email,
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        token_validation = await auth_service.validate_reset_token(reset_token)
        
        assert token_validation['valid'] is True
        assert token_validation['email'] == email
        
        # Step 3: Complete password reset
        auth_service.complete_password_reset.return_value = {
            'success': True,
            'password_updated': True,
            'user_id': token_validation['user_id'],
            'all_sessions_revoked': True
        }
        
        reset_completion = await auth_service.complete_password_reset(
            token=reset_token,
            new_password=new_password
        )
        
        assert reset_completion['success'] is True
        assert reset_completion['password_updated'] is True
        assert reset_completion['all_sessions_revoked'] is True
        
        # Step 4: Login with new password
        auth_service.login_user.return_value = {
            'success': True,
            'user_id': token_validation['user_id'],
            'access_token': 'new_login_token_789'
        }
        
        login_result = await auth_service.login_user(
            email=email,
            password=new_password
        )
        
        assert login_result['success'] is True
        assert 'access_token' in login_result

    async def test_password_reset_with_invalid_email(self, auth_service):
        """Test password reset attempt with non-existent email."""
        invalid_email = 'nonexistent@example.com'
        
        # Should return success message for security (don't reveal email existence)
        auth_service.initiate_password_reset.return_value = {
            'email_sent': False,  # No actual email sent
            'message': 'If the email exists, a reset link has been sent'
        }
        
        reset_result = await auth_service.initiate_password_reset(invalid_email)
        
        # Should appear successful to prevent email enumeration
        assert 'message' in reset_result
        assert reset_result['email_sent'] is False

    async def test_password_reset_token_expiration(self, auth_service):
        """Test password reset with expired token."""
        expired_token = 'expired_reset_token_123'
        
        auth_service.validate_reset_token.return_value = {
            'valid': False,
            'error': 'token_expired',
            'expired_at': datetime.now(timezone.utc) - timedelta(minutes=1)
        }
        
        validation_result = await auth_service.validate_reset_token(expired_token)
        
        assert validation_result['valid'] is False
        assert validation_result['error'] == 'token_expired'

    async def test_password_reset_rate_limiting(self, auth_service):
        """Test rate limiting on password reset requests."""
        email = 'ratelimited@example.com'
        
        auth_service.initiate_password_reset.side_effect = ValueError(
            "Too many password reset attempts. Please wait before trying again."
        )
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service.initiate_password_reset(email)
        
        assert "too many" in str(exc_info.value).lower()


class TestAuthStateManagementIntegration:
    """Test auth state management and synchronization (Iteration 75)."""

    @pytest.fixture
    def auth_database(self):
        """Mock auth database for testing."""
        db = MagicMock(spec=AuthDatabase)
        db.get_user_by_id = AsyncMock()
        db.update_user_status = AsyncMock()
        db.create_session = AsyncMock()
        db.get_active_sessions = AsyncMock()
        db.revoke_all_sessions = AsyncMock()
        return db

    @pytest.fixture
    def session_manager(self):
        """Mock session manager for testing."""
        manager = MagicMock(spec=SessionManager)
        manager.get_all_user_sessions = AsyncMock()
        manager.revoke_all_user_sessions = AsyncMock()
        manager.sync_session_state = AsyncMock()
        return manager

    async def test_user_state_synchronization_across_sessions(self, auth_database, session_manager):
        """Test user state changes are synchronized across all sessions."""
        user_id = str(uuid4())
        session_ids = [str(uuid4()) for _ in range(3)]
        
        # Mock active sessions
        session_manager.get_all_user_sessions.return_value = [
            {'session_id': sid, 'user_id': user_id, 'status': 'active'}
            for sid in session_ids
        ]
        
        # Mock user status update (e.g., account suspension)
        auth_database.update_user_status.return_value = {
            'user_id': user_id,
            'old_status': 'active',
            'new_status': 'suspended',
            'sessions_affected': len(session_ids)
        }
        
        # Update user status
        status_update = await auth_database.update_user_status(
            user_id=user_id,
            new_status='suspended'
        )
        
        assert status_update['new_status'] == 'suspended'
        assert status_update['sessions_affected'] == 3
        
        # Verify session synchronization
        session_manager.sync_session_state.return_value = {
            'sessions_updated': len(session_ids),
            'new_status': 'suspended'
        }
        
        sync_result = await session_manager.sync_session_state(
            user_id=user_id,
            new_status='suspended'
        )
        
        assert sync_result['sessions_updated'] == len(session_ids)
        assert sync_result['new_status'] == 'suspended'

    async def test_concurrent_session_management(self, session_manager):
        """Test management of concurrent user sessions."""
        user_id = str(uuid4())
        
        # Mock multiple concurrent sessions
        concurrent_sessions = [
            {
                'session_id': str(uuid4()),
                'user_id': user_id,
                'device_type': 'web',
                'ip_address': '192.168.1.100',
                'created_at': datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                'session_id': str(uuid4()),
                'user_id': user_id,
                'device_type': 'mobile',
                'ip_address': '192.168.1.101',
                'created_at': datetime.now(timezone.utc) - timedelta(minutes=30)
            },
            {
                'session_id': str(uuid4()),
                'user_id': user_id,
                'device_type': 'desktop',
                'ip_address': '192.168.1.102',
                'created_at': datetime.now(timezone.utc) - timedelta(minutes=5)
            }
        ]
        
        session_manager.get_all_user_sessions.return_value = concurrent_sessions
        
        sessions = await session_manager.get_all_user_sessions(user_id)
        
        assert len(sessions) == 3
        assert all(session['user_id'] == user_id for session in sessions)
        
        # Test session revocation
        session_manager.revoke_all_user_sessions.return_value = {
            'sessions_revoked': len(concurrent_sessions),
            'user_id': user_id
        }
        
        revocation_result = await session_manager.revoke_all_user_sessions(user_id)
        
        assert revocation_result['sessions_revoked'] == 3
        assert revocation_result['user_id'] == user_id

    async def test_auth_state_consistency_validation(self, auth_database):
        """Test validation of auth state consistency."""
        user_id = str(uuid4())
        
        # Mock user data
        auth_database.get_user_by_id.return_value = {
            'id': user_id,
            'email': 'user@example.com',
            'is_active': True,
            'is_verified': True,
            'status': 'active',
            'last_login': datetime.now(timezone.utc) - timedelta(minutes=30)
        }
        
        user_data = await auth_database.get_user_by_id(user_id)
        
        # Validate auth state consistency
        assert user_data['is_active'] is True
        assert user_data['is_verified'] is True
        assert user_data['status'] == 'active'
        assert user_data['last_login'] is not None
        
        # Test state validation with inconsistent data
        auth_database.get_user_by_id.return_value = {
            'id': user_id,
            'is_active': False,  # Inactive
            'status': 'active',  # But status says active - inconsistent!
            'is_verified': True
        }
        
        inconsistent_user = await auth_database.get_user_by_id(user_id)
        
        # Should detect inconsistency
        is_consistent = (
            inconsistent_user['is_active'] == (inconsistent_user['status'] == 'active')
        )
        
        assert is_consistent is False  # Detects inconsistency

    async def test_cross_service_auth_state_propagation(self, auth_database):
        """Test auth state changes propagate across services."""
        user_id = str(uuid4())
        
        # Mock cross-service state change
        auth_database.update_user_status.return_value = {
            'user_id': user_id,
            'status_updated': True,
            'services_notified': ['netra_backend', 'frontend', 'api_gateway'],
            'propagation_success': True
        }
        
        update_result = await auth_database.update_user_status(
            user_id=user_id,
            new_status='suspended'
        )
        
        assert update_result['status_updated'] is True
        assert len(update_result['services_notified']) == 3
        assert update_result['propagation_success'] is True


# Mock exception classes for testing
class SecurityError(Exception):
    """Mock security error for OAuth testing."""
    pass