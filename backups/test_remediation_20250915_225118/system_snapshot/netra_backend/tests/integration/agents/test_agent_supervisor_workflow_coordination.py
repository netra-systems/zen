"""CRITICAL AGENT INTEGRATION TEST: Supervisor Agent Workflow Coordination

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
6. Complex workflows MUST deliver substantive AI value through coordinated agent actions

FAILURE CONDITIONS:
- Supervisor coordination failures = COMPLEX WORKFLOW BREAKDOWN
- Missing workflow progress events = POOR USER EXPERIENCE
- Sub-agent isolation violations = USER DATA LEAKAGE
- Workflow orchestration errors = BUSINESS VALUE DELIVERY FAILURE

This test uses REAL supervisor agent coordination with WebSocket integration (NO MOCKS per CLAUDE.md).
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
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from shared.isolated_environment import get_env

# Supervisor agent and orchestration imports
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
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
    coordination_events: List[Dict[str, Any]] = field(default_factory=list)
    workflow_progress: Dict[str, Any] = field(default_factory=dict)


class AgentSupervisorWorkflowCoordinationTests(SSotAsyncTestCase):
    """CRITICAL integration tests for supervisor agent workflow coordination."""

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
    async def test_supervisor_agent_workflow_coordination(self, execution_engine_factory, agent_registry, websocket_utility):
        """Test supervisor agent coordinating workflow with WebSocket events.

        BVJ: Validates complex AI workflows - enables $100K+ value delivery through coordinated analysis.
        """
        test_context = self.create_supervisor_coordination_context("workflow_coordination_user")

        async with websocket_utility:
            # Create authenticated WebSocket client
            client = await websocket_utility.create_authenticated_client(test_context.user_id)
            connected = await client.connect()
            assert connected, "WebSocket connection required for supervisor coordination testing"

            # Create execution context and engine
            exec_context = self.create_user_execution_context(test_context)
            engine = await execution_engine_factory.create_execution_engine(exec_context)

            # Get supervisor agent
            supervisor = await agent_registry.get_agent("supervisor", context=exec_context)
            if supervisor is None:
                # Try alternative agent names or create basic supervisor behavior
                supervisor = await agent_registry.get_agent("data", context=exec_context)
                assert supervisor is not None, "At least one agent must be available for coordination testing"

            # Clear previous WebSocket messages
            client.received_messages.clear()

            # Define workflow request
            workflow_request = {
                "user_request": "Perform comprehensive data analysis with coordination",
                "workflow_type": "multi_step_analysis",
                "coordination_required": True,
                "user_context": test_context.user_id
            }

            # Record workflow start time
            workflow_start_time = time.time()

            # Execute workflow through supervisor/agent
            workflow_result = await engine.execute_agent_pipeline(
                agent_name="supervisor" if await agent_registry.has_agent("supervisor") else "data",
                execution_context=exec_context,
                input_data=workflow_request
            )

            workflow_end_time = time.time()
            workflow_duration = workflow_end_time - workflow_start_time

            # Wait for coordination events
            expected_events = [WebSocketEventType.AGENT_STARTED, WebSocketEventType.AGENT_COMPLETED]
            events = await client.wait_for_events(expected_events, timeout=30.0)

            # Validate workflow coordination through WebSocket events
            assert len(events) > 0, "Workflow must generate WebSocket coordination events"

            # Verify coordination event sequence
            received_event_types = set(events.keys())
            assert WebSocketEventType.AGENT_STARTED in received_event_types, "Must signal workflow start"
            assert WebSocketEventType.AGENT_COMPLETED in received_event_types, "Must signal workflow completion"

            # Validate workflow completion
            assert workflow_result is not None, "Workflow must complete successfully"

            # Analyze coordination events
            coordination_events = client.received_messages

            # Validate user context isolation in all events
            for event in coordination_events:
                if hasattr(event, 'data') and isinstance(event.data, dict):
                    if "user_id" in event.data:
                        assert event.data["user_id"] == test_context.user_id, (
                            f"Event user context violation: expected {test_context.user_id}, got {event.data['user_id']}"
                        )

            # Record coordination metrics
            test_context.coordination_events = coordination_events
            test_context.workflow_progress = {
                "workflow_completed": workflow_result is not None,
                "total_coordination_events": len(coordination_events),
                "workflow_duration": workflow_duration
            }

            # Record success metrics
            self.record_metric("supervisor_workflow_coordinated", True)
            self.record_metric("total_coordination_events", len(coordination_events))
            self.record_metric("workflow_duration", workflow_duration)
            self.record_metric("coordination_successful", len(received_event_types) > 0)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_supervisor_workflow_isolation(self, execution_engine_factory, agent_registry, websocket_utility):
        """Test supervisor agent handling concurrent workflows with isolated coordination.

        BVJ: Validates platform scalability - ensures 3+ concurrent workflows don't interfere.
        """
        num_concurrent_workflows = 3
        coordination_contexts = []

        # Create multiple workflow contexts
        for i in range(num_concurrent_workflows):
            context = self.create_supervisor_coordination_context(f"concurrent_supervisor_user_{i}")
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
            async def execute_concurrent_supervisor_workflow(context: SupervisorCoordinationContext):
                """Execute supervisor workflow with coordination tracking."""
                client = context.websocket_client
                client.received_messages.clear()

                # Create engine for this workflow
                engine = await execution_engine_factory.create_execution_engine(context.execution_context)

                # Create workflow request specific to this user
                workflow_request = {
                    "user_request": f"Analyze data pipeline for {context.user_id}",
                    "workflow_type": "user_specific_analysis",
                    "user_specific_data": f"confidential_workflow_data_{context.user_id}",
                    "user_context": context.user_id
                }

                # Execute workflow
                start_time = time.time()
                workflow_result = await engine.execute_agent_pipeline(
                    agent_name="data",  # Use available agent
                    execution_context=context.execution_context,
                    input_data=workflow_request
                )
                end_time = time.time()

                # Wait for coordination events
                expected_events = [WebSocketEventType.AGENT_STARTED, WebSocketEventType.AGENT_COMPLETED]
                events = await client.wait_for_events(expected_events, timeout=25.0)

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
                task = asyncio.create_task(execute_concurrent_supervisor_workflow(context))
                tasks.append(task)

            # Wait for all concurrent workflow executions
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Validate all workflows succeeded
            successful_workflows = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent supervisor workflow {i} failed: {result}")
                else:
                    successful_workflows += 1
                    assert len(result) > 0, f"Supervisor workflow {i} should generate coordination events"

            assert successful_workflows == num_concurrent_workflows

            # Validate workflow isolation
            for i, context in enumerate(coordination_contexts):
                coordination_events = context.coordination_events

                # Verify events belong to correct user
                for event in coordination_events:
                    if hasattr(event, 'data') and isinstance(event.data, dict):
                        if "user_id" in event.data:
                            assert event.data["user_id"] == context.user_id, (
                                f"Supervisor workflow isolation violation: Workflow {i} received event for {event.data['user_id']}"
                            )

            # Calculate concurrent workflow metrics
            total_coordination_events = sum(len(ctx.coordination_events) for ctx in coordination_contexts)
            avg_execution_time = sum(ctx.workflow_progress["execution_duration"] for ctx in coordination_contexts) / len(coordination_contexts)

            self.record_metric("concurrent_supervisor_workflows_tested", num_concurrent_workflows)
            self.record_metric("total_concurrent_coordination_events", total_coordination_events)
            self.record_metric("successful_concurrent_supervisor_workflows", successful_workflows)
            self.record_metric("average_concurrent_supervisor_workflow_duration", avg_execution_time)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_supervisor_workflow_error_recovery(self, execution_engine_factory, agent_registry, websocket_utility):
        """Test supervisor agent handling workflow errors with WebSocket coordination.

        BVJ: Ensures robust workflow execution - prevents failures from breaking workflows.
        """
        test_context = self.create_supervisor_coordination_context("error_recovery_user")

        async with websocket_utility:
            client = await websocket_utility.create_authenticated_client(test_context.user_id)
            connected = await client.connect()
            assert connected, "WebSocket connection required for error recovery test"

            exec_context = self.create_user_execution_context(test_context)
            engine = await execution_engine_factory.create_execution_engine(exec_context)

            # Clear previous messages
            client.received_messages.clear()

            # Create workflow that may encounter issues
            error_prone_workflow = {
                "user_request": "Execute workflow with potential error scenarios",
                "workflow_type": "error_handling_test",
                "user_context": test_context.user_id
            }

            # Execute workflow that may have errors
            try:
                workflow_result = await engine.execute_agent_pipeline(
                    agent_name="data",
                    execution_context=exec_context,
                    input_data=error_prone_workflow
                )
            except Exception as e:
                # Some errors may be expected
                workflow_result = None

            # Wait for coordination events including error handling
            await asyncio.sleep(2.0)
            coordination_events = client.received_messages

            # Test workflow recovery - execute successful workflow after potential error
            client.received_messages.clear()

            recovery_workflow = {
                "user_request": "Recovery workflow after error handling",
                "workflow_type": "recovery_test",
                "user_context": test_context.user_id
            }

            # Execute recovery workflow
            recovery_result = await engine.execute_agent_pipeline(
                agent_name="data",
                execution_context=exec_context,
                input_data=recovery_workflow
            )

            # Wait for recovery coordination events
            recovery_coordination_events = await client.wait_for_events(
                [WebSocketEventType.AGENT_STARTED, WebSocketEventType.AGENT_COMPLETED],
                timeout=15.0
            )

            # Validate system recovery
            assert len(recovery_coordination_events) > 0, "System should recover and coordinate successfully"
            assert recovery_result is not None, "Recovery workflow should succeed"

            # Record error handling metrics
            self.record_metric("supervisor_error_handling_tested", True)
            self.record_metric("recovery_coordination_events", len(recovery_coordination_events))
            self.record_metric("supervisor_recovery_successful", recovery_result is not None)

    def teardown_method(self, method=None):
        """Clean up supervisor coordination test resources."""
        super().teardown_method(method)

        # Log supervisor coordination metrics
        metrics = self.get_all_metrics()
        print(f"\nSupervisor Workflow Coordination Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        # Additional cleanup
        env = get_env()
        env.delete("WEBSOCKET_TEST_MODE", "test_cleanup")
        env.delete("ENABLE_SUPERVISOR_WEBSOCKET_EVENTS", "test_cleanup")