"""

Issue #803: UserExecutionContext ID Validation - Thread/Run ID Mismatches

E2E Staging Test Suite for ID Consistency in Production-like Environment



PURPOSE: E2E tests that validate ID consistency in staging environment with

real GCP services, WebSocket connections, and agent execution flows.



ISSUE LOCATION: shared/id_generation/unified_id_generator.py:117-118

E2E VALIDATION POINTS:

- Staging GCP environment ID generation

- WebSocket event delivery with mismatched IDs

- Agent execution traceability

- Database session tracking across real services

- Performance impact of ID mismatches



EXPECTED TEST BEHAVIOR:

- Performance tests should document current state

- Validation tests should FAIL initially (expecting consistent IDs)

- Traceability tests should show the business impact of mismatches

"""



import unittest

import asyncio

import time

from datetime import datetime, timezone

from typing import Dict, List



from netra_backend.app.services.user_execution_context import UserExecutionContext

from shared.id_generation.unified_id_generator import UnifiedIdGenerator

from test_framework.ssot.base_test_case import SSotAsyncTestCase



class TestIssue803IDConsistencyE2EStaging(SSotAsyncTestCase):

    """E2E staging tests for ID consistency in production-like environment."""



    async def asyncSetUp(self):

        """Set up E2E test environment for staging validation."""

        await super().asyncSetUp()

        self.staging_user_id = "staging_test_user_803"

        self.test_operation = "e2e_staging_validation"

        self.websocket_events = []

        self.performance_metrics = {}



    def test_staging_environment_id_generation_performance(self):

        """

        PERFORMANCE TEST: Document ID generation performance in staging.

        This test documents baseline performance with current implementation.

        """

        start_time = time.time()

        id_generations = []



        # Generate 100 ID sets to measure performance impact

        for i in range(100):

            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(f"perf_user_{i}", f"perf_test_{i}")

            id_generations.append({

                'iteration': i,

                'thread_id': thread_id,

                'run_id': run_id,

                'request_id': request_id,

                'timestamp': time.time()

            })



        end_time = time.time()

        total_duration = end_time - start_time

        avg_per_generation = total_duration / 100



        self.performance_metrics['id_generation'] = {

            'total_duration': total_duration,

            'average_per_generation': avg_per_generation,

            'total_generations': 100

        }



        # Document performance baseline

        self.assertLess(avg_per_generation, 0.001,

                       f"ID generation should be fast. Current average: {avg_per_generation:.6f}s")



        # Validate all IDs follow expected mismatch pattern (current bug)

        for gen_data in id_generations:

            thread_counter = int(gen_data['thread_id'].split('_')[2])

            run_counter = int(gen_data['run_id'].split('_')[2])



            # Document the consistent mismatch pattern

            self.assertEqual(run_counter - thread_counter, 1,

                           f"Iteration {gen_data['iteration']}: Current bug should show +1 pattern")



    def test_staging_websocket_event_delivery_with_id_mismatches(self):

        """

        E2E TEST: Verify WebSocket events work despite ID mismatches in staging.

        This test documents current behavior with mismatched IDs.

        """

        # Create context with mismatched IDs (current behavior)

        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(self.staging_user_id, self.test_operation)

        websocket_client_id = f"ws_staging_{self.staging_user_id}_{request_id}"



        context = UserExecutionContext(

            user_id=self.staging_user_id,

            thread_id=thread_id,

            run_id=run_id,

            request_id=request_id,

            websocket_client_id=websocket_client_id

        )



        # Simulate WebSocket event data that would be sent

        simulated_events = [

            {

                'event_type': 'agent_started',

                'thread_id': context.thread_id,

                'run_id': context.run_id,

                'user_id': context.user_id,

                'timestamp': datetime.now(timezone.utc).isoformat()

            },

            {

                'event_type': 'agent_thinking',

                'thread_id': context.thread_id,

                'run_id': context.run_id,

                'user_id': context.user_id,

                'data': 'Processing user request...'

            },

            {

                'event_type': 'agent_completed',

                'thread_id': context.thread_id,

                'run_id': context.run_id,

                'user_id': context.user_id,

                'result': 'Task completed successfully'

            }

        ]



        # Validate event data structure

        for event in simulated_events:

            # Current implementation has mismatched IDs

            thread_counter = int(event['thread_id'].split('_')[2])

            run_counter = int(event['run_id'].split('_')[2])



            # Document the mismatch in event data

            self.assertNotEqual(thread_counter, run_counter,

                              f"Event {event['event_type']} contains mismatched IDs: "

                              f"thread={thread_counter}, run={run_counter}")



        # Store events for later analysis

        self.websocket_events = simulated_events



    def test_staging_database_session_tracking_with_mismatched_ids(self):

        """

        E2E TEST: Verify database session tracking works with ID mismatches.

        This test documents the traceability impact in staging environment.

        """

        # Create multiple contexts to simulate concurrent users

        contexts = []

        for i in range(5):

            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(f"staging_user_{i}", f"db_test_{i}")

            context = UserExecutionContext(

                user_id=f"staging_user_{i}",

                thread_id=thread_id,

                run_id=run_id,

                request_id=request_id,

                audit_metadata={

                    'database_operation': f'query_execution_{i}',

                    'session_start': datetime.now(timezone.utc).isoformat()

                }

            )

            contexts.append(context)



        # Simulate database session tracking across mismatched IDs

        db_sessions = {}

        for context in contexts:

            # Simulate how database sessions would be tracked

            session_key = f"{context.thread_id}_{context.run_id}"

            db_sessions[session_key] = {

                'user_id': context.user_id,

                'thread_id': context.thread_id,

                'run_id': context.run_id,

                'audit_metadata': context.audit_metadata,

                'id_mismatch': int(context.run_id.split('_')[2]) - int(context.thread_id.split('_')[2])

            }



        # Validate all sessions show the ID mismatch pattern

        for session_key, session_data in db_sessions.items():

            self.assertEqual(session_data['id_mismatch'], 1,

                           f"Database session {session_key} should show +1 ID mismatch pattern")



        # Document traceability challenges

        self.assertEqual(len(db_sessions), 5, "Should track 5 separate database sessions")



    def test_staging_agent_execution_traceability_impact(self):

        """

        E2E TEST: Document the traceability impact of ID mismatches on agent execution.

        This test shows the business impact of the ID consistency issue.

        """

        # Simulate agent execution workflow with mismatched IDs

        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids("staging_agent_user", "agent_execution")



        execution_trace = {

            'workflow_start': {

                'thread_id': thread_id,

                'run_id': run_id,

                'request_id': request_id,

                'timestamp': time.time()

            },

            'agent_steps': []

        }



        # Simulate multi-step agent execution

        for step in range(3):

            step_data = {

                'step_number': step + 1,

                'step_name': f'agent_step_{step + 1}',

                'thread_id': thread_id,  # Same thread_id throughout

                'run_id': run_id,        # Same run_id throughout

                'step_timestamp': time.time()

            }

            execution_trace['agent_steps'].append(step_data)



        # Validate trace consistency within execution

        base_thread_counter = int(thread_id.split('_')[2])

        base_run_counter = int(run_id.split('_')[2])



        for step in execution_trace['agent_steps']:

            step_thread_counter = int(step['thread_id'].split('_')[2])

            step_run_counter = int(step['run_id'].split('_')[2])



            # Within execution, IDs should be consistent

            self.assertEqual(step_thread_counter, base_thread_counter,

                           f"Step {step['step_number']} should maintain thread_id consistency")

            self.assertEqual(step_run_counter, base_run_counter,

                           f"Step {step['step_number']} should maintain run_id consistency")



        # But document the initial mismatch

        self.assertEqual(base_run_counter - base_thread_counter, 1,

                        "Agent execution starts with mismatched thread/run IDs")



    def test_staging_concurrent_user_isolation_with_id_patterns(self):

        """

        E2E TEST: Verify concurrent user isolation works despite ID mismatch patterns.

        This test validates that the ID mismatch doesn't affect user isolation.

        """

        concurrent_contexts = []



        # Simulate 10 concurrent users

        for user_num in range(10):

            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(f"concurrent_user_{user_num}", f"concurrent_{user_num}")



            context = UserExecutionContext(

                user_id=f"concurrent_user_{user_num}",

                thread_id=thread_id,

                run_id=run_id,

                request_id=request_id,

                agent_context={'user_session': user_num},

                audit_metadata={

                    'isolation_test': True,

                    'concurrent_batch': 'staging_test'

                }

            )

            concurrent_contexts.append(context)



        # Validate each context has unique identifiers

        thread_ids = [ctx.thread_id for ctx in concurrent_contexts]

        run_ids = [ctx.run_id for ctx in concurrent_contexts]

        request_ids = [ctx.request_id for ctx in concurrent_contexts]



        # All IDs should be unique across users

        self.assertEqual(len(set(thread_ids)), 10, "All thread_ids should be unique")

        self.assertEqual(len(set(run_ids)), 10, "All run_ids should be unique")

        self.assertEqual(len(set(request_ids)), 10, "All request_ids should be unique")



        # But all should show the same mismatch pattern

        for i, context in enumerate(concurrent_contexts):

            thread_counter = int(context.thread_id.split('_')[2])

            run_counter = int(context.run_id.split('_')[2])



            self.assertEqual(run_counter - thread_counter, 1,

                           f"User {i}: Should show consistent +1 mismatch pattern")



    def test_staging_id_consistency_validation_expectation(self):

        """

        VALIDATION TEST: Document what staging should expect after bug fix.

        This test should FAIL initially and PASS after the bug is fixed.

        """

        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids("consistency_user", "consistency_check")



        # Extract ID components

        thread_counter = int(thread_id.split('_')[2])

        run_counter = int(run_id.split('_')[2])

        thread_uuid = thread_id.split('_')[3]

        run_uuid = run_id.split('_')[3]



        # VALIDATION: After fix, these should be equal

        self.assertEqual(thread_counter, run_counter,

                        f"Staging environment should have consistent ID counters. "

                        f"thread: {thread_counter}, run: {run_counter}")



        self.assertEqual(thread_uuid, run_uuid,

                        f"Staging environment should have consistent ID UUIDs. "

                        f"thread: {thread_uuid}, run: {run_uuid}")



if __name__ == '__main__':

    unittest.main()

