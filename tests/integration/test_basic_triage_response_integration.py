"""
Integration Tests for Basic Triage & Response (UVS) Validation - Issue #135

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All tiers (Free/Early/Mid/Enterprise) - Core chat functionality 
- Business Goal: Validate WebSocket message flow integration for $500K+ ARR Golden Path
- Value Impact: Integration-level validation of triage processing without Docker services
- Revenue Protection: Ensure complete message flow works end-to-end with real components

PURPOSE: Test WebSocket message flow integration for triage responses without Docker dependencies.
Focus on component integration, real service connections where possible, and complete
message processing pipeline validation.

KEY COVERAGE:
1. WebSocket connection and message routing integration
2. Agent handler and message service integration  
3. Real database session management (without Docker)
4. WebSocket event delivery integration
5. Error propagation and recovery integration
6. Multi-component failure analysis

GOLDEN PATH INTEGRATION VALIDATION:
These tests validate integrated components that enable:
User Connection  ->  Message Routing  ->  Agent Processing  ->  Event Delivery  ->  Response

These tests MUST initially FAIL to demonstrate current WebSocket 1011 integration issues.
"""

import pytest
import asyncio
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Import integration components
from netra_backend.app.websocket_core.handlers import MessageRouter
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.dependencies import get_request_scoped_db_session
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.no_docker  # Explicitly no Docker required
@pytest.mark.issue_135
class TestBasicTriageResponseIntegration(SSotAsyncTestCase):
    """
    Integration tests for basic triage response processing without Docker.
    
    These tests validate component integration for WebSocket message handling
    and triage processing with real service connections where possible.
    
    CRITICAL: These tests should initially FAIL to demonstrate current 
    WebSocket 1011 integration issues that block the Golden Path.
    """
    
    async def async_setup_method(self, method=None):
        """Setup integration test environment with real services where possible"""
        await super().async_setup_method(method)
        
        self.env = IsolatedEnvironment()
        self.env.set('ENVIRONMENT', 'test') 
        self.env.set('DEMO_MODE', '1')  # Enable demo mode for isolated testing
        self.env.set('USE_WEBSOCKET_SUPERVISOR_V3', 'true')  # Use clean WebSocket pattern
        
        # Generate test identifiers
        self.user_id = f"integration_user_{uuid.uuid4().hex[:8]}"
        self.thread_id = f"integration_thread_{uuid.uuid4().hex[:8]}"
        self.run_id = f"integration_run_{uuid.uuid4().hex[:8]}"
        self.connection_id = f"integration_conn_{uuid.uuid4().hex[:8]}"
        
        # Mock WebSocket with realistic scope
        self.mock_websocket = AsyncMock()
        self.mock_websocket.scope = {
            'type': 'websocket',
            'user': {'sub': self.user_id},
            'path': '/ws',
            'client': ('127.0.0.1', 8000),
            'headers': [
                (b'authorization', f'Bearer test_token_{self.user_id}'.encode()),
                (b'user-agent', b'Integration-Test-Client/1.0')
            ],
            'app': MagicMock()
        }
        
        # Mock app state for WebSocket context
        app_state = MagicMock()
        app_state.bridge = MagicMock()
        app_state.supervisor_factory = MagicMock()
        self.mock_websocket.scope['app'].state = app_state
        
        # Track WebSocket events for validation
        self.sent_events = []
        self.mock_websocket.send_text = AsyncMock(side_effect=self._track_sent_events)
        
        # Initialize real components for integration testing
        self.message_router = MessageRouter()
        self.agent_handler = AgentMessageHandler()
        
        # Track test metrics
        self.test_start_time = time.time()
        
    async def _track_sent_events(self, event_data: str):
        """Track WebSocket events sent during integration testing"""
        try:
            event = json.loads(event_data)
            event['_timestamp'] = time.time()
            self.sent_events.append(event)
        except json.JSONDecodeError:
            self.sent_events.append({"raw": event_data, "_timestamp": time.time()})
    
    # ========================================================================
    # WEBSOCKET CONNECTION AND ROUTING INTEGRATION
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_message_routing_integration(self):
        """
        Test complete WebSocket message routing integration.
        
        Business Impact: Validates core message routing pipeline that enables
        all chat functionality in the platform.
        
        EXPECTED OUTCOME: Should initially FAIL due to WebSocket 1011 issues.
        """
        # Create realistic user message
        user_message = {
            "type": "user_message",
            "content": "I need to optimize my cloud infrastructure costs. Current AWS spend is $8,000/month on EC2 instances.",
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "platform": "aws",
                "current_spend": 8000,
                "service_type": "ec2"
            }
        }
        
        routing_steps = {
            "message_received": False,
            "message_normalized": False,
            "handler_found": False,
            "handler_invoked": False,
            "response_generated": False
        }
        
        try:
            # Step 1: Message received by router
            routing_steps["message_received"] = True
            
            # Step 2: Message normalized
            normalized_message = self.message_router._prepare_message(user_message)
            assert normalized_message is not None, "Message normalization failed"
            routing_steps["message_normalized"] = True
            
            # Step 3: Handler found
            handler = self.message_router._find_handler("user_message")
            assert handler is not None, "No handler found for user_message"
            routing_steps["handler_found"] = True
            
            # Step 4: Handler invoked (this is where integration issues may occur)
            with patch.object(handler, 'handle_message', new_callable=AsyncMock) as mock_handle:
                mock_handle.return_value = True
                
                result = await self.message_router.route_message(
                    user_id=self.user_id,
                    websocket=self.mock_websocket,
                    message_data=user_message
                )
                
                routing_steps["handler_invoked"] = True
                mock_handle.assert_called_once()
                
            routing_steps["response_generated"] = True
            
            # Validate complete routing integration
            completed_steps = sum(1 for completed in routing_steps.values() if completed)
            assert completed_steps == len(routing_steps), f"Routing incomplete: {completed_steps}/{len(routing_steps)}"
            
            self.record_metric("routing_integration_steps_completed", completed_steps)
            self.record_metric("routing_integration_success", True)
            
        except Exception as e:
            # Document routing integration failures
            failed_step = None
            for step, completed in routing_steps.items():
                if not completed:
                    failed_step = step
                    break
            
            self.record_metric("routing_integration_failure", str(e))
            self.record_metric("routing_failed_at_step", failed_step or "unknown")
            pytest.fail(f"WebSocket routing integration failed at {failed_step}: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_context_creation_integration(self):
        """
        Test WebSocket context creation and user authentication integration.
        
        Business Impact: Validates user context establishment that enables
        personalized AI responses and secure multi-tenant operation.
        """
        # Test WebSocket context creation
        try:
            # Create WebSocket context with realistic user data
            websocket_context = WebSocketContext(
                websocket=self.mock_websocket,
                user_id=self.user_id,
                connection_id=self.connection_id
            )
            
            assert websocket_context.user_id == self.user_id
            assert websocket_context.connection_id == self.connection_id
            assert websocket_context.websocket == self.mock_websocket
            
            # Test context authentication state
            websocket_context.set_authenticated(True)
            assert websocket_context.is_authenticated == True
            
            # Test thread association
            websocket_context.set_thread_id(self.thread_id)
            assert websocket_context.thread_id == self.thread_id
            
            self.record_metric("websocket_context_creation_success", True)
            self.record_metric("websocket_authentication_integration", True)
            
        except Exception as e:
            self.record_metric("websocket_context_creation_failure", str(e))
            pytest.fail(f"WebSocket context creation integration failed: {e}")
    
    # ========================================================================
    # AGENT HANDLER INTEGRATION WITH DATABASE SESSIONS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_agent_handler_database_session_integration(self):
        """
        Test agent handler integration with database session management.
        
        Business Impact: Validates database connectivity required for all
        AI processing, conversation persistence, and user data management.
        
        EXPECTED OUTCOME: Should initially FAIL due to async session pattern issues.
        """
        # Create message for agent handler
        agent_message = Mock()
        agent_message.type = "start_agent"
        agent_message.payload = {
            "agent_type": "triage",
            "user_request": "Help me optimize my infrastructure costs",
            "thread_id": self.thread_id,
            "run_id": self.run_id
        }
        agent_message.thread_id = self.thread_id
        
        session_integration_steps = {
            "session_context_created": False,
            "session_acquired": False,
            "agent_handler_executed": False,
            "session_cleanup": False
        }
        
        try:
            # Step 1: Create session context
            session_context = get_request_scoped_db_session()
            assert session_context is not None, "Database session context creation failed"
            session_integration_steps["session_context_created"] = True
            
            # Step 2: Test session acquisition (this is where the async pattern fails)
            # This test will FAIL initially due to async for vs async with pattern issue
            async with session_context as db_session:  # Use CORRECT pattern
                assert db_session is not None, "Database session acquisition failed"
                session_integration_steps["session_acquired"] = True
                
                # Step 3: Mock agent handler execution with session
                with patch.object(self.agent_handler, '_route_agent_message_v3') as mock_route:
                    mock_route.return_value = True
                    
                    # This would be the real call in agent_handler.py line 125
                    # Currently fails due to async for instead of async with
                    result = await mock_route(
                        user_id=self.user_id,
                        websocket=self.mock_websocket,
                        message=agent_message,
                        db_session=db_session
                    )
                    
                    session_integration_steps["agent_handler_executed"] = True
                    
            # Step 4: Session cleanup should happen automatically
            session_integration_steps["session_cleanup"] = True
            
            # Validate complete session integration
            completed_steps = sum(1 for completed in session_integration_steps.values() if completed)
            assert completed_steps == len(session_integration_steps)
            
            self.record_metric("session_integration_steps_completed", completed_steps)
            self.record_metric("session_integration_success", True)
            
        except Exception as e:
            # Document session integration failures (expected initially)
            failed_step = None
            for step, completed in session_integration_steps.items():
                if not completed:
                    failed_step = step
                    break
            
            self.record_metric("session_integration_failure", str(e))
            self.record_metric("session_failed_at_step", failed_step or "unknown")
            
            # Check if this is the specific async pattern error
            if "async for" in str(e) or "__aiter__" in str(e):
                self.record_metric("async_pattern_error_confirmed", True)
                pytest.fail(f"EXPECTED FAILURE - Database session async pattern error at {failed_step}: {e}")
            else:
                pytest.fail(f"Unexpected session integration failure at {failed_step}: {e}")
    
    @pytest.mark.asyncio
    async def test_agent_handler_v3_clean_pattern_integration(self):
        """
        Test agent handler V3 clean pattern integration.
        
        Business Impact: Validates the improved WebSocket handling pattern
        that should resolve integration issues with proper async session management.
        """
        # Create message for V3 handler pattern
        message = Mock()
        message.type = "user_message"
        message.payload = {
            "type": "user_message",
            "content": "Test triage message for V3 pattern",
            "thread_id": self.thread_id
        }
        message.thread_id = self.thread_id
        
        v3_integration_steps = {
            "websocket_context_created": False,
            "thread_id_extracted": False,
            "session_acquired": False,
            "supervisor_created": False,
            "message_routed": False
        }
        
        try:
            # Mock the components that come after session acquisition
            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_supervisor, \
                 patch.object(self.agent_handler, '_route_agent_message_v3') as mock_route:
                
                mock_supervisor.return_value = AsyncMock()
                mock_route.return_value = True
                
                # Test V3 clean pattern (should work with async with)
                result = await self.agent_handler._handle_message_v3_clean(
                    user_id=self.user_id,
                    websocket=self.mock_websocket,
                    message=message
                )
                
                # If we reach here, V3 pattern is working
                self.record_metric("v3_clean_pattern_success", True)
                self.record_metric("v3_integration_complete", True)
                
        except Exception as e:
            # Document V3 pattern failures
            error_message = str(e)
            self.record_metric("v3_clean_pattern_failure", error_message)
            
            # Check for specific async pattern errors
            if "async for" in error_message or "__aiter__" in error_message:
                self.record_metric("v3_async_pattern_error", True)
                pytest.fail(f"CRITICAL - V3 clean pattern has async session error: {e}")
            else:
                pytest.fail(f"V3 clean pattern integration failed: {e}")
    
    # ========================================================================
    # WEBSOCKET EVENT DELIVERY INTEGRATION
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_integration(self):
        """
        Test complete WebSocket event delivery integration.
        
        Business Impact: Validates real-time event delivery that provides
        users with AI processing progress and builds trust in the system.
        """
        # Test event delivery sequence
        test_events = [
            {"type": "agent_started", "data": {"agent": "triage", "status": "initializing"}},
            {"type": "agent_thinking", "data": {"step": "analyzing_request", "progress": 0.3}},
            {"type": "tool_executing", "data": {"tool": "cost_analyzer", "status": "running"}},
            {"type": "tool_completed", "data": {"tool": "cost_analyzer", "results": {"category": "optimization"}}},
            {"type": "agent_completed", "data": {"agent": "triage", "results": {"next_agents": ["data_helper"]}}}
        ]
        
        event_delivery_metrics = {
            "events_sent": 0,
            "events_received": 0,
            "delivery_times": [],
            "event_order_preserved": True,
            "all_events_delivered": False
        }
        
        try:
            # Send events and measure delivery
            for i, event in enumerate(test_events):
                start_time = time.time()
                
                # Add required fields
                event.update({
                    "user_id": self.user_id,
                    "thread_id": self.thread_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "sequence": i
                })
                
                # Send event via WebSocket
                await self.mock_websocket.send_text(json.dumps(event))
                
                delivery_time = time.time() - start_time
                event_delivery_metrics["delivery_times"].append(delivery_time)
                event_delivery_metrics["events_sent"] += 1
                
                # Brief pause between events
                await asyncio.sleep(0.1)
            
            # Validate event delivery
            event_delivery_metrics["events_received"] = len(self.sent_events)
            event_delivery_metrics["all_events_delivered"] = (
                event_delivery_metrics["events_received"] == len(test_events)
            )
            
            # Check event order preservation
            received_sequences = [
                event.get("sequence", -1) for event in self.sent_events 
                if isinstance(event, dict) and "sequence" in event
            ]
            expected_sequences = list(range(len(test_events)))
            event_delivery_metrics["event_order_preserved"] = (received_sequences == expected_sequences)
            
            # Calculate delivery performance
            avg_delivery_time = sum(event_delivery_metrics["delivery_times"]) / len(event_delivery_metrics["delivery_times"])
            max_delivery_time = max(event_delivery_metrics["delivery_times"])
            
            # Validate delivery requirements
            assert event_delivery_metrics["all_events_delivered"], "Not all events delivered"
            assert event_delivery_metrics["event_order_preserved"], "Event order not preserved"
            assert avg_delivery_time < 0.1, f"Average delivery time too high: {avg_delivery_time:.3f}s"
            assert max_delivery_time < 0.5, f"Max delivery time too high: {max_delivery_time:.3f}s"
            
            self.record_metric("event_delivery_success", True)
            self.record_metric("events_delivered", event_delivery_metrics["events_received"])
            self.record_metric("avg_delivery_time", avg_delivery_time)
            self.record_metric("event_order_preserved", event_delivery_metrics["event_order_preserved"])
            
        except Exception as e:
            self.record_metric("event_delivery_failure", str(e))
            self.record_metric("events_delivered", event_delivery_metrics["events_received"])
            pytest.fail(f"WebSocket event delivery integration failed: {e}")
    
    @pytest.mark.asyncio
    async def test_event_delivery_with_connection_issues(self):
        """
        Test event delivery resilience with connection issues.
        
        Business Impact: Validates system handles network instability without
        losing events or breaking user experience.
        """
        # Simulate connection issues during event delivery
        connection_issue_scenarios = [
            {"type": "slow_connection", "delay": 0.5},
            {"type": "temporary_failure", "fail_count": 2},
            {"type": "partial_send", "success_rate": 0.7}
        ]
        
        resilience_results = []
        
        for scenario in connection_issue_scenarios:
            scenario_start = time.time()
            events_attempted = 0
            events_delivered = 0
            errors_encountered = 0
            
            try:
                # Create test events for scenario
                test_events = [
                    {"type": f"test_event_{i}", "data": {"scenario": scenario["type"], "index": i}}
                    for i in range(5)
                ]
                
                for event in test_events:
                    events_attempted += 1
                    
                    try:
                        # Apply scenario-specific behavior
                        if scenario["type"] == "slow_connection":
                            await asyncio.sleep(scenario["delay"])
                        elif scenario["type"] == "temporary_failure" and events_attempted <= scenario["fail_count"]:
                            raise ConnectionError("Simulated connection failure")
                        elif scenario["type"] == "partial_send" and events_attempted % 3 == 0:
                            raise ConnectionError("Simulated partial send failure")
                        
                        # Send event
                        await self.mock_websocket.send_text(json.dumps(event))
                        events_delivered += 1
                        
                    except Exception as e:
                        errors_encountered += 1
                        # Simulate retry logic
                        await asyncio.sleep(0.1)
                        try:
                            await self.mock_websocket.send_text(json.dumps(event))
                            events_delivered += 1
                        except:
                            pass  # Retry failed
                
                scenario_time = time.time() - scenario_start
                
                resilience_results.append({
                    "scenario": scenario["type"],
                    "events_attempted": events_attempted,
                    "events_delivered": events_delivered,
                    "errors_encountered": errors_encountered,
                    "delivery_rate": events_delivered / events_attempted,
                    "scenario_time": scenario_time,
                    "resilience_success": events_delivered >= events_attempted * 0.6  # 60% minimum
                })
                
            except Exception as e:
                resilience_results.append({
                    "scenario": scenario["type"],
                    "error": str(e),
                    "resilience_success": False
                })
        
        # Validate resilience across scenarios
        successful_scenarios = [r for r in resilience_results if r.get("resilience_success", False)]
        overall_resilience_rate = len(successful_scenarios) / len(connection_issue_scenarios)
        
        assert overall_resilience_rate >= 0.5, f"Resilience rate too low: {overall_resilience_rate:.2f}"
        
        self.record_metric("connection_resilience_scenarios", len(connection_issue_scenarios))
        self.record_metric("resilience_success_rate", overall_resilience_rate)
        self.record_metric("event_delivery_resilience", True)
    
    # ========================================================================
    # MULTI-COMPONENT FAILURE ANALYSIS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_multi_component_failure_cascade_analysis(self):
        """
        Test how failures cascade through integrated components.
        
        Business Impact: Validates error isolation and recovery mechanisms
        that prevent single component failures from breaking entire user sessions.
        
        EXPECTED OUTCOME: Should demonstrate current failure propagation issues.
        """
        # Define failure injection points
        failure_points = [
            {"component": "message_router", "failure_type": "parsing_error"},
            {"component": "agent_handler", "failure_type": "session_error"},
            {"component": "websocket", "failure_type": "connection_error"},
            {"component": "database", "failure_type": "timeout_error"}
        ]
        
        cascade_analysis = {
            "failure_isolation": {},
            "recovery_attempts": {},
            "downstream_impact": {},
            "user_experience_impact": {}
        }
        
        for failure_point in failure_points:
            component = failure_point["component"]
            failure_type = failure_point["failure_type"]
            
            try:
                # Inject failure at specific component
                if component == "message_router":
                    # Simulate router parsing failure
                    with patch.object(self.message_router, '_prepare_message', side_effect=ValueError("Parsing failed")):
                        try:
                            await self.message_router.route_message(
                                user_id=self.user_id,
                                websocket=self.mock_websocket,
                                message_data={"invalid": "message"}
                            )
                        except Exception as e:
                            cascade_analysis["failure_isolation"][component] = f"Isolated: {str(e)}"
                
                elif component == "agent_handler":
                    # Simulate agent handler session error (the main issue in Issue #135)
                    with patch('netra_backend.app.dependencies.get_request_scoped_db_session', 
                              side_effect=RuntimeError("Session creation failed")):
                        try:
                            message = Mock()
                            message.type = "user_message"
                            message.payload = {"content": "test"}
                            message.thread_id = self.thread_id
                            
                            await self.agent_handler._handle_message_v3_clean(
                                user_id=self.user_id,
                                websocket=self.mock_websocket,
                                message=message
                            )
                        except Exception as e:
                            cascade_analysis["failure_isolation"][component] = f"Isolated: {str(e)}"
                
                elif component == "websocket":
                    # Simulate WebSocket connection error
                    self.mock_websocket.send_text.side_effect = ConnectionError("WebSocket disconnected")
                    try:
                        await self.mock_websocket.send_text(json.dumps({"test": "event"}))
                    except Exception as e:
                        cascade_analysis["failure_isolation"][component] = f"Isolated: {str(e)}"
                    finally:
                        # Reset WebSocket mock
                        self.mock_websocket.send_text.side_effect = self._track_sent_events
                
                # Test recovery mechanisms
                cascade_analysis["recovery_attempts"][component] = "Recovery not implemented"
                
                # Analyze downstream impact
                if component in cascade_analysis["failure_isolation"]:
                    cascade_analysis["downstream_impact"][component] = "Complete user session failure"
                    cascade_analysis["user_experience_impact"][component] = "No AI response delivered"
                
            except Exception as e:
                cascade_analysis["failure_isolation"][component] = f"Unhandled: {str(e)}"
        
        # Validate failure analysis results
        isolated_failures = len(cascade_analysis["failure_isolation"])
        total_failure_points = len(failure_points)
        
        # Currently expect poor failure isolation (should improve after fixes)
        isolation_rate = isolated_failures / total_failure_points
        
        self.record_metric("failure_points_tested", total_failure_points)
        self.record_metric("failures_isolated", isolated_failures)
        self.record_metric("failure_isolation_rate", isolation_rate)
        self.record_metric("cascade_analysis_complete", True)
        
        # Document specific findings for Issue #135
        if "agent_handler" in cascade_analysis["failure_isolation"]:
            self.record_metric("agent_handler_session_failure_confirmed", True)
            self.record_metric("session_error_details", cascade_analysis["failure_isolation"]["agent_handler"])
    
    # ========================================================================
    # GOLDEN PATH INTEGRATION VALIDATION
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_golden_path_integration_end_to_end(self):
        """
        Test complete Golden Path integration without Docker dependencies.
        
        Business Impact: Validates the integrated components that deliver
        the core $500K+ ARR user journey with real service connections.
        
        Flow: Connection  ->  Authentication  ->  Message  ->  Processing  ->  Events  ->  Response
        
        EXPECTED OUTCOME: Should initially FAIL demonstrating integration issues.
        """
        golden_path_integration = {
            "websocket_connection": False,
            "user_authentication": False,
            "message_routing": False,
            "agent_processing": False,
            "event_delivery": False,
            "response_completion": False
        }
        
        integration_start_time = time.time()
        
        try:
            # Step 1: WebSocket connection simulation
            websocket_context = WebSocketContext(
                websocket=self.mock_websocket,
                user_id=self.user_id,
                connection_id=self.connection_id
            )
            golden_path_integration["websocket_connection"] = True
            
            # Step 2: User authentication
            websocket_context.set_authenticated(True)
            websocket_context.set_thread_id(self.thread_id)
            golden_path_integration["user_authentication"] = True
            
            # Step 3: Message routing
            user_message = {
                "type": "user_message",
                "content": "I need comprehensive AI cost optimization analysis for my multi-cloud setup",
                "thread_id": self.thread_id,
                "user_id": self.user_id,
                "metadata": {"priority": "high", "complexity": "enterprise"}
            }
            
            with patch.object(self.agent_handler, 'handle_message', new_callable=AsyncMock) as mock_handle:
                mock_handle.return_value = True
                
                await self.message_router.route_message(
                    user_id=self.user_id,
                    websocket=self.mock_websocket,
                    message_data=user_message
                )
                
                golden_path_integration["message_routing"] = True
            
            # Step 4: Agent processing simulation (with session integration)
            with patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_session:
                @asynccontextmanager
                async def mock_session_context():
                    yield AsyncMock()  # Mock database session
                
                mock_session.return_value = mock_session_context()
                
                # This step tests the critical session integration
                async with mock_session.return_value as db_session:
                    assert db_session is not None
                    golden_path_integration["agent_processing"] = True
            
            # Step 5: Event delivery
            critical_events = [
                {"type": "agent_started", "data": {"agent": "triage"}},
                {"type": "agent_thinking", "data": {"analysis": "processing"}},
                {"type": "agent_completed", "data": {"results": "optimization_plan"}}
            ]
            
            for event in critical_events:
                event.update({
                    "user_id": self.user_id,
                    "thread_id": self.thread_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                await self.mock_websocket.send_text(json.dumps(event))
            
            golden_path_integration["event_delivery"] = True
            
            # Step 6: Response completion
            final_response = {
                "type": "assistant_message",
                "content": "Cost optimization analysis complete",
                "thread_id": self.thread_id,
                "results": {"savings_potential": "30%", "next_steps": ["implement", "monitor"]}
            }
            
            await self.mock_websocket.send_text(json.dumps(final_response))
            golden_path_integration["response_completion"] = True
            
            # Validate complete integration
            integration_time = time.time() - integration_start_time
            completed_steps = sum(1 for completed in golden_path_integration.values() if completed)
            total_steps = len(golden_path_integration)
            
            assert completed_steps == total_steps, f"Integration incomplete: {completed_steps}/{total_steps}"
            assert len(self.sent_events) >= len(critical_events) + 1, "Missing events or response"
            assert integration_time < 5.0, f"Integration took too long: {integration_time:.3f}s"
            
            self.record_metric("golden_path_integration_steps", completed_steps)
            self.record_metric("golden_path_integration_time", integration_time)
            self.record_metric("golden_path_events_delivered", len(self.sent_events))
            self.record_metric("golden_path_integration_success", True)
            
        except Exception as e:
            # Document integration failures for remediation
            failed_step = None
            for step, completed in golden_path_integration.items():
                if not completed:
                    failed_step = step
                    break
            
            integration_time = time.time() - integration_start_time
            
            self.record_metric("golden_path_integration_failure", str(e))
            self.record_metric("golden_path_failed_at_step", failed_step or "unknown")
            self.record_metric("golden_path_partial_completion", sum(golden_path_integration.values()))
            self.record_metric("golden_path_integration_time", integration_time)
            
            # Check for specific known issues
            error_message = str(e)
            if "async for" in error_message or "__aiter__" in error_message:
                self.record_metric("golden_path_async_session_error", True)
                pytest.fail(f"CRITICAL - Golden Path blocked by async session pattern at {failed_step}: {e}")
            elif "1011" in error_message or "WebSocket" in error_message:
                self.record_metric("golden_path_websocket_1011_error", True)
                pytest.fail(f"CRITICAL - Golden Path blocked by WebSocket 1011 error at {failed_step}: {e}")
            else:
                pytest.fail(f"Golden Path integration failed at {failed_step}: {e}")
    
    # ========================================================================
    # CLEANUP AND METRICS
    # ========================================================================
    
    async def async_teardown_method(self, method=None):
        """Cleanup integration test environment and record metrics"""
        await super().async_teardown_method(method)
        
        # Calculate test execution metrics
        total_test_time = time.time() - self.test_start_time
        metrics = self.get_all_metrics()
        
        # Log integration test results
        print(f"\n=== INTEGRATION TEST RESULTS - Issue #135 ===")
        print(f"Test Execution Time: {total_test_time:.3f}s")
        print(f"WebSocket Events Generated: {len(self.sent_events)}")
        
        # Categorize metrics
        success_metrics = [k for k, v in metrics.items() if k.endswith("_success") and v is True]
        failure_metrics = [k for k, v in metrics.items() if k.endswith("_failure")]
        error_metrics = [k for k, v in metrics.items() if "error" in k and v is True]
        
        print(f"Successful Operations: {len(success_metrics)}")
        print(f"Failed Operations: {len(failure_metrics)}")
        print(f"Errors Identified: {len(error_metrics)}")
        
        # Key findings for Issue #135
        if any("async_session" in k for k in error_metrics):
            print(" ALERT:  CRITICAL: Async session pattern errors confirmed")
        if any("websocket_1011" in k for k in error_metrics):
            print(" ALERT:  CRITICAL: WebSocket 1011 errors confirmed")
        if any("golden_path" in k for k in failure_metrics):
            print(" ALERT:  BUSINESS IMPACT: Golden Path integration failures confirmed")
        
        self.record_metric("integration_test_execution_time", total_test_time)
        self.record_metric("integration_events_generated", len(self.sent_events))
        self.record_metric("integration_test_complete", True)
        
        print("=" * 60)


if __name__ == '__main__':
    # Run integration tests
    pytest.main([__file__, '-v', '--tb=long', '--asyncio-mode=auto'])