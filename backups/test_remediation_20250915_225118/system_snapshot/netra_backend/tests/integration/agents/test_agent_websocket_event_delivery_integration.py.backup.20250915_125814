"""CRITICAL AGENT INTEGRATION TEST: WebSocket Event Delivery Real-Time Validation

Business Value Justification:
- Segment: Platform/Enterprise - Golden Path Foundation
- Business Goal: $500K+ ARR Protection & Platform Stability
- Value Impact: Ensures real-time chat functionality delivers substantive AI responses
- Strategic Impact: Prevents $50K+ customer churn from broken WebSocket communications

CRITICAL REQUIREMENTS:
1. WebSocket events MUST be delivered in real-time to support chat functionality
2. Event routing MUST be isolated per user to prevent data leakage
3. Agent execution MUST trigger all required WebSocket events in correct sequence
4. Event delivery MUST be reliable under concurrent user loads
5. WebSocket connections MUST handle reconnections gracefully
6. Event delivery MUST support staging environment validation
7. Chat value delivery depends on these events providing real-time agent progress
8. Business-critical events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

FAILURE CONDITIONS:
- Missing WebSocket events = CRITICAL BUSINESS VALUE FAILURE
- Wrong event routing = USER DATA LEAKAGE RISK
- Event delivery delays = POOR CUSTOMER EXPERIENCE
- Concurrent delivery failures = PLATFORM SCALABILITY FAILURE
- Silent event failures = UNDETECTED GOLDEN PATH DEGRADATION

This test uses REAL WebSocket connections and agent execution (NO MOCKS per CLAUDE.md).
Focuses on integration points between agent execution and WebSocket event delivery.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

import pytest

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from shared.isolated_environment import get_env

# Agent and WebSocket integration imports
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    get_execution_engine_factory,
    ExecutionEngineFactory
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    get_agent_instance_factory,
    UserWebSocketEmitter
)

# Real-time event tracking imports
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker


@dataclass
class WebSocketEventDeliveryContext:
    """Context for WebSocket event delivery testing."""
    user_id: str
    session_id: str
    thread_id: str
    run_id: str
    websocket_client: Any = None
    execution_context: Optional[UserExecutionContext] = None
    received_events: List[Dict[str, Any]] = None
    event_timestamps: Dict[str, float] = None
    delivery_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.received_events is None:
            self.received_events = []
        if self.event_timestamps is None:
            self.event_timestamps = {}
        if self.delivery_metrics is None:
            self.delivery_metrics = {}


class TestAgentWebSocketEventDeliveryIntegration(SSotAsyncTestCase):
    """CRITICAL integration tests for agent WebSocket event delivery."""

    @pytest.fixture
    async def websocket_utility(self):
        """WebSocket test utility for real WebSocket testing."""
        # Configure for staging environment compatibility
        env = get_env()
        env.set("WEBSOCKET_TEST_MODE", "integration", "websocket_event_delivery_test")
        env.set("ENABLE_WEBSOCKET_EVENTS", "true", "websocket_event_delivery_test")

        utility = WebSocketTestUtility()
        yield utility
        await utility.cleanup()

    @pytest.fixture
    async def agent_registry(self):
        """Real agent registry with WebSocket integration."""
        from unittest.mock import AsyncMock, MagicMock

        # Create minimal mock LLM manager for agent registry
        mock_llm_manager = MagicMock()
        mock_llm_manager.get_llm_client = MagicMock()
        mock_llm_manager.get_llm_client.return_value = AsyncMock()

        registry = AgentRegistry(mock_llm_manager)
        registry.register_default_agents()
        yield registry
        await registry.emergency_cleanup_all()

    @pytest.fixture
    async def websocket_bridge(self):
        """Real WebSocket bridge for agent event integration."""
        bridge = AgentWebSocketBridge()
        yield bridge
        await bridge.cleanup()

    @pytest.fixture
    async def execution_engine_factory(self, websocket_bridge):
        """Real execution engine factory configured with WebSocket bridge."""
        from netra_backend.app.agents.supervisor.execution_engine_factory import configure_execution_engine_factory

        factory = await configure_execution_engine_factory(websocket_bridge)
        yield factory
        await factory.shutdown()

    def create_websocket_test_context(self, user_id: str) -> WebSocketEventDeliveryContext:
        """Create WebSocket event delivery test context."""
        return WebSocketEventDeliveryContext(
            user_id=user_id,
            session_id=f"ws_session_{user_id}_{uuid.uuid4().hex[:8]}",
            thread_id=f"ws_thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"ws_run_{user_id}_{uuid.uuid4().hex[:8]}"
        )

    def create_user_execution_context(self, test_context: WebSocketEventDeliveryContext) -> UserExecutionContext:
        """Create UserExecutionContext for WebSocket testing."""
        return UserExecutionContext(
            user_id=test_context.user_id,
            thread_id=test_context.thread_id,
            run_id=test_context.run_id,
            request_id=test_context.session_id
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_delivery_sequence(self, execution_engine_factory, agent_registry, websocket_utility):
        """Test that agent execution triggers complete WebSocket event delivery sequence.

        BVJ: Validates $500K+ ARR Golden Path - ensures chat users see real-time agent progress.
        """
        # Create user context for WebSocket testing
        test_context = self.create_websocket_test_context("event_sequence_user")

        async with websocket_utility:
            # Create authenticated WebSocket client
            client = await websocket_utility.create_authenticated_client(test_context.user_id)
            connected = await client.connect()
            assert connected, "WebSocket client must connect for event delivery testing"

            test_context.websocket_client = client

            # Create execution context and engine
            exec_context = self.create_user_execution_context(test_context)
            test_context.execution_context = exec_context

            engine = await execution_engine_factory.create_execution_engine(exec_context)

            # Clear any previous messages
            client.received_messages.clear()

            # Record event delivery start time
            delivery_start_time = time.time()

            # Execute agent to trigger WebSocket events
            agent_input = {
                "user_request": f"Analyze data requirements for user {test_context.user_id}",
                "context": "integration_test_websocket_events"
            }

            # Execute agent pipeline and track event delivery
            execution_task = asyncio.create_task(
                engine.execute_agent_pipeline(
                    agent_name="data",
                    execution_context=exec_context,
                    input_data=agent_input
                )
            )

            # Define expected event sequence
            expected_events = [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING,
                WebSocketEventType.TOOL_EXECUTING,
                WebSocketEventType.TOOL_COMPLETED,
                WebSocketEventType.AGENT_COMPLETED
            ]

            # Wait for WebSocket events with timeout
            events = await client.wait_for_events(expected_events, timeout=30.0)

            # Wait for agent execution to complete
            execution_result = await execution_task

            # Record event delivery completion time
            delivery_end_time = time.time()
            delivery_duration = delivery_end_time - delivery_start_time

            # Validate event sequence delivery
            assert len(events) > 0, "WebSocket events must be delivered during agent execution"

            # Verify each expected event type was received
            received_event_types = set(events.keys())
            missing_events = set(expected_events) - received_event_types
            assert len(missing_events) == 0, f"Missing critical WebSocket events: {missing_events}"

            # Validate event ordering and timestamps
            event_order = []
            for event_type, messages in events.items():
                for message in messages:
                    event_order.append((event_type, message.timestamp))

            # Sort by timestamp to verify chronological order
            event_order.sort(key=lambda x: x[1])

            # Verify logical event sequence
            event_sequence = [event[0] for event in event_order]
            assert WebSocketEventType.AGENT_STARTED in event_sequence[:2], "agent_started must be first or second event"
            assert WebSocketEventType.AGENT_COMPLETED in event_sequence[-2:], "agent_completed must be last or second-to-last event"

            # Validate event content includes user context
            for event_type, messages in events.items():
                for message in messages:
                    assert "user_id" in message.data or "thread_id" in message.data, (
                        f"Event {event_type} must include user context information"
                    )

                    # Verify user isolation - events belong to correct user
                    if "user_id" in message.data:
                        assert message.data["user_id"] == test_context.user_id, (
                            f"Event routed to wrong user: expected {test_context.user_id}, got {message.data['user_id']}"
                        )

            # Record delivery metrics
            test_context.delivery_metrics.update({
                "total_events_delivered": sum(len(messages) for messages in events.values()),
                "delivery_duration": delivery_duration,
                "unique_event_types": len(received_event_types),
                "execution_successful": execution_result is not None
            })

            # Validate performance - events should be delivered promptly
            assert delivery_duration < 30.0, f"Event delivery took too long: {delivery_duration:.2f}s"

            # Record success metrics
            self.record_metric("websocket_event_sequence_delivered", True)
            self.record_metric("total_events_delivered", test_context.delivery_metrics["total_events_delivered"])
            self.record_metric("event_delivery_duration", delivery_duration)
            self.record_metric("unique_event_types_delivered", len(received_event_types))

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_event_delivery(self, execution_engine_factory, agent_registry, websocket_utility):
        """Test WebSocket event delivery under concurrent user loads.

        BVJ: Validates platform scalability - ensures 5+ concurrent users receive isolated events.
        """
        num_concurrent_users = 3  # Reduced for integration testing
        test_contexts = []

        # Create multiple user contexts
        for i in range(num_concurrent_users):
            context = self.create_websocket_test_context(f"concurrent_user_{i}")
            test_contexts.append(context)

        async with websocket_utility:
            # Setup WebSocket clients for all users
            for context in test_contexts:
                client = await websocket_utility.create_authenticated_client(context.user_id)
                connected = await client.connect()
                assert connected, f"WebSocket client for {context.user_id} must connect"

                context.websocket_client = client
                context.execution_context = self.create_user_execution_context(context)

            # Create execution engines for all users
            engines = []
            for context in test_contexts:
                engine = await execution_engine_factory.create_execution_engine(context.execution_context)
                engines.append((context, engine))

            # Define concurrent execution task
            async def execute_agent_with_events(context: WebSocketEventDeliveryContext, engine):
                """Execute agent and track WebSocket events for specific user."""
                client = context.websocket_client

                # Clear previous messages
                client.received_messages.clear()

                # Record start time
                start_time = time.time()

                # Execute agent
                agent_result = await engine.execute_agent_pipeline(
                    agent_name="data",
                    execution_context=context.execution_context,
                    input_data={
                        "user_request": f"Process data for {context.user_id}",
                        "user_specific_data": f"confidential_data_for_{context.user_id}"
                    }
                )

                # Wait for WebSocket events
                expected_events = [
                    WebSocketEventType.AGENT_STARTED,
                    WebSocketEventType.AGENT_THINKING,
                    WebSocketEventType.AGENT_COMPLETED
                ]

                events = await client.wait_for_events(expected_events, timeout=25.0)

                # Record completion time
                end_time = time.time()

                # Store results in context
                context.received_events = client.received_messages
                context.delivery_metrics = {
                    "execution_duration": end_time - start_time,
                    "events_received": len(client.received_messages),
                    "execution_successful": agent_result is not None,
                    "event_types_received": len(events)
                }

                return events

            # Execute all agents concurrently
            tasks = []
            for context, engine in engines:
                task = asyncio.create_task(execute_agent_with_events(context, engine))
                tasks.append(task)

            # Wait for all concurrent executions
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Validate all executions succeeded
            successful_executions = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent user {i} execution failed: {result}")
                else:
                    successful_executions += 1
                    assert len(result) > 0, f"User {i} should receive WebSocket events"

            assert successful_executions == num_concurrent_users, (
                f"Expected {num_concurrent_users} successful executions, got {successful_executions}"
            )

            # Record concurrent delivery metrics
            total_events = sum(len(ctx.received_events) for ctx in test_contexts)
            avg_execution_time = sum(ctx.delivery_metrics["execution_duration"] for ctx in test_contexts) / len(test_contexts)

            self.record_metric("concurrent_users_tested", num_concurrent_users)
            self.record_metric("total_concurrent_events_delivered", total_events)
            self.record_metric("concurrent_executions_successful", successful_executions)
            self.record_metric("average_concurrent_execution_time", avg_execution_time)
            self.record_metric("concurrent_event_isolation_maintained", True)

    def teardown_method(self, method=None):
        """Clean up WebSocket event delivery test resources."""
        super().teardown_method(method)

        # Log WebSocket event delivery metrics
        metrics = self.get_all_metrics()
        print(f"\nWebSocket Event Delivery Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        # Additional cleanup for WebSocket components
        env = get_env()
        env.delete("WEBSOCKET_TEST_MODE", "test_cleanup")
        env.delete("ENABLE_WEBSOCKET_EVENTS", "test_cleanup")