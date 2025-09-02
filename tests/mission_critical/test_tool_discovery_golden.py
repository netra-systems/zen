"""Mission Critical Test Suite: ToolDiscoverySubAgent Golden Pattern Compliance

CRITICAL: This test suite validates that ToolDiscoverySubAgent follows the golden pattern
and delivers chat value through proper WebSocket events.

Tests cover:
1. BaseAgent inheritance and initialization
2. WebSocket event emission for chat value
3. Tool discovery business logic  
4. Error handling and resilience
5. Golden pattern compliance
"""

import asyncio
import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.agents.tool_discovery_sub_agent import ToolDiscoverySubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle


class TestToolDiscoveryGoldenPattern:
    """Test ToolDiscoverySubAgent golden pattern compliance."""
    
    @pytest.fixture
    def agent(self):
        """Create ToolDiscoverySubAgent instance for testing."""
        return ToolDiscoverySubAgent()
    
    @pytest.fixture
    def mock_context(self):
        """Create mock execution context."""
        context = Mock(spec=ExecutionContext)
        context.run_id = "test_run_123"
        context.stream_updates = True
        context.state = Mock(spec=DeepAgentState)
        context.state.user_request = "I need help optimizing my AI workload costs"
        return context
    
    @pytest.fixture
    def websocket_bridge_mock(self):
        """Create mock WebSocket bridge."""
        bridge = AsyncMock()
        bridge.emit_event = AsyncMock()
        return bridge

    def test_golden_pattern_inheritance(self, agent):
        """Test that agent follows BaseAgent inheritance pattern."""
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # CRITICAL: Must inherit from BaseAgent
        assert isinstance(agent, BaseAgent)
        assert agent.name == "ToolDiscoverySubAgent"
        assert agent.description == "AI-powered tool discovery and recommendation agent"
        
        # CRITICAL: Must have infrastructure enabled
        assert agent._enable_reliability is True
        assert agent._enable_execution_engine is True
        assert agent._enable_caching is True

    def test_initialization_business_logic_only(self, agent):
        """Test that agent initializes only business logic components."""
        # CRITICAL: Should have business logic components
        assert hasattr(agent, 'tool_recommender')
        assert hasattr(agent, 'discovery_cache')
        
        # CRITICAL: Should NOT have infrastructure components (inherited from BaseAgent)
        assert not hasattr(agent, 'websocket_handler')
        assert not hasattr(agent, 'retry_handler')
        assert not hasattr(agent, 'execution_engine_local')

    @pytest.mark.asyncio
    async def test_validate_preconditions_success(self, agent, mock_context):
        """Test successful precondition validation."""
        result = await agent.validate_preconditions(mock_context)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_preconditions_no_request(self, agent, mock_context):
        """Test precondition validation fails with no request."""
        mock_context.state.user_request = None
        
        with patch.object(agent, 'emit_error', new_callable=AsyncMock) as mock_emit_error:
            result = await agent.validate_preconditions(mock_context)
            
            assert result is False
            mock_emit_error.assert_called_once_with(
                "No user request provided for tool discovery",
                error_type="ValidationError"
            )

    @pytest.mark.asyncio
    async def test_validate_preconditions_short_request(self, agent, mock_context):
        """Test precondition validation fails with short request."""
        mock_context.state.user_request = "help"  # Too short
        
        with patch.object(agent, 'emit_error', new_callable=AsyncMock) as mock_emit_error:
            result = await agent.validate_preconditions(mock_context)
            
            assert result is False
            mock_emit_error.assert_called_once_with(
                "User request too short for meaningful tool discovery",
                error_type="ValidationError"
            )


