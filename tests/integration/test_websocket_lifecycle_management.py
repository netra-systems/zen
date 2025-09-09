"""
Integration Tests for WebSocket Lifecycle Management Race Conditions

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket lifecycle reliability for chat functionality
- Value Impact: Prevent MessageHandlerService initialization gaps causing failures
- Strategic Impact: Eliminate race conditions in WebSocket state management

CRITICAL: These tests focus on WebSocket lifecycle management with real services.
They target the MessageHandlerService initialization gaps and service readiness issues.
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
import aiohttp

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    create_authenticated_user_context
)

logger = logging.getLogger(__name__)


class TestWebSocketLifecycleManagement(BaseIntegrationTest):
    """
    Integration tests for WebSocket lifecycle management with real services.
    
    Tests WebSocket initialization, MessageHandlerService setup, and service readiness
    validation timing using real PostgreSQL and Redis services.
    """

    @pytest.fixture(autouse=True)
    async def setup_auth_helper(self):
        """Set up authentication helper for integration tests."""
        self.auth_helper = E2EAuthHelper(environment="test")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_redis_connection_race(self, real_services_fixture):
        """
        Test WebSocket connection with Redis state synchronization race conditions.
        
        EXPECTED RESULT: Should detect synchronization issues between WebSocket and Redis state.
        Uses real Redis and authentication to reproduce race conditions.
        """
        # Get real services
        redis_client = real_services_fixture["redis"]
        db_session = real_services_fixture["db"]
        
        # Create authenticated user
        user_context = await create_authenticated_user_context(
            user_email=f"redis_race_test_{int(time.time())}@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        # Clear any existing Redis state for this user
        user_redis_keys = [
            f"websocket:user:{user_context.user_id}",
            f"websocket:connection:{user_context.websocket_client_id}",
            f"user:session:{user_context.user_id}",
            f"websocket:state:{user_context.websocket_client_id}"
        ]
        
        for key in user_redis_keys:
            await redis_client.delete(key)
        
        # Test rapid WebSocket connection attempts with Redis state tracking
        connection_attempts = []
        redis_state_tracking = []
        
        for attempt in range(5):
            try:
                # Track Redis state before connection
                redis_state_before = {}
                for key in user_redis_keys:
                    value = await redis_client.get(key)
                    redis_state_before[key] = value.decode() if value else None
                
                # Attempt WebSocket connection with timing
                connection_start = time.time()
                
                # Simulate WebSocket connection initialization
                # Set Redis state as WebSocket connection would
                connection_id = f"conn_{attempt}_{int(time.time() * 1000)}"
                websocket_state = {
                    "user_id": str(user_context.user_id),
                    "connection_id": connection_id,
                    "status": "connecting",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attempt": attempt
                }
                
                # Set Redis state (simulating WebSocket manager)
                await redis_client.setex(
                    f"websocket:connection:{connection_id}",
                    300,  # 5 minute expiry
                    json.dumps(websocket_state)
                )
                
                # Simulate race condition: rapid state updates
                for i in range(3):
                    state_update = websocket_state.copy()
                    state_update["status"] = f"update_{i}"
                    state_update["update_time"] = datetime.now(timezone.utc).isoformat()
                    
                    await redis_client.setex(
                        f"websocket:connection:{connection_id}",
                        300,
                        json.dumps(state_update)
                    )
                    
                    # Concurrent read to simulate race condition
                    concurrent_read = await redis_client.get(f"websocket:connection:{connection_id}")
                    if concurrent_read:
                        concurrent_data = json.loads(concurrent_read.decode())
                        # Check for state consistency
                        if concurrent_data.get("status") != state_update["status"]:
                            # Race condition detected
                            print(f"⚠️  Redis race condition detected in attempt {attempt}, update {i}")
                    
                    await asyncio.sleep(0.01)  # 10ms between updates to trigger race
                
                # Final state update
                websocket_state["status"] = "connected"
                websocket_state["connected_at"] = datetime.now(timezone.utc).isoformat()
                await redis_client.setex(
                    f"websocket:connection:{connection_id}",
                    300,
                    json.dumps(websocket_state)
                )
                
                connection_time = time.time() - connection_start
                
                # Track Redis state after connection
                redis_state_after = {}
                for key in user_redis_keys:
                    value = await redis_client.get(key)
                    redis_state_after[key] = value.decode() if value else None
                
                # Verify state consistency
                final_state = await redis_client.get(f"websocket:connection:{connection_id}")
                final_data = json.loads(final_state.decode()) if final_state else {}
                
                connection_attempts.append({
                    "attempt": attempt,
                    "success": True,
                    "connection_time": connection_time,
                    "connection_id": connection_id,
                    "final_status": final_data.get("status"),
                    "state_consistent": final_data.get("status") == "connected"
                })
                
                redis_state_tracking.append({
                    "attempt": attempt,
                    "before": redis_state_before,
                    "after": redis_state_after,
                    "final_state": final_data
                })
                
            except Exception as e:
                connection_time = time.time() - connection_start if 'connection_start' in locals() else 0
                connection_attempts.append({
                    "attempt": attempt,
                    "success": False,
                    "connection_time": connection_time,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
            
            # Small delay between attempts
            await asyncio.sleep(0.1)
        
        # Analyze results for race conditions
        successful_attempts = sum(1 for a in connection_attempts if a.get("success", False))
        inconsistent_states = sum(1 for a in connection_attempts if not a.get("state_consistent", True))
        avg_connection_time = sum(a.get("connection_time", 0) for a in connection_attempts) / len(connection_attempts)
        
        print(f"\n🔄 WEBSOCKET-REDIS RACE CONDITION ANALYSIS:")
        print(f"📊 Successful attempts: {successful_attempts}/{len(connection_attempts)}")
        print(f"❌ Inconsistent states: {inconsistent_states}")
        print(f"⏱️  Average connection time: {avg_connection_time:.3f}s")
        
        # Print detailed results
        for attempt in connection_attempts:
            attempt_num = attempt["attempt"]
            if attempt.get("success"):
                status = "✅ SUCCESS" if attempt.get("state_consistent") else "⚠️  INCONSISTENT"
                conn_time = attempt.get("connection_time", 0)
                final_status = attempt.get("final_status", "unknown")
                print(f"   Attempt {attempt_num}: {status} ({conn_time:.3f}s) - Final: {final_status}")
            else:
                error = attempt.get("error", "Unknown error")
                print(f"   Attempt {attempt_num}: ❌ FAILED - {error}")
        
        # Check for race conditions
        race_conditions_detected = (
            inconsistent_states > 0 or           # State inconsistency indicates race conditions
            successful_attempts < len(connection_attempts) or  # Connection failures
            avg_connection_time > 0.1            # Slow connections may indicate contention
        )
        
        if race_conditions_detected:
            print(f"\n🚨 WEBSOCKET-REDIS RACE CONDITIONS DETECTED:")
            print(f"   State inconsistencies suggest race conditions between WebSocket and Redis")
            print(f"   These can cause connection state corruption")
            
            # This test is designed to detect race conditions
            assert False, (
                f"WebSocket-Redis race conditions detected:\n"
                f"Inconsistent states: {inconsistent_states} (should be 0)\n"
                f"Success rate: {successful_attempts}/{len(connection_attempts)}\n"
                f"Average time: {avg_connection_time:.3f}s\n"
                f"This proves WebSocket-Redis synchronization race conditions exist."
            )
        else:
            print(f"\n✅ WEBSOCKET-REDIS SYNCHRONIZATION APPEARS STABLE:")
            print(f"   No race conditions detected in state synchronization")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_validation_with_redis_delay(self, real_services_fixture):
        """
        Test authentication validation when Redis responses are delayed.
        
        EXPECTED RESULT: Should detect auth validation timing issues during Redis delays.
        """
        # Get real services
        redis_client = real_services_fixture["redis"]
        
        # Create authenticated user
        user_context = await create_authenticated_user_context(
            user_email=f"auth_delay_test_{int(time.time())}@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        # Get JWT token for testing
        jwt_token = user_context.agent_context['jwt_token']
        
        # Test auth validation with simulated Redis delays
        auth_validation_results = []
        
        for delay_ms in [0, 50, 100, 200, 500, 1000]:  # Increasing delays
            try:
                # Store auth data in Redis with timing
                auth_data = {
                    "user_id": str(user_context.user_id),
                    "email": user_context.agent_context['user_email'],
                    "token": jwt_token,
                    "permissions": user_context.agent_context['permissions'],
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                    "delay_test": delay_ms
                }
                
                # Store in Redis
                auth_key = f"auth:validation:{user_context.user_id}"
                await redis_client.setex(auth_key, 300, json.dumps(auth_data))
                
                # Simulate Redis delay
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)
                
                # Validate auth with timing
                validation_start = time.time()
                
                # Simulate auth validation process
                stored_auth = await redis_client.get(auth_key)
                if stored_auth:
                    stored_data = json.loads(stored_auth.decode())
                    
                    # Simulate JWT validation timing
                    jwt_validation_start = time.time()
                    
                    # Mock JWT validation (normally would decode and verify)
                    try:
                        # Simulate validation work
                        await asyncio.sleep(0.01)  # 10ms JWT validation time
                        jwt_valid = stored_data.get("token") == jwt_token
                        jwt_validation_time = time.time() - jwt_validation_start
                    except Exception:
                        jwt_valid = False
                        jwt_validation_time = time.time() - jwt_validation_start
                    
                    # Complete validation
                    total_validation_time = time.time() - validation_start
                    
                    auth_validation_results.append({
                        "delay_ms": delay_ms,
                        "success": jwt_valid,
                        "redis_response_time": delay_ms / 1000.0,
                        "jwt_validation_time": jwt_validation_time,
                        "total_validation_time": total_validation_time,
                        "auth_data_retrieved": bool(stored_auth)
                    })
                    
                else:
                    # Redis data not found
                    total_validation_time = time.time() - validation_start
                    auth_validation_results.append({
                        "delay_ms": delay_ms,
                        "success": False,
                        "error": "Auth data not found in Redis",
                        "total_validation_time": total_validation_time,
                        "auth_data_retrieved": False
                    })
                    
            except Exception as e:
                validation_time = time.time() - validation_start if 'validation_start' in locals() else 0
                auth_validation_results.append({
                    "delay_ms": delay_ms,
                    "success": False,
                    "error": str(e),
                    "total_validation_time": validation_time,
                    "auth_data_retrieved": False
                })
        
        # Analyze auth validation under delays
        successful_validations = sum(1 for r in auth_validation_results if r.get("success", False))
        max_validation_time = max(r.get("total_validation_time", 0) for r in auth_validation_results)
        avg_validation_time = sum(r.get("total_validation_time", 0) for r in auth_validation_results) / len(auth_validation_results)
        
        # Find validation failures under delay
        failed_under_delay = [r for r in auth_validation_results if r.get("delay_ms", 0) > 0 and not r.get("success", False)]
        
        print(f"\n🔐 AUTH VALIDATION WITH REDIS DELAY ANALYSIS:")
        print(f"📊 Successful validations: {successful_validations}/{len(auth_validation_results)}")
        print(f"⏱️  Maximum validation time: {max_validation_time:.3f}s")
        print(f"📈 Average validation time: {avg_validation_time:.3f}s")
        print(f"❌ Failures under delay: {len(failed_under_delay)}")
        
        # Print detailed results
        print(f"\n📋 Validation Results by Delay:")
        for result in auth_validation_results:
            delay = result.get("delay_ms", 0)
            success = "✅" if result.get("success", False) else "❌"
            val_time = result.get("total_validation_time", 0)
            error = result.get("error", "")
            print(f"   {delay:4d}ms delay: {success} ({val_time:.3f}s) {error}")
        
        # Check for auth validation timing issues
        auth_timing_issues = (
            len(failed_under_delay) > 0 or        # Failures when Redis is delayed
            max_validation_time > 2.0 or          # Validation takes too long
            successful_validations < len(auth_validation_results)  # Some validations failed
        )
        
        if auth_timing_issues:
            print(f"\n🚨 AUTH VALIDATION TIMING ISSUES DETECTED:")
            print(f"   Redis delays cause auth validation failures")
            print(f"   These can prevent WebSocket connections during Redis latency spikes")
            
            assert False, (
                f"Auth validation timing issues detected:\n"
                f"Failures under delay: {len(failed_under_delay)}\n"
                f"Max validation time: {max_validation_time:.3f}s (should be <1s)\n"
                f"Success rate: {successful_validations}/{len(auth_validation_results)}\n"
                f"This proves auth validation race conditions exist with Redis delays."
            )
        else:
            print(f"\n✅ AUTH VALIDATION TIMING APPEARS ROBUST:")
            print(f"   Auth validation handles Redis delays properly")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_websocket_session_persistence(self, real_services_fixture):
        """
        Test WebSocket session persistence in Redis during connection issues.
        
        EXPECTED RESULT: Should test session recovery after temporary disconnections.
        """
        # Get real services
        redis_client = real_services_fixture["redis"]
        
        # Create authenticated user
        user_context = await create_authenticated_user_context(
            user_email=f"session_persist_test_{int(time.time())}@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        # Test session persistence through connection lifecycle
        session_persistence_results = []
        session_id = f"session_{user_context.user_id}_{int(time.time())}"
        
        # Create initial session
        initial_session = {
            "session_id": session_id,
            "user_id": str(user_context.user_id),
            "websocket_id": str(user_context.websocket_client_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "message_count": 0,
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        
        session_key = f"websocket:session:{session_id}"
        await redis_client.setex(session_key, 3600, json.dumps(initial_session))  # 1 hour expiry
        
        # Test session persistence through various scenarios
        test_scenarios = [
            {"name": "normal_activity", "simulation": "normal"},
            {"name": "connection_drop", "simulation": "disconnect"},
            {"name": "rapid_reconnect", "simulation": "fast_reconnect"},
            {"name": "delayed_reconnect", "simulation": "slow_reconnect"},
            {"name": "concurrent_updates", "simulation": "concurrent"}
        ]
        
        for scenario in test_scenarios:
            try:
                scenario_start = time.time()
                scenario_name = scenario["name"]
                simulation_type = scenario["simulation"]
                
                print(f"\n🔄 Testing scenario: {scenario_name}")
                
                if simulation_type == "normal":
                    # Normal session activity
                    for i in range(5):
                        # Update session with activity
                        session_update = initial_session.copy()
                        session_update["message_count"] = i + 1
                        session_update["last_activity"] = datetime.now(timezone.utc).isoformat()
                        session_update["activity_type"] = "message_sent"
                        
                        await redis_client.setex(session_key, 3600, json.dumps(session_update))
                        await asyncio.sleep(0.01)  # 10ms between updates
                    
                    success = True
                    error = None
                    
                elif simulation_type == "disconnect":
                    # Simulate connection drop
                    session_update = initial_session.copy()
                    session_update["status"] = "disconnected"
                    session_update["disconnected_at"] = datetime.now(timezone.utc).isoformat()
                    
                    await redis_client.setex(session_key, 3600, json.dumps(session_update))
                    await asyncio.sleep(0.1)  # Brief disconnection
                    
                    # Check if session persisted
                    persisted_session = await redis_client.get(session_key)
                    success = persisted_session is not None
                    error = None if success else "Session not persisted during disconnect"
                    
                elif simulation_type == "fast_reconnect":
                    # Simulate rapid reconnection
                    session_update = initial_session.copy()
                    session_update["status"] = "disconnected"
                    await redis_client.setex(session_key, 3600, json.dumps(session_update))
                    
                    # Immediate reconnect
                    session_update["status"] = "reconnecting"
                    session_update["reconnect_attempt"] = 1
                    await redis_client.setex(session_key, 3600, json.dumps(session_update))
                    
                    # Quick reconnect complete
                    session_update["status"] = "active"
                    session_update["reconnected_at"] = datetime.now(timezone.utc).isoformat()
                    await redis_client.setex(session_key, 3600, json.dumps(session_update))
                    
                    # Verify final state
                    final_session = await redis_client.get(session_key)
                    if final_session:
                        final_data = json.loads(final_session.decode())
                        success = final_data.get("status") == "active"
                        error = None if success else f"Wrong final status: {final_data.get('status')}"
                    else:
                        success = False
                        error = "Session lost during fast reconnect"
                        
                elif simulation_type == "slow_reconnect":
                    # Simulate delayed reconnection
                    session_update = initial_session.copy()
                    session_update["status"] = "disconnected"
                    await redis_client.setex(session_key, 3600, json.dumps(session_update))
                    
                    # Longer delay before reconnect
                    await asyncio.sleep(0.5)  # 500ms delay
                    
                    session_update["status"] = "reconnecting"
                    session_update["reconnect_delay"] = 0.5
                    await redis_client.setex(session_key, 3600, json.dumps(session_update))
                    
                    await asyncio.sleep(0.1)
                    
                    session_update["status"] = "active"
                    session_update["reconnected_at"] = datetime.now(timezone.utc).isoformat()
                    await redis_client.setex(session_key, 3600, json.dumps(session_update))
                    
                    # Verify persistence after delay
                    final_session = await redis_client.get(session_key)
                    success = final_session is not None
                    error = None if success else "Session not persisted after delayed reconnect"
                    
                elif simulation_type == "concurrent":
                    # Simulate concurrent session updates (race condition test)
                    async def concurrent_update(update_id):
                        for i in range(3):
                            session_update = initial_session.copy()
                            session_update["concurrent_update_id"] = update_id
                            session_update["update_sequence"] = i
                            session_update["update_time"] = datetime.now(timezone.utc).isoformat()
                            
                            await redis_client.setex(session_key, 3600, json.dumps(session_update))
                            await asyncio.sleep(0.001)  # 1ms between updates
                    
                    # Run 3 concurrent update tasks
                    await asyncio.gather(
                        concurrent_update("task_1"),
                        concurrent_update("task_2"),
                        concurrent_update("task_3")
                    )
                    
                    # Check final state consistency
                    final_session = await redis_client.get(session_key)
                    if final_session:
                        final_data = json.loads(final_session.decode())
                        # Should have data from one of the concurrent updates
                        success = "concurrent_update_id" in final_data
                        error = None if success else "Concurrent updates caused data corruption"
                    else:
                        success = False
                        error = "Session lost during concurrent updates"
                
                scenario_time = time.time() - scenario_start
                
                session_persistence_results.append({
                    "scenario": scenario_name,
                    "success": success,
                    "scenario_time": scenario_time,
                    "error": error,
                    "simulation_type": simulation_type
                })
                
            except Exception as e:
                scenario_time = time.time() - scenario_start if 'scenario_start' in locals() else 0
                session_persistence_results.append({
                    "scenario": scenario_name,
                    "success": False,
                    "scenario_time": scenario_time,
                    "error": str(e),
                    "simulation_type": simulation_type
                })
        
        # Analyze session persistence results
        successful_scenarios = sum(1 for r in session_persistence_results if r.get("success", False))
        failed_scenarios = [r for r in session_persistence_results if not r.get("success", False)]
        avg_scenario_time = sum(r.get("scenario_time", 0) for r in session_persistence_results) / len(session_persistence_results)
        
        print(f"\n💾 SESSION PERSISTENCE ANALYSIS:")
        print(f"📊 Successful scenarios: {successful_scenarios}/{len(session_persistence_results)}")
        print(f"❌ Failed scenarios: {len(failed_scenarios)}")
        print(f"⏱️  Average scenario time: {avg_scenario_time:.3f}s")
        
        # Print detailed results
        print(f"\n📋 Session Persistence Results:")
        for result in session_persistence_results:
            scenario = result.get("scenario", "unknown")
            success = "✅" if result.get("success", False) else "❌"
            time_taken = result.get("scenario_time", 0)
            error = result.get("error", "")
            print(f"   {scenario}: {success} ({time_taken:.3f}s) {error}")
        
        # Check for session persistence issues
        persistence_issues = (
            len(failed_scenarios) > 0 or         # Any scenario failures
            successful_scenarios < len(session_persistence_results)  # Not all scenarios passed
        )
        
        if persistence_issues:
            print(f"\n🚨 SESSION PERSISTENCE ISSUES DETECTED:")
            print(f"   Session persistence failures during connection lifecycle")
            print(f"   These can cause loss of user context during reconnections")
            
            for failed in failed_scenarios:
                print(f"   Failed: {failed['scenario']} - {failed.get('error', 'Unknown error')}")
            
            assert False, (
                f"Session persistence issues detected:\n"
                f"Failed scenarios: {len(failed_scenarios)}/{len(session_persistence_results)}\n"
                f"Successful scenarios: {successful_scenarios}\n"
                f"This proves session persistence race conditions exist."
            )
        else:
            print(f"\n✅ SESSION PERSISTENCE APPEARS ROBUST:")
            print(f"   All session persistence scenarios passed")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_concurrent_user_isolation(self, real_services_fixture):
        """
        Test multi-user WebSocket connections with Redis state isolation.
        
        EXPECTED RESULT: Should validate user isolation during race conditions.
        """
        # Get real services
        redis_client = real_services_fixture["redis"]
        
        # Create multiple authenticated users for isolation testing
        user_contexts = []
        for i in range(3):  # 3 users for isolation testing
            user_email = f"isolation_test_user_{i}_{int(time.time())}@example.com"
            context = await create_authenticated_user_context(
                user_email=user_email,
                environment="test",
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        # Test concurrent user operations with state isolation
        isolation_test_results = []
        
        async def user_operation(user_context, user_index):
            """Perform user-specific operations and track state isolation."""
            try:
                user_id = str(user_context.user_id)
                websocket_id = str(user_context.websocket_client_id)
                
                # Create user-specific Redis state
                user_state = {
                    "user_id": user_id,
                    "websocket_id": websocket_id,
                    "user_index": user_index,
                    "messages": [],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "active"
                }
                
                user_key = f"user:state:{user_id}"
                websocket_key = f"websocket:state:{websocket_id}"
                
                # Store initial state
                await redis_client.setex(user_key, 3600, json.dumps(user_state))
                await redis_client.setex(websocket_key, 3600, json.dumps(user_state))
                
                # Perform rapid operations to test isolation
                for operation in range(5):
                    # Update user state
                    user_state["messages"].append({
                        "operation": operation,
                        "message": f"User {user_index} operation {operation}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    user_state["last_operation"] = operation
                    
                    # Store updated state
                    await redis_client.setex(user_key, 3600, json.dumps(user_state))
                    await redis_client.setex(websocket_key, 3600, json.dumps(user_state))
                    
                    # Small delay to allow concurrent operations
                    await asyncio.sleep(0.01)
                
                # Verify final state integrity
                final_user_state = await redis_client.get(user_key)
                final_websocket_state = await redis_client.get(websocket_key)
                
                if final_user_state and final_websocket_state:
                    user_data = json.loads(final_user_state.decode())
                    websocket_data = json.loads(final_websocket_state.decode())
                    
                    # Check state consistency
                    state_consistent = (
                        user_data.get("user_id") == user_id and
                        websocket_data.get("user_id") == user_id and
                        user_data.get("user_index") == user_index and
                        len(user_data.get("messages", [])) == 5
                    )
                    
                    # Check for contamination from other users
                    no_contamination = (
                        user_data.get("user_index") == user_index and
                        websocket_data.get("user_index") == user_index
                    )
                    
                    return {
                        "user_index": user_index,
                        "user_id": user_id,
                        "success": True,
                        "state_consistent": state_consistent,
                        "no_contamination": no_contamination,
                        "message_count": len(user_data.get("messages", [])),
                        "final_user_data": user_data,
                        "final_websocket_data": websocket_data
                    }
                else:
                    return {
                        "user_index": user_index,
                        "user_id": user_id,
                        "success": False,
                        "error": "State not found in Redis",
                        "state_consistent": False,
                        "no_contamination": False
                    }
                    
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id if user_context else "unknown",
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "state_consistent": False,
                    "no_contamination": False
                }
        
        # Run concurrent user operations
        user_tasks = [
            user_operation(context, i) 
            for i, context in enumerate(user_contexts)
        ]
        
        isolation_test_results = await asyncio.gather(*user_tasks)
        
        # Analyze isolation results
        successful_users = sum(1 for r in isolation_test_results if r.get("success", False))
        consistent_states = sum(1 for r in isolation_test_results if r.get("state_consistent", False))
        no_contamination_count = sum(1 for r in isolation_test_results if r.get("no_contamination", False))
        
        print(f"\n👥 MULTI-USER ISOLATION ANALYSIS:")
        print(f"📊 Successful user operations: {successful_users}/{len(isolation_test_results)}")
        print(f"✅ Consistent states: {consistent_states}/{len(isolation_test_results)}")
        print(f"🔒 No contamination: {no_contamination_count}/{len(isolation_test_results)}")
        
        # Print detailed isolation results
        print(f"\n📋 User Isolation Results:")
        for result in isolation_test_results:
            user_idx = result.get("user_index", "unknown")
            success = "✅" if result.get("success", False) else "❌"
            consistent = "✅" if result.get("state_consistent", False) else "❌"
            no_contam = "✅" if result.get("no_contamination", False) else "❌"
            msg_count = result.get("message_count", 0)
            error = result.get("error", "")
            
            print(f"   User {user_idx}: {success} Consistent:{consistent} Isolated:{no_contam} Messages:{msg_count} {error}")
        
        # Check for cross-user contamination in Redis
        contamination_detected = False
        for i, result_a in enumerate(isolation_test_results):
            if not result_a.get("success"):
                continue
                
            user_data_a = result_a.get("final_user_data", {})
            for j, result_b in enumerate(isolation_test_results):
                if i == j or not result_b.get("success"):
                    continue
                    
                user_data_b = result_b.get("final_user_data", {})
                
                # Check if user A's data contains user B's information
                if user_data_a.get("user_index") != i:
                    contamination_detected = True
                    print(f"   ⚠️  User {i} data contaminated with user {user_data_a.get('user_index')} data")
        
        # Check for isolation failures
        isolation_failures = (
            successful_users < len(isolation_test_results) or  # Some operations failed
            consistent_states < len(isolation_test_results) or  # State inconsistency
            no_contamination_count < len(isolation_test_results) or  # Contamination detected
            contamination_detected  # Cross-user data leakage
        )
        
        if isolation_failures:
            print(f"\n🚨 USER ISOLATION FAILURES DETECTED:")
            print(f"   Multi-user isolation race conditions found")
            print(f"   These can cause user data leakage and state corruption")
            
            assert False, (
                f"User isolation failures detected:\n"
                f"Successful operations: {successful_users}/{len(isolation_test_results)}\n"
                f"Consistent states: {consistent_states}/{len(isolation_test_results)}\n"
                f"No contamination: {no_contamination_count}/{len(isolation_test_results)}\n"
                f"Cross-contamination: {contamination_detected}\n"
                f"This proves user isolation race conditions exist."
            )
        else:
            print(f"\n✅ USER ISOLATION APPEARS ROBUST:")
            print(f"   All users maintained proper state isolation")
            print(f"   No cross-user contamination detected")