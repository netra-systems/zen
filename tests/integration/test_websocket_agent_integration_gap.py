"""
Test WebSocket-Agent Integration Gap

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure users receive real-time agent progress updates
- Value Impact: WebSocket events provide transparency and trust in AI interactions
- Strategic Impact: Core chat functionality that drives $500K+ ARR

CRITICAL: This test reproduces the integration gap where ExecutionEngine was not updated
when AgentWebSocketBridge was migrated from singleton to per-request pattern.

Based on Five Whys Root Cause Analysis:
- Root Cause: Missing dependency orchestration between factory components
- Impact: Users don't receive the 5 critical WebSocket events during agent execution
- Evidence: ExecutionEngine -> AgentWebSocketBridge -> UserWebSocketEmitter chain failure

This test SHOULD FAIL initially because it reproduces the current broken integration.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


class TestWebSocketAgentIntegrationGap(BaseIntegrationTest):
    """
    Test the integration gap between ExecutionEngine and AgentWebSocketBridge.
    
    CRITICAL: This test reproduces the factory delegation failure that prevents
    WebSocket events from reaching users during agent execution.
    """

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_websocket_bridge_chain_failure(self, real_services_fixture):
        """
        Test ExecutionEngine -> AgentWebSocketBridge -> UserWebSocketEmitter chain failure.
        
        EXPECTED: This test SHOULD FAIL because ExecutionEngine doesn't properly
        delegate to the new per-request factory pattern.
        
        Five Whys Root Cause:
        - ExecutionEngine was not updated when AgentWebSocketBridge migrated
        - Factory delegation is broken at the handoff point
        - Users don't receive WebSocket events during agent execution
        """
        # Setup authenticated user context using SSOT E2E auth helper
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="integration_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        logger.info(f"Testing WebSocket integration gap with user: {user_context.user_id}")
        
        # Mock WebSocket event collector to verify events are NOT sent
        websocket_events = []
        
        def mock_websocket_emit(event_type: str, data: Dict[str, Any], **kwargs):
            """Mock WebSocket emitter that records events."""
            websocket_events.append({
                "event_type": event_type,
                "data": data,
                "user_id": kwargs.get("user_id"),
                "timestamp": asyncio.get_event_loop().time()
            })
            logger.info(f"Mock WebSocket event: {event_type} for user {kwargs.get('user_id')}")
        
        try:
            # Import ExecutionEngine to test the integration
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            from netra_backend.app.websocket_core.agent_websocket_bridge import AgentWebSocketBridge
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            
            # CRITICAL TEST: Verify ExecutionEngine uses factory delegation pattern
            execution_factory = ExecutionEngineFactory()
            execution_factory.configure()
            
            # Create ExecutionEngine instance - this should delegate to factory
            execution_engine = execution_factory.create_execution_engine(user_context)
            
            # CRITICAL FAILURE POINT: Check if ExecutionEngine has WebSocket bridge reference
            # According to Five Whys analysis, this delegation is broken
            assert hasattr(execution_engine, '_websocket_bridge'), (
                "INTEGRATION GAP: ExecutionEngine missing _websocket_bridge attribute. "
                "This confirms the factory delegation failure identified in Five Whys analysis."
            )
            
            websocket_bridge = execution_engine._websocket_bridge
            assert websocket_bridge is not None, (
                "INTEGRATION GAP: ExecutionEngine._websocket_bridge is None. "
                "ExecutionEngine not properly updated for per-request factory pattern."
            )
            
            # CRITICAL FAILURE POINT: Check if WebSocket bridge has user emitter
            # This is where the per-request pattern should create user-specific emitter
            assert hasattr(websocket_bridge, '_user_emitter'), (
                "INTEGRATION GAP: AgentWebSocketBridge missing _user_emitter attribute. "
                "Per-request factory pattern not creating user-specific emitters."
            )
            
            user_emitter = websocket_bridge._user_emitter
            assert user_emitter is not None, (
                "INTEGRATION GAP: AgentWebSocketBridge._user_emitter is None. "
                "create_user_emitter() factory method failing."
            )
            
            # CRITICAL FAILURE POINT: Check if user emitter can emit events
            # This is where WebSocket events should be sent to users
            assert hasattr(user_emitter, 'emit_agent_started'), (
                "INTEGRATION GAP: UserWebSocketEmitter missing emit_agent_started method. "
                "Event emission interface broken."
            )
            
            # Test the complete chain by simulating agent execution
            with patch.object(user_emitter, 'emit_agent_started', side_effect=mock_websocket_emit):
                with patch.object(user_emitter, 'emit_agent_thinking', side_effect=mock_websocket_emit):
                    with patch.object(user_emitter, 'emit_tool_executing', side_effect=mock_websocket_emit):
                        with patch.object(user_emitter, 'emit_tool_completed', side_effect=mock_websocket_emit):
                            with patch.object(user_emitter, 'emit_agent_completed', side_effect=mock_websocket_emit):
                                
                                # Simulate agent execution that should trigger events
                                try:
                                    # This should trigger WebSocket events through the chain
                                    await execution_engine.execute_agent_request(
                                        agent_type="triage_agent",
                                        message="Test integration gap",
                                        user_context=user_context
                                    )
                                    
                                    # CRITICAL ASSERTION: Events should be collected
                                    assert len(websocket_events) >= 2, (
                                        f"INTEGRATION GAP CONFIRMED: Only {len(websocket_events)} events collected. "
                                        f"Expected at least agent_started and agent_completed events. "
                                        f"This confirms the WebSocket integration is broken."
                                    )
                                    
                                    # Verify specific required events
                                    event_types = [event["event_type"] for event in websocket_events]
                                    
                                    assert "agent_started" in event_types, (
                                        "INTEGRATION GAP: agent_started event not sent. "
                                        "ExecutionEngine not triggering WebSocket notifications."
                                    )
                                    
                                    assert "agent_completed" in event_types, (
                                        "INTEGRATION GAP: agent_completed event not sent. "
                                        "Agent execution not properly notifying WebSocket system."
                                    )
                                    
                                except Exception as e:
                                    # This is the expected failure - capture it for analysis
                                    logger.error(f"INTEGRATION GAP CONFIRMED: Agent execution failed: {e}")
                                    
                                    # Verify this is the specific integration failure we're testing
                                    error_message = str(e).lower()
                                    integration_gap_indicators = [
                                        "websocket",
                                        "factory",
                                        "emitter",
                                        "bridge",
                                        "delegation"
                                    ]
                                    
                                    gap_detected = any(indicator in error_message for indicator in integration_gap_indicators)
                                    
                                    pytest.fail(
                                        f"INTEGRATION GAP REPRODUCED: Agent execution failed due to WebSocket integration issues. "
                                        f"Error: {e}. "
                                        f"Integration gap indicators detected: {gap_detected}. "
                                        f"This confirms the ExecutionEngine -> AgentWebSocketBridge chain is broken."
                                    )
                    
        except ImportError as e:
            pytest.fail(
                f"INTEGRATION GAP: Required components not available for testing. "
                f"Import error: {e}. "
                f"This indicates the factory pattern migration is incomplete."
            )
        
        except AttributeError as e:
            pytest.fail(
                f"INTEGRATION GAP CONFIRMED: Missing attributes in WebSocket chain. "
                f"AttributeError: {e}. "
                f"This confirms the integration between ExecutionEngine and AgentWebSocketBridge is broken."
            )
        
        except Exception as e:
            pytest.fail(
                f"INTEGRATION GAP: Unexpected failure in WebSocket chain testing. "
                f"Error: {e}. "
                f"Events collected: {len(websocket_events)}. "
                f"This indicates broader integration issues in the factory pattern."
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_delegation_handoff_failure(self, real_services_fixture):
        """
        Test the specific handoff point where ExecutionEngine should delegate to factories.
        
        EXPECTED: This test SHOULD FAIL because factory delegation is broken.
        
        Based on Five Whys Analysis:
        - ExecutionEngine factory delegation to UserExecutionEngine is broken
        - Per-request WebSocket emitter creation fails
        - Factory initialization failures cause cascade errors
        """
        # Setup test context
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="factory_test@example.com",
            environment="test"
        )
        
        logger.info(f"Testing factory delegation handoff for user: {user_context.user_id}")
        
        try:
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            
            # CRITICAL TEST: Factory should be configurable
            execution_factory = ExecutionEngineFactory()
            websocket_factory = WebSocketBridgeFactory()
            
            # Configure factories - this is where SSOT validation can fail
            try:
                execution_factory.configure()
                websocket_factory.configure()
            except Exception as e:
                pytest.fail(
                    f"FACTORY DELEGATION FAILURE: Factory configuration failed. "
                    f"Error: {e}. "
                    f"This confirms SSOT validation failures identified in Five Whys analysis."
                )
            
            # CRITICAL TEST: Factory should create user-specific instances
            try:
                execution_engine = execution_factory.create_execution_engine(user_context)
                assert execution_engine is not None, (
                    "Factory delegation failure: create_execution_engine returned None"
                )
            except Exception as e:
                pytest.fail(
                    f"FACTORY DELEGATION FAILURE: ExecutionEngine creation failed. "
                    f"Error: {e}. "
                    f"Factory pattern not properly implemented for user isolation."
                )
            
            # CRITICAL TEST: WebSocket factory should create user emitter
            try:
                user_emitter = websocket_factory.create_user_emitter(
                    user_id=str(user_context.user_id),
                    websocket_client_id=str(user_context.websocket_client_id)
                )
                assert user_emitter is not None, (
                    "Factory delegation failure: create_user_emitter returned None"
                )
            except Exception as e:
                pytest.fail(
                    f"FACTORY DELEGATION FAILURE: UserWebSocketEmitter creation failed. "
                    f"Error: {e}. "
                    f"create_user_emitter() factory method broken as identified in Five Whys."
                )
            
            # CRITICAL TEST: ExecutionEngine should have WebSocket bridge reference
            # This is the key integration point that's broken
            try:
                # Check if ExecutionEngine was configured with WebSocket bridge
                assert hasattr(execution_engine, '_websocket_bridge') or hasattr(execution_engine, 'websocket_bridge'), (
                    "INTEGRATION GAP CONFIRMED: ExecutionEngine lacks WebSocket bridge reference. "
                    "Factory delegation not establishing proper component connections."
                )
                
                # If bridge exists, verify it's properly configured
                websocket_bridge = getattr(execution_engine, '_websocket_bridge', None) or getattr(execution_engine, 'websocket_bridge', None)
                if websocket_bridge:
                    # Verify bridge has user emitter
                    assert hasattr(websocket_bridge, '_user_emitter') or hasattr(websocket_bridge, 'user_emitter'), (
                        "INTEGRATION GAP: WebSocket bridge lacks user emitter reference. "
                        "Per-request factory pattern not creating proper user-specific connections."
                    )
                
            except Exception as e:
                pytest.fail(
                    f"INTEGRATION GAP CONFIRMED: ExecutionEngine-WebSocket bridge integration broken. "
                    f"Error: {e}. "
                    f"This is the exact handoff failure identified in the Five Whys analysis."
                )
                
        except ImportError as e:
            pytest.fail(
                f"FACTORY DELEGATION FAILURE: Required factory components not available. "
                f"Import error: {e}. "
                f"Factory pattern migration incomplete."
            )

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_emitter_creation_failure_cascade(self, real_services_fixture):
        """
        Test the cascade failure when WebSocket emitter creation fails.
        
        EXPECTED: This test SHOULD FAIL due to dependency chain failures.
        
        Based on Five Whys Analysis:
        - WebSocket emitter creation has multiple failure points
        - Dependency chain requires all components to be perfectly initialized
        - No dependency management system to ensure chain integrity
        """
        # Setup test context
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="cascade_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        logger.info(f"Testing WebSocket emitter creation cascade for user: {user_context.user_id}")
        
        failure_points = []
        
        try:
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            
            # CRITICAL TEST: Factory should be able to create user emitter
            websocket_factory = WebSocketBridgeFactory()
            
            # Test each step in the dependency chain
            try:
                # Step 1: Factory configuration
                websocket_factory.configure()
                logger.info("[U+2713] Factory configuration succeeded")
            except Exception as e:
                failure_points.append(f"Factory configuration: {e}")
            
            try:
                # Step 2: Connection pool availability  
                assert hasattr(websocket_factory, '_connection_pool'), (
                    "Missing connection pool dependency"
                )
                connection_pool = websocket_factory._connection_pool
                assert connection_pool is not None, "Connection pool is None"
                logger.info("[U+2713] Connection pool available")
            except Exception as e:
                failure_points.append(f"Connection pool: {e}")
            
            try:
                # Step 3: Agent registry availability
                assert hasattr(websocket_factory, '_agent_registry'), (
                    "Missing agent registry dependency"
                )
                agent_registry = websocket_factory._agent_registry
                assert agent_registry is not None, "Agent registry is None"
                logger.info("[U+2713] Agent registry available")
            except Exception as e:
                failure_points.append(f"Agent registry: {e}")
            
            try:
                # Step 4: Health monitor availability
                assert hasattr(websocket_factory, '_health_monitor'), (
                    "Missing health monitor dependency"
                )
                health_monitor = websocket_factory._health_monitor
                assert health_monitor is not None, "Health monitor is None"
                logger.info("[U+2713] Health monitor available")
            except Exception as e:
                failure_points.append(f"Health monitor: {e}")
            
            try:
                # Step 5: User emitter creation (the final failure point)
                user_emitter = websocket_factory.create_user_emitter(
                    user_id=str(user_context.user_id),
                    websocket_client_id=str(user_context.websocket_client_id)
                )
                assert user_emitter is not None, "User emitter creation returned None"
                logger.info("[U+2713] User emitter created successfully")
                
                # If we get here, the test should fail because the integration gap should prevent this
                pytest.fail(
                    f"UNEXPECTED SUCCESS: User emitter creation succeeded when it should fail. "
                    f"This suggests the integration gap may have been partially fixed, "
                    f"but we need to verify the complete ExecutionEngine integration chain."
                )
                
            except Exception as e:
                failure_points.append(f"User emitter creation: {e}")
            
            # CRITICAL ASSERTION: If any failure points exist, the cascade failure is confirmed
            if failure_points:
                pytest.fail(
                    f"CASCADE FAILURE CONFIRMED: WebSocket emitter creation failed at multiple points. "
                    f"Failure points: {failure_points}. "
                    f"This confirms the complex dependency chain identified in Five Whys analysis. "
                    f"No dependency orchestration system ensures component availability."
                )
            
        except ImportError as e:
            pytest.fail(
                f"CASCADE FAILURE: WebSocket factory components not available. "
                f"Import error: {e}. "
                f"Dependency chain broken at import level."
            )
        
        except Exception as e:
            pytest.fail(
                f"CASCADE FAILURE: Unexpected error in dependency chain testing. "
                f"Error: {e}. "
                f"Failure points detected: {len(failure_points)}. "
                f"This indicates broader dependency management issues."
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_integration_gap_silent_failure_detection(self, real_services_fixture):
        """
        Test detection of silent failures in the WebSocket integration chain.
        
        EXPECTED: This test SHOULD FAIL by detecting silent event delivery failures.
        
        Based on Five Whys Analysis:
        - Dependency chain failures cause silent event delivery failures
        - Users lose trust due to lack of progress visibility
        - Complex dependency chain without proper dependency management
        """
        # Setup test context with monitoring
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="silent_failure_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        logger.info(f"Testing silent failure detection for user: {user_context.user_id}")
        
        # Track all WebSocket events that should be sent
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        received_events = []
        silent_failures = []
        
        def event_monitor(event_type: str, **kwargs):
            """Monitor function to track event delivery."""
            received_events.append(event_type)
            logger.info(f"Event monitored: {event_type}")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            
            # Create execution engine with monitoring
            execution_factory = ExecutionEngineFactory()
            execution_factory.configure()
            
            execution_engine = execution_factory.create_execution_engine(user_context)
            
            # CRITICAL TEST: Monitor for silent failures in event delivery
            # Patch all WebSocket event methods to detect if they're called
            websocket_methods = [
                'emit_agent_started',
                'emit_agent_thinking', 
                'emit_tool_executing',
                'emit_tool_completed',
                'emit_agent_completed'
            ]
            
            patches = []
            
            # Try to find the WebSocket emitter and patch its methods
            try:
                if hasattr(execution_engine, '_websocket_bridge'):
                    websocket_bridge = execution_engine._websocket_bridge
                    if hasattr(websocket_bridge, '_user_emitter'):
                        user_emitter = websocket_bridge._user_emitter
                        
                        for method_name in websocket_methods:
                            if hasattr(user_emitter, method_name):
                                original_method = getattr(user_emitter, method_name)
                                
                                def create_monitored_method(event_type, original):
                                    async def monitored_method(*args, **kwargs):
                                        event_monitor(event_type)
                                        return await original(*args, **kwargs)
                                    return monitored_method
                                
                                event_type = method_name.replace('emit_', '')
                                monitored_method = create_monitored_method(event_type, original_method)
                                setattr(user_emitter, method_name, monitored_method)
                                
                                logger.info(f"Monitoring patched for: {method_name}")
                            else:
                                silent_failures.append(f"Method {method_name} not found on user emitter")
                    else:
                        silent_failures.append("User emitter not found on WebSocket bridge")
                else:
                    silent_failures.append("WebSocket bridge not found on execution engine")
                    
            except Exception as e:
                silent_failures.append(f"Failed to setup event monitoring: {e}")
            
            # CRITICAL TEST: Execute agent and monitor for silent failures
            try:
                # Simulate a simple agent execution that should trigger events
                test_message = "Test message for silent failure detection"
                
                # This should trigger WebSocket events through the chain
                result = await execution_engine.execute_agent_request(
                    agent_type="triage_agent",
                    message=test_message,
                    user_context=user_context
                )
                
                # Check for silent failures
                missing_events = [event for event in expected_events if event not in received_events]
                
                if missing_events or silent_failures:
                    pytest.fail(
                        f"SILENT FAILURE DETECTED: WebSocket events not delivered silently. "
                        f"Missing events: {missing_events}. "
                        f"Silent failures: {silent_failures}. "
                        f"Received events: {received_events}. "
                        f"This confirms the integration gap causes silent event delivery failures."
                    )
                
            except Exception as e:
                # Agent execution failure is expected - check if it's due to integration issues
                error_message = str(e).lower()
                integration_keywords = ['websocket', 'emitter', 'bridge', 'factory', 'delegation']
                integration_failure = any(keyword in error_message for keyword in integration_keywords)
                
                pytest.fail(
                    f"SILENT FAILURE CONFIRMED: Agent execution failed with integration-related error. "
                    f"Error: {e}. "
                    f"Integration failure detected: {integration_failure}. "
                    f"Silent failures: {silent_failures}. "
                    f"This confirms the WebSocket integration chain is broken."
                )
                
        except ImportError as e:
            pytest.fail(
                f"SILENT FAILURE: Required components for integration testing not available. "
                f"Import error: {e}. "
                f"This indicates incomplete factory pattern migration."
            )
        
        except Exception as e:
            pytest.fail(
                f"SILENT FAILURE: Unexpected error during silent failure detection. "
                f"Error: {e}. "
                f"Silent failures detected: {len(silent_failures)}. "
                f"Received events: {len(received_events)}/{len(expected_events)}. "
                f"This indicates broader integration issues in the WebSocket chain."
            )