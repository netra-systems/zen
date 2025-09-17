"""Multi-User Concurrent Session E2E Test for Netra - Focused Implementation
CRITICAL: Enterprise Feature - Multi-User Concurrent Chat Sessions

Business Value Justification (BVJ):
- Segment: Enterprise (concurrent user support required)
- Business Goal: Validate concurrent user isolation and performance
- Value Impact: Prevents enterprise customer churn from concurrency issues  
- Revenue Impact: Protects $100K+ ARR from enterprise contracts

Test #4: Multi-User Concurrent Chat Sessions
- 10 simultaneous users
- Concurrent logins  
- Parallel message sending
- No cross-contamination
- All get correct responses
- <10 seconds total execution time

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Modular design with focused responsibilities
"""

import asyncio
import pytest
import time
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as WebSocketManager
from tests.e2e.concurrent_user_models import IsolationValidator
from tests.e2e.concurrent_user_simulators import (
    ConcurrentUserSimulator,
    ConcurrentWebSocketManager,

)


@pytest.mark.asyncio

@pytest.mark.integration
@pytest.mark.e2e
async def test_multi_user_concurrent_chat_sessions():

    """

    CRITICAL E2E Test #4: Multi-User Concurrent Chat Sessions
    

    Enterprise Feature Validation:

    - 10 simultaneous users

    - Concurrent logins

    - Parallel message sending  

    - No cross-contamination

    - All get correct responses

    - <10 seconds total execution time
    

    Business Value: $100K+ ARR protection from enterprise contracts

    """

    simulator = ConcurrentUserSimulator()
    

    start_time = time.time()
    

    try:
        # Step 1: Start mock services

        await simulator.service_manager.start_auth_service()

        await simulator.service_manager.start_backend_service()
        
        # Step 2: Create 10 concurrent users

        users = await simulator.create_concurrent_users(10)

        assert len(users) == 10, f"Expected 10 users, got {len(users)}"

        assert simulator.metrics.successful_logins == 10, f"Expected 10 logins, got {simulator.metrics.successful_logins}"
        
        # Step 3: Establish concurrent WebSocket connections

        ws_manager = ConcurrentWebSocketManager(simulator)

        connections = await ws_manager.establish_all_connections(users)

        assert connections == 10, f"Expected 10 connections, got {connections}"
        
        # Step 4: Send concurrent messages

        message_results = await ws_manager.send_concurrent_messages(users)

        assert message_results["successful_messages"] == 10, f"Expected 10 messages, got {message_results['successful_messages']}"
        
        # Step 5: Validate isolation

        validator = IsolationValidator(simulator.metrics)

        isolation_results = validator.validate_user_isolation(users)
        
        # Isolation assertions

        assert isolation_results["thread_id_conflicts"] == 0, "Thread ID conflicts detected"

        assert isolation_results["response_contamination"] == 0, "Response contamination detected"

        assert isolation_results["token_isolation"] == 0, "Token isolation violations detected"

        assert not simulator.metrics.cross_contamination_detected, "Cross-contamination detected"
        
        # Performance assertion

        total_time = time.time() - start_time

        assert total_time < 10.0, f"Test took {total_time:.2f}s, must be <10s"
        
        # Success metrics

        assert simulator.metrics.successful_messages == 10, "Not all messages succeeded"

        assert len(simulator.metrics.response_times) == 10, "Missing response times"
        
        # Log success

        avg_response = sum(simulator.metrics.response_times) / len(simulator.metrics.response_times)

        print(f"SUCCESS: Concurrent Users Test PASSED: {total_time:.2f}s")

        print(f"SUCCESS: Users: 10/10, Connections: {connections}/10, Messages: {simulator.metrics.successful_messages}/10")

        print(f"SUCCESS: Avg Response Time: {avg_response:.2f}s")

        print(f"SUCCESS: Enterprise Feature VALIDATED - $100K+ ARR PROTECTED")
        

    finally:
        # Cleanup

        await simulator.service_manager.stop_all_services()


@pytest.mark.asyncio

@pytest.mark.performance
@pytest.mark.e2e
async def test_concurrent_user_performance_targets():

    """

    Performance validation for concurrent users - enterprise SLA requirements.

    Business Value: Enterprise SLA compliance protects renewal rates.

    """

    simulator = ConcurrentUserSimulator()
    

    try:

        await simulator.service_manager.start_auth_service()

        await simulator.service_manager.start_backend_service()
        
        # Create users and establish connections

        users = await simulator.create_concurrent_users(10)

        ws_manager = ConcurrentWebSocketManager(simulator)

        await ws_manager.establish_all_connections(users)
        
        # Measure performance over multiple iterations

        performance_samples = []

        for i in range(3):

            start_time = time.time()

            await ws_manager.send_concurrent_messages(users)

            iteration_time = time.time() - start_time

            performance_samples.append(iteration_time)
            
            # Each iteration must meet performance target

            assert iteration_time < 5.0, f"Iteration {i+1} took {iteration_time:.2f}s > 5s limit"
        
        # Validate consistency

        avg_time = sum(performance_samples) / len(performance_samples)

        max_time = max(performance_samples)
        

        assert avg_time < 3.0, f"Average time {avg_time:.2f}s exceeds 3s target"

        assert max_time < 5.0, f"Max time {max_time:.2f}s exceeds 5s limit"
        

        print(f"SUCCESS: Performance Target MET - Avg: {avg_time:.2f}s, Max: {max_time:.2f}s")
        

    finally:

        await simulator.service_manager.stop_all_services()


@pytest.mark.asyncio

@pytest.mark.critical
@pytest.mark.e2e
async def test_concurrent_user_data_isolation():

    """

    Validate strict data isolation between concurrent users.

    Business Value: Data security compliance for enterprise customers.

    """

    simulator = ConcurrentUserSimulator()
    

    try:

        await simulator.service_manager.start_auth_service()

        await simulator.service_manager.start_backend_service()
        
        # Create users with distinctive content

        users = await simulator.create_concurrent_users(5)

        ws_manager = ConcurrentWebSocketManager(simulator)

        await ws_manager.establish_all_connections(users)
        
        # Send messages with unique identifiable content

        for user in users:

            secret_content = f"SECRET_DATA_FOR_{user.user_id}_ONLY"

            message = {

                "type": "chat_message",

                "content": f"Process my {secret_content} confidential information",

                "thread_id": user.thread_id,

                "user_id": user.user_id

            }

            await user.websocket_client.send(message)

            user.sent_messages.append(message)
        
        # Collect all responses

        for user in users:

            response = await user.websocket_client.receive(timeout=3.0)

            if response:

                user.received_responses.append(response)
        
        # Validate strict isolation

        validator = IsolationValidator(simulator.metrics)

        isolation_results = validator.validate_user_isolation(users)
        
        # Critical isolation assertions

        assert isolation_results["response_contamination"] == 0, "CRITICAL: User data leaked between sessions"

        assert isolation_results["content_isolation"] == 0, "CRITICAL: Content isolation violated"

        assert not simulator.metrics.cross_contamination_detected, "CRITICAL: Cross-contamination detected"
        

        print("SUCCESS: Data Isolation VALIDATED - Enterprise security requirements MET")
        

    finally:

        await simulator.service_manager.stop_all_services()
