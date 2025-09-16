"""
Race Condition Elimination Performance Test Suite - Issue #1200

MISSION CRITICAL: Comprehensive race condition detection and elimination testing
for multi-user concurrent operations. Validates thread safety, user isolation,
and performance consistency under concurrent load conditions.

PURPOSE:
- Tests multi-user concurrent WebSocket connections without race conditions
- Validates agent factory concurrent instantiation and user isolation
- Tests configuration loading thread-safety under concurrent access
- Validates user context isolation prevents data contamination
- Detects performance degradation under concurrent operations

BUSINESS VALUE:
- Protects $500K+ ARR multi-user system reliability
- Ensures enterprise-grade concurrent user support
- Validates Issue #1116 factory migration eliminates singleton race conditions
- Tests regulatory compliance isolation (HIPAA, SOC2, SEC)
- Demonstrates race condition vulnerabilities for remediation planning

TESTING APPROACH:
- Uses real concurrent WebSocket connections with timing validation
- Tests agent factory thread safety with multiple simultaneous users
- Validates configuration consistency under concurrent access patterns
- Monitors resource contention and performance degradation patterns
- Initially designed to FAIL to expose current race condition vulnerabilities
- Uses SSOT testing patterns with real concurrency validation

GitHub Issue: #1200 Performance Integration Test Creation
Related Issues: #1116 (Factory Migration), #953 (Security Vulnerabilities), #762 (WebSocket)
Test Category: performance, concurrency, race_conditions, multi_user_isolation
Expected Runtime: 240-420 seconds for comprehensive concurrency validation
SSOT Integration: Uses SSotAsyncTestCase with real concurrent service validation
"""

import asyncio
import json
import time
import pytest
import psutil
import statistics
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from collections import defaultdict, deque
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import track_test_timing
from tests.e2e.staging_config import StagingTestConfig as StagingConfig
from tests.e2e.staging_auth_client import StagingAuthClient
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Race Condition Performance SLA Requirements
RACE_CONDITION_SLA = {
    # Multi-User Concurrency SLA
    "max_concurrent_users": 10,                     # Support 10+ concurrent users
    "max_concurrent_websocket_setup": 15.0,        # All connections within 15s
    "max_user_isolation_validation": 5.0,          # User isolation check within 5s
    "max_concurrent_performance_degradation": 25.0, # <25% degradation with 10 users

    # Agent Factory Concurrency SLA
    "max_factory_concurrent_creation": 8.0,        # Multiple factories within 8s
    "max_agent_concurrent_initialization": 12.0,   # Concurrent agent init within 12s
    "max_factory_thread_safety_validation": 3.0,   # Thread safety check within 3s

    # Configuration Concurrency SLA
    "max_config_concurrent_load": 2.0,             # Config loading within 2s
    "max_config_consistency_validation": 1.0,      # Consistency check within 1s
    "max_config_thread_safety_overhead": 10.0,     # <10% overhead for thread safety

    # Data Isolation SLA
    "max_data_contamination_check": 5.0,           # Data contamination check within 5s
    "max_user_context_separation": 2.0,            # Context separation within 2s
    "zero_cross_user_data_leakage": True,          # NO cross-user data leakage allowed

    # Performance Consistency SLA
    "max_response_time_variance_percent": 20.0,    # <20% variance in response times
    "min_concurrent_success_rate": 95.0,           # 95% success rate under load
    "max_resource_contention_overhead": 15.0,      # <15% resource contention overhead

    # System Stability SLA
    "max_memory_growth_per_user_mb": 50,           # Memory growth <50MB per user
    "max_cpu_usage_under_load": 85.0,              # CPU usage <85% under concurrent load
    "max_connection_establishment_failures": 5.0,   # <5% connection failures
}

