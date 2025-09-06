"""Integration test for state persistence foreign key fix.

This test verifies that the state persistence service properly auto-creates
dev users to prevent foreign key violations when saving agent state.
"""

import uuid
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from netra_backend.app.db.models_agent_state import AgentStateSnapshot
from netra_backend.app.db.models_user import User
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.state_persistence import state_persistence_service
from test_framework.fixtures.database_fixtures import test_db_session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_persistence_auto_creates_dev_user(test_db_session):
    """Test that dev-temp users are auto-created when saving state."""
    # Create a unique dev user ID
    dev_user_id = f"dev-temp-{uuid.uuid4().hex[:8]}"
    
    # Create persistence request with dev user
    request = StatePersistenceRequest(
        run_id=f"run_{uuid.uuid4()}",
        thread_id=f"thread_{dev_user_id}",
        user_id=dev_user_id,
        state_data={
            "conversation": [],
            "current_step": 0,
            "metadata": {"test": True},
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        checkpoint_type=CheckpointType.AUTO,
        execution_context={"source": "integration_test"},
        is_recovery_point=False
    )
    
    # Verify user doesn't exist initially
    result = await test_db_session.execute(
        select(User).where(User.id == dev_user_id)
    )
    initial_user = result.scalar_one_or_none()
    assert initial_user is None, "User should not exist initially"
    
    # Save agent state - this should auto-create the user
    success, snapshot_id = await state_persistence_service.save_agent_state(
        request, test_db_session
    )
    
    # Verify the save succeeded
    assert success is True, "State save should succeed"
    assert snapshot_id is not None, "Should return a snapshot ID"
    
    # Verify the user was created
    result = await test_db_session.execute(
        select(User).where(User.id == dev_user_id)
    )
    created_user = result.scalar_one_or_none()
    assert created_user is not None, "User should be auto-created"
    assert created_user.id == dev_user_id
    assert created_user.email == f"{dev_user_id}@dev.local"
    assert created_user.is_developer is True
    assert created_user.role == "developer"
    
    # Verify the snapshot was saved
    result = await test_db_session.execute(
        select(AgentStateSnapshot).where(AgentStateSnapshot.id == snapshot_id)
    )
    snapshot = result.scalar_one_or_none()
    assert snapshot is not None, "Snapshot should be saved"
    assert snapshot.user_id == dev_user_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_persistence_handles_existing_user(test_db_session):
    """Test that existing users are not recreated."""
    # Create a user first
    existing_user = User(
        id=f"existing-dev-{uuid.uuid4().hex[:8]}",
        email="existing@test.com",
        full_name="Existing User",
        is_active=True,
        role="standard_user"
    )
    test_db_session.add(existing_user)
    await test_db_session.commit()
    
    # Create persistence request with existing user
    request = StatePersistenceRequest(
        run_id=f"run_{uuid.uuid4()}",
        thread_id=f"thread_existing",
        user_id=existing_user.id,
        state_data={
            "conversation": [],
            "current_step": 0,
            "metadata": {"test": True}
        },
        checkpoint_type=CheckpointType.MANUAL,
        execution_context={"source": "integration_test"},
        is_recovery_point=False
    )
    
    # Save agent state
    success, snapshot_id = await state_persistence_service.save_agent_state(
        request, test_db_session
    )
    
    # Verify save succeeded
    assert success is True
    assert snapshot_id is not None
    
    # Verify user wasn't modified
    await test_db_session.refresh(existing_user)
    assert existing_user.email == "existing@test.com"
    assert existing_user.role == "standard_user"


@pytest.mark.asyncio
@pytest.mark.integration  
async def test_state_persistence_auto_creates_test_user(test_db_session):
    """Test that test- prefixed users are also auto-created."""
    # Create a unique test user ID
    test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    
    # Create persistence request with test user
    request = StatePersistenceRequest(
        run_id=f"run_{uuid.uuid4()}",
        thread_id=f"thread_{test_user_id}",
        user_id=test_user_id,
        state_data={
            "conversation": [],
            "current_step": 0,
            "metadata": {"test": True}
        },
        checkpoint_type=CheckpointType.AUTO,
        execution_context={"source": "integration_test"},
        is_recovery_point=True
    )
    
    # Save agent state - should auto-create the test user
    success, snapshot_id = await state_persistence_service.save_agent_state(
        request, test_db_session
    )
    
    # Verify the save succeeded
    assert success is True
    assert snapshot_id is not None
    
    # Verify the test user was created
    result = await test_db_session.execute(
        select(User).where(User.id == test_user_id)
    )
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.id == test_user_id
    assert created_user.email == f"{test_user_id}@dev.local"
    assert created_user.is_developer is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_persistence_skips_regular_user_creation(test_db_session):
    """Test that regular (non-dev/test) users are NOT auto-created."""
    # Create a regular user ID (doesn't match dev/test pattern)
    regular_user_id = f"user-{uuid.uuid4().hex[:8]}"
    
    # Create persistence request with regular user
    request = StatePersistenceRequest(
        run_id=f"run_{uuid.uuid4()}",
        thread_id=f"thread_regular",
        user_id=regular_user_id,
        state_data={
            "conversation": [],
            "current_step": 0,
            "metadata": {"test": True}
        },
        checkpoint_type=CheckpointType.AUTO,
        execution_context={"source": "integration_test"},
        is_recovery_point=False
    )
    
    # Attempt to save agent state - should fail with FK violation
    success, snapshot_id = await state_persistence_service.save_agent_state(
        request, test_db_session
    )
    
    # Verify the save failed (expected for security)
    assert success is False, "Should fail for non-dev users"
    assert snapshot_id is None
    
    # Verify no user was created
    result = await test_db_session.execute(
        select(User).where(User.id == regular_user_id)
    )
    user = result.scalar_one_or_none()
    assert user is None, "Regular users should NOT be auto-created"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_persistence_handles_run_prefix(test_db_session):
    """Test that run_ prefixed IDs skip persistence entirely."""
    # Create persistence request with run_ prefix (temp test ID)
    request = StatePersistenceRequest(
        run_id=f"run_{uuid.uuid4()}",
        thread_id="thread_test",
        user_id=f"run_{uuid.uuid4()}",  # run_ prefix should skip persistence
        state_data={
            "conversation": [],
            "current_step": 0
        },
        checkpoint_type=CheckpointType.AUTO,
        execution_context={"source": "integration_test"},
        is_recovery_point=False
    )
    
    # Save agent state - should return dummy ID without DB interaction
    success, snapshot_id = await state_persistence_service.save_agent_state(
        request, test_db_session
    )
    
    # Verify it returns success with a dummy ID
    assert success is True
    assert snapshot_id is not None
    
    # Verify no snapshot was actually saved to DB
    result = await test_db_session.execute(
        select(AgentStateSnapshot).where(AgentStateSnapshot.id == snapshot_id)
    )
    snapshot = result.scalar_one_or_none()
    assert snapshot is None, "No snapshot should be saved for run_ prefixed IDs"