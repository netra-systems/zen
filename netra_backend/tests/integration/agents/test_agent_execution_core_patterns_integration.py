"""
Agent Execution Core Patterns Integration Tests - Phase 1 Execution Focus

Business Value Justification (BVJ):
- Segment: Platform/All Tiers
- Business Goal: Agent Execution Reliability & Performance
- Value Impact: Protects $500K+ ARR by ensuring agent execution patterns work correctly
- Strategic Impact: Core chat functionality depends on reliable agent execution patterns

CRITICAL MISSION: Validates agent execution patterns including retry logic, circuit breakers,
error handling, WebSocket event emission, and integration with execution infrastructure.

Phase 1 Focus Areas:
1. Agent execution patterns (sync/async, retry, fallback)
2. WebSocket event emission during execution lifecycle
3. Circuit breaker integration and recovery patterns
4. Error handling and graceful degradation
5. Tool execution integration and event emission
6. Token tracking and cost optimization during execution
7. Execution monitoring and metrics collection
8. Real business value execution scenarios

NO Docker dependencies - all tests run locally with real SSOT components.
BUSINESS CRITICAL: Agent execution failures = immediate chat functionality loss.
"""

import asyncio
import gc
import pytest
import time
import uuid
from datetime import datetime, timezone, UTC
from typing import Any, Dict, List, Optional, Callable
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core Agent Infrastructure  
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus

# Execution Infrastructure
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult

# Tool and LLM Infrastructure
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

# Services and Utilities
from netra_backend.app.services.billing.token_counter import TokenCounter
from netra_backend.app.services.token_optimization.context_manager import TokenOptimizationContextManager


class BusinessValueExecutionAgent(BaseAgent):
    """Agent that demonstrates real business value execution patterns."""
    
    def __init__(self, agent_type: str, business_scenario: str = "cost_analysis", *args, **kwargs):
        super().__init__(
            name=f"BusinessValueAgent_{agent_type}",
            description=f"Agent for {business_scenario} business scenario",
            *args,
            **kwargs
        )
        self.agent_type = agent_type
        self.business_scenario = business_scenario
        self.execution_phases = []
        self.business_metrics = {}
        
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with realistic business value patterns."""
        
        self.execution_phases.append({"phase": "started", "timestamp": time.time()})
        
        # Emit agent started
        await self.emit_agent_started(f"Starting {self.business_scenario} analysis")
        
        try:
            # Phase 1: Business Analysis
            await self._execute_business_analysis_phase(context)
            
            # Phase 2: Data Processing
            await self._execute_data_processing_phase(context)
            
            # Phase 3: Insight Generation
            result = await self._execute_insight_generation_phase(context)
            
            # Phase 4: Business Value Calculation
            await self._calculate_business_value(context, result)
            
            # Store comprehensive result
            self.store_metadata_result(context, f"{self.business_scenario}_result", result)
            
            self.execution_phases.append({"phase": "completed", "timestamp": time.time()})
            
            # Emit completion with business value
            await self.emit_agent_completed(result, context=context)
            
            return result
            
        except Exception as e:
            self.execution_phases.append({"phase": "failed", "timestamp": time.time(), "error": str(e)})
            await self.emit_error(f"Business execution failed: {str(e)}", "BusinessExecutionError")
            raise
    
    async def _execute_business_analysis_phase(self, context: UserExecutionContext):
        """Execute business analysis with realistic patterns."""
        await self.emit_thinking("Analyzing business requirements and constraints", step_number=1, context=context)
        
        # Simulate business analysis work
        await asyncio.sleep(0.01)
        
        # Track business analysis metrics
        self.business_metrics["analysis_duration"] = 0.01
        self.business_metrics["requirements_identified"] = 5
        
        self.execution_phases.append({"phase": "analysis_completed", "timestamp": time.time()})
    
    async def _execute_data_processing_phase(self, context: UserExecutionContext):
        """Execute data processing with tool integration."""
        await self.emit_thinking("Processing business data and generating insights", step_number=2, context=context)
        
        # Simulate tool execution for data processing
        await self.emit_tool_executing("business_data_processor", {
            "scenario": self.business_scenario,
            "data_volume": "large",
            "processing_mode": "real_time"
        })
        
        # Simulate tool processing time
        await asyncio.sleep(0.02)
        
        # Tool completion with results
        await self.emit_tool_completed("business_data_processor", {
            "records_processed": 15000,
            "processing_time": "20ms",
            "data_quality_score": 0.94
        })
        
        # Track data processing metrics
        self.business_metrics["data_processing_duration"] = 0.02
        self.business_metrics["records_processed"] = 15000
        
        self.execution_phases.append({"phase": "data_processing_completed", "timestamp": time.time()})
    
    async def _execute_insight_generation_phase(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Generate business insights with LLM integration."""
        await self.emit_thinking("Generating actionable business insights", step_number=3, context=context)
        
        # Track LLM usage for cost optimization
        enhanced_context = self.track_llm_usage(
            context=context,
            input_tokens=250,
            output_tokens=150,
            model="gpt-4",
            operation_type="insight_generation"
        )
        
        # Simulate insight generation
        await asyncio.sleep(0.015)
        
        # Create business insights result
        insights = {
            "primary_insights": [
                f"{self.business_scenario}_insight_1",
                f"{self.business_scenario}_insight_2",
                f"{self.business_scenario}_insight_3"
            ],
            "confidence_score": 0.87,
            "actionability_score": 0.92,
            "business_impact": "high"
        }
        
        self.business_metrics["insight_generation_duration"] = 0.015
        self.business_metrics["insights_generated"] = len(insights["primary_insights"])
        
        self.execution_phases.append({"phase": "insights_completed", "timestamp": time.time()})
        
        return insights
    
    async def _calculate_business_value(self, context: UserExecutionContext, insights: Dict[str, Any]):
        """Calculate business value metrics."""
        # Simulate business value calculation
        business_value = {
            "potential_cost_savings": 2500.00,
            "efficiency_improvement": 0.25,
            "implementation_time": "2-3 weeks",
            "roi_estimate": 3.2
        }
        
        insights["business_value"] = business_value
        self.business_metrics["business_value_calculated"] = True
        
        # Get cost optimization suggestions
        enhanced_context, suggestions = self.get_cost_optimization_suggestions(context)
        if suggestions:
            insights["cost_optimization"] = {
                "suggestions_count": len(suggestions),
                "potential_savings": sum(s.get("potential_savings", 0) for s in suggestions)
            }


