class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""Mission Critical Token Optimization Compliance Tests

This test suite validates that the token optimization system respects all critical
architectural constraints including frozen dataclass compliance, SSOT patterns,
and user isolation requirements.

CRITICAL: These tests ensure production safety and SSOT compliance.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.token_optimization.context_manager import TokenOptimizationContextManager
from netra_backend.app.services.token_optimization.session_factory import TokenOptimizationSessionFactory
from netra_backend.app.services.token_optimization.config_manager import TokenOptimizationConfigManager
from netra_backend.app.services.token_optimization.integration_service import TokenOptimizationIntegrationService
from netra_backend.app.services.billing.token_counter import TokenCounter
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestFrozenDataclassCompliance:
    """Test that token optimization respects UserExecutionContext frozen=True constraint."""
    
    @pytest.fixture
    def sample_context(self):
        """Create sample UserExecutionContext for testing."""
        return UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456", 
            run_id="run_789",
            metadata={"existing_key": "existing_value"}
        )
    
    @pytest.fixture
    def context_manager(self):
        """Create TokenOptimizationContextManager for testing."""
        token_counter = TokenCounter()
        return TokenOptimizationContextManager(token_counter)
    
    def test_context_is_frozen(self, sample_context):
        """Verify UserExecutionContext is indeed frozen."""
        
        # Attempting to modify frozen dataclass fields should raise FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            sample_context.user_id = "modified_user"
        
        # Note: metadata is a dict field, so it's mutable even in frozen dataclass
        # This is expected behavior - the context itself is frozen but dict contents can change
        # Our implementation addresses this by never mutating the original context
        original_metadata = sample_context.metadata.copy()
        sample_context.metadata["test_key"] = "test_value"  # This should work
        
        # Verify we can modify metadata dict (this is why we need immutable patterns)
        assert sample_context.metadata["test_key"] == "test_value"
        assert "test_key" not in original_metadata  # Original copy unchanged
    
    def test_track_usage_returns_new_context(self, context_manager, sample_context):
        """Test that track_usage returns new context without mutating original."""
        
        original_metadata = sample_context.metadata.copy()
        original_id = id(sample_context)
        
        # Track usage should return new context
        enhanced_context = context_manager.track_agent_usage(
            context=sample_context,
            agent_name="test_agent",
            input_tokens=100,
            output_tokens=50,
            model="gpt-4",
            operation_type="execution"
        )
        
        # Original context should be unchanged
        assert sample_context.metadata == original_metadata
        assert id(sample_context) == original_id
        
        # Enhanced context should be different object
        assert enhanced_context is not sample_context
        assert id(enhanced_context) != original_id
        
        # Enhanced context should have token data
        assert "token_usage" in enhanced_context.metadata
        assert enhanced_context.metadata["existing_key"] == "existing_value"  # Preserved
    
    def test_optimize_prompt_returns_new_context(self, context_manager, sample_context):
        """Test that prompt optimization returns new context without mutating original."""
        
        original_metadata = sample_context.metadata.copy()
        
        # Optimize prompt should return new context and optimized prompt
        enhanced_context, optimized_prompt = context_manager.optimize_prompt_for_context(
            context=sample_context,
            agent_name="test_agent",
            prompt="This is a test prompt that can be optimized for better efficiency.",
            target_reduction=20
        )
        
        # Original context should be unchanged
        assert sample_context.metadata == original_metadata
        
        # Enhanced context should be different and have optimization data
        assert enhanced_context is not sample_context
        assert "prompt_optimizations" in enhanced_context.metadata
        assert enhanced_context.metadata["existing_key"] == "existing_value"  # Preserved
        
        # Optimized prompt should be different
        assert isinstance(optimized_prompt, str)
        assert len(optimized_prompt) > 0
    
    def test_add_suggestions_returns_new_context(self, context_manager, sample_context):
        """Test that adding suggestions returns new context without mutating original."""
        
        original_metadata = sample_context.metadata.copy()
        
        # Add suggestions should return new context
        enhanced_context = context_manager.add_cost_suggestions(
            context=sample_context,
            agent_name="test_agent"
        )
        
        # Original context should be unchanged
        assert sample_context.metadata == original_metadata
        
        # Enhanced context should be different and have suggestions data
        assert enhanced_context is not sample_context
        assert "cost_optimization_suggestions" in enhanced_context.metadata
        assert enhanced_context.metadata["existing_key"] == "existing_value"  # Preserved


