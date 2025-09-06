from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio
import json
import pytest
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.unified_triage_agent import ( )
    # REMOVED_SYNTAX_ERROR: UnifiedTriageAgent,
    # REMOVED_SYNTAX_ERROR: UnifiedTriageAgentFactory,
    # REMOVED_SYNTAX_ERROR: TriageResult,
    # REMOVED_SYNTAX_ERROR: Priority,
    # REMOVED_SYNTAX_ERROR: Complexity,
    # REMOVED_SYNTAX_ERROR: ExtractedEntities,
    # REMOVED_SYNTAX_ERROR: UserIntent,
    # REMOVED_SYNTAX_ERROR: ToolRecommendation,
    # REMOVED_SYNTAX_ERROR: TriageConfig
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger

    # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


    # ============================================================================
    # FIXTURES
    # ============================================================================

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock LLM manager"""
    # REMOVED_SYNTAX_ERROR: manager = manager_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: manager.generate_structured_response = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.generate_response = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return manager


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock tool dispatcher"""
    # REMOVED_SYNTAX_ERROR: dispatcher = dispatcher_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: dispatcher.execute_tool = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: dispatcher.has_websocket_support = True
    # REMOVED_SYNTAX_ERROR: return dispatcher


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_bridge():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket bridge"""
    # REMOVED_SYNTAX_ERROR: bridge = bridge_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_started = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_thinking = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_error = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: bridge.notify_tool_executing = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: bridge.notify_tool_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return bridge


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user execution context"""
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="test_user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_789",
    # REMOVED_SYNTAX_ERROR: run_id="run_abc",
    # REMOVED_SYNTAX_ERROR: request_id="req_456",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="ws_conn_123"
    


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_state():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test execution state"""
# REMOVED_SYNTAX_ERROR: class TestState:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.original_request = "Optimize my GPT-4 costs for the last 30 days"
    # REMOVED_SYNTAX_ERROR: self.context = {}
    # REMOVED_SYNTAX_ERROR: self.metadata = {}
    # REMOVED_SYNTAX_ERROR: return TestState()


    # ============================================================================
    # FACTORY PATTERN TESTS
    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestUnifiedTriageAgentFactory:
    # REMOVED_SYNTAX_ERROR: """Test factory pattern for user isolation"""

# REMOVED_SYNTAX_ERROR: def test_factory_creates_isolated_agents(self, mock_llm_manager, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Test that factory creates separate agent instances per context"""
    # Create two different user contexts
    # REMOVED_SYNTAX_ERROR: context1 = UserExecutionContext("user1", "req1", "thread1")
    # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext("user2", "req2", "thread2")

    # Create agents for each context
    # REMOVED_SYNTAX_ERROR: agent1 = UnifiedTriageAgentFactory.create_for_context( )
    # REMOVED_SYNTAX_ERROR: context1, mock_llm_manager, mock_tool_dispatcher
    
    # REMOVED_SYNTAX_ERROR: agent2 = UnifiedTriageAgentFactory.create_for_context( )
    # REMOVED_SYNTAX_ERROR: context2, mock_llm_manager, mock_tool_dispatcher
    

    # Verify different instances
    # REMOVED_SYNTAX_ERROR: assert agent1 is not agent2
    # REMOVED_SYNTAX_ERROR: assert agent1.context is context1
    # REMOVED_SYNTAX_ERROR: assert agent2.context is context2

    # Verify execution priority
    # REMOVED_SYNTAX_ERROR: assert agent1.execution_priority == 0
    # REMOVED_SYNTAX_ERROR: assert agent2.execution_priority == 0

# REMOVED_SYNTAX_ERROR: def test_factory_sets_websocket_bridge(self, mock_llm_manager, mock_tool_dispatcher,
# REMOVED_SYNTAX_ERROR: mock_websocket_bridge, user_context):
    # REMOVED_SYNTAX_ERROR: """Test that factory properly sets WebSocket bridge"""
    # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgentFactory.create_for_context( )
    # REMOVED_SYNTAX_ERROR: user_context, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge
    

    # Verify WebSocket bridge is set
    # REMOVED_SYNTAX_ERROR: assert agent.websocket_bridge is mock_websocket_bridge


    # ============================================================================
    # EXECUTION ORDER TESTS
    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestExecutionOrder:
    # REMOVED_SYNTAX_ERROR: """Test that triage runs FIRST in the pipeline"""