class TestToolDiscoveryWebSocketEvents:
    """Test WebSocket event emission for chat value delivery."""
    
    @pytest.fixture
    def agent(self):
        """Create agent with mocked WebSocket methods."""
        agent = ToolDiscoverySubAgent()
        # Mock WebSocket methods
        agent.emit_thinking = AsyncMock()
        agent.emit_progress = AsyncMock()
        agent.emit_tool_executing = AsyncMock()
        agent.emit_tool_completed = AsyncMock()
        agent.emit_error = AsyncMock()
        return agent
    
    @pytest.fixture
    def mock_context(self):
        """Create mock execution context."""
        context = Mock(spec=ExecutionContext)
        context.run_id = "test_run_456"
        context.stream_updates = True
        context.state = Mock(spec=DeepAgentState)
        context.state.user_request = "I need help analyzing my AI model performance metrics"
        return context

    @pytest.mark.asyncio
    async def test_websocket_events_emission_sequence(self, agent, mock_context):
        """Test that all critical WebSocket events are emitted in correct sequence."""
        
        # Mock internal methods to focus on WebSocket events
        agent._extract_entities_from_request = AsyncMock(return_value=Mock(
            models_mentioned=['model'], metrics_mentioned=['performance']
        ))
        agent._categorize_request = AsyncMock(return_value=["Performance Optimization"])
        agent._discover_tools = AsyncMock(return_value=[
            Mock(tool_name="analyze_performance", relevance_score=0.9)
        ])
        agent._enhance_recommendations = AsyncMock(return_value=[{
            "tool_name": "analyze_performance",
            "relevance_score": 0.9,
            "description": "Test tool"
        }])
        agent._finalize_discovery_result = AsyncMock(return_value={
            "discovered_tools": [{"tool_name": "analyze_performance"}],
            "total_tools_found": 1
        })
        
        # Execute core logic
        result = await agent.execute_core_logic(mock_context)
        
        # CRITICAL: Verify WebSocket events for chat value delivery
        
        # 1. agent_thinking events (reasoning visibility)
        agent.emit_thinking.assert_any_call("Starting intelligent tool discovery for your request...")
        agent.emit_thinking.assert_any_call("Analyzing your request to understand intent and context...")
        agent.emit_thinking.assert_any_call("Categorizing your request to identify relevant tool categories...")
        agent.emit_thinking.assert_any_call("Discovering tools that match your specific needs...")
        agent.emit_thinking.assert_any_call("Finalizing tool discovery results with prioritized recommendations...")
        
        # 2. Progress updates (partial results)
        agent.emit_progress.assert_any_call("Extracting key entities and concepts from your request...")
        agent.emit_progress.assert_any_call("Determining the most appropriate tool categories...")
        agent.emit_progress.assert_any_call("Enhancing recommendations with usage guidance and examples...")
        
        # 3. Tool execution events (transparency)
        agent.emit_tool_executing.assert_called_once_with(
            "tool_recommendation_engine", 
            {"categories": ["Performance Optimization"]}
        )
        agent.emit_tool_completed.assert_called_once_with(
            "tool_recommendation_engine",
            {"found_tools": 1, "categories_analyzed": 1}
        )
        
        # 4. Completion event
        agent.emit_progress.assert_any_call(
            "Tool discovery completed! Found 1 relevant tools.", 
            is_complete=True
        )
        
        # Verify result structure
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio 
    async def test_websocket_error_emission(self, agent, mock_context):
        """Test WebSocket error emission on failure."""
        
        # Force an exception during execution
        agent._extract_entities_from_request = AsyncMock(side_effect=Exception("Test error"))
        
        # Execute and expect validation error
        with pytest.raises(AgentValidationError):
            await agent.execute_core_logic(mock_context)
        
        # Verify error emission
        agent.emit_error.assert_called_once_with(
            "Tool discovery failed: Test error", 
            error_type="DiscoveryError"
        )


