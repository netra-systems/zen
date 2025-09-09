"""
MISSION CRITICAL: WebSocket Events Never Fail Test for Golden Path

🚨 MISSION CRITICAL TEST 🚨
This test MUST NEVER FAIL - it validates the core revenue-generating WebSocket events
that enable the $500K+ ARR chat experience. Failure blocks deployment.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket events that deliver business value NEVER fail
- Value Impact: Missing events = broken chat = complete revenue loss
- Strategic Impact: Core platform reliability that enables all business operations

ZERO TOLERANCE FAILURE CONDITIONS:
- Missing any of the 5 critical WebSocket events = HARD FAIL
- Events delivered in wrong order = HARD FAIL  
- Event delivery timeout = HARD FAIL
- Any silent failures = HARD FAIL

This test represents the absolute minimum functionality required for business continuity.
"""

import asyncio
import pytest
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.types.core_types import UserID, ThreadID, RunID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestWebSocketEventsNeverFail(SSotAsyncTestCase):
    """
    🚨 MISSION CRITICAL TEST 🚨
    
    This test validates that the 5 critical WebSocket events are ALWAYS delivered
    for every Golden Path execution. This is non-negotiable for business operations.
    """
    
    def setup_method(self, method=None):
        """Setup with mission critical context."""
        super().setup_method(method)
        
        # Mission critical business metrics
        self.record_metric("mission_critical", True)
        self.record_metric("revenue_protection", 500000)  # $500K ARR
        self.record_metric("zero_tolerance", True)
        self.record_metric("deployment_blocker", True)
        
        # Initialize components
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.id_generator = UnifiedIdGenerator()
        
        # Test configuration
        self.websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # The 5 mission critical events that MUST be delivered
        self.CRITICAL_EVENTS = [
            "agent_started",      # User sees AI began work
            "agent_thinking",     # Real-time reasoning visibility  
            "tool_executing",     # Tool usage transparency
            "tool_completed",     # Tool results display
            "agent_completed"     # Final results ready
        ]
        
        # Active connections for cleanup
        self.active_connections = []
        
    async def async_teardown_method(self, method=None):
        """Cleanup with mission critical logging."""
        try:
            # Close any active connections
            for connection in self.active_connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(connection)
                except:
                    pass
            
        except Exception as e:
            # Mission critical test cleanup failures are logged but don't fail test
            print(f"⚠️  Mission Critical Cleanup Warning: {e}")
        
        await super().async_teardown_method(method)
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip  # NEVER skip this test
    @pytest.mark.asyncio
    async def test_all_five_critical_events_must_be_delivered(self):
        """
        🚨 MISSION CRITICAL: All 5 WebSocket events MUST be delivered.
        
        This test CANNOT FAIL without blocking deployment.
        Missing events = broken chat experience = revenue loss.
        """
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="mission_critical_events@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Get authentication token
        jwt_token = await self.auth_helper.get_staging_token_async(
            email=user_context.agent_context.get('user_email')
        )
        
        if not jwt_token:
            pytest.fail("🚨 MISSION CRITICAL FAILURE: Cannot authenticate user - complete system breakdown")
        
        # Get WebSocket headers
        ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
        
        # Establish WebSocket connection
        mission_critical_start = time.time()
        
        try:
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=ws_headers,
                timeout=10.0,
                user_id=str(user_context.user_id)
            )
            self.active_connections.append(connection)
            
        except Exception as e:
            pytest.fail(f"🚨 MISSION CRITICAL FAILURE: WebSocket connection failed - {e}")
        
        connection_time = time.time() - mission_critical_start
        
        # Mission critical timing requirement
        if connection_time > 10.0:
            pytest.fail(f"🚨 MISSION CRITICAL FAILURE: Connection too slow ({connection_time:.2f}s > 10s)")
        
        # Send Golden Path message
        golden_path_message = {
            "type": "chat_message",
            "content": "MISSION CRITICAL: Optimize my AI costs",
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),
            "run_id": str(user_context.run_id),
            "mission_critical": True,
            "timestamp": time.time()
        }
        
        try:
            await WebSocketTestHelpers.send_test_message(
                connection, golden_path_message, timeout=5.0
            )
        except Exception as e:
            pytest.fail(f"🚨 MISSION CRITICAL FAILURE: Cannot send message - {e}")
        
        # Collect WebSocket events with ZERO tolerance for missing events
        events_collected = []
        event_types_received = set()
        event_collection_start = time.time()
        max_collection_time = 60.0  # 60 seconds absolute maximum
        
        while (time.time() - event_collection_start) < max_collection_time:
            try:
                event = await WebSocketTestHelpers.receive_test_message(
                    connection, timeout=5.0
                )
                
                if event and isinstance(event, dict):
                    event_type = event.get("type")
                    if event_type:
                        events_collected.append({
                            "type": event_type,
                            "timestamp": time.time(),
                            "data": event
                        })
                        event_types_received.add(event_type)
                        
                        # Check if we have all critical events
                        if all(event_type in event_types_received for event_type in self.CRITICAL_EVENTS):
                            break
                            
            except Exception:
                # Continue collecting - timeout on individual event is acceptable
                continue
        
        event_collection_time = time.time() - event_collection_start
        total_mission_critical_time = time.time() - mission_critical_start
        
        # 🚨 MISSION CRITICAL VALIDATIONS - ZERO TOLERANCE 🚨
        
        # Validation 1: All 5 critical events MUST be present
        missing_events = [event for event in self.CRITICAL_EVENTS if event not in event_types_received]
        if missing_events:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Missing critical events: {missing_events}\n"
                f"Events received: {list(event_types_received)}\n"
                f"This breaks the chat experience and blocks revenue generation!"
            )
        
        # Validation 2: Event collection MUST complete within time limit
        if event_collection_time >= max_collection_time:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Event collection timeout ({event_collection_time:.2f}s >= {max_collection_time}s)\n"
                f"Received events: {list(event_types_received)}\n"
                f"Users cannot wait this long for AI responses!"
            )
        
        # Validation 3: Total Golden Path time MUST be acceptable
        if total_mission_critical_time > 90.0:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Golden Path too slow ({total_mission_critical_time:.2f}s > 90s)\n"
                f"This degrades user experience below acceptable levels!"
            )
        
        # Validation 4: Events MUST be in logical order
        event_order = [event["type"] for event in events_collected if event["type"] in self.CRITICAL_EVENTS]
        
        # agent_started should come before agent_completed
        if "agent_started" in event_order and "agent_completed" in event_order:
            started_index = event_order.index("agent_started")
            completed_index = event_order.index("agent_completed")
            
            if started_index >= completed_index:
                pytest.fail(
                    f"🚨 MISSION CRITICAL FAILURE: Events in wrong order\n"
                    f"agent_started must come before agent_completed\n"
                    f"Order received: {event_order}"
                )
        
        # Validation 5: Must have received substantial events (not just connection events)
        if len(events_collected) < 5:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Too few events received ({len(events_collected)} < 5)\n"
                f"This indicates the agent pipeline is not working properly!"
            )
        
        # 🚨 MISSION CRITICAL SUCCESS LOGGING 🚨
        success_metrics = {
            "all_critical_events_received": True,
            "event_collection_time": event_collection_time,
            "total_execution_time": total_mission_critical_time,
            "events_received_count": len(events_collected),
            "critical_events_received": len(event_types_received.intersection(self.CRITICAL_EVENTS)),
            "connection_time": connection_time
        }
        
        # Record mission critical success
        for metric, value in success_metrics.items():
            self.record_metric(f"mission_critical_{metric}", value)
        
        # Cleanup connection
        await WebSocketTestHelpers.close_test_connection(connection)
        self.active_connections.remove(connection)
        
        # Mission Critical Success Report
        print(f"\n🎯 MISSION CRITICAL SUCCESS:")
        print(f"   ✅ ALL 5 Critical Events Delivered: {self.CRITICAL_EVENTS}")
        print(f"   ⏱️  Event Collection Time: {event_collection_time:.2f}s")
        print(f"   🚀 Total Execution Time: {total_mission_critical_time:.2f}s")
        print(f"   📊 Total Events Received: {len(events_collected)}")
        print(f"   💰 $500K+ ARR Revenue Stream: PROTECTED")
        
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_websocket_events_under_high_load_never_fail(self):
        """
        🚨 MISSION CRITICAL: WebSocket events MUST be delivered even under high load.
        
        System must maintain event delivery reliability under stress conditions.
        """
        # Test with multiple concurrent users to simulate load
        concurrent_users = 3  # Conservative for mission critical test
        user_tasks = []
        
        high_load_start = time.time()
        
        # Create concurrent user tasks
        for i in range(concurrent_users):
            task = self._execute_mission_critical_user_flow(
                f"mission_critical_load_user_{i}@example.com",
                i
            )
            user_tasks.append(task)
        
        # Execute all users concurrently
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        high_load_time = time.time() - high_load_start
        
        # 🚨 MISSION CRITICAL VALIDATION UNDER LOAD 🚨
        
        successful_users = 0
        failed_users = 0
        event_delivery_failures = []
        
        for i, result in enumerate(user_results):
            if isinstance(result, Exception):
                failed_users += 1
                event_delivery_failures.append(f"User {i}: {result}")
            elif not result.get("success", False):
                failed_users += 1
                event_delivery_failures.append(f"User {i}: {result.get('error', 'Unknown failure')}")
            elif not result.get("all_events_delivered", False):
                failed_users += 1
                event_delivery_failures.append(f"User {i}: Missing critical events - {result.get('missing_events', [])}")
            else:
                successful_users += 1
        
        # ZERO TOLERANCE for event delivery failures under load
        if failed_users > 0:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Event delivery failed under load\n"
                f"Failed users: {failed_users}/{concurrent_users}\n"
                f"Failures: {event_delivery_failures}\n"
                f"System cannot handle concurrent load - revenue at risk!"
            )
        
        # Performance requirement under load
        if high_load_time > 120.0:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: High load test too slow ({high_load_time:.2f}s > 120s)\n"
                f"System cannot handle concurrent users effectively!"
            )
        
        # Success rate must be 100% for mission critical
        success_rate = successful_users / concurrent_users
        if success_rate < 1.0:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Success rate {success_rate:.1%} < 100%\n"
                f"Mission critical systems must have 100% success rate!"
            )
        
        # Record mission critical load test success
        self.record_metric("mission_critical_load_test_passed", True)
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("load_test_success_rate", success_rate)
        self.record_metric("load_test_duration", high_load_time)
        
        print(f"\n🚀 MISSION CRITICAL LOAD TEST SUCCESS:")
        print(f"   ✅ Success Rate: {success_rate:.1%} ({successful_users}/{concurrent_users})")
        print(f"   ⏱️  Load Test Duration: {high_load_time:.2f}s")
        print(f"   💪 System Reliability: PROVEN UNDER LOAD")
        
    async def _execute_mission_critical_user_flow(
        self, 
        user_email: str, 
        user_index: int
    ) -> Dict[str, Any]:
        """Execute mission critical user flow for load testing."""
        flow_start = time.time()
        
        try:
            # Create user context
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                environment=self.environment,
                websocket_enabled=True
            )
            
            # Authenticate
            jwt_token = await self.auth_helper.get_staging_token_async(
                email=user_context.agent_context.get('user_email')
            )
            
            if not jwt_token:
                return {
                    "success": False,
                    "user_index": user_index,
                    "error": "Authentication failed",
                    "execution_time": time.time() - flow_start
                }
            
            # Connect WebSocket
            ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=ws_headers,
                timeout=15.0,
                user_id=str(user_context.user_id)
            )
            
            # Send mission critical message
            message = {
                "type": "chat_message",
                "content": f"Mission Critical Load Test {user_index}: Optimize AI costs",
                "user_id": str(user_context.user_id),
                "user_index": user_index,
                "timestamp": time.time()
            }
            
            await WebSocketTestHelpers.send_test_message(connection, message, timeout=5.0)
            
            # Collect critical events
            events_received = set()
            event_collection_start = time.time()
            max_event_wait = 45.0
            
            while (time.time() - event_collection_start) < max_event_wait:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(
                        connection, timeout=3.0
                    )
                    
                    if event and isinstance(event, dict):
                        event_type = event.get("type")
                        if event_type in self.CRITICAL_EVENTS:
                            events_received.add(event_type)
                            
                            # Check if all events received
                            if len(events_received) == len(self.CRITICAL_EVENTS):
                                break
                                
                except:
                    # Individual timeout acceptable
                    continue
            
            # Cleanup
            await WebSocketTestHelpers.close_test_connection(connection)
            
            # Validate results
            missing_events = [event for event in self.CRITICAL_EVENTS if event not in events_received]
            all_events_delivered = len(missing_events) == 0
            
            execution_time = time.time() - flow_start
            
            return {
                "success": True,
                "user_index": user_index,
                "all_events_delivered": all_events_delivered,
                "events_received": list(events_received),
                "missing_events": missing_events,
                "execution_time": execution_time,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_index": user_index,
                "all_events_delivered": False,
                "events_received": [],
                "missing_events": self.CRITICAL_EVENTS,
                "execution_time": time.time() - flow_start,
                "error": str(e)
            }
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_timing_never_exceeds_limits(self):
        """
        🚨 MISSION CRITICAL: Event delivery timing MUST meet business requirements.
        
        Events delivered too slowly = poor user experience = customer loss.
        """
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="mission_critical_timing@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Authenticate and connect
        jwt_token = await self.auth_helper.get_staging_token_async(
            email=user_context.agent_context.get('user_email')
        )
        ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
        
        connection = await WebSocketTestHelpers.create_test_websocket_connection(
            url=self.websocket_url,
            headers=ws_headers,
            timeout=10.0,
            user_id=str(user_context.user_id)
        )
        self.active_connections.append(connection)
        
        # Send message and track event timing
        timing_test_message = {
            "type": "chat_message",
            "content": "TIMING TEST: Show me cost optimization recommendations",
            "user_id": str(user_context.user_id),
            "timing_test": True,
            "timestamp": time.time()
        }
        
        message_send_time = time.time()
        await WebSocketTestHelpers.send_test_message(connection, timing_test_message, timeout=5.0)
        
        # Track timing for each critical event
        event_timings = {}
        events_received = set()
        
        first_event_time = None
        last_event_time = None
        
        max_event_wait = 60.0  # 60 seconds absolute maximum
        event_start = time.time()
        
        while (time.time() - event_start) < max_event_wait:
            try:
                event = await WebSocketTestHelpers.receive_test_message(
                    connection, timeout=5.0
                )
                
                if event and isinstance(event, dict):
                    event_type = event.get("type")
                    event_time = time.time()
                    
                    if event_type in self.CRITICAL_EVENTS:
                        time_from_message = event_time - message_send_time
                        event_timings[event_type] = time_from_message
                        events_received.add(event_type)
                        
                        if first_event_time is None:
                            first_event_time = time_from_message
                        last_event_time = time_from_message
                        
                        # Check if all events received
                        if len(events_received) == len(self.CRITICAL_EVENTS):
                            break
                            
            except:
                continue
        
        total_event_collection_time = time.time() - event_start
        
        # 🚨 MISSION CRITICAL TIMING VALIDATIONS 🚨
        
        # Validation 1: First event must arrive quickly (user engagement)
        if first_event_time is None:
            pytest.fail("🚨 MISSION CRITICAL FAILURE: No events received - system completely broken!")
        
        if first_event_time > 10.0:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: First event too slow ({first_event_time:.2f}s > 10s)\n"
                f"Users will abandon chat if they don't see immediate response!"
            )
        
        # Validation 2: All events must be received within time limit
        missing_events = [event for event in self.CRITICAL_EVENTS if event not in events_received]
        if missing_events:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Missing critical events within time limit: {missing_events}\n"
                f"Received: {list(events_received)}\n"
                f"Time limit: {max_event_wait}s"
            )
        
        # Validation 3: Last event (completion) must arrive within business requirements
        if last_event_time > 60.0:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Complete flow too slow ({last_event_time:.2f}s > 60s)\n"
                f"Users expect AI responses within 1 minute!"
            )
        
        # Validation 4: Individual event timing requirements
        timing_failures = []
        for event_type, timing in event_timings.items():
            if event_type == "agent_started" and timing > 5.0:
                timing_failures.append(f"agent_started too slow: {timing:.2f}s > 5s")
            elif event_type == "agent_completed" and timing > 60.0:
                timing_failures.append(f"agent_completed too slow: {timing:.2f}s > 60s")
        
        if timing_failures:
            pytest.fail(
                f"🚨 MISSION CRITICAL FAILURE: Event timing requirements not met:\n" +
                "\n".join(timing_failures)
            )
        
        # Mission Critical Timing Success
        self.record_metric("mission_critical_timing_test_passed", True)
        self.record_metric("first_event_time", first_event_time)
        self.record_metric("last_event_time", last_event_time)
        self.record_metric("total_event_collection_time", total_event_collection_time)
        
        for event_type, timing in event_timings.items():
            self.record_metric(f"event_timing_{event_type}", timing)
        
        # Cleanup
        await WebSocketTestHelpers.close_test_connection(connection)
        self.active_connections.remove(connection)
        
        print(f"\n⏰ MISSION CRITICAL TIMING SUCCESS:")
        print(f"   🚀 First Event: {first_event_time:.2f}s")
        print(f"   🏁 Last Event: {last_event_time:.2f}s")
        print(f"   📊 All Events Within Limits: {list(events_received)}")
        print(f"   💰 User Experience: PRESERVED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])