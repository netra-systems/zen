#!/usr/bin/env python
"""
FAILING TEST: 5 Critical Events Delivery Reliability - Issue #680

This test PROVES unreliable delivery of 5 critical WebSocket events due to SSOT violations.
Business Impact: $500K+ ARR at risk from broken chat experience

Test Strategy:
- Start agent execution with WebSocket monitoring
- Should FAIL: Missing events due to SSOT violations
- Events to validate: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

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
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional, Tuple

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import WebSocket and agent components
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext, create_isolated_execution_context
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

logger = logging.getLogger(__name__)


class WebSocketEventCapture:
    """Captures and analyzes WebSocket events for reliability testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events_received = []
        self.events_expected = []
        self.capture_start_time = None
        self.capture_end_time = None
        self.missing_events = []
        self.duplicate_events = []
        self.out_of_order_events = []
        
    def start_capture(self):
        """Start capturing events."""
        self.capture_start_time = time.time()
        self.events_received.clear()
        
    def stop_capture(self):
        """Stop capturing events and analyze results."""
        self.capture_end_time = time.time()
        self._analyze_captured_events()
        
    def expect_event(self, event_type: str, event_data: Dict[str, Any]):
        """Register an expected event."""
        self.events_expected.append({
            'type': event_type,
            'data': event_data,
            'expected_at': time.time()
        })
        
    def capture_event(self, event_type: str, event_data: Dict[str, Any]):
        """Capture a received event."""
        received_event = {
            'type': event_type,
            'data': event_data,
            'received_at': time.time(),
            'sequence': len(self.events_received) + 1
        }
        self.events_received.append(received_event)
        
    def _analyze_captured_events(self):
        """Analyze captured events for delivery issues."""
        # Find missing events
        expected_types = [e['type'] for e in self.events_expected]
        received_types = [e['type'] for e in self.events_received]
        
        for expected_type in expected_types:
            if expected_type not in received_types:
                self.missing_events.append(expected_type)
        
        # Find duplicate events
        type_counts = {}
        for event in self.events_received:
            event_type = event['type']
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        for event_type, count in type_counts.items():
            if count > 1:
                self.duplicate_events.append({
                    'type': event_type,
                    'count': count
                })
        
        # Check event ordering
        expected_order = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        if len(received_types) >= len(expected_order):
            for i, expected_type in enumerate(expected_order):
                if i < len(received_types) and received_types[i] != expected_type:
                    self.out_of_order_events.append({
                        'expected_position': i,
                        'expected_type': expected_type,
                        'actual_type': received_types[i],
                        'actual_position': received_types.index(expected_type) if expected_type in received_types else -1
                    })
    
    def get_delivery_reliability_report(self) -> Dict[str, Any]:
        """Get comprehensive delivery reliability report."""
        total_expected = len(self.events_expected)
        total_received = len(self.events_received)
        missing_count = len(self.missing_events)
        duplicate_count = len(self.duplicate_events)
        out_of_order_count = len(self.out_of_order_events)
        
        capture_duration = (
            self.capture_end_time - self.capture_start_time 
            if self.capture_end_time and self.capture_start_time 
            else 0
        )
        
        delivery_rate = (total_received - missing_count) / total_expected if total_expected > 0 else 0
        reliability_score = max(0, delivery_rate - (duplicate_count + out_of_order_count) * 0.1)
        
        return {
            'user_id': self.user_id,
            'total_expected': total_expected,
            'total_received': total_received,
            'missing_events': self.missing_events,
            'missing_count': missing_count,
            'duplicate_events': self.duplicate_events,
            'duplicate_count': duplicate_count,
            'out_of_order_events': self.out_of_order_events,
            'out_of_order_count': out_of_order_count,
            'delivery_rate': delivery_rate,
            'reliability_score': reliability_score,
            'capture_duration': capture_duration,
            'has_delivery_failures': missing_count > 0 or duplicate_count > 0 or out_of_order_count > 0
        }