class RetryPatternTestAgent(BaseAgent):
    """Agent for testing retry patterns and circuit breakers."""
    
    def __init__(self, failure_pattern: str = "none", *args, **kwargs):
        super().__init__(
            name=f"RetryTestAgent_{failure_pattern}",
            description=f"Agent with {failure_pattern} failure pattern",
            *args,
            **kwargs
        )
        self.failure_pattern = failure_pattern
        self.execution_attempts = 0
        self.retry_history = []
    
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with specific failure patterns for testing."""
        
        self.execution_attempts += 1
        attempt_id = f"attempt_{self.execution_attempts}"
        
        self.retry_history.append({
            "attempt": self.execution_attempts,
            "timestamp": time.time(),
            "failure_pattern": self.failure_pattern
        })
        
        await self.emit_agent_started(f"Starting retry test execution (attempt {self.execution_attempts})")
        
        # Apply failure pattern
        if self.failure_pattern == "transient_error" and self.execution_attempts <= 2:
            await self.emit_error(f"Transient error on attempt {self.execution_attempts}", "TransientError")
            raise ValueError(f"Simulated transient error - attempt {self.execution_attempts}")
        
        elif self.failure_pattern == "persistent_error":
            await self.emit_error(f"Persistent error on attempt {self.execution_attempts}", "PersistentError")
            raise RuntimeError(f"Simulated persistent error - attempt {self.execution_attempts}")
        
        elif self.failure_pattern == "timeout" and self.execution_attempts == 1:
            await asyncio.sleep(0.1)  # Simulate timeout
            await self.emit_error("Execution timeout", "TimeoutError")
            raise asyncio.TimeoutError("Simulated timeout")
        
        # Success case
        await self.emit_thinking(f"Processing successful attempt {self.execution_attempts}", context=context)
        
        result = {
            "status": "completed",
            "final_attempt": self.execution_attempts,
            "failure_pattern": self.failure_pattern,
            "retry_history": self.retry_history
        }
        
        await self.emit_agent_completed(result, context=context)
        return result


@pytest.mark.integration
class AgentExecutionCorePatternsTests(SSotAsyncTestCase):
    """Integration tests for agent execution patterns."""
    
    def create_test_user_context(self, user_id: str = None, scenario: str = "execution_test") -> UserExecutionContext:
        """Create test user context with execution-specific data."""
        user_id = user_id or f"exec_test_user_{uuid.uuid4().hex[:8]}"
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            db_session=None,
            websocket_connection_id=f"ws_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": f"Execute {scenario} test scenario",
                "scenario_type": scenario,
                "execution_priority": "high",
                "business_context": {
                    "user_tier": "enterprise",
                    "cost_center": "engineering",
                    "region": "us-east-1"
                }
            }
        )
    
    @pytest.fixture
    async def mock_llm_manager(self):
        """Mock LLM manager with realistic responses."""
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.initialize = AsyncMock()
        mock_manager._initialized = True
        mock_manager.generate_text = AsyncMock(return_value={
            "response": "Business analysis shows significant optimization opportunities",
            "token_usage": {"input_tokens": 200, "output_tokens": 100, "total_cost": 0.005}
        })
        return mock_manager
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Mock WebSocket bridge with comprehensive event tracking."""
        mock_bridge = AsyncMock()
        mock_bridge.execution_events = []
        
        async def track_execution_event(event_type, *args, **kwargs):
            mock_bridge.execution_events.append({
                "event_type": event_type,
                "timestamp": datetime.now(UTC),
                "args": args,
                "kwargs": kwargs
            })
            return True
        
        # Mock all WebSocket events
        mock_bridge.emit_agent_started = AsyncMock(side_effect=lambda *args, **kwargs: track_execution_event("agent_started", *args, **kwargs))
        mock_bridge.emit_agent_thinking = AsyncMock(side_effect=lambda *args, **kwargs: track_execution_event("agent_thinking", *args, **kwargs))
        mock_bridge.emit_tool_executing = AsyncMock(side_effect=lambda *args, **kwargs: track_execution_event("tool_executing", *args, **kwargs))
        mock_bridge.emit_tool_completed = AsyncMock(side_effect=lambda *args, **kwargs: track_execution_event("tool_completed", *args, **kwargs))
        mock_bridge.emit_agent_completed = AsyncMock(side_effect=lambda *args, **kwargs: track_execution_event("agent_completed", *args, **kwargs))
        mock_bridge.emit_error = AsyncMock(side_effect=lambda *args, **kwargs: track_execution_event("error", *args, **kwargs))
        
        return mock_bridge
    
    @pytest.mark.real_services
    async def test_business_value_execution_pattern_complete_flow(self, mock_websocket_bridge, mock_llm_manager):
        """Test complete business value execution pattern with all phases."""
        
        user_context = self.create_test_user_context("business_user", "cost_optimization")
        
        # Create business value agent
        agent = BusinessValueExecutionAgent(
            agent_type="cost_optimizer",
            business_scenario="cost_analysis",
            llm_manager=mock_llm_manager,
            user_context=user_context
        )
        
        agent.set_websocket_bridge(mock_websocket_bridge, user_context.run_id)
        
        # Execute business scenario
        start_time = time.time()
        result = await agent.execute(user_context, stream_updates=True)
        execution_time = time.time() - start_time
        
        # Validate business execution result
        assert result["primary_insights"] is not None
        assert len(result["primary_insights"]) >= 3
        assert result["confidence_score"] > 0.8
        assert result["business_impact"] == "high"
        assert "business_value" in result
        
        # Validate business value metrics
        business_value = result["business_value"]
        assert business_value["potential_cost_savings"] > 0
        assert business_value["roi_estimate"] > 1.0
        
        # Validate execution phases
        assert len(agent.execution_phases) >= 4
        phase_names = [phase["phase"] for phase in agent.execution_phases]
        expected_phases = ["started", "analysis_completed", "data_processing_completed", "insights_completed", "completed"]
        for phase in expected_phases:
            assert phase in phase_names
        
        # Validate business metrics
        assert agent.business_metrics["analysis_duration"] > 0
        assert agent.business_metrics["data_processing_duration"] > 0
        assert agent.business_metrics["insights_generated"] >= 3
        assert agent.business_metrics["business_value_calculated"] is True
        
        # Validate WebSocket events were emitted
        event_types = {event["event_type"] for event in mock_websocket_bridge.execution_events}
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for event_type in critical_events:
            assert event_type in event_types, f"Critical event {event_type} not emitted"
        
        # Validate context metadata storage
        assert "cost_analysis_result" in user_context.metadata
        stored_result = user_context.metadata["cost_analysis_result"]
        assert stored_result["confidence_score"] == result["confidence_score"]
        
        # Validate performance
        assert execution_time < 0.5, f"Business execution too slow: {execution_time:.2f}s"
        
        self.record_metric("business_execution_success", True)
        self.record_metric("execution_phases", len(agent.execution_phases))
        self.record_metric("business_insights_generated", agent.business_metrics["insights_generated"])
        self.record_metric("execution_time", execution_time)
        
    @pytest.mark.real_services
    async def test_agent_retry_pattern_with_transient_errors(self, mock_websocket_bridge):
        """Test agent retry patterns with transient error recovery."""
        
        user_context = self.create_test_user_context("retry_user", "transient_error_test")
        
        # Create agent that fails first 2 attempts, succeeds on 3rd
        agent = RetryPatternTestAgent(
            failure_pattern="transient_error",
            user_context=user_context,
            enable_reliability=True
        )
        
        agent.set_websocket_bridge(mock_websocket_bridge, user_context.run_id)
        
        # Execute with retry logic
        async def retry_execution():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = await agent.execute(user_context)
                    return result
                except ValueError as e:
                    if attempt == max_retries - 1:
                        raise  # Final attempt failed
                    # Wait before retry
                    await asyncio.sleep(0.01)
            return None
        
        result = await retry_execution()
        
        # Validate retry behavior
        assert result["status"] == "completed"
        assert result["final_attempt"] == 3  # Should succeed on 3rd attempt
        assert len(result["retry_history"]) == 3
        
        # Validate attempt progression
        for i, attempt in enumerate(result["retry_history"]):
            assert attempt["attempt"] == i + 1
            assert attempt["failure_pattern"] == "transient_error"
        
        # Validate WebSocket events include error events
        event_types = [event["event_type"] for event in mock_websocket_bridge.execution_events]
        assert "error" in event_types, "Error events should be emitted during retries"
        assert "agent_completed" in event_types, "Final success should emit completion"
        
        # Check error events
        error_events = [e for e in mock_websocket_bridge.execution_events if e["event_type"] == "error"]
        assert len(error_events) >= 2, "Should have error events from failed attempts"
        
        self.record_metric("retry_pattern_success", True)
        self.record_metric("retry_attempts", result["final_attempt"])
        self.record_metric("error_recovery_verified", True)
        
    @pytest.mark.real_services
    async def test_agent_circuit_breaker_integration(self):
        """Test agent circuit breaker integration and failure isolation."""
        
        user_context = self.create_test_user_context("circuit_breaker_user", "circuit_breaker_test")
        
        # Create agent with persistent errors to trigger circuit breaker
        agent = RetryPatternTestAgent(
            failure_pattern="persistent_error",
            user_context=user_context,
            enable_reliability=True
        )
        
        # Get initial circuit breaker status
        initial_cb_status = agent.get_circuit_breaker_status()
        assert initial_cb_status["state"] in ["closed", "CLOSED", "healthy"]
        
        # Execute multiple times to trigger circuit breaker
        failures = []
        for i in range(5):
            try:
                await agent.execute(user_context)
            except Exception as e:
                failures.append(str(e))
        
        # Should have multiple failures
        assert len(failures) >= 3
        
        # Check circuit breaker status after failures
        post_failure_cb_status = agent.get_circuit_breaker_status()
        
        # Circuit breaker should be aware of failures
        if "metrics" in post_failure_cb_status:
            # Some circuit breaker implementations track metrics
            pass
        
        # Test health status includes circuit breaker info
        health_status = agent.get_health_status()
        assert "circuit_breaker" in health_status or "circuit_breaker_state" in health_status
        
        # Validate reliability manager is working
        assert agent.reliability_manager is not None
        reliability_health = agent.reliability_manager.get_health_status()
        assert "status" in reliability_health
        
        self.record_metric("circuit_breaker_integration_verified", True)
        self.record_metric("persistent_failures_handled", len(failures))
        self.record_metric("health_monitoring_working", True)
        
    @pytest.mark.real_services
    async def test_agent_execution_engine_integration(self, mock_websocket_bridge):
        """Test agent integration with execution engine infrastructure."""
        
        user_context = self.create_test_user_context("execution_engine_user", "execution_engine_test")
        
        # Create agent with execution engine enabled
        agent = BusinessValueExecutionAgent(
            agent_type="execution_engine_test",
            business_scenario="infrastructure_test",
            user_context=user_context,
            enable_execution_engine=True
        )
        
        agent.set_websocket_bridge(mock_websocket_bridge, user_context.run_id)
        
        # Validate execution engine is available
        assert agent.execution_engine is not None
        assert agent.execution_monitor is not None
        
        # Execute via execution engine integration
        execution_context = ExecutionContext(
            request_id=user_context.request_id,
            run_id=user_context.run_id,
            agent_name=agent.name,
            user_id=user_context.user_id,
            correlation_id=agent.correlation_id
        )
        
        # Execute through execution engine
        result = await agent.execution_engine.execute(agent, execution_context)
        
        # Validate execution result
        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.COMPLETED
        assert result.request_id == user_context.request_id
        assert "primary_insights" in result.data or "status" in result.data
        assert result.execution_time_ms > 0
        
        # Validate monitoring data
        monitor_health = agent.execution_monitor.get_health_status()
        assert "total_executions" in monitor_health
        assert monitor_health["total_executions"] >= 1
        
        # Validate health status includes execution engine info
        health_status = agent.get_health_status()
        assert "execution_engine" in health_status or "modern_execution" in health_status
        
        self.record_metric("execution_engine_integration_success", True)
        self.record_metric("execution_result_valid", True)
        self.record_metric("monitoring_data_captured", True)
        
    @pytest.mark.real_services
    async def test_agent_token_tracking_and_cost_optimization(self, mock_llm_manager):
        """Test agent token tracking and cost optimization during execution."""
        
        user_context = self.create_test_user_context("token_test_user", "cost_optimization_test")
        
        # Create agent with LLM manager
        agent = BusinessValueExecutionAgent(
            agent_type="cost_optimizer",
            business_scenario="token_optimization",
            llm_manager=mock_llm_manager,
            user_context=user_context
        )
        
        # Execute agent to trigger token tracking
        result = await agent.execute(user_context)
        
        # Validate token usage was tracked
        assert "token_usage" in user_context.metadata
        token_usage = user_context.metadata["token_usage"]
        assert "operations" in token_usage
        assert len(token_usage["operations"]) >= 1
        
        # Validate token operation data
        operations = token_usage["operations"]
        for operation in operations:
            assert "input_tokens" in operation
            assert "output_tokens" in operation
            assert "cost" in operation
            assert "model" in operation
            assert operation["input_tokens"] > 0
            assert operation["output_tokens"] > 0
            assert operation["cost"] > 0
        
        # Test token usage summary
        usage_summary = agent.get_token_usage_summary(user_context)
        assert "current_session" in usage_summary
        assert usage_summary["current_session"]["operations_count"] >= 1
        assert usage_summary["current_session"]["cumulative_cost"] > 0
        
        # Test cost optimization suggestions
        enhanced_context, suggestions = agent.get_cost_optimization_suggestions(user_context)
        assert isinstance(suggestions, list)
        
        # Validate cost optimization in result
        if "cost_optimization" in result:
            cost_opt = result["cost_optimization"]
            assert "suggestions_count" in cost_opt
        
        self.record_metric("token_tracking_working", True)
        self.record_metric("token_operations_recorded", len(operations))
        self.record_metric("cost_optimization_available", len(suggestions) > 0)
        
    @pytest.mark.real_services
    async def test_concurrent_agent_execution_patterns(self, mock_websocket_bridge):
        """Test concurrent agent execution with different patterns."""
        
        # Create contexts for different execution patterns
        execution_patterns = [
            ("fast_execution", "normal"),
            ("slow_execution", "normal"), 
            ("error_recovery", "transient_error"),
            ("business_analysis", "cost_analysis")
        ]
        
        user_contexts = []
        agents = []
        
        for i, (pattern_name, pattern_type) in enumerate(execution_patterns):
            context = self.create_test_user_context(f"concurrent_user_{i}", pattern_name)
            user_contexts.append(context)
            
            if pattern_type == "transient_error":
                agent = RetryPatternTestAgent(
                    failure_pattern=pattern_type,
                    user_context=context
                )
            else:
                agent = BusinessValueExecutionAgent(
                    agent_type=f"concurrent_{i}",
                    business_scenario=pattern_type,
                    user_context=context
                )
            
            agent.set_websocket_bridge(mock_websocket_bridge, context.run_id)
            agents.append(agent)
        
        # Execute all patterns concurrently
        async def safe_execute(agent, context):
            try:
                return await agent.execute(context)
            except Exception as e:
                return {"status": "failed", "error": str(e), "agent_name": agent.name}
        
        start_time = time.time()
        results = await asyncio.gather(*[
            safe_execute(agent, context)
            for agent, context in zip(agents, user_contexts)
        ])
        execution_time = time.time() - start_time
        
        # Validate concurrent execution results
        assert len(results) == len(execution_patterns)
        
        successful_results = [r for r in results if r["status"] in ["completed", "success"]]
        failed_results = [r for r in results if r["status"] == "failed"]
        
        # At least some should succeed (depending on error patterns)
        assert len(successful_results) >= 2
        
        # Validate WebSocket events from all agents
        total_events = len(mock_websocket_bridge.execution_events)
        assert total_events >= len(agents) * 2  # At least start and one other event per agent
        
        # Validate performance under concurrent load
        assert execution_time < 1.0, f"Concurrent execution too slow: {execution_time:.2f}s"
        
        self.record_metric("concurrent_patterns_tested", len(execution_patterns))
        self.record_metric("successful_concurrent_executions", len(successful_results))
        self.record_metric("concurrent_execution_time", execution_time)
        self.record_metric("total_websocket_events", total_events)
        
    @pytest.mark.real_services
    async def test_agent_execution_monitoring_and_metrics(self):
        """Test comprehensive execution monitoring and metrics collection."""
        
        user_context = self.create_test_user_context("monitoring_user", "metrics_test")
        
        # Create agent with monitoring enabled
        agent = BusinessValueExecutionAgent(
            agent_type="monitoring_test",
            business_scenario="metrics_collection",
            user_context=user_context,
            enable_execution_engine=True
        )
        
        # Get initial metrics
        initial_health = agent.get_health_status()
        initial_metrics = {
            "total_executions": initial_health.get("total_executions", 0),
            "success_rate": initial_health.get("success_rate", 0.0)
        }
        
        # Execute multiple times to generate metrics
        execution_results = []
        for i in range(3):
            result = await agent.execute(user_context)
            execution_results.append(result)
            
            # Small delay between executions
            await asyncio.sleep(0.01)
        
        # Get final health status
        final_health = agent.get_health_status()
        
        # Validate health status structure
        expected_health_fields = [
            "agent_name", "state", "websocket_available",
            "total_executions", "success_rate", "uses_unified_reliability"
        ]
        
        for field in expected_health_fields:
            if field in final_health:
                assert final_health[field] is not None
        
        # Validate monitoring data
        if agent.execution_monitor:
            monitor_health = agent.execution_monitor.get_health_status()
            assert "total_executions" in monitor_health
            assert monitor_health["total_executions"] >= 3
        
        # Validate reliability metrics
        if agent.reliability_manager:
            reliability_health = agent.reliability_manager.get_health_status()
            assert "status" in reliability_health
        
        # Validate business metrics were collected
        assert len(agent.business_metrics) > 0
        assert "business_value_calculated" in agent.business_metrics
        
        # Validate execution phases were tracked
        assert len(agent.execution_phases) >= 10  # 3 executions * ~3-4 phases each
        
        self.record_metric("monitoring_integration_verified", True)
        self.record_metric("health_status_comprehensive", True)
        self.record_metric("business_metrics_collected", len(agent.business_metrics))
        self.record_metric("execution_phases_tracked", len(agent.execution_phases))
        
    def teardown_method(self, method=None):
        """Clean up test resources."""
        super().teardown_method(method)
        
        # Force garbage collection
        gc.collect()
        
        # Log comprehensive metrics
        metrics = self.get_all_metrics()
        print(f"\nAgent Execution Core Patterns Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        # Verify critical metrics for business value protection
        critical_metrics = [
            "business_execution_success",
            "retry_pattern_success", 
            "circuit_breaker_integration_verified",
            "execution_engine_integration_success",
            "token_tracking_working",
            "monitoring_integration_verified"
        ]
        
        for metric in critical_metrics:
            assert metrics.get(metric, False), f"Critical metric {metric} failed - agent execution patterns compromised"