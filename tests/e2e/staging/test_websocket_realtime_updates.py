"""
Test WebSocket Real-Time Updates E2E

Business Value Justification (BVJ):
- Segment: All (Real-time updates critical for user experience across all tiers)
- Business Goal: Ensure users receive timely, real-time updates during agent execution
- Value Impact: Users see immediate feedback, progress updates, and results as they happen
- Strategic Impact: Real-time experience differentiates platform from batch-processing competitors

CRITICAL AUTHENTICATION REQUIREMENT:
ALL tests MUST use authentication to ensure WebSocket connections are properly secured
and associated with authenticated user sessions.

CRITICAL WEBSOCKET REQUIREMENTS:
- Event Delivery Pipeline: All 5 critical events must be delivered reliably
- Real-Time Updates: Events delivered within seconds of generation
- Message Ordering: Events arrive in correct sequence
- Connection Recovery: Handles connection drops gracefully
- Event Validation: Each event contains required data and proper formatting
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import websockets

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from tests.e2e.staging_config import get_staging_config


class TestWebSocketRealTimeUpdates(BaseE2ETest):
    """Test WebSocket real-time updates and event delivery pipeline."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment="staging")
        
    async def collect_events_with_timing(self, websocket, timeout: float = 60.0) -> List[Dict]:
        """Collect events with precise timing information."""
        events = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                event_str = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                receive_time = time.time()
                
                event = json.loads(event_str)
                event["_receive_time"] = receive_time
                event["_elapsed_time"] = receive_time - start_time
                events.append(event)
                
                if event["type"] == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                # Log timeout for debugging
                elapsed = time.time() - start_time
                self.logger.warning(f"⏱️ WebSocket receive timeout after {elapsed:.1f}s")
                break
                
        return events
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_complete_event_delivery_pipeline(self, real_services, real_llm):
        """Test complete WebSocket event delivery pipeline with all 5 critical events."""
        self.logger.info("🚀 Starting Complete Event Delivery Pipeline E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"event-pipeline-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            # Connect WebSocket with authentication
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers,
                    open_timeout=20.0
                ),
                timeout=25.0
            )
            
            self.logger.info("✅ WebSocket connected for event pipeline test")
            
            # Send agent request that will trigger all event types
            agent_request = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Perform comprehensive cost analysis with detailed breakdown",
                "context": {
                    "user_id": user_data["id"],
                    "analysis_depth": "comprehensive",
                    "require_tools": True,  # Ensure tool execution events
                    "test_scenario": "event_pipeline_validation"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            request_sent_time = time.time()
            await websocket.send(json.dumps(agent_request))
            self.logger.info("📤 Agent request sent for event pipeline test")
            
            # Collect all events with timing
            events = await self.collect_events_with_timing(websocket, timeout=120.0)
            
            await websocket.close()
            
            # CRITICAL: Validate all 5 required events are present
            event_types = [e["type"] for e in events]
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            missing_events = []
            for event_type in required_events:
                if event_type not in event_types:
                    missing_events.append(event_type)
            
            assert len(missing_events) == 0, f"Missing critical events: {missing_events}"
            
            # Validate event timing - events should arrive within reasonable time
            first_event_time = events[0]["_elapsed_time"] if events else float('inf')
            last_event_time = events[-1]["_elapsed_time"] if events else 0
            
            assert first_event_time < 10.0, f"First event took too long: {first_event_time:.1f}s"
            assert last_event_time < 120.0, f"Agent completion took too long: {last_event_time:.1f}s"
            
            # Validate event ordering
            agent_started_idx = next((i for i, e in enumerate(events) if e["type"] == "agent_started"), None)
            agent_completed_idx = next((i for i, e in enumerate(events) if e["type"] == "agent_completed"), None)
            
            assert agent_started_idx is not None, "agent_started event not found"
            assert agent_completed_idx is not None, "agent_completed event not found"
            assert agent_started_idx < agent_completed_idx, "Events should be in correct order"
            
            # Validate event content
            agent_started_event = events[agent_started_idx]
            assert "data" in agent_started_event, "agent_started should have data"
            assert "timestamp" in agent_started_event["data"], "Events should have timestamps"
            
            agent_completed_event = events[agent_completed_idx]
            assert "data" in agent_completed_event, "agent_completed should have data"
            assert "result" in agent_completed_event["data"], "agent_completed should have result"
            
            self.logger.info(f"✅ Event Pipeline Test - All 5 events delivered in {last_event_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f"❌ Event Delivery Pipeline test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_websocket_connection_recovery(self, real_services):
        """Test WebSocket connection recovery and reconnection scenarios."""
        self.logger.info("🚀 Starting WebSocket Connection Recovery E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"connection-recovery-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        # Test initial connection
        websocket1 = await websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=websocket_headers
        )
        
        # Send initial request
        initial_request = {
            "type": "agent_request",
            "agent": "triage_agent",
            "message": "Initial request before connection test",
            "context": {"user_id": user_data["id"], "phase": "initial"}
        }
        
        await websocket1.send(json.dumps(initial_request))
        
        # Wait for some events
        initial_events = []
        for _ in range(2):  # Get a couple events
            try:
                event_str = await asyncio.wait_for(websocket1.recv(), timeout=10.0)
                event = json.loads(event_str)
                initial_events.append(event)
            except asyncio.TimeoutError:
                break
        
        # Simulate connection drop
        await websocket1.close()
        self.logger.info("🔄 Simulated connection drop")
        
        # Wait brief moment
        await asyncio.sleep(2)
        
        # Reconnect with same authentication
        websocket2 = await websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=websocket_headers
        )
        
        self.logger.info("✅ Reconnected after simulated drop")
        
        # Send new request after reconnection
        recovery_request = {
            "type": "agent_request",
            "agent": "triage_agent", 
            "message": "Request after reconnection",
            "context": {"user_id": user_data["id"], "phase": "recovery"}
        }
        
        await websocket2.send(json.dumps(recovery_request))
        
        # Collect events from reconnected session
        recovery_events = []
        start_time = time.time()
        
        while time.time() - start_time < 30:
            try:
                event_str = await asyncio.wait_for(websocket2.recv(), timeout=8.0)
                event = json.loads(event_str)
                recovery_events.append(event)
                
                if event["type"] == "agent_completed":
                    break
            except asyncio.TimeoutError:
                break
        
        await websocket2.close()
        
        # Validate recovery
        recovery_event_types = [e["type"] for e in recovery_events]
        assert "agent_started" in recovery_event_types, "Reconnection should work"
        assert "agent_completed" in recovery_event_types, "Agent should complete after reconnection"
        
        # Validate we got different sessions
        initial_has_events = len(initial_events) > 0
        recovery_has_events = len(recovery_events) > 0
        assert initial_has_events and recovery_has_events, "Both sessions should have events"
        
        self.logger.info("✅ WebSocket Connection Recovery Test completed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_realtime_agent_status_updates(self, real_services, real_llm):
        """Test real-time agent status updates during execution."""
        self.logger.info("🚀 Starting Real-Time Agent Status Updates E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"status-updates-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await websockets.connect(
                self.staging_config.urls.websocket_url,
                additional_headers=websocket_headers
            )
            
            # Send request that should generate multiple status updates
            agent_request = {
                "type": "agent_request",
                "agent": "data_analysis",
                "message": "Perform multi-step analysis with status reporting",
                "context": {
                    "user_id": user_data["id"],
                    "steps": ["data_collection", "analysis", "visualization", "recommendations"],
                    "report_progress": True
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Track status updates specifically
            events = []
            status_updates = []
            thinking_events = []
            start_time = time.time()
            
            while time.time() - start_time < 90:
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    # Track different types of status updates
                    if event["type"] == "agent_thinking":
                        thinking_events.append(event)
                        if "status" in event.get("data", {}):
                            status_updates.append(event["data"]["status"])
                    
                    if event["type"] == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate real-time status updates
            event_types = [e["type"] for e in events]
            
            # Should have multiple thinking events showing progress
            assert len(thinking_events) >= 2, "Should have multiple agent_thinking events for status updates"
            
            # Should have standard completion
            assert "agent_completed" in event_types, "Should complete successfully"
            
            # Validate timing - status updates should be spread over time
            if len(thinking_events) >= 2:
                first_thinking = next(e for e in events if e["type"] == "agent_thinking")["_elapsed_time"]
                last_thinking = next(e for e in reversed(events) if e["type"] == "agent_thinking")["_elapsed_time"]
                
                time_spread = last_thinking - first_thinking
                assert time_spread > 5.0, "Status updates should be spread over time, not all at once"
            
            self.logger.info(f"✅ Real-Time Status Updates - {len(thinking_events)} status events")
            
        except Exception as e:
            self.logger.error(f"❌ Real-Time Status Updates test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_message_ordering_and_consistency(self, real_services):
        """Test WebSocket message ordering and consistency."""
        self.logger.info("🚀 Starting Message Ordering and Consistency E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"message-ordering-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await websockets.connect(
                self.staging_config.urls.websocket_url,
                additional_headers=websocket_headers
            )
            
            # Send multiple requests in sequence to test ordering
            requests = [
                {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Sequential request {i+1}",
                    "context": {
                        "user_id": user_data["id"],
                        "sequence": i+1,
                        "request_id": f"order-test-{i+1}"
                    }
                }
                for i in range(3)
            ]
            
            # Send all requests with small delays
            request_times = []
            for i, request in enumerate(requests):
                send_time = time.time()
                await websocket.send(json.dumps(request))
                request_times.append(send_time)
                self.logger.info(f"📤 Sent request {i+1}")
                await asyncio.sleep(2)  # Small delay between requests
            
            # Collect all events maintaining order
            all_events = []
            start_time = time.time()
            completed_agents = 0
            
            while time.time() - start_time < 60 and completed_agents < 3:
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_str)
                    event["_receive_order"] = len(all_events)
                    all_events.append(event)
                    
                    if event["type"] == "agent_completed":
                        completed_agents += 1
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate message ordering
            agent_started_events = [e for e in all_events if e["type"] == "agent_started"]
            agent_completed_events = [e for e in all_events if e["type"] == "agent_completed"]
            
            # Should have started and completed events for each request
            assert len(agent_started_events) >= 1, "Should have agent_started events"
            assert len(agent_completed_events) >= 1, "Should have agent_completed events"
            
            # For each agent, started should come before completed
            for i, started_event in enumerate(agent_started_events):
                started_order = started_event["_receive_order"]
                
                # Find corresponding completed event
                completed_events_after = [
                    e for e in agent_completed_events 
                    if e["_receive_order"] > started_order
                ]
                
                assert len(completed_events_after) > 0, f"No completion event found after start event {i}"
            
            # Validate event consistency
            event_types = [e["type"] for e in all_events]
            required_types = ["agent_started", "agent_completed"]
            
            for req_type in required_types:
                assert req_type in event_types, f"Missing {req_type} in event sequence"
            
            self.logger.info(f"✅ Message Ordering Test - {len(all_events)} events in correct order")
            
        except Exception as e:
            self.logger.error(f"❌ Message Ordering test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_connection_scaling_under_load(self, real_services):
        """Test WebSocket connection scaling with multiple concurrent connections."""
        self.logger.info("🚀 Starting Connection Scaling Under Load E2E Test")
        
        # Create multiple users for load testing
        num_users = 3  # Conservative for staging environment
        users = []
        for i in range(num_users):
            token, user_data = await create_authenticated_user(
                environment="staging",
                email=f"load-test-{i}-{uuid.uuid4().hex[:6]}@staging.netrasystems.ai"
            )
            users.append((token, user_data))
        
        async def run_concurrent_websocket_session(user_idx: int, token: str, user_data: Dict):
            """Run a WebSocket session for load testing."""
            session_id = f"load-{user_idx}"
            
            try:
                websocket_headers = self.auth_helper.get_websocket_headers(token)
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.staging_config.urls.websocket_url,
                        additional_headers=websocket_headers,
                        open_timeout=20.0
                    ),
                    timeout=25.0
                )
                
                # Send load test request
                load_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Load test request from user {user_idx}",
                    "context": {
                        "user_id": user_data["id"],
                        "session_id": session_id,
                        "load_test": True
                    }
                }
                
                request_start = time.time()
                await websocket.send(json.dumps(load_request))
                
                # Collect events for this session
                events = []
                while time.time() - request_start < 45:
                    try:
                        event_str = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event = json.loads(event_str)
                        events.append(event)
                        
                        if event["type"] == "agent_completed":
                            break
                    except asyncio.TimeoutError:
                        break
                
                await websocket.close()
                
                # Validate session results
                event_types = [e["type"] for e in events]
                success = "agent_completed" in event_types
                
                return {
                    "user_idx": user_idx,
                    "session_id": session_id,
                    "success": success,
                    "events": len(events),
                    "duration": time.time() - request_start
                }
                
            except Exception as e:
                return {
                    "user_idx": user_idx,
                    "session_id": session_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Run all sessions concurrently
        start_time = time.time()
        tasks = [
            run_concurrent_websocket_session(i, token, user_data) 
            for i, (token, user_data) in enumerate(users)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Validate load handling
        successful_sessions = [
            r for r in results 
            if not isinstance(r, Exception) and r.get("success", False)
        ]
        
        success_rate = len(successful_sessions) / num_users
        assert success_rate >= 0.8, f"Load test failed - only {success_rate*100:.1f}% success rate"
        
        # Validate reasonable performance under load
        avg_duration = sum(s["duration"] for s in successful_sessions) / len(successful_sessions)
        assert avg_duration < 60.0, f"Average session duration too high under load: {avg_duration:.1f}s"
        
        total_events = sum(s["events"] for s in successful_sessions)
        
        self.logger.info(f"✅ Connection Scaling Test - {len(successful_sessions)}/{num_users} sessions successful")
        self.logger.info(f"📊 Load Test Stats - {total_events} total events, {avg_duration:.1f}s avg duration")
        
    async def teardown_method(self):
        """Cleanup after each test method."""
        await super().cleanup_resources()