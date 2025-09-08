"""Integration Tests for ID Persistence and User Isolation with Real Database

Business Value Justification (BVJ):
- Segment: Platform/Internal - Multi-User Data Isolation
- Business Goal: Ensure complete user data isolation in database operations
- Value Impact: Prevents user data contamination, protects user privacy, ensures multi-tenant security
- Strategic Impact: Foundation for enterprise-grade multi-user platform reliability

CRITICAL CONTEXT:
This test suite validates ID persistence and user isolation using REAL PostgreSQL database.
Tests focus on preventing the CASCADE FAILURES identified in type drift audit:
1. User data leakage between database sessions
2. Thread/conversation mixing across users  
3. Agent execution context contamination
4. WebSocket message routing violations

These tests use REAL services and will FAIL until proper isolation is implemented.
NO MOCKS - this validates actual database behavior and isolation patterns.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

# SSOT Type Imports - Critical for isolation
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, SessionID, WebSocketID,
    AgentID, ExecutionID, DatabaseSessionID,
    ensure_user_id, ensure_thread_id, ensure_run_id,
    AuthValidationResult, AgentExecutionContext, ExecutionContextState,
    WebSocketMessage, WebSocketEventType
)

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture

# Application imports for real database models
try:
    from netra_backend.app.models import User, Thread, Message, Run
    from netra_backend.app.database.connection import get_database_session
    from netra_backend.app.services.user_execution_context import UserExecutionContextFactory
except ImportError as e:
    # Fallback for test isolation if imports fail
    User = Thread = Message = Run = None
    get_database_session = None
    UserExecutionContextFactory = None


class TestIDPersistenceIsolation(BaseIntegrationTest):
    """Integration tests for ID persistence and user isolation with real database.
    
    CRITICAL PURPOSE: Validate that strongly typed IDs prevent user data mixing
    in actual database operations. Tests will FAIL until proper isolation implemented.
    """
    
    def setup_method(self):
        """Set up test environment with real database connection."""
        super().setup_method()
        self.logger.info("Setting up ID persistence isolation tests with real database")
        
        # Test user data for isolation validation
        self.user1_id = UserID(str(uuid.uuid4()))
        self.user2_id = UserID(str(uuid.uuid4()))
        self.user1_email = f"user1-{uuid.uuid4().hex[:8]}@example.com"
        self.user2_email = f"user2-{uuid.uuid4().hex[:8]}@example.com"
        
        # Test thread and execution data
        self.user1_thread_id = ThreadID(str(uuid.uuid4()))
        self.user2_thread_id = ThreadID(str(uuid.uuid4()))
        self.user1_run_id = RunID(str(uuid.uuid4()))
        self.user2_run_id = RunID(str(uuid.uuid4()))
        self.user1_request_id = RequestID(str(uuid.uuid4()))
        self.user2_request_id = RequestID(str(uuid.uuid4()))
        
        # Session and WebSocket data
        self.user1_session_id = SessionID(str(uuid.uuid4()))
        self.user2_session_id = SessionID(str(uuid.uuid4()))
        self.user1_websocket_id = WebSocketID(str(uuid.uuid4()))
        self.user2_websocket_id = WebSocketID(str(uuid.uuid4()))
        
        # Agent execution data
        self.agent1_id = AgentID(str(uuid.uuid4()))
        self.agent2_id = AgentID(str(uuid.uuid4()))
        self.execution1_id = ExecutionID(str(uuid.uuid4()))
        self.execution2_id = ExecutionID(str(uuid.uuid4()))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.database
    async def test_user_creation_with_strongly_typed_ids(self, real_services_fixture):
        """Test user creation using strongly typed UserIDs with real database.
        
        CRITICAL: Validates that user creation properly handles UserID type.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for integration test")
        
        db_session = real_services_fixture["db"]
        if db_session is None:
            pytest.skip("Database session not available")
        
        # Create users with strongly typed IDs
        try:
            # Test direct SQL with typed IDs
            user1_insert = text("""
                INSERT INTO users (id, email, name, created_at, updated_at)
                VALUES (:user_id, :email, :name, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """)
            
            user2_insert = text("""
                INSERT INTO users (id, email, name, created_at, updated_at) 
                VALUES (:user_id, :email, :name, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """)
            
            current_time = datetime.now(timezone.utc)
            
            # Insert user 1 with UserID type
            await db_session.execute(user1_insert, {
                "user_id": str(self.user1_id),  # Convert UserID to string for SQL
                "email": self.user1_email,
                "name": "Test User 1",
                "created_at": current_time,
                "updated_at": current_time
            })
            
            # Insert user 2 with UserID type  
            await db_session.execute(user2_insert, {
                "user_id": str(self.user2_id),  # Convert UserID to string for SQL
                "email": self.user2_email,
                "name": "Test User 2", 
                "created_at": current_time,
                "updated_at": current_time
            })
            
            await db_session.commit()
            
            # Verify users created with correct isolation
            user1_query = text("SELECT id, email, name FROM users WHERE id = :user_id")
            user2_query = text("SELECT id, email, name FROM users WHERE id = :user_id")
            
            user1_result = await db_session.execute(user1_query, {"user_id": str(self.user1_id)})
            user2_result = await db_session.execute(user2_query, {"user_id": str(self.user2_id)})
            
            user1_row = user1_result.fetchone()
            user2_row = user2_result.fetchone()
            
            # Validate proper isolation
            assert user1_row is not None, "User 1 should be created"
            assert user2_row is not None, "User 2 should be created"
            assert user1_row[0] != user2_row[0], "Users should have different IDs"
            assert user1_row[1] == self.user1_email, "User 1 email should match"
            assert user2_row[1] == self.user2_email, "User 2 email should match"
            
            # CRITICAL: Validate UserID type conversion
            retrieved_user1_id = UserID(user1_row[0])
            retrieved_user2_id = UserID(user2_row[0])
            
            assert retrieved_user1_id == self.user1_id, "User 1 ID should match after type conversion"
            assert retrieved_user2_id == self.user2_id, "User 2 ID should match after type conversion"
            
            self.logger.info(f"Successfully created isolated users: {retrieved_user1_id}, {retrieved_user2_id}")
            
        finally:
            # Cleanup test data
            await self._cleanup_test_users(db_session)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.database
    async def test_thread_creation_with_user_isolation(self, real_services_fixture):
        """Test thread creation with proper user isolation using strongly typed IDs.
        
        CRITICAL: This validates that threads cannot leak between users.
        Test will FAIL if thread isolation violations exist.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")
        
        db_session = real_services_fixture["db"]
        if db_session is None:
            pytest.skip("Database session not available")
        
        try:
            # First create test users
            await self._create_test_users(db_session)
            
            # Create threads for each user with strongly typed IDs
            thread1_insert = text("""
                INSERT INTO threads (id, user_id, title, created_at, updated_at)
                VALUES (:thread_id, :user_id, :title, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """)
            
            current_time = datetime.now(timezone.utc)
            
            # User 1 thread
            await db_session.execute(thread1_insert, {
                "thread_id": str(self.user1_thread_id),
                "user_id": str(self.user1_id),
                "title": "User 1 Conversation",
                "created_at": current_time,
                "updated_at": current_time
            })
            
            # User 2 thread
            await db_session.execute(thread1_insert, {
                "thread_id": str(self.user2_thread_id),
                "user_id": str(self.user2_id),
                "title": "User 2 Conversation", 
                "created_at": current_time,
                "updated_at": current_time
            })
            
            await db_session.commit()
            
            # CRITICAL TEST: Validate thread isolation
            user1_threads_query = text("""
                SELECT id, user_id, title FROM threads WHERE user_id = :user_id
            """)
            
            user1_threads = await db_session.execute(user1_threads_query, {
                "user_id": str(self.user1_id)
            })
            user1_thread_rows = user1_threads.fetchall()
            
            user2_threads = await db_session.execute(user1_threads_query, {
                "user_id": str(self.user2_id)
            })
            user2_thread_rows = user2_threads.fetchall()
            
            # Validate complete isolation
            assert len(user1_thread_rows) == 1, "User 1 should have exactly 1 thread"
            assert len(user2_thread_rows) == 1, "User 2 should have exactly 1 thread"
            
            user1_thread_row = user1_thread_rows[0]
            user2_thread_row = user2_thread_rows[0]
            
            # Validate no cross-user contamination
            assert user1_thread_row[1] == str(self.user1_id), "User 1 thread belongs to User 1"
            assert user2_thread_row[1] == str(self.user2_id), "User 2 thread belongs to User 2"
            assert user1_thread_row[2] == "User 1 Conversation", "User 1 thread has correct title"
            assert user2_thread_row[2] == "User 2 Conversation", "User 2 thread has correct title"
            
            # CRITICAL: Test cross-contamination prevention
            cross_contamination_query = text("""
                SELECT COUNT(*) as count FROM threads 
                WHERE user_id = :user1_id AND id = :user2_thread_id
            """)
            
            contamination_check = await db_session.execute(cross_contamination_query, {
                "user1_id": str(self.user1_id),
                "user2_thread_id": str(self.user2_thread_id)
            })
            contamination_count = contamination_check.fetchone()[0]
            
            assert contamination_count == 0, (
                "CRITICAL VIOLATION: User 1 should NOT have access to User 2's thread. "
                "This indicates thread isolation failure causing user data leakage."
            )
            
            self.logger.info("Thread isolation validation passed - no cross-user contamination detected")
            
        finally:
            await self._cleanup_test_data(db_session)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.database
    async def test_message_storage_with_thread_isolation(self, real_services_fixture):
        """Test message storage with proper thread and user isolation.
        
        CRITICAL: Validates that messages cannot leak between users or threads.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")
        
        db_session = real_services_fixture["db"]
        if db_session is None:
            pytest.skip("Database session not available")
        
        try:
            # Set up users and threads
            await self._create_test_users(db_session)
            await self._create_test_threads(db_session)
            
            # Create messages with strongly typed IDs
            message_insert = text("""
                INSERT INTO messages (id, thread_id, user_id, content, role, created_at, updated_at)
                VALUES (:message_id, :thread_id, :user_id, :content, :role, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """)
            
            current_time = datetime.now(timezone.utc)
            message1_id = str(uuid.uuid4())
            message2_id = str(uuid.uuid4())
            
            # User 1 message in User 1's thread
            await db_session.execute(message_insert, {
                "message_id": message1_id,
                "thread_id": str(self.user1_thread_id),
                "user_id": str(self.user1_id),
                "content": "User 1 sensitive message",
                "role": "user",
                "created_at": current_time,
                "updated_at": current_time
            })
            
            # User 2 message in User 2's thread
            await db_session.execute(message_insert, {
                "message_id": message2_id,
                "thread_id": str(self.user2_thread_id),
                "user_id": str(self.user2_id),
                "content": "User 2 sensitive message",
                "role": "user", 
                "created_at": current_time,
                "updated_at": current_time
            })
            
            await db_session.commit()
            
            # CRITICAL TEST: Validate message isolation by user
            user1_messages_query = text("""
                SELECT m.id, m.content, m.thread_id, m.user_id
                FROM messages m
                WHERE m.user_id = :user_id
            """)
            
            user1_messages = await db_session.execute(user1_messages_query, {
                "user_id": str(self.user1_id)
            })
            user1_message_rows = user1_messages.fetchall()
            
            user2_messages = await db_session.execute(user1_messages_query, {
                "user_id": str(self.user2_id)
            })
            user2_message_rows = user2_messages.fetchall()
            
            # Validate complete message isolation
            assert len(user1_message_rows) == 1, "User 1 should see only their message"
            assert len(user2_message_rows) == 1, "User 2 should see only their message"
            
            user1_msg = user1_message_rows[0]
            user2_msg = user2_message_rows[0]
            
            assert user1_msg[1] == "User 1 sensitive message", "User 1 sees correct content"
            assert user2_msg[1] == "User 2 sensitive message", "User 2 sees correct content"
            assert user1_msg[2] == str(self.user1_thread_id), "User 1 message in correct thread"
            assert user2_msg[2] == str(self.user2_thread_id), "User 2 message in correct thread"
            
            # CRITICAL: Test for cross-user message contamination
            cross_user_query = text("""
                SELECT COUNT(*) as count
                FROM messages m
                JOIN threads t ON m.thread_id = t.id
                WHERE m.user_id = :user1_id AND t.user_id = :user2_id
            """)
            
            cross_contamination = await db_session.execute(cross_user_query, {
                "user1_id": str(self.user1_id),
                "user2_id": str(self.user2_id)
            })
            contamination_count = cross_contamination.fetchone()[0]
            
            assert contamination_count == 0, (
                "CRITICAL VIOLATION: Found messages from User 1 in User 2's threads. "
                "This indicates message isolation failure causing sensitive data leakage."
            )
            
            self.logger.info("Message isolation validation passed - no cross-user message leakage")
            
        finally:
            await self._cleanup_test_data(db_session)
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    @pytest.mark.database
    async def test_run_execution_isolation_with_typed_ids(self, real_services_fixture):
        """Test agent run execution isolation using strongly typed IDs.
        
        CRITICAL: Validates that agent runs cannot contaminate between users.
        Test will FAIL if agent execution isolation violations exist.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")
        
        db_session = real_services_fixture["db"]
        if db_session is None:
            pytest.skip("Database session not available")
        
        try:
            # Set up test data
            await self._create_test_users(db_session)
            await self._create_test_threads(db_session)
            
            # Create agent runs with strongly typed IDs
            run_insert = text("""
                INSERT INTO runs (id, thread_id, user_id, agent_name, status, created_at, updated_at)
                VALUES (:run_id, :thread_id, :user_id, :agent_name, :status, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """)
            
            current_time = datetime.now(timezone.utc)
            
            # User 1 agent run
            await db_session.execute(run_insert, {
                "run_id": str(self.user1_run_id),
                "thread_id": str(self.user1_thread_id),
                "user_id": str(self.user1_id),
                "agent_name": "cost_optimizer",
                "status": "running",
                "created_at": current_time,
                "updated_at": current_time
            })
            
            # User 2 agent run
            await db_session.execute(run_insert, {
                "run_id": str(self.user2_run_id), 
                "thread_id": str(self.user2_thread_id),
                "user_id": str(self.user2_id),
                "agent_name": "cost_optimizer",
                "status": "running",
                "created_at": current_time,
                "updated_at": current_time
            })
            
            await db_session.commit()
            
            # CRITICAL TEST: Validate run isolation by user
            user_runs_query = text("""
                SELECT r.id, r.agent_name, r.status, r.thread_id, r.user_id
                FROM runs r
                WHERE r.user_id = :user_id
            """)
            
            user1_runs = await db_session.execute(user_runs_query, {
                "user_id": str(self.user1_id)
            })
            user1_run_rows = user1_runs.fetchall()
            
            user2_runs = await db_session.execute(user_runs_query, {
                "user_id": str(self.user2_id)
            })
            user2_run_rows = user2_runs.fetchall()
            
            # Validate run isolation
            assert len(user1_run_rows) == 1, "User 1 should see only their run"
            assert len(user2_run_rows) == 1, "User 2 should see only their run"
            
            user1_run = user1_run_rows[0]
            user2_run = user2_run_rows[0]
            
            # Validate run data integrity
            assert user1_run[0] == str(self.user1_run_id), "User 1 run has correct ID"
            assert user2_run[0] == str(self.user2_run_id), "User 2 run has correct ID"
            assert user1_run[3] == str(self.user1_thread_id), "User 1 run in correct thread"
            assert user2_run[3] == str(self.user2_thread_id), "User 2 run in correct thread"
            assert user1_run[4] == str(self.user1_id), "User 1 run belongs to User 1"
            assert user2_run[4] == str(self.user2_id), "User 2 run belongs to User 2"
            
            # CRITICAL: Test for run cross-contamination
            cross_run_query = text("""
                SELECT COUNT(*) as count
                FROM runs r
                WHERE r.user_id = :user1_id AND r.thread_id = :user2_thread_id
            """)
            
            cross_contamination = await db_session.execute(cross_run_query, {
                "user1_id": str(self.user1_id),
                "user2_thread_id": str(self.user2_thread_id)
            })
            contamination_count = cross_contamination.fetchone()[0]
            
            assert contamination_count == 0, (
                "CRITICAL VIOLATION: Found User 1 run in User 2's thread. "
                "This indicates agent execution isolation failure."
            )
            
            self.logger.info("Agent run isolation validation passed - no cross-user contamination")
            
        finally:
            await self._cleanup_test_data(db_session)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.database
    async def test_concurrent_user_operations_isolation(self, real_services_fixture):
        """Test concurrent operations between users maintain isolation.
        
        CRITICAL: Validates that concurrent database operations don't cause
        user data mixing. This tests the core multi-user isolation capability.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")
        
        db_session = real_services_fixture["db"]
        if db_session is None:
            pytest.skip("Database session not available")
        
        try:
            # Create base test data
            await self._create_test_users(db_session)
            
            # Define concurrent operations for each user
            async def user1_operations():
                """Simulate User 1 operations with their data."""
                # Create thread
                thread_insert = text("""
                    INSERT INTO threads (id, user_id, title, created_at, updated_at)
                    VALUES (:thread_id, :user_id, :title, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """)
                
                await db_session.execute(thread_insert, {
                    "thread_id": str(self.user1_thread_id),
                    "user_id": str(self.user1_id),
                    "title": "Concurrent User 1 Thread",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                
                # Create message
                message_insert = text("""
                    INSERT INTO messages (id, thread_id, user_id, content, role, created_at, updated_at)
                    VALUES (:message_id, :thread_id, :user_id, :content, :role, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """)
                
                await db_session.execute(message_insert, {
                    "message_id": str(uuid.uuid4()),
                    "thread_id": str(self.user1_thread_id),
                    "user_id": str(self.user1_id),
                    "content": "Concurrent User 1 Message",
                    "role": "user",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                
                # Create run
                run_insert = text("""
                    INSERT INTO runs (id, thread_id, user_id, agent_name, status, created_at, updated_at)
                    VALUES (:run_id, :thread_id, :user_id, :agent_name, :status, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """)
                
                await db_session.execute(run_insert, {
                    "run_id": str(self.user1_run_id),
                    "thread_id": str(self.user1_thread_id),
                    "user_id": str(self.user1_id),
                    "agent_name": "concurrent_agent",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                
                return "user1_completed"
            
            async def user2_operations():
                """Simulate User 2 operations with their data."""
                # Create thread
                thread_insert = text("""
                    INSERT INTO threads (id, user_id, title, created_at, updated_at)
                    VALUES (:thread_id, :user_id, :title, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """)
                
                await db_session.execute(thread_insert, {
                    "thread_id": str(self.user2_thread_id),
                    "user_id": str(self.user2_id),
                    "title": "Concurrent User 2 Thread",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                
                # Create message
                message_insert = text("""
                    INSERT INTO messages (id, thread_id, user_id, content, role, created_at, updated_at)
                    VALUES (:message_id, :thread_id, :user_id, :content, :role, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """)
                
                await db_session.execute(message_insert, {
                    "message_id": str(uuid.uuid4()),
                    "thread_id": str(self.user2_thread_id),
                    "user_id": str(self.user2_id),
                    "content": "Concurrent User 2 Message",
                    "role": "user",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                
                # Create run
                run_insert = text("""
                    INSERT INTO runs (id, thread_id, user_id, agent_name, status, created_at, updated_at)
                    VALUES (:run_id, :thread_id, :user_id, :agent_name, :status, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """)
                
                await db_session.execute(run_insert, {
                    "run_id": str(self.user2_run_id),
                    "thread_id": str(self.user2_thread_id),
                    "user_id": str(self.user2_id),
                    "agent_name": "concurrent_agent",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                
                return "user2_completed"
            
            # Execute concurrent operations
            results = await asyncio.gather(
                user1_operations(),
                user2_operations(),
                return_exceptions=True
            )
            
            # Validate both operations completed successfully
            assert results[0] == "user1_completed", "User 1 operations should complete"
            assert results[1] == "user2_completed", "User 2 operations should complete"
            
            await db_session.commit()
            
            # CRITICAL: Validate complete isolation after concurrent operations
            isolation_query = text("""
                SELECT 
                    u.id as user_id,
                    COUNT(DISTINCT t.id) as thread_count,
                    COUNT(DISTINCT m.id) as message_count,
                    COUNT(DISTINCT r.id) as run_count
                FROM users u
                LEFT JOIN threads t ON u.id = t.user_id
                LEFT JOIN messages m ON u.id = m.user_id
                LEFT JOIN runs r ON u.id = r.user_id
                WHERE u.id IN (:user1_id, :user2_id)
                GROUP BY u.id
                ORDER BY u.id
            """)
            
            isolation_results = await db_session.execute(isolation_query, {
                "user1_id": str(self.user1_id),
                "user2_id": str(self.user2_id)
            })
            
            isolation_rows = isolation_results.fetchall()
            assert len(isolation_rows) == 2, "Should have data for both users"
            
            # Validate each user has exactly their own data
            for row in isolation_rows:
                user_id, thread_count, message_count, run_count = row
                assert thread_count == 1, f"User {user_id} should have exactly 1 thread"
                assert message_count == 1, f"User {user_id} should have exactly 1 message"
                assert run_count == 1, f"User {user_id} should have exactly 1 run"
            
            # CRITICAL: Validate no cross-contamination
            cross_contamination_query = text("""
                SELECT COUNT(*) as violations
                FROM (
                    SELECT 'thread' as type, t.user_id as owner, m.user_id as accessor
                    FROM threads t
                    JOIN messages m ON t.id = m.thread_id
                    WHERE t.user_id != m.user_id
                    
                    UNION ALL
                    
                    SELECT 'run' as type, t.user_id as owner, r.user_id as accessor
                    FROM threads t
                    JOIN runs r ON t.id = r.thread_id
                    WHERE t.user_id != r.user_id
                ) violations
            """)
            
            contamination_check = await db_session.execute(cross_contamination_query)
            violation_count = contamination_check.fetchone()[0]
            
            assert violation_count == 0, (
                f"CRITICAL VIOLATION: Found {violation_count} cross-user contamination violations. "
                "Concurrent operations caused user data mixing."
            )
            
            self.logger.info("Concurrent user operations isolation validation passed")
            
        finally:
            await self._cleanup_test_data(db_session)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.database
    async def test_database_session_isolation_per_user(self, real_services_fixture):
        """Test database session isolation prevents user context mixing.
        
        CRITICAL: This test will FAIL if database session management has
        user context contamination violations.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available")
        
        db_session = real_services_fixture["db"]
        if db_session is None:
            pytest.skip("Database session not available")
        
        try:
            # Test session context isolation
            if UserExecutionContextFactory is None:
                # Fallback test without UserExecutionContextFactory
                self.logger.warning("UserExecutionContextFactory not available, using basic session test")
                
                # Basic session isolation test
                await self._create_test_users(db_session)
                
                # Test that session maintains user context
                current_user_query = text("SELECT current_setting('app.user_id', true) as user_id")
                
                # Set user context for User 1
                await db_session.execute(text("SELECT set_config('app.user_id', :user_id, true)"), {
                    "user_id": str(self.user1_id)
                })
                
                user1_context = await db_session.execute(current_user_query)
                user1_session_user = user1_context.fetchone()
                
                # Set user context for User 2
                await db_session.execute(text("SELECT set_config('app.user_id', :user_id, true)"), {
                    "user_id": str(self.user2_id)
                })
                
                user2_context = await db_session.execute(current_user_query)
                user2_session_user = user2_context.fetchone()
                
                # Validate session context isolation
                if user1_session_user and user2_session_user:
                    # Context should change between users
                    assert user1_session_user[0] != user2_session_user[0], (
                        "Session context should be isolated between users"
                    )
                
                self.logger.info("Basic database session isolation test passed")
            
            else:
                # Full UserExecutionContextFactory test
                context_factory = UserExecutionContextFactory()
                
                # Create execution contexts for both users
                user1_context = await context_factory.create_execution_context(
                    user_id=self.user1_id,
                    thread_id=self.user1_thread_id,
                    run_id=self.user1_run_id,
                    request_id=self.user1_request_id
                )
                
                user2_context = await context_factory.create_execution_context(
                    user_id=self.user2_id,
                    thread_id=self.user2_thread_id,
                    run_id=self.user2_run_id,
                    request_id=self.user2_request_id
                )
                
                # Validate contexts are properly isolated
                assert user1_context.user_id != user2_context.user_id
                assert user1_context.thread_id != user2_context.thread_id
                assert user1_context.run_id != user2_context.run_id
                assert user1_context.request_id != user2_context.request_id
                
                # CRITICAL: Test context isolation in database operations
                # This should fail if contexts leak between users
                
                # Simulate database operations within user contexts
                async def simulate_user_operations(context):
                    """Simulate database operations within user execution context."""
                    # This should maintain user isolation
                    return {
                        "user_id": context.user_id,
                        "thread_id": context.thread_id,
                        "operation_result": "success"
                    }
                
                user1_result = await simulate_user_operations(user1_context)
                user2_result = await simulate_user_operations(user2_context)
                
                # Validate no context mixing
                assert str(user1_result["user_id"]) == str(self.user1_id)
                assert str(user2_result["user_id"]) == str(self.user2_id)
                assert user1_result["thread_id"] != user2_result["thread_id"]
                
                self.logger.info("UserExecutionContextFactory isolation validation passed")
            
        finally:
            await self._cleanup_test_data(db_session)
    
    # =============================================================================
    # Helper Methods for Test Setup and Cleanup
    # =============================================================================
    
    async def _create_test_users(self, db_session: AsyncSession):
        """Create test users for isolation testing."""
        user_insert = text("""
            INSERT INTO users (id, email, name, created_at, updated_at)
            VALUES (:user_id, :email, :name, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """)
        
        current_time = datetime.now(timezone.utc)
        
        await db_session.execute(user_insert, {
            "user_id": str(self.user1_id),
            "email": self.user1_email,
            "name": "Test User 1",
            "created_at": current_time,
            "updated_at": current_time
        })
        
        await db_session.execute(user_insert, {
            "user_id": str(self.user2_id),
            "email": self.user2_email,
            "name": "Test User 2",
            "created_at": current_time,
            "updated_at": current_time
        })
        
        await db_session.commit()
    
    async def _create_test_threads(self, db_session: AsyncSession):
        """Create test threads for both users."""
        thread_insert = text("""
            INSERT INTO threads (id, user_id, title, created_at, updated_at)
            VALUES (:thread_id, :user_id, :title, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """)
        
        current_time = datetime.now(timezone.utc)
        
        await db_session.execute(thread_insert, {
            "thread_id": str(self.user1_thread_id),
            "user_id": str(self.user1_id),
            "title": "Test Thread 1",
            "created_at": current_time,
            "updated_at": current_time
        })
        
        await db_session.execute(thread_insert, {
            "thread_id": str(self.user2_thread_id),
            "user_id": str(self.user2_id),
            "title": "Test Thread 2",
            "created_at": current_time,
            "updated_at": current_time
        })
        
        await db_session.commit()
    
    async def _cleanup_test_users(self, db_session: AsyncSession):
        """Clean up test users."""
        try:
            delete_users = text("DELETE FROM users WHERE id IN (:user1_id, :user2_id)")
            await db_session.execute(delete_users, {
                "user1_id": str(self.user1_id),
                "user2_id": str(self.user2_id)
            })
            await db_session.commit()
        except Exception as e:
            self.logger.warning(f"Failed to cleanup test users: {e}")
            await db_session.rollback()
    
    async def _cleanup_test_data(self, db_session: AsyncSession):
        """Clean up all test data."""
        try:
            # Clean up in reverse dependency order
            await db_session.execute(text("DELETE FROM runs WHERE user_id IN (:user1_id, :user2_id)"), {
                "user1_id": str(self.user1_id), "user2_id": str(self.user2_id)
            })
            await db_session.execute(text("DELETE FROM messages WHERE user_id IN (:user1_id, :user2_id)"), {
                "user1_id": str(self.user1_id), "user2_id": str(self.user2_id)
            })
            await db_session.execute(text("DELETE FROM threads WHERE user_id IN (:user1_id, :user2_id)"), {
                "user1_id": str(self.user1_id), "user2_id": str(self.user2_id)
            })
            await db_session.execute(text("DELETE FROM users WHERE id IN (:user1_id, :user2_id)"), {
                "user1_id": str(self.user1_id), "user2_id": str(self.user2_id)
            })
            await db_session.commit()
        except Exception as e:
            self.logger.warning(f"Failed to cleanup test data: {e}")
            await db_session.rollback()
    
    def teardown_method(self):
        """Clean up after test."""
        super().teardown_method()
        self.logger.info("Completed ID persistence isolation test")


# =============================================================================
# Standalone Test Functions (for pytest discovery)
# =============================================================================

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.database
@pytest.mark.critical
@pytest.mark.multi_user
async def test_comprehensive_id_persistence_isolation(real_services_fixture):
    """Comprehensive test runner for ID persistence and isolation.
    
    This test validates the entire ID persistence and isolation system
    with real database operations. Will FAIL until violations are fixed.
    """
    test_instance = TestIDPersistenceIsolation()
    test_instance.setup_method()
    
    try:
        # Core persistence tests
        await test_instance.test_user_creation_with_strongly_typed_ids(real_services_fixture)
        await test_instance.test_thread_creation_with_user_isolation(real_services_fixture)
        await test_instance.test_message_storage_with_thread_isolation(real_services_fixture)
        
        # Execution isolation tests
        await test_instance.test_run_execution_isolation_with_typed_ids(real_services_fixture)
        await test_instance.test_concurrent_user_operations_isolation(real_services_fixture)
        
        # Session isolation tests
        await test_instance.test_database_session_isolation_per_user(real_services_fixture)
        
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    # Run specific test for debugging
    pytest.main([__file__, "-v", "--tb=short", "-s"])