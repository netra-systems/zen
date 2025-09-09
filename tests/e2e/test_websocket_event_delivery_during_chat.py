#!/usr/bin/env python
"""
E2E TESTS: WebSocket Event Delivery During Chat - Real-Time UX Validation

CRITICAL BUSINESS MISSION: These tests validate REAL-TIME WebSocket event delivery 
that enables SUBSTANTIVE CHAT VALUE through transparent AI processing visibility.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate real-time chat UX through WebSocket event transparency  
- Value Impact: Ensures users see AI working (agent_thinking, tool_executing) for trust
- Strategic Impact: Protects $500K+ ARR by ensuring chat feels responsive and transparent

CRITICAL REQUIREMENTS per CLAUDE.md:
1. MUST use REAL WebSocket connections - NO mocks per "MOCKS = Abomination"
2. MUST use REAL authentication (JWT/OAuth) for WebSocket connections
3. MUST validate ALL 5 REQUIRED WebSocket events: agent_started, agent_thinking, 
   tool_executing, tool_completed, agent_completed
4. MUST test with REAL services (Docker containers) for full E2E validation
5. MUST be designed to fail hard if events are missing or delayed

TEST FOCUS: E2E tests with REAL WebSocket connections to validate the complete
real-time event delivery pipeline that enables substantive chat value.
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque

# SSOT IMPORTS - Following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.ssot.real_services_test_fixtures import real_services_fixture

# Core system imports for E2E WebSocket testing
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, WebSocketEventType
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Import Docker service management for E2E tests
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType


class WebSocketEventCollector:
    """Collects and analyzes WebSocket events during E2E chat testing."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_timeline: deque = deque()
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.start_time = time.time()
        
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add WebSocket event with timing metadata."""
        enriched_event = {
            **event,
            "received_timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "sequence_number": len(self.events)
        }
        
        self.events.append(enriched_event)
        self.event_timeline.append(enriched_event)
        self.event_counts[event.get("type", "unknown")] += 1
        
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of specific type."""
        return [event for event in self.events if event.get("type") == event_type]
        
    def get_event_sequence(self) -> List[str]:
        """Get sequence of event types in order received."""
        return [event.get("type", "unknown") for event in self.events]
        
    def validate_required_events(self, required_events: List[str]) -> Dict[str, Any]:
        """Validate all required events were received."""
        received_types = set(self.get_event_sequence())
        missing_events = [event_type for event_type in required_events 
                         if event_type not in received_types]
        
        return {
            "all_required_present": len(missing_events) == 0,
            "missing_events": missing_events,
            "received_events": list(received_types),
            "total_events": len(self.events),
            "event_sequence": self.get_event_sequence()
        }
        
    def get_timing_analysis(self) -> Dict[str, Any]:
        """Analyze event timing for UX validation."""
        if not self.events:
            return {"error": "no_events"}
            
        first_event_time = self.events[0]["relative_time"] 
        last_event_time = self.events[-1]["relative_time"]
        total_duration = last_event_time - first_event_time
        
        # Calculate inter-event delays
        delays = []
        for i in range(1, len(self.events)):
            delay = self.events[i]["relative_time"] - self.events[i-1]["relative_time"]
            delays.append(delay)
            
        return {
            "total_duration_seconds": total_duration,
            "average_delay_between_events": sum(delays) / len(delays) if delays else 0,
            "max_delay_between_events": max(delays) if delays else 0,
            "events_per_second": len(self.events) / total_duration if total_duration > 0 else 0,
            "first_event_delay": first_event_time,
            "responsive_ux": first_event_time < 2.0 and max(delays) < 5.0 if delays else False
        }


