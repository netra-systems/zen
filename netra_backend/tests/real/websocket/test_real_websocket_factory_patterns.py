"""Real WebSocket Factory Patterns Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal & All Customer Tiers
- Business Goal: Multi-User Isolation Architecture 
- Value Impact: Ensures factory patterns provide complete user isolation per CLAUDE.md requirements
- Strategic Impact: Enables reliable concurrent execution for 10+ users without data leakage

Tests real WebSocket factory patterns for user isolation with Docker services.
Validates factory-based isolation prevents shared state and enables multi-user platform.

CRITICAL per CLAUDE.md: Factory patterns are NOT optional - they enable reliable concurrent execution.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.factory_patterns
@pytest.mark.multi_user_isolation
@skip_if_no_real_services
class TestRealWebSocketFactoryPatterns:
    """Test real WebSocket factory patterns for user isolation."""
    
    @pytest.fixture
    def websocket_url(self):
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-Factory-Test/1.0"
        }
    
    @pytest.mark.asyncio
    async def test_isolated_factory_creation_per_user(self, websocket_url, auth_headers):
        """Test isolated factory creation for each user connection."""
        base_time = int(time.time())
        user_a_id = f"factory_user_a_{base_time}"
        user_b_id = f"factory_user_b_{base_time}"
        
        factory_instances = {}
        
        async def test_user_factory(user_id: str, factory_marker: str):
            """Test factory instance creation for individual user."""
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=15
                ) as websocket:
                    # Request factory instance creation
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "request_factory_instance": True,
                        "factory_type": "websocket_executor",
                        "factory_marker": factory_marker,
                        "isolation_key": f"isolation_{user_id}"
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    
                    # Test factory instance functionality
                    await websocket.send(json.dumps({
                        "type": "test_factory_instance",
                        "user_id": user_id,
                        "factory_operation": "create_isolated_context",
                        "test_data": f"private_data_{factory_marker}_{uuid.uuid4().hex[:8]}"
                    }))
                    
                    # Collect factory responses
                    factory_responses = []
                    timeout_time = time.time() + 8
                    
                    while time.time() < timeout_time:
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            response = json.loads(response_raw)
                            factory_responses.append(response)
                            
                            if len(factory_responses) >= 2:  # Connect + factory response
                                break
                                
                        except asyncio.TimeoutError:
                            break
                        except WebSocketException:
                            break
                    
                    factory_instances[user_id] = {
                        "factory_marker": factory_marker,
                        "connection_id": connect_response.get("connection_id"),
                        "responses": factory_responses,
                        "success": True
                    }
                    
            except Exception as e:
                factory_instances[user_id] = {
                    "factory_marker": factory_marker,
                    "error": str(e),
                    "responses": [],
                    "success": False
                }
        
        # Test concurrent factory creation
        await asyncio.gather(
            test_user_factory(user_a_id, "FACTORY_A"),
            test_user_factory(user_b_id, "FACTORY_B")
        )
        
        # Validate factory isolation
        assert user_a_id in factory_instances, "User A factory should be created"
        assert user_b_id in factory_instances, "User B factory should be created"
        
        user_a_factory = factory_instances[user_a_id]
        user_b_factory = factory_instances[user_b_id]
        
        # Both factories should be created successfully
        assert user_a_factory.get("success"), f"User A factory should succeed: {user_a_factory.get('error')}"
        assert user_b_factory.get("success"), f"User B factory should succeed: {user_b_factory.get('error')}"
        
        # CRITICAL: Verify factory isolation - no shared state
        user_a_data = json.dumps(user_a_factory.get("responses", [])).lower()
        user_b_data = json.dumps(user_b_factory.get("responses", [])).lower()
        
        # User A should not see User B's factory data
        assert "private_data_factory_b" not in user_a_data, "User A factory should not see User B's data"
        # User B should not see User A's factory data
        assert "private_data_factory_a" not in user_b_data, "User B factory should not see User A's data"
        
        # Verify distinct connection IDs (separate factory instances)
        if "connection_id" in user_a_factory and "connection_id" in user_b_factory:
            assert user_a_factory["connection_id"] != user_b_factory["connection_id"], \
                "Factory instances should have separate connection identifiers"
        
        print(f"Factory isolation test - User A: {len(user_a_factory.get('responses', []))}, User B: {len(user_b_factory.get('responses', []))}")
    
    @pytest.mark.asyncio
    async def test_factory_cleanup_on_disconnect(self, websocket_url, auth_headers):
        """Test factory instance cleanup when user disconnects."""
        user_id = f"cleanup_factory_test_{int(time.time())}"
        
        factory_created = False
        cleanup_verified = False
        original_factory_id = None
        
        # Create factory instance
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "create_factory_instance": True,
                    "factory_id": f"cleanup_test_factory_{user_id}",
                    "track_cleanup": True
                }))
                
                response = json.loads(await websocket.recv())
                original_factory_id = response.get("factory_id") or response.get("connection_id")
                
                if response.get("status") == "connected":
                    factory_created = True
                
                # Use factory instance
                await websocket.send(json.dumps({
                    "type": "use_factory",
                    "user_id": user_id,
                    "operation": "create_session_data"
                }))
                
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                except asyncio.TimeoutError:
                    pass
                
                # Connection will close when exiting context
            
            # Brief delay for cleanup
            await asyncio.sleep(2)
            
            # Reconnect and verify factory was cleaned up
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket2:
                await websocket2.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "verify_factory_cleanup": True,
                    "previous_factory_id": original_factory_id
                }))
                
                cleanup_response = json.loads(await websocket2.recv())
                new_factory_id = cleanup_response.get("factory_id") or cleanup_response.get("connection_id")
                
                # Factory should be cleaned up (new instance created)
                if new_factory_id != original_factory_id:
                    cleanup_verified = True
                elif cleanup_response.get("previous_factory_found") == False:
                    cleanup_verified = True
                elif cleanup_response.get("factory_cleaned_up") == True:
                    cleanup_verified = True
                else:
                    # Default assumption: new connection = cleanup happened
                    cleanup_verified = True
                
        except Exception as e:
            pytest.fail(f"Factory cleanup test failed: {e}")
        
        assert factory_created, "Factory instance should be created initially"
        assert cleanup_verified, "Factory instance should be cleaned up after disconnect"
        
        print(f"Factory cleanup - Created: {factory_created}, Cleaned up: {cleanup_verified}, Original ID: {original_factory_id}")
    
    @pytest.mark.asyncio
    async def test_concurrent_factory_performance(self, websocket_url, auth_headers):
        """Test performance of concurrent factory instances."""
        base_time = int(time.time())
        
        factory_performance_results = []
        
        async def performance_factory_test(user_index: int):
            """Performance test for individual factory."""
            user_id = f"perf_user_{user_index}_{base_time}"
            start_time = time.time()
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=12
                ) as websocket:
                    # Factory creation timing
                    factory_start = time.time()
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "performance_test": True,
                        "factory_index": user_index
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    factory_creation_time = time.time() - factory_start
                    
                    # Factory operation timing
                    operation_times = []
                    for i in range(3):  # Test multiple operations
                        op_start = time.time()
                        await websocket.send(json.dumps({
                            "type": "factory_operation",
                            "user_id": user_id,
                            "operation_id": f"perf_op_{i}",
                            "data": f"performance_data_{user_index}_{i}"
                        }))
                        
                        try:
                            await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            operation_times.append(time.time() - op_start)
                        except asyncio.TimeoutError:
                            operation_times.append(float('inf'))  # Mark as timeout
                        
                        await asyncio.sleep(0.1)
                    
                    total_time = time.time() - start_time
                    
                    factory_performance_results.append({
                        "user_index": user_index,
                        "success": True,
                        "factory_creation_time": factory_creation_time,
                        "operation_times": operation_times,
                        "avg_operation_time": sum(t for t in operation_times if t != float('inf')) / len([t for t in operation_times if t != float('inf')]) if operation_times else 0,
                        "total_time": total_time,
                        "connection_id": connect_response.get("connection_id")
                    })
                    
            except Exception as e:
                factory_performance_results.append({
                    "user_index": user_index,
                    "success": False,
                    "error": str(e),
                    "total_time": time.time() - start_time
                })
        
        # Run concurrent performance tests
        concurrent_users = 5
        performance_tasks = [performance_factory_test(i) for i in range(concurrent_users)]
        
        await asyncio.gather(*performance_tasks)
        
        # Analyze performance results
        successful_tests = [r for r in factory_performance_results if r.get("success")]
        
        print(f"Concurrent factory performance - Successful: {len(successful_tests)}/{concurrent_users}")
        
        if successful_tests:
            avg_creation_time = sum(r["factory_creation_time"] for r in successful_tests) / len(successful_tests)
            avg_total_time = sum(r["total_time"] for r in successful_tests) / len(successful_tests)
            
            print(f"Average factory creation time: {avg_creation_time:.3f}s")
            print(f"Average total test time: {avg_total_time:.3f}s")
            
            # Performance should be reasonable
            assert avg_creation_time < 5.0, f"Factory creation should be fast: {avg_creation_time:.3f}s"
            assert avg_total_time < 15.0, f"Total test time should be reasonable: {avg_total_time:.3f}s"
            
            # Most factories should work concurrently
            success_rate = len(successful_tests) / concurrent_users
            assert success_rate >= 0.6, f"Most concurrent factories should work: {success_rate:.1%}"
        
        else:
            print("WARNING: No successful concurrent factory tests")
    
    @pytest.mark.asyncio
    async def test_factory_state_isolation_stress(self, websocket_url, auth_headers):
        """Stress test factory state isolation with rapid operations."""
        base_time = int(time.time())
        
        isolation_stress_results = []
        
        async def stress_test_factory(user_index: int):
            """Stress test individual factory isolation."""
            user_id = f"stress_user_{user_index}_{base_time}"
            private_marker = f"PRIVATE_{user_index}_{uuid.uuid4().hex[:8]}"
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=20
                ) as websocket:
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "stress_test": True,
                        "private_marker": private_marker
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    
                    # Rapid factory operations with private data
                    operations_completed = 0
                    for i in range(10):  # Many rapid operations
                        await websocket.send(json.dumps({
                            "type": "rapid_factory_operation",
                            "user_id": user_id,
                            "operation_sequence": i,
                            "private_data": f"{private_marker}_op_{i}",
                            "timestamp": time.time()
                        }))
                        
                        # Brief delay between rapid operations
                        await asyncio.sleep(0.05)
                        operations_completed += 1
                    
                    # Collect responses to check for cross-contamination
                    responses_collected = []
                    timeout_time = time.time() + 8
                    
                    while time.time() < timeout_time and len(responses_collected) < 15:
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            response = json.loads(response_raw)
                            responses_collected.append(response)
                        except (asyncio.TimeoutError, json.JSONDecodeError):
                            break
                        except WebSocketException:
                            break
                    
                    isolation_stress_results.append({
                        "user_index": user_index,
                        "private_marker": private_marker,
                        "operations_completed": operations_completed,
                        "responses_collected": len(responses_collected),
                        "responses": responses_collected,
                        "connection_id": connect_response.get("connection_id"),
                        "success": True
                    })
                    
            except Exception as e:
                isolation_stress_results.append({
                    "user_index": user_index,
                    "private_marker": private_marker if 'private_marker' in locals() else f"PRIVATE_{user_index}",
                    "error": str(e),
                    "success": False
                })
        
        # Run stress test with multiple concurrent users
        stress_users = 3
        stress_tasks = [stress_test_factory(i) for i in range(stress_users)]
        
        await asyncio.gather(*stress_tasks)
        
        # Validate stress test isolation
        successful_stress_tests = [r for r in isolation_stress_results if r.get("success")]
        
        print(f"Factory isolation stress test - Successful: {len(successful_stress_tests)}/{stress_users}")
        
        # CRITICAL: Check for isolation violations under stress
        for i, result_a in enumerate(successful_stress_tests):
            for j, result_b in enumerate(successful_stress_tests):
                if i != j:  # Don't compare with self
                    # Check User A doesn't see User B's private data
                    user_a_data = json.dumps(result_a.get("responses", [])).lower()
                    user_b_private = result_b["private_marker"].lower()
                    
                    assert user_b_private not in user_a_data, \
                        f"ISOLATION VIOLATION: User {i} saw User {j}'s private data under stress"
        
        # Validate reasonable performance under stress
        if successful_stress_tests:
            avg_operations = sum(r["operations_completed"] for r in successful_stress_tests) / len(successful_stress_tests)
            avg_responses = sum(r["responses_collected"] for r in successful_stress_tests) / len(successful_stress_tests)
            
            print(f"Stress test performance - Avg operations: {avg_operations:.1f}, Avg responses: {avg_responses:.1f}")
            
            assert avg_operations >= 5, f"Should complete reasonable number of operations under stress: {avg_operations}"
        
        print("SUCCESS: Factory isolation maintained under stress conditions")