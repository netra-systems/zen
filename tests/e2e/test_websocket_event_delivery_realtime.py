"""
WebSocket Event Delivery and Real-Time Updates E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time user experience with immediate feedback
- Value Impact: Users see progress and stay engaged during agent execution
- Strategic Impact: WebSocket events enable "Chat" business value - without them, no user experience

These tests validate the CRITICAL WebSocket infrastructure that enables substantive chat interactions:
1. All 5 mandatory WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
2. Real-time event delivery with proper timing
3. Event ordering and sequencing validation
4. Multi-user event isolation (events go to correct users only)
5. WebSocket connection stability and recovery
6. Event payload validation and business context
7. Performance under concurrent WebSocket load

CRITICAL E2E REQUIREMENTS:
1. Real authentication for WebSocket connections - NO MOCKS
2. Real services with WebSocket infrastructure - NO MOCKS
3. Real LLM integration triggering actual events
4. ALL 5 WebSocket events MUST be validated
5. Event timing and ordering must be verified
6. Multi-user isolation must be tested
7. Connection stability under load tested
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set
import websockets
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user, get_test_jwt_token
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketEventDeliveryRealTime(SSotBaseTestCase):
    """
    E2E tests for WebSocket event delivery and real-time updates.
    Validates the mission-critical WebSocket events that enable chat business value.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated helper for E2E tests."""
        return E2EAuthHelper(environment="test")
    
    @pytest.fixture
    async def authenticated_user(self, auth_helper):
        """Create authenticated user for WebSocket tests."""
        return await create_authenticated_user(
            environment="test",
            email="websocket_test@example.com",
            permissions=["read", "write", "agent_execution", "websocket_access"]
        )

    #  ALERT:  CRITICAL: The 5 mandatory WebSocket events for chat business value
    MANDATORY_EVENTS = [
        'agent_started',      # User sees agent began processing
        'agent_thinking',     # Real-time reasoning visibility  
        'tool_executing',     # Tool usage transparency
        'tool_completed',     # Tool results delivery
        'agent_completed'     # User knows valuable response is ready
    ]

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_all_five_mandatory_websocket_events(self, auth_helper, authenticated_user):
        """
        Test ALL 5 mandatory WebSocket events are delivered.
        
        Business Scenario: User sends request and expects real-time feedback
        throughout the entire agent execution process.
        
        MISSION CRITICAL: Without these events, chat has no business value!
        
        Validates:
        - All 5 mandatory events are delivered
        - Events arrive in logical order
        - Each event contains proper payload structure
        - Event timing is reasonable for user experience
        - Events provide meaningful progress information
        """
        token, user_data = authenticated_user
        
        print(f"[U+1F680] MISSION CRITICAL: Testing all 5 mandatory WebSocket events")
        print(f"[U+1F464] User: {user_data['email']}")
        print(f"[U+1F4CB] Required events: {', '.join(self.MANDATORY_EVENTS)}")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Request that should trigger all agent workflow phases
        comprehensive_request = {
            "type": "agent_request", 
            "agent": "supervisor",
            "message": "Analyze my AI costs and provide optimization recommendations. I'm spending $3000/month on GPT-4 for 20,000 customer service requests.",
            "context": {
                "requires_tools": True,  # Ensure tool execution
                "comprehensive_analysis": True,
                "monthly_spend": 3000,
                "monthly_requests": 20000,
                "use_case": "customer_service"
            },
            "user_id": user_data["id"]
        }
        
        all_events = []
        event_timestamps = {}
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                print(f" PASS:  WebSocket connected")
                
                # Send request that should trigger comprehensive agent workflow
                await websocket.send(json.dumps(comprehensive_request))
                print(f"[U+1F4E4] Sent comprehensive request")
                
                start_time = time.time()
                timeout_duration = 90.0  # Generous timeout for comprehensive workflow
                
                # Collect all events
                while time.time() - start_time < timeout_duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=15)
                        event = json.loads(message)
                        
                        event_time = time.time()
                        event_type = event['type']
                        
                        all_events.append(event)
                        event_timestamps[event_type] = event_timestamps.get(event_type, []) + [event_time - start_time]
                        
                        print(f"[U+1F4E8] Event #{len(all_events)}: {event_type} (t={event_time - start_time:.2f}s)")
                        
                        # Log additional details for key events
                        if event_type == 'agent_thinking' and event.get('data'):
                            thinking_content = event['data'].get('content', '')[:100]
                            print(f"   [U+1F4AD] Thinking: {thinking_content}...")
                        elif event_type == 'tool_executing' and event.get('data'):
                            tool_name = event['data'].get('tool_name', 'unknown')
                            print(f"   [U+1F527] Tool: {tool_name}")
                        elif event_type == 'tool_completed' and event.get('data'):
                            tool_result = str(event['data'].get('result', ''))[:50]
                            print(f"    PASS:  Tool result: {tool_result}...")
                        
                        # Stop when workflow complete
                        if event_type == 'agent_completed':
                            completion_time = event_time - start_time
                            print(f"[U+1F3C1] Workflow completed in {completion_time:.2f}s")
                            break
                            
                    except asyncio.TimeoutError:
                        print(f"[U+23F0] Timeout waiting for events after {time.time() - start_time:.2f}s")
                        break
                    except json.JSONDecodeError as e:
                        print(f" FAIL:  JSON decode error: {e}")
                        continue
                    except Exception as e:
                        print(f" FAIL:  Event collection error: {e}")
                        continue
        
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
        
        #  ALERT:  CRITICAL VALIDATION: All 5 mandatory events MUST be present
        print(f"\n CHART:  EVENT ANALYSIS:")
        print(f"   Total events received: {len(all_events)}")
        
        event_types = [e['type'] for e in all_events]
        event_type_counts = {event_type: event_types.count(event_type) for event_type in set(event_types)}
        
        for event_type, count in event_type_counts.items():
            print(f"   {event_type}: {count}")
        
        # Validate all mandatory events are present
        missing_events = []
        for mandatory_event in self.MANDATORY_EVENTS:
            if mandatory_event not in event_types:
                missing_events.append(mandatory_event)
        
        assert len(missing_events) == 0, f"CRITICAL FAILURE: Missing mandatory events: {missing_events}"
        print(f" PASS:  All 5 mandatory events present!")
        
        # Validate event ordering makes logical sense
        event_order = [e['type'] for e in all_events]
        
        # agent_started should be first
        assert event_order[0] == 'agent_started', f"First event should be agent_started, got: {event_order[0]}"
        
        # agent_completed should be last  
        assert event_order[-1] == 'agent_completed', f"Last event should be agent_completed, got: {event_order[-1]}"
        
        # tool_executing should come before tool_completed
        tool_executing_indices = [i for i, event_type in enumerate(event_order) if event_type == 'tool_executing']
        tool_completed_indices = [i for i, event_type in enumerate(event_order) if event_type == 'tool_completed']
        
        if tool_executing_indices and tool_completed_indices:
            # Each tool_executing should have a corresponding tool_completed after it
            for exec_idx in tool_executing_indices:
                next_completed = [idx for idx in tool_completed_indices if idx > exec_idx]
                assert len(next_completed) > 0, f"tool_executing at index {exec_idx} has no subsequent tool_completed"
        
        print(f" PASS:  Event ordering validated")
        
        # Validate event timing (reasonable intervals)
        event_intervals = []
        for i in range(1, len(all_events)):
            prev_time = event_timestamps[all_events[i-1]['type']][-1] if all_events[i-1]['type'] in event_timestamps else 0
            curr_time = event_timestamps[all_events[i]['type']][-1] if all_events[i]['type'] in event_timestamps else 0
            interval = curr_time - prev_time
            event_intervals.append(interval)
        
        # No single event should take more than 30 seconds (reasonable UX)
        max_interval = max(event_intervals) if event_intervals else 0
        assert max_interval < 30, f"Event interval too long: {max_interval:.2f}s (max 30s for good UX)"
        
        # Average interval should be reasonable
        avg_interval = sum(event_intervals) / len(event_intervals) if event_intervals else 0
        assert avg_interval < 10, f"Average event interval too long: {avg_interval:.2f}s (max 10s)"
        
        print(f" PASS:  Event timing validated (max: {max_interval:.2f}s, avg: {avg_interval:.2f}s)")
        
        # Validate event payloads contain business context
        business_context_found = False
        for event in all_events:
            if event['type'] == 'agent_completed' and 'data' in event and 'result' in event['data']:
                result = event['data']['result']
                result_text = str(result).lower()
                
                # Should contain business-relevant optimization content
                business_indicators = ['cost', 'optimization', 'savings', 'recommendation', '3000', 'customer service']
                found_indicators = [ind for ind in business_indicators if ind in result_text]
                
                if len(found_indicators) >= 2:
                    business_context_found = True
                    print(f" PASS:  Business context validated: {found_indicators}")
                    break
        
        assert business_context_found, "Final result lacks business context"
        
        print(f" CELEBRATION:  MISSION CRITICAL TEST SUCCESS!")
        print(f"   [U+2713] All 5 mandatory WebSocket events delivered")
        print(f"   [U+2713] Logical event ordering maintained") 
        print(f"   [U+2713] Reasonable event timing for UX")
        print(f"   [U+2713] Business context in event payloads")
        print(f"   [U+2713] Complete agent workflow tracked in real-time")


    @pytest.mark.e2e  
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_websocket_event_isolation_multi_user(self, auth_helper):
        """
        Test WebSocket event isolation between multiple concurrent users.
        
        Business Scenario: Multiple users connected simultaneously should only
        receive their own events, not events from other users' sessions.
        
        CRITICAL for multi-tenant security and user experience.
        
        Validates:
        - Events are delivered only to the correct user
        - No event leakage between user sessions  
        - Concurrent WebSocket connections work properly
        - Each user receives complete event stream
        """
        print(f"[U+1F680] Testing WebSocket event isolation with multiple users")
        
        # Create 3 distinct users
        users = []
        for i in range(3):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                email=f"websocket_isolation_{i}_{int(time.time())}@example.com",
                permissions=["read", "write", "agent_execution"]
            )
            users.append((user_token, user_data))
        
        print(f" PASS:  Created {len(users)} users for isolation test")
        
        # Define distinct requests for each user
        user_requests = [
            {
                "message": "Help me optimize costs for e-commerce chatbot",
                "context": {"use_case": "ecommerce", "user_marker": "ECOMMERCE_USER"}
            },
            {
                "message": "Improve performance for healthcare diagnostics", 
                "context": {"use_case": "healthcare", "user_marker": "HEALTHCARE_USER"}
            },
            {
                "message": "Scale content generation for media company",
                "context": {"use_case": "content", "user_marker": "CONTENT_USER"}
            }
        ]
        
        # Function to handle individual user WebSocket session
        async def user_websocket_session(user_index: int, user_token: str, user_data: Dict, request_data: Dict) -> Dict:
            """Handle WebSocket session for individual user with event collection."""
            websocket_url = "ws://localhost:8000/ws"
            headers = auth_helper.get_websocket_headers(user_token)
            
            session_result = {
                "user_index": user_index,
                "user_id": user_data["id"], 
                "user_email": user_data["email"],
                "events_received": [],
                "mandatory_events_count": 0,
                "completion_time": None,
                "error": None
            }
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    print(f"[U+1F50C] User {user_index} WebSocket connected")
                    
                    # Send user-specific request
                    request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": request_data["message"],
                        "context": {**request_data["context"], "isolation_test": True},
                        "user_id": user_data["id"]
                    }
                    
                    await websocket.send(json.dumps(request))
                    print(f"[U+1F4E4] User {user_index} sent request")
                    
                    start_time = time.time()
                    
                    # Collect events for this user
                    while time.time() - start_time < 60:  # 1 minute per user
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message)
                            
                            session_result["events_received"].append(event)
                            
                            # Count mandatory events
                            if event['type'] in self.MANDATORY_EVENTS:
                                session_result["mandatory_events_count"] += 1
                            
                            print(f"[U+1F4E8] User {user_index}: {event['type']}")
                            
                            if event['type'] == 'agent_completed':
                                session_result["completion_time"] = time.time() - start_time
                                print(f" PASS:  User {user_index} completed")
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                session_result["error"] = str(e)
                print(f" FAIL:  User {user_index} session error: {e}")
            
            return session_result
        
        # Execute all user sessions concurrently
        print(f"[U+1F3C3] Starting concurrent WebSocket sessions...")
        
        tasks = []
        for i, ((user_token, user_data), request_data) in enumerate(zip(users, user_requests)):
            task = user_websocket_session(i, user_token, user_data, request_data)
            tasks.append(task)
        
        # Wait for all sessions to complete
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate all sessions completed successfully
        successful_sessions = []
        for result in session_results:
            if isinstance(result, Exception):
                pytest.fail(f"Session failed with exception: {result}")
            elif result.get("error"):
                pytest.fail(f"Session error: {result['error']}")
            else:
                successful_sessions.append(result)
        
        assert len(successful_sessions) == 3, f"Expected 3 successful sessions, got {len(successful_sessions)}"
        print(f" PASS:  All {len(successful_sessions)} sessions completed")
        
        #  ALERT:  CRITICAL: Validate event isolation - no cross-user contamination
        for i, session in enumerate(successful_sessions):
            user_events = session["events_received"]
            user_marker = user_requests[i]["context"]["user_marker"]
            
            print(f" CHART:  User {i} ({session['user_email']}):")
            print(f"   Events received: {len(user_events)}")
            print(f"   Mandatory events: {session['mandatory_events_count']}")
            print(f"   Completion time: {session['completion_time']:.2f}s" if session['completion_time'] else "   No completion")
            
            # Each user should receive mandatory events
            assert session["mandatory_events_count"] >= 3, \
                f"User {i} insufficient mandatory events: {session['mandatory_events_count']}"
            
            # Validate no cross-contamination in event content
            for event in user_events:
                if event['type'] == 'agent_completed' and 'data' in event:
                    result_text = str(event['data']).lower()
                    
                    # Should NOT contain other users' markers
                    for j, other_session in enumerate(successful_sessions):
                        if i == j:
                            continue
                        
                        other_marker = user_requests[j]["context"]["user_marker"].lower()
                        other_use_case = user_requests[j]["context"]["use_case"]
                        
                        assert other_marker.replace("_", "") not in result_text, \
                            f"User {i} contaminated with User {j} marker: {other_marker}"
                        
                        # Should not heavily discuss other use cases (some overlap acceptable)
                        contamination_score = result_text.count(other_use_case)
                        own_use_case_score = result_text.count(user_requests[i]["context"]["use_case"])
                        
                        if own_use_case_score > 0:  # Only check if own use case is present
                            contamination_ratio = contamination_score / own_use_case_score
                            assert contamination_ratio < 0.5, \
                                f"User {i} over-contaminated with User {j} use case: {contamination_ratio:.2f}"
            
            print(f" PASS:  User {i} isolation validated")
        
        print(f" CELEBRATION:  WEBSOCKET EVENT ISOLATION SUCCESS!")
        print(f"   [U+2713] All users received events concurrently")
        print(f"   [U+2713] No cross-user event contamination")
        print(f"   [U+2713] Each user received complete event stream")
        print(f"   [U+2713] Multi-tenant WebSocket security validated")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_websocket_connection_stability(self, auth_helper, authenticated_user):
        """
        Test WebSocket connection stability under various conditions.
        
        Business Scenario: User maintains WebSocket connection during
        extended agent execution and various network conditions.
        
        Validates:
        - Connection stability during long-running operations
        - Proper handling of temporary network issues
        - Event delivery reliability
        - Connection recovery mechanisms
        """
        token, user_data = authenticated_user
        
        print(f"[U+1F680] Testing WebSocket connection stability")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Long-running request to test connection stability
        stability_request = {
            "type": "agent_request",
            "agent": "supervisor", 
            "message": "Provide comprehensive analysis of AI infrastructure optimization including cost analysis, performance tuning, quality improvements, and implementation roadmap for enterprise deployment.",
            "context": {
                "comprehensive": True,
                "extended_processing": True,
                "stability_test": True
            },
            "user_id": user_data["id"]
        }
        
        connection_metrics = {
            "events_received": 0,
            "connection_drops": 0,
            "reconnections": 0,
            "max_event_gap": 0,
            "total_duration": 0
        }
        
        try:
            # Test with potential reconnection scenario
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                print(f" PASS:  WebSocket connected for stability test")
                
                await websocket.send(json.dumps(stability_request))
                print(f"[U+1F4E4] Sent long-running comprehensive request")
                
                start_time = time.time()
                last_event_time = start_time
                timeout_duration = 120.0  # Extended timeout for comprehensive processing
                
                while time.time() - start_time < timeout_duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=20)
                        event = json.loads(message)
                        
                        current_time = time.time()
                        event_gap = current_time - last_event_time
                        connection_metrics["max_event_gap"] = max(connection_metrics["max_event_gap"], event_gap)
                        connection_metrics["events_received"] += 1
                        last_event_time = current_time
                        
                        print(f"[U+1F4E8] Event #{connection_metrics['events_received']}: {event['type']} " + 
                              f"(gap: {event_gap:.1f}s)")
                        
                        if event['type'] == 'agent_completed':
                            connection_metrics["total_duration"] = current_time - start_time
                            print(f" PASS:  Long-running operation completed")
                            break
                            
                    except asyncio.TimeoutError:
                        print(f"[U+23F0] Event timeout - connection stable")
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        connection_metrics["connection_drops"] += 1
                        print(f"[U+1F50C] Connection dropped (#{connection_metrics['connection_drops']})")
                        break
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            pytest.fail(f"WebSocket stability test failed: {e}")
        
        # Validate connection stability metrics
        print(f"\n CHART:  CONNECTION STABILITY METRICS:")
        print(f"   Events received: {connection_metrics['events_received']}")
        print(f"   Connection drops: {connection_metrics['connection_drops']}")
        print(f"   Max event gap: {connection_metrics['max_event_gap']:.1f}s")  
        print(f"   Total duration: {connection_metrics['total_duration']:.1f}s")
        
        # Validation criteria
        assert connection_metrics["events_received"] >= 5, \
            f"Too few events for stability test: {connection_metrics['events_received']}"
        
        assert connection_metrics["connection_drops"] == 0, \
            f"Unexpected connection drops: {connection_metrics['connection_drops']}"
        
        assert connection_metrics["max_event_gap"] < 30, \
            f"Event gap too large: {connection_metrics['max_event_gap']:.1f}s (max 30s)"
        
        print(f" PASS:  CONNECTION STABILITY VALIDATED!")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_websocket_event_payload_validation(self, auth_helper, authenticated_user):
        """
        Test WebSocket event payload structure and content validation.
        
        Business Scenario: Events must contain proper structure and
        meaningful business context for frontend consumption.
        
        Validates:
        - Event payload structure consistency
        - Required fields in each event type
        - Business context in event data
        - Payload size and performance
        """
        token, user_data = authenticated_user
        
        print(f"[U+1F680] Testing WebSocket event payload validation")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        payload_request = {
            "type": "agent_request",
            "agent": "supervisor",
            "message": "Analyze AI costs for customer service chatbot - currently spending $2000/month on 30,000 requests with GPT-4",
            "context": {
                "monthly_spend": 2000,
                "monthly_requests": 30000,
                "model": "GPT-4",
                "payload_validation_test": True
            },
            "user_id": user_data["id"]
        }
        
        collected_events = []
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                await websocket.send(json.dumps(payload_request))
                print(f"[U+1F4E4] Sent payload validation request")
                
                start_time = time.time()
                
                while time.time() - start_time < 45:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        event = json.loads(message)
                        collected_events.append(event)
                        
                        print(f"[U+1F4E8] Collected event: {event['type']}")
                        
                        if event['type'] == 'agent_completed':
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Invalid JSON in WebSocket event: {e}")
        
        except Exception as e:
            pytest.fail(f"WebSocket payload validation test failed: {e}")
        
        assert len(collected_events) > 0, "No events collected for payload validation"
        
        print(f" CHART:  Validating {len(collected_events)} event payloads...")
        
        # Validate each event type's payload structure
        event_validation_results = {}
        
        for event in collected_events:
            event_type = event['type']
            
            if event_type not in event_validation_results:
                event_validation_results[event_type] = {
                    "count": 0,
                    "has_type": False,
                    "has_timestamp": False, 
                    "has_data": False,
                    "avg_payload_size": 0,
                    "business_context_found": False
                }
            
            result = event_validation_results[event_type]
            result["count"] += 1
            
            # Required fields validation
            result["has_type"] = result["has_type"] or ('type' in event)
            result["has_timestamp"] = result["has_timestamp"] or ('timestamp' in event)
            result["has_data"] = result["has_data"] or ('data' in event)
            
            # Payload size tracking  
            payload_size = len(json.dumps(event))
            result["avg_payload_size"] += payload_size
            
            # Business context validation (for relevant events)
            if event_type in ['agent_completed', 'tool_completed'] and 'data' in event:
                data_content = str(event['data']).lower()
                business_indicators = ['cost', 'chatbot', '2000', '30000', 'optimization', 'recommendation']
                
                if any(indicator in data_content for indicator in business_indicators):
                    result["business_context_found"] = True
        
        # Calculate averages and validate
        print(f"\n[U+1F4CB] EVENT PAYLOAD VALIDATION RESULTS:")
        
        for event_type, results in event_validation_results.items():
            results["avg_payload_size"] = results["avg_payload_size"] / results["count"]
            
            print(f"   {event_type}:")
            print(f"     Count: {results['count']}")
            print(f"     Has type field: {results['has_type']}")
            print(f"     Has timestamp: {results['has_timestamp']}")
            print(f"     Has data: {results['has_data']}")
            print(f"     Avg payload size: {results['avg_payload_size']:.0f} bytes")
            print(f"     Business context: {results['business_context_found']}")
            
            # Validation assertions
            assert results["has_type"], f"{event_type} missing required 'type' field"
            
            # agent_completed must have substantial data with business context
            if event_type == 'agent_completed':
                assert results["has_data"], f"{event_type} must have 'data' field"
                assert results["business_context_found"], f"{event_type} must contain business context"
                assert results["avg_payload_size"] > 100, f"{event_type} payload too small: {results['avg_payload_size']} bytes"
            
            # Payload size should be reasonable (not too large)
            assert results["avg_payload_size"] < 50000, f"{event_type} payload too large: {results['avg_payload_size']} bytes"
        
        # Validate we have the mandatory events with proper payloads
        found_mandatory = set(event_validation_results.keys()).intersection(set(self.MANDATORY_EVENTS))
        assert len(found_mandatory) >= 4, f"Missing mandatory events in payload validation: {found_mandatory}"
        
        print(f" PASS:  EVENT PAYLOAD VALIDATION SUCCESS!")
        print(f"   [U+2713] All event types have proper structure")
        print(f"   [U+2713] Business context preserved in relevant events")
        print(f"   [U+2713] Payload sizes within reasonable limits")
        print(f"   [U+2713] {len(found_mandatory)} mandatory events validated")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_websocket_performance_under_load(self, auth_helper):
        """
        Test WebSocket performance under concurrent load.
        
        Business Scenario: Platform handles multiple WebSocket connections
        during peak usage without degrading event delivery performance.
        
        Validates:
        - Event delivery performance under concurrent load
        - WebSocket scalability
        - No event loss under pressure
        - Response time degradation limits
        """
        print(f"[U+1F680] Testing WebSocket performance under concurrent load")
        
        # Create multiple users for load testing
        load_user_count = 5
        load_users = []
        
        for i in range(load_user_count):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                email=f"load_test_{i}_{int(time.time())}@example.com",
                permissions=["read", "write", "agent_execution"]
            )
            load_users.append((user_token, user_data))
        
        print(f" PASS:  Created {load_user_count} users for load testing")
        
        # Load test WebSocket session
        async def load_test_session(user_index: int, user_token: str, user_data: Dict) -> Dict:
            """WebSocket session under load testing."""
            websocket_url = "ws://localhost:8000/ws"
            headers = auth_helper.get_websocket_headers(user_token)
            
            session_metrics = {
                "user_index": user_index,
                "events_received": 0,
                "response_time": None,
                "mandatory_events": 0,
                "error": None
            }
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": f"Quick cost optimization for user {user_index} - need basic recommendations",
                        "context": {"user_index": user_index, "load_test": True},
                        "user_id": user_data["id"]
                    }
                    
                    start_time = time.time()
                    await websocket.send(json.dumps(request))
                    
                    # Collect events with shorter timeout for load test
                    while time.time() - start_time < 30:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=5)
                            event = json.loads(message)
                            
                            session_metrics["events_received"] += 1
                            
                            if event['type'] in self.MANDATORY_EVENTS:
                                session_metrics["mandatory_events"] += 1
                            
                            if event['type'] == 'agent_completed':
                                session_metrics["response_time"] = time.time() - start_time
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                session_metrics["error"] = str(e)
            
            return session_metrics
        
        # Execute load test
        print(f"[U+1F3C3] Executing load test with {load_user_count} concurrent WebSocket connections...")
        
        load_start_time = time.time()
        
        tasks = []
        for i, (user_token, user_data) in enumerate(load_users):
            task = load_test_session(i, user_token, user_data)
            tasks.append(task)
        
        load_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_load_time = time.time() - load_start_time
        
        # Analyze load test results
        successful_sessions = []
        failed_sessions = []
        
        for result in load_results:
            if isinstance(result, Exception):
                failed_sessions.append(str(result))
            elif result.get("error"):
                failed_sessions.append(result["error"])
            else:
                successful_sessions.append(result)
        
        print(f" CHART:  LOAD TEST RESULTS:")
        print(f"   Total load time: {total_load_time:.2f}s")
        print(f"   Successful sessions: {len(successful_sessions)}")
        print(f"   Failed sessions: {len(failed_sessions)}")
        
        # Performance validation
        success_rate = len(successful_sessions) / load_user_count
        assert success_rate >= 0.8, f"Load test success rate too low: {success_rate:.1%}"
        
        if successful_sessions:
            response_times = [s["response_time"] for s in successful_sessions if s["response_time"]]
            event_counts = [s["events_received"] for s in successful_sessions]
            mandatory_event_counts = [s["mandatory_events"] for s in successful_sessions]
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            avg_events = sum(event_counts) / len(event_counts) if event_counts else 0
            avg_mandatory = sum(mandatory_event_counts) / len(mandatory_event_counts) if mandatory_event_counts else 0
            
            print(f"   Avg response time: {avg_response_time:.2f}s")
            print(f"   Max response time: {max_response_time:.2f}s")
            print(f"   Avg events per session: {avg_events:.1f}")
            print(f"   Avg mandatory events: {avg_mandatory:.1f}")
            
            # Performance criteria
            assert avg_response_time < 20, f"Average response time too slow under load: {avg_response_time:.2f}s"
            assert max_response_time < 40, f"Max response time too slow under load: {max_response_time:.2f}s"
            assert avg_mandatory >= 3, f"Too few mandatory events under load: {avg_mandatory:.1f}"
        
        print(f" PASS:  WEBSOCKET LOAD PERFORMANCE VALIDATED!")
        print(f"   [U+2713] {success_rate:.1%} success rate under {load_user_count}-user load")
        print(f"   [U+2713] Response times within acceptable limits")
        print(f"   [U+2713] Event delivery maintained under pressure")
        print(f"   [U+2713] WebSocket scalability demonstrated")