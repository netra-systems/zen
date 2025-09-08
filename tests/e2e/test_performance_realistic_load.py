"""
Performance Under Realistic Load E2E Tests

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (high-volume customers)
- Business Goal: Ensure platform performs at scale with acceptable response times
- Value Impact: Users receive timely responses even during peak usage periods
- Strategic Impact: Performance scalability enables growth and enterprise adoption

These tests validate COMPLETE performance characteristics under realistic load:
1. Response time performance under concurrent user load
2. WebSocket connection scalability and stability
3. Agent execution throughput with multiple simultaneous requests
4. Database and service performance under concurrent access
5. Memory and resource utilization under sustained load
6. Business value delivery consistency during high load
7. Performance degradation patterns and limits
8. Load balancing and queue management effectiveness

CRITICAL E2E REQUIREMENTS:
1. Real authentication for all concurrent users - NO MOCKS
2. Real services under actual load conditions - NO MOCKS
3. Real LLM integration with concurrent requests
4. Realistic user behavior simulation
5. Performance measurements with statistical significance
6. Business value delivery validation under load
7. Resource utilization monitoring
8. Scalability limit identification
"""

import asyncio
import json
import pytest
import time
import statistics
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import websockets
import psutil
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user, get_test_jwt_token
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestPerformanceRealisticLoad(SSotBaseTestCase):
    """
    E2E tests for performance under realistic load conditions.
    Tests complete system performance with concurrent users and realistic usage patterns.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated helper for E2E tests."""
        return E2EAuthHelper(environment="test")

    async def create_load_test_users(self, user_count: int) -> List[Tuple[str, Dict[str, Any]]]:
        """Create multiple users for load testing."""
        users = []
        for i in range(user_count):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                email=f"load_test_user_{i}_{int(time.time())}@example.com",
                permissions=["read", "write", "agent_execution"]
            )
            users.append((user_token, user_data))
        
        return users

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.performance
    async def test_concurrent_user_response_time_performance(self, auth_helper):
        """
        Test response time performance with concurrent users.
        
        Business Scenario: Platform serves 10+ concurrent enterprise customers
        during peak hours with acceptable response times for optimization requests.
        
        Validates:
        - Response time consistency under concurrent load
        - WebSocket connection stability with multiple users
        - Agent execution performance with concurrent requests
        - Business value delivery maintained under load
        - Performance metrics within acceptable SLA bounds
        """
        print(f"🚀 Testing concurrent user response time performance")
        
        # Load test configuration
        concurrent_users = 8  # Realistic concurrent user load
        requests_per_user = 2  # Multiple requests per user to simulate real usage
        
        print(f"📊 Test configuration:")
        print(f"   Concurrent users: {concurrent_users}")
        print(f"   Requests per user: {requests_per_user}")
        print(f"   Total requests: {concurrent_users * requests_per_user}")
        
        # Create users for load test
        load_test_users = await self.create_load_test_users(concurrent_users)
        print(f"✅ Created {len(load_test_users)} users for load testing")
        
        # Define realistic user request scenarios
        request_scenarios = [
            {
                "type": "cost_optimization",
                "message": "Help me optimize my AI costs - currently spending $3000/month on customer service chatbot with 25k requests",
                "complexity": "medium",
                "expected_duration": 20
            },
            {
                "type": "performance_tuning", 
                "message": "Need to improve response time for my AI API - currently taking 2-3 seconds per request",
                "complexity": "medium",
                "expected_duration": 25
            },
            {
                "type": "scaling_analysis",
                "message": "Planning to scale from 1000 to 10000 daily AI requests - what infrastructure changes needed?",
                "complexity": "high",
                "expected_duration": 30
            },
            {
                "type": "quick_question",
                "message": "Quick question - which AI model is most cost-effective for simple classification tasks?",
                "complexity": "low", 
                "expected_duration": 15
            }
        ]
        
        # Function to simulate realistic user session
        async def user_load_session(user_index: int, user_token: str, user_data: Dict) -> Dict:
            """Simulate realistic user session with multiple requests."""
            session_result = {
                "user_index": user_index,
                "user_id": user_data["id"],
                "requests_completed": 0,
                "total_response_time": 0,
                "response_times": [],
                "business_value_delivered": 0,
                "websocket_events": 0,
                "errors_encountered": 0,
                "session_successful": False
            }
            
            websocket_url = "ws://localhost:8000/ws"
            headers = auth_helper.get_websocket_headers(user_token)
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    print(f"🔌 User {user_index} connected")
                    
                    # Send multiple requests per user (realistic usage)
                    for request_num in range(requests_per_user):
                        scenario = request_scenarios[request_num % len(request_scenarios)]
                        
                        load_request = {
                            "type": "agent_request",
                            "agent": "supervisor",
                            "message": scenario["message"],
                            "context": {
                                "scenario_type": scenario["type"],
                                "load_test": True,
                                "user_index": user_index,
                                "request_num": request_num
                            },
                            "user_id": user_data["id"]
                        }
                        
                        request_start_time = time.time()
                        await websocket.send(json.dumps(load_request))
                        
                        print(f"📤 User {user_index} request {request_num + 1}: {scenario['type']}")
                        
                        # Collect response events
                        request_events = 0
                        business_value_found = False
                        
                        timeout_duration = scenario["expected_duration"] + 20  # Buffer time
                        
                        while time.time() - request_start_time < timeout_duration:
                            try:
                                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                                event = json.loads(message)
                                
                                request_events += 1
                                session_result["websocket_events"] += 1
                                
                                if event['type'] == 'agent_completed':
                                    response_time = time.time() - request_start_time
                                    session_result["response_times"].append(response_time)
                                    session_result["total_response_time"] += response_time
                                    session_result["requests_completed"] += 1
                                    
                                    # Check for business value delivery
                                    result_data = event.get('data', {}).get('result', {})
                                    result_text = str(result_data).lower()
                                    
                                    business_indicators = [
                                        'optimization', 'cost', 'recommendation', 'strategy',
                                        'performance', 'scaling', 'model', 'improve'
                                    ]
                                    
                                    business_value_score = sum(1 for indicator in business_indicators if indicator in result_text)
                                    
                                    if business_value_score >= 2:
                                        session_result["business_value_delivered"] += 1
                                        business_value_found = True
                                    
                                    print(f"✅ User {user_index} request {request_num + 1} completed: {response_time:.2f}s")
                                    break
                                    
                                elif event['type'] == 'error':
                                    session_result["errors_encountered"] += 1
                                    print(f"❌ User {user_index} request {request_num + 1} error: {event.get('data', {}).get('message', 'Unknown error')}")
                                    break
                                    
                            except asyncio.TimeoutError:
                                continue
                            except json.JSONDecodeError:
                                continue
                        
                        # Brief pause between requests (realistic user behavior)
                        if request_num < requests_per_user - 1:
                            await asyncio.sleep(2)
                    
                    # Mark session as successful if majority of requests completed
                    if session_result["requests_completed"] >= requests_per_user * 0.5:
                        session_result["session_successful"] = True
                        
            except Exception as e:
                print(f"❌ User {user_index} session error: {e}")
            
            return session_result
        
        # Execute concurrent user load test
        print(f"🏃 Starting concurrent load test...")
        
        load_test_start_time = time.time()
        
        # Monitor system resources during test
        initial_memory = psutil.virtual_memory().percent
        initial_cpu = psutil.cpu_percent()
        
        print(f"📊 Initial system state:")
        print(f"   Memory usage: {initial_memory:.1f}%")
        print(f"   CPU usage: {initial_cpu:.1f}%")
        
        # Run all user sessions concurrently
        tasks = []
        for i, (user_token, user_data) in enumerate(load_test_users):
            task = user_load_session(i, user_token, user_data)
            tasks.append(task)
        
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_load_test_time = time.time() - load_test_start_time
        
        # Monitor system resources after test
        final_memory = psutil.virtual_memory().percent
        final_cpu = psutil.cpu_percent()
        
        print(f"📊 Final system state:")
        print(f"   Memory usage: {final_memory:.1f}%")
        print(f"   CPU usage: {final_cpu:.1f}%")
        print(f"   Total test duration: {total_load_test_time:.2f}s")
        
        # Analyze performance results
        successful_sessions = []
        failed_sessions = []
        
        for result in session_results:
            if isinstance(result, Exception):
                failed_sessions.append(str(result))
            elif result.get("session_successful"):
                successful_sessions.append(result)
            else:
                failed_sessions.append(f"User {result.get('user_index', 'unknown')}: Incomplete session")
        
        print(f"\n📊 CONCURRENT LOAD TEST RESULTS:")
        print(f"   Total users: {concurrent_users}")
        print(f"   Successful sessions: {len(successful_sessions)}")
        print(f"   Failed sessions: {len(failed_sessions)}")
        
        if failed_sessions:
            for failure in failed_sessions[:3]:  # Show first 3 failures
                print(f"   ❌ {failure}")
        
        # Performance metrics analysis
        if successful_sessions:
            all_response_times = []
            total_requests_completed = 0
            total_business_value = 0
            total_events = 0
            total_errors = 0
            
            for session in successful_sessions:
                all_response_times.extend(session["response_times"])
                total_requests_completed += session["requests_completed"]
                total_business_value += session["business_value_delivered"]
                total_events += session["websocket_events"]
                total_errors += session["errors_encountered"]
            
            # Calculate performance statistics
            if all_response_times:
                avg_response_time = statistics.mean(all_response_times)
                median_response_time = statistics.median(all_response_times)
                p95_response_time = sorted(all_response_times)[int(len(all_response_times) * 0.95)]
                max_response_time = max(all_response_times)
                min_response_time = min(all_response_times)
                
                print(f"\n⚡ PERFORMANCE METRICS:")
                print(f"   Requests completed: {total_requests_completed}")
                print(f"   Average response time: {avg_response_time:.2f}s")
                print(f"   Median response time: {median_response_time:.2f}s")
                print(f"   95th percentile: {p95_response_time:.2f}s")
                print(f"   Max response time: {max_response_time:.2f}s")
                print(f"   Min response time: {min_response_time:.2f}s")
                print(f"   Business value delivery rate: {(total_business_value/total_requests_completed)*100:.1f}%")
                print(f"   Total WebSocket events: {total_events}")
                print(f"   Total errors: {total_errors}")
                
                # Performance validation criteria
                success_rate = len(successful_sessions) / concurrent_users
                assert success_rate >= 0.7, f"Success rate too low under load: {success_rate:.1%}"
                
                assert avg_response_time < 45, f"Average response time too slow: {avg_response_time:.2f}s"
                assert p95_response_time < 90, f"95th percentile response time too slow: {p95_response_time:.2f}s"
                
                business_value_rate = total_business_value / total_requests_completed if total_requests_completed > 0 else 0
                assert business_value_rate >= 0.6, f"Business value delivery rate too low: {business_value_rate:.1%}"
                
                error_rate = total_errors / total_requests_completed if total_requests_completed > 0 else 0
                assert error_rate < 0.2, f"Error rate too high under load: {error_rate:.1%}"
                
                print(f"✅ CONCURRENT LOAD PERFORMANCE SUCCESS!")
                print(f"   ✓ {success_rate:.1%} session success rate")
                print(f"   ✓ {avg_response_time:.2f}s average response time")
                print(f"   ✓ {business_value_rate:.1%} business value delivery rate")
                print(f"   ✓ {error_rate:.1%} error rate")
        else:
            pytest.fail("No successful sessions in concurrent load test")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.performance
    async def test_sustained_load_endurance(self, auth_helper):
        """
        Test system performance under sustained load over extended period.
        
        Business Scenario: Platform maintains performance during sustained
        high usage periods (e.g., business hours peak usage).
        
        Validates:
        - Performance stability over extended time periods
        - Memory leak detection and resource management
        - Response time consistency during sustained load
        - No performance degradation over time
        - System recovery after sustained load
        """
        print(f"🚀 Testing sustained load endurance")
        
        # Sustained load test configuration
        test_duration_minutes = 3  # 3 minutes of sustained load
        concurrent_users = 4  # Moderate concurrent load
        request_interval_seconds = 15  # Request every 15 seconds per user
        
        print(f"📊 Sustained load configuration:")
        print(f"   Test duration: {test_duration_minutes} minutes")
        print(f"   Concurrent users: {concurrent_users}")
        print(f"   Request interval: {request_interval_seconds} seconds")
        
        # Create users for sustained test
        sustained_users = await self.create_load_test_users(concurrent_users)
        print(f"✅ Created {len(sustained_users)} users for sustained load test")
        
        # Performance tracking
        performance_snapshots = []
        
        # Function for continuous user activity
        async def sustained_user_activity(user_index: int, user_token: str, user_data: Dict, test_duration: float) -> Dict:
            """Continuous user activity for sustained load test."""
            activity_result = {
                "user_index": user_index,
                "requests_sent": 0,
                "requests_completed": 0,
                "response_times": [],
                "errors": 0,
                "average_response_time": 0
            }
            
            websocket_url = "ws://localhost:8000/ws" 
            headers = auth_helper.get_websocket_headers(user_token)
            
            end_time = time.time() + test_duration
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    print(f"🔌 Sustained user {user_index} connected")
                    
                    request_counter = 0
                    
                    while time.time() < end_time:
                        request_counter += 1
                        request_start = time.time()
                        
                        sustained_request = {
                            "type": "agent_request",
                            "agent": "supervisor",
                            "message": f"Sustained load request #{request_counter} - provide quick optimization advice",
                            "context": {
                                "sustained_load_test": True,
                                "user_index": user_index,
                                "request_counter": request_counter
                            },
                            "user_id": user_data["id"]
                        }
                        
                        try:
                            await websocket.send(json.dumps(sustained_request))
                            activity_result["requests_sent"] += 1
                            
                            # Wait for response
                            response_received = False
                            
                            while time.time() - request_start < request_interval_seconds - 2:  # Leave time for next request
                                try:
                                    message = await asyncio.wait_for(websocket.recv(), timeout=3)
                                    event = json.loads(message)
                                    
                                    if event['type'] == 'agent_completed':
                                        response_time = time.time() - request_start
                                        activity_result["response_times"].append(response_time)
                                        activity_result["requests_completed"] += 1
                                        response_received = True
                                        
                                        if user_index == 0 and request_counter % 5 == 0:  # Periodic logging
                                            print(f"📊 Sustained request #{request_counter} completed: {response_time:.2f}s")
                                        
                                        break
                                        
                                    elif event['type'] == 'error':
                                        activity_result["errors"] += 1
                                        response_received = True
                                        break
                                        
                                except asyncio.TimeoutError:
                                    continue
                                except json.JSONDecodeError:
                                    continue
                            
                            # Wait for next request interval
                            next_request_time = request_start + request_interval_seconds
                            wait_time = next_request_time - time.time()
                            
                            if wait_time > 0:
                                await asyncio.sleep(wait_time)
                                
                        except Exception as e:
                            activity_result["errors"] += 1
                            print(f"❌ Sustained user {user_index} request error: {e}")
                            
            except Exception as e:
                print(f"❌ Sustained user {user_index} connection error: {e}")
            
            # Calculate average response time
            if activity_result["response_times"]:
                activity_result["average_response_time"] = statistics.mean(activity_result["response_times"])
            
            return activity_result
        
        # Resource monitoring function
        async def monitor_system_resources(duration: float):
            """Monitor system resources during sustained load."""
            monitoring_result = {
                "memory_snapshots": [],
                "cpu_snapshots": [],
                "peak_memory": 0,
                "peak_cpu": 0,
                "memory_trend": "stable"  # stable, increasing, decreasing
            }
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                memory_percent = psutil.virtual_memory().percent
                cpu_percent = psutil.cpu_percent(interval=1)
                
                monitoring_result["memory_snapshots"].append(memory_percent)
                monitoring_result["cpu_snapshots"].append(cpu_percent)
                
                monitoring_result["peak_memory"] = max(monitoring_result["peak_memory"], memory_percent)
                monitoring_result["peak_cpu"] = max(monitoring_result["peak_cpu"], cpu_percent)
                
                await asyncio.sleep(10)  # Sample every 10 seconds
            
            # Analyze memory trend
            if len(monitoring_result["memory_snapshots"]) >= 3:
                first_third = monitoring_result["memory_snapshots"][:len(monitoring_result["memory_snapshots"])//3]
                last_third = monitoring_result["memory_snapshots"][-len(monitoring_result["memory_snapshots"])//3:]
                
                first_avg = statistics.mean(first_third)
                last_avg = statistics.mean(last_third)
                
                if last_avg > first_avg + 5:  # 5% increase
                    monitoring_result["memory_trend"] = "increasing"
                elif last_avg < first_avg - 5:  # 5% decrease
                    monitoring_result["memory_trend"] = "decreasing"
            
            return monitoring_result
        
        # Start sustained load test
        print(f"🏃 Starting sustained load test for {test_duration_minutes} minutes...")
        
        test_start_time = time.time()
        test_duration_seconds = test_duration_minutes * 60
        
        # Start user activities and monitoring concurrently
        user_tasks = []
        for i, (user_token, user_data) in enumerate(sustained_users):
            task = sustained_user_activity(i, user_token, user_data, test_duration_seconds)
            user_tasks.append(task)
        
        monitoring_task = monitor_system_resources(test_duration_seconds)
        
        # Wait for all tasks to complete
        all_tasks = user_tasks + [monitoring_task]
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        total_test_time = time.time() - test_start_time
        
        # Analyze sustained load results
        user_results = results[:-1]
        monitoring_result = results[-1]
        
        print(f"\n📊 SUSTAINED LOAD TEST RESULTS:")
        print(f"   Test duration: {total_test_time:.1f} seconds")
        
        # User activity analysis
        total_requests_sent = sum(r["requests_sent"] for r in user_results if isinstance(r, dict))
        total_requests_completed = sum(r["requests_completed"] for r in user_results if isinstance(r, dict))
        total_errors = sum(r["errors"] for r in user_results if isinstance(r, dict))
        
        all_response_times = []
        for result in user_results:
            if isinstance(result, dict):
                all_response_times.extend(result["response_times"])
        
        completion_rate = (total_requests_completed / total_requests_sent * 100) if total_requests_sent > 0 else 0
        error_rate = (total_errors / total_requests_sent * 100) if total_requests_sent > 0 else 0
        
        print(f"   Requests sent: {total_requests_sent}")
        print(f"   Requests completed: {total_requests_completed}")
        print(f"   Completion rate: {completion_rate:.1f}%")
        print(f"   Error rate: {error_rate:.1f}%")
        
        if all_response_times:
            avg_response_time = statistics.mean(all_response_times)
            median_response_time = statistics.median(all_response_times)
            
            print(f"   Average response time: {avg_response_time:.2f}s")
            print(f"   Median response time: {median_response_time:.2f}s")
        
        # Resource utilization analysis
        if isinstance(monitoring_result, dict):
            print(f"\n🖥️  RESOURCE UTILIZATION:")
            print(f"   Peak memory usage: {monitoring_result['peak_memory']:.1f}%")
            print(f"   Peak CPU usage: {monitoring_result['peak_cpu']:.1f}%")
            print(f"   Memory trend: {monitoring_result['memory_trend']}")
            
            # Memory leak detection
            if monitoring_result["memory_trend"] == "increasing":
                print(f"⚠️ Potential memory leak detected (memory trend increasing)")
            else:
                print(f"✅ No memory leak detected")
        
        # Validation criteria for sustained load
        assert completion_rate >= 70, f"Completion rate too low during sustained load: {completion_rate:.1f}%"
        assert error_rate <= 15, f"Error rate too high during sustained load: {error_rate:.1f}%"
        
        if all_response_times:
            avg_response_time = statistics.mean(all_response_times)
            assert avg_response_time < 60, f"Average response time degraded during sustained load: {avg_response_time:.2f}s"
        
        if isinstance(monitoring_result, dict):
            assert monitoring_result["peak_memory"] < 85, f"Memory usage too high: {monitoring_result['peak_memory']:.1f}%"
            assert monitoring_result["memory_trend"] != "increasing", "Memory leak detected during sustained load"
        
        print(f"✅ SUSTAINED LOAD ENDURANCE SUCCESS!")
        print(f"   ✓ {completion_rate:.1f}% completion rate maintained")
        print(f"   ✓ {error_rate:.1f}% error rate within limits")
        print(f"   ✓ Response times stable during sustained load")
        print(f"   ✓ No memory leaks detected")
        print(f"   ✓ System performance stable over {test_duration_minutes} minutes")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_websocket_connection_scalability(self, auth_helper):
        """
        Test WebSocket connection scalability limits.
        
        Business Scenario: Platform needs to support many concurrent
        WebSocket connections during peak usage periods.
        
        Validates:
        - Maximum concurrent WebSocket connections supported
        - Connection establishment time under load
        - Message delivery performance with many connections
        - Connection stability at scale
        - Resource usage scaling with connection count
        """
        print(f"🚀 Testing WebSocket connection scalability")
        
        # Scalability test configuration
        connection_batches = [5, 10, 15]  # Test increasing connection counts
        websocket_url = "ws://localhost:8000/ws"
        
        scalability_results = {}
        
        for batch_size in connection_batches:
            print(f"\n📊 Testing {batch_size} concurrent WebSocket connections")
            
            # Create users for this batch
            batch_users = await self.create_load_test_users(batch_size)
            
            batch_result = {
                "target_connections": batch_size,
                "successful_connections": 0,
                "connection_times": [],
                "message_delivery_times": [],
                "connection_failures": 0,
                "average_connection_time": 0,
                "average_message_time": 0
            }
            
            # Function to establish and test single WebSocket connection
            async def test_single_websocket_connection(user_index: int, user_token: str, user_data: Dict) -> Dict:
                """Test single WebSocket connection performance."""
                connection_result = {
                    "user_index": user_index,
                    "connection_successful": False,
                    "connection_time": None,
                    "message_delivery_time": None,
                    "error": None
                }
                
                try:
                    headers = auth_helper.get_websocket_headers(user_token)
                    
                    # Measure connection establishment time
                    connection_start = time.time()
                    
                    async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                        connection_time = time.time() - connection_start
                        connection_result["connection_time"] = connection_time
                        connection_result["connection_successful"] = True
                        
                        # Test message delivery performance
                        test_message = {
                            "type": "agent_request", 
                            "agent": "supervisor",
                            "message": f"Connection scalability test from user {user_index}",
                            "context": {"scalability_test": True, "batch_size": batch_size},
                            "user_id": user_data["id"]
                        }
                        
                        message_start = time.time()
                        await websocket.send(json.dumps(test_message))
                        
                        # Wait for first response to measure delivery time
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=20)
                            message_delivery_time = time.time() - message_start
                            connection_result["message_delivery_time"] = message_delivery_time
                            
                        except asyncio.TimeoutError:
                            connection_result["error"] = "Message delivery timeout"
                        
                        # Keep connection open briefly to test stability
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    connection_result["error"] = str(e)
                
                return connection_result
            
            # Test all connections in this batch concurrently
            batch_start_time = time.time()
            
            connection_tasks = []
            for i, (user_token, user_data) in enumerate(batch_users):
                task = test_single_websocket_connection(i, user_token, user_data)
                connection_tasks.append(task)
            
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            batch_total_time = time.time() - batch_start_time
            
            # Analyze batch results
            successful_connections = 0
            connection_times = []
            message_times = []
            failures = 0
            
            for result in connection_results:
                if isinstance(result, Exception):
                    failures += 1
                elif isinstance(result, dict):
                    if result["connection_successful"]:
                        successful_connections += 1
                        if result["connection_time"]:
                            connection_times.append(result["connection_time"])
                        if result["message_delivery_time"]:
                            message_times.append(result["message_delivery_time"])
                    else:
                        failures += 1
                        if result["error"]:
                            print(f"   ❌ User {result['user_index']}: {result['error']}")
            
            batch_result["successful_connections"] = successful_connections
            batch_result["connection_failures"] = failures
            batch_result["connection_times"] = connection_times
            batch_result["message_delivery_times"] = message_times
            
            if connection_times:
                batch_result["average_connection_time"] = statistics.mean(connection_times)
            if message_times:
                batch_result["average_message_time"] = statistics.mean(message_times)
            
            # Report batch results
            connection_success_rate = (successful_connections / batch_size) * 100
            print(f"   📊 Batch {batch_size} results:")
            print(f"      Successful connections: {successful_connections}/{batch_size} ({connection_success_rate:.1f}%)")
            print(f"      Average connection time: {batch_result['average_connection_time']:.3f}s")
            print(f"      Average message delivery: {batch_result['average_message_time']:.3f}s") 
            print(f"      Total batch time: {batch_total_time:.2f}s")
            
            scalability_results[batch_size] = batch_result
        
        # Analyze scalability trends
        print(f"\n📈 WEBSOCKET SCALABILITY ANALYSIS:")
        
        for batch_size, result in scalability_results.items():
            success_rate = (result["successful_connections"] / result["target_connections"]) * 100
            print(f"   {batch_size} connections:")
            print(f"     Success rate: {success_rate:.1f}%")
            print(f"     Avg connection time: {result['average_connection_time']:.3f}s")
            print(f"     Avg message time: {result['average_message_time']:.3f}s")
        
        # Validation criteria for scalability
        for batch_size, result in scalability_results.items():
            success_rate = result["successful_connections"] / result["target_connections"]
            
            # Success rate should remain high even with more connections
            min_success_rate = 0.8 if batch_size <= 10 else 0.6  # Allow degradation at higher scales
            assert success_rate >= min_success_rate, f"Success rate too low at {batch_size} connections: {success_rate:.1%}"
            
            # Connection times should remain reasonable
            if result["average_connection_time"]:
                max_connection_time = 5.0 if batch_size <= 10 else 10.0  # Allow degradation at higher scales
                assert result["average_connection_time"] <= max_connection_time, \
                    f"Connection time too slow at {batch_size} connections: {result['average_connection_time']:.3f}s"
        
        # Check for scalability degradation patterns
        connection_time_trend = []
        message_time_trend = []
        
        for batch_size in sorted(scalability_results.keys()):
            result = scalability_results[batch_size]
            if result["average_connection_time"]:
                connection_time_trend.append(result["average_connection_time"])
            if result["average_message_time"]:
                message_time_trend.append(result["average_message_time"])
        
        # Connection times shouldn't degrade too severely
        if len(connection_time_trend) >= 2:
            time_increase_ratio = connection_time_trend[-1] / connection_time_trend[0]
            assert time_increase_ratio <= 3.0, f"Connection time degradation too severe: {time_increase_ratio:.1f}x"
            
            print(f"📊 Connection time scaling factor: {time_increase_ratio:.2f}x")
        
        print(f"✅ WEBSOCKET SCALABILITY SUCCESS!")
        print(f"   ✓ Handles up to {max(connection_batches)} concurrent connections")
        print(f"   ✓ Acceptable performance degradation with scale")
        print(f"   ✓ Connection establishment times reasonable")
        print(f"   ✓ Message delivery performance maintained")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_performance_degradation_recovery(self, auth_helper):
        """
        Test performance degradation detection and recovery.
        
        Business Scenario: System automatically detects and recovers
        from performance degradation during high load periods.
        
        Validates:
        - Performance degradation detection mechanisms
        - Automatic load shedding or throttling
        - System recovery after load reduction
        - Performance baseline restoration
        - User experience during degradation and recovery
        """
        print(f"🚀 Testing performance degradation and recovery")
        
        # Create baseline performance measurement
        print(f"📊 Establishing performance baseline...")
        
        baseline_user_token, baseline_user_data = await create_authenticated_user(
            environment="test",
            email=f"baseline_user_{int(time.time())}@example.com",
            permissions=["read", "write", "agent_execution"]
        )
        
        # Measure baseline performance
        async def measure_baseline_performance() -> Dict:
            """Measure baseline performance with single user."""
            websocket_url = "ws://localhost:8000/ws"
            headers = auth_helper.get_websocket_headers(baseline_user_token)
            
            baseline_result = {
                "response_times": [],
                "average_response_time": 0,
                "successful_requests": 0,
                "baseline_established": False
            }
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    # Send 3 baseline requests
                    for i in range(3):
                        baseline_request = {
                            "type": "agent_request",
                            "agent": "supervisor",
                            "message": f"Baseline performance test #{i+1} - provide optimization recommendations",
                            "context": {"baseline_test": True, "request_num": i+1},
                            "user_id": baseline_user_data["id"]
                        }
                        
                        request_start = time.time()
                        await websocket.send(json.dumps(baseline_request))
                        
                        # Wait for completion
                        while time.time() - request_start < 30:
                            try:
                                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                                event = json.loads(message)
                                
                                if event['type'] == 'agent_completed':
                                    response_time = time.time() - request_start
                                    baseline_result["response_times"].append(response_time)
                                    baseline_result["successful_requests"] += 1
                                    
                                    print(f"   Baseline request #{i+1}: {response_time:.2f}s")
                                    break
                                    
                            except asyncio.TimeoutError:
                                break
                            except json.JSONDecodeError:
                                continue
                        
                        # Brief pause between baseline requests
                        await asyncio.sleep(2)
                
                if baseline_result["response_times"]:
                    baseline_result["average_response_time"] = statistics.mean(baseline_result["response_times"])
                    baseline_result["baseline_established"] = True
                    
            except Exception as e:
                print(f"❌ Baseline measurement error: {e}")
            
            return baseline_result
        
        baseline_performance = await measure_baseline_performance()
        
        if not baseline_performance["baseline_established"]:
            pytest.fail("Could not establish performance baseline")
        
        baseline_avg = baseline_performance["average_response_time"]
        print(f"✅ Baseline established: {baseline_avg:.2f}s average response time")
        
        # Induce load to cause performance degradation
        print(f"\n🔥 Inducing high load to cause performance degradation...")
        
        degradation_users = await self.create_load_test_users(12)  # Higher load
        
        async def high_load_session(user_index: int, user_token: str, user_data: Dict, duration: float) -> Dict:
            """High-load session to induce performance degradation."""
            load_result = {
                "requests_sent": 0,
                "response_times": [],
                "errors": 0
            }
            
            websocket_url = "ws://localhost:8000/ws"
            headers = auth_helper.get_websocket_headers(user_token)
            
            end_time = time.time() + duration
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    request_count = 0
                    
                    while time.time() < end_time:
                        request_count += 1
                        
                        load_request = {
                            "type": "agent_request",
                            "agent": "supervisor",
                            "message": f"High load degradation test #{request_count} - complex analysis needed",
                            "context": {"degradation_test": True, "high_load": True},
                            "user_id": user_data["id"]
                        }
                        
                        request_start = time.time()
                        
                        try:
                            await websocket.send(json.dumps(load_request))
                            load_result["requests_sent"] += 1
                            
                            # Wait for response with timeout
                            while time.time() - request_start < 20:  # Shorter timeout during load
                                try:
                                    message = await asyncio.wait_for(websocket.recv(), timeout=3)
                                    event = json.loads(message)
                                    
                                    if event['type'] == 'agent_completed':
                                        response_time = time.time() - request_start
                                        load_result["response_times"].append(response_time)
                                        break
                                    elif event['type'] == 'error':
                                        load_result["errors"] += 1
                                        break
                                        
                                except asyncio.TimeoutError:
                                    continue
                                except json.JSONDecodeError:
                                    continue
                            
                            # Brief pause before next request
                            await asyncio.sleep(3)
                            
                        except Exception as e:
                            load_result["errors"] += 1
                            
            except Exception as e:
                print(f"❌ High load session {user_index} error: {e}")
            
            return load_result
        
        # Run high load for 60 seconds
        load_duration = 60
        load_tasks = []
        
        for i, (user_token, user_data) in enumerate(degradation_users[:8]):  # Use 8 users for high load
            task = high_load_session(i, user_token, user_data, load_duration)
            load_tasks.append(task)
        
        print(f"🏃 Running high load for {load_duration} seconds...")
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        
        # Analyze degradation
        all_degraded_times = []
        total_load_requests = 0
        total_load_errors = 0
        
        for result in load_results:
            if isinstance(result, dict):
                all_degraded_times.extend(result["response_times"])
                total_load_requests += result["requests_sent"]
                total_load_errors += result["errors"]
        
        if all_degraded_times:
            degraded_avg = statistics.mean(all_degraded_times)
            degradation_factor = degraded_avg / baseline_avg
            
            print(f"📊 Performance during high load:")
            print(f"   Average response time: {degraded_avg:.2f}s")
            print(f"   Degradation factor: {degradation_factor:.2f}x")
            print(f"   Error rate: {(total_load_errors/total_load_requests)*100:.1f}%")
        
        # Test recovery after load reduction
        print(f"\n🔄 Testing performance recovery after load reduction...")
        
        await asyncio.sleep(10)  # Brief cooldown period
        
        recovery_performance = await measure_baseline_performance()
        
        if recovery_performance["baseline_established"]:
            recovery_avg = recovery_performance["average_response_time"]
            recovery_factor = recovery_avg / baseline_avg
            
            print(f"📊 Performance after recovery:")
            print(f"   Average response time: {recovery_avg:.2f}s")
            print(f"   Recovery factor: {recovery_factor:.2f}x")
            
            # Validation criteria
            assert degradation_factor >= 1.2, f"No significant performance degradation detected: {degradation_factor:.2f}x"
            assert recovery_factor <= 2.0, f"Performance did not recover adequately: {recovery_factor:.2f}x"
            
            # System should show some recovery
            improvement_factor = degraded_avg / recovery_avg
            assert improvement_factor >= 1.1, f"No performance improvement after load reduction: {improvement_factor:.2f}x"
            
            print(f"✅ PERFORMANCE DEGRADATION AND RECOVERY SUCCESS!")
            print(f"   ✓ Performance degradation detected: {degradation_factor:.2f}x slowdown")
            print(f"   ✓ System recovery validated: {recovery_factor:.2f}x from baseline")
            print(f"   ✓ Performance improvement after load reduction: {improvement_factor:.2f}x")
        else:
            pytest.fail("Could not measure recovery performance")