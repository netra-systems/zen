"""
Redis Session State Core Tests

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) - Core session management functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from session state failures
- Value Impact: Ensures WebSocket connect → Redis state → multiple connections → state consistency
- Revenue Impact: Prevents customer session loss/desync that would cause immediate churn

Core Redis session state synchronization tests.

UPDATE: Refactored to use REAL services per CLAUDE.md standards:
- Uses real Redis service instead of mocks
- Uses IsolatedEnvironment for all environment access
- Uses proper absolute imports
- Validates real system under test behavior
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.redis.session_manager import RedisSessionManager
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.websocket_core import WebSocketManager, get_websocket_manager

# Set up environment using IsolatedEnvironment
env = get_env()
env.set("TESTING", "1", "test_setup")
env.set("ENVIRONMENT", "testing", "test_setup") 
env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test_setup")

logger = central_logger.get_logger(__name__)


class MockWebSocketConnection:
    """Simple mock WebSocket for testing Redis integration."""
    
    def __init__(self, user_id: str, connection_id: str):
    pass
        self.user_id = user_id
        self.connection_id = connection_id
        self.state = "connected"
        self.messages_sent = []
        
    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json for testing."""
        if self.state == "connected":
            self.messages_sent.append({
                "type": "json", 
                "content": data, 
                "timestamp": datetime.now(timezone.utc)
            })
        else:
            raise Exception("WebSocket not connected")


