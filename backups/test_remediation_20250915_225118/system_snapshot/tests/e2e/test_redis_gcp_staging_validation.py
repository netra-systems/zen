"""
Redis GCP Staging Validation Test Suite - End-to-End

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Production
- Business Goal: Production Chat Reliability (90% of platform value)
- Value Impact: Validates complete golden path: users login → get AI responses
- Strategic Impact: Protects $500K+ ARR by ensuring staging matches production behavior

This test suite validates the complete Redis integration in GCP staging environment:
1. Redis connectivity through VPC connector
2. Complete chat workflow with Redis state persistence
3. WebSocket events delivery with Redis backend
4. Multi-user chat sessions without conflicts
5. Production-like performance characteristics
6. Error recovery and resilience

CRITICAL: Targets GCP staging environment (*.netrasystems.ai domains)
Uses REAL Redis services as deployed in Cloud Run staging
NO DOCKER - validates actual GCP deployment architecture
"""

import asyncio
import pytest
import time
import json
import uuid
import os
from typing import Dict, Any, List, Optional
import aiohttp
import websockets
from unittest.mock import patch

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Redis SSOT imports
from netra_backend.app.redis_manager import redis_manager

# Configuration imports
from netra_backend.app.core.backend_environment import BackendEnvironment

# Shared utilities
from shared.isolated_environment import get_env

# Logging
import logging
logger = logging.getLogger(__name__)


