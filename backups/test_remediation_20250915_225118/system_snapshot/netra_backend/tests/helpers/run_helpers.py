"""Run database repository test helper functions.

This module provides helper functions for run test operations
on database repositories. All functions are  <= 8 lines.
COMPLIANCE: 450-line max file, 25-line max functions
"""

from datetime import datetime
from unittest.mock import AsyncMock

# Run test helpers
async def create_test_run(uow, thread_id, status="completed", tools=None):
    """Create a test run with minimal setup."""
    return await uow.runs.create({
        "thread_id": thread_id,
        "status": status,
        "tools": tools or []
    })

def setup_run_mock_behavior(mock_repo):
    """Setup mock behavior for run repository."""
    run_counter = [0]
    created_runs = []
    _setup_run_create_mock(mock_repo, run_counter, created_runs)
    _setup_run_operation_mocks(mock_repo, created_runs)

def _setup_run_create_mock(mock_repo, run_counter, created_runs):
    """Setup run creation mock."""
    async def create_run(data=None, **kwargs):
        if data and isinstance(data, dict):
            kwargs = data
        run_counter[0] += 1
        run = _create_mock_run(kwargs, run_counter[0])
        created_runs.append(run)
        return run
    mock_repo.create.side_effect = create_run

def _create_mock_run(kwargs, counter):
    """Create a mock run object."""
    base_attrs = _get_run_base_attrs(kwargs, counter)
    optional_attrs = _get_run_optional_attrs(kwargs)
    return AsyncMock(**{**base_attrs, **optional_attrs})

def _setup_run_operation_mocks(mock_repo, created_runs):
    """Setup run operation mocks."""
    _setup_run_update_status_mock(mock_repo, created_runs)
    _setup_run_active_query_mock(mock_repo, created_runs)

def _setup_run_update_status_mock(mock_repo, created_runs):
    """Setup run status update mock."""
    update_func = _create_run_update_status_func(created_runs)
    mock_repo.update_status.side_effect = update_func

def _create_fallback_run(run_id, status, metadata):
    """Create fallback run for update operations."""
    return AsyncMock(
        id=run_id,
        status=status,
        completed_at=datetime.now() if status == "completed" else None,
        metadata=metadata or {}
    )

def _setup_run_active_query_mock(mock_repo, created_runs):
    """Setup active runs query mock."""
    async def get_active_runs_impl():
        return [run for run in created_runs if run.status in ["in_progress", "queued", "requires_action"]]
    mock_repo.get_active_runs.side_effect = get_active_runs_impl
    mock_repo.get_active = mock_repo.get_active_runs

def _get_run_base_attrs(kwargs, counter):
    """Get base run attributes."""
    return {
        'id': kwargs.get('id', f"run_{counter}"),
        'thread_id': kwargs.get('thread_id'),
        'status': kwargs.get('status', 'completed'),
        'tools': kwargs.get('tools', [])
    }

def _get_run_optional_attrs(kwargs):
    """Get optional run attributes."""
    return {
        'model': kwargs.get('model'),
        'instructions': kwargs.get('instructions'),
        'completed_at': None,
        'metadata': {}
    }

def _create_run_update_status_func(created_runs):
    """Create run status update function."""
    async def update_run_status(run_id, status, metadata=None):
        existing_run = _find_existing_run(created_runs, run_id)
        if existing_run:
            return _update_existing_run(existing_run, status, metadata)
        return _create_fallback_run(run_id, status, metadata)
    return update_run_status

def _find_existing_run(created_runs, run_id):
    """Find existing run by ID."""
    for run in created_runs:
        if run.id == run_id:
            return run
    return None

def _update_existing_run(run, status, metadata):
    """Update existing run with new status."""
    run.status = status
    run.completed_at = datetime.now() if status == "completed" else None
    run.metadata = metadata or {}
    return run