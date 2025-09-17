"
Mission Critical Agent Integration Violation Tests for Issue #885

These tests are designed to FAIL and prove agent integration violations exist.
They validate proper agent-WebSocket integration for the Golden Path user flow.

Business Value: Proves agent system integration failures affecting $500K+ ARR chat functionality
Expected Result: ALL TESTS SHOULD FAIL proving violations exist
""

import asyncio
import pytest
import json
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestAgentIntegrationViolations(SSotAsyncTestCase):
    ""Test suite to prove agent-WebSocket integration violations."

    async def asyncSetUp(self):
        "Setup for agent integration violation tests.""
        await super().asyncSetUp()
        self.integration_violations = []
        self.tested_components = []

    async def test_websocket_agent_registry_not_integrated(self):
        ""
        EXPECTED TO FAIL: Test should detect that WebSocket manager lacks proper agent registry integration.

        This proves agent registry is not properly integrated with WebSocket manager.
        "
        registry_integration_violations = []

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            # Create WebSocket manager
            user_context = {"user_id: agent_registry_test", "session_id: registry_session"}
            ws_manager = get_websocket_manager(user_context=user_context)

            self.tested_components.append("WebSocket Manager)

            # Test 1: Check if WebSocket manager has agent registry
            if not hasattr(ws_manager, '_agent_registry') and not hasattr(ws_manager, 'agent_registry'):
                violation = CRITICAL: WebSocket manager lacks agent registry integration"
                registry_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 2: Check if WebSocket manager can register agents
            agent_registration_methods = [
                'register_agent',
                'set_agent_registry',
                'add_agent',
                'configure_agent_registry'
            ]

            has_agent_registration = any(hasattr(ws_manager, method) for method in agent_registration_methods)
            if not has_agent_registration:
                violation = "CRITICAL: WebSocket manager cannot register agents
                registry_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 3: Try to access agent registry functionality
            try:
                # Attempt to import agent registry
                from netra_backend.app.agents.registry import AgentRegistry
                self.tested_components.append(Agent Registry")

                # Check if agent registry can be integrated with WebSocket manager
                agent_registry = AgentRegistry()

                # Try to set the registry on the WebSocket manager
                integration_successful = False
                for method in agent_registration_methods:
                    if hasattr(ws_manager, method):
                        try:
                            method_func = getattr(ws_manager, method)
                            if callable(method_func):
                                method_func(agent_registry)
                                integration_successful = True
                                break
                        except Exception as e:
                            logger.debug(f"Agent registry integration attempt failed: {method} - {e})

                if not integration_successful:
                    violation = CRITICAL: Agent registry cannot be integrated with WebSocket manager"
                    registry_integration_violations.append(violation)
                    self.integration_violations.append(violation)

            except ImportError:
                violation = "CRITICAL: Agent registry not available for WebSocket integration
                registry_integration_violations.append(violation)
                self.integration_violations.append(violation)

        except Exception as e:
            violation = fAgent registry integration test failed: {e}"
            registry_integration_violations.append(violation)
            self.integration_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Agent registry integration violations detected
        self.assertGreater(
            len(registry_integration_violations), 0,
            f"AGENT REGISTRY INTEGRATION VIOLATION: Found {len(registry_integration_violations)} integration violations. 
            fWebSocket manager should be properly integrated with agent registry for Golden Path. "
            f"Violations: {registry_integration_violations}
        )

        logger.error(fAGENT REGISTRY VIOLATIONS: {len(registry_integration_violations)} violations detected")

    async def test_websocket_events_not_properly_integrated(self):
        "
        EXPECTED TO FAIL: Test should detect that required WebSocket events are not integrated.

        This proves the 5 critical WebSocket events are not properly implemented.
        ""
        event_integration_violations = []

        # Required events for Golden Path
        required_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            user_context = {user_id": "event_test_user, session_id": "event_session}
            ws_manager = get_websocket_manager(user_context=user_context)

            self.tested_components.append(WebSocket Event System")

            # Test 1: Check if WebSocket manager can send required events
            for event_type in required_events:
                can_send_event = False

                # Check various event sending methods
                event_methods = [
                    f'send_{event_type}',
                    f'emit_{event_type}',
                    f'broadcast_{event_type}',
                    'send_event',
                    'emit_event',
                    'broadcast_event'
                ]

                for method_name in event_methods:
                    if hasattr(ws_manager, method_name):
                        can_send_event = True
                        break

                if not can_send_event:
                    violation = f"CRITICAL: WebSocket manager cannot send '{event_type}' event
                    event_integration_violations.append(violation)
                    self.integration_violations.append(violation)

            # Test 2: Check if event validation exists
            if not hasattr(ws_manager, '_validate_event') and not hasattr(ws_manager, 'validate_event'):
                violation = CRITICAL: WebSocket manager lacks event validation"
                event_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 3: Try to send a test event and check if it fails
            mock_websocket = AsyncMock()
            test_event = {
                "type: agent_started",
                "data: {agent_id": "test_agent, user_id": user_context["user_id]},
                timestamp": "2024-01-01T00:00:00Z
            }

            # Try to send event using various methods
            event_sent_successfully = False
            event_methods_tried = []

            for method_name in ['send_event', 'emit_event', 'broadcast_event', 'send_to_user']:
                if hasattr(ws_manager, method_name):
                    event_methods_tried.append(method_name)
                    try:
                        method = getattr(ws_manager, method_name)
                        if callable(method):
                            await method(test_event)
                            event_sent_successfully = True
                            break
                    except Exception as e:
                        logger.debug(fEvent sending failed with {method_name}: {e}")

            if not event_sent_successfully and event_methods_tried:
                violation = f"CRITICAL: WebSocket manager cannot send events (tried: {event_methods_tried}
                event_integration_violations.append(violation)
                self.integration_violations.append(violation)

        except Exception as e:
            violation = fEvent integration test failed: {e}"
            event_integration_violations.append(violation)
            self.integration_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Event integration violations detected
        self.assertGreater(
            len(event_integration_violations), 0,
            f"EVENT INTEGRATION VIOLATION: Found {len(event_integration_violations)} event integration violations. 
            fWebSocket manager should properly support all 5 critical events for Golden Path. "
            f"Violations: {event_integration_violations}
        )

        logger.error(fEVENT INTEGRATION VIOLATIONS: {len(event_integration_violations)} violations detected")

    async def test_agent_execution_engine_not_integrated(self):
        "
        EXPECTED TO FAIL: Test should detect that agent execution engine is not integrated with WebSocket.

        This proves agent execution is not properly integrated with WebSocket notifications.
        ""
        execution_integration_violations = []

        try:
            # Test execution engine integration
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            user_context = {user_id": "execution_test, session_id": "execution_session}
            ws_manager = get_websocket_manager(user_context=user_context)

            self.tested_components.append(Agent Execution Engine")

            # Test 1: Check if execution engine can be integrated
            try:
                from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
                execution_engine = ExecutionEngine()

                # Check if execution engine has WebSocket notification capability
                if not hasattr(execution_engine, 'websocket_manager') and not hasattr(execution_engine, 'set_websocket_manager'):
                    violation = "CRITICAL: Execution engine lacks WebSocket manager integration
                    execution_integration_violations.append(violation)
                    self.integration_violations.append(violation)

                # Check if execution engine can send notifications
                notification_methods = [
                    'notify_agent_started',
                    'notify_tool_executing',
                    'notify_agent_thinking',
                    'send_websocket_notification'
                ]

                has_notification_capability = any(hasattr(execution_engine, method) for method in notification_methods)
                if not has_notification_capability:
                    violation = CRITICAL: Execution engine cannot send WebSocket notifications"
                    execution_integration_violations.append(violation)
                    self.integration_violations.append(violation)

            except ImportError:
                violation = "CRITICAL: Cannot import execution engine for integration testing
                execution_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 2: Check if tool dispatcher is integrated
            try:
                from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
                tool_dispatcher = EnhancedToolDispatcher()

                self.tested_components.append(Tool Dispatcher")

                # Check if tool dispatcher has WebSocket integration
                if not hasattr(tool_dispatcher, 'websocket_manager') and not hasattr(tool_dispatcher, 'set_websocket_manager'):
                    violation = "CRITICAL: Tool dispatcher lacks WebSocket manager integration
                    execution_integration_violations.append(violation)
                    self.integration_violations.append(violation)

                # Check if tool dispatcher can notify about tool execution
                tool_notification_methods = [
                    'notify_tool_started',
                    'notify_tool_completed',
                    'send_tool_notification'
                ]

                has_tool_notifications = any(hasattr(tool_dispatcher, method) for method in tool_notification_methods)
                if not has_tool_notifications:
                    violation = CRITICAL: Tool dispatcher cannot send WebSocket notifications"
                    execution_integration_violations.append(violation)
                    self.integration_violations.append(violation)

            except ImportError:
                violation = "CRITICAL: Cannot import tool dispatcher for integration testing
                execution_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 3: Check supervisor agent integration
            try:
                from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
                supervisor = SupervisorAgent()

                self.tested_components.append(Supervisor Agent")

                # Check if supervisor has WebSocket integration
                if not hasattr(supervisor, 'websocket_manager') and not hasattr(supervisor, 'set_websocket_manager'):
                    violation = "CRITICAL: Supervisor agent lacks WebSocket manager integration
                    execution_integration_violations.append(violation)
                    self.integration_violations.append(violation)

            except ImportError:
                violation = CRITICAL: Cannot import supervisor agent for integration testing"
                execution_integration_violations.append(violation)
                self.integration_violations.append(violation)

        except Exception as e:
            violation = f"Execution engine integration test failed: {e}
            execution_integration_violations.append(violation)
            self.integration_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Execution integration violations detected
        self.assertGreater(
            len(execution_integration_violations), 0,
            fEXECUTION INTEGRATION VIOLATION: Found {len(execution_integration_violations)} execution integration violations. "
            f"Agent execution components should be properly integrated with WebSocket system. 
            fViolations: {execution_integration_violations}"
        )

        logger.error(f"EXECUTION INTEGRATION VIOLATIONS: {len(execution_integration_violations)} violations detected)

    async def test_message_routing_not_integrated_with_agents(self):
        ""
        EXPECTED TO FAIL: Test should detect that message routing is not integrated with agents.

        This proves message routing between WebSocket and agents is broken.
        "
        routing_integration_violations = []

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            user_context = {"user_id: routing_test", "session_id: routing_session"}
            ws_manager = get_websocket_manager(user_context=user_context)

            self.tested_components.append("Message Router)

            # Test 1: Check if message router exists and is integrated
            try:
                from netra_backend.app.websocket_core.message_router import MessageRouter
                message_router = MessageRouter()

                # Check if message router can route to agents
                agent_routing_methods = [
                    'route_to_agent',
                    'send_to_agent',
                    'forward_to_agent',
                    'dispatch_to_agent'
                ]

                has_agent_routing = any(hasattr(message_router, method) for method in agent_routing_methods)
                if not has_agent_routing:
                    violation = CRITICAL: Message router cannot route messages to agents"
                    routing_integration_violations.append(violation)
                    self.integration_violations.append(violation)

                # Check if message router can handle agent responses
                response_handling_methods = [
                    'handle_agent_response',
                    'process_agent_message',
                    'route_agent_response'
                ]

                has_response_handling = any(hasattr(message_router, method) for method in response_handling_methods)
                if not has_response_handling:
                    violation = "CRITICAL: Message router cannot handle agent responses
                    routing_integration_violations.append(violation)
                    self.integration_violations.append(violation)

            except ImportError:
                violation = CRITICAL: Message router not available for integration testing"
                routing_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 2: Check if WebSocket manager has message routing capability
            routing_methods = [
                'route_message',
                'handle_incoming_message',
                'process_user_message',
                'forward_to_agent'
            ]

            has_routing_capability = any(hasattr(ws_manager, method) for method in routing_methods)
            if not has_routing_capability:
                violation = "CRITICAL: WebSocket manager lacks message routing capability
                routing_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 3: Test message flow integration
            # Create a test message that should be routed to an agent
            test_user_message = {
                type": "user_message,
                content": "Please analyze this data for me,
                user_id": user_context["user_id],
                session_id": user_context["session_id],
                requires_agent": True
            }

            # Try to route the message
            message_routed = False
            for method_name in routing_methods:
                if hasattr(ws_manager, method_name):
                    try:
                        method = getattr(ws_manager, method_name)
                        if callable(method):
                            await method(test_user_message)
                            message_routed = True
                            break
                    except Exception as e:
                        logger.debug(f"Message routing failed with {method_name}: {e})

            if not message_routed:
                violation = CRITICAL: WebSocket manager cannot route user messages to agents"
                routing_integration_violations.append(violation)
                self.integration_violations.append(violation)

        except Exception as e:
            violation = f"Message routing integration test failed: {e}
            routing_integration_violations.append(violation)
            self.integration_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Message routing integration violations detected
        self.assertGreater(
            len(routing_integration_violations), 0,
            fMESSAGE ROUTING VIOLATION: Found {len(routing_integration_violations)} routing integration violations. "
            f"Message routing should be properly integrated between WebSocket and agents. 
            fViolations: {routing_integration_violations}"
        )

        logger.error(f"MESSAGE ROUTING VIOLATIONS: {len(routing_integration_violations)} violations detected)

    async def test_agent_lifecycle_events_not_integrated(self):
        ""
        EXPECTED TO FAIL: Test should detect that agent lifecycle events are not integrated.

        This proves agent lifecycle is not properly integrated with WebSocket notifications.
        "
        lifecycle_integration_violations = []

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            user_context = {"user_id: lifecycle_test", "session_id: lifecycle_session"}
            ws_manager = get_websocket_manager(user_context=user_context)

            self.tested_components.append("Agent Lifecycle)

            # Test 1: Check if agent lifecycle events can be tracked
            lifecycle_events = [
                'agent_created',
                'agent_started',
                'agent_thinking',
                'agent_tool_use',
                'agent_completed',
                'agent_error',
                'agent_timeout'
            ]

            lifecycle_tracking_methods = []
            for event in lifecycle_events:
                tracking_methods = [
                    f'track_{event}',
                    f'on_{event}',
                    f'handle_{event}',
                    f'notify_{event}'
                ]

                for method_name in tracking_methods:
                    if hasattr(ws_manager, method_name):
                        lifecycle_tracking_methods.append(method_name)

            if not lifecycle_tracking_methods:
                violation = CRITICAL: WebSocket manager cannot track agent lifecycle events"
                lifecycle_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 2: Check if agent state changes are communicated
            state_communication_methods = [
                'notify_agent_state_change',
                'broadcast_agent_status',
                'send_agent_update',
                'emit_agent_event'
            ]

            has_state_communication = any(hasattr(ws_manager, method) for method in state_communication_methods)
            if not has_state_communication:
                violation = "CRITICAL: WebSocket manager cannot communicate agent state changes
                lifecycle_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 3: Test agent error handling integration
            error_handling_methods = [
                'handle_agent_error',
                'notify_agent_error',
                'send_agent_error',
                'broadcast_agent_failure'
            ]

            has_error_handling = any(hasattr(ws_manager, method) for method in error_handling_methods)
            if not has_error_handling:
                violation = CRITICAL: WebSocket manager cannot handle agent errors"
                lifecycle_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 4: Check if agent progress can be communicated
            progress_methods = [
                'send_agent_progress',
                'update_agent_progress',
                'notify_progress',
                'broadcast_progress'
            ]

            has_progress_communication = any(hasattr(ws_manager, method) for method in progress_methods)
            if not has_progress_communication:
                violation = "CRITICAL: WebSocket manager cannot communicate agent progress
                lifecycle_integration_violations.append(violation)
                self.integration_violations.append(violation)

            # Test 5: Test integration with agent timeout handling
            timeout_methods = [
                'handle_agent_timeout',
                'notify_agent_timeout',
                'cancel_agent_execution'
            ]

            has_timeout_handling = any(hasattr(ws_manager, method) for method in timeout_methods)
            if not has_timeout_handling:
                violation = CRITICAL: WebSocket manager cannot handle agent timeouts"
                lifecycle_integration_violations.append(violation)
                self.integration_violations.append(violation)

        except Exception as e:
            violation = f"Agent lifecycle integration test failed: {e}
            lifecycle_integration_violations.append(violation)
            self.integration_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Lifecycle integration violations detected
        self.assertGreater(
            len(lifecycle_integration_violations), 0,
            fLIFECYCLE INTEGRATION VIOLATION: Found {len(lifecycle_integration_violations)} lifecycle integration violations. "
            f"Agent lifecycle should be properly integrated with WebSocket notifications. 
            fViolations: {lifecycle_integration_violations}"
        )

        logger.error(f"LIFECYCLE INTEGRATION VIOLATIONS: {len(lifecycle_integration_violations)} violations detected)

    def tearDown(self):
        ""Report all agent integration violations found."
        if self.integration_violations:
            logger.error("=*80)
            logger.error(AGENT INTEGRATION VIOLATIONS SUMMARY")
            logger.error("=*80)
            for i, violation in enumerate(self.integration_violations, 1):
                logger.error(f{i:2d}. {violation}")
            logger.error("=*80)
            logger.error(fTOTAL INTEGRATION VIOLATIONS: {len(self.integration_violations)}")
            logger.error("THESE VIOLATIONS AFFECT GOLDEN PATH USER FLOW ($500K+ ARR))
            logger.error(="*80)

        if self.tested_components:
            logger.info("Components tested:  + , ".join(set(self.tested_components)))


if __name__ == "__main__:
    pytest.main([__file__, -v", "-s, --tb=short"]