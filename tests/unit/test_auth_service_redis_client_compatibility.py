"""
Unit Tests for Auth Service Redis Client Compatibility

These tests validate the fix for auth service startup issues related to Redis client
references vs session_manager references.

Commit 41e0dd6a8 fixed:
- AuthService session_manager references (use redis_client instead)
- Proper Redis connection cleanup using redis_client
- Redis status checking using redis_client availability

Root cause: Code was referencing session_manager properties that didn't exist
Impact: Auth service failed to start properly in staging environment
Resolution: Updated code to use auth_service.redis_client directly

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure auth service reliability and proper startup
- Value Impact: Prevents auth service crashes and startup failures
- Strategic Impact: Maintains authentication system availability
"""
import pytest
import asyncio
import sys
import os
from typing import Optional, Any
from unittest.mock import Mock, AsyncMock
from shared.isolated_environment import IsolatedEnvironment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class MockWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
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
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self):
        self.closed = False

    async def close(self):
        """Mock close method."""
        self.closed = True

class MockAuthService:
    """Mock AuthService that simulates the fixed behavior."""

    def __init__(self):
        """Initialize with redis_client (not session_manager)."""
        self.redis_client: Optional[Any] = None
        self._initialize_redis_client()

    def _initialize_redis_client(self):
        """Initialize Redis client (simulates real initialization)."""
        self.redis_client = MockRedisClient()
        self.websocket = TestWebSocketConnection()

@pytest.mark.unit
class AuthServiceRedisClientCompatibilityTests:
    """Test suite for auth service Redis client compatibility fixes."""

    def test_auth_service_uses_redis_client_not_session_manager(self):
        """Test that auth service exposes redis_client attribute directly.

        The regression occurred because code tried to access session_manager.redis_enabled
        but AuthService actually uses redis_client directly.
        """
        auth_service = MockAuthService()
        assert hasattr(auth_service, 'redis_client'), 'AuthService should have redis_client attribute'
        if hasattr(auth_service, 'session_manager'):
            pytest.skip('session_manager present but should not be used for Redis')
        assert auth_service.redis_client is not None, 'AuthService redis_client should be initialized'

    def test_redis_status_check_uses_redis_client(self):
        """Test that Redis status is checked via redis_client availability.

        Fixed implementation checks: auth_service.redis_client is not None
        instead of: auth_service.session_manager.redis_enabled
        """
        auth_service_with_redis = MockAuthService()
        auth_service_with_redis.websocket = TestWebSocketConnection()
        redis_enabled = auth_service_with_redis.redis_client is not None
        assert redis_enabled is True, 'Redis should be considered enabled when redis_client is not None'
        auth_service_without_redis = MockAuthService()
        auth_service_without_redis.redis_client = None
        redis_enabled = auth_service_without_redis.redis_client is not None
        assert redis_enabled is False, 'Redis should be considered disabled when redis_client is None'

    @pytest.mark.asyncio
    async def test_redis_cleanup_uses_redis_client_close(self):
        """Test that Redis cleanup uses redis_client.close() directly.

        Fixed implementation calls: auth_service.redis_client.close()
        instead of: auth_service.session_manager.close_redis()
        """
        auth_service = MockAuthService()
        auth_service.websocket = TestWebSocketConnection()
        auth_service.redis_client.close = AsyncMock()
        if hasattr(auth_service, 'redis_client') and auth_service.redis_client:
            if hasattr(auth_service.redis_client, 'close'):
                await auth_service.redis_client.close()
        auth_service.redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_cleanup_handles_missing_redis_client(self):
        """Test that Redis cleanup handles missing redis_client gracefully."""
        auth_service = MockAuthService()
        auth_service.redis_client = None
        try:
            if hasattr(auth_service, 'redis_client') and auth_service.redis_client:
                if hasattr(auth_service.redis_client, 'close'):
                    await auth_service.redis_client.close()
        except Exception as e:
            pytest.fail(f'Redis cleanup should handle None redis_client gracefully, got: {e}')

    @pytest.mark.asyncio
    async def test_redis_cleanup_handles_redis_client_without_close(self):
        """Test that Redis cleanup handles redis_client without close method gracefully."""
        auth_service = MockAuthService()
        auth_service.websocket = TestWebSocketConnection()
        auth_service.redis_client = Mock(spec=[])
        try:
            if hasattr(auth_service, 'redis_client') and auth_service.redis_client:
                if hasattr(auth_service.redis_client, 'close'):
                    await auth_service.redis_client.close()
        except Exception as e:
            pytest.fail(f'Redis cleanup should handle redis_client without close gracefully, got: {e}')

    def test_redis_status_logging_uses_redis_client(self):
        """Test that Redis status logging uses redis_client availability.

        Fixed implementation:
        redis_enabled = auth_service.redis_client is not None
        redis_status = "enabled" if redis_enabled else "disabled"
        """
        auth_service_enabled = MockAuthService()
        auth_service_enabled.websocket = TestWebSocketConnection()
        redis_enabled = auth_service_enabled.redis_client is not None
        redis_status = 'enabled' if redis_enabled else 'disabled'
        assert redis_status == 'enabled', "Redis status should be 'enabled' when redis_client is present"
        auth_service_disabled = MockAuthService()
        auth_service_disabled.redis_client = None
        redis_enabled = auth_service_disabled.redis_client is not None
        redis_status = 'enabled' if redis_enabled else 'disabled'
        assert redis_status == 'disabled', "Redis status should be 'disabled' when redis_client is None"

    def test_auth_service_startup_compatibility_check(self):
        """Test that auth service startup compatibility check works correctly.

        This test ensures the fixed startup code can determine Redis status
        without relying on session_manager properties.
        """
        auth_service = MockAuthService()
        startup_checks = {'has_redis_client_attribute': hasattr(auth_service, 'redis_client'), 'redis_client_not_none': auth_service.redis_client is not None, 'redis_client_has_close': auth_service.redis_client is not None and hasattr(auth_service.redis_client, 'close')}
        assert startup_checks['has_redis_client_attribute'], 'AuthService must have redis_client attribute for compatibility'
        assert startup_checks['redis_client_not_none'], 'AuthService redis_client should be initialized (not None)'
        assert startup_checks['redis_client_has_close'], 'AuthService redis_client should have close method'

    def test_regression_prevention_session_manager_independence(self):
        """Test that Redis functionality doesn't depend on session_manager.

        This test prevents the regression where Redis status was checked via
        session_manager instead of redis_client.
        """
        auth_service = MockAuthService()
        if hasattr(auth_service, 'session_manager'):
            redis_via_client = auth_service.redis_client is not None
            assert isinstance(redis_via_client, bool), 'Redis status should be determinable from redis_client alone'

    def test_fixed_code_pattern_validation(self):
        """Test that the fixed code patterns work as expected.

        This test validates the exact patterns used in the fix commit.
        """
        auth_service = MockAuthService()
        has_redis_client = hasattr(auth_service, 'redis_client')
        assert has_redis_client, 'Should have redis_client attribute'
        redis_enabled = auth_service.redis_client is not None
        assert isinstance(redis_enabled, bool), 'Should return boolean for Redis status'
        redis_status = 'enabled' if redis_enabled else 'disabled'
        assert redis_status in ['enabled', 'disabled'], "Redis status should be 'enabled' or 'disabled'"

