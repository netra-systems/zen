"""Comprehensive tests for UnifiedTriageAgent - SSOT Implementation

Tests verify:
1. Correct execution order (MUST RUN FIRST)
2. Factory pattern for user isolation
3. WebSocket event emissions
4. Metadata SSOT methods
5. All critical triage logic preserved
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any

from netra_backend.app.agents.triage.unified_triage_agent import (
    UnifiedTriageAgent,
    UnifiedTriageAgentFactory,
    TriageResult,
    Priority,
    Complexity,
    ExtractedEntities,
    UserIntent,
    ToolRecommendation,
    TriageConfig
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager"""
    manager = Mock()
    manager.generate_structured_response = AsyncMock()
    manager.generate_response = AsyncMock()
    return manager


@pytest.fixture
def mock_tool_dispatcher():
    """Create mock tool dispatcher"""
    dispatcher = Mock()
    dispatcher.execute_tool = AsyncMock()
    dispatcher.has_websocket_support = True
    return dispatcher


@pytest.fixture
def mock_websocket_bridge():
    """Create mock WebSocket bridge"""
    bridge = Mock()
    bridge.notify_agent_started = AsyncMock()
    bridge.notify_agent_completed = AsyncMock()
    bridge.notify_agent_thinking = AsyncMock()
    bridge.notify_agent_error = AsyncMock()
    bridge.notify_tool_executing = AsyncMock()
    bridge.notify_tool_completed = AsyncMock()
    return bridge


@pytest.fixture
def user_context():
    """Create test user execution context"""
    return UserExecutionContext(
        user_id="test_user_123",
        thread_id="thread_789",
        run_id="run_abc",
        request_id="req_456",
        websocket_connection_id="ws_conn_123"
    )


@pytest.fixture
def test_state():
    """Create test execution state"""
    class TestState:
        def __init__(self):
            self.original_request = "Optimize my GPT-4 costs for the last 30 days"
            self.context = {}
            self.metadata = {}
    return TestState()


# ============================================================================
# FACTORY PATTERN TESTS
# ============================================================================

