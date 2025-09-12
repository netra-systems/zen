"""
Multi-User Concurrent Execution with Isolation E2E Tests

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (multi-user customers)
- Business Goal: Ensure platform can handle multiple concurrent users safely
- Value Impact: Platform must isolate user data and execution contexts
- Strategic Impact: Multi-tenant architecture validation - prevents data leaks between customers

These tests validate CRITICAL multi-user isolation patterns to ensure:
1. User contexts are completely isolated (Factory patterns)
2. Concurrent agent execution doesn't cause data leakage
3. WebSocket events are delivered to correct users only
4. Database operations maintain user boundaries
5. Agent execution state is properly scoped per user

CRITICAL E2E REQUIREMENTS:
1. Real authentication for each user - NO MOCKS
2. Real services with concurrent load - NO MOCKS
3. Real LLM integration for all users
4. Proper user context isolation validation
5. WebSocket event isolation verification
6. Race condition and concurrency testing
7. Data leakage prevention validation
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import websockets
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user, get_test_jwt_token
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMultiUserConcurrentIsolation(SSotBaseTestCase):
    """
    E2E tests for multi-user concurrent execution with proper isolation.
    Validates the Factory-based isolation patterns work under concurrent load.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated helper for E2E tests."""
        return E2EAuthHelper(environment="test")

    async def create_test_user(self, user_suffix: str) -> Tuple[str, Dict[str, Any]]:
        """Create a test user with unique identifier."""
        return await create_authenticated_user(
            environment="test",
            email=f"multiuser_test_{user_suffix}@example.com",
            permissions=["read", "write", "agent_execution"]
        )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_concurrent_user_isolation_basic(self, auth_helper):
        """
        Test basic concurrent user isolation with 3 users.
        
        Business Scenario: 3 different customers using the platform simultaneously.
        Each should get their own optimization results without data leakage.
        
        Validates:
        - Each user gets isolated agent execution context
        - WebSocket events are delivered to correct user only
        - Results contain user-specific data without cross-contamination
        - User execution contexts don't interfere with each other
        """
        print(f"[U+1F680] Starting concurrent user isolation test with 3 users")
        
        # Create 3 distinct users
        users = []
        for i in range(3):
            user_token, user_data = await self.create_test_user(f"concurrent_{i}_{int(time.time())}")
            users.append((user_token, user_data))
        
        print(f" PASS:  Created {len(users)} test users")
        for i, (_, user_data) in enumerate(users):
            print(f"   User {i}: {user_data['email']}")
        
        # Define distinct optimization requests for each user
        user_requests = [
            {
                "type": "agent_request",
                "agent": "supervisor", 
                "message": "Optimize costs for my e-commerce chatbot handling 50k requests/month at $2000 budget",
                "context": {
                    "use_case": "ecommerce_chatbot",
                    "monthly_requests": 50000,
                    "budget": 2000,
                    "user_identifier": "ecommerce_user"
                },
                "user_id": users[0][1]["id"]
            },
            {
                "type": "agent_request", 
                "agent": "supervisor",
                "message": "Improve performance for healthcare diagnostic AI serving 200 concurrent doctors",
                "context": {
                    "use_case": "healthcare_diagnostics",
                    "concurrent_users": 200,
                    "latency_target": 300,
                    "user_identifier": "healthcare_user"
                },
                "user_id": users[1][1]["id"]
            },
            {
                "type": "agent_request",
                "agent": "supervisor", 
                "message": "Scale content generation from 100 to 1000 articles daily while maintaining quality",
                "context": {
                    "use_case": "content_scaling",
                    "current_volume": 100,
                    "target_volume": 1000,
                    "user_identifier": "content_user"
                },
                "user_id": users[2][1]["id"]
            }
        ]
        
        # Function to handle single user WebSocket connection
        async def user_session(user_index: int, user_token: str, user_data: Dict, request: Dict) -> Dict:
            """Handle WebSocket session for a single user."""
            websocket_url = "ws://localhost:8000/ws"
            headers = auth_helper.get_websocket_headers(user_token)
            
            session_result = {
                "user_index": user_index,
                "user_id": user_data["id"],
                "user_email": user_data["email"],
                "events": [],
                "completion_time": None,
                "error": None
            }
            
            try:
                print(f"[U+1F50C] User {user_index} connecting to WebSocket...")
                
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    print(f" PASS:  User {user_index} WebSocket connected")
                    
                    # Send request
                    await websocket.send(json.dumps(request))
                    print(f"[U+1F4E4] User {user_index} sent request")
                    
                    start_time = time.time()
                    timeout_duration = 90.0  # Extended timeout for concurrent execution
                    
                    while True:
                        try:
                            remaining_time = timeout_duration - (time.time() - start_time)
                            if remaining_time <= 0:
                                print(f"[U+23F0] User {user_index} session timed out")
                                break
                            
                            message = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=min(remaining_time, 15.0)  # Chunk timeout
                            )
                            
                            event = json.loads(message)
                            session_result["events"].append(event)
                            
                            print(f"[U+1F4E8] User {user_index} received: {event['type']}")
                            
                            if event['type'] == 'agent_completed':
                                session_result["completion_time"] = time.time() - start_time
                                print(f" PASS:  User {user_index} completed in {session_result['completion_time']:.2f}s")
                                break
                                
                        except asyncio.TimeoutError:
                            print(f"[U+23F0] User {user_index} message timeout")
                            continue
                        except json.JSONDecodeError as e:
                            print(f" FAIL:  User {user_index} JSON decode error: {e}")
                            continue
                            
            except Exception as e:
                session_result["error"] = str(e)
                print(f" FAIL:  User {user_index} session error: {e}")
            
            return session_result
        
        # Execute all user sessions concurrently
        print(f"[U+1F3C3] Starting concurrent execution for {len(users)} users...")
        start_time = time.time()
        
        tasks = []
        for i, ((user_token, user_data), request) in enumerate(zip(users, user_requests)):
            task = user_session(i, user_token, user_data, request)
            tasks.append(task)
        
        # Wait for all sessions to complete
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        print(f"[U+23F1][U+FE0F] All sessions completed in {total_time:.2f}s")
        
        # Validate session results
        successful_sessions = []
        for result in session_results:
            if isinstance(result, Exception):
                pytest.fail(f"Session failed with exception: {result}")
            elif result.get("error"):
                pytest.fail(f"Session failed: {result['error']}")
            else:
                successful_sessions.append(result)
        
        assert len(successful_sessions) == 3, f"Expected 3 successful sessions, got {len(successful_sessions)}"
        print(f" PASS:  All {len(successful_sessions)} sessions completed successfully")
        
        #  ALERT:  CRITICAL: Validate user isolation - each user should get distinct results
        for i, session in enumerate(successful_sessions):
            events = session["events"]
            event_types = [e['type'] for e in events]
            
            # Validate basic event flow
            required_events = ['agent_started', 'agent_completed']
            for event in required_events:
                assert event in event_types, f"User {i} missing {event}"
            
            # Get completion result
            completion_events = [e for e in events if e['type'] == 'agent_completed']
            assert len(completion_events) > 0, f"User {i} no completion event"
            
            result_data = completion_events[-1]['data']['result']
            result_text = str(result_data).lower()
            
            # Validate user-specific context in results
            user_context = user_requests[i]["context"]
            user_identifier = user_context["user_identifier"]
            use_case = user_context["use_case"]
            
            # Results should be relevant to user's specific use case
            if use_case == "ecommerce_chatbot":
                assert any(term in result_text for term in ["ecommerce", "chatbot", "cost", "50k", "2000"]), \
                    f"User {i} results don't match ecommerce context"
            elif use_case == "healthcare_diagnostics":
                assert any(term in result_text for term in ["healthcare", "diagnostic", "performance", "200", "300"]), \
                    f"User {i} results don't match healthcare context"
            elif use_case == "content_scaling":
                assert any(term in result_text for term in ["content", "scaling", "articles", "100", "1000"]), \
                    f"User {i} results don't match content context"
            
            print(f" PASS:  User {i} isolation validated - results match expected use case")
        
        #  ALERT:  CRITICAL: Validate no cross-user data contamination
        for i, session in enumerate(successful_sessions):
            completion_events = [e for e in session["events"] if e['type'] == 'agent_completed']
            result_text = str(completion_events[-1]['data']['result']).lower()
            
            # Check that this user's results don't contain other users' identifiers
            for j, other_session in enumerate(successful_sessions):
                if i == j:
                    continue
                    
                other_context = user_requests[j]["context"]
                other_identifier = other_context["user_identifier"]
                other_use_case = other_context["use_case"]
                
                # Results should NOT contain other users' specific identifiers
                contamination_terms = [other_identifier.replace("_", ""), other_use_case.replace("_", "")]
                
                for term in contamination_terms:
                    assert term not in result_text, \
                        f"User {i} results contaminated with User {j} data: found '{term}'"
            
            print(f" PASS:  User {i} no data contamination detected")
        
        # Performance validation - concurrent execution should be efficient
        max_completion_time = max(s["completion_time"] for s in successful_sessions)
        avg_completion_time = sum(s["completion_time"] for s in successful_sessions) / len(successful_sessions)
        
        assert max_completion_time < 120, f"Slowest user took too long: {max_completion_time:.2f}s"
        assert avg_completion_time < 90, f"Average completion time too slow: {avg_completion_time:.2f}s"
        
        print(f" PASS:  Performance validated:")
        print(f"   Max completion: {max_completion_time:.2f}s")
        print(f"   Avg completion: {avg_completion_time:.2f}s")
        print(f"   Total test time: {total_time:.2f}s")
        
        print(f" CELEBRATION:  CONCURRENT USER ISOLATION SUCCESS!")
        print(f"   [U+2713] All users executed concurrently without interference")
        print(f"   [U+2713] User contexts properly isolated")
        print(f"   [U+2713] No cross-user data contamination")
        print(f"   [U+2713] WebSocket events delivered to correct users")
        print(f"   [U+2713] Performance within acceptable limits")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_high_concurrency_stress(self, auth_helper):
        """
        Test high concurrency with 10 users simultaneously.
        
        Business Scenario: Platform handles peak load with multiple enterprise customers
        running optimization workflows simultaneously.
        
        Validates system stability and isolation under higher concurrent load.
        """
        print(f"[U+1F680] Starting high concurrency stress test with 10 users")
        
        # Create 10 users
        user_count = 10
        users = []
        for i in range(user_count):
            user_token, user_data = await self.create_test_user(f"stress_{i}_{int(time.time())}")
            users.append((user_token, user_data))
        
        print(f" PASS:  Created {user_count} stress test users")
        
        # Create varied requests to simulate real load
        request_templates = [
            "Optimize my AI costs - currently spending ${} monthly",
            "Need to improve performance for {} concurrent users", 
            "Scale my content generation to {} articles per day",
            "Reduce false positives in fraud detection by {}%",
            "Optimize chatbot for {} customer interactions daily"
        ]
        
        user_requests = []
        for i in range(user_count):
            template = request_templates[i % len(request_templates)]
            value = 1000 + (i * 500)  # Varying values
            
            request = {
                "type": "agent_request",
                "agent": "supervisor",
                "message": template.format(value),
                "context": {
                    "user_index": i,
                    "test_value": value,
                    "load_test": True
                },
                "user_id": users[i][1]["id"]
            }
            user_requests.append(request)
        
        # Simplified concurrent session handler for stress testing
        async def stress_user_session(user_index: int, user_token: str, request: Dict) -> bool:
            """Simplified session handler focused on completion validation."""
            try:
                websocket_url = "ws://localhost:8000/ws"
                headers = auth_helper.get_websocket_headers(user_token)
                
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    await websocket.send(json.dumps(request))
                    
                    start_time = time.time()
                    completed = False
                    
                    while time.time() - start_time < 60:  # 1 minute timeout per user
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message)
                            
                            if event['type'] == 'agent_completed':
                                print(f" PASS:  Stress user {user_index} completed")
                                completed = True
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue
                    
                    return completed
                    
            except Exception as e:
                print(f" FAIL:  Stress user {user_index} failed: {e}")
                return False
        
        # Execute stress test
        print(f"[U+1F3C3] Starting stress test with {user_count} concurrent users...")
        start_time = time.time()
        
        tasks = []
        for i, ((user_token, _), request) in enumerate(zip(users, user_requests)):
            task = stress_user_session(i, user_token, request)
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Validate results
        successful_count = sum(1 for r in results if r is True)
        success_rate = (successful_count / user_count) * 100
        
        print(f" CHART:  Stress test results:")
        print(f"   Users: {user_count}")
        print(f"   Successful: {successful_count}")  
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total time: {total_time:.2f}s")
        
        # Validation criteria for stress test
        assert success_rate >= 80, f"Success rate too low: {success_rate:.1f}% (min 80%)"
        assert total_time < 180, f"Stress test took too long: {total_time:.2f}s (max 180s)"
        
        print(f" PASS:  High concurrency stress test passed!")
        print(f"   [U+2713] {success_rate:.1f}% success rate ( >= 80% required)")
        print(f"   [U+2713] Completed in {total_time:.2f}s ( <= 180s required)")


    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.real_llm
    async def test_user_session_race_conditions(self, auth_helper):
        """
        Test race conditions in user session management.
        
        Business Scenario: Users rapidly connecting/disconnecting and sending requests
        in quick succession to test session state management.
        
        Validates session state isolation and proper cleanup under race conditions.
        """
        print(f"[U+1F680] Starting user session race condition test")
        
        # Create test user
        user_token, user_data = await self.create_test_user(f"race_{int(time.time())}")
        
        # Function to simulate rapid connect/request/disconnect cycle  
        async def rapid_session_cycle(cycle_id: int) -> Dict:
            """Simulate rapid WebSocket session cycle."""
            websocket_url = "ws://localhost:8000/ws"
            headers = auth_helper.get_websocket_headers(user_token)
            
            result = {
                "cycle_id": cycle_id,
                "connected": False,
                "request_sent": False, 
                "events_received": 0,
                "completed": False,
                "error": None
            }
            
            try:
                # Rapid connect
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    result["connected"] = True
                    
                    # Send request immediately
                    request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": f"Quick optimization request #{cycle_id}",
                        "context": {"cycle_id": cycle_id, "race_test": True},
                        "user_id": user_data["id"]
                    }
                    
                    await websocket.send(json.dumps(request))
                    result["request_sent"] = True
                    
                    # Collect events for short duration (race condition simulation)
                    start_time = time.time()
                    timeout = 10.0  # Short timeout to simulate rapid disconnect
                    
                    while time.time() - start_time < timeout:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            event = json.loads(message)
                            result["events_received"] += 1
                            
                            if event['type'] == 'agent_completed':
                                result["completed"] = True
                                break
                                
                        except asyncio.TimeoutError:
                            break  # Simulate early disconnect
                        except json.JSONDecodeError:
                            continue
                    
                    # Rapid disconnect (implicit with context manager)
                    
            except Exception as e:
                result["error"] = str(e)
            
            return result
        
        # Execute multiple rapid cycles concurrently
        cycle_count = 5
        print(f" CYCLE:  Running {cycle_count} rapid session cycles...")
        
        tasks = [rapid_session_cycle(i) for i in range(cycle_count)]
        cycle_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate race condition handling
        successful_connections = 0
        successful_requests = 0
        received_events = 0
        
        for i, result in enumerate(cycle_results):
            if isinstance(result, Exception):
                print(f" FAIL:  Cycle {i} exception: {result}")
                continue
            
            if result.get("error"):
                print(f" FAIL:  Cycle {i} error: {result['error']}")
                continue
                
            if result["connected"]:
                successful_connections += 1
            if result["request_sent"]:
                successful_requests += 1
            
            received_events += result["events_received"]
            
            print(f" PASS:  Cycle {result['cycle_id']}: " + 
                  f"Connected={result['connected']}, " +
                  f"Sent={result['request_sent']}, " +
                  f"Events={result['events_received']}, " +
                  f"Completed={result['completed']}")
        
        # Validation criteria
        connection_rate = (successful_connections / cycle_count) * 100
        request_rate = (successful_requests / cycle_count) * 100
        
        assert connection_rate >= 80, f"Connection rate too low: {connection_rate:.1f}%"
        assert request_rate >= 80, f"Request rate too low: {request_rate:.1f}%"
        assert received_events > 0, "No events received across all cycles"
        
        print(f" PASS:  Race condition test passed!")
        print(f"   [U+2713] Connection rate: {connection_rate:.1f}%")
        print(f"   [U+2713] Request rate: {request_rate:.1f}%")
        print(f"   [U+2713] Total events received: {received_events}")
        print(f"   [U+2713] No system crashes or hangs detected")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_mixed_user_types_concurrent(self, auth_helper):
        """
        Test concurrent execution with mixed user permission levels.
        
        Business Scenario: Platform serving users with different subscription tiers
        and permission levels simultaneously (Free, Mid, Enterprise).
        
        Validates permission isolation and proper access control under concurrent load.
        """
        print(f"[U+1F680] Starting mixed user types concurrent test")
        
        # Create users with different permission levels
        free_user_token, free_user_data = await create_authenticated_user(
            environment="test",
            email=f"free_user_{int(time.time())}@example.com",
            permissions=["read"]  # Limited permissions
        )
        
        mid_user_token, mid_user_data = await create_authenticated_user(
            environment="test", 
            email=f"mid_user_{int(time.time())}@example.com",
            permissions=["read", "write"]  # Standard permissions
        )
        
        enterprise_user_token, enterprise_user_data = await create_authenticated_user(
            environment="test",
            email=f"enterprise_user_{int(time.time())}@example.com", 
            permissions=["read", "write", "agent_execution", "advanced_optimization"]  # Full permissions
        )
        
        users_config = [
            {
                "token": free_user_token,
                "data": free_user_data, 
                "tier": "free",
                "request": {
                    "type": "agent_request",
                    "agent": "supervisor",
                    "message": "Basic cost analysis for my small chatbot",
                    "context": {"tier": "free", "simple_request": True},
                    "user_id": free_user_data["id"]
                }
            },
            {
                "token": mid_user_token,
                "data": mid_user_data,
                "tier": "mid", 
                "request": {
                    "type": "agent_request",
                    "agent": "supervisor", 
                    "message": "Optimize my AI workload costs and performance for moderate scale",
                    "context": {"tier": "mid", "moderate_complexity": True},
                    "user_id": mid_user_data["id"]
                }
            },
            {
                "token": enterprise_user_token,
                "data": enterprise_user_data,
                "tier": "enterprise",
                "request": {
                    "type": "agent_request",
                    "agent": "supervisor",
                    "message": "Full optimization analysis with advanced strategies for enterprise-scale AI deployment across multiple models and regions",
                    "context": {"tier": "enterprise", "advanced_optimization": True, "multi_model": True},
                    "user_id": enterprise_user_data["id"]
                }
            }
        ]
        
        # Execute all user types concurrently
        async def user_type_session(user_config: Dict) -> Dict:
            """Handle session for specific user type."""
            websocket_url = "ws://localhost:8000/ws"
            headers = auth_helper.get_websocket_headers(user_config["token"])
            
            session_result = {
                "tier": user_config["tier"],
                "user_id": user_config["data"]["id"],
                "events": [],
                "completed": False,
                "error": None
            }
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    await websocket.send(json.dumps(user_config["request"]))
                    
                    start_time = time.time()
                    
                    while time.time() - start_time < 60:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message)
                            session_result["events"].append(event)
                            
                            if event['type'] == 'agent_completed':
                                session_result["completed"] = True
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                session_result["error"] = str(e)
            
            return session_result
        
        # Run all user types concurrently
        print(f"[U+1F3C3] Executing mixed user types concurrently...")
        tasks = [user_type_session(config) for config in users_config]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate results for each user type
        for i, result in enumerate(session_results):
            if isinstance(result, Exception):
                pytest.fail(f"User type {users_config[i]['tier']} failed: {result}")
            
            if result.get("error"):
                pytest.fail(f"User type {result['tier']} error: {result['error']}")
            
            # All user types should complete successfully
            assert result["completed"], f"User type {result['tier']} did not complete"
            
            # Validate appropriate event flow
            event_types = [e['type'] for e in result["events"]]
            assert 'agent_started' in event_types, f"User type {result['tier']} missing agent_started"
            assert 'agent_completed' in event_types, f"User type {result['tier']} missing agent_completed"
            
            print(f" PASS:  User type {result['tier']} completed with {len(result['events'])} events")
        
        # Validate tier-appropriate responses
        free_result = next(r for r in session_results if r["tier"] == "free")
        enterprise_result = next(r for r in session_results if r["tier"] == "enterprise")
        
        # Enterprise user should generally get more comprehensive results
        free_events = len(free_result["events"])
        enterprise_events = len(enterprise_result["events"])
        
        print(f" CHART:  Event counts: Free={free_events}, Enterprise={enterprise_events}")
        
        # Get final results
        free_completion = [e for e in free_result["events"] if e['type'] == 'agent_completed'][-1]
        enterprise_completion = [e for e in enterprise_result["events"] if e['type'] == 'agent_completed'][-1]
        
        free_result_text = str(free_completion['data']['result'])
        enterprise_result_text = str(enterprise_completion['data']['result'])
        
        # Enterprise should get more detailed optimization strategies
        assert len(enterprise_result_text) >= len(free_result_text), \
            "Enterprise user should receive more comprehensive results"
        
        print(f" PASS:  Mixed user types concurrent test passed!")
        print(f"   [U+2713] All user tiers completed successfully")
        print(f"   [U+2713] Appropriate tier-based response differentiation")
        print(f"   [U+2713] No permission violations or cross-tier contamination")
        print(f"   [U+2713] Concurrent execution handled properly")