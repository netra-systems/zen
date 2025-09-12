"""
Integration Tests for Agent Execution Pipeline

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Platform Stability & User Experience - Core agent execution reliability
- Value Impact: Ensures agents execute correctly to deliver business value to users
- Strategic Impact: $500K+ ARR protection - Agent execution pipeline must work reliably

This module tests the core agent execution pipeline with real services, focusing on:
1. Agent factory patterns for user context isolation
2. UserExecutionEngine for concurrent user execution
3. Agent pipeline orchestration and coordination
4. Tool dispatcher integration and execution flows
5. Performance characteristics under realistic load

CRITICAL REQUIREMENTS per CLAUDE.md:
- NO MOCKS - use real services without requiring services to be actually running
- SSOT patterns from test_framework/
- Focus on agent responses, execution flows, and business value delivery
- User context isolation using factory patterns
- WebSocket event emission validation
- Test both success and failure scenarios
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
import pytest

# SSOT imports following established patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Core agent execution infrastructure - REAL SERVICES ONLY
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    get_agent_instance_factory,
    configure_agent_instance_factory
)
from netra_backend.app.agents.supervisor.agent_class_registry import (
    AgentClassRegistry,
    get_agent_class_registry
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter


class TestAgentExecutionPipeline(SSotAsyncTestCase):
    """Integration tests for agent execution pipeline with real services."""
    
    def setup_method(self, method=None):
        """Set up test environment with real agent execution infrastructure."""
        super().setup_method(method)
        
        # Initialize environment
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_MODE", "integration")
        
        # Create unique test identifiers
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"test_run_{uuid.uuid4().hex[:8]}"
        
        # Initialize agent execution infrastructure
        self.agent_factory = None
        self.agent_registry = None
        self.execution_engine = None
        self.websocket_bridge = None
        self.websocket_emitter = None
        self.tool_dispatcher = None
        
        # Performance tracking
        self.execution_metrics = {
            'agent_creation_time': [],
            'execution_time': [],
            'websocket_events': [],
            'tool_executions': [],
            'memory_usage': []
        }
        
        # Note: _initialize_test_infrastructure is async, will be called in test methods as needed
    
    async def _initialize_test_infrastructure(self):
        """Initialize real agent execution infrastructure for testing."""
        try:
            # Initialize agent registry
            self.agent_registry = get_agent_class_registry()
            # Registry is already initialized on first access
            
            # Initialize agent factory
            self.agent_factory = get_agent_instance_factory()
            configure_agent_instance_factory(self.agent_factory)
            
            # Initialize WebSocket infrastructure for event tracking
            self.websocket_emitter = UnifiedWebSocketEmitter(user_id=self.test_user_id)
            self.websocket_bridge = AgentWebSocketBridge(
                websocket_emitter=self.websocket_emitter
            )
            
            # Initialize tool dispatcher
            self.tool_dispatcher = EnhancedToolDispatcher()
            
            # Initialize execution engine with real infrastructure
            self.execution_engine = UserExecutionEngine(
                agent_registry=self.agent_registry,
                websocket_bridge=self.websocket_bridge,
                tool_dispatcher=self.tool_dispatcher
            )
            
            self.record_metric("infrastructure_init_success", True)
            
        except Exception as e:
            self.record_metric("infrastructure_init_error", str(e))
            raise
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_creation_and_execution_flow(self):
        """
        Test complete agent creation and execution flow with real infrastructure.
        
        Business Value: Validates that agents can be created and execute successfully,
        delivering the core functionality users expect from the platform.
        """
        # Initialize test infrastructure
        await self._initialize_test_infrastructure()
        
        start_time = time.time()
        
        # Create user execution context with isolation
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            session_metadata={"test_type": "agent_execution"}
        )
        
        # Validate user context isolation
        validate_user_context(user_context)
        self.assertTrue(user_context.is_isolated())
        
        # Create agent execution context
        execution_context = AgentExecutionContext(
            agent_name="triage_agent",
            user_message="Analyze system performance issues",
            user_context=user_context,
            tools_available=["system_analyzer", "performance_monitor"],
            execution_id=f"exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Execute agent with real infrastructure
        creation_start = time.time()
        result = await self.execution_engine.execute_agent(execution_context)
        execution_time = time.time() - creation_start
        
        # Validate execution result
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AgentExecutionResult)
        self.assertTrue(result.success or result.partial_success)
        
        # Business value validation - agent must provide meaningful response
        self.assertIsNotNone(result.agent_response)
        self.assertGreater(len(result.agent_response), 10)
        self.assertIn("analysis", result.agent_response.lower())
        
        # Performance characteristics validation
        self.assertLess(execution_time, 30.0)  # Agent should execute within 30 seconds
        self.execution_metrics['execution_time'].append(execution_time)
        
        # User context isolation validation
        self.assertEqual(result.user_context.user_id, self.test_user_id)
        self.assertEqual(result.user_context.thread_id, self.test_thread_id)
        
        # WebSocket events validation
        events = result.websocket_events_sent
        self.assertGreater(len(events), 0)
        self.assertIn("agent_started", [e.get("type") for e in events])
        self.assertIn("agent_completed", [e.get("type") for e in events])
        
        total_time = time.time() - start_time
        self.record_metric("test_agent_creation_execution_total_time", total_time)
        self.record_metric("business_value_delivered", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_execution_isolation(self):
        """
        Test concurrent agent execution with proper user isolation.
        
        Business Value: Ensures multiple users can interact with agents simultaneously
        without context leakage, supporting multi-tenant platform architecture.
        """
        # Create multiple user contexts for concurrent execution
        user_contexts = []
        execution_contexts = []
        
        for i in range(3):
            user_id = f"test_user_{i}_{uuid.uuid4().hex[:6]}"
            thread_id = f"test_thread_{i}_{uuid.uuid4().hex[:6]}"
            
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=f"run_{i}_{uuid.uuid4().hex[:6]}",
                session_metadata={"test_type": "concurrent_execution", "user_index": i}
            )
            user_contexts.append(user_context)
            
            execution_context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message=f"User {i} requests system analysis",
                user_context=user_context,
                tools_available=["system_analyzer"],
                execution_id=f"exec_{i}_{uuid.uuid4().hex[:6]}"
            )
            execution_contexts.append(execution_context)
        
        # Execute agents concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[self.execution_engine.execute_agent(ctx) for ctx in execution_contexts],
            return_exceptions=True
        )
        concurrent_execution_time = time.time() - start_time
        
        # Validate all executions succeeded
        self.assertEqual(len(results), 3)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.fail(f"Agent execution {i} failed: {result}")
            
            self.assertIsInstance(result, AgentExecutionResult)
            self.assertTrue(result.success or result.partial_success)
            
            # Validate user isolation
            self.assertEqual(result.user_context.user_id, user_contexts[i].user_id)
            self.assertEqual(result.user_context.thread_id, user_contexts[i].thread_id)
            
            # Validate no cross-contamination in responses
            self.assertIn(f"User {i}", result.agent_response or "")
        
        # Performance validation - concurrent execution should be efficient
        self.assertLess(concurrent_execution_time, 45.0)  # Should complete within 45 seconds
        
        self.record_metric("concurrent_execution_time", concurrent_execution_time)
        self.record_metric("concurrent_users_supported", 3)
        self.record_metric("user_isolation_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_tool_integration_execution(self):
        """
        Test agent execution with tool dispatcher integration.
        
        Business Value: Validates agents can execute tools to solve real problems,
        delivering actionable insights and solutions to users.
        """
        # Create user context for tool-heavy execution
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            session_metadata={"test_type": "tool_integration"}
        )
        
        # Create execution context with multiple tools available
        execution_context = AgentExecutionContext(
            agent_name="data_helper_agent",
            user_message="Generate performance report with system metrics",
            user_context=user_context,
            tools_available=[
                "system_analyzer",
                "performance_monitor", 
                "report_generator",
                "data_processor"
            ],
            execution_id=f"tool_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Track tool execution events
        tool_execution_events = []
        
        def track_tool_execution(event):
            tool_execution_events.append(event)
        
        # Execute agent with tool tracking
        start_time = time.time()
        result = await self.execution_engine.execute_agent(execution_context)
        execution_time = time.time() - start_time
        
        # Validate agent execution with tools
        self.assertIsNotNone(result)
        self.assertTrue(result.success or result.partial_success)
        
        # Validate tool integration
        self.assertIsNotNone(result.tools_used)
        self.assertGreater(len(result.tools_used), 0)
        
        # Business value validation - tools should provide meaningful data
        if result.tool_results:
            for tool_result in result.tool_results:
                self.assertIsNotNone(tool_result.get("result"))
                self.assertNotEqual(tool_result.get("result", ""), "")
        
        # WebSocket events should include tool execution events
        events = result.websocket_events_sent
        tool_events = [e for e in events if e.get("type") in ["tool_executing", "tool_completed"]]
        self.assertGreater(len(tool_events), 0)
        
        # Performance validation
        self.assertLess(execution_time, 60.0)  # Tool execution should complete within 60 seconds
        
        self.record_metric("tool_execution_time", execution_time)
        self.record_metric("tools_used_count", len(result.tools_used or []))
        self.record_metric("tool_integration_success", True)
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_agent_pipeline_orchestration_flow(self):
        """
        Test multi-step agent pipeline orchestration with state management.
        
        Business Value: Validates complex workflows can be orchestrated to solve
        sophisticated business problems requiring multiple processing steps.
        """
        # Create user context for pipeline execution
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            session_metadata={"test_type": "pipeline_orchestration"}
        )
        
        # Define multi-step pipeline
        pipeline_steps = [
            PipelineStep(
                step_name="data_collection",
                agent_name="data_helper_agent",
                step_message="Collect system performance data",
                expected_duration=10000
            ),
            PipelineStep(
                step_name="analysis",
                agent_name="triage_agent", 
                step_message="Analyze collected performance data",
                expected_duration=15000
            ),
            PipelineStep(
                step_name="optimization",
                agent_name="apex_optimizer_agent",
                step_message="Generate optimization recommendations",
                expected_duration=20000
            )
        ]
        
        # Create pipeline execution context
        execution_context = AgentExecutionContext(
            agent_name="supervisor_agent",
            user_message="Execute comprehensive system optimization pipeline",
            user_context=user_context,
            pipeline_steps=pipeline_steps,
            tools_available=["system_analyzer", "performance_monitor", "optimizer"],
            execution_id=f"pipeline_{uuid.uuid4().hex[:8]}"
        )
        
        # Execute pipeline
        start_time = time.time()
        result = await self.execution_engine.execute_agent(execution_context)
        pipeline_time = time.time() - start_time
        
        # Validate pipeline execution
        self.assertIsNotNone(result)
        self.assertTrue(result.success or result.partial_success)
        
        # Validate pipeline state management
        if hasattr(result, 'pipeline_results'):
            self.assertIsNotNone(result.pipeline_results)
            self.assertGreater(len(result.pipeline_results), 0)
        
        # Business value validation - pipeline should deliver comprehensive results
        self.assertIsNotNone(result.agent_response)
        self.assertGreater(len(result.agent_response), 50)
        
        # Validate state persistence between steps
        self.assertEqual(result.user_context.user_id, self.test_user_id)
        self.assertEqual(result.user_context.thread_id, self.test_thread_id)
        
        # WebSocket events should track pipeline progress
        events = result.websocket_events_sent
        pipeline_events = [e for e in events if "pipeline" in e.get("type", "").lower() or "step" in e.get("type", "").lower()]
        
        # Performance validation - pipeline should complete within reasonable time
        self.assertLess(pipeline_time, 120.0)  # Complex pipeline should complete within 2 minutes
        
        self.record_metric("pipeline_execution_time", pipeline_time)
        self.record_metric("pipeline_steps_completed", len(pipeline_steps))
        self.record_metric("pipeline_orchestration_success", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_performance_characteristics(self):
        """
        Test agent execution performance characteristics under realistic load.
        
        Business Value: Ensures platform can handle realistic user loads while
        maintaining responsive performance, supporting business scalability.
        """
        # Performance test parameters
        execution_count = 5
        max_concurrent = 3
        performance_thresholds = {
            'avg_execution_time': 25.0,  # seconds
            'max_execution_time': 45.0,  # seconds
            'memory_growth_limit': 100,  # MB
            'websocket_event_latency': 1.0  # seconds
        }
        
        execution_results = []
        execution_times = []
        
        # Create semaphore for controlled concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single_agent(iteration: int) -> Dict[str, Any]:
            async with semaphore:
                # Create isolated user context for each execution
                user_context = UserExecutionContext(
                    user_id=f"perf_user_{iteration}_{uuid.uuid4().hex[:6]}",
                    thread_id=f"perf_thread_{iteration}_{uuid.uuid4().hex[:6]}",
                    run_id=f"perf_run_{iteration}_{uuid.uuid4().hex[:6]}",
                    session_metadata={"test_type": "performance", "iteration": iteration}
                )
                
                execution_context = AgentExecutionContext(
                    agent_name="triage_agent",
                    user_message=f"Performance test iteration {iteration} - analyze system metrics",
                    user_context=user_context,
                    tools_available=["system_analyzer"],
                    execution_id=f"perf_exec_{iteration}_{uuid.uuid4().hex[:6]}"
                )
                
                start_time = time.time()
                result = await self.execution_engine.execute_agent(execution_context)
                execution_time = time.time() - start_time
                
                return {
                    'iteration': iteration,
                    'execution_time': execution_time,
                    'result': result,
                    'success': result.success if result else False,
                    'websocket_events_count': len(result.websocket_events_sent) if result and result.websocket_events_sent else 0
                }
        
        # Execute performance test
        start_time = time.time()
        results = await asyncio.gather(
            *[execute_single_agent(i) for i in range(execution_count)],
            return_exceptions=True
        )
        total_time = time.time() - start_time
        
        # Analyze performance results
        successful_results = [r for r in results if not isinstance(r, Exception) and r.get('success')]
        execution_times = [r['execution_time'] for r in successful_results]
        
        # Validate performance characteristics
        self.assertGreaterEqual(len(successful_results), execution_count * 0.8)  # 80% success rate minimum
        
        if execution_times:
            avg_execution_time = sum(execution_times) / len(execution_times)
            max_execution_time = max(execution_times)
            
            # Performance thresholds validation
            self.assertLess(avg_execution_time, performance_thresholds['avg_execution_time'])
            self.assertLess(max_execution_time, performance_thresholds['max_execution_time'])
            
            self.record_metric("avg_execution_time", avg_execution_time)
            self.record_metric("max_execution_time", max_execution_time)
            self.record_metric("successful_executions", len(successful_results))
        
        # Validate WebSocket event delivery performance
        total_events = sum(r.get('websocket_events_count', 0) for r in successful_results)
        self.assertGreater(total_events, 0)
        
        self.record_metric("total_execution_time", total_time)
        self.record_metric("performance_test_success", True)
        self.record_metric("throughput_executions_per_second", execution_count / total_time)
    
    def teardown_method(self, method=None):
        """Clean up test infrastructure and log performance metrics."""
        try:
            # Log performance metrics
            metrics = self.get_all_metrics()
            if metrics:
                print(f"\nAgent Execution Integration Test Metrics:")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
            
            # Clean up infrastructure (sync cleanup methods only in teardown)
            if self.execution_engine:
                # If cleanup is async, skip it here (should be handled in test methods)
                pass
            
            if self.websocket_bridge:
                # If cleanup is async, skip it here
                pass
            
            if self.agent_factory:
                self.agent_factory.cleanup()
            
            self.record_metric("test_cleanup_success", True)
            
        except Exception as e:
            self.record_metric("test_cleanup_error", str(e))
        
        super().teardown_method(method)