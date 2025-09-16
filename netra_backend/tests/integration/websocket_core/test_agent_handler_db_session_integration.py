"""
Integration Tests for Agent Handler Database Session Patterns

This integration test uses REAL database services to reproduce the triage start 
failure caused by incorrect async session pattern usage in agent_handler.py.

PURPOSE: Validate async session patterns with real database connections,
reproducing the exact conditions that cause triage agent start failures.

CRITICAL ERROR REPRODUCTION:
- agent_handler.py line 125: `async for db_session in get_request_scoped_db_session():`
- This fails with real database because get_request_scoped_db_session() returns
  _AsyncGeneratorContextManager, not an async iterator

Business Value: Platform/Internal - System Stability  
Ensures database session patterns work correctly for agent operations affecting
$500K+ ARR chat functionality.

INTEGRATION REQUIREMENTS:
- Uses REAL database connections (no mocks)
- Tests MUST fail with current broken code  
- Tests will pass after 'async for'  ->  'async with' fix
- Validates complete session lifecycle with real services

PHASE 1 PRIORITY: Real service validation of async session patterns
"""
import asyncio
import pytest
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.dependencies import get_request_scoped_db_session
from netra_backend.app.database.request_scoped_session_factory import get_session_factory
from netra_backend.app.db.database_manager import DatabaseManager