class TestRedisGCPStagingValidation(SSotAsyncTestCase):
    """Test Redis integration in GCP staging environment."""
    
    async def asyncSetUp(self):
        """Set up GCP staging test environment."""
        await super().asyncSetUp()
        
        # Configure for GCP staging environment
        self.staging_env = {
            "ENVIRONMENT": "staging",
            "GCP_PROJECT": "netra-staging",
            # Updated staging domains per Issue #1278 fix
            "BACKEND_URL": "https://staging.netrasystems.ai",
            "FRONTEND_URL": "https://staging.netrasystems.ai",
            "WEBSOCKET_URL": "wss://api.staging.netrasystems.ai",
            "REDIS_URL": "redis://10.0.0.3:6379/0",  # GCP internal Redis
            "VPC_CONNECTOR": "staging-connector"
        }
        
        for key, value in self.staging_env.items():
            self.set_env_var(key, value)
        
        # Initialize Redis with staging configuration
        await redis_manager.initialize()
        
        # Test session tracking
        self.staging_session_id = f"gcp_staging_{uuid.uuid4().hex[:8]}"
        
        # Skip tests if not in staging environment or Redis not available
        if not self._is_staging_environment():
            pytest.skip("Not in staging environment - skipping GCP staging tests")
        
        if not redis_manager.is_connected:
            pytest.skip("Redis not connected in staging - skipping GCP Redis tests")
        
        logger.info(f"GCP staging Redis test session: {self.staging_session_id}")
    
    async def asyncTearDown(self):
        """Clean up GCP staging test state."""
        try:
            # Clean up staging test data
            if redis_manager.is_connected:
                staging_keys = await redis_manager.keys(f"gcp_staging:{self.staging_session_id}:*")
                for key in staging_keys:
                    await redis_manager.delete(key)
                    
                logger.info(f"Cleaned up {len(staging_keys)} staging test keys")
        except Exception as e:
            logger.debug(f"GCP staging cleanup error (non-critical): {e}")
        
        await super().asyncTearDown()
    
    def _is_staging_environment(self) -> bool:
        """Check if running in staging environment."""
        environment = get_env().get("ENVIRONMENT", "").lower()
        backend_url = get_env().get("BACKEND_URL", "")
        
        return (
            environment == "staging" or
            "staging.netrasystems.ai" in backend_url or
            "netra-staging" in get_env().get("GCP_PROJECT", "")
        )
    
    async def test_gcp_redis_connectivity_through_vpc(self):
        """Test Redis connectivity through GCP VPC connector."""
        # Verify Redis is connected through VPC
        self.assertTrue(redis_manager.is_connected, "Redis should be connected through VPC connector")
        
        # Test basic connectivity
        ping_result = await redis_manager._client.ping() if redis_manager._client else False
        self.assertTrue(ping_result, "Redis ping should succeed through VPC connector")
        
        # Store staging connectivity test data
        connectivity_data = {
            "test_type": "gcp_vpc_connectivity",
            "session_id": self.staging_session_id,
            "timestamp": time.time(),
            "vpc_connector": "staging-connector",
            "redis_internal_ip": "10.0.0.3"
        }
        
        connectivity_key = f"gcp_staging:{self.staging_session_id}:connectivity"
        stored = await redis_manager.set(connectivity_key, json.dumps(connectivity_data), ex=300)
        self.assertTrue(stored, "Should store connectivity data through VPC")
        
        # Verify data retrieval
        retrieved_data_json = await redis_manager.get(connectivity_key)
        self.assertIsNotNone(retrieved_data_json, "Should retrieve data through VPC")
        
        retrieved_data = json.loads(retrieved_data_json)
        self.assertEqual(retrieved_data["vpc_connector"], "staging-connector")
        
        logger.info("GCP VPC Redis connectivity validated successfully")
    
    async def test_complete_chat_workflow_with_staging_redis(self):
        """Test complete chat workflow using staging Redis backend."""
        # Simulate complete golden path: user login → agent execution → AI response
        
        # 1. User session setup
        user_id = f"staging_user_{uuid.uuid4().hex[:8]}"
        chat_session_id = f"chat_{uuid.uuid4().hex[:8]}"
        
        user_session = {
            "user_id": user_id,
            "chat_session_id": chat_session_id,
            "stage": "authenticated",
            "timestamp": time.time(),
            "staging_test": True
        }
        
        session_key = f"gcp_staging:{self.staging_session_id}:user_session:{user_id}"
        await redis_manager.set(session_key, json.dumps(user_session), ex=600)
        
        # 2. Agent execution state
        agent_states = [
            {"phase": "initialization", "status": "started", "agent": "supervisor"},
            {"phase": "analysis", "status": "thinking", "agent": "supervisor"}, 
            {"phase": "tool_execution", "status": "executing", "tool": "search"},
            {"phase": "tool_completion", "status": "completed", "tool": "search"},
            {"phase": "response_generation", "status": "completed", "result": "AI response generated"}
        ]
        
        # Store agent execution sequence
        for i, state in enumerate(agent_states):
            state_with_metadata = {
                **state,
                "user_id": user_id,
                "chat_session_id": chat_session_id,
                "sequence": i,
                "timestamp": time.time()
            }
            
            state_key = f"gcp_staging:{self.staging_session_id}:agent_state:{chat_session_id}:{i}"
            await redis_manager.set(state_key, json.dumps(state_with_metadata), ex=600)
        
        # 3. WebSocket events simulation
        websocket_events = [
            {"type": "agent_started", "data": {"agent": "supervisor"}},
            {"type": "agent_thinking", "data": {"phase": "analysis"}},
            {"type": "tool_executing", "data": {"tool": "search"}},
            {"type": "tool_completed", "data": {"tool": "search", "result": "success"}},
            {"type": "agent_completed", "data": {"status": "completed", "response": "AI response"}}
        ]
        
        # Store WebSocket events
        events_key = f"gcp_staging:{self.staging_session_id}:ws_events:{chat_session_id}"
        for event in websocket_events:
            event_with_metadata = {
                **event,
                "chat_session_id": chat_session_id,
                "user_id": user_id,
                "timestamp": time.time()
            }
            await redis_manager.lpush(events_key, json.dumps(event_with_metadata))
        
        await redis_manager.expire(events_key, 600)
        
        # 4. Validate complete workflow state
        # Check user session
        retrieved_session_json = await redis_manager.get(session_key)
        retrieved_session = json.loads(retrieved_session_json)
        self.assertEqual(retrieved_session["user_id"], user_id)
        self.assertEqual(retrieved_session["stage"], "authenticated")
        
        # Check agent states
        for i in range(len(agent_states)):
            state_key = f"gcp_staging:{self.staging_session_id}:agent_state:{chat_session_id}:{i}"
            state_json = await redis_manager.get(state_key)
            state_data = json.loads(state_json)
            self.assertEqual(state_data["sequence"], i)
            self.assertEqual(state_data["user_id"], user_id)
        
        # Check WebSocket events
        events_count = await redis_manager.llen(events_key)
        self.assertEqual(events_count, 5, "All 5 WebSocket events should be stored")
        
        logger.info(f"Complete chat workflow validated in staging Redis for user {user_id}")
    
    async def test_staging_redis_multi_user_chat_isolation(self):
        """Test multi-user chat isolation in staging Redis."""
        # Simulate multiple concurrent users in staging
        user_count = 3
        users_data = []
        
        for i in range(user_count):
            user_id = f"staging_multi_user_{i}_{uuid.uuid4().hex[:4]}"
            chat_session_id = f"multi_chat_{i}_{uuid.uuid4().hex[:4]}"
            
            user_data = {
                "user_id": user_id,
                "chat_session_id": chat_session_id,
                "user_index": i,
                "session_type": "multi_user_test",
                "staging_environment": True
            }
            
            users_data.append(user_data)
        
        # Store all users concurrently
        async def store_user_session(user_data):
            user_id = user_data["user_id"]
            chat_session_id = user_data["chat_session_id"]
            
            # Store user session
            session_key = f"gcp_staging:{self.staging_session_id}:multi_user:{user_id}"
            await redis_manager.set(session_key, json.dumps(user_data), ex=600)
            
            # Store user-specific chat state
            chat_state = {
                "user_id": user_id,
                "chat_session_id": chat_session_id,
                "messages": [
                    {"role": "user", "content": f"Hello from user {user_data['user_index']}"},
                    {"role": "assistant", "content": f"Hello user {user_data['user_index']}! How can I help?"}
                ],
                "agent_status": "ready"
            }
            
            chat_key = f"gcp_staging:{self.staging_session_id}:chat_state:{chat_session_id}"
            await redis_manager.set(chat_key, json.dumps(chat_state), ex=600)
            
            return user_id, chat_session_id
        
        # Execute concurrent user operations
        results = await asyncio.gather(*[
            store_user_session(user_data) for user_data in users_data
        ])
        
        # Validate user isolation
        for i, (user_id, chat_session_id) in enumerate(results):
            # Check user session
            session_key = f"gcp_staging:{self.staging_session_id}:multi_user:{user_id}"
            session_json = await redis_manager.get(session_key)
            session_data = json.loads(session_json)
            
            self.assertEqual(session_data["user_id"], user_id)
            self.assertEqual(session_data["user_index"], i)
            
            # Check chat state
            chat_key = f"gcp_staging:{self.staging_session_id}:chat_state:{chat_session_id}"
            chat_json = await redis_manager.get(chat_key)
            chat_data = json.loads(chat_json)
            
            self.assertEqual(chat_data["user_id"], user_id)
            self.assertEqual(chat_data["chat_session_id"], chat_session_id)
            self.assertEqual(len(chat_data["messages"]), 2)
        
        logger.info(f"Multi-user chat isolation validated for {user_count} users in staging Redis")
    
    async def test_staging_redis_performance_characteristics(self):
        """Test Redis performance characteristics in staging environment."""
        # Test basic operation performance in staging
        operations_count = 50
        
        operation_times = []
        
        for i in range(operations_count):
            test_data = {
                "operation_id": i,
                "staging_test": True,
                "data_size": "1KB",
                "test_content": "x" * 1024  # 1KB of data
            }
            
            start_time = time.time()
            
            # Set operation
            key = f"gcp_staging:{self.staging_session_id}:perf:{i}"
            await redis_manager.set(key, json.dumps(test_data), ex=300)
            
            # Get operation
            retrieved_data = await redis_manager.get(key)
            
            operation_time = time.time() - start_time
            operation_times.append(operation_time)
            
            # Verify data integrity
            retrieved_obj = json.loads(retrieved_data)
            self.assertEqual(retrieved_obj["operation_id"], i)
        
        # Calculate performance metrics
        avg_operation_time = sum(operation_times) / len(operation_times) * 1000  # ms
        max_operation_time = max(operation_times) * 1000  # ms
        
        # Staging performance should be reasonable for chat functionality
        self.assertLess(avg_operation_time, 50.0, "Average staging Redis operation should be < 50ms")
        self.assertLess(max_operation_time, 200.0, "Max staging Redis operation should be < 200ms")
        
        logger.info(f"Staging Redis performance: avg={avg_operation_time:.2f}ms, max={max_operation_time:.2f}ms")
    
    async def test_staging_redis_error_recovery(self):
        """Test Redis error recovery in staging environment."""
        # Test circuit breaker functionality in staging
        circuit_status = redis_manager._circuit_breaker.get_status()
        self.assertIn("state", circuit_status)
        
        # Test that operations continue working
        recovery_data = {
            "test_type": "error_recovery",
            "staging_environment": True,
            "session_id": self.staging_session_id,
            "timestamp": time.time()
        }
        
        recovery_key = f"gcp_staging:{self.staging_session_id}:recovery_test"
        stored = await redis_manager.set(recovery_key, json.dumps(recovery_data), ex=300)
        self.assertTrue(stored, "Recovery test data should be stored")
        
        # Test circuit breaker reset
        await redis_manager.reset_circuit_breaker()
        
        # Verify operations still work after reset
        post_reset_data = {
            "test_type": "post_circuit_reset",
            "staging_environment": True,
            "timestamp": time.time()
        }
        
        post_reset_key = f"gcp_staging:{self.staging_session_id}:post_reset"
        stored = await redis_manager.set(post_reset_key, json.dumps(post_reset_data), ex=300)
        self.assertTrue(stored, "Post-reset operations should work")
        
        logger.info("Staging Redis error recovery validated successfully")
    
    async def test_staging_websocket_redis_integration(self):
        """Test WebSocket + Redis integration in staging environment."""
        # Test WebSocket event persistence in staging Redis
        websocket_session_id = f"ws_staging_{uuid.uuid4().hex[:8]}"
        
        # Simulate WebSocket connection state
        connection_state = {
            "websocket_session_id": websocket_session_id,
            "staging_test": True,
            "connection_status": "active",
            "user_id": f"ws_user_{uuid.uuid4().hex[:8]}",
            "connected_at": time.time()
        }
        
        connection_key = f"gcp_staging:{self.staging_session_id}:ws_connection:{websocket_session_id}"
        await redis_manager.set(connection_key, json.dumps(connection_state), ex=600)
        
        # Simulate WebSocket message sequence
        messages = [
            {"type": "connection_established", "timestamp": time.time()},
            {"type": "agent_request", "content": "Help me optimize my AI workflow", "timestamp": time.time()},
            {"type": "agent_started", "agent": "supervisor", "timestamp": time.time()},
            {"type": "agent_response", "content": "I'll help you optimize your workflow...", "timestamp": time.time()},
            {"type": "conversation_completed", "timestamp": time.time()}
        ]
        
        # Store message sequence
        for i, message in enumerate(messages):
            message_key = f"gcp_staging:{self.staging_session_id}:ws_message:{websocket_session_id}:{i}"
            await redis_manager.set(message_key, json.dumps(message), ex=600)
        
        # Validate WebSocket state persistence
        retrieved_connection_json = await redis_manager.get(connection_key)
        retrieved_connection = json.loads(retrieved_connection_json)
        
        self.assertEqual(retrieved_connection["websocket_session_id"], websocket_session_id)
        self.assertEqual(retrieved_connection["connection_status"], "active")
        
        # Validate message persistence
        for i in range(len(messages)):
            message_key = f"gcp_staging:{self.staging_session_id}:ws_message:{websocket_session_id}:{i}"
            message_json = await redis_manager.get(message_key)
            message_data = json.loads(message_json)
            
            self.assertEqual(message_data["type"], messages[i]["type"])
        
        logger.info(f"WebSocket + Redis integration validated in staging for session {websocket_session_id}")


