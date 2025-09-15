"""
Test reproduction for Issue #964: UserExecutionContext metadata parameter error

This test file is designed to reproduce the exact error where UserExecutionContext
constructor is called with a non-existent 'metadata' parameter.

EXPECTED BEHAVIOR: These tests should FAIL until Issue #964 is fixed
"""

import unittest
from unittest.mock import AsyncMock
from test_framework.ssot.base import BaseTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUserExecutionContextParameterValidation(BaseTestCase):
    """Test cases to reproduce Issue #964 UserExecutionContext metadata parameter errors."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    def test_user_execution_context_with_metadata_parameter_fails(self):
        """
        REPRODUCTION TEST: UserExecutionContext called with metadata parameter should fail.

        This test reproduces the exact error from test_triage_init_validation.py line 24:
        UserExecutionContext(..., metadata={'user_request': 'test'})

        EXPECTED: This test should FAIL with TypeError about unexpected keyword argument 'metadata'
        """
        with self.assertRaises(TypeError) as context:
            # This should fail - UserExecutionContext doesn't have a 'metadata' parameter
            user_context = UserExecutionContext(
                user_id='test-user-reproduction',
                thread_id='test-thread-reproduction',
                run_id='test-run-reproduction',
                metadata={'user_request': 'test reproduction'}  # This parameter doesn't exist
            )

        # Verify the exact error message
        error_message = str(context.exception)
        self.assertIn("unexpected keyword argument 'metadata'", error_message)
        self.assertIn("UserExecutionContext", error_message)

    def test_user_execution_context_line_24_reproduction(self):
        """
        REPRODUCTION TEST: Exact reproduction of line 24 from test_triage_init_validation.py

        Original failing line:
        self.test_context = UserExecutionContext(user_id='test-user-init', thread_id='test-thread-init',
                                                run_id='test-run-init',
                                                metadata={'user_request': 'test initialization validation'}).with_db_session(AsyncMock())

        EXPECTED: This test should FAIL with TypeError about unexpected keyword argument 'metadata'
        """
        with self.assertRaises(TypeError) as context:
            # Exact reproduction of the failing line
            test_context = UserExecutionContext(
                user_id='test-user-init',
                thread_id='test-thread-init',
                run_id='test-run-init',
                metadata={'user_request': 'test initialization validation'}
            ).with_db_session(AsyncMock())

        # Verify the exact error message
        error_message = str(context.exception)
        self.assertIn("unexpected keyword argument 'metadata'", error_message)

    def test_user_execution_context_line_67_reproduction(self):
        """
        REPRODUCTION TEST: Exact reproduction of line 67 from test_triage_init_validation.py

        Original failing line:
        context_no_request = UserExecutionContext(user_id='test-user', thread_id='test-thread',
                                                  run_id='test-run', metadata={}).with_db_session(AsyncMock())

        EXPECTED: This test should FAIL with TypeError about unexpected keyword argument 'metadata'
        """
        with self.assertRaises(TypeError) as context:
            # Exact reproduction of the failing line
            context_no_request = UserExecutionContext(
                user_id='test-user',
                thread_id='test-thread',
                run_id='test-run',
                metadata={}
            ).with_db_session(AsyncMock())

        # Verify the exact error message
        error_message = str(context.exception)
        self.assertIn("unexpected keyword argument 'metadata'", error_message)

    def test_user_execution_context_line_119_reproduction(self):
        """
        REPRODUCTION TEST: Exact reproduction of line 119 from test_triage_init_validation.py

        Original failing line:
        context_no_db = UserExecutionContext(user_id='test-user', thread_id='test-thread',
                                            run_id='test-run', metadata={'user_request': 'test request'})

        EXPECTED: This test should FAIL with TypeError about unexpected keyword argument 'metadata'
        """
        with self.assertRaises(TypeError) as context:
            # Exact reproduction of the failing line
            context_no_db = UserExecutionContext(
                user_id='test-user',
                thread_id='test-thread',
                run_id='test-run',
                metadata={'user_request': 'test request'}
            )

        # Verify the exact error message
        error_message = str(context.exception)
        self.assertIn("unexpected keyword argument 'metadata'", error_message)

    def test_user_execution_context_correct_parameters_work(self):
        """
        VALIDATION TEST: UserExecutionContext with correct parameters should work.

        This test verifies that UserExecutionContext works when called with valid parameters,
        demonstrating that the issue is specifically with the 'metadata' parameter.

        EXPECTED: This test should PASS
        """
        # This should work - using correct parameters
        user_context = UserExecutionContext(
            user_id='test-user-valid',
            thread_id='test-thread-valid',
            run_id='test-run-valid'
            # No metadata parameter - should work fine
        )

        # Verify the context was created successfully
        self.assertEqual(user_context.user_id, 'test-user-valid')
        self.assertEqual(user_context.thread_id, 'test-thread-valid')
        self.assertEqual(user_context.run_id, 'test-run-valid')

    def test_user_execution_context_with_correct_agent_context_works(self):
        """
        VALIDATION TEST: UserExecutionContext with correct agent_context parameter should work.

        This test shows that the correct way to pass metadata-like information is through
        the agent_context parameter.

        EXPECTED: This test should PASS
        """
        # This should work - using correct agent_context parameter
        user_context = UserExecutionContext(
            user_id='test-user-agent-ctx',
            thread_id='test-thread-agent-ctx',
            run_id='test-run-agent-ctx',
            agent_context={'user_request': 'test with agent context'}  # Correct parameter
        )

        # Verify the context was created successfully
        self.assertEqual(user_context.user_id, 'test-user-agent-ctx')
        self.assertEqual(user_context.thread_id, 'test-thread-agent-ctx')
        self.assertEqual(user_context.run_id, 'test-run-agent-ctx')
        self.assertEqual(user_context.agent_context['user_request'], 'test with agent context')


if __name__ == '__main__':
    print("ISSUE #964 REPRODUCTION TESTS")
    print("These tests are designed to reproduce the UserExecutionContext metadata parameter error")
    print("EXPECTED: Tests with 'metadata' parameter should FAIL")
    print("EXPECTED: Tests with correct parameters should PASS")
    print("Run via: python tests/unified_test_runner.py --category unit")
    unittest.main()