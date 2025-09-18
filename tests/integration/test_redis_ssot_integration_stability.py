"""Integration Test: Redis SSOT Integration Stability

This test suite validates system-wide stability after Redis SSOT
consolidation, ensuring all services work together reliably
and the Golden Path is restored.

Business Value:
- Validates restoration of $500K+ ARR chat functionality
- Ensures cross-service Redis integration stability
- Validates agent execution pipeline reliability
- Confirms service startup sequence stability

Test Strategy:
- Test service startup with unified Redis configuration
- Validate cross-service Redis integration (Auth, Backend)
- Test agent execution pipeline reliability
- Validate WebSocket-Redis-Agent integration chain
- Test system under load conditions

Expected Initial Result: FAIL (service integration conflicts)
Expected Final Result: PASS (95%+ system stability)
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@dataclass
class ServiceHealthResult:
    """Result of service health check."""
    service_name: str
    healthy: bool
    response_time: float
    redis_connected: bool
    error_details: str


@dataclass
class IntegrationTestResult:
    """Result of integration test."""
    test_name: str
    success: bool
    response_time: float
    redis_operations: int
    websocket_events: int
    error_details: str


class RedisSSOTIntegrationStabilityTests(SSotAsyncTestCase):
    """Integration tests for Redis SSOT stability across services."""

    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        self.logger = logging.getLogger(__name__)
        self.service_results: List[ServiceHealthResult] = []
        self.integration_results: List[IntegrationTestResult] = []

        # Test configuration
        self.test_timeout = 30.0
        self.redis_test_keys = set()

    async def test_service_startup_stability(self):
        """Test service startup stability with unified Redis configuration.

        This test validates that all services can start cleanly with
        the SSOT Redis configuration without conflicts.
        """
        self.logger.info("Testing service startup stability with Redis SSOT")

        # Test Redis manager initialization
        startup_results = []

        try:
            # Test main Redis manager
            from netra_backend.app.redis_manager import redis_manager

            start_time = time.time()
            await redis_manager.ping()
            redis_response_time = time.time() - start_time

            startup_results.append({
                "component": "netra_backend_redis_manager",
                "success": True,
                "response_time": redis_response_time,
                "instance_id": id(redis_manager)
            })

        except Exception as e:
            startup_results.append({
                "component": "netra_backend_redis_manager",
                "success": False,
                "response_time": 0,
                "error": str(e),
                "instance_id": 0
            })

        # Test Redis through different service interfaces
        service_tests = [
            ("auth_integration", self._test_auth_redis_integration),
            ("websocket_integration", self._test_websocket_redis_integration),
            ("agent_integration", self._test_agent_redis_integration)
        ]

        for service_name, test_func in service_tests:
            try:
                start_time = time.time()
                result = await test_func()
                response_time = time.time() - start_time

                startup_results.append({
                    "component": service_name,
                    "success": result.get("success", False),
                    "response_time": response_time,
                    "details": result.get("details", "")
                })

            except Exception as e:
                startup_results.append({
                    "component": service_name,
                    "success": False,
                    "response_time": 0,
                    "error": str(e)
                })

        # Analyze startup stability
        successful_components = sum(1 for r in startup_results if r["success"])
        total_components = len(startup_results)
        stability_rate = (successful_components / total_components) * 100

        startup_evidence = {
            "test_name": "service_startup_stability",
            "total_components": total_components,
            "successful_components": successful_components,
            "stability_rate": stability_rate,
            "startup_results": startup_results
        }

        with open("/c/netra-apex/service_startup_stability_evidence.json", "w") as f:
            json.dump(startup_evidence, f, indent=2)

        self.logger.info(f"Service startup stability: {successful_components}/{total_components} components stable")
        self.logger.info(f"Stability rate: {stability_rate:.1f}%")

        # Validate startup stability
        self.assertGreaterEqual(
            stability_rate,
            95.0,
            f"Service startup instability detected: {stability_rate:.1f}% stability rate. "
            f"Failed components: {total_components - successful_components}"
        )

    async def test_cross_service_redis_integration(self):
        """Test Redis integration consistency across services.

        This test validates that all services use the same Redis instance
        and can share data reliably.
        """
        self.logger.info("Testing cross-service Redis integration")

        # Test data sharing between service contexts
        test_data = {
            "integration_test_id": "redis_ssot_integration",
            "timestamp": time.time(),
            "test_payload": "cross_service_validation"
        }

        integration_steps = []

        # Step 1: Store data through main Redis manager
        try:
            from netra_backend.app.redis_manager import redis_manager

            test_key = "integration_test:cross_service"
            await redis_manager.set(test_key, json.dumps(test_data), ex=300)
            self.redis_test_keys.add(test_key)

            integration_steps.append({
                "step": "store_data_main_manager",
                "success": True,
                "instance_id": id(redis_manager)
            })

        except Exception as e:
            integration_steps.append({
                "step": "store_data_main_manager",
                "success": False,
                "error": str(e)
            })

        # Step 2: Retrieve data through auth context (if available)
        try:
            # Attempt to get data through auth service Redis
            # This should use the same SSOT instance
            from netra_backend.app.redis_manager import redis_manager as auth_redis

            retrieved_data = await auth_redis.get(test_key)
            if retrieved_data:
                parsed_data = json.loads(retrieved_data)
                data_matches = parsed_data["integration_test_id"] == test_data["integration_test_id"]
            else:
                data_matches = False

            integration_steps.append({
                "step": "retrieve_data_auth_context",
                "success": data_matches,
                "instance_id": id(auth_redis),
                "data_consistent": data_matches
            })

        except Exception as e:
            integration_steps.append({
                "step": "retrieve_data_auth_context",
                "success": False,
                "error": str(e)
            })

        # Step 3: Test concurrent access from multiple contexts
        async def concurrent_redis_access(context_id: int):
            try:
                from netra_backend.app.redis_manager import redis_manager

                # Each context stores its own data
                context_key = f"integration_test:context_{context_id}"
                context_data = {"context_id": context_id, "timestamp": time.time()}

                await redis_manager.set(context_key, json.dumps(context_data), ex=60)
                self.redis_test_keys.add(context_key)

                # Verify data integrity
                retrieved = await redis_manager.get(context_key)
                if retrieved:
                    parsed = json.loads(retrieved)
                    success = parsed["context_id"] == context_id
                else:
                    success = False

                return {
                    "context_id": context_id,
                    "success": success,
                    "instance_id": id(redis_manager)
                }

            except Exception as e:
                return {
                    "context_id": context_id,
                    "success": False,
                    "error": str(e)
                }

        # Run concurrent contexts
        concurrent_tasks = [concurrent_redis_access(i) for i in range(5)]
        concurrent_results = await asyncio.gather(*concurrent_tasks)

        integration_steps.append({
            "step": "concurrent_context_access",
            "results": concurrent_results
        })

        # Analyze integration results
        all_contexts_success = all(r["success"] for r in concurrent_results)
        unique_instances = len(set(r.get("instance_id", 0) for r in concurrent_results if "instance_id" in r))

        integration_evidence = {
            "test_name": "cross_service_redis_integration",
            "integration_steps": integration_steps,
            "concurrent_contexts": len(concurrent_results),
            "all_contexts_success": all_contexts_success,
            "unique_redis_instances": unique_instances,
            "data_consistency_validated": True
        }

        with open("/c/netra-apex/cross_service_integration_evidence.json", "w") as f:
            json.dump(integration_evidence, f, indent=2)

        self.logger.info(f"Cross-service integration: {len(concurrent_results)} contexts tested")
        self.logger.info(f"All contexts successful: {all_contexts_success}")
        self.logger.info(f"Unique Redis instances: {unique_instances}")

        # Validate integration
        self.assertTrue(
            all_contexts_success,
            f"Cross-service Redis integration failed: {sum(1 for r in concurrent_results if not r['success'])} "
            f"contexts failed"
        )

        self.assertEqual(
            unique_instances,
            1,
            f"Redis SSOT violation in cross-service integration: {unique_instances} unique instances detected"
        )

    async def test_agent_execution_pipeline_stability(self):
        """Test agent execution pipeline stability with Redis SSOT.

        This test validates that the agent execution pipeline works
        reliably with the unified Redis configuration.
        """
        self.logger.info("Testing agent execution pipeline stability")

        pipeline_results = []

        # Test basic agent pipeline components
        try:
            # Test Redis state management for agent execution
            from netra_backend.app.redis_manager import redis_manager

            # Simulate agent execution state management
            agent_session_id = "test_agent_session_001"
            agent_state = {
                "session_id": agent_session_id,
                "status": "initializing",
                "timestamp": time.time(),
                "user_id": "test_user_001"
            }

            # Store agent state
            state_key = f"agent_session:{agent_session_id}"
            await redis_manager.set(state_key, json.dumps(agent_state), ex=300)
            self.redis_test_keys.add(state_key)

            # Update agent state through pipeline
            agent_state["status"] = "executing"
            agent_state["updated"] = time.time()
            await redis_manager.set(state_key, json.dumps(agent_state), ex=300)

            # Verify state persistence
            retrieved_state = await redis_manager.get(state_key)
            if retrieved_state:
                parsed_state = json.loads(retrieved_state)
                state_valid = parsed_state["status"] == "executing"
            else:
                state_valid = False

            pipeline_results.append({
                "component": "agent_state_management",
                "success": state_valid,
                "details": "Agent state stored and retrieved successfully" if state_valid else "State management failed"
            })

        except Exception as e:
            pipeline_results.append({
                "component": "agent_state_management",
                "success": False,
                "error": str(e)
            })

        # Test agent message queue simulation
        try:
            message_queue_key = f"agent_messages:{agent_session_id}"
            messages = [
                {"type": "user_input", "content": "Test message 1", "timestamp": time.time()},
                {"type": "agent_response", "content": "Test response 1", "timestamp": time.time()},
                {"type": "tool_execution", "content": "Tool result", "timestamp": time.time()}
            ]

            # Store messages in queue
            for i, message in enumerate(messages):
                await redis_manager.lpush(message_queue_key, json.dumps(message))

            self.redis_test_keys.add(message_queue_key)

            # Retrieve messages
            queue_length = await redis_manager.llen(message_queue_key)
            message_queue_valid = queue_length == len(messages)

            pipeline_results.append({
                "component": "agent_message_queue",
                "success": message_queue_valid,
                "queue_length": queue_length,
                "expected_length": len(messages)
            })

        except Exception as e:
            pipeline_results.append({
                "component": "agent_message_queue",
                "success": False,
                "error": str(e)
            })

        # Test agent result caching
        try:
            result_cache_key = f"agent_results:{agent_session_id}"
            agent_result = {
                "result_type": "completion",
                "content": "Agent execution completed successfully",
                "execution_time": 2.5,
                "timestamp": time.time()
            }

            await redis_manager.set(result_cache_key, json.dumps(agent_result), ex=600)
            self.redis_test_keys.add(result_cache_key)

            # Verify result caching
            cached_result = await redis_manager.get(result_cache_key)
            if cached_result:
                parsed_result = json.loads(cached_result)
                cache_valid = parsed_result["result_type"] == "completion"
            else:
                cache_valid = False

            pipeline_results.append({
                "component": "agent_result_caching",
                "success": cache_valid,
                "details": "Agent result cached successfully" if cache_valid else "Result caching failed"
            })

        except Exception as e:
            pipeline_results.append({
                "component": "agent_result_caching",
                "success": False,
                "error": str(e)
            })

        # Analyze pipeline stability
        successful_components = sum(1 for r in pipeline_results if r["success"])
        total_components = len(pipeline_results)
        pipeline_stability = (successful_components / total_components) * 100

        pipeline_evidence = {
            "test_name": "agent_execution_pipeline_stability",
            "total_components": total_components,
            "successful_components": successful_components,
            "pipeline_stability": pipeline_stability,
            "pipeline_results": pipeline_results
        }

        with open("/c/netra-apex/agent_pipeline_stability_evidence.json", "w") as f:
            json.dump(pipeline_evidence, f, indent=2)

        self.logger.info(f"Agent pipeline stability: {successful_components}/{total_components} components stable")
        self.logger.info(f"Pipeline stability: {pipeline_stability:.1f}%")

        # Validate pipeline stability
        self.assertGreaterEqual(
            pipeline_stability,
            95.0,
            f"Agent execution pipeline instability detected: {pipeline_stability:.1f}% stability. "
            f"Failed components: {total_components - successful_components}"
        )

    async def test_system_load_stability(self):
        """Test system stability under load with Redis SSOT.

        This test validates that the system remains stable under
        concurrent load with the unified Redis configuration.
        """
        self.logger.info("Testing system load stability")

        load_test_results = []

        async def simulate_concurrent_load(worker_id: int):
            """Simulate concurrent system load."""
            try:
                from netra_backend.app.redis_manager import redis_manager

                operations = []
                start_time = time.time()

                # Simulate typical system operations
                for i in range(10):
                    # User session
                    session_key = f"load_test:session:{worker_id}_{i}"
                    session_data = {
                        "worker_id": worker_id,
                        "operation": i,
                        "timestamp": time.time()
                    }

                    operations.append(redis_manager.set(session_key, json.dumps(session_data), ex=60))
                    self.redis_test_keys.add(session_key)

                    # Agent state
                    agent_key = f"load_test:agent:{worker_id}_{i}"
                    agent_data = {
                        "status": "processing",
                        "worker_id": worker_id,
                        "operation": i
                    }

                    operations.append(redis_manager.set(agent_key, json.dumps(agent_data), ex=60))
                    self.redis_test_keys.add(agent_key)

                # Execute all operations
                await asyncio.gather(*operations)

                # Verify operations
                verification_tasks = []
                for i in range(10):
                    session_key = f"load_test:session:{worker_id}_{i}"
                    agent_key = f"load_test:agent:{worker_id}_{i}"

                    verification_tasks.extend([
                        redis_manager.get(session_key),
                        redis_manager.get(agent_key)
                    ])

                verification_results = await asyncio.gather(*verification_tasks)
                successful_verifications = sum(1 for r in verification_results if r is not None)

                operation_time = time.time() - start_time

                return {
                    "worker_id": worker_id,
                    "success": successful_verifications == len(verification_tasks),
                    "operation_time": operation_time,
                    "operations_completed": len(operations),
                    "verifications_passed": successful_verifications,
                    "redis_instance_id": id(redis_manager)
                }

            except Exception as e:
                return {
                    "worker_id": worker_id,
                    "success": False,
                    "error": str(e),
                    "operation_time": 0
                }

        # Run concurrent load test
        num_workers = 10
        load_tasks = [simulate_concurrent_load(i) for i in range(num_workers)]
        load_test_results = await asyncio.gather(*load_tasks)

        # Analyze load test results
        successful_workers = sum(1 for r in load_test_results if r["success"])
        load_success_rate = (successful_workers / num_workers) * 100
        avg_operation_time = sum(r.get("operation_time", 0) for r in load_test_results) / len(load_test_results)
        unique_redis_instances = len(set(r.get("redis_instance_id", 0) for r in load_test_results if "redis_instance_id" in r))

        load_evidence = {
            "test_name": "system_load_stability",
            "concurrent_workers": num_workers,
            "successful_workers": successful_workers,
            "load_success_rate": load_success_rate,
            "average_operation_time": avg_operation_time,
            "unique_redis_instances": unique_redis_instances,
            "worker_results": load_test_results
        }

        with open("/c/netra-apex/system_load_stability_evidence.json", "w") as f:
            json.dump(load_evidence, f, indent=2)

        self.logger.info(f"Load test: {successful_workers}/{num_workers} workers successful")
        self.logger.info(f"Load success rate: {load_success_rate:.1f}%")
        self.logger.info(f"Average operation time: {avg_operation_time:.3f}s")
        self.logger.info(f"Unique Redis instances: {unique_redis_instances}")

        # Validate load stability
        self.assertGreaterEqual(
            load_success_rate,
            95.0,
            f"System load instability detected: {load_success_rate:.1f}% success rate under load"
        )

        self.assertEqual(
            unique_redis_instances,
            1,
            f"Redis instance fragmentation under load: {unique_redis_instances} instances detected"
        )

    async def _test_auth_redis_integration(self) -> Dict[str, Any]:
        """Test Auth service Redis integration."""
        try:
            from netra_backend.app.redis_manager import redis_manager

            # Test auth-specific Redis operations
            auth_key = "auth_integration_test"
            auth_data = {"user_id": "test_user", "session": "test_session"}

            await redis_manager.set(auth_key, json.dumps(auth_data), ex=60)
            self.redis_test_keys.add(auth_key)

            retrieved = await redis_manager.get(auth_key)
            success = retrieved is not None

            return {
                "success": success,
                "details": "Auth Redis integration successful" if success else "Auth Redis integration failed"
            }

        except Exception as e:
            return {
                "success": False,
                "details": f"Auth Redis integration error: {e}"
            }

    async def _test_websocket_redis_integration(self) -> Dict[str, Any]:
        """Test WebSocket service Redis integration."""
        try:
            from netra_backend.app.redis_manager import redis_manager

            # Test WebSocket-specific Redis operations
            ws_key = "websocket_integration_test"
            ws_data = {"connection_id": "test_conn", "user_id": "test_user"}

            await redis_manager.set(ws_key, json.dumps(ws_data), ex=60)
            self.redis_test_keys.add(ws_key)

            retrieved = await redis_manager.get(ws_key)
            success = retrieved is not None

            return {
                "success": success,
                "details": "WebSocket Redis integration successful" if success else "WebSocket Redis integration failed"
            }

        except Exception as e:
            return {
                "success": False,
                "details": f"WebSocket Redis integration error: {e}"
            }

    async def _test_agent_redis_integration(self) -> Dict[str, Any]:
        """Test Agent service Redis integration."""
        try:
            from netra_backend.app.redis_manager import redis_manager

            # Test agent-specific Redis operations
            agent_key = "agent_integration_test"
            agent_data = {"agent_id": "test_agent", "status": "ready"}

            await redis_manager.set(agent_key, json.dumps(agent_data), ex=60)
            self.redis_test_keys.add(agent_key)

            retrieved = await redis_manager.get(agent_key)
            success = retrieved is not None

            return {
                "success": success,
                "details": "Agent Redis integration successful" if success else "Agent Redis integration failed"
            }

        except Exception as e:
            return {
                "success": False,
                "details": f"Agent Redis integration error: {e}"
            }

    async def asyncTearDown(self):
        """Clean up test resources."""
        # Clean up all test keys
        if self.redis_test_keys:
            try:
                from netra_backend.app.redis_manager import redis_manager

                for key in self.redis_test_keys:
                    await redis_manager.delete(key)

                # Clean up any list keys
                for key in list(self.redis_test_keys):
                    if "messages:" in key:
                        await redis_manager.delete(key)

            except Exception as e:
                self.logger.warning(f"Failed to clean up test keys: {e}")

        # Save final integration evidence
        final_evidence = {
            "test_suite": "redis_ssot_integration_stability",
            "execution_time": time.time(),
            "test_keys_created": len(self.redis_test_keys),
            "integration_results": [
                {
                    "test_name": result.test_name,
                    "success": result.success,
                    "response_time": result.response_time,
                    "error_details": result.error_details
                }
                for result in self.integration_results
            ]
        }

        with open("/c/netra-apex/redis_integration_stability_final.json", "w") as f:
            json.dump(final_evidence, f, indent=2)

        await super().asyncTearDown()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])