"""Test run repository specific functionality.

MODULE PURPOSE:
Tests the run repository layer with comprehensive mocking to ensure
run-specific data access patterns work correctly.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest

# Add project root to path
from .database_repository_helpers import (
    assert_run_created_correctly,
    create_test_run,
    # Add project root to path
    create_test_thread,
)

# Import fixtures from helpers
pytest_plugins = ["app.tests.helpers.database_repository_fixtures"]
class TestRunRepository:
    """Test run repository specific functionality."""

    async def test_create_run_with_tools(self, unit_of_work):
        """Test creating a run with tool configurations."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            
            run = await uow.runs.create({
                "thread_id": thread.id,
                "status": "in_progress",
                "tools": ["code_interpreter", "retrieval"],
                "model": "gpt-4",
                "instructions": "Test instructions"
            })
            
            assert_run_created_correctly(run, thread.id, "in_progress", ["code_interpreter", "retrieval"])

    async def test_update_run_status(self, unit_of_work):
        """Test updating run status."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            run = await create_test_run(uow, thread.id, "in_progress")
            
            updated = await uow.runs.update_status(
                run.id, "completed", metadata={"tokens_used": 150}
            )
            
            assert updated.status == "completed"
            assert updated.completed_at is not None
            assert updated.metadata["tokens_used"] == 150

    async def test_get_active_runs(self, unit_of_work):
        """Test getting active runs."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            
            active_run = await create_test_run(uow, thread.id, "in_progress")
            completed_run = await create_test_run(uow, thread.id, "completed")
            
            active = await uow.runs.get_active_runs()
            
            assert any(r.id == active_run.id for r in active)
            assert not any(r.id == completed_run.id for r in active)