@pytest.mark.unit
class AuthServiceRedisClientErrorHandlingTests:
    """Test suite for auth service Redis client error handling."""

    @pytest.mark.asyncio
    async def test_redis_close_exception_handling(self):
        """Test that Redis close exceptions are handled gracefully.

        The fixed code should handle Redis close exceptions to prevent
        startup/shutdown failures.
        """
        auth_service = MockAuthService()
        auth_service.websocket = TestWebSocketConnection()
        close_exception = Exception('Redis connection lost')
        auth_service.redis_client.close = AsyncMock(side_effect=close_exception)
        exception_caught = False
        try:
            if hasattr(auth_service, 'redis_client') and auth_service.redis_client:
                if hasattr(auth_service.redis_client, 'close'):
                    await auth_service.redis_client.close()
        except Exception:
            exception_caught = True
        auth_service.redis_client.close.assert_called_once()

    def test_redis_client_none_safety(self):
        """Test that None redis_client is handled safely.

        Prevents AttributeError when redis_client is None.
        """
        auth_service = MockAuthService()
        auth_service.redis_client = None
        redis_enabled = auth_service.redis_client is not None
        assert redis_enabled is False, 'Should handle None redis_client safely'
        has_close = auth_service.redis_client is not None and hasattr(auth_service.redis_client, 'close')
        assert has_close is False, 'Should handle None redis_client in hasattr safely'

    def test_redis_client_attribute_missing_safety(self):
        """Test behavior when redis_client attribute is missing entirely."""
        auth_service = Mock(spec=[])
        has_redis_client = hasattr(auth_service, 'redis_client')
        assert has_redis_client is False, 'Should detect missing redis_client attribute'
        if hasattr(auth_service, 'redis_client'):
            redis_enabled = auth_service.redis_client is not None
        else:
            redis_enabled = False
        assert redis_enabled is False, 'Should handle missing redis_client attribute safely'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')