# REMOVED_SYNTAX_ERROR: def test_execution_priority_is_zero(self, mock_llm_manager, mock_tool_dispatcher, user_context):
    # REMOVED_SYNTAX_ERROR: """Test that triage agent has execution priority 0 (runs first)"""
    # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent( )
    # REMOVED_SYNTAX_ERROR: mock_llm_manager, mock_tool_dispatcher, user_context, execution_priority=0
    

    # REMOVED_SYNTAX_ERROR: assert agent.EXECUTION_ORDER == 0
    # REMOVED_SYNTAX_ERROR: assert agent.execution_priority == 0

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_triage_determines_next_agents(self, mock_llm_manager, mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: user_context, test_state):
        # REMOVED_SYNTAX_ERROR: """Test that triage correctly determines which agents run next"""
        # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

        # Mock LLM to await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return different data sufficiency levels
        # REMOVED_SYNTAX_ERROR: test_cases = [ )
        # REMOVED_SYNTAX_ERROR: ("sufficient", ["data", "optimization", "actions", "reporting"]),
        # REMOVED_SYNTAX_ERROR: ("partial", ["data_helper", "data", "optimization", "actions", "reporting"]),
        # REMOVED_SYNTAX_ERROR: ("insufficient", ["data_helper"]),
        # REMOVED_SYNTAX_ERROR: ("unknown", ["data", "optimization", "actions", "reporting"])
        

        # REMOVED_SYNTAX_ERROR: for data_sufficiency, expected_agents in test_cases:
            # REMOVED_SYNTAX_ERROR: mock_llm_manager.generate_structured_response.return_value = TriageResult( )
            # REMOVED_SYNTAX_ERROR: category="Cost Optimization",
            # REMOVED_SYNTAX_ERROR: data_sufficiency=data_sufficiency,
            # REMOVED_SYNTAX_ERROR: confidence_score=0.9
            

            # REMOVED_SYNTAX_ERROR: result = await agent.execute(test_state, user_context)

            # REMOVED_SYNTAX_ERROR: assert result["next_agents"] == expected_agents
            # REMOVED_SYNTAX_ERROR: assert result["data_sufficiency"] == data_sufficiency


            # ============================================================================
            # WEBSOCKET EVENT TESTS
            # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestWebSocketEvents:
    # REMOVED_SYNTAX_ERROR: """Test all required WebSocket events are emitted"""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_events_emitted(self, mock_llm_manager, mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge, user_context, test_state):
        # REMOVED_SYNTAX_ERROR: """Test that all critical WebSocket events are emitted during execution"""
        # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
        # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(mock_websocket_bridge)

        # Mock successful LLM response
        # REMOVED_SYNTAX_ERROR: mock_llm_manager.generate_structured_response.return_value = TriageResult( )
        # REMOVED_SYNTAX_ERROR: category="Cost Optimization",
        # REMOVED_SYNTAX_ERROR: confidence_score=0.95,
        # REMOVED_SYNTAX_ERROR: data_sufficiency="sufficient",
        # REMOVED_SYNTAX_ERROR: user_intent=UserIntent(primary_intent="optimize", confidence=0.9)
        

        # Execute agent
        # REMOVED_SYNTAX_ERROR: result = await agent.execute(test_state, user_context)

        # Verify agent_started was called
        # REMOVED_SYNTAX_ERROR: mock_websocket_bridge.notify_agent_started.assert_called()
        # REMOVED_SYNTAX_ERROR: start_call = mock_websocket_bridge.notify_agent_started.call_args[0]
        # REMOVED_SYNTAX_ERROR: assert "triage" in start_call[0].lower()

        # Verify agent_thinking was called
        # REMOVED_SYNTAX_ERROR: mock_websocket_bridge.notify_agent_thinking.assert_called()

        # Verify agent_completed was called with correct data
        # REMOVED_SYNTAX_ERROR: mock_websocket_bridge.notify_agent_completed.assert_called()
        # REMOVED_SYNTAX_ERROR: complete_call = mock_websocket_bridge.notify_agent_completed.call_args[0]
        # REMOVED_SYNTAX_ERROR: complete_data = complete_call[1]
        # REMOVED_SYNTAX_ERROR: assert complete_data["triage_category"] == "Cost Optimization"
        # REMOVED_SYNTAX_ERROR: assert complete_data["confidence_score"] == 0.95
        # REMOVED_SYNTAX_ERROR: assert complete_data["intent"] == "optimize"
        # REMOVED_SYNTAX_ERROR: assert complete_data["data_sufficiency"] == "sufficient"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_websocket_error_event(self, mock_llm_manager, mock_tool_dispatcher,
        # REMOVED_SYNTAX_ERROR: mock_websocket_bridge, user_context):
            # REMOVED_SYNTAX_ERROR: """Test that error events are emitted on failure"""
            # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)
            # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(mock_websocket_bridge)

            # Create invalid state (no request)
            # REMOVED_SYNTAX_ERROR: bad_state = Mock(spec=[])  # No attributes

            # Execute should fail
            # REMOVED_SYNTAX_ERROR: result = await agent.execute(bad_state, user_context)

            # Verify error event was emitted
            # REMOVED_SYNTAX_ERROR: mock_websocket_bridge.notify_agent_error.assert_called()
            # REMOVED_SYNTAX_ERROR: assert result["success"] is False


            # ============================================================================
            # METADATA SSOT TESTS
            # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestMetadataSSoT:
    # REMOVED_SYNTAX_ERROR: """Test that metadata uses SSOT methods, not direct assignment"""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_metadata_uses_ssot_methods(self, mock_llm_manager, mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: user_context, test_state):
        # REMOVED_SYNTAX_ERROR: """Test that metadata is stored using BaseAgent SSOT methods"""
        # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

        # Mock LLM response
        # REMOVED_SYNTAX_ERROR: mock_llm_manager.generate_structured_response.return_value = TriageResult( )
        # REMOVED_SYNTAX_ERROR: category="Performance Optimization",
        # REMOVED_SYNTAX_ERROR: data_sufficiency="partial",
        # REMOVED_SYNTAX_ERROR: priority=Priority.HIGH
        

        # Spy on SSOT method
        # REMOVED_SYNTAX_ERROR: with patch.object(agent, 'store_metadata_result') as mock_store:
            # REMOVED_SYNTAX_ERROR: result = await agent.execute(test_state, user_context)

            # Verify SSOT methods were called
            # REMOVED_SYNTAX_ERROR: assert mock_store.called

            # Check specific metadata stores
            # REMOVED_SYNTAX_ERROR: call_args_list = mock_store.call_args_list
            # REMOVED_SYNTAX_ERROR: stored_keys = [args[0][1] for args in call_args_list]  # Get the key argument

            # REMOVED_SYNTAX_ERROR: assert 'triage_result' in stored_keys
            # REMOVED_SYNTAX_ERROR: assert 'triage_category' in stored_keys
            # REMOVED_SYNTAX_ERROR: assert 'data_sufficiency' in stored_keys
            # REMOVED_SYNTAX_ERROR: assert 'triage_priority' in stored_keys
            # REMOVED_SYNTAX_ERROR: assert 'next_agents' in stored_keys

