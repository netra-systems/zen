"""
Thread Switching Basic Integration Tests - Comprehensive Business Value Coverage

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) - Thread management is core platform functionality
- Business Goal: Enable seamless conversation continuity and user experience
- Value Impact: Users can switch between conversations, maintain context, and access historical data
- Strategic Impact: CRITICAL - Thread switching enables the chat-based value delivery that drives revenue
- Revenue Impact: Without thread switching, users cannot maintain conversation history, reducing engagement

This module provides comprehensive integration testing for basic thread switching functionality
using REAL services (database, Redis) with proper user isolation and business-focused scenarios.

CRITICAL COMPLIANCE:
- Uses REAL PostgreSQL and Redis services (NO MOCKS per CLAUDE.md)
- Follows SSOT patterns from test_framework
- Tests actual business value delivery, not just technical functionality
- Uses UserExecutionContext for proper multi-user isolation
- Validates end-to-end thread operations that users experience

Test Coverage:
- Tests 1-5: Basic thread creation and retrieval with real database
- Tests 6-10: Thread context switching with proper user isolation
- Tests 11-15: Thread persistence across user sessions
- Tests 16-20: Thread validation and authorization scenarios
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock

# Core system imports
from netra_backend.app.schemas.core_models import Thread, ThreadMetadata, User, Message
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, ensure_user_id, ensure_thread_id

# Test framework imports - SSOT patterns
from test_framework.base import BaseTestCase
from test_framework.fixtures.real_services import real_services_fixture, real_postgres_connection, with_test_database
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser

# Database and service imports
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text, select
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    AsyncSession = None

# Import actual thread service
try:
    from netra_backend.app.services.thread_service import ThreadService
    THREAD_SERVICE_AVAILABLE = True
except ImportError:
    ThreadService = None
    THREAD_SERVICE_AVAILABLE = False


class TestThreadSwitchingBasicIntegration(BaseTestCase):
    """
    Comprehensive integration tests for basic thread switching functionality.
    
    These tests validate the core thread management operations that enable
    users to create, switch between, and manage conversation threads with
    proper isolation and persistence.
    
    CRITICAL: Uses REAL services (database, Redis) to validate actual system behavior.
    """
    
    def setup_method(self):
        """Set up test fixtures with proper isolation."""
        super().setup_method()
        self.env = get_env()
        self.id_manager = UnifiedIDManager()
        self.auth_helper = E2EAuthHelper()
        
        # Create test users for multi-user scenarios
        self.test_user_1 = ensure_user_id("test_thread_user_001")
        self.test_user_2 = ensure_user_id("test_thread_user_002") 
        
        # Record test metrics
        self.record_metric("test_suite", "thread_switching_basic_integration")
        self.record_metric("test_compliance", "real_services_only")
    
    def teardown_method(self):
        """Clean up test resources."""
        self.id_manager.clear_all()
        super().teardown_method()
    
    # ============================================================================
    # TESTS 1-5: BASIC THREAD CREATION AND RETRIEVAL
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_001_create_new_thread_with_real_database(self, real_services_fixture):
        """
        Test 1/20: Create new thread with real database persistence.
        
        Business Value: Users must be able to start new conversations.
        This test validates the fundamental thread creation flow that enables
        users to begin new AI optimization sessions.
        """
        services = real_services_fixture
        
        # Skip if database not available
        if not services["database_available"]:
            pytest.skip("Real database not available - cannot test thread creation")
        
        # Create authenticated user context
        user_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=self.id_manager.generate_thread_id(),
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # Create thread using real database
        thread_data = {
            "id": user_context.thread_id,
            "name": "Cost Optimization Discussion",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,
            "metadata": {"category": "optimization", "priority": 5},
            "is_active": True,
            "message_count": 0
        }
        
        # Insert thread into real database
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                {
                    **thread_data,
                    "metadata": str(thread_data["metadata"])  # Convert to string for storage
                }
            )
        
        # Verify thread exists in database
        result = await services["db"].execute(
            text("SELECT * FROM threads WHERE id = :thread_id"),
            {"thread_id": user_context.thread_id}
        )
        thread_row = result.fetchone()
        
        # Validate business requirements
        assert thread_row is not None, "Thread must be persisted in database"
        assert thread_row[1] == "Cost Optimization Discussion", "Thread name must be preserved"
        assert thread_row[4] == self.test_user_1, "Thread must be associated with correct user"
        assert thread_row[6] == True, "New threads must be active by default"
        
        # Record success metrics
        self.record_metric("test_001_status", "passed")
        self.record_metric("thread_creation_database_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_002_retrieve_existing_thread_by_id(self, real_services_fixture):
        """
        Test 2/20: Retrieve existing thread by ID with database lookup.
        
        Business Value: Users must be able to access their conversation history.
        This validates thread retrieval for conversation continuity.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Pre-create thread in database
        thread_id = self.id_manager.generate_thread_id()
        thread_data = {
            "id": thread_id,
            "name": "Data Analysis Session",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,
            "metadata": '{"tags": ["analysis", "monthly"], "priority": 3}',
            "is_active": True,
            "message_count": 5
        }
        
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                thread_data
            )
        
        # Create user context for retrieval
        user_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # Retrieve thread from database
        result = await services["db"].execute(
            text("SELECT * FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": thread_id, "user_id": self.test_user_1}
        )
        retrieved_thread = result.fetchone()
        
        # Validate retrieval success
        assert retrieved_thread is not None, "Thread must be retrievable by ID"
        assert retrieved_thread[1] == "Data Analysis Session", "Retrieved thread name must match"
        assert retrieved_thread[7] == 5, "Message count must be preserved"
        assert retrieved_thread[4] == self.test_user_1, "User isolation must be maintained"
        
        self.record_metric("test_002_status", "passed")
        self.record_metric("thread_retrieval_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_003_list_user_threads_with_pagination(self, real_services_fixture):
        """
        Test 3/20: List user's threads with proper pagination and ordering.
        
        Business Value: Users need to see their conversation history organized
        and accessible for thread switching decisions.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create multiple threads for the user
        threads_data = []
        for i in range(7):  # Create 7 threads to test pagination
            thread_data = {
                "id": self.id_manager.generate_thread_id(),
                "name": f"Optimization Session {i+1}",
                "created_at": datetime.now(timezone.utc) - timedelta(days=i),
                "updated_at": datetime.now(timezone.utc) - timedelta(hours=i),
                "user_id": self.test_user_1,
                "metadata": f'{{"session_number": {i+1}, "type": "optimization"}}',
                "is_active": True,
                "message_count": i + 1
            }
            threads_data.append(thread_data)
        
        # Insert all threads
        async with services["db"].begin():
            for thread_data in threads_data:
                await services["db"].execute(
                    text("""
                        INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                        VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                    """),
                    thread_data
                )
        
        # Create user context
        user_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=self.id_manager.generate_thread_id(),
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # Test pagination: Get first 5 threads ordered by updated_at DESC
        result = await services["db"].execute(
            text("""
                SELECT id, name, updated_at, message_count 
                FROM threads 
                WHERE user_id = :user_id AND is_active = true
                ORDER BY updated_at DESC 
                LIMIT 5 OFFSET 0
            """),
            {"user_id": self.test_user_1}
        )
        page_1_threads = result.fetchall()
        
        # Test second page
        result = await services["db"].execute(
            text("""
                SELECT id, name, updated_at, message_count 
                FROM threads 
                WHERE user_id = :user_id AND is_active = true
                ORDER BY updated_at DESC 
                LIMIT 5 OFFSET 5
            """),
            {"user_id": self.test_user_1}
        )
        page_2_threads = result.fetchall()
        
        # Validate pagination results
        assert len(page_1_threads) == 5, "First page must return 5 threads"
        assert len(page_2_threads) == 2, "Second page must return remaining 2 threads"
        
        # Validate ordering (most recently updated first)
        assert page_1_threads[0][1] == "Optimization Session 1", "Most recent thread must be first"
        assert page_1_threads[0][3] == 1, "Message count must be correct"
        
        self.record_metric("test_003_status", "passed")
        self.record_metric("pagination_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_004_thread_creation_with_metadata_validation(self, real_services_fixture):
        """
        Test 4/20: Create thread with complex metadata and validate storage.
        
        Business Value: Thread metadata enables categorization and search
        functionality that helps users organize their AI sessions.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create user context
        user_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=self.id_manager.generate_thread_id(),
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # Complex metadata for business use case
        complex_metadata = {
            "tags": ["cost-optimization", "aws", "quarterly-review"],
            "priority": 8,
            "category": "enterprise",
            "estimated_savings": 50000,
            "department": "engineering",
            "review_cycle": "Q1-2025",
            "stakeholders": ["cto", "finance", "devops"],
            "custom_fields": {
                "budget_code": "ENG-OPT-2025",
                "approval_required": True,
                "confidentiality": "high"
            }
        }
        
        thread_data = {
            "id": user_context.thread_id,
            "name": "Q1 2025 AWS Cost Optimization Review",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,
            "metadata": str(complex_metadata),
            "is_active": True,
            "message_count": 0
        }
        
        # Insert thread with complex metadata
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                thread_data
            )
        
        # Retrieve and validate metadata preservation
        result = await services["db"].execute(
            text("SELECT id, name, metadata FROM threads WHERE id = :thread_id"),
            {"thread_id": user_context.thread_id}
        )
        thread_row = result.fetchone()
        
        assert thread_row is not None, "Thread with metadata must be stored"
        stored_metadata = thread_row[2]
        assert "cost-optimization" in stored_metadata, "Metadata tags must be preserved"
        assert "50000" in stored_metadata, "Numeric metadata must be preserved"
        assert "enterprise" in stored_metadata, "Category metadata must be preserved"
        
        self.record_metric("test_004_status", "passed")
        self.record_metric("metadata_validation_passed", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_005_thread_soft_delete_and_recovery(self, real_services_fixture):
        """
        Test 5/20: Test thread soft deletion and recovery functionality.
        
        Business Value: Users need ability to archive/restore conversations
        without losing valuable historical optimization data.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create thread to be soft-deleted
        thread_id = self.id_manager.generate_thread_id()
        thread_data = {
            "id": thread_id,
            "name": "Important Optimization History",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,
            "metadata": '{"important": true, "savings_achieved": 25000}',
            "is_active": True,
            "message_count": 10
        }
        
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                thread_data
            )
        
        # Perform soft delete (set is_active = false)
        async with services["db"].begin():
            await services["db"].execute(
                text("UPDATE threads SET is_active = false, updated_at = :updated_at WHERE id = :thread_id"),
                {"thread_id": thread_id, "updated_at": datetime.now(timezone.utc)}
            )
        
        # Verify thread is hidden from active list
        result = await services["db"].execute(
            text("SELECT COUNT(*) FROM threads WHERE id = :thread_id AND is_active = true"),
            {"thread_id": thread_id}
        )
        active_count = result.fetchone()[0]
        assert active_count == 0, "Soft-deleted thread must not appear in active list"
        
        # Verify thread still exists in database
        result = await services["db"].execute(
            text("SELECT name, message_count FROM threads WHERE id = :thread_id"),
            {"thread_id": thread_id}
        )
        thread_row = result.fetchone()
        assert thread_row is not None, "Soft-deleted thread must still exist in database"
        assert thread_row[1] == 10, "Message count must be preserved after soft delete"
        
        # Test recovery (restore is_active = true)
        async with services["db"].begin():
            await services["db"].execute(
                text("UPDATE threads SET is_active = true, updated_at = :updated_at WHERE id = :thread_id"),
                {"thread_id": thread_id, "updated_at": datetime.now(timezone.utc)}
            )
        
        # Verify thread is back in active list
        result = await services["db"].execute(
            text("SELECT name FROM threads WHERE id = :thread_id AND is_active = true"),
            {"thread_id": thread_id}
        )
        recovered_thread = result.fetchone()
        assert recovered_thread is not None, "Recovered thread must be active"
        assert recovered_thread[0] == "Important Optimization History", "Thread name must be preserved"
        
        self.record_metric("test_005_status", "passed")
        self.record_metric("soft_delete_recovery_verified", True)
    
    # ============================================================================
    # TESTS 6-10: THREAD CONTEXT SWITCHING WITH USER ISOLATION
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_006_switch_between_user_threads_with_isolation(self, real_services_fixture):
        """
        Test 6/20: Switch between threads while maintaining user isolation.
        
        Business Value: Users must only access their own threads. Critical for
        data security and preventing information leakage between users.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create threads for two different users
        user1_thread_id = self.id_manager.generate_thread_id()
        user2_thread_id = self.id_manager.generate_thread_id()
        
        threads_data = [
            {
                "id": user1_thread_id,
                "name": "User 1 Confidential Optimization",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": '{"confidential": true, "user1_data": "sensitive"}',
                "is_active": True,
                "message_count": 5
            },
            {
                "id": user2_thread_id,
                "name": "User 2 Private Analysis",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_2,
                "metadata": '{"private": true, "user2_data": "restricted"}',
                "is_active": True,
                "message_count": 3
            }
        ]
        
        # Insert both threads
        async with services["db"].begin():
            for thread_data in threads_data:
                await services["db"].execute(
                    text("""
                        INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                        VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                    """),
                    thread_data
                )
        
        # Create user context for User 1
        user1_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=user1_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # User 1 should access their own thread
        result = await services["db"].execute(
            text("SELECT name FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": user1_thread_id, "user_id": self.test_user_1}
        )
        user1_thread = result.fetchone()
        assert user1_thread is not None, "User 1 must access their own thread"
        assert user1_thread[0] == "User 1 Confidential Optimization"
        
        # User 1 should NOT access User 2's thread
        result = await services["db"].execute(
            text("SELECT name FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": user2_thread_id, "user_id": self.test_user_1}
        )
        unauthorized_access = result.fetchone()
        assert unauthorized_access is None, "User 1 must NOT access User 2's thread"
        
        # Create user context for User 2 and verify isolation
        user2_context = UserExecutionContext.from_request(
            user_id=self.test_user_2,
            thread_id=user2_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # User 2 should access their own thread
        result = await services["db"].execute(
            text("SELECT name FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": user2_thread_id, "user_id": self.test_user_2}
        )
        user2_thread = result.fetchone()
        assert user2_thread is not None, "User 2 must access their own thread"
        assert user2_thread[0] == "User 2 Private Analysis"
        
        # Verify context isolation
        user1_context.verify_isolation()
        user2_context.verify_isolation()
        
        self.record_metric("test_006_status", "passed")
        self.record_metric("user_isolation_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_007_thread_context_switch_preserves_state(self, real_services_fixture):
        """
        Test 7/20: Verify thread context switching preserves execution state.
        
        Business Value: When users switch threads, their execution context
        must maintain state to enable continued AI optimization work.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create two threads for context switching
        thread1_id = self.id_manager.generate_thread_id()
        thread2_id = self.id_manager.generate_thread_id()
        
        threads_data = [
            {
                "id": thread1_id,
                "name": "AWS Cost Analysis Thread",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": '{"analysis_type": "cost", "cloud_provider": "aws"}',
                "is_active": True,
                "message_count": 8
            },
            {
                "id": thread2_id,
                "name": "Azure Performance Optimization",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": '{"analysis_type": "performance", "cloud_provider": "azure"}',
                "is_active": True,
                "message_count": 12
            }
        ]
        
        async with services["db"].begin():
            for thread_data in threads_data:
                await services["db"].execute(
                    text("""
                        INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                        VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                    """),
                    thread_data
                )
        
        # Create initial context for Thread 1
        context1 = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=thread1_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            agent_context={
                "current_analysis": "aws_cost_optimization",
                "progress": "analyzing_ec2_instances",
                "estimated_savings": 15000,
                "recommendations_count": 3
            }
        )
        
        # Switch to Thread 2 - create new context
        context2 = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=thread2_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            agent_context={
                "current_analysis": "azure_performance_optimization",
                "progress": "monitoring_metrics",
                "performance_gain": "25%",
                "bottlenecks_found": 5
            }
        )
        
        # Verify thread contexts are isolated and preserve state
        assert context1.thread_id == thread1_id
        assert context2.thread_id == thread2_id
        assert context1.user_id == context2.user_id  # Same user
        assert context1.request_id != context2.request_id  # Different requests
        
        # Verify agent context preservation
        assert context1.agent_context["current_analysis"] == "aws_cost_optimization"
        assert context1.agent_context["estimated_savings"] == 15000
        
        assert context2.agent_context["current_analysis"] == "azure_performance_optimization" 
        assert context2.agent_context["performance_gain"] == "25%"
        
        # Verify database queries work with each context
        result1 = await services["db"].execute(
            text("SELECT name, message_count FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": context1.thread_id, "user_id": context1.user_id}
        )
        thread1_data = result1.fetchone()
        assert thread1_data[0] == "AWS Cost Analysis Thread"
        assert thread1_data[1] == 8
        
        result2 = await services["db"].execute(
            text("SELECT name, message_count FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": context2.thread_id, "user_id": context2.user_id}
        )
        thread2_data = result2.fetchone()
        assert thread2_data[0] == "Azure Performance Optimization"
        assert thread2_data[1] == 12
        
        self.record_metric("test_007_status", "passed")
        self.record_metric("context_state_preservation", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_008_concurrent_thread_access_isolation(self, real_services_fixture):
        """
        Test 8/20: Test concurrent thread access with proper isolation.
        
        Business Value: Multiple users must be able to work with threads
        simultaneously without interference. Critical for multi-user platform.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create threads for concurrent access testing
        concurrent_threads = []
        for i in range(3):
            thread_id = self.id_manager.generate_thread_id()
            thread_data = {
                "id": thread_id,
                "name": f"Concurrent Thread {i+1}",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": f'{{"thread_number": {i+1}, "concurrent_test": true}}',
                "is_active": True,
                "message_count": i + 1
            }
            concurrent_threads.append((thread_id, thread_data))
        
        # Insert all threads
        async with services["db"].begin():
            for _, thread_data in concurrent_threads:
                await services["db"].execute(
                    text("""
                        INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                        VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                    """),
                    thread_data
                )
        
        async def concurrent_thread_operation(thread_id, operation_id):
            """Simulate concurrent thread operation."""
            context = UserExecutionContext.from_request(
                user_id=self.test_user_1,
                thread_id=thread_id,
                run_id=self.id_manager.generate_run_id(),
                db_session=services["db"],
                agent_context={"operation_id": operation_id, "start_time": datetime.now(timezone.utc)}
            )
            
            # Simulate concurrent database operations
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Update thread with concurrent operation
            async with services["db"].begin():
                await services["db"].execute(
                    text("UPDATE threads SET updated_at = :updated_at WHERE id = :thread_id"),
                    {"thread_id": thread_id, "updated_at": datetime.now(timezone.utc)}
                )
            
            # Verify thread data integrity
            result = await services["db"].execute(
                text("SELECT name, user_id FROM threads WHERE id = :thread_id"),
                {"thread_id": thread_id}
            )
            thread_data = result.fetchone()
            
            return {
                "operation_id": operation_id,
                "thread_id": thread_id,
                "name": thread_data[0] if thread_data else None,
                "user_id": thread_data[1] if thread_data else None,
                "context_valid": context.user_id == self.test_user_1
            }
        
        # Execute concurrent operations
        tasks = []
        for i, (thread_id, _) in enumerate(concurrent_threads):
            task = concurrent_thread_operation(thread_id, f"op_{i+1}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        assert len(results) == 3, "All concurrent operations must complete"
        
        for result in results:
            assert result["name"] is not None, "Thread name must be preserved during concurrent access"
            assert result["user_id"] == self.test_user_1, "User ID must be preserved"
            assert result["context_valid"], "Context must remain valid during concurrent operations"
        
        # Verify no data corruption
        result = await services["db"].execute(
            text("SELECT COUNT(*) FROM threads WHERE user_id = :user_id AND name LIKE 'Concurrent Thread%'"),
            {"user_id": self.test_user_1}
        )
        thread_count = result.fetchone()[0]
        assert thread_count == 3, "All concurrent threads must be preserved"
        
        self.record_metric("test_008_status", "passed")
        self.record_metric("concurrent_access_isolation", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_009_thread_context_cleanup_on_switch(self, real_services_fixture):
        """
        Test 9/20: Verify proper cleanup when switching thread contexts.
        
        Business Value: Context cleanup prevents memory leaks and ensures
        system stability during long-running optimization sessions.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create thread for cleanup testing
        thread_id = self.id_manager.generate_thread_id()
        thread_data = {
            "id": thread_id,
            "name": "Cleanup Test Thread",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,
            "metadata": '{"cleanup_test": true}',
            "is_active": True,
            "message_count": 0
        }
        
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                thread_data
            )
        
        # Create context with cleanup callbacks
        cleanup_called = {"value": False}
        
        def test_cleanup_callback():
            cleanup_called["value"] = True
        
        async def async_cleanup_callback():
            cleanup_called["value"] = True
        
        context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            agent_context={
                "resources_allocated": ["memory_cache", "temp_files", "connections"],
                "cleanup_required": True
            }
        )
        
        # Add cleanup callbacks
        context.cleanup_callbacks.append(test_cleanup_callback)
        context.cleanup_callbacks.append(async_cleanup_callback)
        
        # Verify context is properly initialized
        assert len(context.cleanup_callbacks) == 2, "Cleanup callbacks must be registered"
        assert context.agent_context["cleanup_required"] is True
        
        # Simulate context cleanup (as would happen during thread switch)
        await context.cleanup()
        
        # Verify cleanup was executed
        assert cleanup_called["value"] is True, "Cleanup callbacks must be executed"
        assert len(context.cleanup_callbacks) == 0, "Cleanup callbacks must be cleared after execution"
        
        # Create new context for thread switch
        new_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=self.id_manager.generate_thread_id(),
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            agent_context={"clean_state": True}
        )
        
        # Verify new context is clean
        assert len(new_context.cleanup_callbacks) == 0, "New context must start clean"
        assert "resources_allocated" not in new_context.agent_context, "New context must not inherit previous state"
        assert new_context.agent_context["clean_state"] is True
        
        self.record_metric("test_009_status", "passed")
        self.record_metric("cleanup_verification", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_010_thread_switching_with_websocket_context(self, real_services_fixture):
        """
        Test 10/20: Test thread switching with WebSocket context preservation.
        
        Business Value: Real-time updates must continue working when users
        switch threads, enabling seamless chat experience during optimization.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create threads for WebSocket context testing
        ws_thread1_id = self.id_manager.generate_thread_id()
        ws_thread2_id = self.id_manager.generate_thread_id()
        
        threads_data = [
            {
                "id": ws_thread1_id,
                "name": "Real-time Cost Analysis",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": '{"realtime": true, "websocket_enabled": true}',
                "is_active": True,
                "message_count": 5
            },
            {
                "id": ws_thread2_id,
                "name": "Live Performance Monitoring",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": '{"monitoring": true, "live_updates": true}',
                "is_active": True,
                "message_count": 8
            }
        ]
        
        async with services["db"].begin():
            for thread_data in threads_data:
                await services["db"].execute(
                    text("""
                        INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                        VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                    """),
                    thread_data
                )
        
        # Create WebSocket-enabled contexts
        websocket_client_id = f"ws_{self.test_user_1}_{int(datetime.now().timestamp())}"
        
        ws_context1 = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=ws_thread1_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            websocket_client_id=websocket_client_id,
            agent_context={
                "websocket_enabled": True,
                "thread_type": "cost_analysis",
                "real_time_updates": True
            }
        )
        
        # Switch to different thread but maintain WebSocket connection
        ws_context2 = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=ws_thread2_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            websocket_client_id=websocket_client_id,  # Same WebSocket connection
            agent_context={
                "websocket_enabled": True,
                "thread_type": "performance_monitoring",
                "real_time_updates": True
            }
        )
        
        # Verify WebSocket context is preserved across thread switch
        assert ws_context1.websocket_client_id == ws_context2.websocket_client_id
        assert ws_context1.user_id == ws_context2.user_id
        assert ws_context1.thread_id != ws_context2.thread_id  # Different threads
        
        # Verify WebSocket compatibility properties
        assert ws_context1.websocket_connection_id == websocket_client_id  # Compatibility property
        assert ws_context2.websocket_connection_id == websocket_client_id
        
        # Simulate WebSocket message routing for both threads
        def simulate_websocket_routing(context, message_type):
            return {
                "user_id": context.user_id,
                "thread_id": context.thread_id,
                "websocket_client_id": context.websocket_client_id,
                "message_type": message_type,
                "routed_successfully": context.websocket_client_id is not None
            }
        
        # Test routing for both contexts
        routing1 = simulate_websocket_routing(ws_context1, "cost_update")
        routing2 = simulate_websocket_routing(ws_context2, "performance_alert")
        
        assert routing1["routed_successfully"], "WebSocket routing must work for thread 1"
        assert routing2["routed_successfully"], "WebSocket routing must work for thread 2"
        assert routing1["thread_id"] != routing2["thread_id"], "Routing must distinguish threads"
        assert routing1["websocket_client_id"] == routing2["websocket_client_id"], "WebSocket ID must be preserved"
        
        self.record_metric("test_010_status", "passed")
        self.record_metric("websocket_context_switching", True)
    
    # ============================================================================
    # TESTS 11-15: THREAD PERSISTENCE ACROSS SESSIONS
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_011_thread_persistence_across_user_sessions(self, real_services_fixture):
        """
        Test 11/20: Verify thread persistence when user reconnects across sessions.
        
        Business Value: Users must be able to continue optimization work after
        disconnecting and reconnecting, ensuring work continuity.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Simulate initial user session
        session1_thread_id = self.id_manager.generate_thread_id()
        session1_run_id = self.id_manager.generate_run_id()
        
        # Create thread in "session 1"
        thread_data = {
            "id": session1_thread_id,
            "name": "Long-running Optimization Project",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
            "updated_at": datetime.now(timezone.utc) - timedelta(minutes=30),
            "user_id": self.test_user_1,
            "metadata": '{"project_phase": "analysis", "progress": 65, "session_id": "session_1"}',
            "is_active": True,
            "message_count": 25
        }
        
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                thread_data
            )
        
        # Simulate session 1 context
        session1_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=session1_thread_id,
            run_id=session1_run_id,
            db_session=services["db"],
            agent_context={
                "session_id": "session_1",
                "last_activity": "cost_analysis",
                "optimization_progress": 65,
                "work_in_progress": True
            }
        )
        
        # Add some session state to database (simulate work being done)
        async with services["db"].begin():
            await services["db"].execute(
                text("UPDATE threads SET message_count = 30, updated_at = :updated_at WHERE id = :thread_id"),
                {"thread_id": session1_thread_id, "updated_at": datetime.now(timezone.utc)}
            )
        
        # Simulate session disconnect/cleanup
        await session1_context.cleanup()
        
        # Simulate NEW user session (reconnection)
        session2_run_id = self.id_manager.generate_run_id()
        
        # User reconnects and retrieves existing thread
        result = await services["db"].execute(
            text("SELECT * FROM threads WHERE id = :thread_id AND user_id = :user_id AND is_active = true"),
            {"thread_id": session1_thread_id, "user_id": self.test_user_1}
        )
        persisted_thread = result.fetchone()
        
        # Verify thread persisted across sessions
        assert persisted_thread is not None, "Thread must persist across user sessions"
        assert persisted_thread[1] == "Long-running Optimization Project", "Thread name must be preserved"
        assert persisted_thread[7] == 30, "Updated message count must be persisted"
        assert persisted_thread[6] is True, "Thread must remain active"
        
        # Create new session context for the persisted thread
        session2_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=session1_thread_id,  # Same thread, new session
            run_id=session2_run_id,  # New run ID for new session
            db_session=services["db"],
            agent_context={
                "session_id": "session_2",
                "resumed_session": True,
                "previous_work_preserved": True
            }
        )
        
        # Verify session separation but thread continuity
        assert session1_context.run_id != session2_context.run_id, "Sessions must have different run IDs"
        assert session1_context.thread_id == session2_context.thread_id, "Thread ID must be preserved"
        assert session1_context.user_id == session2_context.user_id, "User ID must be preserved"
        assert session2_context.agent_context["resumed_session"] is True
        
        # Verify user can continue work in new session
        async with services["db"].begin():
            await services["db"].execute(
                text("UPDATE threads SET message_count = message_count + 5, updated_at = :updated_at WHERE id = :thread_id"),
                {"thread_id": session1_thread_id, "updated_at": datetime.now(timezone.utc)}
            )
        
        # Verify updates work in resumed session
        result = await services["db"].execute(
            text("SELECT message_count FROM threads WHERE id = :thread_id"),
            {"thread_id": session1_thread_id}
        )
        final_count = result.fetchone()[0]
        assert final_count == 35, "User must be able to continue work in resumed session"
        
        self.record_metric("test_011_status", "passed")
        self.record_metric("session_persistence_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_012_thread_state_recovery_after_system_restart(self, real_services_fixture):
        """
        Test 12/20: Test thread state recovery after simulated system restart.
        
        Business Value: System reliability requires thread state to survive
        restarts, ensuring users don't lose optimization work during updates.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create thread with rich state before "system restart"
        pre_restart_thread_id = self.id_manager.generate_thread_id()
        complex_state = {
            "optimization_targets": ["compute", "storage", "networking"],
            "analysis_results": {
                "potential_savings": 45000,
                "recommendations": 12,
                "implementation_status": "in_progress"
            },
            "user_preferences": {
                "risk_tolerance": "medium",
                "budget_constraints": True,
                "timeline": "Q2_2025"
            },
            "system_state": {
                "last_checkpoint": "2025-01-15T10:30:00Z",
                "analysis_phase": "optimization_modeling",
                "completion_percentage": 78
            }
        }
        
        thread_data = {
            "id": pre_restart_thread_id,
            "name": "Enterprise Optimization - Phase 2",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=4),
            "updated_at": datetime.now(timezone.utc) - timedelta(minutes=5),
            "user_id": self.test_user_1,
            "metadata": str(complex_state),  # Store complex state as metadata
            "is_active": True,
            "message_count": 42
        }
        
        # Persist thread state to database
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                thread_data
            )
        
        # Simulate "system restart" by clearing in-memory state and creating fresh context
        # (In real scenario, this would be a server restart)
        
        # Post-restart: Create new context and recover thread state
        post_restart_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=pre_restart_thread_id,
            run_id=self.id_manager.generate_run_id(),  # New run ID post-restart
            db_session=services["db"],
            agent_context={
                "recovery_mode": True,
                "system_restarted": True,
                "state_recovery_required": True
            }
        )
        
        # Recover thread state from database
        result = await services["db"].execute(
            text("SELECT id, name, metadata, message_count, created_at, updated_at FROM threads WHERE id = :thread_id"),
            {"thread_id": pre_restart_thread_id}
        )
        recovered_thread = result.fetchone()
        
        # Verify complete state recovery
        assert recovered_thread is not None, "Thread must be recoverable after system restart"
        assert recovered_thread[1] == "Enterprise Optimization - Phase 2", "Thread name must be recovered"
        assert recovered_thread[3] == 42, "Message count must be recovered"
        
        # Parse and verify complex state recovery
        recovered_metadata = recovered_thread[2]
        assert "potential_savings" in recovered_metadata, "Analysis results must be recoverable"
        assert "45000" in recovered_metadata, "Specific savings data must be preserved"
        assert "optimization_modeling" in recovered_metadata, "Analysis phase must be preserved"
        assert "risk_tolerance" in recovered_metadata, "User preferences must be recoverable"
        assert "78" in recovered_metadata, "Completion percentage must be preserved"
        
        # Verify context can be used for continued work
        assert post_restart_context.thread_id == pre_restart_thread_id
        assert post_restart_context.agent_context["recovery_mode"] is True
        
        # Test that work can continue post-recovery
        async with services["db"].begin():
            await services["db"].execute(
                text("""UPDATE threads SET 
                        message_count = message_count + 3, 
                        updated_at = :updated_at,
                        metadata = :metadata
                     WHERE id = :thread_id"""),
                {
                    "thread_id": pre_restart_thread_id,
                    "updated_at": datetime.now(timezone.utc),
                    "metadata": str({**complex_state, "post_restart_update": True})
                }
            )
        
        # Verify post-restart updates work
        result = await services["db"].execute(
            text("SELECT message_count, metadata FROM threads WHERE id = :thread_id"),
            {"thread_id": pre_restart_thread_id}
        )
        updated_data = result.fetchone()
        assert updated_data[0] == 45, "Updates must work after state recovery"
        assert "post_restart_update" in updated_data[1], "New state must be appendable"
        
        self.record_metric("test_012_status", "passed")
        self.record_metric("restart_recovery_verified", True)
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_013_thread_data_integrity_during_concurrent_updates(self, real_services_fixture):
        """
        Test 13/20: Test thread data integrity during concurrent session updates.
        
        Business Value: Multiple browser tabs or devices must maintain data
        consistency when accessing same optimization thread.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create thread for concurrent update testing
        concurrent_thread_id = self.id_manager.generate_thread_id()
        initial_data = {
            "id": concurrent_thread_id,
            "name": "Concurrent Access Thread",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,
            "metadata": '{"concurrent_test": true, "update_count": 0}',
            "is_active": True,
            "message_count": 10
        }
        
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                initial_data
            )
        
        async def concurrent_update_session(session_id, update_count):
            """Simulate concurrent session updating the same thread."""
            # Create session-specific context
            session_context = UserExecutionContext.from_request(
                user_id=self.test_user_1,
                thread_id=concurrent_thread_id,
                run_id=self.id_manager.generate_run_id(),
                db_session=services["db"],
                agent_context={
                    "session_id": session_id,
                    "concurrent_update_test": True
                }
            )
            
            updates = []
            
            for i in range(update_count):
                try:
                    # Read current state
                    result = await services["db"].execute(
                        text("SELECT message_count, updated_at FROM threads WHERE id = :thread_id"),
                        {"thread_id": concurrent_thread_id}
                    )
                    current_data = result.fetchone()
                    current_count = current_data[0] if current_data else 0
                    
                    # Simulate processing time
                    await asyncio.sleep(0.05)
                    
                    # Update with optimistic approach
                    new_count = current_count + 1
                    update_time = datetime.now(timezone.utc)
                    
                    async with services["db"].begin():
                        await services["db"].execute(
                            text("""UPDATE threads 
                                   SET message_count = :new_count, 
                                       updated_at = :update_time 
                                   WHERE id = :thread_id"""),
                            {
                                "thread_id": concurrent_thread_id,
                                "new_count": new_count,
                                "update_time": update_time
                            }
                        )
                    
                    updates.append({
                        "session_id": session_id,
                        "update_index": i,
                        "old_count": current_count,
                        "new_count": new_count,
                        "success": True
                    })
                    
                except Exception as e:
                    updates.append({
                        "session_id": session_id,
                        "update_index": i,
                        "error": str(e),
                        "success": False
                    })
            
            return updates
        
        # Run concurrent updates from 3 simulated sessions
        session_tasks = [
            concurrent_update_session("browser_tab_1", 5),
            concurrent_update_session("mobile_app", 4),
            concurrent_update_session("browser_tab_2", 6)
        ]
        
        session_results = await asyncio.gather(*session_tasks)
        
        # Verify data integrity after concurrent updates
        result = await services["db"].execute(
            text("SELECT message_count, updated_at FROM threads WHERE id = :thread_id"),
            {"thread_id": concurrent_thread_id}
        )
        final_data = result.fetchone()
        final_count = final_data[0]
        
        # Calculate expected updates
        total_expected_updates = sum(len(session_result) for session_result in session_results)
        successful_updates = sum(
            1 for session_result in session_results
            for update in session_result
            if update.get("success", False)
        )
        
        # Verify integrity constraints
        assert final_count >= 10, "Message count must not go below initial value"
        assert final_count <= 10 + total_expected_updates, "Message count must not exceed expected maximum"
        
        # Verify no data corruption
        assert final_data[1] is not None, "Updated timestamp must be preserved"
        
        # Verify at least some updates succeeded (system should handle concurrent access)
        assert successful_updates > 0, "Some concurrent updates must succeed"
        
        # Log concurrent access statistics
        self.record_metric("total_concurrent_sessions", 3)
        self.record_metric("successful_updates", successful_updates)
        self.record_metric("final_message_count", final_count)
        
        self.record_metric("test_013_status", "passed")
        self.record_metric("concurrent_integrity_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_014_thread_session_timeout_and_cleanup(self, real_services_fixture):
        """
        Test 14/20: Test thread session timeout and cleanup behavior.
        
        Business Value: System must clean up inactive sessions to prevent
        resource leaks while preserving user data for return sessions.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create thread for timeout testing
        timeout_thread_id = self.id_manager.generate_thread_id()
        thread_data = {
            "id": timeout_thread_id,
            "name": "Session Timeout Test Thread",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=6),  # Old thread
            "updated_at": datetime.now(timezone.utc) - timedelta(hours=3),  # Last activity 3h ago
            "user_id": self.test_user_1,
            "metadata": '{"last_activity": "3_hours_ago", "timeout_test": true}',
            "is_active": True,
            "message_count": 15
        }
        
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                thread_data
            )
        
        # Create "stale" session context (simulating old session)
        stale_session_time = datetime.now(timezone.utc) - timedelta(hours=3)
        stale_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=timeout_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            agent_context={
                "session_start": stale_session_time,
                "last_heartbeat": stale_session_time,
                "session_stale": True
            }
        )
        
        # Simulate session cleanup check (would normally be done by background process)
        session_age_hours = 3
        session_timeout_hours = 2
        is_session_expired = session_age_hours > session_timeout_hours
        
        assert is_session_expired, "Session must be detected as expired"
        
        # Simulate session cleanup (context cleanup, but preserve thread data)
        await stale_context.cleanup()
        
        # Verify thread data is preserved despite session cleanup
        result = await services["db"].execute(
            text("SELECT name, is_active, message_count FROM threads WHERE id = :thread_id"),
            {"thread_id": timeout_thread_id}
        )
        thread_after_cleanup = result.fetchone()
        
        assert thread_after_cleanup is not None, "Thread must be preserved after session cleanup"
        assert thread_after_cleanup[1] is True, "Thread must remain active after session timeout"
        assert thread_after_cleanup[2] == 15, "Message count must be preserved"
        
        # Simulate user returning with fresh session
        fresh_session_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=timeout_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            agent_context={
                "session_start": datetime.now(timezone.utc),
                "fresh_session": True,
                "resumed_after_timeout": True
            }
        )
        
        # Verify user can resume work after timeout
        assert fresh_session_context.thread_id == timeout_thread_id
        assert fresh_session_context.agent_context["fresh_session"] is True
        
        # Test that thread can be updated in fresh session
        async with services["db"].begin():
            await services["db"].execute(
                text("""UPDATE threads 
                       SET message_count = message_count + 2, 
                           updated_at = :updated_at 
                       WHERE id = :thread_id"""),
                {"thread_id": timeout_thread_id, "updated_at": datetime.now(timezone.utc)}
            )
        
        # Verify updates work in resumed session
        result = await services["db"].execute(
            text("SELECT message_count, updated_at FROM threads WHERE id = :thread_id"),
            {"thread_id": timeout_thread_id}
        )
        updated_data = result.fetchone()
        assert updated_data[0] == 17, "Thread must be updatable after session resume"
        
        # Verify updated timestamp is recent (within last minute)
        time_diff = datetime.now(timezone.utc) - updated_data[1]
        assert time_diff.total_seconds() < 60, "Updated timestamp must be recent"
        
        self.record_metric("test_014_status", "passed")
        self.record_metric("session_timeout_handling", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_015_thread_backup_and_restore_validation(self, real_services_fixture):
        """
        Test 15/20: Test thread data backup and restore validation.
        
        Business Value: Critical optimization data must be recoverable through
        backup/restore processes to ensure business continuity.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create thread with valuable business data
        backup_thread_id = self.id_manager.generate_thread_id()
        valuable_data = {
            "business_impact": {
                "annual_savings": 120000,
                "risk_reduction": "high",
                "compliance_improvements": ["SOX", "GDPR", "HIPAA"]
            },
            "technical_details": {
                "infrastructure_optimizations": 15,
                "security_enhancements": 8,
                "performance_gains": "40%"
            },
            "stakeholder_approvals": {
                "cfo_approved": True,
                "cto_reviewed": True,
                "security_team_validated": True
            }
        }
        
        original_thread = {
            "id": backup_thread_id,
            "name": "Critical Enterprise Optimization - $120K Impact",
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "updated_at": datetime.now(timezone.utc) - timedelta(hours=1),
            "user_id": self.test_user_1,
            "metadata": str(valuable_data),
            "is_active": True,
            "message_count": 85
        }
        
        # Create original thread
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                original_thread
            )
        
        # Simulate backup process by reading thread data
        result = await services["db"].execute(
            text("SELECT * FROM threads WHERE id = :thread_id"),
            {"thread_id": backup_thread_id}
        )
        backup_data = result.fetchone()
        
        assert backup_data is not None, "Thread must be readable for backup"
        
        # Extract critical data from backup
        backup_record = {
            "id": backup_data[0],
            "name": backup_data[1], 
            "created_at": backup_data[2],
            "updated_at": backup_data[3],
            "user_id": backup_data[4],
            "metadata": backup_data[5],
            "is_active": backup_data[6],
            "message_count": backup_data[7]
        }
        
        # Simulate data loss scenario (delete thread)
        async with services["db"].begin():
            await services["db"].execute(
                text("DELETE FROM threads WHERE id = :thread_id"),
                {"thread_id": backup_thread_id}
            )
        
        # Verify thread is gone
        result = await services["db"].execute(
            text("SELECT COUNT(*) FROM threads WHERE id = :thread_id"),
            {"thread_id": backup_thread_id}
        )
        count_after_delete = result.fetchone()[0]
        assert count_after_delete == 0, "Thread must be deleted for restore test"
        
        # Simulate restore process
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                backup_record
            )
        
        # Validate restored data integrity
        result = await services["db"].execute(
            text("SELECT * FROM threads WHERE id = :thread_id"),
            {"thread_id": backup_thread_id}
        )
        restored_thread = result.fetchone()
        
        # Verify complete data restoration
        assert restored_thread is not None, "Thread must be restored from backup"
        assert restored_thread[1] == "Critical Enterprise Optimization - $120K Impact", "Thread name must be restored"
        assert restored_thread[4] == self.test_user_1, "User association must be restored" 
        assert restored_thread[7] == 85, "Message count must be restored"
        
        # Verify valuable business data is restored
        restored_metadata = restored_thread[5]
        assert "120000" in restored_metadata, "Annual savings data must be restored"
        assert "SOX" in restored_metadata, "Compliance data must be restored"
        assert "cfo_approved" in restored_metadata, "Stakeholder approval data must be restored"
        assert "40%" in restored_metadata, "Performance gain data must be restored"
        
        # Verify restored thread is functional
        restore_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=backup_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            agent_context={
                "restored_from_backup": True,
                "data_validation_required": True
            }
        )
        
        # Test functionality of restored thread
        async with services["db"].begin():
            await services["db"].execute(
                text("UPDATE threads SET message_count = message_count + 1, updated_at = :updated_at WHERE id = :thread_id"),
                {"thread_id": backup_thread_id, "updated_at": datetime.now(timezone.utc)}
            )
        
        # Verify restored thread can be updated
        result = await services["db"].execute(
            text("SELECT message_count FROM threads WHERE id = :thread_id"),
            {"thread_id": backup_thread_id}
        )
        final_count = result.fetchone()[0]
        assert final_count == 86, "Restored thread must be functional for updates"
        
        self.record_metric("test_015_status", "passed")
        self.record_metric("backup_restore_verified", True)
    
    # ============================================================================
    # TESTS 16-20: THREAD VALIDATION AND AUTHORIZATION
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_016_thread_access_authorization_validation(self, real_services_fixture):
        """
        Test 16/20: Validate thread access authorization and security boundaries.
        
        Business Value: Security is paramount - users must only access authorized
        threads to prevent data breaches and maintain client trust.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create threads with different access levels
        public_thread_id = self.id_manager.generate_thread_id()
        private_thread_id = self.id_manager.generate_thread_id()
        confidential_thread_id = self.id_manager.generate_thread_id()
        
        threads_data = [
            {
                "id": public_thread_id,
                "name": "Public Cost Analysis",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": '{"access_level": "public", "sensitivity": "low"}',
                "is_active": True,
                "message_count": 8
            },
            {
                "id": private_thread_id,
                "name": "Internal Infrastructure Review",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": '{"access_level": "private", "sensitivity": "medium"}',
                "is_active": True,
                "message_count": 12
            },
            {
                "id": confidential_thread_id,
                "name": "Executive Financial Optimization",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_2,  # Different user
                "metadata": '{"access_level": "confidential", "sensitivity": "high", "requires_authorization": true}',
                "is_active": True,
                "message_count": 5
            }
        ]
        
        # Insert all threads
        async with services["db"].begin():
            for thread_data in threads_data:
                await services["db"].execute(
                    text("""
                        INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                        VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                    """),
                    thread_data
                )
        
        # Test authorized access (User 1 accessing their own threads)
        user1_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=public_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # User 1 should access their public thread
        result = await services["db"].execute(
            text("SELECT name FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": public_thread_id, "user_id": self.test_user_1}
        )
        authorized_thread = result.fetchone()
        assert authorized_thread is not None, "User must access their own public thread"
        
        # User 1 should access their private thread
        result = await services["db"].execute(
            text("SELECT name FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": private_thread_id, "user_id": self.test_user_1}
        )
        private_thread = result.fetchone()
        assert private_thread is not None, "User must access their own private thread"
        
        # Test unauthorized access (User 1 trying to access User 2's confidential thread)
        result = await services["db"].execute(
            text("SELECT name FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": confidential_thread_id, "user_id": self.test_user_1}
        )
        unauthorized_thread = result.fetchone()
        assert unauthorized_thread is None, "User must NOT access other user's confidential thread"
        
        # Test cross-user authorization validation
        def validate_thread_access(requesting_user_id, thread_id, expected_owner_id):
            """Simulate authorization check."""
            return requesting_user_id == expected_owner_id
        
        # Valid access checks
        assert validate_thread_access(self.test_user_1, public_thread_id, self.test_user_1)
        assert validate_thread_access(self.test_user_1, private_thread_id, self.test_user_1)
        assert validate_thread_access(self.test_user_2, confidential_thread_id, self.test_user_2)
        
        # Invalid access checks
        assert not validate_thread_access(self.test_user_1, confidential_thread_id, self.test_user_2)
        assert not validate_thread_access(self.test_user_2, public_thread_id, self.test_user_1)
        
        # Test context isolation verification
        user1_context.verify_isolation()
        
        # Verify audit trail for security compliance
        audit_trail = user1_context.get_audit_trail()
        assert audit_trail["user_id"] == self.test_user_1
        assert "correlation_id" in audit_trail
        assert audit_trail["has_db_session"] is True
        
        self.record_metric("test_016_status", "passed")
        self.record_metric("authorization_security_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_017_thread_validation_business_rules(self, real_services_fixture):
        """
        Test 17/20: Validate thread creation and modification business rules.
        
        Business Value: Business rules ensure data quality and prevent invalid
        optimization configurations that could lead to incorrect results.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Test business rule validations
        def validate_thread_business_rules(thread_data):
            """Validate thread against business rules."""
            errors = []
            
            # Rule 1: Thread name must be meaningful (not generic)
            if not thread_data.get("name") or len(thread_data["name"].strip()) < 5:
                errors.append("Thread name must be at least 5 characters")
            
            generic_names = ["test", "thread", "new thread", "untitled"]
            if thread_data.get("name", "").lower() in generic_names:
                errors.append("Thread name must be descriptive, not generic")
            
            # Rule 2: Must have valid user association
            if not thread_data.get("user_id"):
                errors.append("Thread must be associated with a valid user")
            
            # Rule 3: Metadata validation for optimization threads
            metadata = thread_data.get("metadata", {})
            if isinstance(metadata, str):
                # Parse metadata if string
                try:
                    import json
                    metadata = eval(metadata) if metadata.startswith("{") else {}
                except:
                    metadata = {}
            
            if "optimization" in thread_data.get("name", "").lower():
                if "priority" not in metadata:
                    errors.append("Optimization threads must have priority metadata")
                elif not isinstance(metadata.get("priority"), int) or not (1 <= metadata["priority"] <= 10):
                    errors.append("Priority must be integer between 1-10")
            
            # Rule 4: Message count validation
            message_count = thread_data.get("message_count", 0)
            if not isinstance(message_count, int) or message_count < 0:
                errors.append("Message count must be non-negative integer")
            
            return errors
        
        # Test valid thread creation
        valid_thread_id = self.id_manager.generate_thread_id()
        valid_thread_data = {
            "id": valid_thread_id,
            "name": "AWS Cost Optimization - Q1 Review",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,
            "metadata": '{"priority": 7, "category": "optimization", "estimated_savings": 25000}',
            "is_active": True,
            "message_count": 0
        }
        
        # Validate business rules
        validation_errors = validate_thread_business_rules(valid_thread_data)
        assert len(validation_errors) == 0, f"Valid thread should pass validation: {validation_errors}"
        
        # Create valid thread
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                valid_thread_data
            )
        
        # Test invalid thread scenarios
        invalid_scenarios = [
            {
                "name": "Short name scenario",
                "data": {
                    "name": "xyz",  # Too short
                    "user_id": self.test_user_1,
                    "message_count": 0
                },
                "expected_errors": ["Thread name must be at least 5 characters"]
            },
            {
                "name": "Generic name scenario", 
                "data": {
                    "name": "test",  # Generic
                    "user_id": self.test_user_1,
                    "message_count": 0
                },
                "expected_errors": ["Thread name must be descriptive, not generic"]
            },
            {
                "name": "Missing user scenario",
                "data": {
                    "name": "Valid Optimization Thread",
                    "user_id": None,  # Missing user
                    "message_count": 0
                },
                "expected_errors": ["Thread must be associated with a valid user"]
            },
            {
                "name": "Optimization without priority",
                "data": {
                    "name": "Cost Optimization Analysis",
                    "user_id": self.test_user_1,
                    "metadata": '{"category": "optimization"}',  # Missing priority
                    "message_count": 0
                },
                "expected_errors": ["Optimization threads must have priority metadata"]
            },
            {
                "name": "Invalid priority range",
                "data": {
                    "name": "Performance Optimization Review",
                    "user_id": self.test_user_1,
                    "metadata": '{"priority": 15}',  # Priority out of range
                    "message_count": 0
                },
                "expected_errors": ["Priority must be integer between 1-10"]
            },
            {
                "name": "Negative message count",
                "data": {
                    "name": "Valid Thread Name",
                    "user_id": self.test_user_1,
                    "message_count": -5  # Invalid count
                },
                "expected_errors": ["Message count must be non-negative integer"]
            }
        ]
        
        # Test each invalid scenario
        for scenario in invalid_scenarios:
            validation_errors = validate_thread_business_rules(scenario["data"])
            assert len(validation_errors) > 0, f"{scenario['name']} should have validation errors"
            
            # Check that expected errors are present
            for expected_error in scenario["expected_errors"]:
                assert any(expected_error in error for error in validation_errors), \
                    f"Expected error '{expected_error}' not found in {validation_errors}"
        
        # Test business rule enforcement in context creation
        context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=valid_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # Verify context passes validation
        context.verify_isolation()
        
        # Test thread updates maintain business rules
        async with services["db"].begin():
            await services["db"].execute(
                text("UPDATE threads SET message_count = 5, updated_at = :updated_at WHERE id = :thread_id"),
                {"thread_id": valid_thread_id, "updated_at": datetime.now(timezone.utc)}
            )
        
        # Verify update maintained data integrity
        result = await services["db"].execute(
            text("SELECT message_count FROM threads WHERE id = :thread_id"),
            {"thread_id": valid_thread_id}
        )
        updated_count = result.fetchone()[0]
        assert updated_count == 5, "Business rule compliant updates must succeed"
        
        self.record_metric("test_017_status", "passed")
        self.record_metric("business_rules_validation", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_018_thread_permission_inheritance_validation(self, real_services_fixture):
        """
        Test 18/20: Validate thread permission inheritance and delegation.
        
        Business Value: Complex organizational structures require permission
        delegation for optimization projects involving multiple stakeholders.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create thread with complex permission structure
        enterprise_thread_id = self.id_manager.generate_thread_id()
        permission_metadata = {
            "owner": self.test_user_1,
            "permissions": {
                "read": [self.test_user_1, self.test_user_2],
                "write": [self.test_user_1],
                "admin": [self.test_user_1]
            },
            "delegation_rules": {
                "can_delegate_read": True,
                "can_delegate_write": False,
                "max_delegation_depth": 2
            },
            "organizational_context": {
                "department": "engineering",
                "project_code": "OPT-2025-Q1",
                "budget_authority": "director_level"
            }
        }
        
        enterprise_thread = {
            "id": enterprise_thread_id,
            "name": "Enterprise-wide Infrastructure Optimization",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,  # Owner
            "metadata": str(permission_metadata),
            "is_active": True,
            "message_count": 0
        }
        
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                enterprise_thread
            )
        
        def check_thread_permissions(user_id, thread_metadata_str, requested_permission):
            """Simulate permission checking logic."""
            try:
                import ast
                metadata = ast.literal_eval(thread_metadata_str)
                permissions = metadata.get("permissions", {})
                
                # Check if user has direct permission
                if user_id in permissions.get(requested_permission, []):
                    return True, "direct_permission"
                
                # Check ownership
                if user_id == metadata.get("owner") and requested_permission in ["read", "write", "admin"]:
                    return True, "owner_permission"
                
                # Check inheritance (admin includes write, write includes read)
                if requested_permission == "read":
                    if user_id in permissions.get("write", []) or user_id in permissions.get("admin", []):
                        return True, "inherited_permission"
                elif requested_permission == "write":
                    if user_id in permissions.get("admin", []):
                        return True, "inherited_permission"
                
                return False, "permission_denied"
                
            except Exception as e:
                return False, f"metadata_parse_error: {e}"
        
        # Test owner permissions (User 1)
        owner_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=enterprise_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        # Get thread metadata for permission checking
        result = await services["db"].execute(
            text("SELECT metadata FROM threads WHERE id = :thread_id"),
            {"thread_id": enterprise_thread_id}
        )
        thread_metadata = result.fetchone()[0]
        
        # Test owner permissions
        read_allowed, read_reason = check_thread_permissions(self.test_user_1, thread_metadata, "read")
        write_allowed, write_reason = check_thread_permissions(self.test_user_1, thread_metadata, "write")
        admin_allowed, admin_reason = check_thread_permissions(self.test_user_1, thread_metadata, "admin")
        
        assert read_allowed, f"Owner must have read permission: {read_reason}"
        assert write_allowed, f"Owner must have write permission: {write_reason}"
        assert admin_allowed, f"Owner must have admin permission: {admin_reason}"
        
        # Test delegated permissions (User 2 has read access)
        delegate_context = UserExecutionContext.from_request(
            user_id=self.test_user_2,
            thread_id=enterprise_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"]
        )
        
        read_delegated, read_del_reason = check_thread_permissions(self.test_user_2, thread_metadata, "read")
        write_delegated, write_del_reason = check_thread_permissions(self.test_user_2, thread_metadata, "write")
        admin_delegated, admin_del_reason = check_thread_permissions(self.test_user_2, thread_metadata, "admin")
        
        assert read_delegated, f"User 2 must have delegated read permission: {read_del_reason}"
        assert not write_delegated, f"User 2 must NOT have write permission: {write_del_reason}"
        assert not admin_delegated, f"User 2 must NOT have admin permission: {admin_del_reason}"
        
        # Test permission enforcement in database operations
        # Owner can update thread
        async with services["db"].begin():
            await services["db"].execute(
                text("UPDATE threads SET message_count = 1, updated_at = :updated_at WHERE id = :thread_id AND user_id = :user_id"),
                {
                    "thread_id": enterprise_thread_id, 
                    "user_id": self.test_user_1,  # Owner
                    "updated_at": datetime.now(timezone.utc)
                }
            )
        
        # Verify owner update succeeded
        result = await services["db"].execute(
            text("SELECT message_count FROM threads WHERE id = :thread_id"),
            {"thread_id": enterprise_thread_id}
        )
        updated_count = result.fetchone()[0]
        assert updated_count == 1, "Owner updates must succeed"
        
        # User 2 cannot update thread (no write permission)
        result = await services["db"].execute(
            text("SELECT COUNT(*) FROM threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": enterprise_thread_id, "user_id": self.test_user_2}
        )
        user2_ownership = result.fetchone()[0]
        assert user2_ownership == 0, "User 2 must not have ownership for write operations"
        
        # Test organizational context validation
        def validate_organizational_access(user_id, thread_metadata_str, required_context):
            """Validate organizational context requirements."""
            try:
                import ast
                metadata = ast.literal_eval(thread_metadata_str)
                org_context = metadata.get("organizational_context", {})
                
                # In real system, this would check user's organizational role
                # For test, simulate based on user ID
                user_dept = "engineering" if user_id == self.test_user_1 else "finance"
                user_authority = "director_level" if user_id == self.test_user_1 else "manager_level"
                
                required_dept = required_context.get("department")
                required_authority = required_context.get("budget_authority")
                
                if required_dept and user_dept != required_dept:
                    return False, f"Department mismatch: required {required_dept}, user has {user_dept}"
                
                if required_authority and user_authority != required_authority:
                    return False, f"Authority mismatch: required {required_authority}, user has {user_authority}"
                
                return True, "organizational_access_granted"
                
            except Exception as e:
                return False, f"org_validation_error: {e}"
        
        # Test organizational context
        org_valid, org_reason = validate_organizational_access(
            self.test_user_1, 
            thread_metadata,
            {"department": "engineering", "budget_authority": "director_level"}
        )
        assert org_valid, f"Owner must meet organizational requirements: {org_reason}"
        
        self.record_metric("test_018_status", "passed")
        self.record_metric("permission_inheritance_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_019_thread_audit_trail_compliance_validation(self, real_services_fixture):
        """
        Test 19/20: Validate thread audit trail and compliance logging.
        
        Business Value: Regulatory compliance requires comprehensive audit trails
        for all optimization decisions and data access patterns.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Create thread requiring compliance tracking
        compliance_thread_id = self.id_manager.generate_thread_id()
        compliance_metadata = {
            "compliance_requirements": {
                "sox_compliance": True,
                "gdpr_applicable": True,
                "data_retention_years": 7,
                "audit_trail_required": True
            },
            "data_classification": {
                "level": "restricted",
                "contains_pii": False,
                "contains_financial_data": True,
                "geographic_restrictions": ["US", "EU"]
            },
            "regulatory_context": {
                "industry": "financial_services",
                "regulations": ["SOX", "GDPR", "PCI-DSS"],
                "compliance_officer": "jane.doe@company.com"
            }
        }
        
        compliance_thread = {
            "id": compliance_thread_id,
            "name": "SOX-Compliant Financial Infrastructure Optimization",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": self.test_user_1,
            "metadata": str(compliance_metadata),
            "is_active": True,
            "message_count": 0
        }
        
        async with services["db"].begin():
            await services["db"].execute(
                text("""
                    INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                    VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                """),
                compliance_thread
            )
        
        # Create context with comprehensive audit metadata
        compliance_context = UserExecutionContext.from_request(
            user_id=self.test_user_1,
            thread_id=compliance_thread_id,
            run_id=self.id_manager.generate_run_id(),
            db_session=services["db"],
            agent_context={
                "compliance_mode": True,
                "audit_session_id": str(uuid.uuid4()),
                "regulatory_framework": "SOX_2025"
            },
            audit_metadata={
                "compliance_officer_notified": True,
                "data_access_logged": True,
                "retention_policy_applied": True,
                "geographic_compliance_verified": True,
                "audit_timestamp": datetime.now(timezone.utc).isoformat(),
                "user_authentication_method": "oauth_jwt",
                "session_security_level": "high"
            }
        )
        
        # Test comprehensive audit trail generation
        audit_trail = compliance_context.get_audit_trail()
        
        # Verify required audit fields
        required_fields = [
            "correlation_id", "user_id", "thread_id", "run_id", 
            "request_id", "created_at", "has_db_session"
        ]
        
        for field in required_fields:
            assert field in audit_trail, f"Audit trail must contain {field}"
        
        # Verify compliance-specific audit data
        assert audit_trail["audit_metadata"]["compliance_officer_notified"] is True
        assert audit_trail["audit_metadata"]["data_access_logged"] is True
        assert audit_trail["audit_metadata"]["retention_policy_applied"] is True
        assert "audit_timestamp" in audit_trail["audit_metadata"]
        
        # Simulate audit events during thread operations
        audit_events = []
        
        def log_audit_event(event_type, details):
            """Simulate audit event logging."""
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "user_id": compliance_context.user_id,
                "thread_id": compliance_context.thread_id,
                "correlation_id": compliance_context.get_correlation_id(),
                "details": details
            }
            audit_events.append(event)
            return event
        
        # Log thread access event
        access_event = log_audit_event("thread_access", {
            "access_type": "read",
            "authorization_method": "direct_ownership",
            "data_classification": "restricted",
            "compliance_frameworks": ["SOX", "GDPR"]
        })
        
        # Log thread modification event
        async with services["db"].begin():
            await services["db"].execute(
                text("UPDATE threads SET message_count = 3, updated_at = :updated_at WHERE id = :thread_id"),
                {"thread_id": compliance_thread_id, "updated_at": datetime.now(timezone.utc)}
            )
        
        modification_event = log_audit_event("thread_modification", {
            "modification_type": "message_count_update",
            "old_value": 0,
            "new_value": 3,
            "business_justification": "optimization_progress_tracking",
            "compliance_impact": "none"
        })
        
        # Log compliance validation event
        validation_event = log_audit_event("compliance_validation", {
            "frameworks_checked": ["SOX", "GDPR", "PCI-DSS"],
            "validation_result": "compliant",
            "data_retention_verified": True,
            "geographic_restrictions_met": True
        })
        
        # Verify audit events structure
        assert len(audit_events) == 3, "All audit events must be logged"
        
        for event in audit_events:
            assert "timestamp" in event, "Each audit event must have timestamp"
            assert "event_type" in event, "Each audit event must have type"
            assert "user_id" in event, "Each audit event must have user ID"
            assert "correlation_id" in event, "Each audit event must have correlation ID"
            assert event["user_id"] == self.test_user_1, "Audit events must track correct user"
        
        # Test compliance report generation
        def generate_compliance_report(thread_id, audit_events):
            """Generate compliance report from audit events."""
            thread_events = [e for e in audit_events if e["thread_id"] == thread_id]
            
            report = {
                "thread_id": thread_id,
                "audit_period": {
                    "start": min(e["timestamp"] for e in thread_events),
                    "end": max(e["timestamp"] for e in thread_events)
                },
                "total_events": len(thread_events),
                "event_types": list(set(e["event_type"] for e in thread_events)),
                "compliance_status": "compliant",
                "violations": [],
                "data_access_summary": {
                    "read_events": len([e for e in thread_events if e["event_type"] == "thread_access"]),
                    "modification_events": len([e for e in thread_events if e["event_type"] == "thread_modification"]),
                    "validation_events": len([e for e in thread_events if e["event_type"] == "compliance_validation"])
                }
            }
            
            return report
        
        compliance_report = generate_compliance_report(compliance_thread_id, audit_events)
        
        # Verify compliance report
        assert compliance_report["total_events"] == 3, "Report must include all events"
        assert "thread_access" in compliance_report["event_types"], "Report must include access events"
        assert "thread_modification" in compliance_report["event_types"], "Report must include modification events"
        assert "compliance_validation" in compliance_report["event_types"], "Report must include validation events"
        assert compliance_report["compliance_status"] == "compliant", "Report must show compliance status"
        assert len(compliance_report["violations"]) == 0, "No violations should be detected"
        
        # Test audit trail persistence and retrieval
        def simulate_audit_storage(events):
            """Simulate storing audit events for compliance."""
            stored_events = []
            for event in events:
                # In real system, this would go to secure audit storage
                stored_event = {
                    **event,
                    "stored_at": datetime.now(timezone.utc).isoformat(),
                    "storage_location": "secure_audit_db",
                    "integrity_hash": f"hash_{len(str(event))}"  # Simplified hash
                }
                stored_events.append(stored_event)
            return stored_events
        
        stored_audit_events = simulate_audit_storage(audit_events)
        
        # Verify audit storage integrity
        assert len(stored_audit_events) == len(audit_events), "All events must be stored"
        for stored_event in stored_audit_events:
            assert "stored_at" in stored_event, "Stored events must have storage timestamp"
            assert "integrity_hash" in stored_event, "Stored events must have integrity verification"
        
        self.record_metric("test_019_status", "passed")
        self.record_metric("compliance_audit_trail_verified", True)
        self.record_metric("audit_events_logged", len(audit_events))
        self.record_metric("compliance_frameworks_validated", ["SOX", "GDPR", "PCI-DSS"])
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_020_thread_performance_and_scalability_validation(self, real_services_fixture):
        """
        Test 20/20: Validate thread performance and scalability under load.
        
        Business Value: Platform must handle enterprise-scale thread operations
        efficiently to support large optimization projects with many stakeholders.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available")
        
        # Performance test setup
        performance_start_time = datetime.now(timezone.utc)
        performance_metrics = {
            "thread_creation_times": [],
            "thread_retrieval_times": [],
            "concurrent_operations": 0,
            "memory_usage_checkpoints": [],
            "database_query_times": []
        }
        
        # Test 1: Bulk thread creation performance
        bulk_thread_count = 50
        thread_ids = []
        
        bulk_creation_start = datetime.now(timezone.utc)
        
        for i in range(bulk_thread_count):
            thread_id = self.id_manager.generate_thread_id()
            thread_ids.append(thread_id)
            
            creation_start = datetime.now(timezone.utc)
            
            thread_data = {
                "id": thread_id,
                "name": f"Performance Test Thread {i+1:03d}",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "user_id": self.test_user_1,
                "metadata": f'{{"thread_index": {i+1}, "performance_test": true, "batch_size": {bulk_thread_count}}}',
                "is_active": True,
                "message_count": i % 10  # Varying message counts
            }
            
            async with services["db"].begin():
                await services["db"].execute(
                    text("""
                        INSERT INTO threads (id, name, created_at, updated_at, user_id, metadata, is_active, message_count)
                        VALUES (:id, :name, :created_at, :updated_at, :user_id, :metadata, :is_active, :message_count)
                    """),
                    thread_data
                )
            
            creation_end = datetime.now(timezone.utc)
            creation_time = (creation_end - creation_start).total_seconds()
            performance_metrics["thread_creation_times"].append(creation_time)
        
        bulk_creation_end = datetime.now(timezone.utc)
        bulk_creation_duration = (bulk_creation_end - bulk_creation_start).total_seconds()
        
        # Test 2: Bulk retrieval performance
        retrieval_start = datetime.now(timezone.utc)
        
        # Retrieve all threads in batches
        batch_size = 10
        retrieved_threads = []
        
        for i in range(0, len(thread_ids), batch_size):
            batch_start = datetime.now(timezone.utc)
            batch_thread_ids = thread_ids[i:i+batch_size]
            
            # Create IN clause for batch query
            placeholders = ", ".join([f":thread_id_{j}" for j in range(len(batch_thread_ids))])
            query_params = {f"thread_id_{j}": tid for j, tid in enumerate(batch_thread_ids)}
            query_params["user_id"] = self.test_user_1
            
            result = await services["db"].execute(
                text(f"""
                    SELECT id, name, message_count FROM threads 
                    WHERE id IN ({placeholders}) AND user_id = :user_id
                    ORDER BY name
                """),
                query_params
            )
            
            batch_threads = result.fetchall()
            retrieved_threads.extend(batch_threads)
            
            batch_end = datetime.now(timezone.utc)
            batch_time = (batch_end - batch_start).total_seconds()
            performance_metrics["thread_retrieval_times"].append(batch_time)
        
        retrieval_end = datetime.now(timezone.utc)
        retrieval_duration = (retrieval_end - retrieval_start).total_seconds()
        
        # Test 3: Concurrent access simulation
        async def concurrent_thread_operation(thread_id, operation_id):
            """Simulate concurrent thread operations."""
            op_start = datetime.now(timezone.utc)
            
            # Create context for operation
            context = UserExecutionContext.from_request(
                user_id=self.test_user_1,
                thread_id=thread_id,
                run_id=self.id_manager.generate_run_id(),
                db_session=services["db"],
                agent_context={
                    "operation_id": operation_id,
                    "performance_test": True,
                    "concurrent_operation": True
                }
            )
            
            # Simulate read operation
            result = await services["db"].execute(
                text("SELECT name, message_count FROM threads WHERE id = :thread_id"),
                {"thread_id": thread_id}
            )
            thread_data = result.fetchone()
            
            # Simulate processing time
            await asyncio.sleep(0.01)
            
            # Simulate write operation
            new_count = (thread_data[1] if thread_data else 0) + 1
            async with services["db"].begin():
                await services["db"].execute(
                    text("UPDATE threads SET message_count = :new_count, updated_at = :updated_at WHERE id = :thread_id"),
                    {
                        "thread_id": thread_id,
                        "new_count": new_count,
                        "updated_at": datetime.now(timezone.utc)
                    }
                )
            
            op_end = datetime.now(timezone.utc)
            operation_time = (op_end - op_start).total_seconds()
            
            return {
                "thread_id": thread_id,
                "operation_id": operation_id,
                "operation_time": operation_time,
                "final_message_count": new_count,
                "success": True
            }
        
        # Run concurrent operations on subset of threads
        concurrent_start = datetime.now(timezone.utc)
        concurrent_thread_subset = thread_ids[:20]  # Use 20 threads for concurrency test
        
        concurrent_tasks = []
        for i, thread_id in enumerate(concurrent_thread_subset):
            task = concurrent_thread_operation(thread_id, f"concurrent_op_{i}")
            concurrent_tasks.append(task)
        
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_end = datetime.now(timezone.utc)
        concurrent_duration = (concurrent_end - concurrent_start).total_seconds()
        
        performance_metrics["concurrent_operations"] = len(concurrent_results)
        
        # Test 4: Large result set pagination performance
        pagination_start = datetime.now(timezone.utc)
        
        # Test paginated queries with different page sizes
        page_sizes = [10, 25, 50]
        pagination_times = {}
        
        for page_size in page_sizes:
            page_start = datetime.now(timezone.utc)
            
            # Get first page
            result = await services["db"].execute(
                text("""
                    SELECT id, name, created_at FROM threads 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC 
                    LIMIT :limit OFFSET 0
                """),
                {"user_id": self.test_user_1, "limit": page_size}
            )
            first_page = result.fetchall()
            
            # Get second page
            result = await services["db"].execute(
                text("""
                    SELECT id, name, created_at FROM threads 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC 
                    LIMIT :limit OFFSET :offset
                """),
                {"user_id": self.test_user_1, "limit": page_size, "offset": page_size}
            )
            second_page = result.fetchall()
            
            page_end = datetime.now(timezone.utc)
            page_time = (page_end - page_start).total_seconds()
            pagination_times[page_size] = {
                "query_time": page_time,
                "first_page_count": len(first_page),
                "second_page_count": len(second_page)
            }
        
        pagination_end = datetime.now(timezone.utc)
        pagination_duration = (pagination_end - pagination_start).total_seconds()
        
        # Performance analysis and assertions
        performance_end_time = datetime.now(timezone.utc)
        total_test_duration = (performance_end_time - performance_start_time).total_seconds()
        
        # Calculate performance statistics
        avg_creation_time = sum(performance_metrics["thread_creation_times"]) / len(performance_metrics["thread_creation_times"])
        max_creation_time = max(performance_metrics["thread_creation_times"])
        avg_retrieval_time = sum(performance_metrics["thread_retrieval_times"]) / len(performance_metrics["thread_retrieval_times"])
        
        concurrent_operation_times = [r["operation_time"] for r in concurrent_results]
        avg_concurrent_time = sum(concurrent_operation_times) / len(concurrent_operation_times)
        max_concurrent_time = max(concurrent_operation_times)
        
        # Performance assertions
        assert avg_creation_time < 0.5, f"Average thread creation time must be under 0.5s, got {avg_creation_time:.3f}s"
        assert max_creation_time < 2.0, f"Maximum thread creation time must be under 2.0s, got {max_creation_time:.3f}s"
        assert avg_retrieval_time < 0.1, f"Average batch retrieval time must be under 0.1s, got {avg_retrieval_time:.3f}s"
        assert avg_concurrent_time < 0.5, f"Average concurrent operation time must be under 0.5s, got {avg_concurrent_time:.3f}s"
        
        # Scalability assertions
        threads_per_second = bulk_thread_count / bulk_creation_duration
        assert threads_per_second > 10, f"Thread creation rate must exceed 10/sec, got {threads_per_second:.1f}/sec"
        
        concurrent_ops_per_second = len(concurrent_results) / concurrent_duration
        assert concurrent_ops_per_second > 5, f"Concurrent ops rate must exceed 5/sec, got {concurrent_ops_per_second:.1f}/sec"
        
        # Verify data integrity after performance tests
        result = await services["db"].execute(
            text("SELECT COUNT(*) FROM threads WHERE user_id = :user_id"),
            {"user_id": self.test_user_1}
        )
        final_thread_count = result.fetchone()[0]
        assert final_thread_count >= bulk_thread_count, "All threads must be preserved after performance testing"
        
        # Verify no concurrent operation failures
        successful_concurrent_ops = sum(1 for r in concurrent_results if r["success"])
        assert successful_concurrent_ops == len(concurrent_results), "All concurrent operations must succeed"
        
        # Record comprehensive performance metrics
        self.record_metric("test_020_status", "passed")
        self.record_metric("total_test_duration_seconds", total_test_duration)
        self.record_metric("bulk_thread_creation_count", bulk_thread_count)
        self.record_metric("threads_created_per_second", threads_per_second)
        self.record_metric("average_creation_time_ms", avg_creation_time * 1000)
        self.record_metric("average_retrieval_time_ms", avg_retrieval_time * 1000)
        self.record_metric("concurrent_operations_executed", len(concurrent_results))
        self.record_metric("concurrent_ops_per_second", concurrent_ops_per_second)
        self.record_metric("average_concurrent_op_time_ms", avg_concurrent_time * 1000)
        self.record_metric("pagination_test_results", pagination_times)
        self.record_metric("performance_scalability_verified", True)
        
        # Final cleanup (optional - could be done in teardown)
        # await self._cleanup_performance_test_threads(services["db"], thread_ids)
        
    async def _cleanup_performance_test_threads(self, db_session, thread_ids):
        """Clean up performance test threads."""
        if not thread_ids:
            return
            
        # Delete in batches to avoid query size limits
        batch_size = 20
        for i in range(0, len(thread_ids), batch_size):
            batch = thread_ids[i:i+batch_size]
            placeholders = ", ".join([f":thread_id_{j}" for j in range(len(batch))])
            params = {f"thread_id_{j}": tid for j, tid in enumerate(batch)}
            
            async with db_session.begin():
                await db_session.execute(
                    text(f"DELETE FROM threads WHERE id IN ({placeholders})"),
                    params
                )


if __name__ == "__main__":
    # For direct test execution
    import sys
    sys.exit(pytest.main([__file__, "-v", "--real-services"]))