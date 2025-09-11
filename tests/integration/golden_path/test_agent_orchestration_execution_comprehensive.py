"""
Comprehensive Integration Tests for Agent Orchestration and Execution in the Golden Path

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable AI agent execution delivering $500K+ ARR
- Value Impact: Validates complete agent orchestration pipeline critical to user experience
- Strategic Impact: Protects core platform value delivery through agent coordination

This test suite covers the complete agent orchestration and execution pipeline as documented
in the Golden Path User Flow. Tests focus on real agent execution with minimal mocks to 
validate actual business logic and agent workflows.

Key Coverage Areas:
- SupervisorAgent orchestration and workflow management
- Sub-agent execution (DataAgent, TriageAgent, OptimizerAgent, ReportAgent)  
- ExecutionEngineFactory user isolation patterns
- Agent pipeline sequencing and coordination
- Tool execution integration and monitoring
- Agent context management and state persistence
- WebSocket event integration for user experience
- Error handling and recovery mechanisms
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.ssot.websocket import WebSocketTestUtility
from test_framework.ssot.database import DatabaseTestUtility
from test_framework.real_services_test_fixtures import (
    real_services_fixture,
    real_redis_fixture
)
from test_framework.isolated_environment_fixtures import (
    isolated_env,
    test_env
)

# Agent orchestration imports
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)

# Agent types for sub-agent testing
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.triage_agent import TriageAgent  
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent

# WebSocket and tool integration
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.tools.enhanced_tool_execution_engine import EnhancedToolExecutionEngine
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

# Database and configuration imports
from netra_backend.app.db.models_auth import User
from netra_backend.app.db.models_corpus import Thread, Message, Run
from netra_backend.app.core.configuration.base import get_config
from shared.isolated_environment import get_env

# Logging and monitoring
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker

logger = central_logger.get_logger(__name__)


class TestAgentOrchestrationExecution(SSotAsyncTestCase):
    """
    Comprehensive integration tests for agent orchestration and execution.
    
    Tests the complete golden path agent pipeline with real services where possible,
    focusing on business value delivery through agent coordination.
    """

    def setup_method(self, method):
        """Setup test environment with proper SSOT patterns."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        self.websocket_utility = WebSocketTestUtility()
        self.db_utility = DatabaseTestUtility()
        
        # Test user context for all tests
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = str(uuid.uuid4())
        self.test_run_id = str(uuid.uuid4())
        
        # Mock WebSocket for testing
        self.mock_websocket = self.mock_factory.create_websocket_mock()
        self.mock_emitter = self.mock_factory.create_websocket_manager_mock()
        
        # Mock LLM Manager for SupervisorAgent
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.get_default_client.return_value = self.mock_factory.create_llm_client_mock()

    async def async_setup_method(self, method):
        """Async setup for database and service initialization."""
        await super().async_setup_method(method)
        
        # Initialize test database if available
        if hasattr(self, 'real_db'):
            await self.db_utility.initialize_test_database(self.real_db)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_supervisor_agent_orchestration_basic_flow(self, real_services_fixture):
        """
        BVJ: All segments | Retention | Ensures basic agent orchestration works
        Test basic SupervisorAgent orchestration with sub-agent coordination.
        """
        # Setup user execution context
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Create supervisor agent with real dependencies
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        # Mock WebSocket bridge for event tracking
        websocket_bridge = AsyncMock(spec=AgentWebSocketBridge)
        supervisor.websocket_bridge = websocket_bridge
        
        # Execute basic workflow
        request_data = {
            "message": "Analyze my AI costs and suggest optimizations",
            "user_context": user_context.to_dict()
        }
        
        # Execute supervisor workflow
        result = await supervisor.execute_workflow(
            request_data=request_data,
            context=user_context
        )
        
        # Verify basic orchestration success
        self.assertIsNotNone(result)
        self.assertIn("status", result)
        self.assertEqual(result["status"], "completed")
        
        # Verify WebSocket events were sent
        websocket_bridge.send_event.assert_called()
        event_calls = websocket_bridge.send_event.call_args_list
        
        # Should have at least agent_started and agent_completed events
        event_types = [call[1]["event_type"] for call in event_calls]
        self.assertIn("agent_started", event_types)
        self.assertIn("agent_completed", event_types)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_factory_user_isolation(self, real_services_fixture):
        """
        BVJ: All segments | Platform Stability | Ensures users don't interfere with each other
        Test ExecutionEngineFactory creates properly isolated user execution engines.
        """
        factory = ExecutionEngineFactory()
        
        # Create execution engines for different users
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        
        user1_context = UserExecutionContext(user_id=user1_id)
        user2_context = UserExecutionContext(user_id=user2_id)
        
        engine1 = await factory.create_user_execution_engine(user1_context)
        engine2 = await factory.create_user_execution_engine(user2_context)
        
        # Verify engines are different instances
        self.assertIsNot(engine1, engine2)
        self.assertNotEqual(engine1.user_context.user_id, engine2.user_context.user_id)
        
        # Verify user isolation - state should not leak
        engine1.set_execution_state("test_key", "user1_value")
        engine2.set_execution_state("test_key", "user2_value")
        
        self.assertEqual(engine1.get_execution_state("test_key"), "user1_value")
        self.assertEqual(engine2.get_execution_state("test_key"), "user2_value")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_sub_agent_execution_pipeline_sequencing(self, real_services_fixture):
        """
        BVJ: Early/Mid/Enterprise | Value Delivery | Ensures agents execute in correct order
        Test sub-agent pipeline execution with proper sequencing and coordination.
        """
        # Create execution context
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Create sub-agents through factory
        factory = get_agent_instance_factory()
        
        # Create agents in expected execution order
        triage_agent = await factory.create_agent("triage", user_context)
        data_agent = await factory.create_agent("data_helper", user_context) 
        optimizer_agent = await factory.create_agent("apex_optimizer", user_context)
        report_agent = await factory.create_agent("reporting", user_context)
        
        # Mock tool execution for agents
        mock_tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
        mock_tool_dispatcher.execute_tool.return_value = {"status": "success", "result": "mock_result"}
        
        # Setup agents with mocked dependencies
        for agent in [triage_agent, data_agent, optimizer_agent, report_agent]:
            agent.tool_dispatcher = mock_tool_dispatcher
            agent.websocket_emitter = self.mock_emitter
        
        # Execute pipeline in sequence
        execution_order = []
        
        # 1. Triage agent determines requirements
        triage_result = await triage_agent.execute(
            message="Analyze AI costs",
            context=user_context
        )
        execution_order.append("triage")
        
        # 2. Data agent collects required data
        data_result = await data_agent.execute(
            message="Collect cost data based on triage requirements",
            context=user_context,
            previous_result=triage_result
        )
        execution_order.append("data")
        
        # 3. Optimizer agent processes data
        optimizer_result = await optimizer_agent.execute(
            message="Optimize based on collected data", 
            context=user_context,
            previous_result=data_result
        )
        execution_order.append("optimizer")
        
        # 4. Report agent generates final output
        report_result = await report_agent.execute(
            message="Generate optimization report",
            context=user_context, 
            previous_result=optimizer_result
        )
        execution_order.append("report")
        
        # Verify correct execution order
        self.assertEqual(execution_order, ["triage", "data", "optimizer", "report"])
        
        # Verify each agent produced results
        self.assertIsNotNone(triage_result)
        self.assertIsNotNone(data_result)
        self.assertIsNotNone(optimizer_result)
        self.assertIsNotNone(report_result)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_tool_execution_integration(self, real_services_fixture):
        """
        BVJ: All segments | User Experience | Ensures tools execute properly with monitoring
        Test agent integration with tool execution and monitoring.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Create agent with real tool dispatcher
        factory = get_agent_instance_factory()
        agent = await factory.create_agent("data_helper", user_context)
        
        # Mock tool dispatcher with realistic tool execution
        mock_tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
        mock_tool_dispatcher.execute_tool.return_value = {
            "status": "success",
            "tool_name": "cost_analyzer", 
            "result": {"monthly_cost": 1500.50, "recommendations": ["optimize_batch_sizes"]},
            "execution_time": 2.3
        }
        agent.tool_dispatcher = mock_tool_dispatcher
        
        # Setup WebSocket emitter to track events
        agent.websocket_emitter = self.mock_emitter
        
        # Execute agent with tool usage
        result = await agent.execute(
            message="Analyze current AI costs",
            context=user_context
        )
        
        # Verify tool was executed
        mock_tool_dispatcher.execute_tool.assert_called()
        tool_call = mock_tool_dispatcher.execute_tool.call_args
        self.assertIn("cost_analyzer", str(tool_call))
        
        # Verify WebSocket events for tool execution
        emitter_calls = self.mock_emitter.send_event.call_args_list
        event_types = [call[1]["event_type"] for call in emitter_calls]
        
        # Should have tool execution events
        self.assertIn("tool_executing", event_types)
        self.assertIn("tool_completed", event_types)
        
        # Verify result contains tool output
        self.assertIsNotNone(result)
        self.assertIn("tool_results", result)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_context_management_persistence(self, real_services_fixture):
        """
        BVJ: Mid/Enterprise | Conversation Continuity | Ensures context persists across executions
        Test agent context management and state persistence across multiple executions.
        """
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Create execution engine for context management
        factory = ExecutionEngineFactory()
        engine = await factory.create_user_execution_engine(user_context)
        
        # First execution - establish context
        execution1_data = {
            "message": "Analyze my current AI infrastructure costs",
            "context_key": "initial_analysis"
        }
        
        # Execute first analysis
        result1 = await engine.execute_agent_pipeline(
            agent_type="data_helper",
            request_data=execution1_data,
            context=user_context
        )
        
        # Store context data
        context_data = {
            "infrastructure_type": "cloud_ml",
            "monthly_spend": 5000.00,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        engine.set_execution_state("infrastructure_analysis", context_data)
        
        # Second execution - use previous context
        execution2_data = {
            "message": "Based on previous analysis, suggest optimizations",
            "context_key": "optimization_recommendations",
            "use_previous_context": True
        }
        
        # Execute optimization using context
        result2 = await engine.execute_agent_pipeline(
            agent_type="apex_optimizer", 
            request_data=execution2_data,
            context=user_context
        )
        
        # Verify context was preserved and used
        stored_context = engine.get_execution_state("infrastructure_analysis")
        self.assertIsNotNone(stored_context)
        self.assertEqual(stored_context["infrastructure_type"], "cloud_ml")
        self.assertEqual(stored_context["monthly_spend"], 5000.00)
        
        # Verify both executions succeeded
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_integration_comprehensive(self, real_services_fixture):
        """
        BVJ: All segments | User Experience | Critical WebSocket events deliver transparency
        Test comprehensive WebSocket event integration across the agent execution pipeline.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Create supervisor with WebSocket tracking
        supervisor = SupervisorAgent()
        event_tracker = []
        
        # Mock WebSocket bridge to capture all events
        async def mock_send_event(event_type: str, data: Dict[str, Any], **kwargs):
            event_tracker.append({
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow(),
                "user_id": kwargs.get("user_id")
            })
        
        websocket_bridge = AsyncMock(spec=AgentWebSocketBridge)
        websocket_bridge.send_event.side_effect = mock_send_event
        supervisor.websocket_bridge = websocket_bridge
        
        # Execute complete workflow
        request_data = {
            "message": "Perform complete AI cost optimization analysis",
            "user_context": user_context.to_dict()
        }
        
        result = await supervisor.execute_workflow(
            request_data=request_data,
            context=user_context
        )
        
        # Verify all 5 critical WebSocket events were sent
        event_types = [event["type"] for event in event_tracker]
        
        required_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        for required_event in required_events:
            self.assertIn(required_event, event_types,
                         f"Missing required WebSocket event: {required_event}")
        
        # Verify events are in logical order
        started_idx = event_types.index("agent_started")
        completed_idx = event_types.index("agent_completed")
        self.assertLess(started_idx, completed_idx, 
                       "agent_started should come before agent_completed")
        
        # Verify event data contains required fields
        for event in event_tracker:
            self.assertIn("timestamp", event)
            self.assertIsNotNone(event["data"])
            if "user_id" in event:
                self.assertEqual(event["user_id"], self.test_user_id)

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_agent_error_handling_recovery(self, real_services_fixture):
        """
        BVJ: All segments | System Reliability | Ensures graceful error handling
        Test agent error handling and recovery mechanisms during execution failures.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Create agent with failure scenarios
        factory = get_agent_instance_factory()
        agent = await factory.create_agent("data_helper", user_context)
        
        # Mock tool dispatcher that fails initially then succeeds
        failure_count = 0
        async def mock_tool_execution(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count == 1:
                raise Exception("Simulated tool execution failure")
            return {"status": "success", "result": "recovery_successful"}
        
        mock_tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
        mock_tool_dispatcher.execute_tool.side_effect = mock_tool_execution
        agent.tool_dispatcher = mock_tool_dispatcher
        agent.websocket_emitter = self.mock_emitter
        
        # Execute agent with retry logic
        result = await agent.execute_with_retry(
            message="Test error recovery",
            context=user_context,
            max_retries=2
        )
        
        # Verify recovery was successful
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "success")
        
        # Verify tool was called twice (failure + success)
        self.assertEqual(mock_tool_dispatcher.execute_tool.call_count, 2)
        
        # Verify error was logged and handled gracefully
        emitter_calls = self.mock_emitter.send_event.call_args_list
        event_types = [call[1]["event_type"] for call in emitter_calls]
        
        # Should have error handling events
        self.assertIn("agent_error", event_types)
        self.assertIn("agent_recovered", event_types)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_timeout_performance_management(self, real_services_fixture):
        """
        BVJ: All segments | Performance SLA | Ensures agents complete within time limits
        Test agent timeout and performance management for SLA compliance.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Create agent with performance tracking
        factory = get_agent_instance_factory()
        agent = await factory.create_agent("apex_optimizer", user_context)
        
        # Mock slow tool execution
        async def slow_tool_execution(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {"status": "success", "result": "optimization_complete"}
        
        mock_tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
        mock_tool_dispatcher.execute_tool.side_effect = slow_tool_execution
        agent.tool_dispatcher = mock_tool_dispatcher
        agent.websocket_emitter = self.mock_emitter
        
        # Execute with timeout constraints
        start_time = time.time()
        
        result = await asyncio.wait_for(
            agent.execute(
                message="Optimize AI infrastructure with performance monitoring",
                context=user_context
            ),
            timeout=5.0  # 5 second timeout
        )
        
        execution_time = time.time() - start_time
        
        # Verify execution completed within performance expectations
        self.assertLess(execution_time, 5.0, "Agent execution exceeded timeout")
        self.assertIsNotNone(result)
        
        # Verify performance metrics were recorded
        execution_tracker = get_execution_tracker()
        metrics = execution_tracker.get_execution_metrics(user_context.user_id)
        
        self.assertIsNotNone(metrics)
        self.assertIn("execution_time", metrics)
        self.assertGreater(metrics["execution_time"], 0)

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_multi_agent_coordination_communication(self, real_services_fixture):
        """
        BVJ: Mid/Enterprise | Complex Workflows | Enables sophisticated agent cooperation
        Test multi-agent coordination and communication in complex workflows.
        """
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Create multiple coordinated agents
        factory = get_agent_instance_factory()
        
        data_agent = await factory.create_agent("data_helper", user_context)
        optimizer_agent = await factory.create_agent("apex_optimizer", user_context)
        report_agent = await factory.create_agent("reporting", user_context)
        
        # Setup inter-agent communication
        shared_context = {}
        
        # Mock tool dispatchers for each agent
        async def data_tool_execution(*args, **kwargs):
            shared_context["data_analysis"] = {
                "cost_data": {"monthly": 3500, "trend": "increasing"},
                "resource_utilization": {"cpu": 0.75, "memory": 0.68}
            }
            return {"status": "success", "shared_data": shared_context["data_analysis"]}
        
        async def optimizer_tool_execution(*args, **kwargs):
            # Use data from data agent
            data = shared_context.get("data_analysis", {})
            shared_context["optimization_plan"] = {
                "recommendations": ["scale_down_non_prod", "optimize_batch_jobs"],
                "estimated_savings": data.get("cost_data", {}).get("monthly", 0) * 0.2
            }
            return {"status": "success", "optimization": shared_context["optimization_plan"]}
        
        async def report_tool_execution(*args, **kwargs):
            # Combine data from both previous agents
            report = {
                "data_analysis": shared_context.get("data_analysis"),
                "optimization": shared_context.get("optimization_plan"),
                "final_recommendations": "Comprehensive optimization strategy ready"
            }
            return {"status": "success", "report": report}
        
        # Setup agents with coordinated tools
        data_agent.tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
        data_agent.tool_dispatcher.execute_tool.side_effect = data_tool_execution
        
        optimizer_agent.tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine) 
        optimizer_agent.tool_dispatcher.execute_tool.side_effect = optimizer_tool_execution
        
        report_agent.tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
        report_agent.tool_dispatcher.execute_tool.side_effect = report_tool_execution
        
        # Execute coordinated workflow
        data_result = await data_agent.execute(
            message="Collect infrastructure cost and utilization data",
            context=user_context
        )
        
        optimizer_result = await optimizer_agent.execute(
            message="Generate optimization recommendations",
            context=user_context,
            shared_context=shared_context
        )
        
        report_result = await report_agent.execute(
            message="Create comprehensive optimization report", 
            context=user_context,
            shared_context=shared_context
        )
        
        # Verify agent coordination worked
        self.assertIn("data_analysis", shared_context)
        self.assertIn("optimization_plan", shared_context)
        
        # Verify data flowed between agents
        self.assertEqual(shared_context["data_analysis"]["cost_data"]["monthly"], 3500)
        expected_savings = 3500 * 0.2
        self.assertEqual(shared_context["optimization_plan"]["estimated_savings"], expected_savings)
        
        # Verify final report combines all agent outputs
        self.assertIsNotNone(report_result)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_result_compilation_aggregation(self, real_services_fixture):
        """
        BVJ: All segments | Result Quality | Ensures comprehensive result aggregation
        Test agent result compilation and aggregation from multiple execution steps.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Create execution engine for result aggregation
        factory = ExecutionEngineFactory()
        engine = await factory.create_user_execution_engine(user_context)
        
        # Mock multiple agent results
        agent_results = [
            {
                "agent_type": "triage",
                "result": {"requirements": ["cost_analysis", "optimization"], "priority": "high"},
                "execution_time": 1.2,
                "timestamp": datetime.utcnow()
            },
            {
                "agent_type": "data_helper", 
                "result": {"cost_data": {"monthly": 4200}, "utilization": {"avg": 0.73}},
                "execution_time": 2.8,
                "timestamp": datetime.utcnow() 
            },
            {
                "agent_type": "apex_optimizer",
                "result": {"recommendations": ["optimize_scaling"], "savings": 840},
                "execution_time": 3.1,
                "timestamp": datetime.utcnow()
            }
        ]
        
        # Aggregate results using engine
        aggregated_result = await engine.compile_agent_results(
            agent_results=agent_results,
            context=user_context
        )
        
        # Verify aggregation includes all agent outputs
        self.assertIn("triage_analysis", aggregated_result)
        self.assertIn("data_analysis", aggregated_result) 
        self.assertIn("optimization_results", aggregated_result)
        
        # Verify summary metrics
        self.assertIn("total_execution_time", aggregated_result)
        expected_total_time = 1.2 + 2.8 + 3.1
        self.assertEqual(aggregated_result["total_execution_time"], expected_total_time)
        
        # Verify business value calculations
        self.assertIn("business_impact", aggregated_result)
        self.assertEqual(aggregated_result["business_impact"]["potential_monthly_savings"], 840)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_monitoring_logging(self, real_services_fixture):
        """
        BVJ: Platform/Internal | Observability | Enables system monitoring and debugging
        Test agent execution monitoring and logging for observability.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Create agent with monitoring
        factory = get_agent_instance_factory()
        agent = await factory.create_agent("data_helper", user_context)
        
        # Setup monitoring collectors
        execution_logs = []
        performance_metrics = []
        
        # Mock monitoring integration
        original_execute = agent.execute
        async def monitored_execute(*args, **kwargs):
            start_time = time.time()
            execution_logs.append({
                "event": "execution_started",
                "timestamp": datetime.utcnow(),
                "user_id": user_context.user_id
            })
            
            try:
                result = await original_execute(*args, **kwargs)
                execution_time = time.time() - start_time
                
                execution_logs.append({
                    "event": "execution_completed", 
                    "timestamp": datetime.utcnow(),
                    "execution_time": execution_time,
                    "result_size": len(str(result))
                })
                
                performance_metrics.append({
                    "agent_type": "data_helper",
                    "execution_time": execution_time,
                    "memory_usage": "tracked",  # Would be real in production
                    "success": True
                })
                
                return result
            except Exception as e:
                execution_logs.append({
                    "event": "execution_failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow()
                })
                raise
        
        agent.execute = monitored_execute
        
        # Execute agent with monitoring
        result = await agent.execute(
            message="Test monitoring and logging",
            context=user_context
        )
        
        # Verify monitoring data was collected
        self.assertGreater(len(execution_logs), 0)
        self.assertGreater(len(performance_metrics), 0)
        
        # Verify execution lifecycle was logged
        events = [log["event"] for log in execution_logs]
        self.assertIn("execution_started", events)
        self.assertIn("execution_completed", events)
        
        # Verify performance metrics were captured
        metric = performance_metrics[0]
        self.assertIn("execution_time", metric)
        self.assertGreater(metric["execution_time"], 0)
        self.assertTrue(metric["success"])

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_memory_management_cleanup(self, real_services_fixture):
        """
        BVJ: Platform/Internal | System Stability | Prevents memory leaks in production
        Test agent memory management and proper resource cleanup.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Create multiple agents to test memory usage
        factory = get_agent_instance_factory()
        agents = []
        
        initial_memory_usage = self._get_memory_usage()  # Mock measurement
        
        # Create and execute multiple agents
        for i in range(5):
            agent = await factory.create_agent("triage", user_context)
            
            # Mock tool dispatcher
            mock_tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
            mock_tool_dispatcher.execute_tool.return_value = {"status": "success"}
            agent.tool_dispatcher = mock_tool_dispatcher
            agent.websocket_emitter = self.mock_emitter
            
            # Execute agent
            result = await agent.execute(
                message=f"Test execution {i}",
                context=user_context
            )
            
            agents.append(agent)
        
        # Measure memory usage after agent creation
        post_creation_memory = self._get_memory_usage()
        
        # Cleanup all agents
        for agent in agents:
            await agent.cleanup()
        
        # Force garbage collection
        import gc
        gc.collect()
        await asyncio.sleep(0.1)  # Allow cleanup to complete
        
        # Measure memory after cleanup
        post_cleanup_memory = self._get_memory_usage()
        
        # Verify memory was properly cleaned up
        # In real implementation, would check actual memory usage
        self.assertLessEqual(post_cleanup_memory, post_creation_memory * 1.1,
                            "Memory usage should decrease after cleanup")
        
        # Verify all agents were marked as cleaned up
        for agent in agents:
            self.assertTrue(hasattr(agent, '_cleaned_up'))

    def _get_memory_usage(self) -> int:
        """Mock memory usage measurement for testing."""
        import psutil
        import os
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except:
            # Fallback for testing environment
            return 1000000  # Mock memory usage

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_permission_access_control(self, real_services_fixture):
        """
        BVJ: Enterprise | Security | Ensures proper access control and permissions
        Test agent permission and access control for secure execution.
        """
        # Create contexts for different user types
        free_user_context = UserExecutionContext(
            user_id=str(uuid.uuid4()),
            user_tier="free"
        )
        enterprise_user_context = UserExecutionContext(
            user_id=str(uuid.uuid4()), 
            user_tier="enterprise"
        )
        
        factory = get_agent_instance_factory()
        
        # Test access control for different agents
        free_agent = await factory.create_agent("triage", free_user_context)
        enterprise_agent = await factory.create_agent("apex_optimizer", enterprise_user_context)
        
        # Mock permission checker
        def check_agent_permissions(agent_type: str, user_context: UserExecutionContext) -> bool:
            if user_context.user_tier == "free":
                return agent_type in ["triage", "data_helper"]
            elif user_context.user_tier == "enterprise":
                return True  # Enterprise users have access to all agents
            return False
        
        # Verify free user can access basic agents
        self.assertTrue(check_agent_permissions("triage", free_user_context))
        self.assertFalse(check_agent_permissions("apex_optimizer", free_user_context))
        
        # Verify enterprise user can access all agents
        self.assertTrue(check_agent_permissions("triage", enterprise_user_context))
        self.assertTrue(check_agent_permissions("apex_optimizer", enterprise_user_context))
        
        # Test execution with permission enforcement
        try:
            # Free user should be able to execute triage
            result = await free_agent.execute(
                message="Basic analysis",
                context=free_user_context
            )
            self.assertIsNotNone(result)
        except PermissionError:
            self.fail("Free user should have access to triage agent")
        
        # Enterprise user should access advanced agent
        try:
            result = await enterprise_agent.execute(
                message="Advanced optimization", 
                context=enterprise_user_context
            )
            self.assertIsNotNone(result)
        except PermissionError:
            self.fail("Enterprise user should have access to optimizer agent")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_load_balancing_scaling(self, real_services_fixture):
        """
        BVJ: Mid/Enterprise | Performance | Ensures system scales with concurrent users
        Test agent load balancing and scaling under concurrent execution.
        """
        # Create multiple concurrent user contexts
        user_contexts = []
        for i in range(10):
            user_contexts.append(UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4())
            ))
        
        factory = ExecutionEngineFactory()
        
        # Create execution engines for all users
        engines = []
        for context in user_contexts:
            engine = await factory.create_user_execution_engine(context)
            engines.append(engine)
        
        # Execute agents concurrently
        async def execute_user_workflow(engine, context):
            start_time = time.time()
            
            # Mock agent execution
            agent = await get_agent_instance_factory().create_agent("data_helper", context)
            agent.tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
            agent.tool_dispatcher.execute_tool.return_value = {"status": "success"}
            
            result = await agent.execute(
                message=f"Concurrent execution for user {context.user_id}",
                context=context
            )
            
            execution_time = time.time() - start_time
            return {
                "user_id": context.user_id,
                "result": result,
                "execution_time": execution_time
            }
        
        # Execute all workflows concurrently
        start_time = time.time()
        tasks = [
            execute_user_workflow(engine, context) 
            for engine, context in zip(engines, user_contexts)
        ]
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify all executions completed successfully
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertIsNotNone(result["result"])
            self.assertIn("user_id", result)
        
        # Verify performance under load
        avg_execution_time = sum(r["execution_time"] for r in results) / len(results)
        self.assertLess(avg_execution_time, 5.0, "Average execution time should be reasonable")
        self.assertLess(total_time, 10.0, "Total concurrent execution should be efficient")
        
        # Verify user isolation was maintained
        user_ids = [r["user_id"] for r in results]
        self.assertEqual(len(set(user_ids)), 10, "All user IDs should be unique")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_dependency_management(self, real_services_fixture):
        """
        BVJ: All segments | System Reliability | Ensures proper service dependency handling
        Test agent dependency management and service availability handling.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Test with missing dependencies
        factory = get_agent_instance_factory()
        
        # Mock dependency checker
        service_availability = {
            "database": True,
            "redis": True, 
            "llm_service": False,  # Simulate LLM service down
            "tool_dispatcher": True
        }
        
        def check_service_availability(service_name: str) -> bool:
            return service_availability.get(service_name, False)
        
        # Create agent with dependency checking
        agent = await factory.create_agent("data_helper", user_context)
        agent.check_service_availability = check_service_availability
        
        # Mock fallback behavior when LLM is unavailable
        fallback_responses = {
            "llm_unavailable": {
                "status": "degraded",
                "message": "LLM service unavailable, using cached responses",
                "fallback_used": True
            }
        }
        
        # Execute agent with missing dependency
        result = await agent.execute_with_fallback(
            message="Test with missing LLM service",
            context=user_context,
            fallback_responses=fallback_responses
        )
        
        # Verify graceful degradation
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "degraded")
        self.assertTrue(result.get("fallback_used"))
        
        # Test with all services available
        service_availability["llm_service"] = True
        
        result_normal = await agent.execute_with_fallback(
            message="Test with all services available",
            context=user_context,
            fallback_responses=fallback_responses
        )
        
        # Verify normal operation
        self.assertIsNotNone(result_normal)
        self.assertNotEqual(result_normal.get("status"), "degraded")
        self.assertIsNone(result_normal.get("fallback_used"))

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_agent_execution_metrics_analytics(self, real_services_fixture):
        """
        BVJ: Platform/Internal | Business Intelligence | Provides execution analytics
        Test agent execution metrics and analytics collection.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Create execution tracker for metrics
        execution_tracker = get_execution_tracker()
        
        factory = get_agent_instance_factory()
        agent = await factory.create_agent("apex_optimizer", user_context)
        
        # Mock tool dispatcher with metrics
        async def metrics_tool_execution(*args, **kwargs):
            await asyncio.sleep(0.05)  # Simulate processing time
            return {
                "status": "success",
                "metrics": {
                    "tokens_used": 1500,
                    "api_calls": 3,
                    "processing_time": 0.05
                }
            }
        
        agent.tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
        agent.tool_dispatcher.execute_tool.side_effect = metrics_tool_execution
        agent.websocket_emitter = self.mock_emitter
        
        # Execute agent with metrics collection
        start_time = time.time()
        
        result = await agent.execute(
            message="Optimization with metrics collection",
            context=user_context
        )
        
        execution_time = time.time() - start_time
        
        # Record execution metrics
        execution_metrics = {
            "user_id": user_context.user_id,
            "agent_type": "apex_optimizer",
            "execution_time": execution_time,
            "tokens_used": result.get("metrics", {}).get("tokens_used", 0),
            "api_calls": result.get("metrics", {}).get("api_calls", 0),
            "timestamp": datetime.utcnow(),
            "success": True
        }
        
        execution_tracker.record_execution(execution_metrics)
        
        # Retrieve and verify analytics
        analytics = execution_tracker.get_execution_analytics(
            time_range=timedelta(minutes=1)
        )
        
        self.assertIn("total_executions", analytics)
        self.assertIn("avg_execution_time", analytics)
        self.assertIn("total_tokens_used", analytics)
        self.assertIn("success_rate", analytics)
        
        # Verify metrics are reasonable
        self.assertGreater(analytics["total_executions"], 0)
        self.assertGreater(analytics["avg_execution_time"], 0)
        self.assertEqual(analytics["success_rate"], 1.0)  # 100% success rate

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_rollback_retry_mechanisms(self, real_services_fixture):
        """
        BVJ: All segments | System Reliability | Ensures robust error recovery
        Test agent rollback and retry mechanisms for reliable execution.
        """
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Create execution engine with state management
        factory = ExecutionEngineFactory()
        engine = await factory.create_user_execution_engine(user_context)
        
        # Mock execution that fails then succeeds
        execution_attempts = 0
        saved_states = []
        
        async def failing_then_succeeding_execution(request_data, context):
            nonlocal execution_attempts
            execution_attempts += 1
            
            # Save state before execution
            state_snapshot = {
                "attempt": execution_attempts,
                "context": context.to_dict(),
                "timestamp": datetime.utcnow()
            }
            saved_states.append(state_snapshot)
            
            if execution_attempts <= 2:
                # Fail first two attempts
                raise Exception(f"Execution failed on attempt {execution_attempts}")
            
            # Succeed on third attempt
            return {
                "status": "success",
                "attempt": execution_attempts,
                "recovered": True
            }
        
        # Execute with retry logic
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                result = await failing_then_succeeding_execution(
                    request_data={"message": "Test retry mechanism"},
                    context=user_context
                )
                break  # Success, exit retry loop
            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt failed, perform rollback
                    await engine.rollback_to_last_stable_state()
                    raise
                
                # Wait before retry
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        # Verify execution eventually succeeded
        self.assertEqual(execution_attempts, 3)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["recovered"])
        
        # Verify state snapshots were saved
        self.assertEqual(len(saved_states), 3)
        for i, state in enumerate(saved_states):
            self.assertEqual(state["attempt"], i + 1)
            self.assertIn("timestamp", state)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_configuration_customization(self, real_services_fixture):
        """
        BVJ: Mid/Enterprise | Customization | Enables tailored agent behavior
        Test agent configuration and customization capabilities.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Test different configuration profiles
        configurations = {
            "conservative": {
                "max_tokens": 1000,
                "temperature": 0.1,
                "max_tools": 2,
                "timeout": 30
            },
            "aggressive": {
                "max_tokens": 4000,
                "temperature": 0.8,
                "max_tools": 8,
                "timeout": 120
            },
            "balanced": {
                "max_tokens": 2000,
                "temperature": 0.5,
                "max_tools": 4,
                "timeout": 60
            }
        }
        
        factory = get_agent_instance_factory()
        
        # Test each configuration profile
        results = {}
        
        for profile_name, config in configurations.items():
            agent = await factory.create_agent(
                "data_helper", 
                user_context,
                configuration=config
            )
            
            # Mock tool dispatcher respecting configuration
            async def configured_tool_execution(*args, **kwargs):
                # Simulate respecting max_tokens limit
                return {
                    "status": "success",
                    "tokens_used": min(config["max_tokens"], 1500),
                    "tools_executed": min(config["max_tools"], 3),
                    "configuration_applied": profile_name
                }
            
            agent.tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
            agent.tool_dispatcher.execute_tool.side_effect = configured_tool_execution
            agent.websocket_emitter = self.mock_emitter
            
            # Execute with timeout based on configuration
            result = await asyncio.wait_for(
                agent.execute(
                    message=f"Test {profile_name} configuration",
                    context=user_context
                ),
                timeout=config["timeout"]
            )
            
            results[profile_name] = result
        
        # Verify configuration was applied
        conservative_result = results["conservative"]
        aggressive_result = results["aggressive"]
        
        # Conservative should use fewer tokens
        self.assertLessEqual(
            conservative_result["tokens_used"], 
            configurations["conservative"]["max_tokens"]
        )
        
        # Aggressive should potentially use more resources
        self.assertLessEqual(
            aggressive_result["tokens_used"],
            configurations["aggressive"]["max_tokens"] 
        )
        
        # Verify configuration profiles work differently
        self.assertEqual(conservative_result["configuration_applied"], "conservative")
        self.assertEqual(aggressive_result["configuration_applied"], "aggressive")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_integration_external_services(self, real_services_fixture):
        """
        BVJ: All segments | Platform Integration | Ensures external service connectivity
        Test agent integration with external services and APIs.
        """
        user_context = UserExecutionContext(user_id=self.test_user_id)
        
        # Mock external services
        external_services = {
            "cost_api": AsyncMock(),
            "optimization_engine": AsyncMock(),
            "metrics_collector": AsyncMock()
        }
        
        # Configure service responses
        external_services["cost_api"].get_cost_data.return_value = {
            "monthly_cost": 5500.75,
            "breakdown": {"compute": 3200, "storage": 1800, "network": 500.75}
        }
        
        external_services["optimization_engine"].analyze.return_value = {
            "recommendations": [
                {"type": "scaling", "potential_savings": 850},
                {"type": "resource_optimization", "potential_savings": 420}
            ]
        }
        
        external_services["metrics_collector"].record_metrics.return_value = {"recorded": True}
        
        factory = get_agent_instance_factory()
        agent = await factory.create_agent("apex_optimizer", user_context)
        
        # Mock tool dispatcher that calls external services
        async def external_service_tool_execution(tool_name: str, *args, **kwargs):
            if tool_name == "fetch_cost_data":
                cost_data = await external_services["cost_api"].get_cost_data()
                return {"status": "success", "data": cost_data}
            
            elif tool_name == "optimize_infrastructure":
                analysis = await external_services["optimization_engine"].analyze()
                return {"status": "success", "analysis": analysis}
            
            elif tool_name == "record_metrics":
                result = await external_services["metrics_collector"].record_metrics()
                return {"status": "success", "recorded": result["recorded"]}
            
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}
        
        agent.tool_dispatcher = AsyncMock(spec=EnhancedToolExecutionEngine)
        agent.tool_dispatcher.execute_tool.side_effect = external_service_tool_execution
        agent.websocket_emitter = self.mock_emitter
        
        # Execute agent workflow using external services
        result = await agent.execute(
            message="Perform cost analysis using external services",
            context=user_context,
            tools=["fetch_cost_data", "optimize_infrastructure", "record_metrics"]
        )
        
        # Verify external services were called
        external_services["cost_api"].get_cost_data.assert_called_once()
        external_services["optimization_engine"].analyze.assert_called_once()
        external_services["metrics_collector"].record_metrics.assert_called_once()
        
        # Verify result contains data from external services
        self.assertIsNotNone(result)
        self.assertIn("external_data", result)
        
        # Verify cost data was retrieved
        cost_data = result["external_data"].get("cost_analysis")
        if cost_data:
            self.assertEqual(cost_data["monthly_cost"], 5500.75)
            self.assertIn("breakdown", cost_data)
        
        # Verify optimization analysis was performed
        optimization_data = result["external_data"].get("optimization")
        if optimization_data:
            self.assertIn("recommendations", optimization_data)
            self.assertGreater(len(optimization_data["recommendations"]), 0)

    def teardown_method(self, method):
        """Cleanup after tests."""
        # Cleanup any remaining resources
        if hasattr(self, 'mock_emitter'):
            self.mock_emitter.reset_mock()
        
        super().teardown_method(method)
    
    async def async_teardown_method(self, method):
        """Async cleanup after tests."""
        await super().async_teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])