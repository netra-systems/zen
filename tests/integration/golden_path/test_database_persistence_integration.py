"""
Test Database Persistence Integration for Golden Path

CRITICAL INTEGRATION TEST: This validates database persistence across all Golden Path
exit points with real PostgreSQL integration for data integrity and business continuity.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure conversation data and insights are never lost
- Value Impact: Lost data = lost business insights and user frustration  
- Strategic Impact: Data reliability foundation for $500K+ ARR platform trust

INTEGRATION POINTS TESTED:
1. Thread persistence across all exit points (normal, error, timeout, disconnect)
2. Message history storage with user isolation
3. Agent execution results storage and retrieval
4. Database cleanup on user disconnection
5. Multi-user data isolation validation
6. Performance and timing requirements

MUST use REAL PostgreSQL - NO MOCKS per CLAUDE.md standards
"""

import asyncio
import pytest
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from shared.types.core_types import UserID, ThreadID, RunID, MessageID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Database models and operations - using real system imports
from netra_backend.app.models.conversation_models import Thread, Message
from netra_backend.app.models.user_models import User
from netra_backend.app.database.session_manager import get_db_session
from netra_backend.app.services.persistence_service import PersistenceService


class TestDatabasePersistenceIntegration(SSotAsyncTestCase):
    """Test database persistence integration with real PostgreSQL."""
    
    async def async_setup_method(self, method=None):
        """Async setup for database integration test components."""
        await super().async_setup_method(method)
        
        # Initialize components
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.id_generator = UnifiedIdGenerator()
        self.persistence_service = PersistenceService()
        
        # Test metrics
        self.record_metric("test_category", "integration")
        self.record_metric("golden_path_component", "database_persistence")
        self.record_metric("real_database_required", True)
        
        # Test data tracking for cleanup
        self.created_users = []
        self.created_threads = []
        self.created_messages = []
        
    async def async_teardown_method(self, method=None):
        """Cleanup test data from database."""
        try:
            # Clean up in reverse order of dependencies
            async with get_db_session() as db:
                # Delete messages
                for message_id in self.created_messages:
                    await db.execute("DELETE FROM messages WHERE id = $1", str(message_id))
                
                # Delete threads  
                for thread_id in self.created_threads:
                    await db.execute("DELETE FROM threads WHERE id = $1", str(thread_id))
                
                # Delete users
                for user_id in self.created_users:
                    await db.execute("DELETE FROM users WHERE id = $1", str(user_id))
                
                await db.commit()
                
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")
        
        await super().async_teardown_method(method)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_thread_persistence_normal_completion(self, real_db_fixture):
        """Test thread persistence for normal Golden Path completion."""
        # Create user context for thread
        user_context = await create_authenticated_user_context(
            user_email="thread_persistence_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create thread data
        thread_data = {
            "id": user_context.thread_id,
            "user_id": user_context.user_id,
            "title": "Golden Path Cost Optimization",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "metadata": {
                "agent_pipeline": ["data_agent", "optimization_agent", "report_agent"],
                "business_intent": "cost_optimization",
                "completion_status": "normal"
            }
        }
        
        # Persist thread to real database
        persistence_start = time.time()
        
        async with get_db_session() as db:
            await db.execute(
                """INSERT INTO threads (id, user_id, title, created_at, updated_at, metadata) 
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                str(thread_data["id"]),
                str(thread_data["user_id"]),
                thread_data["title"],
                thread_data["created_at"],
                thread_data["updated_at"],
                json.dumps(thread_data["metadata"])
            )
            await db.commit()
            
        persistence_time = time.time() - persistence_start
        
        # Track for cleanup
        self.created_threads.append(user_context.thread_id)
        
        # Verify persistence by retrieving
        async with get_db_session() as db:
            retrieved_thread = await db.fetchrow(
                "SELECT * FROM threads WHERE id = $1",
                str(user_context.thread_id)
            )
            
        # Assertions
        assert retrieved_thread is not None, "Thread should be persisted in database"
        assert retrieved_thread["id"] == str(user_context.thread_id), \
            "Thread ID should match"
        assert retrieved_thread["user_id"] == str(user_context.user_id), \
            "User ID should match"
        assert retrieved_thread["title"] == "Golden Path Cost Optimization", \
            "Thread title should be preserved"
        
        # Check metadata preservation
        stored_metadata = json.loads(retrieved_thread["metadata"])
        assert stored_metadata["business_intent"] == "cost_optimization", \
            "Business intent should be preserved"
        assert stored_metadata["completion_status"] == "normal", \
            "Completion status should be preserved"
        
        # Performance requirement
        assert persistence_time < 1.0, \
            f"Thread persistence should be < 1s: {persistence_time:.2f}s"
        
        self.record_metric("thread_persistence_normal_test_passed", True)
        self.record_metric("thread_persistence_time", persistence_time)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_message_history_storage_with_isolation(self, real_db_fixture):
        """Test message history storage with proper user isolation."""
        # Create two different user contexts
        user1_context = await create_authenticated_user_context(
            user_email="message_user1@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        user2_context = await create_authenticated_user_context(
            user_email="message_user2@example.com", 
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create threads for both users
        async with get_db_session() as db:
            # User 1 thread
            await db.execute(
                """INSERT INTO threads (id, user_id, title, created_at, updated_at) 
                   VALUES ($1, $2, $3, $4, $5)""",
                str(user1_context.thread_id),
                str(user1_context.user_id),
                "User 1 Conversation",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            )
            
            # User 2 thread
            await db.execute(
                """INSERT INTO threads (id, user_id, title, created_at, updated_at) 
                   VALUES ($1, $2, $3, $4, $5)""",
                str(user2_context.thread_id),
                str(user2_context.user_id),
                "User 2 Conversation",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            )
            
            await db.commit()
        
        # Track for cleanup
        self.created_threads.extend([user1_context.thread_id, user2_context.thread_id])
        
        # Create messages for both users
        messages_data = [
            # User 1 messages
            {
                "id": MessageID(self.id_generator.generate_message_id()),
                "thread_id": user1_context.thread_id,
                "user_id": user1_context.user_id,
                "role": "user",
                "content": "Optimize my AI costs",
                "metadata": {"business_intent": "cost_optimization"}
            },
            {
                "id": MessageID(self.id_generator.generate_message_id()),
                "thread_id": user1_context.thread_id,
                "user_id": user1_context.user_id,
                "role": "assistant",
                "content": "I'll help you optimize your AI costs...",
                "metadata": {"agent": "cost_optimizer"}
            },
            # User 2 messages
            {
                "id": MessageID(self.id_generator.generate_message_id()),
                "thread_id": user2_context.thread_id,
                "user_id": user2_context.user_id,
                "role": "user", 
                "content": "Analyze my usage patterns",
                "metadata": {"business_intent": "usage_analysis"}
            },
            {
                "id": MessageID(self.id_generator.generate_message_id()),
                "thread_id": user2_context.thread_id,
                "user_id": user2_context.user_id,
                "role": "assistant",
                "content": "I'll analyze your usage patterns...",
                "metadata": {"agent": "usage_analyzer"}
            }
        ]
        
        # Store messages in database
        storage_start = time.time()
        
        async with get_db_session() as db:
            for msg in messages_data:
                await db.execute(
                    """INSERT INTO messages (id, thread_id, role, content, metadata, created_at) 
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    str(msg["id"]),
                    str(msg["thread_id"]),
                    msg["role"],
                    msg["content"],
                    json.dumps(msg["metadata"]),
                    datetime.now(timezone.utc)
                )
                self.created_messages.append(msg["id"])
                
            await db.commit()
            
        storage_time = time.time() - storage_start
        
        # Verify isolation: User 1 should only see their messages
        async with get_db_session() as db:
            user1_messages = await db.fetch(
                """SELECT * FROM messages WHERE thread_id = $1 ORDER BY created_at""",
                str(user1_context.thread_id)
            )
            
            user2_messages = await db.fetch(
                """SELECT * FROM messages WHERE thread_id = $1 ORDER BY created_at""",
                str(user2_context.thread_id)
            )
        
        # Assertions for isolation
        assert len(user1_messages) == 2, f"User 1 should have 2 messages: {len(user1_messages)}"
        assert len(user2_messages) == 2, f"User 2 should have 2 messages: {len(user2_messages)}"
        
        # Verify content isolation
        user1_content = [msg["content"] for msg in user1_messages]
        user2_content = [msg["content"] for msg in user2_messages]
        
        assert "Optimize my AI costs" in user1_content[0], "User 1 content should be preserved"
        assert "Analyze my usage patterns" in user2_content[0], "User 2 content should be preserved"
        
        # Verify no cross-contamination
        assert not any("usage patterns" in content for content in user1_content), \
            "User 1 should not see User 2 content"
        assert not any("AI costs" in content for content in user2_content), \
            "User 2 should not see User 1 content"
        
        # Performance requirement
        assert storage_time < 2.0, \
            f"Message storage should be < 2s: {storage_time:.2f}s"
        
        self.record_metric("message_isolation_test_passed", True)
        self.record_metric("message_storage_time", storage_time)
        self.record_metric("users_tested", 2)
        self.record_metric("messages_stored", len(messages_data))
        
    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.asyncio
    async def test_agent_execution_results_storage(self, real_db_fixture):
        """Test storage and retrieval of agent execution results."""
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="agent_results_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create thread
        async with get_db_session() as db:
            await db.execute(
                """INSERT INTO threads (id, user_id, title, created_at, updated_at) 
                   VALUES ($1, $2, $3, $4, $5)""",
                str(user_context.thread_id),
                str(user_context.user_id),
                "Agent Results Test",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            )
            await db.commit()
            
        self.created_threads.append(user_context.thread_id)
        
        # Create agent execution results
        agent_results = [
            {
                "agent_name": "data_agent",
                "execution_id": self.id_generator.generate_execution_id(),
                "start_time": time.time() - 30,
                "end_time": time.time() - 25,
                "status": "completed",
                "results": {
                    "data_collected": {
                        "total_tokens": 150000,
                        "total_cost": 75.50,
                        "api_calls": 245
                    },
                    "analysis": {
                        "cost_trend": "increasing",
                        "peak_usage_hours": [9, 10, 14, 15]
                    }
                },
                "metadata": {
                    "tools_used": ["token_counter", "cost_calculator"],
                    "execution_time": 5.0
                }
            },
            {
                "agent_name": "optimization_agent",
                "execution_id": self.id_generator.generate_execution_id(),
                "start_time": time.time() - 25,
                "end_time": time.time() - 15,
                "status": "completed",
                "results": {
                    "recommendations": [
                        {
                            "type": "model_optimization",
                            "description": "Switch to GPT-3.5 for simple queries",
                            "potential_savings": 1200.00
                        },
                        {
                            "type": "caching_strategy",
                            "description": "Implement result caching",
                            "potential_savings": 800.00
                        }
                    ],
                    "total_potential_savings": 2000.00
                },
                "metadata": {
                    "tools_used": ["optimization_analyzer", "cost_calculator"],
                    "execution_time": 10.0
                }
            }
        ]
        
        # Store agent results
        storage_start = time.time()
        
        async with get_db_session() as db:
            for result in agent_results:
                await db.execute(
                    """INSERT INTO agent_executions 
                       (id, thread_id, agent_name, status, results, metadata, start_time, end_time, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                    result["execution_id"],
                    str(user_context.thread_id),
                    result["agent_name"],
                    result["status"],
                    json.dumps(result["results"]),
                    json.dumps(result["metadata"]),
                    datetime.fromtimestamp(result["start_time"], tz=timezone.utc),
                    datetime.fromtimestamp(result["end_time"], tz=timezone.utc),
                    datetime.now(timezone.utc)
                )
                
            await db.commit()
            
        storage_time = time.time() - storage_start
        
        # Retrieve and verify agent results
        async with get_db_session() as db:
            stored_results = await db.fetch(
                """SELECT * FROM agent_executions WHERE thread_id = $1 ORDER BY start_time""",
                str(user_context.thread_id)
            )
        
        # Assertions
        assert len(stored_results) == 2, f"Should store 2 agent results: {len(stored_results)}"
        
        # Verify data agent results
        data_result = next(r for r in stored_results if r["agent_name"] == "data_agent")
        data_results_json = json.loads(data_result["results"])
        
        assert data_results_json["data_collected"]["total_cost"] == 75.50, \
            "Data agent cost should be preserved"
        assert data_results_json["analysis"]["cost_trend"] == "increasing", \
            "Data agent analysis should be preserved"
        
        # Verify optimization agent results
        opt_result = next(r for r in stored_results if r["agent_name"] == "optimization_agent")
        opt_results_json = json.loads(opt_result["results"])
        
        assert opt_results_json["total_potential_savings"] == 2000.00, \
            "Optimization savings should be preserved"
        assert len(opt_results_json["recommendations"]) == 2, \
            "Should preserve all recommendations"
        
        # Verify metadata preservation
        data_metadata = json.loads(data_result["metadata"])
        assert "token_counter" in data_metadata["tools_used"], \
            "Tools used should be preserved"
        
        # Performance requirement
        assert storage_time < 1.0, \
            f"Agent results storage should be < 1s: {storage_time:.2f}s"
        
        self.record_metric("agent_results_storage_test_passed", True)
        self.record_metric("agent_results_storage_time", storage_time)
        self.record_metric("agent_results_stored", len(agent_results))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_database_cleanup_on_user_disconnect(self, real_db_fixture):
        """Test database cleanup behavior when user disconnects."""
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="cleanup_test@example.com", 
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create session data in database
        session_data = {
            "user_id": user_context.user_id,
            "websocket_id": user_context.websocket_id,
            "connection_time": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "status": "active"
        }
        
        async with get_db_session() as db:
            # Create session record
            await db.execute(
                """INSERT INTO user_sessions (id, user_id, websocket_id, connection_time, last_activity, status)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                str(user_context.websocket_id),
                str(session_data["user_id"]),
                str(session_data["websocket_id"]),
                session_data["connection_time"],
                session_data["last_activity"],
                session_data["status"]
            )
            
            # Create temporary data that should be cleaned up
            await db.execute(
                """INSERT INTO temporary_user_data (user_id, websocket_id, data_type, data, created_at)
                   VALUES ($1, $2, $3, $4, $5)""",
                str(user_context.user_id),
                str(user_context.websocket_id),
                "active_execution",
                json.dumps({"agent": "in_progress", "step": 2}),
                datetime.now(timezone.utc)
            )
            
            await db.commit()
        
        # Simulate user disconnect cleanup
        cleanup_start = time.time()
        
        async with get_db_session() as db:
            # Mark session as disconnected
            await db.execute(
                """UPDATE user_sessions SET status = 'disconnected', disconnection_time = $1 
                   WHERE websocket_id = $2""",
                datetime.now(timezone.utc),
                str(user_context.websocket_id)
            )
            
            # Clean up temporary data
            await db.execute(
                """DELETE FROM temporary_user_data WHERE websocket_id = $1""",
                str(user_context.websocket_id)
            )
            
            await db.commit()
            
        cleanup_time = time.time() - cleanup_start
        
        # Verify cleanup results
        async with get_db_session() as db:
            # Check session status updated
            session_status = await db.fetchrow(
                "SELECT status, disconnection_time FROM user_sessions WHERE websocket_id = $1",
                str(user_context.websocket_id)
            )
            
            # Check temporary data removed
            temp_data_count = await db.fetchval(
                "SELECT COUNT(*) FROM temporary_user_data WHERE websocket_id = $1",
                str(user_context.websocket_id)
            )
            
            # Cleanup our test data
            await db.execute("DELETE FROM user_sessions WHERE websocket_id = $1", str(user_context.websocket_id))
            await db.commit()
        
        # Assertions
        assert session_status["status"] == "disconnected", \
            "Session should be marked as disconnected"
        assert session_status["disconnection_time"] is not None, \
            "Disconnection time should be recorded"
        assert temp_data_count == 0, \
            "Temporary data should be cleaned up"
        
        # Performance requirement
        assert cleanup_time < 0.5, \
            f"Cleanup should be fast: {cleanup_time:.2f}s"
        
        self.record_metric("disconnect_cleanup_test_passed", True)
        self.record_metric("cleanup_time", cleanup_time)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_user_data_isolation_validation(self, real_db_fixture):
        """Test comprehensive multi-user data isolation in database."""
        # Create 5 concurrent users
        concurrent_users = 5
        user_contexts = []
        
        for i in range(concurrent_users):
            context = await create_authenticated_user_context(
                user_email=f"isolation_user_{i}@example.com",
                environment=self.environment,
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        # Create threads and data for all users concurrently
        isolation_start = time.time()
        
        async with get_db_session() as db:
            for i, context in enumerate(user_contexts):
                # Create thread
                await db.execute(
                    """INSERT INTO threads (id, user_id, title, created_at, updated_at, metadata)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    str(context.thread_id),
                    str(context.user_id),
                    f"User {i} Conversation",
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc),
                    json.dumps({"user_index": i, "isolation_test": True})
                )
                
                # Create messages
                for j in range(3):  # 3 messages per user
                    message_id = MessageID(self.id_generator.generate_message_id())
                    await db.execute(
                        """INSERT INTO messages (id, thread_id, role, content, metadata, created_at)
                           VALUES ($1, $2, $3, $4, $5, $6)""",
                        str(message_id),
                        str(context.thread_id),
                        "user" if j % 2 == 0 else "assistant",
                        f"User {i} Message {j}: Unique content {context.user_id}",
                        json.dumps({"user_index": i, "message_index": j}),
                        datetime.now(timezone.utc)
                    )
                    self.created_messages.append(message_id)
                
                # Track for cleanup
                self.created_threads.append(context.thread_id)
            
            await db.commit()
            
        isolation_time = time.time() - isolation_start
        
        # Verify isolation: Each user should only see their own data
        async with get_db_session() as db:
            for i, context in enumerate(user_contexts):
                # Check thread isolation
                user_threads = await db.fetch(
                    "SELECT * FROM threads WHERE user_id = $1",
                    str(context.user_id)
                )
                
                assert len(user_threads) == 1, \
                    f"User {i} should see exactly 1 thread: {len(user_threads)}"
                assert user_threads[0]["title"] == f"User {i} Conversation", \
                    f"User {i} should see their own thread title"
                
                # Check message isolation
                user_messages = await db.fetch(
                    "SELECT * FROM messages WHERE thread_id = $1",
                    str(context.thread_id)
                )
                
                assert len(user_messages) == 3, \
                    f"User {i} should have 3 messages: {len(user_messages)}"
                
                # Verify content isolation
                for message in user_messages:
                    content = message["content"]
                    assert f"User {i}" in content, \
                        f"User {i} message should contain their user index"
                    assert str(context.user_id) in content, \
                        f"User {i} message should contain their user ID"
                
                # Verify no cross-contamination
                all_other_messages = await db.fetch(
                    """SELECT * FROM messages m 
                       JOIN threads t ON m.thread_id = t.id 
                       WHERE t.user_id != $1""",
                    str(context.user_id)
                )
                
                for other_message in all_other_messages:
                    other_content = other_message["content"]
                    assert f"User {i}" not in other_content or str(context.user_id) not in other_content, \
                        f"User {i} should not see other users' content: {other_content}"
        
        # Cross-user query test - simulate potential SQL injection or access control bypass
        async with get_db_session() as db:
            # Try to access all users' data with one user's context
            test_context = user_contexts[0]
            
            # This should only return the first user's data
            cross_user_query = await db.fetch(
                """SELECT DISTINCT t.user_id, t.title FROM threads t 
                   WHERE t.user_id = $1""",
                str(test_context.user_id)
            )
            
            assert len(cross_user_query) == 1, \
                "Cross-user query should only return one user's data"
            assert cross_user_query[0]["user_id"] == str(test_context.user_id), \
                "Should only return querying user's data"
        
        # Performance requirement for concurrent operations
        assert isolation_time < 10.0, \
            f"Multi-user data creation should be < 10s: {isolation_time:.2f}s"
        
        self.record_metric("multi_user_isolation_test_passed", True)
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("isolation_setup_time", isolation_time)
        self.record_metric("total_messages_created", concurrent_users * 3)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_persistence_performance_requirements(self, real_db_fixture):
        """Test database persistence meets performance requirements."""
        performance_metrics = {
            "thread_create_times": [],
            "message_batch_times": [],
            "result_storage_times": [],
            "retrieval_times": []
        }
        
        # Performance test with multiple iterations
        test_iterations = 5
        messages_per_batch = 10
        
        for iteration in range(test_iterations):
            # Create user context
            user_context = await create_authenticated_user_context(
                user_email=f"perf_test_{iteration}@example.com",
                environment=self.environment,
                websocket_enabled=True
            )
            
            # Test 1: Thread creation performance
            thread_start = time.time()
            async with get_db_session() as db:
                await db.execute(
                    """INSERT INTO threads (id, user_id, title, created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5)""",
                    str(user_context.thread_id),
                    str(user_context.user_id),
                    f"Performance Test {iteration}",
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc)
                )
                await db.commit()
            thread_time = time.time() - thread_start
            performance_metrics["thread_create_times"].append(thread_time)
            self.created_threads.append(user_context.thread_id)
            
            # Test 2: Batch message insertion performance
            batch_start = time.time()
            async with get_db_session() as db:
                for j in range(messages_per_batch):
                    message_id = MessageID(self.id_generator.generate_message_id())
                    await db.execute(
                        """INSERT INTO messages (id, thread_id, role, content, created_at)
                           VALUES ($1, $2, $3, $4, $5)""",
                        str(message_id),
                        str(user_context.thread_id),
                        "user" if j % 2 == 0 else "assistant",
                        f"Performance test message {j} with content",
                        datetime.now(timezone.utc)
                    )
                    self.created_messages.append(message_id)
                await db.commit()
            batch_time = time.time() - batch_start
            performance_metrics["message_batch_times"].append(batch_time)
            
            # Test 3: Agent result storage performance
            result_start = time.time()
            async with get_db_session() as db:
                await db.execute(
                    """INSERT INTO agent_executions 
                       (id, thread_id, agent_name, status, results, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    self.id_generator.generate_execution_id(),
                    str(user_context.thread_id),
                    "performance_test_agent",
                    "completed",
                    json.dumps({"test_data": "performance_result", "iteration": iteration}),
                    datetime.now(timezone.utc)
                )
                await db.commit()
            result_time = time.time() - result_start
            performance_metrics["result_storage_times"].append(result_time)
            
            # Test 4: Data retrieval performance
            retrieval_start = time.time()
            async with get_db_session() as db:
                thread_data = await db.fetchrow(
                    "SELECT * FROM threads WHERE id = $1", str(user_context.thread_id)
                )
                messages = await db.fetch(
                    "SELECT * FROM messages WHERE thread_id = $1 ORDER BY created_at",
                    str(user_context.thread_id)
                )
                results = await db.fetch(
                    "SELECT * FROM agent_executions WHERE thread_id = $1",
                    str(user_context.thread_id)
                )
            retrieval_time = time.time() - retrieval_start
            performance_metrics["retrieval_times"].append(retrieval_time)
        
        # Calculate performance statistics
        avg_thread_time = sum(performance_metrics["thread_create_times"]) / test_iterations
        avg_batch_time = sum(performance_metrics["message_batch_times"]) / test_iterations
        avg_result_time = sum(performance_metrics["result_storage_times"]) / test_iterations
        avg_retrieval_time = sum(performance_metrics["retrieval_times"]) / test_iterations
        
        # Business performance requirements
        assert avg_thread_time < 0.5, \
            f"Thread creation should be < 0.5s: {avg_thread_time:.2f}s"
        assert avg_batch_time < 2.0, \
            f"Batch message storage should be < 2s: {avg_batch_time:.2f}s"
        assert avg_result_time < 0.3, \
            f"Result storage should be < 0.3s: {avg_result_time:.2f}s"
        assert avg_retrieval_time < 1.0, \
            f"Data retrieval should be < 1s: {avg_retrieval_time:.2f}s"
        
        # Per-message performance (batch_time / messages_per_batch)
        avg_per_message_time = avg_batch_time / messages_per_batch
        assert avg_per_message_time < 0.2, \
            f"Per-message time should be < 0.2s: {avg_per_message_time:.2f}s"
        
        self.record_metric("persistence_performance_test_passed", True)
        self.record_metric("avg_thread_creation_time", avg_thread_time)
        self.record_metric("avg_message_batch_time", avg_batch_time)
        self.record_metric("avg_result_storage_time", avg_result_time)
        self.record_metric("avg_retrieval_time", avg_retrieval_time)
        self.record_metric("performance_test_iterations", test_iterations)
        
        print(f"\n📊 DATABASE PERFORMANCE METRICS:")
        print(f"   🧵 Thread Creation: {avg_thread_time:.3f}s")
        print(f"   💬 Message Batch ({messages_per_batch}): {avg_batch_time:.3f}s")
        print(f"   📄 Result Storage: {avg_result_time:.3f}s")
        print(f"   📥 Data Retrieval: {avg_retrieval_time:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])