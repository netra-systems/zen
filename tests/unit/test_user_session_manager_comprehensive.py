"""Comprehensive tests for UserSessionManager SSOT implementation.

This test suite validates the complete UserSessionManager functionality including:
- Session creation and reuse for conversation continuity
- Multi-user isolation
- Thread management and WebSocket integration  
- Session cleanup and memory management
- Metrics collection and monitoring
- Error handling and recovery

Business Value Justification (BVJ):
- Segment: All (Tests critical chat continuity functionality)
- Business Goal: Ensure reliable multi-turn AI conversations
- Value Impact: Validates 90% of platform value delivery mechanism
- Strategic Impact: Prevents memory leaks and session management failures
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# SSOT imports
from shared.session_management import (
    UserSessionManager, 
    UserSession,
    SessionMetrics,
    SessionManagerError,
    get_session_manager,
    get_user_session,
    initialize_session_manager,
    shutdown_session_manager
)
from shared.id_generation import UnifiedIdGenerator
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError
)


class TestUserSessionManager:
    """Test UserSessionManager core functionality."""
    
    @pytest.fixture
    async def session_manager(self):
        """Create a clean session manager for testing."""
        manager = UserSessionManager(
            cleanup_interval_minutes=1,  # Short interval for testing
            max_session_age_hours=1,     # Short age for testing
            max_inactive_minutes=5       # Short inactivity for testing
        )
        yield manager
        # Cleanup
        await manager.stop_cleanup_task()
    
    @pytest.fixture
    def test_user_data(self):
        """Test user data for session creation."""
        return {
            'user_id': 'valid_user_a1b2c3d4e5f6789',
            'thread_id': 'thread_chat_456',
            'run_id': 'run_execution_789',
            'websocket_connection_id': 'ws_conn_abc123'
        }
    
    @pytest.mark.asyncio
    async def test_session_creation_new_user(self, session_manager, test_user_data):
        """Test creating a new session for a new user."""
        context = await session_manager.get_or_create_user_session(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id'],
            websocket_connection_id=test_user_data['websocket_connection_id']
        )
        
        assert isinstance(context, UserExecutionContext)
        assert context.user_id == test_user_data['user_id']
        assert context.thread_id == test_user_data['thread_id']
        assert context.websocket_client_id == test_user_data['websocket_connection_id']
        assert context.request_id is not None
        
        # Validate session storage
        session_key = f"{test_user_data['user_id']}:{test_user_data['thread_id']}"
        assert session_key in session_manager._sessions
        
        stored_session = session_manager._sessions[session_key]
        assert isinstance(stored_session, UserSession)
        assert stored_session.user_id == test_user_data['user_id']
        assert stored_session.execution_context is not None
    
    @pytest.mark.asyncio 
    async def test_session_reuse_for_continuity(self, session_manager, test_user_data):
        """Test that existing sessions are reused for conversation continuity."""
        # Create initial session
        context1 = await session_manager.get_or_create_user_session(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id']
        )
        
        # Request same session - should reuse
        context2 = await session_manager.get_or_create_user_session(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id']
        )
        
        # Should have same core identifiers (continuity)
        assert context1.user_id == context2.user_id
        assert context1.thread_id == context2.thread_id
        assert context1.run_id == context2.run_id
        
        # But different request IDs (new request)
        assert context1.request_id != context2.request_id
        
        # Should only have one session stored
        assert len(session_manager._sessions) == 1
    
    @pytest.mark.asyncio
    async def test_multi_user_isolation(self, session_manager):
        """Test that different users get isolated sessions."""
        user1_context = await session_manager.get_or_create_user_session(
            user_id='valid_user_abc123456789def',
            thread_id='thread_a'
        )
        
        user2_context = await session_manager.get_or_create_user_session(
            user_id='valid_user_xyz987654321abc', 
            thread_id='thread_a'  # Same thread name but different user
        )
        
        # Should be completely different contexts
        assert user1_context.user_id != user2_context.user_id
        assert user1_context.run_id != user2_context.run_id
        assert user1_context.request_id != user2_context.request_id
        
        # Should have two separate sessions
        assert len(session_manager._sessions) == 2
        assert 'valid_user_abc123456789def:thread_a' in session_manager._sessions
        assert 'valid_user_xyz987654321abc:thread_a' in session_manager._sessions
    
    @pytest.mark.asyncio
    async def test_multi_thread_per_user(self, session_manager):
        """Test that one user can have multiple thread sessions."""
        user_id = 'test_user'
        
        context1 = await session_manager.get_or_create_user_session(
            user_id=user_id,
            thread_id='thread_1'
        )
        
        context2 = await session_manager.get_or_create_user_session(
            user_id=user_id,
            thread_id='thread_2'
        )
        
        # Same user, different threads - should be separate
        assert context1.user_id == context2.user_id
        assert context1.thread_id != context2.thread_id
        assert context1.run_id != context2.run_id
        
        # Should have two sessions for same user
        assert len(session_manager._sessions) == 2
        assert f'{user_id}:thread_1' in session_manager._sessions
        assert f'{user_id}:thread_2' in session_manager._sessions
    
    @pytest.mark.asyncio
    async def test_run_id_handling_new_execution(self, session_manager, test_user_data):
        """Test run_id handling for new agent executions within same thread."""
        # Create initial session
        context1 = await session_manager.get_or_create_user_session(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id'],
            run_id='run_initial'
        )
        
        # Same thread, different run_id (new agent execution)
        context2 = await session_manager.get_or_create_user_session(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id'],
            run_id='run_new_execution'
        )
        
        # Should maintain thread continuity but update run
        assert context1.user_id == context2.user_id
        assert context1.thread_id == context2.thread_id
        assert context2.run_id == 'run_new_execution'
        
        # Should still be one session (thread continuity)
        assert len(session_manager._sessions) == 1
    
    @pytest.mark.asyncio
    async def test_websocket_connection_update(self, session_manager, test_user_data):
        """Test updating WebSocket connection for existing session."""
        # Create session
        context = await session_manager.get_or_create_user_session(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id']
        )
        
        # Update WebSocket connection
        new_ws_id = 'new_websocket_connection_123'
        success = await session_manager.update_session_websocket(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id'],
            websocket_connection_id=new_ws_id
        )
        
        assert success is True
        
        # Verify session was updated
        session_key = f"{test_user_data['user_id']}:{test_user_data['thread_id']}"
        stored_session = session_manager._sessions[session_key]
        assert stored_session.websocket_connection_id == new_ws_id
        assert stored_session.execution_context.websocket_client_id == new_ws_id
    
    @pytest.mark.asyncio
    async def test_websocket_update_nonexistent_session(self, session_manager):
        """Test updating WebSocket for non-existent session returns False."""
        success = await session_manager.update_session_websocket(
            user_id='nonexistent_user',
            thread_id='nonexistent_thread',
            websocket_connection_id='some_connection'
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_existing_session_found(self, session_manager, test_user_data):
        """Test getting existing session when it exists."""
        # Create session first
        original_context = await session_manager.get_or_create_user_session(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id']
        )
        
        # Get existing session
        existing_context = await session_manager.get_existing_session(
            user_id=test_user_data['user_id'],
            thread_id=test_user_data['thread_id']
        )
        
        assert existing_context is not None
        assert existing_context.user_id == original_context.user_id
        assert existing_context.thread_id == original_context.thread_id
        assert existing_context.run_id == original_context.run_id
        # Different request ID for new request
        assert existing_context.request_id != original_context.request_id
    
    @pytest.mark.asyncio
    async def test_get_existing_session_not_found(self, session_manager):
        """Test getting existing session when it doesn't exist."""
        existing_context = await session_manager.get_existing_session(
            user_id='nonexistent_user',
            thread_id='nonexistent_thread'
        )
        
        assert existing_context is None
    
    @pytest.mark.asyncio
    async def test_invalidate_user_sessions(self, session_manager):
        """Test invalidating all sessions for a specific user."""
        user_id = 'test_user'
        
        # Create multiple sessions for user
        await session_manager.get_or_create_user_session(user_id, 'thread_1')
        await session_manager.get_or_create_user_session(user_id, 'thread_2')
        await session_manager.get_or_create_user_session('other_user', 'thread_3')
        
        assert len(session_manager._sessions) == 3
        
        # Invalidate sessions for test_user
        invalidated_count = await session_manager.invalidate_user_sessions(user_id)
        
        assert invalidated_count == 2
        assert len(session_manager._sessions) == 1
        assert 'other_user:thread_3' in session_manager._sessions
        assert 'test_user:thread_1' not in session_manager._sessions
        assert 'test_user:thread_2' not in session_manager._sessions
    
    @pytest.mark.asyncio
    async def test_session_cleanup_expired_by_age(self, session_manager):
        """Test cleanup of sessions that exceed maximum age."""
        # Create session
        user_context = await session_manager.get_or_create_user_session(
            user_id='test_user',
            thread_id='test_thread'
        )
        
        # Manually age the session
        session_key = 'test_user:test_thread'
        stored_session = session_manager._sessions[session_key]
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)  # Older than max_age_hours=1
        stored_session.created_at = old_time
        stored_session.last_activity = old_time
        
        # Run cleanup
        cleaned_count = await session_manager.cleanup_expired_sessions()
        
        assert cleaned_count >= 1  # At least our session should be cleaned
        assert session_key not in session_manager._sessions
    
    @pytest.mark.asyncio
    async def test_session_cleanup_expired_by_inactivity(self, session_manager):
        """Test cleanup of sessions that exceed maximum inactivity."""
        # Create session
        await session_manager.get_or_create_user_session(
            user_id='test_user',
            thread_id='test_thread'
        )
        
        # Manually mark as inactive
        session_key = 'test_user:test_thread'
        stored_session = session_manager._sessions[session_key]
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)  # Older than max_inactive_minutes=5
        stored_session.last_activity = old_time
        
        # Run cleanup
        cleaned_count = await session_manager.cleanup_expired_sessions()
        
        assert cleaned_count >= 1
        assert session_key not in session_manager._sessions
    
    @pytest.mark.asyncio
    async def test_session_metrics_collection(self, session_manager):
        """Test session metrics collection and calculation."""
        # Create some sessions
        await session_manager.get_or_create_user_session('user1', 'thread1')
        await session_manager.get_or_create_user_session('user2', 'thread2')
        
        # Get metrics
        metrics = session_manager.get_session_metrics()
        
        assert isinstance(metrics, SessionMetrics)
        assert metrics.active_sessions == 2
        assert metrics.sessions_created_today == 2
        assert metrics.total_sessions == 2
        assert metrics.average_session_duration_minutes >= 0
        assert metrics.memory_usage_mb >= 0
        
        # Test metrics dict conversion
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert 'active_sessions' in metrics_dict
        assert 'memory_usage_mb' in metrics_dict
    
    @pytest.mark.asyncio
    async def test_get_active_sessions_anonymized(self, session_manager):
        """Test getting active sessions with anonymized data."""
        # Create sessions
        await session_manager.get_or_create_user_session('sensitive_user_123', 'thread1')
        await session_manager.get_or_create_user_session('another_user_456', 'thread2')
        
        # Get active sessions
        sessions = session_manager.get_active_sessions()
        
        assert len(sessions) == 2
        
        for session_dict in sessions:
            assert isinstance(session_dict, dict)
            # Verify anonymization - user_id should be truncated
            assert '...' in session_dict['user_id']
            assert len(session_dict['user_id']) > 8  # Should have original[:8] + '...'
            assert 'created_at' in session_dict
            assert 'age_minutes' in session_dict
    
    @pytest.mark.asyncio
    async def test_managed_session_context_manager(self, session_manager):
        """Test managed session context manager."""
        user_id = 'context_test_user'
        thread_id = 'context_test_thread'
        
        # Use managed session
        async with session_manager.managed_session(user_id, thread_id) as context:
            assert isinstance(context, UserExecutionContext)
            assert context.user_id == user_id
            assert context.thread_id == thread_id
            
            # Session should exist
            session_key = f'{user_id}:{thread_id}'
            assert session_key in session_manager._sessions
        
        # After context manager, session should still exist but activity updated
        assert session_key in session_manager._sessions
        stored_session = session_manager._sessions[session_key]
        # last_activity should be recent (within last few seconds)
        age_seconds = (datetime.now(timezone.utc) - stored_session.last_activity).total_seconds()
        assert age_seconds < 5  # Should be very recent
    
    @pytest.mark.asyncio
    async def test_background_cleanup_task_lifecycle(self, session_manager):
        """Test background cleanup task start and stop."""
        # Start cleanup task
        await session_manager.start_cleanup_task()
        assert session_manager._cleanup_task is not None
        assert not session_manager._cleanup_task.done()
        
        # Stop cleanup task
        await session_manager.stop_cleanup_task()
        assert session_manager._cleanup_task.done()
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_user_data(self, session_manager):
        """Test error handling with invalid user data."""
        with pytest.raises(Exception):  # Could be SessionManagerError or related
            await session_manager.get_or_create_user_session(
                user_id='',  # Invalid empty user_id
                thread_id='valid_thread'
            )
    
    @pytest.mark.asyncio 
    async def test_session_integration_with_unified_id_generator(self, session_manager):
        """Test integration with UnifiedIdGenerator session management."""
        user_id = 'integration_user'
        thread_id = 'integration_thread'
        
        # Create session through UserSessionManager
        context = await session_manager.get_or_create_user_session(user_id, thread_id)
        
        # Verify UnifiedIdGenerator was used for ID generation
        assert context.run_id.startswith('run_')
        assert context.request_id.startswith('req_')
        
        # Check that UnifiedIdGenerator has session data
        unified_session = UnifiedIdGenerator.get_existing_session(user_id, thread_id)
        assert unified_session is not None
        assert unified_session['thread_id'] == thread_id


