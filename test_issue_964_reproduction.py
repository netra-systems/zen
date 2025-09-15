#!/usr/bin/env python3
"""
Issue #964 Reproduction Test - UserExecutionContext Parameter Fix Validation

This test reproduces the TypeError that was occurring when tests used 'metadata'
instead of 'agent_context' parameter in UserExecutionContext constructor.

Expected: All tests should pass, demonstrating the fix is working.
"""

import unittest
from unittest.mock import AsyncMock
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestIssue964Reproduction(unittest.TestCase):
    """Reproduction test for Issue #964 UserExecutionContext parameter errors."""

    def test_userexecutioncontext_with_correct_agent_context_parameter(self):
        """Test that UserExecutionContext works with correct 'agent_context' parameter."""
        try:
            # This should work - using the correct 'agent_context' parameter
            context = UserExecutionContext(
                user_id='test-user-init',
                thread_id='test-thread-init',
                run_id='test-run-init',
                agent_context={'user_request': 'test initialization validation'}
            ).with_db_session(AsyncMock())

            self.assertIsNotNone(context)
            self.assertEqual(context.user_id, 'test-user-init')
            self.assertEqual(context.agent_context['user_request'], 'test initialization validation')
            print("SUCCESS: UserExecutionContext with agent_context works correctly")

        except Exception as e:
            self.fail(f"FAILED: UserExecutionContext with agent_context failed: {e}")

    def test_userexecutioncontext_with_wrong_metadata_parameter_should_fail(self):
        """Test that UserExecutionContext fails with wrong 'metadata' parameter (reproduces original issue)."""
        try:
            # This should fail - using the incorrect 'metadata' parameter
            context = UserExecutionContext(
                user_id='test-user-init',
                thread_id='test-thread-init',
                run_id='test-run-init',
                metadata={'user_request': 'test initialization validation'}
            )

            # If we get here, the test failed because it should have raised TypeError
            self.fail("EXPECTED FAILURE: UserExecutionContext should reject 'metadata' parameter")

        except TypeError as e:
            # This is expected - the metadata parameter should be rejected
            if "unexpected keyword argument 'metadata'" in str(e):
                print("SUCCESS: UserExecutionContext correctly rejects 'metadata' parameter")
            else:
                self.fail(f"UNEXPECTED ERROR: {e}")
        except Exception as e:
            self.fail(f"UNEXPECTED ERROR TYPE: {e}")

    def test_userexecutioncontext_empty_agent_context(self):
        """Test that UserExecutionContext works with empty agent_context."""
        try:
            context = UserExecutionContext(
                user_id='test-user',
                thread_id='test-thread',
                run_id='test-run',
                agent_context={}
            ).with_db_session(AsyncMock())

            self.assertIsNotNone(context)
            self.assertEqual(context.agent_context, {})
            print("SUCCESS: UserExecutionContext with empty agent_context works correctly")

        except Exception as e:
            self.fail(f"FAILED: UserExecutionContext with empty agent_context failed: {e}")

    def test_userexecutioncontext_no_agent_context_specified(self):
        """Test that UserExecutionContext works when agent_context is not specified (should use default)."""
        try:
            context = UserExecutionContext(
                user_id='test-user',
                thread_id='test-thread',
                run_id='test-run'
            )

            self.assertIsNotNone(context)
            self.assertEqual(context.agent_context, {})  # Should default to empty dict
            print("SUCCESS: UserExecutionContext with default agent_context works correctly")

        except Exception as e:
            self.fail(f"FAILED: UserExecutionContext with default agent_context failed: {e}")


if __name__ == '__main__':
    print("Running Issue #964 Reproduction Tests...")
    print("Testing UserExecutionContext parameter fix...")
    print()

    unittest.main(verbosity=2)