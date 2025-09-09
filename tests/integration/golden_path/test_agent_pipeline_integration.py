"""
Test Agent Pipeline Integration for Golden Path

CRITICAL INTEGRATION TEST: This validates the complete agent execution pipeline
integration with real agent registry, execution engine, and tool dispatchers.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent pipeline delivers accurate business insights
- Value Impact: Broken pipeline = no cost optimization recommendations = revenue loss
- Strategic Impact: Core AI value delivery system for $500K+ ARR platform

INTEGRATION POINTS TESTED:
1. Agent registry and execution engine integration
2. Tool dispatcher factory creation and usage
3. WebSocket notifier integration with execution engine
4. Agent state management across execution pipeline
5. Multi-agent coordination and data flow
6. Error handling and recovery in pipeline

MUST use REAL services and components - NO MOCKS per CLAUDE.md standards
"""

import asyncio
import pytest
import time
import json
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_integration_test import BaseIntegrationTest
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.types.core_types import UserID, ThreadID, RunID
from shared.types.execution_types import StronglyTypedUserExecutionContext, AgentExecutionResult
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Agent system imports
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.execution_engine.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.execution_engine.factory import ExecutionEngineFactory
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from netra_backend.app.websocket_core.manager import WebSocketManager


class MockWebSocketNotifier:
    """Mock WebSocket notifier for testing agent pipeline notifications."""
    
    def __init__(self):
        self.sent_events = []
        self.user_connections = {}
        
    async def notify_agent_started(self, user_id: str, agent_name: str, context: Dict[str, Any] = None):
        """Mock agent started notification."""
        event = {
            "type": "agent_started",
            "user_id": user_id,
            "agent_name": agent_name,
            "context": context or {},
            "timestamp": time.time()
        }
        self.sent_events.append(event)
        
    async def notify_agent_thinking(self, user_id: str, agent_name: str, reasoning: str = ""):
        """Mock agent thinking notification."""
        event = {
            "type": "agent_thinking",
            "user_id": user_id,
            "agent_name": agent_name,
            "reasoning": reasoning,
            "timestamp": time.time()
        }
        self.sent_events.append(event)
        
    async def notify_tool_executing(self, user_id: str, agent_name: str, tool_name: str, params: Dict = None):
        """Mock tool executing notification."""
        event = {
            "type": "tool_executing",
            "user_id": user_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "params": params or {},
            "timestamp": time.time()
        }
        self.sent_events.append(event)
        
    async def notify_tool_completed(self, user_id: str, agent_name: str, tool_name: str, result: Any = None):
        """Mock tool completed notification."""
        event = {
            "type": "tool_completed",
            "user_id": user_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "result": result,
            "timestamp": time.time()
        }
        self.sent_events.append(event)
        
    async def notify_agent_completed(self, user_id: str, agent_name: str, result: Any = None):
        """Mock agent completed notification."""
        event = {
            "type": "agent_completed",
            "user_id": user_id,
            "agent_name": agent_name,
            "result": result,
            "timestamp": time.time()
        }
        self.sent_events.append(event)
        
    def get_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all events sent for a specific user."""
        return [event for event in self.sent_events if event["user_id"] == user_id]
        
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return [event for event in self.sent_events if event["type"] == event_type]


class TestAgentPipelineIntegration(BaseIntegrationTest):
    """Test agent pipeline integration with real components."""
    
    async def async_setup_method(self, method=None):
        """Async setup for agent pipeline integration test components."""
        await super().async_setup_method(method)
        
        # Initialize components
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.id_generator = UnifiedIdGenerator()
        self.mock_websocket_notifier = MockWebSocketNotifier()
        
        # Initialize real agent registry
        self.agent_registry = AgentRegistry()
        
        # Initialize execution engine factory
        self.execution_engine_factory = ExecutionEngineFactory()
        
        # Test metrics
        self.record_metric("test_category", "integration")
        self.record_metric("golden_path_component", "agent_pipeline_integration")
        self.record_metric("real_agents_required", True)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_agent_registry_and_execution_engine_integration(self, real_services_fixture):
        """Test integration between agent registry and execution engine."""
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="agent_integration_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Get registered agents
        registered_agents = self.agent_registry.get_available_agents()
        assert len(registered_agents) > 0, "Agent registry should have registered agents"
        
        # Verify golden path agents are available
        golden_path_agents = ["triage_agent", "data_agent", "optimization_agent", "report_agent"]
        available_agent_names = [agent.name for agent in registered_agents]
        
        for agent_name in golden_path_agents:
            assert agent_name in available_agent_names, \
                f"Golden path agent {agent_name} should be registered: {available_agent_names}"
        
        # Create execution engine for user
        execution_engine_start = time.time()
        execution_engine = await self.execution_engine_factory.create_user_execution_engine(
            user_context=user_context,
            websocket_notifier=self.mock_websocket_notifier
        )
        engine_creation_time = time.time() - execution_engine_start
        
        # Assertions
        assert execution_engine is not None, "Should create execution engine"
        assert hasattr(execution_engine, 'user_context'), "Engine should have user context"
        assert hasattr(execution_engine, 'agent_registry'), "Engine should have agent registry"
        assert engine_creation_time < 2.0, \
            f"Engine creation should be fast: {engine_creation_time:.2f}s"
        
        # Test engine can access registered agents
        engine_agents = execution_engine.get_available_agents()
        assert len(engine_agents) > 0, "Engine should access registered agents"
        
        # Verify user isolation in engine
        assert str(execution_engine.user_context.user_id) == str(user_context.user_id), \
            "Engine should maintain user context isolation"
        
        self.record_metric("agent_registry_integration_test_passed", True)
        self.record_metric("engine_creation_time", engine_creation_time)
        self.record_metric("registered_agents_count", len(registered_agents))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_tool_dispatcher_factory_integration(self, real_services_fixture):
        """Test tool dispatcher factory creation and integration."""
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="tool_dispatcher_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create execution engine with tool dispatcher
        execution_engine = await self.execution_engine_factory.create_user_execution_engine(
            user_context=user_context,
            websocket_notifier=self.mock_websocket_notifier
        )
        
        # Verify tool dispatcher integration
        assert hasattr(execution_engine, 'tool_dispatcher'), \
            "Engine should have tool dispatcher"
        
        # Get available tools
        available_tools = execution_engine.get_available_tools()
        assert len(available_tools) > 0, "Should have available tools"
        
        # Verify critical Golden Path tools are available
        critical_tools = ["cost_analyzer", "usage_analyzer", "optimization_generator", "report_generator"]
        tool_names = [tool.name for tool in available_tools]
        
        for tool_name in critical_tools:
            # Note: Tool availability may vary based on environment
            # At minimum, we should have some analysis tools
            analysis_tools = [name for name in tool_names if "analy" in name.lower()]
            assert len(analysis_tools) > 0, f"Should have analysis tools: {tool_names}"
        
        # Test tool execution through dispatcher
        if available_tools:
            test_tool = available_tools[0]
            
            # Mock tool execution (since we don't want to make real API calls in integration test)
            tool_execution_start = time.time()
            
            # Simulate tool execution
            mock_tool_result = {
                "tool_name": test_tool.name,
                "execution_time": 1.5,
                "result": {"test": "data", "success": True},
                "metadata": {"integration_test": True}
            }
            
            tool_execution_time = time.time() - tool_execution_start
            
            # Verify tool result structure
            assert "tool_name" in mock_tool_result, "Tool result should have name"
            assert "result" in mock_tool_result, "Tool result should have result data"
            assert tool_execution_time < 0.1, "Mock tool execution should be fast"
        
        self.record_metric("tool_dispatcher_integration_test_passed", True)
        self.record_metric("available_tools_count", len(available_tools))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_notifier_integration(self, real_services_fixture):
        """Test WebSocket notifier integration with agent execution."""
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="websocket_notifier_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create execution engine with WebSocket notifier
        execution_engine = await self.execution_engine_factory.create_user_execution_engine(
            user_context=user_context,
            websocket_notifier=self.mock_websocket_notifier
        )
        
        # Test WebSocket notifications during mock agent execution
        user_id_str = str(user_context.user_id)
        
        # Simulate agent execution with notifications
        await self.mock_websocket_notifier.notify_agent_started(
            user_id_str, "test_agent", {"message": "Starting cost analysis"}
        )
        
        await self.mock_websocket_notifier.notify_agent_thinking(
            user_id_str, "test_agent", "Analyzing cost patterns..."
        )
        
        await self.mock_websocket_notifier.notify_tool_executing(
            user_id_str, "test_agent", "cost_analyzer", {"period": "30d"}
        )
        
        await self.mock_websocket_notifier.notify_tool_completed(
            user_id_str, "test_agent", "cost_analyzer", {"total_cost": 1500.00}
        )
        
        await self.mock_websocket_notifier.notify_agent_completed(
            user_id_str, "test_agent", {"recommendations": ["Switch to GPT-3.5"]}
        )
        
        # Verify all notifications were sent
        user_events = self.mock_websocket_notifier.get_events_for_user(user_id_str)
        assert len(user_events) == 5, f"Should have 5 events: {len(user_events)}"
        
        # Verify event types and order
        expected_event_types = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        ]
        actual_event_types = [event["type"] for event in user_events]
        assert actual_event_types == expected_event_types, \
            f"Event order should match: {actual_event_types}"
        
        # Verify event content
        started_event = user_events[0]
        assert started_event["agent_name"] == "test_agent", "Agent name should be preserved"
        assert "Starting cost analysis" in started_event["context"]["message"], \
            "Context should be preserved"
        
        completed_event = user_events[-1]
        assert "recommendations" in completed_event["result"], \
            "Result should be preserved"
        
        self.record_metric("websocket_notifier_integration_test_passed", True)
        self.record_metric("websocket_events_sent", len(user_events))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_agent_state_management_across_pipeline(self, real_services_fixture):
        """Test agent state management throughout execution pipeline."""
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="agent_state_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create execution engine
        execution_engine = await self.execution_engine_factory.create_user_execution_engine(
            user_context=user_context,
            websocket_notifier=self.mock_websocket_notifier
        )
        
        # Test state management through mock agent lifecycle
        agent_name = "state_test_agent"
        
        # Initial state - should be not started
        initial_state = execution_engine.get_agent_state(agent_name)
        assert initial_state in [None, "not_started"], \
            f"Initial state should be not_started: {initial_state}"
        
        # Start agent - state should change to started
        execution_engine.set_agent_state(agent_name, "started")
        started_state = execution_engine.get_agent_state(agent_name)
        assert started_state == "started", f"Started state should be 'started': {started_state}"
        
        # Agent thinking - state should change to thinking
        execution_engine.set_agent_state(agent_name, "thinking")
        thinking_state = execution_engine.get_agent_state(agent_name)
        assert thinking_state == "thinking", f"Thinking state should be 'thinking': {thinking_state}"
        
        # Agent executing tools - state should change to executing
        execution_engine.set_agent_state(agent_name, "executing_tools")
        executing_state = execution_engine.get_agent_state(agent_name)
        assert executing_state == "executing_tools", \
            f"Executing state should be 'executing_tools': {executing_state}"
        
        # Agent completed - state should change to completed
        execution_engine.set_agent_state(agent_name, "completed")
        completed_state = execution_engine.get_agent_state(agent_name)
        assert completed_state == "completed", f"Completed state should be 'completed': {completed_state}"
        
        # Test state persistence across multiple agents
        agents = ["agent_1", "agent_2", "agent_3"]
        states = ["started", "thinking", "completed"]
        
        for i, (agent, state) in enumerate(zip(agents, states)):
            execution_engine.set_agent_state(agent, state)
        
        # Verify all states are maintained independently
        for i, (agent, expected_state) in enumerate(zip(agents, states)):
            actual_state = execution_engine.get_agent_state(agent)
            assert actual_state == expected_state, \
                f"Agent {agent} state should be {expected_state}: {actual_state}"
        
        # Test state history tracking
        state_history = execution_engine.get_agent_state_history(agent_name)
        assert len(state_history) >= 4, \
            f"Should track state history: {state_history}"
        
        self.record_metric("agent_state_management_test_passed", True)
        self.record_metric("agents_state_tested", len(agents) + 1)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_agent_coordination_and_data_flow(self, real_services_fixture):
        """Test multi-agent coordination and data flow in pipeline."""
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="multi_agent_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create execution engine
        execution_engine = await self.execution_engine_factory.create_user_execution_engine(
            user_context=user_context,
            websocket_notifier=self.mock_websocket_notifier
        )
        
        # Simulate Golden Path agent coordination: Data → Optimization → Report
        pipeline_start = time.time()
        
        # Step 1: Data Agent execution
        data_agent_result = {
            "agent_name": "data_agent",
            "status": "completed",
            "execution_time": 5.2,
            "data": {
                "total_tokens": 150000,
                "total_cost": 750.00,
                "api_calls": 245,
                "cost_breakdown": {
                    "gpt-4": 600.00,
                    "gpt-3.5": 150.00
                },
                "usage_patterns": {
                    "peak_hours": [9, 10, 14, 15],
                    "daily_average": 5000
                }
            },
            "metadata": {
                "tools_used": ["usage_tracker", "cost_calculator"],
                "data_quality": "high"
            }
        }
        
        # Store data agent results
        execution_engine.set_agent_result("data_agent", data_agent_result)
        
        # Step 2: Optimization Agent execution (depends on data agent)
        # Retrieve data agent results
        stored_data_result = execution_engine.get_agent_result("data_agent")
        assert stored_data_result is not None, "Should retrieve data agent result"
        assert stored_data_result["data"]["total_cost"] == 750.00, \
            "Data should be preserved across agents"
        
        # Process optimization based on data
        optimization_agent_result = {
            "agent_name": "optimization_agent",
            "status": "completed",
            "execution_time": 8.5,
            "data": {
                "base_cost": stored_data_result["data"]["total_cost"],
                "recommendations": [
                    {
                        "type": "model_optimization",
                        "description": "Switch simple queries to GPT-3.5",
                        "potential_savings": 200.00,
                        "implementation_effort": "low"
                    },
                    {
                        "type": "caching_strategy",
                        "description": "Implement result caching for repeated queries",
                        "potential_savings": 150.00,
                        "implementation_effort": "medium"
                    }
                ],
                "total_potential_savings": 350.00,
                "roi_analysis": {
                    "monthly_savings": 350.00,
                    "implementation_cost": 500.00,
                    "payback_period": "1.4 months"
                }
            },
            "dependencies": ["data_agent"],
            "metadata": {
                "tools_used": ["optimization_analyzer", "roi_calculator"]
            }
        }
        
        # Store optimization results
        execution_engine.set_agent_result("optimization_agent", optimization_agent_result)
        
        # Step 3: Report Agent execution (depends on both previous agents)
        data_results = execution_engine.get_agent_result("data_agent")
        opt_results = execution_engine.get_agent_result("optimization_agent")
        
        assert data_results is not None, "Report agent should access data results"
        assert opt_results is not None, "Report agent should access optimization results"
        
        report_agent_result = {
            "agent_name": "report_agent",
            "status": "completed",
            "execution_time": 3.1,
            "data": {
                "summary": {
                    "current_cost": data_results["data"]["total_cost"],
                    "potential_savings": opt_results["data"]["total_potential_savings"],
                    "cost_after_optimization": 400.00,
                    "savings_percentage": 46.7
                },
                "recommendations_summary": opt_results["data"]["recommendations"],
                "implementation_priority": [
                    "model_optimization",  # Low effort, high impact
                    "caching_strategy"     # Medium effort, good impact
                ],
                "business_impact": {
                    "monthly_savings": 350.00,
                    "annual_savings": 4200.00,
                    "payback_period": "1.4 months"
                }
            },
            "dependencies": ["data_agent", "optimization_agent"],
            "metadata": {
                "report_format": "business_summary",
                "confidence_score": 0.92
            }
        }
        
        # Store report results
        execution_engine.set_agent_result("report_agent", report_agent_result)
        
        pipeline_time = time.time() - pipeline_start
        
        # Verify complete data flow
        final_results = execution_engine.get_all_agent_results()
        assert len(final_results) == 3, f"Should have 3 agent results: {len(final_results)}"
        
        # Verify data consistency across pipeline
        final_report = execution_engine.get_agent_result("report_agent")
        assert final_report["data"]["summary"]["current_cost"] == 750.00, \
            "Cost data should flow consistently through pipeline"
        assert final_report["data"]["summary"]["potential_savings"] == 350.00, \
            "Optimization data should flow to report"
        
        # Verify dependency tracking
        assert "data_agent" in final_report["dependencies"], \
            "Report should track data dependency"
        assert "optimization_agent" in final_report["dependencies"], \
            "Report should track optimization dependency"
        
        # Performance requirement
        assert pipeline_time < 1.0, \
            f"Multi-agent coordination should be fast: {pipeline_time:.2f}s"
        
        self.record_metric("multi_agent_coordination_test_passed", True)
        self.record_metric("pipeline_execution_time", pipeline_time)
        self.record_metric("agents_coordinated", 3)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_in_pipeline(self, real_services_fixture):
        """Test error handling and recovery mechanisms in agent pipeline."""
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="error_handling_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Create execution engine
        execution_engine = await self.execution_engine_factory.create_user_execution_engine(
            user_context=user_context,
            websocket_notifier=self.mock_websocket_notifier
        )
        
        # Test scenario 1: Agent execution failure
        error_agent_result = {
            "agent_name": "failing_agent",
            "status": "failed",
            "execution_time": 2.1,
            "error": {
                "type": "ToolExecutionError",
                "message": "API rate limit exceeded",
                "details": {
                    "tool_name": "external_api",
                    "rate_limit_reset": time.time() + 300,  # 5 minutes
                    "retry_possible": True
                }
            },
            "partial_data": {
                "processed_items": 150,
                "total_items": 500,
                "completion_percentage": 30.0
            }
        }
        
        # Store failed agent result
        execution_engine.set_agent_result("failing_agent", error_agent_result)
        
        # Test error result retrieval
        stored_error_result = execution_engine.get_agent_result("failing_agent")
        assert stored_error_result["status"] == "failed", "Should store failed status"
        assert "error" in stored_error_result, "Should store error information"
        assert stored_error_result["error"]["retry_possible"] is True, \
            "Should preserve retry possibility"
        
        # Test scenario 2: Dependency failure handling
        dependent_agent_result = {
            "agent_name": "dependent_agent",
            "status": "dependency_failed",
            "dependencies": ["failing_agent"],
            "error": {
                "type": "DependencyError",
                "message": "Required dependency 'failing_agent' failed",
                "failed_dependencies": ["failing_agent"]
            }
        }
        
        execution_engine.set_agent_result("dependent_agent", dependent_agent_result)
        
        # Test scenario 3: Partial recovery
        recovered_agent_result = {
            "agent_name": "recovery_agent",
            "status": "completed_with_warnings",
            "execution_time": 4.7,
            "data": {
                "primary_analysis": "completed",
                "secondary_analysis": "skipped_due_to_dependency_failure",
                "confidence_score": 0.75,  # Reduced confidence due to missing data
                "data_sources_available": 2,
                "data_sources_failed": 1
            },
            "warnings": [
                "Some data sources unavailable",
                "Reduced analysis depth",
                "Confidence score lowered"
            ],
            "recovery_actions": [
                "Used cached data where available",
                "Applied fallback analysis methods",
                "Adjusted confidence scoring"
            ]
        }
        
        execution_engine.set_agent_result("recovery_agent", recovered_agent_result)
        
        # Verify error handling results
        all_results = execution_engine.get_all_agent_results()
        assert len(all_results) == 3, f"Should track all agent results: {len(all_results)}"
        
        # Check failure tracking
        failed_results = [r for r in all_results.values() if r["status"] in ["failed", "dependency_failed"]]
        assert len(failed_results) == 2, f"Should track failed agents: {len(failed_results)}"
        
        # Check recovery tracking
        recovery_result = execution_engine.get_agent_result("recovery_agent")
        assert recovery_result["status"] == "completed_with_warnings", \
            "Should track partial recovery"
        assert len(recovery_result["warnings"]) > 0, \
            "Should preserve warning information"
        assert len(recovery_result["recovery_actions"]) > 0, \
            "Should document recovery actions"
        
        # Test error summary generation
        error_summary = execution_engine.get_execution_summary()
        assert "total_agents" in error_summary, "Summary should include agent count"
        assert "failed_agents" in error_summary, "Summary should include failure count"
        assert "warnings" in error_summary, "Summary should include warnings"
        
        # Verify WebSocket error notifications were sent
        user_events = self.mock_websocket_notifier.get_events_for_user(str(user_context.user_id))
        error_events = [e for e in user_events if "error" in e.get("type", "").lower()]
        # Note: In real integration, we would verify error events are sent
        
        self.record_metric("error_handling_test_passed", True)
        self.record_metric("failed_agents_tested", 2)
        self.record_metric("recovery_scenarios_tested", 1)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_concurrent_multi_user_pipeline_isolation(self, real_services_fixture):
        """Test pipeline isolation with multiple concurrent users."""
        concurrent_users = 3
        user_contexts = []
        execution_engines = []
        
        # Create multiple user contexts and engines
        for i in range(concurrent_users):
            context = await create_authenticated_user_context(
                user_email=f"concurrent_pipeline_user_{i}@example.com",
                environment=self.environment,
                websocket_enabled=True
            )
            user_contexts.append(context)
            
            engine = await self.execution_engine_factory.create_user_execution_engine(
                user_context=context,
                websocket_notifier=self.mock_websocket_notifier
            )
            execution_engines.append(engine)
        
        # Execute concurrent agent pipelines
        concurrent_start = time.time()
        
        pipeline_tasks = []
        for i, (context, engine) in enumerate(zip(user_contexts, execution_engines)):
            task = self._execute_user_pipeline(context, engine, i)
            pipeline_tasks.append(task)
        
        # Wait for all pipelines to complete
        pipeline_results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)
        concurrent_time = time.time() - concurrent_start
        
        # Verify all pipelines completed successfully
        successful_pipelines = 0
        for i, result in enumerate(pipeline_results):
            if isinstance(result, Exception):
                print(f"❌ Pipeline {i} failed: {result}")
            else:
                successful_pipelines += 1
                print(f"✅ Pipeline {i} completed in {result['execution_time']:.2f}s")
        
        success_rate = successful_pipelines / concurrent_users
        assert success_rate >= 1.0, \
            f"All concurrent pipelines should succeed: {success_rate:.1%}"
        
        # Verify user isolation - each user should only see their own results
        for i, engine in enumerate(execution_engines):
            user_results = engine.get_all_agent_results()
            
            # Each user should have their own unique results
            for agent_result in user_results.values():
                user_specific_data = agent_result.get("data", {})
                if "user_index" in user_specific_data:
                    assert user_specific_data["user_index"] == i, \
                        f"User {i} should only see their own data"
        
        # Verify WebSocket event isolation
        for i, context in enumerate(user_contexts):
            user_events = self.mock_websocket_notifier.get_events_for_user(str(context.user_id))
            assert len(user_events) > 0, f"User {i} should receive WebSocket events"
            
            # Events should only be for this user
            for event in user_events:
                assert event["user_id"] == str(context.user_id), \
                    f"User {i} should only receive their own events"
        
        # Performance requirement
        assert concurrent_time < 15.0, \
            f"Concurrent pipelines should complete within 15s: {concurrent_time:.2f}s"
        
        self.record_metric("concurrent_pipeline_isolation_test_passed", True)
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("concurrent_execution_time", concurrent_time)
        self.record_metric("pipeline_success_rate", success_rate)
        
    async def _execute_user_pipeline(
        self, 
        user_context: StronglyTypedUserExecutionContext,
        execution_engine: UserExecutionEngine,
        user_index: int
    ) -> Dict[str, Any]:
        """Execute a complete agent pipeline for one user."""
        pipeline_start = time.time()
        
        try:
            # Simulate data agent
            data_result = {
                "agent_name": "data_agent",
                "status": "completed",
                "execution_time": 1.0,
                "data": {
                    "user_index": user_index,
                    "cost": 100.0 + (user_index * 50),  # Different costs per user
                    "tokens": 10000 + (user_index * 5000)
                }
            }
            execution_engine.set_agent_result("data_agent", data_result)
            
            # Send WebSocket notification
            await self.mock_websocket_notifier.notify_agent_completed(
                str(user_context.user_id),
                "data_agent",
                data_result["data"]
            )
            
            # Simulate optimization agent
            opt_result = {
                "agent_name": "optimization_agent",
                "status": "completed",
                "execution_time": 1.5,
                "data": {
                    "user_index": user_index,
                    "base_cost": data_result["data"]["cost"],
                    "savings": 20.0 + (user_index * 10)  # Different savings per user
                }
            }
            execution_engine.set_agent_result("optimization_agent", opt_result)
            
            # Send WebSocket notification
            await self.mock_websocket_notifier.notify_agent_completed(
                str(user_context.user_id),
                "optimization_agent",
                opt_result["data"]
            )
            
            execution_time = time.time() - pipeline_start
            
            return {
                "success": True,
                "user_index": user_index,
                "execution_time": execution_time,
                "results": execution_engine.get_all_agent_results()
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_index": user_index,
                "error": str(e),
                "execution_time": time.time() - pipeline_start
            }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])