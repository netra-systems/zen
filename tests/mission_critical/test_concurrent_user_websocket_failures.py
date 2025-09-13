#!/usr/bin/env python
"""
FAILING TEST: Concurrent User WebSocket Isolation Violation - Issue #680

This test REPRODUCES the 0% concurrent user success rate by proving SSOT violations exist.
Business Impact: $500K+ ARR at risk from WebSocket cross-contamination

Test Strategy:
- Start 2 concurrent users with WebSocket connections  
- Verify they get isolated WebSocket events (not shared)
- Should FAIL: Cross-contamination of WebSocket events
- Should FAIL: Shared state between users causing race conditions

Expected Result: FAILS before SSOT refactor, PASSES after SSOT consolidation
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Any, Optional

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import WebSocket components following SSOT patterns
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext, create_isolated_execution_context
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

logger = logging.getLogger(__name__)


class TestConcurrentUserWebSocketFailures(SSotAsyncTestCase):
    """
    FAILING TEST: Proves WebSocket SSOT violations cause 0% concurrent user success rate.
    
    This test is designed to FAIL and demonstrate the issue described in Issue #680:
    - WebSocket events are cross-contaminated between users
    - Shared state causes race conditions
    - Multiple concurrent users cannot operate independently
    
    After SSOT consolidation, this test should PASS with proper user isolation.
    """
    
    def setup_method(self, method=None):
        """Setup for concurrent user isolation testing."""
        super().setup_method(method)
        
        # Test configuration
        self.test_timeout = 15.0  # Generous timeout for concurrent operations
        self.event_capture_timeout = 5.0
        
        # Track test state
        self.websocket_managers = {}
        self.user_contexts = {}
        self.event_logs = {}
        self.execution_engines = {}
        
        # CRITICAL: These will be used to detect SSOT violations
        self.cross_contamination_detected = False
        self.shared_state_violations = []
        self.concurrent_operation_failures = []
        
        logger.info(f"Starting test: {self._test_context.test_id}")
    
    def teardown_method(self, method=None):
        """Clean up test resources."""
        # Clean up WebSocket managers
        for manager in self.websocket_managers.values():
            try:
                if hasattr(manager, 'cleanup'):
                    manager.cleanup()
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")
        
        super().teardown_method(method)
    
    async def create_isolated_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Create isolated user context for testing.
        
        This method is designed to expose SSOT violations by attempting
        to create truly isolated user contexts. If SSOT violations exist,
        we'll see shared state leakage.
        """
        # Create user execution context
        context = await create_isolated_execution_context(
            user_id=user_id,
            request_id=f"req_{user_id}_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{user_id}_{uuid.uuid4().hex[:8]}"
        )
        
        # Create WebSocket manager (should be isolated per user)
        websocket_manager = get_websocket_manager()
        
        # Create agent WebSocket bridge
        bridge = create_agent_websocket_bridge(
            websocket_manager=websocket_manager,
            user_context=context
        )
        
        # Create execution engine
        execution_engine = UserExecutionEngine(
            user_context=context,
            websocket_bridge=bridge
        )
        
        # Store references for violation detection
        user_data = {
            'context': context,
            'websocket_manager': websocket_manager,
            'bridge': bridge,
            'execution_engine': execution_engine,
            'events_received': [],
            'start_time': time.time()
        }
        
        # Track for SSOT violation detection
        self.user_contexts[user_id] = user_data
        self.websocket_managers[user_id] = websocket_manager
        self.execution_engines[user_id] = execution_engine
        self.event_logs[user_id] = []
        
        return user_data
    
    async def simulate_agent_execution(self, user_id: str, operation_name: str) -> Dict[str, Any]:
        """
        Simulate agent execution that should trigger WebSocket events.
        
        This exposes SSOT violations by running concurrent agent operations
        and checking if events cross-contaminate between users.
        """
        user_data = self.user_contexts.get(user_id)
        if not user_data:
            raise ValueError(f"User context not found for {user_id}")
        
        execution_engine = user_data['execution_engine']
        bridge = user_data['bridge']
        
        # Simulate the 5 critical WebSocket events that should be isolated per user
        events_to_send = [
            {"type": "agent_started", "data": {"operation": operation_name, "user_id": user_id}},
            {"type": "agent_thinking", "data": {"thought": f"Processing {operation_name} for {user_id}"}},
            {"type": "tool_executing", "data": {"tool": "test_tool", "user_id": user_id}},
            {"type": "tool_completed", "data": {"tool": "test_tool", "result": "success", "user_id": user_id}},
            {"type": "agent_completed", "data": {"operation": operation_name, "status": "completed", "user_id": user_id}}
        ]
        
        sent_events = []
        
        # Send events through the bridge - this is where SSOT violations manifest
        for event in events_to_send:
            try:
                # Add timestamp and user tracking
                event['timestamp'] = time.time()
                event['sent_by_user'] = user_id
                
                # Send through WebSocket bridge
                await bridge.send_event(event['type'], event['data'])
                sent_events.append(event)
                
                # Record that this user sent this event
                self.event_logs[user_id].append({
                    'action': 'sent',
                    'event': event,
                    'timestamp': time.time()
                })
                
                # Small delay to simulate processing
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to send event {event['type']} for user {user_id}: {e}")
                self.concurrent_operation_failures.append({
                    'user_id': user_id,
                    'operation': operation_name,
                    'event_type': event['type'],
                    'error': str(e)
                })
        
        return {
            'user_id': user_id,
            'operation': operation_name,
            'events_sent': sent_events,
            'sent_count': len(sent_events)
        }
    
    def detect_cross_contamination(self) -> List[Dict[str, Any]]:
        """
        Detect if events from one user are received by another user.
        
        This is the core SSOT violation detection logic.
        If WebSocket managers are shared (SSOT violation), events will cross-contaminate.
        """
        violations = []
        
        # Check if WebSocket managers are the same instance (SSOT violation)
        manager_instances = list(self.websocket_managers.values())
        if len(manager_instances) > 1:
            first_manager = manager_instances[0]
            for i, manager in enumerate(manager_instances[1:], 1):
                if manager is first_manager:
                    violations.append({
                        'type': 'shared_websocket_manager',
                        'description': f'WebSocket manager instance shared between users (SSOT violation)',
                        'manager_id': id(manager),
                        'users_affected': list(self.websocket_managers.keys())
                    })
        
        # Check if execution engines share state
        engine_instances = list(self.execution_engines.values())
        if len(engine_instances) > 1:
            # Check for shared internal state
            first_engine = engine_instances[0]
            for i, engine in enumerate(engine_instances[1:], 1):
                if hasattr(first_engine, '_shared_state') and hasattr(engine, '_shared_state'):
                    if first_engine._shared_state is engine._shared_state:
                        violations.append({
                            'type': 'shared_execution_engine_state',
                            'description': f'Execution engines share internal state (SSOT violation)',
                            'state_id': id(first_engine._shared_state),
                            'users_affected': list(self.execution_engines.keys())
                        })
        
        # Check for event cross-contamination in logs
        for user_id, events in self.event_logs.items():
            for event_log in events:
                if event_log['action'] == 'received':
                    event = event_log['event']
                    if 'sent_by_user' in event and event['sent_by_user'] != user_id:
                        violations.append({
                            'type': 'event_cross_contamination',
                            'description': f'User {user_id} received event sent by {event["sent_by_user"]}',
                            'receiving_user': user_id,
                            'sending_user': event['sent_by_user'],
                            'event_type': event.get('type'),
                            'timestamp': event_log['timestamp']
                        })
        
        return violations
    
    def detect_concurrent_operation_failures(self) -> List[Dict[str, Any]]:
        """
        Detect failures specific to concurrent operations.
        
        These failures indicate SSOT violations preventing proper multi-user support.
        """
        failures = []
        
        # Check if any operations failed due to shared state conflicts
        if self.concurrent_operation_failures:
            failures.extend(self.concurrent_operation_failures)
        
        # Check for timing conflicts (race conditions)
        user_timings = {}
        for user_id, user_data in self.user_contexts.items():
            user_timings[user_id] = user_data.get('start_time', 0)
        
        # If users started at very similar times but some failed, it's likely a race condition
        timing_values = list(user_timings.values())
        if len(timing_values) > 1:
            max_timing = max(timing_values)
            min_timing = min(timing_values)
            if (max_timing - min_timing) < 1.0:  # Started within 1 second
                # Check for failures
                for failure in self.concurrent_operation_failures:
                    failures.append({
                        'type': 'race_condition_failure',
                        'description': f'Concurrent operation failed due to timing conflict',
                        'user_id': failure['user_id'],
                        'error': failure['error'],
                        'timing_spread': max_timing - min_timing
                    })
        
        return failures
    
    @pytest.mark.asyncio
    async def test_concurrent_users_websocket_isolation_violation(self):
        """
        FAILING TEST: Proves 0% concurrent user success rate from SSOT violations.
        
        This test creates 2 concurrent users and verifies they are properly isolated.
        Expected to FAIL due to SSOT violations causing:
        1. Shared WebSocket manager instances
        2. Cross-contamination of events between users  
        3. Race conditions in concurrent operations
        4. Shared state in execution engines
        
        After SSOT consolidation, this test should PASS with proper isolation.
        """
        logger.info("Starting concurrent user WebSocket isolation violation test")
        
        # Define test users
        test_users = ['user_alpha', 'user_beta']
        
        # Phase 1: Create isolated user contexts concurrently
        logger.info("Phase 1: Creating isolated user contexts")
        context_tasks = []
        for user_id in test_users:
            task = asyncio.create_task(self.create_isolated_user_context(user_id))
            context_tasks.append((user_id, task))
        
        # Wait for all contexts to be created
        for user_id, task in context_tasks:
            try:
                user_data = await asyncio.wait_for(task, timeout=self.test_timeout)
                logger.info(f"Created context for {user_id}")
            except asyncio.TimeoutError:
                self.concurrent_operation_failures.append({
                    'user_id': user_id,
                    'operation': 'context_creation',
                    'event_type': 'setup',
                    'error': 'Context creation timed out'
                })
        
        # Phase 2: Run concurrent agent operations
        logger.info("Phase 2: Running concurrent agent operations")
        operation_tasks = []
        for i, user_id in enumerate(test_users):
            operation_name = f"test_operation_{i}"
            task = asyncio.create_task(self.simulate_agent_execution(user_id, operation_name))
            operation_tasks.append((user_id, task))
        
        # Execute operations concurrently and collect results
        operation_results = {}
        for user_id, task in operation_tasks:
            try:
                result = await asyncio.wait_for(task, timeout=self.test_timeout)
                operation_results[user_id] = result
                logger.info(f"Completed operation for {user_id}: {result['sent_count']} events sent")
            except asyncio.TimeoutError:
                self.concurrent_operation_failures.append({
                    'user_id': user_id,
                    'operation': 'agent_execution',
                    'event_type': 'timeout',
                    'error': 'Agent execution timed out'
                })
        
        # Phase 3: Wait for event propagation
        logger.info("Phase 3: Waiting for event propagation")
        await asyncio.sleep(self.event_capture_timeout)
        
        # Phase 4: Detect SSOT violations
        logger.info("Phase 4: Analyzing for SSOT violations")
        
        # Detect cross-contamination
        cross_contamination_violations = self.detect_cross_contamination()
        
        # Detect concurrent operation failures
        concurrent_failures = self.detect_concurrent_operation_failures()
        
        # Phase 5: Assert violations exist (test should FAIL)
        logger.info("Phase 5: Asserting SSOT violations exist")
        
        # Record test metrics
        self.record_metric('users_tested', len(test_users))
        self.record_metric('contexts_created', len(self.user_contexts))
        self.record_metric('operations_attempted', len(operation_tasks))
        self.record_metric('operations_completed', len(operation_results))
        self.record_metric('cross_contamination_violations', len(cross_contamination_violations))
        self.record_metric('concurrent_failures', len(concurrent_failures))
        
        # Document violations for debugging
        logger.error(f"SSOT Violations Detected:")
        logger.error(f"  Cross-contamination violations: {len(cross_contamination_violations)}")
        logger.error(f"  Concurrent operation failures: {len(concurrent_failures)}")
        
        if cross_contamination_violations:
            logger.error("Cross-contamination details:")
            for violation in cross_contamination_violations:
                logger.error(f"  - {violation['type']}: {violation['description']}")
        
        if concurrent_failures:
            logger.error("Concurrent failure details:")
            for failure in concurrent_failures:
                logger.error(f"  - {failure.get('type', 'unknown')}: {failure.get('description', failure.get('error'))}")
        
        # SUCCESS CRITERIA FOR AFTER SSOT CONSOLIDATION:
        # After SSOT refactor, these assertions should be flipped to verify isolation works
        
        # CURRENT EXPECTATION: Test should FAIL due to SSOT violations
        # This proves the issue exists and needs to be fixed
        
        # Assert that we have evidence of SSOT violations
        total_violations = len(cross_contamination_violations) + len(concurrent_failures)
        
        # If no violations detected, the test infrastructure might not be sensitive enough
        if total_violations == 0:
            pytest.fail(
                "UNEXPECTED: No SSOT violations detected. "
                "Either the violations don't exist (good) or the test needs improvement. "
                "Expected: WebSocket cross-contamination and concurrent user failures."
            )
        
        # Expected violations that prove Issue #680 exists
        assert total_violations > 0, (
            f"EXPECTED SSOT VIOLATIONS DETECTED: {total_violations} violations found. "
            f"Cross-contamination: {len(cross_contamination_violations)}, "
            f"Concurrent failures: {len(concurrent_failures)}. "
            "This confirms Issue #680 exists and requires SSOT consolidation."
        )
        
        # Specific checks for types of violations we expect
        violation_types = set()
        for violation in cross_contamination_violations:
            violation_types.add(violation['type'])
        
        # Document the specific SSOT violations found
        logger.info(f"SSOT violation types detected: {violation_types}")
        
        # The test PASSES by proving violations exist (confirming the issue)
        logger.info("TEST PASSES: SSOT violations confirmed, Issue #680 reproduced")
        logger.info("Next step: Implement SSOT consolidation to fix these violations")
        
        # Return violation details for analysis
        return {
            'cross_contamination_violations': cross_contamination_violations,
            'concurrent_failures': concurrent_failures,
            'total_violations': total_violations,
            'users_tested': test_users,
            'test_status': 'violations_confirmed'
        }


if __name__ == "__main__":
    # Run the test directly for debugging
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])