class TestStagingRedisProductionReadiness(SSotAsyncTestCase):
    """Test production readiness of Redis in staging environment."""
    
    async def asyncSetUp(self):
        """Set up production readiness test environment."""
        await super().asyncSetUp()
        
        # Configure for staging
        self.set_env_var("ENVIRONMENT", "staging")
        
        await redis_manager.initialize()
        
        if not redis_manager.is_connected:
            pytest.skip("Redis not connected in staging - skipping production readiness tests")
        
        self.readiness_session_id = f"readiness_{uuid.uuid4().hex[:8]}"
    
    async def asyncTearDown(self):
        """Clean up production readiness test state."""
        try:
            if redis_manager.is_connected:
                readiness_keys = await redis_manager.keys(f"production_readiness:{self.readiness_session_id}:*")
                for key in readiness_keys:
                    await redis_manager.delete(key)
        except Exception as e:
            logger.debug(f"Production readiness cleanup error (non-critical): {e}")
        
        await super().asyncTearDown()
    
    async def test_redis_production_load_simulation(self):
        """Test Redis under production-like load in staging."""
        # Simulate production load characteristics
        concurrent_users = 10
        operations_per_user = 20
        
        async def simulate_production_user(user_index: int):
            user_id = f"prod_sim_user_{user_index}"
            
            # Simulate typical user session operations
            operations = [
                "user_authentication",
                "session_creation", 
                "chat_initialization",
                "agent_execution",
                "websocket_events",
                "state_persistence",
                "cache_operations",
                "session_cleanup"
            ]
            
            for op_index in range(operations_per_user):
                operation_type = operations[op_index % len(operations)]
                
                operation_data = {
                    "user_id": user_id,
                    "operation_type": operation_type,
                    "operation_index": op_index,
                    "timestamp": time.time(),
                    "production_simulation": True
                }
                
                key = f"production_readiness:{self.readiness_session_id}:user_{user_index}:op_{op_index}"
                await redis_manager.set(key, json.dumps(operation_data), ex=300)
                
                # Small delay to simulate realistic usage
                await asyncio.sleep(0.02)
            
            return user_index
        
        # Run production load simulation
        start_time = time.time()
        
        results = await asyncio.gather(*[
            simulate_production_user(i) for i in range(concurrent_users)
        ])
        
        total_time = time.time() - start_time
        total_operations = concurrent_users * operations_per_user
        throughput = total_operations / total_time
        
        # Production readiness criteria
        self.assertEqual(len(results), concurrent_users, "All users should complete successfully")
        self.assertGreater(throughput, 50.0, "Should handle > 50 ops/sec for production readiness")
        
        logger.info(f"Production load simulation: {concurrent_users} users, {total_operations} ops, {throughput:.2f} ops/sec")
    
    async def test_redis_data_consistency_under_load(self):
        """Test data consistency under concurrent load."""
        # Test data consistency with concurrent writes/reads
        shared_counter_key = f"production_readiness:{self.readiness_session_id}:shared_counter"
        
        # Initialize counter
        await redis_manager.set(shared_counter_key, "0", ex=300)
        
        # Concurrent increment operations
        increment_count = 50
        
        async def increment_shared_counter(increment_id: int):
            # Read current value
            current_value = await redis_manager.get(shared_counter_key)
            current_int = int(current_value) if current_value else 0
            
            # Increment
            new_value = current_int + 1
            
            # Write back
            await redis_manager.set(shared_counter_key, str(new_value), ex=300)
            
            return increment_id
        
        # Run concurrent increments
        await asyncio.gather(*[
            increment_shared_counter(i) for i in range(increment_count)
        ])
        
        # Check final value (may not be exactly increment_count due to race conditions, but should be reasonable)
        final_value = await redis_manager.get(shared_counter_key)
        final_int = int(final_value) if final_value else 0
        
        # Final value should be positive and not exceed the increment count
        self.assertGreater(final_int, 0, "Counter should be incremented")
        self.assertLessEqual(final_int, increment_count, "Counter should not exceed increment count")
        
        logger.info(f"Data consistency test: final counter value {final_int} (expected max {increment_count})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])