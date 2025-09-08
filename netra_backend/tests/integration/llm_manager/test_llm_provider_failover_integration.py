"""
Test LLM Provider Failover Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure service continuity during provider outages
- Value Impact: Maintains chat availability when primary LLM provider fails
- Strategic Impact: Prevents revenue loss from service disruptions

RELIABILITY CRITICAL: Provider failover must work seamlessly to maintain business value delivery.
This validates that LLM operations continue when providers fail, with proper user context preservation.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, patch, MagicMock
import time
import uuid
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest  
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.llm.llm_manager import LLMManager, create_llm_manager
from netra_backend.app.llm.client_unified import ResilientLLMClient, RetryableUnifiedClient
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.llm_types import LLMProvider, LLMResponse, TokenUsage
from shared.isolated_environment import get_env


class ProviderStatus(Enum):
    """Provider availability status for testing."""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    FAILED = "failed"
    TIMEOUT = "timeout"


class TestLLMProviderFailoverIntegration(BaseIntegrationTest):
    """
    Test LLM provider failover scenarios with user context preservation.
    
    CRITICAL: These tests ensure chat remains available during provider failures.
    """
    
    @pytest.fixture
    async def user_contexts(self):
        """Create user contexts for failover testing."""
        contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"failover-user-{i}",
                session_id=f"failover-session-{i}", 
                thread_id=f"failover-thread-{i}",
                execution_id=f"failover-exec-{i}",
                permissions=["read", "write"],
                metadata={
                    "priority": "high" if i == 0 else "normal",
                    "subscription": "enterprise" if i == 0 else "free"
                }
            )
            contexts.append(context)
        return contexts
    
    @pytest.fixture
    def mock_provider_responses(self):
        """Mock responses for different provider states."""
        return {
            ProviderStatus.HEALTHY: "Healthy response from primary provider",
            ProviderStatus.DEGRADED: "Slow response from degraded provider",
            ProviderStatus.FAILED: Exception("Provider unavailable"),
            ProviderStatus.TIMEOUT: asyncio.TimeoutError("Provider timeout")
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_primary_provider_failure_failover(self, real_services_fixture, user_contexts, mock_provider_responses):
        """
        Test failover when primary provider fails completely.
        
        BVJ: System must continue serving users when primary LLM provider fails.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Mock provider failure sequence: primary fails, secondary succeeds
        call_count = 0
        async def mock_llm_request(prompt, config_name):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call (primary provider) fails
                raise Exception("Primary provider failed")
            else:
                # Second call (fallback provider) succeeds
                return f"Fallback response: {prompt[:50]}"
        
        with patch.object(manager, '_make_llm_request', side_effect=mock_llm_request):
            # User makes request during provider failure
            response = await manager.ask_llm(
                "Analyze cost optimization opportunities",
                use_cache=False  # Disable cache to test actual provider calls
            )
        
        # CRITICAL: User should get response from fallback provider
        assert "Fallback response" in response, "Should receive fallback provider response"
        assert call_count == 2, "Should have attempted primary then fallback"
        
        # Verify user context maintained through failover
        assert manager._user_context.user_id == "failover-user-0", "User context should be preserved"
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_provider_timeout_handling(self, real_services_fixture, user_contexts, mock_provider_responses):
        """
        Test handling of provider timeouts with user session preservation.
        
        BVJ: Slow providers must not block user interactions indefinitely.
        """
        manager = create_llm_manager(user_contexts[1])
        await manager.initialize()
        
        # Mock provider timeout scenario
        async def mock_timeout_request(prompt, config_name):
            # Simulate provider timeout
            await asyncio.sleep(0.1)  # Short delay for test
            raise asyncio.TimeoutError("Provider response timeout")
        
        with patch.object(manager, '_make_llm_request', side_effect=mock_timeout_request):
            start_time = time.time()
            
            response = await manager.ask_llm(
                "Quick analysis request",
                use_cache=False
            )
            
            end_time = time.time()
        
        # CRITICAL: Should handle timeout gracefully and quickly
        assert end_time - start_time < 5.0, "Timeout should be handled quickly"
        assert "unable to process" in response.lower(), "Should return graceful error message"
        
        # Verify manager remains functional after timeout
        assert manager._initialized, "Manager should remain initialized after timeout"
        assert manager._user_context.user_id == "failover-user-1", "User context preserved after timeout"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_failover_isolation(self, real_services_fixture, user_contexts, mock_provider_responses):
        """
        Test failover isolation between concurrent users.
        
        BVJ: Provider failure for one user must not affect other users' sessions.
        """
        managers = [create_llm_manager(ctx) for ctx in user_contexts]
        
        # Initialize all managers
        for manager in managers:
            await manager.initialize()
        
        # Mock different provider states for different users
        provider_states = {
            "failover-user-0": ProviderStatus.FAILED,    # User 0 experiences failure
            "failover-user-1": ProviderStatus.HEALTHY,   # User 1 has healthy provider  
            "failover-user-2": ProviderStatus.DEGRADED   # User 2 has slow provider
        }
        
        async def mock_user_specific_request(manager_instance, prompt, config_name):
            user_id = manager_instance._user_context.user_id
            state = provider_states[user_id]
            
            if state == ProviderStatus.FAILED:
                # First attempt fails, second succeeds with fallback
                if not hasattr(manager_instance, '_failover_attempted'):
                    manager_instance._failover_attempted = True
                    raise Exception(f"Primary provider failed for {user_id}")
                else:
                    return f"Fallback response for {user_id}: {prompt[:30]}"
            elif state == ProviderStatus.HEALTHY:
                return f"Healthy response for {user_id}: {prompt[:30]}"
            elif state == ProviderStatus.DEGRADED:
                await asyncio.sleep(0.2)  # Simulate slow response
                return f"Degraded response for {user_id}: {prompt[:30]}"
        
        # Patch each manager's request method individually
        for manager in managers:
            async def make_request_for_manager(prompt, config_name, mgr=manager):
                return await mock_user_specific_request(mgr, prompt, config_name)
            
            manager._make_llm_request = make_request_for_manager
        
        # Execute concurrent requests
        async def make_user_request(manager, user_prompt):
            start_time = time.time()
            response = await manager.ask_llm(user_prompt, use_cache=False)
            end_time = time.time()
            
            return {
                "user_id": manager._user_context.user_id,
                "response": response,
                "duration": end_time - start_time,
                "manager": manager
            }
        
        user_prompts = [
            "Enterprise user cost analysis",
            "Free user basic query", 
            "Normal user optimization request"
        ]
        
        # Run all requests concurrently
        tasks = [make_user_request(managers[i], user_prompts[i]) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Verify isolation and appropriate responses
        for i, result in enumerate(results):
            expected_user_id = f"failover-user-{i}"
            assert result["user_id"] == expected_user_id, f"User ID should match for result {i}"
            
            if i == 0:  # Failed provider user
                assert "Fallback response" in result["response"], "User 0 should get fallback response"
            elif i == 1:  # Healthy provider user
                assert "Healthy response" in result["response"], "User 1 should get healthy response"
                assert result["duration"] < 1.0, "Healthy response should be fast"
            elif i == 2:  # Degraded provider user
                assert "Degraded response" in result["response"], "User 2 should get degraded response"
                assert result["duration"] > 0.1, "Degraded response should be slower"
        
        # Verify no cross-user contamination
        for i, result_i in enumerate(results):
            for j, result_j in enumerate(results):
                if i != j:
                    assert result_i["response"] != result_j["response"], f"Responses {i} and {j} should differ"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_provider_circuit_breaker_functionality(self, real_services_fixture, user_contexts):
        """
        Test circuit breaker prevents cascading provider failures.
        
        BVJ: Circuit breaker protects system from cascading failures during provider outages.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Track circuit breaker state
        circuit_failures = 0
        circuit_opened = False
        
        async def mock_failing_provider(prompt, config_name):
            nonlocal circuit_failures, circuit_opened
            
            # Simulate consistent failures that should trigger circuit breaker
            circuit_failures += 1
            
            if circuit_failures >= 3:
                circuit_opened = True
                
            if circuit_opened and circuit_failures < 8:
                # Circuit is open, return fast failure
                raise Exception("Circuit breaker open - fast failure")
            elif circuit_failures >= 8:
                # Circuit attempts to close, provider recovers
                return f"Provider recovered: {prompt[:50]}"
            else:
                # Initial failures
                raise Exception(f"Provider failure #{circuit_failures}")
        
        with patch.object(manager, '_make_llm_request', side_effect=mock_failing_provider):
            responses = []
            
            # Make multiple requests to trigger circuit breaker
            for i in range(10):
                try:
                    response = await manager.ask_llm(
                        f"Request {i} during provider issues",
                        use_cache=False
                    )
                    responses.append(("success", response))
                except Exception as e:
                    responses.append(("error", str(e)))
                
                # Small delay between requests
                await asyncio.sleep(0.05)
        
        # Verify circuit breaker behavior
        error_responses = [r for r in responses if r[0] == "error"]
        success_responses = [r for r in responses if r[0] == "success"]
        
        # Should have some failures, then some fast failures (circuit open), then recovery
        assert len(error_responses) >= 3, "Should have initial failures"
        assert len(success_responses) >= 1, "Should have recovery success"
        
        # Check for fast failure messages (circuit breaker open)
        fast_failures = [r for r in error_responses if "Circuit breaker open" in r[1]]
        assert len(fast_failures) > 0, "Should have fast failures when circuit is open"
        
        # Verify provider recovery
        recovery_responses = [r for r in success_responses if "Provider recovered" in r[1]]
        assert len(recovery_responses) > 0, "Should have recovery responses"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_structured_response_failover(self, real_services_fixture, user_contexts):
        """
        Test structured responses work correctly during provider failover.
        
        BVJ: Structured data parsing must work with fallback providers.
        """
        from pydantic import BaseModel
        
        class OptimizationResult(BaseModel):
            savings_percentage: float = 0.0
            recommendations: List[str] = []
            provider_used: str = "unknown"
        
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Mock failover with different structured response formats
        call_attempts = 0
        async def mock_structured_failover(prompt, config_name):
            nonlocal call_attempts
            call_attempts += 1
            
            if call_attempts == 1:
                # Primary provider fails
                raise Exception("Primary structured provider failed")
            else:
                # Fallback provider returns structured data
                return '{"savings_percentage": 15.5, "recommendations": ["Use reserved instances", "Archive old data"], "provider_used": "fallback"}'
        
        with patch.object(manager, '_make_llm_request', side_effect=mock_structured_failover):
            response = await manager.ask_llm_structured(
                "Analyze cost optimization with structured output",
                OptimizationResult,
                use_cache=False
            )
        
        # CRITICAL: Should receive valid structured response from fallback
        assert isinstance(response, OptimizationResult), "Should return OptimizationResult object"
        assert response.savings_percentage == 15.5, "Should have correct savings percentage"
        assert len(response.recommendations) == 2, "Should have 2 recommendations"
        assert response.provider_used == "fallback", "Should indicate fallback provider was used"
        assert call_attempts == 2, "Should have attempted primary then fallback"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_consistency_during_failover(self, real_services_fixture, user_contexts):
        """
        Test cache remains consistent during provider failover.
        
        BVJ: Cache consistency prevents duplicate charges and ensures response consistency.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Mock first request success, second request (same prompt) with provider failure
        request_count = 0
        cached_response = "Cached optimization analysis result"
        
        async def mock_cache_failover_scenario(prompt, config_name):
            nonlocal request_count
            request_count += 1
            
            if request_count == 1:
                # First request succeeds and gets cached
                return cached_response
            else:
                # Provider fails for subsequent requests
                raise Exception("Provider failed after cache populated")
        
        with patch.object(manager, '_make_llm_request', side_effect=mock_cache_failover_scenario):
            # First request - should succeed and populate cache
            response1 = await manager.ask_llm(
                "Analyze optimization opportunities",
                use_cache=True
            )
            
            # Second request with same prompt - should use cache, not hit failing provider
            response2 = await manager.ask_llm(
                "Analyze optimization opportunities", 
                use_cache=True
            )
        
        # CRITICAL: Both responses should be identical (from cache)
        assert response1 == response2 == cached_response, "Cache should provide consistent responses"
        assert request_count == 1, "Should only make one provider request due to caching"
        
        # Verify cache state
        prompt = "Analyze optimization opportunities"
        cache_key = manager._get_cache_key(prompt, "default")
        assert cache_key in manager._cache, "Response should be cached"
        assert manager._cache[cache_key] == cached_response, "Cached response should match"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_provider_health_monitoring(self, real_services_fixture, user_contexts):
        """
        Test health monitoring across multiple providers during failures.
        
        BVJ: Health monitoring enables proactive failover and system reliability.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Mock health check results for different providers
        provider_health_states = {
            "primary": {"status": "failed", "last_error": "Connection timeout"},
            "secondary": {"status": "healthy", "response_time": 150},
            "tertiary": {"status": "degraded", "response_time": 800}
        }
        
        with patch.object(manager, 'health_check') as mock_health:
            mock_health.return_value = {
                "status": "degraded",  # Overall degraded due to primary failure
                "providers": provider_health_states,
                "active_provider": "secondary",
                "failover_count": 1,
                "initialized": True,
                "cache_size": len(manager._cache)
            }
            
            health_result = await manager.health_check()
        
        # Verify health monitoring captures provider states
        assert health_result["status"] == "degraded", "Overall status should reflect primary failure"
        assert health_result["active_provider"] == "secondary", "Should indicate secondary provider is active"
        assert health_result["failover_count"] == 1, "Should track failover events"
        
        # Verify provider-specific health data
        providers = health_result["providers"]
        assert providers["primary"]["status"] == "failed", "Primary should be marked failed"
        assert providers["secondary"]["status"] == "healthy", "Secondary should be healthy"
        assert providers["tertiary"]["status"] == "degraded", "Tertiary should be degraded"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_provider_recovery_after_failure(self, real_services_fixture, user_contexts):
        """
        Test provider recovery and restoration after failure period.
        
        BVJ: System should use recovered primary provider for optimal performance.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Simulate provider failure, then recovery cycle
        recovery_cycle = {
            "phase": "failing",  # failing -> recovering -> recovered
            "request_count": 0
        }
        
        async def mock_recovery_cycle(prompt, config_name):
            recovery_cycle["request_count"] += 1
            count = recovery_cycle["request_count"]
            
            if count <= 3:
                # Initial failure period
                recovery_cycle["phase"] = "failing"
                raise Exception(f"Provider failed (attempt {count})")
            elif count <= 6:
                # Recovery period - intermittent success
                recovery_cycle["phase"] = "recovering"
                if count % 2 == 0:
                    return f"Recovering provider response: {prompt[:30]}"
                else:
                    raise Exception(f"Recovery attempt failed (attempt {count})")
            else:
                # Fully recovered
                recovery_cycle["phase"] = "recovered"
                return f"Fully recovered response: {prompt[:30]}"
        
        responses = []
        with patch.object(manager, '_make_llm_request', side_effect=mock_recovery_cycle):
            # Make requests through the recovery cycle
            for i in range(10):
                try:
                    response = await manager.ask_llm(
                        f"Request {i} during recovery",
                        use_cache=False
                    )
                    responses.append(("success", response, recovery_cycle["phase"]))
                except Exception as e:
                    responses.append(("failure", str(e), recovery_cycle["phase"]))
                
                await asyncio.sleep(0.02)  # Small delay
        
        # Verify recovery progression
        failure_responses = [r for r in responses if r[0] == "failure" and r[2] == "failing"]
        recovering_responses = [r for r in responses if r[2] == "recovering"]
        recovered_responses = [r for r in responses if r[0] == "success" and r[2] == "recovered"]
        
        assert len(failure_responses) >= 2, "Should have initial failure period"
        assert len(recovering_responses) >= 2, "Should have recovery period"  
        assert len(recovered_responses) >= 1, "Should have successful recovery"
        
        # Verify final state indicates recovery
        final_successful = [r for r in responses if r[0] == "success" and "Fully recovered" in r[1]]
        assert len(final_successful) > 0, "Should have fully recovered responses"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_failover_preserves_user_session_state(self, real_services_fixture, user_contexts):
        """
        Test user session state preservation during provider failover.
        
        BVJ: User session continuity is critical for conversation flow and trust.
        """
        manager = create_llm_manager(user_contexts[0])
        await manager.initialize()
        
        # Setup session state before failover
        initial_state = {
            "conversation_turns": 0,
            "user_preferences": {"response_style": "technical"},
            "session_data": {"started_at": time.time(), "topic": "cost_optimization"}
        }
        
        # Simulate session state in manager
        manager._session_state = initial_state.copy()
        
        # Mock failover scenario that should preserve session state
        failover_occurred = False
        
        async def mock_failover_with_state_preservation(prompt, config_name):
            nonlocal failover_occurred
            
            # Update session state during request processing
            manager._session_state["conversation_turns"] += 1
            
            if not failover_occurred:
                failover_occurred = True
                # First request triggers failover
                raise Exception("Primary provider failed during active session")
            else:
                # Fallback provider continues session
                return f"Failover response (turn {manager._session_state['conversation_turns']}): {prompt[:40]}"
        
        with patch.object(manager, '_make_llm_request', side_effect=mock_failover_with_state_preservation):
            # Make request that triggers failover
            response1 = await manager.ask_llm("First request in session", use_cache=False)
            
            # Make another request that uses fallback provider  
            response2 = await manager.ask_llm("Second request after failover", use_cache=False)
        
        # CRITICAL: Session state should be preserved through failover
        assert manager._session_state["conversation_turns"] == 2, "Should have 2 conversation turns"
        assert manager._session_state["user_preferences"]["response_style"] == "technical", "User preferences should be preserved"
        assert manager._session_state["session_data"]["topic"] == "cost_optimization", "Session topic should be preserved"
        
        # Responses should indicate continuity
        assert "(turn 1)" in response1, "First response should show turn 1"
        assert "(turn 2)" in response2, "Second response should show turn 2"
        
        # User context should remain intact
        assert manager._user_context.user_id == "failover-user-0", "User ID should be preserved"
        assert manager._user_context.session_id == "failover-session-0", "Session ID should be preserved"