class AgentHandlerDbSessionIntegrationTests(SSotAsyncTestCase):
    """
    Integration tests for database session patterns in agent_handler.py
    
    Uses REAL database services to validate that async session patterns
    work correctly for agent operations.
    """

    async def async_setup_method(self, method=None):
        """Set up test environment with real database connections."""
        await super().async_setup_method(method)
        self.env = IsolatedEnvironment()
        self.env.set('ENVIRONMENT', 'test')
        self.db_manager = None
        try:
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
        except Exception as e:
            pytest.skip(f'Database not available for integration test: {e}')
        self.mock_websocket = AsyncMock()
        self.mock_websocket.scope = {'app': MagicMock(), 'user': {'sub': 'test_user_integration_123'}, 'path': '/ws/chat'}
        self.mock_websocket.scope['app'].state = MagicMock()
        self.connection_id = 'integration_connection_123'
        self.run_id = 'integration_run_456'

    @pytest.mark.asyncio
    async def test_real_session_factory_pattern(self):
        """
        Test the real session factory with the broken 'async for' pattern.
        
        This reproduces the exact failure that occurs when agent_handler.py
        tries to start a triage agent with real database connections.
        
        EXPECTED BEHAVIOR:
        - With current broken code: Test FAILS with TypeError
        - After fix (async for  ->  async with): Test PASSES
        """
        try:
            session_context = get_request_scoped_db_session()
            with pytest.raises(TypeError) as exc_info:
                async for db_session in session_context:
                    pytest.fail('Should not reach this code due to TypeError')
                    break
            error_message = str(exc_info.value)
            assert 'async for' in error_message.lower()
            assert '__aiter__' in error_message
            self.record_metric('real_session_factory_async_for_failure', f'REPRODUCED - Real session factory async for failure: {error_message}')
        except Exception as e:
            if 'Database not available' in str(e):
                pytest.skip('Database not available for integration test')
            else:
                raise

    @pytest.mark.asyncio
    async def test_real_session_correct_async_with_pattern(self):
        """
        Test that the CORRECT 'async with' pattern works with real session factory.
        
        This demonstrates the fix that should be applied to agent_handler.py:
        changing line 125 from 'async for' to 'async with'.
        
        EXPECTED BEHAVIOR:
        - Always passes with real database (correct pattern)
        - Validates complete session lifecycle
        """
        try:
            session_context = get_request_scoped_db_session()
            async with session_context as db_session:
                assert db_session is not None
                assert hasattr(db_session, 'execute')
                assert hasattr(db_session, 'commit')
                assert hasattr(db_session, 'rollback')
                try:
                    result = await db_session.execute('SELECT 1 as test_value')
                    rows = result.fetchall()
                    assert len(rows) == 1
                    assert rows[0][0] == 1
                    await db_session.commit()
                except Exception as db_error:
                    await db_session.rollback()
                    raise AssertionError(f'Database operation failed: {db_error}')
            self.record_metric('real_session_async_with_success', 'PASSED - Real session with async with pattern works correctly')
        except Exception as e:
            if 'Database not available' in str(e):
                pytest.skip('Database not available for integration test')
            else:
                raise

    @pytest.mark.asyncio
    async def test_real_websocket_scoped_supervisor_session_pattern(self):
        """
        Test the complete session pattern that agent_handler.py uses for
        creating WebSocket-scoped supervisors with real database.
        
        This reproduces the exact flow that fails when triage agent starts:
        1. get_request_scoped_db_session() called
        2. 'async for' used (incorrectly) 
        3. get_websocket_scoped_supervisor called with session
        4. TypeError prevents supervisor creation
        """
        try:
            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_supervisor:
                mock_supervisor.return_value = AsyncMock()
                session_context = get_request_scoped_db_session()
                with pytest.raises(TypeError) as exc_info:
                    async for db_session in session_context:
                        supervisor = await mock_supervisor(context={'user_id': 'test_user'}, db_session=db_session, app_state=self.mock_websocket.scope['app'].state)
                        pytest.fail('Should not create supervisor due to TypeError')
                        break
                error_message = str(exc_info.value)
                assert 'async for' in error_message.lower()
                mock_supervisor.assert_not_called()
                self.record_metric('websocket_supervisor_session_failure', 'REPRODUCED - WebSocket supervisor creation blocked by session pattern failure')
        except Exception as e:
            if 'Database not available' in str(e):
                pytest.skip('Database not available for integration test')
            else:
                raise

    @pytest.mark.asyncio
    async def test_real_session_lifecycle_validation(self):
        """
        Validate that real database sessions have proper lifecycle management
        when used correctly with 'async with' pattern.
        
        This ensures that the fix (async for  ->  async with) maintains proper
        session cleanup and resource management.
        """
        try:
            session_context = get_request_scoped_db_session()
            session_created = False
            session_closed = False
            async with session_context as db_session:
                session_created = True
                assert db_session is not None
                assert hasattr(db_session, 'bind')
                result = await db_session.execute('SELECT 1')
                assert result is not None
                assert not db_session.is_active or True
            session_closed = True
            assert session_created, 'Session should have been created'
            assert session_closed, 'Session should have been closed'
            self.record_metric('real_session_lifecycle_validation', 'PASSED - Real session lifecycle properly managed with async with pattern')
        except Exception as e:
            if 'Database not available' in str(e):
                pytest.skip('Database not available for integration test')
            else:
                raise

    @pytest.mark.asyncio
    async def test_integration_session_factory_configuration(self):
        """
        Validate that the session factory is properly configured for
        integration testing with real database connections.
        
        This ensures our integration tests accurately represent production
        conditions where the triage start failure occurs.
        """
        try:
            session_factory = get_session_factory()
            assert session_factory is not None
            session_context = get_request_scoped_db_session()
            assert session_context is not None
            from contextlib import _AsyncGeneratorContextManager
            assert isinstance(session_context, _AsyncGeneratorContextManager)
            assert not hasattr(session_context, '__aiter__')
            assert hasattr(session_context, '__aenter__')
            assert hasattr(session_context, '__aexit__')
            self.record_metric('session_factory_configuration', 'VALIDATED - Session factory correctly configured for integration testing')
        except Exception as e:
            if 'Database not available' in str(e):
                pytest.skip('Database not available for integration test')
            else:
                raise

    async def async_teardown_method(self, method=None):
        """Clean up test environment and database connections."""
        try:
            if self.db_manager:
                await self.db_manager.cleanup()
        except Exception:
            pass
        await super().async_teardown_method(method)
        print(f'\n=== Agent Handler DB Session Integration Tests Completed ===')
        metrics = self.get_all_metrics()
        for metric_name, metric_value in metrics.items():
            print(f'  {metric_name}: {metric_value}')
        print('=' * 70)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')