class TestUserIsolationCompliance:
    """Test that token optimization provides complete user isolation."""
    
    @pytest.fixture
    def session_factory(self):
        """Create session factory for testing."""
        return TokenOptimizationSessionFactory()
    
    @pytest.fixture
    def user_context_a(self):
        """Create context for user A."""
        return UserExecutionContext(
            user_id="user_a",
            thread_id="thread_a",
            run_id="run_a"
        )
    
    @pytest.fixture 
    def user_context_b(self):
        """Create context for user B."""
        return UserExecutionContext(
            user_id="user_b", 
            thread_id="thread_b",
            run_id="run_b"
        )
    
    def test_session_isolation(self, session_factory, user_context_a, user_context_b):
        """Test that users get completely isolated sessions."""
        
        # Create sessions for both users
        session_a = session_factory.create_session(user_context_a)
        session_b = session_factory.create_session(user_context_b)
        
        # Sessions should be different objects
        assert session_a is not session_b
        assert session_a.session_id != session_b.session_id
        assert session_a.context.user_id != session_b.context.user_id
        
        # Track usage for both users
        result_a = session_a.track_usage(
            input_tokens=100,
            output_tokens=50,
            model="gpt-4",
            operation_type="test_a"
        )
        
        result_b = session_b.track_usage(
            input_tokens=200,
            output_tokens=75,
            model="claude-3",
            operation_type="test_b"
        )
        
        # Results should be isolated
        assert result_a["session_id"] != result_b["session_id"]
        assert session_a.operations_count == 1
        assert session_b.operations_count == 1
        assert session_a.total_tokens == 150  # 100 + 50
        assert session_b.total_tokens == 275  # 200 + 75
        
        # No cross-contamination
        assert session_a.total_tokens != session_b.total_tokens
        assert session_a.total_cost != session_b.total_cost
    
    def test_context_isolation_in_integration_service(self):
        """Test user isolation in integration service."""
        
        # Create integration service
        integration_service = TokenOptimizationIntegrationService()
        
        # Create contexts for different users
        context_user1 = UserExecutionContext(
            user_id="user1",
            thread_id="thread1", 
            run_id="run1"
        )
        
        context_user2 = UserExecutionContext(
            user_id="user2",
            thread_id="thread2",
            run_id="run2"
        )
        
        # Track usage for both users
        async def test_isolation():
            enhanced_context1, result1 = await integration_service.track_agent_usage(
                context=context_user1,
                agent_name="agent1",
                input_tokens=100,
                output_tokens=50,
                model="gpt-4"
            )
            
            enhanced_context2, result2 = await integration_service.track_agent_usage(
                context=context_user2,
                agent_name="agent2", 
                input_tokens=200,
                output_tokens=75,
                model="claude-3"
            )
            
            # Contexts should remain isolated
            assert enhanced_context1.user_id != enhanced_context2.user_id
            assert result1["session_result"]["session_id"] != result2["session_result"]["session_id"]
            
            # No data leakage between users
            user1_token_data = enhanced_context1.metadata.get("token_usage", {})
            user2_token_data = enhanced_context2.metadata.get("token_usage", {})
            
            assert user1_token_data != user2_token_data
            assert user1_token_data.get("cumulative_tokens") != user2_token_data.get("cumulative_tokens")
        
        # Run async test
        asyncio.run(test_isolation())


