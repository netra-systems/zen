"""
Business-Critical WebSocket Events Validation for Staging - Issue #1176
======================================================================

MISSION CRITICAL: Validate all 5 business-critical WebSocket events are delivered
reliably on staging environment, protecting $500K+ ARR chat functionality.

BUSINESS IMPACT: These events provide transparency and trust in AI processing:
- agent_started: User sees AI began work (engagement)
- agent_thinking: Real-time reasoning (trust building) 
- tool_executing: Tool transparency (process understanding)
- tool_completed: Tool results (progress satisfaction)
- agent_completed: Final results ready (conversion)

TARGET: Real staging WebSocket validation at wss://api.staging.netrasystems.ai/ws

PURPOSE: Ensure WebSocket event delivery works reliably under staging Cloud Run
conditions and identify any event delivery failures blocking user experience.
"""

import asyncio
import json
import time
import pytest
import websockets
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
import httpx

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


@dataclass
class WebSocketEventTracker:
    """Track WebSocket events with timing and validation."""
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    start_time: float = field(default_factory=time.time)
    error_count: int = 0
    
    def add_event(self, event_data: Dict[str, Any]):
        """Add an event to tracking."""
        timestamp = time.time()
        event_type = event_data.get("type")
        
        self.events_received.append({
            **event_data,
            "received_timestamp": timestamp,
            "elapsed_time": timestamp - self.start_time
        })
        
        if event_type:
            self.event_types_seen.add(event_type)
    
    def has_all_required_events(self, required_events: Set[str]) -> bool:
        """Check if all required events were received."""
        return required_events.issubset(self.event_types_seen)
    
    def get_missing_events(self, required_events: Set[str]) -> Set[str]:
        """Get list of missing required events."""
        return required_events - self.event_types_seen
    
    def get_event_sequence(self) -> List[str]:
        """Get sequence of event types received."""
        return [event.get("type") for event in self.events_received]
    
    def get_event_timing(self) -> Dict[str, float]:
        """Get timing for each event type."""
        timing = {}
        for event in self.events_received:
            event_type = event.get("type")
            if event_type and event_type not in timing:
                timing[event_type] = event.get("elapsed_time", 0)
        return timing


