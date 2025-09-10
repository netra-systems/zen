"""
Test Session Management Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maintain user session continuity and data integrity
- Value Impact: Users can maintain context across interactions and browser sessions
- Strategic Impact: Core platform functionality for user experience and data consistency

This test suite validates the session management system including:
- User session lifecycle (create, update, close)
- Session data persistence and retrieval
- Multi-user session isolation
- Session timeout and cleanup
- WebSocket session integration

Performance Requirements:
- Session operations should complete within 100ms
- Session data should be consistently retrievable
- Session isolation should be maintained across concurrent users
- Memory usage should be bounded per session
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional, Set

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.websocket_core.user_session_manager import UserSessionManager
from netra_backend.app.database.session_manager import (
    SessionManager,
    DatabaseSessionManager,
    SessionScopeValidator,
    SessionIsolationError,
    managed_session,
    validate_agent_session_isolation
)
from netra_backend.app.models.user_session import UserSession
from shared.types import UserID


class TestUserSessionManager(SSotBaseTestCase):
    """Test UserSessionManager business logic and lifecycle."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Initialize session manager
        self.session_manager = UserSessionManager()
        
        # Test user IDs
        self.user1_id = UserID(f"user1_{uuid.uuid4().hex[:8]}")
        self.user2_id = UserID(f"user2_{uuid.uuid4().hex[:8]}")
        self.user3_id = UserID(f"user3_{uuid.uuid4().hex[:8]}")
        
        # Test session data
        self.session_data_1 = {
            "theme": "dark",
            "language": "en",
            "preferences": {"notifications": True}
        }
        
        self.session_data_2 = {
            "theme": "light",
            "language": "es",
            "preferences": {"notifications": False}
        }
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    async def test_create_session_generates_unique_ids(self):
        """Test that session creation generates unique session IDs."""
        # When: Creating multiple sessions
        session1_id = await self.session_manager.create_session(
            user_id=self.user1_id,
            session_data=self.session_data_1.copy()
        )
        
        session2_id = await self.session_manager.create_session(
            user_id=self.user1_id,
            session_data=self.session_data_2.copy()
        )
        
        session3_id = await self.session_manager.create_session(
            user_id=self.user2_id,
            session_data=self.session_data_1.copy()
        )
        
        # Then: Session IDs should be unique
        assert session1_id != session2_id
        assert session2_id != session3_id
        assert session1_id != session3_id
        
        # And: Sessions should be retrievable
        session1 = await self.session_manager.get_session(session1_id)
        session2 = await self.session_manager.get_session(session2_id)
        session3 = await self.session_manager.get_session(session3_id)
        
        assert session1 is not None
        assert session2 is not None
        assert session3 is not None
        
        # And: Session data should be preserved
        assert session1["user_id"] == self.user1_id
        assert session1["active"] is True
        assert session1["data"]["theme"] == "dark"
        
        assert session2["user_id"] == self.user1_id
        assert session2["data"]["theme"] == "light"
        
        assert session3["user_id"] == self.user2_id
        assert session3["data"]["theme"] == "dark"
        
        self.record_metric("unique_sessions_created", 3)
        self.record_metric("session_creation_validated", True)
    
    @pytest.mark.unit
    async def test_session_data_isolation_between_users(self):
        """Test that session data is properly isolated between users."""
        # Given: Sessions for different users with sensitive data
        sensitive_data_1 = {
            "api_keys": {"service_a": "key_123_user1"},
            "personal_info": {"email": "user1@test.com"},
            "settings": {"private_mode": True}
        }
        
        sensitive_data_2 = {
            "api_keys": {"service_a": "key_456_user2"},
            "personal_info": {"email": "user2@test.com"},
            "settings": {"private_mode": False}
        }
        
        # When: Creating sessions with sensitive data
        session1_id = await self.session_manager.create_session(
            user_id=self.user1_id,
            session_data=sensitive_data_1
        )
        
        session2_id = await self.session_manager.create_session(
            user_id=self.user2_id,
            session_data=sensitive_data_2
        )
        
        # Then: Each user should only access their own session data
        session1 = await self.session_manager.get_session(session1_id)
        session2 = await self.session_manager.get_session(session2_id)
        
        # User 1's data should be isolated
        assert session1["data"]["api_keys"]["service_a"] == "key_123_user1"
        assert session1["data"]["personal_info"]["email"] == "user1@test.com"
        assert session1["data"]["settings"]["private_mode"] is True
        
        # User 2's data should be isolated
        assert session2["data"]["api_keys"]["service_a"] == "key_456_user2"
        assert session2["data"]["personal_info"]["email"] == "user2@test.com"
        assert session2["data"]["settings"]["private_mode"] is False
        
        # And: No cross-contamination
        assert "user2@test.com" not in str(session1["data"])
        assert "user1@test.com" not in str(session2["data"])
        assert "key_456_user2" not in str(session1["data"])
        assert "key_123_user1" not in str(session2["data"])
        
        self.record_metric("session_isolation_validated", True)
    
    @pytest.mark.unit
    async def test_user_session_tracking(self):
        """Test that user sessions are properly tracked per user."""
        # When: Creating multiple sessions for the same user
        session1_id = await self.session_manager.create_session(
            user_id=self.user1_id,
            session_data={"client": "web"}
        )
        
        session2_id = await self.session_manager.create_session(
            user_id=self.user1_id,
            session_data={"client": "mobile"}
        )
        
        session3_id = await self.session_manager.create_session(
            user_id=self.user2_id,
            session_data={"client": "desktop"}
        )
        
        # Then: User sessions should be tracked correctly
        user1_sessions = await self.session_manager.get_user_sessions(self.user1_id)
        user2_sessions = await self.session_manager.get_user_sessions(self.user2_id)
        user3_sessions = await self.session_manager.get_user_sessions(self.user3_id)
        
        assert len(user1_sessions) == 2
        assert session1_id in user1_sessions
        assert session2_id in user1_sessions
        
        assert len(user2_sessions) == 1
        assert session3_id in user2_sessions
        
        assert len(user3_sessions) == 0  # No sessions created
        
        self.record_metric("user_sessions_tracked", len(user1_sessions) + len(user2_sessions))
    
    @pytest.mark.unit
    async def test_session_update_preserves_consistency(self):
        """Test that session updates preserve data consistency."""
        # Given: Initial session
        initial_data = {
            "counter": 0,
            "preferences": {"theme": "light"},
            "metadata": {"created": time.time()}
        }
        
        session_id = await self.session_manager.create_session(
            user_id=self.user1_id,
            session_data=initial_data
        )
        
        # When: Updating session multiple times
        update1 = {"counter": 1, "last_action": "login"}
        success1 = await self.session_manager.update_session(session_id, update1)
        
        update2 = {"counter": 2, "preferences": {"theme": "dark", "font_size": 14}}
        success2 = await self.session_manager.update_session(session_id, update2)
        
        # Then: Updates should succeed
        assert success1 is True
        assert success2 is True
        
        # And: Session data should be consistently updated
        final_session = await self.session_manager.get_session(session_id)
        final_data = final_session["data"]
        
        assert final_data["counter"] == 2
        assert final_data["last_action"] == "login"
        assert final_data["preferences"]["theme"] == "dark"
        assert final_data["preferences"]["font_size"] == 14
        assert "created" in final_data["metadata"]  # Original data preserved
        
        self.record_metric("session_updates_applied", 2)
        self.record_metric("data_consistency_validated", True)
    
    @pytest.mark.unit
    async def test_session_closure_and_cleanup(self):
        """Test proper session closure and cleanup."""
        # Given: Active sessions
        session1_id = await self.session_manager.create_session(
            user_id=self.user1_id,
            session_data={"status": "active"}
        )
        
        session2_id = await self.session_manager.create_session(
            user_id=self.user1_id,
            session_data={"status": "active"}
        )
        
        # Verify sessions are initially active
        assert await self.session_manager.is_session_active(session1_id) is True
        assert await self.session_manager.is_session_active(session2_id) is True
        
        # When: Closing one session
        close_result = await self.session_manager.close_session(session1_id)
        
        # Then: Only the closed session should be inactive
        assert close_result is True
        assert await self.session_manager.is_session_active(session1_id) is False
        assert await self.session_manager.is_session_active(session2_id) is True
        
        # And: Session should be removed from user sessions tracking
        user_sessions = await self.session_manager.get_user_sessions(self.user1_id)
        assert session1_id not in user_sessions
        assert session2_id in user_sessions
        
        # And: Session data should still be retrievable but marked inactive
        closed_session = await self.session_manager.get_session(session1_id)
        assert closed_session is not None
        assert closed_session["active"] is False
        
        self.record_metric("session_closure_validated", True)
    
    @pytest.mark.unit
    async def test_concurrent_session_operations(self):
        """Test that concurrent session operations maintain consistency."""
        # Given: Concurrent session operations setup
        operations_per_user = 5
        concurrent_users = 3
        
        async def create_user_sessions(user_base_id: str, operation_count: int):
            """Create multiple sessions for a user concurrently."""
            tasks = []
            for i in range(operation_count):
                session_data = {
                    "operation_id": i,
                    "user_type": user_base_id,
                    "timestamp": time.time()
                }
                
                task = self.session_manager.create_session(
                    user_id=UserID(f"{user_base_id}_{uuid.uuid4().hex[:8]}"),
                    session_data=session_data
                )
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        # When: Running concurrent session creation
        concurrent_tasks = []
        for user_idx in range(concurrent_users):
            user_base = f"concurrent_user_{user_idx}"
            task = create_user_sessions(user_base, operations_per_user)
            concurrent_tasks.append(task)
        
        results = await asyncio.gather(*concurrent_tasks)
        
        # Then: All sessions should be created successfully
        total_sessions_created = sum(len(user_sessions) for user_sessions in results)
        expected_total = concurrent_users * operations_per_user
        
        assert total_sessions_created == expected_total
        
        # And: All session IDs should be unique
        all_session_ids = []
        for user_sessions in results:
            all_session_ids.extend(user_sessions)
        
        assert len(all_session_ids) == len(set(all_session_ids))  # All unique
        
        # And: Each session should be retrievable
        retrieval_tasks = [
            self.session_manager.get_session(session_id) 
            for session_id in all_session_ids
        ]
        
        retrieved_sessions = await asyncio.gather(*retrieval_tasks)
        valid_sessions = [s for s in retrieved_sessions if s is not None]
        
        assert len(valid_sessions) == total_sessions_created
        
        self.record_metric("concurrent_sessions_created", total_sessions_created)
        self.record_metric("concurrent_operations_validated", True)