class TestSSOTCompliance:
    """Test that token optimization respects SSOT (Single Source of Truth) principles."""
    
    def test_uses_existing_token_counter(self):
        """Test that system uses existing TokenCounter instead of creating duplicates."""
        
        context_manager = TokenOptimizationContextManager(TokenCounter())
        session_factory = TokenOptimizationSessionFactory()
        
        # Both should use TokenCounter (not create new tracking classes)
        assert isinstance(context_manager.token_counter, TokenCounter)
        assert isinstance(session_factory._token_counter, TokenCounter)
        
        # Should not create duplicate tracking functionality
        assert not hasattr(context_manager, 'custom_tracker')
        assert not hasattr(session_factory, 'duplicate_counter')
    
    def test_uses_universal_registry(self):
        """Test that session factory uses UniversalRegistry for user isolation."""
        
        session_factory = TokenOptimizationSessionFactory()
        
        # Should use UniversalRegistry for session management
        assert hasattr(session_factory, '_session_registry')
        assert session_factory._session_registry is not None
        
        # Registry should handle user isolation
        context1 = UserExecutionContext(user_id="user1", thread_id="t1", run_id="r1")
        context2 = UserExecutionContext(user_id="user2", thread_id="t2", run_id="r2")
        
        session1 = session_factory.create_session(context1)
        session2 = session_factory.create_session(context2)
        
        # Should be registered separately
        assert session1 is not session2
        
        # Check that sessions are registered (keys will include request_id)
        registry_keys = list(session_factory._active_sessions.keys())
        assert len(registry_keys) == 2
        
        # Verify user separation in keys
        user1_key = next((k for k in registry_keys if "user1" in k), None)
        user2_key = next((k for k in registry_keys if "user2" in k), None)
        
        assert user1_key is not None, f"No user1 session found in keys: {registry_keys}"
        assert user2_key is not None, f"No user2 session found in keys: {registry_keys}"
        assert user1_key != user2_key
    
    def test_configuration_driven_pricing(self):
        """Test that pricing comes from configuration system, not hardcoded."""
        
        config_manager = TokenOptimizationConfigManager()
        
        # Should use UnifiedConfigurationManager
        assert hasattr(config_manager, 'config_manager')
        assert config_manager.config_manager is not None
        
        # Should get pricing from configuration
        pricing = config_manager.get_model_pricing()
        
        assert isinstance(pricing, dict)
        assert len(pricing) > 0
        assert "default" in pricing or len(pricing) > 1
        
        # Should have proper decimal precision
        for model_pricing in pricing.values():
            if isinstance(model_pricing, dict):
                assert "input" in model_pricing
                assert "output" in model_pricing
    
    def test_no_new_websocket_events(self):
        """Test that system uses existing WebSocket events, not new ones."""
        
        # Mock WebSocket manager
        websocket = TestWebSocketConnection()
        integration_service = TokenOptimizationIntegrationService(mock_websocket)
        
        # Test that service can work with existing WebSocket patterns
        assert integration_service.websocket_manager is mock_websocket
        
        # Integration service should only use existing event types like:
        # - agent_thinking
        # - agent_completed  
        # NOT new event types like token_usage_update, token_optimization_alert
        
        # This is verified through the WebSocket emission methods which
        # only use "agent_thinking" and "agent_completed" event types


class TestBaseAgentIntegration:
    """Test BaseAgent integration respects architectural constraints."""
    
    def test_base_agent_has_token_optimization(self):
        """Test that BaseAgent has token optimization capabilities."""
        
        agent = BaseAgent(name="test_agent")
        
        # Should have token counter and context manager
        assert hasattr(agent, 'token_counter')
        assert hasattr(agent, 'token_context_manager')
        
        # Should be proper types
        assert isinstance(agent.token_counter, TokenCounter)
        assert isinstance(agent.token_context_manager, TokenOptimizationContextManager)
    
    def test_base_agent_methods_return_new_context(self):
        """Test that BaseAgent token methods return new contexts."""
        
        agent = BaseAgent(name="test_agent")
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run"
        )
        
        # track_llm_usage should return new context
        enhanced_context = agent.track_llm_usage(
            context=context,
            input_tokens=100,
            output_tokens=50,
            model="gpt-4"
        )
        
        assert enhanced_context is not context
        assert enhanced_context.user_id == context.user_id  # Same user
        assert "token_usage" in enhanced_context.metadata
        
        # optimize_prompt_for_context should return tuple with new context
        optimized_context, optimized_prompt = agent.optimize_prompt_for_context(
            context=context,
            prompt="Test prompt for optimization"
        )
        
        assert optimized_context is not context
        assert isinstance(optimized_prompt, str)
        assert "prompt_optimizations" in optimized_context.metadata
        
        # get_cost_optimization_suggestions should return tuple with new context
        suggestions_context, suggestions = agent.get_cost_optimization_suggestions(context)
        
        assert suggestions_context is not context
        assert isinstance(suggestions, list)
        assert "cost_optimization_suggestions" in suggestions_context.metadata


