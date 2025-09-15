"""
Test to reproduce Issue #1265 - AgentExecutionContext import failure

This test validates that the import failure exists and then validates the fix.
Following CLAUDE.md principles - test must fail hard on errors, no mocking business logic.
"""

import pytest
import sys
from pathlib import Path

def test_import_failure_reproduction():
    """
    Test that reproduces the exact import failure from Issue #1265.

    This test should FAIL initially, demonstrating the broken import path.
    After fixing the import path, this test should pass.
    """

    # Test the failing import - this should raise ImportError
    with pytest.raises(ImportError, match="cannot import name 'AgentExecutionContext'"):
        from netra_backend.app.services.user_execution_context import UserExecutionContext, AgentExecutionContext


def test_correct_import_path():
    """
    Test that the correct import path works.

    This test validates the fix by importing from the correct location.
    """

    # This should work - import from the correct location
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext

    # Verify the class exists and has expected structure
    assert AgentExecutionContext is not None

    # Verify it's a class that can be instantiated (with required parameters)
    # Based on the actual definition, it needs run_id, thread_id, user_id, agent_name
    context = AgentExecutionContext(
        run_id="test_run_123",
        thread_id="test_thread_456",
        user_id="test_user_789",
        agent_name="test_agent"
    )

    assert context.run_id == "test_run_123"
    assert context.thread_id == "test_thread_456"
    assert context.user_id == "test_user_789"
    assert context.agent_name == "test_agent"
    assert context.metadata == {}  # default empty dict


def test_import_comparison():
    """
    Test to verify that UserExecutionContext can be imported correctly from its original location
    but AgentExecutionContext cannot.
    """

    # This should work
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    assert UserExecutionContext is not None

    # This should fail
    with pytest.raises(ImportError):
        from netra_backend.app.services.user_execution_context import AgentExecutionContext


if __name__ == "__main__":
    print("Running Issue #1265 import failure reproduction tests...")

    # Run the tests
    try:
        test_import_failure_reproduction()
        print("PASS: Import failure reproduction test passed")
    except AssertionError as e:
        print(f"FAIL: Import failure reproduction test failed: {e}")

    try:
        test_correct_import_path()
        print("PASS: Correct import path test passed")
    except Exception as e:
        print(f"FAIL: Correct import path test failed: {e}")

    try:
        test_import_comparison()
        print("PASS: Import comparison test passed")
    except Exception as e:
        print(f"FAIL: Import comparison test failed: {e}")