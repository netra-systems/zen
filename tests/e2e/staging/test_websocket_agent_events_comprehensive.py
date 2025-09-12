#!/usr/bin/env python
"""
WebSocket Agent Events Comprehensive E2E Tests for Staging

Business Value Justification (BVJ):
- Segment: Platform/Internal + All Customer Tiers
- Business Goal: Ensure mission-critical WebSocket event delivery for real-time AI value
- Value Impact: Enables $500K+ ARR through transparent AI agent execution visibility
- Strategic/Revenue Impact: Prevents customer churn from poor real-time experience

This test suite validates ALL 5 required WebSocket events for agent execution:
1. agent_started - User sees agent began processing their problem  
2. agent_thinking - Real-time reasoning visibility (shows AI working on valuable solutions)
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User knows when valuable response is ready

 ALERT:  MISSION CRITICAL: These events enable substantive chat interactions - core business value!

 ALERT:  CRITICAL E2E REQUIREMENTS:
- ALL tests use real authentication (JWT/OAuth) - NO EXCEPTIONS
- Real WebSocket connections to staging services
- Validate ALL 5 WebSocket events in correct sequence
- Test event delivery timing and content quality
- Validate multi-user WebSocket isolation
- Real agent execution with LLM integration
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
import pytest
import websockets
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

# Import E2E auth helper for SSOT authentication
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper,
    create_authenticated_user_context,
    E2EAuthConfig
)
from test_framework.base_e2e_test import BaseE2ETest
from tests.e2e.staging_config import StagingTestConfig, get_staging_config

logger = logging.getLogger(__name__)


@dataclass
class WebSocketEventSequence:
    """Tracks WebSocket event sequence for validation."""
    events: List[Dict[str, Any]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add event with timing information."""
        event_with_timing = {
            **event,
            "capture_timestamp": time.time(),
            "relative_time": time.time() - self.start_time
        }
        self.events.append(event_with_timing)
    
    def get_event_types(self) -> List[str]:
        """Get list of event types in order."""
        return [event.get("type", "unknown") for event in self.events]
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of specific type."""
        return [event for event in self.events if event.get("type") == event_type]
    
    def validate_required_sequence(self) -> Tuple[bool, List[str]]:
        """Validate all 5 required events are present."""
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        event_types = self.get_event_types()
        missing_events = [event for event in required_events if event not in event_types]
        return len(missing_events) == 0, missing_events
    
    def get_execution_duration(self) -> float:
        """Get total execution duration from start to completion."""
        if not self.events:
            return 0.0
        return self.events[-1]["relative_time"]


class TestWebSocketAgentEventsComprehensive(BaseE2ETest):
    """
    Comprehensive WebSocket Agent Events E2E Tests for Staging Environment.
    
    Tests all aspects of WebSocket event delivery that enable real-time AI value.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_websocket_testing_environment(self):
        """Set up staging environment with WebSocket-specific configuration."""
        await self.initialize_test_environment()
        
        # Configure for staging environment
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment="staging")
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Validate staging configuration
        assert self.staging_config.validate_configuration(), "Staging configuration invalid"
        
        # Pre-authenticate users for WebSocket testing
        self.test_users = []
        for i in range(5):  # More users for comprehensive WebSocket testing
            user_context = await create_authenticated_user_context(
                user_email=f"e2e_ws_events_test_{i}_{int(time.time())}@staging.netra.ai",
                environment="staging",
                permissions=["read", "write", "execute_agents", "websocket_connect"]
            )
            self.test_users.append(user_context)
        
        # WebSocket event tracking
        self.event_sequences: Dict[str, WebSocketEventSequence] = {}
        
        self.logger.info(f" PASS:  WebSocket testing environment setup complete - {len(self.test_users)} authenticated users")
        
    async def test_all_five_required_websocket_events_authenticated(self):
        """
        Test that ALL 5 required WebSocket events are delivered for agent execution.
        
        BVJ: Validates core $500K+ ARR real-time AI transparency value proposition
        MISSION CRITICAL: These events enable substantive chat interactions
        """
        user_context = self.test_users[0]
        
        # Create authenticated WebSocket connection
        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        self.register_cleanup_task(lambda: asyncio.create_task(websocket.close()))
        
        # Initialize event sequence tracking
        event_sequence = WebSocketEventSequence(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id
        )
        
        # Collect WebSocket events
        async def collect_all_events():
            """Collect all WebSocket events during agent execution."""
            try:
                async for message in websocket:
                    event = json.loads(message)
                    event_sequence.add_event(event)
                    
                    # Log event for debugging
                    self.logger.info(f"[U+1F4E8] WebSocket Event: {event.get('type')} - {event.get('data', {}).get('message', 'No message')}")
                    
                    # Stop collecting after agent completion
                    if event.get("type") == "agent_completed":
                        break
                        
            except Exception as e:
                self.logger.error(f"Event collection error: {e}")
                raise
        
        # Start event collection
        event_task = asyncio.create_task(collect_all_events())
        
        # Send agent execution request that will trigger all events
        comprehensive_request = {
            "type": "execute_agent",
            "agent_type": "comprehensive_analyzer",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "analysis_type": "full_spectrum",
                "require_tools": True,  # Ensure tool events
                "detailed_reasoning": True,  # Ensure thinking events
                "progress_updates": True,  # Enable progress visibility
                "expected_duration": 20  # Expected 20+ second execution
            },
            "auth": {
                "user_id": user_context.user_id,
                "permissions": user_context.agent_context.get("permissions", [])
            }
        }
        
        await websocket.send(json.dumps(comprehensive_request))
        
        # Wait for agent completion with generous timeout
        try:
            await asyncio.wait_for(event_task, timeout=90.0)
        except asyncio.TimeoutError:
            pytest.fail(f"WebSocket event collection timed out. Events received: {event_sequence.get_event_types()}")
        
        # CRITICAL VALIDATION: All 5 required events must be present
        is_valid, missing_events = event_sequence.validate_required_sequence()
        
        if not is_valid:
            received_types = event_sequence.get_event_types()
            self.logger.error(f" FAIL:  Missing required WebSocket events: {missing_events}")
            self.logger.error(f"[U+1F4CB] Events received: {received_types}")
            pytest.fail(f"MISSION CRITICAL FAILURE: Missing required WebSocket events: {missing_events}")
        
        # Validate event content quality and timing
        event_types = event_sequence.get_event_types()
        
        # 1. Validate agent_started event
        started_events = event_sequence.get_events_by_type("agent_started")
        assert len(started_events) == 1, f"Expected exactly 1 agent_started event, got {len(started_events)}"
        assert started_events[0].get("data", {}).get("agent_type"), "agent_started missing agent_type"
        
        # 2. Validate agent_thinking events (should have multiple)
        thinking_events = event_sequence.get_events_by_type("agent_thinking")
        assert len(thinking_events) >= 2, f"Expected at least 2 agent_thinking events, got {len(thinking_events)}"
        
        # Validate thinking content quality
        for thinking_event in thinking_events:
            reasoning = thinking_event.get("data", {}).get("reasoning", "")
            assert len(reasoning) > 20, f"Thinking event has insufficient reasoning content: {len(reasoning)} chars"
        
        # 3. Validate tool_executing events
        tool_executing_events = event_sequence.get_events_by_type("tool_executing")
        assert len(tool_executing_events) >= 1, f"Expected at least 1 tool_executing event, got {len(tool_executing_events)}"
        
        for tool_event in tool_executing_events:
            tool_data = tool_event.get("data", {})
            assert tool_data.get("tool_name"), "tool_executing missing tool_name"
            assert tool_data.get("operation"), "tool_executing missing operation description"
        
        # 4. Validate tool_completed events 
        tool_completed_events = event_sequence.get_events_by_type("tool_completed")
        assert len(tool_completed_events) >= 1, f"Expected at least 1 tool_completed event, got {len(tool_completed_events)}"
        
        for completion_event in tool_completed_events:
            completion_data = completion_event.get("data", {})
            assert completion_data.get("tool_name"), "tool_completed missing tool_name"
            assert "results" in completion_data, "tool_completed missing results"
        
        # 5. Validate agent_completed event
        completed_events = event_sequence.get_events_by_type("agent_completed")
        assert len(completed_events) == 1, f"Expected exactly 1 agent_completed event, got {len(completed_events)}"
        
        completion_data = completed_events[0].get("data", {})
        assert completion_data.get("status") == "completed", "agent_completed status not 'completed'"
        assert "results" in completion_data, "agent_completed missing results"
        
        # Validate event timing and sequence
        execution_duration = event_sequence.get_execution_duration()
        assert execution_duration >= 5.0, f"Expected execution duration >= 5s, got {execution_duration:.1f}s"
        assert execution_duration <= 90.0, f"Execution took too long: {execution_duration:.1f}s"
        
        # Validate event sequence order (agent_started should be first)
        assert event_types[0] == "agent_started", f"First event should be agent_started, got {event_types[0]}"
        assert event_types[-1] == "agent_completed", f"Last event should be agent_completed, got {event_types[-1]}"
        
        self.logger.info(f" PASS:  All 5 required WebSocket events validated successfully")
        self.logger.info(f" CHART:  Total events: {len(event_sequence.events)}")
        self.logger.info(f"[U+23F1][U+FE0F] Execution duration: {execution_duration:.1f}s")
        self.logger.info(f"[U+1F4CB] Event sequence: {'  ->  '.join(event_types)}")
        
    async def test_websocket_event_timing_and_distribution(self):
        """
        Test WebSocket event timing distribution for optimal user experience.
        
        BVJ: Validates $100K+ MRR user experience quality - Real-time responsiveness
        Ensures events are distributed appropriately over execution time
        """
        user_context = self.test_users[0]
        
        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        self.register_cleanup_task(lambda: asyncio.create_task(websocket.close()))
        
        event_sequence = WebSocketEventSequence(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id
        )
        
        async def collect_timed_events():
            async for message in websocket:
                event = json.loads(message)
                event_sequence.add_event(event)
                
                if event.get("type") == "agent_completed":
                    break
        
        event_task = asyncio.create_task(collect_timed_events())
        
        # Request long-running execution to test timing distribution
        timing_request = {
            "type": "execute_agent",
            "agent_type": "timing_analysis",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "execution_duration": "extended",  # Request extended execution
                "progress_frequency": "regular",
                "thinking_updates": "frequent"
            }
        }
        
        await websocket.send(json.dumps(timing_request))
        await asyncio.wait_for(event_task, timeout=75.0)
        
        # Validate event timing distribution
        events = event_sequence.events
        total_duration = event_sequence.get_execution_duration()
        
        # Validate minimum execution time for meaningful distribution
        assert total_duration >= 10.0, f"Execution too short for timing analysis: {total_duration:.1f}s"
        
        # Validate events are distributed over time (not all at once)
        event_times = [event["relative_time"] for event in events]
        
        # Check that events span the execution duration
        time_span = max(event_times) - min(event_times)
        assert time_span >= (total_duration * 0.7), f"Events not well distributed over time: {time_span:.1f}s span vs {total_duration:.1f}s total"
        
        # Validate thinking events are spread out (user sees continuous progress)
        thinking_events = event_sequence.get_events_by_type("agent_thinking")
        if len(thinking_events) >= 3:
            thinking_times = [event["relative_time"] for event in thinking_events]
            min_gap_between_thinking = min(thinking_times[i+1] - thinking_times[i] for i in range(len(thinking_times)-1))
            max_gap_between_thinking = max(thinking_times[i+1] - thinking_times[i] for i in range(len(thinking_times)-1))
            
            # Validate reasonable gaps between thinking events (not too fast, not too slow)
            assert min_gap_between_thinking >= 1.0, f"Thinking events too frequent: min gap {min_gap_between_thinking:.1f}s"
            assert max_gap_between_thinking <= 20.0, f"Thinking events too infrequent: max gap {max_gap_between_thinking:.1f}s"
        
        # Validate first event happens quickly (responsiveness)
        first_event_time = min(event_times)
        assert first_event_time <= 3.0, f"First event too slow: {first_event_time:.1f}s"
        
        self.logger.info(f" PASS:  WebSocket event timing validation completed")
        self.logger.info(f"[U+23F1][U+FE0F] Total duration: {total_duration:.1f}s")
        self.logger.info(f" CHART:  Event distribution span: {time_span:.1f}s")
        self.logger.info(f"[U+1F9E0] Thinking events: {len(thinking_events)}")
        
    async def test_multi_user_websocket_event_isolation(self):
        """
        Test WebSocket event isolation between multiple concurrent users.
        
        BVJ: Validates $200K+ MRR multi-tenant architecture - User isolation
        Ensures WebSocket events are properly isolated between users
        """
        assert len(self.test_users) >= 3, "Need at least 3 users for isolation testing"
        
        user_sequences = {}
        
        async def run_user_websocket_session(user_context, user_index):
            """Run WebSocket session for specific user and track events."""
            try:
                # Each user gets their own WebSocket connection and auth
                user_ws_helper = E2EWebSocketAuthHelper(environment="staging")
                websocket = await user_ws_helper.connect_authenticated_websocket(timeout=20.0)
                
                # Track events for this specific user
                event_sequence = WebSocketEventSequence(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id
                )
                
                async def collect_user_specific_events():
                    async for message in websocket:
                        event = json.loads(message)
                        event_sequence.add_event(event)
                        
                        # Validate event belongs to this user
                        event_user_id = event.get("user_id") or event.get("data", {}).get("user_id")
                        if event_user_id and event_user_id != user_context.user_id:
                            raise Exception(f"User {user_index} received event for different user: {event_user_id}")
                        
                        if event.get("type") == "agent_completed":
                            break
                
                event_task = asyncio.create_task(collect_user_specific_events())
                
                # Send user-specific request
                user_request = {
                    "type": "execute_agent",
                    "agent_type": "isolation_test",
                    "user_id": user_context.user_id,
                    "thread_id": user_context.thread_id,
                    "request_id": user_context.request_id,
                    "data": {
                        "user_identifier": f"user_{user_index}",
                        "isolation_test": True,
                        "unique_data": f"data_for_user_{user_index}"
                    }
                }
                
                await websocket.send(json.dumps(user_request))
                await asyncio.wait_for(event_task, timeout=60.0)
                await websocket.close()
                
                return {
                    "user_id": user_context.user_id,
                    "user_index": user_index,
                    "event_sequence": event_sequence,
                    "success": True
                }
                
            except Exception as e:
                return {
                    "user_id": user_context.user_id,
                    "user_index": user_index,
                    "error": str(e),
                    "success": False
                }
        
        # Run concurrent user sessions
        user_tasks = [
            run_user_websocket_session(user_context, i)
            for i, user_context in enumerate(self.test_users[:3])
        ]
        
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Validate all users completed successfully with proper isolation
        successful_users = []
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                successful_users.append(result)
                
                # Validate user got all required events
                event_sequence = result["event_sequence"]
                is_valid, missing_events = event_sequence.validate_required_sequence()
                
                if not is_valid:
                    pytest.fail(f"User {result['user_index']} missing events: {missing_events}")
                
                # Validate events contain user-specific data
                completed_events = event_sequence.get_events_by_type("agent_completed")
                if completed_events:
                    completion_data = completed_events[0].get("data", {})
                    expected_identifier = f"user_{result['user_index']}"
                    actual_identifier = completion_data.get("user_identifier")
                    assert actual_identifier == expected_identifier, f"User isolation failed: expected {expected_identifier}, got {actual_identifier}"
        
        assert len(successful_users) == 3, f"Expected 3 successful users, got {len(successful_users)}"
        
        # Cross-validate no event leakage between users
        all_event_types = set()
        for user_result in successful_users:
            event_sequence = user_result["event_sequence"]
            user_event_types = set(event_sequence.get_event_types())
            all_event_types.update(user_event_types)
            
            # Validate each user got complete event sequence
            required_events = {"agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"}
            user_events = set(event_sequence.get_event_types())
            assert required_events.issubset(user_events), f"User {user_result['user_index']} missing events: {required_events - user_events}"
        
        self.logger.info(f" PASS:  Multi-user WebSocket isolation validation completed")
        self.logger.info(f"[U+1F465] Successful concurrent users: {len(successful_users)}")
        self.logger.info(f"[U+1F4E8] Unique event types across all users: {len(all_event_types)}")
        
    async def test_websocket_reconnection_and_event_continuity(self):
        """
        Test WebSocket reconnection and event continuity during agent execution.
        
        BVJ: Validates $50K+ MRR reliability - Connection resilience  
        Ensures users don't lose agent execution progress during connection issues
        """
        user_context = self.test_users[0]
        
        # Phase 1: Establish initial connection and start agent
        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        
        initial_events = []
        
        # Start long-running agent execution
        long_execution_request = {
            "type": "execute_agent",
            "agent_type": "resilience_test",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "execution_time": "extended",
                "checkpoint_support": True,  # Agent supports checkpointing
                "interruption_recovery": True
            }
        }
        
        await websocket.send(json.dumps(long_execution_request))
        
        # Collect initial events
        event_collection_time = 0
        async for message in websocket:
            event = json.loads(message)
            initial_events.append(event)
            
            event_collection_time += 1
            
            # Simulate connection interruption after getting started events
            if event.get("type") == "agent_thinking" and event_collection_time >= 3:
                break
        
        # Phase 2: Simulate connection loss and reconnection
        await websocket.close()
        
        # Wait brief moment to simulate network interruption
        await asyncio.sleep(2.0)
        
        # Phase 3: Reconnect and continue receiving events
        websocket_reconnected = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        self.register_cleanup_task(lambda: asyncio.create_task(websocket_reconnected.close()))
        
        # Send reconnection request to resume agent execution
        resume_request = {
            "type": "resume_agent",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "resume_from_checkpoint": True
            }
        }
        
        await websocket_reconnected.send(json.dumps(resume_request))
        
        # Collect remaining events after reconnection
        reconnected_events = []
        
        async def collect_remaining_events():
            async for message in websocket_reconnected:
                event = json.loads(message)
                reconnected_events.append(event)
                
                if event.get("type") == "agent_completed":
                    break
        
        try:
            await asyncio.wait_for(collect_remaining_events(), timeout=60.0)
        except asyncio.TimeoutError:
            pytest.fail("Agent execution did not complete after reconnection")
        
        # Validate event continuity and completion
        all_events = initial_events + reconnected_events
        all_event_types = [event.get("type") for event in all_events]
        
        # Validate we got essential events across the disconnection
        assert "agent_started" in all_event_types, "Missing agent_started event"
        assert "agent_completed" in all_event_types, "Missing agent_completed event"
        
        # Validate execution completed despite interruption
        completed_events = [event for event in all_events if event.get("type") == "agent_completed"]
        assert len(completed_events) == 1, f"Expected 1 completion event, got {len(completed_events)}"
        
        completion_data = completed_events[0].get("data", {})
        assert completion_data.get("status") == "completed", "Agent execution did not complete successfully"
        
        # Validate reconnection was transparent to user
        assert "reconnection_successful" in str(completion_data) or completion_data.get("resumed_from_checkpoint"), "No indication of successful reconnection recovery"
        
        self.logger.info(f" PASS:  WebSocket reconnection and continuity validation completed")
        self.logger.info(f" CHART:  Events before disconnection: {len(initial_events)}")
        self.logger.info(f" CYCLE:  Events after reconnection: {len(reconnected_events)}")
        self.logger.info(f"[U+2728] Total event continuity maintained: {len(all_events)} events")
        
    async def test_websocket_event_content_quality_validation(self):
        """
        Test WebSocket event content quality and business value delivery.
        
        BVJ: Validates $200K+ MRR content quality - Meaningful AI interactions
        Ensures events contain high-quality, actionable content for users
        """
        user_context = self.test_users[0]
        
        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
        self.register_cleanup_task(lambda: asyncio.create_task(websocket.close()))
        
        event_sequence = WebSocketEventSequence(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id
        )
        
        async def collect_quality_events():
            async for message in websocket:
                event = json.loads(message)
                event_sequence.add_event(event)
                
                if event.get("type") == "agent_completed":
                    break
        
        event_task = asyncio.create_task(collect_quality_events())
        
        # Request high-quality analysis that should generate rich event content
        quality_request = {
            "type": "execute_agent",
            "agent_type": "content_quality_analyzer",
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_id": user_context.request_id,
            "data": {
                "content_focus": "high_quality",
                "detailed_explanations": True,
                "actionable_insights": True,
                "business_context": True
            }
        }
        
        await websocket.send(json.dumps(quality_request))
        await asyncio.wait_for(event_task, timeout=75.0)
        
        # Validate event content quality
        
        # 1. Validate agent_thinking events have substantial reasoning
        thinking_events = event_sequence.get_events_by_type("agent_thinking")
        assert len(thinking_events) >= 2, "Expected multiple thinking events for quality analysis"
        
        for thinking_event in thinking_events:
            reasoning = thinking_event.get("data", {}).get("reasoning", "")
            assert len(reasoning) >= 50, f"Thinking event reasoning too short: {len(reasoning)} chars"
            
            # Validate reasoning contains business-relevant terms
            business_terms = ["analysis", "optimization", "recommendation", "insight", "value", "improvement", "efficiency"]
            reasoning_lower = reasoning.lower()
            relevant_terms = [term for term in business_terms if term in reasoning_lower]
            assert len(relevant_terms) >= 2, f"Reasoning lacks business relevance. Terms found: {relevant_terms}"
        
        # 2. Validate tool_executing events have clear operation descriptions
        tool_executing_events = event_sequence.get_events_by_type("tool_executing")
        assert len(tool_executing_events) >= 1, "Expected tool execution events"
        
        for tool_event in tool_executing_events:
            tool_data = tool_event.get("data", {})
            operation = tool_data.get("operation", "")
            assert len(operation) >= 20, f"Tool operation description too short: {len(operation)} chars"
            
            tool_name = tool_data.get("tool_name", "")
            assert len(tool_name) >= 3, f"Tool name too short: {tool_name}"
        
        # 3. Validate tool_completed events have meaningful results
        tool_completed_events = event_sequence.get_events_by_type("tool_completed")
        assert len(tool_completed_events) >= 1, "Expected tool completion events"
        
        for completion_event in tool_completed_events:
            completion_data = completion_event.get("data", {})
            results = completion_data.get("results", {})
            
            if isinstance(results, dict):
                assert len(results) >= 1, "Tool results dictionary is empty"
            elif isinstance(results, str):
                assert len(results) >= 30, f"Tool results string too short: {len(results)} chars"
            else:
                assert results is not None, "Tool results are None"
        
        # 4. Validate agent_completed event has comprehensive results
        completed_events = event_sequence.get_events_by_type("agent_completed")
        assert len(completed_events) == 1, "Expected exactly one completion event"
        
        completion_data = completed_events[0].get("data", {})
        results = completion_data.get("results", {})
        
        # Validate comprehensive results structure
        expected_result_keys = ["analysis_summary", "key_insights", "recommendations", "next_steps"]
        result_keys = list(results.keys()) if isinstance(results, dict) else []
        
        matching_keys = [key for key in expected_result_keys if any(expected in key.lower() for expected in key.lower().split('_'))]
        assert len(matching_keys) >= 2, f"Results lack expected business structure. Keys found: {result_keys}"
        
        # 5. Validate overall content coherence and progression
        all_content = []
        for event in event_sequence.events:
            event_data = event.get("data", {})
            if "reasoning" in event_data:
                all_content.append(event_data["reasoning"])
            if "message" in event_data:
                all_content.append(event_data["message"])
            if "operation" in event_data:
                all_content.append(event_data["operation"])
        
        total_content_length = sum(len(content) for content in all_content)
        assert total_content_length >= 500, f"Overall event content too sparse: {total_content_length} chars"
        
        # Validate progression shows logical flow
        content_text = " ".join(all_content).lower()
        progression_indicators = ["analyzing", "executing", "processing", "completing", "finalizing"]
        found_indicators = [ind for ind in progression_indicators if ind in content_text]
        assert len(found_indicators) >= 2, f"Content lacks progression indicators: {found_indicators}"
        
        self.logger.info(f" PASS:  WebSocket event content quality validation completed")
        self.logger.info(f"[U+1F4DD] Total content length: {total_content_length} characters")
        self.logger.info(f"[U+1F9E0] Thinking events: {len(thinking_events)}")
        self.logger.info(f"[U+1F527] Tool events: {len(tool_executing_events)} executing, {len(tool_completed_events)} completed")
        self.logger.info(f"[U+1F4C8] Progression indicators found: {len(found_indicators)}")


# Integration with pytest for automated test discovery
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])