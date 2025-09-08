"""
E2E tests for WebSocket Performance and Reliability - Testing system reliability under realistic conditions.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System reliability and user experience quality
- Value Impact: Ensures WebSocket system performs reliably under real-world conditions
- Strategic Impact: Critical for user retention - validates system can handle production workloads

These E2E tests validate WebSocket performance characteristics, reliability under load,
error recovery, and end-to-end system resilience with full authentication.

CRITICAL: All E2E tests MUST use authentication as per CLAUDE.md requirements.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from test_framework.ssot.base import SSotBaseTestCase  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import WebSocketTestUtility
from shared.isolated_environment import get_env


class TestWebSocketPerformanceReliabilityE2E(SSotBaseTestCase):
    """E2E tests for WebSocket performance and reliability."""
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated E2E auth helper."""
        env = get_env()
        config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            jwt_secret=env.get("JWT_SECRET", "test-jwt-secret-key-unified-testing-32chars")
        )
        return E2EAuthHelper(config)
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_connection_reliability_e2e(self, auth_helper, websocket_utility):
        """Test WebSocket connection reliability and recovery with authentication.
        
        Validates that WebSocket connections are stable and recover gracefully from interruptions.
        """
        # STEP 1: Authenticate user (MANDATORY for E2E)
        auth_result = await auth_helper.authenticate_test_user(
            email="reliability_test@example.com",
            subscription_tier="enterprise"
        )
        
        assert auth_result.success is True, f"Authentication failed: {auth_result.error}"
        
        # STEP 2: Test connection stability over time
        connection_start_time = time.time()
        total_test_duration = 60  # 1 minute stability test
        message_interval = 3  # Send message every 3 seconds
        
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=auth_result.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket:
            
            # STEP 3: Send periodic messages to test connection stability
            messages_sent = []
            responses_received = []
            connection_interruptions = 0
            
            while (time.time() - connection_start_time) < total_test_duration:
                try:
                    # Send heartbeat/status message
                    message_id = len(messages_sent) + 1
                    heartbeat_message = {
                        "type": "connection_heartbeat",
                        "message_id": message_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": auth_result.user_id,
                        "connection_test": True
                    }
                    
                    send_time = time.time()
                    await websocket.send_json(heartbeat_message)
                    messages_sent.append({
                        "id": message_id,
                        "sent_at": send_time,
                        "message": heartbeat_message
                    })
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                        receive_time = time.time()
                        
                        responses_received.append({
                            "message_id": message_id,
                            "received_at": receive_time,
                            "response": response,
                            "latency_ms": (receive_time - send_time) * 1000
                        })
                        
                    except asyncio.TimeoutError:
                        print(f"No response for message {message_id} within 5 seconds")
                        connection_interruptions += 1
                    
                    # Wait before next message
                    await asyncio.sleep(message_interval)
                    
                except Exception as e:
                    print(f"Connection error: {e}")
                    connection_interruptions += 1
                    
                    # Try to recover connection
                    await asyncio.sleep(1)
                    continue
            
            # STEP 4: Validate connection reliability metrics
            total_messages = len(messages_sent)
            total_responses = len(responses_received)
            
            # Should send reasonable number of messages
            expected_messages = total_test_duration // message_interval
            assert total_messages >= expected_messages * 0.8, f"Should send at least 80% of expected messages, sent {total_messages}/{expected_messages}"
            
            # Should receive most responses
            response_rate = total_responses / total_messages if total_messages > 0 else 0
            assert response_rate >= 0.85, f"Should receive at least 85% of responses, got {response_rate:.2%}"
            
            # Connection should be stable (minimal interruptions)
            interruption_rate = connection_interruptions / total_messages if total_messages > 0 else 0
            assert interruption_rate <= 0.1, f"Connection interruption rate should be < 10%, got {interruption_rate:.2%}"
            
            # STEP 5: Validate response latency
            if responses_received:
                latencies = [resp["latency_ms"] for resp in responses_received]
                avg_latency = sum(latencies) / len(latencies)
                max_latency = max(latencies)
                
                # Average latency should be reasonable
                assert avg_latency <= 2000, f"Average latency {avg_latency:.1f}ms too high (should be < 2000ms)"
                
                # Maximum latency should not be excessive
                assert max_latency <= 10000, f"Maximum latency {max_latency:.1f}ms too high (should be < 10s)"
                
                # Most responses should be fast
                fast_responses = sum(1 for lat in latencies if lat <= 1000)
                fast_response_rate = fast_responses / len(latencies)
                assert fast_response_rate >= 0.8, f"At least 80% of responses should be under 1s, got {fast_response_rate:.2%}"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_concurrent_user_performance_e2e(self, auth_helper, websocket_utility):
        """Test WebSocket performance with multiple concurrent users with authentication.
        
        Validates that system performance remains acceptable with multiple simultaneous users.
        """
        # STEP 1: Authenticate multiple users (MANDATORY for E2E)
        concurrent_users = 5  # 5 concurrent users for E2E test
        authenticated_users = []
        
        for i in range(concurrent_users):
            auth_result = await auth_helper.authenticate_test_user(
                email=f"concurrent_user_{i}@example.com",
                subscription_tier="enterprise" if i < 2 else "early"  # Mix of tiers
            )
            assert auth_result.success is True, f"Authentication failed for user {i}"
            authenticated_users.append(auth_result)
        
        # STEP 2: Create concurrent WebSocket connections
        user_tasks = []
        performance_results = []
        
        async def user_workflow(user_auth, user_index):
            """Simulate realistic user workflow."""
            user_results = {
                "user_index": user_index,
                "messages_sent": 0,
                "responses_received": 0,
                "total_latency_ms": 0,
                "errors": 0,
                "start_time": time.time()
            }
            
            try:
                async with websocket_utility.create_authenticated_websocket_client(
                    access_token=user_auth.access_token,
                    websocket_url=auth_helper.config.websocket_url
                ) as websocket:
                    
                    # User workflow: Send several messages simulating normal usage
                    user_messages = [
                        {"type": "user_message", "content": f"Hello from user {user_index}"},
                        {"type": "start_agent", "agent": "cost_optimizer", "message": f"Analyze costs for user {user_index}"},
                        {"type": "user_message", "content": f"Follow-up question from user {user_index}"},
                        {"type": "system_status", "request": "health_check"}
                    ]
                    
                    for msg_data in user_messages:
                        try:
                            # Add user context to message
                            message = {
                                **msg_data,
                                "user_id": user_auth.user_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                            
                            send_time = time.time()
                            await websocket.send_json(message)
                            user_results["messages_sent"] += 1
                            
                            # Wait for response with timeout
                            try:
                                response = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
                                receive_time = time.time()
                                
                                user_results["responses_received"] += 1
                                user_results["total_latency_ms"] += (receive_time - send_time) * 1000
                                
                            except asyncio.TimeoutError:
                                user_results["errors"] += 1
                                print(f"User {user_index}: No response for message within 10s")
                            
                            # Wait between messages (realistic user behavior)
                            await asyncio.sleep(2)
                            
                        except Exception as e:
                            user_results["errors"] += 1
                            print(f"User {user_index}: Message error: {e}")
                    
                    user_results["end_time"] = time.time()
                    user_results["total_duration"] = user_results["end_time"] - user_results["start_time"]
                    
                    if user_results["responses_received"] > 0:
                        user_results["average_latency_ms"] = user_results["total_latency_ms"] / user_results["responses_received"]
                    else:
                        user_results["average_latency_ms"] = 0
                    
            except Exception as e:
                user_results["connection_error"] = str(e)
                user_results["errors"] += 1
            
            return user_results
        
        # STEP 3: Execute concurrent user workflows
        start_concurrent_test = time.time()
        
        for i, user_auth in enumerate(authenticated_users):
            task = asyncio.create_task(user_workflow(user_auth, i))
            user_tasks.append(task)
        
        # Wait for all users to complete
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        concurrent_test_duration = time.time() - start_concurrent_test
        
        # STEP 4: Analyze concurrent performance results
        successful_users = []
        failed_users = []
        
        for result in user_results:
            if isinstance(result, Exception):
                failed_users.append(result)
            else:
                successful_users.append(result)
        
        # Most users should complete successfully
        success_rate = len(successful_users) / len(authenticated_users)
        assert success_rate >= 0.8, f"At least 80% of users should complete successfully, got {success_rate:.2%}"
        
        # Analyze performance metrics
        if successful_users:
            total_messages = sum(user["messages_sent"] for user in successful_users)
            total_responses = sum(user["responses_received"] for user in successful_users)
            total_errors = sum(user["errors"] for user in successful_users)
            
            # Overall response rate should be good
            overall_response_rate = total_responses / total_messages if total_messages > 0 else 0
            assert overall_response_rate >= 0.7, f"Overall response rate should be >= 70%, got {overall_response_rate:.2%}"
            
            # Error rate should be low
            error_rate = total_errors / total_messages if total_messages > 0 else 0
            assert error_rate <= 0.2, f"Error rate should be <= 20%, got {error_rate:.2%}"
            
            # Average latency across all users should be reasonable
            user_latencies = [user["average_latency_ms"] for user in successful_users if user["average_latency_ms"] > 0]
            if user_latencies:
                overall_avg_latency = sum(user_latencies) / len(user_latencies)
                assert overall_avg_latency <= 5000, f"Overall average latency {overall_avg_latency:.1f}ms too high (should be < 5s)"
            
            # Test duration should be reasonable (not excessively slow due to concurrency)
            expected_duration = 12  # Rough estimate for 4 messages with 2s gaps + processing time
            assert concurrent_test_duration <= expected_duration * 2, f"Concurrent test took {concurrent_test_duration:.1f}s (should be < {expected_duration*2}s)"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_error_recovery_resilience_e2e(self, auth_helper, websocket_utility):
        """Test WebSocket error recovery and system resilience with authentication.
        
        Validates that the system handles errors gracefully and recovers properly.
        """
        # Authenticate user (MANDATORY for E2E)
        auth_result = await auth_helper.authenticate_test_user(
            email="error_recovery@example.com",
            subscription_tier="enterprise"
        )
        
        assert auth_result.success is True
        
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=auth_result.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket:
            
            # STEP 1: Test invalid message handling
            invalid_messages = [
                {"type": "invalid_message_type", "user_id": auth_result.user_id},
                {"type": "start_agent", "agent": "nonexistent_agent", "user_id": auth_result.user_id},
                {"invalid_json": "this should be handled gracefully"},
                {"type": "user_message", "content": "x" * 50000, "user_id": auth_result.user_id}  # Very large message
            ]
            
            error_responses = []
            recovery_successful = True
            
            for i, invalid_msg in enumerate(invalid_messages):
                try:
                    await websocket.send_json(invalid_msg)
                    
                    # Wait for error response
                    try:
                        error_response = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                        error_responses.append(error_response)
                        
                        # Error should be graceful (not disconnect)
                        if error_response.get("type") == "error":
                            error_message = error_response.get("message", "")
                            # Should be user-friendly error message
                            technical_terms = ["exception", "traceback", "null", "undefined"]
                            is_user_friendly = not any(term in error_message.lower() for term in technical_terms)
                            assert is_user_friendly, f"Error message should be user-friendly: {error_message}"
                    
                    except asyncio.TimeoutError:
                        # No response is also acceptable for some invalid messages
                        pass
                    
                    # Test that connection still works after error
                    recovery_test = {
                        "type": "user_message", 
                        "content": f"Recovery test after error {i}",
                        "user_id": auth_result.user_id
                    }
                    
                    await websocket.send_json(recovery_test)
                    
                    try:
                        recovery_response = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                        # Should process valid message after handling error
                        assert recovery_response is not None, f"Should recover after error {i}"
                    except asyncio.TimeoutError:
                        recovery_successful = False
                        print(f"Failed to recover after error {i}")
                    
                    await asyncio.sleep(0.5)  # Brief pause between tests
                    
                except Exception as e:
                    print(f"Exception handling invalid message {i}: {e}")
                    recovery_successful = False
            
            # STEP 2: Validate error handling quality
            assert recovery_successful, "Connection should remain functional after handling invalid messages"
            
            # Should have received some error responses
            if error_responses:
                # Error responses should indicate the type of error
                for error_resp in error_responses:
                    if error_resp.get("type") == "error":
                        assert "message" in error_resp or "error" in error_resp, "Error responses should include error message"
            
            # STEP 3: Test rapid message burst handling
            burst_messages = []
            burst_size = 20
            
            burst_start_time = time.time()
            
            for i in range(burst_size):
                burst_message = {
                    "type": "user_message",
                    "content": f"Burst message {i}",
                    "user_id": auth_result.user_id,
                    "burst_test": True
                }
                burst_messages.append(burst_message)
            
            # Send messages rapidly
            send_tasks = []
            for msg in burst_messages:
                task = asyncio.create_task(websocket.send_json(msg))
                send_tasks.append(task)
            
            await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # Collect responses
            burst_responses = []
            burst_collection_time = 15
            collection_start = time.time()
            
            while (time.time() - collection_start) < burst_collection_time:
                try:
                    response = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                    burst_responses.append(response)
                    
                    # Stop if we got most responses
                    if len(burst_responses) >= burst_size * 0.7:  # 70% of burst messages
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            # STEP 4: Validate burst handling
            burst_response_rate = len(burst_responses) / burst_size
            
            # Should handle most burst messages (may apply rate limiting)
            assert burst_response_rate >= 0.5, f"Should handle at least 50% of burst messages, got {burst_response_rate:.2%}"
            
            # System should not crash from burst
            # Test with normal message after burst
            post_burst_message = {
                "type": "user_message",
                "content": "Normal message after burst test",
                "user_id": auth_result.user_id
            }
            
            await websocket.send_json(post_burst_message)
            
            try:
                post_burst_response = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
                assert post_burst_response is not None, "System should handle normal messages after burst"
            except asyncio.TimeoutError:
                assert False, "System should respond to normal messages after burst test"