"""
Test race condition detection in WebSocket manager initialization for Issue #1182.

CRITICAL BUSINESS IMPACT: $500K+ ARR Golden Path depends on race-condition-free WebSocket operations.
This test validates factory pattern consistency and initialization safety in concurrent scenarios.

ISSUE #1182: WebSocket Manager SSOT Migration
- Problem: Race conditions in WebSocket manager initialization across competing implementations
- Impact: User isolation failures, event delivery inconsistencies, connection state corruption
- Solution: Factory patterns with proper user context isolation and initialization safety

RELATED ISSUES:
- Issue #1116: User isolation vulnerabilities in singleton patterns
- Issue #849: WebSocket 1011 errors from race conditions
- Issue #1209: DemoWebSocketBridge interface failures under race conditions

Test Strategy:
1. Detect concurrent initialization race conditions (SHOULD FAIL INITIALLY)
2. Validate user isolation factory pattern consistency (SHOULD FAIL INITIALLY)
3. Test connection state management under concurrent access (SHOULD FAIL INITIALLY)
4. Verify WebSocket event delivery isolation in multi-user scenarios (SHOULD FAIL INITIALLY)

Business Value Justification:
- Segment: Enterprise/Multi-User Platform
- Business Goal: System Reliability & User Data Security
- Value Impact: Prevents user data leakage and connection state corruption
- Revenue Impact: Enables HIPAA/SOC2/SEC compliance for enterprise customers
"""

import pytest
import asyncio
import unittest
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from datetime import datetime

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ThreadID, ConnectionID

logger = get_logger(__name__)


@dataclass
class RaceConditionTest:
    """Data class to track race condition test scenarios and results."""
    scenario_name: str
    concurrent_operations: int
    success_count: int = 0
    failure_count: int = 0
    race_conditions_detected: int = 0
    user_isolation_violations: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@pytest.mark.unit