@pytest.mark.e2e
@pytest.mark.requires_docker
class TestWebSocketEventDeliveryDuringChat(SSotAsyncTestCase):
    """
    CRITICAL: E2E tests for real-time WebSocket event delivery during chat interactions.
    
    These tests validate the complete WebSocket event pipeline that enables users to see
    AI agents working in real-time, building trust through transparency.
    """
    
    def setup_method(self, method=None):
        """Setup with business context and Docker services."""
        super().setup_method(method)
        
        # Business value metrics
        self.record_metric("business_segment", "all_segments")
        self.record_metric("test_type", "e2e_websocket_events")
        self.record_metric("expected_business_value", "real_time_chat_transparency")
        
        # Initialize test components
        self._auth_helper = None
        self._websocket_helper = None
        self._docker_manager = None
        self._event_collector = None
        
    async def async_setup_method(self, method=None):
        """Async setup for E2E WebSocket testing with Docker services."""
        await super().async_setup_method(method)
        
        # Initialize Docker manager for real services
        self._docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        
        # Start required services for E2E testing
        if self._docker_manager.is_docker_available():
            await self._docker_manager.start_services(['backend', 'auth', 'redis'])
            await asyncio.sleep(5)  # Allow services to initialize
            
        # Initialize auth helpers for E2E environment
        environment = self.get_env_var("TEST_ENV", "test")
        self._websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Initialize event collector
        self._event_collector = WebSocketEventCollector()
        
    @pytest.mark.asyncio
    async def test_complete_websocket_event_sequence_during_ai_chat_processing(self):
        """
        Test complete WebSocket event sequence during AI chat processing with REAL services.
        
        CRITICAL: This validates the CORE business value delivery mechanism:
        User Message → WebSocket Events Show AI Working → User Trusts System → Business Value
        
        Business Value: Validates real-time transparency that builds user trust in AI system.
        """
        # Arrange - Create authenticated user with WebSocket connection
        user_context = await create_authenticated_user_context(
            user_email="websocket_test_user@example.com",
            environment="test",
            permissions=["read", "write", "execute_agents", "websocket_access"],
            websocket_enabled=True
        )
        
        # Establish REAL WebSocket connection with authentication
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        headers = self._websocket_helper.get_websocket_headers()
        
        self.logger.info(f"🔌 Connecting to WebSocket: {websocket_url}")
        
        # Act - Connect and send business problem requiring AI processing
        async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
            
            # Send chat message that requires multi-stage AI processing
            chat_request = {
                "type": "chat_message",
                "content": "Analyze my cloud infrastructure costs and provide detailed optimization recommendations with specific savings estimates",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requires_comprehensive_analysis": True,
                "expected_processing_stages": ["triage", "data_analysis", "optimization", "reporting"]
            }
            
            await websocket.send(json.dumps(chat_request))
            self.logger.info(f"📤 Sent chat request for comprehensive AI analysis")
            
            # Collect WebSocket events with timeout for complete processing
            event_collection_timeout = 60.0  # Allow time for comprehensive analysis
            collection_start = time.time()
            
            while (time.time() - collection_start) < event_collection_timeout:
                try:
                    # Receive WebSocket events with short timeout for responsiveness
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(event_data)
                    
                    self._event_collector.add_event(event)
                    self.logger.info(f"📨 Received: {event.get('type', 'unknown')} event")
                    
                    # Stop collecting when we receive final completion event
                    if event.get("type") == "agent_completed" and event.get("final", False):
                        self.logger.info(f"✅ Received final completion event")
                        break
                        
                except asyncio.TimeoutError:
                    # Check if we have sufficient events for validation
                    if len(self._event_collector.events) >= 3:
                        self.logger.info(f"⏰ Timeout but sufficient events collected: {len(self._event_collector.events)}")
                        break
                    continue
                except Exception as e:
                    self.logger.error(f"❌ Error receiving WebSocket event: {e}")
                    break
        
        # Assert - Validate all 5 REQUIRED WebSocket events were received
        required_events = [
            "agent_started",     # User sees AI begins processing
            "agent_thinking",    # User sees AI reasoning process  
            "tool_executing",    # User sees AI using tools
            "tool_completed",    # User sees tool results
            "agent_completed"    # User sees AI finished with results
        ]
        
        validation_result = self._event_collector.validate_required_events(required_events)
        
        # CRITICAL: All required events must be present for business value
        self.assertTrue(validation_result["all_required_present"],
            f"CRITICAL FAILURE: Missing required WebSocket events: {validation_result['missing_events']}. "
            f"This breaks real-time chat transparency. Received: {validation_result['received_events']}")
        
        # Validate timing for responsive UX
        timing_analysis = self._event_collector.get_timing_analysis()
        
        # First event must arrive quickly for responsiveness
        self.assertLess(timing_analysis["first_event_delay"], 3.0,
            f"First WebSocket event took {timing_analysis['first_event_delay']:.2f}s - too slow for responsive UX")
        
        # Events should arrive regularly without long gaps
        self.assertLess(timing_analysis["max_delay_between_events"], 10.0,
            f"Max delay between events: {timing_analysis['max_delay_between_events']:.2f}s - too long for smooth UX")
        
        # Validate business content in events
        agent_started_events = self._event_collector.get_events_by_type("agent_started")
        self.assertGreater(len(agent_started_events), 0, "Must have agent_started events")
        
        thinking_events = self._event_collector.get_events_by_type("agent_thinking")
        self.assertGreater(len(thinking_events), 0, "Must have agent_thinking events for transparency")
        
        # Validate events contain business context
        all_event_content = " ".join([str(event) for event in self._event_collector.events])
        business_indicators = ["cost", "optimization", "analysis", "infrastructure"]
        
        found_indicators = [indicator for indicator in business_indicators 
                           if indicator.lower() in all_event_content.lower()]
        
        self.assertGreaterEqual(len(found_indicators), 2,
            f"WebSocket events must contain business context. Found: {found_indicators}")
        
        # Record business value metrics
        self.record_metric("total_events_received", len(self._event_collector.events))
        self.record_metric("required_events_present", validation_result["all_required_present"])
        self.record_metric("first_event_delay_seconds", timing_analysis["first_event_delay"])
        self.record_metric("responsive_ux_achieved", timing_analysis["responsive_ux"])
        self.record_metric("business_context_indicators", len(found_indicators))
        
        self.logger.info(f"✅ WebSocket event delivery validated: {len(self._event_collector.events)} events, "
                        f"responsive UX: {timing_analysis['responsive_ux']}")
    
    @pytest.mark.asyncio  
    async def test_websocket_event_delivery_under_concurrent_chat_load(self):
        """
        Test WebSocket event delivery remains reliable under concurrent chat load.
        
        CRITICAL: This validates system can maintain real-time UX under business load:
        Multiple Users → Concurrent Chat → All Get Real-Time Events → Business Value Protected
        
        Business Value: Ensures chat transparency scales with user growth (revenue protection).
        """
        # Arrange - Create multiple authenticated users for concurrent testing
        concurrent_users = 3  # Moderate load for E2E testing
        user_contexts = []
        websocket_connections = []
        event_collectors = []
        
        for i in range(concurrent_users):
            user_context = await create_authenticated_user_context(
                user_email=f"concurrent_user_{i}@example.com",
                environment="test",
                permissions=["read", "write", "execute_agents", "websocket_access"],
                websocket_enabled=True
            )
            user_contexts.append(user_context)
            event_collectors.append(WebSocketEventCollector())
        
        # Establish concurrent WebSocket connections
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        try:
            # Create concurrent WebSocket connections
            connection_tasks = []
            for i, user_context in enumerate(user_contexts):
                headers = self._websocket_helper.get_websocket_headers()
                connection_task = websockets.connect(websocket_url, additional_headers=headers)
                connection_tasks.append(connection_task)
            
            websocket_connections = await asyncio.gather(*connection_tasks)
            self.logger.info(f"🔌 Established {len(websocket_connections)} concurrent WebSocket connections")
            
            # Act - Send concurrent chat messages requiring AI processing
            chat_tasks = []
            
            for i, (websocket, user_context) in enumerate(zip(websocket_connections, user_contexts)):
                chat_request = {
                    "type": "chat_message", 
                    "content": f"User {i}: Analyze my API usage patterns and suggest cost optimization strategies",
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_index": i,
                    "requires_analysis": True
                }
                
                chat_task = asyncio.create_task(websocket.send(json.dumps(chat_request)))
                chat_tasks.append(chat_task)
            
            # Send all messages concurrently
            await asyncio.gather(*chat_tasks)
            self.logger.info(f"📤 Sent {len(chat_tasks)} concurrent chat requests")
            
            # Collect events from all connections concurrently
            collection_timeout = 45.0
            collection_tasks = []
            
            for i, (websocket, collector) in enumerate(zip(websocket_connections, event_collectors)):
                collection_task = asyncio.create_task(
                    self._collect_events_for_user(websocket, collector, i, collection_timeout)
                )
                collection_tasks.append(collection_task)
            
            # Wait for all event collection to complete
            await asyncio.gather(*collection_tasks, return_exceptions=True)
            
        finally:
            # Cleanup WebSocket connections
            cleanup_tasks = []
            for websocket in websocket_connections:
                if websocket and not websocket.closed:
                    cleanup_tasks.append(asyncio.create_task(websocket.close()))
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Assert - Validate all users received their WebSocket events
        required_events = ["agent_started", "agent_thinking", "agent_completed"]
        
        for i, collector in enumerate(event_collectors):
            user_validation = collector.validate_required_events(required_events)
            
            self.assertTrue(user_validation["all_required_present"],
                f"User {i} missing required events: {user_validation['missing_events']}. "
                f"Concurrent load must not break individual user event delivery.")
            
            # Validate timing remained responsive under load
            timing_analysis = collector.get_timing_analysis()
            self.assertLess(timing_analysis["first_event_delay"], 5.0,
                f"User {i} first event delay: {timing_analysis['first_event_delay']:.2f}s - too slow under load")
        
        # Validate system-wide metrics
        total_events = sum(len(collector.events) for collector in event_collectors)
        successful_users = sum(1 for collector in event_collectors 
                              if collector.validate_required_events(required_events)["all_required_present"])
        
        self.assertEqual(successful_users, concurrent_users,
            f"All {concurrent_users} users must receive events. Only {successful_users} successful.")
        
        # Business continuity validation
        self.assertGreaterEqual(total_events, concurrent_users * 3,
            f"Expected minimum {concurrent_users * 3} events, got {total_events}")
        
        # Record concurrent performance metrics
        self.record_metric("concurrent_users", concurrent_users)
        self.record_metric("total_events_all_users", total_events)
        self.record_metric("successful_users", successful_users)
        self.record_metric("events_per_user_avg", total_events / concurrent_users)
        
        self.logger.info(f"✅ Concurrent WebSocket event delivery validated: "
                        f"{successful_users}/{concurrent_users} users successful, {total_events} total events")
    
    # Helper Methods
    
    async def _collect_events_for_user(self, websocket, collector: WebSocketEventCollector, 
                                     user_index: int, timeout: float) -> None:
        """Collect WebSocket events for a specific user during concurrent testing."""
        collection_start = time.time()
        events_received = 0
        
        try:
            while (time.time() - collection_start) < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(event_data)
                    
                    collector.add_event(event)
                    events_received += 1
                    
                    # Stop when we receive completion event
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    if events_received >= 3:  # Minimum for validation
                        break
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error collecting events for user {user_index}: {e}")
        
        self.logger.info(f"User {user_index}: Collected {events_received} events")
    
    async def async_teardown_method(self, method=None):
        """Cleanup Docker services and connections."""
        if self._docker_manager and self._docker_manager.is_docker_available():
            try:
                await self._docker_manager.stop_services(['backend', 'auth', 'redis'])
            except Exception as e:
                self.logger.warning(f"Error stopping Docker services: {e}")
        
        await super().async_teardown_method(method)
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        super().teardown_method(method)
        
        # Clear event collectors
        if self._event_collector:
            self._event_collector.events.clear()
            
        self.logger.info(f"✅ WebSocket event delivery E2E test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])