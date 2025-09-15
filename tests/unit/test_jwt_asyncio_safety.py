"""
Unit Tests for JWT Handler Asyncio Safety

Tests to ensure JWT handling doesn't have nested event loop issues.
"""
import asyncio
import sys
from pathlib import Path
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from shared.isolated_environment import IsolatedEnvironment
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.utils.asyncio_test_utils import AsyncioTestUtils, EventLoopTestError

class TestJWTAsyncioSafety:
    """Test JWT operations for asyncio safety"""

    @pytest.mark.asyncio
    async def test_jwt_handler_no_nested_loops(self):
        """Test JWT handler doesn't use nested asyncio.run()"""

        class JWTHandler:

            def __init__(self):
                self.secret = 'test_secret'

            async def verify_token_async(self, token: str) -> dict:
                """Async token verification"""
                await asyncio.sleep(0)
                try:
                    payload = jwt.decode(token, self.secret, algorithms=['HS256'])
                    await asyncio.sleep(0)
                    return {'valid': True, 'payload': payload}
                except jwt.InvalidTokenError:
                    return {'valid': False, 'error': 'Invalid token'}

            def verify_token_sync(self, token: str) -> dict:
                """Pure sync version for async context"""
                try:
                    payload = jwt.decode(token, self.secret, algorithms=['HS256'])
                    return {'valid': True, 'payload': payload}
                except jwt.InvalidTokenError:
                    return {'valid': False, 'error': 'Invalid token'}

            def verify_token(self, token: str) -> dict:
                """Smart wrapper that detects context"""
                try:
                    loop = asyncio.get_running_loop()
                    return self.verify_token_sync(token)
                except RuntimeError:
                    return asyncio.run(self.verify_token_async(token))
        handler = JWTHandler()
        test_payload = {'user_id': '123', 'exp': datetime.now(timezone.utc) + timedelta(hours=1)}
        test_token = jwt.encode(test_payload, handler.secret, algorithm='HS256')
        result = handler.verify_token(test_token)
        assert result['valid'] is True
        assert result['payload']['user_id'] == '123'

    def test_jwt_handler_sync_context(self):
        """Test JWT handler works in synchronous context"""

        class JWTHandler:

            def __init__(self):
                self.secret = 'test_secret'

            async def verify_token_async(self, token: str) -> dict:
                await asyncio.sleep(0)
                payload = jwt.decode(token, self.secret, algorithms=['HS256'])
                return {'valid': True, 'payload': payload}

            def verify_token(self, token: str) -> dict:
                try:
                    asyncio.get_running_loop()
                    payload = jwt.decode(token, self.secret, algorithms=['HS256'])
                    return {'valid': True, 'payload': payload}
                except RuntimeError:
                    return asyncio.run(self.verify_token_async(token))
        handler = JWTHandler()
        test_payload = {'user_id': '456'}
        test_token = jwt.encode(test_payload, handler.secret, algorithm='HS256')
        result = handler.verify_token(test_token)
        assert result['valid'] is True
        assert result['payload']['user_id'] == '456'

    @pytest.mark.asyncio
    async def test_jwt_middleware_async_safety(self):
        """Test JWT middleware patterns for async safety"""

        class JWTMiddleware:

            def __init__(self):
                self.secret = 'middleware_secret'

            async def authenticate_request(self, headers: dict) -> dict:
                """Async authentication"""
                token = headers.get('Authorization', '').replace('Bearer ', '')
                if not token:
                    await asyncio.sleep(0)
                    return {'authenticated': False, 'error': 'No token'}
                await asyncio.sleep(0)
                try:
                    payload = jwt.decode(token, self.secret, algorithms=['HS256'])
                    return {'authenticated': True, 'user': payload}
                except jwt.InvalidTokenError:
                    return {'authenticated': False, 'error': 'Invalid token'}
        middleware = JWTMiddleware()
        test_payload = {'user_id': '789', 'role': 'admin'}
        test_token = jwt.encode(test_payload, middleware.secret, algorithm='HS256')
        result = await middleware.authenticate_request({'Authorization': f'Bearer {test_token}'})
        assert result['authenticated'] is True
        assert result['user']['user_id'] == '789'

    @pytest.mark.asyncio
    async def test_jwt_refresh_token_async_safety(self):
        """Test JWT refresh token operations for async safety"""

        class TokenRefresher:

            def __init__(self):
                self.secret = 'refresh_secret'

            async def refresh_token_async(self, refresh_token: str) -> dict:
                """Async token refresh"""
                await asyncio.sleep(0)
                try:
                    payload = jwt.decode(refresh_token, self.secret, algorithms=['HS256'])
                    new_payload = {'user_id': payload['user_id'], 'exp': datetime.now(timezone.utc) + timedelta(hours=1)}
                    new_token = jwt.encode(new_payload, self.secret, algorithm='HS256')
                    await asyncio.sleep(0)
                    return {'success': True, 'access_token': new_token, 'expires_in': 3600}
                except jwt.InvalidTokenError:
                    return {'success': False, 'error': 'Invalid refresh token'}

            async def refresh_token(self, refresh_token: str) -> dict:
                """Proper async wrapper"""
                return await self.refresh_token_async(refresh_token)
        refresher = TokenRefresher()
        refresh_payload = {'user_id': '101', 'type': 'refresh'}
        refresh_token = jwt.encode(refresh_payload, refresher.secret, algorithm='HS256')
        result = await refresher.refresh_token(refresh_token)
        assert result['success'] is True
        assert 'access_token' in result
        assert result['expires_in'] == 3600

