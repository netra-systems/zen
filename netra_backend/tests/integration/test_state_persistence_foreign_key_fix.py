import asyncio

# REMOVED_SYNTAX_ERROR: '''Integration test for state persistence foreign key fix.

# REMOVED_SYNTAX_ERROR: This test verifies that the state persistence service properly auto-creates
# REMOVED_SYNTAX_ERROR: dev users to prevent foreign key violations when saving agent state.
""

import uuid
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from netra_backend.app.db.models_agent_state import AgentStateSnapshot
from netra_backend.app.db.models_user import User
# REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.agent_state import ( )
CheckpointType,
StatePersistenceRequest,

from netra_backend.app.services.state_persistence import state_persistence_service
from test_framework.fixtures.database_fixtures import test_db_session


# Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: @pytest.mark.integration
# Removed problematic line: async def test_state_persistence_auto_creates_dev_user(test_db_session):
    # REMOVED_SYNTAX_ERROR: """Test that dev-temp users are auto-created when saving state."""
    # Create a unique dev user ID
    # REMOVED_SYNTAX_ERROR: dev_user_id = "formatted_string",
    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: user_id=dev_user_id,
    # REMOVED_SYNTAX_ERROR: state_data={ )
    # REMOVED_SYNTAX_ERROR: "conversation": [],
    # REMOVED_SYNTAX_ERROR: "current_step": 0,
    # REMOVED_SYNTAX_ERROR: "metadata": {"test": True},
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat()
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: checkpoint_type=CheckpointType.AUTO,
    # REMOVED_SYNTAX_ERROR: execution_context={"source": "integration_test"},
    # REMOVED_SYNTAX_ERROR: is_recovery_point=False
    

    # Verify user doesn't exist initially
    # REMOVED_SYNTAX_ERROR: result = await test_db_session.execute( )
    # REMOVED_SYNTAX_ERROR: select(User).where(User.id == dev_user_id)
    
    # REMOVED_SYNTAX_ERROR: initial_user = result.scalar_one_or_none()
    # REMOVED_SYNTAX_ERROR: assert initial_user is None, "User should not exist initially"

    # Save agent state - this should auto-create the user
    # REMOVED_SYNTAX_ERROR: success, snapshot_id = await state_persistence_service.save_agent_state( )
    # REMOVED_SYNTAX_ERROR: request, test_db_session
    

    # Verify the save succeeded
    # REMOVED_SYNTAX_ERROR: assert success is True, "State save should succeed"
    # REMOVED_SYNTAX_ERROR: assert snapshot_id is not None, "Should return a snapshot ID"

    # Verify the user was created
    # REMOVED_SYNTAX_ERROR: result = await test_db_session.execute( )
    # REMOVED_SYNTAX_ERROR: select(User).where(User.id == dev_user_id)
    
    # REMOVED_SYNTAX_ERROR: created_user = result.scalar_one_or_none()
    # REMOVED_SYNTAX_ERROR: assert created_user is not None, "User should be auto-created"
    # REMOVED_SYNTAX_ERROR: assert created_user.id == dev_user_id
    # REMOVED_SYNTAX_ERROR: assert created_user.email == "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert created_user.is_developer is True
    # REMOVED_SYNTAX_ERROR: assert created_user.role == "developer"

    # Verify the snapshot was saved
    # REMOVED_SYNTAX_ERROR: result = await test_db_session.execute( )
    # REMOVED_SYNTAX_ERROR: select(AgentStateSnapshot).where(AgentStateSnapshot.id == snapshot_id)
    
    # REMOVED_SYNTAX_ERROR: snapshot = result.scalar_one_or_none()
    # REMOVED_SYNTAX_ERROR: assert snapshot is not None, "Snapshot should be saved"
    # REMOVED_SYNTAX_ERROR: assert snapshot.user_id == dev_user_id


    # Removed problematic line: @pytest.mark.asyncio
    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
    # Removed problematic line: async def test_state_persistence_handles_existing_user(test_db_session):
        # REMOVED_SYNTAX_ERROR: """Test that existing users are not recreated."""
        # Create a user first
        # REMOVED_SYNTAX_ERROR: existing_user = User( )
        # REMOVED_SYNTAX_ERROR: id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id=f"thread_existing",
        # REMOVED_SYNTAX_ERROR: user_id=existing_user.id,
        # REMOVED_SYNTAX_ERROR: state_data={ )
        # REMOVED_SYNTAX_ERROR: "conversation": [],
        # REMOVED_SYNTAX_ERROR: "current_step": 0,
        # REMOVED_SYNTAX_ERROR: "metadata": {"test": True}
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: checkpoint_type=CheckpointType.MANUAL,
        # REMOVED_SYNTAX_ERROR: execution_context={"source": "integration_test"},
        # REMOVED_SYNTAX_ERROR: is_recovery_point=False
        

        # Save agent state
        # REMOVED_SYNTAX_ERROR: success, snapshot_id = await state_persistence_service.save_agent_state( )
        # REMOVED_SYNTAX_ERROR: request, test_db_session
        

        # Verify save succeeded
        # REMOVED_SYNTAX_ERROR: assert success is True
        # REMOVED_SYNTAX_ERROR: assert snapshot_id is not None

        # Verify user wasn't modified
        # REMOVED_SYNTAX_ERROR: await test_db_session.refresh(existing_user)
        # REMOVED_SYNTAX_ERROR: assert existing_user.email == "existing@test.com"
        # REMOVED_SYNTAX_ERROR: assert existing_user.role == "standard_user"


        # Removed problematic line: @pytest.mark.asyncio
        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
        # Removed problematic line: async def test_state_persistence_auto_creates_test_user(test_db_session):
            # REMOVED_SYNTAX_ERROR: """Test that test- prefixed users are also auto-created."""
            # Create a unique test user ID
            # REMOVED_SYNTAX_ERROR: test_user_id = "formatted_string",
            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: user_id=test_user_id,
            # REMOVED_SYNTAX_ERROR: state_data={ )
            # REMOVED_SYNTAX_ERROR: "conversation": [],
            # REMOVED_SYNTAX_ERROR: "current_step": 0,
            # REMOVED_SYNTAX_ERROR: "metadata": {"test": True}
            # REMOVED_SYNTAX_ERROR: },
            # REMOVED_SYNTAX_ERROR: checkpoint_type=CheckpointType.AUTO,
            # REMOVED_SYNTAX_ERROR: execution_context={"source": "integration_test"},
            # REMOVED_SYNTAX_ERROR: is_recovery_point=True
            

            # Save agent state - should auto-create the test user
            # REMOVED_SYNTAX_ERROR: success, snapshot_id = await state_persistence_service.save_agent_state( )
            # REMOVED_SYNTAX_ERROR: request, test_db_session
            

            # Verify the save succeeded
            # REMOVED_SYNTAX_ERROR: assert success is True
            # REMOVED_SYNTAX_ERROR: assert snapshot_id is not None

            # Verify the test user was created
            # REMOVED_SYNTAX_ERROR: result = await test_db_session.execute( )
            # REMOVED_SYNTAX_ERROR: select(User).where(User.id == test_user_id)
            
            # REMOVED_SYNTAX_ERROR: created_user = result.scalar_one_or_none()
            # REMOVED_SYNTAX_ERROR: assert created_user is not None
            # REMOVED_SYNTAX_ERROR: assert created_user.id == test_user_id
            # REMOVED_SYNTAX_ERROR: assert created_user.email == "formatted_string"
            # REMOVED_SYNTAX_ERROR: assert created_user.is_developer is True


            # Removed problematic line: @pytest.mark.asyncio
            # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
            # Removed problematic line: async def test_state_persistence_skips_regular_user_creation(test_db_session):
                # REMOVED_SYNTAX_ERROR: """Test that regular (non-dev/test) users are NOT auto-created."""
                # Create a regular user ID (doesn't match dev/test pattern)
                # REMOVED_SYNTAX_ERROR: regular_user_id = "formatted_string",
                # REMOVED_SYNTAX_ERROR: thread_id=f"thread_regular",
                # REMOVED_SYNTAX_ERROR: user_id=regular_user_id,
                # REMOVED_SYNTAX_ERROR: state_data={ )
                # REMOVED_SYNTAX_ERROR: "conversation": [],
                # REMOVED_SYNTAX_ERROR: "current_step": 0,
                # REMOVED_SYNTAX_ERROR: "metadata": {"test": True}
                # REMOVED_SYNTAX_ERROR: },
                # REMOVED_SYNTAX_ERROR: checkpoint_type=CheckpointType.AUTO,
                # REMOVED_SYNTAX_ERROR: execution_context={"source": "integration_test"},
                # REMOVED_SYNTAX_ERROR: is_recovery_point=False
                

                # Attempt to save agent state - should fail with FK violation
                # REMOVED_SYNTAX_ERROR: success, snapshot_id = await state_persistence_service.save_agent_state( )
                # REMOVED_SYNTAX_ERROR: request, test_db_session
                

                # Verify the save failed (expected for security)
                # REMOVED_SYNTAX_ERROR: assert success is False, "Should fail for non-dev users"
                # REMOVED_SYNTAX_ERROR: assert snapshot_id is None

                # Verify no user was created
                # REMOVED_SYNTAX_ERROR: result = await test_db_session.execute( )
                # REMOVED_SYNTAX_ERROR: select(User).where(User.id == regular_user_id)
                
                # REMOVED_SYNTAX_ERROR: user = result.scalar_one_or_none()
                # REMOVED_SYNTAX_ERROR: assert user is None, "Regular users should NOT be auto-created"


                # Removed problematic line: @pytest.mark.asyncio
                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                # Removed problematic line: async def test_state_persistence_handles_run_prefix(test_db_session):
                    # REMOVED_SYNTAX_ERROR: """Test that run_ prefixed IDs skip persistence entirely."""
                    # Create persistence request with run_ prefix (temp test ID)
                    # REMOVED_SYNTAX_ERROR: request = StatePersistenceRequest( )
                    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread_test",
                    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",  # run_ prefix should skip persistence
                    # REMOVED_SYNTAX_ERROR: state_data={ )
                    # REMOVED_SYNTAX_ERROR: "conversation": [],
                    # REMOVED_SYNTAX_ERROR: "current_step": 0
                    # REMOVED_SYNTAX_ERROR: },
                    # REMOVED_SYNTAX_ERROR: checkpoint_type=CheckpointType.AUTO,
                    # REMOVED_SYNTAX_ERROR: execution_context={"source": "integration_test"},
                    # REMOVED_SYNTAX_ERROR: is_recovery_point=False
                    

                    # Save agent state - should return dummy ID without DB interaction
                    # REMOVED_SYNTAX_ERROR: success, snapshot_id = await state_persistence_service.save_agent_state( )
                    # REMOVED_SYNTAX_ERROR: request, test_db_session
                    

                    # Verify it returns success with a dummy ID
                    # REMOVED_SYNTAX_ERROR: assert success is True
                    # REMOVED_SYNTAX_ERROR: assert snapshot_id is not None

                    # Verify no snapshot was actually saved to DB
                    # REMOVED_SYNTAX_ERROR: result = await test_db_session.execute( )
                    # REMOVED_SYNTAX_ERROR: select(AgentStateSnapshot).where(AgentStateSnapshot.id == snapshot_id)
                    
                    # REMOVED_SYNTAX_ERROR: snapshot = result.scalar_one_or_none()
                    # REMOVED_SYNTAX_ERROR: assert snapshot is None, "No snapshot should be saved for run_ prefixed IDs"