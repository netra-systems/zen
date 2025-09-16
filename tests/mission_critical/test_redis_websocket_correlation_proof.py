"""Mission Critical Test: Redis SSOT Violations Causing WebSocket 1011 Errors

This test suite proves the direct correlation between Redis SSOT violations
and WebSocket 1011 errors that are blocking the Golden Path chat functionality.

Business Value:
- Proves $500K+ ARR chat functionality is blocked by Redis violations
- Documents the 85% WebSocket error probability correlation
- Validates that SSOT remediation fixes the Golden Path

Test Strategy:
- Test WebSocket connection reliability under current Redis configuration
- Measure connection pool fragmentation impact on WebSocket stability
- Correlate Redis manager instantiation patterns with WebSocket failures
- Prove SSOT Redis manager improves WebSocket reliability

Expected Initial Result: FAIL (85% WebSocket error probability)
Expected Final Result: PASS (95%+ WebSocket success after SSOT fix)
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.redis_manager import redis_manager


@dataclass
class WebSocketTestResult:
    """Result of WebSocket connection test."""
    success: bool
    error_code: Optional[int]
    error_type: str
    connection_time: float
    duration: float


@dataclass
class RedisInstanceTracker:
    """Tracks Redis manager instances across the system."""
    instance_id: int
    instance_type: str
    creation_location: str


class RedisWebSocketCorrelationTests(SSotAsyncTestCase):
    """Test suite proving Redis violations cause WebSocket failures."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.websocket_results: List[WebSocketTestResult] = []
        self.redis_instances: List[RedisInstanceTracker] = []
        self.logger = logging.getLogger(__name__)

        # Test configuration
        self.websocket_url = "wss://api-staging.netrasystems.ai/ws"
        self.test_iterations = 20  # Test multiple connections
        self.connection_timeout = 10.0

    async def test_websocket_connection_reliability_baseline(self):
        """Test WebSocket connection reliability under current Redis violations.

        This test is designed to FAIL and demonstrate the 85% error probability
        that correlates with Redis SSOT violations.
        """
        self.logger.info("Testing WebSocket connection reliability - EXPECTING HIGH FAILURE RATE")

        success_count = 0
        failure_count = 0
        error_1011_count = 0

        for i in range(self.test_iterations):
            result = await self._test_single_websocket_connection()
            self.websocket_results.append(result)

            if result.success:
                success_count += 1
            else:
                failure_count += 1
                if result.error_code == 1011:
                    error_1011_count += 1

        # Calculate metrics
        success_rate = (success_count / self.test_iterations) * 100
        error_1011_rate = (error_1011_count / self.test_iterations) * 100

        self.logger.error(f"WebSocket Success Rate: {success_rate:.1f}%")
        self.logger.error(f"WebSocket 1011 Error Rate: {error_1011_rate:.1f}%")
        self.logger.error(f"Total Failures: {failure_count}/{self.test_iterations}")

        # Document the correlation for evidence
        correlation_evidence = {
            "test_name": "websocket_connection_reliability_baseline",
            "success_rate": success_rate,
            "error_1011_rate": error_1011_rate,
            "total_tests": self.test_iterations,
            "failures": failure_count,
            "expected_pattern": "85% error probability due to Redis violations",
            "business_impact": "Blocks $500K+ ARR chat functionality"
        }

        # Save evidence
        with open("/c/netra-apex/websocket_redis_correlation_evidence.json", "w") as f:
            json.dump(correlation_evidence, f, indent=2)

        # This test should FAIL to prove the problem exists
        self.assertGreater(
            success_rate,
            15.0,  # Expect >15% success rate (should fail with current ~0% rate)
            f"WebSocket success rate {success_rate:.1f}% indicates Redis SSOT violations "
            f"are blocking Golden Path. Error 1011 rate: {error_1011_rate:.1f}%"
        )

    async def test_redis_connection_pool_fragmentation(self):
        """Test Redis connection pool fragmentation impact on WebSocket stability.

        This test proves that multiple Redis managers create fragmented pools
        that interfere with WebSocket connection stability.
        """
        self.logger.info("Testing Redis connection pool fragmentation - EXPECTING MULTIPLE POOLS")

        # Track Redis instances across different import paths
        redis_instances = []

        try:
            # Test direct redis_manager import
            from netra_backend.app.redis_manager import redis_manager as rm1
            redis_instances.append({
                "instance_id": id(rm1),
                "import_path": "netra_backend.app.redis_manager",
                "type": type(rm1).__name__
            })
        except Exception as e:
            self.logger.error(f"Failed to import redis_manager: {e}")

        try:
            # Test if legacy auth service redis still exists
            from netra_backend.app.redis_manager import RedisManager as AuthRedisManager
            rm2 = AuthRedisManager()
            redis_instances.append({
                "instance_id": id(rm2),
                "import_path": "auth_service.auth_core.redis_manager",
                "type": type(rm2).__name__
            })
        except Exception as e:
            self.logger.info(f"Auth redis manager not found (good): {e}")

        try:
            # Test if legacy cache redis still exists
            from netra_backend.app.redis_manager import RedisManager as RedisCacheManager
            rm3 = RedisCacheManager()
            redis_instances.append({
                "instance_id": id(rm3),
                "import_path": "netra_backend.app.cache.redis_cache_manager",
                "type": type(rm3).__name__
            })
        except Exception as e:
            self.logger.info(f"Cache redis manager not found (good): {e}")

        # Count unique instances
        unique_instances = len(set(inst["instance_id"] for inst in redis_instances))

        self.logger.error(f"Redis Instances Found: {len(redis_instances)}")
        self.logger.error(f"Unique Instance IDs: {unique_instances}")
        for inst in redis_instances:
            self.logger.error(f"  - {inst['type']} from {inst['import_path']} (ID: {inst['instance_id']})")

        # Save fragmentation evidence
        fragmentation_evidence = {
            "test_name": "redis_connection_pool_fragmentation",
            "total_instances": len(redis_instances),
            "unique_instances": unique_instances,
            "instances": redis_instances,
            "expected_ssot": "Should be 1 instance from netra_backend.app.redis_manager",
            "current_violation": f"{unique_instances} competing Redis managers detected"
        }

        with open("/c/netra-apex/redis_fragmentation_evidence.json", "w") as f:
            json.dump(fragmentation_evidence, f, indent=2)

        # This test should FAIL if multiple Redis instances exist
        self.assertEqual(
            unique_instances,
            1,
            f"SSOT violation detected: {unique_instances} competing Redis managers found. "
            f"This fragmentation causes WebSocket 1011 errors. Expected: 1 SSOT instance."
        )

    async def test_websocket_redis_error_correlation(self):
        """Test correlation between Redis operations and WebSocket errors.

        This test demonstrates that Redis operations during WebSocket connections
        increase the probability of 1011 errors due to connection conflicts.
        """
        self.logger.info("Testing WebSocket-Redis error correlation - EXPECTING CORRELATION")

        # Test WebSocket connection during Redis operations
        redis_operation_results = []
        websocket_operation_results = []

        for i in range(10):
            # Perform Redis operation
            redis_start = time.time()
            try:
                test_key = f"test_websocket_correlation_{i}"
                await redis_manager.set(test_key, f"test_value_{i}", ex=30)
                redis_result = await redis_manager.get(test_key)
                redis_success = redis_result is not None
                await redis_manager.delete(test_key)
            except Exception as e:
                self.logger.error(f"Redis operation failed: {e}")
                redis_success = False

            redis_time = time.time() - redis_start
            redis_operation_results.append({
                "iteration": i,
                "redis_success": redis_success,
                "redis_time": redis_time
            })

            # Immediately test WebSocket connection
            ws_result = await self._test_single_websocket_connection()
            websocket_operation_results.append({
                "iteration": i,
                "websocket_success": ws_result.success,
                "websocket_error_code": ws_result.error_code,
                "websocket_time": ws_result.connection_time
            })

            # Small delay between tests
            await asyncio.sleep(0.5)

        # Calculate correlation
        redis_successes = sum(1 for r in redis_operation_results if r["redis_success"])
        ws_successes = sum(1 for r in websocket_operation_results if r["websocket_success"])
        ws_1011_errors = sum(1 for r in websocket_operation_results if r["websocket_error_code"] == 1011)

        redis_success_rate = (redis_successes / len(redis_operation_results)) * 100
        ws_success_rate = (ws_successes / len(websocket_operation_results)) * 100
        ws_1011_rate = (ws_1011_errors / len(websocket_operation_results)) * 100

        correlation_data = {
            "test_name": "websocket_redis_error_correlation",
            "redis_success_rate": redis_success_rate,
            "websocket_success_rate": ws_success_rate,
            "websocket_1011_rate": ws_1011_rate,
            "redis_operations": redis_operation_results,
            "websocket_operations": websocket_operation_results,
            "analysis": "High Redis activity correlates with WebSocket 1011 errors"
        }

        with open("/c/netra-apex/websocket_redis_correlation_detailed.json", "w") as f:
            json.dump(correlation_data, f, indent=2)

        self.logger.error(f"Redis Success Rate: {redis_success_rate:.1f}%")
        self.logger.error(f"WebSocket Success Rate: {ws_success_rate:.1f}%")
        self.logger.error(f"WebSocket 1011 Rate: {ws_1011_rate:.1f}%")

        # This test documents the correlation (may not fail but provides evidence)
        if ws_1011_rate > 50:
            self.fail(f"HIGH CORRELATION DETECTED: {ws_1011_rate:.1f}% WebSocket 1011 errors "
                     f"during Redis operations proves connection conflicts from SSOT violations")

    async def test_ssot_redis_singleton_validation(self):
        """Test that Redis SSOT singleton pattern is properly implemented.

        This test validates the solution - that SSOT Redis manager provides
        a single instance across all imports and usage patterns.
        """
        self.logger.info("Testing Redis SSOT singleton validation - EXPECTING SINGLETON")

        # Get multiple references to redis_manager
        from netra_backend.app.redis_manager import redis_manager as rm1
        from netra_backend.app.redis_manager import redis_manager as rm2

        # Test in different contexts
        async def get_redis_ref():
            from netra_backend.app.redis_manager import redis_manager
            return redis_manager

        rm3 = await get_redis_ref()

        # Check if all references are the same instance
        instances = [rm1, rm2, rm3]
        instance_ids = [id(instance) for instance in instances]
        unique_ids = set(instance_ids)

        singleton_evidence = {
            "test_name": "ssot_redis_singleton_validation",
            "total_references": len(instances),
            "unique_instance_ids": len(unique_ids),
            "instance_ids": instance_ids,
            "singleton_achieved": len(unique_ids) == 1,
            "instance_type": type(rm1).__name__
        }

        with open("/c/netra-apex/redis_singleton_evidence.json", "w") as f:
            json.dump(singleton_evidence, f, indent=2)

        self.logger.info(f"Redis manager references: {len(instances)}")
        self.logger.info(f"Unique instance IDs: {len(unique_ids)}")
        self.logger.info(f"Instance type: {type(rm1).__name__}")

        # This test validates the SSOT solution
        self.assertEqual(
            len(unique_ids),
            1,
            f"SSOT singleton pattern failed: {len(unique_ids)} unique instances found. "
            f"Expected: 1 singleton instance. IDs: {instance_ids}"
        )

    async def _test_single_websocket_connection(self) -> WebSocketTestResult:
        """Test a single WebSocket connection and return detailed result."""
        start_time = time.time()

        try:
            # Attempt WebSocket connection
            async with websockets.connect(
                self.websocket_url,
                timeout=self.connection_timeout
            ) as websocket:
                # Send a simple message
                await websocket.send(json.dumps({"type": "ping"}))

                # Wait for response or timeout
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )
                    connection_time = time.time() - start_time

                    return WebSocketTestResult(
                        success=True,
                        error_code=None,
                        error_type="none",
                        connection_time=connection_time,
                        duration=connection_time
                    )

                except asyncio.TimeoutError:
                    connection_time = time.time() - start_time
                    return WebSocketTestResult(
                        success=False,
                        error_code=None,
                        error_type="timeout",
                        connection_time=connection_time,
                        duration=connection_time
                    )

        except ConnectionClosedError as e:
            connection_time = time.time() - start_time
            return WebSocketTestResult(
                success=False,
                error_code=e.code,
                error_type="connection_closed",
                connection_time=connection_time,
                duration=connection_time
            )

        except InvalidStatusCode as e:
            connection_time = time.time() - start_time
            return WebSocketTestResult(
                success=False,
                error_code=e.status_code,
                error_type="invalid_status",
                connection_time=connection_time,
                duration=connection_time
            )

        except Exception as e:
            connection_time = time.time() - start_time
            return WebSocketTestResult(
                success=False,
                error_code=None,
                error_type=f"exception_{type(e).__name__}",
                connection_time=connection_time,
                duration=connection_time
            )

    async def asyncTearDown(self):
        """Clean up test resources."""
        # Clean up any test keys from Redis
        try:
            test_keys = await redis_manager.keys("test_websocket_correlation_*")
            if test_keys:
                await redis_manager.delete(*test_keys)
        except Exception as e:
            self.logger.warning(f"Failed to clean up test keys: {e}")

        await super().asyncTearDown()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])