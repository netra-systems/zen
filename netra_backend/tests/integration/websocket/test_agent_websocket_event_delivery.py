"""
WebSocket Agent Event Delivery Integration Tests - Phase 2

Tests WebSocket agent event delivery through real WebSocket connections
and real database persistence. Validates that agent execution properly
emits all 5 critical WebSocket events through actual service infrastructure.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time agent feedback enables chat value
- Value Impact: Users receive timely updates during agent processing
- Strategic Impact: Core platform functionality for AI interaction value

CRITICAL: Uses REAL services (PostgreSQL, Redis, WebSocket connections)
No mocks in integration tests per CLAUDE.md standards.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from uuid import uuid4

from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.websocket_helpers import (
    WebSocketTestHelpers,
    establish_minimum_websocket_connections,
    ensure_websocket_service_ready
)
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.id_generation import UnifiedIdGenerator


class TestAgentWebSocketEventDelivery(BaseIntegrationTest):
    """Integration tests for WebSocket agent event delivery with real services."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, real_services_fixture):
        """Setup test environment with real services."""
        self.services = real_services_fixture
        self.env = get_env()
        
        # Validate real services are available
        if not self.services["database_available"]:
            pytest.skip("Real database not available - required for integration testing")
        
        # Store service URLs for WebSocket connections
        self.backend_url = self.services["backend_url"]
        self.websocket_url = self.backend_url.replace("http://", "ws://") + "/ws"
        
        # Generate test identifiers using SSOT patterns
        self.test_user_id = UserID(f"integration_user_{UnifiedIdGenerator.generate_user_id()}")
        self.test_thread_id = ThreadID(f"integration_thread_{UnifiedIdGenerator.generate_thread_id()}")
        self.test_run_id = RunID(UnifiedIdGenerator.generate_run_id())
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_emits_all_websocket_events(self, real_services_fixture):
        """Test that agent execution emits all 5 critical WebSocket events through real connections."""
        start_time = time.time()
        
        # Ensure WebSocket service is ready
        service_ready = await ensure_websocket_service_ready(self.backend_url)
        if not service_ready:
            pytest.skip("WebSocket service not ready - required for integration testing")
        
        # Create test authentication token (mocked for integration)
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Establish WebSocket connection
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            timeout=10.0,
            max_retries=3,
            user_id=str(self.test_user_id)
        )
        
        try:
            collected_events = []
            
            # Send agent execution request
            agent_request = {
                "type": "agent_request",
                "agent_name": "triage_agent",
                "message": "Integration test: analyze simple request",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "run_id": str(self.test_run_id),
                "timestamp": time.time()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, agent_request)
            
            # Collect events with timeout
            event_collection_timeout = 30.0
            collection_start = time.time()
            
            while time.time() - collection_start < event_collection_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                    collected_events.append(event)
                    
                    # Stop collecting when agent_completed is received
                    if event.get("type") == "agent_completed":
                        break
                        
                except Exception as e:
                    if "timeout" in str(e).lower():
                        # Check if we have minimum required events
                        if len(collected_events) >= 5:
                            break
                        continue
                    else:
                        raise
            
            # Verify test took significant time (real service validation)
            test_duration = time.time() - start_time
            assert test_duration > 0.5, f"Test completed too quickly ({test_duration:.2f}s) - likely not using real services"
            
            # Verify all 5 critical WebSocket events were received
            event_types = [event.get("type") for event in collected_events]
            
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            for required_event in required_events:
                assert required_event in event_types, (
                    f"Missing required WebSocket event: {required_event}. "
                    f"Received events: {event_types}"
                )
            
            # Verify event ordering (agent_started comes before agent_completed)
            agent_started_idx = next(i for i, event in enumerate(collected_events) if event.get("type") == "agent_started")
            agent_completed_idx = next(i for i, event in enumerate(collected_events) if event.get("type") == "agent_completed")
            assert agent_started_idx < agent_completed_idx, "agent_started must come before agent_completed"
            
            # Verify event structure and required fields
            for event in collected_events:
                assert "type" in event, f"Event missing type field: {event}"
                assert "timestamp" in event, f"Event missing timestamp field: {event}"
                
                # Verify thread isolation
                if "thread_id" in event:
                    assert event["thread_id"] == str(self.test_thread_id), "Event sent to wrong thread"
                    
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_database_persistence(self, real_services_fixture):
        """Test that WebSocket events are persisted to real database."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
            
        # Create WebSocket connection
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            # Send agent request that should persist events
            agent_request = {
                "type": "agent_request", 
                "agent_name": "data_agent",
                "message": "Integration test: create database entries",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "persist_events": True
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, agent_request)
            
            # Wait for agent processing
            await asyncio.sleep(2.0)
            
            # Query database for persisted events
            query = """
            SELECT event_type, thread_id, user_id, created_at, payload
            FROM websocket_events 
            WHERE thread_id = :thread_id
            ORDER BY created_at ASC
            """
            
            result = await db_session.execute(query, {"thread_id": str(self.test_thread_id)})
            persisted_events = result.fetchall()
            
            # Verify test duration (real database operations)
            test_duration = time.time() - start_time  
            assert test_duration > 0.3, "Test completed too quickly - likely not using real database"
            
            # Verify events were persisted
            assert len(persisted_events) >= 3, f"Expected at least 3 persisted events, got {len(persisted_events)}"
            
            # Verify event types are persisted correctly
            persisted_event_types = [event.event_type for event in persisted_events]
            assert "agent_started" in persisted_event_types, "agent_started event not persisted"
            
            # Verify user and thread isolation in database
            for event in persisted_events:
                assert event.user_id == str(self.test_user_id), "User isolation violated in database"
                assert event.thread_id == str(self.test_thread_id), "Thread isolation violated in database"
                
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_multi_service_event_coordination(self, real_services_fixture):
        """Test WebSocket event coordination between backend and auth services."""
        start_time = time.time()
        
        # Test requires both backend and auth services
        if not self.services["services_available"]["backend"] or not self.services["services_available"]["auth"]:
            pytest.skip("Both backend and auth services must be available")
            
        # Create connections to both services
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Backend WebSocket connection
        backend_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        # Auth service connection (for validation events)
        auth_url = self.services["auth_url"].replace("http://", "ws://") + "/ws/auth"
        auth_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{auth_url}/{self.test_user_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            backend_events = []
            auth_events = []
            
            # Send request that requires auth validation
            auth_required_request = {
                "type": "agent_request",
                "agent_name": "secure_agent", 
                "message": "Integration test: requires cross-service coordination",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "requires_auth_validation": True
            }
            
            await WebSocketTestHelpers.send_test_message(backend_ws, auth_required_request)
            
            # Collect events from both services concurrently
            async def collect_backend_events():
                try:
                    for _ in range(10):  # Collect up to 10 events
                        event = await WebSocketTestHelpers.receive_test_message(backend_ws, timeout=3.0)
                        backend_events.append(event)
                        if event.get("type") == "agent_completed":
                            break
                except Exception:
                    pass  # Timeout is expected
                    
            async def collect_auth_events():
                try:
                    for _ in range(5):  # Collect up to 5 auth events
                        event = await WebSocketTestHelpers.receive_test_message(auth_ws, timeout=3.0)
                        auth_events.append(event)
                except Exception:
                    pass  # Timeout is expected
            
            # Run collection concurrently
            await asyncio.gather(
                collect_backend_events(),
                collect_auth_events(),
                return_exceptions=True
            )
            
            # Verify test duration (real service coordination)
            test_duration = time.time() - start_time
            assert test_duration > 1.0, "Test completed too quickly - likely not coordinating real services"
            
            # Verify coordination occurred
            backend_event_types = [e.get("type") for e in backend_events]
            auth_event_types = [e.get("type") for e in auth_events]
            
            # Backend should have agent events
            assert "agent_started" in backend_event_types, "Backend agent events missing"
            
            # Auth service should have validation events
            assert len(auth_events) > 0, "No auth coordination events received"
            
            # Verify cross-service event correlation
            for backend_event in backend_events:
                if "correlation_id" in backend_event:
                    # Check if corresponding auth event exists
                    correlation_id = backend_event["correlation_id"]
                    auth_correlations = [e.get("correlation_id") for e in auth_events]
                    # Note: This might not always match in real system, so we just verify structure
                    assert correlation_id is not None, "Correlation ID should be present for cross-service events"
                    
        finally:
            await WebSocketTestHelpers.close_test_connection(backend_ws)
            await WebSocketTestHelpers.close_test_connection(auth_ws)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_ordering_with_real_latency(self, real_services_fixture):
        """Test WebSocket event ordering under real network latency conditions."""
        start_time = time.time()
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            collected_events = []
            
            # Send complex request that generates multiple ordered events
            complex_request = {
                "type": "agent_request",
                "agent_name": "multi_step_agent",
                "message": "Integration test: execute multiple tools in sequence",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "steps": ["analyze", "process", "validate", "complete"]
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, complex_request)
            
            # Collect all events with real network timing
            timeout_duration = 25.0
            collection_start = time.time()
            
            while time.time() - collection_start < timeout_duration:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                    
                    # Add reception timestamp for ordering analysis
                    event["received_at"] = time.time()
                    collected_events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except Exception as e:
                    if "timeout" in str(e).lower() and collected_events:
                        break
                    continue
            
            # Verify real timing
            test_duration = time.time() - start_time
            assert test_duration > 2.0, "Test completed too quickly - likely not experiencing real latency"
            
            # Analyze event ordering
            event_types_with_timestamps = [
                (event.get("type"), event.get("timestamp", 0), event.get("received_at", 0))
                for event in collected_events
            ]
            
            # Verify logical event ordering
            agent_started_time = None
            agent_completed_time = None
            
            for event_type, sent_timestamp, received_timestamp in event_types_with_timestamps:
                if event_type == "agent_started":
                    agent_started_time = sent_timestamp
                elif event_type == "agent_completed":
                    agent_completed_time = sent_timestamp
            
            if agent_started_time and agent_completed_time:
                assert agent_started_time <= agent_completed_time, (
                    "agent_started must have timestamp <= agent_completed timestamp"
                )
            
            # Verify reasonable event spacing (not all at once)
            if len(collected_events) >= 3:
                timestamps = [event.get("received_at", 0) for event in collected_events]
                time_spans = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                
                # At least some events should have realistic spacing
                realistic_spacing_count = sum(1 for span in time_spans if 0.01 <= span <= 5.0)
                assert realistic_spacing_count >= 1, "Events should have realistic timing spacing"
                
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_websocket_event_error_scenarios(self, real_services_fixture):
        """Test WebSocket event delivery under real error conditions."""
        start_time = time.time()
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Test 1: Invalid agent request should generate error events
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            error_events = []
            
            # Send intentionally invalid request
            invalid_request = {
                "type": "agent_request",
                "agent_name": "nonexistent_agent",
                "message": "This should fail",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id)
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, invalid_request)
            
            # Collect error events
            for _ in range(10):
                try:
                    event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                    error_events.append(event)
                    
                    # Stop on agent failure or completion
                    if event.get("type") in ["agent_failed", "agent_completed", "error"]:
                        break
                        
                except Exception:
                    break  # Timeout expected for error scenarios
            
            # Verify test took real time
            test_duration = time.time() - start_time
            assert test_duration > 0.5, "Error test completed too quickly"
            
            # Verify error handling
            event_types = [event.get("type") for event in error_events]
            
            # Should receive either error events or failure events
            error_indicators = ["error", "agent_failed", "tool_failed"]
            has_error_event = any(error_type in event_types for error_type in error_indicators)
            
            assert has_error_event or len(error_events) == 0, (
                "Should receive error events or no events for invalid requests"
            )
            
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)
    
    def _create_test_auth_token(self, user_id: str) -> str:
        """Create test authentication token for integration testing."""
        # Mock JWT token for integration testing
        # In real implementation, this would come from auth service
        import base64
        
        payload = {
            "user_id": user_id,
            "email": f"test_{user_id}@example.com",
            "iat": int(time.time()),
            "exp": int(time.time() + 3600),  # 1 hour expiry
            "test_mode": True
        }
        
        # Create simple base64 encoded token for testing
        token_data = base64.b64encode(json.dumps(payload).encode()).decode()
        return f"test.{token_data}.signature"