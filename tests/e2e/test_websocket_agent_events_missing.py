"""
Test WebSocket Agent Events Missing (E2E with Authentication)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure users receive all 5 critical WebSocket events during agent execution
- Value Impact: WebSocket events provide real-time progress and transparency in AI interactions
- Strategic Impact: Core chat experience that drives $500K+ ARR and user trust

CRITICAL: This E2E test reproduces the missing WebSocket events issue identified
in the Five Whys Root Cause Analysis. All e2e tests MUST use authentication per CLAUDE.md.

Expected Events (ALL REQUIRED for business value):
1. agent_started - User must see agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User must know when response is ready

This test SHOULD FAIL initially because the integration gap prevents events from reaching users.
"""

import pytest
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import websockets
from unittest.mock import patch

from test_framework.base_e2e_test import BaseE2ETest  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.websocket_helpers import WebSocketTestClient

logger = logging.getLogger(__name__)


class TestWebSocketAgentEventsMissing(BaseE2ETest):
    """
    E2E test for missing WebSocket agent events with full authentication.
    
    CRITICAL: This test uses real authentication and WebSocket connections to verify
    that all 5 critical events are sent during agent execution. Per CLAUDE.md,
    all e2e tests MUST use authentication.
    """

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_all_five_critical_events_missing_with_auth(self, real_services_fixture):
        """
        Test that all 5 critical WebSocket events are sent during authenticated agent execution.
        
        EXPECTED: This test SHOULD FAIL because events are not reaching users due to
        the ExecutionEngine -> AgentWebSocketBridge integration gap.
        
        Critical Events Required:
        - agent_started: Confirms agent began processing user request
        - agent_thinking: Shows AI reasoning process to user
        - tool_executing: Demonstrates problem-solving approach  
        - tool_completed: Delivers actionable insights
        - agent_completed: Signals complete response ready
        """
        # CRITICAL: Use E2E authentication as required by CLAUDE.md
        auth_helper = E2EAuthHelper(environment="test")
        authenticated_user = await auth_helper.create_authenticated_user(
            email="e2e_websocket_events@example.com",
            full_name="E2E WebSocket Events User"
        )
        
        logger.info(f"Testing WebSocket events with authenticated user: {authenticated_user.user_id}")
        
        # Track all WebSocket events received
        received_events = []
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        # Get authentication headers for WebSocket connection
        websocket_headers = auth_helper.get_websocket_headers(authenticated_user.jwt_token)
        websocket_url = real_services_fixture.get("websocket_url", "ws://localhost:8000/ws")
        
        logger.info(f"Connecting to WebSocket: {websocket_url}")
        logger.info(f"Authentication headers count: {len(websocket_headers)}")
        
        try:
            # CRITICAL: Establish authenticated WebSocket connection
            async with websockets.connect(
                websocket_url,
                additional_headers=websocket_headers,
                timeout=15.0
            ) as websocket:
                
                logger.info("✓ Authenticated WebSocket connection established")
                
                # Send agent execution request
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Test message to trigger all 5 WebSocket events",
                    "user_id": authenticated_user.user_id,
                    "request_id": f"test_events_{int(datetime.now(timezone.utc).timestamp())}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                logger.info(f"Sent agent request: {agent_request['message']}")
                
                # Collect WebSocket events for analysis
                event_timeout = 30.0  # Maximum time to wait for all events
                start_time = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - start_time) < event_timeout:
                    try:
                        # Wait for WebSocket messages with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        
                        try:
                            event_data = json.loads(message)
                            event_type = event_data.get("type", "unknown")
                            
                            # Log all received events
                            logger.info(f"Received WebSocket event: {event_type}")
                            received_events.append({
                                "type": event_type,
                                "data": event_data,
                                "timestamp": asyncio.get_event_loop().time() - start_time
                            })
                            
                            # Check if this is an agent completion event
                            if event_type == "agent_completed":
                                logger.info("Agent execution completed - stopping event collection")
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse WebSocket message: {e}")
                            continue
                            
                    except asyncio.TimeoutError:
                        # No more events received - check what we have
                        logger.warning("Timeout waiting for WebSocket events")
                        break
                    
                    except Exception as e:
                        logger.error(f"Error receiving WebSocket events: {e}")
                        break
                
                # CRITICAL ANALYSIS: Check which events were received vs. expected
                received_event_types = [event["type"] for event in received_events]
                missing_events = [event for event in expected_events if event not in received_event_types]
                unexpected_events = [event for event in received_event_types if event not in expected_events]
                
                logger.info(f"Events analysis:")
                logger.info(f"  Expected: {expected_events}")
                logger.info(f"  Received: {received_event_types}")
                logger.info(f"  Missing: {missing_events}")
                logger.info(f"  Unexpected: {unexpected_events}")
                
                # CRITICAL ASSERTION: All 5 events must be present for business value
                if missing_events:
                    pytest.fail(
                        f"WEBSOCKET EVENTS MISSING (E2E): Critical events not received by authenticated user. "
                        f"Missing events: {missing_events}. "
                        f"Received events: {received_event_types}. "
                        f"Total events received: {len(received_events)}. "
                        f"This confirms the integration gap prevents events from reaching users. "
                        f"User experience is broken - no progress visibility during agent execution."
                    )
                
                # Additional validation: Check event timing and order
                if len(received_events) < len(expected_events):
                    pytest.fail(
                        f"WEBSOCKET EVENTS INCOMPLETE (E2E): Only {len(received_events)} events received, "
                        f"expected {len(expected_events)}. "
                        f"Event sequence: {[e['type'] for e in received_events]}. "
                        f"This indicates partial WebSocket integration failure."
                    )
                
                # Validate event order (agent_started should be first, agent_completed should be last)
                if received_events and received_events[0]["type"] != "agent_started":
                    pytest.fail(
                        f"WEBSOCKET EVENTS ORDER WRONG (E2E): First event was '{received_events[0]['type']}', "
                        f"expected 'agent_started'. "
                        f"Event sequence: {[e['type'] for e in received_events]}. "
                        f"Users will see confusing progress updates."
                    )
                
                if received_events and received_events[-1]["type"] != "agent_completed":
                    pytest.fail(
                        f"WEBSOCKET EVENTS ORDER WRONG (E2E): Last event was '{received_events[-1]['type']}', "
                        f"expected 'agent_completed'. "
                        f"Event sequence: {[e['type'] for e in received_events]}. "
                        f"Users won't know when agent finished processing."
                    )
                
        except websockets.exceptions.ConnectionClosed as e:
            pytest.fail(
                f"WEBSOCKET CONNECTION FAILED (E2E): Connection closed during event testing. "
                f"Error: {e}. "
                f"Events received before close: {len(received_events)}. "
                f"This indicates WebSocket infrastructure failure affecting user experience."
            )
        
        except websockets.exceptions.InvalidStatusCode as e:
            pytest.fail(
                f"WEBSOCKET AUTH FAILED (E2E): Invalid status code during connection. "
                f"Error: {e}. "
                f"This indicates authentication issues in WebSocket handshake. "
                f"Users cannot establish authenticated connections for real-time updates."
            )
        
        except asyncio.TimeoutError:
            pytest.fail(
                f"WEBSOCKET TIMEOUT (E2E): Connection timed out during event testing. "
                f"Events received: {len(received_events)}. "
                f"Event types: {[e['type'] for e in received_events]}. "
                f"This indicates performance issues affecting user experience."
            )
        
        except Exception as e:
            pytest.fail(
                f"WEBSOCKET EVENTS FAILURE (E2E): Unexpected error during event testing. "
                f"Error: {e}. "
                f"Events received: {len(received_events)}. "
                f"This indicates broader WebSocket integration issues."
            )

    @pytest.mark.e2e  
    @pytest.mark.real_services
    async def test_websocket_events_user_isolation_with_auth(self, real_services_fixture):
        """
        Test that WebSocket events are properly isolated per authenticated user.
        
        EXPECTED: This test SHOULD FAIL because the per-user factory pattern
        is not properly creating isolated WebSocket emitters.
        
        Based on Five Whys Analysis:
        - Per-user isolation test for create_user_emitter() factory pattern
        - Each user should receive only their own agent events
        - Cross-user event contamination breaks multi-user system
        """
        # CRITICAL: Create two authenticated users for isolation testing
        auth_helper = E2EAuthHelper(environment="test")
        
        user1 = await auth_helper.create_authenticated_user(
            email="user1_isolation@example.com",
            full_name="User 1 Isolation Test"
        )
        
        user2 = await auth_helper.create_authenticated_user(
            email="user2_isolation@example.com", 
            full_name="User 2 Isolation Test"
        )
        
        logger.info(f"Testing WebSocket event isolation between users: {user1.user_id} and {user2.user_id}")
        
        user1_events = []
        user2_events = []
        websocket_url = real_services_fixture.get("websocket_url", "ws://localhost:8000/ws")
        
        try:
            # CRITICAL: Establish separate authenticated WebSocket connections
            user1_headers = auth_helper.get_websocket_headers(user1.jwt_token)
            user2_headers = auth_helper.get_websocket_headers(user2.jwt_token)
            
            async with websockets.connect(
                websocket_url,
                additional_headers=user1_headers,
                timeout=15.0
            ) as user1_ws:
                
                async with websockets.connect(
                    websocket_url,
                    additional_headers=user2_headers,
                    timeout=15.0
                ) as user2_ws:
                    
                    logger.info("✓ Both authenticated WebSocket connections established")
                    
                    # Send agent requests from both users simultaneously
                    user1_request = {
                        "type": "agent_request",
                        "agent": "triage_agent",
                        "message": "User 1 agent request for isolation testing",
                        "user_id": user1.user_id,
                        "request_id": f"user1_isolation_{int(datetime.now(timezone.utc).timestamp())}"
                    }
                    
                    user2_request = {
                        "type": "agent_request", 
                        "agent": "triage_agent",
                        "message": "User 2 agent request for isolation testing",
                        "user_id": user2.user_id,
                        "request_id": f"user2_isolation_{int(datetime.now(timezone.utc).timestamp())}"
                    }
                    
                    # Send requests simultaneously to test isolation
                    await user1_ws.send(json.dumps(user1_request))
                    await user2_ws.send(json.dumps(user2_request))
                    
                    logger.info("Sent simultaneous agent requests from both users")
                    
                    # Collect events from both users
                    async def collect_user_events(websocket, user_id, events_list, timeout=30.0):
                        """Collect WebSocket events for a specific user."""
                        start_time = asyncio.get_event_loop().time()
                        
                        while (asyncio.get_event_loop().time() - start_time) < timeout:
                            try:
                                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                                event_data = json.loads(message)
                                event_type = event_data.get("type", "unknown")
                                
                                events_list.append({
                                    "user_id": user_id,
                                    "type": event_type,
                                    "data": event_data,
                                    "timestamp": asyncio.get_event_loop().time() - start_time
                                })
                                
                                logger.info(f"User {user_id} received event: {event_type}")
                                
                                if event_type == "agent_completed":
                                    break
                                    
                            except asyncio.TimeoutError:
                                break
                            except Exception as e:
                                logger.error(f"Error collecting events for user {user_id}: {e}")
                                break
                    
                    # Collect events from both users concurrently
                    await asyncio.gather(
                        collect_user_events(user1_ws, user1.user_id, user1_events),
                        collect_user_events(user2_ws, user2.user_id, user2_events)
                    )
                    
                    # CRITICAL ANALYSIS: Verify event isolation
                    logger.info(f"User 1 events: {len(user1_events)}")
                    logger.info(f"User 2 events: {len(user2_events)}")
                    
                    # Check for cross-user contamination
                    contamination_issues = []
                    
                    for event in user1_events:
                        event_user_id = event["data"].get("user_id")
                        if event_user_id and event_user_id != user1.user_id:
                            contamination_issues.append(f"User 1 received event for user {event_user_id}")
                    
                    for event in user2_events:
                        event_user_id = event["data"].get("user_id") 
                        if event_user_id and event_user_id != user2.user_id:
                            contamination_issues.append(f"User 2 received event for user {event_user_id}")
                    
                    # CRITICAL ASSERTION: No cross-user event contamination
                    if contamination_issues:
                        pytest.fail(
                            f"USER ISOLATION FAILURE (E2E): Cross-user event contamination detected. "
                            f"Contamination issues: {contamination_issues}. "
                            f"User 1 events: {len(user1_events)}, User 2 events: {len(user2_events)}. "
                            f"This confirms the per-user factory pattern is broken. "
                            f"Multi-user system security compromised."
                        )
                    
                    # Check if both users received events (or both failed)
                    if len(user1_events) == 0 and len(user2_events) == 0:
                        pytest.fail(
                            f"WEBSOCKET EVENTS MISSING FOR ALL USERS (E2E): Neither user received events. "
                            f"This confirms the WebSocket integration gap affects all users. "
                            f"Complete system failure - no users receive real-time updates."
                        )
                    
                    if len(user1_events) == 0 or len(user2_events) == 0:
                        pytest.fail(
                            f"WEBSOCKET EVENTS PARTIAL FAILURE (E2E): Events missing for one user. "
                            f"User 1 events: {len(user1_events)}, User 2 events: {len(user2_events)}. "
                            f"This indicates inconsistent WebSocket event delivery. "
                            f"Some users experience degraded real-time functionality."
                        )
                    
        except Exception as e:
            pytest.fail(
                f"USER ISOLATION TEST FAILURE (E2E): Failed to test WebSocket event isolation. "
                f"Error: {e}. "
                f"User 1 events: {len(user1_events)}, User 2 events: {len(user2_events)}. "
                f"This indicates broader WebSocket infrastructure issues."
            )

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_events_business_value_impact(self, real_services_fixture):
        """
        Test the business value impact of missing WebSocket events.
        
        EXPECTED: This test SHOULD FAIL to demonstrate the business impact
        of the WebSocket integration gap on user experience and trust.
        
        Business Impact Analysis:
        - Missing events → No progress visibility → User frustration → Churn
        - Real-time updates are core value proposition for $500K+ ARR
        - User trust depends on transparency during AI processing
        """
        # CRITICAL: Use authenticated user for business value testing
        auth_helper = E2EAuthHelper(environment="test")
        business_user = await auth_helper.create_authenticated_user(
            email="business_value@example.com",
            full_name="Business Value Test User",
            permissions=["read", "write", "premium_features"]
        )
        
        logger.info(f"Testing business value impact for user: {business_user.user_id}")
        
        websocket_url = real_services_fixture.get("websocket_url", "ws://localhost:8000/ws")
        business_metrics = {
            "events_received": 0,
            "events_expected": 5,
            "user_experience_score": 0,
            "transparency_indicators": [],
            "trust_factors": []
        }
        
        try:
            # CRITICAL: Establish authenticated connection for business user
            headers = auth_helper.get_websocket_headers(business_user.jwt_token)
            
            async with websockets.connect(
                websocket_url,
                additional_headers=headers,
                timeout=15.0
            ) as websocket:
                
                logger.info("✓ Business user authenticated WebSocket connection established")
                
                # Send business-critical agent request
                business_request = {
                    "type": "agent_request",
                    "agent": "optimization_agent",  # Business-critical agent
                    "message": "Analyze cost optimization opportunities for Q4 planning",
                    "user_id": business_user.user_id,
                    "priority": "high",
                    "business_context": {
                        "user_tier": "premium",
                        "use_case": "business_planning",
                        "expected_savings": "$50000"
                    }
                }
                
                await websocket.send(json.dumps(business_request))
                logger.info("Sent business-critical agent request")
                
                # Monitor business value indicators through WebSocket events
                start_time = asyncio.get_event_loop().time()
                timeout = 45.0  # Extended timeout for business-critical processing
                
                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event_data = json.loads(message)
                        event_type = event_data.get("type", "unknown")
                        
                        business_metrics["events_received"] += 1
                        
                        # Analyze business value indicators
                        if event_type == "agent_started":
                            business_metrics["trust_factors"].append("user_notified_of_processing")
                            business_metrics["user_experience_score"] += 20
                            
                        elif event_type == "agent_thinking":
                            business_metrics["transparency_indicators"].append("reasoning_visible")
                            business_metrics["user_experience_score"] += 15
                            
                        elif event_type == "tool_executing":
                            business_metrics["transparency_indicators"].append("tool_usage_visible")
                            business_metrics["user_experience_score"] += 10
                            
                        elif event_type == "tool_completed":
                            business_metrics["transparency_indicators"].append("results_delivered")
                            business_metrics["user_experience_score"] += 15
                            
                        elif event_type == "agent_completed":
                            business_metrics["trust_factors"].append("completion_confirmed")
                            business_metrics["user_experience_score"] += 40
                            
                        logger.info(f"Business event: {event_type}, Score: {business_metrics['user_experience_score']}")
                        
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        break
                    except Exception as e:
                        logger.error(f"Error in business value monitoring: {e}")
                        break
                
                # CRITICAL BUSINESS ANALYSIS
                events_received = business_metrics["events_received"]
                events_expected = business_metrics["events_expected"]
                experience_score = business_metrics["user_experience_score"]
                max_possible_score = 100  # Sum of all event scores
                
                transparency_score = (len(business_metrics["transparency_indicators"]) / 3) * 100
                trust_score = (len(business_metrics["trust_factors"]) / 2) * 100
                
                logger.info(f"Business Value Analysis:")
                logger.info(f"  Events: {events_received}/{events_expected}")
                logger.info(f"  Experience Score: {experience_score}/{max_possible_score}")
                logger.info(f"  Transparency Score: {transparency_score}%")
                logger.info(f"  Trust Score: {trust_score}%")
                
                # CRITICAL BUSINESS ASSERTIONS
                if events_received < events_expected:
                    business_impact = {
                        "revenue_risk": "HIGH" if experience_score < 50 else "MEDIUM",
                        "user_satisfaction": "POOR" if experience_score < 30 else "DEGRADED",
                        "competitive_disadvantage": transparency_score < 50,
                        "churn_risk": trust_score < 50,
                        "missing_events": events_expected - events_received
                    }
                    
                    pytest.fail(
                        f"BUSINESS VALUE DESTROYED (E2E): Missing WebSocket events damage user experience. "
                        f"Business Impact: {business_impact}. "
                        f"Events missing: {events_expected - events_received}. "
                        f"Experience score: {experience_score}/{max_possible_score} ({experience_score/max_possible_score*100:.1f}%). "
                        f"Transparency score: {transparency_score}%. "
                        f"Trust score: {trust_score}%. "
                        f"This directly impacts $500K+ ARR through poor user experience. "
                        f"Users cannot see AI processing progress, reducing trust and satisfaction."
                    )
                
        except Exception as e:
            pytest.fail(
                f"BUSINESS VALUE TEST FAILURE (E2E): Cannot measure business impact due to WebSocket issues. "
                f"Error: {e}. "
                f"Events received: {business_metrics['events_received']}. "
                f"This indicates complete failure of real-time user experience. "
                f"Business-critical functionality broken."
            )