class TestGlobalSessionManagerFunctions:
    """Test global session manager utility functions."""
    
    def test_get_session_manager_singleton(self):
        """Test that get_session_manager returns singleton instance."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, UserSessionManager)
    
    @pytest.mark.asyncio
    async def test_get_user_session_convenience_function(self):
        """Test convenience function for getting user sessions."""
        context = await get_user_session(
            user_id='convenience_user',
            thread_id='convenience_thread'
        )
        
        assert isinstance(context, UserExecutionContext)
        assert context.user_id == 'convenience_user'
        assert context.thread_id == 'convenience_thread'
    
    @pytest.mark.asyncio
    async def test_initialize_and_shutdown_session_manager(self):
        """Test session manager initialization and shutdown."""
        # Initialize
        manager = await initialize_session_manager()
        assert isinstance(manager, UserSessionManager)
        assert manager._cleanup_task is not None
        
        # Shutdown
        await shutdown_session_manager()
        # Should not raise exception


class TestUserSession:
    """Test UserSession data structure."""
    
    def test_user_session_creation(self):
        """Test creating UserSession instance."""
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id='test_user',
            thread_id='test_thread',
            run_id='test_run',
            request_id='test_request',
            created_at=now,
            last_activity=now
        )
        
        assert session.user_id == 'test_user'
        assert session.get_age_minutes() >= 0
        assert session.get_inactivity_minutes() >= 0
    
    def test_user_session_activity_update(self):
        """Test updating session activity."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(minutes=5)
        
        session = UserSession(
            user_id='test_user',
            thread_id='test_thread', 
            run_id='test_run',
            request_id='test_request',
            created_at=old_time,
            last_activity=old_time
        )
        
        # Initial inactivity should be ~5 minutes
        initial_inactivity = session.get_inactivity_minutes()
        assert initial_inactivity >= 4.5  # Allow for slight timing differences
        
        # Update activity
        session.update_activity()
        
        # Inactivity should now be near 0
        updated_inactivity = session.get_inactivity_minutes()
        assert updated_inactivity < 0.1  # Should be very recent
    
    def test_user_session_to_dict(self):
        """Test converting UserSession to dictionary."""
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id='dict_test_user',
            thread_id='dict_test_thread',
            run_id='dict_test_run', 
            request_id='dict_test_request',
            created_at=now,
            last_activity=now,
            websocket_connection_id='dict_test_ws',
            session_metadata={'test_key': 'test_value'}
        )
        
        session_dict = session.to_dict()
        
        assert isinstance(session_dict, dict)
        assert session_dict['user_id'] == 'dict_test_user'
        assert session_dict['websocket_connection_id'] == 'dict_test_ws'
        assert 'created_at' in session_dict
        assert 'age_minutes' in session_dict
        assert 'metadata_keys' in session_dict


