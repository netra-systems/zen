"""
Test LLM Manager Multi-User Context Isolation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent catastrophic conversation mixing between users 
- Value Impact: Ensures user privacy and trust in LLM conversations
- Strategic Impact: Enables 90% of current business value through secure chat

CRITICAL: LLM conversations mixing between users would destroy trust and violate privacy.
This test suite validates that the factory pattern prevents conversation data leakage.
"""

import asyncio
import pytest
from typing import Dict, List, Any
from unittest.mock import AsyncMock, patch
import time
import uuid

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.llm.llm_manager import LLMManager, create_llm_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env


class TestLLMManagerMultiUserIsolation(BaseIntegrationTest):
    """
    Test LLM Manager factory pattern and multi-user isolation.
    
    CRITICAL: These tests prevent conversation mixing that would destroy user trust.
    """
    
    @pytest.fixture
    async def user_contexts(self):
        """Create multiple isolated user contexts for testing."""
        contexts = []
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"test-user-{i}",
                session_id=f"session-{i}",
                thread_id=f"thread-{i}",
                execution_id=f"exec-{i}",
                permissions=["read", "write"],
                metadata={"test_user": True}
            )
            contexts.append(context)
        return contexts
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_creates_isolated_managers(self, real_services_fixture, user_contexts):
        """
        Test that factory creates truly isolated LLM managers per user.
        
        BVJ: Each user MUST have their own manager to prevent conversation mixing.
        """
        managers = []
        
        # Create managers for different users
        for context in user_contexts:
            manager = create_llm_manager(context)
            await manager.initialize()
            managers.append(manager)
        
        # Verify each manager is unique instance
        for i, manager1 in enumerate(managers):
            for j, manager2 in enumerate(managers):
                if i != j:
                    assert manager1 is not manager2, "Managers should be different instances"
                    assert id(manager1) != id(manager2), "Manager memory addresses should differ"
        
        # Verify each manager has its own cache
        for i, manager1 in enumerate(managers):
            for j, manager2 in enumerate(managers):
                if i != j:
                    assert manager1._cache is not manager2._cache, "Caches should be separate instances"
                    assert id(manager1._cache) != id(manager2._cache), "Cache memory addresses should differ"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_llm_operations_isolation(self, real_services_fixture, user_contexts):
        """
        Test concurrent LLM operations maintain user isolation.
        
        BVJ: Multiple users making simultaneous requests must not share cache or responses.
        """
        managers = [create_llm_manager(ctx) for ctx in user_contexts[:3]]
        
        # Initialize all managers
        for manager in managers:
            await manager.initialize()
        
        # Create different prompts for each user
        user_prompts = [
            ("User A: Analyze my AWS costs", "confidential_aws_data_user_a"),
            ("User B: Optimize my Azure spend", "confidential_azure_data_user_b"), 
            ("User C: Review my GCP usage", "confidential_gcp_data_user_c")
        ]
        
        # Execute concurrent requests
        async def make_request(manager, prompt_data):
            prompt, expected_suffix = prompt_data
            response = await manager.ask_llm(prompt, use_cache=True)
            return response, manager._user_context.user_id
        
        # Run all requests concurrently
        tasks = [
            make_request(managers[i], user_prompts[i]) 
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify responses are different and user-specific
        responses = [result[0] for result in results]
        user_ids = [result[1] for result in results]
        
        # Each response should be unique
        assert len(set(responses)) == 3, "All responses should be different"
        
        # Verify user IDs are correctly maintained
        expected_user_ids = ["test-user-0", "test-user-1", "test-user-2"]
        assert user_ids == expected_user_ids, f"User IDs mismatch: {user_ids}"
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_cache_isolation_prevents_leakage(self, real_services_fixture, user_contexts):
        """
        Test that cache isolation prevents conversation leakage between users.
        
        BVJ: CRITICAL - Cache must be per-user to prevent privacy violations.
        """
        manager_a = create_llm_manager(user_contexts[0])
        manager_b = create_llm_manager(user_contexts[1])
        
        await manager_a.initialize()
        await manager_b.initialize()
        
        # User A makes a request (should be cached)
        prompt_a = "Confidential: My company's financial data shows..."
        response_a = await manager_a.ask_llm(prompt_a, use_cache=True)
        
        # Verify User A's response is cached
        assert manager_a._is_cached(prompt_a, "default"), "User A's response should be cached"
        
        # User B makes the SAME request  
        response_b = await manager_b.ask_llm(prompt_a, use_cache=True)
        
        # CRITICAL: User B should NOT get User A's cached response
        # The cache key includes user_id, so should not be cached for User B
        assert not manager_b._is_cached(prompt_a, "default"), "User B should NOT have User A's cache"
        
        # Verify responses are different (due to different user contexts)
        assert response_a != response_b, "Responses should differ due to user isolation"
        
        # Verify cache sizes are independent
        assert len(manager_a._cache) == 1, "User A should have 1 cached item"
        assert len(manager_b._cache) == 1, "User B should have 1 cached item"
        
        # Double-check: Clear User A's cache, User B should be unaffected
        manager_a.clear_cache()
        assert len(manager_a._cache) == 0, "User A's cache should be empty"
        assert len(manager_b._cache) == 1, "User B's cache should still have 1 item"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_scoped_cache_keys(self, real_services_fixture, user_contexts):
        """
        Test that cache keys are properly scoped to user contexts.
        
        BVJ: Cache keys must include user_id to prevent cross-user access.
        """
        manager_a = create_llm_manager(user_contexts[0])
        manager_b = create_llm_manager(user_contexts[1])
        
        await manager_a.initialize()
        await manager_b.initialize()
        
        prompt = "Analyze optimization opportunities"
        
        # Generate cache keys for same prompt but different users
        cache_key_a = manager_a._get_cache_key(prompt, "default")
        cache_key_b = manager_b._get_cache_key(prompt, "default")
        
        # Cache keys should be different due to user_id prefix
        assert cache_key_a != cache_key_b, "Cache keys should differ by user"
        assert user_contexts[0].user_id in cache_key_a, "Cache key A should contain user A's ID"
        assert user_contexts[1].user_id in cache_key_b, "Cache key B should contain user B's ID"
        
        # Make requests to populate caches
        await manager_a.ask_llm(prompt, use_cache=True)
        await manager_b.ask_llm(prompt, use_cache=True)
        
        # Verify both caches have entries with different keys
        assert cache_key_a in manager_a._cache, "Manager A should have its cache key"
        assert cache_key_b in manager_b._cache, "Manager B should have its cache key"
        
        # Cross-contamination check
        assert cache_key_a not in manager_b._cache, "Manager B should NOT have Manager A's key"
        assert cache_key_b not in manager_a._cache, "Manager A should NOT have Manager B's key"
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_manager_memory_isolation(self, real_services_fixture, user_contexts):
        """
        Test memory isolation between managers prevents state contamination.
        
        BVJ: Each manager must maintain independent state to prevent user data mixing.
        """
        managers = [create_llm_manager(ctx) for ctx in user_contexts[:4]]
        
        # Initialize with different configurations
        config_states = []
        for i, manager in enumerate(managers):
            await manager.initialize() 
            
            # Modify manager state uniquely
            manager._test_marker = f"user_{i}_unique_marker"
            manager._custom_data = {"user_specific": i, "timestamp": time.time()}
            
            config_states.append({
                "marker": manager._test_marker,
                "data": manager._custom_data.copy()
            })
        
        # Verify each manager maintains its unique state
        for i, manager in enumerate(managers):
            assert hasattr(manager, "_test_marker"), f"Manager {i} should have test marker"
            assert manager._test_marker == f"user_{i}_unique_marker", f"Manager {i} marker corrupted"
            
            expected_data = config_states[i]["data"]
            assert manager._custom_data == expected_data, f"Manager {i} custom data corrupted"
        
        # Modify one manager's state and verify others unaffected
        managers[0]._test_marker = "MODIFIED"
        managers[0]._custom_data["modified"] = True
        
        # Other managers should be unchanged
        for i in range(1, len(managers)):
            assert managers[i]._test_marker != "MODIFIED", f"Manager {i} should not be affected"
            assert "modified" not in managers[i]._custom_data, f"Manager {i} data should not change"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_cache_operations_safety(self, real_services_fixture, user_contexts):
        """
        Test concurrent cache operations maintain isolation and thread safety.
        
        BVJ: High-load scenarios must not cause cache corruption or user data mixing.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Simulate high concurrency with rapid cache operations
        async def rapid_cache_operations(operation_id: int):
            results = []
            for i in range(10):
                prompt = f"Operation {operation_id}, Request {i}"
                response = await manager.ask_llm(prompt, use_cache=True)
                results.append((prompt, response))
                
                # Verify cache state after each operation
                cache_key = manager._get_cache_key(prompt, "default")
                assert cache_key in manager._cache, f"Cache should contain key for operation {operation_id}.{i}"
            
            return results
        
        # Run multiple concurrent operations
        tasks = [rapid_cache_operations(op_id) for op_id in range(5)]
        all_results = await asyncio.gather(*tasks)
        
        # Verify results integrity
        total_requests = sum(len(results) for results in all_results)
        assert total_requests == 50, "Should have 50 total requests"
        
        # Verify cache integrity
        expected_cache_size = 50  # All unique prompts
        assert len(manager._cache) == expected_cache_size, f"Cache should have {expected_cache_size} entries"
        
        # Verify no duplicate or corrupted entries
        all_prompts = []
        for results in all_results:
            for prompt, _ in results:
                all_prompts.append(prompt)
        
        assert len(set(all_prompts)) == 50, "All prompts should be unique"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_manager_cleanup_isolation(self, real_services_fixture, user_contexts):
        """
        Test that manager cleanup doesn't affect other user managers.
        
        BVJ: User session cleanup must not impact other active users.
        """
        managers = [create_llm_manager(ctx) for ctx in user_contexts[:3]]
        
        # Initialize and populate caches
        for i, manager in enumerate(managers):
            await manager.initialize()
            for j in range(3):
                prompt = f"User {i} request {j}"
                await manager.ask_llm(prompt, use_cache=True)
        
        # Verify initial state
        for manager in managers:
            assert len(manager._cache) == 3, "Each manager should have 3 cached items"
        
        # Shutdown one manager
        await managers[1].shutdown()
        
        # Verify shutdown manager is cleaned
        assert len(managers[1]._cache) == 0, "Shutdown manager cache should be empty"
        assert not managers[1]._initialized, "Shutdown manager should not be initialized"
        
        # Verify other managers unaffected
        assert len(managers[0]._cache) == 3, "Manager 0 cache should be intact"
        assert len(managers[2]._cache) == 3, "Manager 2 cache should be intact"
        assert managers[0]._initialized, "Manager 0 should still be initialized"
        assert managers[2]._initialized, "Manager 2 should still be initialized"
        
        # Verify shutdown manager can't serve requests
        response = await managers[1].ask_llm("Test after shutdown")
        assert "unable to process" in response.lower(), "Shutdown manager should return error"
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_deprecated_singleton_isolation_warning(self, real_services_fixture):
        """
        Test that deprecated singleton function warns about isolation issues.
        
        BVJ: Migration safety - deprecated functions must warn about security risks.
        """
        from netra_backend.app.llm.llm_manager import get_llm_manager
        
        with pytest.warns(DeprecationWarning, match="mix conversations between users"):
            manager = await get_llm_manager()
            
        assert isinstance(manager, LLMManager), "Should return LLMManager instance"
        assert manager._user_context is None, "Deprecated manager should have no user context"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_stress_user_creation_cleanup(self, real_services_fixture):
        """
        Test stress scenario of rapid user manager creation and cleanup.
        
        BVJ: System must handle high user churn without memory leaks.
        """
        created_managers = []
        
        # Rapid creation of many managers
        for i in range(20):
            context = UserExecutionContext(
                user_id=f"stress-user-{i}",
                session_id=f"stress-session-{i}",
                thread_id=f"stress-thread-{i}",
                execution_id=f"stress-exec-{i}",
                permissions=["read"],
                metadata={"stress_test": True}
            )
            
            manager = create_llm_manager(context)
            await manager.initialize()
            
            # Make a request to populate cache
            await manager.ask_llm(f"Stress test request {i}", use_cache=True)
            created_managers.append(manager)
        
        # Verify all managers are isolated
        for i, manager in enumerate(created_managers):
            assert manager._user_context.user_id == f"stress-user-{i}"
            assert len(manager._cache) == 1, f"Manager {i} should have 1 cache entry"
        
        # Cleanup half the managers
        for i in range(0, 20, 2):  # Even indices
            await created_managers[i].shutdown()
        
        # Verify remaining managers unaffected  
        for i in range(1, 20, 2):  # Odd indices
            manager = created_managers[i]
            assert manager._initialized, f"Manager {i} should still be initialized"
            assert len(manager._cache) == 1, f"Manager {i} should still have cache"
            
            # Should still be able to make requests
            response = await manager.ask_llm("Post-cleanup test", use_cache=True)
            assert "unable to process" not in response.lower(), f"Manager {i} should still work"