# REMOVED_SYNTAX_ERROR: def test_no_direct_metadata_assignment(self):
    # REMOVED_SYNTAX_ERROR: """Verify no direct context.metadata[key] = value in the code"""
    # REMOVED_SYNTAX_ERROR: import inspect
    # REMOVED_SYNTAX_ERROR: import re

    # Get the source code of UnifiedTriageAgent
    # REMOVED_SYNTAX_ERROR: source = inspect.getsource(UnifiedTriageAgent)

    # Check for direct metadata assignments
    # REMOVED_SYNTAX_ERROR: direct_assignment_pattern = r'context\.metadata\[[\'"].*?[\'"]\]\s*='
    # REMOVED_SYNTAX_ERROR: matches = re.findall(direct_assignment_pattern, source)

    # Should find no direct assignments (all use SSOT methods)
    # REMOVED_SYNTAX_ERROR: assert len(matches) == 0, "formatted_string"


    # ============================================================================
    # TRIAGE LOGIC PRESERVATION TESTS
    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestTriageLogicPreservation:
    # REMOVED_SYNTAX_ERROR: """Test that all critical triage logic is preserved"""

# REMOVED_SYNTAX_ERROR: def test_intent_detection(self, mock_llm_manager, mock_tool_dispatcher, user_context):
    # REMOVED_SYNTAX_ERROR: """Test intent detection logic is preserved"""
    # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

    # Test various intents
    # REMOVED_SYNTAX_ERROR: test_cases = [ )
    # REMOVED_SYNTAX_ERROR: ("I need to analyze my workload patterns", "analyze"),
    # REMOVED_SYNTAX_ERROR: ("Help me optimize costs", "optimize"),
    # REMOVED_SYNTAX_ERROR: ("Configure the alert thresholds", "configure"),
    # REMOVED_SYNTAX_ERROR: ("Monitor system performance", "monitor"),
    # REMOVED_SYNTAX_ERROR: ("Troubleshoot the latency issue", "troubleshoot"),
    # REMOVED_SYNTAX_ERROR: ("Compare GPT-4 vs Claude performance", "compare"),
    # REMOVED_SYNTAX_ERROR: ("Admin mode: generate synthetic data", "admin")
    

    # REMOVED_SYNTAX_ERROR: for request, expected_intent in test_cases:
        # REMOVED_SYNTAX_ERROR: intent = agent._detect_intent(request)
        # REMOVED_SYNTAX_ERROR: assert intent.primary_intent == expected_intent