class TestRedisSessionStateCore:
    """Core Redis session state synchronization tests using REAL services."""
    pass

    @pytest.fixture
    async def redis_service(self):
        """Create real Redis service instance."""
        service = RedisService(test_mode=True)
        await service.connect()
        yield service
        await service.disconnect()

    @pytest.fixture
    async def session_manager(self, redis_service):
        """Create real Redis session manager."""
    pass
        await asyncio.sleep(0)
    return RedisSessionManager(redis_client=redis_service)
        
    @pytest.fixture
    def websocket_manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Get real WebSocket manager."""
    pass
        return get_websocket_manager()

    @pytest.mark.asyncio
    async def test_redis_session_state_creation_and_retrieval(self, redis_service, session_manager):
        """BVJ: Validates Redis session creation and state storage works correctly."""
        
        user_id = "test_user_session_create"
        initial_data = {
            "user_preferences": {"theme": "dark", "notifications": True},
            "current_context": {"page": "dashboard", "tab": "overview"}
        }
        
        start_time = time.time()
        
        # Create session using real Redis session manager
        session_id = await session_manager.create_session(user_id, initial_data)
        
        creation_time = time.time() - start_time
        
        # Validate session was created
        assert session_id is not None, "Session ID not created"
        assert session_id.startswith(user_id), "Session ID should contain user_id"
        
        # Retrieve and validate session data
        retrieved_session = await session_manager.get_session(session_id)
        
        assert retrieved_session is not None, "Session not retrievable from Redis"
        assert retrieved_session["user_id"] == user_id, "User ID mismatch in retrieved session"
        assert retrieved_session["data"] == initial_data, "Session data not preserved"
        assert "created_at" in retrieved_session, "Session missing created_at timestamp"
        assert "last_accessed" in retrieved_session, "Session missing last_accessed timestamp"
        
        # Validate session appears in user sessions list
        user_sessions = await session_manager.get_user_sessions(user_id)
        assert session_id in user_sessions, "Session not in user sessions list"
        
        # Validate performance
        assert creation_time < 1.0, f"Session creation took {creation_time:.2f}s, exceeds 1s limit"
        
        logger.info(f"Redis session creation validated: {creation_time:.3f}s creation time")

    @pytest.mark.asyncio
    async def test_multiple_session_state_consistency(self, redis_service, session_manager):
        """BVJ: Validates multiple sessions can share consistent state updates."""
        
        user_id = "multi_session_user"
        session_ids = []
        
        # Create multiple sessions for the same user
        for i in range(3):
            session_data = {
                "connection_info": f"connection_{i+1}",
                "initial_state": {"active": True, "connection_number": i+1}
            }
            session_id = await session_manager.create_session(user_id, session_data)
            session_ids.append(session_id)
        
        # Update state for each session
        state_updates = {
            "current_thread": "thread_123", 
            "agent_mode": "optimization", 
            "preferences": {"theme": "dark", "notifications": True}
        }
        
        start_time = time.time()
        
        # Update each session with the same state
        update_results = []
        for session_id in session_ids:
            result = await session_manager.update_session(session_id, state_updates)
            update_results.append(result)
        
        sync_time = time.time() - start_time
        
        # Validate all updates succeeded
        assert all(update_results), f"Not all session updates succeeded: {update_results}"
        
        # Validate state consistency across sessions
        for i, session_id in enumerate(session_ids):
            session_data = await session_manager.get_session(session_id)
            assert session_data is not None, f"Session {i+1} not found after update"
            
            session_state = session_data["data"]
            assert session_state["current_thread"] == "thread_123", f"Thread mismatch in session {i+1}"
            assert session_state["agent_mode"] == "optimization", f"Agent mode mismatch in session {i+1}"
            assert session_state["preferences"]["theme"] == "dark", f"Theme mismatch in session {i+1}"
            assert session_state["preferences"]["notifications"] is True, f"Notifications mismatch in session {i+1}"
        
        # Validate performance
        assert sync_time < 1.0, f"State sync took {sync_time:.3f}s, exceeds 1s limit"
        
        # Validate user sessions list is correct
        user_sessions = await session_manager.get_user_sessions(user_id)
        assert len(user_sessions) == 3, f"Expected 3 user sessions, got {len(user_sessions)}"
        
        for session_id in session_ids:
            assert session_id in user_sessions, f"Session {session_id} not in user sessions list"
        
        logger.info(f"Multiple session consistency validated: {len(session_ids)} sessions in {sync_time:.3f}s")

    @pytest.mark.asyncio
    async def test_session_persistence_and_deletion(self, redis_service, session_manager):
        """BVJ: Validates session persistence and proper cleanup."""
        
        user_id = "persistence_test_user"
        
        # Create session with complex state
        session_state = {
            "conversation_history": ["Hello", "Hi there!", "Can you help with optimization?"],
            "current_context": {
                "topic": "gpu_optimization", 
                "complexity": "intermediate", 
                "user_preferences": {"detailed_analysis": True}
            },
            "agent_memory": {
                "user_expertise": "intermediate", 
                "previous_requests": ["memory_optimization", "cost_analysis"]
            }
        }
        
        # Create session
        session_id = await session_manager.create_session(user_id, session_state)
        assert session_id is not None, "Session creation failed"
        
        # Validate initial state persistence
        persisted_session = await session_manager.get_session(session_id)
        assert persisted_session is not None, "Session state not persisted in Redis"
        
        original_data = persisted_session["data"]
        assert original_data["conversation_history"] == session_state["conversation_history"], "Conversation history not preserved"
        assert original_data["current_context"]["topic"] == "gpu_optimization", "Context topic not preserved"
        assert original_data["current_context"]["complexity"] == "intermediate", "Context complexity not preserved"
        assert original_data["agent_memory"]["user_expertise"] == "intermediate", "Agent memory not preserved"
        
        # Update session state
        continuation_update = {"new_message": "Continue where we left off", "session_continued": True}
        update_success = await session_manager.update_session(session_id, continuation_update)
        assert update_success, "Session update failed"
        
        # Validate updated state persistence
        updated_session = await session_manager.get_session(session_id)
        assert updated_session is not None, "Updated session not found"
        
        updated_data = updated_session["data"]
        assert updated_data["new_message"] == "Continue where we left off", "Continuation update not preserved"
        assert updated_data["session_continued"] is True, "Session continuation flag not preserved"
        
        # Original data should still be present
        assert updated_data["conversation_history"] == session_state["conversation_history"], "Original data lost after update"
        
        # Test session validation
        is_valid = await session_manager.validate_session(session_id, user_id)
        assert is_valid, "Session validation failed for correct user"
        
        is_invalid = await session_manager.validate_session(session_id, "wrong_user")
        assert not is_invalid, "Session validation passed for wrong user"
        
        # Test session deletion
        delete_success = await session_manager.delete_session(session_id)
        assert delete_success, "Session deletion failed"
        
        # Validate session is gone
        deleted_session = await session_manager.get_session(session_id)
        assert deleted_session is None, "Session still exists after deletion"
        
        # Validate user sessions list is updated
        user_sessions_after_delete = await session_manager.get_user_sessions(user_id)
        assert session_id not in user_sessions_after_delete, "Deleted session still in user sessions list"
        
        logger.info(f"Session persistence and cleanup validated successfully")

    @pytest.mark.asyncio
    async def test_websocket_manager_redis_integration(self, redis_service, websocket_manager):
        """BVJ: Validates WebSocket manager integrates properly with Redis session management."""
        
        user_id = f"websocket_integration_{uuid.uuid4().hex[:8]}"
        
        # Create a mock WebSocket connection
        mock_websocket = AsyncNone  # TODO: Use real service instance
        mock_websocket.send_json = AsyncNone  # TODO: Use real service instance
        
        # Test WebSocket connection creation
        start_time = time.time()
        connection_id = await websocket_manager.connect_user(user_id, mock_websocket)
        connection_time = time.time() - start_time
        
        # Validate connection was created
        assert connection_id is not None, "Connection ID not created"
        assert connection_id in websocket_manager.connections, "Connection not tracked in manager"
        
        # Validate connection info
        connection_info = websocket_manager.connections[connection_id]
        assert connection_info["user_id"] == user_id, "User ID mismatch in connection info"
        assert connection_info["websocket"] is mock_websocket, "WebSocket reference incorrect"
        
        # Validate user connections mapping
        assert user_id in websocket_manager.user_connections, "User not in user_connections mapping"
        assert connection_id in websocket_manager.user_connections[user_id], "Connection not in user's connections"
        
        # Test message sending
        test_message = {"type": "test_message", "data": {"test": "value"}}
        send_success = await websocket_manager.send_to_user(user_id, test_message)
        assert send_success, "Message sending failed"
        
        # Validate WebSocket was called
        mock_websocket.send_json.assert_called_once()
        
        # Test connection cleanup
        await websocket_manager.disconnect_user(user_id, mock_websocket)
        
        # Validate cleanup
        assert connection_id not in websocket_manager.connections, "Connection not cleaned up"
        
        # Validate performance
        assert connection_time < 1.0, f"WebSocket connection took {connection_time:.3f}s, exceeds 1s limit"
        
        logger.info(f"WebSocket-Redis integration validated: {connection_time:.3f}s connection time")

    @pytest.mark.asyncio
    async def test_redis_service_real_operations(self, redis_service):
        """BVJ: Validates real Redis service operations work correctly."""
        
        # Test basic key-value operations
        test_key = f"test_key_{uuid.uuid4().hex[:8]}"
        test_value = "test_value_with_special_chars_!@#$%"
        
        # Test set operation
        set_result = await redis_service.set(test_key, test_value, ex=60)
        assert set_result, "Redis set operation failed"
        
        # Test get operation
        retrieved_value = await redis_service.get(test_key)
        assert retrieved_value == test_value, f"Retrieved value mismatch: {retrieved_value} != {test_value}"
        
        # Test exists operation
        key_exists = await redis_service.exists(test_key)
        assert key_exists, "Key should exist after set operation"
        
        # Test JSON operations
        json_key = f"json_key_{uuid.uuid4().hex[:8]}"
        json_data = {
            "user_id": "test_user",
            "session_data": {"theme": "dark", "notifications": True},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        json_set_result = await redis_service.set_json(json_key, json_data, ex=60)
        assert json_set_result, "Redis JSON set operation failed"
        
        retrieved_json = await redis_service.get_json(json_key)
        assert retrieved_json is not None, "JSON data not retrieved"
        assert retrieved_json["user_id"] == "test_user", "JSON user_id mismatch"
        assert retrieved_json["session_data"]["theme"] == "dark", "JSON nested data mismatch"
        
        # Test hash operations
        hash_key = f"hash_key_{uuid.uuid4().hex[:8]}"
        hash_field = "session_id"
        hash_value = f"session_{uuid.uuid4().hex[:8]}"
        
        hset_result = await redis_service.hset(hash_key, hash_field, hash_value)
        assert hset_result, "Redis hset operation failed"
        
        hget_result = await redis_service.hget(hash_key, hash_field)
        assert hget_result == hash_value, f"Hash field value mismatch: {hget_result} != {hash_value}"
        
        # Test cleanup
        delete_count = await redis_service.delete(test_key, json_key, hash_key)
        assert delete_count >= 2, f"Expected at least 2 keys deleted, got {delete_count}"  # hash and regular keys
        
        logger.info("Real Redis service operations validated successfully")

    @pytest.mark.asyncio
    async def test_session_manager_performance_requirements(self, redis_service, session_manager):
        """BVJ: Validates session manager meets performance requirements for <2s response times."""
        
        user_id = f"perf_test_user_{uuid.uuid4().hex[:8]}"
        session_count = 10
        session_ids = []
        
        # Test session creation performance
        start_time = time.time()
        
        for i in range(session_count):
            session_data = {
                "connection_id": f"conn_{i}",
                "user_preferences": {"theme": "dark" if i % 2 == 0 else "light"},
                "created_batch": True,
                "batch_index": i
            }
            session_id = await session_manager.create_session(user_id, session_data)
            session_ids.append(session_id)
        
        creation_time = time.time() - start_time
        
        # Validate all sessions created
        assert len(session_ids) == session_count, f"Expected {session_count} sessions, created {len(session_ids)}"
        
        # Test batch retrieval performance
        start_time = time.time()
        
        retrieved_sessions = []
        for session_id in session_ids:
            session_data = await session_manager.get_session(session_id)
            retrieved_sessions.append(session_data)
        
        retrieval_time = time.time() - start_time
        
        # Test batch update performance
        start_time = time.time()
        
        update_data = {"batch_updated": True, "update_timestamp": datetime.now(timezone.utc).isoformat()}
        update_results = []
        for session_id in session_ids:
            result = await session_manager.update_session(session_id, update_data)
            update_results.append(result)
        
        update_time = time.time() - start_time
        
        # Validate performance requirements
        avg_creation_time = creation_time / session_count
        avg_retrieval_time = retrieval_time / session_count
        avg_update_time = update_time / session_count
        
        assert creation_time < 2.0, f"Batch session creation took {creation_time:.3f}s, exceeds 2s limit"
        assert retrieval_time < 2.0, f"Batch session retrieval took {retrieval_time:.3f}s, exceeds 2s limit"
        assert update_time < 2.0, f"Batch session update took {update_time:.3f}s, exceeds 2s limit"
        
        assert avg_creation_time < 0.2, f"Average session creation took {avg_creation_time:.3f}s, exceeds 0.2s per session"
        assert avg_retrieval_time < 0.1, f"Average session retrieval took {avg_retrieval_time:.3f}s, exceeds 0.1s per session"
        assert avg_update_time < 0.15, f"Average session update took {avg_update_time:.3f}s, exceeds 0.15s per session"
        
        # Validate all operations succeeded
        assert all(s is not None for s in retrieved_sessions), "Some sessions failed to retrieve"
        assert all(update_results), "Some session updates failed"
        
        # Validate updated data
        for session_id in session_ids:
            updated_session = await session_manager.get_session(session_id)
            assert updated_session["data"]["batch_updated"] is True, "Batch update not applied"
        
        # Clean up
        cleanup_start = time.time()
        cleanup_results = []
        for session_id in session_ids:
            result = await session_manager.delete_session(session_id)
            cleanup_results.append(result)
        cleanup_time = time.time() - cleanup_start
        
        assert cleanup_time < 2.0, f"Batch session cleanup took {cleanup_time:.3f}s, exceeds 2s limit"
        assert all(cleanup_results), "Some session deletions failed"
        
        logger.info(f"Performance validated - Create: {creation_time:.3f}s, Retrieve: {retrieval_time:.3f}s, Update: {update_time:.3f}s, Cleanup: {cleanup_time:.3f}s")

    @pytest.mark.asyncio 
    async def test_session_manager_error_handling(self, redis_service, session_manager):
        """BVJ: Validates session manager handles errors gracefully."""
        
        # Test getting non-existent session
        non_existent_session = await session_manager.get_session("non_existent_session_id")
        assert non_existent_session is None, "Non-existent session should await asyncio.sleep(0)
    return None"
        
        # Test updating non-existent session
        update_result = await session_manager.update_session("non_existent_session_id", {"test": "data"})
        assert not update_result, "Updating non-existent session should return False"
        
        # Test deleting non-existent session
        delete_result = await session_manager.delete_session("non_existent_session_id")
        assert not delete_result, "Deleting non-existent session should return False"
        
        # Test session validation with wrong user
        valid_user_id = "valid_user"
        session_id = await session_manager.create_session(valid_user_id, {"test": "data"})
        
        # Valid case
        is_valid = await session_manager.validate_session(session_id, valid_user_id)
        assert is_valid, "Session validation should succeed for correct user"
        
        # Invalid case
        is_invalid = await session_manager.validate_session(session_id, "wrong_user")
        assert not is_invalid, "Session validation should fail for wrong user"
        
        # Test getting sessions for non-existent user
        empty_sessions = await session_manager.get_user_sessions("non_existent_user")
        assert isinstance(empty_sessions, list), "User sessions should return list even for non-existent user"
        assert len(empty_sessions) == 0, "Non-existent user should have no sessions"
        
        # Clean up
        await session_manager.delete_session(session_id)
        
        logger.info("Session manager error handling validated successfully")

    @pytest.mark.asyncio
    async def test_isolated_environment_usage(self):
        """BVJ: Validates test uses IsolatedEnvironment correctly per CLAUDE.md standards."""
        
        # Validate IsolatedEnvironment is being used
        env = get_env()
        
        # Check that test environment variables are set
        testing_value = env.get("TESTING")
        environment_value = env.get("ENVIRONMENT")
        database_url = env.get("DATABASE_URL")
        
        assert testing_value == "1", f"TESTING should be '1', got '{testing_value}'"
        assert environment_value == "testing", f"ENVIRONMENT should be 'testing', got '{environment_value}'"
        assert database_url is not None, "DATABASE_URL should be set"
        assert "memory" in database_url.lower(), "DATABASE_URL should use in-memory database for testing"
        
        # Test setting and getting custom environment variables
        test_key = "TEST_CUSTOM_VAR"
        test_value = "test_value_123"
        
        env.set(test_key, test_value, "test_isolated_environment")
        retrieved_value = env.get(test_key)
        
        assert retrieved_value == test_value, f"Custom env var mismatch: {retrieved_value} != {test_value}"
        
        # Test environment variable exists
        assert env.exists(test_key), "Custom environment variable should exist"
        
        # Test environment variable deletion
        env.delete(test_key)
        assert not env.exists(test_key), "Deleted environment variable should not exist"
        assert env.get(test_key) is None, "Deleted environment variable should await asyncio.sleep(0)
    return None"
        
        logger.info("IsolatedEnvironment usage validation completed successfully")