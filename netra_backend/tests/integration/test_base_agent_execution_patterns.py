"""
Comprehensive BaseAgent Execution Patterns Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Stability & Agent Execution Reliability
- Value Impact: Ensures BaseAgent properly integrates with core SSOT classes for reliable agent execution
- Strategic Impact: Core platform functionality - agent execution enables chat value delivery

CRITICAL MISSION: Validates that BaseAgent properly integrates with execution infrastructure while 
maintaining user isolation and emitting proper WebSocket events for chat business value.

This comprehensive test suite covers:
- BaseAgent [U+2194] ExecutionEngine (agent execution lifecycle) 
- BaseAgent [U+2194] UnifiedToolDispatcher (tool execution with WebSocket events)
- BaseAgent [U+2194] LLMManager (LLM operations with user context)
- BaseAgent [U+2194] UnifiedWebSocketEmitter (event emission during execution)
- BaseAgent [U+2194] UserExecutionContext (context passing and isolation)
- BaseAgent [U+2194] ReliabilityManager (error handling and retries)
- Real business value scenarios (cost analysis, data processing, etc.)
- Execution pattern validation and error handling
- WebSocket event emission and validation
- User isolation and context management
- Token tracking and cost optimization
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

from test_framework.base_integration_test import BaseIntegrationTest

# Import the class under test
from netra_backend.app.agents.base_agent import BaseAgent

# Import core SSOT classes and dependencies for testing
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.base.executor import BaseExecutionEngine, ExecutionStrategy
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.services.billing.token_counter import TokenCounter
from netra_backend.app.services.token_optimization.context_manager import TokenOptimizationContextManager

# WebSocket infrastructure
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter


# ============================================================================
# TEST UTILITIES AND FIXTURES
# ============================================================================

@pytest.fixture
def user_execution_context():
    """Create a test UserExecutionContext with realistic data."""
    return UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        thread_id=f"thread_{uuid.uuid4().hex[:8]}",
        run_id=f"run_{uuid.uuid4().hex[:8]}",
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        db_session=None,  # No real DB session for integration test
        websocket_connection_id=f"ws_{uuid.uuid4().hex[:8]}",
        metadata={
            "user_request": "Analyze my cloud costs and suggest optimizations",
            "agent_input": "cost_analysis_request",
            "request_type": "cost_optimization",
            "priority": "high"
        }
    )

@pytest.fixture
def mock_llm_manager():
    """Create realistic mock LLM manager with user context support."""
    mock_llm = AsyncMock(spec=LLMManager)
    mock_llm.initialize = AsyncMock()
    mock_llm._initialized = True
    mock_llm._config = {}
    mock_llm._cache = {}
    mock_llm._user_context = None
    
    # Mock realistic LLM response for cost analysis
    mock_llm.generate_text = AsyncMock(return_value={
        "response": "Based on your cloud usage patterns, I recommend: 1) Resize underutilized instances 2) Implement auto-scaling 3) Use reserved instances for stable workloads",
        "token_usage": {"input_tokens": 150, "output_tokens": 75, "total_cost": 0.0045},
        "model": "gpt-4"
    })
    
    # Mock structured response generation
    mock_llm.generate_structured = AsyncMock(return_value={
        "cost_savings_potential": 2500.00,
        "optimization_recommendations": [
            {"type": "instance_resizing", "savings": 800.00, "priority": "high"},
            {"type": "auto_scaling", "savings": 1200.00, "priority": "medium"},
            {"type": "reserved_instances", "savings": 500.00, "priority": "low"}
        ],
        "implementation_timeline": "2-4 weeks"
    })
    
    return mock_llm

@pytest.fixture
def mock_websocket_bridge():
    """Create realistic mock WebSocket bridge with event tracking."""
    mock_bridge = AsyncMock()
    
    # Track emitted events for validation
    mock_bridge.events_emitted = []
    
    async def track_event(event_type, *args, **kwargs):
        mock_bridge.events_emitted.append({
            "event_type": event_type,
            "timestamp": datetime.utcnow(),
            "args": args,
            "kwargs": kwargs
        })
        return True
    
    # Mock all critical WebSocket events
    mock_bridge.emit_agent_started = AsyncMock(side_effect=lambda *args, **kwargs: track_event("agent_started", *args, **kwargs))
    mock_bridge.emit_agent_thinking = AsyncMock(side_effect=lambda *args, **kwargs: track_event("agent_thinking", *args, **kwargs))
    mock_bridge.emit_tool_executing = AsyncMock(side_effect=lambda *args, **kwargs: track_event("tool_executing", *args, **kwargs))
    mock_bridge.emit_tool_completed = AsyncMock(side_effect=lambda *args, **kwargs: track_event("tool_completed", *args, **kwargs))
    mock_bridge.emit_agent_completed = AsyncMock(side_effect=lambda *args, **kwargs: track_event("agent_completed", *args, **kwargs))
    mock_bridge.emit_error = AsyncMock(side_effect=lambda *args, **kwargs: track_event("error", *args, **kwargs))
    
    return mock_bridge

@pytest.fixture
def mock_tool_dispatcher():
    """Create realistic mock tool dispatcher with business logic."""
    mock_dispatcher = AsyncMock()
    
    # Mock cost analysis tool execution
    mock_dispatcher.execute_tool = AsyncMock(return_value={
        "tool_name": "cloud_cost_analyzer",
        "result": {
            "current_monthly_cost": 5200.00,
            "projected_savings": 2100.00,
            "cost_breakdown": {
                "compute": 3200.00,
                "storage": 1200.00,  
                "network": 800.00
            },
            "recommendations": [
                "Resize 15 underutilized EC2 instances",
                "Implement auto-scaling for web tier",
                "Purchase reserved instances for database tier"
            ]
        },
        "execution_time_ms": 1250.0,
        "status": "completed"
    })
    
    # Mock data processing tool
    mock_dispatcher.execute_data_processing = AsyncMock(return_value={
        "tool_name": "data_processor",
        "result": {
            "processed_records": 15000,
            "processing_time_seconds": 45.2,
            "quality_score": 0.94,
            "anomalies_detected": 23,
            "data_insights": [
                "Peak usage occurs between 9-11 AM EST",
                "Weekend usage is 40% lower than weekdays",
                "Storage costs increasing 15% monthly"
            ]
        },
        "status": "completed"
    })
    
    return mock_dispatcher

@pytest.fixture 
def mock_reliability_manager():
    """Create realistic mock reliability manager."""
    mock_rm = AsyncMock()
    mock_rm.get_health_status = Mock(return_value={
        "status": "healthy",
        "total_executions": 147,
        "success_rate": 0.94,
        "circuit_breaker_state": "closed",
        "last_execution": datetime.utcnow(),
        "error_rate": 0.06
    })
    
    # Mock retry execution
    mock_rm.execute_with_reliability = AsyncMock(side_effect=lambda context, func: func())
    
    return mock_rm


# ============================================================================
# TEST CLASS
# ============================================================================

@pytest.mark.integration
class TestBaseAgentExecutionPatterns(BaseIntegrationTest):
    """Test BaseAgent execution patterns with core SSOT classes integration."""
    
    async def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        await self.async_setup()
    
    async def teardown_method(self):
        """Tear down method called after each test method."""
        await self.async_teardown()
        super().teardown_method()
    
    # ========================================================================
    # CORE AGENT INITIALIZATION AND LIFECYCLE TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_base_agent_initialization_with_all_components(
        self, user_execution_context, mock_llm_manager, mock_reliability_manager
    ):
        """Test BaseAgent initializes properly with all core components."""
        # Act
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="CostAnalysisAgent",
            description="Agent for cloud cost analysis and optimization",
            user_context=user_execution_context,
            enable_reliability=True,
            enable_execution_engine=True,
            enable_caching=False
        )
        
        # Assert core initialization
        assert agent.name == "CostAnalysisAgent"
        assert agent.llm_manager == mock_llm_manager
        assert agent.user_context == user_execution_context
        assert agent.state == SubAgentLifecycle.PENDING
        
        # Assert infrastructure components initialized
        assert agent._reliability_manager_instance is not None
        assert agent._execution_engine is not None
        assert agent.monitor is not None
        assert agent.timing_collector is not None
        assert agent.token_counter is not None
        assert agent.token_context_manager is not None
        
        # Assert WebSocket integration
        assert agent._websocket_adapter is not None
        assert hasattr(agent, 'user_context')
        
        # Assert session isolation validation passed
        # (BaseAgent.__init__ calls _validate_session_isolation())
    
    @pytest.mark.asyncio
    async def test_base_agent_factory_method_creates_context_aware_agent(
        self, user_execution_context
    ):
        """Test BaseAgent.create_agent_with_context() factory method creates properly isolated agent."""
        # Act
        agent = BaseAgent.create_agent_with_context(user_execution_context)
        
        # Assert proper factory creation
        assert isinstance(agent, BaseAgent)
        assert agent._user_execution_context == user_execution_context
        assert agent.name == "BaseAgent"
        
        # Assert no deprecated tool_dispatcher to avoid warnings
        assert agent.tool_dispatcher is None
        
        # Assert user context isolation
        assert hasattr(agent, '_user_execution_context')
        
        self.logger.info(" PASS:  BaseAgent factory method creates context-aware agent successfully")
    
    @pytest.mark.asyncio
    async def test_base_agent_state_management_lifecycle(self):
        """Test BaseAgent state management through complete lifecycle."""
        # Arrange
        agent = BaseAgent(name="StateTestAgent")
        
        # Test valid state transitions
        assert agent.get_state() == SubAgentLifecycle.PENDING
        
        # Act & Assert valid transitions
        agent.set_state(SubAgentLifecycle.RUNNING)
        assert agent.get_state() == SubAgentLifecycle.RUNNING
        
        agent.set_state(SubAgentLifecycle.COMPLETED)
        assert agent.get_state() == SubAgentLifecycle.COMPLETED
        
        agent.set_state(SubAgentLifecycle.SHUTDOWN)
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN
        
        # Test invalid transition (should raise error)
        with pytest.raises(ValueError, match="Invalid state transition"):
            agent.set_state(SubAgentLifecycle.RUNNING)  # Can't go back from SHUTDOWN
        
        self.logger.info(" PASS:  BaseAgent state management lifecycle works correctly")
    
    # ========================================================================
    # EXECUTION ENGINE INTEGRATION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_base_agent_execution_engine_integration(
        self, user_execution_context, mock_llm_manager, mock_websocket_bridge
    ):
        """Test BaseAgent integration with BaseExecutionEngine for orchestrated execution."""
        
        # Create agent with execution engine enabled
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="ExecutionTestAgent",
            user_context=user_execution_context,
            enable_execution_engine=True
        )
        
        # Set WebSocket bridge
        agent.set_websocket_bridge(mock_websocket_bridge, user_execution_context.run_id)
        
        # Mock agent's core execution method
        async def mock_execute_core_logic(context):
            await agent.emit_thinking("Processing cost analysis request")
            await asyncio.sleep(0.01)  # Simulate processing time
            return {
                "status": "completed",
                "analysis_result": "Cost optimization potential: $2,100/month",
                "recommendations": 3,
                "processing_time_ms": 125.5
            }
        
        agent.execute_core_logic = mock_execute_core_logic
        
        # Act - Execute through execution engine
        execution_context = ExecutionContext(
            request_id=user_execution_context.request_id,
            run_id=user_execution_context.run_id,
            agent_name=agent.name,
            user_id=user_execution_context.user_id,
            correlation_id=agent.correlation_id
        )
        
        result = await agent._execution_engine.execute(agent, execution_context)
        
        # Assert execution result
        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.COMPLETED
        assert result.request_id == user_execution_context.request_id
        assert "analysis_result" in result.data
        assert result.execution_time_ms > 0
        
        # Assert WebSocket events were emitted during execution
        assert len(mock_websocket_bridge.events_emitted) >= 1
        thinking_events = [e for e in mock_websocket_bridge.events_emitted if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) >= 1
        
        self.logger.info(" PASS:  BaseAgent integrates properly with ExecutionEngine")
    
    @pytest.mark.asyncio
    async def test_base_agent_execution_with_reliability_manager(
        self, user_execution_context, mock_llm_manager, mock_reliability_manager
    ):
        """Test BaseAgent execution with ReliabilityManager for error handling and retries."""
        
        # Create agent with reliability enabled
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilityTestAgent", 
            user_context=user_execution_context,
            enable_reliability=True
        )
        
        # Mock a flaky operation that fails first time, succeeds second time
        call_count = 0
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Simulated transient error")
            return {"status": "success_after_retry", "attempt": call_count}
        
        # Test reliability manager execution
        result = await agent.execute_with_reliability(
            operation=flaky_operation,
            operation_name="flaky_cost_analysis",
            timeout=5.0
        )
        
        # Assert reliability manager handled retry
        assert result["status"] == "success_after_retry"
        assert result["attempt"] == 2  # Should have retried once
        assert call_count == 2
        
        # Test circuit breaker status
        cb_status = agent.get_circuit_breaker_status()
        assert "state" in cb_status
        assert cb_status["state"] in ["closed", "half_open", "open"]
        
        self.logger.info(" PASS:  BaseAgent integrates properly with ReliabilityManager")
    
    # ========================================================================
    # LLM MANAGER INTEGRATION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_base_agent_llm_manager_integration_with_token_tracking(
        self, user_execution_context, mock_llm_manager
    ):
        """Test BaseAgent integration with LLMManager including token tracking and cost optimization."""
        
        # Create agent with LLM manager
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="LLMIntegrationAgent",
            user_context=user_execution_context
        )
        
        # Test LLM usage tracking
        enhanced_context = agent.track_llm_usage(
            context=user_execution_context,
            input_tokens=150,
            output_tokens=75, 
            model="gpt-4",
            operation_type="cost_analysis"
        )
        
        # Assert context was enhanced with token data
        assert "token_usage" in enhanced_context.metadata
        token_usage = enhanced_context.metadata["token_usage"]
        assert "operations" in token_usage
        assert len(token_usage["operations"]) >= 1
        
        latest_op = token_usage["operations"][-1]
        assert latest_op["input_tokens"] == 150
        assert latest_op["output_tokens"] == 75
        assert latest_op["model"] == "gpt-4"
        assert latest_op["operation_type"] == "cost_analysis"
        assert "cost" in latest_op
        
        # Test prompt optimization
        original_prompt = "Analyze the cloud infrastructure costs for the following data: " + "x" * 1000
        enhanced_context_2, optimized_prompt = agent.optimize_prompt_for_context(
            context=enhanced_context,
            prompt=original_prompt,
            target_reduction=20
        )
        
        # Assert prompt was optimized
        assert len(optimized_prompt) <= len(original_prompt)
        assert "prompt_optimizations" in enhanced_context_2.metadata
        
        # Test cost optimization suggestions
        enhanced_context_3, suggestions = agent.get_cost_optimization_suggestions(enhanced_context_2)
        
        # Assert suggestions were generated
        assert isinstance(suggestions, list)
        assert "cost_optimization_suggestions" in enhanced_context_3.metadata
        
        # Test token usage summary
        usage_summary = agent.get_token_usage_summary(enhanced_context_3)
        assert "current_session" in usage_summary
        assert usage_summary["current_session"]["operations_count"] >= 1
        
        self.logger.info(" PASS:  BaseAgent integrates properly with LLMManager and token tracking")
    
    # ========================================================================
    # WEBSOCKET EVENT INTEGRATION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_base_agent_websocket_event_emission_complete_flow(
        self, user_execution_context, mock_websocket_bridge, mock_llm_manager
    ):
        """Test BaseAgent emits all 5 critical WebSocket events during execution flow."""
        
        # Create agent with WebSocket integration
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="WebSocketTestAgent",
            user_context=user_execution_context
        )
        
        # Set WebSocket bridge
        agent.set_websocket_bridge(mock_websocket_bridge, user_execution_context.run_id)
        
        # Execute complete agent workflow with all event types
        await agent.emit_agent_started("Starting cost analysis")
        
        await agent.emit_thinking("Analyzing current cloud infrastructure", step_number=1, context=user_execution_context)
        
        await agent.emit_tool_executing("cloud_cost_analyzer", {"account_id": "123456789"})
        
        # Simulate some processing time
        await asyncio.sleep(0.01)
        
        await agent.emit_tool_completed("cloud_cost_analyzer", {
            "savings_identified": 2100.00,
            "processing_time": "1.25s"
        })
        
        # Enhanced completion with cost analysis
        completion_result = {
            "total_savings": 2100.00,
            "recommendations": 3,
            "confidence_score": 0.92
        }
        await agent.emit_agent_completed(completion_result, context=user_execution_context)
        
        # Validate all 5 critical events were emitted
        emitted_event_types = {event["event_type"] for event in mock_websocket_bridge.events_emitted}
        
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for event_type in critical_events:
            assert event_type in emitted_event_types, f"Critical event {event_type} was not emitted"
        
        # Validate events have proper data
        thinking_events = [e for e in mock_websocket_bridge.events_emitted if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) >= 1
        
        completed_events = [e for e in mock_websocket_bridge.events_emitted if e["event_type"] == "agent_completed"]
        assert len(completed_events) >= 1
        
        # Assert enhanced completion data (cost analysis)
        completed_event = completed_events[0]
        # The completion result would be enhanced with cost analysis if context was provided
        
        self.logger.info(" PASS:  BaseAgent emits all critical WebSocket events correctly")
    
    @pytest.mark.asyncio
    async def test_base_agent_websocket_bridge_adapter_integration(
        self, user_execution_context, mock_websocket_bridge
    ):
        """Test BaseAgent WebSocketBridgeAdapter integration and event delegation."""
        
        agent = BaseAgent(name="AdapterTestAgent", user_context=user_execution_context)
        
        # Test WebSocket bridge setting
        agent.set_websocket_bridge(mock_websocket_bridge, user_execution_context.run_id)
        
        # Test has_websocket_context detection
        assert agent.has_websocket_context()
        
        # Test event delegation through adapter
        await agent.emit_thinking("Testing WebSocket adapter delegation")
        await agent.emit_progress("Processing step 1 of 3", is_complete=False)
        await agent.emit_error("Test error message", error_type="ValidationError")
        
        # Verify events were delegated to bridge
        assert len(mock_websocket_bridge.events_emitted) >= 3
        
        event_types = [event["event_type"] for event in mock_websocket_bridge.events_emitted]
        assert "agent_thinking" in event_types
        # Note: emit_progress and emit_error may map to different event types in the adapter
        
        self.logger.info(" PASS:  BaseAgent WebSocketBridgeAdapter integration works correctly")
    
    # ========================================================================
    # BUSINESS VALUE SCENARIO TESTS 
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_cost_analysis_agent_complete_business_scenario(
        self, user_execution_context, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge
    ):
        """Test complete cost analysis business scenario with real value delivery."""
        
        # Create specialized cost analysis agent
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="CloudCostAnalysisAgent",
            description="AI agent for cloud cost optimization and savings identification",
            user_context=user_execution_context,
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Set up WebSocket for user feedback
        agent.set_websocket_bridge(mock_websocket_bridge, user_execution_context.run_id)
        
        # Mock agent's business logic implementation
        async def execute_cost_analysis_logic(context):
            """Mock implementation of cost analysis business logic."""
            
            # Step 1: Announce start
            await agent.emit_agent_started("Starting comprehensive cloud cost analysis")
            
            # Step 2: Analyze current usage
            await agent.emit_thinking("Analyzing current cloud resource usage patterns", step_number=1)
            
            # Step 3: Execute cost analysis tool
            await agent.emit_tool_executing("cloud_cost_analyzer", {
                "account_id": user_execution_context.metadata.get("aws_account_id", "123456789"),
                "time_range": "30_days",
                "include_recommendations": True
            })
            
            # Simulate tool execution
            tool_result = await mock_tool_dispatcher.execute_tool()
            
            await agent.emit_tool_completed("cloud_cost_analyzer", {
                "analysis_completed": True,
                "records_processed": tool_result["result"]["processed_records"] if "processed_records" in tool_result["result"] else 15000,
                "savings_identified": tool_result["result"]["projected_savings"]
            })
            
            # Step 4: Generate LLM insights
            await agent.emit_thinking("Generating optimization recommendations", step_number=2)
            
            # Track LLM usage
            enhanced_context = agent.track_llm_usage(
                context=user_execution_context,
                input_tokens=200,
                output_tokens=150,
                model="gpt-4",
                operation_type="cost_analysis"
            )
            
            # Step 5: Create business value result
            business_result = {
                "cost_analysis": {
                    "current_monthly_cost": tool_result["result"]["current_monthly_cost"],
                    "projected_monthly_savings": tool_result["result"]["projected_savings"],
                    "savings_percentage": round((tool_result["result"]["projected_savings"] / tool_result["result"]["current_monthly_cost"]) * 100, 1),
                    "payback_period_months": 2.5
                },
                "recommendations": tool_result["result"]["recommendations"],
                "implementation_priority": "high",
                "confidence_level": 0.89,
                "next_steps": [
                    "Review recommended instance resizing",
                    "Implement auto-scaling policies", 
                    "Evaluate reserved instance purchases"
                ]
            }
            
            # Store results in context
            agent.store_metadata_result(enhanced_context, "cost_analysis_result", business_result)
            
            # Step 6: Complete with business value
            await agent.emit_agent_completed(business_result, context=enhanced_context)
            
            return business_result
        
        # Execute the complete business scenario
        result = await execute_cost_analysis_logic(user_execution_context)
        
        # Validate business value was delivered
        assert "cost_analysis" in result
        assert "projected_monthly_savings" in result["cost_analysis"]
        assert result["cost_analysis"]["projected_monthly_savings"] > 0
        assert "recommendations" in result
        assert len(result["recommendations"]) >= 3
        
        # Validate all critical WebSocket events were emitted for user visibility
        emitted_event_types = {event["event_type"] for event in mock_websocket_bridge.events_emitted}
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for event_type in critical_events:
            assert event_type in emitted_event_types, f"Critical business event {event_type} missing"
        
        # Validate user received meaningful progress updates
        thinking_events = [e for e in mock_websocket_bridge.events_emitted if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) >= 2  # Should have multiple thinking steps
        
        self.logger.info(" PASS:  Complete cost analysis business scenario delivers real value")
    
    @pytest.mark.asyncio
    async def test_data_processing_agent_business_scenario(
        self, user_execution_context, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge
    ):
        """Test data processing business scenario with quality validation and insights."""
        
        # Create data processing agent
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="DataProcessingAgent",
            description="AI agent for data processing, quality validation, and insights generation",
            user_context=user_execution_context,
            enable_reliability=True
        )
        
        # Configure for data processing scenario
        user_execution_context.metadata.update({
            "user_request": "Process customer usage data and identify trends",
            "data_source": "customer_metrics_table",
            "processing_type": "trend_analysis"
        })
        
        agent.set_websocket_bridge(mock_websocket_bridge, user_execution_context.run_id)
        
        # Mock business logic
        async def execute_data_processing(context):
            await agent.emit_agent_started("Starting data processing and analysis")
            
            # Data validation phase
            await agent.emit_thinking("Validating data quality and completeness", step_number=1)
            
            # Data processing tool execution
            await agent.emit_tool_executing("data_processor", {
                "source_table": "customer_metrics",
                "processing_mode": "trend_analysis",
                "quality_checks": True
            })
            
            processing_result = await mock_tool_dispatcher.execute_data_processing()
            
            await agent.emit_tool_completed("data_processor", {
                "records_processed": processing_result["result"]["processed_records"],
                "quality_score": processing_result["result"]["quality_score"],
                "processing_time": processing_result["result"]["processing_time_seconds"]
            })
            
            # Insights generation
            await agent.emit_thinking("Generating business insights from processed data", step_number=2)
            
            # Track token usage for insights
            enhanced_context = agent.track_llm_usage(
                context=context,
                input_tokens=300,
                output_tokens=200,
                model="gpt-4",
                operation_type="data_insights"
            )
            
            # Create business insights
            insights_result = {
                "data_processing": {
                    "records_processed": processing_result["result"]["processed_records"],
                    "quality_score": processing_result["result"]["quality_score"],
                    "anomalies_detected": processing_result["result"]["anomalies_detected"],
                    "processing_efficiency": "high"
                },
                "business_insights": processing_result["result"]["data_insights"],
                "trend_analysis": {
                    "primary_trend": "Peak usage during business hours",
                    "seasonal_patterns": "Weekend usage 40% lower",
                    "growth_trend": "15% monthly increase in storage costs"
                },
                "recommendations": [
                    "Implement usage-based pricing model",
                    "Optimize storage allocation policies",
                    "Schedule batch processing during off-peak hours"
                ]
            }
            
            # Store business insights
            agent.store_metadata_result(enhanced_context, "data_insights_result", insights_result)
            
            await agent.emit_agent_completed(insights_result, context=enhanced_context)
            
            return insights_result
        
        # Execute data processing scenario
        result = await execute_data_processing(user_execution_context)
        
        # Validate business value
        assert "data_processing" in result
        assert result["data_processing"]["records_processed"] > 0
        assert result["data_processing"]["quality_score"] > 0.8
        assert "business_insights" in result
        assert "trend_analysis" in result
        assert len(result["recommendations"]) >= 3
        
        # Validate WebSocket communication
        emitted_events = {event["event_type"] for event in mock_websocket_bridge.events_emitted}
        assert "agent_started" in emitted_events
        assert "agent_thinking" in emitted_events
        assert "tool_executing" in emitted_events
        assert "tool_completed" in emitted_events
        assert "agent_completed" in emitted_events
        
        self.logger.info(" PASS:  Data processing business scenario delivers actionable insights")
    
    # ========================================================================
    # USER ISOLATION AND CONTEXT MANAGEMENT TESTS
    # ========================================================================
    
    @pytest.mark.asyncio 
    async def test_base_agent_user_context_isolation_validation(self):
        """Test BaseAgent properly isolates user contexts and prevents data leakage."""
        
        # Create contexts for two different users
        user1_context = UserExecutionContext(
            user_id="user_001",
            thread_id="thread_001", 
            run_id="run_001",
            metadata={"sensitive_data": "user1_secret", "user_request": "user1 request"}
        )
        
        user2_context = UserExecutionContext(
            user_id="user_002",
            thread_id="thread_002",
            run_id="run_002", 
            metadata={"sensitive_data": "user2_secret", "user_request": "user2 request"}
        )
        
        # Create agents for each user using factory method
        agent1 = BaseAgent.create_agent_with_context(user1_context)
        agent2 = BaseAgent.create_agent_with_context(user2_context)
        
        # Verify agents have isolated contexts
        assert agent1._user_execution_context.user_id == "user_001"
        assert agent2._user_execution_context.user_id == "user_002"
        
        # Verify metadata isolation
        assert agent1._user_execution_context.metadata["sensitive_data"] == "user1_secret"
        assert agent2._user_execution_context.metadata["sensitive_data"] == "user2_secret"
        
        # Verify no shared state between agents
        agent1.context["test_data"] = "agent1_data"
        agent2.context["test_data"] = "agent2_data"
        
        assert agent1.context["test_data"] != agent2.context["test_data"]
        
        # Verify agents have different correlation IDs
        assert agent1.correlation_id != agent2.correlation_id
        
        # Test token tracking isolation
        enhanced_context1 = agent1.track_llm_usage(user1_context, 100, 50, "gpt-4", "test")
        enhanced_context2 = agent2.track_llm_usage(user2_context, 200, 75, "gpt-4", "test")
        
        # Verify token usage is isolated per user
        assert "token_usage" in enhanced_context1.metadata
        assert "token_usage" in enhanced_context2.metadata
        
        user1_ops = enhanced_context1.metadata["token_usage"]["operations"]
        user2_ops = enhanced_context2.metadata["token_usage"]["operations"]
        
        assert user1_ops[0]["input_tokens"] == 100
        assert user2_ops[0]["input_tokens"] == 200
        assert user1_ops != user2_ops
        
        self.logger.info(" PASS:  BaseAgent properly isolates user contexts")
    
    @pytest.mark.asyncio
    async def test_base_agent_metadata_storage_and_retrieval(self, user_execution_context):
        """Test BaseAgent metadata storage methods work correctly with context isolation."""
        
        agent = BaseAgent(name="MetadataTestAgent", user_context=user_execution_context)
        
        # Test single metadata storage
        test_data = {
            "analysis_type": "cost_optimization",
            "confidence_score": 0.94,
            "processing_time": 125.5
        }
        
        agent.store_metadata_result(user_execution_context, "analysis_result", test_data)
        
        # Verify data was stored
        assert "analysis_result" in user_execution_context.metadata
        assert user_execution_context.metadata["analysis_result"]["confidence_score"] == 0.94
        
        # Test batch metadata storage
        batch_data = {
            "recommendations": ["rec1", "rec2", "rec3"],
            "priority_level": "high",
            "estimated_savings": 2100.00
        }
        
        agent.store_metadata_batch(user_execution_context, batch_data)
        
        # Verify batch data was stored
        for key, expected_value in batch_data.items():
            assert key in user_execution_context.metadata
            assert user_execution_context.metadata[key] == expected_value
        
        # Test metadata retrieval
        retrieved_savings = agent.get_metadata_value(user_execution_context, "estimated_savings")
        assert retrieved_savings == 2100.00
        
        # Test default value handling
        nonexistent_value = agent.get_metadata_value(user_execution_context, "nonexistent_key", "default_val")
        assert nonexistent_value == "default_val"
        
        self.logger.info(" PASS:  BaseAgent metadata storage and retrieval works correctly")
    
    # ========================================================================
    # ERROR HANDLING AND RESILIENCE TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_base_agent_error_handling_and_recovery_patterns(
        self, user_execution_context, mock_llm_manager, mock_websocket_bridge
    ):
        """Test BaseAgent error handling, recovery patterns, and graceful degradation."""
        
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="ErrorHandlingAgent",
            user_context=user_execution_context,
            enable_reliability=True
        )
        
        agent.set_websocket_bridge(mock_websocket_bridge, user_execution_context.run_id)
        
        # Test error emission
        await agent.emit_error("Test error for validation", error_type="ValidationError", error_details={
            "field": "user_input",
            "issue": "missing_required_data"
        })
        
        # Verify error was emitted to WebSocket
        error_events = [e for e in mock_websocket_bridge.events_emitted if e["event_type"] == "error"]
        assert len(error_events) >= 1
        
        # Test circuit breaker status during error conditions
        initial_cb_status = agent.get_circuit_breaker_status()
        assert "state" in initial_cb_status
        
        # Test health status during error conditions  
        health_status = agent.get_health_status()
        assert "agent_name" in health_status
        assert "state" in health_status
        assert "websocket_available" in health_status
        assert health_status["websocket_available"] is True
        
        # Test graceful state reset after errors
        await agent.reset_state()
        assert agent.get_state() == SubAgentLifecycle.PENDING
        
        # Verify reset cleared any error state
        post_reset_health = agent.get_health_status()
        assert post_reset_health["state"] == SubAgentLifecycle.PENDING.value
        
        self.logger.info(" PASS:  BaseAgent error handling and recovery patterns work correctly")
    
    @pytest.mark.asyncio
    async def test_base_agent_graceful_shutdown_and_cleanup(
        self, user_execution_context, mock_websocket_bridge
    ):
        """Test BaseAgent graceful shutdown and resource cleanup."""
        
        agent = BaseAgent(
            name="ShutdownTestAgent",
            user_context=user_execution_context,
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        agent.set_websocket_bridge(mock_websocket_bridge, user_execution_context.run_id)
        
        # Set up some agent state
        agent.context["active_operations"] = ["op1", "op2"]
        agent.set_state(SubAgentLifecycle.RUNNING)
        
        # Test graceful shutdown
        await agent.shutdown()
        
        # Verify final state
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN
        
        # Verify context was cleared
        assert len(agent.context) == 0
        
        # Test idempotent shutdown (should not error on multiple calls)
        await agent.shutdown()  # Should not raise exception
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN
        
        self.logger.info(" PASS:  BaseAgent graceful shutdown and cleanup works correctly")
    
    # ========================================================================
    # PERFORMANCE AND MONITORING TESTS
    # ========================================================================
    
    @pytest.mark.asyncio 
    async def test_base_agent_performance_monitoring_and_metrics(
        self, user_execution_context, mock_llm_manager
    ):
        """Test BaseAgent performance monitoring and metrics collection."""
        
        agent = BaseAgent(
            llm_manager=mock_llm_manager,
            name="PerformanceTestAgent",
            user_context=user_execution_context,
            enable_execution_engine=True
        )
        
        # Test timing collector functionality
        assert agent.timing_collector is not None
        assert agent.timing_collector.agent_name == "PerformanceTestAgent"
        
        # Test execution monitor 
        assert agent.monitor is not None
        assert agent._execution_monitor is not None
        
        # Test health status includes performance metrics
        health_status = agent.get_health_status()
        
        # Should include monitoring information
        assert "monitor" in health_status or "monitoring" in health_status
        assert "total_executions" in health_status
        assert "success_rate" in health_status
        assert "uses_unified_reliability" in health_status
        assert health_status["uses_unified_reliability"] is True
        
        # Test token usage tracking and optimization
        enhanced_context = agent.track_llm_usage(
            context=user_execution_context,
            input_tokens=500,
            output_tokens=250,
            model="gpt-4-turbo", 
            operation_type="performance_test"
        )
        
        # Verify token metrics
        token_usage = enhanced_context.metadata["token_usage"]
        assert "operations" in token_usage
        assert "cumulative_tokens" in token_usage
        assert "cumulative_cost" in token_usage
        
        # Test usage summary
        usage_summary = agent.get_token_usage_summary(enhanced_context)
        assert "current_session" in usage_summary
        assert usage_summary["current_session"]["operations_count"] >= 1
        
        self.logger.info(" PASS:  BaseAgent performance monitoring and metrics work correctly")


# ============================================================================
# INTEGRATION SCENARIO CLASSES
# ============================================================================

class MockCostAnalysisAgent(BaseAgent):
    """Mock cost analysis agent for testing realistic execution patterns."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="MockCostAnalysisAgent",
            description="Mock agent for cost analysis testing",
            *args,
            **kwargs
        )
    
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Modern execution pattern implementation."""
        
        # Emit start event
        await self.emit_agent_started("Starting cost analysis")
        
        # Analysis phase
        await self.emit_thinking("Analyzing cloud infrastructure costs", step_number=1, context=context)
        
        # Tool execution simulation
        await self.emit_tool_executing("cost_analyzer", {"account_type": "production"})
        
        # Simulate processing time
        await asyncio.sleep(0.01)
        
        # Tool completion
        await self.emit_tool_completed("cost_analyzer", {
            "analysis_complete": True,
            "potential_savings": 1500.00
        })
        
        # Generate insights
        await self.emit_thinking("Generating optimization recommendations", step_number=2, context=context)
        
        # Final result
        result = {
            "cost_analysis": {
                "current_cost": 5200.00,
                "potential_savings": 1500.00,
                "savings_percentage": 28.8
            },
            "recommendations": [
                "Rightsize underutilized instances",
                "Implement auto-scaling",
                "Use spot instances for batch jobs"
            ],
            "confidence": 0.91
        }
        
        # Store result
        self.store_metadata_result(context, "cost_analysis_result", result)
        
        # Emit completion
        await self.emit_agent_completed(result, context=context)
        
        return result


@pytest.mark.integration
class TestMockAgentIntegrationScenarios(BaseIntegrationTest):
    """Test realistic agent integration scenarios using mock agents."""
    
    @pytest.mark.asyncio
    async def test_mock_cost_analysis_agent_complete_execution(
        self, user_execution_context, mock_llm_manager, mock_websocket_bridge
    ):
        """Test mock cost analysis agent with complete execution pattern."""
        
        # Create mock agent
        agent = MockCostAnalysisAgent(
            llm_manager=mock_llm_manager,
            user_context=user_execution_context,
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Set WebSocket bridge
        agent.set_websocket_bridge(mock_websocket_bridge, user_execution_context.run_id)
        
        # Execute with modern pattern
        result = await agent.execute(user_execution_context, stream_updates=True)
        
        # Validate result
        assert "cost_analysis" in result
        assert result["cost_analysis"]["potential_savings"] > 0
        assert "recommendations" in result
        assert len(result["recommendations"]) >= 3
        
        # Validate WebSocket events
        emitted_events = {event["event_type"] for event in mock_websocket_bridge.events_emitted}
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for event_type in critical_events:
            assert event_type in emitted_events, f"Critical event {event_type} missing from mock agent"
        
        # Validate context metadata storage
        assert "cost_analysis_result" in user_execution_context.metadata
        
        self.logger.info(" PASS:  Mock cost analysis agent executes complete pattern correctly")


# Test execution summary  
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])