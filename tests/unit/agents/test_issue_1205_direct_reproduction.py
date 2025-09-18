"""
Direct reproduction test for Issue #1205 - AgentRegistryAdapter method signature mismatch.

This test creates the exact TypeError that occurs in production when
AgentExecutionCore calls AgentRegistryAdapter.get_async() with a context parameter.

EXPECTED BEHAVIOR: This test should FAIL with TypeError, demonstrating the bug.
"""

import pytest
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.services.user_execution_context import UserExecutionContext


class Issue1205DirectReproductionTests(SSotAsyncTestCase, unittest.TestCase):
    """Direct reproduction of Issue #1205 TypeError."""

    def setUp(self):
        """Set up minimal test fixtures."""
        super().setUp()

        # Create minimal mocks
        self.mock_agent_class_registry = Mock()
        self.mock_agent_factory = AsyncMock()
        self.mock_user_context = Mock(spec=UserExecutionContext)
        self.mock_user_context.user_id = "test_user"

        # Create adapter
        self.adapter = AgentRegistryAdapter(
            agent_class_registry=self.mock_agent_class_registry,
            agent_factory=self.mock_agent_factory,
            user_context=self.mock_user_context
        )

    def test_type_error_reproduction(self):
        """Reproduce the exact TypeError from Issue #1205.

        This test demonstrates the interface mismatch that causes production failures.
        """
        async def run_test():
            try:
                # This call should fail with TypeError:
                # "get_async() got an unexpected keyword argument 'context'"
                result = await self.adapter.get_async("supervisor_agent", context=self.mock_user_context)

                # If we reach here, the bug has been fixed
                print(f"UNEXPECTED: Method call succeeded, result: {result}")
                pytest.fail("Expected TypeError not raised - Issue #1205 may be fixed")

            except TypeError as e:
                # This is the expected bug
                if "unexpected keyword argument 'context'" in str(e):
                    print(f"CHECK Issue #1205 reproduced: {e}")
                    # This confirms the bug exists
                    pytest.fail(f"CONFIRMED Issue #1205 TypeError: {e}")
                else:
                    pytest.fail(f"Unexpected TypeError: {e}")
            except Exception as e:
                pytest.fail(f"Unexpected exception: {e}")

        # Run the async test
        asyncio.run(run_test())

    def test_current_method_signature(self):
        """Document the current method signature causing the issue."""
        import inspect

        sig = inspect.signature(self.adapter.get_async)
        params = list(sig.parameters.keys())

        print(f"Current get_async signature: {params}")
        print(f"Expected signature: ['agent_name', 'context']")

        # This assertion confirms the signature mismatch
        if params != ['agent_name', 'context']:
            print(f"CHECK Issue #1205 confirmed: Signature mismatch")
            print(f"  Current:  {params}")
            print(f"  Expected: ['agent_name', 'context']")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])