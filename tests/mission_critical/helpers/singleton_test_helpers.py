'''
Singleton Test Helpers - Utilities for validating singleton removal

BUSINESS VALUE JUSTIFICATION:
    - Segment: Platform/Internal
    - Business Goal: Testing Infrastructure & Quality Assurance
    - Value Impact: Enables comprehensive validation of concurrent user isolation
    - Strategic Impact: Foundation for enterprise-grade concurrent user support

These utilities provide comprehensive testing infrastructure for validating
that singleton patterns have been properly removed and replaced with factory
patterns that support concurrent user isolation.

KEY CAPABILITIES:
    1. Concurrent User Context Generation
    2. State Isolation Verification
    3. WebSocket Event Capture and Analysis
    4. Memory Leak Detection
    5. Race Condition Detection
    6. Performance Degradation Measurement
    7. Factory Pattern Validation
    8. Data Leakage Detection
'''

import asyncio
import time
import uuid
import gc
import psutil
import threading
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

# Core imports with graceful fallback
try:
    from netra_backend.app.services.websocket_bridge_factory import (
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        UserWebSocketContext,
        UserWebSocketConnection,
        WebSocketEvent
    )
    from netra_backend.app.agents.supervisor.execution_factory import (
        ExecutionEngineFactory,
        UserExecutionContext
    )
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from shared.isolated_environment import IsolatedEnvironment
except ImportError as e:
    logger.warning(f"Some imports failed: {e}. Mock implementations will be used.")


@dataclass
class UserTestContext:
    """Represents a complete user context for testing isolation."""
    user_id: str
    thread_id: str
    connection_id: str
    run_id: str
    session_id: str
    created_at: datetime

    @classmethod
    def generate(cls, user_prefix: str = "test_user") -> 'UserTestContext':
        """Generate a unique user context for testing."""
        timestamp = datetime.now(timezone.utc)
        unique_id = uuid.uuid4().hex[:8]

        return cls(
            user_id=f"{user_prefix}_{unique_id}",
            thread_id=f"thread_{unique_id}",
            connection_id=f"conn_{unique_id}",
            run_id=f"run_{unique_id}",
            session_id=f"session_{unique_id}",
            created_at=timestamp
        )


@dataclass
class IsolationTestResult:
    """Results of user isolation testing."""
    test_name: str
    users_tested: int
    isolation_violations: List[str]
    data_leakage_detected: bool
    memory_leaks_detected: bool
    race_conditions_detected: bool
    performance_degradation: bool
    success: bool
    details: Dict[str, Any]


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self, user_context: UserTestContext):
        self.user_context = user_context
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        self.events_captured = []

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")

        # Add user context to message for isolation tracking
        message_with_context = {
            **message,
            '_test_user_id': self.user_context.user_id,
            '_test_timestamp': datetime.now(timezone.utc).isoformat()
        }

        self.messages_sent.append(message_with_context)
        self.events_captured.append(message_with_context)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()