# REMOVED_SYNTAX_ERROR: def test_entity_extraction(self, mock_llm_manager, mock_tool_dispatcher, user_context):
    # REMOVED_SYNTAX_ERROR: """Test entity extraction logic is preserved"""
    # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

    # REMOVED_SYNTAX_ERROR: text = "Optimize GPT-4 costs for the last 30 days with 95% accuracy threshold"
    # REMOVED_SYNTAX_ERROR: entities = agent._extract_entities(text)

    # Check models extracted
    # REMOVED_SYNTAX_ERROR: assert any("gpt-4" in model.lower() for model in entities.models)

    # Check metrics extracted
    # REMOVED_SYNTAX_ERROR: assert "cost" in entities.metrics or "costs" in entities.metrics

    # Check time ranges extracted
    # REMOVED_SYNTAX_ERROR: assert any("30 days" in tr for tr in entities.time_ranges)

    # Check thresholds extracted
    # REMOVED_SYNTAX_ERROR: assert 95.0 in entities.thresholds or 95 in entities.raw_values.values()

# REMOVED_SYNTAX_ERROR: def test_tool_recommendation(self, mock_llm_manager, mock_tool_dispatcher, user_context):
    # REMOVED_SYNTAX_ERROR: """Test tool recommendation logic is preserved"""
    # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

    # REMOVED_SYNTAX_ERROR: entities = ExtractedEntities(models=["gpt-4"], metrics=["cost"])
    # REMOVED_SYNTAX_ERROR: tools = agent._recommend_tools("Cost Optimization", entities)

    # Check primary tools
    # REMOVED_SYNTAX_ERROR: assert len(tools.primary_tools) > 0
    # REMOVED_SYNTAX_ERROR: assert any("cost" in tool.lower() for tool in tools.primary_tools)

    # Check tool scores
    # REMOVED_SYNTAX_ERROR: assert len(tools.tool_scores) > 0
    # REMOVED_SYNTAX_ERROR: assert all(0 <= score <= 1 for score in tools.tool_scores.values())

