"""
Issue #1265 Validation Test - AgentExecutionContext Import Fix

This test validates that Issue #1265 has been correctly resolved:
- Original issue: ImportError when importing AgentExecutionContext from wrong path
- Root cause: Wrong import path in test_execution_engine_consolidated_comprehensive.py:58
- Solution: Fixed import path + updated test constructor calls to match actual interface

Following CLAUDE.md principles - test fails hard on errors, no mocking business logic.
"""

import pytest
import sys
from pathlib import Path


def test_issue_1265_import_fix_validation():
    """
    Validate that Issue #1265 AgentExecutionContext import failure is resolved.

    Tests:
    1. Correct import path works
    2. AgentExecutionContext can be instantiated with proper interface
    3. UserExecutionContext can still be imported from original location
    4. Wrong import path still fails (ensuring we didn't break anything)
    """

    # Test 1: Correct import path works
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
    assert AgentExecutionContext is not None
    assert AgentExecutionResult is not None

    # Test 2: AgentExecutionContext can be instantiated with proper interface
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
    assert context.retry_count == 0  # default value
    assert context.max_retries == 3  # default value

    # Test 3: UserExecutionContext can still be imported from original location
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    assert UserExecutionContext is not None

    # Test 4: Wrong import path still fails (ensuring we didn't break the error detection)
    with pytest.raises(ImportError, match="cannot import name 'AgentExecutionContext'"):
        from netra_backend.app.services.user_execution_context import AgentExecutionContext


def test_issue_1265_test_file_imports():
    """
    Validate that the fixed test file can be imported successfully.
    """

    # This should work without ImportError
    from netra_backend.tests.unit.agents.test_execution_engine_consolidated_comprehensive import TestAgentExecutionContext

    assert TestAgentExecutionContext is not None


def test_issue_1265_helper_function():
    """
    Validate the helper function created to fix constructor calls.
    """

    from netra_backend.tests.unit.agents.test_execution_engine_consolidated_comprehensive import create_test_agent_context

    # Test helper function creates valid context
    context = create_test_agent_context(
        agent_name="test_agent",
        user_id="user123",
        task_info="test_task"
    )

    assert context.agent_name == "test_agent"
    assert context.user_id == "user123"
    assert context.metadata["task"] == "test_task"  # task stored in metadata
    assert context.run_id is not None  # auto-generated
    assert context.thread_id is not None  # auto-generated


if __name__ == "__main__":
    print("Running Issue #1265 validation tests...")

    try:
        test_issue_1265_import_fix_validation()
        print("PASS: Import fix validation")
    except Exception as e:
        print(f"FAIL: Import fix validation - {e}")
        sys.exit(1)

    try:
        test_issue_1265_test_file_imports()
        print("PASS: Test file import validation")
    except Exception as e:
        print(f"FAIL: Test file import validation - {e}")
        sys.exit(1)

    try:
        test_issue_1265_helper_function()
        print("PASS: Helper function validation")
    except Exception as e:
        print(f"FAIL: Helper function validation - {e}")
        sys.exit(1)

    print("SUCCESS: All Issue #1265 validation tests passed!")
    print("Issue #1265 - AgentExecutionContext import failure has been resolved.")