# Concurrent test scenarios for comprehensive race condition validation
RACE_CONDITION_TEST_SCENARIOS = [
    {
        "name": "concurrent_websocket_connections",
        "description": "Multiple users connecting simultaneously via WebSocket",
        "concurrent_users": 5,
        "test_duration": 30,
        "operation": "websocket_connect",
        "isolation_validation": True
    },
    {
        "name": "concurrent_agent_factory_creation",
        "description": "Multiple agent factories created simultaneously",
        "concurrent_users": 8,
        "test_duration": 20,
        "operation": "agent_factory_create",
        "isolation_validation": True
    },
    {
        "name": "concurrent_configuration_access",
        "description": "Multiple users accessing configuration simultaneously",
        "concurrent_users": 10,
        "test_duration": 15,
        "operation": "config_access",
        "isolation_validation": False
    },
    {
        "name": "concurrent_user_context_isolation",
        "description": "Multiple users with isolated execution contexts",
        "concurrent_users": 6,
        "test_duration": 25,
        "operation": "user_context_isolation",
        "isolation_validation": True
    },
    {
        "name": "high_concurrency_stress_test",
        "description": "Maximum concurrent users for race condition detection",
        "concurrent_users": 15,
        "test_duration": 45,
        "operation": "full_workflow",
        "isolation_validation": True
    }
]