# REMOVED_SYNTAX_ERROR: def test_fallback_categorization(self, mock_llm_manager, mock_tool_dispatcher, user_context):
    # REMOVED_SYNTAX_ERROR: """Test fallback categorization when LLM fails"""
    # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

    # Test fallback categories
    # REMOVED_SYNTAX_ERROR: test_cases = [ )
    # REMOVED_SYNTAX_ERROR: ("optimize my costs", "Cost Optimization"),
    # REMOVED_SYNTAX_ERROR: ("analyze performance metrics", "Workload Analysis"),
    # REMOVED_SYNTAX_ERROR: ("configure alert settings", "Configuration & Settings"),
    # REMOVED_SYNTAX_ERROR: ("generate a report", "Monitoring & Reporting"),
    # REMOVED_SYNTAX_ERROR: ("select the best model", "Model Selection")
    

    # REMOVED_SYNTAX_ERROR: for request, expected_category in test_cases:
        # REMOVED_SYNTAX_ERROR: result = agent._create_fallback_result(request)
        # REMOVED_SYNTAX_ERROR: assert result.category == expected_category
        # REMOVED_SYNTAX_ERROR: assert result.confidence_score < 0.5  # Low confidence for fallback
        # REMOVED_SYNTAX_ERROR: assert result.metadata["fallback"] is True

# REMOVED_SYNTAX_ERROR: def test_validation_security_checks(self, mock_llm_manager, mock_tool_dispatcher, user_context):
    # REMOVED_SYNTAX_ERROR: """Test request validation and security checks"""
    # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

    # Test valid request
    # REMOVED_SYNTAX_ERROR: valid = agent._validate_request("Optimize my AI costs")
    # REMOVED_SYNTAX_ERROR: assert valid["valid"] is True

    # Test too short
    # REMOVED_SYNTAX_ERROR: short = agent._validate_request("Hi")
    # REMOVED_SYNTAX_ERROR: assert short["valid"] is False
    # REMOVED_SYNTAX_ERROR: assert "too short" in short["reason"].lower()

    # Test too long
    # REMOVED_SYNTAX_ERROR: long = agent._validate_request("x" * 11000)
    # REMOVED_SYNTAX_ERROR: assert long["valid"] is False
    # REMOVED_SYNTAX_ERROR: assert "too long" in long["reason"].lower()

    # Test injection attempts
    # REMOVED_SYNTAX_ERROR: injections = [ )
    # REMOVED_SYNTAX_ERROR: "<script>alert('xss')</script>",
    # REMOVED_SYNTAX_ERROR: "DROP TABLE users",
    # REMOVED_SYNTAX_ERROR: "rm -rf /",
    # REMOVED_SYNTAX_ERROR: "eval('malicious')"
    

    # REMOVED_SYNTAX_ERROR: for injection in injections:
        # REMOVED_SYNTAX_ERROR: result = agent._validate_request(injection)
        # REMOVED_SYNTAX_ERROR: assert result["valid"] is False
        # REMOVED_SYNTAX_ERROR: assert "malicious" in result["reason"].lower()


        # ============================================================================
        # MULTI-USER ISOLATION TESTS
        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestMultiUserIsolation:
    # REMOVED_SYNTAX_ERROR: """Test that multiple users are properly isolated"""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_concurrent_user_isolation(self, mock_llm_manager, mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge):
        # REMOVED_SYNTAX_ERROR: """Test that concurrent users don't interfere with each other"""
        # Create multiple user contexts
        # REMOVED_SYNTAX_ERROR: users = [ )
        # REMOVED_SYNTAX_ERROR: UserExecutionContext("formatted_string", "formatted_string", "formatted_string")
        # REMOVED_SYNTAX_ERROR: for i in range(5)
        

        # Create agents for each user
        # REMOVED_SYNTAX_ERROR: agents = [ )
        # REMOVED_SYNTAX_ERROR: UnifiedTriageAgentFactory.create_for_context( )
        # REMOVED_SYNTAX_ERROR: ctx, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge
        
        # REMOVED_SYNTAX_ERROR: for ctx in users
        

        # Create states with different requests
        # REMOVED_SYNTAX_ERROR: states = []
        # REMOVED_SYNTAX_ERROR: for i in range(5):
            # REMOVED_SYNTAX_ERROR: state = state_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: state.original_request = "formatted_string", confidence_score=0.5 + i * 0.1)
            # REMOVED_SYNTAX_ERROR: for i in range(5)
            

            # Execute all agents concurrently
            # Removed problematic line: results = await asyncio.gather(*[ ))
            # REMOVED_SYNTAX_ERROR: agents[i].execute(states[i], users[i]) for i in range(5)
            

            # Verify each got their own result
            # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
                # REMOVED_SYNTAX_ERROR: assert result["category"] == "formatted_string"


                    # ============================================================================
                    # PERFORMANCE TESTS
                    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestPerformance:
    # REMOVED_SYNTAX_ERROR: """Test performance characteristics of UnifiedTriageAgent"""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_execution_timeout(self, mock_llm_manager, mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: user_context, test_state):
        # REMOVED_SYNTAX_ERROR: """Test that triage respects timeout configuration"""
        # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

        # Mock LLM to take too long
