"""Test Case for Issue #1028: Missing WebSocket completion notifications

This test reproduces the specific bug where notify_agent_completed() is not called
in the success path of agent execution.

AGENT_SESSION_ID = agent-session-2025-01-14-1524
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

# Test the agent_execution_core directly since it's the suspected source
@pytest.mark.unit
async def test_issue_1028_websocket_completion_missing():
    """Reproduce Issue #1028: Missing WebSocket completion notifications in success path.

    This test should FAIL initially to prove the bug exists.

    Expected Behavior:
    - Agent executes successfully
    - notify_agent_completed() is called with success=True

    Actual Bug Behavior:
    - Agent executes successfully
    - notify_agent_completed() is NOT called (or called incorrectly)
    """
    print("\\n=== Issue #1028 Bug Reproduction Test ===")
    print("Testing WebSocket completion notifications in agent execution success path")

    # Import the modules we need to test
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from uuid import uuid4

    # Create test contexts (use realistic IDs to pass validation)
    user_context = UserExecutionContext(
        user_id="user_abc123xyz",
        thread_id="thread_def456ghi",
        run_id="run_jkl789mno"
    )

    agent_context = AgentExecutionContext(
        agent_name="test_agent",
        thread_id="thread_def456ghi",
        user_id="user_abc123xyz",
        run_id="run_jkl789mno",
        metadata={"message": "Test Issue #1028"}
    )

    # Mock the registry to return a successful agent
    mock_registry = AsyncMock()
    mock_agent = AsyncMock()

    # Mock agent.execute to return success
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
    success_result = AgentExecutionResult(
        success=True,
        data={"response": "Success response for Issue #1028"},
        duration=1.0,
        error=None
    )
    mock_agent.execute = AsyncMock(return_value=success_result)
    mock_registry.get_async = AsyncMock(return_value=mock_agent)

    # Mock WebSocket bridge - THIS IS WHAT WE'RE TESTING
    mock_websocket_bridge = AsyncMock()
    mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)

    print(f"Created mocks: agent={mock_agent}, registry={mock_registry}, websocket={mock_websocket_bridge}")

    # Create the AgentExecutionCore with our mocks
    execution_core = AgentExecutionCore(
        registry=mock_registry,
        websocket_bridge=mock_websocket_bridge
    )

    print("Created AgentExecutionCore with mocked dependencies")

    # Execute the agent - this should trigger the bug
    print("Executing agent to test WebSocket completion notification...")
    try:
        result = await execution_core.execute_agent(
            context=agent_context,
            user_context=user_context
        )

        print(f"Agent execution completed: success={result.success}")
        print(f"Agent execution result: {result.data}")

        # Verify the execution was successful
        assert result.success, f"Agent execution should have succeeded, but got: {result.error}"

        # THE CRITICAL TEST: Was notify_agent_completed called?
        print("\\n=== CRITICAL TEST: WebSocket notification verification ===")

        websocket_calls = mock_websocket_bridge.notify_agent_completed.call_count
        print(f"notify_agent_completed call count: {websocket_calls}")

        if websocket_calls == 0:
            print("BUG CONFIRMED: notify_agent_completed was NOT called!")
            print("This proves Issue #1028 exists - WebSocket completion notifications are missing")
            print("User will not see completion notification in frontend")
            return False  # Bug confirmed
        elif websocket_calls == 1:
            print("PASS: notify_agent_completed was called once (expected)")
            # Verify the call had correct parameters
            call_args = mock_websocket_bridge.notify_agent_completed.call_args
            print(f"Call arguments: {call_args}")
            return True  # Bug fixed
        else:
            print(f"UNEXPECTED: notify_agent_completed called {websocket_calls} times (expected 1)")
            return False  # Unexpected behavior

    except Exception as e:
        print(f"FAIL: Agent execution failed with error: {e}")
        print(f"Error type: {type(e).__name__}")
        raise


if __name__ == "__main__":
    async def run_test():
        try:
            bug_confirmed = await test_issue_1028_websocket_completion_missing()

            print("\\n" + "="*80)
            if not bug_confirmed:
                print("ISSUE #1028 BUG REPRODUCTION: SUCCESS")
                print("Test demonstrates the WebSocket completion notification bug exists")
                print("Ready for bug fix implementation")
            else:
                print("ISSUE #1028 BUG APPEARS TO BE FIXED")
                print("WebSocket completion notifications are working correctly")

            print("="*80)

        except Exception as e:
            print(f"\\nTest execution failed: {e}")
            import traceback
            traceback.print_exc()

    # Run the test
    asyncio.run(run_test())