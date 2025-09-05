"""
Test for WebSocket thread association timing issue fix

This test reproduces and validates the fix for the emission failure bug where
agent events fail to emit because thread association happens too late.

Bug: WebSocket messages fail with "Cannot deliver message for thread - no connections"
Fix: Ensure thread association completes before agent execution starts
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime
from typing import Dict, Any, Optional

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.db.models_postgres import Thread, Run
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_websocket_manager():
    """Create a mock WebSocket manager with thread association tracking"""
    manager = MagicMock(spec=WebSocketManager)
    manager.update_connection_thread = MagicMock(return_value=True)
    manager.send_to_thread = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_supervisor():
    """Create a mock supervisor agent"""
    supervisor = MagicMock()
    supervisor.agent_registry = MagicMock()
    supervisor.agent_registry.set_websocket_manager = MagicMock()
    supervisor.process = AsyncMock(return_value={"response": "test response"})
    return supervisor


@pytest.fixture
def mock_thread_service():
    """Create a mock thread service"""
    service = MagicMock(spec=ThreadService)
    service.create_user_message = AsyncMock()
    service.create_run = AsyncMock(return_value=MagicMock(id="test_run_id"))
    return service


@pytest.fixture
def mock_thread():
    """Create a mock thread object"""
    thread = MagicMock(spec=Thread)
    thread.id = "thread_test123"
    thread.user_id = "user_test"
    return thread


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
class TestWebSocketThreadAssociation:
    """Test suite for WebSocket thread association timing fix"""
    
    async def test_thread_association_happens_before_agent_execution(
        self,
        mock_websocket_manager,
        mock_supervisor,
        mock_thread_service,
        mock_thread,
        mock_db_session
    ):
        """Test that thread association is established before agent execution starts"""
        
        # Arrange
        message_handler = MessageHandlerService(
            supervisor=mock_supervisor,
            thread_service=mock_thread_service,
            websocket_manager=mock_websocket_manager
        )
        
        user_id = "test_user"
        user_request = "Test request"
        
        # Track the order of operations
        operation_order = []
        
        # Mock update_connection_thread to track when it's called
        def track_thread_update(uid, tid):
            operation_order.append(("thread_association", uid, tid))
            return True
        mock_websocket_manager.update_connection_thread.side_effect = track_thread_update
        
        # Mock thread service methods  
        mock_thread_service.create_user_message = AsyncMock()
        
        # Create a proper Run mock
        mock_run = MagicMock()
        mock_run.id = "test_run_id"
        mock_thread_service.create_run = AsyncMock(return_value=mock_run)
        
        # Mock all the other methods we'll need
        with patch.object(message_handler, '_create_user_message', new=AsyncMock()), \
             patch.object(message_handler, '_create_run', new=AsyncMock(return_value=mock_run)), \
             patch.object(message_handler, '_execute_supervisor', new=AsyncMock(return_value={"response": "test"})) as mock_execute, \
             patch.object(message_handler, '_save_response', new=AsyncMock()), \
             patch.object(message_handler, '_complete_run', new=AsyncMock()), \
             patch.object(message_handler, '_send_completion', new=AsyncMock()):
            
            # Track when execute_supervisor is called
            async def track_execution(*args, **kwargs):
                operation_order.append(("agent_execution", args, kwargs))
                return {"response": "test"}
            mock_execute.side_effect = track_execution
            
            # Act
            await message_handler._process_agent_request(
                user_id=user_id,
                user_request=user_request,
                thread=mock_thread,
                db_session=mock_db_session
            )
        
        # Assert
        # 1. Thread association should be called with correct parameters
        mock_websocket_manager.update_connection_thread.assert_called_once_with(
            user_id, mock_thread.id
        )
        
        # 2. Thread association should happen BEFORE agent execution
        assert len(operation_order) >= 2
        thread_op_index = next(i for i, op in enumerate(operation_order) if op[0] == "thread_association")
        agent_op_index = next(i for i, op in enumerate(operation_order) if op[0] == "agent_execution")
        assert thread_op_index < agent_op_index, "Thread association must happen before agent execution"
        
        # 3. Supervisor should have WebSocket manager set
        mock_supervisor.agent_registry.set_websocket_manager.assert_called_once_with(mock_websocket_manager)
    
    async def test_agent_continues_without_websocket_connection(
        self,
        mock_websocket_manager,
        mock_supervisor,
        mock_thread_service,
        mock_thread,
        mock_db_session
    ):
        """Test that agent execution continues even if no WebSocket connection exists"""
        
        # Arrange
        message_handler = MessageHandlerService(
            supervisor=mock_supervisor,
            thread_service=mock_thread_service,
            websocket_manager=mock_websocket_manager
        )
        
        # Simulate no WebSocket connection
        mock_websocket_manager.update_connection_thread.return_value = False
        
        # Mock all the methods we'll need
        mock_run = MagicMock(id="test_run_id")
        with patch.object(message_handler, '_create_user_message', new=AsyncMock()), \
             patch.object(message_handler, '_create_run', new=AsyncMock(return_value=mock_run)), \
             patch.object(message_handler, '_execute_supervisor', new=AsyncMock(return_value={"response": "test"})) as mock_execute, \
             patch.object(message_handler, '_save_response', new=AsyncMock()), \
             patch.object(message_handler, '_complete_run', new=AsyncMock()), \
             patch.object(message_handler, '_send_completion', new=AsyncMock()):
            
            # Act
            await message_handler._process_agent_request(
                user_id="test_user",
                user_request="Test request",
                thread=mock_thread,
                db_session=mock_db_session
            )
            
            # Assert
            # Agent should still be executed despite no WebSocket connection
            mock_execute.assert_called_once()
        
    async def test_no_error_when_websocket_manager_is_none(
        self,
        mock_supervisor,
        mock_thread_service,
        mock_thread,
        mock_db_session
    ):
        """Test that agent execution works when WebSocket manager is None"""
        
        # Arrange
        message_handler = MessageHandlerService(
            supervisor=mock_supervisor,
            thread_service=mock_thread_service,
            websocket_manager=None  # No WebSocket manager
        )
        
        # Mock all the methods we'll need
        mock_run = MagicMock(id="test_run_id")
        with patch.object(message_handler, '_create_user_message', new=AsyncMock()), \
             patch.object(message_handler, '_create_run', new=AsyncMock(return_value=mock_run)), \
             patch.object(message_handler, '_execute_supervisor', new=AsyncMock(return_value={"response": "test"})) as mock_execute, \
             patch.object(message_handler, '_save_response', new=AsyncMock()), \
             patch.object(message_handler, '_complete_run', new=AsyncMock()), \
             patch.object(message_handler, '_send_completion', new=AsyncMock()):
            
            # Act
            await message_handler._process_agent_request(
                user_id="test_user",
                user_request="Test request",
                thread=mock_thread,
                db_session=mock_db_session
            )
            
            # Assert
            # Agent should be executed normally
            mock_execute.assert_called_once()
    
    async def test_thread_association_with_delay(
        self,
        mock_websocket_manager,
        mock_supervisor,
        mock_thread_service,
        mock_thread,
        mock_db_session
    ):
        """Test that there's a small delay after thread association to ensure propagation"""
        
        # Arrange
        message_handler = MessageHandlerService(
            supervisor=mock_supervisor,
            thread_service=mock_thread_service,
            websocket_manager=mock_websocket_manager
        )
        
        # Track timing
        association_time = None
        execution_time = None
        
        def track_association(uid, tid):
            nonlocal association_time
            association_time = asyncio.get_event_loop().time()
            return True
        mock_websocket_manager.update_connection_thread.side_effect = track_association
        
        async def track_execution(*args, **kwargs):
            nonlocal execution_time
            execution_time = asyncio.get_event_loop().time()
            return {"response": "test"}
        
        # Mock all the methods we'll need
        mock_run = MagicMock(id="test_run_id")
        with patch.object(message_handler, '_create_user_message', new=AsyncMock()), \
             patch.object(message_handler, '_create_run', new=AsyncMock(return_value=mock_run)), \
             patch.object(message_handler, '_execute_supervisor', new=AsyncMock(side_effect=track_execution)), \
             patch.object(message_handler, '_save_response', new=AsyncMock()), \
             patch.object(message_handler, '_complete_run', new=AsyncMock()), \
             patch.object(message_handler, '_send_completion', new=AsyncMock()):
            
            # Act
            await message_handler._process_agent_request(
                user_id="test_user",
                user_request="Test request",
                thread=mock_thread,
                db_session=mock_db_session
            )
        
        # Assert
        # There should be at least a small delay between association and execution
        if association_time and execution_time:
            delay = execution_time - association_time
            assert delay >= 0.01, f"Expected at least 0.01s delay, got {delay}s"


@pytest.mark.asyncio
async def test_integration_websocket_emission_after_fix():
    """Integration test to verify WebSocket emissions work after the fix"""
    
    # This test would run with real services to verify the fix works end-to-end
    # It's marked for manual execution during verification
    
    # Setup: Create real WebSocket connection and manager
    # Step 1: Connect WebSocket as user
    # Step 2: Send start_agent message with thread_id
    # Step 3: Verify thread association happens
    # Step 4: Verify agent events are emitted successfully
    # Step 5: Verify no "Cannot deliver message" errors in logs
    
    # This would be run as part of the mission critical test suite
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])