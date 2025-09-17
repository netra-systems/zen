"
WebSocket Race Condition Integration Tests - Issue #1176

Business Value Justification:
- Segment: ALL (Free -> Enterprise)
- Business Goal: Prevent Golden Path failures from WebSocket race conditions
- Value Impact: Protects $500K+ ARR chat functionality from timing-related failures
- Strategic Impact: CRITICAL - Ensures reliable WebSocket infrastructure for AI chat interactions

RACE CONDITION TARGETS:
1. Cloud Run startup timing vs WebSocket handshake coordination
2. WebSocket manager initialization conflicts during concurrent requests
3. Progressive handshake delays causing service startup validation failures
4. Concurrent WebSocket connection establishment conflicts

CRITICAL: These tests are designed to FAIL initially to prove race condition problems exist.
They validate that Issue #1176 WebSocket race conditions cause Golden Path failures.

TEST STRATEGY:
- Integration tests (non-Docker) for service coordination
- Real service dependencies to expose timing issues
- Progressive delay patterns to trigger race conditions
- Concurrent connection scenarios to expose conflicts
"

import asyncio
import pytest
import time
import uuid
from typing import Dict, List, Optional, Any
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

# SSOT BaseTestCase for compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core WebSocket components
from netra_backend.app.websocket_core.websocket_manager import (
    get_websocket_manager,
    WebSocketManager,
    WebSocketManagerMode,
    check_websocket_service_available
)
from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter
# UserExecutionContextFactory not available - using mock context instead

# Logging and monitoring
from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

logger = get_logger(__name__)


class WebSocketRaceConditionIntegrationTests(SSotAsyncTestCase):
    "
    Integration tests for WebSocket race conditions that cause Golden Path failures.
    
    CRITICAL: These tests expose timing issues between:
    - Cloud Run startup sequences
    - WebSocket handshake coordination  
    - Service dependency initialization
    - Concurrent connection establishment
    
    Business Impact: $500K+ ARR depends on reliable WebSocket infrastructure.