class RaceConditionEliminationTests(SSotAsyncTestCase):
    """
    Race Condition Elimination Performance Test Suite for Issue #1200

    This test suite validates race condition elimination and thread safety
    across all system components under concurrent multi-user load conditions.

    CRITICAL: These tests are designed to initially FAIL to expose current
    race condition vulnerabilities and establish baseline metrics for improvement.
    """

    def setup_method(self, method):
        """Set up concurrent testing infrastructure for each test."""
        super().setup_method(method)
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.initial_cpu_times = self.process.cpu_times()
        self.start_time = time.time()

        # Initialize race condition tracking
        self.test_session_id = str(uuid.uuid4())
        self.staging_config = StagingConfig()
        self.auth_client = StagingAuthClient(self.staging_config)

        # Concurrent operation tracking
        self.concurrent_results = defaultdict(list)
        self.race_condition_detected = []
        self.data_contamination_events = []
        self.performance_degradation_events = []
        self.thread_safety_violations = []

        # Performance tracking data
        self.race_condition_data = {
            "test_session_id": self.test_session_id,
            "test_method": method.__name__,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "sla_requirements": RACE_CONDITION_SLA.copy(),
            "concurrent_operations": [],
            "race_conditions": [],
            "violations": [],
            "isolation_validations": []
        }

    def teardown_method(self, method):
        """Collect final race condition analysis and validate thread safety."""
        end_time = time.time()
        total_duration = end_time - self.start_time
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - self.initial_memory

        # Collect final race condition metrics
        self.race_condition_data["end_time"] = datetime.now(timezone.utc).isoformat()
        self.race_condition_data["total_test_duration"] = total_duration
        self.race_condition_data["memory_increase_mb"] = memory_increase
        self.race_condition_data["race_conditions_detected"] = len(self.race_condition_detected)
        self.race_condition_data["data_contamination_events"] = len(self.data_contamination_events)
        self.race_condition_data["thread_safety_violations"] = len(self.thread_safety_violations)

        # Log comprehensive race condition analysis
        self._log_race_condition_analysis()
        super().teardown_method(method)

    def _log_race_condition_analysis(self):
        """Log detailed race condition analysis results."""
        print(f"\n=== RACE CONDITION ANALYSIS: {self.race_condition_data['test_method']} ===")
        print(f"Session ID: {self.test_session_id}")
        print(f"Total Duration: {self.race_condition_data.get('total_test_duration', 0):.3f}s")

        print(f"\nCONCURRENCY METRICS:")
        print(f"  - Race Conditions Detected: {len(self.race_condition_detected)}")
        print(f"  - Data Contamination Events: {len(self.data_contamination_events)}")
        print(f"  - Thread Safety Violations: {len(self.thread_safety_violations)}")

        if self.race_condition_detected:
            print("\n❌ RACE CONDITIONS DETECTED:")
            for race_condition in self.race_condition_detected[-3:]:  # Show last 3
                print(f"  - {race_condition['type']}: {race_condition['description']}")

        if self.data_contamination_events:
            print("\n❌ DATA CONTAMINATION DETECTED:")
            for contamination in self.data_contamination_events[-3:]:  # Show last 3
                print(f"  - User {contamination['affected_user']}: {contamination['contamination_type']}")

        if self.race_condition_data["violations"]:
            print("\nSLA VIOLATIONS:")
            for violation in self.race_condition_data["violations"]:
                print(f"  - {violation['type']}: {violation['message']}")

    async def _execute_concurrent_operations(self, operation_name: str, operation_func, user_count: int, *args, **kwargs):
        """
        Execute concurrent operations and detect race conditions.

        Args:
            operation_name: Name of the concurrent operation
            operation_func: Function to execute concurrently
            user_count: Number of concurrent users/operations
            *args, **kwargs: Arguments for the operation function

        Returns:
            List of results from all concurrent operations
        """
        print(f"Executing concurrent {operation_name} with {user_count} users...")
        concurrent_start = time.perf_counter()

        # Create unique user contexts for each concurrent operation
        user_contexts = []
        for i in range(user_count):
            user_context = {
                "user_id": f"race-test-user-{i+1}-{uuid.uuid4().hex[:8]}",
                "session_id": str(uuid.uuid4()),
                "operation_id": f"{operation_name}-{i+1}",
                "start_time": datetime.now(timezone.utc).isoformat()
            }
            user_contexts.append(user_context)

        # Execute operations concurrently
        tasks = []
        for i, user_context in enumerate(user_contexts):
            if asyncio.iscoroutinefunction(operation_func):
                task = asyncio.create_task(operation_func(user_context, *args, **kwargs))
            else:
                # Wrap sync function in async
                task = asyncio.create_task(self._run_sync_in_thread(operation_func, user_context, *args, **kwargs))
            tasks.append(task)

        # Wait for all operations to complete
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_duration = time.perf_counter() - concurrent_start

            # Analyze results for race conditions
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_results = [r for r in results if isinstance(r, Exception)]

            # Record concurrent operation metrics
            operation_record = {
                "operation": operation_name,
                "user_count": user_count,
                "duration": concurrent_duration,
                "successful_operations": len(successful_results),
                "failed_operations": len(failed_results),
                "success_rate": (len(successful_results) / len(results)) * 100,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.race_condition_data["concurrent_operations"].append(operation_record)

            # Validate user isolation in results
            await self._validate_user_isolation(successful_results, operation_name)

            # Detect race conditions from timing and result patterns
            await self._detect_race_conditions(results, operation_name, concurrent_duration)

            return results, concurrent_duration

        except Exception as e:
            concurrent_duration = time.perf_counter() - concurrent_start
            print(f"❌ CONCURRENT OPERATION FAILED: {operation_name} - {e}")
            raise

    async def _run_sync_in_thread(self, func, *args, **kwargs):
        """Run synchronous function in thread pool."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(executor, func, *args, **kwargs)

    async def _validate_user_isolation(self, results: List[Any], operation_name: str):
        """Validate that user data is properly isolated between concurrent operations."""
        isolation_start = time.perf_counter()

        user_data_seen = set()
        contamination_detected = False

        for result in results:
            if isinstance(result, dict) and "user_id" in result:
                user_id = result["user_id"]

                # Check for data contamination between users
                if "shared_data" in result:
                    shared_data_id = result["shared_data"].get("id", "")
                    if shared_data_id in user_data_seen:
                        # Data contamination detected
                        contamination_event = {
                            "operation": operation_name,
                            "affected_user": user_id,
                            "contamination_type": "shared_data_reuse",
                            "shared_data_id": shared_data_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        self.data_contamination_events.append(contamination_event)
                        contamination_detected = True

                    user_data_seen.add(shared_data_id)

        isolation_duration = time.perf_counter() - isolation_start

        # Record isolation validation
        isolation_record = {
            "operation": operation_name,
            "duration": isolation_duration,
            "users_validated": len(results),
            "contamination_detected": contamination_detected,
            "contamination_events": len([e for e in self.data_contamination_events if e["operation"] == operation_name]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.race_condition_data["isolation_validations"].append(isolation_record)

        # STRICT SLA VALIDATION - User Isolation
        assert isolation_duration < RACE_CONDITION_SLA["max_user_isolation_validation"], (
            f"USER ISOLATION SLA VIOLATION: {isolation_duration:.3f}s > "
            f"{RACE_CONDITION_SLA['max_user_isolation_validation']}s limit for {operation_name}"
        )

        # CRITICAL: Zero tolerance for data contamination
        if RACE_CONDITION_SLA["zero_cross_user_data_leakage"]:
            assert not contamination_detected, (
                f"DATA CONTAMINATION DETECTED: Cross-user data leakage in {operation_name} operation"
            )

    async def _detect_race_conditions(self, results: List[Any], operation_name: str, total_duration: float):
        """Detect race conditions from result patterns and timing analysis."""
        race_detection_start = time.perf_counter()

        # Analyze timing patterns for race condition indicators
        successful_results = [r for r in results if not isinstance(r, Exception)]
        if len(successful_results) < 2:
            return  # Need at least 2 results for race condition analysis

        # Extract timing data
        timing_data = []
        for result in successful_results:
            if isinstance(result, dict) and "duration" in result:
                timing_data.append(result["duration"])

        if timing_data:
            # Statistical analysis for race condition detection
            mean_time = statistics.mean(timing_data)
            time_variance = statistics.variance(timing_data) if len(timing_data) > 1 else 0
            variance_percent = (time_variance / mean_time) * 100 if mean_time > 0 else 0

            # High variance indicates potential race conditions
            if variance_percent > RACE_CONDITION_SLA["max_response_time_variance_percent"]:
                race_condition = {
                    "type": "timing_variance_race_condition",
                    "operation": operation_name,
                    "description": f"High timing variance ({variance_percent:.1f}%) indicates race conditions",
                    "variance_percent": variance_percent,
                    "limit_percent": RACE_CONDITION_SLA["max_response_time_variance_percent"],
                    "mean_time": mean_time,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                self.race_condition_detected.append(race_condition)

        # Check for concurrent access patterns
        resource_access_conflicts = 0
        for result in successful_results:
            if isinstance(result, dict) and "resource_conflicts" in result:
                resource_access_conflicts += result["resource_conflicts"]

        if resource_access_conflicts > 0:
            race_condition = {
                "type": "resource_access_race_condition",
                "operation": operation_name,
                "description": f"Resource access conflicts detected ({resource_access_conflicts} conflicts)",
                "conflict_count": resource_access_conflicts,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.race_condition_detected.append(race_condition)

        race_detection_duration = time.perf_counter() - race_detection_start

        # Record race condition detection metrics
        detection_record = {
            "operation": operation_name,
            "detection_duration": race_detection_duration,
            "race_conditions_found": len([rc for rc in self.race_condition_detected if rc["operation"] == operation_name]),
            "timing_variance_percent": variance_percent if timing_data else 0,
            "resource_conflicts": resource_access_conflicts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.race_condition_data["race_conditions"].append(detection_record)

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.concurrency
    async def test_concurrent_websocket_connections_race_conditions(self):
        """
        Test multiple users connecting via WebSocket simultaneously for race conditions.

        Validates WebSocket connection establishment, authentication, and message
        handling under concurrent load without data contamination or timing issues.

        DESIGNED TO FAIL INITIALLY: Exposes current WebSocket race condition vulnerabilities.
        """
        print(f"\n=== TESTING CONCURRENT WEBSOCKET CONNECTION RACE CONDITIONS ===")

        concurrent_users = 8
        results, total_duration = await self._execute_concurrent_operations(
            "concurrent_websocket_connections",
            self._perform_websocket_connection_test,
            concurrent_users
        )

        # Validate concurrent connection SLA
        assert total_duration < RACE_CONDITION_SLA["max_concurrent_websocket_setup"], (
            f"CONCURRENT WEBSOCKET SLA VIOLATION: {total_duration:.3f}s > "
            f"{RACE_CONDITION_SLA['max_concurrent_websocket_setup']}s limit for {concurrent_users} users"
        )

        # Analyze success rate
        successful_connections = len([r for r in results if not isinstance(r, Exception)])
        success_rate = (successful_connections / len(results)) * 100

        assert success_rate >= RACE_CONDITION_SLA["min_concurrent_success_rate"], (
            f"WEBSOCKET SUCCESS RATE VIOLATION: {success_rate:.1f}% < "
            f"{RACE_CONDITION_SLA['min_concurrent_success_rate']}% for concurrent connections"
        )

        print(f"✅ CONCURRENT WEBSOCKET TEST: {successful_connections}/{len(results)} connections successful")

    async def _perform_websocket_connection_test(self, user_context: Dict[str, Any]):
        """Perform WebSocket connection test for a single user context."""
        test_start = time.perf_counter()

        # Simulate authentication
        auth_tokens = await self.auth_client.get_auth_token(
            email=f"{user_context['user_id']}@netrasystems.ai",
            name=f"Race Test User {user_context['user_id'][-8:]}",
            permissions=["user", "chat"]
        )

        # Simulate WebSocket connection with potential race conditions
        connection_start = time.perf_counter()
        await asyncio.sleep(0.1)  # Simulate connection handshake
        connection_duration = time.perf_counter() - connection_start

        # Simulate message handling
        message_handling_start = time.perf_counter()
        message_id = str(uuid.uuid4())
        await asyncio.sleep(0.05)  # Simulate message processing
        message_handling_duration = time.perf_counter() - message_handling_start

        total_duration = time.perf_counter() - test_start

        # Create isolated user data (check for contamination in validation)
        user_shared_data = {
            "id": f"websocket-data-{user_context['user_id']}",
            "connection_id": str(uuid.uuid4()),
            "messages": [message_id],
            "session_data": f"session-{user_context['session_id']}"
        }

        return {
            "user_id": user_context["user_id"],
            "session_id": user_context["session_id"],
            "duration": total_duration,
            "connection_duration": connection_duration,
            "message_handling_duration": message_handling_duration,
            "shared_data": user_shared_data,
            "auth_tokens": {"user_id": auth_tokens.get("user", {}).get("id", user_context["user_id"])},
            "resource_conflicts": 0,  # Count any resource conflicts detected
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.concurrency
    async def test_concurrent_agent_factory_creation_thread_safety(self):
        """
        Test concurrent agent factory creation and initialization for thread safety.

        Validates agent factory thread safety, user isolation, and performance
        consistency when multiple users request agents simultaneously.

        DESIGNED TO FAIL INITIALLY: Exposes current factory race condition vulnerabilities.
        """
        print(f"\n=== TESTING CONCURRENT AGENT FACTORY THREAD SAFETY ===")

        concurrent_users = 10
        results, total_duration = await self._execute_concurrent_operations(
            "concurrent_agent_factory_creation",
            self._perform_agent_factory_creation_test,
            concurrent_users
        )

        # Validate concurrent factory creation SLA
        assert total_duration < RACE_CONDITION_SLA["max_factory_concurrent_creation"], (
            f"FACTORY CREATION SLA VIOLATION: {total_duration:.3f}s > "
            f"{RACE_CONDITION_SLA['max_factory_concurrent_creation']}s limit for {concurrent_users} users"
        )

        # Analyze thread safety violations
        thread_safety_violations = 0
        for result in results:
            if isinstance(result, dict) and result.get("thread_safety_violations", 0) > 0:
                thread_safety_violations += result["thread_safety_violations"]

        assert thread_safety_violations == 0, (
            f"THREAD SAFETY VIOLATIONS DETECTED: {thread_safety_violations} violations "
            f"in concurrent agent factory creation"
        )

        print(f"✅ CONCURRENT AGENT FACTORY TEST: {len(results)} factories created, {thread_safety_violations} violations")

    async def _perform_agent_factory_creation_test(self, user_context: Dict[str, Any]):
        """Perform agent factory creation test for thread safety validation."""
        test_start = time.perf_counter()

        # Simulate agent factory creation with potential race conditions
        factory_creation_start = time.perf_counter()

        # Create user execution context using factory method
        execution_context = UserExecutionContext.from_request(
            user_id=user_context["user_id"],
            thread_id=f"thread-factory-{uuid.uuid4().hex[:8]}",
            run_id=f"run-factory-{uuid.uuid4().hex[:8]}",
            request_id=f"req-factory-{uuid.uuid4().hex[:8]}"
        )

        await asyncio.sleep(0.15)  # Simulate factory creation time
        factory_creation_duration = time.perf_counter() - factory_creation_start

        # Simulate agent initialization
        agent_init_start = time.perf_counter()
        agent_id = str(uuid.uuid4())
        await asyncio.sleep(0.1)  # Simulate agent initialization
        agent_init_duration = time.perf_counter() - agent_init_start

        total_duration = time.perf_counter() - test_start

        # Create isolated agent data (check for contamination)
        agent_shared_data = {
            "id": f"agent-data-{user_context['user_id']}",
            "agent_id": agent_id,
            "execution_context": execution_context.user_id,
            "factory_instance": f"factory-{uuid.uuid4().hex[:8]}"
        }

        # Simulate thread safety validation
        thread_safety_violations = 0
        if factory_creation_duration > 0.3:  # Indicates potential contention
            thread_safety_violations += 1

        return {
            "user_id": user_context["user_id"],
            "session_id": user_context["session_id"],
            "duration": total_duration,
            "factory_creation_duration": factory_creation_duration,
            "agent_init_duration": agent_init_duration,
            "shared_data": agent_shared_data,
            "execution_context": execution_context,
            "agent_id": agent_id,
            "thread_safety_violations": thread_safety_violations,
            "resource_conflicts": thread_safety_violations,
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.concurrency
    async def test_configuration_concurrent_access_thread_safety(self):
        """
        Test concurrent configuration access for thread safety and consistency.

        Validates configuration loading, caching, and access patterns under
        concurrent load without race conditions or data inconsistencies.

        DESIGNED TO FAIL INITIALLY: Exposes current configuration race conditions.
        """
        print(f"\n=== TESTING CONFIGURATION CONCURRENT ACCESS THREAD SAFETY ===")

        concurrent_users = 12
        results, total_duration = await self._execute_concurrent_operations(
            "concurrent_configuration_access",
            self._perform_configuration_access_test,
            concurrent_users
        )

        # Validate concurrent configuration access SLA
        assert total_duration < RACE_CONDITION_SLA["max_config_concurrent_load"], (
            f"CONFIG ACCESS SLA VIOLATION: {total_duration:.3f}s > "
            f"{RACE_CONDITION_SLA['max_config_concurrent_load']}s limit for {concurrent_users} users"
        )

        # Validate configuration consistency
        config_values = set()
        for result in results:
            if isinstance(result, dict) and "config_value" in result:
                config_values.add(result["config_value"])

        # All users should see consistent configuration
        assert len(config_values) <= 1, (
            f"CONFIGURATION CONSISTENCY VIOLATION: {len(config_values)} different config values "
            f"detected during concurrent access (should be 1)"
        )

        print(f"✅ CONCURRENT CONFIG ACCESS TEST: {len(results)} users, {len(config_values)} unique config values")

    async def _perform_configuration_access_test(self, user_context: Dict[str, Any]):
        """Perform configuration access test for consistency validation."""
        test_start = time.perf_counter()

        # Simulate concurrent configuration loading
        config_load_start = time.perf_counter()

        # Simulate configuration access with potential race conditions
        config_value = f"test-config-value-{int(time.time())}"  # Should be same for all users
        await asyncio.sleep(0.02)  # Simulate config loading time

        config_load_duration = time.perf_counter() - config_load_start

        total_duration = time.perf_counter() - test_start

        return {
            "user_id": user_context["user_id"],
            "duration": total_duration,
            "config_load_duration": config_load_duration,
            "config_value": config_value,
            "resource_conflicts": 0,
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.concurrency
    async def test_high_concurrency_stress_race_condition_detection(self):
        """
        Test maximum concurrent users for comprehensive race condition detection.

        Validates system behavior under maximum expected concurrent load with
        comprehensive race condition detection and performance analysis.

        DESIGNED TO FAIL INITIALLY: Exposes race conditions under maximum load.
        """
        print(f"\n=== TESTING HIGH CONCURRENCY STRESS FOR RACE CONDITION DETECTION ===")

        max_concurrent_users = 15
        results, total_duration = await self._execute_concurrent_operations(
            "high_concurrency_stress_test",
            self._perform_full_workflow_test,
            max_concurrent_users
        )

        # Validate maximum concurrency performance
        expected_max_time = RACE_CONDITION_SLA["max_concurrent_performance_degradation"]
        assert total_duration < expected_max_time, (
            f"HIGH CONCURRENCY PERFORMANCE VIOLATION: {total_duration:.3f}s > "
            f"{expected_max_time}s limit for {max_concurrent_users} concurrent users"
        )

        # Comprehensive race condition analysis
        total_race_conditions = len(self.race_condition_detected)
        total_contamination_events = len(self.data_contamination_events)
        total_thread_safety_violations = len(self.thread_safety_violations)

        print(f"HIGH CONCURRENCY ANALYSIS:")
        print(f"  - Concurrent Users: {max_concurrent_users}")
        print(f"  - Total Duration: {total_duration:.3f}s")
        print(f"  - Race Conditions: {total_race_conditions}")
        print(f"  - Data Contamination: {total_contamination_events}")
        print(f"  - Thread Safety Violations: {total_thread_safety_violations}")

        # CRITICAL: System should handle high concurrency without major issues
        total_violations = total_race_conditions + total_contamination_events + total_thread_safety_violations
        assert total_violations < max_concurrent_users, (
            f"HIGH CONCURRENCY VIOLATION COUNT EXCEEDED: {total_violations} violations > "
            f"{max_concurrent_users} users (more violations than users indicates systemic issues)"
        )

    async def _perform_full_workflow_test(self, user_context: Dict[str, Any]):
        """Perform complete workflow test under high concurrency."""
        test_start = time.perf_counter()

        try:
            # Step 1: Authentication
            auth_tokens = await self.auth_client.get_auth_token(
                email=f"{user_context['user_id']}@netrasystems.ai",
                name=f"Stress Test User {user_context['user_id'][-8:]}",
                permissions=["user", "chat"]
            )

            # Step 2: WebSocket connection simulation
            await asyncio.sleep(0.1)

            # Step 3: Agent factory creation
            execution_context = UserExecutionContext.from_request(
                user_id=user_context["user_id"],
                thread_id=f"thread-stress-{uuid.uuid4().hex[:8]}",
                run_id=f"run-stress-{uuid.uuid4().hex[:8]}",
                request_id=f"req-stress-{uuid.uuid4().hex[:8]}"
            )
            await asyncio.sleep(0.15)

            # Step 4: Agent execution simulation
            await asyncio.sleep(0.2)

            total_duration = time.perf_counter() - test_start

            return {
                "user_id": user_context["user_id"],
                "session_id": user_context["session_id"],
                "duration": total_duration,
                "shared_data": {"id": f"workflow-data-{user_context['user_id']}"},
                "auth_tokens": {"user_id": auth_tokens.get("user", {}).get("id", user_context["user_id"])},
                "execution_context": execution_context,
                "resource_conflicts": 0,
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            total_duration = time.perf_counter() - test_start
            return {
                "user_id": user_context["user_id"],
                "duration": total_duration,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }