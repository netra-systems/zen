"""Test that verifies the fix for state persistence foreign key violation."""

import uuid
from datetime import datetime, timezone
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.db.models_user import User
from netra_backend.app.schemas.agent_state import CheckpointType, StatePersistenceRequest
from netra_backend.app.services.state_persistence import state_persistence_service
import asyncio


@pytest.fixture
def real_db_session():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a mock database session."""
    pass
    session = MagicMock(spec=AsyncSession)
    session.add = MagicNone  # TODO: Use real service instance
    session.commit = AsyncNone  # TODO: Use real service instance
    session.flush = AsyncNone  # TODO: Use real service instance
    session.rollback = AsyncNone  # TODO: Use real service instance
    session.begin = MagicNone  # TODO: Use real service instance
    session.begin.return_value.__aenter__ = AsyncNone  # TODO: Use real service instance
    session.begin.return_value.__aexit__ = AsyncNone  # TODO: Use real service instance
    return session


@pytest.fixture  
def sample_state():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create sample agent state for testing."""
    pass
    return DeepAgentState(
user_request="Test request",
chat_thread_id="thread_dev-temp-test123",
user_id="dev-temp-test123",
status="pending",
step_count=0
)


@pytest.fixture
def persistence_request(sample_state):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create sample persistence request."""
    pass
    return StatePersistenceRequest(
run_id=f"run_{uuid.uuid4()}",
thread_id="thread_dev-temp-test123", 
user_id="dev-temp-test123",
state_data=sample_state.model_dump(),
checkpoint_type=CheckpointType.AUTO,
is_recovery_point=True,
execution_context={"step_count": 0}
)


@pytest.mark.asyncio
async def test_state_persistence_creates_missing_dev_user(mock_db_session, persistence_request):
    """Test that missing dev users are auto-created during state persistence."""
    
    # Mock user_service to simulate user not existing, then being created
    with patch('netra_backend.app.services.user_service.user_service') as mock_user_service:
        # First call to get returns None (user doesn't exist)
        mock_user_service.get = AsyncMock(return_value=None)
        # Create should succeed
        mock_user_service.create = AsyncMock(return_value=User(
        id="dev-temp-test123",
        email="dev-temp-test123@dev.local",
        full_name="Dev User dev-temp-test123",
        is_active=True,
        is_developer=True,
        role="developer"
        ))
        
        # Execute save operation
        success, snapshot_id = await state_persistence_service.save_agent_state(
        persistence_request, mock_db_session
        )
        
        # Verify user lookup was called
        mock_user_service.get.assert_called_once()
        # Verify user was created
        mock_user_service.create.assert_called_once()
        
        # Verify the user create call had correct parameters
        create_call_args = mock_user_service.create.call_args
        assert create_call_args[0][0] == mock_db_session
        user_create_obj = create_call_args[1]['obj_in']
        assert user_create_obj.id == "dev-temp-test123"
        assert user_create_obj.email == "dev-temp-test123@dev.local"
        assert user_create_obj.password == "DevPassword123!"
        assert user_create_obj.is_developer is True


        @pytest.mark.asyncio
        async def test_state_persistence_handles_existing_user(mock_db_session, persistence_request):
            """Test that existing users are not recreated."""
    
            with patch('netra_backend.app.services.user_service.user_service') as mock_user_service:
        # User already exists
                existing_user = User(
                id="dev-temp-test123",
                email="existing@dev.local",
                full_name="Existing User",
                is_active=True
                )
                mock_user_service.get = AsyncMock(return_value=existing_user)
                mock_user_service.create = AsyncNone  # TODO: Use real service instance
        
        # Execute save operation  
                await state_persistence_service.save_agent_state(
                persistence_request, mock_db_session
                )
        
        # Verify user was checked
                mock_user_service.get.assert_called_once()
        # Verify no attempt to create user
                mock_user_service.create.assert_not_called()


                @pytest.mark.asyncio
                async def test_state_persistence_handles_test_prefix_users(mock_db_session, sample_state):
                    """Test that test- prefixed users are also auto-created."""
    
                    test_request = StatePersistenceRequest(
                    run_id=f"run_{uuid.uuid4()}",
                    thread_id="thread_test-user456",
                    user_id="test-user456",
                    state_data=sample_state.model_dump(),
                    checkpoint_type=CheckpointType.AUTO,
                    is_recovery_point=True,
                    execution_context={"step_count": 0}
                    )
    
                    with patch('netra_backend.app.services.user_service.user_service') as mock_user_service:
                        mock_user_service.get = AsyncMock(return_value=None)
                        mock_user_service.create = AsyncMock(return_value=User(
                        id="test-user456",
                        email="test-user456@dev.local",
                        full_name="Dev User test-user456"
                        ))
        
                        await state_persistence_service.save_agent_state(test_request, mock_db_session)
        
        # Verify test user was created
                        mock_user_service.create.assert_called_once()
                        create_args = mock_user_service.create.call_args[1]['obj_in']
                        assert create_args.id == "test-user456"
                        assert create_args.email == "test-user456@dev.local"


                        @pytest.mark.asyncio
                        async def test_state_persistence_skips_creation_for_regular_users(mock_db_session, sample_state):
                            """Test that regular (non-dev) users are not auto-created if missing."""
    
                            regular_request = StatePersistenceRequest(
                            run_id=f"run_{uuid.uuid4()}",
                            thread_id="thread_regular-user789",
                            user_id="regular-user789",
                            state_data=sample_state.model_dump(),
                            checkpoint_type=CheckpointType.AUTO,
                            is_recovery_point=True,
                            execution_context={"step_count": 0}
                            )
    
                            with patch('netra_backend.app.services.user_service.user_service') as mock_user_service:
                                mock_user_service.get = AsyncMock(return_value=None)
                                mock_user_service.create = AsyncNone  # TODO: Use real service instance
        
        # Should still try to save, but without creating user
        # This will likely fail with FK violation, but that's expected for regular users
                                await state_persistence_service.save_agent_state(regular_request, mock_db_session)
        
        # Verify user was checked but NOT created (since it's not a dev user)
                                mock_user_service.get.assert_called_once()
                                mock_user_service.create.assert_not_called()


                                @pytest.mark.asyncio
                                async def test_state_persistence_handles_empty_user_id(mock_db_session, sample_state):
                                    """Test that empty/None user_id is handled gracefully."""
    
                                    no_user_request = StatePersistenceRequest(
                                    run_id=f"run_{uuid.uuid4()}",
                                    thread_id="thread_anonymous",
                                    user_id=None,  # No user_id
                                    state_data=sample_state.model_dump(),
                                    checkpoint_type=CheckpointType.AUTO,
                                    is_recovery_point=True,
                                    execution_context={"step_count": 0}
                                    )
    
                                    with patch('netra_backend.app.services.user_service.user_service') as mock_user_service:
                                        mock_user_service.get = AsyncNone  # TODO: Use real service instance
                                        mock_user_service.create = AsyncNone  # TODO: Use real service instance
        
                                        await state_persistence_service.save_agent_state(no_user_request, mock_db_session)
        
        # Should not attempt to look up or create user when user_id is None
                                        mock_user_service.get.assert_not_called()
                                        mock_user_service.create.assert_not_called()
                                        pass