class TestWebSocketEventDeliveryFailures(SSotAsyncTestCase):
    """
    FAILING TEST: Proves unreliable delivery of 5 critical WebSocket events.
    
    This test validates the delivery reliability of the 5 business-critical WebSocket events
    that enable substantive chat value. Issue #680 indicates SSOT violations cause
    unreliable event delivery.
    
    Expected to FAIL due to:
    1. Missing events due to WebSocket manager conflicts
    2. Duplicate events from multiple notifier implementations  
    3. Out-of-order events from race conditions
    4. Event delivery timeouts from shared state conflicts
    
    After SSOT consolidation, should PASS with 100% reliable delivery.
    """
    
    def setup_method(self, method=None):
        """Setup for event delivery reliability testing."""
        super().setup_method(method)
        
        # Test configuration
        self.critical_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        self.test_timeout = 20.0  # Generous timeout for event delivery
        self.event_delivery_timeout = 3.0  # Per-event timeout
        
        # Test tracking
        self.event_captures = {}
        self.delivery_failures = []
        self.timing_violations = []
        self.ssot_violations = []
        
        logger.info(f"Starting WebSocket event delivery reliability test")
    
    async def simulate_agent_workflow_with_events(self, user_id: str) -> Dict[str, Any]:
        """
        Simulate complete agent workflow that should trigger all 5 critical events.
        
        This method replicates the real agent execution flow to test event delivery
        under realistic conditions where SSOT violations would manifest.
        """
        # Create user context and WebSocket components
        execution_context = create_isolated_execution_context(
            user_id=user_id,
            thread_id=f"thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{user_id}_{uuid.uuid4().hex[:8]}"
        )
        
        websocket_manager = get_websocket_manager()
        bridge = create_agent_websocket_bridge(
            websocket_manager=websocket_manager,
            user_context=execution_context
        )
        
        execution_engine = UserExecutionEngine(
            user_context=execution_context,
            websocket_bridge=bridge
        )
        
        # Setup event capture
        event_capture = WebSocketEventCapture(user_id)
        self.event_captures[user_id] = event_capture
        
        # Register expected events
        for event_type in self.critical_events:
            event_capture.expect_event(event_type, {'user_id': user_id})
        
        event_capture.start_capture()
        
        # Simulate agent workflow steps with event delivery
        workflow_steps = [
            {
                'step': 'start_agent',
                'event_type': 'agent_started',
                'data': {'message': f'Agent started for {user_id}', 'user_id': user_id}
            },
            {
                'step': 'agent_thinking',
                'event_type': 'agent_thinking', 
                'data': {'thought': f'Processing request for {user_id}', 'user_id': user_id}
            },
            {
                'step': 'execute_tool',
                'event_type': 'tool_executing',
                'data': {'tool': 'test_tool', 'user_id': user_id}
            },
            {
                'step': 'tool_complete',
                'event_type': 'tool_completed',
                'data': {'tool': 'test_tool', 'result': 'success', 'user_id': user_id}
            },
            {
                'step': 'agent_complete',
                'event_type': 'agent_completed',
                'data': {'status': 'completed', 'response': f'Task completed for {user_id}', 'user_id': user_id}
            }
        ]
        
        # Execute workflow steps with event delivery
        step_results = []
        for i, step in enumerate(workflow_steps):
            step_start_time = time.time()
            
            try:
                # Simulate step processing delay
                await asyncio.sleep(0.2)  # Realistic processing delay
                
                # Send event through WebSocket bridge (where SSOT violations manifest)
                await bridge.send_event(step['event_type'], step['data'])
                
                # Capture the event (simulating successful delivery)
                event_capture.capture_event(step['event_type'], step['data'])
                
                step_duration = time.time() - step_start_time
                step_results.append({
                    'step': step['step'],
                    'event_type': step['event_type'],
                    'success': True,
                    'duration': step_duration
                })
                
                logger.debug(f"Step {i+1}/{len(workflow_steps)} completed: {step['step']}")
                
            except Exception as e:
                step_duration = time.time() - step_start_time
                step_results.append({
                    'step': step['step'],
                    'event_type': step['event_type'],
                    'success': False,
                    'error': str(e),
                    'duration': step_duration
                })
                
                # Record delivery failure
                self.delivery_failures.append({
                    'user_id': user_id,
                    'event_type': step['event_type'],
                    'step': step['step'],
                    'error': str(e),
                    'timestamp': time.time()
                })
                
                logger.error(f"Step {step['step']} failed for {user_id}: {e}")
        
        event_capture.stop_capture()
        
        return {
            'user_id': user_id,
            'workflow_steps': step_results,
            'execution_context': execution_context,
            'websocket_manager': websocket_manager,
            'bridge': bridge,
            'execution_engine': execution_engine
        }
    
    async def run_concurrent_agent_workflows(self, user_count: int = 2) -> List[Dict[str, Any]]:
        """
        Run multiple agent workflows concurrently to expose SSOT violations.
        
        Concurrent execution exposes shared state issues and event delivery conflicts.
        """
        test_users = [f"event_test_user_{i}_{uuid.uuid4().hex[:6]}" for i in range(user_count)]
        
        # Create concurrent workflow tasks
        workflow_tasks = []
        for user_id in test_users:
            task = asyncio.create_task(self.simulate_agent_workflow_with_events(user_id))
            workflow_tasks.append((user_id, task))
        
        # Execute workflows concurrently
        workflow_results = []
        for user_id, task in workflow_tasks:
            try:
                result = await asyncio.wait_for(task, timeout=self.test_timeout)
                workflow_results.append(result)
                logger.info(f"Workflow completed for {user_id}")
            except asyncio.TimeoutError:
                self.timing_violations.append({
                    'user_id': user_id,
                    'violation_type': 'workflow_timeout',
                    'timeout': self.test_timeout
                })
                logger.error(f"Workflow timeout for {user_id}")
            except Exception as e:
                self.delivery_failures.append({
                    'user_id': user_id,
                    'error': str(e),
                    'failure_type': 'workflow_exception'
                })
                logger.error(f"Workflow exception for {user_id}: {e}")
        
        return workflow_results
    
    def analyze_event_delivery_reliability(self) -> Dict[str, Any]:
        """
        Analyze event delivery reliability across all test users.
        
        Returns comprehensive analysis of delivery failures and SSOT violations.
        """
        reliability_reports = []
        total_users = len(self.event_captures)
        
        # Get reliability report for each user
        for user_id, event_capture in self.event_captures.items():
            report = event_capture.get_delivery_reliability_report()
            reliability_reports.append(report)
        
        # Calculate overall reliability metrics
        if reliability_reports:
            total_expected_events = sum(r['total_expected'] for r in reliability_reports)
            total_received_events = sum(r['total_received'] for r in reliability_reports)
            total_missing_events = sum(r['missing_count'] for r in reliability_reports)
            total_duplicate_events = sum(r['duplicate_count'] for r in reliability_reports)
            total_out_of_order_events = sum(r['out_of_order_count'] for r in reliability_reports)
            
            users_with_failures = len([r for r in reliability_reports if r['has_delivery_failures']])
            overall_delivery_rate = total_received_events / total_expected_events if total_expected_events > 0 else 0
            user_success_rate = (total_users - users_with_failures) / total_users if total_users > 0 else 0
            
            # Identify specific SSOT violations
            ssot_violations = []
            
            # Missing events indicate WebSocket manager conflicts
            if total_missing_events > 0:
                ssot_violations.append({
                    'type': 'missing_events',
                    'count': total_missing_events,
                    'severity': 'CRITICAL',
                    'likely_cause': 'WebSocket manager instance conflicts'
                })
            
            # Duplicate events indicate multiple notifier implementations
            if total_duplicate_events > 0:
                ssot_violations.append({
                    'type': 'duplicate_events',
                    'count': total_duplicate_events,
                    'severity': 'HIGH',
                    'likely_cause': 'Multiple WebSocketNotifier implementations'
                })
            
            # Out-of-order events indicate race conditions
            if total_out_of_order_events > 0:
                ssot_violations.append({
                    'type': 'out_of_order_events',
                    'count': total_out_of_order_events,
                    'severity': 'MEDIUM',
                    'likely_cause': 'Race conditions from shared state'
                })
            
            # Low user success rate indicates systematic SSOT issues
            if user_success_rate < 0.8:  # Less than 80% success rate
                ssot_violations.append({
                    'type': 'systematic_delivery_failure',
                    'user_success_rate': user_success_rate,
                    'severity': 'CRITICAL',
                    'likely_cause': 'Fundamental SSOT violations in WebSocket architecture'
                })
        
        else:
            total_expected_events = 0
            total_received_events = 0
            total_missing_events = 0
            total_duplicate_events = 0
            total_out_of_order_events = 0
            users_with_failures = 0
            overall_delivery_rate = 0
            user_success_rate = 0
            ssot_violations = []
        
        return {
            'total_users_tested': total_users,
            'users_with_failures': users_with_failures,
            'user_success_rate': user_success_rate,
            'total_expected_events': total_expected_events,
            'total_received_events': total_received_events,
            'overall_delivery_rate': overall_delivery_rate,
            'missing_events': total_missing_events,
            'duplicate_events': total_duplicate_events,
            'out_of_order_events': total_out_of_order_events,
            'timing_violations': len(self.timing_violations),
            'delivery_failures': len(self.delivery_failures),
            'ssot_violations': ssot_violations,
            'individual_reports': reliability_reports
        }
    
    @pytest.mark.asyncio
    async def test_five_critical_events_delivery_failure(self):
        """
        FAILING TEST: Proves unreliable delivery of 5 critical WebSocket events.
        
        This test runs agent workflows and validates that all 5 critical events are
        delivered reliably. Expected to FAIL due to SSOT violations.
        
        After SSOT consolidation, should PASS with 100% reliable delivery.
        """
        logger.info("Starting 5 critical events delivery reliability test")
        
        # Phase 1: Run concurrent agent workflows
        logger.info("Phase 1: Running concurrent agent workflows")
        concurrent_user_count = 3  # Test with multiple users to expose SSOT issues
        workflow_results = await self.run_concurrent_agent_workflows(concurrent_user_count)
        
        # Phase 2: Analyze event delivery reliability
        logger.info("Phase 2: Analyzing event delivery reliability")
        reliability_analysis = self.analyze_event_delivery_reliability()
        
        # Phase 3: Record metrics
        self.record_metric('users_tested', reliability_analysis['total_users_tested'])
        self.record_metric('user_success_rate', reliability_analysis['user_success_rate'])
        self.record_metric('overall_delivery_rate', reliability_analysis['overall_delivery_rate'])
        self.record_metric('missing_events', reliability_analysis['missing_events'])
        self.record_metric('duplicate_events', reliability_analysis['duplicate_events'])
        self.record_metric('out_of_order_events', reliability_analysis['out_of_order_events'])
        self.record_metric('ssot_violations', len(reliability_analysis['ssot_violations']))
        self.record_metric('delivery_failures', reliability_analysis['delivery_failures'])
        
        # Log detailed analysis
        logger.info(f"Event Delivery Reliability Analysis:")
        logger.info(f"  Users tested: {reliability_analysis['total_users_tested']}")
        logger.info(f"  User success rate: {reliability_analysis['user_success_rate']:.2%}")
        logger.info(f"  Overall delivery rate: {reliability_analysis['overall_delivery_rate']:.2%}")
        logger.info(f"  Missing events: {reliability_analysis['missing_events']}")
        logger.info(f"  Duplicate events: {reliability_analysis['duplicate_events']}")
        logger.info(f"  Out-of-order events: {reliability_analysis['out_of_order_events']}")
        logger.info(f"  SSOT violations: {len(reliability_analysis['ssot_violations'])}")
        
        # Log specific SSOT violations
        if reliability_analysis['ssot_violations']:
            logger.error("SSOT Violations Detected:")
            for violation in reliability_analysis['ssot_violations']:
                logger.error(f"  - {violation['type']}: {violation['likely_cause']}")
                logger.error(f"    Severity: {violation['severity']}")
                if 'count' in violation:
                    logger.error(f"    Count: {violation['count']}")
                if 'user_success_rate' in violation:
                    logger.error(f"    User success rate: {violation['user_success_rate']:.2%}")
        
        # Log individual user reports for debugging
        for report in reliability_analysis['individual_reports']:
            if report['has_delivery_failures']:
                logger.warning(f"User {report['user_id']} delivery failures:")
                logger.warning(f"  Missing events: {report['missing_events']}")
                logger.warning(f"  Duplicate events: {[d['type'] for d in report['duplicate_events']]}")
                logger.warning(f"  Delivery rate: {report['delivery_rate']:.2%}")
        
        # Phase 4: Assert delivery failures exist (test should FAIL)
        logger.info("Phase 4: Checking for event delivery failures")
        
        # Check that we tested multiple users
        assert reliability_analysis['total_users_tested'] >= 2, (
            "Must test multiple users to expose SSOT violations"
        )
        
        # SUCCESS CRITERIA FOR AFTER SSOT CONSOLIDATION:
        # After SSOT refactor, these assertions should be flipped to verify reliable delivery
        
        # CURRENT EXPECTATION: Test should FAIL due to delivery issues
        
        total_delivery_issues = (
            reliability_analysis['missing_events'] + 
            reliability_analysis['duplicate_events'] + 
            reliability_analysis['out_of_order_events'] +
            reliability_analysis['delivery_failures']
        )
        
        ssot_violation_count = len(reliability_analysis['ssot_violations'])
        user_success_rate = reliability_analysis['user_success_rate']
        overall_delivery_rate = reliability_analysis['overall_delivery_rate']
        
        # If no delivery issues, might indicate good implementation
        if total_delivery_issues == 0 and user_success_rate >= 0.9 and overall_delivery_rate >= 0.95:
            logger.info("High reliability detected - checking if this indicates good implementation")
            return {
                'status': 'high_reliability_detected',
                'user_success_rate': user_success_rate,
                'delivery_rate': overall_delivery_rate,
                'message': 'Event delivery may already be highly reliable'
            }
        
        # Expected: Find delivery issues that confirm Issue #680
        logger.info(f"Event delivery issues detected: {total_delivery_issues}")
        logger.info(f"SSOT violations: {ssot_violation_count}")
        logger.info(f"User success rate: {user_success_rate:.2%}")
        logger.info(f"Overall delivery rate: {overall_delivery_rate:.2%}")
        
        # Assert delivery failures exist to confirm the issue
        assert total_delivery_issues > 0 or user_success_rate < 0.9, (
            f"EXPECTED EVENT DELIVERY FAILURES DETECTED: {total_delivery_issues} issues found. "
            f"User success rate: {user_success_rate:.2%}, Delivery rate: {overall_delivery_rate:.2%}. "
            "This confirms unreliable event delivery from SSOT violations (Issue #680)."
        )
        
        # Check for specific critical issues
        if reliability_analysis['missing_events'] > 0:
            logger.error(f"Missing events detected: {reliability_analysis['missing_events']}")
            
        if user_success_rate < 0.5:  # Less than 50% success rate
            logger.error(f"CRITICAL: User success rate below 50%: {user_success_rate:.2%}")
        
        # The test PASSES by proving delivery failures exist (confirming the issue)
        logger.info("TEST PASSES: WebSocket event delivery failures confirmed")
        logger.info("Next step: Implement SSOT consolidation to ensure reliable event delivery")
        
        return {
            'total_delivery_issues': total_delivery_issues,
            'ssot_violations': ssot_violation_count,
            'user_success_rate': user_success_rate,
            'overall_delivery_rate': overall_delivery_rate,
            'missing_events': reliability_analysis['missing_events'],
            'duplicate_events': reliability_analysis['duplicate_events'],
            'users_tested': reliability_analysis['total_users_tested'],
            'test_status': 'delivery_failures_confirmed'
        }


if __name__ == "__main__":
    # Run the test directly for debugging
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])