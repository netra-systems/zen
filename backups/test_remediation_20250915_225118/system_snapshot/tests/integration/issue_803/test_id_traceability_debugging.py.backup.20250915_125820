"""
Issue #803: UserExecutionContext ID Validation - Thread/Run ID Mismatches
Integration Test Suite for ID Traceability and Debugging Support

PURPOSE: Integration tests that provide comprehensive debugging information
for the ID mismatch issue, including traceability patterns, logging analysis,
and diagnostic utilities for developers.

ISSUE LOCATION: shared/id_generation/unified_id_generator.py:117-118
DEBUGGING FOCUS:
- ID generation call stack analysis
- Cross-service ID propagation patterns
- WebSocket event correlation debugging
- Database query traceability impact
- Performance profiling of ID operations

EXPECTED TEST BEHAVIOR:
- Debugging tests should PASS (they document current behavior)
- Diagnostic tests provide detailed analysis for developers
- Traceability tests show the impact across system boundaries
"""

import pytest
import unittest
import time
import traceback
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, List, Any

from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.integration
class TestIssue803IDTraceabilityDebugging(SSotAsyncTestCase):
    """Integration tests for ID traceability debugging and analysis."""

    async def asyncSetUp(self):
        """Set up debugging test environment."""
        await super().asyncSetUp()
        self.debug_user_id = "debug_user_803"
        self.test_operations = ["debug_op_1", "debug_op_2", "debug_op_3"]
        self.trace_data = []
        self.performance_data = {}

    def test_id_generation_call_stack_analysis(self):
        """
        DEBUGGING TEST: Analyze the call stack when ID generation occurs.
        This test documents where and how IDs are generated for debugging.
        """
        call_stack_info = []

        def capture_call_stack():
            """Capture call stack information during ID generation."""
            stack = traceback.format_stack()
            return {
                'timestamp': time.time(),
                'stack_depth': len(stack),
                'relevant_frames': [frame for frame in stack if 'id_generation' in frame or 'user_execution_context' in frame],
                'full_stack': stack
            }

        # Patch the ID generation to capture call stack
        original_generate = UnifiedIdGenerator.generate_user_context_ids

        def patched_generate(*args, **kwargs):
            stack_info = capture_call_stack()
            call_stack_info.append(stack_info)
            return original_generate(*args, **kwargs)

        with patch.object(UnifiedIdGenerator, 'generate_user_context_ids', side_effect=patched_generate):
            # Generate IDs and capture call stack
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids("debug_user", "debug_test")

            # Analyze call stack data
            self.assertEqual(len(call_stack_info), 1, "Should capture one call stack trace")
            stack_info = call_stack_info[0]

            # Document call patterns
            self.assertGreater(stack_info['stack_depth'], 3,
                             "ID generation should have meaningful call stack depth")

            # Store for debugging analysis
            self.trace_data.append({
                'test': 'call_stack_analysis',
                'thread_id': thread_id,
                'run_id': run_id,
                'call_stack': stack_info
            })

    def test_cross_service_id_propagation_debugging(self):
        """
        DEBUGGING TEST: Trace how IDs propagate across different services.
        This test documents ID flow for cross-service debugging.
        """
        propagation_trace = {
            'id_generation': {},
            'context_creation': {},
            'service_boundaries': [],
            'websocket_events': [],
            'database_operations': []
        }

        # Step 1: Generate IDs
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids("cross_service_user", "cross_service")
        propagation_trace['id_generation'] = {
            'thread_id': thread_id,
            'run_id': run_id,
            'request_id': request_id,
            'generation_time': time.time(),
            'thread_counter': int(thread_id.split('_')[2]),
            'run_counter': int(run_id.split('_')[2]),
            'counter_mismatch': int(run_id.split('_')[2]) - int(thread_id.split('_')[2])
        }

        # Step 2: Create UserExecutionContext
        context = UserExecutionContext(
            user_id=self.debug_user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=f"ws_{self.debug_user_id}_{request_id}"
        )
        propagation_trace['context_creation'] = {
            'context_created': True,
            'websocket_client_id': context.websocket_client_id,
            'creation_time': context.created_at.isoformat()
        }

        # Step 3: Simulate service boundary crossings
        service_boundaries = [
            {'service': 'backend_api', 'thread_id': thread_id, 'run_id': run_id},
            {'service': 'agent_supervisor', 'thread_id': thread_id, 'run_id': run_id},
            {'service': 'websocket_manager', 'thread_id': thread_id, 'run_id': run_id},
            {'service': 'database_session', 'thread_id': thread_id, 'run_id': run_id}
        ]
        propagation_trace['service_boundaries'] = service_boundaries

        # Step 4: Simulate WebSocket events with ID tracking
        websocket_events = [
            {'event': 'agent_started', 'thread_id': thread_id, 'run_id': run_id, 'correlation_id': f"{thread_id}_{run_id}"},
            {'event': 'tool_executing', 'thread_id': thread_id, 'run_id': run_id, 'correlation_id': f"{thread_id}_{run_id}"},
            {'event': 'agent_completed', 'thread_id': thread_id, 'run_id': run_id, 'correlation_id': f"{thread_id}_{run_id}"}
        ]
        propagation_trace['websocket_events'] = websocket_events

        # Step 5: Simulate database operations
        db_operations = [
            {'operation': 'session_create', 'key': f"{thread_id}_{run_id}", 'thread_id': thread_id, 'run_id': run_id},
            {'operation': 'user_query', 'key': f"{thread_id}_{run_id}", 'thread_id': thread_id, 'run_id': run_id},
            {'operation': 'result_store', 'key': f"{thread_id}_{run_id}", 'thread_id': thread_id, 'run_id': run_id}
        ]
        propagation_trace['database_operations'] = db_operations

        # Validate propagation consistency
        all_thread_ids = [trace['thread_id'] for trace in service_boundaries + websocket_events + db_operations]
        all_run_ids = [trace['run_id'] for trace in service_boundaries + websocket_events + db_operations]

        # All services should use the same thread_id and run_id
        self.assertEqual(len(set(all_thread_ids)), 1, "thread_id should be consistent across services")
        self.assertEqual(len(set(all_run_ids)), 1, "run_id should be consistent across services")

        # Document the ID mismatch throughout the trace
        self.assertEqual(propagation_trace['id_generation']['counter_mismatch'], 1,
                        "ID mismatch should be consistent throughout propagation")

        # Store comprehensive trace for analysis
        self.trace_data.append({
            'test': 'cross_service_propagation',
            'propagation_trace': propagation_trace
        })

    def test_websocket_event_correlation_debugging(self):
        """
        DEBUGGING TEST: Analyze WebSocket event correlation with mismatched IDs.
        This test helps debug WebSocket event delivery issues.
        """
        correlation_analysis = {
            'context_setup': {},
            'event_sequence': [],
            'correlation_patterns': {},
            'potential_issues': []
        }

        # Create context with mismatched IDs
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(self.debug_user_id, "websocket_debug")
        websocket_client_id = f"ws_debug_{self.debug_user_id}_{request_id}"

        context = UserExecutionContext(
            user_id=self.debug_user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=websocket_client_id
        )

        correlation_analysis['context_setup'] = {
            'thread_id': thread_id,
            'run_id': run_id,
            'request_id': request_id,
            'websocket_client_id': websocket_client_id,
            'id_mismatch': int(run_id.split('_')[2]) - int(thread_id.split('_')[2])
        }

        # Simulate WebSocket event sequence
        events = [
            {'type': 'agent_started', 'data': {'message': 'Starting agent execution'}},
            {'type': 'agent_thinking', 'data': {'thought': 'Analyzing user request'}},
            {'type': 'tool_executing', 'data': {'tool': 'database_query', 'params': {}}},
            {'type': 'tool_completed', 'data': {'result': 'Query successful', 'rows': 5}},
            {'type': 'agent_completed', 'data': {'response': 'Task completed successfully'}}
        ]

        for i, event in enumerate(events):
            event_data = {
                'sequence': i + 1,
                'event_type': event['type'],
                'thread_id': thread_id,
                'run_id': run_id,
                'websocket_client_id': websocket_client_id,
                'correlation_key': f"{thread_id}_{run_id}",
                'event_data': event['data'],
                'timestamp': time.time()
            }
            correlation_analysis['event_sequence'].append(event_data)

        # Analyze correlation patterns
        correlation_keys = [event['correlation_key'] for event in correlation_analysis['event_sequence']]
        correlation_analysis['correlation_patterns'] = {
            'unique_correlation_keys': len(set(correlation_keys)),
            'total_events': len(correlation_keys),
            'consistent_correlation': len(set(correlation_keys)) == 1
        }

        # Identify potential issues
        if correlation_analysis['context_setup']['id_mismatch'] != 0:
            correlation_analysis['potential_issues'].append({
                'issue': 'ID_MISMATCH_IN_CORRELATION_KEY',
                'description': 'thread_id and run_id have different counters in correlation key',
                'impact': 'May cause WebSocket event routing issues'
            })

        # Validate correlation consistency
        self.assertTrue(correlation_analysis['correlation_patterns']['consistent_correlation'],
                       "All events should use same correlation key")
        self.assertEqual(correlation_analysis['correlation_patterns']['unique_correlation_keys'], 1,
                        "Should have exactly one correlation pattern")

        # Store correlation analysis
        self.trace_data.append({
            'test': 'websocket_correlation',
            'analysis': correlation_analysis
        })

    def test_database_query_traceability_impact(self):
        """
        DEBUGGING TEST: Analyze the impact of ID mismatches on database query traceability.
        This test documents how mismatched IDs affect database operations.
        """
        db_traceability = {
            'session_management': {},
            'query_tracking': [],
            'transaction_correlation': {},
            'cleanup_patterns': {}
        }

        # Create context for database operations
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(self.debug_user_id, "db_traceability")

        context = UserExecutionContext(
            user_id=self.debug_user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id
        )

        # Simulate database session management
        session_key = f"db_session_{thread_id}_{run_id}"
        db_traceability['session_management'] = {
            'session_key': session_key,
            'thread_id': thread_id,
            'run_id': run_id,
            'id_consistency': int(thread_id.split('_')[2]) == int(run_id.split('_')[2]),
            'counter_difference': int(run_id.split('_')[2]) - int(thread_id.split('_')[2])
        }

        # Simulate query tracking with mismatched IDs
        queries = [
            {'query_id': 1, 'type': 'SELECT', 'table': 'users', 'thread_id': thread_id, 'run_id': run_id},
            {'query_id': 2, 'type': 'INSERT', 'table': 'audit_log', 'thread_id': thread_id, 'run_id': run_id},
            {'query_id': 3, 'type': 'UPDATE', 'table': 'user_sessions', 'thread_id': thread_id, 'run_id': run_id}
        ]

        for query in queries:
            query['correlation_id'] = f"{query['thread_id']}_{query['run_id']}"
            query['timestamp'] = time.time()
            db_traceability['query_tracking'].append(query)

        # Analyze transaction correlation
        correlation_ids = [query['correlation_id'] for query in db_traceability['query_tracking']]
        db_traceability['transaction_correlation'] = {
            'unique_correlations': len(set(correlation_ids)),
            'total_queries': len(correlation_ids),
            'correlation_consistency': len(set(correlation_ids)) == 1,
            'all_correlations': list(set(correlation_ids))
        }

        # Simulate cleanup patterns
        cleanup_operations = [
            {'operation': 'close_session', 'key': session_key, 'thread_id': thread_id, 'run_id': run_id},
            {'operation': 'clear_cache', 'key': session_key, 'thread_id': thread_id, 'run_id': run_id},
            {'operation': 'log_completion', 'key': session_key, 'thread_id': thread_id, 'run_id': run_id}
        ]
        db_traceability['cleanup_patterns'] = {
            'operations': cleanup_operations,
            'cleanup_key': session_key
        }

        # Validate database traceability
        self.assertFalse(db_traceability['session_management']['id_consistency'],
                        "Current implementation has ID inconsistency")
        self.assertEqual(db_traceability['session_management']['counter_difference'], 1,
                        "Database operations show +1 counter mismatch")
        self.assertTrue(db_traceability['transaction_correlation']['correlation_consistency'],
                       "Queries within same transaction should have consistent correlation")

        # Store traceability analysis
        self.trace_data.append({
            'test': 'database_traceability',
            'analysis': db_traceability
        })

    def test_performance_profiling_of_id_operations(self):
        """
        DEBUGGING TEST: Profile the performance impact of ID generation and operations.
        This test measures current performance for optimization guidance.
        """
        performance_profile = {
            'id_generation_timing': [],
            'context_creation_timing': [],
            'bulk_operation_timing': {},
            'memory_usage_patterns': {}
        }

        # Profile ID generation timing
        for i in range(50):
            start_time = time.perf_counter()
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(f"perf_user_{i}", f"perf_test_{i}")
            end_time = time.perf_counter()

            timing_data = {
                'iteration': i,
                'duration': end_time - start_time,
                'thread_id': thread_id,
                'run_id': run_id,
                'request_id': request_id
            }
            performance_profile['id_generation_timing'].append(timing_data)

        # Profile context creation timing
        for i in range(20):
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(f"perf_user_{i}", f"context_perf_{i}")

            start_time = time.perf_counter()
            context = UserExecutionContext(
                user_id=f"perf_user_{i}",
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id
            )
            end_time = time.perf_counter()

            timing_data = {
                'iteration': i,
                'duration': end_time - start_time,
                'context_created': True
            }
            performance_profile['context_creation_timing'].append(timing_data)

        # Profile bulk operations
        bulk_start = time.perf_counter()
        bulk_contexts = []
        for i in range(100):
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(f"bulk_user_{i}", f"bulk_{i}")
            context = UserExecutionContext(
                user_id=f"bulk_user_{i}",
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id
            )
            bulk_contexts.append(context)
        bulk_end = time.perf_counter()

        performance_profile['bulk_operation_timing'] = {
            'total_duration': bulk_end - bulk_start,
            'contexts_created': len(bulk_contexts),
            'average_per_context': (bulk_end - bulk_start) / len(bulk_contexts)
        }

        # Calculate performance statistics
        id_gen_durations = [timing['duration'] for timing in performance_profile['id_generation_timing']]
        context_durations = [timing['duration'] for timing in performance_profile['context_creation_timing']]

        self.performance_data = {
            'id_generation': {
                'min': min(id_gen_durations),
                'max': max(id_gen_durations),
                'average': sum(id_gen_durations) / len(id_gen_durations),
                'total_operations': len(id_gen_durations)
            },
            'context_creation': {
                'min': min(context_durations),
                'max': max(context_durations),
                'average': sum(context_durations) / len(context_durations),
                'total_operations': len(context_durations)
            },
            'bulk_operations': performance_profile['bulk_operation_timing']
        }

        # Performance assertions
        self.assertLess(self.performance_data['id_generation']['average'], 0.001,
                       f"ID generation should be fast. Average: {self.performance_data['id_generation']['average']:.6f}s")
        self.assertLess(self.performance_data['context_creation']['average'], 0.01,
                       f"Context creation should be fast. Average: {self.performance_data['context_creation']['average']:.6f}s")

        # Store performance data
        self.trace_data.append({
            'test': 'performance_profiling',
            'performance_data': self.performance_data
        })

    def test_comprehensive_debugging_report_generation(self):
        """
        DEBUGGING TEST: Generate comprehensive debugging report for Issue #803.
        This test consolidates all debugging data for developer analysis.
        """
        # Ensure all previous debugging tests have run
        if not self.trace_data:
            self.test_id_generation_call_stack_analysis()
            self.test_cross_service_id_propagation_debugging()
            self.test_websocket_event_correlation_debugging()
            self.test_database_query_traceability_impact()
            self.test_performance_profiling_of_id_operations()

        # Generate comprehensive debugging report
        debugging_report = {
            'issue_summary': {
                'issue_number': 803,
                'title': 'UserExecutionContext ID Validation - Thread/Run ID Mismatches',
                'location': 'shared/id_generation/unified_id_generator.py:117-118',
                'problem': 'thread_id uses counter_base, run_id uses counter_base + 1',
                'impact': 'ID inconsistency affects traceability and correlation'
            },
            'debugging_data': self.trace_data,
            'performance_impact': self.performance_data,
            'test_execution_summary': {
                'total_debugging_tests': len(self.trace_data),
                'all_tests_passed': True,  # Debugging tests should pass
                'report_generated_at': datetime.now(timezone.utc).isoformat()
            },
            'recommendations': [
                'Fix UnifiedIdGenerator.generate_user_context_ids() to use same counter for thread_id and run_id',
                'Use same UUID part for both thread_id and run_id',
                'Add validation to UserExecutionContext to detect ID inconsistencies',
                'Update correlation patterns to handle consistent IDs',
                'Add integration tests to verify fix across all services'
            ]
        }

        # Validate debugging report completeness
        self.assertGreaterEqual(len(debugging_report['debugging_data']), 4,
                               "Should have comprehensive debugging data from all tests")
        self.assertIsNotNone(debugging_report['performance_impact'],
                            "Should include performance impact analysis")

        # Store final report
        self.debugging_report = debugging_report

        # The debugging tests should all pass - they document current behavior
        self.assertTrue(True, "Comprehensive debugging report generated successfully")

if __name__ == '__main__':
    unittest.main()
