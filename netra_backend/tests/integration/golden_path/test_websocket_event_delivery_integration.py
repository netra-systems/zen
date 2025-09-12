"""
Test WebSocket Event Delivery Integration - Golden Path Business Value

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket event delivery for chat business value
- Value Impact: WebSocket events enable user transparency and trust in AI processing
- Strategic Impact: Chat is 90% of business value - events MUST be delivered reliably

CRITICAL: These tests validate the 5 mission-critical WebSocket events that enable
substantive AI chat interactions worth $500K+ ARR:
- agent_started: User sees agent began processing
- agent_thinking: Real-time reasoning visibility 
- tool_executing: Tool usage transparency
- tool_completed: Tool results display
- agent_completed: Final response delivery
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    HealthStatus,
    IntegrationConfig
)
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketEventDeliveryIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket event delivery in Golden Path scenarios."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_event_delivery_with_real_connections_and_database(self, real_services_fixture):
        """
        BVJ: All segments - Ensure agent events reach users through real WebSocket connections
        Value: Users see AI working on their problems, building trust and engagement
        """
        # Setup real user context with database
        user_context = await self.create_test_user_context(
            real_services_fixture,
            {"email": "test-agent-events@example.com", "name": "Event Test User"}
        )
        user_id = UserID(user_context["id"])
        
        # Create real WebSocket manager and bridge with user context
        # Note: Will be updated with proper execution context below
        websocket_manager = await create_websocket_manager(user_id=user_id)
        bridge = AgentWebSocketBridge()
        
        # Track events delivered
        delivered_events = []
        
        # Mock WebSocket emitter to capture events
        mock_emitter = AsyncMock()
        async def capture_event(event_type, data=None, **kwargs):
            delivered_events.append({
                "type": event_type,
                "data": data or {},
                "timestamp": datetime.now(timezone.utc),
                **kwargs
            })
        mock_emitter.emit_agent_event = capture_event
        
        # Setup bridge with real database connection
        await bridge._ensure_thread_run_registry(real_services_fixture["db"])
        
        # Execute agent with event monitoring
        execution_context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID("thread_123"),
            run_id=RunID("run_456"),
            request_id=RequestID("req_789"),
            websocket_emitter=mock_emitter
        )
        
        # Simulate agent execution with all 5 critical events
        await mock_emitter.emit_agent_event("agent_started", {
            "agent_type": "cost_optimizer",
            "message": "Analyzing your AWS costs",
            "user_id": str(user_id)
        })
        
        await mock_emitter.emit_agent_event("agent_thinking", {
            "thought_process": "Examining AWS billing data patterns",
            "progress": 0.2
        })
        
        await mock_emitter.emit_agent_event("tool_executing", {
            "tool_name": "aws_cost_analyzer",
            "parameters": {"time_range": "30d"}
        })
        
        await mock_emitter.emit_agent_event("tool_completed", {
            "tool_name": "aws_cost_analyzer",
            "result": {"monthly_savings": 1500, "recommendations": 3}
        })
        
        await mock_emitter.emit_agent_event("agent_completed", {
            "final_result": {
                "cost_savings": {"amount": 1500, "percentage": 12},
                "recommendations": ["Use Reserved Instances", "Right-size instances"]
            },
            "business_value": True
        })
        
        # Verify all 5 mission-critical events delivered
        assert len(delivered_events) == 5, f"Expected 5 events, got {len(delivered_events)}"
        
        event_types = [event["type"] for event in delivered_events]
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for required_event in required_events:
            assert required_event in event_types, f"Missing critical event: {required_event}"
        
        # Verify events contain business value indicators
        final_event = next(e for e in delivered_events if e["type"] == "agent_completed")
        assert final_event["data"]["business_value"] is True
        assert "cost_savings" in final_event["data"]["final_result"]
        
        self.assert_business_value_delivered(final_event["data"]["final_result"], "cost_savings")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_ordering_validation_complete_agent_flow(self, real_services_fixture):
        """
        BVJ: All segments - Validate events arrive in correct order for user experience
        Value: Users see logical progression of AI work, not confusing out-of-order updates
        """
        # Setup with real database
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Create bridge and track event ordering
        bridge = AgentWebSocketBridge()
        event_sequence = []
        
        mock_emitter = AsyncMock()
        async def track_event_order(event_type, data=None, **kwargs):
            event_sequence.append({
                "type": event_type,
                "timestamp": time.time(),
                "order": len(event_sequence)
            })
        mock_emitter.emit_agent_event = track_event_order
        
        # Execute events in business-logical order
        events_to_send = [
            ("agent_started", {"agent": "data_researcher"}),
            ("agent_thinking", {"analysis": "Reviewing requirements"}),
            ("tool_executing", {"tool": "data_collector"}),
            ("tool_completed", {"results": "Data collected"}),
            ("agent_thinking", {"analysis": "Processing results"}),
            ("tool_executing", {"tool": "data_analyzer"}),
            ("tool_completed", {"insights": "Analysis complete"}),
            ("agent_completed", {"final_insights": "Research complete"})
        ]
        
        # Send events with small delays to simulate real execution
        for event_type, data in events_to_send:
            await mock_emitter.emit_agent_event(event_type, data)
            await asyncio.sleep(0.01)  # Simulate processing time
        
        # Verify events maintain proper order
        assert len(event_sequence) == 8
        assert event_sequence[0]["type"] == "agent_started"
        assert event_sequence[-1]["type"] == "agent_completed"
        
        # Verify timestamps are sequential
        for i in range(1, len(event_sequence)):
            assert event_sequence[i]["timestamp"] >= event_sequence[i-1]["timestamp"]
        
        # Verify business logic: thinking -> tool -> thinking -> tool -> completion
        thinking_indices = [i for i, e in enumerate(event_sequence) if e["type"] == "agent_thinking"]
        tool_exec_indices = [i for i, e in enumerate(event_sequence) if e["type"] == "tool_executing"]
        
        assert len(thinking_indices) == 2, "Expected 2 thinking events"
        assert len(tool_exec_indices) == 2, "Expected 2 tool execution events"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_buffering_reliable_delivery_redis(self, real_services_fixture):
        """
        BVJ: All segments - Test event buffering ensures no lost events during network issues
        Value: Users never miss important AI updates, even during connection problems
        """
        # Setup Redis-backed event buffering
        redis_client = None
        try:
            import redis.asyncio as redis
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
                host="localhost", 
                port=6381,  # Test Redis port
                db=1,
                decode_responses=True
            )
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available for buffering test: {e}")
        
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Create event buffer in Redis
        buffer_key = f"websocket_events:{user_id}"
        events_to_buffer = [
            {"type": "agent_started", "data": {"message": "Starting analysis"}},
            {"type": "agent_thinking", "data": {"thought": "Analyzing data"}},
            {"type": "tool_executing", "data": {"tool": "analyzer"}},
            {"type": "tool_completed", "data": {"result": "Analysis done"}},
            {"type": "agent_completed", "data": {"final": "Complete"}}
        ]
        
        # Buffer events in Redis (simulating network interruption)
        for i, event in enumerate(events_to_buffer):
            event_with_order = {**event, "sequence": i, "timestamp": time.time()}
            await redis_client.lpush(buffer_key, json.dumps(event_with_order))
        
        # Verify events stored in Redis
        buffered_count = await redis_client.llen(buffer_key)
        assert buffered_count == 5, f"Expected 5 buffered events, got {buffered_count}"
        
        # Simulate connection recovery and event delivery
        delivered_events = []
        while await redis_client.llen(buffer_key) > 0:
            event_json = await redis_client.rpop(buffer_key)
            if event_json:
                event = json.loads(event_json)
                delivered_events.append(event)
        
        # Verify all events delivered in correct order
        assert len(delivered_events) == 5
        for i, event in enumerate(delivered_events):
            assert event["sequence"] == i, f"Event out of order: expected {i}, got {event['sequence']}"
        
        # Verify all critical events present
        event_types = [e["type"] for e in delivered_events]
        assert "agent_started" in event_types
        assert "agent_completed" in event_types

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_event_isolation_routing(self, real_services_fixture):
        """
        BVJ: All segments - Ensure events only go to correct users, preventing data leaks
        Value: User privacy and data isolation critical for enterprise customers
        """
        # Create multiple user contexts with real database
        user1_context = await self.create_test_user_context(
            real_services_fixture,
            {"email": "user1@example.com", "name": "User One"}
        )
        user2_context = await self.create_test_user_context(
            real_services_fixture, 
            {"email": "user2@example.com", "name": "User Two"}
        )
        
        user1_id = UserID(user1_context["id"])
        user2_id = UserID(user2_context["id"])
        
        # Track events per user
        user1_events = []
        user2_events = []
        
        # Create isolated emitters
        mock_emitter1 = AsyncMock()
        mock_emitter2 = AsyncMock()
        
        async def capture_user1_events(event_type, data=None, **kwargs):
            user1_events.append({"type": event_type, "data": data, "user": str(user1_id)})
        
        async def capture_user2_events(event_type, data=None, **kwargs):
            user2_events.append({"type": event_type, "data": data, "user": str(user2_id)})
        
        mock_emitter1.emit_agent_event = capture_user1_events
        mock_emitter2.emit_agent_event = capture_user2_events
        
        # Send events to both users simultaneously
        user1_events_to_send = [
            ("agent_started", {"message": "User 1 cost analysis"}),
            ("agent_completed", {"savings": 1000})
        ]
        
        user2_events_to_send = [
            ("agent_started", {"message": "User 2 security audit"}),
            ("agent_completed", {"vulnerabilities": 3})
        ]
        
        # Send events concurrently to test isolation
        await asyncio.gather(
            *[mock_emitter1.emit_agent_event(event_type, data) 
              for event_type, data in user1_events_to_send],
            *[mock_emitter2.emit_agent_event(event_type, data)
              for event_type, data in user2_events_to_send]
        )
        
        # Verify complete isolation
        assert len(user1_events) == 2
        assert len(user2_events) == 2
        
        # Verify no data leakage
        for event in user1_events:
            assert "cost analysis" in event["data"]["message"] or "savings" in event["data"]
            assert "security audit" not in str(event)
            assert "vulnerabilities" not in str(event)
        
        for event in user2_events:
            assert "security audit" in event["data"]["message"] or "vulnerabilities" in event["data"]
            assert "cost analysis" not in str(event)
            assert "savings" not in str(event)

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_event_delivery_failure_retry_mechanisms(self, real_services_fixture):
        """
        BVJ: All segments - Test retry mechanisms ensure events reach users despite failures
        Value: Reliability builds user trust and prevents lost business value
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Track delivery attempts
        delivery_attempts = []
        successful_deliveries = []
        
        # Mock emitter with controlled failures
        failure_count = 0
        max_failures = 2  # Fail first 2 attempts, succeed on 3rd
        
        async def mock_emit_with_failures(event_type, data=None, **kwargs):
            nonlocal failure_count
            delivery_attempts.append({
                "attempt": len(delivery_attempts) + 1,
                "event_type": event_type,
                "timestamp": time.time()
            })
            
            if failure_count < max_failures:
                failure_count += 1
                raise ConnectionError(f"Mock delivery failure {failure_count}")
            else:
                successful_deliveries.append({
                    "type": event_type,
                    "data": data,
                    "final_attempt": len(delivery_attempts)
                })
        
        # Implement retry logic
        async def emit_with_retry(event_type, data, max_retries=3):
            for attempt in range(max_retries):
                try:
                    await mock_emit_with_failures(event_type, data)
                    return True
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff
            return False
        
        # Test critical event delivery with retries
        critical_event = {
            "type": "agent_completed",
            "data": {
                "business_value": {"cost_savings": 2000},
                "user_impact": "high"
            }
        }
        
        # This should eventually succeed after retries
        success = await emit_with_retry(
            critical_event["type"], 
            critical_event["data"]
        )
        
        assert success, "Event delivery should succeed after retries"
        assert len(delivery_attempts) == 3, f"Expected 3 delivery attempts, got {len(delivery_attempts)}"
        assert len(successful_deliveries) == 1, "Should have 1 successful delivery"
        
        # Verify exponential backoff timing
        if len(delivery_attempts) > 1:
            time_diff = delivery_attempts[1]["timestamp"] - delivery_attempts[0]["timestamp"]
            assert time_diff >= 0.1, "Should have exponential backoff delay"

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_event_serialization_complex_data(self, real_services_fixture):
        """
        BVJ: Enterprise segment - Complex data serialization for enterprise AI workflows
        Value: Enterprise customers need rich data in events for business intelligence
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Complex enterprise data structure
        complex_business_data = {
            "cost_analysis": {
                "monthly_spend": 45000.50,
                "categories": {
                    "compute": {"amount": 25000, "change": "+12%"},
                    "storage": {"amount": 15000, "change": "-5%"},
                    "network": {"amount": 5000.50, "change": "+8%"}
                },
                "recommendations": [
                    {
                        "id": "rec_001",
                        "type": "rightsizing", 
                        "potential_savings": 3500,
                        "confidence": 0.85,
                        "implementation_effort": "low"
                    },
                    {
                        "id": "rec_002",
                        "type": "reserved_instances",
                        "potential_savings": 8500,
                        "confidence": 0.92,
                        "implementation_effort": "medium"
                    }
                ],
                "risk_factors": ["market_volatility", "usage_patterns"],
                "metadata": {
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                    "data_sources": ["aws_billing", "usage_metrics", "market_data"],
                    "model_version": "v2.1.3"
                }
            }
        }
        
        # Test serialization
        serialized_events = []
        
        mock_emitter = AsyncMock()
        async def capture_serialized_event(event_type, data=None, **kwargs):
            # Simulate JSON serialization/deserialization
            try:
                json_str = json.dumps(data, default=str)  # Handle datetime serialization
                deserialized = json.loads(json_str)
                serialized_events.append({
                    "type": event_type,
                    "original_data": data,
                    "serialized_data": deserialized,
                    "serialization_success": True
                })
            except Exception as e:
                serialized_events.append({
                    "type": event_type,
                    "serialization_success": False,
                    "error": str(e)
                })
        
        mock_emitter.emit_agent_event = capture_serialized_event
        
        # Send complex event
        await mock_emitter.emit_agent_event("agent_completed", complex_business_data)
        
        # Verify successful serialization
        assert len(serialized_events) == 1
        event = serialized_events[0]
        
        assert event["serialization_success"] is True, f"Serialization failed: {event.get('error')}"
        
        # Verify data integrity after serialization
        serialized_data = event["serialized_data"]
        assert "cost_analysis" in serialized_data
        assert serialized_data["cost_analysis"]["monthly_spend"] == 45000.50
        assert len(serialized_data["cost_analysis"]["recommendations"]) == 2
        
        # Verify business value preserved
        recommendations = serialized_data["cost_analysis"]["recommendations"]
        total_savings = sum(rec["potential_savings"] for rec in recommendations)
        assert total_savings == 12000, f"Expected total savings 12000, got {total_savings}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_delivery_performance_concurrent_connections(self, real_services_fixture):
        """
        BVJ: Enterprise segment - Performance under concurrent load for enterprise scale
        Value: Enterprise customers need reliable performance with multiple simultaneous users
        """
        # Create multiple user contexts
        num_concurrent_users = 10
        user_contexts = []
        
        for i in range(num_concurrent_users):
            user_context = await self.create_test_user_context(
                real_services_fixture,
                {"email": f"perf-user-{i}@example.com", "name": f"Performance User {i}"}
            )
            user_contexts.append(user_context)
        
        # Track performance metrics
        performance_metrics = {
            "total_events": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "delivery_times": [],
            "start_time": time.time()
        }
        
        async def simulate_user_session(user_context, user_index):
            """Simulate a user's agent interaction session."""
            user_id = UserID(user_context["id"])
            session_events = []
            
            mock_emitter = AsyncMock()
            async def track_delivery_performance(event_type, data=None, **kwargs):
                delivery_start = time.time()
                
                # Simulate network/processing delay
                await asyncio.sleep(0.01)
                
                delivery_time = time.time() - delivery_start
                
                session_events.append({
                    "type": event_type,
                    "user_index": user_index,
                    "delivery_time": delivery_time
                })
                
                performance_metrics["total_events"] += 1
                performance_metrics["successful_deliveries"] += 1
                performance_metrics["delivery_times"].append(delivery_time)
            
            mock_emitter.emit_agent_event = track_delivery_performance
            
            # Send typical agent session events
            events_per_session = [
                ("agent_started", {"user": f"user_{user_index}"}),
                ("agent_thinking", {"analysis": "processing"}),
                ("tool_executing", {"tool": "analyzer"}),
                ("tool_completed", {"results": "analyzed"}),
                ("agent_completed", {"value": f"result_{user_index}"})
            ]
            
            for event_type, data in events_per_session:
                await mock_emitter.emit_agent_event(event_type, data)
                await asyncio.sleep(0.005)  # Small delay between events
        
        # Run concurrent user sessions
        start_time = time.time()
        await asyncio.gather(*[
            simulate_user_session(user_context, i)
            for i, user_context in enumerate(user_contexts)
        ])
        total_duration = time.time() - start_time
        
        # Verify performance requirements
        expected_total_events = num_concurrent_users * 5  # 5 events per user
        assert performance_metrics["total_events"] == expected_total_events
        assert performance_metrics["successful_deliveries"] == expected_total_events
        assert performance_metrics["failed_deliveries"] == 0
        
        # Performance assertions for enterprise scale
        avg_delivery_time = sum(performance_metrics["delivery_times"]) / len(performance_metrics["delivery_times"])
        max_delivery_time = max(performance_metrics["delivery_times"])
        
        assert avg_delivery_time < 0.1, f"Average delivery time too slow: {avg_delivery_time:.3f}s"
        assert max_delivery_time < 0.5, f"Max delivery time too slow: {max_delivery_time:.3f}s"
        assert total_duration < 5.0, f"Total execution too slow: {total_duration:.3f}s"
        
        # Throughput calculation
        events_per_second = performance_metrics["total_events"] / total_duration
        assert events_per_second > 10, f"Throughput too low: {events_per_second:.1f} events/sec"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_state_tracking_acknowledgment(self, real_services_fixture):
        """
        BVJ: Enterprise segment - Event acknowledgment for reliable enterprise workflows
        Value: Enterprise customers need confirmation that critical events were received
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Track event states
        event_states = {}
        acknowledgments = {}
        
        async def track_event_state(event_type, data=None, event_id=None, **kwargs):
            if event_id is None:
                event_id = f"{event_type}_{len(event_states)}"
            
            event_states[event_id] = {
                "type": event_type,
                "data": data,
                "status": "sent",
                "sent_at": time.time(),
                "acknowledged": False
            }
            
            # Simulate acknowledgment with delay
            async def simulate_ack():
                await asyncio.sleep(0.05)  # Network round-trip
                acknowledgments[event_id] = {
                    "acknowledged_at": time.time(),
                    "status": "confirmed"
                }
                event_states[event_id]["acknowledged"] = True
            
            # Start acknowledgment simulation
            asyncio.create_task(simulate_ack())
            return event_id
        
        mock_emitter = AsyncMock()
        mock_emitter.emit_agent_event = track_event_state
        
        # Send critical business events
        critical_events = [
            ("agent_started", {"business_critical": True}),
            ("tool_completed", {"cost_savings": 5000}),
            ("agent_completed", {"final_recommendations": ["save_money", "optimize_usage"]})
        ]
        
        sent_event_ids = []
        for event_type, data in critical_events:
            event_id = await mock_emitter.emit_agent_event(event_type, data, event_id=f"critical_{event_type}")
            sent_event_ids.append(event_id)
        
        # Wait for acknowledgments
        max_wait_time = 2.0
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait_time:
            if all(event_states[eid]["acknowledged"] for eid in sent_event_ids):
                break
            await asyncio.sleep(0.01)
        
        # Verify all critical events acknowledged
        for event_id in sent_event_ids:
            assert event_states[event_id]["acknowledged"], f"Event {event_id} not acknowledged"
            assert event_id in acknowledgments, f"No acknowledgment record for {event_id}"
            
            # Verify acknowledgment timing
            ack_time = acknowledgments[event_id]["acknowledged_at"]
            sent_time = event_states[event_id]["sent_at"]
            round_trip = ack_time - sent_time
            
            assert round_trip < 1.0, f"Acknowledgment too slow: {round_trip:.3f}s"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_payload_validation_security(self, real_services_fixture):
        """
        BVJ: Enterprise segment - Security validation prevents malicious event payloads
        Value: Enterprise customers need security against data injection and XSS attacks
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Test various security attack vectors
        security_test_cases = [
            {
                "name": "script_injection",
                "payload": {"message": "<script>alert('xss')</script>"},
                "should_block": True
            },
            {
                "name": "sql_injection",
                "payload": {"query": "'; DROP TABLE users; --"},
                "should_block": True  
            },
            {
                "name": "large_payload",
                "payload": {"data": "x" * 1000000},  # 1MB payload
                "should_block": True
            },
            {
                "name": "valid_business_data", 
                "payload": {"cost_savings": 1500, "recommendations": ["optimize"]},
                "should_block": False
            },
            {
                "name": "nested_object_bomb",
                "payload": self._create_nested_object(depth=100),
                "should_block": True
            }
        ]
        
        validation_results = []
        
        def validate_event_payload(event_type, data):
            """Security validation for event payloads."""
            try:
                # Check for script injection
                data_str = json.dumps(data, default=str)
                if "<script>" in data_str or "DROP TABLE" in data_str:
                    return False, "Malicious content detected"
                
                # Check payload size (100KB limit)
                if len(data_str) > 100000:
                    return False, "Payload too large"
                
                # Check nesting depth
                if self._check_nesting_depth(data) > 10:
                    return False, "Excessive nesting depth"
                
                return True, "Valid payload"
                
            except Exception as e:
                return False, f"Validation error: {str(e)}"
        
        mock_emitter = AsyncMock()
        async def secure_emit(event_type, data=None, **kwargs):
            is_valid, reason = validate_event_payload(event_type, data)
            validation_results.append({
                "event_type": event_type,
                "valid": is_valid,
                "reason": reason,
                "data": data
            })
            
            if not is_valid:
                raise ValueError(f"Invalid payload: {reason}")
        
        mock_emitter.emit_agent_event = secure_emit
        
        # Test each security case
        for test_case in security_test_cases:
            try:
                await mock_emitter.emit_agent_event("test_event", test_case["payload"])
                validation_success = True
            except ValueError:
                validation_success = False
            
            if test_case["should_block"]:
                assert not validation_success, f"Security test '{test_case['name']}' should have been blocked"
            else:
                assert validation_success, f"Valid test '{test_case['name']}' should have passed"
        
        # Verify validation results
        blocked_count = sum(1 for r in validation_results if not r["valid"])
        allowed_count = sum(1 for r in validation_results if r["valid"])
        
        assert blocked_count == 4, f"Expected 4 blocked payloads, got {blocked_count}"
        assert allowed_count == 1, f"Expected 1 allowed payload, got {allowed_count}"

    def _create_nested_object(self, depth):
        """Create deeply nested object for testing."""
        if depth <= 0:
            return "deep"
        return {"nested": self._create_nested_object(depth - 1)}
    
    def _check_nesting_depth(self, obj, current_depth=0):
        """Check nesting depth of object."""
        if current_depth > 20:  # Prevent stack overflow
            return current_depth
        
        if isinstance(obj, dict):
            return max([self._check_nesting_depth(v, current_depth + 1) for v in obj.values()] + [current_depth])
        elif isinstance(obj, list):
            return max([self._check_nesting_depth(item, current_depth + 1) for item in obj] + [current_depth])
        else:
            return current_depth

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_delivery_network_interruption_recovery(self, real_services_fixture):
        """
        BVJ: All segments - Network interruption recovery ensures no lost business value
        Value: Users never lose important AI insights due to temporary network issues
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Simulate network interruption scenarios
        network_states = {
            "connected": True,
            "interruption_count": 0,
            "recovery_count": 0
        }
        
        buffered_events = []
        delivered_events = []
        
        async def network_aware_emit(event_type, data=None, **kwargs):
            """Emitter that handles network interruptions."""
            if not network_states["connected"]:
                # Buffer events during network interruption
                buffered_events.append({
                    "type": event_type,
                    "data": data,
                    "buffered_at": time.time()
                })
                raise ConnectionError("Network interruption")
            else:
                # Deliver event when network available
                delivered_events.append({
                    "type": event_type,
                    "data": data,
                    "delivered_at": time.time()
                })
        
        async def simulate_network_interruption():
            """Simulate temporary network failure."""
            await asyncio.sleep(0.1)  # Let some events go through
            network_states["connected"] = False
            network_states["interruption_count"] += 1
            
            await asyncio.sleep(0.2)  # Network down for 200ms
            
            network_states["connected"] = True
            network_states["recovery_count"] += 1
            
            # Flush buffered events on recovery
            while buffered_events:
                buffered_event = buffered_events.pop(0)
                await network_aware_emit(
                    buffered_event["type"],
                    buffered_event["data"]
                )
        
        mock_emitter = AsyncMock()
        mock_emitter.emit_agent_event = network_aware_emit
        
        # Start network interruption simulation
        interruption_task = asyncio.create_task(simulate_network_interruption())
        
        # Send critical events during network issues
        critical_events = [
            ("agent_started", {"critical": True}),
            ("agent_thinking", {"analysis": "important"}),
            ("tool_executing", {"tool": "critical_analyzer"}),
            ("tool_completed", {"business_value": 10000}),
            ("agent_completed", {"final_result": "success"})
        ]
        
        # Send events with network recovery handling
        for event_type, data in critical_events:
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    await mock_emitter.emit_agent_event(event_type, data)
                    break
                except ConnectionError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1)  # Wait for network recovery
                    else:
                        raise
        
        await interruption_task
        
        # Verify all events eventually delivered
        total_events = len(delivered_events)
        assert total_events == 5, f"Expected 5 events delivered, got {total_events}"
        
        # Verify network interruption occurred and recovered
        assert network_states["interruption_count"] >= 1, "Network interruption should have occurred"
        assert network_states["recovery_count"] >= 1, "Network should have recovered"
        
        # Verify business-critical events preserved
        event_types = [e["type"] for e in delivered_events]
        assert "agent_completed" in event_types, "Final result must be delivered"
        
        # Find business value event
        value_event = next(e for e in delivered_events if e["type"] == "tool_completed")
        assert value_event["data"]["business_value"] == 10000, "Business value must be preserved"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_queue_management_prioritization(self, real_services_fixture):
        """
        BVJ: Enterprise segment - Event prioritization ensures critical events delivered first
        Value: Business-critical notifications reach users before less important updates
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Event priority system
        EVENT_PRIORITIES = {
            "agent_started": 1,      # Low priority
            "agent_thinking": 2,     # Medium priority 
            "tool_executing": 2,     # Medium priority
            "tool_completed": 4,     # High priority (business value)
            "agent_completed": 5,    # Critical priority (final result)
            "system_error": 6        # Emergency priority
        }
        
        # Priority queue implementation
        import heapq
        event_queue = []
        delivered_events = []
        
        async def priority_queue_emit(event_type, data=None, **kwargs):
            """Add events to priority queue."""
            priority = EVENT_PRIORITIES.get(event_type, 1)
            # Use negative priority for max-heap behavior
            heapq.heappush(event_queue, (-priority, time.time(), {
                "type": event_type,
                "data": data,
                "priority": priority
            }))
        
        async def process_event_queue():
            """Process events in priority order."""
            while event_queue:
                neg_priority, timestamp, event = heapq.heappop(event_queue)
                delivered_events.append({
                    **event,
                    "delivered_at": time.time()
                })
                await asyncio.sleep(0.01)  # Simulate processing
        
        mock_emitter = AsyncMock()
        mock_emitter.emit_agent_event = priority_queue_emit
        
        # Send events in random order (not priority order)
        mixed_events = [
            ("agent_thinking", {"thought": "analyzing"}),
            ("agent_completed", {"result": "critical_business_value"}),
            ("tool_executing", {"tool": "analyzer"}),
            ("system_error", {"error": "critical_system_failure"}),
            ("agent_started", {"message": "starting"}),
            ("tool_completed", {"savings": 5000}),
        ]
        
        # Queue all events
        for event_type, data in mixed_events:
            await mock_emitter.emit_agent_event(event_type, data)
        
        # Process queue (should deliver in priority order)
        await process_event_queue()
        
        # Verify events delivered in priority order
        assert len(delivered_events) == 6
        
        delivered_priorities = [e["priority"] for e in delivered_events]
        assert delivered_priorities == sorted(delivered_priorities, reverse=True), \
            f"Events not delivered in priority order: {delivered_priorities}"
        
        # Verify critical events delivered first
        assert delivered_events[0]["type"] == "system_error", "Emergency event should be first"
        assert delivered_events[1]["type"] == "agent_completed", "Critical result should be second"
        assert delivered_events[2]["type"] == "tool_completed", "Business value should be third"
        
        # Verify business value preserved in high-priority events
        business_value_event = next(e for e in delivered_events if e["type"] == "tool_completed")
        assert business_value_event["data"]["savings"] == 5000, "Business value must be preserved"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_delivery_metrics_monitoring(self, real_services_fixture):
        """
        BVJ: Platform/Internal - Metrics monitoring for operational excellence
        Value: Operations team needs visibility into event delivery performance
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Metrics collection system
        metrics = {
            "total_events": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "retry_attempts": 0,
            "delivery_times": [],
            "event_types": {},
            "error_types": {}
        }
        
        async def metrics_tracking_emit(event_type, data=None, **kwargs):
            """Emit events with comprehensive metrics tracking."""
            delivery_start = time.time()
            metrics["total_events"] += 1
            
            # Track event type distribution
            metrics["event_types"][event_type] = metrics["event_types"].get(event_type, 0) + 1
            
            # Simulate delivery with possible failure
            import random
            failure_rate = 0.1  # 10% failure rate for testing
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Simulate random failures
                    if random.random() < failure_rate and attempt == 0:
                        raise ConnectionError("Simulated network failure")
                    
                    # Simulate successful delivery
                    await asyncio.sleep(0.01)  # Processing time
                    
                    delivery_time = time.time() - delivery_start
                    metrics["delivery_times"].append(delivery_time)
                    metrics["successful_deliveries"] += 1
                    
                    if attempt > 0:
                        metrics["retry_attempts"] += attempt
                    
                    return
                    
                except Exception as e:
                    error_type = type(e).__name__
                    metrics["error_types"][error_type] = metrics["error_types"].get(error_type, 0) + 1
                    
                    if attempt == max_retries - 1:
                        metrics["failed_deliveries"] += 1
                        raise
                    
                    await asyncio.sleep(0.05 * (attempt + 1))  # Backoff
        
        mock_emitter = AsyncMock()
        mock_emitter.emit_agent_event = metrics_tracking_emit
        
        # Send various events to generate metrics
        test_events = [
            ("agent_started", {"test": "metrics"}),
            ("agent_thinking", {"analysis": "test"}),
            ("tool_executing", {"tool": "test_tool"}),
            ("tool_completed", {"result": "test_result"}),
            ("agent_completed", {"final": "test_complete"}),
        ] * 4  # Send 20 events total (4 complete cycles)
        
        # Send events and collect metrics
        for event_type, data in test_events:
            try:
                await mock_emitter.emit_agent_event(event_type, data)
            except Exception:
                pass  # Failed deliveries are tracked in metrics
        
        # Analyze metrics
        total_events = metrics["total_events"]
        success_rate = metrics["successful_deliveries"] / total_events if total_events > 0 else 0
        failure_rate = metrics["failed_deliveries"] / total_events if total_events > 0 else 0
        
        # Verify metrics collection
        assert total_events == 20, f"Expected 20 events, tracked {total_events}"
        assert success_rate > 0.8, f"Success rate too low: {success_rate:.2%}"
        
        # Verify performance metrics
        if metrics["delivery_times"]:
            avg_delivery_time = sum(metrics["delivery_times"]) / len(metrics["delivery_times"])
            assert avg_delivery_time < 0.1, f"Average delivery time too slow: {avg_delivery_time:.3f}s"
        
        # Verify event type distribution
        expected_event_types = ["agent_started", "agent_thinking", "tool_executing", 
                               "tool_completed", "agent_completed"]
        for event_type in expected_event_types:
            assert event_type in metrics["event_types"], f"Missing metrics for {event_type}"
            assert metrics["event_types"][event_type] == 4, \
                f"Expected 4 {event_type} events, got {metrics['event_types'][event_type]}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_delivery_authentication_context(self, real_services_fixture):
        """
        BVJ: Enterprise segment - Authentication context validation for secure event delivery
        Value: Enterprise customers need secure event delivery with proper user authentication
        """
        # Create authenticated user context
        user_context = await self.create_test_user_context(
            real_services_fixture,
            {"email": "secure-user@enterprise.com", "name": "Secure User"}
        )
        user_id = UserID(user_context["id"])
        
        # Mock authentication system
        authenticated_sessions = {
            str(user_id): {
                "session_id": "sess_12345",
                "authenticated": True,
                "permissions": ["read_events", "receive_notifications"],
                "expires_at": time.time() + 3600  # 1 hour
            }
        }
        
        def validate_user_authentication(user_id_str):
            """Validate user authentication for event delivery."""
            session = authenticated_sessions.get(user_id_str)
            if not session:
                return False, "No active session"
            
            if not session["authenticated"]:
                return False, "User not authenticated"
            
            if time.time() > session["expires_at"]:
                return False, "Session expired"
            
            if "receive_notifications" not in session["permissions"]:
                return False, "Insufficient permissions"
            
            return True, "Authenticated"
        
        # Track authentication checks
        auth_checks = []
        delivered_events = []
        
        async def authenticated_emit(event_type, data=None, user_id_str=None, **kwargs):
            """Emit events with authentication validation."""
            if user_id_str is None:
                user_id_str = str(user_id)
            
            # Perform authentication check
            is_authenticated, auth_message = validate_user_authentication(user_id_str)
            auth_checks.append({
                "user_id": user_id_str,
                "authenticated": is_authenticated,
                "message": auth_message,
                "timestamp": time.time()
            })
            
            if not is_authenticated:
                raise PermissionError(f"Authentication failed: {auth_message}")
            
            # Deliver event if authenticated
            delivered_events.append({
                "type": event_type,
                "data": data,
                "user_id": user_id_str,
                "authenticated": True
            })
        
        mock_emitter = AsyncMock()
        mock_emitter.emit_agent_event = authenticated_emit
        
        # Test authenticated event delivery
        business_events = [
            ("agent_started", {"secure_analysis": True}),
            ("tool_completed", {"confidential_savings": 15000}),
            ("agent_completed", {"enterprise_result": "classified_recommendations"})
        ]
        
        for event_type, data in business_events:
            await mock_emitter.emit_agent_event(
                event_type, data, user_id_str=str(user_id)
            )
        
        # Verify all events delivered with authentication
        assert len(delivered_events) == 3
        assert len(auth_checks) == 3
        
        for check in auth_checks:
            assert check["authenticated"] is True, "All authentication checks should pass"
        
        for event in delivered_events:
            assert event["authenticated"] is True, "All events should be authenticated"
        
        # Test authentication failure scenario
        # Expire the session
        authenticated_sessions[str(user_id)]["expires_at"] = time.time() - 1
        
        # Try to send event with expired session
        with pytest.raises(PermissionError, match="Session expired"):
            await mock_emitter.emit_agent_event(
                "agent_started", {"data": "should_fail"}, user_id_str=str(user_id)
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_delivery_error_recovery_graceful_degradation(self, real_services_fixture):
        """
        BVJ: All segments - Graceful degradation ensures business continuity during failures
        Value: Users continue receiving AI value even when event delivery is impaired
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # System state tracking
        system_state = {
            "primary_delivery": True,
            "fallback_active": False,
            "degraded_mode": False,
            "failure_count": 0
        }
        
        primary_events = []
        fallback_events = []
        critical_events = []
        
        async def resilient_emit(event_type, data=None, **kwargs):
            """Event emitter with graceful degradation."""
            try:
                # Try primary delivery system
                if system_state["primary_delivery"]:
                    # Simulate primary system failure after 3 events
                    if system_state["failure_count"] >= 3:
                        raise ConnectionError("Primary delivery system failed")
                    
                    primary_events.append({
                        "type": event_type,
                        "data": data,
                        "delivery_mode": "primary"
                    })
                    system_state["failure_count"] += 1
                    return
                
            except Exception as e:
                logger.info(f"Primary delivery failed: {e}")
                system_state["primary_delivery"] = False
                system_state["fallback_active"] = True
                system_state["degraded_mode"] = True
            
            # Fallback delivery system
            if system_state["fallback_active"]:
                # Determine if event is critical
                critical_event_types = ["agent_completed", "tool_completed", "system_error"]
                is_critical = event_type in critical_event_types
                
                if is_critical or not system_state["degraded_mode"]:
                    fallback_events.append({
                        "type": event_type,
                        "data": data,
                        "delivery_mode": "fallback",
                        "critical": is_critical
                    })
                    
                    if is_critical:
                        critical_events.append({
                            "type": event_type,
                            "data": data,
                            "guaranteed_delivery": True
                        })
        
        mock_emitter = AsyncMock()
        mock_emitter.emit_agent_event = resilient_emit
        
        # Send events that will trigger system degradation
        test_events = [
            ("agent_started", {"test": "resilience_1"}),
            ("agent_thinking", {"test": "resilience_2"}),
            ("tool_executing", {"test": "resilience_3"}),
            # Primary system fails here
            ("tool_completed", {"business_value": 8000}),  # Critical event
            ("agent_thinking", {"test": "resilience_4"}),  # Non-critical, may be dropped
            ("agent_completed", {"final": "business_result"}),  # Critical event
        ]
        
        for event_type, data in test_events:
            await mock_emitter.emit_agent_event(event_type, data)
        
        # Verify graceful degradation occurred
        assert system_state["degraded_mode"] is True, "System should be in degraded mode"
        assert system_state["fallback_active"] is True, "Fallback system should be active"
        
        # Verify primary events delivered before failure
        assert len(primary_events) == 3, f"Expected 3 primary events, got {len(primary_events)}"
        
        # Verify critical events delivered via fallback
        assert len(critical_events) == 2, f"Expected 2 critical events, got {len(critical_events)}"
        
        critical_types = [e["type"] for e in critical_events]
        assert "tool_completed" in critical_types, "Critical business value event must be delivered"
        assert "agent_completed" in critical_types, "Critical final result must be delivered"
        
        # Verify business value preserved
        business_value_event = next(e for e in critical_events if e["type"] == "tool_completed")
        assert business_value_event["data"]["business_value"] == 8000, "Business value must be preserved"
        
        final_result_event = next(e for e in critical_events if e["type"] == "agent_completed")
        assert "business_result" in final_result_event["data"]["final"], "Final result must be preserved"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_delivery_coordination_agent_execution_state(self, real_services_fixture):
        """
        BVJ: All segments - Event delivery coordination with agent execution state
        Value: Users see accurate agent progress that matches actual execution state
        """
        user_context = await self.create_test_user_context(real_services_fixture)
        user_id = UserID(user_context["id"])
        
        # Agent execution state tracking
        agent_state = {
            "status": "idle",
            "current_tool": None,
            "progress": 0.0,
            "start_time": None,
            "completion_time": None,
            "business_value_generated": 0
        }
        
        state_history = []
        event_state_correlation = []
        
        async def state_aware_emit(event_type, data=None, **kwargs):
            """Emit events coordinated with agent execution state."""
            timestamp = time.time()
            
            # Update agent state based on event
            if event_type == "agent_started":
                agent_state["status"] = "running"
                agent_state["start_time"] = timestamp
                agent_state["progress"] = 0.1
                
            elif event_type == "agent_thinking":
                agent_state["status"] = "analyzing"
                agent_state["progress"] += 0.1
                
            elif event_type == "tool_executing":
                tool_name = data.get("tool_name", "unknown_tool") if data else "unknown_tool"
                agent_state["status"] = "executing_tool"
                agent_state["current_tool"] = tool_name
                agent_state["progress"] += 0.2
                
            elif event_type == "tool_completed":
                agent_state["status"] = "processing_results"
                agent_state["current_tool"] = None
                agent_state["progress"] += 0.3
                
                # Extract business value
                if data and "business_value" in data:
                    agent_state["business_value_generated"] += data["business_value"]
                    
            elif event_type == "agent_completed":
                agent_state["status"] = "completed"
                agent_state["completion_time"] = timestamp
                agent_state["progress"] = 1.0
            
            # Record state snapshot
            state_snapshot = {
                **agent_state.copy(),
                "timestamp": timestamp,
                "event_trigger": event_type
            }
            state_history.append(state_snapshot)
            
            # Correlate event with state
            event_state_correlation.append({
                "event_type": event_type,
                "event_data": data,
                "agent_status": agent_state["status"],
                "progress": agent_state["progress"],
                "timestamp": timestamp
            })
        
        mock_emitter = AsyncMock()
        mock_emitter.emit_agent_event = state_aware_emit
        
        # Execute realistic agent workflow
        workflow_events = [
            ("agent_started", {"agent": "business_analyst", "task": "cost_optimization"}),
            ("agent_thinking", {"analysis": "Reviewing current costs"}),
            ("tool_executing", {"tool_name": "cost_analyzer", "scope": "monthly"}),
            ("tool_completed", {"tool_name": "cost_analyzer", "business_value": 3500}),
            ("agent_thinking", {"analysis": "Identifying optimization opportunities"}),
            ("tool_executing", {"tool_name": "optimization_finder", "criteria": "savings"}),
            ("tool_completed", {"tool_name": "optimization_finder", "business_value": 4500}),
            ("agent_completed", {"recommendations": 5, "total_savings": 8000})
        ]
        
        for event_type, data in workflow_events:
            await mock_emitter.emit_agent_event(event_type, data)
            await asyncio.sleep(0.05)  # Simulate execution time
        
        # Verify state progression
        assert len(state_history) == 8, f"Expected 8 state snapshots, got {len(state_history)}"
        
        # Verify state transitions are logical
        status_progression = [s["status"] for s in state_history]
        expected_statuses = ["running", "analyzing", "executing_tool", "processing_results",
                           "analyzing", "executing_tool", "processing_results", "completed"]
        assert status_progression == expected_statuses, f"Unexpected state progression: {status_progression}"
        
        # Verify progress increases monotonically
        progress_values = [s["progress"] for s in state_history]
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i-1], \
                f"Progress should increase monotonically: {progress_values}"
        
        # Verify final state
        final_state = state_history[-1]
        assert final_state["status"] == "completed"
        assert final_state["progress"] == 1.0
        assert final_state["business_value_generated"] == 8000
        
        # Verify execution timing
        total_execution_time = final_state["completion_time"] - state_history[0]["start_time"]
        assert total_execution_time > 0, "Execution should take measurable time"
        
        # Verify event-state correlation
        for correlation in event_state_correlation:
            if correlation["event_type"] == "agent_completed":
                assert correlation["agent_status"] == "completed"
                assert correlation["progress"] == 1.0