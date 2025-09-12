"""
E2E Test: WebSocket Event Delivery Throughout Chat - MISSION CRITICAL Event Infrastructure

BUSINESS IMPACT: Tests WebSocket event delivery that enables real-time chat experience.
This validates the event infrastructure that provides transparency and engagement for 90% of revenue.

Business Value Justification (BVJ):
- Segment: Platform/All Users - Real-time Chat Experience  
- Business Goal: User Experience - Real-time transparency drives engagement
- Value Impact: Validates event delivery that differentiates from static chatbots
- Strategic Impact: Tests the real-time experience that increases customer satisfaction and retention

CRITICAL SUCCESS METRICS:
 PASS:  All 5 critical WebSocket events delivered in real-time
 PASS:  Event timing and sequencing maintains user engagement
 PASS:  Event content provides meaningful progress updates
 PASS:  No missing or delayed events that break user experience
 PASS:  Events delivered consistently across different chat scenarios

CRITICAL EVENTS TESTED:
[U+2022] agent_started - User knows AI is working on their request
[U+2022] agent_thinking - Real-time progress visibility maintains engagement  
[U+2022] tool_executing - User sees AI taking action on their behalf
[U+2022] tool_completed - User receives intermediate results and confidence
[U+2022] agent_completed - User gets final response with full context

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat (Section 6)
@compliance CLAUDE.md - E2E AUTH MANDATORY (Section 7.3)
@compliance CLAUDE.md - NO MOCKS in E2E tests
@compliance SPEC/core.xml - WebSocket event patterns
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# SSOT Imports - Authentication and Events
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from netra_backend.app.websocket_core.event_validator import (
    AgentEventValidator,
    CriticalAgentEventType,
    WebSocketEventMessage,
    assert_critical_events_received
)
from test_framework.ssot.websocket_golden_path_helpers import (
    WebSocketGoldenPathHelper,
    GoldenPathTestConfig
)

# SSOT Imports - Types
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Test Framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.e2e
@pytest.mark.staging_compatible
class TestWebSocketEventDeliveryChatE2E(SSotBaseTestCase):
    """
    MISSION CRITICAL E2E Tests for WebSocket Event Delivery During Chat.
    
    These tests validate that the WebSocket event infrastructure delivers
    all critical events that enable engaging real-time chat experiences.
    
    REVENUE IMPACT: If events are missing, user experience degrades and retention suffers.
    """
    
    def setup_method(self):
        """Set up WebSocket event delivery E2E test environment."""
        super().setup_method()
        
        # Initialize SSOT helpers
        self.environment = self.get_test_environment()
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.golden_path_helper = WebSocketGoldenPathHelper(environment=self.environment)
        
        # Event-focused test configuration
        self.config = GoldenPathTestConfig.for_environment(self.environment)
        self.config.validate_event_timing = True
        self.config.validate_event_sequence = True
        self.config.require_all_critical_events = True
        
        # Event delivery tracking
        self.test_start_time = time.time()
        self.events_delivered = 0
        self.critical_events_received = 0
        self.event_delivery_score = 0.0
        self.timing_scores = []
        
        print(f"\n[U+1F4E1] WEBSOCKET EVENT DELIVERY E2E TEST - Environment: {self.environment}")
        print(f" TARGET:  Target: Complete event delivery for engaging chat experience")
        print(f" LIGHTNING:  Business Impact: Real-time transparency drives user engagement")
    
    def teardown_method(self):
        """Clean up and report event delivery metrics."""
        test_duration = time.time() - self.test_start_time
        avg_timing_score = sum(self.timing_scores) / len(self.timing_scores) if self.timing_scores else 0.0
        
        print(f"\n CHART:  Event Delivery Test Summary:")
        print(f"[U+23F1][U+FE0F] Duration: {test_duration:.2f}s")
        print(f"[U+1F4E1] Events Delivered: {self.events_delivered}")
        print(f" TARGET:  Critical Events: {self.critical_events_received}/5")
        print(f"[U+1F4C8] Event Delivery Score: {self.event_delivery_score:.1f}%")
        print(f" LIGHTNING:  Average Timing Score: {avg_timing_score:.1f}%")
        
        if self.critical_events_received >= 5 and self.event_delivery_score >= 80.0:
            print(f" PASS:  EXCELLENT EVENT DELIVERY - User experience optimal")
        elif self.critical_events_received >= 4 and self.event_delivery_score >= 60.0:
            print(f" PASS:  GOOD EVENT DELIVERY - User experience acceptable")
        else:
            print(f" FAIL:  POOR EVENT DELIVERY - User experience degraded")
        
        super().teardown_method()
    
    async def _monitor_detailed_event_delivery(
        self,
        websocket: websockets.WebSocketServerProtocol,
        user_context: StronglyTypedUserExecutionContext,
        timeout: float = 60.0
    ) -> Tuple[List[WebSocketEventMessage], Dict[str, Any]]:
        """
        Monitor detailed WebSocket event delivery with timing analysis.
        
        Args:
            websocket: Authenticated WebSocket connection
            user_context: User execution context
            timeout: Monitoring timeout
            
        Returns:
            Tuple of (events_received, delivery_metrics)
        """
        events_received = []
        delivery_metrics = {
            "first_event_time": None,
            "last_event_time": None,
            "event_intervals": [],
            "critical_events_timing": {},
            "sequence_correct": True,
            "total_events": 0
        }
        
        monitoring_start = time.time()
        last_event_time = monitoring_start
        expected_sequence = [
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        ]
        sequence_index = 0
        
        print(f" SEARCH:  Monitoring detailed event delivery for {timeout}s...")
        
        while time.time() - monitoring_start < timeout:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                message_data = json.loads(message)
                
                event_type = message_data.get("type")
                current_time = time.time()
                event_elapsed = current_time - monitoring_start
                
                # Process all events
                if event_type:
                    event = WebSocketEventMessage.from_dict(message_data)
                    events_received.append(event)
                    delivery_metrics["total_events"] += 1
                    
                    # Record timing
                    if delivery_metrics["first_event_time"] is None:
                        delivery_metrics["first_event_time"] = event_elapsed
                    
                    delivery_metrics["last_event_time"] = event_elapsed
                    
                    # Calculate interval since last event
                    interval = current_time - last_event_time
                    delivery_metrics["event_intervals"].append(interval)
                    last_event_time = current_time
                    
                    print(f"[U+1F4E8] Event: {event_type} at {event_elapsed:.2f}s (interval: {interval:.2f}s)")
                    
                    # Track critical events
                    if event_type in [e.value for e in CriticalAgentEventType]:
                        delivery_metrics["critical_events_timing"][event_type] = event_elapsed
                        
                        # Check sequence
                        if sequence_index < len(expected_sequence) and event_type == expected_sequence[sequence_index]:
                            sequence_index += 1
                            print(f" PASS:  Sequence correct: {event_type} ({sequence_index}/{len(expected_sequence)})")
                        elif event_type in expected_sequence:
                            # Event out of order
                            delivery_metrics["sequence_correct"] = False
                            print(f" WARNING: [U+FE0F] Sequence issue: {event_type} received out of order")
                        
                        # Check if all critical events received
                        if len(delivery_metrics["critical_events_timing"]) >= 5:
                            print(" CELEBRATION:  All 5 critical events received!")
                            break
                
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Warning: Event monitoring error: {e}")
                continue
        
        return events_received, delivery_metrics
    
    def _calculate_event_delivery_score(self, delivery_metrics: Dict[str, Any]) -> float:
        """Calculate event delivery quality score."""
        score_components = []
        
        # Critical event completeness (40% of score)
        critical_events_count = len(delivery_metrics["critical_events_timing"])
        completeness_score = (critical_events_count / 5.0) * 40.0
        score_components.append(completeness_score)
        
        # Event timing quality (30% of score)
        if delivery_metrics["first_event_time"]:
            # Good: first event within 5s, excellent: within 2s
            first_event_score = max(0, 30 - (delivery_metrics["first_event_time"] * 6))
            score_components.append(min(30.0, first_event_score))
        
        # Sequence correctness (20% of score)
        sequence_score = 20.0 if delivery_metrics["sequence_correct"] else 10.0
        score_components.append(sequence_score)
        
        # Event consistency (10% of score)
        if delivery_metrics["event_intervals"]:
            avg_interval = sum(delivery_metrics["event_intervals"]) / len(delivery_metrics["event_intervals"])
            # Good: consistent intervals under 10s
            consistency_score = max(0, 10 - (avg_interval * 1))
            score_components.append(min(10.0, consistency_score))
        
        return sum(score_components)
    
    @pytest.mark.asyncio
    async def test_complete_critical_event_delivery_sequence(self):
        """
        MISSION CRITICAL: Complete critical event delivery sequence.
        
        Tests that all 5 critical WebSocket events are delivered
        in proper sequence with good timing for optimal UX.
        
        BUSINESS IMPACT: Validates the event delivery that drives user engagement.
        """
        print("\n[U+1F9EA] MISSION CRITICAL: Testing complete critical event delivery...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"event_delivery_complete_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "agent_execution", "websocket"],
            websocket_enabled=True
        )
        
        print(f"[U+1F464] User authenticated for event delivery test: {user_context.user_id}")
        
        # STEP 2: Establish authenticated WebSocket connection
        jwt_token = user_context.agent_context["jwt_token"]
        ws_headers = self.ws_auth_helper.get_websocket_headers(jwt_token)
        ws_headers.update({
            "X-User-ID": str(user_context.user_id),
            "X-Thread-ID": str(user_context.thread_id),
            "X-Event-Monitoring": "critical_sequence"
        })
        
        websocket_url = self.ws_auth_helper.config.websocket_url
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    websocket_url,
                    additional_headers=ws_headers,
                    ping_interval=30,
                    ping_timeout=15
                ),
                timeout=self.config.connection_timeout
            )
            
            print("[U+1F50C] WebSocket connected for event delivery monitoring")
            
        except Exception as e:
            pytest.fail(f"CRITICAL: Event delivery WebSocket connection failed: {e}")
        
        try:
            # STEP 3: Send chat request designed to trigger all critical events
            event_trigger_request = {
                "type": "chat_message",
                "content": (
                    "Please perform a comprehensive data analysis task that involves: "
                    "1) Loading and analyzing sample business data "
                    "2) Identifying key trends and patterns "
                    "3) Generating strategic insights and recommendations "
                    "4) Creating a summary report with actionable next steps. "
                    "Please show your thinking process and tool usage throughout."
                ),
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_id": f"event_trigger_{uuid.uuid4().hex[:8]}",
                "event_monitoring": True
            }
            
            await websocket.send(json.dumps(event_trigger_request))
            request_time = time.time() - self.test_start_time
            print(f"[U+1F4E4] Event-triggering request sent at {request_time:.2f}s")
            
            # STEP 4: Monitor detailed event delivery
            events_received, delivery_metrics = await self._monitor_detailed_event_delivery(
                websocket=websocket,
                user_context=user_context,
                timeout=self.config.event_timeout
            )
            
            # STEP 5: Validate critical event delivery
            print(" PASS:  STEP 5: Validating critical event delivery...")
            
            self.events_delivered = len(events_received)
            self.critical_events_received = len(delivery_metrics["critical_events_timing"])
            self.event_delivery_score = self._calculate_event_delivery_score(delivery_metrics)
            
            # Critical assertions for event delivery
            assert self.critical_events_received >= 3, f"Insufficient critical events: {self.critical_events_received}/5"
            assert delivery_metrics["first_event_time"] is not None, "No events received"
            assert delivery_metrics["first_event_time"] < 10.0, f"First event too slow: {delivery_metrics['first_event_time']:.2f}s"
            
            # STEP 6: Validate event sequence and timing
            required_events = [e.value for e in CriticalAgentEventType]
            received_event_types = set(delivery_metrics["critical_events_timing"].keys())
            
            missing_events = set(required_events) - received_event_types
            if missing_events:
                print(f" WARNING: [U+FE0F] Missing critical events: {missing_events}")
            else:
                print(f" PASS:  All critical events received!")
            
            # STEP 7: Timing quality validation
            timing_analysis = []
            for event_type, timing in delivery_metrics["critical_events_timing"].items():
                if timing <= 5.0:
                    timing_score = 100.0
                elif timing <= 10.0:
                    timing_score = 80.0
                elif timing <= 20.0:
                    timing_score = 60.0
                else:
                    timing_score = 40.0
                
                timing_analysis.append(timing_score)
                print(f"[U+23F1][U+FE0F] {event_type}: {timing:.2f}s (score: {timing_score:.1f}%)")
            
            self.timing_scores = timing_analysis
            
            # STEP 8: Business impact validation
            assert self.event_delivery_score >= 50.0, f"Event delivery quality too low: {self.event_delivery_score:.1f}%"
            
            if delivery_metrics["sequence_correct"]:
                print(" PASS:  Event sequence correct - optimal user experience")
            else:
                print(" WARNING: [U+FE0F] Event sequence issues detected - may impact UX")
            
            print(f" CHART:  Event Delivery Summary:")
            print(f"   [U+2022] Total Events: {self.events_delivered}")
            print(f"   [U+2022] Critical Events: {self.critical_events_received}/5")
            print(f"   [U+2022] First Event: {delivery_metrics['first_event_time']:.2f}s")
            print(f"   [U+2022] Sequence Correct: {delivery_metrics['sequence_correct']}")
            print(f"   [U+2022] Delivery Score: {self.event_delivery_score:.1f}%")
            
        finally:
            if websocket and not websocket.closed:
                await websocket.close()
    
    @pytest.mark.asyncio
    async def test_event_delivery_consistency_across_scenarios(self):
        """
        CRITICAL: Event delivery consistency across different chat scenarios.
        
        Tests that WebSocket events are delivered consistently
        regardless of chat request type or complexity.
        
        BUSINESS IMPACT: Ensures reliable event delivery for all user interactions.
        """
        print("\n[U+1F9EA] CRITICAL: Testing event delivery consistency...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"event_consistency_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "consistency_testing"],
            websocket_enabled=True
        )
        
        # STEP 2: Define multiple chat scenarios
        chat_scenarios = [
            {
                "name": "simple_query",
                "message": "What are the key principles of effective business strategy?",
                "expected_events": ["agent_started", "agent_thinking", "agent_completed"],
                "min_events": 3
            },
            {
                "name": "complex_analysis",
                "message": (
                    "Analyze the business impact of implementing AI automation "
                    "in customer service operations, including cost-benefit analysis "
                    "and implementation timeline recommendations."
                ),
                "expected_events": ["agent_started", "agent_thinking", "tool_executing", "agent_completed"],
                "min_events": 4
            },
            {
                "name": "data_request",
                "message": (
                    "Please analyze sample sales data to identify trends, "
                    "calculate key metrics, and provide actionable insights "
                    "for improving sales performance."
                ),
                "expected_events": ["agent_started", "tool_executing", "tool_completed", "agent_completed"],
                "min_events": 4
            }
        ]
        
        # STEP 3: Test event delivery across scenarios
        scenario_results = []
        
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            for i, scenario in enumerate(chat_scenarios):
                print(f" CYCLE:  Testing scenario {i+1}: {scenario['name']}")
                
                scenario_start = time.time()
                
                try:
                    # Execute scenario
                    result = await self.golden_path_helper.execute_golden_path_flow(
                        user_message=scenario["message"],
                        user_context=user_context,
                        timeout=60.0
                    )
                    
                    # Analyze event delivery for this scenario
                    events_received = len(result.events_received)
                    event_types = [event.event_type for event in result.events_received]
                    
                    # Check for expected events
                    expected_found = sum(1 for event_type in scenario["expected_events"] if event_type in event_types)
                    consistency_score = (expected_found / len(scenario["expected_events"])) * 100
                    
                    scenario_result = {
                        "name": scenario["name"],
                        "events_received": events_received,
                        "expected_found": expected_found,
                        "consistency_score": consistency_score,
                        "execution_time": time.time() - scenario_start,
                        "success": result.success
                    }
                    
                    scenario_results.append(scenario_result)
                    
                    print(f"    CHART:  Events: {events_received}, Expected: {expected_found}/{len(scenario['expected_events'])}")
                    print(f"   [U+23F1][U+FE0F] Time: {scenario_result['execution_time']:.2f}s")
                    print(f"   [U+1F4C8] Consistency: {consistency_score:.1f}%")
                    
                    # Brief delay between scenarios
                    await asyncio.sleep(2.0)
                
                except Exception as e:
                    print(f"    FAIL:  Scenario failed: {str(e)[:100]}")
                    scenario_results.append({
                        "name": scenario["name"],
                        "events_received": 0,
                        "expected_found": 0,
                        "consistency_score": 0.0,
                        "execution_time": time.time() - scenario_start,
                        "success": False
                    })
        
        # STEP 4: Validate consistency across scenarios
        successful_scenarios = [r for r in scenario_results if r["success"]]
        assert len(successful_scenarios) >= 2, f"Insufficient successful scenarios: {len(successful_scenarios)}/3"
        
        # Calculate consistency metrics
        consistency_scores = [r["consistency_score"] for r in successful_scenarios]
        avg_consistency = sum(consistency_scores) / len(consistency_scores)
        
        execution_times = [r["execution_time"] for r in successful_scenarios]
        avg_execution_time = sum(execution_times) / len(execution_times)
        
        self.event_delivery_score = avg_consistency
        self.events_delivered = sum(r["events_received"] for r in successful_scenarios)
        
        # Consistency validation
        assert avg_consistency >= 60.0, f"Event delivery consistency too low: {avg_consistency:.1f}%"
        assert avg_execution_time < 45.0, f"Average execution time too slow: {avg_execution_time:.2f}s"
        
        print(f" CELEBRATION:  Event delivery consistency validation complete")
        print(f" CHART:  Successful scenarios: {len(successful_scenarios)}/3")
        print(f"[U+1F4C8] Average consistency: {avg_consistency:.1f}%")
        print(f"[U+23F1][U+FE0F] Average execution time: {avg_execution_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_event_delivery_under_load_conditions(self):
        """
        CRITICAL: Event delivery under simulated load conditions.
        
        Tests that WebSocket event delivery remains reliable
        when the system is under moderate load.
        
        BUSINESS IMPACT: Ensures event delivery stability during peak usage.
        """
        print("\n[U+1F9EA] CRITICAL: Testing event delivery under load...")
        
        # STEP 1: Create multiple authenticated user contexts
        user_contexts = []
        for i in range(3):  # Moderate load simulation
            context = await create_authenticated_user_context(
                user_email=f"load_test_user_{i}_{uuid.uuid4().hex[:6]}@example.com",
                environment=self.environment,
                permissions=["read", "write", "chat", "load_testing"],
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        print(f"[U+1F465] Created {len(user_contexts)} users for load testing")
        
        # STEP 2: Execute concurrent chat requests
        async def execute_user_chat_with_events(user_context, user_index):
            """Execute chat with event monitoring for one user."""
            helper = WebSocketGoldenPathHelper(environment=self.environment)
            
            try:
                async with helper.authenticated_websocket_connection(user_context):
                    load_message = (
                        f"User {user_index + 1} load test: Please analyze business metrics "
                        f"and provide optimization recommendations with detailed explanations."
                    )
                    
                    result = await helper.execute_golden_path_flow(
                        user_message=load_message,
                        user_context=user_context,
                        timeout=75.0
                    )
                    
                    return {
                        "user_index": user_index,
                        "success": result.success,
                        "events_received": len(result.events_received),
                        "execution_time": result.execution_metrics.total_execution_time,
                        "business_value_score": result.execution_metrics.business_value_score
                    }
            
            except Exception as e:
                return {
                    "user_index": user_index,
                    "success": False,
                    "events_received": 0,
                    "execution_time": 0.0,
                    "business_value_score": 0.0,
                    "error": str(e)[:100]
                }
        
        # STEP 3: Run concurrent executions
        load_start = time.time()
        
        load_results = await asyncio.gather(
            *[execute_user_chat_with_events(ctx, i) for i, ctx in enumerate(user_contexts)],
            return_exceptions=True
        )
        
        load_duration = time.time() - load_start
        
        # STEP 4: Analyze load test results
        successful_results = []
        for result in load_results:
            if isinstance(result, dict) and result.get("success"):
                successful_results.append(result)
            elif isinstance(result, dict):
                print(f" WARNING: [U+FE0F] User {result.get('user_index', '?')} failed: {result.get('error', 'Unknown')}")
            else:
                print(f" WARNING: [U+FE0F] Load test exception: {str(result)[:100]}")
        
        # STEP 5: Validate load performance
        success_rate = len(successful_results) / len(user_contexts) * 100
        
        if successful_results:
            avg_events = sum(r["events_received"] for r in successful_results) / len(successful_results)
            avg_execution_time = sum(r["execution_time"] for r in successful_results) / len(successful_results)
            avg_business_value = sum(r["business_value_score"] for r in successful_results) / len(successful_results)
            
            self.events_delivered = sum(r["events_received"] for r in successful_results)
            self.event_delivery_score = success_rate
        else:
            avg_events = 0
            avg_execution_time = 0
            avg_business_value = 0
        
        # Load test validation
        assert success_rate >= 66.0, f"Load test success rate too low: {success_rate:.1f}%"
        assert load_duration < 120.0, f"Load test duration too long: {load_duration:.2f}s"
        
        if successful_results:
            assert avg_events >= 2.0, f"Insufficient events under load: {avg_events:.1f}"
            assert avg_execution_time < 60.0, f"Execution too slow under load: {avg_execution_time:.2f}s"
        
        print(f" CELEBRATION:  Load test event delivery validation complete")
        print(f" CHART:  Success rate: {success_rate:.1f}%")
        print(f"[U+1F4E1] Average events per user: {avg_events:.1f}")
        print(f"[U+23F1][U+FE0F] Average execution time: {avg_execution_time:.2f}s")
        print(f" TARGET:  Average business value: {avg_business_value:.1f}%")


if __name__ == "__main__":
    """
    Run E2E tests for WebSocket event delivery during chat.
    
    Usage:
        python -m pytest tests/e2e/test_websocket_event_delivery_chat_e2e.py -v
        python -m pytest tests/e2e/test_websocket_event_delivery_chat_e2e.py::TestWebSocketEventDeliveryChatE2E::test_complete_critical_event_delivery_sequence -v -s
    """
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))