class TestToolDiscoveryBusinessLogic:
    """Test tool discovery business logic."""
    
    @pytest.fixture
    def agent(self):
        return ToolDiscoverySubAgent()

    @pytest.mark.asyncio
    async def test_entity_extraction_models(self, agent):
        """Test entity extraction identifies models correctly."""
        request = "I want to compare GPT and Claude models for my use case"
        
        entities = await agent._extract_entities_from_request(request)
        
        assert len(entities.models_mentioned) > 0
        assert len(entities.metrics_mentioned) == 0

    @pytest.mark.asyncio
    async def test_entity_extraction_metrics(self, agent):
        """Test entity extraction identifies metrics correctly."""
        request = "Show me performance metrics and cost analysis for my workload"
        
        entities = await agent._extract_entities_from_request(request)
        
        assert len(entities.models_mentioned) == 0
        assert len(entities.metrics_mentioned) > 0

    @pytest.mark.asyncio
    async def test_request_categorization_cost(self, agent):
        """Test request categorization for cost optimization."""
        request = "Help me reduce costs and save money on my AI infrastructure"
        entities = Mock(models_mentioned=[], metrics_mentioned=[])
        
        categories = await agent._categorize_request(request, entities)
        
        assert "Cost Optimization" in categories

    @pytest.mark.asyncio
    async def test_request_categorization_performance(self, agent):
        """Test request categorization for performance optimization."""
        request = "I need to optimize performance and reduce latency"
        entities = Mock(models_mentioned=[], metrics_mentioned=['performance'])
        
        categories = await agent._categorize_request(request, entities)
        
        assert "Performance Optimization" in categories

    @pytest.mark.asyncio
    async def test_request_categorization_model_selection(self, agent):
        """Test request categorization for model selection."""
        request = "Which model should I choose for my chatbot?"
        entities = Mock(models_mentioned=['model'], metrics_mentioned=[])
        
        categories = await agent._categorize_request(request, entities)
        
        assert "Model Selection" in categories

    @pytest.mark.asyncio
    async def test_request_categorization_default(self, agent):
        """Test request categorization defaults to workload analysis."""
        request = "Generic request with no specific keywords"
        entities = Mock(models_mentioned=[], metrics_mentioned=[])
        
        categories = await agent._categorize_request(request, entities)
        
        assert "Workload Analysis" in categories
        assert len(categories) >= 1

    @pytest.mark.asyncio
    async def test_tool_discovery_removes_duplicates(self, agent):
        """Test tool discovery removes duplicate recommendations."""
        categories = ["Cost Optimization", "Performance Optimization"] 
        entities = Mock(models_mentioned=[], metrics_mentioned=['performance'])
        
        recommendations = await agent._discover_tools(categories, entities)
        
        # Check for duplicates
        tool_names = [rec.tool_name for rec in recommendations]
        assert len(tool_names) == len(set(tool_names))  # No duplicates
        
        # Should be sorted by relevance
        relevance_scores = [rec.relevance_score for rec in recommendations]
        assert relevance_scores == sorted(relevance_scores, reverse=True)

    @pytest.mark.asyncio
    async def test_recommendation_enhancement(self, agent):
        """Test recommendation enhancement adds guidance."""
        recommendations = [Mock(
            tool_name="analyze_performance",
            relevance_score=0.9,
            parameters={}
        )]
        user_request = "I need performance analysis"
        
        enhanced = await agent._enhance_recommendations(recommendations, user_request)
        
        assert len(enhanced) == 1
        enhanced_rec = enhanced[0]
        
        assert enhanced_rec["tool_name"] == "analyze_performance"
        assert enhanced_rec["relevance_score"] == 0.9
        assert "description" in enhanced_rec
        assert "usage_example" in enhanced_rec
        assert "category" in enhanced_rec
        assert enhanced_rec["category"] == "Performance Optimization"

    def test_tool_description_generation(self, agent):
        """Test tool description generation."""
        desc = agent._get_tool_description("analyze_performance")
        assert "performance analysis" in desc.lower()
        
        # Test unknown tool
        desc = agent._get_tool_description("unknown_tool")
        assert "unknown tool" in desc.lower()

    def test_tool_category_determination(self, agent):
        """Test tool category determination logic."""
        assert agent._determine_tool_category("analyze_workload_events") == "Workload Analysis"
        assert agent._determine_tool_category("calculate_cost_savings") == "Cost Optimization"
        assert agent._determine_tool_category("optimize_throughput") == "Performance Optimization"
        assert agent._determine_tool_category("compare_models") == "Model Selection"
        assert agent._determine_tool_category("get_supply_catalog") == "Supply Catalog Management"
        assert agent._determine_tool_category("generate_report") == "Monitoring & Reporting"
        assert agent._determine_tool_category("unknown_tool") == "Quality Optimization"