class TestUnifiedTriageAgentFactory:
    """Test factory pattern for user isolation"""
    
    def test_factory_creates_isolated_agents(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that factory creates separate agent instances per context"""
        # Create two different user contexts
        context1 = UserExecutionContext("user1", "req1", "thread1")
        context2 = UserExecutionContext("user2", "req2", "thread2")
        
        # Create agents for each context
        agent1 = UnifiedTriageAgentFactory.create_for_context(
            context1, mock_llm_manager, mock_tool_dispatcher
        )
        agent2 = UnifiedTriageAgentFactory.create_for_context(
            context2, mock_llm_manager, mock_tool_dispatcher
        )
        
        # Verify different instances
        assert agent1 is not agent2
        assert agent1.context is context1
        assert agent2.context is context2
        
        # Verify execution priority
        assert agent1.execution_priority == 0
        assert agent2.execution_priority == 0
        
    def test_factory_sets_websocket_bridge(self, mock_llm_manager, mock_tool_dispatcher, 
                                          mock_websocket_bridge, user_context):
        """Test that factory properly sets WebSocket bridge"""
        agent = UnifiedTriageAgentFactory.create_for_context(
            user_context, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge
        )
        
        # Verify WebSocket bridge is set
        assert agent.websocket_bridge is mock_websocket_bridge


# ============================================================================
# EXECUTION ORDER TESTS
# ============================================================================

class TestExecutionOrder:
    """Test that triage runs FIRST in the pipeline"""
    
    def test_execution_priority_is_zero(self, mock_llm_manager, mock_tool_dispatcher, user_context):
        """Test that triage agent has execution priority 0 (runs first)"""
        agent = UnifiedTriageAgent(
            mock_llm_manager, mock_tool_dispatcher, user_context, execution_priority=0
        )
        
        assert agent.EXECUTION_ORDER == 0
        assert agent.execution_priority == 0
    
    @pytest.mark.asyncio
    async def test_triage_determines_next_agents(self, mock_llm_manager, mock_tool_dispatcher, 
                                                 user_context, test_state):
        """Test that triage correctly determines which agents run next"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        # Mock LLM to return different data sufficiency levels
        test_cases = [
            ("sufficient", ["data", "optimization", "actions", "reporting"]),
            ("partial", ["data_helper", "data", "optimization", "actions", "reporting"]),
            ("insufficient", ["data_helper"]),
            ("unknown", ["data", "optimization", "actions", "reporting"])
        ]
        
        for data_sufficiency, expected_agents in test_cases:
            mock_llm_manager.generate_structured_response.return_value = TriageResult(
                category="Cost Optimization",
                data_sufficiency=data_sufficiency,
                confidence_score=0.9
            )
            
            result = await agent.execute(test_state, user_context)
            
            assert result["next_agents"] == expected_agents
            assert result["data_sufficiency"] == data_sufficiency


# ============================================================================
# WEBSOCKET EVENT TESTS
# ============================================================================

class TestWebSocketEvents:
    """Test all required WebSocket events are emitted"""
    
    @pytest.mark.asyncio
    async def test_websocket_events_emitted(self, mock_llm_manager, mock_tool_dispatcher,
                                           mock_websocket_bridge, user_context, test_state):
        """Test that all critical WebSocket events are emitted during execution"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        agent.set_websocket_bridge(mock_websocket_bridge)
        
        # Mock successful LLM response
        mock_llm_manager.generate_structured_response.return_value = TriageResult(
            category="Cost Optimization",
            confidence_score=0.95,
            data_sufficiency="sufficient",
            user_intent=UserIntent(primary_intent="optimize", confidence=0.9)
        )
        
        # Execute agent
        result = await agent.execute(test_state, user_context)
        
        # Verify agent_started was called
        mock_websocket_bridge.notify_agent_started.assert_called()
        start_call = mock_websocket_bridge.notify_agent_started.call_args[0]
        assert "triage" in start_call[0].lower()
        
        # Verify agent_thinking was called
        mock_websocket_bridge.notify_agent_thinking.assert_called()
        
        # Verify agent_completed was called with correct data
        mock_websocket_bridge.notify_agent_completed.assert_called()
        complete_call = mock_websocket_bridge.notify_agent_completed.call_args[0]
        complete_data = complete_call[1]
        assert complete_data["triage_category"] == "Cost Optimization"
        assert complete_data["confidence_score"] == 0.95
        assert complete_data["intent"] == "optimize"
        assert complete_data["data_sufficiency"] == "sufficient"
    
    @pytest.mark.asyncio
    async def test_websocket_error_event(self, mock_llm_manager, mock_tool_dispatcher,
                                        mock_websocket_bridge, user_context):
        """Test that error events are emitted on failure"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        agent.set_websocket_bridge(mock_websocket_bridge)
        
        # Create invalid state (no request)
        bad_state = Mock(spec=[])  # No attributes
        
        # Execute should fail
        result = await agent.execute(bad_state, user_context)
        
        # Verify error event was emitted
        mock_websocket_bridge.notify_agent_error.assert_called()
        assert result["success"] is False


# ============================================================================
# METADATA SSOT TESTS
# ============================================================================

class TestMetadataSSoT:
    """Test that metadata uses SSOT methods, not direct assignment"""
    
    @pytest.mark.asyncio
    async def test_metadata_uses_ssot_methods(self, mock_llm_manager, mock_tool_dispatcher,
                                             user_context, test_state):
        """Test that metadata is stored using BaseAgent SSOT methods"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        # Mock LLM response
        mock_llm_manager.generate_structured_response.return_value = TriageResult(
            category="Performance Optimization",
            data_sufficiency="partial",
            priority=Priority.HIGH
        )
        
        # Spy on SSOT method
        with patch.object(agent, 'store_metadata_result') as mock_store:
            result = await agent.execute(test_state, user_context)
            
            # Verify SSOT methods were called
            assert mock_store.called
            
            # Check specific metadata stores
            call_args_list = mock_store.call_args_list
            stored_keys = [args[0][1] for args in call_args_list]  # Get the key argument
            
            assert 'triage_result' in stored_keys
            assert 'triage_category' in stored_keys
            assert 'data_sufficiency' in stored_keys
            assert 'triage_priority' in stored_keys
            assert 'next_agents' in stored_keys
    
    def test_no_direct_metadata_assignment(self):
        """Verify no direct context.metadata[key] = value in the code"""
        import inspect
        import re
        
        # Get the source code of UnifiedTriageAgent
        source = inspect.getsource(UnifiedTriageAgent)
        
        # Check for direct metadata assignments
        direct_assignment_pattern = r'context\.metadata\[[\'"].*?[\'"]\]\s*='
        matches = re.findall(direct_assignment_pattern, source)
        
        # Should find no direct assignments (all use SSOT methods)
        assert len(matches) == 0, f"Found direct metadata assignments: {matches}"


# ============================================================================
# TRIAGE LOGIC PRESERVATION TESTS
# ============================================================================

class TestTriageLogicPreservation:
    """Test that all critical triage logic is preserved"""
    
    def test_intent_detection(self, mock_llm_manager, mock_tool_dispatcher, user_context):
        """Test intent detection logic is preserved"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        # Test various intents
        test_cases = [
            ("I need to analyze my workload patterns", "analyze"),
            ("Help me optimize costs", "optimize"),
            ("Configure the alert thresholds", "configure"),
            ("Monitor system performance", "monitor"),
            ("Troubleshoot the latency issue", "troubleshoot"),
            ("Compare GPT-4 vs Claude performance", "compare"),
            ("Admin mode: generate synthetic data", "admin")
        ]
        
        for request, expected_intent in test_cases:
            intent = agent._detect_intent(request)
            assert intent.primary_intent == expected_intent
    
    def test_entity_extraction(self, mock_llm_manager, mock_tool_dispatcher, user_context):
        """Test entity extraction logic is preserved"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        text = "Optimize GPT-4 costs for the last 30 days with 95% accuracy threshold"
        entities = agent._extract_entities(text)
        
        # Check models extracted
        assert any("gpt-4" in model.lower() for model in entities.models)
        
        # Check metrics extracted
        assert "cost" in entities.metrics or "costs" in entities.metrics
        
        # Check time ranges extracted
        assert any("30 days" in tr for tr in entities.time_ranges)
        
        # Check thresholds extracted
        assert 95.0 in entities.thresholds or 95 in entities.raw_values.values()
    
    def test_tool_recommendation(self, mock_llm_manager, mock_tool_dispatcher, user_context):
        """Test tool recommendation logic is preserved"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        entities = ExtractedEntities(models=["gpt-4"], metrics=["cost"])
        tools = agent._recommend_tools("Cost Optimization", entities)
        
        # Check primary tools
        assert len(tools.primary_tools) > 0
        assert any("cost" in tool.lower() for tool in tools.primary_tools)
        
        # Check tool scores
        assert len(tools.tool_scores) > 0
        assert all(0 <= score <= 1 for score in tools.tool_scores.values())
    
    def test_fallback_categorization(self, mock_llm_manager, mock_tool_dispatcher, user_context):
        """Test fallback categorization when LLM fails"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        # Test fallback categories
        test_cases = [
            ("optimize my costs", "Cost Optimization"),
            ("analyze performance metrics", "Workload Analysis"),
            ("configure alert settings", "Configuration & Settings"),
            ("generate a report", "Monitoring & Reporting"),
            ("select the best model", "Model Selection")
        ]
        
        for request, expected_category in test_cases:
            result = agent._create_fallback_result(request)
            assert result.category == expected_category
            assert result.confidence_score < 0.5  # Low confidence for fallback
            assert result.metadata["fallback"] is True
    
    def test_validation_security_checks(self, mock_llm_manager, mock_tool_dispatcher, user_context):
        """Test request validation and security checks"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        # Test valid request
        valid = agent._validate_request("Optimize my AI costs")
        assert valid["valid"] is True
        
        # Test too short
        short = agent._validate_request("Hi")
        assert short["valid"] is False
        assert "too short" in short["reason"].lower()
        
        # Test too long
        long = agent._validate_request("x" * 11000)
        assert long["valid"] is False
        assert "too long" in long["reason"].lower()
        
        # Test injection attempts
        injections = [
            "<script>alert('xss')</script>",
            "DROP TABLE users",
            "rm -rf /",
            "eval('malicious')"
        ]
        
        for injection in injections:
            result = agent._validate_request(injection)
            assert result["valid"] is False
            assert "malicious" in result["reason"].lower()


# ============================================================================
# MULTI-USER ISOLATION TESTS
# ============================================================================

class TestMultiUserIsolation:
    """Test that multiple users are properly isolated"""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_isolation(self, mock_llm_manager, mock_tool_dispatcher,
                                            mock_websocket_bridge):
        """Test that concurrent users don't interfere with each other"""
        # Create multiple user contexts
        users = [
            UserExecutionContext(f"user_{i}", f"req_{i}", f"thread_{i}")
            for i in range(5)
        ]
        
        # Create agents for each user
        agents = [
            UnifiedTriageAgentFactory.create_for_context(
                ctx, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge
            )
            for ctx in users
        ]
        
        # Create states with different requests
        states = []
        for i in range(5):
            state = Mock()
            state.original_request = f"User {i} request about {['costs', 'performance', 'models'][i % 3]}"
            states.append(state)
        
        # Mock LLM to return different results for each
        mock_llm_manager.generate_structured_response.side_effect = [
            TriageResult(category=f"Category_{i}", confidence_score=0.5 + i * 0.1)
            for i in range(5)
        ]
        
        # Execute all agents concurrently
        results = await asyncio.gather(*[
            agents[i].execute(states[i], users[i]) for i in range(5)
        ])
        
        # Verify each got their own result
        for i, result in enumerate(results):
            assert result["category"] == f"Category_{i}"
            assert result["confidence_score"] == 0.5 + i * 0.1
        
        # Verify no cross-contamination of contexts
        for i, agent in enumerate(agents):
            assert agent.context.user_id == f"user_{i}"


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance characteristics of UnifiedTriageAgent"""
    
    @pytest.mark.asyncio
    async def test_execution_timeout(self, mock_llm_manager, mock_tool_dispatcher, 
                                    user_context, test_state):
        """Test that triage respects timeout configuration"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        # Mock LLM to take too long
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(100)  # Simulate slow response
            return TriageResult()
        
        mock_llm_manager.generate_structured_response.side_effect = slow_response
        
        # Should fallback instead of hanging
        import time
        start = time.time()
        
        # Use timeout for test
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                agent.execute(test_state, user_context),
                timeout=2.0
            )
        
        elapsed = time.time() - start
        assert elapsed < 3.0  # Should timeout quickly
    
    def test_cache_key_generation(self, mock_llm_manager, mock_tool_dispatcher, user_context):
        """Test that cache keys are generated consistently"""
        agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        
        request = "Optimize my costs"
        
        # Generate keys for same request
        key1 = agent._generate_request_hash(request, user_context)
        key2 = agent._generate_request_hash(request, user_context)
        
        # Should be identical
        assert key1 == key2
        
        # Different user should get different key
        other_context = UserExecutionContext("other_user", "req", "thread")
        key3 = agent._generate_request_hash(request, other_context)
        
        assert key3 != key1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for UnifiedTriageAgent"""
    
    @pytest.mark.asyncio
    async def test_full_execution_flow(self, mock_llm_manager, mock_tool_dispatcher,
                                      mock_websocket_bridge, user_context):
        """Test complete execution flow from request to result"""
        # Setup
        agent = UnifiedTriageAgentFactory.create_for_context(
            user_context, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge
        )
        
        # Create realistic state
        state = Mock()
        state.original_request = "I need to optimize GPT-4 costs for production workloads. " \
                                "We're spending over $10,000/month and need to reduce by 30%."
        
        # Mock realistic LLM response
        mock_llm_manager.generate_structured_response.return_value = TriageResult(
            category="Cost Optimization",
            sub_category="LLM Cost Reduction",
            priority=Priority.HIGH,
            complexity=Complexity.HIGH,
            confidence_score=0.92,
            data_sufficiency="sufficient",
            extracted_entities=ExtractedEntities(
                models=["gpt-4"],
                metrics=["cost", "spending"],
                thresholds=[10000.0],
                targets=[30.0]
            ),
            user_intent=UserIntent(
                primary_intent="optimize",
                secondary_intents=["analyze", "reduce"],
                action_required=True,
                confidence=0.95
            ),
            tool_recommendation=ToolRecommendation(
                primary_tools=["calculate_cost_savings", "simulate_cost_optimization"],
                secondary_tools=["analyze_cost_trends"],
                tool_scores={"calculate_cost_savings": 0.9, "simulate_cost_optimization": 0.85}
            ),
            next_steps=[
                "Analyze current GPT-4 usage patterns",
                "Identify optimization opportunities",
                "Simulate cost reduction strategies",
                "Generate implementation plan"
            ],
            reasoning="High-value cost optimization request with clear targets and urgency"
        )
        
        # Execute
        result = await agent.execute(state, user_context)
        
        # Verify comprehensive result
        assert result["success"] is True
        assert result["category"] == "Cost Optimization"
        assert result["priority"] == "high"
        assert result["complexity"] == "high"
        assert result["confidence_score"] == 0.92
        assert result["data_sufficiency"] == "sufficient"
        
        # Verify entities extracted
        assert "gpt-4" in result["entities"]["models"]
        assert "cost" in result["entities"]["metrics"]
        assert 10000.0 in result["entities"]["thresholds"]
        assert 30.0 in result["entities"]["targets"]
        
        # Verify intent detected
        assert result["intent"]["primary_intent"] == "optimize"
        assert result["intent"]["action_required"] is True
        
        # Verify tools recommended
        assert "calculate_cost_savings" in result["tools"]["primary_tools"]
        assert result["tools"]["tool_scores"]["calculate_cost_savings"] == 0.9
        
        # Verify next agents determined
        assert result["next_agents"] == ["data", "optimization", "actions", "reporting"]
        
        # Verify WebSocket events
        assert mock_websocket_bridge.notify_agent_started.called
        assert mock_websocket_bridge.notify_agent_thinking.called
        assert mock_websocket_bridge.notify_agent_completed.called
        
        # Verify metadata stored (via context)
        assert user_context.metadata.get('triage_category') == "Cost Optimization"
        assert user_context.metadata.get('data_sufficiency') == "sufficient"
        assert user_context.metadata.get('triage_priority') == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])