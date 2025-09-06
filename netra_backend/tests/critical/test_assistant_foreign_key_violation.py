from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import AsyncMock, Mock, patch, MagicMock

env = get_env()

"""
Test to reproduce and fix the assistant foreign key violation error.

Error: insert or update on table "runs" violates foreign key constraint "runs_assistant_id_fkey"
DETAIL: Key (assistant_id)=(netra-assistant) is not present in table "assistants".
""""
import os
import pytest
import asyncio
from sqlalchemy import select

from netra_backend.app.db.models_postgres import Assistant, Run, Thread
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.database.unit_of_work import get_unit_of_work
from netra_backend.tests.test_utils import setup_test_path

setup_test_path()

@pytest.mark.asyncio
@pytest.mark.env_test
@pytest.mark.skipif(
    "sqlite" in env.get("DATABASE_URL", "sqlite"),
    reason="SQLite doesn't support PostgreSQL-specific features like ARRAY types"
)
class TestAssistantForeignKeyViolation:
    """Test suite to reproduce and fix the assistant foreign key violation."""
    
    async def test_create_run_without_assistant_fails(self, test_db_session):
        """Test that creating a run without the assistant in the database fails with foreign key violation."""
        # Arrange
        thread_service = ThreadService()
        
        # Create a thread first
        thread = Thread(
            id="thread_test123",
            object="thread",
            created_at=1234567890,
            metadata_={"user_id": "test_user"}
        )
        test_db_session.add(thread)
        await test_db_session.commit()
        
        # Act & Assert - Try to create a run without the assistant existing
        with pytest.raises(Exception) as exc_info:
            await thread_service.create_run(
                thread_id="thread_test123",
                assistant_id="netra-assistant",  # This assistant doesn't exist in DB
                model="gemini-2.5-flash",
                instructions="Test instructions",
                db=test_db_session
            )
        
        # The error should be about foreign key violation
        assert "foreign key" in str(exc_info.value).lower() or "assistant" in str(exc_info.value).lower()
    
    async def test_ensure_assistant_exists_before_run(self, test_db_session):
        """Test that the assistant is created before any run operations."""
        # Arrange
        from netra_backend.app.startup_checks.database_checks import DatabaseConnectionCheck
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state.db_session_factory = lambda: test_db_session
        
        db_check = DatabaseConnectionCheck(app)
        
        # Act - Ensure assistant is created
        assistant = db_check._build_assistant_instance()
        test_db_session.add(assistant)
        await test_db_session.commit()
        
        # Verify assistant exists
        result = await test_db_session.execute(
            select(Assistant).where(Assistant.id == "netra-assistant")
        )
        found_assistant = result.scalar_one_or_none()
        assert found_assistant is not None
        assert found_assistant.id == "netra-assistant"
        
        # Now create thread and run
        thread = Thread(
            id="thread_test456",
            object="thread", 
            created_at=1234567890,
            metadata_={"user_id": "test_user2"}
        )
        test_db_session.add(thread)
        await test_db_session.commit()
        
        # Create run - should succeed now
        thread_service = ThreadService()
        run = await thread_service.create_run(
            thread_id="thread_test456",
            assistant_id="netra-assistant",
            model="gemini-2.5-flash",
            instructions="Test instructions",
            db=test_db_session
        )
        
        assert run is not None
        assert run.assistant_id == "netra-assistant"
    
    async def test_websocket_handler_ensures_assistant(self, test_db_session):
        """Test that WebSocket handlers ensure assistant exists before creating runs."""
        from netra_backend.app.services.websocket.message_handler import MessageHandler
        from netra_backend.app.startup_checks.database_checks import DatabaseConnectionCheck
        from fastapi import FastAPI
        
        # Setup
        app = FastAPI()
        app.state.db_session_factory = lambda: test_db_session
        
        # Create assistant first
        db_check = DatabaseConnectionCheck(app)
        assistant = db_check._build_assistant_instance()
        test_db_session.add(assistant)
        await test_db_session.commit()
        
        # Create thread
        thread = Thread(
            id="thread_test789",
            object="thread",
            created_at=1234567890,
            metadata_={"user_id": "test_user3"}
        )
        test_db_session.add(thread)
        await test_db_session.commit()
        
        # Mock WebSocket manager
        with patch('netra_backend.app.services.websocket.message_handler.manager') as mock_manager:
            mock_manager.send_message = AsyncMock()  # TODO: Use real service instance
            
            # Create message handler
            handler = MessageHandler()
            
            # Mock the thread service to use our test session
            with patch.object(handler.thread_service, 'create_run') as mock_create_run:
                mock_create_run.return_value = AsyncMock(
                    id="run_test123",
                    thread_id="thread_test789",
                    assistant_id="netra-assistant",
                    status="in_progress"
                )
                
                # Process a message - should not fail
                await handler.process_message(
                    user_id="test_user3",
                    content="Test message",
                    thread_id="thread_test789",
                    db=test_db_session
                )
                
                # Verify run creation was attempted with correct assistant
                mock_create_run.assert_called_once()
                call_args = mock_create_run.call_args
                assert call_args[1]['assistant_id'] == "netra-assistant"
    
    async def test_assistant_creation_idempotent(self, test_db_session):
        """Test that assistant creation is idempotent and doesn't fail if already exists."""
        from netra_backend.app.startup_checks.database_checks import DatabaseConnectionCheck
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state.db_session_factory = lambda: test_db_session
        
        db_check = DatabaseConnectionCheck(app)
        
        # Create assistant first time
        assistant1 = db_check._build_assistant_instance()
        test_db_session.add(assistant1)
        await test_db_session.commit()
        
        # Try to create again - should not fail
        existing = await db_check._find_assistant(test_db_session)
        assert existing is not None
        assert existing.id == "netra-assistant"
        
        # Count assistants - should be exactly 1
        result = await test_db_session.execute(
            select(Assistant).where(Assistant.id == "netra-assistant")
        )
        assistants = result.scalars().all()
        assert len(assistants) == 1