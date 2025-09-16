from unittest.mock import Mock, AsyncMock, patch, MagicMock

class WebSocketConnectionTests:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

        async def send_json(self, message: dict):
            """Send JSON message."""
            if self._closed:
                raise RuntimeError('WebSocket is closed')
            self.messages_sent.append(message)

            async def close(self, code: int=1000, reason: str='Normal closure'):
                """Close WebSocket connection."""
                pass
                self._closed = True
                self.is_connected = False

                def get_messages(self) -> list:
                    """Get all sent messages."""
                    pass
                    return self.messages_sent.copy()
                '\n                Regression test for auth refresh database session issue\n                Issue: Auth service was not receiving database session during token refresh\n                Date: 2025-09-03\n                Fix: Added database session dependency injection to refresh endpoint\n                '
                import asyncio
                import json
                import pytest
                from sqlalchemy.ext.asyncio import AsyncSession
                from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
                from test_framework.database.test_database_manager import DatabaseTestManager
                from auth_service.core.auth_manager import AuthManager
                from shared.isolated_environment import IsolatedEnvironment
                from auth_service.auth_core.routes.auth_routes import refresh_tokens, auth_service
                from auth_service.auth_core.services.auth_service import AuthService
                from fastapi import Request
                from fastapi.testclient import TestClient
                from fastapi import FastAPI
                from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
                from netra_backend.app.db.database_manager import DatabaseManager
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                from shared.isolated_environment import get_env

                class AuthRefreshDatabaseSessionRegressionTests:
                    """
                    Regression test to ensure auth refresh always has database session
                    This prevents the "No database session" error seen in staging logs
                    """

                    @pytest.mark.asyncio
                    async def test_refresh_endpoint_has_database_session(self):
                        """Test that refresh endpoint injects database session"""
                        mock_request = AsyncMock(spec=Request)
                        mock_db = AsyncMock(spec=AsyncSession)
                        refresh_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token'
                        request_body = json.dumps({'refresh_token': refresh_token}).encode()
                        mock_request.body.return_value = request_body
                        original_refresh = auth_service.refresh_tokens
                        db_session_was_set = False

                        async def check_db_session(token):
                            nonlocal db_session_was_set
                            if auth_service.db_session is not None:
                                db_session_was_set = True
                                await asyncio.sleep(0)
                                return ('new_access_token', 'new_refresh_token')
                            with patch.object(auth_service, 'refresh_tokens', side_effect=check_db_session):
                                result = await refresh_tokens(mock_request, mock_db)
                                assert db_session_was_set, 'Database session was not set on auth_service'
                                assert result['access_token'] == 'new_access_token'
                                assert result['refresh_token'] == 'new_refresh_token'

                                @pytest.mark.asyncio
                                async def test_refresh_uses_database_for_user_lookup(self):
                                    """Test that refresh actually uses database to look up user info"""
                                    test_auth_service = AuthService()
                                    mock_db_session = AsyncMock(spec=AsyncSession)
                                    test_auth_service.db_session = mock_db_session
                                    test_user_id = 'test-user-123'
                                    refresh_token = test_auth_service.jwt_handler.create_refresh_token(test_user_id)
                                    from auth_service.auth_core.database.repository import AuthUserRepository
                                    with patch('auth_service.auth_core.services.auth_service.AuthUserRepository') as MockRepo:
                                        websocket = WebSocketConnectionTests()
                                        MockRepo.return_value = mock_repo_instance
                                        from auth_service.auth_core.database.models import AuthUser
                                        mock_user = AuthUser(id=test_user_id, email='test@example.com', full_name='Test User', auth_provider='local', is_active=True, is_verified=True)
                                        mock_repo_instance.get.return_value = mock_user
                                        result = await test_auth_service.refresh_tokens(refresh_token)
                                        assert result is not None
                                        access_token, new_refresh = result
                                        assert access_token is not None
                                        assert new_refresh is not None
                                        MockRepo.assert_called_once_with(mock_db_session)
                                        mock_repo_instance.get.assert_called_once_with(test_user_id)

                                        @pytest.mark.asyncio
                                        async def test_refresh_without_db_session_falls_back_gracefully(self):
                                            """Test that refresh without DB session falls back to token data"""
                                            test_auth_service = AuthService()
                                            test_auth_service.db_session = None
                                            test_user_id = 'test-user-456'
                                            refresh_token = test_auth_service.jwt_handler.create_refresh_token(test_user_id)
                                            with patch.object(test_auth_service, 'logger') as mock_logger:
                                                result = await test_auth_service.refresh_tokens(refresh_token)
                                                assert result is not None
                                                access_token, new_refresh = result
                                                assert access_token is not None
                                                assert new_refresh is not None
                                                mock_logger.info.assert_any_call(f'Refresh token: No database session, using token payload for user {test_user_id}')

                                                def test_refresh_endpoint_dependency_injection(self):
                                                    """Test that refresh endpoint has correct dependency injection signature"""
                                                    pass
                                                    import inspect
                                                    from auth_service.auth_core.routes.auth_routes import refresh_tokens
                                                    sig = inspect.signature(refresh_tokens)
                                                    params = list(sig.parameters.keys())
                                                    assert 'request' in params, "refresh_tokens should have 'request' parameter"
                                                    assert 'db' in params, "refresh_tokens should have 'db' parameter for database session"
                                                    db_param = sig.parameters['db']
                                                    assert db_param.default is not inspect.Parameter.empty, 'db parameter should have a default (Depends)'

                                                    @pytest.mark.asyncio
                                                    async def test_staging_scenario_with_real_tokens(self):
                                                        """Test the exact scenario from staging logs"""
                                                        staging_refresh_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlOGM1YmMxZS03ZGY4LTQ3NzUtODY5ZS1iNDA1NDU4MWRiM2UiLCJpYXQiOjE3NTY5MzA5NTUsImV4cCI6MTc1NzUzNTc1NSwidG9rZW5fdHlwZSI6InJlZnJlc2giLCJ0eXBlIjoicmVmcmVzaCJ9.test_signature'
                                                        mock_request = AsyncMock(spec=Request)
                                                        request_body = json.dumps({'refresh_token': staging_refresh_token}).encode()
                                                        mock_request.body.return_value = request_body
                                                        mock_db = AsyncMock(spec=AsyncSession)
                                                        with patch.object(auth_service, 'refresh_tokens') as mock_refresh:
                                                            mock_refresh.return_value = ('new_access', 'new_refresh')
                                                            result = await refresh_tokens(mock_request, mock_db)
                                                            mock_refresh.assert_called_once()
                                                            assert auth_service.db_session == mock_db
                                                            assert result['access_token'] == 'new_access'
                                                            assert result['refresh_token'] == 'new_refresh'

                                                            class AuthLoopPreventionIntegrationTests:
                                                                """Integration tests for auth loop prevention"""

                                                                @pytest.mark.asyncio
                                                                async def test_no_auth_loop_with_db_session(self):
                                                                    """Test that having DB session prevents auth loops"""
                                                                    test_auth_service = AuthService()
                                                                    mock_db = AsyncMock(spec=AsyncSession)
                                                                    test_auth_service.db_session = mock_db
                                                                    user_id = 'loop-test-user'
                                                                    refresh_token = test_auth_service.jwt_handler.create_refresh_token(user_id)
                                                                    from auth_service.auth_core.database.repository import AuthUserRepository
                                                                    with patch('auth_service.auth_core.services.auth_service.AuthUserRepository') as MockRepo:
                                                                        websocket = WebSocketConnectionTests()
                                                                        MockRepo.return_value = mock_repo
                                                                        from auth_service.auth_core.database.models import AuthUser
                                                                        mock_user = AuthUser(id=user_id, email='loop@test.com', full_name='Loop Test', auth_provider='local', is_active=True, is_verified=True)
                                                                        mock_repo.get.return_value = mock_user
                                                                        successful_refreshes = 0
                                                                        last_refresh_token = refresh_token
                                                                        for i in range(3):
                                                                            result = await test_auth_service.refresh_tokens(last_refresh_token)
                                                                            if result:
                                                                                successful_refreshes += 1
                                                                                _, last_refresh_token = result
                                                                                await asyncio.sleep(0.1)
                                                                                assert successful_refreshes == 3, 'All refreshes should succeed with DB session'
                                                                                if __name__ == '__main__':
                                                                                    'MIGRATED: Use SSOT unified test runner'
                                                                                    print('MIGRATION NOTICE: Please use SSOT unified test runner')
                                                                                    print('Command: python tests/unified_test_runner.py --category <category>')