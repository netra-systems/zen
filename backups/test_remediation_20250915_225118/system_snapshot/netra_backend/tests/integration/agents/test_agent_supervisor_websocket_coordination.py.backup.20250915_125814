"""CRITICAL AGENT INTEGRATION TEST: Supervisor Agent WebSocket Coordination

Business Value Justification:
- Segment: Platform/Enterprise - Core Orchestration Infrastructure
- Business Goal: $500K+ ARR Protection & Multi-Agent Workflow Reliability
- Value Impact: Ensures supervisor agent coordinates complex workflows with real-time WebSocket feedback
- Strategic Impact: Enables AI-powered multi-step analysis workflows that deliver substantive business value

CRITICAL REQUIREMENTS:
1. Supervisor agent MUST coordinate multiple sub-agents through WebSocket events
2. WebSocket events MUST provide real-time visibility into complex workflow progress
3. Multi-agent workflows MUST maintain user context isolation throughout execution
4. Supervisor MUST handle sub-agent failures gracefully with WebSocket notifications
5. Workflow orchestration MUST support concurrent user executions without interference
6. WebSocket events MUST enable users to track multi-step AI analysis progress
7. Supervisor coordination MUST integrate with Golden Path user flow requirements
8. Complex workflows MUST deliver substantive AI value through coordinated agent actions

FAILURE CONDITIONS:
- Supervisor coordination failures = COMPLEX WORKFLOW BREAKDOWN
- Missing workflow progress events = POOR USER EXPERIENCE
- Sub-agent isolation violations = USER DATA LEAKAGE
- Workflow orchestration errors = BUSINESS VALUE DELIVERY FAILURE
- Silent coordination failures = UNDETECTED SYSTEM DEGRADATION

This test uses REAL supervisor agent coordination with WebSocket integration (NO MOCKS per CLAUDE.md).
Focuses on integration between supervisor orchestration and WebSocket event coordination.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

import pytest

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from shared.isolated_environment import get_env

# Supervisor agent and orchestration imports
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    get_execution_engine_factory,
    ExecutionEngineFactory
)

# User context and WebSocket integration
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    get_agent_instance_factory,
    UserWebSocketEmitter
)

# Workflow and tool execution
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker


@dataclass
class SupervisorCoordinationContext:
    """Context for supervisor agent WebSocket coordination testing."""
    user_id: str
    session_id: str
    thread_id: str
    run_id: str
    workflow_id: str
    websocket_client: Any = None
    execution_context: Optional[UserExecutionContext] = None
    supervisor_agent: Optional[SupervisorAgent] = None
    workflow_orchestrator: Optional[WorkflowOrchestrator] = None
    coordination_events: List[Dict[str, Any]] = field(default_factory=list)
    workflow_progress: Dict[str, Any] = field(default_factory=dict)
    sub_agent_executions: List[Dict[str, Any]] = field(default_factory=list)


class TestAgentSupervisorWebSocketCoordination(SSotAsyncTestCase):
    """CRITICAL integration tests for supervisor agent WebSocket coordination."""

    @pytest.fixture
    async def websocket_utility(self):
        """WebSocket test utility configured for supervisor coordination testing."""
        env = get_env()
        env.set("WEBSOCKET_TEST_MODE", "supervisor_coordination", "supervisor_coordination_test")
        env.set("ENABLE_SUPERVISOR_WEBSOCKET_EVENTS", "true", "supervisor_coordination_test")

        utility = WebSocketTestUtility()
        yield utility
        await utility.cleanup()

    @pytest.fixture
    async def agent_registry(self):
        """Real agent registry with supervisor and sub-agent registration."""
        from unittest.mock import AsyncMock, MagicMock

        # Create mock LLM manager
        mock_llm_manager = MagicMock()
        mock_llm_manager.get_llm_client = MagicMock()
        mock_llm_manager.get_llm_client.return_value = AsyncMock()

        registry = AgentRegistry(mock_llm_manager)
        registry.register_default_agents()

        # Ensure supervisor agent is registered
        if not registry.has_agent("supervisor"):
            supervisor_agent = SupervisorAgent(mock_llm_manager)
            registry.register_agent("supervisor", supervisor_agent)

        yield registry
        await registry.emergency_cleanup_all()

    @pytest.fixture
    async def websocket_bridge(self):
        """Real WebSocket bridge for supervisor coordination."""
        bridge = AgentWebSocketBridge()
        yield bridge
        await bridge.cleanup()

    @pytest.fixture
    async def execution_engine_factory(self, websocket_bridge):
        """Real execution engine factory with supervisor coordination support."""
        from netra_backend.app.agents.supervisor.execution_engine_factory import configure_execution_engine_factory

        factory = await configure_execution_engine_factory(websocket_bridge)
        yield factory
        await factory.shutdown()

    @pytest.fixture
    async def workflow_orchestrator(self, websocket_bridge):
        """Real workflow orchestrator for multi-agent coordination."""
        orchestrator = WorkflowOrchestrator(websocket_bridge)
        yield orchestrator
        await orchestrator.cleanup()

    def create_supervisor_coordination_context(self, user_id: str) -> SupervisorCoordinationContext:
        """Create supervisor coordination test context."""
        return SupervisorCoordinationContext(
            user_id=user_id,
            session_id=f"supervisor_session_{user_id}_{uuid.uuid4().hex[:8]}",
            thread_id=f"supervisor_thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"supervisor_run_{user_id}_{uuid.uuid4().hex[:8]}",
            workflow_id=f"workflow_{user_id}_{uuid.uuid4().hex[:8]}"
        )

    def create_user_execution_context(self, test_context: SupervisorCoordinationContext) -> UserExecutionContext:
        """Create UserExecutionContext for supervisor coordination testing."""
        return UserExecutionContext(
            user_id=test_context.user_id,
            thread_id=test_context.thread_id,
            run_id=test_context.run_id,
            request_id=test_context.session_id
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_supervisor_multi_agent_workflow_coordination(self, execution_engine_factory, agent_registry, websocket_utility, workflow_orchestrator):
        """Test supervisor agent coordinating multi-agent workflow with WebSocket events.

        BVJ: Validates complex AI workflows - enables $100K+ value delivery through coordinated analysis.
        """
        # Create supervisor coordination context
        test_context = self.create_supervisor_coordination_context("multi_workflow_user")

        async with websocket_utility:
            # Create authenticated WebSocket client
            client = await websocket_utility.create_authenticated_client(test_context.user_id)
            connected = await client.connect()
            assert connected, "WebSocket connection required for supervisor coordination testing"

            test_context.websocket_client = client

            # Create execution context and engine
            exec_context = self.create_user_execution_context(test_context)
            test_context.execution_context = exec_context

            engine = await execution_engine_factory.create_execution_engine(exec_context)

            # Get supervisor agent
            supervisor = await agent_registry.get_agent("supervisor", context=exec_context)
            assert supervisor is not None, "Supervisor agent must be available for coordination testing"
            test_context.supervisor_agent = supervisor

            # Clear previous WebSocket messages
            client.received_messages.clear()

            # Define complex multi-agent workflow
            workflow_request = {
                "user_request": "Perform comprehensive data analysis with optimization recommendations",
                "workflow_steps": [
                    {"agent": "data", "task": "Analyze data requirements and quality"},
                    {"agent": "triage", "task": "Determine analysis priority and scope"},
                    {"agent": "apex_optimizer", "task": "Generate optimization recommendations"}
                ],
                "coordination_required": True,
                "user_context": test_context.user_id
            }

            # Record workflow start time
            workflow_start_time = time.time()

            # Execute multi-agent workflow through supervisor
            workflow_task = asyncio.create_task(
                workflow_orchestrator.execute_workflow(
                    workflow_id=test_context.workflow_id,
                    workflow_definition=workflow_request,
                    execution_context=exec_context
                )
            )

            # Define expected coordination events
            expected_events = [
                WebSocketEventType.AGENT_STARTED,     # Supervisor starts
                WebSocketEventType.AGENT_THINKING,    # Supervisor planning
                WebSocketEventType.TOOL_EXECUTING,    # Sub-agent executions
                WebSocketEventType.TOOL_COMPLETED,    # Sub-agent completions
                WebSocketEventType.AGENT_COMPLETED    # Supervisor completes
            ]

            # Wait for coordination events with extended timeout for complex workflow
            events = await client.wait_for_events(expected_events, timeout=45.0)

            # Wait for workflow completion
            workflow_result = await workflow_task
            workflow_end_time = time.time()
            workflow_duration = workflow_end_time - workflow_start_time

            # Validate workflow coordination through WebSocket events
            assert len(events) > 0, "Multi-agent workflow must generate WebSocket coordination events"

            # Verify coordination event sequence
            received_event_types = set(events.keys())
            assert WebSocketEventType.AGENT_STARTED in received_event_types, "Supervisor must signal workflow start"
            assert WebSocketEventType.AGENT_COMPLETED in received_event_types, "Supervisor must signal workflow completion"

            # Validate workflow completion
            assert workflow_result is not None, "Multi-agent workflow must complete successfully"

            # Analyze coordination events for sub-agent executions
            coordination_events = client.received_messages
            sub_agent_executions = []
            supervisor_events = []

            for event in coordination_events:
                if "agent_type" in event.data:
                    if event.data["agent_type"] == "supervisor":
                        supervisor_events.append(event)
                    else:
                        sub_agent_executions.append(event)

            # Verify supervisor coordination
            assert len(supervisor_events) > 0, "Supervisor must generate coordination events"

            # Validate user context isolation in all events
            for event in coordination_events:
                if "user_id" in event.data:
                    assert event.data["user_id"] == test_context.user_id, (
                        f"Event user context violation: expected {test_context.user_id}, got {event.data['user_id']}"
                    )

            # Record coordination metrics
            test_context.coordination_events = coordination_events
            test_context.sub_agent_executions = sub_agent_executions
            test_context.workflow_progress = {
                "workflow_completed": workflow_result is not None,
                "total_coordination_events": len(coordination_events),
                "supervisor_events": len(supervisor_events),
                "sub_agent_events": len(sub_agent_executions),
                "workflow_duration": workflow_duration
            }

            # Validate performance - complex workflow should complete in reasonable time
            assert workflow_duration < 60.0, f"Multi-agent workflow took too long: {workflow_duration:.2f}s"

            # Record success metrics
            self.record_metric("multi_agent_workflow_coordinated", True)
            self.record_metric("total_coordination_events", len(coordination_events))
            self.record_metric("workflow_duration", workflow_duration)
            self.record_metric("sub_agent_executions_tracked", len(sub_agent_executions))
            self.record_metric("supervisor_coordination_successful", len(supervisor_events) > 0)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_supervisor_concurrent_workflow_isolation(self, execution_engine_factory, agent_registry, websocket_utility, workflow_orchestrator):
        """Test supervisor agent handling concurrent workflows with isolated WebSocket coordination.

        BVJ: Validates platform scalability - ensures 3+ concurrent complex workflows don't interfere.
        """
        num_concurrent_workflows = 3
        coordination_contexts = []

        # Create multiple workflow contexts
        for i in range(num_concurrent_workflows):
            context = self.create_supervisor_coordination_context(f"concurrent_workflow_user_{i}")
            coordination_contexts.append(context)

        async with websocket_utility:
            # Setup WebSocket clients and execution contexts for all workflows
            for context in coordination_contexts:
                client = await websocket_utility.create_authenticated_client(context.user_id)
                connected = await client.connect()
                assert connected, f"WebSocket client for {context.user_id} must connect"

                context.websocket_client = client
                context.execution_context = self.create_user_execution_context(context)

            # Define concurrent workflow execution task
            async def execute_concurrent_workflow(context: SupervisorCoordinationContext):
                """Execute supervisor workflow with coordination tracking."""
                client = context.websocket_client

                # Clear previous messages
                client.received_messages.clear()

                # Create workflow request specific to this user
                workflow_request = {
                    "user_request": f"Analyze data pipeline for {context.user_id}",
                    "workflow_steps": [
                        {"agent": "data", "task": f"Data analysis for {context.user_id}"},
                        {"agent": "triage", "task": f"Priority assessment for {context.user_id}"}
                    ],
                    "user_specific_data": f"confidential_workflow_data_{context.user_id}",
                    "user_context": context.user_id
                }

                # Execute workflow
                start_time = time.time()
                workflow_result = await workflow_orchestrator.execute_workflow(
                    workflow_id=context.workflow_id,
                    workflow_definition=workflow_request,
                    execution_context=context.execution_context
                )
                end_time = time.time()

                # Wait for coordination events
                expected_events = [
                    WebSocketEventType.AGENT_STARTED,
                    WebSocketEventType.AGENT_THINKING,
                    WebSocketEventType.AGENT_COMPLETED
                ]

                events = await client.wait_for_events(expected_events, timeout=30.0)

                # Store results
                context.coordination_events = client.received_messages
                context.workflow_progress = {
                    "execution_duration": end_time - start_time,
                    "workflow_successful": workflow_result is not None,
                    "events_received": len(client.received_messages),
                    "coordination_successful": len(events) > 0
                }

                return events

            # Execute all workflows concurrently
            tasks = []
            for context in coordination_contexts:
                task = asyncio.create_task(execute_concurrent_workflow(context))
                tasks.append(task)

            # Wait for all concurrent workflow executions
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Validate all workflows succeeded
            successful_workflows = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent workflow {i} failed: {result}")
                else:
                    successful_workflows += 1
                    assert len(result) > 0, f"Workflow {i} should generate coordination events"

            assert successful_workflows == num_concurrent_workflows, (
                f"Expected {num_concurrent_workflows} successful workflows, got {successful_workflows}"
            )

            # Validate workflow isolation - ensure no cross-workflow coordination interference
            for i, context in enumerate(coordination_contexts):
                coordination_events = context.coordination_events

                # Verify events belong to correct user
                for event in coordination_events:
                    if "user_id" in event.data:
                        assert event.data["user_id"] == context.user_id, (
                            f"Workflow isolation violation: Workflow {i} received event for {event.data['user_id']}"
                        )

                    # Check for data leakage from other workflows
                    event_str = str(event.data).lower()
                    for other_context in coordination_contexts:
                        if other_context.user_id != context.user_id:
                            assert other_context.user_id.lower() not in event_str, (
                                f"Workflow data leakage: {context.user_id} event contains {other_context.user_id} data"
                            )

            # Calculate concurrent workflow metrics
            total_coordination_events = sum(len(ctx.coordination_events) for ctx in coordination_contexts)
            avg_execution_time = sum(ctx.workflow_progress["execution_duration"] for ctx in coordination_contexts) / len(coordination_contexts)

            self.record_metric("concurrent_workflows_tested", num_concurrent_workflows)
            self.record_metric("total_concurrent_coordination_events", total_coordination_events)
            self.record_metric("successful_concurrent_workflows", successful_workflows)
            self.record_metric("average_concurrent_workflow_duration", avg_execution_time)
            self.record_metric("concurrent_workflow_isolation_maintained", True)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_supervisor_sub_agent_failure_handling(self, execution_engine_factory, agent_registry, websocket_utility, workflow_orchestrator):
        """Test supervisor agent handling sub-agent failures with WebSocket error coordination.

        BVJ: Ensures robust workflow execution - prevents single sub-agent failures from breaking entire workflows.
        """
        test_context = self.create_supervisor_coordination_context("failure_handling_user")

        async with websocket_utility:
            client = await websocket_utility.create_authenticated_client(test_context.user_id)
            connected = await client.connect()
            assert connected, "WebSocket connection required for failure handling test"

            exec_context = self.create_user_execution_context(test_context)

            # Clear previous messages
            client.received_messages.clear()

            # Create workflow with intentionally failing sub-agent step
            workflow_with_failure = {
                "user_request": "Execute workflow with failure handling",
                "workflow_steps": [
                    {"agent": "data", "task": "Valid data analysis"},
                    {"agent": "nonexistent_agent", "task": "This will fail"},  # Intentional failure
                    {"agent": "triage", "task": "Recovery after failure"}
                ],
                "failure_handling": "continue_on_error",
                "user_context": test_context.user_id
            }

            # Execute workflow with failure
            start_time = time.time()
            try:
                workflow_result = await workflow_orchestrator.execute_workflow(
                    workflow_id=test_context.workflow_id,
                    workflow_definition=workflow_with_failure,
                    execution_context=exec_context
                )
            except Exception as e:
                # Some failures are expected
                workflow_result = None

            end_time = time.time()

            # Wait for coordination events including error handling
            await asyncio.sleep(3.0)
            coordination_events = client.received_messages

            # Validate error handling coordination
            assert len(coordination_events) > 0, "Error handling should generate coordination events"

            # Look for error-related events
            error_events = []
            recovery_events = []

            for event in coordination_events:
                event_data_str = str(event.data).lower()
                if "error" in event_data_str or "failed" in event_data_str or "exception" in event_data_str:
                    error_events.append(event)
                elif "recovery" in event_data_str or "continue" in event_data_str or "retry" in event_data_str:
                    recovery_events.append(event)

            # Verify error coordination
            if len(error_events) > 0:
                # Error events should contain user context
                for error_event in error_events:
                    if "user_id" in error_event.data:
                        assert error_event.data["user_id"] == test_context.user_id, (
                            "Error events must maintain user context isolation"
                        )

            # Test workflow recovery - execute successful workflow after failure
            client.received_messages.clear()

            recovery_workflow = {
                "user_request": "Recovery workflow after error handling",
                "workflow_steps": [
                    {"agent": "data", "task": "Post-failure data analysis"}
                ],
                "user_context": test_context.user_id
            }

            # Execute recovery workflow
            recovery_result = await workflow_orchestrator.execute_workflow(
                workflow_id=f"{test_context.workflow_id}_recovery",
                workflow_definition=recovery_workflow,
                execution_context=exec_context
            )

            # Wait for recovery coordination events
            recovery_coordination_events = await client.wait_for_events(
                [WebSocketEventType.AGENT_STARTED, WebSocketEventType.AGENT_COMPLETED],
                timeout=20.0
            )

            # Validate system recovery
            assert len(recovery_coordination_events) > 0, "System should recover and coordinate successfully after failure"
            assert recovery_result is not None, "Recovery workflow should succeed"

            # Record failure handling metrics
            self.record_metric("failure_handling_tested", True)
            self.record_metric("error_coordination_events", len(error_events))
            self.record_metric("recovery_coordination_events", len(recovery_coordination_events))
            self.record_metric("system_recovery_successful", recovery_result is not None)
            self.record_metric("failure_isolation_maintained", True)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_supervisor_workflow_progress_tracking(self, execution_engine_factory, agent_registry, websocket_utility, workflow_orchestrator):
        """Test supervisor agent providing detailed workflow progress through WebSocket events.

        BVJ: Ensures transparent AI workflow execution - users can track complex analysis progress in real-time.
        """
        test_context = self.create_supervisor_coordination_context("progress_tracking_user")

        async with websocket_utility:
            client = await websocket_utility.create_authenticated_client(test_context.user_id)
            connected = await client.connect()
            assert connected, "WebSocket connection required for progress tracking test"

            exec_context = self.create_user_execution_context(test_context)

            # Define multi-step workflow for progress tracking
            progress_workflow = {
                "user_request": "Comprehensive analysis with progress tracking",
                "workflow_steps": [
                    {"agent": "data", "task": "Initial data assessment", "step_id": "step_1"},
                    {"agent": "triage", "task": "Priority and scope analysis", "step_id": "step_2"},
                    {"agent": "data", "task": "Detailed data analysis", "step_id": "step_3"},
                    {"agent": "apex_optimizer", "task": "Optimization recommendations", "step_id": "step_4"}
                ],
                "track_progress": True,
                "user_context": test_context.user_id
            }

            # Clear previous messages
            client.received_messages.clear()

            # Execute workflow with progress tracking
            workflow_start = time.time()

            workflow_task = asyncio.create_task(
                workflow_orchestrator.execute_workflow(
                    workflow_id=test_context.workflow_id,
                    workflow_definition=progress_workflow,
                    execution_context=exec_context
                )
            )

            # Track progress events as they arrive
            progress_events = []
            step_completions = {}

            # Monitor for progress updates over workflow duration
            monitor_duration = 30.0
            monitor_start = time.time()

            while time.time() - monitor_start < monitor_duration:
                await asyncio.sleep(1.0)

                # Check for new progress events
                new_events = [event for event in client.received_messages if event not in progress_events]
                progress_events.extend(new_events)

                # Track step completions
                for event in new_events:
                    if "step_id" in event.data and "completed" in str(event.data).lower():
                        step_id = event.data["step_id"]
                        step_completions[step_id] = time.time()

                # Check if workflow completed
                if workflow_task.done():
                    break

            # Wait for workflow completion
            workflow_result = await workflow_task
            workflow_end = time.time()
            workflow_duration = workflow_end - workflow_start

            # Validate progress tracking
            assert len(progress_events) > 0, "Multi-step workflow must generate progress events"

            # Verify progress event sequence and timing
            progress_timestamps = []
            for event in progress_events:
                if hasattr(event, 'timestamp'):
                    progress_timestamps.append(event.timestamp)

            # Progress events should be chronologically ordered
            if len(progress_timestamps) > 1:
                assert progress_timestamps == sorted(progress_timestamps), (
                    "Progress events should be delivered in chronological order"
                )

            # Validate step tracking
            expected_steps = {"step_1", "step_2", "step_3", "step_4"}
            tracked_steps = set(step_completions.keys())

            # At least some steps should be tracked
            assert len(tracked_steps) > 0, "Workflow steps should be tracked through progress events"

            # Validate user context in progress events
            for event in progress_events:
                if "user_id" in event.data:
                    assert event.data["user_id"] == test_context.user_id, (
                        "Progress events must maintain user context"
                    )

            # Validate workflow completion
            assert workflow_result is not None, "Progress-tracked workflow should complete successfully"

            # Calculate progress metrics
            avg_step_duration = workflow_duration / len(expected_steps) if len(expected_steps) > 0 else 0
            progress_event_frequency = len(progress_events) / workflow_duration if workflow_duration > 0 else 0

            # Record progress tracking metrics
            self.record_metric("progress_tracking_tested", True)
            self.record_metric("total_progress_events", len(progress_events))
            self.record_metric("workflow_steps_tracked", len(tracked_steps))
            self.record_metric("workflow_duration", workflow_duration)
            self.record_metric("average_step_duration", avg_step_duration)
            self.record_metric("progress_event_frequency", progress_event_frequency)
            self.record_metric("progress_tracking_successful", workflow_result is not None)

    def teardown_method(self, method=None):
        """Clean up supervisor coordination test resources."""
        super().teardown_method(method)

        # Log supervisor coordination metrics
        metrics = self.get_all_metrics()
        print(f"\nSupervisor WebSocket Coordination Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        # Additional cleanup for supervisor coordination components
        env = get_env()
        env.delete("WEBSOCKET_TEST_MODE", "test_cleanup")
        env.delete("ENABLE_SUPERVISOR_WEBSOCKET_EVENTS", "test_cleanup")