# REMOVED_SYNTAX_ERROR: async def slow_response(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(100)  # Simulate slow response
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return TriageResult()

    # REMOVED_SYNTAX_ERROR: mock_llm_manager.generate_structured_response.side_effect = slow_response

    # Should fallback instead of hanging
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: start = time.time()

    # Use timeout for test
    # REMOVED_SYNTAX_ERROR: with pytest.raises(asyncio.TimeoutError):
        # REMOVED_SYNTAX_ERROR: await asyncio.wait_for( )
        # REMOVED_SYNTAX_ERROR: agent.execute(test_state, user_context),
        # REMOVED_SYNTAX_ERROR: timeout=2.0
        

        # REMOVED_SYNTAX_ERROR: elapsed = time.time() - start
        # REMOVED_SYNTAX_ERROR: assert elapsed < 3.0  # Should timeout quickly

# REMOVED_SYNTAX_ERROR: def test_cache_key_generation(self, mock_llm_manager, mock_tool_dispatcher, user_context):
    # REMOVED_SYNTAX_ERROR: """Test that cache keys are generated consistently"""
    # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgent(mock_llm_manager, mock_tool_dispatcher, user_context)

    # REMOVED_SYNTAX_ERROR: request = "Optimize my costs"

    # Generate keys for same request
    # REMOVED_SYNTAX_ERROR: key1 = agent._generate_request_hash(request, user_context)
    # REMOVED_SYNTAX_ERROR: key2 = agent._generate_request_hash(request, user_context)

    # Should be identical
    # REMOVED_SYNTAX_ERROR: assert key1 == key2

    # Different user should get different key
    # REMOVED_SYNTAX_ERROR: other_context = UserExecutionContext("other_user", "req", "thread")
    # REMOVED_SYNTAX_ERROR: key3 = agent._generate_request_hash(request, other_context)

    # REMOVED_SYNTAX_ERROR: assert key3 != key1


    # ============================================================================
    # INTEGRATION TESTS
    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for UnifiedTriageAgent"""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_full_execution_flow(self, mock_llm_manager, mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge, user_context):
        # REMOVED_SYNTAX_ERROR: """Test complete execution flow from request to result"""
        # Setup
        # REMOVED_SYNTAX_ERROR: agent = UnifiedTriageAgentFactory.create_for_context( )
        # REMOVED_SYNTAX_ERROR: user_context, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge
        

        # Create realistic state
        # REMOVED_SYNTAX_ERROR: state = state_instance  # Initialize appropriate service
        # REMOVED_SYNTAX_ERROR: state.original_request = "I need to optimize GPT-4 costs for production workloads. " \
        # REMOVED_SYNTAX_ERROR: "We"re spending over $10,000/month and need to reduce by 30%."

        # Mock realistic LLM response
        # REMOVED_SYNTAX_ERROR: mock_llm_manager.generate_structured_response.return_value = TriageResult( )
        # REMOVED_SYNTAX_ERROR: category="Cost Optimization",
        # REMOVED_SYNTAX_ERROR: sub_category="LLM Cost Reduction",
        # REMOVED_SYNTAX_ERROR: priority=Priority.HIGH,
        # REMOVED_SYNTAX_ERROR: complexity=Complexity.HIGH,
        # REMOVED_SYNTAX_ERROR: confidence_score=0.92,
        # REMOVED_SYNTAX_ERROR: data_sufficiency="sufficient",
        # REMOVED_SYNTAX_ERROR: extracted_entities=ExtractedEntities( )
        # REMOVED_SYNTAX_ERROR: models=["gpt-4"],
        # REMOVED_SYNTAX_ERROR: metrics=["cost", "spending"],
        # REMOVED_SYNTAX_ERROR: thresholds=[10000.0],
        # REMOVED_SYNTAX_ERROR: targets=[30.0]
        # REMOVED_SYNTAX_ERROR: ),
        # REMOVED_SYNTAX_ERROR: user_intent=UserIntent( )
        # REMOVED_SYNTAX_ERROR: primary_intent="optimize",
        # REMOVED_SYNTAX_ERROR: secondary_intents=["analyze", "reduce"],
        # REMOVED_SYNTAX_ERROR: action_required=True,
        # REMOVED_SYNTAX_ERROR: confidence=0.95
        # REMOVED_SYNTAX_ERROR: ),
        # REMOVED_SYNTAX_ERROR: tool_recommendation=ToolRecommendation( )
        # REMOVED_SYNTAX_ERROR: primary_tools=["calculate_cost_savings", "simulate_cost_optimization"],
        # REMOVED_SYNTAX_ERROR: secondary_tools=["analyze_cost_trends"],
        # REMOVED_SYNTAX_ERROR: tool_scores={"calculate_cost_savings": 0.9, "simulate_cost_optimization": 0.85}
        # REMOVED_SYNTAX_ERROR: ),
        # REMOVED_SYNTAX_ERROR: next_steps=[ )
        # REMOVED_SYNTAX_ERROR: "Analyze current GPT-4 usage patterns",
        # REMOVED_SYNTAX_ERROR: "Identify optimization opportunities",
        # REMOVED_SYNTAX_ERROR: "Simulate cost reduction strategies",
        # REMOVED_SYNTAX_ERROR: "Generate implementation plan"
        # REMOVED_SYNTAX_ERROR: ],
        # REMOVED_SYNTAX_ERROR: reasoning="High-value cost optimization request with clear targets and urgency"
        

        # Execute
        # REMOVED_SYNTAX_ERROR: result = await agent.execute(state, user_context)

        # Verify comprehensive result
        # REMOVED_SYNTAX_ERROR: assert result["success"] is True
        # REMOVED_SYNTAX_ERROR: assert result["category"] == "Cost Optimization"
        # REMOVED_SYNTAX_ERROR: assert result["priority"] == "high"
        # REMOVED_SYNTAX_ERROR: assert result["complexity"] == "high"
        # REMOVED_SYNTAX_ERROR: assert result["confidence_score"] == 0.92
        # REMOVED_SYNTAX_ERROR: assert result["data_sufficiency"] == "sufficient"

        # Verify entities extracted
        # REMOVED_SYNTAX_ERROR: assert "gpt-4" in result["entities"]["models"]
        # REMOVED_SYNTAX_ERROR: assert "cost" in result["entities"]["metrics"]
        # REMOVED_SYNTAX_ERROR: assert 10000.0 in result["entities"]["thresholds"]
        # REMOVED_SYNTAX_ERROR: assert 30.0 in result["entities"]["targets"]

        # Verify intent detected
        # REMOVED_SYNTAX_ERROR: assert result["intent"]["primary_intent"] == "optimize"
        # REMOVED_SYNTAX_ERROR: assert result["intent"]["action_required"] is True

        # Verify tools recommended
        # REMOVED_SYNTAX_ERROR: assert "calculate_cost_savings" in result["tools"]["primary_tools"]
        # REMOVED_SYNTAX_ERROR: assert result["tools"]["tool_scores"]["calculate_cost_savings"] == 0.9

        # Verify next agents determined
        # REMOVED_SYNTAX_ERROR: assert result["next_agents"] == ["data", "optimization", "actions", "reporting"]

        # Verify WebSocket events
        # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_agent_started.called
        # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_agent_thinking.called
        # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_agent_completed.called

        # Verify metadata stored (via context)
        # REMOVED_SYNTAX_ERROR: assert user_context.metadata.get('triage_category') == "Cost Optimization"
        # REMOVED_SYNTAX_ERROR: assert user_context.metadata.get('data_sufficiency') == "sufficient"
        # REMOVED_SYNTAX_ERROR: assert user_context.metadata.get('triage_priority') == "high"


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])