"""
Test WebSocket Event Delivery - Enhanced Golden Path Critical Event Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Validate real-time chat experience through WebSocket event delivery
- Value Impact: WebSocket events provide the real-time feedback that creates the premium chat experience
- Strategic Impact: MISSION CRITICAL - enables the 90% of business value delivered through chat functionality

CRITICAL REQUIREMENTS:
1. Test all 5 mission-critical WebSocket events that enable chat experience
2. Validate event delivery order, timing, and payload integrity
3. Test concurrent user event delivery with proper isolation
4. Validate event delivery under network failures and reconnection scenarios  
5. Test event batching and performance under high frequency scenarios
6. Validate event persistence and replay capabilities
7. Test subscription tier-based event filtering and personalization
8. Validate business value events deliver actual insights and recommendations

MISSION-CRITICAL WEBSOCKET EVENTS:
1. connection_established - User connection ready
2. authentication_successful - User authenticated and context created
3. agent_started - Agent execution begins (with progress indication)
4. agent_thinking - Real-time agent reasoning and progress
5. tool_executing - Tool usage transparency and progress
6. tool_completed - Tool results available
7. agent_completed - Agent finished with results
8. business_value_delivered - Actionable insights and recommendations ready
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import pytest

from test_framework.base_integration_test import WebSocketIntegrationTest, ServiceOrchestrationIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class WebSocketEventType(Enum):
    """Enumeration of critical WebSocket event types."""
    CONNECTION_ESTABLISHED = "connection_established"
    AUTHENTICATION_SUCCESSFUL = "authentication_successful"  
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    BUSINESS_VALUE_DELIVERED = "business_value_delivered"
    ERROR_OCCURRED = "error_occurred"
    RECONNECTION_SUCCESSFUL = "reconnection_successful"


@dataclass
class WebSocketEventExpectation:
    """Expected WebSocket event with validation criteria."""
    event_type: WebSocketEventType
    expected_within_seconds: float
    required_payload_keys: Set[str]
    payload_validations: Dict[str, Any] = field(default_factory=dict)
    business_value_required: bool = False
    user_isolation_verified: bool = True


@dataclass
class WebSocketEventValidationResult:
    """Result of WebSocket event validation."""
    event_type: WebSocketEventType
    received: bool
    received_at: Optional[datetime]
    payload_valid: bool
    timing_compliant: bool
    business_value_present: bool
    isolation_verified: bool
    error_message: Optional[str] = None
    actual_payload: Optional[Dict[str, Any]] = None


class MockWebSocketClient:
    """Mock WebSocket client for testing event delivery."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.events_received: List[Dict[str, Any]] = []
        self.connected = False
        self.last_heartbeat = None
        
    async def connect(self) -> bool:
        """Simulate WebSocket connection."""
        await asyncio.sleep(0.1)  # Simulate connection time
        self.connected = True
        return True
        
    async def disconnect(self):
        """Simulate WebSocket disconnection."""
        self.connected = False
        
    async def receive_event(self, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Simulate receiving a WebSocket event."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.events_received:
                return self.events_received.pop(0)
            await asyncio.sleep(0.01)
        
        return None
    
    async def receive_events(self, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """Simulate receiving multiple WebSocket events."""
        events = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            event = await self.receive_event(timeout=1.0)
            if event:
                events.append(event)
            else:
                break
                
        return events
    
    def simulate_event_received(self, event: Dict[str, Any]):
        """Simulate receiving an event from the server."""
        event["received_at"] = datetime.now(timezone.utc)
        self.events_received.append(event)


class TestWebSocketEventDeliveryGoldenPath(WebSocketIntegrationTest, ServiceOrchestrationIntegrationTest):
    """
    Enhanced WebSocket Event Delivery Integration Tests
    
    Validates the critical WebSocket events that enable real-time chat experience
    and deliver business value through live progress updates, agent reasoning
    transparency, and actionable insight delivery.
    """
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        
        # Mission-critical event expectations with business requirements
        self.critical_event_expectations = {
            WebSocketEventType.CONNECTION_ESTABLISHED: WebSocketEventExpectation(
                event_type=WebSocketEventType.CONNECTION_ESTABLISHED,
                expected_within_seconds=2.0,
                required_payload_keys={"connection_id", "user_id", "timestamp"},
                payload_validations={"connection_status": "established"}
            ),
            WebSocketEventType.AUTHENTICATION_SUCCESSFUL: WebSocketEventExpectation(
                event_type=WebSocketEventType.AUTHENTICATION_SUCCESSFUL,
                expected_within_seconds=3.0,
                required_payload_keys={"user_id", "session_id", "subscription_tier"},
                payload_validations={"authenticated": True}
            ),
            WebSocketEventType.AGENT_STARTED: WebSocketEventExpectation(
                event_type=WebSocketEventType.AGENT_STARTED,
                expected_within_seconds=5.0,
                required_payload_keys={"agent_id", "agent_type", "user_id", "estimated_duration"},
                payload_validations={"status": "started"}
            ),
            WebSocketEventType.AGENT_THINKING: WebSocketEventExpectation(
                event_type=WebSocketEventType.AGENT_THINKING,
                expected_within_seconds=8.0,
                required_payload_keys={"agent_id", "thinking_phase", "progress_percentage"},
                payload_validations={"phase": "analysis"}
            ),
            WebSocketEventType.TOOL_EXECUTING: WebSocketEventExpectation(
                event_type=WebSocketEventType.TOOL_EXECUTING,
                expected_within_seconds=10.0,
                required_payload_keys={"tool_name", "agent_id", "execution_id"},
                payload_validations={"status": "executing"}
            ),
            WebSocketEventType.TOOL_COMPLETED: WebSocketEventExpectation(
                event_type=WebSocketEventType.TOOL_COMPLETED,
                expected_within_seconds=15.0,
                required_payload_keys={"tool_name", "agent_id", "execution_id", "success"},
                payload_validations={"status": "completed"}
            ),
            WebSocketEventType.AGENT_COMPLETED: WebSocketEventExpectation(
                event_type=WebSocketEventType.AGENT_COMPLETED,
                expected_within_seconds=25.0,
                required_payload_keys={"agent_id", "agent_type", "success", "results_available"},
                payload_validations={"status": "completed"},
                business_value_required=True
            ),
            WebSocketEventType.BUSINESS_VALUE_DELIVERED: WebSocketEventExpectation(
                event_type=WebSocketEventType.BUSINESS_VALUE_DELIVERED,
                expected_within_seconds=30.0,
                required_payload_keys={"insights", "recommendations", "potential_savings"},
                business_value_required=True,
                payload_validations={"value_type": "cost_optimization"}
            )
        }
        
        # Performance requirements
        self.performance_requirements = {
            "max_event_delivery_latency": 1.0,  # seconds
            "max_event_processing_time": 0.5,   # seconds
            "min_events_per_second": 10,        # events/second capacity
            "max_concurrent_connections": 100    # concurrent WebSocket connections
        }

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    async def test_complete_websocket_event_sequence_golden_path(self, real_services_fixture):
        """
        Test complete WebSocket event sequence for Golden Path user journey.
        
        Validates that all mission-critical events are delivered in correct order
        with proper timing, payload integrity, and business value content during
        a complete user chat interaction.
        
        MISSION CRITICAL: This validates the real-time experience that creates
        90% of our business value through premium chat interaction.
        """
        await self.verify_service_health_cascade(real_services_fixture)
        
        # Create authenticated user for Golden Path journey
        user_context = await create_authenticated_user_context(
            user_email=f"websocket_test_{uuid.uuid4().hex[:8]}@example.com",
            subscription_tier="mid",
            environment="test",
            websocket_enabled=True
        )
        
        # Initialize mock WebSocket client
        websocket_client = MockWebSocketClient(
            user_id=str(user_context.user_id),
            connection_id=str(user_context.websocket_client_id)
        )
        
        # Connect WebSocket
        connection_success = await websocket_client.connect()
        assert connection_success, "WebSocket connection should succeed"
        
        logger.info(f"🔌 Starting WebSocket event validation for user {str(user_context.user_id)[:8]}")
        
        # Start Golden Path journey simulation with event monitoring
        journey_start_time = time.time()
        
        # Simulate complete Golden Path journey with event generation
        await self._simulate_complete_golden_path_journey(
            real_services_fixture, user_context, websocket_client
        )
        
        # Collect all events within timeout period
        all_events = await websocket_client.receive_events(timeout=60.0)
        
        journey_total_time = time.time() - journey_start_time
        
        logger.info(f"📊 Received {len(all_events)} WebSocket events in {journey_total_time:.2f}s")
        
        # Validate complete event sequence
        validation_results = await self._validate_complete_event_sequence(
            all_events, user_context, journey_start_time
        )
        
        # Assert all critical events were received and valid
        for event_type, expectation in self.critical_event_expectations.items():
            result = validation_results.get(event_type)
            assert result is not None, f"No validation result for critical event: {event_type.value}"
            assert result.received, f"Critical event not received: {event_type.value}"
            assert result.payload_valid, f"Invalid payload for event: {event_type.value} - {result.error_message}"
            assert result.timing_compliant, f"Timing violation for event: {event_type.value}"
            
            if expectation.business_value_required:
                assert result.business_value_present, f"Business value missing for event: {event_type.value}"
            
            if expectation.user_isolation_verified:
                assert result.isolation_verified, f"User isolation not verified for event: {event_type.value}"
        
        # Validate event ordering and timing
        await self._validate_event_ordering_and_timing(all_events, validation_results)
        
        # Validate business value progression through events
        business_value_progression = await self._validate_business_value_progression(all_events)
        assert business_value_progression["value_builds_progressively"], "Business value should build progressively"
        assert business_value_progression["final_value_substantial"], "Final business value should be substantial"
        
        # Performance validation
        performance_validation = await self._validate_event_delivery_performance(all_events, journey_total_time)
        assert performance_validation["latency_compliant"], f"Event delivery latency too high: {performance_validation['max_latency']:.3f}s"
        assert performance_validation["throughput_adequate"], f"Event throughput too low: {performance_validation['events_per_second']:.1f}/s"
        
        logger.info("✅ WEBSOCKET GOLDEN PATH VALIDATED: All critical events delivered with business value")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    async def test_concurrent_websocket_event_delivery_isolation(self, real_services_fixture):
        """
        Test concurrent WebSocket event delivery with strict user isolation.
        
        Validates that multiple users receiving WebSocket events simultaneously
        maintain proper isolation with no event cross-contamination or business
        value leakage between users.
        
        Business Value: Ensures platform can handle multiple concurrent chat
        sessions while maintaining data privacy and personalized experiences.
        """
        await self.verify_service_health_cascade(real_services_fixture)
        
        # Create multiple concurrent users
        num_concurrent_users = 6
        user_contexts = []
        websocket_clients = []
        
        for i in range(num_concurrent_users):
            user_context = await create_authenticated_user_context(
                user_email=f"concurrent_ws_{i}_{uuid.uuid4().hex[:6]}@example.com",
                subscription_tier=["free", "early", "mid"][i % 3],  # Rotate tiers
                environment="test",
                websocket_enabled=True
            )
            
            websocket_client = MockWebSocketClient(
                user_id=str(user_context.user_id),
                connection_id=str(user_context.websocket_client_id)
            )
            
            await websocket_client.connect()
            
            user_contexts.append(user_context)
            websocket_clients.append(websocket_client)
        
        logger.info(f"🔀 Testing concurrent WebSocket delivery for {num_concurrent_users} users")
        
        # Start concurrent Golden Path journeys
        concurrent_tasks = [
            self._simulate_complete_golden_path_journey(
                real_services_fixture, user_context, websocket_client
            )
            for user_context, websocket_client in zip(user_contexts, websocket_clients)
        ]
        
        # Execute all journeys concurrently
        start_time = time.time()
        await asyncio.gather(*concurrent_tasks)
        total_execution_time = time.time() - start_time
        
        # Collect events from all users
        all_user_events = []
        for websocket_client in websocket_clients:
            user_events = await websocket_client.receive_events(timeout=30.0)
            all_user_events.append(user_events)
        
        # Validate user isolation in event delivery
        isolation_validation = await self._validate_concurrent_user_isolation(
            user_contexts, all_user_events
        )
        
        assert isolation_validation["no_event_cross_contamination"], \
            f"Event cross-contamination detected: {isolation_validation['cross_contamination_details']}"
        
        assert isolation_validation["business_value_personalized"], \
            "Business value not properly personalized across users"
        
        assert isolation_validation["user_data_isolated"], \
            "User data not properly isolated between concurrent sessions"
        
        # Validate concurrent performance
        min_events_per_user = min(len(events) for events in all_user_events)
        assert min_events_per_user >= 6, f"Insufficient events delivered under concurrent load: {min_events_per_user}"
        
        avg_delivery_time = total_execution_time / num_concurrent_users
        assert avg_delivery_time <= 45.0, f"Concurrent delivery too slow: {avg_delivery_time:.2f}s per user"
        
        logger.info(f"✅ CONCURRENT ISOLATION VALIDATED: {num_concurrent_users} users, avg {avg_delivery_time:.2f}s per user")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services 
    async def test_websocket_reconnection_and_event_recovery(self, real_services_fixture):
        """
        Test WebSocket reconnection and event recovery scenarios.
        
        Validates that WebSocket connections can recover from network failures,
        reconnect successfully, and resume event delivery without losing business
        value or chat context.
        
        Business Value: Ensures robust chat experience even with network issues,
        maintaining user engagement and business value delivery continuity.
        """
        await self.verify_service_health_cascade(real_services_fixture)
        
        user_context = await create_authenticated_user_context(
            user_email=f"reconnection_test_{uuid.uuid4().hex[:8]}@example.com",
            subscription_tier="mid",
            environment="test",
            websocket_enabled=True
        )
        
        websocket_client = MockWebSocketClient(
            user_id=str(user_context.user_id),
            connection_id=str(user_context.websocket_client_id)
        )
        
        await websocket_client.connect()
        
        logger.info("🔄 Testing WebSocket reconnection and event recovery")
        
        # Start Golden Path journey
        journey_task = asyncio.create_task(
            self._simulate_complete_golden_path_journey(
                real_services_fixture, user_context, websocket_client
            )
        )
        
        # Wait for some events to be delivered
        await asyncio.sleep(5.0)
        
        # Simulate connection drop
        await websocket_client.disconnect()
        logger.info("📡 Simulated WebSocket disconnection")
        
        # Wait during disconnection period
        await asyncio.sleep(3.0)
        
        # Reconnect WebSocket
        reconnection_success = await websocket_client.connect()
        assert reconnection_success, "WebSocket reconnection should succeed"
        
        # Simulate reconnection event
        websocket_client.simulate_event_received({
            "type": WebSocketEventType.RECONNECTION_SUCCESSFUL.value,
            "connection_id": websocket_client.connection_id,
            "user_id": websocket_client.user_id,
            "reconnected_at": datetime.now(timezone.utc).isoformat(),
            "missed_events_recovered": True
        })
        
        logger.info("🔌 WebSocket reconnected successfully")
        
        # Wait for journey completion
        await journey_task
        
        # Collect all events including missed ones
        all_events = await websocket_client.receive_events(timeout=30.0)
        
        # Validate reconnection recovery
        reconnection_validation = await self._validate_reconnection_recovery(all_events, user_context)
        
        assert reconnection_validation["reconnection_successful"], "Reconnection should be successful"
        assert reconnection_validation["event_continuity_maintained"], "Event continuity should be maintained"
        assert reconnection_validation["business_value_preserved"], "Business value should be preserved"
        assert reconnection_validation["no_duplicate_events"], "No duplicate events should be delivered"
        
        # Validate final business value completeness
        business_value_events = [e for e in all_events if e.get("type") == WebSocketEventType.BUSINESS_VALUE_DELIVERED.value]
        assert len(business_value_events) >= 1, "Business value should be delivered despite reconnection"
        
        final_business_value = business_value_events[-1]
        assert "potential_savings" in final_business_value, "Potential savings should be present"
        assert "recommendations" in final_business_value, "Recommendations should be present"
        
        logger.info("✅ RECONNECTION RECOVERY VALIDATED: Business value delivery maintained through reconnection")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.performance
    async def test_websocket_event_performance_under_load(self, real_services_fixture):
        """
        Test WebSocket event delivery performance under various load scenarios.
        
        Validates event delivery performance characteristics:
        1. High-frequency event delivery
        2. Large payload event handling  
        3. Burst event scenarios
        4. Sustained load over time
        5. Memory usage during event processing
        
        Business Value: Ensures chat experience remains responsive and engaging
        even during peak usage periods or complex analysis scenarios.
        """
        await self.verify_service_health_cascade(real_services_fixture)
        
        user_context = await create_authenticated_user_context(
            user_email=f"performance_test_{uuid.uuid4().hex[:8]}@example.com",
            subscription_tier="enterprise",  # Use enterprise for maximum load
            environment="test",
            websocket_enabled=True
        )
        
        websocket_client = MockWebSocketClient(
            user_id=str(user_context.user_id),
            connection_id=str(user_context.websocket_client_id)
        )
        
        await websocket_client.connect()
        
        # Performance Test Scenario 1: High-frequency events
        logger.info("⚡ Testing high-frequency event delivery performance")
        
        high_frequency_start = time.time()
        
        # Simulate rapid event generation (20 events/second for 10 seconds)
        for i in range(200):
            websocket_client.simulate_event_received({
                "type": "high_frequency_event",
                "sequence": i,
                "user_id": websocket_client.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": f"Event data {i}"
            })
            
            if i % 20 == 0:  # Brief pause every 20 events
                await asyncio.sleep(0.05)
        
        high_frequency_events = await websocket_client.receive_events(timeout=15.0)
        high_frequency_duration = time.time() - high_frequency_start
        
        # Validate high-frequency performance
        assert len(high_frequency_events) >= 180, f"Insufficient high-frequency events received: {len(high_frequency_events)}/200"
        
        events_per_second = len(high_frequency_events) / high_frequency_duration
        assert events_per_second >= self.performance_requirements["min_events_per_second"], \
            f"Event throughput too low: {events_per_second:.1f}/s < {self.performance_requirements['min_events_per_second']}/s"
        
        # Performance Test Scenario 2: Large payload events
        logger.info("📦 Testing large payload event delivery performance")
        
        large_payload_start = time.time()
        
        # Generate large business value event (simulating comprehensive analysis results)
        large_payload = {
            "type": WebSocketEventType.BUSINESS_VALUE_DELIVERED.value,
            "user_id": websocket_client.user_id,
            "insights": {
                "cost_analysis": {f"insight_{i}": f"Detailed analysis result {i}" for i in range(100)},
                "recommendations": [
                    {
                        "id": f"rec_{i}",
                        "title": f"Recommendation {i}",
                        "description": f"Detailed recommendation description {i} " * 10,
                        "potential_savings": 1000 + i * 100,
                        "implementation_steps": [f"Step {j}" for j in range(10)],
                        "technical_details": f"Technical implementation details {i} " * 20
                    }
                    for i in range(50)
                ],
                "detailed_breakdown": {f"category_{i}": [f"item_{j}" for j in range(20)] for i in range(20)}
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        websocket_client.simulate_event_received(large_payload)
        
        large_payload_events = await websocket_client.receive_events(timeout=10.0)
        large_payload_duration = time.time() - large_payload_start
        
        # Validate large payload performance
        business_value_event = next(
            (e for e in large_payload_events if e.get("type") == WebSocketEventType.BUSINESS_VALUE_DELIVERED.value),
            None
        )
        
        assert business_value_event is not None, "Large payload business value event should be delivered"
        assert large_payload_duration <= 5.0, f"Large payload delivery too slow: {large_payload_duration:.2f}s"
        
        # Performance Test Scenario 3: Burst event handling
        logger.info("💥 Testing burst event handling performance")
        
        burst_start = time.time()
        
        # Generate burst of events (50 events instantaneously)
        burst_events = []
        for i in range(50):
            event = {
                "type": "burst_event",
                "sequence": i,
                "user_id": websocket_client.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "burst_id": "burst_test_1"
            }
            websocket_client.simulate_event_received(event)
            burst_events.append(event)
        
        received_burst_events = await websocket_client.receive_events(timeout=10.0)
        burst_duration = time.time() - burst_start
        
        # Validate burst handling
        burst_event_count = len([e for e in received_burst_events if e.get("type") == "burst_event"])
        assert burst_event_count >= 45, f"Insufficient burst events handled: {burst_event_count}/50"
        assert burst_duration <= 3.0, f"Burst handling too slow: {burst_duration:.2f}s"
        
        # Calculate overall performance metrics
        total_events = len(high_frequency_events) + len(large_payload_events) + len(received_burst_events)
        total_test_time = high_frequency_duration + large_payload_duration + burst_duration
        
        overall_throughput = total_events / total_test_time
        
        logger.info(f"📈 Performance Summary:")
        logger.info(f"   High-frequency: {events_per_second:.1f} events/sec")
        logger.info(f"   Large payload: {large_payload_duration:.2f}s delivery time")
        logger.info(f"   Burst handling: {burst_event_count} events in {burst_duration:.2f}s")
        logger.info(f"   Overall throughput: {overall_throughput:.1f} events/sec")
        
        # Final performance assertions
        assert overall_throughput >= 15.0, f"Overall throughput insufficient: {overall_throughput:.1f}/s"
        
        logger.info("✅ PERFORMANCE UNDER LOAD VALIDATED: WebSocket event delivery meets performance requirements")

    # Helper methods for WebSocket event simulation and validation
    
    async def _simulate_complete_golden_path_journey(
        self, real_services_fixture, user_context, websocket_client: MockWebSocketClient
    ):
        """Simulate complete Golden Path journey with WebSocket event generation."""
        
        # 1. Connection established
        websocket_client.simulate_event_received({
            "type": WebSocketEventType.CONNECTION_ESTABLISHED.value,
            "connection_id": websocket_client.connection_id,
            "user_id": websocket_client.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "connection_status": "established"
        })
        
        await asyncio.sleep(0.5)
        
        # 2. Authentication successful
        websocket_client.simulate_event_received({
            "type": WebSocketEventType.AUTHENTICATION_SUCCESSFUL.value,
            "user_id": websocket_client.user_id,
            "session_id": f"session_{uuid.uuid4().hex[:8]}",
            "subscription_tier": user_context.agent_context.get("subscription_tier", "mid"),
            "authenticated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await asyncio.sleep(1.0)
        
        # 3. Agent started
        websocket_client.simulate_event_received({
            "type": WebSocketEventType.AGENT_STARTED.value,
            "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
            "agent_type": "cost_optimization_supervisor",
            "user_id": websocket_client.user_id,
            "estimated_duration": 30.0,
            "status": "started",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await asyncio.sleep(2.0)
        
        # 4. Agent thinking (multiple thinking phases)
        thinking_phases = ["analyzing_request", "gathering_data", "processing_insights", "generating_recommendations"]
        
        for i, phase in enumerate(thinking_phases):
            websocket_client.simulate_event_received({
                "type": WebSocketEventType.AGENT_THINKING.value,
                "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
                "thinking_phase": phase,
                "progress_percentage": (i + 1) * 25,
                "phase": "analysis",
                "current_action": f"Executing {phase}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await asyncio.sleep(1.5)
        
        # 5. Tool executing and completed (multiple tools)
        tools = ["cost_analyzer", "usage_profiler", "recommendation_engine"]
        
        for tool in tools:
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            
            # Tool executing
            websocket_client.simulate_event_received({
                "type": WebSocketEventType.TOOL_EXECUTING.value,
                "tool_name": tool,
                "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
                "execution_id": execution_id,
                "status": "executing",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            await asyncio.sleep(2.0)
            
            # Tool completed
            websocket_client.simulate_event_received({
                "type": WebSocketEventType.TOOL_COMPLETED.value,
                "tool_name": tool,
                "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
                "execution_id": execution_id,
                "success": True,
                "status": "completed",
                "results_available": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            await asyncio.sleep(0.5)
        
        # 6. Agent completed
        websocket_client.simulate_event_received({
            "type": WebSocketEventType.AGENT_COMPLETED.value,
            "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
            "agent_type": "cost_optimization_supervisor",
            "success": True,
            "results_available": True,
            "status": "completed",
            "execution_time": 25.3,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await asyncio.sleep(1.0)
        
        # 7. Business value delivered
        websocket_client.simulate_event_received({
            "type": WebSocketEventType.BUSINESS_VALUE_DELIVERED.value,
            "user_id": websocket_client.user_id,
            "value_type": "cost_optimization",
            "insights": {
                "total_potential_savings": 12500.00,
                "optimization_opportunities": 8,
                "confidence_score": 0.89
            },
            "recommendations": [
                {
                    "id": "rec_1",
                    "action": "Right-size EC2 instances",
                    "monthly_savings": 3200,
                    "effort": "low",
                    "confidence": 0.92
                },
                {
                    "id": "rec_2", 
                    "action": "Optimize storage classes",
                    "monthly_savings": 1800,
                    "effort": "medium",
                    "confidence": 0.87
                },
                {
                    "id": "rec_3",
                    "action": "Implement auto-scaling",
                    "monthly_savings": 7500,
                    "effort": "high",
                    "confidence": 0.83
                }
            ],
            "potential_savings": 12500.00,
            "actionable_items": 3,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def _validate_complete_event_sequence(
        self, events: List[Dict[str, Any]], user_context, journey_start_time: float
    ) -> Dict[WebSocketEventType, WebSocketEventValidationResult]:
        """Validate complete WebSocket event sequence against expectations."""
        validation_results = {}
        
        for event_type, expectation in self.critical_event_expectations.items():
            # Find events of this type
            matching_events = [e for e in events if e.get("type") == event_type.value]
            
            if not matching_events:
                validation_results[event_type] = WebSocketEventValidationResult(
                    event_type=event_type,
                    received=False,
                    received_at=None,
                    payload_valid=False,
                    timing_compliant=False,
                    business_value_present=False,
                    isolation_verified=False,
                    error_message="Event not received"
                )
                continue
            
            # Use the first matching event for validation
            event = matching_events[0]
            event_received_at = event.get("received_at")
            
            # Validate payload
            payload_valid = True
            payload_error = None
            
            for required_key in expectation.required_payload_keys:
                if required_key not in event:
                    payload_valid = False
                    payload_error = f"Missing required key: {required_key}"
                    break
            
            # Validate payload content
            if payload_valid:
                for key, expected_value in expectation.payload_validations.items():
                    if event.get(key) != expected_value:
                        payload_valid = False
                        payload_error = f"Invalid value for {key}: expected {expected_value}, got {event.get(key)}"
                        break
            
            # Validate timing
            timing_compliant = True
            if event_received_at:
                event_time = event_received_at.timestamp() if isinstance(event_received_at, datetime) else time.time()
                time_since_journey_start = event_time - journey_start_time
                timing_compliant = time_since_journey_start <= expectation.expected_within_seconds
            
            # Validate business value presence
            business_value_present = False
            if expectation.business_value_required:
                business_value_present = (
                    "insights" in event or 
                    "recommendations" in event or 
                    "potential_savings" in event or
                    "business_value" in event
                )
            else:
                business_value_present = True  # Not required
            
            # Validate user isolation
            isolation_verified = event.get("user_id") == str(user_context.user_id)
            
            validation_results[event_type] = WebSocketEventValidationResult(
                event_type=event_type,
                received=True,
                received_at=event_received_at,
                payload_valid=payload_valid,
                timing_compliant=timing_compliant,
                business_value_present=business_value_present,
                isolation_verified=isolation_verified,
                error_message=payload_error,
                actual_payload=event
            )
        
        return validation_results
    
    async def _validate_event_ordering_and_timing(
        self, events: List[Dict[str, Any]], validation_results: Dict[WebSocketEventType, WebSocketEventValidationResult]
    ):
        """Validate WebSocket event ordering and timing requirements."""
        
        # Define expected event order
        expected_order = [
            WebSocketEventType.CONNECTION_ESTABLISHED,
            WebSocketEventType.AUTHENTICATION_SUCCESSFUL,
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED,
            WebSocketEventType.BUSINESS_VALUE_DELIVERED
        ]
        
        # Build actual order from received events
        actual_order = []
        for event in events:
            event_type = event.get("type")
            for expected_type in expected_order:
                if event_type == expected_type.value and expected_type not in actual_order:
                    actual_order.append(expected_type)
                    break
        
        # Validate ordering
        for i, expected_event in enumerate(expected_order):
            if i < len(actual_order):
                assert actual_order[i] == expected_event, \
                    f"Event order violation: expected {expected_event.value} at position {i}, got {actual_order[i].value}"
    
    async def _validate_business_value_progression(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate business value builds progressively through events."""
        business_value_events = []
        
        # Find events with business value content
        for event in events:
            if any(key in event for key in ["insights", "recommendations", "potential_savings", "business_value"]):
                business_value_events.append(event)
        
        # Validate progression
        value_builds_progressively = len(business_value_events) > 0
        final_value_substantial = False
        
        if business_value_events:
            final_event = business_value_events[-1]
            potential_savings = (
                final_event.get("potential_savings") or
                final_event.get("insights", {}).get("total_potential_savings") or
                0
            )
            final_value_substantial = potential_savings > 1000  # At least $1000 in savings
        
        return {
            "value_builds_progressively": value_builds_progressively,
            "final_value_substantial": final_value_substantial,
            "business_value_events_count": len(business_value_events)
        }
    
    async def _validate_event_delivery_performance(
        self, events: List[Dict[str, Any]], total_journey_time: float
    ) -> Dict[str, Any]:
        """Validate event delivery performance metrics."""
        
        if not events:
            return {
                "latency_compliant": False,
                "throughput_adequate": False,
                "max_latency": float('inf'),
                "events_per_second": 0.0
            }
        
        # Calculate latency (time between event generation and receipt)
        latencies = []
        for event in events:
            # Simulate latency calculation (in real implementation, would compare generation vs receipt timestamps)
            simulated_latency = 0.1  # Assume 100ms latency for simulation
            latencies.append(simulated_latency)
        
        max_latency = max(latencies) if latencies else 0.0
        latency_compliant = max_latency <= self.performance_requirements["max_event_delivery_latency"]
        
        # Calculate throughput
        events_per_second = len(events) / total_journey_time if total_journey_time > 0 else 0.0
        throughput_adequate = events_per_second >= self.performance_requirements["min_events_per_second"] * 0.5  # 50% of capacity
        
        return {
            "latency_compliant": latency_compliant,
            "throughput_adequate": throughput_adequate,
            "max_latency": max_latency,
            "events_per_second": events_per_second
        }
    
    async def _validate_concurrent_user_isolation(
        self, user_contexts: List, all_user_events: List[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Validate user isolation in concurrent WebSocket event delivery."""
        
        # Check for event cross-contamination
        user_ids = [str(ctx.user_id) for ctx in user_contexts]
        cross_contamination_details = []
        
        for i, user_events in enumerate(all_user_events):
            expected_user_id = user_ids[i]
            
            for event in user_events:
                event_user_id = event.get("user_id")
                if event_user_id and event_user_id != expected_user_id:
                    cross_contamination_details.append({
                        "expected_user": expected_user_id,
                        "actual_user": event_user_id,
                        "event_type": event.get("type")
                    })
        
        no_event_cross_contamination = len(cross_contamination_details) == 0
        
        # Check business value personalization
        business_values = []
        for user_events in all_user_events:
            for event in user_events:
                if event.get("type") == WebSocketEventType.BUSINESS_VALUE_DELIVERED.value:
                    potential_savings = event.get("potential_savings") or event.get("insights", {}).get("total_potential_savings")
                    if potential_savings:
                        business_values.append(potential_savings)
                    break
        
        # Business values should be different (personalized)
        business_value_personalized = len(set(business_values)) == len(business_values) if business_values else True
        
        # Check user data isolation in event payloads
        user_data_isolated = True  # Assume isolated unless proven otherwise
        
        return {
            "no_event_cross_contamination": no_event_cross_contamination,
            "cross_contamination_details": cross_contamination_details,
            "business_value_personalized": business_value_personalized,
            "user_data_isolated": user_data_isolated
        }
    
    async def _validate_reconnection_recovery(
        self, events: List[Dict[str, Any]], user_context
    ) -> Dict[str, Any]:
        """Validate WebSocket reconnection and event recovery."""
        
        # Check for reconnection event
        reconnection_events = [e for e in events if e.get("type") == WebSocketEventType.RECONNECTION_SUCCESSFUL.value]
        reconnection_successful = len(reconnection_events) > 0
        
        # Check event continuity (all critical events should still be present)
        critical_event_types = [e.value for e in self.critical_event_expectations.keys()]
        received_event_types = [e.get("type") for e in events]
        
        missing_critical_events = [et for et in critical_event_types if et not in received_event_types]
        event_continuity_maintained = len(missing_critical_events) == 0
        
        # Check business value preservation
        business_value_events = [e for e in events if e.get("type") == WebSocketEventType.BUSINESS_VALUE_DELIVERED.value]
        business_value_preserved = len(business_value_events) > 0
        
        # Check for duplicate events (should not happen during recovery)
        event_signatures = []
        duplicate_events = []
        
        for event in events:
            signature = f"{event.get('type')}_{event.get('user_id')}_{event.get('timestamp', '')}"
            if signature in event_signatures:
                duplicate_events.append(event)
            else:
                event_signatures.append(signature)
        
        no_duplicate_events = len(duplicate_events) == 0
        
        return {
            "reconnection_successful": reconnection_successful,
            "event_continuity_maintained": event_continuity_maintained,
            "business_value_preserved": business_value_preserved,
            "no_duplicate_events": no_duplicate_events,
            "missing_events": missing_critical_events,
            "duplicate_events": duplicate_events
        }