@pytest.mark.e2e
class WebSocketEventsBusinessCriticalStagingTests(SSotAsyncTestCase):
    """
    Comprehensive validation of business-critical WebSocket events on staging.
    
    These tests focus specifically on the 5 WebSocket events that are essential
    for user experience and business value in the Golden Path.
    """

    # Staging configuration
    STAGING_AUTH_URL = "https://auth.staging.netrasystems.ai"
    STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"
    
    # Business-critical events in expected order
    REQUIRED_EVENTS = {
        "agent_started",      # AI begins processing
        "agent_thinking",     # Real-time updates  
        "tool_executing",     # Tool usage starts
        "tool_completed",     # Tool usage ends
        "agent_completed"     # AI processing complete
    }
    
    # Expected event sequence (some events may repeat)
    EXPECTED_EVENT_ORDER = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]
    
    # Business value metrics
    MAX_EVENT_DELAY = 30.0  # Max seconds for event delivery
    MAX_TOTAL_TIME = 120.0  # Max total time for all events
    MIN_TRANSPARENCY_SCORE = 80.0  # Min percentage for user transparency

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for WebSocket tests"""
        return UserExecutionContext.from_request(
            user_id="ws_events_test_user",
            thread_id="ws_events_test_thread",
            run_id="ws_events_test_run"
        )

    def setup_method(self, method):
        """Set up WebSocket events validation tests."""
        super().setup_method(method)
        self.auth_token = None
        self.user_id = None

    async def _authenticate_staging_user(self) -> str:
        """Authenticate with staging environment and return JWT token."""
        if self.auth_token:
            return self.auth_token
            
        async with httpx.AsyncClient(timeout=15.0) as client:
            auth_payload = {
                "simulation_key": "staging-e2e-test-bypass-key-2025",
                "email": "websocket-events-test@staging.netrasystems.ai"
            }
            
            auth_response = await client.post(
                f"{self.STAGING_AUTH_URL}/auth/e2e/test-auth",
                headers={"Content-Type": "application/json"},
                json=auth_payload
            )
            
            if auth_response.status_code != 200:
                raise Exception(f"Authentication failed: {auth_response.status_code}")
            
            auth_data = auth_response.json()
            self.auth_token = auth_data["access_token"]
            self.user_id = auth_data["user_id"]
            
            return self.auth_token

    async def test_all_business_critical_events_delivered_staging(self):
        """
        P0 CRITICAL: Validate all 5 business-critical WebSocket events are delivered.
        
        This is the fundamental test for Golden Path WebSocket functionality.
        All 5 events MUST be delivered for proper user experience.
        """
        auth_token = await self._authenticate_staging_user()
        event_tracker = WebSocketEventTracker()
        
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            async with websockets.connect(
                self.STAGING_WS_URL,
                additional_headers=headers,
                timeout=30.0
            ) as websocket:
                
                # Wait for connection ready
                welcome_message = await asyncio.wait_for(
                    websocket.recv(), timeout=10.0
                )
                welcome_data = json.loads(welcome_message)
                
                self.assertEqual(
                    welcome_data.get("type"), "connection_ready",
                    f"Expected connection_ready, got: {welcome_data}"
                )
                
                # Send message that will trigger all events
                test_message = {
                    "type": "user_message",
                    "text": "Analyze Netra Apex AI optimization capabilities and show me the process",
                    "thread_id": f"events_test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                event_tracker.start_time = time.time()
                
                # Collect events until complete or timeout
                while time.time() - event_tracker.start_time < self.MAX_TOTAL_TIME:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(), timeout=10.0
                        )
                        
                        message_data = json.loads(message)
                        event_tracker.add_event(message_data)
                        
                        # Check if we have all required events
                        if event_tracker.has_all_required_events(self.REQUIRED_EVENTS):
                            # Wait a bit more to see if we get final response
                            try:
                                final_message = await asyncio.wait_for(
                                    websocket.recv(), timeout=5.0
                                )
                                final_data = json.loads(final_message)
                                event_tracker.add_event(final_data)
                                
                                if final_data.get("type") == "assistant_message":
                                    break
                            except asyncio.TimeoutError:
                                break
                        
                    except asyncio.TimeoutError:
                        # No message for 10 seconds, check if we're done
                        if event_tracker.has_all_required_events(self.REQUIRED_EVENTS):
                            break
                        continue
                
                # Validate all required events were received
                missing_events = event_tracker.get_missing_events(self.REQUIRED_EVENTS)
                
                self.assertEqual(
                    len(missing_events), 0,
                    f"MISSING BUSINESS-CRITICAL WEBSOCKET EVENTS:\n"
                    f"Required events: {self.REQUIRED_EVENTS}\n"
                    f"Missing events: {missing_events}\n"
                    f"Events received: {event_tracker.event_types_seen}\n"
                    f"Event sequence: {event_tracker.get_event_sequence()}\n"
                    f"Event timing: {event_tracker.get_event_timing()}\n"
                    f"\nMissing events break user experience and reduce business value.\n"
                    f"Users cannot see AI processing transparency without these events."
                )
                
                # Validate event timing is reasonable
                event_timing = event_tracker.get_event_timing()
                total_time = max(event_timing.values()) if event_timing else 0
                
                self.assertLessEqual(
                    total_time, self.MAX_TOTAL_TIME,
                    f"WEBSOCKET EVENTS TOO SLOW:\n"
                    f"Total time: {total_time:.1f}s\n"
                    f"Max allowed: {self.MAX_TOTAL_TIME}s\n"
                    f"Event timing: {event_timing}\n"
                    f"Slow events hurt user experience and perceived performance."
                )
                
        except Exception as e:
            self.fail(
                f"BUSINESS-CRITICAL WEBSOCKET EVENTS TEST FAILED:\n"
                f"Error: {str(e)}\n"
                f"Events received: {event_tracker.get_event_sequence()}\n"
                f"This completely breaks Golden Path user experience."
            )

    async def test_websocket_events_proper_sequence_staging(self):
        """
        P1 HIGH: Validate WebSocket events are delivered in proper sequence.
        
        Events should follow logical order for optimal user experience.
        Out-of-order events can confuse users about AI processing state.
        """
        auth_token = await self._authenticate_staging_user()
        event_tracker = WebSocketEventTracker()
        
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            async with websockets.connect(
                self.STAGING_WS_URL,
                additional_headers=headers,
                timeout=30.0
            ) as websocket:
                
                # Connection setup
                await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                # Send message
                test_message = {
                    "type": "user_message",
                    "text": "What are the key features of Netra Apex?",
                    "thread_id": f"sequence_test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                event_tracker.start_time = time.time()
                
                # Collect events
                while time.time() - event_tracker.start_time < 60.0:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                        message_data = json.loads(message)
                        event_tracker.add_event(message_data)
                        
                        if message_data.get("type") == "assistant_message":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                # Analyze event sequence
                event_sequence = event_tracker.get_event_sequence()
                business_events = [
                    event for event in event_sequence 
                    if event in self.REQUIRED_EVENTS
                ]
                
                # Validate we got business events
                self.assertGreater(
                    len(business_events), 0,
                    f"NO BUSINESS-CRITICAL EVENTS RECEIVED:\n"
                    f"All events: {event_sequence}\n"
                    f"This indicates complete failure of event system."
                )
                
                # Validate agent_started comes first among business events
                if "agent_started" in business_events:
                    first_business_event = business_events[0]
                    self.assertEqual(
                        first_business_event, "agent_started",
                        f"WRONG EVENT SEQUENCE - agent_started should be first:\n"
                        f"Business events: {business_events}\n"
                        f"First business event: {first_business_event}\n"
                        f"Proper sequence improves user experience."
                    )
                
                # Validate agent_completed comes last among business events
                if "agent_completed" in business_events:
                    last_business_event = business_events[-1]
                    self.assertEqual(
                        last_business_event, "agent_completed",
                        f"WRONG EVENT SEQUENCE - agent_completed should be last:\n"
                        f"Business events: {business_events}\n"
                        f"Last business event: {last_business_event}\n"
                        f"Proper sequence provides clear completion signal."
                    )
                
        except Exception as e:
            self.fail(
                f"WEBSOCKET EVENT SEQUENCE TEST FAILED:\n"
                f"Error: {str(e)}\n"
                f"This affects user experience quality."
            )

    async def test_websocket_events_content_quality_staging(self):
        """
        P1 HIGH: Validate WebSocket events contain meaningful content.
        
        Events should provide useful information to users, not just notifications.
        Empty or generic events reduce transparency and trust.
        """
        auth_token = await self._authenticate_staging_user()
        event_tracker = WebSocketEventTracker()
        
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            async with websockets.connect(
                self.STAGING_WS_URL,
                additional_headers=headers,
                timeout=30.0
            ) as websocket:
                
                # Connection setup
                await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                # Send detailed question to get rich events
                test_message = {
                    "type": "user_message",
                    "text": "Explain how Netra Apex optimizes AI infrastructure costs and performance",
                    "thread_id": f"content_test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Collect events
                while time.time() - event_tracker.start_time < 90.0:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        message_data = json.loads(message)
                        event_tracker.add_event(message_data)
                        
                        if message_data.get("type") == "assistant_message":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                # Analyze event content quality
                content_quality_issues = []
                
                for event in event_tracker.events_received:
                    event_type = event.get("type")
                    
                    if event_type in self.REQUIRED_EVENTS:
                        # Check for meaningful content
                        event_content = event.get("content", "")
                        event_message = event.get("message", "")
                        event_text = event.get("text", "")
                        
                        content_length = len(str(event_content) + str(event_message) + str(event_text))
                        
                        if content_length < 10:
                            content_quality_issues.append({
                                "event_type": event_type,
                                "issue": "too_short",
                                "content_length": content_length,
                                "event_data": event
                            })
                        
                        # Check for generic/placeholder content
                        combined_content = (str(event_content) + str(event_message) + str(event_text)).lower()
                        generic_phrases = ["processing", "working", "loading", "please wait"]
                        
                        if any(phrase in combined_content for phrase in generic_phrases):
                            content_quality_issues.append({
                                "event_type": event_type,
                                "issue": "generic_content",
                                "content": combined_content[:100]
                            })
                
                # Validate content quality
                self.assertLessEqual(
                    len(content_quality_issues), 2,
                    f"WEBSOCKET EVENT CONTENT QUALITY ISSUES:\n"
                    f"Quality issues: {content_quality_issues}\n"
                    f"Events should provide meaningful information to users.\n"
                    f"Poor content quality reduces user trust and transparency."
                )
                
        except Exception as e:
            self.fail(
                f"WEBSOCKET EVENT CONTENT QUALITY TEST FAILED:\n"
                f"Error: {str(e)}\n"
                f"This affects user experience and trust."
            )

    async def test_websocket_events_reliability_under_staging_load(self):
        """
        P1 HIGH: Test WebSocket event reliability under staging load conditions.
        
        Events must be delivered reliably even when staging environment
        experiences load or Cloud Run scaling events.
        """
        auth_token = await self._authenticate_staging_user()
        
        # Test multiple concurrent sessions
        concurrent_sessions = 3
        session_results = []
        
        async def test_session(session_id: int):
            """Test a single WebSocket session."""
            session_tracker = WebSocketEventTracker()
            
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                
                async with websockets.connect(
                    self.STAGING_WS_URL,
                    additional_headers=headers,
                    timeout=30.0
                ) as websocket:
                    
                    # Connection setup
                    await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    
                    # Send message
                    test_message = {
                        "type": "user_message",
                        "text": f"Session {session_id}: Analyze AI optimization strategies",
                        "thread_id": f"load_test_{session_id}_{int(time.time())}"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    session_tracker.start_time = time.time()
                    
                    # Collect events
                    while time.time() - session_tracker.start_time < 60.0:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                            message_data = json.loads(message)
                            session_tracker.add_event(message_data)
                            
                            if message_data.get("type") == "assistant_message":
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                    
                    # Analyze session results
                    missing_events = session_tracker.get_missing_events(self.REQUIRED_EVENTS)
                    
                    return {
                        "session_id": session_id,
                        "success": len(missing_events) == 0,
                        "missing_events": list(missing_events),
                        "events_received": list(session_tracker.event_types_seen),
                        "total_events": len(session_tracker.events_received),
                        "timing": session_tracker.get_event_timing()
                    }
                    
            except Exception as e:
                return {
                    "session_id": session_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Run concurrent sessions
        tasks = [test_session(i) for i in range(concurrent_sessions)]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze reliability
        successful_sessions = [
            result for result in session_results 
            if isinstance(result, dict) and result.get("success")
        ]
        
        reliability_rate = (len(successful_sessions) / len(session_results)) * 100
        
        self.assertGreaterEqual(
            reliability_rate, 80.0,
            f"WEBSOCKET EVENT RELIABILITY TOO LOW UNDER LOAD:\n"
            f"Reliability rate: {reliability_rate:.1f}%\n"
            f"Successful sessions: {len(successful_sessions)}/{len(session_results)}\n"
            f"Session results: {session_results}\n"
            f"Event delivery must be reliable under production-like load."
        )
        
        # Validate at least some sessions got all events
        complete_sessions = [
            result for result in successful_sessions
            if len(result.get("missing_events", [])) == 0
        ]
        
        self.assertGreater(
            len(complete_sessions), 0,
            f"NO SESSIONS GOT ALL REQUIRED EVENTS:\n"
            f"This indicates systematic event delivery failure under load.\n"
            f"Session results: {session_results}"
        )

    async def test_websocket_events_business_value_metrics(self):
        """
        P2 MEDIUM: Validate WebSocket events meet business value metrics.
        
        Events should provide measurable business value through user engagement,
        transparency, and trust-building features.
        """
        auth_token = await self._authenticate_staging_user()
        event_tracker = WebSocketEventTracker()
        
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            async with websockets.connect(
                self.STAGING_WS_URL,
                additional_headers=headers,
                timeout=30.0
            ) as websocket:
                
                # Connection setup
                await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                # Send business-relevant message
                test_message = {
                    "type": "user_message",
                    "text": "How can Netra Apex help me reduce AI infrastructure costs by 30%?",
                    "thread_id": f"business_value_test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                event_tracker.start_time = time.time()
                
                # Collect events with business value analysis
                while time.time() - event_tracker.start_time < 90.0:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        message_data = json.loads(message)
                        event_tracker.add_event(message_data)
                        
                        if message_data.get("type") == "assistant_message":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                # Calculate business value metrics
                business_value_metrics = self._calculate_business_value_metrics(event_tracker)
                
                # Validate transparency score
                self.assertGreaterEqual(
                    business_value_metrics["transparency_score"], self.MIN_TRANSPARENCY_SCORE,
                    f"WEBSOCKET EVENTS TRANSPARENCY SCORE TOO LOW:\n"
                    f"Transparency score: {business_value_metrics['transparency_score']:.1f}%\n"
                    f"Minimum required: {self.MIN_TRANSPARENCY_SCORE}%\n"
                    f"Metrics: {business_value_metrics}\n"
                    f"Low transparency reduces user trust and business value."
                )
                
                # Validate engagement indicators
                self.assertGreater(
                    business_value_metrics["engagement_events"], 2,
                    f"INSUFFICIENT USER ENGAGEMENT EVENTS:\n"
                    f"Engagement events: {business_value_metrics['engagement_events']}\n"
                    f"Users need multiple engagement touchpoints for optimal experience."
                )
                
        except Exception as e:
            self.fail(
                f"WEBSOCKET EVENTS BUSINESS VALUE TEST FAILED:\n"
                f"Error: {str(e)}\n"
                f"This affects revenue and user retention."
            )

    def _calculate_business_value_metrics(self, event_tracker: WebSocketEventTracker) -> Dict[str, Any]:
        """Calculate business value metrics for WebSocket events."""
        required_events_received = len(event_tracker.event_types_seen & self.REQUIRED_EVENTS)
        transparency_score = (required_events_received / len(self.REQUIRED_EVENTS)) * 100
        
        engagement_events = sum(1 for event in event_tracker.events_received 
                              if event.get("type") in ["agent_thinking", "tool_executing"])
        
        total_events = len(event_tracker.events_received)
        event_richness = sum(1 for event in event_tracker.events_received 
                           if len(str(event.get("content", ""))) > 20)
        
        timing = event_tracker.get_event_timing()
        responsiveness_score = 100.0
        if timing:
            avg_delay = sum(timing.values()) / len(timing)
            responsiveness_score = max(0, 100 - (avg_delay / self.MAX_EVENT_DELAY) * 100)
        
        return {
            "transparency_score": transparency_score,
            "engagement_events": engagement_events,
            "total_events": total_events,
            "event_richness": event_richness,
            "responsiveness_score": responsiveness_score,
            "events_received": list(event_tracker.event_types_seen),
            "missing_events": list(self.REQUIRED_EVENTS - event_tracker.event_types_seen)
        }


if __name__ == "__main__":
    import unittest
    unittest.main()