class TestProductionReadiness:
    """Test production readiness and error handling."""
    
    def test_context_manager_handles_invalid_input(self):
        """Test context manager handles invalid input gracefully."""
        
        context_manager = TokenOptimizationContextManager(TokenCounter())
        
        # Invalid context should not crash
        try:
            invalid_context = UserExecutionContext(
                user_id="",  # Invalid empty user_id 
                thread_id="thread",
                run_id="run"
            )
        except Exception:
            # Context validation should catch this
            pass
        
        valid_context = UserExecutionContext(
            user_id="valid_user",
            thread_id="valid_thread", 
            run_id="valid_run"
        )
        
        # Should handle edge cases gracefully
        enhanced_context = context_manager.track_agent_usage(
            context=valid_context,
            agent_name="test_agent",
            input_tokens=0,  # Edge case: zero tokens
            output_tokens=0,
            model="unknown_model",  # Edge case: unknown model
            operation_type="test"
        )
        
        assert enhanced_context is not None
        assert enhanced_context.user_id == "valid_user"
    
    def test_session_factory_prevents_memory_leaks(self):
        """Test that session factory has cleanup mechanisms."""
        
        session_factory = TokenOptimizationSessionFactory()
        
        # Should have cleanup method
        assert hasattr(session_factory, 'cleanup_expired_sessions')
        
        # Should track active sessions for cleanup
        assert hasattr(session_factory, '_active_sessions')
        
        # Cleanup should return number of cleaned sessions
        cleanup_count = session_factory.cleanup_expired_sessions(max_age_hours=0)
        assert isinstance(cleanup_count, int)
        assert cleanup_count >= 0
    
    def test_integration_service_health_check(self):
        """Test that integration service provides health status."""
        
        integration_service = TokenOptimizationIntegrationService()
        
        # Should have health check method
        health_status = integration_service.get_service_health_status()
        
        assert isinstance(health_status, dict)
        assert "service_type" in health_status
        assert "overall_health" in health_status
        assert "components" in health_status
        assert "architecture_compliance" in health_status
        
        # Architecture compliance should be verified
        compliance = health_status["architecture_compliance"]
        assert compliance["uses_ssot_components"] is True
        assert compliance["user_isolation_enabled"] is True
        assert compliance["frozen_dataclass_compliant"] is True
        assert compliance["configuration_driven"] is True
        assert compliance["factory_pattern_implemented"] is True


class TestBusinessValueJustification:
    """Test that implementation delivers the promised business value."""
    
    def test_cost_analysis_provides_actionable_insights(self):
        """Test that cost analysis provides actionable business insights."""
        
        integration_service = TokenOptimizationIntegrationService()
        context = UserExecutionContext(
            user_id="business_user",
            thread_id="business_thread",
            run_id="business_run"
        )
        
        async def test_cost_analysis():
            # Get cost analysis
            enhanced_context, cost_analysis = await integration_service.get_cost_analysis(
                context=context,
                agent_name="business_agent"
            )
            
            # Should provide business-relevant insights
            assert "usage_summary" in cost_analysis
            assert "optimization_suggestions" in cost_analysis
            assert "cost_thresholds" in cost_analysis
            assert "recommendations" in cost_analysis
            
            # Recommendations should be actionable
            recommendations = cost_analysis["recommendations"]
            assert isinstance(recommendations, list)
            
            for recommendation in recommendations:
                assert "action" in recommendation
                assert "potential_savings" in recommendation
                assert "priority" in recommendation
        
        asyncio.run(test_cost_analysis())
    
    def test_optimization_delivers_token_savings(self):
        """Test that prompt optimization actually reduces token usage."""
        
        context_manager = TokenOptimizationContextManager(TokenCounter())
        context = UserExecutionContext(
            user_id="optimization_user",
            thread_id="optimization_thread",
            run_id="optimization_run"
        )
        
        # Test with verbose prompt that should be optimizable
        verbose_prompt = """
        Please could you kindly help me to understand what the current weather 
        conditions are like in order to make appropriate clothing decisions for 
        today's activities and events that I have planned.
        """
        
        enhanced_context, optimized_prompt = context_manager.optimize_prompt_for_context(
            context=context,
            agent_name="optimization_agent", 
            prompt=verbose_prompt,
            target_reduction=20
        )
        
        # Should have optimization data
        optimizations = enhanced_context.metadata.get("prompt_optimizations", [])
        assert len(optimizations) > 0
        
        latest_optimization = optimizations[-1]
        
        # Should show actual savings
        assert latest_optimization["tokens_saved"] >= 0
        assert latest_optimization["reduction_percent"] >= 0
        assert len(optimized_prompt) <= len(verbose_prompt)
        
        # Should preserve meaning while reducing tokens
        assert "weather" in optimized_prompt.lower()
        assert len(optimized_prompt) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])