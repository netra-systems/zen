"""
Test User Context Factory Integration - Regression Prevention for Thread Isolation

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Critical for multi-user system integrity
- Business Goal: Prevent context mixing and data leakage between user conversations 
- Value Impact: Ensures conversation isolation and prevents user data cross-contamination
- Strategic Impact: CRITICAL - Context isolation violations could expose user data

CRITICAL REQUIREMENT: 
This test validates the architectural fix identified in CONTEXT_CREATION_ARCHITECTURE_ANALYSIS.md
where different thread_id values MUST get different context instances while maintaining
user consistency and session continuity.

Key Scenarios Tested:
1. Thread Isolation: Different thread_ids must get different contexts
2. User Consistency: Same user_id maintained across different threads  
3. Context Independence: Changes to one thread don't affect another
4. Multi-User Scenarios: Different users with different threads are isolated
5. Performance: Creating new contexts doesn't impact existing ones
6. Session Continuity: Same thread_id reuses contexts across messages

This follows TEST_CREATION_GUIDE.md patterns using real services and integration testing.
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any, Optional
from unittest.mock import patch

# SSOT imports - absolute imports only per CLAUDE.md requirements
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.database_fixtures import test_db_session
from netra_backend.app.dependencies import get_user_execution_context
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextFactory,
    InvalidContextError
)
from shared.id_generation.unified_id_generator import UnifiedIdGenerator, reset_global_counter
from netra_backend.app.database import get_db


class TestUserContextFactoryIntegration(SSotBaseTestCase):
    """Integration test for user context factory with thread isolation validation.
    
    This test suite validates the critical requirement that different thread_ids
    result in different context instances while maintaining proper user isolation
    and session continuity patterns.
    
    Uses real database connections and services to validate actual system behavior.
    """
    
    def setup_method(self):
        """Set up test environment with clean state."""
        super().setup_method()
        
        # Reset ID generator for consistent test results
        reset_global_counter()
        
        # Initialize performance metrics tracking
        self.performance_metrics = {
            "context_creation_times": [],
            "memory_usage_samples": [],
            "thread_isolation_validations": 0,
            "user_consistency_checks": 0
        }
        
        # Test data for realistic scenarios
        self.test_users = [
            "usr_test_user_001_enterprise",
            "usr_test_user_002_pro", 
            "usr_test_user_003_free"
        ]
        
        self.test_threads = {
            "conversation_1": "thd_cost_optimization_001",
            "conversation_2": "thd_data_analysis_002", 
            "conversation_3": "thd_security_audit_003",
            "conversation_4": "thd_performance_review_004"
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.critical
    async def test_different_threads_get_different_contexts(self, real_services_fixture):
        """CRITICAL: Validate that different thread_ids create different context instances.
        
        This is the core regression prevention test identified in the architecture analysis.
        Different threads for the same user MUST get separate context instances.
        """
        user_id = self.test_users[0]  # Use enterprise user for test
        thread1 = self.test_threads["conversation_1"]
        thread2 = self.test_threads["conversation_2"]
        
        start_time = time.time()
        
        # Create contexts for two different threads
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread1)
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread2)
        
        creation_time = time.time() - start_time
        self.performance_metrics["context_creation_times"].append(creation_time)
        
        # CRITICAL: Different contexts for different threads
        assert context1 is not context2, "Different threads must create different context instances"
        assert context1.thread_id != context2.thread_id, "Thread IDs must be different"
        assert context1.run_id != context2.run_id, "Run IDs must be different for different threads"
        assert context1.request_id != context2.request_id, "Request IDs must always be unique"
        
        # User consistency validation
        assert context1.user_id == context2.user_id == user_id, "User ID must be consistent across threads"
        
        # Context independence validation
        assert context1.agent_context != context2.agent_context or not context1.agent_context, "Agent contexts must be independent"
        
        # Performance validation
        assert creation_time < 0.1, f"Context creation took too long: {creation_time:.3f}s"
        
        self.performance_metrics["thread_isolation_validations"] += 1
        self.performance_metrics["user_consistency_checks"] += 1
        
        self.record_metric("thread_isolation_test_duration", creation_time)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_same_thread_maintains_session_continuity(self, real_services_fixture):
        """Validate that same thread_id reuses context instances for session continuity.
        
        This tests the correct behavior where conversation continuity is maintained
        within the same thread across multiple messages.
        """
        user_id = self.test_users[1]  # Use pro user for test
        thread_id = self.test_threads["conversation_1"]
        
        # First message in thread
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        original_run_id = context1.run_id
        
        # Simulate time passing between messages
        await asyncio.sleep(0.01)  # 10ms delay
        
        # Second message in same thread
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Session continuity validation - context should be reused based on session management
        assert context1.thread_id == context2.thread_id, "Thread ID must be consistent for same thread"
        assert context1.user_id == context2.user_id, "User ID must be consistent"
        
        # Session behavior validation (based on UnifiedIdGenerator session management)
        # Same thread should maintain the same run_id for conversation continuity
        assert context2.run_id == original_run_id, "Run ID should be maintained for session continuity"
        
        # Request IDs should always be unique for proper request tracking
        assert context1.request_id != context2.request_id, "Request IDs must always be unique"
        
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_multi_user_context_isolation(self, real_services_fixture):
        """Validate complete isolation between different users' contexts.
        
        This ensures that different users with different threads are completely
        isolated from each other without any shared state or references.
        """
        contexts = {}
        
        # Create contexts for multiple users using different thread names
        for i, user_id in enumerate(self.test_users):
            thread_name = list(self.test_threads.values())[i]  # Different thread for each user
            contexts[user_id] = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_name
            )
        
        # Validate complete isolation between users
        user_ids = list(contexts.keys())
        for i, user1 in enumerate(user_ids):
            for user2 in user_ids[i+1:]:
                ctx1 = contexts[user1] 
                ctx2 = contexts[user2]
                
                # CRITICAL: All identifiers must be different between users
                assert ctx1.user_id != ctx2.user_id, "User IDs must be different"
                assert ctx1.thread_id != ctx2.thread_id, "Thread IDs must be different between users"
                assert ctx1.run_id != ctx2.run_id, "Run IDs must be different between users"
                assert ctx1.request_id != ctx2.request_id, "Request IDs must be different between users"
                assert ctx1 is not ctx2, "Context instances must be completely separate"
                
                # WebSocket isolation 
                if ctx1.websocket_client_id and ctx2.websocket_client_id:
                    assert ctx1.websocket_client_id != ctx2.websocket_client_id, "WebSocket client IDs must be different"
        
        self.performance_metrics["user_consistency_checks"] += len(self.test_users)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_level_isolation_with_same_thread_names(self, real_services_fixture):
        """Validate that session-level isolation works even with same thread names.
        
        This tests the critical behavior where different users can use the same
        logical thread name but still maintain complete isolation at the session level.
        """
        thread_name = "shared_thread_name"  # Same logical thread name for all users
        contexts = {}
        
        # Create contexts for multiple users using the SAME thread name
        for user_id in self.test_users:
            contexts[user_id] = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_name
            )
        
        # Validate session-level isolation
        user_ids = list(contexts.keys())
        for i, user1 in enumerate(user_ids):
            for user2 in user_ids[i+1:]:
                ctx1 = contexts[user1]
                ctx2 = contexts[user2]
                
                # Users must be different
                assert ctx1.user_id != ctx2.user_id, "User IDs must be different"
                
                # Sessions must be isolated even with same thread name
                # The session key includes both user_id and thread_id for isolation
                assert ctx1.run_id != ctx2.run_id, "Run IDs must be different (session isolation)"
                assert ctx1.request_id != ctx2.request_id, "Request IDs must always be unique"
                assert ctx1 is not ctx2, "Context instances must be completely separate"
                
                # Thread IDs might be the same (user specified), but sessions are isolated
                if ctx1.thread_id == ctx2.thread_id:
                    # Same thread name is OK - isolation is at session level (user_id:thread_id)
                    assert ctx1.thread_id == thread_name, "Thread ID should match requested name"
                    assert ctx2.thread_id == thread_name, "Thread ID should match requested name"
                    # But sessions must still be isolated
                    assert ctx1.run_id != ctx2.run_id, "Session isolation must be maintained"
        
        # Validate that modifying one user's context doesn't affect another's
        first_user = self.test_users[0]
        second_user = self.test_users[1]
        
        ctx1 = contexts[first_user]
        ctx2 = contexts[second_user]
        
        # Create child contexts
        child_ctx1 = ctx1.create_child_context("user1_operation")
        child_ctx2 = ctx2.create_child_context("user2_operation")
        
        # Validate child context isolation
        assert child_ctx1.user_id != child_ctx2.user_id, "Child contexts must maintain user isolation"
        assert child_ctx1.agent_context != child_ctx2.agent_context, "Child agent contexts must be separate"
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_context_independence_validation(self, real_services_fixture):
        """Validate that changes to one thread context don't affect another.
        
        This tests that context modifications are properly isolated and don't
        cause shared state issues between different threads.
        """
        user_id = self.test_users[0]
        thread1 = self.test_threads["conversation_1"]
        thread2 = self.test_threads["conversation_2"]
        
        # Create two contexts for different threads
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread1)
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread2)
        
        # Create child contexts to simulate agent operations
        child_context1 = context1.create_child_context(
            operation_name="cost_analysis",
            additional_agent_context={"analysis_type": "cost_optimization"}
        )
        child_context2 = context2.create_child_context(
            operation_name="data_processing", 
            additional_agent_context={"analysis_type": "data_quality"}
        )
        
        # Validate child context isolation
        assert child_context1.parent_request_id != child_context2.parent_request_id, "Parent request IDs must be different"
        assert child_context1.agent_context != child_context2.agent_context, "Agent contexts must be independent"
        assert child_context1.thread_id != child_context2.thread_id, "Child contexts must maintain thread isolation"
        
        # Validate parent contexts remain unchanged
        assert context1.thread_id == child_context1.thread_id, "Child must inherit parent thread ID"
        assert context2.thread_id == child_context2.thread_id, "Child must inherit parent thread ID"  
        assert context1.thread_id != context2.thread_id, "Original contexts must remain isolated"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_and_memory_validation(self, real_services_fixture):
        """Validate context creation performance and memory usage patterns.
        
        This ensures that creating new contexts for different threads doesn't
        cause performance degradation or memory leaks.
        """
        user_id = self.test_users[0]
        context_count = 10  # Create multiple contexts for testing
        contexts = []
        
        # Measure context creation performance
        start_time = time.time()
        
        for i in range(context_count):
            thread_id = f"{self.test_threads['conversation_1']}_perf_test_{i}"
            context = get_user_execution_context(user_id=user_id, thread_id=thread_id)
            contexts.append(context)
        
        creation_time = time.time() - start_time
        avg_creation_time = creation_time / context_count
        
        # Performance validations
        assert avg_creation_time < 0.01, f"Average context creation too slow: {avg_creation_time:.3f}s"
        assert creation_time < 0.1, f"Total context creation too slow: {creation_time:.3f}s"
        
        # Validate all contexts are unique
        thread_ids = set()
        run_ids = set()
        request_ids = set()
        
        for context in contexts:
            assert context.thread_id not in thread_ids, "Thread ID collision detected"
            assert context.run_id not in run_ids, "Run ID collision detected"
            assert context.request_id not in request_ids, "Request ID collision detected"
            
            thread_ids.add(context.thread_id)
            run_ids.add(context.run_id)
            request_ids.add(context.request_id)
            
            # Validate context is properly initialized
            assert context.user_id == user_id, "User ID consistency failure"
            assert context.created_at is not None, "Creation timestamp missing"
            assert isinstance(context.agent_context, dict), "Agent context must be dictionary"
            assert isinstance(context.audit_metadata, dict), "Audit metadata must be dictionary"
        
        # Memory validation - ensure contexts don't share references
        for i, context1 in enumerate(contexts):
            for j, context2 in enumerate(contexts[i+1:], i+1):
                assert context1 is not context2, f"Context instances {i} and {j} share references"
                assert context1.agent_context is not context2.agent_context, f"Agent contexts {i} and {j} share references"
                assert context1.audit_metadata is not context2.audit_metadata, f"Audit metadata {i} and {j} share references"
        
        self.performance_metrics["context_creation_times"].append(creation_time)
        self.record_metric("performance_test_contexts", context_count)
        self.record_metric("average_creation_time", avg_creation_time)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_context_routing_isolation(self, real_services_fixture):
        """Validate WebSocket context routing maintains thread isolation.
        
        This tests that WebSocket connections are properly routed to the correct
        thread contexts without cross-contamination.
        """
        user_id = self.test_users[0]
        thread1 = self.test_threads["conversation_1"]
        thread2 = self.test_threads["conversation_2"]
        
        # Create contexts with WebSocket client IDs
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread1)
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread2)
        
        # Validate WebSocket routing isolation
        assert context1.websocket_client_id != context2.websocket_client_id, "WebSocket client IDs must be unique"
        
        # Test WebSocket connection context creation
        websocket_context1 = context1.with_websocket_connection(context1.websocket_client_id)
        websocket_context2 = context2.with_websocket_connection(context2.websocket_client_id)
        
        # Validate isolation is maintained in WebSocket contexts
        assert websocket_context1.thread_id != websocket_context2.thread_id, "WebSocket contexts must maintain thread isolation"
        assert websocket_context1.user_id == websocket_context2.user_id == user_id, "User ID must be consistent"
        assert websocket_context1 is not websocket_context2, "WebSocket contexts must be separate instances"
        
        # Validate WebSocket client IDs are properly assigned
        assert websocket_context1.websocket_client_id == context1.websocket_client_id, "WebSocket client ID must match"
        assert websocket_context2.websocket_client_id == context2.websocket_client_id, "WebSocket client ID must match"
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_database_session_isolation(self, real_services_fixture):
        """Validate database session isolation between different thread contexts.
        
        This ensures that database sessions are properly isolated between different
        thread contexts to prevent data leakage.
        """
        user_id = self.test_users[0]
        thread1 = self.test_threads["conversation_1"]
        thread2 = self.test_threads["conversation_2"]
        
        # Get database session generator 
        from netra_backend.app.dependencies import get_request_scoped_db_session
        
        # Create contexts and attach database sessions
        async for db_session1 in get_request_scoped_db_session():
            context1 = get_user_execution_context(user_id=user_id, thread_id=thread1)
            context1_with_db = context1.with_db_session(db_session1)
            
            async for db_session2 in get_request_scoped_db_session():
                context2 = get_user_execution_context(user_id=user_id, thread_id=thread2)
                context2_with_db = context2.with_db_session(db_session2)
                
                # Validate database session isolation
                assert context1_with_db.db_session is not context2_with_db.db_session, "Database sessions must be separate"
                assert id(context1_with_db.db_session) != id(context2_with_db.db_session), "Database session IDs must be different"
                
                # Validate contexts maintain their identity with database sessions
                assert context1_with_db.thread_id != context2_with_db.thread_id, "Thread isolation must be maintained with DB sessions"
                assert context1_with_db.user_id == context2_with_db.user_id == user_id, "User ID must be consistent with DB sessions"
                
                break  # Exit inner session
            break  # Exit outer session
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_context_validation_and_error_handling(self, real_services_fixture):
        """Test context validation and proper error handling for invalid scenarios.
        
        This validates that the context factory properly handles edge cases and
        invalid inputs without compromising system integrity.
        """
        # Test invalid user ID handling
        with pytest.raises(InvalidContextError):
            UserContextFactory.create_context(
                user_id="",  # Empty user ID should fail
                thread_id=self.test_threads["conversation_1"],
                run_id="test_run_001"
            )
        
        # Test invalid thread ID patterns
        with pytest.raises(InvalidContextError):
            UserContextFactory.create_context(
                user_id=self.test_users[0],
                thread_id="placeholder",  # Placeholder values should fail
                run_id="test_run_001"
            )
        
        # Test context validation
        valid_context = get_user_execution_context(
            user_id=self.test_users[0],
            thread_id=self.test_threads["conversation_1"]
        )
        
        # Validation should pass for valid context
        assert valid_context.verify_isolation() is True, "Valid context should pass isolation verification"
        
        # Test child context depth limits
        current_context = valid_context
        for i in range(9):  # Create nested contexts up to limit
            current_context = current_context.create_child_context(f"operation_{i}")
        
        # Should fail at maximum depth
        with pytest.raises(InvalidContextError):
            current_context.create_child_context("operation_too_deep")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_context_creation_safety(self, real_services_fixture):
        """Test thread safety of concurrent context creation.
        
        This validates that multiple concurrent context creation requests
        don't cause race conditions or ID collisions.
        """
        user_id = self.test_users[0]
        concurrent_requests = 20
        
        async def create_context_for_thread(thread_suffix: int) -> UserExecutionContext:
            """Create context for testing concurrency."""
            thread_id = f"{self.test_threads['conversation_1']}_concurrent_{thread_suffix}"
            return get_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Create multiple contexts concurrently
        start_time = time.time()
        tasks = [create_context_for_thread(i) for i in range(concurrent_requests)]
        contexts = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time
        
        # Validate all contexts are unique
        thread_ids = set()
        run_ids = set()
        request_ids = set()
        
        for context in contexts:
            assert context.thread_id not in thread_ids, "Concurrent thread ID collision"
            assert context.run_id not in run_ids, "Concurrent run ID collision"
            assert context.request_id not in request_ids, "Concurrent request ID collision"
            
            thread_ids.add(context.thread_id)
            run_ids.add(context.run_id)
            request_ids.add(context.request_id)
            
            assert context.user_id == user_id, "User ID consistency in concurrent creation"
        
        # Performance validation for concurrent creation
        avg_concurrent_time = concurrent_time / concurrent_requests
        assert avg_concurrent_time < 0.05, f"Concurrent context creation too slow: {avg_concurrent_time:.3f}s"
        
        self.record_metric("concurrent_contexts_created", concurrent_requests)
        self.record_metric("concurrent_creation_time", concurrent_time)
    
    def teardown_method(self):
        """Clean up test environment and log performance metrics."""
        super().teardown_method()
        
        # Log performance metrics for analysis
        if self.performance_metrics["context_creation_times"]:
            avg_time = sum(self.performance_metrics["context_creation_times"]) / len(self.performance_metrics["context_creation_times"])
            max_time = max(self.performance_metrics["context_creation_times"]) 
            min_time = min(self.performance_metrics["context_creation_times"])
            
            print(f"\n=== Performance Metrics ===")
            print(f"Context Creation - Average: {avg_time:.4f}s, Max: {max_time:.4f}s, Min: {min_time:.4f}s")
            print(f"Thread Isolation Validations: {self.performance_metrics['thread_isolation_validations']}")
            print(f"User Consistency Checks: {self.performance_metrics['user_consistency_checks']}")
            print(f"==========================")
        
        # Clear any session state for next test
        UnifiedIdGenerator.cleanup_expired_sessions()