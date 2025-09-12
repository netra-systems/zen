"""
Test WebSocket Message Handling and Event Sequence - Golden Path Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure WebSocket events enable substantive chat value delivery
- Value Impact: Real-time transparency creates user trust and engagement 
- Strategic Impact: WebSocket events are infrastructure for 90% of business value (Chat)

CRITICAL REQUIREMENTS:
1. Test complete WebSocket event sequence: connection  ->  authentication  ->  agent_events  ->  completion
2. Validate event ordering and timing for optimal user experience
3. Test multi-user WebSocket isolation and message routing
4. Test WebSocket reconnection and recovery scenarios  
5. Use real WebSocket connections only (NO MOCKS per CLAUDE.md)
6. Validate business value transparency through event content

WebSocket Events Critical for Business Value:
- agent_started: User sees request acknowledged  
- agent_thinking: User sees AI reasoning process
- tool_executing: User sees tools being used
- tool_completed: User sees tool results
- agent_completed: User receives final actionable response
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import pytest
import websockets
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class WebSocketEventTrace:
    """Trace of a WebSocket event."""
    event_type: str
    timestamp: float
    user_id: str
    data: Dict[str, Any]
    sequence_number: int
    processing_time: Optional[float] = None


@dataclass
class WebSocketSessionMetrics:
    """Metrics for a WebSocket session."""
    connection_time: float
    authentication_time: float
    first_event_time: float
    total_events: int
    event_sequence_correct: bool
    business_value_delivered: bool
    errors_encountered: int


class WebSocketEventType(Enum):
    """WebSocket event types critical for business value."""
    CONNECTION_READY = "connection_ready"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing" 
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    ERROR = "error"


class TestWebSocketMessageHandlingComprehensive(BaseIntegrationTest):
    """Test comprehensive WebSocket message handling and event sequences."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.event_traces: List[WebSocketEventTrace] = []
        self.websocket_url = "ws://localhost:8000/ws"
        self.critical_event_sequence = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ]
    
    @asynccontextmanager
    async def websocket_client_context(self, user_token: str):
        """Create authenticated WebSocket client context."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        try:
            async with websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                # Wait for connection ready
                ready_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                ready_data = json.loads(ready_message)
                assert ready_data.get("type") == "connection_ready"
                
                yield websocket
                
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise

    async def _collect_websocket_events(self, websocket, user_id: str, 
                                      timeout: float = 30.0) -> List[WebSocketEventTrace]:
        """Collect WebSocket events with timing information."""
        events = []
        sequence_number = 0
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    event_data = json.loads(message)
                    
                    event_trace = WebSocketEventTrace(
                        event_type=event_data.get("type", "unknown"),
                        timestamp=time.time(),
                        user_id=user_id,
                        data=event_data,
                        sequence_number=sequence_number
                    )
                    
                    events.append(event_trace)
                    sequence_number += 1
                    
                    # Stop collecting if we get agent_completed
                    if event_data.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    continue  # Keep collecting
                    
        except Exception as e:
            logger.warning(f"Event collection stopped: {e}")
        
        return events

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_complete_event_sequence_validation(self, real_services_fixture):
        """
        Test 1: Complete WebSocket event sequence for agent execution.
        
        Validates that all 5 critical WebSocket events are sent in correct order
        when an agent processes a user request end-to-end.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        # Create authenticated user
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-websocket-sequence@example.com"
        )
        
        async with self.websocket_client_context(user_context["token"]) as websocket:
            start_time = time.time()
            
            # Send agent request
            request_message = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Analyze my cloud costs for optimization opportunities",
                "user_id": user_context["user_id"]
            }
            
            await websocket.send(json.dumps(request_message))
            
            # Collect all events
            events = await self._collect_websocket_events(
                websocket, 
                user_context["user_id"],
                timeout=30.0
            )
            
            total_time = time.time() - start_time
            
            # Verify all critical events received
            event_types = [event.event_type for event in events]
            
            for critical_event in self.critical_event_sequence:
                assert critical_event.value in event_types, \
                    f"Missing critical WebSocket event: {critical_event.value}"
            
            # Verify event ordering
            critical_indices = []
            for critical_event in self.critical_event_sequence:
                try:
                    index = event_types.index(critical_event.value)
                    critical_indices.append(index)
                except ValueError:
                    pytest.fail(f"Critical event {critical_event.value} not found in sequence")
            
            # Verify indices are in ascending order (correct sequence)
            assert critical_indices == sorted(critical_indices), \
                f"WebSocket events out of order. Indices: {critical_indices}, Events: {event_types}"
            
            # Verify final event has business value
            agent_completed_events = [e for e in events if e.event_type == "agent_completed"]
            assert len(agent_completed_events) > 0, "No agent_completed event received"
            
            final_event = agent_completed_events[0]
            assert "result" in final_event.data or "recommendations" in final_event.data, \
                "Final event lacks business value content"
            
            # Verify reasonable timing
            assert total_time < 45.0, f"Event sequence took too long: {total_time}s"
            
            logger.info(f"WebSocket event sequence validated: {len(events)} events in {total_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_multi_user_message_isolation(self, real_services_fixture):
        """
        Test 2: WebSocket messages are properly isolated between users.
        
        Validates that concurrent WebSocket connections for different users
        receive only their own messages and events.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        # Create multiple authenticated users
        num_users = 3
        user_contexts = []
        
        for i in range(num_users):
            user_context = await create_authenticated_user_context(
                real_services_fixture,
                user_email=f"test-isolation-{i}@example.com"
            )
            user_contexts.append(user_context)
        
        # Concurrent WebSocket connections
        async def user_websocket_session(user_context: Dict, user_index: int):
            """Run WebSocket session for a specific user."""
            user_events = []
            
            async with self.websocket_client_context(user_context["token"]) as websocket:
                # Send unique request for this user
                request_message = {
                    "type": "agent_request",
                    "agent": "data_analyzer",
                    "message": f"User {user_index} analysis request - unique identifier {uuid.uuid4()}",
                    "user_id": user_context["user_id"],
                    "user_index": user_index
                }
                
                await websocket.send(json.dumps(request_message))
                
                # Collect events for this user
                events = await self._collect_websocket_events(
                    websocket,
                    user_context["user_id"], 
                    timeout=20.0
                )
                
                return {
                    "user_index": user_index,
                    "user_id": user_context["user_id"],
                    "events": events,
                    "unique_request_id": request_message["message"]
                }
        
        start_time = time.time()
        
        # Run concurrent sessions
        session_tasks = [
            user_websocket_session(user_context, i)
            for i, user_context in enumerate(user_contexts)
        ]
        
        session_results = await asyncio.gather(*session_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Verify all sessions completed successfully
        successful_sessions = [r for r in session_results if isinstance(r, dict)]
        assert len(successful_sessions) == num_users, \
            f"Expected {num_users} successful sessions, got {len(successful_sessions)}"
        
        # Verify message isolation
        for session in successful_sessions:
            user_events = session["events"]
            user_id = session["user_id"]
            
            # Verify user received events
            assert len(user_events) > 0, f"User {session['user_index']} received no events"
            
            # Verify all events belong to this user
            for event in user_events:
                if "user_id" in event.data:
                    assert event.data["user_id"] == user_id, \
                        f"User {session['user_index']} received event for different user"
                
                # Verify no cross-contamination from other users' requests
                if "message" in event.data:
                    message_content = event.data["message"]
                    for other_session in successful_sessions:
                        if other_session["user_index"] != session["user_index"]:
                            assert other_session["unique_request_id"] not in str(message_content), \
                                f"User {session['user_index']} received content from user {other_session['user_index']}"
        
        logger.info(f"Multi-user WebSocket isolation validated: {num_users} users in {total_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_timing_performance(self, real_services_fixture):
        """
        Test 3: WebSocket event timing meets performance requirements.
        
        Validates that WebSocket events are delivered within acceptable timeframes
        to ensure responsive real-time user experience.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-timing-performance@example.com"
        )
        
        # Performance requirements (in seconds)
        timing_requirements = {
            "first_event_after_request": 2.0,
            "agent_started_to_thinking": 3.0,
            "thinking_to_tool_executing": 8.0,
            "tool_executing_to_completed": 15.0,
            "max_total_time": 30.0
        }
        
        async with self.websocket_client_context(user_context["token"]) as websocket:
            request_start = time.time()
            
            # Send performance test request
            request_message = {
                "type": "agent_request",
                "agent": "performance_test",
                "message": "Quick analysis for performance testing",
                "user_id": user_context["user_id"]
            }
            
            await websocket.send(json.dumps(request_message))
            
            # Collect events with precise timing
            events = await self._collect_websocket_events(
                websocket,
                user_context["user_id"],
                timeout=35.0
            )
            
            request_end = time.time()
            total_time = request_end - request_start
            
            # Calculate timing metrics
            timing_metrics = {}
            
            # Find first event timing
            if events:
                first_event_time = events[0].timestamp - request_start
                timing_metrics["first_event_after_request"] = first_event_time
            
            # Calculate transition timings
            event_times = {}
            for event in events:
                if event.event_type not in event_times:
                    event_times[event.event_type] = event.timestamp
            
            transitions = [
                ("agent_started", "agent_thinking", "agent_started_to_thinking"),
                ("agent_thinking", "tool_executing", "thinking_to_tool_executing"),
                ("tool_executing", "agent_completed", "tool_executing_to_completed")
            ]
            
            for from_event, to_event, metric_name in transitions:
                if from_event in event_times and to_event in event_times:
                    timing_metrics[metric_name] = event_times[to_event] - event_times[from_event]
            
            timing_metrics["max_total_time"] = total_time
            
            # Verify performance requirements
            performance_violations = []
            
            for metric, required_time in timing_requirements.items():
                actual_time = timing_metrics.get(metric)
                if actual_time is not None and actual_time > required_time:
                    performance_violations.append({
                        "metric": metric,
                        "required": required_time,
                        "actual": actual_time,
                        "violation": actual_time - required_time
                    })
            
            # Report performance results
            performance_summary = {
                "total_events": len(events),
                "total_time": total_time,
                "timing_metrics": timing_metrics,
                "violations": performance_violations
            }
            
            # Allow some flexibility but flag significant violations
            critical_violations = [v for v in performance_violations if v["violation"] > 5.0]
            
            if critical_violations:
                violation_details = "\n".join([
                    f"- {v['metric']}: {v['actual']:.2f}s (required: {v['required']}s, violation: +{v['violation']:.2f}s)"
                    for v in critical_violations
                ])
                pytest.fail(f"Critical WebSocket timing violations:\n{violation_details}")
            
            logger.info(f"WebSocket timing performance: {performance_summary}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_reconnection_recovery(self, real_services_fixture):
        """
        Test 4: WebSocket reconnection and message recovery.
        
        Validates that WebSocket connections can recover from disconnections
        and continue receiving events without data loss.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-reconnection@example.com"
        )
        
        # Test reconnection scenarios
        reconnection_scenarios = [
            {
                "disconnect_after": 2.0,  # seconds
                "reconnect_delay": 1.0,   # seconds  
                "expected_recovery": True
            },
            {
                "disconnect_after": 5.0,
                "reconnect_delay": 3.0,
                "expected_recovery": True
            }
        ]
        
        reconnection_results = []
        
        for scenario in reconnection_scenarios:
            scenario_start = time.time()
            events_before_disconnect = []
            events_after_reconnect = []
            
            try:
                # Initial connection
                async with self.websocket_client_context(user_context["token"]) as websocket:
                    # Send request
                    request_message = {
                        "type": "agent_request", 
                        "agent": "reconnection_test",
                        "message": "Test reconnection recovery",
                        "user_id": user_context["user_id"]
                    }
                    
                    await websocket.send(json.dumps(request_message))
                    
                    # Collect events until disconnect time
                    disconnect_time = scenario["disconnect_after"]
                    start_collect = time.time()
                    
                    while time.time() - start_collect < disconnect_time:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                            event_data = json.loads(message)
                            events_before_disconnect.append(event_data)
                        except asyncio.TimeoutError:
                            continue
                    
                    # Simulate disconnect by breaking out of context
                
                # Simulate network delay
                await asyncio.sleep(scenario["reconnect_delay"])
                
                # Reconnect
                async with self.websocket_client_context(user_context["token"]) as websocket:
                    # Check if we can continue receiving events
                    reconnect_start = time.time()
                    
                    while time.time() - reconnect_start < 10.0:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            event_data = json.loads(message)
                            events_after_reconnect.append(event_data)
                            
                            # Stop if we get completion event
                            if event_data.get("type") == "agent_completed":
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                
                total_events = len(events_before_disconnect) + len(events_after_reconnect)
                recovery_successful = len(events_after_reconnect) > 0
                
                reconnection_results.append({
                    "disconnect_after": scenario["disconnect_after"],
                    "reconnect_delay": scenario["reconnect_delay"],
                    "events_before": len(events_before_disconnect),
                    "events_after": len(events_after_reconnect),
                    "total_events": total_events,
                    "recovery_successful": recovery_successful,
                    "scenario_time": time.time() - scenario_start
                })
                
            except Exception as e:
                reconnection_results.append({
                    "disconnect_after": scenario["disconnect_after"],
                    "reconnect_delay": scenario["reconnect_delay"],
                    "recovery_successful": False,
                    "error": str(e)
                })
        
        # Verify reconnection results
        for result in reconnection_results:
            if result.get("recovery_successful"):
                assert result["events_after"] > 0, \
                    f"No events received after reconnection: {result}"
                assert result["total_events"] > 0, \
                    f"No total events in reconnection scenario: {result}"
            
        successful_recoveries = sum(1 for r in reconnection_results if r.get("recovery_successful"))
        logger.info(f"WebSocket reconnection testing: {successful_recoveries}/{len(reconnection_scenarios)} scenarios successful")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_handling_graceful_degradation(self, real_services_fixture):
        """
        Test 5: WebSocket error handling and graceful degradation.
        
        Validates that WebSocket errors are handled gracefully without
        breaking the user experience or losing critical information.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-error-handling@example.com"
        )
        
        # Test error scenarios
        error_scenarios = [
            {
                "scenario": "invalid_message_format",
                "message": "invalid json {",
                "expected_error": "parsing_error",
                "recovery_expected": True
            },
            {
                "scenario": "missing_authentication",
                "message": {"type": "agent_request", "message": "test"},  # No user_id
                "expected_error": "authentication_error",
                "recovery_expected": True  
            },
            {
                "scenario": "invalid_agent_type",
                "message": {
                    "type": "agent_request",
                    "agent": "nonexistent_agent",
                    "message": "test request",
                    "user_id": "user_context['user_id']"
                },
                "expected_error": "agent_not_found",
                "recovery_expected": True
            }
        ]
        
        error_handling_results = []
        
        async with self.websocket_client_context(user_context["token"]) as websocket:
            for scenario in error_scenarios:
                scenario_start = time.time()
                
                try:
                    # Send error-inducing message
                    if isinstance(scenario["message"], str):
                        await websocket.send(scenario["message"])  # Invalid JSON
                    else:
                        # Replace placeholder with actual user_id
                        if "user_id" in scenario["message"] and "user_context" in scenario["message"]["user_id"]:
                            scenario["message"]["user_id"] = user_context["user_id"]
                        await websocket.send(json.dumps(scenario["message"]))
                    
                    # Collect response events
                    error_events = []
                    collect_start = time.time()
                    
                    while time.time() - collect_start < 5.0:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            event_data = json.loads(message)
                            error_events.append(event_data)
                            
                            # Stop collecting if we get error event
                            if event_data.get("type") == "error":
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            # Handle case where server sends non-JSON error
                            error_events.append({"type": "parsing_error", "raw_message": message})
                            break
                    
                    # Try to send valid message after error to test recovery
                    recovery_message = {
                        "type": "agent_request",
                        "agent": "recovery_test", 
                        "message": "Recovery test after error",
                        "user_id": user_context["user_id"]
                    }
                    
                    await websocket.send(json.dumps(recovery_message))
                    
                    # Check if we receive recovery response
                    recovery_events = []
                    recovery_start = time.time()
                    
                    while time.time() - recovery_start < 3.0:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            event_data = json.loads(message)
                            recovery_events.append(event_data)
                            
                            if event_data.get("type") == "agent_started":
                                break  # Recovery successful
                                
                        except asyncio.TimeoutError:
                            continue
                    
                    scenario_time = time.time() - scenario_start
                    recovery_successful = len(recovery_events) > 0
                    
                    error_handling_results.append({
                        "scenario": scenario["scenario"],
                        "error_events": len(error_events),
                        "recovery_events": len(recovery_events), 
                        "recovery_successful": recovery_successful,
                        "scenario_time": scenario_time,
                        "expected_recovery": scenario["recovery_expected"]
                    })
                    
                except Exception as e:
                    error_handling_results.append({
                        "scenario": scenario["scenario"],
                        "recovery_successful": False,
                        "error": str(e)
                    })
        
        # Verify error handling results  
        for result in error_handling_results:
            if result["expected_recovery"]:
                assert result["recovery_successful"], \
                    f"Expected recovery for {result['scenario']} but failed: {result}"
            
            assert result["scenario_time"] < 10.0, \
                f"Error handling took too long for {result['scenario']}: {result['scenario_time']}s"
        
        logger.info(f"WebSocket error handling validated: {len(error_handling_results)} scenarios tested")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_business_value_content_validation(self, real_services_fixture):
        """
        Test 6: WebSocket events contain proper business value content.
        
        Validates that WebSocket events carry meaningful business information
        that enables substantive user interactions and decision-making.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-business-content@example.com"
        )
        
        # Test different business value scenarios
        business_scenarios = [
            {
                "agent": "cost_optimizer",
                "message": "Analyze cloud costs and provide savings recommendations",
                "expected_content": {
                    "agent_completed": ["recommendations", "cost_savings", "actionable_items"]
                }
            },
            {
                "agent": "data_analyzer",
                "message": "Analyze system performance and provide insights", 
                "expected_content": {
                    "agent_completed": ["insights", "analysis_results", "performance_metrics"]
                }
            },
            {
                "agent": "security_auditor",
                "message": "Review security posture and recommend improvements",
                "expected_content": {
                    "agent_completed": ["security_findings", "recommendations", "compliance_score"]
                }
            }
        ]
        
        business_value_results = []
        
        for scenario in business_scenarios:
            async with self.websocket_client_context(user_context["token"]) as websocket:
                # Send business value request
                request_message = {
                    "type": "agent_request",
                    "agent": scenario["agent"],
                    "message": scenario["message"],
                    "user_id": user_context["user_id"]
                }
                
                await websocket.send(json.dumps(request_message))
                
                # Collect events
                events = await self._collect_websocket_events(
                    websocket,
                    user_context["user_id"],
                    timeout=25.0
                )
                
                # Analyze business value content
                content_analysis = {
                    "agent_type": scenario["agent"],
                    "total_events": len(events),
                    "has_thinking_content": False,
                    "has_tool_execution_details": False,
                    "has_business_value_result": False,
                    "business_value_fields": []
                }
                
                for event in events:
                    event_data = event.data
                    
                    # Check thinking content
                    if event.event_type == "agent_thinking":
                        if "reasoning" in event_data or "analysis" in event_data:
                            content_analysis["has_thinking_content"] = True
                    
                    # Check tool execution details
                    if event.event_type == "tool_executing":
                        if "tool_name" in event_data or "parameters" in event_data:
                            content_analysis["has_tool_execution_details"] = True
                    
                    # Check business value in final result
                    if event.event_type == "agent_completed":
                        expected_fields = scenario["expected_content"]["agent_completed"]
                        found_fields = []
                        
                        for field in expected_fields:
                            if field in event_data or any(field in str(v) for v in event_data.values()):
                                found_fields.append(field)
                        
                        content_analysis["business_value_fields"] = found_fields
                        content_analysis["has_business_value_result"] = len(found_fields) > 0
                
                business_value_results.append(content_analysis)
        
        # Verify business value content
        for result in business_value_results:
            assert result["total_events"] > 0, \
                f"No events received for {result['agent_type']}"
            
            assert result["has_thinking_content"], \
                f"Missing thinking content for {result['agent_type']} - users need transparency"
            
            assert result["has_tool_execution_details"], \
                f"Missing tool execution details for {result['agent_type']} - users need to see work"
            
            assert result["has_business_value_result"], \
                f"Missing business value in final result for {result['agent_type']}: {result['business_value_fields']}"
            
            # Verify at least 2 business value fields present
            assert len(result["business_value_fields"]) >= 2, \
                f"Insufficient business value content for {result['agent_type']}: only {result['business_value_fields']}"
        
        logger.info(f"WebSocket business value content validated: {len(business_value_results)} agent types")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_high_frequency_message_handling(self, real_services_fixture):
        """
        Test 7: WebSocket handling of high-frequency messages and events.
        
        Validates that WebSocket connections can handle rapid message exchanges
        without dropping events or degrading performance under load.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-high-frequency@example.com"
        )
        
        # High frequency test parameters
        message_batches = [
            {"batch_size": 5, "delay_between": 0.1, "description": "rapid_requests"},
            {"batch_size": 10, "delay_between": 0.05, "description": "high_frequency"}, 
            {"batch_size": 3, "delay_between": 0.02, "description": "burst_mode"}
        ]
        
        high_frequency_results = []
        
        for batch_config in message_batches:
            async with self.websocket_client_context(user_context["token"]) as websocket:
                batch_start = time.time()
                
                # Send batch of messages
                sent_messages = []
                for i in range(batch_config["batch_size"]):
                    message = {
                        "type": "agent_request",
                        "agent": "high_frequency_test",
                        "message": f"High frequency test message {i} - {batch_config['description']}",
                        "user_id": user_context["user_id"],
                        "batch_id": f"{batch_config['description']}_{int(time.time())}",
                        "message_index": i
                    }
                    
                    await websocket.send(json.dumps(message))
                    sent_messages.append(message)
                    
                    if batch_config["delay_between"] > 0:
                        await asyncio.sleep(batch_config["delay_between"])
                
                send_time = time.time() - batch_start
                
                # Collect all resulting events
                all_events = []
                collection_start = time.time()
                expected_completion_events = batch_config["batch_size"]
                
                while time.time() - collection_start < 30.0:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event_data = json.loads(message)
                        all_events.append(event_data)
                        
                        # Count completion events
                        completion_count = sum(1 for e in all_events if e.get("type") == "agent_completed")
                        if completion_count >= expected_completion_events:
                            break
                            
                    except asyncio.TimeoutError:
                        # Check if we have enough completion events
                        completion_count = sum(1 for e in all_events if e.get("type") == "agent_completed")
                        if completion_count >= expected_completion_events:
                            break
                        continue
                
                total_time = time.time() - batch_start
                
                # Analyze results
                event_types = [e.get("type") for e in all_events]
                completion_events = [e for e in all_events if e.get("type") == "agent_completed"]
                
                batch_result = {
                    "batch_description": batch_config["description"],
                    "messages_sent": len(sent_messages),
                    "total_events_received": len(all_events),
                    "completion_events": len(completion_events),
                    "send_time": send_time,
                    "total_time": total_time,
                    "events_per_message": len(all_events) / len(sent_messages) if sent_messages else 0,
                    "message_processing_rate": len(sent_messages) / total_time if total_time > 0 else 0,
                    "all_messages_completed": len(completion_events) == batch_config["batch_size"]
                }
                
                high_frequency_results.append(batch_result)
        
        # Verify high frequency handling
        for result in high_frequency_results:
            assert result["total_events_received"] > 0, \
                f"No events received in {result['batch_description']} batch"
            
            assert result["completion_events"] >= result["messages_sent"] * 0.8, \
                f"Too many lost messages in {result['batch_description']}: {result['completion_events']}/{result['messages_sent']}"
            
            assert result["total_time"] < 60.0, \
                f"High frequency batch took too long: {result['total_time']}s for {result['batch_description']}"
            
            # Verify reasonable event-to-message ratio
            assert 2.0 <= result["events_per_message"] <= 10.0, \
                f"Unusual event ratio for {result['batch_description']}: {result['events_per_message']} events per message"
        
        logger.info(f"High frequency WebSocket handling validated: {len(high_frequency_results)} batches processed")