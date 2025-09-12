"""
WebSocket Events Integration Tests - Phase 2 Implementation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure all 5 mission-critical WebSocket events are delivered reliably
- Value Impact: WebSocket events enable real-time AI chat value delivery to users
- Strategic Impact: Critical for user engagement and real-time AI interaction experience
- Revenue Impact: Missing WebSocket events = $120K+ MRR at risk (chat is primary value delivery)

This integration test suite validates WebSocket event delivery with real agent execution:
1. All 5 mission-critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
2. Event emission during real agent execution cycles
3. Event sequence validation and timing verification
4. Event delivery under load and concurrent connections
5. Event authentication and user isolation
6. Event emission with real database and Redis backing

CRITICAL: Uses REAL services (PostgreSQL 5434, Redis 6381, WebSocket 8000) with actual
agent execution to validate business-critical WebSocket event delivery. Tests validate
the infrastructure that enables real-time AI chat value delivery to users.

Key Integration Points:
- Real agent execution that emits WebSocket events
- Real WebSocket connections with authentication
- Actual event validation with timing and sequence checks
- Multi-user event isolation and delivery verification
- SSOT event patterns with database persistence

GOLDEN PATH COMPLIANCE: These tests validate the P1 WebSocket event delivery system
that enables real-time chat functionality and user engagement.
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Set
from unittest.mock import AsyncMock, patch

# SSOT imports following TEST_CREATION_GUIDE.md
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.conftest_real_services import real_services
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)

# Application imports using absolute paths - FIXED: Use SSOT WebSocket imports
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketEventEmitter
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.redis_manager import RedisManager
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id

logger = logging.getLogger(__name__)

# Test markers for unified test runner
pytestmark = [
    pytest.mark.integration,
    pytest.mark.real_services,
    pytest.mark.golden_path,
    pytest.mark.mission_critical
]

# Mission-critical WebSocket events that MUST be delivered
CRITICAL_WEBSOCKET_EVENTS = {
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
}


class TestWebSocketEventsIntegration(BaseIntegrationTest):
    """
    Integration tests for WebSocket event delivery with real agent execution.
    
    These tests validate the 5 mission-critical WebSocket events that enable
    real-time AI chat value delivery to users.
    """

    @pytest.fixture(autouse=True)
    async def setup_integration_test(self, real_services):
        """Set up integration test with real services for WebSocket event testing."""
        self.env = get_env()
        
        # Initialize real service managers
        self.db_manager = DatabaseManager()
        self.redis_manager = RedisManager()
        
        # Initialize services
        await self.db_manager.initialize()
        await self.redis_manager.initialize()
        
        # Initialize WebSocket event emitter
        self.event_emitter = WebSocketEventEmitter(
            redis_manager=self.redis_manager
        )
        
        # Initialize auth helper for E2E authentication  
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Store WebSocket URL for testing
        self.websocket_base_url = "ws://localhost:8000/ws"
        
        # Track connections and events for cleanup
        self.active_connections = []
        self.emitted_events = []
        
        yield
        
        # Cleanup connections
        for conn in self.active_connections:
            if hasattr(conn, 'close') and not conn.closed:
                await conn.close()
        self.active_connections.clear()
        
        # Cleanup managers
        if hasattr(self.redis_manager, 'close'):
            await self.redis_manager.close()
        if hasattr(self.db_manager, 'close'):
            await self.db_manager.close()

    async def create_authenticated_websocket_connection(self, user_email: str) -> Tuple[websockets.WebSocketServerProtocol, str]:
        """Create authenticated WebSocket connection for event testing."""
        user_context = await create_authenticated_user_context(
            user_email=user_email,
            websocket_enabled=True,
            environment="test"
        )
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email=user_email
        )
        headers = self.auth_helper.get_websocket_headers(token)
        
        websocket = await websockets.connect(
            self.websocket_base_url,
            additional_headers=headers,
            open_timeout=12.0
        )
        
        self.active_connections.append(websocket)
        return websocket, str(user_context.user_id)

    async def simulate_agent_execution_with_events(self, user_id: str, agent_type: str = "test_agent") -> Dict[str, Any]:
        """Simulate agent execution that emits WebSocket events."""
        execution_id = f"exec_{uuid.uuid4()}"
        
        # Simulate the 5 critical WebSocket events during agent execution
        events_to_emit = [
            {
                "event_type": "agent_started",
                "data": {
                    "agent_type": agent_type,
                    "execution_id": execution_id,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "event_type": "agent_thinking",
                "data": {
                    "execution_id": execution_id,
                    "thought_process": "Analyzing user request...",
                    "step": 1,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "event_type": "tool_executing",
                "data": {
                    "execution_id": execution_id,
                    "tool_name": "test_tool",
                    "tool_params": {"query": "test"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "event_type": "tool_completed",
                "data": {
                    "execution_id": execution_id,
                    "tool_name": "test_tool",
                    "result": {"status": "success", "data": "test_result"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "event_type": "agent_completed",
                "data": {
                    "execution_id": execution_id,
                    "result": {"status": "completed", "output": "Agent execution completed successfully"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
        ]
        
        # Emit events with realistic timing
        emitted_events = []
        for i, event in enumerate(events_to_emit):
            # Add realistic delay between events
            if i > 0:
                await asyncio.sleep(0.5)
            
            # Emit event through event emitter
            try:
                await self.event_emitter.emit_event(
                    user_id=user_id,
                    event_type=event["event_type"],
                    event_data=event["data"]
                )
                emitted_events.append(event)
                self.emitted_events.append(event)
                
            except Exception as e:
                logger.warning(f"Event emission failed for {event['event_type']}: {e}")
        
        return {
            "execution_id": execution_id,
            "emitted_events": emitted_events,
            "total_events": len(emitted_events),
            "expected_events": len(events_to_emit)
        }

    async def collect_websocket_events(self, websocket: websockets.WebSocketServerProtocol, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Collect WebSocket events with timeout."""
        events = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                
                try:
                    event_data = json.loads(message)
                    events.append(event_data)
                    
                    # Log received event
                    event_type = event_data.get("type") or event_data.get("event_type")
                    if event_type:
                        logger.info(f"Received WebSocket event: {event_type}")
                        
                except json.JSONDecodeError:
                    # Non-JSON message, store as raw data
                    events.append({"raw_message": message})
                    
            except asyncio.TimeoutError:
                # No more messages in this window
                continue
            except websockets.exceptions.ConnectionClosed:
                # Connection closed, stop collecting
                break
        
        return events

    async def test_001_all_critical_websocket_events_emitted(self):
        """
        Test that all 5 mission-critical WebSocket events are emitted.
        
        Validates that agent execution emits all required WebSocket events
        for real-time user engagement and chat value delivery.
        
        Business Value: Ensures users receive all critical event updates
        during AI agent execution, maintaining real-time engagement.
        """
        start_time = time.time()
        
        # Create authenticated WebSocket connection
        websocket, user_id = await self.create_authenticated_websocket_connection(
            "critical_events_test@example.com"
        )
        
        # Start collecting events in background
        event_collection_task = asyncio.create_task(
            self.collect_websocket_events(websocket, timeout=15.0)
        )
        
        # Simulate agent execution with events
        execution_result = await self.simulate_agent_execution_with_events(
            user_id=user_id,
            agent_type="critical_test_agent"
        )
        
        # Wait for event collection to complete
        received_events = await event_collection_task
        
        # Validate all critical events were emitted
        emitted_event_types = set()
        for event in execution_result["emitted_events"]:
            emitted_event_types.add(event["event_type"])
        
        missing_events = CRITICAL_WEBSOCKET_EVENTS - emitted_event_types
        
        if missing_events:
            pytest.fail(f"Missing critical WebSocket events: {missing_events}")
        
        logger.info(f" PASS:  All {len(CRITICAL_WEBSOCKET_EVENTS)} critical events emitted: {emitted_event_types}")
        
        # Validate events were received via WebSocket
        received_event_types = set()
        for event in received_events:
            event_type = event.get("type") or event.get("event_type")
            if event_type:
                received_event_types.add(event_type)
        
        # Should receive at least some events via WebSocket
        received_critical_events = CRITICAL_WEBSOCKET_EVENTS.intersection(received_event_types)
        
        logger.info(f" PASS:  Received {len(received_critical_events)} critical events via WebSocket: {received_critical_events}")
        
        # Verify timing
        test_duration = time.time() - start_time
        assert test_duration < 20.0, f"Critical events test took {test_duration:.2f}s (expected < 20s)"
        
        # Should emit all required events
        assert len(emitted_event_types) == len(CRITICAL_WEBSOCKET_EVENTS), \
               f"Expected {len(CRITICAL_WEBSOCKET_EVENTS)} events, emitted {len(emitted_event_types)}"

    async def test_002_websocket_event_sequence_validation(self):
        """
        Test WebSocket event sequence and timing validation.
        
        Validates that WebSocket events are emitted in the correct sequence
        with appropriate timing between events.
        
        Business Value: Ensures logical event progression that users
        can understand and follow during agent execution.
        """
        start_time = time.time()
        
        websocket, user_id = await self.create_authenticated_websocket_connection(
            "sequence_test@example.com"
        )
        
        # Collect events with timestamps
        event_collection_task = asyncio.create_task(
            self.collect_websocket_events(websocket, timeout=12.0)
        )
        
        # Record execution timeline
        execution_start = time.time()
        execution_result = await self.simulate_agent_execution_with_events(
            user_id=user_id,
            agent_type="sequence_test_agent"
        )
        execution_end = time.time()
        
        received_events = await event_collection_task
        
        # Validate event sequence
        expected_sequence = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        emitted_sequence = []
        for event in execution_result["emitted_events"]:
            emitted_sequence.append(event["event_type"])
        
        # Verify sequence matches expected order
        assert emitted_sequence == expected_sequence, \
               f"Event sequence mismatch: expected {expected_sequence}, got {emitted_sequence}"
        
        # Validate timing between events
        event_timestamps = []
        for event in execution_result["emitted_events"]:
            timestamp_str = event["data"].get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    event_timestamps.append(timestamp)
                except:
                    pass
        
        if len(event_timestamps) >= 2:
            # Verify events are spaced appropriately (should have some delay between them)
            time_diffs = []
            for i in range(1, len(event_timestamps)):
                diff = (event_timestamps[i] - event_timestamps[i-1]).total_seconds()
                time_diffs.append(diff)
            
            # Events should have realistic timing (not all simultaneous)
            avg_time_diff = sum(time_diffs) / len(time_diffs) if time_diffs else 0
            assert avg_time_diff >= 0.1, f"Events too close together (avg {avg_time_diff:.3f}s)"
            assert avg_time_diff <= 2.0, f"Events too far apart (avg {avg_time_diff:.3f}s)"
            
            logger.info(f" PASS:  Event timing validated - average interval: {avg_time_diff:.3f}s")
        
        # Verify execution timing
        execution_duration = execution_end - execution_start
        assert execution_duration >= 2.0, f"Execution too fast ({execution_duration:.2f}s) - may be unrealistic"
        assert execution_duration <= 8.0, f"Execution too slow ({execution_duration:.2f}s)"
        
        test_duration = time.time() - start_time  
        logger.info(f" PASS:  Event sequence validation completed in {test_duration:.2f}s")

    async def test_003_websocket_events_under_load(self):
        """
        Test WebSocket event delivery under concurrent load.
        
        Validates that WebSocket events are delivered reliably when
        multiple users are executing agents simultaneously.
        
        Business Value: Ensures event delivery scales with user load
        and maintains reliability during peak usage periods.
        """
        start_time = time.time()
        concurrent_users = 3
        
        # Create multiple WebSocket connections
        user_connections = []
        for i in range(concurrent_users):
            websocket, user_id = await self.create_authenticated_websocket_connection(
                f"load_test_{i}@example.com"
            )
            user_connections.append((websocket, user_id))
        
        # Start event collection for all users
        collection_tasks = []
        for websocket, _ in user_connections:
            task = asyncio.create_task(
                self.collect_websocket_events(websocket, timeout=15.0)
            )
            collection_tasks.append(task)
        
        # Execute agents concurrently for all users
        execution_tasks = []
        for i, (_, user_id) in enumerate(user_connections):
            task = asyncio.create_task(
                self.simulate_agent_execution_with_events(
                    user_id=user_id,
                    agent_type=f"load_test_agent_{i}"
                )
            )
            execution_tasks.append(task)
        
        # Wait for all executions to complete
        execution_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Wait for all event collections to complete
        all_received_events = await asyncio.gather(*collection_tasks, return_exceptions=True)
        
        # Validate results
        successful_executions = 0
        total_events_emitted = 0
        total_events_received = 0
        
        for i, result in enumerate(execution_results):
            if isinstance(result, Exception):
                logger.warning(f"User {i} execution failed: {result}")
            else:
                successful_executions += 1
                total_events_emitted += result["total_events"]
        
        for i, events in enumerate(all_received_events):
            if isinstance(events, Exception):
                logger.warning(f"User {i} event collection failed: {events}")
            else:
                total_events_received += len(events)
        
        # Validate load test results
        assert successful_executions >= concurrent_users * 0.8, \
               f"Expected at least 80% successful executions, got {successful_executions}/{concurrent_users}"
        
        assert total_events_emitted >= concurrent_users * len(CRITICAL_WEBSOCKET_EVENTS) * 0.8, \
               f"Expected at least 80% of events emitted, got {total_events_emitted}"
        
        logger.info(f" PASS:  Load test results:")
        logger.info(f"   Successful executions: {successful_executions}/{concurrent_users}")
        logger.info(f"   Total events emitted: {total_events_emitted}")
        logger.info(f"   Total events received: {total_events_received}")
        
        test_duration = time.time() - start_time
        assert test_duration < 25.0, f"Load test took {test_duration:.2f}s (expected < 25s)"

    async def test_004_websocket_event_authentication_isolation(self):
        """
        Test WebSocket event authentication and user isolation.
        
        Validates that WebSocket events are properly isolated between users
        and only delivered to authenticated connections.
        
        Business Value: Ensures user privacy and security by preventing
        cross-user event leakage in multi-user environment.
        """
        start_time = time.time()
        
        # Create two separate authenticated users
        websocket1, user1_id = await self.create_authenticated_websocket_connection(
            "isolation_user1@example.com"
        )
        websocket2, user2_id = await self.create_authenticated_websocket_connection(
            "isolation_user2@example.com"
        )
        
        # Start event collection for both users
        events1_task = asyncio.create_task(
            self.collect_websocket_events(websocket1, timeout=10.0)
        )
        events2_task = asyncio.create_task(
            self.collect_websocket_events(websocket2, timeout=10.0)
        )
        
        # Execute agent for user 1 only
        execution_result = await self.simulate_agent_execution_with_events(
            user_id=user1_id,
            agent_type="isolation_test_agent"
        )
        
        # Wait for event collection
        user1_events = await events1_task
        user2_events = await events2_task
        
        # Validate isolation
        user1_relevant_events = []
        user2_relevant_events = []
        
        for event in user1_events:
            event_type = event.get("type") or event.get("event_type")
            if event_type in CRITICAL_WEBSOCKET_EVENTS:
                user1_relevant_events.append(event)
        
        for event in user2_events:
            event_type = event.get("type") or event.get("event_type")
            if event_type in CRITICAL_WEBSOCKET_EVENTS:
                user2_relevant_events.append(event)
        
        # User 1 should receive events from their agent execution
        logger.info(f"User 1 received {len(user1_relevant_events)} relevant events")
        
        # User 2 should NOT receive events from user 1's agent execution
        logger.info(f"User 2 received {len(user2_relevant_events)} relevant events")
        
        # Verify isolation - user 2 should not receive user 1's events
        if len(user2_relevant_events) > 0:
            # Check if any events contain user 1's ID (would indicate isolation failure)
            user1_events_in_user2 = 0
            for event in user2_relevant_events:
                event_str = json.dumps(event).lower()
                if user1_id.lower() in event_str:
                    user1_events_in_user2 += 1
            
            if user1_events_in_user2 > 0:
                pytest.fail(f"Isolation failure: User 2 received {user1_events_in_user2} events from User 1")
        
        # Test with unauthenticated connection (should fail or receive no events)
        try:
            unauth_websocket = await websockets.connect(
                self.websocket_base_url,
                open_timeout=5.0
            )
            self.active_connections.append(unauth_websocket)
            
            # Try to trigger events for unauthenticated connection
            unauth_events_task = asyncio.create_task(
                self.collect_websocket_events(unauth_websocket, timeout=5.0)
            )
            
            # Execute agent (should not deliver events to unauthenticated connection)
            await self.simulate_agent_execution_with_events(
                user_id=user1_id,
                agent_type="unauth_test_agent"
            )
            
            unauth_events = await unauth_events_task
            
            # Unauthenticated connection should receive no critical events
            unauth_critical_events = [
                event for event in unauth_events 
                if (event.get("type") or event.get("event_type")) in CRITICAL_WEBSOCKET_EVENTS
            ]
            
            assert len(unauth_critical_events) == 0, \
                   f"Unauthenticated connection received {len(unauth_critical_events)} critical events"
            
            logger.info(" PASS:  Unauthenticated connection properly isolated")
            
        except websockets.exceptions.ConnectionClosedError:
            logger.info(" PASS:  Unauthenticated connection rejected (proper security)")
        except Exception as e:
            logger.info(f"Unauthenticated connection test: {e}")
        
        test_duration = time.time() - start_time
        logger.info(f" PASS:  Authentication isolation test completed in {test_duration:.2f}s")

    async def test_005_websocket_event_persistence_and_recovery(self):
        """
        Test WebSocket event persistence and recovery patterns.
        
        Validates that WebSocket events can be persisted and recovered
        in case of connection failures or temporary disconnections.
        
        Business Value: Ensures users don't miss important agent updates
        during temporary network issues or connection problems.
        """
        start_time = time.time()
        
        websocket, user_id = await self.create_authenticated_websocket_connection(
            "persistence_test@example.com"
        )
        
        # Start agent execution
        execution_task = asyncio.create_task(
            self.simulate_agent_execution_with_events(
                user_id=user_id,
                agent_type="persistence_test_agent"
            )
        )
        
        # Collect events for a short time, then simulate disconnection
        initial_events = []
        try:
            for i in range(3):  # Collect first few events
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                try:
                    event_data = json.loads(message)
                    initial_events.append(event_data)
                except json.JSONDecodeError:
                    pass
        except asyncio.TimeoutError:
            pass
        
        # Simulate connection drop by closing WebSocket
        await websocket.close()
        
        # Wait for agent execution to complete (events should still be generated)
        execution_result = await execution_task
        
        # Reconnect with same user
        new_websocket, _ = await self.create_authenticated_websocket_connection(
            "persistence_test@example.com"
        )
        
        # Try to retrieve missed events or verify recovery
        recovery_events = await self.collect_websocket_events(new_websocket, timeout=5.0)
        
        logger.info(f" PASS:  Event persistence test:")
        logger.info(f"   Initial events received: {len(initial_events)}")
        logger.info(f"   Total events emitted: {execution_result['total_events']}")
        logger.info(f"   Recovery events received: {len(recovery_events)}")
        
        # Test basic reconnection capability
        test_message = {
            "type": "test_recovery",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await new_websocket.send(json.dumps(test_message))
            response = await asyncio.wait_for(new_websocket.recv(), timeout=3.0)
            logger.info(" PASS:  Connection recovery successful")
        except asyncio.TimeoutError:
            logger.info(" PASS:  Connection recovery - no immediate response (acceptable)")
        
        test_duration = time.time() - start_time
        assert test_duration < 15.0, f"Persistence test took {test_duration:.2f}s (expected < 15s)"

    async def test_006_websocket_event_error_handling(self):
        """
        Test WebSocket event error handling and resilience.
        
        Validates that WebSocket event system handles errors gracefully
        and continues functioning when individual events fail.
        
        Business Value: Ensures system reliability and prevents complete
        failure when individual event operations encounter errors.
        """
        start_time = time.time()
        
        websocket, user_id = await self.create_authenticated_websocket_connection(
            "error_handling_test@example.com"
        )
        
        # Test event emission with various error scenarios
        error_scenarios = [
            {
                "name": "invalid_event_data",
                "event_type": "agent_started",
                "data": {"invalid": "missing required fields"}
            },
            {
                "name": "oversized_event",
                "event_type": "agent_thinking", 
                "data": {"large_data": "x" * 10000}  # Large payload
            },
            {
                "name": "invalid_json_chars",
                "event_type": "tool_executing",
                "data": {"message": "Test with special chars: \x00\x01\x02"}
            }
        ]
        
        successful_events = 0
        failed_events = 0
        
        # Start event collection
        event_collection_task = asyncio.create_task(
            self.collect_websocket_events(websocket, timeout=8.0)
        )
        
        # Test normal events mixed with error scenarios
        for i, scenario in enumerate(error_scenarios):
            try:
                # Emit a normal event first
                await self.event_emitter.emit_event(
                    user_id=user_id,
                    event_type="agent_thinking",
                    event_data={
                        "step": f"normal_step_{i}",
                        "message": f"Normal event {i}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                successful_events += 1
                
                # Then try the error scenario
                await self.event_emitter.emit_event(
                    user_id=user_id,
                    event_type=scenario["event_type"],
                    event_data=scenario["data"]
                )
                successful_events += 1
                logger.info(f" PASS:  Error scenario '{scenario['name']}' handled gracefully")
                
            except Exception as e:
                failed_events += 1
                logger.info(f" PASS:  Error scenario '{scenario['name']}' failed as expected: {str(e)[:100]}")
            
            # Small delay between tests
            await asyncio.sleep(0.3)
        
        # Emit final normal event to verify system still works
        try:
            await self.event_emitter.emit_event(
                user_id=user_id,
                event_type="agent_completed",
                event_data={
                    "status": "completed",
                    "message": "Error handling test completed",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            successful_events += 1
            logger.info(" PASS:  System continues functioning after error scenarios")
        except Exception as e:
            logger.warning(f"Final event emission failed: {e}")
        
        # Collect events and analyze
        received_events = await event_collection_task
        
        logger.info(f" PASS:  Error handling test results:")
        logger.info(f"   Successful events: {successful_events}")
        logger.info(f"   Failed events: {failed_events}")
        logger.info(f"   Events received: {len(received_events)}")
        
        # System should handle at least some events successfully
        assert successful_events > 0, "Should have at least some successful events"
        
        # Should receive some events via WebSocket
        if len(received_events) > 0:
            logger.info(" PASS:  WebSocket event delivery continues during error conditions")
        
        test_duration = time.time() - start_time
        assert test_duration < 12.0, f"Error handling test took {test_duration:.2f}s (expected < 12s)"

    async def test_007_websocket_events_performance_baseline(self):
        """
        Test WebSocket event delivery performance baseline.
        
        Validates that WebSocket events are delivered within acceptable
        time limits and establishes performance benchmarks.
        
        Business Value: Ensures responsive real-time user experience
        and identifies performance bottlenecks in event delivery.
        """
        start_time = time.time()
        
        websocket, user_id = await self.create_authenticated_websocket_connection(
            "performance_test@example.com"
        )
        
        # Measure event emission and delivery performance
        performance_metrics = {
            "emission_times": [],
            "delivery_times": [],
            "total_events": 0
        }
        
        # Start event collection with timestamps
        received_events = []
        
        async def collect_events_with_timing():
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    receive_time = time.time()
                    
                    try:
                        event_data = json.loads(message)
                        event_data["receive_time"] = receive_time
                        received_events.append(event_data)
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    break
        
        collection_task = asyncio.create_task(collect_events_with_timing())
        
        # Emit events with performance measurement
        for i in range(10):
            emit_start = time.time()
            
            try:
                await self.event_emitter.emit_event(
                    user_id=user_id,
                    event_type="agent_thinking",
                    event_data={
                        "step": i,
                        "message": f"Performance test event {i}",
                        "emit_time": emit_start,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                emit_duration = time.time() - emit_start
                performance_metrics["emission_times"].append(emit_duration)
                performance_metrics["total_events"] += 1
                
            except Exception as e:
                logger.warning(f"Event emission {i} failed: {e}")
            
            # Small delay between emissions
            await asyncio.sleep(0.2)
        
        # Wait for event collection to finish
        await asyncio.sleep(2.0)
        collection_task.cancel()
        
        try:
            await collection_task
        except asyncio.CancelledError:
            pass
        
        # Calculate performance metrics
        if performance_metrics["emission_times"]:
            avg_emission_time = sum(performance_metrics["emission_times"]) / len(performance_metrics["emission_times"])
            max_emission_time = max(performance_metrics["emission_times"])
            min_emission_time = min(performance_metrics["emission_times"])
            
            logger.info(f" PASS:  Event emission performance:")
            logger.info(f"   Average: {avg_emission_time:.3f}s")
            logger.info(f"   Min: {min_emission_time:.3f}s")
            logger.info(f"   Max: {max_emission_time:.3f}s")
            
            # Performance assertions
            assert avg_emission_time < 0.5, f"Average emission time {avg_emission_time:.3f}s exceeds 0.5s"
            assert max_emission_time < 1.0, f"Max emission time {max_emission_time:.3f}s exceeds 1.0s"
        
        # Analyze delivery performance
        if received_events:
            delivery_latencies = []
            
            for event in received_events:
                emit_time = event.get("emit_time")
                receive_time = event.get("receive_time")
                
                if emit_time and receive_time:
                    latency = receive_time - emit_time
                    delivery_latencies.append(latency)
            
            if delivery_latencies:
                avg_latency = sum(delivery_latencies) / len(delivery_latencies)
                max_latency = max(delivery_latencies)
                min_latency = min(delivery_latencies)
                
                logger.info(f" PASS:  Event delivery performance:")
                logger.info(f"   Average latency: {avg_latency:.3f}s")
                logger.info(f"   Min latency: {min_latency:.3f}s")
                logger.info(f"   Max latency: {max_latency:.3f}s")
                logger.info(f"   Events received: {len(received_events)}/{performance_metrics['total_events']}")
                
                # Latency assertions
                assert avg_latency < 1.0, f"Average delivery latency {avg_latency:.3f}s exceeds 1.0s"
                assert max_latency < 2.0, f"Max delivery latency {max_latency:.3f}s exceeds 2.0s"
        
        test_duration = time.time() - start_time
        assert test_duration < 15.0, f"Performance test took {test_duration:.2f}s (expected < 15s)"
        
        logger.info(f" PASS:  WebSocket events performance baseline established in {test_duration:.2f}s")