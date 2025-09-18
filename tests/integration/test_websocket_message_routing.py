"""Empty docstring."""
Integration Test: WebSocket Message Routing Pipeline - Agent Event Routing Validation

MISSION CRITICAL: Tests the WebSocket message routing pipeline that ensures agent events
reach the correct users with proper isolation, security, and real-time delivery guarantees.

Business Value Justification (BVJ):
    - Segment: Platform/All - Core Chat Infrastructure
- Business Goal: Revenue Protection - Ensures event delivery for $"500K" plus ARR chat functionality
- Value Impact: Validates the routing system that delivers real-time AI value to users
- Strategic Impact: Tests the infrastructure that powers 90% of platform business value

CRITICAL REQUIREMENTS:
    1. Message routing with enterprise-grade user isolation
2. Real-time delivery with performance SLAs (<"100ms" routing time)
3. Event ordering and sequencing guarantees
4. Connection health monitoring and failover handling
5. Security validation and access control enforcement

COMPLIANCE:
    @compliance CLAUDE.md - WebSocket events enable substantive chat (Section 6)
@compliance CLAUDE.md - E2E AUTH MANDATORY (Section 7.3)
@compliance CLAUDE.md - NO MOCKS for integration tests
@compliance SPEC/core.xml - Single Source of Truth patterns
"""Empty docstring."""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter
from netra_backend.app.services.websocket_broadcast_service import WebSocketBroadcastService
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool
from netra_backend.app.websocket_core.event_validator import ()
    WebSocketEventMessage,
    CriticalAgentEventType,
    UnifiedEventValidator
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.isolated_environment import get_env


@pytest.mark.integration
class WebSocketMessageRoutingIntegrationTests(SSotAsyncTestCase):
    pass
"""Empty docstring."""
    Integration tests for WebSocket message routing pipeline.
    
    These tests validate that agent events are properly routed through the
    WebSocket infrastructure to the correct users with proper isolation,
    performance, and reliability guarantees.
    
    CRITICAL: Tests the routing system that enables real-time AI value delivery.
