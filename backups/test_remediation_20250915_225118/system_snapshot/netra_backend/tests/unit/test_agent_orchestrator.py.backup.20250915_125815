"""
Test Agent Orchestration Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable agent execution with proper user isolation
- Value Impact: Multi-tenant security and context management enable concurrent users
- Strategic Impact: Core platform functionality for agent coordination and execution
"""

import pytest
import threading
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from typing import Dict, Any

from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from netra_backend.app.agents.supervisor.agent_execution_context_manager import (
    AgentExecutionContextManager,
    ExecutionSession,
    ContextIsolationMetrics
)


class TestExecutionSession:
    """Test ExecutionSession business logic"""
    
    @pytest.mark.unit
    def test_execution_session_initialization(self):
        """Test ExecutionSession initialization with proper types"""
        user_id = UserID("user_123")
        thread_id = ThreadID("thread_456")
        now = datetime.now(timezone.utc)
        
        mock_context = Mock(spec=StronglyTypedUserExecutionContext)
        
        session = ExecutionSession(
            session_id="session_789",
            user_id=user_id,
            thread_id=thread_id,
            created_at=now,
            last_activity=now,
            execution_context=mock_context
        )
        
        assert session.session_id == "session_789"
        assert session.user_id == user_id
        assert session.thread_id == thread_id
        assert session.created_at == now
        assert session.last_activity == now
        assert session.execution_context is mock_context
        assert len(session.active_runs) == 0
        assert len(session.metadata) == 0
    
    @pytest.mark.unit
    def test_session_activity_tracking(self):
        """Test session activity timestamp updates"""
        user_id = UserID("user_123")
        thread_id = ThreadID("thread_456")
        original_time = datetime.now(timezone.utc)
        
        session = ExecutionSession(
            session_id="session_789",
            user_id=user_id,
            thread_id=thread_id,
            created_at=original_time,
            last_activity=original_time,
            execution_context=Mock()
        )
        
        # Update activity
        session.update_activity()
        
        assert session.last_activity > original_time
        assert session.created_at == original_time  # Should not change
    
    @pytest.mark.unit
    def test_session_run_management(self):
        """Test session run tracking functionality"""
        session = ExecutionSession(
            session_id="session_789",
            user_id=UserID("user_123"),
            thread_id=ThreadID("thread_456"),
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            execution_context=Mock()
        )
        
        # Add runs
        session.add_run("run_1")
        session.add_run("run_2")
        
        assert len(session.active_runs) == 2
        assert "run_1" in session.active_runs
        assert "run_2" in session.active_runs
        
        # Remove run
        session.remove_run("run_1")
        
        assert len(session.active_runs) == 1
        assert "run_1" not in session.active_runs
        assert "run_2" in session.active_runs
        
        # Remove non-existent run should not error
        session.remove_run("non_existent")
        assert len(session.active_runs) == 1
    
    @pytest.mark.unit
    def test_session_expiration_logic(self):
        """Test session expiration detection"""
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        session = ExecutionSession(
            session_id="session_789",
            user_id=UserID("user_123"),
            thread_id=ThreadID("thread_456"),
            created_at=old_time,
            last_activity=old_time,
            execution_context=Mock()
        )
        
        # Session with no runs should expire after timeout (default 60 minutes)
        assert session.is_expired(timeout_minutes=60) is True
        
        # Session with active runs should not expire
        session.add_run("active_run")
        assert session.is_expired(timeout_minutes=60) is False
        
        # Recent session should not expire
        session.remove_run("active_run")
        session.last_activity = datetime.now(timezone.utc)
        assert session.is_expired(timeout_minutes=60) is False


class TestContextIsolationMetrics:
    """Test ContextIsolationMetrics business logic"""
    
    @pytest.mark.unit
    def test_metrics_initialization(self):
        """Test metrics initialization with default values"""
        metrics = ContextIsolationMetrics()
        
        assert metrics.active_sessions == 0
        assert metrics.active_contexts == 0
        assert metrics.isolation_violations == 0
        assert metrics.context_leaks == 0
        assert metrics.session_timeouts == 0
    
    @pytest.mark.unit
    def test_metrics_reset(self):
        """Test metrics reset functionality"""
        metrics = ContextIsolationMetrics()
        
        # Set some values
        metrics.active_sessions = 5
        metrics.isolation_violations = 2
        metrics.context_leaks = 1
        
        # Reset
        metrics.reset()
        
        assert metrics.active_sessions == 0
        assert metrics.isolation_violations == 0
        assert metrics.context_leaks == 0


