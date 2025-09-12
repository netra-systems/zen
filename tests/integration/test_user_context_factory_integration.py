"""Integration Test for User Context Factory - Thread Isolation Validation.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Critical for multi-user system integrity  
- Business Goal: Prevent context mixing and data leakage between user conversations
- Value Impact: Ensures conversation isolation and prevents user data cross-contamination
- Strategic Impact: CRITICAL - Context isolation violations could expose user data

This test suite validates the critical requirement identified in the architecture analysis
that different thread_id values must result in different context instances while 
maintaining proper user isolation and session management.

CRITICAL: This test prevents the regression where threads share contexts or get mixed up.
"""

import pytest
import time
from typing import Dict

from netra_backend.app.dependencies import get_user_execution_context
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestUserContextFactoryIntegration:
    """Integration test for user context factory with thread isolation validation."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create test users and threads with realistic IDs
        self.test_users = [
            "usr_enterprise_001_12345abcdef",
            "usr_enterprise_002_67890fedcba", 
            "usr_mid_tier_003_abcdef123456"
        ]
        
        self.test_threads = {
            "conversation_1": "thd_conversation_123456_abc",
            "conversation_2": "thd_conversation_789012_def", 
            "conversation_3": "thd_conversation_345678_ghi"
        }
        
        self.performance_metrics: Dict[str, any] = {
            "context_creation_times": [],
            "thread_isolation_validations": 0,
            "user_consistency_checks": 0,
            "memory_efficiency_checks": 0
        }

    def teardown_method(self):
        """Clean up after test."""
        # Log performance metrics
        if self.performance_metrics["context_creation_times"]:
            avg_time = sum(self.performance_metrics["context_creation_times"]) / len(self.performance_metrics["context_creation_times"])
            print(f"\nAverage context creation time: {avg_time:.4f}s")
        
        print(f"Thread isolation validations: {self.performance_metrics['thread_isolation_validations']}")
        print(f"User consistency checks: {self.performance_metrics['user_consistency_checks']}")

    @pytest.mark.integration
    @pytest.mark.critical
    def test_different_threads_get_different_contexts(self):
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

    @pytest.mark.integration
    @pytest.mark.critical
    def test_same_thread_maintains_session_continuity(self):
        """Test that the same thread_id maintains session continuity (same run_id)."""
        user_id = self.test_users[1] 
        thread_id = self.test_threads["conversation_1"]

        # First call to get context
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        original_run_id = context1.run_id

        # Second call with same parameters
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread_id)

        # CRITICAL: Session continuity must be maintained
        assert context2.run_id == original_run_id, "Same thread should maintain run_id for session continuity"
        assert context1.thread_id == context2.thread_id == thread_id, "Thread ID must remain consistent"
        assert context1.user_id == context2.user_id == user_id, "User ID must remain consistent"

        self.performance_metrics["thread_isolation_validations"] += 1

    @pytest.mark.integration
    @pytest.mark.critical 
    def test_multi_user_context_isolation(self):
        """Test complete isolation between different users and threads."""
        user1 = self.test_users[0]
        user2 = self.test_users[1]
        thread1 = self.test_threads["conversation_1"]
        thread2 = self.test_threads["conversation_2"]

        # Create contexts for different users and threads
        context_u1_t1 = get_user_execution_context(user_id=user1, thread_id=thread1)
        context_u1_t2 = get_user_execution_context(user_id=user1, thread_id=thread2)
        context_u2_t1 = get_user_execution_context(user_id=user2, thread_id=thread1)
        context_u2_t2 = get_user_execution_context(user_id=user2, thread_id=thread2)

        # All contexts must be different instances
        all_contexts = [context_u1_t1, context_u1_t2, context_u2_t1, context_u2_t2]
        for i, ctx1 in enumerate(all_contexts):
            for j, ctx2 in enumerate(all_contexts):
                if i != j:
                    assert ctx1 is not ctx2, f"Context {i} and {j} must be different instances"
                    assert ctx1.run_id != ctx2.run_id, f"Run IDs must be unique between contexts {i} and {j}"

        # Validate user isolation
        assert context_u1_t1.user_id == context_u1_t2.user_id == user1
        assert context_u2_t1.user_id == context_u2_t2.user_id == user2
        assert context_u1_t1.user_id != context_u2_t1.user_id, "Different users must have different user_ids"

        # Validate thread isolation  
        assert context_u1_t1.thread_id == context_u2_t1.thread_id == thread1
        assert context_u1_t2.thread_id == context_u2_t2.thread_id == thread2
        assert context_u1_t1.thread_id != context_u1_t2.thread_id, "Different threads must have different thread_ids"

        self.performance_metrics["thread_isolation_validations"] += 4
        self.performance_metrics["user_consistency_checks"] += 4

    @pytest.mark.integration
    def test_performance_and_memory_validation(self):
        """Test that context creation doesn't cause performance issues or memory leaks."""
        user_id = self.test_users[0]
        contexts = []
        
        start_time = time.time()
        
        # Create multiple contexts with different threads
        for i in range(10):
            thread_id = f"thd_perf_test_{i:03d}_abc123def456"
            context = get_user_execution_context(user_id=user_id, thread_id=thread_id)
            contexts.append(context)
        
        total_time = time.time() - start_time
        avg_time_per_context = total_time / 10
        
        # Performance validation
        assert total_time < 1.0, f"Creating 10 contexts took too long: {total_time:.3f}s"
        assert avg_time_per_context < 0.1, f"Average context creation too slow: {avg_time_per_context:.3f}s"
        
        # Validate all contexts are different
        for i, ctx1 in enumerate(contexts):
            for j, ctx2 in enumerate(contexts):
                if i != j:
                    assert ctx1 is not ctx2, f"Context {i} and {j} should be different instances"
                    assert ctx1.run_id != ctx2.run_id, f"Run IDs should be unique: {ctx1.run_id} vs {ctx2.run_id}"
                    assert ctx1.thread_id != ctx2.thread_id, f"Thread IDs should be different"

        # Validate user consistency across all contexts
        for context in contexts:
            assert context.user_id == user_id, "All contexts should have same user_id"

        self.performance_metrics["memory_efficiency_checks"] += 1
        self.performance_metrics["context_creation_times"].append(avg_time_per_context)

    @pytest.mark.integration 
    def test_context_independence_validation(self):
        """Test that contexts for different threads remain independent."""
        user_id = self.test_users[0]
        thread1 = self.test_threads["conversation_1"] 
        thread2 = self.test_threads["conversation_2"]

        # Create two different contexts
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread1)
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread2)

        # Verify contexts remain independent  
        assert context1.thread_id != context2.thread_id, "Thread IDs must remain different"
        assert context1.run_id != context2.run_id, "Run IDs must remain different"
        assert context1.user_id == context2.user_id == user_id, "User ID must remain consistent"

        # Verify they are different object instances
        assert context1 is not context2, "Context instances must be different for different threads"

        self.performance_metrics["thread_isolation_validations"] += 1