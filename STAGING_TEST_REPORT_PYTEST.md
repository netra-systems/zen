# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-13 15:44:10
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 5
- **Passed:** 0 (0.0%)
- **Failed:** 5 (100.0%)
- **Skipped:** 0
- **Duration:** 91.81 seconds
- **Pass Rate:** 0.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_complete_chat_message_to_agent_response_workflow | FAIL failed | 11.247s | test_user_chat_agent_execution.py |
| test_multi_agent_collaboration_with_tool_execution | FAIL failed | 11.290s | test_user_chat_agent_execution.py |
| test_long_running_agent_tasks_with_progress_updates | FAIL failed | 11.305s | test_user_chat_agent_execution.py |
| test_agent_failure_recovery_and_error_handling | FAIL failed | 42.448s | test_user_chat_agent_execution.py |
| test_complex_business_workflows_with_multiple_agent_interactions | FAIL failed | 11.209s | test_user_chat_agent_execution.py |

## Failed Tests Details

### FAILED: test_complete_chat_message_to_agent_response_workflow
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_user_chat_agent_execution.py
- **Duration:** 11.247s
- **Error:** tests\e2e\staging\test_user_chat_agent_execution.py:320: in test_complete_chat_message_to_agent_response_workflow
    assert result.business_value_delivered, "No business value delivered to user"
E   AssertionError: No business value delivered to user
E   assert False
E    +  where False = ChatAgentTestResult(success=True, user_id='e2e-user-5f83c683', conversation_id='thread_e2e_auth_1_0657096b', agent_responses=[{'type': 'connect', 'data': {'mode': 'main', 'user_id': 'demo-use...', 'connection_...

### FAILED: test_multi_agent_collaboration_with_tool_execution
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_user_chat_agent_execution.py
- **Duration:** 11.290s
- **Error:** tests\e2e\staging\test_user_chat_agent_execution.py:446: in test_multi_agent_collaboration_with_tool_execution
    assert len(tool_execution_events) > 0, "No tool execution detected"
E   AssertionError: No tool execution detected
E   assert 0 > 0
E    +  where 0 = len([])

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_user_chat_agent_execution.py:458: in test_multi_agent_collaboration_with_tool_execution
    pytest.fail(f"Multi-agent collaboration wit...

### FAILED: test_long_running_agent_tasks_with_progress_updates
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_user_chat_agent_execution.py
- **Duration:** 11.305s
- **Error:** tests\e2e\staging\test_user_chat_agent_execution.py:594: in test_long_running_agent_tasks_with_progress_updates
    assert user_experience_metrics["regular_communication"], "Insufficient user communication during long task"
E   AssertionError: Insufficient user communication during long task
E   assert False

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_user_chat_agent_execution.py:606: in test_long_running_agent_tasks_with_progress_updates
    pytes...

### FAILED: test_agent_failure_recovery_and_error_handling
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_user_chat_agent_execution.py
- **Duration:** 42.448s
- **Error:** tests\e2e\staging\test_user_chat_agent_execution.py:736: in test_agent_failure_recovery_and_error_handling
    assert user_experience_quality["graceful_handling"], "System did not handle limitations gracefully"
E   AssertionError: System did not handle limitations gracefully
E   assert False

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_user_chat_agent_execution.py:748: in test_agent_failure_recovery_and_error_handling
    pytest.fail(f"Agent failure...

### FAILED: test_complex_business_workflows_with_multiple_agent_interactions
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_user_chat_agent_execution.py
- **Duration:** 11.209s
- **Error:** tests\e2e\staging\test_user_chat_agent_execution.py:883: in test_complex_business_workflows_with_multiple_agent_interactions
    assert workflow_completeness >= 0.4, f"Insufficient workflow coverage: {workflow_completeness:.1%}"
E   AssertionError: Insufficient workflow coverage: 0.0%
E   assert 0.0 >= 0.4

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_user_chat_agent_execution.py:898: in test_complex_business_workflows_with_multiple_agent_interaction...

## Pytest Output Format

```
test_user_chat_agent_execution.py::test_complete_chat_message_to_agent_response_workflow FAILED
test_user_chat_agent_execution.py::test_multi_agent_collaboration_with_tool_execution FAILED
test_user_chat_agent_execution.py::test_long_running_agent_tasks_with_progress_updates FAILED
test_user_chat_agent_execution.py::test_agent_failure_recovery_and_error_handling FAILED
test_user_chat_agent_execution.py::test_complex_business_workflows_with_multiple_agent_interactions FAILED

==================================================
0 passed, 5 failed in 91.81s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 1 | 0 | 1 | 0.0% |
| Agent | 5 | 0 | 5 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
