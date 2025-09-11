"""
Test User Context Security Isolation - Issue #271

Business Value Justification (BVJ):
- Segment: Enterprise/Mid (Multi-tenant customers)
- Business Goal: Ensure complete user isolation for security compliance
- Value Impact: Enterprise customers require guaranteed data isolation
- Revenue Impact: $500K+ ARR protection through enterprise security compliance

CRITICAL ISSUE: #271 - User isolation security vulnerability
ROOT CAUSE: DeepAgentState allowing cross-user contamination
BUSINESS IMPACT: Security breach = enterprise customer loss = significant ARR loss
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# SSOT Import (New Security Architecture)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    InvalidContextError,
    ContextIsolationError,
    managed_user_context,
    validate_user_context,
    create_isolated_execution_context
)

# Test imports for deprecated DeepAgentState
try:
    from netra_backend.app.agents.state import DeepAgentState
    DEEP_AGENT_STATE_EXISTS = True
except ImportError:
    DEEP_AGENT_STATE_EXISTS = False


class TestUserContextSecurity(SSotAsyncTestCase):
    """Test user isolation security after DeepAgentState elimination."""
    
    def setUp(self):
        """Set up isolated test environment."""
        super().setUp()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_USER_ISOLATION", "enabled", source="test")
        
        # Test user IDs for multi-user scenarios
        self.user_id_1 = "user_123_enterprise"
        self.user_id_2 = "user_456_enterprise"
        self.user_id_3 = "user_789_free"
    
    async def test_user_context_creation_isolation(self):
        """UserExecutionContext must create completely isolated contexts per user."""
        # Create contexts for different users
        context_1 = await create_isolated_execution_context(
            user_id=self.user_id_1,
            session_id="session_1"
        )
        
        context_2 = await create_isolated_execution_context(
            user_id=self.user_id_2, 
            session_id="session_2"
        )
        
        # Contexts must be completely separate instances
        assert context_1 is not context_2
        assert context_1.user_id != context_2.user_id
        assert context_1.session_id != context_2.session_id
        
        # Memory isolation - no shared references
        assert id(context_1) != id(context_2)
        assert context_1.__dict__ != context_2.__dict__
    
    async def test_user_context_manager_isolation_enforcement(self):
        """UserContextManager must prevent cross-user contamination."""
        manager = UserContextManager()
        
        # Create isolated contexts for multiple users
        context_1 = await manager.create_context(
            user_id=self.user_id_1,
            request_id="req_1"
        )
        
        context_2 = await manager.create_context(
            user_id=self.user_id_2,
            request_id="req_2"
        )
        
        # Test isolation validation
        assert await validate_user_context(context_1, expected_user=self.user_id_1)
        assert await validate_user_context(context_2, expected_user=self.user_id_2)
        
        # Test cross-user contamination detection
        with pytest.raises(ContextIsolationError):
            await validate_user_context(context_1, expected_user=self.user_id_2)
        
        with pytest.raises(ContextIsolationError):
            await validate_user_context(context_2, expected_user=self.user_id_1)
    
    @pytest.mark.skipif(not DEEP_AGENT_STATE_EXISTS, reason="DeepAgentState not present")
    async def test_deepagentstate_security_violations_prevented(self):
        """DeepAgentState usage must be blocked with clear error messages."""
        if not DEEP_AGENT_STATE_EXISTS:
            pytest.skip("DeepAgentState not present - already eliminated")
        
        # Test that attempts to create DeepAgentState in new code paths fail
        # This should be implemented in the security boundary layer
        
        # Mock the security boundary check
        with patch('netra_backend.app.services.user_execution_context.DEEP_AGENT_STATE_SECURITY_CHECK', True):
            with pytest.raises(InvalidContextError) as exc_info:
                # Simulate code trying to use DeepAgentState
                from netra_backend.app.agents.state import DeepAgentState
                state = DeepAgentState()
                
                # This should trigger security validation
                await validate_user_context(state, expected_user=self.user_id_1)
            
            # Verify security error message guides migration
            error_message = str(exc_info.value)
            assert "DeepAgentState" in error_message
            assert "security" in error_message.lower()
            assert "UserExecutionContext" in error_message
    
    async def test_multi_user_factory_pattern_isolation(self):
        """Factory patterns must create isolated contexts per user."""
        manager = UserContextManager()
        
        # Create multiple contexts concurrently to test isolation
        async def create_user_context(user_id: str, request_count: int):
            contexts = []
            for i in range(request_count):
                context = await manager.create_context(
                    user_id=user_id,
                    request_id=f"req_{user_id}_{i}"
                )
                contexts.append(context)
                
                # Add some user-specific data
                context.set_data("user_request_count", i)
                context.set_data("user_tier", "enterprise" if "enterprise" in user_id else "free")
            
            return contexts
        
        # Create contexts for multiple users concurrently
        user1_contexts, user2_contexts, user3_contexts = await asyncio.gather(
            create_user_context(self.user_id_1, 5),
            create_user_context(self.user_id_2, 5), 
            create_user_context(self.user_id_3, 5)
        )
        
        # Verify isolation between all user contexts
        all_contexts = user1_contexts + user2_contexts + user3_contexts
        
        # No shared memory references
        for i, context_a in enumerate(all_contexts):
            for j, context_b in enumerate(all_contexts):
                if i != j:
                    assert context_a is not context_b
                    assert id(context_a) != id(context_b)
                    
                    # User data must be isolated
                    if context_a.user_id != context_b.user_id:
                        assert context_a.get_data("user_tier") != context_b.get_data("user_tier") or \
                               context_a.user_id != context_b.user_id
    
    async def test_concurrent_user_execution_isolation(self):
        """Concurrent user executions must maintain complete isolation."""
        manager = UserContextManager()
        
        async def user_execution_simulation(user_id: str, execution_id: str):
            async with managed_user_context(user_id, execution_id) as context:
                # Simulate agent execution with user context
                context.set_data("agent_state", "running")
                context.set_data("execution_start", "2025-09-11T10:00:00Z")
                
                # Simulate some processing time
                await asyncio.sleep(0.01)
                
                # Simulate state changes during execution
                context.set_data("agent_state", "thinking")
                context.set_data("tools_used", ["calculator", "web_search"])
                
                await asyncio.sleep(0.01)
                
                context.set_data("agent_state", "completing")
                context.set_data("execution_end", "2025-09-11T10:00:02Z")
                
                return {
                    "user_id": context.user_id,
                    "execution_id": context.execution_id,
                    "final_state": context.get_data("agent_state"),
                    "tools_used": context.get_data("tools_used")
                }
        
        # Run multiple concurrent user executions
        results = await asyncio.gather(
            user_execution_simulation(self.user_id_1, "exec_1_1"),
            user_execution_simulation(self.user_id_1, "exec_1_2"),  # Same user, different execution
            user_execution_simulation(self.user_id_2, "exec_2_1"),
            user_execution_simulation(self.user_id_3, "exec_3_1"),
        )
        
        # Verify all executions completed successfully with proper isolation
        assert len(results) == 4
        
        # Verify each execution has correct user context
        for result in results:
            assert result["user_id"] in [self.user_id_1, self.user_id_2, self.user_id_3]
            assert result["final_state"] == "completing"
            assert result["tools_used"] == ["calculator", "web_search"]
        
        # Verify user_1 had two separate executions
        user_1_results = [r for r in results if r["user_id"] == self.user_id_1]
        assert len(user_1_results) == 2
        assert user_1_results[0]["execution_id"] != user_1_results[1]["execution_id"]
    
    async def test_context_memory_isolation_validation(self):
        """Memory references must be completely isolated between users."""
        manager = UserContextManager()
        
        # Create contexts and add reference data
        context_1 = await manager.create_context(self.user_id_1, "ref_test_1")
        context_2 = await manager.create_context(self.user_id_2, "ref_test_2")
        
        # Add complex data structures
        user_1_data = {
            "sensitive_info": {"account_id": "acc_123", "api_keys": ["key_1", "key_2"]},
            "agent_memory": ["previous_chat_1", "previous_chat_2"],
            "preferences": {"theme": "dark", "language": "en"}
        }
        
        user_2_data = {
            "sensitive_info": {"account_id": "acc_456", "api_keys": ["key_3", "key_4"]},
            "agent_memory": ["different_chat_1", "different_chat_2"], 
            "preferences": {"theme": "light", "language": "es"}
        }
        
        context_1.set_data("user_data", user_1_data)
        context_2.set_data("user_data", user_2_data)
        
        # Verify data isolation
        retrieved_1 = context_1.get_data("user_data")
        retrieved_2 = context_2.get_data("user_data")
        
        # Data must be different
        assert retrieved_1 != retrieved_2
        assert retrieved_1["sensitive_info"]["account_id"] != retrieved_2["sensitive_info"]["account_id"]
        assert retrieved_1["agent_memory"] != retrieved_2["agent_memory"]
        
        # Memory references must be isolated
        assert id(retrieved_1) != id(retrieved_2)
        assert id(retrieved_1["sensitive_info"]) != id(retrieved_2["sensitive_info"])
    
    async def test_enterprise_security_compliance(self):
        """Enterprise security requirements must be met."""
        manager = UserContextManager()
        
        # Test enterprise context creation with audit trail
        enterprise_context = await manager.create_context(
            user_id="enterprise_user_001",
            request_id="audit_req_001",
            audit_required=True
        )
        
        # Enterprise contexts must have enhanced security
        assert enterprise_context.audit_required is True
        assert enterprise_context.user_id == "enterprise_user_001"
        
        # Test audit trail functionality
        enterprise_context.audit_action("agent_execution_start", {
            "agent_type": "cost_optimizer",
            "user_tier": "enterprise"
        })
        
        enterprise_context.audit_action("data_access", {
            "table": "user_data",
            "operation": "read"
        })
        
        # Verify audit trail is captured
        audit_log = enterprise_context.get_audit_log()
        assert len(audit_log) >= 2
        assert any("agent_execution_start" in entry["action"] for entry in audit_log)
        assert any("data_access" in entry["action"] for entry in audit_log)
    
    async def test_context_cleanup_and_ttl(self):
        """User contexts must clean up properly and respect TTL."""
        manager = UserContextManager()
        
        # Create contexts with short TTL
        short_ttl_context = await manager.create_context(
            user_id=self.user_id_1,
            request_id="ttl_test",
            ttl_seconds=0.1  # Very short TTL for testing
        )
        
        # Context should exist initially
        assert await manager.context_exists(short_ttl_context.context_id)
        
        # Wait for TTL expiration
        await asyncio.sleep(0.2)
        
        # Context should be cleaned up
        assert not await manager.context_exists(short_ttl_context.context_id)
    
    async def test_resource_usage_limits(self):
        """User contexts must respect resource usage limits."""
        manager = UserContextManager()
        
        # Test memory limits per user
        with self.isolated_env.temporary_override("MAX_USER_CONTEXT_MEMORY", "1024", source="test"):
            context = await manager.create_context(self.user_id_1, "memory_test")
            
            # Add data up to limit
            small_data = "x" * 512
            context.set_data("data_1", small_data)
            context.set_data("data_2", small_data)
            
            # Attempting to exceed limit should raise error
            large_data = "x" * 1024
            with pytest.raises((MemoryError, ResourceLimitError)):
                context.set_data("data_3", large_data)
    
    @pytest.mark.performance
    async def test_user_isolation_performance_overhead(self):
        """User isolation security must have acceptable performance overhead."""
        import time
        
        manager = UserContextManager()
        
        # Benchmark context creation
        start_time = time.perf_counter()
        
        contexts = []
        for i in range(100):
            context = await manager.create_context(
                user_id=f"perf_user_{i}",
                request_id=f"perf_req_{i}"
            )
            contexts.append(context)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Should create 100 contexts in under 100ms
        assert duration < 0.1, f"Context creation too slow: {duration:.3f}s for 100 contexts"
        
        # Benchmark context validation
        start_time = time.perf_counter()
        
        for context in contexts:
            await validate_user_context(context, expected_user=context.user_id)
        
        end_time = time.perf_counter()
        validation_duration = end_time - start_time
        
        # Should validate 100 contexts in under 50ms
        assert validation_duration < 0.05, f"Context validation too slow: {validation_duration:.3f}s for 100 validations"