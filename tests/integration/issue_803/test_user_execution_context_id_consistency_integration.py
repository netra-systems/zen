"""

Issue #803: UserExecutionContext ID Validation - Thread/Run ID Mismatches

Integration Test Suite for UserExecutionContext ID Consistency



PURPOSE: Integration tests that validate UserExecutionContext ID consistency

with real database sessions and UserExecutionContext factory methods.



ISSUE LOCATION: shared/id_generation/unified_id_generator.py:117-118

INTEGRATION POINTS:

- UserExecutionContext factory methods

- Database session management

- Real WebSocket connections

- Agent context creation



EXPECTED TEST BEHAVIOR:

- Validation tests should FAIL initially (they expect consistent IDs)

- These tests will pass once the ID generation bug is fixed

"""



import unittest

import asyncio

from unittest.mock import patch

from datetime import datetime, timezone



from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError

from shared.id_generation.unified_id_generator import UnifiedIdGenerator

from test_framework.ssot.base_test_case import SSotAsyncTestCase



class TestIssue803UserExecutionContextIDConsistency(SSotAsyncTestCase):

    """Integration tests for UserExecutionContext ID consistency validation."""



    def setUp(self):

        """Set up test fixtures for integration testing."""

        super().setUp()

        self.test_user_id = "test_user_12345"

        self.test_operation = "integrationtest"



    def test_user_execution_context_uses_mismatched_ids(self):

        """

        VALIDATION TEST: Verify UserExecutionContext detects ID inconsistency.

        This test should FAIL initially because it expects consistent IDs.

        After the bug is fixed, this test should PASS.

        """

        # Test data

        test_user_id = "testuser12345"

        test_operation = "integrationtest"



        # Generate IDs using the current (buggy) implementation

        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(test_user_id, test_operation)



        # Create UserExecutionContext with the generated IDs

        context = UserExecutionContext(

            user_id=test_user_id,

            thread_id=thread_id,

            run_id=run_id,

            request_id=request_id

        )



        # Extract counter parts from the IDs for validation

        thread_counter = int(thread_id.split('_')[2])

        run_counter = int(run_id.split('_')[2])



        # VALIDATION: These should be equal for consistency (will fail with current bug)

        self.assertEqual(thread_counter, run_counter,

                        f"UserExecutionContext should use consistent counter values. "

                        f"thread_id counter: {thread_counter}, run_id counter: {run_counter}")



        # VALIDATION: UUIDs should also be consistent

        thread_uuid = thread_id.split('_')[3]

        run_uuid = run_id.split('_')[3]

        self.assertEqual(thread_uuid, run_uuid,

                        f"UserExecutionContext should use consistent UUID parts. "

                        f"thread_uuid: {thread_uuid}, run_uuid: {run_uuid}")



    def test_multiple_contexts_show_consistent_id_relationship(self):

        """

        VALIDATION TEST: Verify multiple UserExecutionContext instances maintain ID consistency.

        This test should FAIL initially due to the ID generation bug.

        """

        contexts = []



        for i in range(3):

            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(f"user_{i}", f"test_{i}")

            context = UserExecutionContext(

                user_id=f"user_{i}",

                thread_id=thread_id,

                run_id=run_id,

                request_id=request_id

            )

            contexts.append(context)



        # Validate each context has consistent IDs

        for i, context in enumerate(contexts):

            thread_counter = int(context.thread_id.split('_')[2])

            run_counter = int(context.run_id.split('_')[2])



            # This validation will fail with current bug

            self.assertEqual(thread_counter, run_counter,

                           f"Context {i}: thread and run IDs should have same counter. "

                           f"Got thread: {thread_counter}, run: {run_counter}")



    async def test_user_execution_context_factory_method_id_consistency(self):

        """

        INTEGRATION TEST: Verify UserExecutionContext factory methods create consistent IDs.

        This test should FAIL initially due to the underlying ID generation bug.

        """

        # Mock request data for factory method

        mock_request_data = {

            'user_id': self.test_user_id,

            'headers': {

                'user-agent': 'test-browser',

                'x-forwarded-for': '192.168.1.100'

            }

        }



        # Test the enhanced factory method

        context = UserExecutionContext.from_request_enhanced(

            user_id=self.test_user_id,

            thread_id=None,  # Will be auto-generated

            run_id=None,     # Will be auto-generated

            request_data=mock_request_data,

            operation="factory_test",

            agent_context={"test": "data"},

            audit_metadata={"source": "integration_test"}

        )



        # Validate the generated IDs are consistent

        thread_counter = int(context.thread_id.split('_')[2])

        run_counter = int(context.run_id.split('_')[2])



        self.assertEqual(thread_counter, run_counter,

                        "Factory method should create consistent thread and run IDs")



        # Validate UUID consistency

        thread_uuid = context.thread_id.split('_')[3]

        run_uuid = context.run_id.split('_')[3]

        self.assertEqual(thread_uuid, run_uuid,

                        "Factory method should use same UUID for both IDs")



    def test_child_context_inherits_consistent_ids(self):

        """

        INTEGRATION TEST: Verify child contexts maintain ID consistency.

        This test should FAIL initially due to the ID generation bug.

        """

        # Create parent context

        parent_thread_id, parent_run_id, parent_request_id = UnifiedIdGenerator.generate_user_context_ids(self.test_user_id, "parent")

        parent_context = UserExecutionContext(

            user_id=self.test_user_id,

            thread_id=parent_thread_id,

            run_id=parent_run_id,

            request_id=parent_request_id

        )



        # Create child context

        child_context = parent_context.create_child_context(

            operation="child_operation",

            agent_context={"child": "data"},

            audit_metadata={"parent_id": parent_request_id}

        )



        # Child should inherit thread_id but get new run_id

        self.assertEqual(child_context.thread_id, parent_context.thread_id,

                        "Child should inherit parent thread_id")

        self.assertNotEqual(child_context.run_id, parent_context.run_id,

                           "Child should have different run_id")



        # But the new run_id should be consistent with thread_id format

        thread_counter = int(child_context.thread_id.split('_')[2])

        run_counter = int(child_context.run_id.split('_')[2])



        # This will fail due to the bug but should pass after fix

        self.assertEqual(thread_counter, run_counter,

                        "Child context should maintain ID consistency")



    def test_context_validation_catches_id_inconsistency(self):

        """

        VALIDATION TEST: Verify context validation detects ID inconsistencies.

        This test documents that validation should catch the ID mismatch.

        """

        # Manually create mismatched IDs to test validation

        mismatched_thread_id = "thread_manual_1000_uuid1"

        mismatched_run_id = "run_manual_1001_uuid2"  # Different counter and UUID



        # Current validation may not catch this, but it should

        try:

            context = UserExecutionContext(

                user_id=self.test_user_id,

                thread_id=mismatched_thread_id,

                run_id=mismatched_run_id

            )



            # If we get here, validation is insufficient

            self.fail("Context validation should detect ID inconsistency between thread_id and run_id")



        except (InvalidContextError, ValueError) as e:

            # This is what should happen - validation catches the inconsistency

            self.assertIn("inconsistency", str(e).lower(),

                         "Error message should mention ID inconsistency")



    def test_websocket_routing_relies_on_consistent_ids(self):

        """

        INTEGRATION TEST: Verify WebSocket routing works with consistent IDs.

        This test documents the business impact of ID consistency.

        """

        # Create context for WebSocket integration

        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(self.test_user_id, "websocket_test")

        websocket_client_id = f"ws_{self.test_user_id}_{request_id}"



        context = UserExecutionContext(

            user_id=self.test_user_id,

            thread_id=thread_id,

            run_id=run_id,

            request_id=request_id,

            websocket_client_id=websocket_client_id

        )



        # Verify WebSocket routing data consistency

        self.assertIn(request_id, context.websocket_client_id,

                     "WebSocket client ID should include consistent request_id")



        # Validate that both thread_id and run_id are part of the same "family"

        thread_operation = thread_id.split('_')[1]

        run_operation = run_id.split('_')[1]



        self.assertEqual(thread_operation, run_operation,

                        "Thread and run IDs should belong to same operation")



if __name__ == '__main__':

    unittest.main()