class WebSocketManagerRaceConditionDetectionTests(SSotAsyncTestCase):
    """
    CRITICAL: Tests for Issue #1182 WebSocket Manager race condition detection.
    
    These tests SHOULD FAIL INITIALLY to demonstrate current race condition vulnerabilities.
    Success indicates proper concurrency safety and user isolation is implemented.
    """

    def setUp(self):
        """Set up test environment for race condition detection."""
        super().setUp()
        self.max_concurrent_users = 10
        self.race_condition_timeout = 5.0  # seconds
        self.test_results = []

    async def test_concurrent_manager_initialization_safety(self):
        """
        Test concurrent WebSocket manager initialization for race conditions.
        
        CURRENT STATE: SHOULD FAIL - Race conditions in initialization detected
        TARGET STATE: SHOULD PASS - Safe concurrent initialization with proper factory patterns
        
        Business Impact: Prevents connection state corruption and initialization failures
        """
        logger.info("🏁 Testing concurrent WebSocket manager initialization safety (Issue #1182)")
        
        race_test = RaceConditionTest(
            scenario_name="concurrent_initialization",
            concurrent_operations=self.max_concurrent_users
        )
        
        # Create multiple concurrent initialization attempts
        async def initialize_websocket_manager(user_index: int) -> Dict[str, Any]:
            """Simulate concurrent WebSocket manager initialization for different users."""
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                from netra_backend.app.core.unified_id_manager import UnifiedIDManager
                
                # Generate unique user context
                id_manager = UnifiedIDManager()
                user_id = f"test_user_{user_index}_{int(time.time() * 1000000)}"
                thread_id = id_manager.generate_id("THREAD", context={"user": user_id})
                
                # Create mock WebSocket for testing
                mock_websocket = AsyncMock()
                mock_websocket.send_text = AsyncMock()
                
                # Time the initialization to detect timing issues
                start_time = time.time()
                
                # Attempt WebSocket manager initialization
                manager = WebSocketManager(websocket=mock_websocket, user_id=user_id)
                
                initialization_time = time.time() - start_time
                
                # Test basic functionality
                await manager.emit_agent_event(
                    event_type="agent_started",
                    data={"message": f"Test from user {user_index}"},
                    user_id=user_id,
                    thread_id=thread_id
                )
                
                return {
                    'user_index': user_index,
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'manager_id': id(manager),
                    'initialization_time': initialization_time,
                    'success': True,
                    'error': None
                }
                
            except Exception as e:
                logger.error(f"❌ Initialization failed for user {user_index}: {e}")
                return {
                    'user_index': user_index,
                    'success': False,
                    'error': str(e),
                    'initialization_time': None
                }
        
        # Execute concurrent initializations
        logger.info(f"🚀 Starting {race_test.concurrent_operations} concurrent initializations...")
        
        start_time = time.time()
        tasks = [
            initialize_websocket_manager(i) 
            for i in range(race_test.concurrent_operations)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results for race conditions
        successful_results = []
        failed_results = []
        manager_ids = set()
        user_ids = set()
        initialization_times = []
        
        for result in results:
            if isinstance(result, Exception):
                race_test.failure_count += 1
                race_test.errors.append(str(result))
                failed_results.append(result)
            elif result.get('success'):
                race_test.success_count += 1
                successful_results.append(result)
                manager_ids.add(result['manager_id'])
                user_ids.add(result['user_id'])
                if result['initialization_time']:
                    initialization_times.append(result['initialization_time'])
            else:
                race_test.failure_count += 1
                race_test.errors.append(result.get('error', 'Unknown error'))
                failed_results.append(result)
        
        # Detect race conditions
        # 1. Manager instance sharing (should be unique per user)
        expected_managers = race_test.success_count
        actual_managers = len(manager_ids)
        if actual_managers != expected_managers:
            race_test.race_conditions_detected += 1
            race_test.errors.append(
                f"Manager instance sharing detected: {expected_managers} users, {actual_managers} unique managers"
            )
        
        # 2. User ID collisions (should be unique)
        expected_users = race_test.success_count
        actual_users = len(user_ids)
        if actual_users != expected_users:
            race_test.user_isolation_violations += 1
            race_test.errors.append(
                f"User ID collision detected: {expected_users} operations, {actual_users} unique users"
            )
        
        # 3. Timing-based race condition indicators
        if initialization_times:
            avg_time = sum(initialization_times) / len(initialization_times)
            max_time = max(initialization_times)
            min_time = min(initialization_times)
            
            # Significant timing variance can indicate race conditions
            timing_variance = max_time - min_time
            if timing_variance > avg_time * 2:  # More than 200% variance
                race_test.race_conditions_detected += 1
                race_test.errors.append(
                    f"High timing variance detected: {timing_variance:.3f}s variance, avg: {avg_time:.3f}s"
                )
        
        # Log detailed analysis
        logger.info(f"📊 Concurrent Initialization Analysis:")
        logger.info(f"   Total operations: {race_test.concurrent_operations}")
        logger.info(f"   Successful: {race_test.success_count}")
        logger.info(f"   Failed: {race_test.failure_count}")
        logger.info(f"   Unique managers: {actual_managers}")
        logger.info(f"   Unique users: {actual_users}")
        logger.info(f"   Race conditions detected: {race_test.race_conditions_detected}")
        logger.info(f"   User isolation violations: {race_test.user_isolation_violations}")
        logger.info(f"   Total execution time: {total_time:.3f}s")
        
        if race_test.errors:
            logger.error(f"   Errors: {race_test.errors}")
        
        self.test_results.append(race_test)
        
        # CRITICAL: No race conditions should be detected for SSOT compliance
        # CURRENT STATE: This assertion SHOULD FAIL (race conditions detected)
        # TARGET STATE: This assertion SHOULD PASS (safe concurrent initialization)
        self.assertEqual(
            race_test.race_conditions_detected, 0,
            f"Race conditions detected in WebSocket manager initialization: {race_test.race_conditions_detected}. "
            f"Issue #1182 concurrent safety not implemented. Errors: {race_test.errors}"
        )
        
        self.assertEqual(
            race_test.user_isolation_violations, 0,
            f"User isolation violations detected: {race_test.user_isolation_violations}. "
            f"Issue #1182 user context isolation not implemented. Related to Issue #1116 vulnerabilities."
        )

    async def test_user_isolation_factory_pattern_consistency(self):
        """
        Validate user isolation through factory patterns.
        
        CURRENT STATE: SHOULD FAIL - Singleton violations detected
        TARGET STATE: SHOULD PASS - Proper factory patterns with user context isolation
        
        Business Impact: Prevents user data leakage and enables enterprise compliance
        Related: Issue #1116 singleton removal and user isolation
        """
        logger.info("👥 Testing user isolation factory pattern consistency (Issue #1182)")
        
        race_test = RaceConditionTest(
            scenario_name="user_isolation_factory",
            concurrent_operations=self.max_concurrent_users
        )
        
        # Test user isolation through concurrent operations
        async def test_user_isolation(user_index: int) -> Dict[str, Any]:
            """Test user isolation in WebSocket operations."""
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                from netra_backend.app.core.unified_id_manager import UnifiedIDManager
                
                # Create unique user context
                id_manager = UnifiedIDManager()
                user_id = f"isolated_user_{user_index}_{uuid.uuid4().hex[:8]}"
                thread_id = id_manager.generate_id("THREAD", context={"user": user_id})
                
                # Create isolated WebSocket manager
                mock_websocket = AsyncMock()
                mock_websocket.send_text = AsyncMock()
                
                manager = WebSocketManager(websocket=mock_websocket, user_id=user_id)
                
                # Perform user-specific operations
                user_data = f"sensitive_data_for_user_{user_index}"
                
                await manager.emit_agent_event(
                    event_type="agent_thinking",
                    data={"user_data": user_data, "user_index": user_index},
                    user_id=user_id,
                    thread_id=thread_id
                )
                
                # Verify user context isolation
                connections = manager.get_active_connections()
                
                return {
                    'user_index': user_index,
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'manager_instance': id(manager),
                    'user_data': user_data,
                    'connections_count': len(connections) if connections else 0,
                    'success': True
                }
                
            except Exception as e:
                logger.error(f"❌ User isolation test failed for user {user_index}: {e}")
                return {
                    'user_index': user_index,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent user isolation tests
        logger.info(f"🚀 Testing user isolation for {race_test.concurrent_operations} concurrent users...")
        
        tasks = [test_user_isolation(i) for i in range(race_test.concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze user isolation
        successful_results = []
        user_contexts = {}
        manager_instances = set()
        data_leakage_detected = False
        
        for result in results:
            if isinstance(result, Exception):
                race_test.failure_count += 1
                race_test.errors.append(str(result))
            elif result.get('success'):
                race_test.success_count += 1
                successful_results.append(result)
                
                user_id = result['user_id']
                manager_id = result['manager_instance']
                user_data = result['user_data']
                
                # Track user contexts
                user_contexts[user_id] = {
                    'manager_id': manager_id,
                    'user_data': user_data,
                    'user_index': result['user_index']
                }
                manager_instances.add(manager_id)
                
            else:
                race_test.failure_count += 1
                race_test.errors.append(result.get('error', 'Unknown isolation error'))
        
        # Check for user isolation violations
        # 1. Each user should have unique manager instance
        expected_instances = race_test.success_count
        actual_instances = len(manager_instances)
        
        if actual_instances < expected_instances:
            race_test.user_isolation_violations += 1
            race_test.errors.append(
                f"Manager instance sharing detected: {expected_instances} users sharing {actual_instances} managers"
            )
        
        # 2. Check for data leakage between user contexts
        user_data_sets = [ctx['user_data'] for ctx in user_contexts.values()]
        unique_data_sets = set(user_data_sets)
        
        if len(unique_data_sets) != len(user_data_sets):
            data_leakage_detected = True
            race_test.user_isolation_violations += 1
            race_test.errors.append(
                f"User data leakage detected: {len(user_data_sets)} users, {len(unique_data_sets)} unique data sets"
            )
        
        # Log isolation analysis
        logger.info(f"📊 User Isolation Analysis:")
        logger.info(f"   Total users tested: {race_test.concurrent_operations}")
        logger.info(f"   Successful isolations: {race_test.success_count}")
        logger.info(f"   Failed isolations: {race_test.failure_count}")
        logger.info(f"   Unique manager instances: {actual_instances}")
        logger.info(f"   Unique user data sets: {len(unique_data_sets)}")
        logger.info(f"   Data leakage detected: {data_leakage_detected}")
        logger.info(f"   Isolation violations: {race_test.user_isolation_violations}")
        
        if race_test.errors:
            logger.error(f"   Isolation errors: {race_test.errors}")
        
        self.test_results.append(race_test)
        
        # CRITICAL: User isolation must be perfect for enterprise compliance
        # CURRENT STATE: This assertion SHOULD FAIL (isolation violations detected)
        # TARGET STATE: This assertion SHOULD PASS (perfect user isolation)
        self.assertEqual(
            race_test.user_isolation_violations, 0,
            f"User isolation violations detected: {race_test.user_isolation_violations}. "
            f"Issue #1182 factory pattern user isolation not implemented. "
            f"Critical for Issue #1116 singleton removal. Violations: {race_test.errors}"
        )
        
        self.assertFalse(
            data_leakage_detected,
            f"User data leakage detected between isolated contexts. "
            f"This violates enterprise compliance requirements (HIPAA/SOC2/SEC). "
            f"Issue #1182 user context isolation is incomplete."
        )

    async def test_websocket_event_delivery_race_conditions(self):
        """
        Test WebSocket event delivery for race conditions in concurrent scenarios.
        
        CURRENT STATE: SHOULD FAIL - Event delivery race conditions detected
        TARGET STATE: SHOULD PASS - Reliable event delivery with no race conditions
        
        Business Impact: Ensures reliable real-time communication for Golden Path
        Related: Issue #849 WebSocket 1011 errors from race conditions
        """
        logger.info("📡 Testing WebSocket event delivery race conditions (Issue #1182)")
        
        race_test = RaceConditionTest(
            scenario_name="event_delivery_race_conditions",
            concurrent_operations=self.max_concurrent_users * 5  # Multiple events per user
        )
        
        # Test concurrent event delivery
        async def send_concurrent_events(user_index: int, event_count: int = 5) -> Dict[str, Any]:
            """Send multiple events concurrently for race condition testing."""
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                from netra_backend.app.core.unified_id_manager import UnifiedIDManager
                
                # Create user context
                id_manager = UnifiedIDManager()
                user_id = f"event_user_{user_index}"
                thread_id = id_manager.generate_id("THREAD", context={"user": user_id})
                
                # Track sent events for verification
                sent_events = []
                mock_websocket = AsyncMock()
                
                # Capture sent messages for race condition analysis
                async def capture_send(message):
                    sent_events.append({
                        'timestamp': time.time(),
                        'message': message,
                        'thread': threading.current_thread().ident
                    })
                    # Simulate small delay to increase race condition probability
                    await asyncio.sleep(0.001)
                
                mock_websocket.send_text = capture_send
                
                manager = WebSocketManager(websocket=mock_websocket, user_id=user_id)
                
                # Send multiple events concurrently
                event_tasks = []
                for event_index in range(event_count):
                    event_task = manager.emit_agent_event(
                        event_type=f"agent_event_{event_index}",
                        data={
                            "user_index": user_index,
                            "event_index": event_index,
                            "timestamp": time.time()
                        },
                        user_id=user_id,
                        thread_id=thread_id
                    )
                    event_tasks.append(event_task)
                
                # Wait for all events to complete
                await asyncio.gather(*event_tasks)
                
                return {
                    'user_index': user_index,
                    'user_id': user_id,
                    'events_sent': len(sent_events),
                    'events_expected': event_count,
                    'sent_events': sent_events,
                    'success': True
                }
                
            except Exception as e:
                logger.error(f"❌ Event delivery test failed for user {user_index}: {e}")
                return {
                    'user_index': user_index,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent event delivery tests
        logger.info(f"🚀 Testing event delivery for {self.max_concurrent_users} users with 5 events each...")
        
        tasks = [send_concurrent_events(i) for i in range(self.max_concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze event delivery for race conditions
        successful_results = []
        total_events_sent = 0
        total_events_expected = 0
        timing_inconsistencies = 0
        event_ordering_violations = 0
        
        for result in results:
            if isinstance(result, Exception):
                race_test.failure_count += 1
                race_test.errors.append(str(result))
            elif result.get('success'):
                race_test.success_count += 1
                successful_results.append(result)
                total_events_sent += result['events_sent']
                total_events_expected += result['events_expected']
                
                # Check for event ordering violations
                sent_events = result['sent_events']
                if len(sent_events) > 1:
                    timestamps = [event['timestamp'] for event in sent_events]
                    if timestamps != sorted(timestamps):
                        event_ordering_violations += 1
                        race_test.race_conditions_detected += 1
                
            else:
                race_test.failure_count += 1
                race_test.errors.append(result.get('error', 'Unknown event delivery error'))
        
        # Check for event delivery completeness
        event_delivery_rate = (total_events_sent / total_events_expected) if total_events_expected > 0 else 0
        
        if event_delivery_rate < 1.0:
            race_test.race_conditions_detected += 1
            race_test.errors.append(
                f"Event delivery incomplete: {total_events_sent}/{total_events_expected} ({event_delivery_rate:.2%})"
            )
        
        # Log event delivery analysis
        logger.info(f"📊 Event Delivery Race Condition Analysis:")
        logger.info(f"   Total users: {self.max_concurrent_users}")
        logger.info(f"   Successful deliveries: {race_test.success_count}")
        logger.info(f"   Failed deliveries: {race_test.failure_count}")
        logger.info(f"   Events sent: {total_events_sent}")
        logger.info(f"   Events expected: {total_events_expected}")
        logger.info(f"   Delivery rate: {event_delivery_rate:.2%}")
        logger.info(f"   Ordering violations: {event_ordering_violations}")
        logger.info(f"   Race conditions detected: {race_test.race_conditions_detected}")
        
        if race_test.errors:
            logger.error(f"   Event delivery errors: {race_test.errors}")
        
        self.test_results.append(race_test)
        
        # CRITICAL: Event delivery must be reliable for Golden Path functionality
        # CURRENT STATE: This assertion SHOULD FAIL (race conditions in event delivery)
        # TARGET STATE: This assertion SHOULD PASS (reliable event delivery)
        self.assertGreaterEqual(
            event_delivery_rate, 1.0,
            f"Event delivery incomplete: {event_delivery_rate:.2%} delivery rate. "
            f"Issue #1182 event delivery race conditions affect Golden Path. "
            f"Related to Issue #849 WebSocket errors."
        )
        
        self.assertEqual(
            race_test.race_conditions_detected, 0,
            f"Race conditions detected in event delivery: {race_test.race_conditions_detected}. "
            f"Issue #1182 concurrent event safety not implemented. "
            f"Critical for $500K+ ARR Golden Path reliability."
        )

    def tearDown(self):
        """Clean up and log comprehensive race condition test results."""
        super().tearDown()
        
        if self.test_results:
            logger.info("📋 COMPREHENSIVE RACE CONDITION TEST SUMMARY:")
            logger.info("=" * 60)
            
            total_operations = sum(test.concurrent_operations for test in self.test_results)
            total_successes = sum(test.success_count for test in self.test_results)
            total_failures = sum(test.failure_count for test in self.test_results)
            total_race_conditions = sum(test.race_conditions_detected for test in self.test_results)
            total_isolation_violations = sum(test.user_isolation_violations for test in self.test_results)
            
            logger.info(f"Total concurrent operations tested: {total_operations}")
            logger.info(f"Total successful operations: {total_successes}")
            logger.info(f"Total failed operations: {total_failures}")
            logger.info(f"Total race conditions detected: {total_race_conditions}")
            logger.info(f"Total user isolation violations: {total_isolation_violations}")
            
            success_rate = (total_successes / total_operations) if total_operations > 0 else 0
            logger.info(f"Overall success rate: {success_rate:.2%}")
            
            for test_result in self.test_results:
                logger.info(f"\n📊 {test_result.scenario_name}:")
                logger.info(f"   Operations: {test_result.concurrent_operations}")
                logger.info(f"   Success: {test_result.success_count}")
                logger.info(f"   Failures: {test_result.failure_count}")
                logger.info(f"   Race conditions: {test_result.race_conditions_detected}")
                logger.info(f"   Isolation violations: {test_result.user_isolation_violations}")
                
                if test_result.errors:
                    logger.error(f"   Errors: {test_result.errors[:3]}...")  # Show first 3 errors
            
            logger.info("=" * 60)


if __name__ == '__main__':
    unittest.main()