class TestToolDiscoveryIntegration:
    """Integration tests for ToolDiscoverySubAgent."""
    
    @pytest.fixture
    def agent(self):
        return ToolDiscoverySubAgent()
    
    @pytest.fixture
    def real_context(self):
        """Create realistic execution context."""
        context = Mock(spec=ExecutionContext)
        context.run_id = "integration_test_789"
        context.stream_updates = True
        context.state = Mock(spec=DeepAgentState)
        context.state.user_request = "I need to optimize my GPT-4 model costs and improve performance metrics for my customer service chatbot"
        return context

    @pytest.mark.asyncio
    async def test_end_to_end_tool_discovery(self, agent, real_context):
        """Test complete end-to-end tool discovery flow."""
        
        # Mock WebSocket events to capture calls
        agent.emit_thinking = AsyncMock()
        agent.emit_progress = AsyncMock()
        agent.emit_tool_executing = AsyncMock()
        agent.emit_tool_completed = AsyncMock()
        agent.emit_error = AsyncMock()
        
        # Test precondition validation
        valid = await agent.validate_preconditions(real_context)
        assert valid is True
        
        # Test core logic execution
        result = await agent.execute_core_logic(real_context)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "discovered_tools" in result
        assert "analyzed_categories" in result
        assert "total_tools_found" in result
        assert "discovery_metadata" in result
        
        # Verify discovered tools
        tools = result["discovered_tools"]
        assert len(tools) > 0
        assert isinstance(tools[0], dict)
        assert "tool_name" in tools[0]
        assert "relevance_score" in tools[0]
        assert "description" in tools[0]
        
        # Verify categories identified
        categories = result["analyzed_categories"]
        assert len(categories) > 0
        # Should detect both cost and performance optimization
        category_names = set(categories)
        assert "Cost Optimization" in category_names or "Performance Optimization" in category_names
        
        # Verify metadata
        metadata = result["discovery_metadata"]
        assert metadata["run_id"] == "integration_test_789"
        assert metadata["agent"] == "ToolDiscoverySubAgent"
        assert "duration_ms" in metadata
        assert "timestamp" in metadata

    @pytest.mark.asyncio
    async def test_state_result_storage(self, agent, real_context):
        """Test that results are stored in state for other agents."""
        agent.emit_thinking = AsyncMock()
        agent.emit_progress = AsyncMock()
        agent.emit_tool_executing = AsyncMock()
        agent.emit_tool_completed = AsyncMock()
        
        # Execute discovery
        result = await agent.execute_core_logic(real_context)
        
        # Verify state was updated
        assert hasattr(real_context.state, 'tool_discovery_result')
        assert real_context.state.tool_discovery_result == result


class TestToolDiscoveryResilience:
    """Test error handling and resilience patterns."""
    
    @pytest.fixture
    def agent(self):
        return ToolDiscoverySubAgent()

    @pytest.mark.asyncio
    async def test_graceful_error_handling(self, agent):
        """Test graceful error handling with proper error types."""
        context = Mock(spec=ExecutionContext)
        context.run_id = "error_test_999"
        context.state = Mock(spec=DeepAgentState)
        context.state.user_request = "valid request"
        
        # Mock emit methods
        agent.emit_thinking = AsyncMock()
        agent.emit_progress = AsyncMock()
        agent.emit_error = AsyncMock()
        
        # Force internal method to fail
        agent._extract_entities_from_request = AsyncMock(side_effect=RuntimeError("Simulated error"))
        
        # Should raise AgentValidationError
        with pytest.raises(AgentValidationError) as exc_info:
            await agent.execute_core_logic(context)
        
        # Verify error handling
        assert "Tool discovery execution failed" in str(exc_info.value)
        agent.emit_error.assert_called_once_with(
            "Tool discovery failed: Simulated error",
            error_type="DiscoveryError"
        )

    @pytest.mark.asyncio
    async def test_empty_tool_recommendations_handling(self, agent):
        """Test handling of empty tool recommendations."""
        categories = ["NonexistentCategory"]
        entities = Mock(models_mentioned=[], metrics_mentioned=[])
        
        recommendations = await agent._discover_tools(categories, entities)
        
        # Should handle gracefully and return empty list
        assert isinstance(recommendations, list)
        assert len(recommendations) == 0


if __name__ == "__main__":
    # Run mission critical tests
    pytest.main([
        __file__, 
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure for faster feedback
    ])