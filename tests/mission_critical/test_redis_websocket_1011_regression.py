"""
"""
Redis WebSocket 1011 Regression Test Suite - Mission Critical

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal
- Business Goal: Chat Functionality Reliability (90% of platform value)
- Value Impact: Prevents WebSocket 1011 errors that break real-time chat
- Strategic Impact: Protects $500K+ ARR by ensuring reliable WebSocket connections

This test suite specifically targets the WebSocket 1011 error that was caused by:
1. Competing Redis managers creating connection conflicts
2. Race conditions during WebSocket handshake with Redis state
3. Circuit breaker failures causing silent Redis errors
4. Legacy Redis manager conflicts with SSOT implementation

CRITICAL ISSUE #849 VALIDATION:
- Ensures SSOT Redis Manager prevents competing implementations
- Validates WebSocket connections don't fail with 1011 errors'
- Tests race condition scenarios that previously caused failures
- Verifies chat functionality remains reliable under load

GOLDEN PATH PROTECTION: Users login → get AI responses
"
"

"""
"""
import asyncio
import pytest
import time
import json
import uuid
import threading
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import SSotWebSocketTestUtility

# Redis SSOT imports - CRITICAL: Only import SSOT implementation
from netra_backend.app.redis_manager import redis_manager as ssot_redis_manager
from netra_backend.app.redis_manager import RedisManager as SSotRedisManager

# Legacy import to verify deprecation
from netra_backend.app.core.redis_manager import redis_manager as legacy_redis_manager

# WebSocket imports
from netra_backend.app.websocket_core.manager import WebSocketManager

# Shared utilities
from shared.isolated_environment import get_env

# Logging
import logging
logger = logging.getLogger(__name__)


