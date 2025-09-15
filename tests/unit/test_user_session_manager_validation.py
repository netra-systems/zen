"""Simple validation test for UserSessionManager functionality.

This test validates the core UserSessionManager functionality with proper user IDs
that pass the UserExecutionContext validation requirements.
"""
import pytest
import asyncio
from datetime import datetime, timezone
from shared.session_management import UserSessionManager, get_user_session, get_session_manager
from shared.id_generation import UnifiedIdGenerator
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.unit
class TestUserSessionManagerValidation:
    """Basic validation tests for UserSessionManager."""

    @pytest.mark.asyncio
    async def test_basic_session_creation_and_reuse(self):
        """Test basic session creation and conversation continuity."""
        session_manager = UserSessionManager()
        try:
            user_id = 'user_session_validation_12345abcdef'
            thread_id = 'validation_thread_67890'
            context1 = await session_manager.get_or_create_user_session(user_id, thread_id)
            assert isinstance(context1, UserExecutionContext)
            assert context1.user_id == user_id
            assert context1.thread_id == thread_id
            context2 = await session_manager.get_or_create_user_session(user_id, thread_id)
            assert context2.user_id == user_id
            assert context2.thread_id == thread_id
            assert context2.run_id == context1.run_id
            assert len(session_manager._sessions) == 1
        finally:
            await session_manager.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_multi_user_isolation_validation(self):
        """Test that different users get completely isolated sessions."""
        session_manager = UserSessionManager()
        try:
            user1_id = 'validation_user_a1b2c3d4e5f6'
            user2_id = 'validation_user_x9y8z7w6v5u4'
            thread_id = 'shared_thread_name'
            context1 = await session_manager.get_or_create_user_session(user1_id, thread_id)
            context2 = await session_manager.get_or_create_user_session(user2_id, thread_id)
            assert context1.user_id != context2.user_id
            assert context1.run_id != context2.run_id
            assert context1.request_id != context2.request_id
            assert len(session_manager._sessions) == 2
        finally:
            await session_manager.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_session_manager_singleton(self):
        """Test that session manager singleton pattern works."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        assert manager1 is manager2
        assert isinstance(manager1, UserSessionManager)

    @pytest.mark.asyncio
    async def test_convenience_function_integration(self):
        """Test convenience function for getting user sessions."""
        user_id = 'convenience_validation_user_abc123'
        thread_id = 'convenience_thread_xyz789'
        context = await get_user_session(user_id, thread_id)
        assert isinstance(context, UserExecutionContext)
        assert context.user_id == user_id
        assert context.thread_id == thread_id

    @pytest.mark.asyncio
    async def test_websocket_integration(self):
        """Test WebSocket connection integration."""
        session_manager = UserSessionManager()
        try:
            user_id = 'websocket_validation_user_def456'
            thread_id = 'websocket_thread_ghi789'
            ws_connection_id = 'ws_validation_conn_jkl012'
            context = await session_manager.get_or_create_user_session(user_id, thread_id, websocket_connection_id=ws_connection_id)
            assert context.websocket_client_id == ws_connection_id
            new_ws_id = 'ws_updated_conn_mno345'
            success = await session_manager.update_session_websocket(user_id, thread_id, new_ws_id)
            assert success is True
        finally:
            await session_manager.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_session_metrics(self):
        """Test basic session metrics collection."""
        session_manager = UserSessionManager()
        try:
            await session_manager.get_or_create_user_session('metrics_user_123abc', 'thread1')
            await session_manager.get_or_create_user_session('metrics_user_456def', 'thread2')
            metrics = session_manager.get_session_metrics()
            assert metrics.active_sessions == 2
            assert metrics.total_sessions == 2
            assert metrics.sessions_created_today == 2
            assert metrics.average_session_duration_minutes >= 0
        finally:
            await session_manager.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_integration_with_unified_id_generator(self):
        """Test that UserSessionManager integrates with UnifiedIdGenerator."""
        session_manager = UserSessionManager()
        try:
            user_id = 'unifiedid_integration_789xyz'
            thread_id = 'unifiedid_thread_012abc'
            context = await session_manager.get_or_create_user_session(user_id, thread_id)
            assert context.run_id.startswith('run_')
            assert context.request_id.startswith('req_')
            unified_session = UnifiedIdGenerator.get_existing_session(user_id, thread_id)
            assert unified_session is not None
            assert unified_session['thread_id'] == thread_id
        finally:
            await session_manager.stop_cleanup_task()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')