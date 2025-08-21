"""Unit tests for CompensationEngine.

Tests revenue calculation accuracy and compensation handling.
HIGHEST PRIORITY - Direct revenue impact for enterprise customers.

Business Value: Ensures accurate compensation in distributed operations,
preventing double billing or lost revenue scenarios.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.compensation_engine_core import CompensationEngine
from netra_backend.app.services.compensation_models import (

# Add project root to path
    CompensationAction, CompensationState, BaseCompensationHandler
)
from netra_backend.app.core.error_recovery import RecoveryContext, OperationType
from netra_backend.app.core.exceptions_auth import NetraSecurityException


class TestCompensationEngine:
    """Test suite for CompensationEngine revenue calculation accuracy."""
    
    @pytest.fixture
    def engine(self):
        """Create compensation engine with minimal dependencies."""
        with patch('app.services.compensation_engine_core.central_logger'):
            engine = CompensationEngine()
            engine.handlers = []  # Clear default handlers for testing
            return engine
    
    @pytest.fixture
    def mock_handler(self):
        """Create mock compensation handler."""
        handler = Mock(spec=BaseCompensationHandler)
        handler.can_compensate = AsyncMock(return_value=True)
        handler.execute_compensation = AsyncMock(return_value=True)
        handler.get_priority.return_value = 1
        return handler
    
    @pytest.fixture
    def recovery_context(self):
        """Create mock recovery context."""
        context = Mock(spec=RecoveryContext)
        context.operation_type = OperationType.DATABASE_WRITE
        context.operation_id = "test-op-123"
        return context
    
    @pytest.fixture
    def compensation_data(self):
        """Create test compensation data."""
        return {"amount": 100.50, "user_id": "user123", "transaction_type": "billing"}
    
    async def test_create_compensation_action_success(self, engine, mock_handler, recovery_context, compensation_data):
        """Test successful compensation action creation."""
        engine.register_handler(mock_handler)
        action_id = await engine.create_compensation_action("op123", recovery_context, compensation_data)
        
        assert action_id in engine.active_compensations
        action = engine.active_compensations[action_id]
        assert action.operation_id == "op123"
        assert action.compensation_data == compensation_data
    
    async def test_create_compensation_action_no_handler(self, engine, recovery_context, compensation_data):
        """Test compensation action creation with no available handler."""
        action_id = await engine.create_compensation_action("op123", recovery_context, compensation_data)
        
        assert action_id not in engine.active_compensations
        mock_handler.can_compensate.assert_not_called()
    
    async def test_execute_compensation_success(self, engine, mock_handler, recovery_context, compensation_data):
        """Test successful compensation execution."""
        action_id = await self._create_test_action(engine, mock_handler, recovery_context, compensation_data)
        
        success = await engine.execute_compensation(action_id)
        
        assert success is True
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.COMPLETED
    
    async def test_execute_compensation_handler_failure(self, engine, mock_handler, recovery_context, compensation_data):
        """Test compensation execution with handler failure."""
        mock_handler.execute_compensation.return_value = False
        action_id = await self._create_test_action(engine, mock_handler, recovery_context, compensation_data)
        
        success = await engine.execute_compensation(action_id)
        
        assert success is False
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.FAILED
    
    async def test_execute_compensation_handler_exception(self, engine, mock_handler, recovery_context, compensation_data):
        """Test compensation execution with handler exception."""
        mock_handler.execute_compensation.side_effect = Exception("Handler error")
        action_id = await self._create_test_action(engine, mock_handler, recovery_context, compensation_data)
        
        success = await engine.execute_compensation(action_id)
        
        assert success is False
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.FAILED
        assert "Handler error" in action.error
    
    async def test_execute_compensation_nonexistent_action(self, engine):
        """Test compensation execution for non-existent action."""
        fake_id = str(uuid.uuid4())
        
        success = await engine.execute_compensation(fake_id)
        
        assert success is False
    
    def test_get_compensation_status_existing(self, engine, mock_handler, recovery_context, compensation_data):
        """Test getting status of existing compensation action."""
        action_id = self._create_sync_test_action(engine, mock_handler, recovery_context, compensation_data)
        
        status = engine.get_compensation_status(action_id)
        
        assert status is not None
        assert status["action_id"] == action_id
        assert status["operation_id"] == "op123"
        assert status["state"] == CompensationState.PENDING.value
    
    def test_get_compensation_status_nonexistent(self, engine):
        """Test getting status of non-existent compensation action."""
        fake_id = str(uuid.uuid4())
        
        status = engine.get_compensation_status(fake_id)
        
        assert status is None
    
    def test_cleanup_compensations_with_completed(self, engine):
        """Test cleanup of completed compensation actions."""
        completed_action = self._create_completed_action(engine)
        failed_action = self._create_failed_action(engine)
        
        cleaned_count = engine.cleanup_compensations()
        
        assert cleaned_count == 2
        assert completed_action not in engine.active_compensations
        assert failed_action not in engine.active_compensations
    
    def test_cleanup_compensations_empty(self, engine):
        """Test cleanup with no completed actions."""
        cleaned_count = engine.cleanup_compensations()
        
        assert cleaned_count == 0
    
    def test_get_active_compensations(self, engine, mock_handler, recovery_context, compensation_data):
        """Test getting list of active compensations."""
        action_id = self._create_sync_test_action(engine, mock_handler, recovery_context, compensation_data)
        
        active_list = engine.get_active_compensations()
        
        assert len(active_list) == 1
        assert active_list[0]["action_id"] == action_id
    
    def test_register_handler_priority_sorting(self, engine):
        """Test handler registration with priority sorting."""
        handler1 = self._create_mock_handler_with_priority(3)
        handler2 = self._create_mock_handler_with_priority(1)
        handler3 = self._create_mock_handler_with_priority(2)
        
        engine.register_handler(handler1)
        engine.register_handler(handler2)
        engine.register_handler(handler3)
        
        priorities = [h.get_priority() for h in engine.handlers]
        assert priorities == [1, 2, 3]
    
    async def test_find_compatible_handler_multiple_handlers(self, engine, recovery_context):
        """Test finding compatible handler with multiple available."""
        handler1 = Mock(spec=BaseCompensationHandler)
        handler1.can_compensate = AsyncMock(return_value=False)
        handler2 = Mock(spec=BaseCompensationHandler)  
        handler2.can_compensate = AsyncMock(return_value=True)
        
        engine.handlers = [handler1, handler2]
        
        handler = await engine._find_compatible_handler(recovery_context)
        
        assert handler == handler2
    
    async def test_find_compatible_handler_none_available(self, engine, recovery_context):
        """Test finding compatible handler when none available."""
        handler1 = Mock(spec=BaseCompensationHandler)
        handler1.can_compensate = AsyncMock(return_value=False)
        
        engine.handlers = [handler1]
        
        handler = await engine._find_compatible_handler(recovery_context)
        
        assert handler is None
    
    def test_update_action_state_transitions(self, engine):
        """Test action state transitions work correctly."""
        action = self._create_test_action_object()
        
        engine._update_action_state_executing(action)
        assert action.state == CompensationState.EXECUTING
        assert action.executed_at is not None
        
        engine._update_action_state_completed(action)
        assert action.state == CompensationState.COMPLETED
        
        engine._update_action_state_failed(action, "Test error")
        assert action.state == CompensationState.FAILED
        assert action.error == "Test error"
    
    # Helper methods (each ≤8 lines)
    async def _create_test_action(self, engine, handler, context, data):
        """Helper to create test compensation action."""
        engine.register_handler(handler)
        return await engine.create_compensation_action("op123", context, data)
    
    def _create_sync_test_action(self, engine, handler, context, data):
        """Helper to create test action synchronously."""
        engine.register_handler(handler)
        action_id = str(uuid.uuid4())
        action = engine._create_compensation_action(action_id, "op123", context, data, handler)
        engine.active_compensations[action_id] = action
        return action_id
    
    def _create_completed_action(self, engine):
        """Helper to create completed compensation action."""
        action_id = str(uuid.uuid4())
        action = self._create_test_action_object()
        action.state = CompensationState.COMPLETED
        engine.active_compensations[action_id] = action
        return action_id
    
    def _create_failed_action(self, engine):
        """Helper to create failed compensation action."""
        action_id = str(uuid.uuid4())
        action = self._create_test_action_object()
        action.state = CompensationState.FAILED
        engine.active_compensations[action_id] = action
        return action_id
    
    def _create_test_action_object(self):
        """Helper to create CompensationAction object."""
        return CompensationAction(
            action_id=str(uuid.uuid4()),
            operation_id="test-op",
            action_type="test",
            compensation_data={},
            handler=AsyncMock()
        )
    
    def _create_mock_handler_with_priority(self, priority):
        """Helper to create mock handler with specific priority."""
        handler = Mock(spec=BaseCompensationHandler)
        handler.get_priority.return_value = priority
        return handler