class TestSessionMetrics:
    """Test SessionMetrics functionality."""
    
    def test_session_metrics_creation(self):
        """Test creating SessionMetrics instance."""
        metrics = SessionMetrics(
            total_sessions=10,
            active_sessions=5,
            sessions_created_today=3,
            average_session_duration_minutes=25.5
        )
        
        assert metrics.total_sessions == 10
        assert metrics.active_sessions == 5
        assert metrics.sessions_created_today == 3
        assert metrics.average_session_duration_minutes == 25.5
    
    def test_session_metrics_to_dict(self):
        """Test converting SessionMetrics to dictionary."""
        metrics = SessionMetrics(
            total_sessions=5,
            active_sessions=3,
            memory_usage_mb=15.7
        )
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert metrics_dict['total_sessions'] == 5
        assert metrics_dict['active_sessions'] == 3
        assert metrics_dict['memory_usage_mb'] == 15.7
        assert 'expired_sessions_cleaned' in metrics_dict


# Integration test with real components
class TestUserSessionManagerIntegration:
    """Integration tests with real system components."""
    
    @pytest.mark.asyncio
    async def test_integration_with_user_execution_context(self):
        """Test integration with UserExecutionContext creation."""
        session_manager = UserSessionManager()
        
        try:
            # Create session
            context = await session_manager.get_or_create_user_session(
                user_id='integration_user_123',
                thread_id='integration_thread_456'
            )
            
            # Validate UserExecutionContext properties
            assert isinstance(context, UserExecutionContext)
            context.verify_isolation()  # Should not raise
            
            # Test context methods
            correlation_id = context.get_correlation_id()
            assert isinstance(correlation_id, str)
            assert 'integration_user_123' in correlation_id
            
            audit_trail = context.get_audit_trail()
            assert isinstance(audit_trail, dict)
            assert 'user_id' in audit_trail
            
        finally:
            await session_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_session_continuity_realistic_scenario(self):
        """Test realistic multi-message conversation scenario."""
        session_manager = UserSessionManager()
        
        try:
            user_id = 'chat_user_789'
            thread_id = 'conversation_thread_123'
            
            # First message in conversation
            context1 = await session_manager.get_or_create_user_session(user_id, thread_id)
            original_run_id = context1.run_id
            
            # Second message in same conversation - should reuse session
            context2 = await session_manager.get_or_create_user_session(user_id, thread_id)
            
            # Third message with WebSocket connection
            context3 = await session_manager.get_or_create_user_session(
                user_id, thread_id, websocket_connection_id='ws_conn_realtime'
            )
            
            # All should maintain conversation continuity
            assert context1.user_id == context2.user_id == context3.user_id
            assert context1.thread_id == context2.thread_id == context3.thread_id
            assert context1.run_id == context2.run_id == context3.run_id == original_run_id
            
            # WebSocket should be added to latest context
            assert context3.websocket_client_id == 'ws_conn_realtime'
            
            # Should still be only one session
            assert len(session_manager._sessions) == 1
            
        finally:
            await session_manager.stop_cleanup_task()


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])