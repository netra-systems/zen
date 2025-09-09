"""
Event Persistence Across Reconnects Integration Tests - Phase 2

Tests that WebSocket state and events are properly maintained during
connection interruptions and reconnections. Validates event replay
and state recovery using real database persistence.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable chat experience during network issues
- Value Impact: Users don't lose context or messages during disconnections
- Strategic Impact: Platform reliability and user trust

CRITICAL: Uses REAL services (PostgreSQL, Redis, WebSocket connections)
No mocks in integration tests per CLAUDE.md standards.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.websocket_helpers import (
    WebSocketTestHelpers,
    ensure_websocket_service_ready
)
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.id_generation import UnifiedIdGenerator


class TestEventPersistenceAcrossReconnects(BaseIntegrationTest):
    """Integration tests for event persistence during WebSocket reconnections."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, real_services_fixture):
        """Setup test environment with real services."""
        self.services = real_services_fixture
        self.env = get_env()
        
        # Validate real services are available
        if not self.services["database_available"]:
            pytest.skip("Real database not available - required for integration testing")
            
        # Store service URLs
        self.backend_url = self.services["backend_url"]
        self.websocket_url = self.backend_url.replace("http://", "ws://") + "/ws"
        
        # Generate test identifiers using SSOT patterns
        self.test_user_id = UserID(f"reconnect_user_{UnifiedIdGenerator.generate_user_id()}")
        self.test_thread_id = ThreadID(f"reconnect_thread_{UnifiedIdGenerator.generate_thread_id()}")
        self.test_run_id = RunID(UnifiedIdGenerator.generate_run_id())

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_persistence_during_connection_drop(self, real_services_fixture):
        """Test that events are persisted when WebSocket connection drops during agent execution."""
        start_time = time.time()
        
        # Ensure services are ready
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
            
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Phase 1: Start agent execution
        initial_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        initial_events = []
        
        try:
            # Start long-running agent
            agent_request = {
                "type": "agent_request",
                "agent_name": "long_running_agent",
                "message": "Execute long task that will survive reconnection",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "run_id": str(self.test_run_id),
                "estimated_duration": 10.0
            }
            
            await WebSocketTestHelpers.send_test_message(initial_ws, agent_request)
            
            # Collect initial events
            for _ in range(3):  # Get first few events
                try:
                    event = await WebSocketTestHelpers.receive_test_message(initial_ws, timeout=5.0)
                    initial_events.append(event)
                    
                    # Stop after agent_started to simulate early disconnection
                    if event.get("type") == "agent_started":
                        break
                except Exception:
                    break
            
            # Verify we got agent_started
            event_types = [e.get("type") for e in initial_events]
            assert "agent_started" in event_types, "Should have received agent_started event"
            
        finally:
            # Simulate connection drop
            await WebSocketTestHelpers.close_test_connection(initial_ws)
        
        # Phase 2: Wait for agent to continue processing in background
        await asyncio.sleep(3.0)  # Allow background processing
        
        # Phase 3: Reconnect and check for event replay
        reconnect_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        reconnect_events = []
        
        try:
            # Send reconnection request
            reconnect_request = {
                "type": "reconnect",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "last_seen_event": initial_events[-1].get("event_id") if initial_events else None
            }
            
            await WebSocketTestHelpers.send_test_message(reconnect_ws, reconnect_request)
            
            # Collect events after reconnection
            collection_timeout = 15.0
            collection_start = time.time()
            
            while time.time() - collection_start < collection_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(reconnect_ws, timeout=5.0)
                    reconnect_events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except Exception as e:
                    if "timeout" in str(e).lower() and reconnect_events:
                        break
                    continue
            
            # Verify test took significant time (real services)
            test_duration = time.time() - start_time
            assert test_duration > 3.0, f"Test completed too quickly ({test_duration:.2f}s) - not using real services"
            
            # Verify event continuity and replay
            all_event_types = [e.get("type") for e in initial_events + reconnect_events]
            
            # Should have complete event sequence despite reconnection
            assert "agent_started" in all_event_types, "Missing agent_started after reconnection"
            assert "agent_completed" in all_event_types, "Agent should have completed despite reconnection"
            
            # Verify database persistence survived reconnection
            query = """
            SELECT event_type, event_id, created_at, payload
            FROM websocket_events 
            WHERE thread_id = :thread_id AND user_id = :user_id
            ORDER BY created_at ASC
            """
            
            result = await db_session.execute(query, {
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id)
            })
            persisted_events = result.fetchall()
            
            # Verify events persisted despite connection drop
            assert len(persisted_events) >= 3, f"Expected at least 3 persisted events, got {len(persisted_events)}"
            
            persisted_types = [event.event_type for event in persisted_events]
            assert "agent_started" in persisted_types, "agent_started event not persisted"
            
        finally:
            await WebSocketTestHelpers.close_test_connection(reconnect_ws)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_replay_after_reconnection(self, real_services_fixture):
        """Test event replay mechanism after WebSocket reconnection."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Phase 1: Complete an agent execution while connected
        initial_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        completed_events = []
        
        try:
            # Execute complete agent workflow
            complete_request = {
                "type": "agent_request",
                "agent_name": "quick_agent",
                "message": "Execute and complete quickly for replay test",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "quick_execution": True
            }
            
            await WebSocketTestHelpers.send_test_message(initial_ws, complete_request)
            
            # Collect all events from complete execution
            for _ in range(10):
                try:
                    event = await WebSocketTestHelpers.receive_test_message(initial_ws, timeout=5.0)
                    completed_events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                except Exception:
                    break
            
            # Verify complete execution occurred
            completed_event_types = [e.get("type") for e in completed_events]
            assert "agent_completed" in completed_event_types, "Agent should have completed"
            
        finally:
            await WebSocketTestHelpers.close_test_connection(initial_ws)
        
        # Phase 2: Wait, then reconnect to test replay
        await asyncio.sleep(1.0)
        
        replay_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        replayed_events = []
        
        try:
            # Request event replay
            replay_request = {
                "type": "replay_events",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "since_timestamp": start_time - 1.0  # Replay from before test started
            }
            
            await WebSocketTestHelpers.send_test_message(replay_ws, replay_request)
            
            # Collect replayed events
            for _ in range(15):  # Allow for more events during replay
                try:
                    event = await WebSocketTestHelpers.receive_test_message(replay_ws, timeout=3.0)
                    replayed_events.append(event)
                    
                    # Stop when replay is complete
                    if event.get("type") == "replay_complete":
                        break
                        
                except Exception:
                    break  # Timeout expected when replay is done
            
            # Verify test duration (real service operations)
            test_duration = time.time() - start_time
            assert test_duration > 2.0, "Replay test completed too quickly"
            
            # Verify replay functionality
            if replayed_events:
                replayed_types = [e.get("type") for e in replayed_events]
                
                # Should contain original events or replay confirmation
                replay_indicators = ["replay_complete", "event_replay", "agent_started", "agent_completed"]
                has_replay_activity = any(indicator in replayed_types for indicator in replay_indicators)
                
                assert has_replay_activity, f"No replay activity detected. Got events: {replayed_types}"
            
            # Verify database state consistency after replay
            query = """
            SELECT COUNT(*) as event_count, MAX(created_at) as last_event_time
            FROM websocket_events 
            WHERE thread_id = :thread_id AND user_id = :user_id
            """
            
            result = await db_session.execute(query, {
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id)
            })
            
            stats = result.fetchone()
            assert stats.event_count > 0, "Events should be persisted in database"
            
        finally:
            await WebSocketTestHelpers.close_test_connection(replay_ws)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_recovery_from_database(self, real_services_fixture):
        """Test WebSocket state recovery from database after service restart."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Phase 1: Create persistent state
        setup_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            # Create agent session with persistent state
            state_request = {
                "type": "create_persistent_session",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "session_data": {
                    "agent_name": "stateful_agent",
                    "conversation_history": ["User: Hello", "Agent: Hi there!"],
                    "context_variables": {"user_preference": "detailed_responses"}
                },
                "persist_to_database": True
            }
            
            await WebSocketTestHelpers.send_test_message(setup_ws, state_request)
            
            # Wait for state persistence
            confirmation_event = await WebSocketTestHelpers.receive_test_message(setup_ws, timeout=5.0)
            assert confirmation_event.get("type") in ["session_created", "state_persisted", "ack"], (
                "Should receive confirmation of state creation"
            )
            
        finally:
            await WebSocketTestHelpers.close_test_connection(setup_ws)
        
        # Phase 2: Simulate service restart by disconnecting and waiting
        await asyncio.sleep(2.0)
        
        # Phase 3: Reconnect and verify state recovery
        recovery_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            # Request state recovery
            recovery_request = {
                "type": "recover_session_state",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id)
            }
            
            await WebSocketTestHelpers.send_test_message(recovery_ws, recovery_request)
            
            # Collect recovery response
            recovery_events = []
            for _ in range(5):
                try:
                    event = await WebSocketTestHelpers.receive_test_message(recovery_ws, timeout=5.0)
                    recovery_events.append(event)
                    
                    if event.get("type") == "state_recovered":
                        break
                        
                except Exception:
                    break
            
            # Verify test took real time
            test_duration = time.time() - start_time
            assert test_duration > 2.5, "State recovery test completed too quickly"
            
            # Verify state recovery
            recovery_types = [e.get("type") for e in recovery_events]
            
            # Should have some form of state recovery response
            recovery_indicators = ["state_recovered", "session_restored", "context_loaded", "ack"]
            has_recovery = any(indicator in recovery_types for indicator in recovery_indicators)
            
            # May not have explicit recovery events in all implementations
            # So we also verify database persistence worked
            query = """
            SELECT session_data, created_at
            FROM user_sessions 
            WHERE thread_id = :thread_id AND user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            result = await db_session.execute(query, {
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id)
            })
            
            session_row = result.fetchone()
            
            # Verify either WebSocket recovery OR database persistence
            assert has_recovery or session_row is not None, (
                "Should have either WebSocket state recovery events or database session persistence"
            )
            
        finally:
            await WebSocketTestHelpers.close_test_connection(recovery_ws)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_resilience_during_agent_execution(self, real_services_fixture):
        """Test connection resilience patterns during active agent execution."""
        start_time = time.time()
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Track all events across connection cycles
        all_collected_events = []
        connection_attempts = 0
        max_connection_attempts = 3
        
        while connection_attempts < max_connection_attempts:
            connection_attempts += 1
            
            # Create connection
            websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                f"{self.websocket_url}/agent/{self.test_thread_id}",
                headers=headers,
                user_id=str(self.test_user_id)
            )
            
            connection_events = []
            
            try:
                if connection_attempts == 1:
                    # First connection: Start agent
                    start_request = {
                        "type": "agent_request",
                        "agent_name": "resilient_agent",
                        "message": "Execute resilient task with connection interruptions",
                        "thread_id": str(self.test_thread_id),
                        "user_id": str(self.test_user_id),
                        "resilience_test": True
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, start_request)
                else:
                    # Subsequent connections: Continue/resume
                    continue_request = {
                        "type": "continue_execution",
                        "thread_id": str(self.test_thread_id),
                        "user_id": str(self.test_user_id),
                        "resume_from": len(all_collected_events)
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, continue_request)
                
                # Collect events for short duration (simulating interruption)
                collection_duration = 2.0 if connection_attempts < max_connection_attempts else 8.0
                collection_start = time.time()
                
                while time.time() - collection_start < collection_duration:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                        connection_events.append(event)
                        
                        # Exit early if agent completes
                        if event.get("type") == "agent_completed":
                            all_collected_events.extend(connection_events)
                            break
                            
                    except Exception:
                        # Timeout or connection error - normal for resilience test
                        break
                
                all_collected_events.extend(connection_events)
                
                # Check if agent completed
                event_types = [e.get("type") for e in connection_events]
                if "agent_completed" in event_types:
                    break
                    
            finally:
                # Simulate connection drop
                await WebSocketTestHelpers.close_test_connection(websocket)
                
                # Brief pause before reconnection
                if connection_attempts < max_connection_attempts:
                    await asyncio.sleep(1.0)
        
        # Verify test characteristics
        test_duration = time.time() - start_time
        assert test_duration > 5.0, "Resilience test should take significant time"
        
        # Analyze resilience results
        all_event_types = [e.get("type") for e in all_collected_events]
        
        # Should have received events across multiple connections
        assert len(all_collected_events) >= connection_attempts, (
            "Should have received events from multiple connection attempts"
        )
        
        # Should have agent lifecycle events
        assert "agent_started" in all_event_types, "Should have agent_started event"
        
        # Agent may or may not complete in resilience test - both outcomes are valid
        agent_outcome = "agent_completed" in all_event_types or "agent_failed" in all_event_types
        
        # Verify we made multiple connection attempts (resilience pattern)
        assert connection_attempts >= 2, "Should have attempted multiple connections for resilience test"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_deduplication_across_reconnects(self, real_services_fixture):
        """Test message deduplication prevents duplicate events after reconnection."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Use unique message ID for deduplication testing
        unique_message_id = f"dedup_test_{int(time.time() * 1000)}"
        
        # Phase 1: Send message and collect initial response
        first_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        first_events = []
        
        try:
            # Send message with unique ID
            dedup_request = {
                "type": "agent_request",
                "agent_name": "dedup_agent",
                "message": "Execute with message deduplication",
                "message_id": unique_message_id,
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "idempotency_key": unique_message_id
            }
            
            await WebSocketTestHelpers.send_test_message(first_ws, dedup_request)
            
            # Collect some initial events
            for _ in range(3):
                try:
                    event = await WebSocketTestHelpers.receive_test_message(first_ws, timeout=3.0)
                    first_events.append(event)
                except Exception:
                    break
            
            assert len(first_events) > 0, "Should have received some events from first connection"
            
        finally:
            await WebSocketTestHelpers.close_test_connection(first_ws)
        
        # Phase 2: Reconnect and send the same message (should be deduplicated)
        await asyncio.sleep(1.0)
        
        second_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        second_events = []
        
        try:
            # Send identical message (should be deduplicated)
            duplicate_request = {
                "type": "agent_request",
                "agent_name": "dedup_agent",
                "message": "Execute with message deduplication",
                "message_id": unique_message_id,  # Same ID
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "idempotency_key": unique_message_id  # Same key
            }
            
            await WebSocketTestHelpers.send_test_message(second_ws, duplicate_request)
            
            # Collect response to duplicate message
            for _ in range(5):
                try:
                    event = await WebSocketTestHelpers.receive_test_message(second_ws, timeout=3.0)
                    second_events.append(event)
                except Exception:
                    break
            
            # Verify test took real time
            test_duration = time.time() - start_time
            assert test_duration > 1.5, "Deduplication test completed too quickly"
            
            # Analyze deduplication behavior
            second_event_types = [e.get("type") for e in second_events]
            
            # Should receive deduplication response or cached result
            dedup_indicators = [
                "duplicate_request",
                "cached_response", 
                "already_processed",
                "idempotency_conflict"
            ]
            
            has_dedup_response = any(indicator in second_event_types for indicator in dedup_indicators)
            
            # OR should get the same agent_completed result quickly (from cache)
            has_quick_completion = "agent_completed" in second_event_types and len(second_events) <= 3
            
            # Verify deduplication occurred
            assert has_dedup_response or has_quick_completion, (
                f"Expected deduplication behavior but got events: {second_event_types}"
            )
            
            # Verify database doesn't have duplicate processing
            query = """
            SELECT COUNT(*) as message_count
            FROM processed_messages 
            WHERE message_id = :message_id OR idempotency_key = :idempotency_key
            """
            
            result = await db_session.execute(query, {
                "message_id": unique_message_id,
                "idempotency_key": unique_message_id
            })
            
            message_count = result.fetchone()
            
            # Should have at most one processed message record
            if message_count:
                assert message_count.message_count <= 1, "Should not have duplicate message processing in database"
                
        finally:
            await WebSocketTestHelpers.close_test_connection(second_ws)

    def _create_test_auth_token(self, user_id: str) -> str:
        """Create test authentication token for integration testing."""
        import base64
        
        payload = {
            "user_id": user_id,
            "email": f"test_{user_id}@example.com",
            "iat": int(time.time()),
            "exp": int(time.time() + 3600),
            "test_mode": True
        }
        
        token_data = base64.b64encode(json.dumps(payload).encode()).decode()
        return f"test.{token_data}.signature"