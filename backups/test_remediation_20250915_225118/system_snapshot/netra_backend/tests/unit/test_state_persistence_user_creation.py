"""Test for state persistence user creation behavior.

This test verifies that the state persistence service properly handles
user creation when saving agent state to prevent foreign key violations.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from netra_backend.app.db.models_agent_state import AgentStateSnapshot
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.state_persistence import state_persistence_service


@pytest.mark.asyncio
async def test_state_persistence_fails_without_user():
    """Test that state persistence fails when user doesn't exist.
    
    This test exposes the foreign key constraint violation that occurs
    when trying to save agent state for a non-existent user.
    """
    # Create a mock database session
    mock_session = AsyncMock()
    
    # Create a persistence request with a user that doesn't exist
    non_existent_user_id = "dev-temp-" + str(uuid.uuid4())[:8]
    request = StatePersistenceRequest(
        run_id="test-run-" + str(uuid.uuid4()),
        thread_id="test-thread-" + str(uuid.uuid4()),
        user_id=non_existent_user_id,
        state_data={
            "conversation": [],
            "current_step": 0,
            "metadata": {"test": True}
        },
        checkpoint_type=CheckpointType.MANUAL,
        execution_context={"source": "test"},
        is_recovery_point=False
    )
    
    # Mock the user service to return None (user doesn't exist)
    with patch('netra_backend.app.services.state_persistence.user_service') as mock_user_service:
        mock_user_service.get = AsyncMock(return_value=None)
        
        # Mock the database session to raise IntegrityError on add
        mock_session.add = Mock(side_effect=IntegrityError(
            statement="INSERT INTO agent_state_snapshots",
            params={},
            orig=Exception("insert or update on table \"agent_state_snapshots\" violates foreign key constraint \"agent_state_snapshots_user_id_fkey\"\nDETAIL: Key (user_id)=(" + non_existent_user_id + ") is not present in table \"userbase\".")
        ))
        
        # This should fail with the foreign key violation
        success, snapshot_id = await state_persistence_service.save_agent_state(
            request, mock_session
        )
        
        # Verify the save failed
        assert success is False
        assert snapshot_id is None


@pytest.mark.asyncio 
async def test_state_persistence_auto_creates_dev_user():
    """Test that state persistence auto-creates dev users.
    
    This test verifies the desired behavior where dev/test users
    are automatically created when saving agent state.
    """
    # Create a mock database session with proper async context manager setup
    mock_session = AsyncMock()
    mock_begin_context = AsyncMock()
    mock_begin_context.__aenter__ = AsyncMock(return_value=None)
    mock_begin_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = Mock(return_value=mock_begin_context)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()
    
    # Create a persistence request with a dev user that doesn't exist
    dev_user_id = "dev-temp-" + str(uuid.uuid4())[:8]
    request = StatePersistenceRequest(
        run_id="test-run-" + str(uuid.uuid4()),
        thread_id="test-thread-" + str(uuid.uuid4()),
        user_id=dev_user_id,
        state_data={
            "conversation": [],
            "current_step": 0,
            "metadata": {"test": True}
        },
        checkpoint_type=CheckpointType.MANUAL,
        execution_context={"source": "test"},
        is_recovery_point=False
    )
    
    # Mock the user service and force legacy save path
    with patch('netra_backend.app.services.state_persistence.user_service') as mock_user_service:
        # First call returns None (user doesn't exist)
        # Second call returns the created user
        mock_created_user = Mock(id=dev_user_id)
        mock_user_service.get = AsyncMock(side_effect=[None, mock_created_user])
        mock_user_service.create = AsyncMock(return_value=mock_created_user)
        
        # Force legacy save path by mocking Redis failure
        with patch('netra_backend.app.services.state_persistence.state_cache_manager') as mock_cache:
            mock_cache.save_primary_state = AsyncMock(return_value=False)  # Force fallback
            mock_cache.cache_legacy_state = AsyncMock(return_value=True)  # Mock legacy cache
            
            # Mock successful database operations
            mock_session.execute = AsyncMock()
            
            # Call the save method with the enhanced implementation
            success, snapshot_id = await state_persistence_service.save_agent_state(
                request, mock_session
            )
            
            # Verify the user was created
            mock_user_service.create.assert_called_once()
            create_call_args = mock_user_service.create.call_args
            user_create_obj = create_call_args[1]['obj_in']
            
            # Verify the created user has correct properties
            assert user_create_obj.id == dev_user_id
            assert user_create_obj.email == f"{dev_user_id}@example.com"
            assert user_create_obj.is_active is True
            assert user_create_obj.is_developer is True
            assert user_create_obj.role == "developer"
            
            # Verify the save succeeded
            assert success is True
            assert snapshot_id is not None


@pytest.mark.asyncio
async def test_state_persistence_skips_creation_for_existing_user():
    """Test that state persistence doesn't create users if they already exist.
    
    This ensures we don't try to recreate users unnecessarily.
    """
    # Create a mock database session
    mock_session = AsyncMock()
    mock_session.begin = AsyncMock()
    mock_session.flush = AsyncMock()
    
    # Create a persistence request with an existing user
    existing_user_id = "existing-user-123"
    request = StatePersistenceRequest(
        run_id="test-run-" + str(uuid.uuid4()),
        thread_id="test-thread-" + str(uuid.uuid4()),
        user_id=existing_user_id,
        state_data={
            "conversation": [],
            "current_step": 0,
            "metadata": {"test": True}
        },
        checkpoint_type=CheckpointType.MANUAL,
        execution_context={"source": "test"},
        is_recovery_point=False
    )
    
    # Mock the user service to return an existing user
    with patch('netra_backend.app.services.state_persistence.user_service') as mock_user_service:
        mock_existing_user = Mock(id=existing_user_id)
        mock_user_service.get = AsyncMock(return_value=mock_existing_user)
        mock_user_service.create = AsyncMock()  # Should not be called
        
        # Mock successful database operations
        mock_session.add = MagicMock()
        mock_session.execute = AsyncMock()
        
        # Call the save method
        success, snapshot_id = await state_persistence_service.save_agent_state(
            request, mock_session
        )
        
        # Verify the user was NOT created (already exists)
        mock_user_service.create.assert_not_called()
        
        # Verify the save succeeded
        assert success is True
        assert snapshot_id is not None


@pytest.mark.asyncio
async def test_state_persistence_handles_test_users():
    """Test that state persistence auto-creates test- prefixed users.
    
    This verifies that test users are handled the same as dev users.
    """
    # Create a mock database session with proper async context manager setup
    mock_session = AsyncMock()
    mock_begin_context = AsyncMock()
    mock_begin_context.__aenter__ = AsyncMock(return_value=None)
    mock_begin_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = Mock(return_value=mock_begin_context)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()
    
    # Create a persistence request with a test user that doesn't exist
    test_user_id = "test-user-" + str(uuid.uuid4())[:8]
    request = StatePersistenceRequest(
        run_id="test-run-" + str(uuid.uuid4()),
        thread_id="test-thread-" + str(uuid.uuid4()),
        user_id=test_user_id,
        state_data={
            "conversation": [],
            "current_step": 0,
            "metadata": {"test": True}
        },
        checkpoint_type=CheckpointType.MANUAL,
        execution_context={"source": "test"},
        is_recovery_point=False
    )
    
    # Mock the user service and force legacy save path
    with patch('netra_backend.app.services.state_persistence.user_service') as mock_user_service:
        # First call returns None (user doesn't exist)
        mock_user_service.get = AsyncMock(return_value=None)
        mock_created_user = Mock(id=test_user_id)
        mock_user_service.create = AsyncMock(return_value=mock_created_user)
        
        # Force legacy save path by mocking Redis failure
        with patch('netra_backend.app.services.state_persistence.state_cache_manager') as mock_cache:
            mock_cache.save_primary_state = AsyncMock(return_value=False)  # Force fallback
            mock_cache.cache_legacy_state = AsyncMock(return_value=True)  # Mock legacy cache
            
            # Mock successful database operations
            mock_session.execute = AsyncMock()
            
            # Call the save method
            success, snapshot_id = await state_persistence_service.save_agent_state(
                request, mock_session
            )
            
            # Verify the user was created
            mock_user_service.create.assert_called_once()
            create_call_args = mock_user_service.create.call_args
            user_create_obj = create_call_args[1]['obj_in']
            
            # Verify the created user has correct properties
            assert user_create_obj.id == test_user_id
            assert user_create_obj.email == f"{test_user_id}@example.com"
            assert user_create_obj.is_developer is True
            
            # Verify the save succeeded
            assert success is True
            assert snapshot_id is not None