"
    
    def setUp(self):
        "Set up test environment with race condition detection.
        super().setUp()
        self.id_manager = UnifiedIDManager()
        self.test_user_id = self.id_manager.generate_id(IDType.USER, prefix=racetest")"
        self.test_thread_id = self.id_manager.generate_id(IDType.THREAD, prefix=racetest)
        self.race_condition_detected = False
        self.timing_failures = []
        
    async def asyncSetUp(self):
        "Async setup for WebSocket race condition testing."
        await super().asyncSetUp()
        
        # Create test user context for isolation
        # Using fallback test context since UserExecutionContextFactory not available
        self.user_context = type('MockUserContext', (), {
            'user_id': self.test_user_id,
            'thread_id': self.test_thread_id,
            'request_id': self.id_manager.generate_id(IDType.REQUEST, prefix=racetest),
            'is_test': True
        }()
    
    async def test_cloud_run_startup_timing_race_condition(self):
        ""
        Test Cloud Run startup timing vs WebSocket handshake coordination.
        
        EXPECTED BEHAVIOR: This test should FAIL initially, proving the race condition exists.
        
        RACE CONDITION SCENARIO:
        1. Cloud Run service starts but WebSocket manager not ready
        2. Client attempts WebSocket handshake before service fully initialized  
        3. Race between service availability and handshake completion
        4. Results in 1011 errors or connection timeouts
        
        BUSINESS IMPACT: Users experience chat connection failures during Cloud Run cold starts.

        logger.info("Testing Cloud Run startup timing race condition...)"
        
        race_conditions = []
        
        for attempt in range(3):
            try:
                # Simulate Cloud Run startup delay
                startup_delay = 0.1 + (attempt * 0.05)  # Progressive delays
                
                # Check service availability before handshake
                start_time = time.time()
                service_available = await check_websocket_service_available()
                availability_check_time = time.time() - start_time
                
                if not service_available:
                    logger.warning(fAttempt {attempt}: Service not available after {availability_check_time:.3f}s)
                
                # Attempt WebSocket manager creation during potential startup race
                manager_start_time = time.time()
                manager = get_websocket_manager(
                    user_context=self.user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                manager_creation_time = time.time() - manager_start_time
                
                # Test race condition scenario: very short time window
                if manager_creation_time > 0.5:  # Threshold indicating potential race condition
                    race_conditions.append({
                        'attempt': attempt,
                        'startup_delay': startup_delay,
                        'availability_check_time': availability_check_time,
                        'manager_creation_time': manager_creation_time,
                        'service_available': service_available
                    }
                    logger.error(fRACE CONDITION DETECTED: Manager creation took {manager_creation_time:.3f}s)
                
                # Introduce delay to increase race condition probability
                await asyncio.sleep(startup_delay)
                
            except Exception as e:
                race_conditions.append({
                    'attempt': attempt,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                logger.error(fException during race condition test attempt {attempt}: {e}")"
        
        # CRITICAL: Test should fail if race conditions detected
        if race_conditions:
            self.race_condition_detected = True
            self.timing_failures.extend(race_conditions)
            
            failure_details = []
            for rc in race_conditions:
                if 'error' in rc:
                    failure_details.append(fAttempt {rc['attempt']}: {rc['error_type']} - {rc['error']})
                else:
                    failure_details.append(
                        fAttempt {rc['attempt']}: Manager creation {rc['manager_creation_time']:.3f}s 
                        f"(service_available={rc['service_available']}
                    )
            
            pytest.fail(
                fRACE CONDITION DETECTED: Cloud Run startup timing issues found. "
                fThis proves Issue #1176 exists. Details: {'; '.join(failure_details)}
            )
    
    async def test_websocket_manager_initialization_race_condition(self):
        "
        Test WebSocket manager initialization conflicts during concurrent requests.
        
        EXPECTED BEHAVIOR: This test should FAIL initially, proving concurrent initialization race conditions.
        
        RACE CONDITION SCENARIO:
        1. Multiple concurrent requests attempt WebSocket manager creation
        2. Factory pattern initialization conflicts
        3. Shared state contamination between user contexts
        4. Memory leaks from incomplete cleanup
        
        BUSINESS IMPACT: Multi-user chat sessions interfere with each other.
"
        logger.info(Testing WebSocket manager initialization race conditions...)"
        
        concurrent_failures = []
        
        # Create multiple user contexts for concurrent testing
        user_contexts = []
        for i in range(5):
            # Using fallback test context since UserExecutionContextFactory not available
            context = type('MockUserContext', (), {
                'user_id': self.id_manager.generate_id(IDType.USER, prefix=fconcurrent_{i}"),
                'thread_id': self.id_manager.generate_id(IDType.THREAD, prefix=fconcurrent_{i}),
                'request_id': self.id_manager.generate_id(IDType.REQUEST, prefix=fconcurrent_{i}),"
                'is_test': True
            }()
            user_contexts.append(context)
        
        async def create_manager_with_timing(context, index):
            "Create WebSocket manager and track timing.
            try:
                start_time = time.time()
                manager = get_websocket_manager(
                    user_context=context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                creation_time = time.time() - start_time
                
                return {
                    'index': index,
                    'success': True,
                    'creation_time': creation_time,
                    'manager': manager,
                    'user_id': context.user_id
                }
            except Exception as e:
                return {
                    'index': index,
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'user_id': context.user_id
                }
        
        # Execute concurrent manager creation
        tasks = [
            create_manager_with_timing(context, i) 
            for i, context in enumerate(user_contexts)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results for race conditions
        successful_creations = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        failed_creations = [r for r in results if isinstance(r, dict) and not r.get('success', True)]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # Check for race condition indicators
        race_indicators = []
        
        # 1. Excessive creation times indicating contention
        long_creations = [r for r in successful_creations if r['creation_time'] > 1.0]
        if long_creations:
            race_indicators.append(fExcessive creation times: {[r['creation_time'] for r in long_creations]}")"
        
        # 2. Failed concurrent creations
        if failed_creations:
            race_indicators.append(fFailed concurrent creations: {len(failed_creations)})
        
        # 3. Exceptions during concurrent access
        if exceptions:
            race_indicators.append(fExceptions during concurrent access: {len(exceptions)})
        
        # 4. Total time indicating serialization instead of parallelization
        if total_time > 3.0:  # Should be much faster if truly concurrent
            race_indicators.append(f"Total time {total_time:.3f}s indicates serialization)
        
        logger.info(fConcurrent manager creation results: {len(successful_creations)} successful, "
                   f{len(failed_creations)} failed, {len(exceptions)} exceptions, 
                   ftotal time: {total_time:.3f}s)"
        
        # CRITICAL: Test should fail if race conditions detected
        if race_indicators:
            self.race_condition_detected = True
            concurrent_failures.extend(race_indicators)
            
            pytest.fail(
                f"RACE CONDITION DETECTED: WebSocket manager initialization conflicts found. 
                fThis proves Issue #1176 concurrent access issues exist. 
                fRace indicators: {'; '.join(race_indicators)}
            )
    
    async def test_progressive_handshake_delay_race_condition(self):
        ""
        Test progressive handshake delays causing service startup validation failures.
        
        EXPECTED BEHAVIOR: This test should FAIL initially, proving handshake timing race conditions.
        
        RACE CONDITION SCENARIO:
        1. WebSocket handshake starts before all services ready
        2. Progressive delays in handshake completion
        3. Service validation fails due to incomplete startup
        4. Authentication timing issues during handshake
        
        BUSINESS IMPACT: Users experience authentication failures and connection drops.

        logger.info("Testing progressive handshake delay race conditions...)"
        
        handshake_failures = []
        
        # Test with increasing delays to trigger race conditions
        delay_scenarios = [0.01, 0.05, 0.1, 0.2, 0.5]  # Progressive delays
        
        for delay in delay_scenarios:
            try:
                # Simulate handshake delay scenario
                logger.info(fTesting handshake with {delay}s delay...)
                
                # Create WebSocket router for handshake testing
                router = WebSocketSSOTRouter()
                
                # Simulate delayed handshake initiation
                await asyncio.sleep(delay)
                
                # Check if services are properly initialized
                start_time = time.time()
                service_available = await check_websocket_service_available()
                service_check_time = time.time() - start_time
                
                # Test WebSocket manager creation during delay scenario
                manager_start_time = time.time()
                manager = get_websocket_manager(
                    user_context=self.user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                manager_time = time.time() - manager_start_time
                
                # Detect race condition indicators
                total_time = service_check_time + manager_time
                
                race_detected = False
                if not service_available:
                    race_detected = True
                    handshake_failures.append({
                        'delay': delay,
                        'issue': 'service_not_available',
                        'service_check_time': service_check_time
                    }
                
                if manager_time > 1.0:  # Excessive manager creation time
                    race_detected = True
                    handshake_failures.append({
                        'delay': delay,
                        'issue': 'excessive_manager_time',
                        'manager_time': manager_time
                    }
                
                if total_time > 1.5:  # Total time indicating race condition
                    race_detected = True
                    handshake_failures.append({
                        'delay': delay,
                        'issue': 'excessive_total_time',
                        'total_time': total_time
                    }
                
                if race_detected:
                    logger.error(fHANDSHAKE RACE CONDITION: delay={delay}s, 
                               fservice_available={service_available}, ""
                               fmanager_time={manager_time:.3f}s, 
                               ftotal_time={total_time:.3f}s)
                
            except Exception as e:
                handshake_failures.append({
                    'delay': delay,
                    'issue': 'exception',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                logger.error(f"Exception during handshake delay test (delay={delay}s): {e})
        
        # CRITICAL: Test should fail if handshake race conditions detected
        if handshake_failures:
            self.race_condition_detected = True
            self.timing_failures.extend(handshake_failures)
            
            failure_summary = {}
            for failure in handshake_failures:
                issue_type = failure['issue']
                if issue_type not in failure_summary:
                    failure_summary[issue_type] = 0
                failure_summary[issue_type] += 1
            
            pytest.fail(
                fHANDSHAKE RACE CONDITION DETECTED: Progressive delays caused validation failures. "
                fThis proves Issue #1176 handshake timing issues exist. 
                fFailure summary: {failure_summary}"
            )
    
    async def test_concurrent_connection_establishment_conflicts(self):
    "
        Test concurrent WebSocket connection establishment conflicts.
        
        EXPECTED BEHAVIOR: This test should FAIL initially, proving concurrent connection race conditions.
        
        RACE CONDITION SCENARIO:
        1. Multiple clients attempt simultaneous WebSocket connections
        2. Connection state management conflicts
        3. Resource contention during connection establishment
        4. Connection cleanup race conditions
        
        BUSINESS IMPACT: Chat sessions fail to establish when multiple users connect simultaneously.
        "
        logger.info(Testing concurrent connection establishment conflicts...")
        
        connection_conflicts = []
        
        # Create multiple concurrent connection scenarios
        connection_attempts = 4
        
        async def attempt_connection(attempt_id):
            Attempt WebSocket connection establishment.""
            try:
                # Create unique user context for each connection
                user_context = type('MockUserContext', (), {
                    'user_id': self.id_manager.generate_id(IDType.USER, prefix=fconn_{attempt_id}),
                    'thread_id': self.id_manager.generate_id(IDType.THREAD, prefix=fconn_{attempt_id}),
                    'request_id': self.id_manager.generate_id(IDType.REQUEST, prefix=fconn_{attempt_id}"),"
                    'is_test': True
                }()
                
                start_time = time.time()
                
                # Test connection establishment timing
                manager = get_websocket_manager(
                    user_context=user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                
                establishment_time = time.time() - start_time
                
                # Simulate connection activity
                await asyncio.sleep(0.01)  # Brief activity
                
                return {
                    'attempt_id': attempt_id,
                    'success': True,
                    'establishment_time': establishment_time,
                    'user_id': user_context.user_id
                }
                
            except Exception as e:
                return {
                    'attempt_id': attempt_id,
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
        
        # Execute concurrent connection attempts
        start_time = time.time()
        tasks = [attempt_connection(i) for i in range(connection_attempts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_concurrent_time = time.time() - start_time
        
        # Analyze concurrent connection results
        successful_connections = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        failed_connections = [r for r in results if isinstance(r, dict) and not r.get('success', True)]
        connection_exceptions = [r for r in results if isinstance(r, Exception)]
        
        # Detect race condition indicators
        conflict_indicators = []
        
        # 1. Connection establishment time variance indicating contention
        if successful_connections:
            establishment_times = [r['establishment_time'] for r in successful_connections]
            max_time = max(establishment_times)
            min_time = min(establishment_times)
            time_variance = max_time - min_time
            
            if time_variance > 0.5:  # High variance indicates contention
                conflict_indicators.append(fHigh establishment time variance: {time_variance:.3f}s)
        
        # 2. Failed concurrent connections
        if failed_connections:
            conflict_indicators.append(fFailed concurrent connections: {len(failed_connections)})
            for failed in failed_connections:
                conflict_indicators.append(f"  - Attempt {failed['attempt_id']}: {failed.get('error_type', 'Unknown')})
        
        # 3. Exceptions during concurrent establishment
        if connection_exceptions:
            conflict_indicators.append(fConnection exceptions: {len(connection_exceptions)}")
        
        # 4. Excessive total time for concurrent operations
        expected_concurrent_time = 1.0  # Should be much faster for true concurrency
        if total_concurrent_time > expected_concurrent_time:
            conflict_indicators.append(fExcessive concurrent time: {total_concurrent_time:.3f}s > {expected_concurrent_time}s)
        
        logger.info(fConcurrent connection results: {len(successful_connections)} successful, "
                   f"{len(failed_connections)} failed, {len(connection_exceptions)} exceptions, 
                   ftotal time: {total_concurrent_time:.3f}s)
        
        # CRITICAL: Test should fail if connection conflicts detected
        if conflict_indicators:
            self.race_condition_detected = True
            connection_conflicts.extend(conflict_indicators)
            
            pytest.fail(
                fCONNECTION RACE CONDITION DETECTED: Concurrent connection establishment conflicts found. 
                fThis proves Issue #1176 concurrent connection issues exist. ""
                fConflict indicators: {'; '.join(conflict_indicators)}
            )
    
    async def test_websocket_router_startup_race_condition(self):
        
        Test WebSocket router startup coordination race conditions.
        
        EXPECTED BEHAVIOR: This test should FAIL initially, proving router startup race conditions.
        
        RACE CONDITION SCENARIO:
        1. WebSocket router initialization before dependencies ready
        2. Route registration timing conflicts
        3. Health check endpoint availability race
        4. Authentication pipeline initialization delays
        
        BUSINESS IMPACT: Chat routes unavailable during service startup causing 404/500 errors.
""
        logger.info(Testing WebSocket router startup race conditions...)
        
        router_race_conditions = []
        
        # Test router initialization scenarios
        for attempt in range(3):
            try:
                # Simulate router startup timing
                router_start_time = time.time()
                
                # Create WebSocket router (may trigger race conditions)
                router = WebSocketSSOTRouter()
                
                router_init_time = time.time() - router_start_time
                
                # Test route availability immediately after creation
                health_check_start = time.time()
                
                # Check if router is properly initialized
                if not hasattr(router, 'router') or router.router is None:
                    router_race_conditions.append({
                        'attempt': attempt,
                        'issue': 'router_not_initialized',
                        'init_time': router_init_time
                    }
                    logger.error(fROUTER RACE CONDITION: Router not properly initialized in attempt {attempt}")"
                
                health_check_time = time.time() - health_check_start
                
                # Check for excessive initialization time
                if router_init_time > 0.5:
                    router_race_conditions.append({
                        'attempt': attempt,
                        'issue': 'excessive_init_time',
                        'init_time': router_init_time
                    }
                    logger.error(fROUTER RACE CONDITION: Excessive init time {router_init_time:.3f}s in attempt {attempt})
                
                # Brief delay between attempts to vary timing
                await asyncio.sleep(0.1 * (attempt + 1))
                
            except Exception as e:
                router_race_conditions.append({
                    'attempt': attempt,
                    'issue': 'exception_during_init',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                logger.error(fException during router startup test attempt {attempt}: {e})
        
        # CRITICAL: Test should fail if router race conditions detected
        if router_race_conditions:
            self.race_condition_detected = True
            
            failure_details = []
            for rc in router_race_conditions:
                if rc['issue'] == 'exception_during_init':
                    failure_details.append(f"Attempt {rc['attempt']}: {rc['error_type']} - {rc['error']})
                else:
                    failure_details.append(fAttempt {rc['attempt']}: {rc['issue']}")
            
            pytest.fail(
                fROUTER STARTUP RACE CONDITION DETECTED: WebSocket router initialization conflicts found. 
                fThis proves Issue #1176 router startup issues exist. "
                f"Details: {'; '.join(failure_details)}
            )

    def tearDown(self):
        Clean up test environment and report race condition findings."
        super().tearDown()
        
        if self.race_condition_detected:
            logger.error(f"ISSUE #1176 VALIDATION: Race conditions detected during testing. 
                        fTotal timing failures: {len(self.timing_failures)})
            
            # Log detailed race condition analysis
            for i, failure in enumerate(self.timing_failures):
                logger.error(fRace condition {i+1}: {failure})


# Additional helper functions for race condition testing

async def simulate_cloud_run_cold_start_delay():
    ""Simulate Cloud Run cold start delay patterns.
    import random
    delay = random.uniform(0.1, 0.3)  # Typical cold start delay range
    await asyncio.sleep(delay)
    return delay

def detect_timing_anomaly(operation_time: float, expected_time: float, tolerance: float = 0.1) -> bool:
    Detect if operation timing indicates race condition.""
    return operation_time > (expected_time + tolerance)

class RaceConditionDetector:
    Helper class for detecting race condition patterns.""
    
    def __init__(self):
        self.timing_samples = []
        self.failure_patterns = []
    
    def record_timing(self, operation: str, duration: float, success: bool):
        Record timing data for race condition analysis."
        self.timing_samples.append({
            'operation': operation,
            'duration': duration,
            'success': success,
            'timestamp': datetime.now(timezone.utc)
        }
    
    def analyze_race_patterns(self) -> Dict[str, Any]:
        "Analyze recorded timings for race condition patterns.
        if not self.timing_samples:
            return {'race_detected': False, 'patterns': []}
        
        patterns = []
        
        # Check for timing variance patterns
        successful_timings = [s['duration'] for s in self.timing_samples if s['success']]
        if len(successful_timings) > 1:
            variance = max(successful_timings) - min(successful_timings)
            if variance > 0.5:  # High variance indicates contention
                patterns.append(f"High timing variance: {variance:.3f}s)
        
        # Check for failure correlation with timing
        failed_operations = [s for s in self.timing_samples if not s['success']]
        if failed_operations:
            patterns.append(fOperations failed: {len(failed_operations)}")"
        
        return {
            'race_detected': len(patterns) > 0,
            'patterns': patterns,
            'total_samples': len(self.timing_samples),
            'failure_rate': len(failed_operations) / len(self.timing_samples) if self.timing_samples else 0
        }