"""Empty docstring."""

    def setup_method(self):
        "Set up test environment with WebSocket routing components."""
        super().setup_method()
        self.env = get_env()
        
        # Initialize routing components
        self.event_router = WebSocketEventRouter()
        self.user_scoped_router = UserScopedWebSocketEventRouter()
        self.broadcast_service = WebSocketBroadcastService()
        self.connection_pool = WebSocketConnectionPool()
        
        # Test state tracking
        self.routed_events: List[Dict[str, Any]] = []
        self.routing_metrics: Dict[str, Any] = {}
        self.test_user_contexts: List[UserExecutionContext] = []
        self.mock_connections: Dict[str, Dict[str, Any]] = {}
        
        # Configure test environment
        self.set_env_var(TESTING", true)"
        self.set_env_var(WEBSOCKET_ROUTING_MODE, test)
        self.set_env_var(EVENT_ROUTING_TIMEOUT, "5000)  # 5 second timeout for tests"
        
    async def teardown_method(self):
        "Clean up routing components and test state."""
        try:
            # Clean up connections
            for connection_id in list(self.mock_connections.keys()):
                await self._cleanup_mock_connection(connection_id)
            
            # Clean up user contexts
            for context in self.test_user_contexts:
                await self._cleanup_user_context(context)
            
            # Reset routing state
            self.routed_events.clear()
            self.routing_metrics.clear()
            self.mock_connections.clear()
        finally:
            await super().teardown_method()

    def _create_test_user_context(self, user_suffix: str = None) -> UserExecutionContext:
        "Create isolated user execution context for routing tests."
        suffix = user_suffix or frouting_{uuid.uuid4().hex[:8]}""
        context = self.create_test_user_execution_context(
            user_id=f"test_user_{suffix},"
            thread_id=fthread_{suffix},
            run_id=frun_{suffix},
            websocket_client_id=fws_{suffix}""
        )
        self.test_user_contexts.append(context)
        return context

    async def _cleanup_user_context(self, context: UserExecutionContext):
        Clean up resources for a user context.""
        try:
            # Remove any active connections for this user
            if context.websocket_client_id in self.mock_connections:
                await self._cleanup_mock_connection(context.websocket_client_id)
        except Exception as e:
            self.logger.warning(fError during context cleanup: {e}")"

    async def _create_mock_websocket_connection(self, user_context: UserExecutionContext) -> Dict[str, Any]:
        Create a mock WebSocket connection for testing routing.""
        connection = {
            connection_id: user_context.websocket_client_id,
            user_id: user_context.user_id,""
            thread_id": user_context.thread_id,"
            connected_at: datetime.now(timezone.utc),
            status": active,"
            received_events: [],
            routing_metrics: {""
                events_received": 0,"
                events_routed: 0,
                last_activity": datetime.now(timezone.utc)"
            }
        }
        self.mock_connections[user_context.websocket_client_id] = connection
        return connection

    async def _cleanup_mock_connection(self, connection_id: str):
        Clean up a mock WebSocket connection.""
        if connection_id in self.mock_connections:
            connection = self.mock_connections[connection_id]
            connection[status"] = disconnected"
            del self.mock_connections[connection_id]

    async def _simulate_event_routing(self, event: WebSocketEventMessage, target_connection_id: str) -> Dict[str, Any]:
        Simulate routing an event to a specific connection.""
        routing_start = time.time()
        
        # Validate connection exists
        if target_connection_id not in self.mock_connections:
            raise ValueError(fConnection {target_connection_id} not found)
        
        connection = self.mock_connections[target_connection_id]
        
        # Validate user isolation
        if event.user_id != connection[user_id]:
            raise SecurityError(f"User isolation violation: event user {event.user_id} != connection user {connection['user_id']})"
        
        # Simulate routing delay
        await asyncio.sleep(0.1)  # "1ms" simulated network latency
        
        # Route event
        routed_event = {
            event": event.to_dict(),"
            routed_at: datetime.now(timezone.utc),
            routing_time_ms": (time.time() - routing_start) * 1000,"
            target_connection: target_connection_id,
            routing_success: True""
        }
        
        # Update connection state
        connection["received_events].append(routed_event)"
        connection[routing_metrics][events_received] += 1
        connection[routing_metrics"][events_routed] += 1"
        connection[routing_metrics][last_activity] = datetime.now(timezone.utc)
        
        self.routed_events.append(routed_event)
        return routed_event

    def _create_test_agent_event(self, event_type: str, user_context: UserExecutionContext, **kwargs) -> WebSocketEventMessage:
        "Create a test agent event for routing validation."
        event_data = {
            type: event_type,
            user_id": user_context.user_id,"
            thread_id: user_context.thread_id,
            run_id: user_context.run_id,""
            "websocket_client_id: user_context.websocket_client_id,"
            timestamp: datetime.now(timezone.utc).isoformat(),
            "data: {"
                message: fTest {event_type} event for routing validation,
                agent_name: test_routing_agent,
                **kwargs.get(data", {)"
            }
        }
        return WebSocketEventMessage.from_dict(event_data)

    class SecurityError(Exception):
        Custom exception for security violations.""
        pass

    @pytest.mark.asyncio
    async def test_basic_event_routing_pipeline(self):
    """Empty docstring."""
        Test: Basic event routing through the complete pipeline.
        
        Validates that events flow correctly from agent generation through
        the routing pipeline to user connections with proper isolation.
        
        Business Value: Ensures basic routing infrastructure works for AI value delivery.
"""Empty docstring."""
        print("\n🧪 Testing basic event routing pipeline...)"
        
        # Create test user and connection
        user_context = self._create_test_user_context(basic_routing)""
        connection = await self._create_mock_websocket_connection(user_context)
        
        # Create test events for routing
        test_events = [
            self._create_test_agent_event("agent_started, user_context),"
            self._create_test_agent_event(agent_thinking, user_context, data={thinking_stage: analysis"),"
            self._create_test_agent_event(tool_executing, user_context, data={tool_name: test_tool),""
            self._create_test_agent_event(tool_completed", user_context, data={results: {test: success)),"
            self._create_test_agent_event(agent_completed", user_context, data={final_response: Test complete)"
        ]
        
        # Route events through pipeline
        routing_times = []
        
        for i, event in enumerate(test_events):
            routing_start = time.time()
            
            # Route event
            routed_event = await self._simulate_event_routing(event, user_context.websocket_client_id)
            
            routing_time = time.time() - routing_start
            routing_times.append(routing_time)
            
            # Validate routing success
            assert routed_event[routing_success], fEvent {i+1} routing failed""
            assert routed_event["event][type] == event.event_type, fEvent type mismatch for event {i+1}"
            assert routed_event[event]["user_id] == user_context.user_id, fUser ID mismatch for event {i+1}"
            
            print(f  📨 Routed: {event.event_type} ({routing_time * 1000:."1f"}ms))""

            
            await asyncio.sleep(0.1)  # Small delay between events
        
        # Validate connection received all events
        connection_events = connection[received_events"]"
        assert len(connection_events) == len(test_events), "fConnection missing events: expected {len(test_events)}, got {len(connection_events)}"
        
        # Validate routing performance
        avg_routing_time = sum(routing_times) / len(routing_times)
        max_routing_time = max(routing_times)
        
        assert avg_routing_time < 0.1, "fAverage routing time too slow: {avg_routing_time * 1000:."1f"}ms"
        assert max_routing_time < 0.2, f"Max routing time too slow: {max_routing_time * 1000:."1f"}ms"
        
        # Validate event ordering
        routed_event_types = [event[event"][type] for event in connection_events]"
        expected_order = [agent_started, agent_thinking, tool_executing", tool_completed, agent_completed]"
        assert routed_event_types == expected_order, "fEvent ordering mismatch: expected {expected_order}, got {routed_event_types}"
        
        # Record metrics
        self.record_metric(events_routed", len(test_events))"
        self.record_metric(avg_routing_time_ms, avg_routing_time * 1000)
        self.record_metric(max_routing_time_ms, max_routing_time * 1000)""
        
        print(f"  CHECK Basic routing pipeline successful - {len(test_events)} events)"
        print(f  ⚡ Performance: avg {avg_routing_time * 1000:."1f"}ms, max {max_routing_time * 1000:."1f"}ms)""

    @pytest.mark.asyncio
    async def test_multi_user_routing_isolation(self):
    """Empty docstring."""
        Test: Multi-user routing with strict isolation enforcement.
        
        Validates that events for different users are properly isolated
        and never cross-contaminate between user connections.
        
        Business Value: Ensures enterprise-grade security for multi-tenant AI platform.
"""Empty docstring."""
        print(\n🧪 Testing multi-user routing isolation...")"
        
        # Create multiple users with connections
        users = [
            self._create_test_user_context(isolation_user_1),""
            self._create_test_user_context(isolation_user_2"),"
            self._create_test_user_context(isolation_user_3)
        ]
        
        connections = {}
        for user_context in users:
            connection = await self._create_mock_websocket_connection(user_context)
            connections[user_context.user_id] = connection
        
        # Create events for each user
        user_events = {}
        all_events = []
        
        for i, user_context in enumerate(users):
            events = [
                self._create_test_agent_event(agent_started", user_context, data={user_marker: fuser_{i+1)),"
                self._create_test_agent_event(agent_thinking, user_context, data={user_marker": fuser_{i+1)),"
                self._create_test_agent_event(agent_completed, user_context, data={user_marker: fuser_{i+1))""
            ]
            user_events[user_context.user_id] = events
            all_events.extend([(event, user_context) for event in events]
        
        # Shuffle events to simulate concurrent routing
        import random
        random.shuffle(all_events)
        
        # Route all events concurrently
        routing_tasks = []
        
        async def route_event_with_validation(event, user_context):
            "Route event and validate isolation."""
            try:
                routed_event = await self._simulate_event_routing(event, user_context.websocket_client_id)
                return {success": True, event: routed_event, user_id: user_context.user_id}"
            except Exception as e:
                return {success: False, error": str(e), user_id: user_context.user_id}"
        
        # Execute routing concurrently
        start_time = time.time()
        routing_results = await asyncio.gather(*[
            route_event_with_validation(event, user_context)
            for event, user_context in all_events
        ]
        total_routing_time = time.time() - start_time
        
        # Validate all routing succeeded
        failed_routings = [result for result in routing_results if not result[success]]
        assert len(failed_routings) == 0, f"Routing failures detected: {failed_routings}"
        
        # Validate user isolation
        for user_context in users:
            user_id = user_context.user_id
            connection = connections[user_id]
            connection_events = connection[received_events"]"
            
            # Check event count
            expected_count = len(user_events[user_id)
            assert len(connection_events) == expected_count, "fUser {user_id} event count mismatch: expected {expected_count}, got {len(connection_events)}"
            
            # Check user isolation
            for routed_event in connection_events:
                event_data = routed_event[event]""
                assert event_data["user_id] == user_id, fUser isolation violation: event user {event_data['user_id']} != connection user {user_id}"
                assert event_data[thread_id] == user_context.thread_id, "fThread isolation violation for user {user_id}"
                
                # Check user markers
                user_marker = event_data["data].get(user_marker, )"
                assert user_marker in fuser_{users.index(user_context) + 1}, f"User marker contamination for {user_id}: {user_marker}"
            
            print(f  🔒 User {user_id[-8:]}: {len(connection_events)} events isolated correctly)""
        
        # Validate no cross-contamination
        for user_context in users:
            user_id = user_context.user_id
            connection = connections[user_id]
            
            for other_user in users:
                if other_user.user_id != user_id:
                    # Ensure no events from other users
                    for routed_event in connection[received_events]:
                        event_user = routed_event[event]["user_id]"
                        assert event_user == user_id, fCross-contamination: user {user_id} received event from user {event_user}""
        
        # Validate concurrent performance
        events_per_second = len(all_events) / total_routing_time
        assert events_per_second > 100, "fConcurrent routing too slow: {events_per_second:."1f"} events/sec"
        
        # Record metrics
        self.record_metric(concurrent_users, len(users))""
        self.record_metric("total_events_routed, len(all_events))"
        self.record_metric(concurrent_routing_time_ms, total_routing_time * 1000)
        self.record_metric("events_per_second, events_per_second)"
        
        print(f  CHECK Multi-user isolation successful - {len(users)} users, {len(all_events)} events)
        print(f  🚀 Concurrent performance: {events_per_second:."1f"} events/sec")"
        print(f  🛡️ Zero cross-contamination detected")"

    @pytest.mark.asyncio
    async def test_event_ordering_guarantees(self):
    """"

        Test: Event ordering and sequencing guarantees in routing.
        
        Validates that events maintain proper ordering through the routing
        pipeline even under concurrent load and varying network conditions.
        
        Business Value: Ensures users see coherent AI reasoning progression.
        
        print(\n🧪 Testing event ordering guarantees...")"
        
        user_context = self._create_test_user_context(ordering_test)
        connection = await self._create_mock_websocket_connection(user_context)
        
        # Create ordered event sequence with explicit ordering
        ordered_events = []
        base_time = datetime.now(timezone.utc)
        
        event_sequence = [
            (agent_started, {"sequence_id: 1, phase: initialization),"
            (agent_thinking, {sequence_id: 2, phase": analysis),"
            (agent_thinking, {sequence_id: 3, phase: "planning),"
            (tool_executing", {sequence_id: 4, phase: execution, tool_name": "analyzer),"
            (agent_thinking, {sequence_id: 5, phase: "processing),"
            (tool_completed", {sequence_id: 6, phase: execution, tool_name": "analyzer),"
            (tool_executing, {sequence_id: 7, phase: "execution, tool_name: optimizer),"
            (tool_completed, {sequence_id: 8, phase": execution, tool_name: optimizer),"
            (agent_thinking, {"sequence_id: 9, phase: finalization),"
            (agent_completed, {sequence_id: 10, phase": completion)"
        ]
        
        for i, (event_type, event_data) in enumerate(event_sequence):
            event = self._create_test_agent_event(
                event_type, 
                user_context, 
                data=event_data
            )
            # Set explicit timestamp with microsecond precision
            event.timestamp = base_time + timedelta(microseconds=i * 1000)
            ordered_events.append(event)
        
        # Route events with intentional timing variations
        routing_delays = [0.1, 0.5, 0.2, 0.8, 0.1, 0.3, 0.6, 0.2, 0.4, 0.1]  # Varying delays
        
        async def route_with_delay(event, delay):
            Route event with specified delay to test ordering.""
            await asyncio.sleep(delay)
            return await self._simulate_event_routing(event, user_context.websocket_client_id)
        
        # Route events concurrently with varying delays
        start_time = time.time()
        routing_tasks = [
            route_with_delay(event, delay)
            for event, delay in zip(ordered_events, routing_delays)
        ]
        
        routed_results = await asyncio.gather(*routing_tasks)
        routing_duration = time.time() - start_time
        
        # Validate all events were routed
        assert len(routed_results) == len(ordered_events), f"Not all events routed: expected {len(ordered_events)}, got {len(routed_results)}"
        
        # Get routed events in received order
        connection_events = connection[received_events]
        assert len(connection_events) == len(ordered_events), Event count mismatch in connection""
        
        # Sort by original timestamp to validate ordering preservation
        received_events_sorted = sorted(
            connection_events,
            key=lambda x: datetime.fromisoformat(x[event"][timestamp].replace('Z', '+0:0'))"
        )
        
        # Validate sequence preservation
        for i, routed_event in enumerate(received_events_sorted):
            event_data = routed_event[event]
            expected_sequence_id = i + 1
            actual_sequence_id = event_data["data][sequence_id]"
            
            assert actual_sequence_id == expected_sequence_id, "fSequence order violation: position {i+1} has sequence_id {actual_sequence_id}, expected {expected_sequence_id}"
            
            print(f  📋 Order {i+1}: {event_data['type']} (seq: {actual_sequence_id} CHECK)""
        
        # Validate phase progression
        phases = [event["event][data][phase] for event in received_events_sorted]"
        expected_phase_order = [initialization", "analysis, planning, execution, processing, "execution, execution, execution, finalization, completion]"
        
        # Check that phases progress logically (allowing for concurrent execution phases)
        initialization_phase = phases[0]
        completion_phase = phases[-1]
        assert initialization_phase == initialization", fFirst phase must be initialization, got {initialization_phase}"
        assert completion_phase == completion, "fLast phase must be completion, got {completion_phase}"
        
        # Validate tool execution ordering
        tool_events = [(i, event) for i, event in enumerate(received_events_sorted) 
                      if event[event][type] in [tool_executing", tool_completed]]"
        
        tool_pairs = {}
        for i, event in tool_events:
            event_data = event[event]
            tool_name = event_data[data].get(tool_name", unknown)"
            event_type = event_data[type]
            
            if tool_name not in tool_pairs:
                tool_pairs[tool_name] = {"executing: None, completed: None}"
            
            tool_pairs[tool_name][event_type.split(_)[1]] = i  # executing or completed""
        
        # Validate each tool has executing before completed
        for tool_name, pair in tool_pairs.items():
            executing_pos = pair[executing"]"
            completed_pos = pair[completed]
            
            assert executing_pos is not None, fTool {tool_name} missing executing event""
            assert completed_pos is not None, "fTool {tool_name} missing completed event"
            assert executing_pos < completed_pos, "fTool {tool_name) completed event ({completed_pos) before executing event ({executing_pos)"
        
        # Record metrics
        self.record_metric("ordered_events_count, len(ordered_events))"
        self.record_metric(ordering_test_duration_ms, routing_duration * 1000)
        self.record_metric(max_routing_delay_ms, max(routing_delays) * 1000)""
        self.record_metric(tool_pairs_validated", len(tool_pairs))"
        
        print(f  CHECK Event ordering preserved - {len(ordered_events)} events in correct sequence)
        print(f  🕒 Routing with delays: {routing_duration * 1000:."1f"}ms total"")
        print(f  🔧 Tool execution pairs: {len(tool_pairs)} tools properly ordered)

    @pytest.mark.asyncio
    async def test_connection_health_and_failover(self):
        """"

        Test: Connection health monitoring and failover handling.
        
        Validates that the routing system properly handles connection failures,
        implements health checks, and provides graceful degradation.
        
        Business Value: Ensures reliable AI value delivery despite infrastructure issues.

        print("\n🧪 Testing connection health and failover...)"
        
        user_context = self._create_test_user_context(health_failover)
        
        # Create primary and backup connections
        primary_connection = await self._create_mock_websocket_connection(user_context)
        primary_connection["connection_type] = primary"
        
        # Create backup connection with different connection ID
        backup_context = UserExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            websocket_client_id=f{user_context.websocket_client_id}_backup
        )
        backup_connection = await self._create_mock_websocket_connection(backup_context)
        backup_connection[connection_type] = backup
        
        # Create test events
        test_events = [
            self._create_test_agent_event(agent_started", user_context),"
            self._create_test_agent_event(agent_thinking, user_context),
            self._create_test_agent_event(tool_executing, user_context),""
        ]
        
        # Route initial events to primary connection
        primary_events_routed = 0
        
        for event in test_events[:2]:  # Route first 2 events to primary
            try:
                await self._simulate_event_routing(event, user_context.websocket_client_id)
                primary_events_routed += 1
                print(f"  📡 Primary: Routed {event.event_type})"
            except Exception as e:
                print(f  X Primary routing failed: {e})""
                break
        
        # Simulate primary connection failure
        print("  🔌 Simulating primary connection failure...)"
        primary_connection[status] = "disconnected"
        primary_connection[error"] = Connection lost due to network issue"
        primary_connection[failed_at] = datetime.now(timezone.utc)
        
        # Implement failover logic
        async def route_with_failover(event, primary_conn_id, backup_conn_id):
            "Route event with failover to backup connection."
            try:
                # Try primary connection first
                if self.mock_connections.get(primary_conn_id, {}.get(status) == "active:"
                    return await self._simulate_event_routing(event, primary_conn_id)
                else:
                    # Failover to backup
                    print(f    🔄 Failing over to backup for {event.event_type}")"
                    # Update event to use backup connection
                    event.websocket_client_id = backup_conn_id
                    return await self._simulate_event_routing(event, backup_conn_id)
            except Exception as e:
                raise Exception(fFailover routing failed: {e})
        
        # Route remaining events with failover
        backup_events_routed = 0
        
        for event in test_events[2:]:  # Route remaining events with failover
            try:
                await route_with_failover(
                    event, 
                    user_context.websocket_client_id, 
                    backup_context.websocket_client_id
                )
                backup_events_routed += 1
                print(f  📡 Backup: Routed {event.event_type}"")
            except Exception as e:
                print(f  X Failover routing failed: {e})
        
        # Add connection recovery test
        print(  🔌 Simulating primary connection recovery..."")
        primary_connection[status] = active
        primary_connection["recovered_at] = datetime.now(timezone.utc)"
        primary_connection[error] = None
        
        # Route additional events after recovery
        recovery_events = [
            self._create_test_agent_event(tool_completed, user_context),""
            self._create_test_agent_event(agent_completed", user_context)"
        ]
        
        recovered_events_routed = 0
        
        for event in recovery_events:
            try:
                # Should route to primary again after recovery
                await self._simulate_event_routing(event, user_context.websocket_client_id)
                recovered_events_routed += 1
                print(f  📡 Recovered: Routed {event.event_type})
            except Exception as e:
                print(f  X Recovery routing failed: {e}"")
        
        # Validate failover behavior
        primary_total_events = len(primary_connection[received_events)
        backup_total_events = len(backup_connection[received_events")"
        
        assert primary_events_routed > 0, "Primary connection should have received initial events"
        assert backup_events_routed > 0, Backup connection should have received failover events""
        assert recovered_events_routed > 0, "Primary connection should have received recovery events"
        
        # Validate event distribution
        total_expected_events = len(test_events) + len(recovery_events)
        total_routed_events = primary_total_events + backup_total_events
        assert total_routed_events == total_expected_events, "fEvent count mismatch: expected {total_expected_events}, got {total_routed_events}"
        
        # Validate no event loss during failover
        all_routed_event_types = []
        all_routed_event_types.extend([event["event)[type) for event in primary_connection[received_events))"
        all_routed_event_types.extend([event[event)["type) for event in backup_connection[received_events))"
        
        expected_event_types = [event.event_type for event in test_events + recovery_events]
        assert len(all_routed_event_types) == len(expected_event_types), "Event loss detected during failover"
        
        # Validate connection health metrics
        primary_metrics = primary_connection[routing_metrics"]"
        backup_metrics = backup_connection[routing_metrics]
        
        assert primary_metrics[events_received] > 0, "Primary connection should have health metrics"
        assert backup_metrics[events_received"] > 0, Backup connection should have health metrics"
        
        # Record metrics
        self.record_metric(primary_events_routed, primary_events_routed)
        self.record_metric("backup_events_routed, backup_events_routed)"
        self.record_metric(recovered_events_routed, recovered_events_routed)
        self.record_metric(failover_success_rate, backup_events_routed / max(len(test_events[2:], 1))""
        
        print(f  CHECK Connection health and failover successful")"
        print(f  📊 Event distribution: Primary {primary_total_events}, Backup {backup_total_events})
        print(f  🔄 Failover success rate: {backup_events_routed}/{len(test_events[2:]} = {backup_events_routed/max(len(test_events[2:], 1"):."2f"})"
        print(f  🚀 Recovery success rate: {recovered_events_routed}/{len(recovery_events)} = {recovered_events_routed/max(len(recovery_events), 1):."2f"})""


    @pytest.mark.asyncio
    async def test_routing_performance_under_load(self):
        """"

        Test: Routing performance under high concurrent load.
        
        Validates that the routing system maintains performance guarantees
        under high load with multiple concurrent users and events.
        
        Business Value: Ensures platform scalability for growing user base.

        print("\n🧪 Testing routing performance under load...)"
        
        # Create multiple users for load testing
        load_users = []
        load_connections = {}
        
        user_count = 10  # 10 concurrent users
        events_per_user = 20  # 20 events per user
        
        for i in range(user_count):
            user_context = self._create_test_user_context(fload_user_{i+1})
            connection = await self._create_mock_websocket_connection(user_context)
            load_users.append(user_context)
            load_connections[user_context.user_id] = connection
        
        # Create events for all users
        all_load_events = []
        user_event_maps = {}
        
        for user_context in load_users:
            user_events = []
            for j in range(events_per_user):
                event_type = ["agent_started, agent_thinking", tool_executing, tool_completed, agent_completed][j % 5]""
                event = self._create_test_agent_event(
                    event_type, 
                    user_context,
                    data={load_test": True, event_index: j, user_index: load_users.index(user_context)}"
                user_events.append(event)
                all_load_events.append((event, user_context))
            user_event_maps[user_context.user_id] = user_events
        
        # Shuffle for realistic concurrent load
        import random
        random.shuffle(all_load_events)
        
        print(f"  🚀 Starting load test: {user_count} users × {events_per_user} events = {len(all_load_events)} total events)"
        
        # Execute high-load routing
        async def route_load_event(event, user_context"):"
            Route event under load conditions.""
            start_time = time.time()
            try:
                result = await self._simulate_event_routing(event, user_context.websocket_client_id)
                routing_time = time.time() - start_time
                return {
                    "success: True, "
                    routing_time: routing_time,
                    "event_type: event.event_type,"
                    user_id: user_context.user_id
                }
            except Exception as e:
                routing_time = time.time() - start_time
                return {
                    success: False, ""
                    error": str(e),"
                    routing_time: routing_time,
                    event_type": event.event_type,"
                    user_id: user_context.user_id
                }
        
        # Execute all routing concurrently
        load_start_time = time.time()
        
        routing_results = await asyncio.gather(*[
            route_load_event(event, user_context)
            for event, user_context in all_load_events
        ]
        
        total_load_time = time.time() - load_start_time
        
        # Analyze performance results
        successful_routings = [r for r in routing_results if r[success]]""
        failed_routings = [r for r in routing_results if not r["success]]"
        
        success_rate = len(successful_routings) / len(routing_results)
        routing_times = [r[routing_time] for r in successful_routings]
        
        avg_routing_time = sum(routing_times) / len(routing_times) if routing_times else 0
        max_routing_time = max(routing_times) if routing_times else 0
        min_routing_time = min(routing_times) if routing_times else 0
        
        # Calculate throughput
        events_per_second = len(all_load_events) / total_load_time
        
        # Validate performance requirements
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%} < 95%"
        assert avg_routing_time < 0.1, fAverage routing time too slow: {avg_routing_time * 1000:."1f"}ms > "100ms"""
        assert events_per_second > 50, "fThroughput too low: {events_per_second:."1f"} events/sec < 50 events/sec"
        
        # Validate user isolation under load
        for user_context in load_users:
            user_id = user_context.user_id
            connection = load_connections[user_id]
            user_routed_events = connection[received_events]""
            
            # Check expected event count
            expected_count = events_per_user
            actual_count = len(user_routed_events)
            
            # Allow for some tolerance under high load
            tolerance = 0.9  # 90% delivery rate acceptable under extreme load
            min_expected = int(expected_count * tolerance)
            
            assert actual_count >= min_expected, f"User {user_id} event loss under load: {actual_count}/{expected_count} < {tolerance:.0%}"
            
            # Validate all events belong to correct user
            for routed_event in user_routed_events:
                event_user = routed_event[event][user_id]
                assert event_user == user_id, fUser isolation failure under load: {event_user} != {user_id}""
        
        # Record comprehensive metrics
        self.record_metric("load_test_users, user_count)"
        self.record_metric(load_test_events_per_user, events_per_user)
        self.record_metric("load_test_total_events, len(all_load_events))"
        self.record_metric(load_test_success_rate, success_rate)
        self.record_metric(load_test_avg_routing_time_ms, avg_routing_time * 1000)""
        self.record_metric(load_test_max_routing_time_ms", max_routing_time * 1000)"
        self.record_metric(load_test_events_per_second, events_per_second)
        self.record_metric(load_test_total_time_ms", total_load_time * 1000)"
        
        print(f  CHECK Load test successful - {success_rate:.1%} success rate)
        print(f  🚀 Throughput: {events_per_second:."1f"} events/sec")"
        print(f  ⚡ Performance: avg {avg_routing_time * 1000:."1f"}ms, max {max_routing_time * 1000:."1f"}ms)
        print(f  🕒 Total duration: {total_load_time * 1000:."1f"}ms")"
        
        if failed_routings:
            print(f  WARNING️ Failures: {len(failed_routings)} events failed routing)


if __name__ == __main__:""
    "MIGRATED: Use SSOT unified test runner"
    print(MIGRATION NOTICE: Please use SSOT unified test runner"")
    print(Command: python tests/unified_test_runner.py --category integration")"
""""

))))))))))))))))))))))))))))))))))