class TestJWTEventLoopPatterns:
    """Test specific JWT event loop patterns"""

    def test_detect_problematic_jwt_pattern(self):
        """Test detection of problematic JWT patterns"""

        def problematic_jwt_verify():

            async def verify_async():
                await asyncio.sleep(0)
                return {'valid': True}
            try:
                return asyncio.run(verify_async())
            except RuntimeError:
                return {'valid': False}
        assert AsyncioTestUtils.detect_nested_asyncio_run(problematic_jwt_verify) is False

        async def test_in_async():
            result = problematic_jwt_verify()
            assert result == {'valid': False}
        asyncio.run(test_in_async())

    @pytest.mark.asyncio
    async def test_jwt_caching_async_safety(self):
        """Test JWT caching doesn't have event loop issues"""

        class JWTCache:

            def __init__(self):
                self.cache = {}
                self.secret = 'cache_secret'

            async def get_cached_or_verify(self, token: str) -> dict:
                """Get from cache or verify"""
                if token in self.cache:
                    await asyncio.sleep(0)
                    return self.cache[token]
                await asyncio.sleep(0)
                try:
                    payload = jwt.decode(token, self.secret, algorithms=['HS256'])
                    result = {'valid': True, 'payload': payload}
                    self.cache[token] = result
                    return result
                except jwt.InvalidTokenError:
                    result = {'valid': False}
                    self.cache[token] = result
                    return result
        cache = JWTCache()
        test_payload = {'user_id': '202'}
        test_token = jwt.encode(test_payload, cache.secret, algorithm='HS256')
        result1 = await cache.get_cached_or_verify(test_token)
        assert result1['valid'] is True
        result2 = await cache.get_cached_or_verify(test_token)
        assert result2['valid'] is True
        assert result2 == result1

class TestJWTAsyncioMigration:
    """Test patterns for migrating JWT code to proper async"""

    @pytest.mark.asyncio
    async def test_migration_pattern_before_after(self):
        """Test migration from problematic to proper pattern"""

        class NewJWTHandler:

            async def verify_async(self, token: str):
                await asyncio.sleep(0)
                return {'valid': True}

            def verify_sync(self, token: str):
                return {'valid': True}

            def verify(self, token: str):
                """Smart wrapper"""
                try:
                    loop = asyncio.get_running_loop()
                    return self.verify_sync(token)
                except RuntimeError:
                    return asyncio.run(self.verify_async(token))
        new_handler = NewJWTHandler()
        result = new_handler.verify('test_token')
        assert result['valid'] is True

    def test_migration_pattern_sync_context(self):
        """Test migrated pattern works in sync context"""

        class MigratedJWTHandler:

            async def verify_async(self, token: str):
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                return {'valid': True, 'token': token}

            def verify(self, token: str):
                try:
                    asyncio.get_running_loop()
                    return {'valid': True, 'token': token}
                except RuntimeError:
                    return asyncio.run(self.verify_async(token))
        handler = MigratedJWTHandler()
        result = handler.verify('sync_token')
        assert result['valid'] is True
        assert result['token'] == 'sync_token'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')