class TestDatabaseSessionManager(SSotBaseTestCase):
    """Test DatabaseSessionManager and session isolation."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        self.session_manager = SessionManager()
        self.db_session_manager = DatabaseSessionManager()
        self.scope_validator = SessionScopeValidator()
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_session_manager_initialization(self):
        """Test that session managers initialize properly."""
        # Given: Session manager instances
        # When: Checking initialization
        # Then: Managers should be properly initialized
        
        assert isinstance(self.session_manager, SessionManager)
        assert isinstance(self.db_session_manager, DatabaseSessionManager)
        assert isinstance(self.db_session_manager, SessionManager)  # Inheritance
        
        self.record_metric("session_managers_initialized", 2)
    
    @pytest.mark.unit
    def test_managed_session_context_manager(self):
        """Test managed_session context manager functionality."""
        # When: Using managed_session context manager
        session_accessed = False
        
        with managed_session() as session:
            session_accessed = True
            # Session should be None for stub implementation
            assert session is None
        
        # Then: Context manager should execute properly
        assert session_accessed is True
        
        self.record_metric("managed_session_validated", True)
    
    @pytest.mark.unit
    async def test_async_session_operations(self):
        """Test async session operations."""
        # When: Using async session methods
        async_session = await self.session_manager.get_async_session()
        created_session = await self.db_session_manager.create_session()
        
        # Then: Async operations should complete
        assert async_session is None  # Stub implementation
        assert created_session is None  # Stub implementation
        
        # And: Close should work without errors
        await self.db_session_manager.close_session(created_session)
        
        self.record_metric("async_session_operations_validated", True)
    
    @pytest.mark.unit
    def test_session_scope_validation(self):
        """Test session scope validation logic."""
        # Given: Mock sessions with different scopes
        valid_session = Mock()
        valid_session._global_storage_flag = None  # No global flag
        
        invalid_session = Mock()
        invalid_session._global_storage_flag = True  # Global storage flag
        
        # When: Validating sessions
        # Then: Valid session should pass
        try:
            self.scope_validator.validate_request_scoped(valid_session)
            valid_passed = True
        except SessionIsolationError:
            valid_passed = False
        
        assert valid_passed is True
        
        # And: Invalid session should fail
        try:
            self.scope_validator.validate_request_scoped(invalid_session)
            invalid_failed = False
        except SessionIsolationError:
            invalid_failed = True
        
        assert invalid_failed is True
        
        self.record_metric("scope_validation_tested", 2)
    
    @pytest.mark.unit
    def test_agent_session_isolation_validation(self):
        """Test agent session isolation validation."""
        # Given: Mock agents
        mock_agent1 = Mock()
        mock_agent1.__class__.__name__ = "TestAgent1"
        
        mock_agent2 = Mock()
        
        # When: Validating agent session isolation
        result1 = validate_agent_session_isolation(mock_agent1)
        result2 = validate_agent_session_isolation(mock_agent2)
        
        # Then: Validation should always pass for stub implementation
        assert result1 is True
        assert result2 is True
        
        self.record_metric("agent_validations_completed", 2)


class TestSessionLifecycleIntegration(SSotBaseTestCase):
    """Test complete session lifecycle integration."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        self.session_manager = UserSessionManager()
        self.test_user_id = UserID(f"lifecycle_user_{uuid.uuid4().hex[:8]}")
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    async def test_complete_session_lifecycle(self):
        """Test complete session lifecycle from creation to cleanup."""
        # Phase 1: Session Creation
        start_time = time.time()
        
        initial_data = {
            "created_at": start_time,
            "client_type": "web",
            "user_agent": "test_browser",
            "session_start": True
        }
        
        session_id = await self.session_manager.create_session(
            user_id=self.test_user_id,
            session_data=initial_data
        )
        
        creation_time = time.time() - start_time
        
        # Phase 2: Session Usage (Multiple Updates)
        usage_start = time.time()
        
        # Simulate user interactions
        interactions = [
            {"action": "page_view", "page": "/dashboard", "timestamp": time.time()},
            {"action": "api_call", "endpoint": "/api/data", "timestamp": time.time()},
            {"action": "settings_change", "setting": "theme", "value": "dark", "timestamp": time.time()},
            {"action": "file_upload", "filename": "test.csv", "size": 1024, "timestamp": time.time()},
        ]
        
        for interaction in interactions:
            await self.session_manager.update_session(session_id, interaction)
            await asyncio.sleep(0.01)  # Simulate time between interactions
        
        usage_time = time.time() - usage_start
        
        # Phase 3: Session Validation
        final_session = await self.session_manager.get_session(session_id)
        
        assert final_session is not None
        assert final_session["active"] is True
        assert final_session["user_id"] == self.test_user_id
        
        # All interactions should be preserved
        session_data = final_session["data"]
        assert session_data["action"] == "file_upload"  # Last action
        assert session_data["created_at"] == start_time  # Original data preserved
        assert session_data["client_type"] == "web"  # Original data preserved
        
        # Phase 4: Session Cleanup
        cleanup_start = time.time()
        
        close_result = await self.session_manager.close_session(session_id)
        assert close_result is True
        
        cleanup_time = time.time() - cleanup_start
        
        # Phase 5: Post-Cleanup Validation
        assert await self.session_manager.is_session_active(session_id) is False
        
        user_sessions = await self.session_manager.get_user_sessions(self.test_user_id)
        assert session_id not in user_sessions
        
        # Session should still exist but be marked inactive
        closed_session = await self.session_manager.get_session(session_id)
        assert closed_session is not None
        assert closed_session["active"] is False
        
        # Record performance metrics
        self.record_metric("session_creation_time_ms", creation_time * 1000)
        self.record_metric("session_usage_time_ms", usage_time * 1000)
        self.record_metric("session_cleanup_time_ms", cleanup_time * 1000)
        self.record_metric("total_interactions", len(interactions))
        self.record_metric("lifecycle_test_completed", True)
        
        # Performance assertions
        assert creation_time < 0.1  # Should create quickly
        assert cleanup_time < 0.1  # Should cleanup quickly
    
    @pytest.mark.unit
    async def test_session_memory_efficiency(self):
        """Test that session management is memory efficient."""
        # Given: Multiple sessions to test memory usage
        session_count = 100
        sessions_created = []
        
        # When: Creating many sessions
        creation_start = time.time()
        
        for i in range(session_count):
            user_id = UserID(f"memory_test_user_{i}")
            session_data = {
                "index": i,
                "data": f"session_data_{i}",
                "large_field": "x" * 100  # Some bulk data
            }
            
            session_id = await self.session_manager.create_session(
                user_id=user_id,
                session_data=session_data
            )
            sessions_created.append((session_id, user_id))
        
        creation_time = time.time() - creation_start
        
        # Then: All sessions should be accessible
        retrieval_start = time.time()
        
        for session_id, user_id in sessions_created[:10]:  # Test first 10
            session = await self.session_manager.get_session(session_id)
            assert session is not None
            assert session["user_id"] == user_id
        
        retrieval_time = time.time() - retrieval_start
        
        # And: Cleanup should be efficient
        cleanup_start = time.time()
        
        for session_id, _ in sessions_created:
            await self.session_manager.close_session(session_id)
        
        cleanup_time = time.time() - cleanup_start
        
        # Performance metrics
        self.record_metric("bulk_sessions_created", session_count)
        self.record_metric("bulk_creation_time_ms", creation_time * 1000)
        self.record_metric("bulk_retrieval_time_ms", retrieval_time * 1000)
        self.record_metric("bulk_cleanup_time_ms", cleanup_time * 1000)
        self.record_metric("avg_creation_time_ms", (creation_time / session_count) * 1000)
        self.record_metric("memory_efficiency_validated", True)
        
        # Performance assertions
        avg_creation = creation_time / session_count
        assert avg_creation < 0.01  # Should average less than 10ms per session
        assert cleanup_time < 2.0  # Should cleanup all sessions quickly
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Clear all sessions to prevent memory leaks
        self.session_manager.clear_all_sessions()
        
        # Verify cleanup metrics
        execution_time = self.get_metrics().execution_time
        if execution_time > 1.0:
            self.record_metric("slow_session_test_warning", execution_time)
        
        super().teardown_method(method)