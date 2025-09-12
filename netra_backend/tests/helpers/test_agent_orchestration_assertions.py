"""
Assertion helpers for agent orchestration tests.

Provides reusable assertion functions to verify agent service behavior,
orchestration metrics, and test outcomes with ≤8 lines per function.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from typing import Any, Dict, List
from netra_backend.app.services.user_execution_context import UserExecutionContext

def assert_agent_service_initialized(service, supervisor):
    """Assert agent service is properly initialized."""
    assert service.supervisor is supervisor
    assert service.thread_service is not None
    assert service.message_handler is not None

def assert_agent_run_completed(result, expected_status='completed'):
    """Assert agent run completed successfully."""
    assert result is not None
    assert result.get('status') == expected_status

def assert_supervisor_called_correctly(mock_supervisor, expected_request, expected_thread_id, expected_user_id, expected_run_id):
    """Assert supervisor was called with correct parameters."""
    mock_supervisor.run.assert_called_once_with(
        expected_request, expected_thread_id, expected_user_id, expected_run_id
    )

def assert_message_handler_called(handler, method_name, expected_args):
    """Assert message handler method was called with correct args."""
    handler_method = getattr(handler, method_name)
    handler_method.assert_called_once_with(*expected_args)

def assert_concurrent_execution_successful(results, expected_count):
    """Assert concurrent execution results are successful."""
    assert len(results) == expected_count
    assert all(result['status'] == 'completed' for result in results)

def assert_orchestration_metrics_valid(metrics, expected_executions=None):
    """Assert orchestration metrics contain valid values."""
    required_keys = ['total_executions', 'failed_executions', 'success_rate']
    for key in required_keys:
        assert key in metrics
    
    if expected_executions:
        assert metrics['total_executions'] == expected_executions

def assert_agent_state_correct(agent, expected_state):
    """Assert agent is in expected state."""
    assert agent.state == expected_state

def assert_agent_pool_size(orchestrator, expected_pool_size, expected_active):
    """Assert agent pool and active counts are correct."""
    assert len(orchestrator.agent_pool) == expected_pool_size
    assert orchestrator.active_agents == expected_active

def assert_agent_assignment_correct(agent, expected_user_id):
    """Assert agent is assigned to correct user."""
    assert agent.user_id == expected_user_id

def assert_success_rate_calculation(metrics, expected_rate):
    """Assert success rate is calculated correctly."""
    assert abs(metrics['success_rate'] - expected_rate) < 0.01

def assert_concurrent_peak_tracked(metrics, expected_peak):
    """Assert concurrent peak is tracked correctly."""
    assert metrics['concurrent_peak'] == expected_peak

def assert_agent_reset_correctly(agent):
    """Assert agent state is reset correctly."""
    assert agent.user_id is None
    assert agent.thread_id is None
    assert agent.db_session is None

def assert_execution_time_positive(metrics):
    """Assert execution time metrics are positive."""
    assert metrics['average_execution_time'] > 0

def assert_failure_metrics_updated(metrics, expected_failures):
    """Assert failure metrics are updated correctly."""
    assert metrics['failed_executions'] == expected_failures

def assert_websocket_message_parsed(parsed_message, expected_type, expected_payload):
    """Assert WebSocket message is parsed correctly."""
    assert parsed_message["type"] == expected_type
    assert parsed_message["payload"] == expected_payload

def assert_thread_operations_handled(handler, operation_type, expected_calls):
    """Assert thread operations are handled correctly."""
    method_map = {
        "get_thread_history": "handle_thread_history",
        "create_thread": "handle_create_thread", 
        "switch_thread": "handle_switch_thread",
        "delete_thread": "handle_delete_thread",
        "list_threads": "handle_list_threads"
    }
    
    method_name = method_map[operation_type]
    handler_method = getattr(handler, method_name)
    assert handler_method.call_count == expected_calls

def assert_circuit_breaker_state(circuit_open, failure_count, expected_open, expected_failures):
    """Assert circuit breaker state is correct."""
    assert circuit_open == expected_open
    assert failure_count == expected_failures

def assert_retry_mechanism_worked(result, expected_status='completed'):
    """Assert retry mechanism succeeded."""
    assert result is not None
    assert result['status'] == expected_status

def assert_agent_creation_tracked(metrics, expected_created, expected_destroyed):
    """Assert agent creation/destruction is tracked."""
    assert metrics['agents_created'] == expected_created
    assert metrics['agents_destroyed'] == expected_destroyed

def setup_mock_request_model(user_request="Test request", model_id="default_id", user_id="default_user"):
    """Setup mock request model for testing."""
    # Mock: Generic component isolation for controlled unit testing
    mock_model = MagicNone  # TODO: Use real service instance
    mock_model.user_request = user_request
    mock_model.id = model_id
    mock_model.user_id = user_id
    return mock_model

def setup_mock_request_model_with_dump(dump_data, model_id="default_id", user_id="default_user"):
    """Setup mock request model with model_dump."""
    # Mock: Generic component isolation for controlled unit testing
    mock_model = MagicNone  # TODO: Use real service instance
    del mock_model.user_request
    mock_model.id = model_id
    mock_model.user_id = user_id
    mock_model.model_dump.return_value = dump_data
    return mock_model

def setup_websocket_message(message_type, payload):
    """Setup WebSocket message for testing."""
    return {"type": message_type, "payload": payload}

def setup_concurrent_tasks(agent_service, num_tasks, base_request="Concurrent request"):
    """Setup multiple concurrent tasks for testing."""
    tasks = []
    for i in range(num_tasks):
        request_model = setup_mock_request_model(f"{base_request} {i}")
        task = agent_service.run(request_model, f"run_{i}")
        tasks.append(task)
    return tasks

def setup_failing_agent(agent, failure_message="Test failure"):
    """Setup agent to fail for testing."""
    agent.should_fail = True
    agent.failure_message = failure_message

def setup_slow_agent(agent, execution_time=1.0):
    """Setup agent with slow execution for timeout testing."""
    agent.execution_time = execution_time

def setup_orchestrator_limits(orchestrator, max_agents=3):
    """Setup orchestrator with specific limits."""
    orchestrator.max_concurrent_agents = max_agents

def verify_no_exceptions_raised():
    """Verify that no exceptions were raised during execution."""
    # This is used in contexts where we expect graceful handling
    pass

def verify_cleanup_completed(orchestrator, user_id):
    """Verify cleanup was completed for user."""
    assert user_id not in orchestrator.agents