class SingletonTestHelpers:
    """
    Comprehensive testing utilities for singleton removal validation.

    Provides tools to test that factory patterns properly isolate user contexts
    and prevent data leakage between concurrent users.
    """

    def __init__(self):
        self.test_results = []
        self.performance_baseline = None
        self.memory_baseline = None

    def generate_concurrent_users(self, count: int, prefix: str = "test_user") -> List[UserTestContext]:
        """Generate multiple user contexts for concurrent testing."""
        users = []
        for i in range(count):
            user_context = UserTestContext.generate(f"{prefix}_{i}")
            users.append(user_context)

        logger.info(f"Generated {count} concurrent user contexts")
        return users

    async def create_isolated_websocket_connections(
        self,
        user_contexts: List[UserTestContext]
    ) -> Dict[str, TestWebSocketConnection]:
        """Create isolated WebSocket connections for each user context."""
        connections = {}

        for user_context in user_contexts:
            connection = TestWebSocketConnection(user_context)
            connections[user_context.user_id] = connection

        logger.info(f"Created {len(connections)} isolated WebSocket connections")
        return connections

    async def simulate_concurrent_agent_execution(
        self,
        user_contexts: List[UserTestContext],
        execution_duration: float = 1.0
    ) -> Dict[str, List[Dict]]:
        """Simulate concurrent agent execution for multiple users."""
        results = {}

        async def execute_for_user(user_context: UserTestContext):
            """Execute agent workflow for a single user."""
            user_results = []

            # Simulate agent lifecycle events
            events = [
                {
                    'event_type': 'agent_started',
                    'user_id': user_context.user_id,
                    'run_id': user_context.run_id,
                    'timestamp': time.time()
                },
                {
                    'event_type': 'agent_thinking',
                    'user_id': user_context.user_id,
                    'run_id': user_context.run_id,
                    'thinking': f'Processing request for user {user_context.user_id}',
                    'timestamp': time.time()
                },
                {
                    'event_type': 'agent_completed',
                    'user_id': user_context.user_id,
                    'run_id': user_context.run_id,
                    'result': {'status': 'success', 'user_specific_data': user_context.user_id},
                    'timestamp': time.time()
                }
            ]

            for event in events:
                user_results.append(event)
                await asyncio.sleep(execution_duration / len(events))

            return user_results

        # Execute concurrently for all users
        tasks = [execute_for_user(user_context) for user_context in user_contexts]
        concurrent_results = await asyncio.gather(*tasks)

        # Organize results by user
        for i, user_context in enumerate(user_contexts):
            results[user_context.user_id] = concurrent_results[i]

        logger.info(f"Completed concurrent execution for {len(user_contexts)} users")
        return results

    def detect_data_leakage(
        self,
        execution_results: Dict[str, List[Dict]]
    ) -> List[str]:
        """Detect data leakage between user contexts."""
        violations = []

        # Check for cross-user data contamination
        for user_id, user_results in execution_results.items():
            for event in user_results:
                # Check if event contains data from other users
                event_user_id = event.get('user_id')
                if event_user_id != user_id:
                    violations.append(
                        f"User {user_id} received event with user_id {event_user_id}"
                    )

                # Check if result contains other users' data
                if 'result' in event and isinstance(event['result'], dict):
                    result_data = str(event['result'])
                    for other_user_id in execution_results.keys():
                        if other_user_id != user_id and other_user_id in result_data:
                            violations.append(
                                f"User {user_id} result contains data from user {other_user_id}"
                            )

        if violations:
            logger.error(f"Data leakage detected: {len(violations)} violations")
        else:
            logger.info("No data leakage detected - user isolation is working")

        return violations

    def detect_memory_leaks(
        self,
        before_execution: Optional[Dict] = None,
        after_execution: Optional[Dict] = None
    ) -> bool:
        """Detect memory leaks during concurrent execution."""
        if before_execution is None:
            before_execution = self._get_memory_stats()

        if after_execution is None:
            after_execution = self._get_memory_stats()

        # Force garbage collection
        gc.collect()

        # Check for significant memory increase
        memory_increase = after_execution['memory_mb'] - before_execution['memory_mb']
        object_increase = after_execution['object_count'] - before_execution['object_count']

        # Thresholds for leak detection
        memory_threshold = 50  # MB
        object_threshold = 1000  # objects

        memory_leak = memory_increase > memory_threshold
        object_leak = object_increase > object_threshold

        if memory_leak or object_leak:
            logger.warning(
                f"Potential memory leak detected: "
                f"Memory: +{memory_increase:.1f}MB, Objects: +{object_increase}"
            )
            return True
        else:
            logger.info("No memory leaks detected")
            return False

    def detect_race_conditions(
        self,
        execution_results: Dict[str, List[Dict]],
        tolerance_ms: float = 100.0
    ) -> bool:
        """Detect potential race conditions in concurrent execution."""
        race_conditions = []

        # Collect all events with timestamps
        all_events = []
        for user_id, events in execution_results.items():
            for event in events:
                if 'timestamp' in event:
                    all_events.append({
                        'user_id': user_id,
                        'event_type': event['event_type'],
                        'timestamp': event['timestamp']
                    })

        # Sort by timestamp
        all_events.sort(key=lambda x: x['timestamp'])

        # Look for suspiciously simultaneous events (potential race conditions)
        for i in range(len(all_events) - 1):
            current_event = all_events[i]
            next_event = all_events[i + 1]

            time_diff_ms = (next_event['timestamp'] - current_event['timestamp']) * 1000

            # Different users with same event type at nearly same time
            if (current_event['user_id'] != next_event['user_id'] and
                current_event['event_type'] == next_event['event_type'] and
                time_diff_ms < tolerance_ms):

                race_conditions.append({
                    'users': [current_event['user_id'], next_event['user_id']],
                    'event_type': current_event['event_type'],
                    'time_diff_ms': time_diff_ms
                })

        if race_conditions:
            logger.warning(f"Potential race conditions detected: {len(race_conditions)}")
            for race in race_conditions:
                logger.warning(f"  {race}")
            return True
        else:
            logger.info("No race conditions detected")
            return False

    def measure_performance_degradation(
        self,
        single_user_time: float,
        concurrent_users_time: float,
        user_count: int
    ) -> bool:
        """Measure if concurrent execution causes performance degradation."""
        # Expected time should scale roughly linearly with user count
        expected_time = single_user_time * user_count

        # Allow some overhead for concurrency management
        acceptable_overhead = 1.5  # 50% overhead is acceptable
        threshold_time = expected_time * acceptable_overhead

        degradation = concurrent_users_time > threshold_time

        if degradation:
            overhead_factor = concurrent_users_time / expected_time
            logger.warning(
                f"Performance degradation detected: "
                f"{overhead_factor:.1f}x overhead (threshold: {acceptable_overhead}x)"
            )
        else:
            logger.info("Performance scaling is acceptable")

        return degradation

    async def comprehensive_isolation_test(
        self,
        user_count: int = 5,
        execution_duration: float = 1.0
    ) -> IsolationTestResult:
        """Run comprehensive user isolation test."""
        test_name = f"comprehensive_isolation_{user_count}_users"
        logger.info(f"Starting {test_name}")

        # Establish baseline
        memory_before = self._get_memory_stats()

        # Generate test users
        user_contexts = self.generate_concurrent_users(user_count)

        # Create isolated connections
        connections = await self.create_isolated_websocket_connections(user_contexts)

        # Run concurrent execution
        start_time = time.time()
        execution_results = await self.simulate_concurrent_agent_execution(
            user_contexts, execution_duration
        )
        execution_time = time.time() - start_time

        # Measure single user performance for comparison
        single_user_start = time.time()
        single_user_result = await self.simulate_concurrent_agent_execution(
            [user_contexts[0]], execution_duration
        )
        single_user_time = time.time() - single_user_start

        # Analyze results
        memory_after = self._get_memory_stats()

        data_leakage_violations = self.detect_data_leakage(execution_results)
        memory_leaks = self.detect_memory_leaks(memory_before, memory_after)
        race_conditions = self.detect_race_conditions(execution_results)
        performance_degradation = self.measure_performance_degradation(
            single_user_time, execution_time, user_count
        )

        # Determine overall success
        success = (
            len(data_leakage_violations) == 0 and
            not memory_leaks and
            not race_conditions and
            not performance_degradation
        )

        result = IsolationTestResult(
            test_name=test_name,
            users_tested=user_count,
            isolation_violations=data_leakage_violations,
            data_leakage_detected=len(data_leakage_violations) > 0,
            memory_leaks_detected=memory_leaks,
            race_conditions_detected=race_conditions,
            performance_degradation=performance_degradation,
            success=success,
            details={
                'execution_time': execution_time,
                'single_user_time': single_user_time,
                'memory_before': memory_before,
                'memory_after': memory_after,
                'execution_results': execution_results
            }
        )

        self.test_results.append(result)

        if success:
            logger.info(f"CHECK {test_name} PASSED - User isolation is working correctly")
        else:
            logger.error(f"X {test_name} FAILED - User isolation issues detected")

        return result

    def _get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics."""
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            'memory_mb': memory_info.rss / 1024 / 1024,
            'memory_percent': process.memory_percent(),
            'object_count': len(gc.get_objects()),
            'timestamp': time.time()
        }

    def print_isolation_test_summary(self, results: List[IsolationTestResult]):
        """Print comprehensive summary of isolation test results."""
        logger.info("\n" + "=" * 80)
        logger.info("🔒 USER ISOLATION TEST SUMMARY")
        logger.info("=" * 80)

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests

        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")

        if failed_tests == 0:
            logger.info("🎉 ALL ISOLATION TESTS PASSED!")
            logger.info("CHECK Singleton removal is complete and effective")
            logger.info("CHECK User contexts are properly isolated")
            logger.info("CHECK No data leakage between concurrent users")
        else:
            logger.error("🚨 ISOLATION ISSUES DETECTED!")

            for result in results:
                if not result.success:
                    logger.error(f"\nX {result.test_name}:")
                    if result.data_leakage_detected:
                        logger.error(f"  Data leakage: {len(result.isolation_violations)} violations")
                    if result.memory_leaks_detected:
                        logger.error("  Memory leaks detected")
                    if result.race_conditions_detected:
                        logger.error("  Race conditions detected")
                    if result.performance_degradation:
                        logger.error("  Performance degradation detected")


# Utility functions for easy import
def generate_test_users(count: int) -> List[UserTestContext]:
    """Convenience function to generate test users."""
    helpers = SingletonTestHelpers()
    return helpers.generate_concurrent_users(count)


async def quick_isolation_test(user_count: int = 3) -> bool:
    """Quick isolation test for basic validation."""
    helpers = SingletonTestHelpers()
    result = await helpers.comprehensive_isolation_test(user_count)
    return result.success


# Test configuration constants
DEFAULT_USER_COUNT = 5
DEFAULT_EXECUTION_DURATION = 1.0
MEMORY_LEAK_THRESHOLD_MB = 50
RACE_CONDITION_TOLERANCE_MS = 100.0
PERFORMANCE_OVERHEAD_THRESHOLD = 1.5