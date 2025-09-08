"""
Concurrent Users Scalability WebSocket Integration Tests

Business Value Justification (BVJ):
- Segment: Mid, Enterprise - Platform scalability requirements  
- Business Goal: Ensure platform can handle concurrent users without degradation
- Value Impact: Scalability enables user growth and premium tier value delivery
- Strategic/Revenue Impact: Poor scalability caps growth and limits enterprise sales potential

CRITICAL CONCURRENT USER SCENARIOS:
1. Multiple simultaneous WebSocket connections and agent executions
2. Load distribution and resource management under concurrent usage
3. Performance stability during high concurrency periods

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real WebSocket connections and real concurrent load
- Tests real scalability patterns with multiple simultaneous users
- Validates performance metrics under load
- Ensures system stability during concurrent operations
- Tests resource contention and isolation under load
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import patch

import pytest
import websockets

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.fixtures.websocket_test_helpers import WebSocketTestSession
from shared.isolated_environment import get_env


class ScalabilityTestLLM:
    """
    Mock LLM for scalability testing with controlled response timing.
    This is the ONLY acceptable mock per CLAUDE.md - external LLM APIs.
    """
    
    def __init__(self, response_delay: float = 0.1, user_identifier: str = "default"):
        self.response_delay = response_delay
        self.user_identifier = user_identifier
        self.call_count = 0
        self.concurrent_calls = 0
    
    async def complete_async(self, messages, **kwargs):
        """Mock LLM with controlled timing for scalability validation."""
        self.concurrent_calls += 1
        self.call_count += 1
        call_id = self.call_count
        
        try:
            # Simulate processing with configurable delay
            await asyncio.sleep(self.response_delay)
            
            return {
                "content": f"Scalability test response #{call_id} for {self.user_identifier}. Testing concurrent processing capability and system throughput under load.",
                "usage": {"total_tokens": 90 + (call_id * 5)},
                "call_metadata": {
                    "call_id": call_id,
                    "concurrent_calls": self.concurrent_calls,
                    "response_delay": self.response_delay
                }
            }
        finally:
            self.concurrent_calls -= 1


class TestConcurrentUsersScalability(BaseIntegrationTest):
    """
    Scalability tests for concurrent WebSocket user scenarios.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL concurrent load
    to validate production-quality scalability and performance patterns.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_scalability_test(self, real_services_fixture):
        """
        Set up concurrent users scalability test environment.
        
        BVJ: Scalability Foundation - Ensures reliable concurrent user testing
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_session_id = f"scalability_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services (CLAUDE.md requirement)
        assert real_services_fixture, "Real services required for scalability testing"
        assert "backend" in real_services_fixture, "Real backend required for concurrent load testing"
        assert "db" in real_services_fixture, "Real database required for scalability validation"
        
        # Define concurrent user test configuration
        self.concurrent_user_configs = {
            "light_load": {
                "user_count": 5,
                "concurrent_requests": 2,
                "request_delay": 0.1
            },
            "moderate_load": {
                "user_count": 10,
                "concurrent_requests": 3, 
                "request_delay": 0.2
            },
            "heavy_load": {
                "user_count": 15,
                "concurrent_requests": 4,
                "request_delay": 0.3
            }
        }
        
        # Initialize scalability metrics
        self.scalability_metrics = {
            "connections_created": 0,
            "connections_successful": 0,
            "connections_failed": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "connection_times": [],
            "response_times": [],
            "concurrent_peak": 0
        }
        
        # Shared auth config for scalability testing
        self.base_auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            timeout=30.0  # Longer timeout for scalability tests
        )
        
        self.active_connections: List[websockets.ServerConnection] = []
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Test environment readiness
        try:
            test_helper = E2EWebSocketAuthHelper(config=self.base_auth_config, environment="test")
            token = test_helper.create_test_jwt_token(user_id=f"scalability_test_{self.test_session_id}")
            assert token, "Failed to create test JWT for scalability testing"
        except Exception as e:
            pytest.fail(f"Scalability test setup failed: {e}")
    
    async def async_teardown(self):
        """Clean up all concurrent connections and scalability test resources."""
        cleanup_tasks = []
        for connection in self.active_connections:
            if not connection.closed:
                cleanup_tasks.append(connection.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.active_connections.clear()
        await super().async_teardown()
    
    async def create_concurrent_user_session(self, user_index: int) -> Dict[str, Any]:
        """
        Create concurrent user session with metrics tracking.
        
        Args:
            user_index: Index of concurrent user
            
        Returns:
            Dict with user session data and connection
        """
        user_id = f"concurrent_user_{user_index}_{self.test_session_id}"
        user_email = f"user{user_index}@scalability-test.com"
        
        # Create user-specific auth config
        user_auth_config = E2EAuthConfig(
            auth_service_url=self.base_auth_config.auth_service_url,
            backend_url=self.base_auth_config.backend_url,
            websocket_url=self.base_auth_config.websocket_url,
            test_user_email=user_email,
            timeout=self.base_auth_config.timeout
        )
        
        auth_helper = E2EWebSocketAuthHelper(config=user_auth_config, environment="test")
        
        self.scalability_metrics["connections_created"] += 1
        connection_start_time = time.time()
        
        try:
            token = auth_helper.create_test_jwt_token(user_id=user_id)
            headers = auth_helper.get_websocket_headers(token)
            
            # Add scalability test headers
            headers.update({
                "X-Scalability-Test": "true",
                "X-User-Index": str(user_index),
                "X-Test-Session": self.test_session_id
            })
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=15.0
                ),
                timeout=20.0
            )
            
            connection_time = time.time() - connection_start_time
            self.scalability_metrics["connection_times"].append(connection_time)
            self.scalability_metrics["connections_successful"] += 1
            
            self.active_connections.append(websocket)
            
            # Update concurrent peak
            current_concurrent = len(self.active_connections)
            if current_concurrent > self.scalability_metrics["concurrent_peak"]:
                self.scalability_metrics["concurrent_peak"] = current_concurrent
            
            user_session = {
                "user_id": user_id,
                "user_index": user_index,
                "websocket": websocket,
                "auth_helper": auth_helper,
                "connection_time": connection_time,
                "messages_sent": 0,
                "messages_received": 0,
                "created_at": time.time()
            }
            
            self.user_sessions[user_id] = user_session
            return user_session
            
        except Exception as e:
            self.scalability_metrics["connections_failed"] += 1
            raise e
    
    async def send_concurrent_agent_requests(
        self,
        user_sessions: List[Dict[str, Any]],
        requests_per_user: int = 1,
        request_delay: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Send concurrent agent requests from multiple user sessions.
        
        Args:
            user_sessions: List of user sessions
            requests_per_user: Number of requests per user
            request_delay: Delay between requests
            
        Returns:
            List of sent request data
        """
        sent_requests = []
        
        for user_session in user_sessions:
            for request_index in range(requests_per_user):
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": user_session["user_id"],
                    "thread_id": f"scalability_thread_{user_session['user_index']}_{request_index}_{self.test_session_id}",
                    "agent_type": "scalability_test_agent",
                    "task": f"Concurrent scalability test from user {user_session['user_index']} request #{request_index}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "scalability_metadata": {
                        "user_index": user_session["user_index"],
                        "request_index": request_index,
                        "test_session": self.test_session_id
                    }
                }
                
                try:
                    await user_session["websocket"].send(json.dumps(agent_request))
                    user_session["messages_sent"] += 1
                    self.scalability_metrics["total_messages_sent"] += 1
                    sent_requests.append(agent_request)
                    
                    # Brief delay between requests to avoid overwhelming
                    if request_delay > 0:
                        await asyncio.sleep(request_delay)
                        
                except Exception as e:
                    # Log error but continue with other requests
                    pass
        
        return sent_requests
    
    async def collect_concurrent_responses(
        self,
        user_sessions: List[Dict[str, Any]],
        expected_responses_per_user: int,
        timeout: float = 30.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect responses from all concurrent user sessions.
        
        Args:
            user_sessions: List of user sessions
            expected_responses_per_user: Expected responses per user
            timeout: Collection timeout
            
        Returns:
            Dict mapping user IDs to their received messages
        """
        user_responses = {}
        collection_tasks = []
        
        for user_session in user_sessions:
            user_id = user_session["user_id"]
            user_responses[user_id] = []
            
            async def collect_user_responses(session):
                messages = []
                start_time = time.time()
                
                try:
                    while (len(messages) < expected_responses_per_user * 2 and 
                           (time.time() - start_time) < timeout):
                        try:
                            response_start = time.time()
                            message_data = await asyncio.wait_for(
                                session["websocket"].recv(), timeout=3.0
                            )
                            response_time = time.time() - response_start
                            self.scalability_metrics["response_times"].append(response_time)
                            
                            message = json.loads(message_data)
                            message["_response_time"] = response_time
                            message["_received_at"] = time.time()
                            message["_user_session"] = session["user_id"]
                            
                            messages.append(message)
                            session["messages_received"] += 1
                            self.scalability_metrics["total_messages_received"] += 1
                            
                        except asyncio.TimeoutError:
                            # Check if we've exceeded total timeout
                            if (time.time() - start_time) >= timeout:
                                break
                            continue
                            
                except Exception as e:
                    # Log error but return collected messages
                    pass
                
                return session["user_id"], messages
            
            collection_tasks.append(collect_user_responses(user_session))
        
        # Collect responses from all users concurrently
        results = await asyncio.gather(*collection_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, tuple):
                user_id, messages = result
                user_responses[user_id] = messages
            else:
                # Handle exceptions
                pass
        
        return user_responses
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_light_concurrent_load_handling(self, real_services_fixture):
        """
        Test light concurrent load handling with multiple simultaneous users.
        
        BVJ: Growth foundation - Platform must handle basic concurrent usage.
        Light load handling enables initial user base growth and Free tier operation.
        """
        load_config = self.concurrent_user_configs["light_load"]
        
        try:
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = ScalabilityTestLLM(0.1, "light_load").complete_async
                
                # Create concurrent user sessions
                session_creation_start = time.time()
                session_tasks = []
                
                for user_index in range(load_config["user_count"]):
                    task = asyncio.create_task(
                        self.create_concurrent_user_session(user_index)
                    )
                    session_tasks.append(task)
                
                user_sessions = await asyncio.gather(*session_tasks, return_exceptions=True)
                session_creation_time = time.time() - session_creation_start
                
                # Filter out failed sessions
                successful_sessions = [s for s in user_sessions if isinstance(s, dict)]
                failed_sessions = [s for s in user_sessions if isinstance(s, Exception)]
                
                # Verify session creation success rate
                success_rate = len(successful_sessions) / load_config["user_count"]
                assert success_rate >= 0.8, f"Session creation success rate too low: {success_rate:.2f}"
                
                # Send concurrent requests
                request_start_time = time.time()
                sent_requests = await self.send_concurrent_agent_requests(
                    successful_sessions,
                    requests_per_user=load_config["concurrent_requests"],
                    request_delay=load_config["request_delay"]
                )
                request_send_time = time.time() - request_start_time
                
                # Collect responses
                response_collection_start = time.time()
                user_responses = await self.collect_concurrent_responses(
                    successful_sessions,
                    expected_responses_per_user=load_config["concurrent_requests"],
                    timeout=25.0
                )
                response_collection_time = time.time() - response_collection_start
                
                # Verify light load performance
                total_expected_responses = len(successful_sessions) * load_config["concurrent_requests"] * 2
                total_actual_responses = sum(len(messages) for messages in user_responses.values())
                
                response_rate = total_actual_responses / max(total_expected_responses, 1)
                assert response_rate >= 0.5, f"Response rate too low under light load: {response_rate:.2f}"
                
                # Performance validation for light load
                avg_connection_time = sum(self.scalability_metrics["connection_times"]) / max(len(self.scalability_metrics["connection_times"]), 1)
                assert avg_connection_time < 5.0, f"Connection time too slow for light load: {avg_connection_time:.2f}s"
                
                if self.scalability_metrics["response_times"]:
                    avg_response_time = sum(self.scalability_metrics["response_times"]) / len(self.scalability_metrics["response_times"])
                    assert avg_response_time < 10.0, f"Response time too slow for light load: {avg_response_time:.2f}s"
                
                # Verify user isolation under light load
                for user_id, messages in user_responses.items():
                    for message in messages:
                        message_user_id = message.get("user_id")
                        if message_user_id:
                            assert message_user_id == user_id, f"User isolation violation under light load: {message_user_id} != {user_id}"
                
                # Log performance metrics for light load
                print(f"Light Load Performance - Sessions: {len(successful_sessions)}, "
                      f"Responses: {total_actual_responses}, "
                      f"Avg Connection Time: {avg_connection_time:.2f}s")
                
        except Exception as e:
            pytest.fail(f"Light concurrent load handling test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_moderate_concurrent_load_stability(self, real_services_fixture):
        """
        Test moderate concurrent load stability and resource management.
        
        BVJ: Scale preparation - Platform must handle moderate concurrent usage.
        Moderate load stability enables Early and Mid tier user growth.
        """
        load_config = self.concurrent_user_configs["moderate_load"]
        
        try:
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = ScalabilityTestLLM(0.15, "moderate_load").complete_async
                
                # Create concurrent user sessions with staggered timing
                session_tasks = []
                for user_index in range(load_config["user_count"]):
                    task = asyncio.create_task(
                        self.create_concurrent_user_session(user_index)
                    )
                    session_tasks.append(task)
                    
                    # Brief stagger to simulate realistic user onboarding
                    await asyncio.sleep(0.05)
                
                user_sessions = await asyncio.gather(*session_tasks, return_exceptions=True)
                successful_sessions = [s for s in user_sessions if isinstance(s, dict)]
                
                # Verify moderate load session creation
                success_rate = len(successful_sessions) / load_config["user_count"]
                assert success_rate >= 0.7, f"Moderate load session success rate too low: {success_rate:.2f}"
                
                # Test system stability under moderate load
                stability_test_duration = 10.0  # seconds
                stability_start_time = time.time()
                
                # Send multiple waves of requests during stability test
                wave_count = 3
                for wave in range(wave_count):
                    wave_requests = await self.send_concurrent_agent_requests(
                        successful_sessions,
                        requests_per_user=1,
                        request_delay=0.1
                    )
                    
                    # Brief pause between waves
                    await asyncio.sleep(2.0)
                
                # Collect all responses
                user_responses = await self.collect_concurrent_responses(
                    successful_sessions,
                    expected_responses_per_user=wave_count,
                    timeout=30.0
                )
                
                stability_duration = time.time() - stability_start_time
                
                # Verify system remained stable under moderate load
                total_responses = sum(len(messages) for messages in user_responses.values())
                assert total_responses > 0, "No responses received under moderate load - system may be unstable"
                
                # Check for performance degradation
                if len(self.scalability_metrics["response_times"]) > 5:
                    # Compare first and last response times to detect degradation
                    early_responses = self.scalability_metrics["response_times"][:5]
                    late_responses = self.scalability_metrics["response_times"][-5:]
                    
                    avg_early = sum(early_responses) / len(early_responses)
                    avg_late = sum(late_responses) / len(late_responses)
                    
                    # Allow some degradation but not excessive
                    degradation_ratio = avg_late / avg_early if avg_early > 0 else 1
                    assert degradation_ratio < 3.0, f"Excessive performance degradation under moderate load: {degradation_ratio:.2f}x"
                
                # Verify resource management
                peak_concurrent = self.scalability_metrics["concurrent_peak"]
                assert peak_concurrent >= load_config["user_count"] * 0.8, f"Concurrent connection management issue: {peak_concurrent}"
                
                # Test connection stability
                active_connections = [s for s in successful_sessions if not s["websocket"].closed]
                connection_stability_rate = len(active_connections) / len(successful_sessions)
                assert connection_stability_rate >= 0.8, f"Connection stability too low under moderate load: {connection_stability_rate:.2f}"
                
                print(f"Moderate Load Stability - Peak Concurrent: {peak_concurrent}, "
                      f"Stability Rate: {connection_stability_rate:.2f}, "
                      f"Total Responses: {total_responses}")
                
        except Exception as e:
            pytest.fail(f"Moderate concurrent load stability test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_performance_metrics(self, real_services_fixture):
        """
        Test comprehensive performance metrics under concurrent user load.
        
        BVJ: Enterprise readiness - Platform must demonstrate scalability metrics.
        Performance metrics validation enables Enterprise tier sales and growth planning.
        """
        # Use moderate load config for performance measurement
        load_config = self.concurrent_user_configs["moderate_load"]
        
        try:
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = ScalabilityTestLLM(0.12, "performance_metrics").complete_async
                
                # Performance monitoring setup
                performance_start_time = time.time()
                
                # Create user sessions with detailed timing
                session_creation_tasks = []
                for user_index in range(load_config["user_count"]):
                    task = asyncio.create_task(
                        self.create_concurrent_user_session(user_index)
                    )
                    session_creation_tasks.append(task)
                
                user_sessions = await asyncio.gather(*session_creation_tasks, return_exceptions=True)
                successful_sessions = [s for s in user_sessions if isinstance(s, dict)]
                
                session_creation_duration = time.time() - performance_start_time
                
                # Concurrent request execution with timing
                request_start_time = time.time()
                sent_requests = await self.send_concurrent_agent_requests(
                    successful_sessions,
                    requests_per_user=load_config["concurrent_requests"],
                    request_delay=load_config["request_delay"]
                )
                request_execution_duration = time.time() - request_start_time
                
                # Response collection with timing
                collection_start_time = time.time()
                user_responses = await self.collect_concurrent_responses(
                    successful_sessions,
                    expected_responses_per_user=load_config["concurrent_requests"],
                    timeout=25.0
                )
                collection_duration = time.time() - collection_start_time
                
                total_test_duration = time.time() - performance_start_time
                
                # Calculate comprehensive performance metrics
                total_messages_expected = len(successful_sessions) * load_config["concurrent_requests"] * 2
                total_messages_received = sum(len(messages) for messages in user_responses.values())
                
                # Connection metrics
                connection_success_rate = len(successful_sessions) / load_config["user_count"]
                avg_connection_time = (sum(self.scalability_metrics["connection_times"]) / 
                                    max(len(self.scalability_metrics["connection_times"]), 1))
                max_connection_time = max(self.scalability_metrics["connection_times"]) if self.scalability_metrics["connection_times"] else 0
                
                # Response metrics
                message_delivery_rate = total_messages_received / max(total_messages_expected, 1)
                avg_response_time = (sum(self.scalability_metrics["response_times"]) / 
                                   max(len(self.scalability_metrics["response_times"]), 1))
                max_response_time = max(self.scalability_metrics["response_times"]) if self.scalability_metrics["response_times"] else 0
                
                # Throughput metrics
                messages_per_second = total_messages_received / max(total_test_duration, 1)
                concurrent_efficiency = self.scalability_metrics["concurrent_peak"] / load_config["user_count"]
                
                # Performance validation thresholds
                performance_checks = {
                    "connection_success_rate": (connection_success_rate, 0.8, "Connection success rate"),
                    "avg_connection_time": (avg_connection_time, 8.0, "Average connection time", "less_than"),
                    "message_delivery_rate": (message_delivery_rate, 0.6, "Message delivery rate"),
                    "avg_response_time": (avg_response_time, 15.0, "Average response time", "less_than"),
                    "messages_per_second": (messages_per_second, 0.5, "Messages per second"),
                    "concurrent_efficiency": (concurrent_efficiency, 0.7, "Concurrent efficiency")
                }
                
                performance_failures = []
                for metric_name, check_data in performance_checks.items():
                    if len(check_data) == 4:
                        value, threshold, description, comparison = check_data
                        if comparison == "less_than":
                            if value >= threshold:
                                performance_failures.append(f"{description}: {value:.2f} >= {threshold}")
                        else:  # greater_than_or_equal
                            if value < threshold:
                                performance_failures.append(f"{description}: {value:.2f} < {threshold}")
                    else:
                        value, threshold, description = check_data
                        if value < threshold:
                            performance_failures.append(f"{description}: {value:.2f} < {threshold}")
                
                # Report performance metrics
                print(f"\n=== Concurrent User Performance Metrics ===")
                print(f"Users: {len(successful_sessions)}/{load_config['user_count']}")
                print(f"Connection Success Rate: {connection_success_rate:.2f}")
                print(f"Avg Connection Time: {avg_connection_time:.2f}s")
                print(f"Message Delivery Rate: {message_delivery_rate:.2f}")
                print(f"Avg Response Time: {avg_response_time:.2f}s")
                print(f"Messages/Second: {messages_per_second:.2f}")
                print(f"Concurrent Efficiency: {concurrent_efficiency:.2f}")
                print(f"Peak Concurrent Connections: {self.scalability_metrics['concurrent_peak']}")
                print("==========================================\n")
                
                # Fail if critical performance thresholds not met
                assert len(performance_failures) == 0, f"Performance validation failures: {performance_failures}"
                
                # Verify no significant performance outliers
                if len(self.scalability_metrics["response_times"]) > 2:
                    response_times = sorted(self.scalability_metrics["response_times"])
                    p95_response_time = response_times[int(len(response_times) * 0.95)]
                    assert p95_response_time < 30.0, f"95th percentile response time too high: {p95_response_time:.2f}s"
                
                # Verify system stability throughout test
                connection_failures = self.scalability_metrics["connections_failed"]
                connection_failure_rate = connection_failures / max(self.scalability_metrics["connections_created"], 1)
                assert connection_failure_rate < 0.3, f"Connection failure rate too high: {connection_failure_rate:.2f}"
                
        except Exception as e:
            pytest.fail(f"Concurrent user performance metrics test failed: {e}")