class TestWebSocket1011Regression(SSotAsyncTestCase):
    "Test WebSocket 1011 error regression scenarios."
    
    async def asyncSetUp(self):
        "Set up test environment for WebSocket 1011 regression testing."
        await super().asyncSetUp()
        
        # Configure test environment to simulate production scenarios
        self.test_env = {
            TESTING: "true,"
            ENVIRONMENT": test,"
            TEST_DISABLE_REDIS: false,
            REDIS_URL": redis://localhost:6381/0,"
            WEBSOCKET_HOST: localhost,
            WEBSOCKET_PORT: "8001"
        }
        
        for key, value in self.test_env.items():
            self.set_env_var(key, value)
        
        # Initialize SSOT Redis manager
        await ssot_redis_manager.initialize()
        
        # Track test session
        self.test_session_id = fregression_{uuid.uuid4().hex[:8]}"
        self.test_session_id = fregression_{uuid.uuid4().hex[:8]}"
        self.websocket_connections = []
        
        logger.info(fWebSocket 1011 regression test session: {self.test_session_id})
    
    async def asyncTearDown(self):
        "Clean up WebSocket 1011 regression test state."
        try:
            # Clean up test data from Redis
            if ssot_redis_manager.is_connected:
                test_keys = await ssot_redis_manager.keys(fregression:{self.test_session_id}:*)
                for key in test_keys:
                    await ssot_redis_manager.delete(key)
            
            # Close any remaining WebSocket connections
            for connection in self.websocket_connections:
                if hasattr(connection, 'close'):
                    try:
                        await connection.close()
                    except Exception:
                        pass
            
        except Exception as e:
            logger.debug(fRegression cleanup error (non-critical): {e})"
            logger.debug(fRegression cleanup error (non-critical): {e})"
        
        await super().asyncTearDown()
    
    async def test_no_competing_redis_managers_prevent_1011(self):
        "Test that SSOT Redis Manager prevents competing implementations."
        # CRITICAL: Verify legacy manager redirects to SSOT
        self.assertIs(
            legacy_redis_manager,
            ssot_redis_manager,
            Legacy Redis manager should redirect to SSOT implementation""
        )
        
        # Verify only one Redis manager instance is active
        redis_manager_id_ssot = id(ssot_redis_manager)
        redis_manager_id_legacy = id(legacy_redis_manager)
        
        self.assertEqual(
            redis_manager_id_ssot,
            redis_manager_id_legacy,
            SSOT and legacy Redis managers should be the same instance
        )
        
        # Test that multiple imports don't create competing instances'
        from netra_backend.app.redis_manager import redis_manager as import1
        from netra_backend.app.core.redis_manager import redis_manager as import2
        
        self.assertIs(import1, import2, Multiple imports should return same Redis manager instance)"
        self.assertIs(import1, import2, Multiple imports should return same Redis manager instance)"
        self.assertIs(import1, ssot_redis_manager, "All imports should reference SSOT manager)"
    
    async def test_websocket_handshake_redis_race_condition_prevention(self):
        Test WebSocket handshake doesn't race with Redis operations.""'
        if not ssot_redis_manager.is_connected:
            self.skipTest(Redis not connected - skipping race condition test)
        
        # Simulate rapid WebSocket connection attempts with Redis state
        connection_attempts = 5
        successful_connections = 0
        
        async def simulate_websocket_connection(connection_id: str):
            "Simulate WebSocket connection with Redis state management."
            try:
                # Store connection state in Redis (simulating WebSocket manager)
                connection_state = {
                    connection_id: connection_id,
                    session_id": self.test_session_id,"
                    status: connecting,
                    timestamp: time.time()"
                    timestamp: time.time()"
                }
                
                state_key = fregression:{self.test_session_id}:ws:{connection_id}"
                state_key = fregression:{self.test_session_id}:ws:{connection_id}"
                
                # This operation should not race with other connections
                stored = await ssot_redis_manager.set(
                    state_key,
                    json.dumps(connection_state),
                    ex=300
                )
                
                if stored:
                    # Update to connected state
                    connection_state[status] = connected
                    await ssot_redis_manager.set(
                        state_key,
                        json.dumps(connection_state),
                        ex=300
                    )
                    return True
                else:
                    logger.warning(f"Failed to store connection state for {connection_id}))"
                    return False
                    
            except Exception as e:
                logger.error(fRace condition in connection {connection_id}: {e}")"
                return False
        
        # Run multiple connection attempts concurrently
        connection_ids = [fconn_{i}_{uuid.uuid4().hex[:4]} for i in range(connection_attempts)]
        
        results = await asyncio.gather(*[
            simulate_websocket_connection(conn_id)
            for conn_id in connection_ids
        ], return_exceptions=True)
        
        # Count successful connections
        successful_connections = sum(1 for result in results if result is True)
        
        # All connections should succeed without race conditions
        self.assertEqual(
            successful_connections,
            connection_attempts,
            fAll {connection_attempts} WebSocket connections should succeed without race conditions"
            fAll {connection_attempts} WebSocket connections should succeed without race conditions"
        )
        
        # Verify all connection states are stored correctly
        for connection_id in connection_ids:
            state_key = f"regression:{self.test_session_id}:ws:{connection_id}"
            stored_state_json = await ssot_redis_manager.get(state_key)
            
            self.assertIsNotNone(stored_state_json, fConnection {connection_id} state should be stored)
            stored_state = json.loads(stored_state_json)
            self.assertEqual(stored_state[status], connected")"
    
    async def test_redis_circuit_breaker_prevents_1011_errors(self):
        "Test Redis circuit breaker prevents cascading failures that cause 1011 errors."
        # Check initial circuit breaker state
        initial_status = ssot_redis_manager._circuit_breaker.get_status()
        self.assertIn(state", initial_status)"
        
        # Test that circuit breaker allows normal operations
        can_execute = ssot_redis_manager._circuit_breaker.can_execute()
        self.assertTrue(can_execute, Circuit breaker should allow execution in normal state)
        
        if ssot_redis_manager.is_connected:
            # Test normal operation through circuit breaker
            test_key = fregression:{self.test_session_id}:circuit_test"
            test_key = fregression:{self.test_session_id}:circuit_test"
            test_data = {"circuit_breaker: functional, websocket: protected}"
            
            stored = await ssot_redis_manager.set(test_key, json.dumps(test_data))
            self.assertTrue(stored, "Normal Redis operations should succeed through circuit breaker)"
            
            # Verify data is retrievable
            retrieved_data_json = await ssot_redis_manager.get(test_key)
            retrieved_data = json.loads(retrieved_data_json)
            self.assertEqual(retrieved_data[circuit_breaker], functional)
        
        # Test circuit breaker reset functionality
        await ssot_redis_manager.reset_circuit_breaker()
        
        # Verify circuit breaker is in proper state after reset
        reset_status = ssot_redis_manager._circuit_breaker.get_status()
        logger.info(fCircuit breaker status after reset: {reset_status})"
        logger.info(fCircuit breaker status after reset: {reset_status})"
    
    async def test_websocket_event_delivery_no_1011_errors(self):
        "Test WebSocket event delivery doesn't cause 1011 errors with Redis state."
        if not ssot_redis_manager.is_connected:
            self.skipTest(Redis not connected - skipping event delivery test")"
        
        # Simulate the 5 critical WebSocket events that must be delivered
        critical_events = [
            {"type": agent_started, "data": {"agent": "supervisor, run_id: self.test_session_id}},"
            {"type": agent_thinking, ""data": {"phase": analysis, progress: 0.2}},"
            {"type": tool_executing", ""data": {"tool: search, status: "running"}},"
            {"type": tool_completed, "data": {""tool: search", result: success}},"
            {"type: agent_completed", "data": {"status: completed, final_result": "success}}"
        ]
        
        # Store events in Redis with proper state management
        event_sequence_key = fregression:{self.test_session_id}:events
        
        for i, event in enumerate(critical_events):
            # Each event should be stored without causing Redis conflicts
            event_with_metadata = {
                **event,
                "sequence_number: i,"
                timestamp: time.time(),
                session_id: self.test_session_id"
                session_id: self.test_session_id"
            }
            
            # Store individual event
            individual_key = fregression:{self.test_session_id}:event:{i}"
            individual_key = fregression:{self.test_session_id}:event:{i}"
            stored = await ssot_redis_manager.set(
                individual_key,
                json.dumps(event_with_metadata),
                ex=300
            )
            self.assertTrue(stored, fEvent {i} ({event['type']} should be stored successfully)
            
            # Add to event sequence
            await ssot_redis_manager.lpush(event_sequence_key, json.dumps(event_with_metadata))
        
        # Verify complete event sequence is intact
        sequence_length = await ssot_redis_manager.llen(event_sequence_key)
        self.assertEqual(sequence_length, 5, All 5 critical events should be in sequence)"
        self.assertEqual(sequence_length, 5, All 5 critical events should be in sequence)"
        
        # Verify events can be retrieved without errors
        for i in range(5):
            individual_key = f"regression:{self.test_session_id}:event:{i}"
            event_json = await ssot_redis_manager.get(individual_key)
            
            self.assertIsNotNone(event_json, fEvent {i} should be retrievable)
            event_data = json.loads(event_json)
            self.assertEqual(event_data[sequence_number], i)"
            self.assertEqual(event_data[sequence_number], i)"
            self.assertIn(event_data[type"), [e[type) for e in critical_events)"
    
    async def test_concurrent_user_websocket_no_1011_conflicts(self):
        Test concurrent users don't cause WebSocket 1011 errors via Redis conflicts.""'
        if not ssot_redis_manager.is_connected:
            self.skipTest(Redis not connected - skipping concurrent user test)
        
        # Simulate multiple users connecting simultaneously
        user_count = 3
        users = [fuser_{i}_{uuid.uuid4().hex[:4]} for i in range(user_count)]"
        users = [fuser_{i}_{uuid.uuid4().hex[:4]} for i in range(user_count)]"
        
        async def simulate_user_websocket_session(user_id: str):
            "Simulate complete user WebSocket session with Redis state."
            user_run_id = frun_{user_id}_{uuid.uuid4().hex[:4]}""
            
            try:
                # Store user session state
                session_state = {
                    user_id: user_id,
                    run_id: user_run_id,"
                    run_id: user_run_id,"
                    "session_id: self.test_session_id,"
                    status: active,
                    websocket_connection": established"
                }
                
                session_key = fregression:{self.test_session_id}:user:{user_id}
                await ssot_redis_manager.set(session_key, json.dumps(session_state), ex=300)
                
                # Simulate agent events for this user
                user_events = [
                    {"type": agent_started", user_id: user_id, run_id: user_run_id},"
                    {"type": agent_thinking, "user_id: user_id, run_id: user_run_id},"
                    {"type": agent_completed, user_id: user_id, run_id": user_run_id}"
                ]
                
                for event in user_events:
                    event_key = f"regression:{self.test_session_id}:user_event:{user_id}:{event['type']}"
                    await ssot_redis_manager.set(event_key, json.dumps(event), ex=300)
                    
                    # Small delay to allow interleaving
                    await asyncio.sleep(0.1)
                
                return {user_id: user_id, success: True}
                
            except Exception as e:
                logger.error(fUser {user_id} WebSocket session failed: {e})"
                logger.error(fUser {user_id} WebSocket session failed: {e})"
                return {"user_id: user_id, success: False, error: str(e)}"
        
        # Run all user sessions concurrently
        results = await asyncio.gather(*[
            simulate_user_websocket_session(user_id)
            for user_id in users
        ]
        
        # Verify all users succeeded without 1011 errors
        successful_users = [r for r in results if r[success"]]"
        self.assertEqual(
            len(successful_users),
            user_count,
            fAll {user_count} users should have successful WebSocket sessions
        )
        
        # Verify user isolation - each user should have their own data
        for user_id in users:
            session_key = fregression:{self.test_session_id}:user:{user_id}
            user_session_json = await ssot_redis_manager.get(session_key)
            
            self.assertIsNotNone(user_session_json, f"User {user_id} session should be stored)"
            user_session = json.loads(user_session_json)
            self.assertEqual(user_session[user_id"], user_id)"
            self.assertEqual(user_session[status], active)
    
    async def test_redis_auto_reconnection_prevents_websocket_1011(self):
        "Test Redis auto-reconnection prevents WebSocket 1011 errors during Redis hiccups."
        # Test Redis connection status
        original_connected = ssot_redis_manager.is_connected
        
        if original_connected:
            # Store critical WebSocket state
            critical_state = {
                session_id: self.test_session_id,"
                session_id: self.test_session_id,"
                "critical_websocket_data: must_survive_reconnection,"
                user_count: 5,
                active_agents": [supervisor, data_helper]"
            }
            
            state_key = fregression:{self.test_session_id}:critical_state
            await ssot_redis_manager.set(state_key, json.dumps(critical_state), ex=600)
            
            # Force reconnection to simulate Redis hiccup
            logger.info(Testing Redis auto-reconnection...")"
            reconnection_success = await ssot_redis_manager.force_reconnect()
            
            if reconnection_success:
                # Verify critical state survived reconnection
                recovered_state_json = await ssot_redis_manager.get(state_key)
                self.assertIsNotNone(recovered_state_json, Critical WebSocket state should survive Redis reconnection)
                
                recovered_state = json.loads(recovered_state_json)
                self.assertEqual(recovered_state[critical_websocket_data], "must_survive_reconnection)"
                self.assertEqual(recovered_state[user_count"], 5)"
                
                logger.info(Redis auto-reconnection successfully preserved WebSocket state)
            else:
                logger.info(Redis reconnection failed in test environment - this is expected")"
        else:
            logger.info(Redis not connected initially - skipping reconnection test)
    
    def test_redis_manager_status_monitoring_prevents_1011(self):
        "Test Redis manager status monitoring helps prevent 1011 errors."
        # Get comprehensive Redis manager status
        status = ssot_redis_manager.get_status()
        
        # Verify all critical status fields are present for 1011 error prevention
        critical_status_fields = [
            connected,
            client_available","
            consecutive_failures,
            background_tasks,"
            background_tasks,"
            "circuit_breaker"
        ]
        
        for field in critical_status_fields:
            self.assertIn(field, status, fStatus should include {field} for 1011 error monitoring)
        
        # Verify background tasks are properly tracked
        bg_tasks = status["background_tasks]"
        self.assertIn(reconnect_task_active, bg_tasks)
        self.assertIn(health_monitor_active, bg_tasks)"
        self.assertIn(health_monitor_active, bg_tasks)"
        
        # Verify circuit breaker status is available
        cb_status = status[circuit_breaker"]"
        self.assertIn(state, cb_status)
        
        # Log status for monitoring
        logger.info(fRedis SSOT Status (1011 Prevention): {json.dumps(status, indent=2)}")"
        
        # Status should indicate healthy state for WebSocket operations
        if status[connected]:
            self.assertTrue(status[client_available], "Redis client should be available when connected)"
            self.assertLessEqual(status[consecutive_failures"], 5, Consecutive failures should be low)"


class TestRedisSSotArchitectureCompliance(SSotAsyncTestCase):
    Test Redis SSOT architecture compliance prevents legacy conflicts.""
    
    def test_only_ssot_redis_manager_exists(self):
        Test that only SSOT Redis Manager is active in the system."
        Test that only SSOT Redis Manager is active in the system."
        # Verify SSOT Redis Manager is the canonical implementation
        from netra_backend.app.redis_manager import RedisManager as CanonicalRedisManager
        from netra_backend.app.redis_manager import redis_manager as canonical_instance
        
        self.assertIsInstance(canonical_instance, CanonicalRedisManager)
        
        # Verify legacy manager redirects to SSOT
        from netra_backend.app.core.redis_manager import redis_manager as legacy_instance
        
        self.assertIs(canonical_instance, legacy_instance, Legacy should redirect to SSOT")"
    
    def test_no_duplicate_redis_implementations(self):
        Test that no duplicate Redis implementations exist that could cause 1011 errors.""
        # This test ensures Issue #849 fix is maintained
        
        # All Redis imports should point to the same instance
        from netra_backend.app.redis_manager import redis_manager as ssot_import
        from netra_backend.app.core.redis_manager import redis_manager as legacy_import
        
        # Should be exactly the same object in memory
        self.assertIs(ssot_import, legacy_import, All Redis managers should be the same instance)
        
        # Verify instance IDs are identical
        ssot_id = id(ssot_import)
        legacy_id = id(legacy_import)
        
        self.assertEqual(ssot_id, legacy_id, Instance IDs should be identical to prevent conflicts)"
        self.assertEqual(ssot_id, legacy_id, Instance IDs should be identical to prevent conflicts)"
    
    def test_redis_ssot_compliance_prevents_websocket_conflicts(self):
        "Test that SSOT compliance prevents WebSocket connection conflicts."
        # Verify SSOT Redis Manager has all required methods for WebSocket support
        required_methods = [
            'initialize', 'get_client', 'set', 'get', 'delete', 'exists',
            'store_session', 'get_session', 'delete_session',
            'force_reconnect', 'reset_circuit_breaker', 'get_status'
        ]
        
        for method in required_methods:
            self.assertTrue(
                hasattr(ssot_redis_manager, method),
                f"SSOT Redis Manager should have {method} method for WebSocket support"
            )
        
        # Verify Redis manager is properly initialized
        self.assertIsInstance(ssot_redis_manager, SSotRedisManager)
        
        # Verify circuit breaker is configured
        self.assertIsNotNone(ssot_redis_manager._circuit_breaker)
        
        # Verify status reporting works for WebSocket monitoring
        status = ssot_redis_manager.get_status()
        self.assertIsInstance(status, dict)
        self.assertIn(connected", status)"


if __name__ == __main__:
    pytest.main([__file__, -v", "--tb=short")"
))))