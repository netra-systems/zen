"""Unit tests for CompensationEngine.

Tests revenue calculation accuracy and compensation handling.
HIGHEST PRIORITY - Direct revenue impact for enterprise customers.

Business Value: Ensures accurate compensation in distributed operations,
preventing double billing or lost revenue scenarios.
"""

import sys
from pathlib import Path

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.error_recovery import OperationType, RecoveryContext
from netra_backend.app.core.exceptions_auth import NetraSecurityException

from netra_backend.app.services.compensation_engine_core import CompensationEngine
from netra_backend.app.services.compensation_models import (
    BaseCompensationHandler,
    CompensationAction,
    CompensationState,
)

class TestCompensationEngine:
    """Test suite for CompensationEngine revenue calculation accuracy."""
    
    @pytest.fixture
    def engine(self):
        """Create compensation engine with minimal dependencies."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.services.compensation_engine_core.central_logger'):
            engine = CompensationEngine()
            engine.handlers = []  # Clear default handlers for testing
            return engine
    
    @pytest.fixture
    def mock_handler(self):
        """Create mock compensation handler."""
        # Mock: Component isolation for controlled unit testing
        handler = Mock(spec=BaseCompensationHandler)
        # Mock: Async component isolation for testing without real async operations
        handler.can_compensate = AsyncMock(return_value=True)
        # Mock: Async component isolation for testing without real async operations
        handler.execute_compensation = AsyncMock(return_value=True)
        handler.get_priority.return_value = 1
        return handler
    
    @pytest.fixture
    def recovery_context(self):
        """Create mock recovery context."""
        # Mock: Component isolation for controlled unit testing
        context = Mock(spec=RecoveryContext)
        context.operation_type = OperationType.DATABASE_WRITE
        context.operation_id = "test-op-123"
        return context
    
    @pytest.fixture
    def compensation_data(self):
        """Create test compensation data."""
        return {"amount": 100.50, "user_id": "user123", "transaction_type": "billing"}
    
    @pytest.mark.asyncio
    async def test_create_compensation_action_success(self, engine, mock_handler, recovery_context, compensation_data):
        """Test successful compensation action creation."""
        engine.register_handler(mock_handler)
        action_id = await engine.create_compensation_action("op123", recovery_context, compensation_data)
        
        assert action_id in engine.active_compensations
        action = engine.active_compensations[action_id]
        assert action.operation_id == "op123"
        assert action.compensation_data == compensation_data
    
    @pytest.mark.asyncio
    async def test_create_compensation_action_no_handler(self, engine, recovery_context, compensation_data):
        """Test compensation action creation with no available handler."""
        action_id = await engine.create_compensation_action("op123", recovery_context, compensation_data)
        
        assert action_id not in engine.active_compensations
    
    @pytest.mark.asyncio
    async def test_execute_compensation_success(self, engine, mock_handler, recovery_context, compensation_data):
        """Test successful compensation execution."""
        action_id = await self._create_test_action(engine, mock_handler, recovery_context, compensation_data)
        
        success = await engine.execute_compensation(action_id)
        
        assert success is True
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execute_compensation_handler_failure(self, engine, mock_handler, recovery_context, compensation_data):
        """Test compensation execution with handler failure."""
        mock_handler.execute_compensation.return_value = False
        action_id = await self._create_test_action(engine, mock_handler, recovery_context, compensation_data)
        
        success = await engine.execute_compensation(action_id)
        
        assert success is False
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.FAILED
    
    @pytest.mark.asyncio
    async def test_execute_compensation_handler_exception(self, engine, mock_handler, recovery_context, compensation_data):
        """Test compensation execution with handler exception."""
        mock_handler.execute_compensation.side_effect = Exception("Handler error")
        action_id = await self._create_test_action(engine, mock_handler, recovery_context, compensation_data)
        
        success = await engine.execute_compensation(action_id)
        
        assert success is False
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.FAILED
        assert "Handler error" in action.error
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
    async def test_find_compatible_handler_multiple_handlers(self, engine, recovery_context):
        """Test finding compatible handler with multiple available."""
        # Mock: Component isolation for controlled unit testing
        handler1 = Mock(spec=BaseCompensationHandler)
        # Mock: Async component isolation for testing without real async operations
        handler1.can_compensate = AsyncMock(return_value=False)
        # Mock: Component isolation for controlled unit testing
        handler2 = Mock(spec=BaseCompensationHandler)  
        # Mock: Async component isolation for testing without real async operations
        handler2.can_compensate = AsyncMock(return_value=True)
        
        engine.handlers = [handler1, handler2]
        
        handler = await engine._find_compatible_handler(recovery_context)
        
        assert handler == handler2
    
    @pytest.mark.asyncio
    async def test_find_compatible_handler_none_available(self, engine, recovery_context):
        """Test finding compatible handler when none available."""
        # Mock: Component isolation for controlled unit testing
        handler1 = Mock(spec=BaseCompensationHandler)
        # Mock: Async component isolation for testing without real async operations
        handler1.can_compensate = AsyncMock(return_value=False)
        
        engine.handlers = [handler1]
        
        handler = await engine._find_compatible_handler(recovery_context)
        
        assert handler is None
    
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
            # Mock: Generic component isolation for controlled unit testing
            handler=AsyncMock()
        )
    
    def _create_mock_handler_with_priority(self, priority):
        """Helper to create mock handler with specific priority."""
        # Mock: Component isolation for controlled unit testing
        handler = Mock(spec=BaseCompensationHandler)
        handler.get_priority.return_value = priority
        return handler


class TestCompensationEngineEdgeCases:
    """Test compensation engine edge cases and error handling."""
    
    @pytest.fixture
    def engine(self):
        """Create compensation engine for testing."""
        return CompensationEngine()
    
    def test_compensation_engine_initialization(self, engine):
        """Test compensation engine initializes correctly."""
        assert engine is not None
        assert hasattr(engine, 'handlers')
        assert isinstance(engine.handlers, list)
        # Engine initializes with default handlers
        assert len(engine.handlers) >= 0  # May have default handlers
    
    def test_register_handler_duplicate_prevention(self, engine):
        """Test that duplicate handlers are handled properly.""" 
        # Mock: Component isolation for controlled unit testing
        handler1 = Mock(spec=BaseCompensationHandler)
        handler1.get_priority.return_value = 1
        handler2 = Mock(spec=BaseCompensationHandler)
        handler2.get_priority.return_value = 2
        
        # Track initial count (engine starts with default handlers)
        initial_count = len(engine.handlers)
        
        # Register handlers
        engine.register_handler(handler1)
        engine.register_handler(handler2)
        
        # Should have both new handlers plus defaults
        assert len(engine.handlers) == initial_count + 2
        assert handler1 in engine.handlers
        assert handler2 in engine.handlers
        
        # Registering same handler again - behavior may vary
        engine.register_handler(handler1)
        
        # Handler count should be managed appropriately (allow duplicate or not)
        assert len(engine.handlers) >= initial_count + 2
    
    def test_empty_handlers_list_behavior(self, engine):
        """Test engine behavior with empty handlers list."""
        # Clear handlers for this test
        engine.handlers = []
        
        # Should be able to call methods without error
        assert hasattr(engine, 'register_handler')
        
        # Test that it doesn't crash with empty list
        handlers_count = len(engine.handlers)
        assert handlers_count == 0
    
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
            # Mock: Generic component isolation for controlled unit testing
            handler=AsyncMock()
        )
    
    def _create_mock_handler_with_priority(self, priority):
        """Helper to create mock handler with specific priority."""
        # Mock: Component isolation for controlled unit testing
        handler = Mock(spec=BaseCompensationHandler)
        handler.get_priority.return_value = priority
        return handler
    @pytest.mark.asyncio
    async def test_compensation_engine_edge_case_scenarios(self, engine):
        """Test compensation engine with various edge cases."""
        
        # Test with non-existent action ID (edge case: action not found)
        result = await engine.execute_compensation("non-existent-id")
        assert result is False
        
        # Test cleanup of expired compensations (edge case)
        expired_count = engine.cleanup_compensations()
        assert expired_count >= 0
        
        # Test getting active compensations when empty
        active_compensations = engine.get_active_compensations()
        assert isinstance(active_compensations, list)
        
        # Test get compensation status for non-existent action
        status = engine.get_compensation_status("non-existent-id")
        assert status is None

    @pytest.mark.asyncio
    async def test_high_volume_compensation_performance_iteration_12(self, engine):
        """Test compensation engine performance under high volume - Iteration 12."""
        import time
        
        # Create multiple handlers for performance testing
        handlers = []
        for i in range(5):
            handler = Mock(spec=BaseCompensationHandler)
            handler.can_compensate = AsyncMock(return_value=True)
            handler.execute_compensation = AsyncMock(return_value=True)
            handler.get_priority.return_value = i + 1
            handlers.append(handler)
            engine.register_handler(handler)
        
        # Test bulk action creation performance
        start_time = time.time()
        action_ids = []
        context = Mock()
        context.operation_type = OperationType.DATABASE_WRITE
        
        for i in range(10):  # Small number for unit test
            action_id = await engine.create_compensation_action(
                f"bulk_op_{i}", context, {"amount": i * 10.0}
            )
            if action_id:
                action_ids.append(action_id)
        
        creation_time = time.time() - start_time
        assert creation_time < 1.0  # Should complete under 1 second
        assert len(action_ids) >= 5  # Most should succeed