class TestAgentExecutionContextManager:
    """Test AgentExecutionContextManager business logic"""
    
    @pytest.mark.unit
    def test_context_manager_initialization(self):
        """Test context manager initialization"""
        manager = AgentExecutionContextManager()
        
        assert len(manager._sessions) == 0
        assert len(manager._user_sessions) == 0
        assert len(manager._context_registry) == 0
        assert manager._lock is not None
        assert isinstance(manager._metrics, ContextIsolationMetrics)
    
    @pytest.mark.unit
    def test_create_execution_session(self):
        """Test execution session creation with proper isolation"""
        manager = AgentExecutionContextManager()
        user_id = UserID("test_user_123")
        thread_id = ThreadID("thread_456")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        
        assert session_id is not None
        assert session_id.startswith("session_")
        assert len(session_id) > 8  # Should have UUID component
        
        # Verify session was created
        session = manager.get_execution_session(session_id)
        assert session is not None
        assert session.user_id == user_id
        assert session.thread_id == thread_id
        assert session.session_id == session_id
        
        # Verify metrics updated
        metrics = manager.get_isolation_metrics()
        assert metrics.active_sessions == 1
        assert metrics.active_contexts == 1
    
    @pytest.mark.unit
    def test_create_session_with_initial_context(self):
        """Test session creation with initial context data"""
        manager = AgentExecutionContextManager()
        user_id = UserID("test_user_123")
        thread_id = ThreadID("thread_456")
        initial_context = {
            "agent_type": "cost_optimizer",
            "priority": "high",
            "custom_setting": "value"
        }
        
        session_id = manager.create_execution_session(
            user_id, thread_id, initial_context
        )
        
        context = manager.get_execution_context(session_id)
        assert context is not None
        assert context.agent_context["agent_type"] == "cost_optimizer"
        assert context.agent_context["priority"] == "high"
        assert context.agent_context["custom_setting"] == "value"
        
        # Should also have isolation metadata
        assert context.agent_context["isolation_boundary"] == str(user_id)
        assert context.agent_context["context_type"] == "isolated_agent_execution"
    
    @pytest.mark.unit
    def test_user_session_isolation(self):
        """Test that different users have completely isolated sessions"""
        manager = AgentExecutionContextManager()
        
        user1_id = UserID("user_1")
        user2_id = UserID("user_2")
        thread_id = ThreadID("thread_123")
        
        # Create sessions for different users
        session1_id = manager.create_execution_session(user1_id, thread_id)
        session2_id = manager.create_execution_session(user2_id, thread_id)
        
        # Sessions should be different
        assert session1_id != session2_id
        
        # Get sessions and verify isolation
        session1 = manager.get_execution_session(session1_id)
        session2 = manager.get_execution_session(session2_id)
        
        assert session1.user_id != session2.user_id
        assert session1.execution_context != session2.execution_context
        
        # Get user sessions
        user1_sessions = manager.get_user_sessions(user1_id)
        user2_sessions = manager.get_user_sessions(user2_id)
        
        assert len(user1_sessions) == 1
        assert len(user2_sessions) == 1
        assert user1_sessions[0].session_id == session1_id
        assert user2_sessions[0].session_id == session2_id
    
    @pytest.mark.unit
    def test_multiple_sessions_same_user(self):
        """Test that same user can have multiple isolated sessions"""
        manager = AgentExecutionContextManager()
        user_id = UserID("multi_session_user")
        
        # Create multiple sessions for same user
        session1_id = manager.create_execution_session(user_id, ThreadID("thread_1"))
        session2_id = manager.create_execution_session(user_id, ThreadID("thread_2"))
        
        # Should be different sessions
        assert session1_id != session2_id
        
        # User should have both sessions
        user_sessions = manager.get_user_sessions(user_id)
        assert len(user_sessions) == 2
        
        session_ids = [s.session_id for s in user_sessions]
        assert session1_id in session_ids
        assert session2_id in session_ids
    
    @pytest.mark.unit
    def test_session_cleanup(self):
        """Test session cleanup and resource deallocation"""
        manager = AgentExecutionContextManager()
        user_id = UserID("cleanup_user")
        thread_id = ThreadID("cleanup_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        
        # Verify session exists
        assert manager.get_execution_session(session_id) is not None
        assert manager.get_execution_context(session_id) is not None
        
        # Cleanup session
        cleanup_result = manager.cleanup_session(session_id)
        assert cleanup_result is True
        
        # Verify session is gone
        assert manager.get_execution_session(session_id) is None
        assert manager.get_execution_context(session_id) is None
        
        # Verify user sessions are updated
        user_sessions = manager.get_user_sessions(user_id)
        assert len(user_sessions) == 0
        
        # Verify metrics updated
        metrics = manager.get_isolation_metrics()
        assert metrics.active_sessions == 0
        assert metrics.active_contexts == 0
    
    @pytest.mark.unit
    def test_cleanup_nonexistent_session(self):
        """Test cleanup of non-existent session"""
        manager = AgentExecutionContextManager()
        
        # Cleanup non-existent session should return False
        result = manager.cleanup_session("non_existent_session")
        assert result is False
    
    @pytest.mark.unit
    def test_context_retrieval_and_validation(self):
        """Test execution context retrieval with isolation validation"""
        manager = AgentExecutionContextManager()
        user_id = UserID("context_user")
        thread_id = ThreadID("context_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        
        # Get context
        context = manager.get_execution_context(session_id)
        assert context is not None
        assert isinstance(context, StronglyTypedUserExecutionContext)
        assert context.user_id == user_id
        assert context.thread_id == thread_id
        
        # Context should have proper isolation
        assert context.agent_context["isolation_boundary"] == str(user_id)
    
    @pytest.mark.unit
    def test_context_updates(self):
        """Test context updates with isolation validation"""
        manager = AgentExecutionContextManager()
        user_id = UserID("update_user")
        thread_id = ThreadID("update_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        
        # Valid updates should succeed
        updates = {
            "current_step": "analyzing_costs",
            "progress": 0.5,
            "metadata": {"tools_used": ["cost_analyzer"]}
        }
        
        result = manager.update_context(session_id, updates)
        assert result is True
        
        # Verify updates applied
        context = manager.get_execution_context(session_id)
        assert context.agent_context["current_step"] == "analyzing_costs"
        assert context.agent_context["progress"] == 0.5
        assert context.agent_context["metadata"]["tools_used"] == ["cost_analyzer"]
    
    @pytest.mark.unit 
    def test_forbidden_context_updates(self):
        """Test that forbidden context updates are rejected"""
        manager = AgentExecutionContextManager()
        user_id = UserID("forbidden_user")
        thread_id = ThreadID("forbidden_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        
        # Forbidden updates should fail
        forbidden_updates = {
            "user_id": "different_user",  # Forbidden
            "isolation_boundary": "hacked",  # Forbidden
            "session_id": "different_session"  # Forbidden
        }
        
        result = manager.update_context(session_id, forbidden_updates)
        assert result is False
        
        # Original context should be unchanged
        context = manager.get_execution_context(session_id)
        assert str(context.user_id) == str(user_id)
        assert context.agent_context["isolation_boundary"] == str(user_id)
    
    @pytest.mark.unit
    def test_run_management(self):
        """Test run registration and unregistration"""
        manager = AgentExecutionContextManager()
        user_id = UserID("run_user")
        thread_id = ThreadID("run_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        session = manager.get_execution_session(session_id)
        
        # Register runs
        assert manager.register_run(session_id, "run_1") is True
        assert manager.register_run(session_id, "run_2") is True
        
        # Verify runs are tracked
        assert len(session.active_runs) == 2
        assert "run_1" in session.active_runs
        assert "run_2" in session.active_runs
        
        # Unregister run
        assert manager.unregister_run(session_id, "run_1") is True
        assert len(session.active_runs) == 1
        assert "run_1" not in session.active_runs
        assert "run_2" in session.active_runs
    
    @pytest.mark.unit
    def test_expired_session_cleanup(self):
        """Test automatic cleanup of expired sessions"""
        manager = AgentExecutionContextManager()
        user_id = UserID("expire_user")
        thread_id = ThreadID("expire_thread")
        
        # Create session and manually set old timestamp
        session_id = manager.create_execution_session(user_id, thread_id)
        session = manager._sessions[session_id]
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Cleanup expired sessions
        cleanup_count = manager.cleanup_expired_sessions()
        assert cleanup_count == 1
        
        # Session should be gone
        assert manager.get_execution_session(session_id) is None
        
        # Metrics should reflect cleanup
        metrics = manager.get_isolation_metrics()
        assert metrics.session_timeouts == 1
    
    @pytest.mark.unit
    def test_isolation_metrics_tracking(self):
        """Test isolation metrics are properly tracked"""
        manager = AgentExecutionContextManager()
        
        # Initial metrics
        metrics = manager.get_isolation_metrics()
        assert metrics.active_sessions == 0
        assert metrics.active_contexts == 0
        assert metrics.isolation_violations == 0
        
        # Create sessions
        user1_id = UserID("metrics_user_1")
        user2_id = UserID("metrics_user_2")
        
        session1_id = manager.create_execution_session(user1_id, ThreadID("thread_1"))
        session2_id = manager.create_execution_session(user2_id, ThreadID("thread_2"))
        
        # Metrics should reflect active sessions
        metrics = manager.get_isolation_metrics()
        assert metrics.active_sessions == 2
        assert metrics.active_contexts == 2
        
        # Cleanup one session
        manager.cleanup_session(session1_id)
        
        metrics = manager.get_isolation_metrics()
        assert metrics.active_sessions == 1
        assert metrics.active_contexts == 1
    
    @pytest.mark.unit
    def test_context_manager_session_lifecycle(self):
        """Test context manager for automatic session lifecycle"""
        manager = AgentExecutionContextManager()
        user_id = UserID("lifecycle_user")
        thread_id = ThreadID("lifecycle_thread")
        
        # Use context manager
        with manager.execution_session_context(user_id, thread_id) as session_id:
            assert session_id is not None
            
            # Session should exist during context
            session = manager.get_execution_session(session_id)
            assert session is not None
            assert session.user_id == user_id
        
        # Session should be cleaned up after context
        session = manager.get_execution_session(session_id)
        assert session is None
    
    @pytest.mark.unit
    def test_thread_safety(self):
        """Test thread safety of context manager operations"""
        manager = AgentExecutionContextManager()
        created_sessions = []
        errors = []
        
        def create_user_session(user_index: int):
            try:
                user_id = UserID(f"user_{user_index}")
                thread_id = ThreadID(f"thread_{user_index}")
                
                session_id = manager.create_execution_session(user_id, thread_id)
                created_sessions.append(session_id)
                
                # Perform some operations
                context = manager.get_execution_context(session_id)
                assert context is not None
                
                manager.register_run(session_id, f"run_{user_index}")
                manager.update_context(session_id, {"step": f"step_{user_index}"})
                
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_user_session, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0
        assert len(created_sessions) == 10
        
        # All sessions should be unique
        assert len(set(created_sessions)) == 10
        
        # Cleanup
        for session_id in created_sessions:
            manager.cleanup_session(session_id)
        
        metrics = manager.get_isolation_metrics()
        assert metrics.active_sessions == 0


class TestContextIsolationValidation:
    """Test context isolation validation business logic"""
    
    @pytest.mark.unit
    def test_context_isolation_validation_success(self):
        """Test successful context isolation validation"""
        manager = AgentExecutionContextManager()
        user_id = UserID("isolation_user")
        thread_id = ThreadID("isolation_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        session = manager.get_execution_session(session_id)
        context = manager.get_execution_context(session_id)
        
        # Valid context should pass isolation validation
        assert manager._validate_context_isolation(context, session) is True
    
    @pytest.mark.unit
    def test_context_isolation_validation_user_mismatch(self):
        """Test context isolation validation fails on user ID mismatch"""
        manager = AgentExecutionContextManager()
        user_id = UserID("original_user")
        thread_id = ThreadID("isolation_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        session = manager.get_execution_session(session_id)
        context = manager.get_execution_context(session_id)
        
        # Modify context user ID to simulate violation
        context.user_id = UserID("different_user")
        
        assert manager._validate_context_isolation(context, session) is False
    
    @pytest.mark.unit
    def test_context_isolation_validation_boundary_violation(self):
        """Test context isolation validation fails on boundary violation"""
        manager = AgentExecutionContextManager()
        user_id = UserID("boundary_user")
        thread_id = ThreadID("boundary_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        session = manager.get_execution_session(session_id)
        context = manager.get_execution_context(session_id)
        
        # Modify isolation boundary to simulate violation
        context.agent_context["isolation_boundary"] = "different_user"
        
        assert manager._validate_context_isolation(context, session) is False
    
    @pytest.mark.unit
    def test_context_updates_validation_success(self):
        """Test context updates validation allows safe updates"""
        manager = AgentExecutionContextManager()
        user_id = UserID("update_user")
        thread_id = ThreadID("update_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        session = manager.get_execution_session(session_id)
        
        safe_updates = {
            "current_tool": "cost_analyzer",
            "progress": 0.75,
            "result_data": {"savings": 1000}
        }
        
        assert manager._validate_context_updates(safe_updates, session) is True
    
    @pytest.mark.unit
    def test_context_updates_validation_forbidden_fields(self):
        """Test context updates validation rejects forbidden fields"""
        manager = AgentExecutionContextManager()
        user_id = UserID("forbidden_user")
        thread_id = ThreadID("forbidden_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        session = manager.get_execution_session(session_id)
        
        forbidden_updates = {
            "user_id": "hacker_user",  # Forbidden
            "safe_field": "safe_value"
        }
        
        assert manager._validate_context_updates(forbidden_updates, session) is False


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_get_session_nonexistent(self):
        """Test getting non-existent session returns None"""
        manager = AgentExecutionContextManager()
        
        session = manager.get_execution_session("non_existent_session")
        assert session is None
    
    @pytest.mark.unit
    def test_get_context_nonexistent_session(self):
        """Test getting context for non-existent session returns None"""
        manager = AgentExecutionContextManager()
        
        context = manager.get_execution_context("non_existent_session")
        assert context is None
    
    @pytest.mark.unit
    def test_update_context_nonexistent_session(self):
        """Test updating context for non-existent session returns False"""
        manager = AgentExecutionContextManager()
        
        result = manager.update_context("non_existent_session", {"key": "value"})
        assert result is False
    
    @pytest.mark.unit
    def test_register_run_nonexistent_session(self):
        """Test registering run with non-existent session returns False"""
        manager = AgentExecutionContextManager()
        
        result = manager.register_run("non_existent_session", "run_123")
        assert result is False
    
    @pytest.mark.unit
    def test_context_without_agent_context(self):
        """Test handling of context without agent_context attribute"""
        manager = AgentExecutionContextManager()
        user_id = UserID("no_agent_context_user")
        thread_id = ThreadID("no_agent_context_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        context = manager.get_execution_context(session_id)
        
        # Remove agent_context to simulate edge case
        context.agent_context = None
        
        # Should handle gracefully
        updates = {"new_field": "value"}
        result = manager.update_context(session_id, updates)
        assert result is True
        
        # Context should have agent_context created
        updated_context = manager.get_execution_context(session_id)
        assert updated_context.agent_context is not None
        assert updated_context.agent_context["new_field"] == "value"
    
    @pytest.mark.unit
    def test_session_expiration_during_retrieval(self):
        """Test session expiration detected during retrieval"""
        manager = AgentExecutionContextManager()
        user_id = UserID("expire_during_get_user")
        thread_id = ThreadID("expire_during_get_thread")
        
        session_id = manager.create_execution_session(user_id, thread_id)
        
        # Manually expire the session
        session = manager._sessions[session_id]
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Getting expired session should return None and clean up
        retrieved_session = manager.get_execution_session(session_id)
        assert retrieved_session is None
        
        # Session should be cleaned up
        assert session_id not in manager._sessions
    
    @pytest.mark.unit
    def test_user_sessions_with_expired_cleanup(self):
        """Test getting user sessions cleans up expired ones"""
        manager = AgentExecutionContextManager()
        user_id = UserID("mixed_expire_user")
        
        # Create multiple sessions for user
        session1_id = manager.create_execution_session(user_id, ThreadID("thread_1"))
        session2_id = manager.create_execution_session(user_id, ThreadID("thread_2"))
        
        # Expire one session
        session1 = manager._sessions[session1_id]
        session1.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Get user sessions should return only active ones
        user_sessions = manager.get_user_sessions(user_id)
        assert len(user_sessions) == 1
        assert user_sessions[0].session_id == session2_id
        
        # Expired session should be cleaned up
        assert session1_id not in manager._sessions
    
    @pytest.mark.unit
    def test_isolation_metrics_edge_cases(self):
        """Test isolation metrics handling edge cases"""
        manager = AgentExecutionContextManager()
        
        # Test metrics don't go negative
        manager._metrics.active_sessions = 1
        manager._cleanup_session("non_existent")  # Should not crash or go negative
        
        metrics = manager.get_isolation_metrics()
        assert metrics.active_sessions >= 0
    
    @pytest.mark.unit 
    def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions properly"""
        manager = AgentExecutionContextManager()
        user_id = UserID("exception_user")
        thread_id = ThreadID("exception_thread")
        
        session_id = None
        try:
            with manager.execution_session_context(user_id, thread_id) as session_id:
                # Session should exist during context
                assert manager.get_execution_session(session_id) is not None
                # Simulate exception
                raise ValueError("Test exception")
                
        except ValueError:
            pass  # Expected exception
        
        # Session should still be cleaned up despite exception
        if session_id:
            assert manager.get_execution_session(session_id) is None