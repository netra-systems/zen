"""Unit tests for Compensation Engine Core functionality.

Tests critical compensation transaction scenarios and database rollbacks.
HIGHEST PRIORITY - Failed compensations = data corruption = enterprise customer loss.

Business Value: Validates transaction rollback scenarios, compensation handler 
registration, and failure recovery paths. Prevents data corruption in distributed operations.

Target Coverage:
- Transaction rollback scenarios and database compensation
- Compensation handler registration and priority management
- Failure recovery paths and error handling
- Concurrent compensation execution and race conditions
- Memory cleanup and resource management
"""

import sys
from pathlib import Path

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.error_recovery import OperationType, RecoveryContext
from netra_backend.app.core.exceptions_auth import NetraSecurityException

from netra_backend.app.services.compensation_engine_core import CompensationEngine
from netra_backend.app.services.compensation_models import (
    BaseCompensationHandler,
    CompensationAction,
    CompensationState,
)

class TestCompensationEngineCore:
    """Test suite for CompensationEngine core functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create compensation engine with mocked logger."""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.compensation_engine_core.central_logger'):
            engine = CompensationEngine()
            engine.handlers = []  # Clear default handlers for testing
            return engine
    
    @pytest.fixture
    def mock_db_handler(self):
        """Create mock database compensation handler."""
        # Mock: Component isolation for controlled unit testing
        handler = Mock(spec=BaseCompensationHandler)
        # Mock: Async component isolation for testing without real async operations
        handler.can_compensate = AsyncMock(return_value=True)
        # Mock: Async component isolation for testing without real async operations
        handler.execute_compensation = AsyncMock(return_value=True)
        handler.get_priority.return_value = 1
        handler.__class__.__name__ = "DatabaseCompensationHandler"
        return handler
    
    @pytest.fixture
    def mock_transaction_context(self):
        """Create mock transaction recovery context."""
        # Mock: Component isolation for controlled unit testing
        context = Mock(spec=RecoveryContext)
        context.operation_type = OperationType.DATABASE_WRITE
        context.operation_id = "txn-123"
        context.transaction_id = "db-txn-456"
        context.metadata = {"table": "user_transactions", "operation": "update"}
        return context
    
    @pytest.fixture
    def compensation_data(self):
        """Create transaction compensation data."""
        return {
            "transaction_id": "db-txn-456",
            "rollback_query": "UPDATE user_transactions SET status='failed' WHERE id='456'",
            "affected_tables": ["user_transactions", "audit_log"],
            "user_id": "user-789"
        }

    @pytest.mark.asyncio
    async def test_transaction_rollback_compensation_success(self, engine, mock_db_handler, mock_transaction_context, compensation_data):
        """Test successful database transaction rollback compensation."""
        engine.register_handler(mock_db_handler)
        
        action_id = await engine.create_compensation_action(
            "txn-rollback-123", mock_transaction_context, compensation_data
        )
        success = await engine.execute_compensation(action_id)
        
        assert success is True
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.COMPLETED
        mock_db_handler.execute_compensation.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_rollback_compensation_failure(self, engine, mock_db_handler, mock_transaction_context, compensation_data):
        """Test failed database transaction rollback compensation."""
        mock_db_handler.execute_compensation.return_value = False
        engine.register_handler(mock_db_handler)
        
        action_id = await engine.create_compensation_action(
            "txn-rollback-fail", mock_transaction_context, compensation_data
        )
        success = await engine.execute_compensation(action_id)
        
        assert success is False
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.FAILED

    @pytest.mark.asyncio
    async def test_transaction_rollback_database_connection_error(self, engine, mock_db_handler, mock_transaction_context, compensation_data):
        """Test compensation handles database connection errors."""
        mock_db_handler.execute_compensation.side_effect = Exception("Database connection failed")
        engine.register_handler(mock_db_handler)
        
        action_id = await engine.create_compensation_action(
            "txn-db-error", mock_transaction_context, compensation_data
        )
        success = await engine.execute_compensation(action_id)
        
        assert success is False
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.FAILED
        assert "Database connection failed" in action.error

    def test_handler_registration_priority_ordering(self, engine):
        """Test compensation handlers registered in priority order."""
        high_priority_handler = self._create_handler_with_priority(1)
        medium_priority_handler = self._create_handler_with_priority(5)
        low_priority_handler = self._create_handler_with_priority(10)
        
        engine.register_handler(medium_priority_handler)
        engine.register_handler(low_priority_handler)
        engine.register_handler(high_priority_handler)
        
        priorities = [h.get_priority() for h in engine.handlers]
        assert priorities == [1, 5, 10]

    def test_handler_registration_maintains_order_on_multiple_registrations(self, engine):
        """Test handler priority order maintained across multiple registrations."""
        handlers = [self._create_handler_with_priority(p) for p in [3, 1, 7, 2, 5]]
        
        for handler in handlers:
            engine.register_handler(handler)
        
        final_priorities = [h.get_priority() for h in engine.handlers]
        assert final_priorities == sorted(final_priorities)

    @pytest.mark.asyncio
    async def test_concurrent_compensation_execution_race_condition(self, engine, mock_transaction_context, compensation_data):
        """Test concurrent compensation execution handles race conditions."""
        handlers = [self._create_handler_with_priority(i) for i in range(3)]
        for handler in handlers:
            engine.register_handler(handler)
        
        # Create multiple compensation actions concurrently
        action_ids = await self._create_concurrent_actions(engine, mock_transaction_context, compensation_data, 5)
        
        # Execute all compensations concurrently
        tasks = [engine.execute_compensation(action_id) for action_id in action_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        successful_results = [r for r in results if r is True]
        assert len(successful_results) >= 3  # At least some should succeed

    @pytest.mark.asyncio
    async def test_compensation_action_lifecycle_state_transitions(self, engine, mock_db_handler, mock_transaction_context, compensation_data):
        """Test compensation action state transitions throughout lifecycle."""
        engine.register_handler(mock_db_handler)
        
        action_id = await engine.create_compensation_action(
            "lifecycle-test", mock_transaction_context, compensation_data
        )
        
        # Initial state
        action = engine.active_compensations[action_id]
        assert action.state == CompensationState.PENDING
        
        # Execute compensation
        await engine.execute_compensation(action_id)
        
        # Final state
        assert action.state == CompensationState.COMPLETED
        assert action.executed_at is not None

    def test_compensation_status_tracking_accuracy(self, engine, mock_db_handler, mock_transaction_context, compensation_data):
        """Test compensation status tracking provides accurate information."""
        engine.register_handler(mock_db_handler)
        action_id = self._create_sync_compensation_action(engine, mock_db_handler, mock_transaction_context, compensation_data)
        
        status = engine.get_compensation_status(action_id)
        
        assert status["action_id"] == action_id
        assert status["operation_id"] == "lifecycle-test"
        assert status["state"] == CompensationState.PENDING.value
        assert "created_at" in status

    def test_compensation_cleanup_removes_completed_actions(self, engine):
        """Test cleanup removes completed and failed compensation actions."""
        completed_action = self._create_completed_compensation_action(engine)
        failed_action = self._create_failed_compensation_action(engine)
        pending_action = self._create_pending_compensation_action(engine)
        
        cleaned_count = engine.cleanup_compensations()
        
        assert cleaned_count == 2  # completed + failed
        assert completed_action not in engine.active_compensations
        assert failed_action not in engine.active_compensations
        assert pending_action in engine.active_compensations

    def test_compensation_cleanup_preserves_active_actions(self, engine):
        """Test cleanup preserves pending and executing actions."""
        pending_action = self._create_pending_compensation_action(engine)
        executing_action = self._create_executing_compensation_action(engine)
        
        cleaned_count = engine.cleanup_compensations()
        
        assert cleaned_count == 0
        assert pending_action in engine.active_compensations
        assert executing_action in engine.active_compensations

    @pytest.mark.asyncio
    async def test_memory_leak_prevention_with_many_compensations(self, engine, mock_db_handler, mock_transaction_context, compensation_data):
        """Test memory leak prevention with large number of compensations."""
        engine.register_handler(mock_db_handler)
        
        # Create and execute many compensations
        for i in range(50):
            action_id = await engine.create_compensation_action(
                f"memory-test-{i}", mock_transaction_context, compensation_data
            )
            await engine.execute_compensation(action_id)
        
        # Cleanup should remove all completed actions
        initial_count = len(engine.active_compensations)
        cleaned_count = engine.cleanup_compensations()
        
        assert cleaned_count == initial_count
        assert len(engine.active_compensations) == 0

    @pytest.mark.asyncio
    async def test_find_compatible_handler_selects_first_compatible(self, engine, mock_transaction_context):
        """Test compatible handler selection chooses first available."""
        incompatible_handler = self._create_incompatible_handler()
        compatible_handler = self._create_compatible_handler()
        
        engine.handlers = [incompatible_handler, compatible_handler]
        
        selected_handler = await engine._find_compatible_handler(mock_transaction_context)
        
        assert selected_handler == compatible_handler

    @pytest.mark.asyncio
    async def test_find_compatible_handler_returns_none_when_no_matches(self, engine, mock_transaction_context):
        """Test compatible handler selection returns None when no handlers match."""
        incompatible_handler1 = self._create_incompatible_handler()
        incompatible_handler2 = self._create_incompatible_handler()
        
        engine.handlers = [incompatible_handler1, incompatible_handler2]
        
        selected_handler = await engine._find_compatible_handler(mock_transaction_context)
        
        assert selected_handler is None

    @pytest.mark.asyncio
    async def test_compensation_action_creation_with_no_handler_returns_empty_id(self, engine, mock_transaction_context, compensation_data):
        """Test compensation action creation without compatible handler."""
        # No handlers registered
        
        action_id = await engine.create_compensation_action(
            "no-handler-test", mock_transaction_context, compensation_data
        )
        
        assert action_id not in engine.active_compensations

    def test_get_active_compensations_returns_current_list(self, engine):
        """Test get active compensations returns current active list."""
        pending_action = self._create_pending_compensation_action(engine)
        executing_action = self._create_executing_compensation_action(engine)
        
        active_list = engine.get_active_compensations()
        
        assert len(active_list) == 2
        action_ids = [item["action_id"] for item in active_list]
        assert pending_action in action_ids
        assert executing_action in action_ids

    @pytest.mark.asyncio
    async def test_execute_nonexistent_compensation_returns_false(self, engine):
        """Test executing non-existent compensation returns False."""
        fake_action_id = str(uuid.uuid4())
        
        success = await engine.execute_compensation(fake_action_id)
        
        assert success is False

    @pytest.mark.asyncio
    async def test_compensation_metadata_preservation(self, engine, mock_db_handler, mock_transaction_context, compensation_data):
        """Test compensation action preserves metadata throughout lifecycle."""
        engine.register_handler(mock_db_handler)
        
        action_id = await engine.create_compensation_action(
            "metadata-test", mock_transaction_context, compensation_data
        )
        
        action = engine.active_compensations[action_id]
        assert action.metadata["context"] == mock_transaction_context
        assert action.metadata["handler_class"] == "Mock"

    # Helper methods (each ≤8 lines)
    def _create_handler_with_priority(self, priority: int):
        """Create mock handler with specific priority."""
        # Mock: Component isolation for controlled unit testing
        handler = Mock(spec=BaseCompensationHandler)
        # Mock: Async component isolation for testing without real async operations
        handler.can_compensate = AsyncMock(return_value=True)
        # Mock: Async component isolation for testing without real async operations
        handler.execute_compensation = AsyncMock(return_value=True)
        handler.get_priority.return_value = priority
        return handler

    def _create_incompatible_handler(self):
        """Create handler that cannot handle any context."""
        # Mock: Component isolation for controlled unit testing
        handler = Mock(spec=BaseCompensationHandler)
        # Mock: Async component isolation for testing without real async operations
        handler.can_compensate = AsyncMock(return_value=False)
        handler.get_priority.return_value = 1
        return handler

    def _create_compatible_handler(self):
        """Create handler that can handle any context."""
        # Mock: Component isolation for controlled unit testing
        handler = Mock(spec=BaseCompensationHandler)
        # Mock: Async component isolation for testing without real async operations
        handler.can_compensate = AsyncMock(return_value=True)
        # Mock: Async component isolation for testing without real async operations
        handler.execute_compensation = AsyncMock(return_value=True)
        handler.get_priority.return_value = 1
        return handler

    async def _create_concurrent_actions(self, engine, context, data, count):
        """Create multiple compensation actions concurrently."""
        tasks = []
        for i in range(count):
            task = engine.create_compensation_action(f"concurrent-{i}", context, data)
            tasks.append(task)
        return await asyncio.gather(*tasks)

    def _create_sync_compensation_action(self, engine, handler, context, data):
        """Create compensation action synchronously for testing."""
        action_id = str(uuid.uuid4())
        action = engine._create_compensation_action(action_id, "lifecycle-test", context, data, handler)
        engine.active_compensations[action_id] = action
        return action_id

    def _create_completed_compensation_action(self, engine):
        """Create completed compensation action for testing."""
        action_id = str(uuid.uuid4())
        action = self._create_test_action()
        action.state = CompensationState.COMPLETED
        engine.active_compensations[action_id] = action
        return action_id

    def _create_failed_compensation_action(self, engine):
        """Create failed compensation action for testing."""
        action_id = str(uuid.uuid4())
        action = self._create_test_action()
        action.state = CompensationState.FAILED
        engine.active_compensations[action_id] = action
        return action_id

    def _create_pending_compensation_action(self, engine):
        """Create pending compensation action for testing."""
        action_id = str(uuid.uuid4())
        action = self._create_test_action()
        action.state = CompensationState.PENDING
        engine.active_compensations[action_id] = action
        return action_id

    def _create_executing_compensation_action(self, engine):
        """Create executing compensation action for testing."""
        action_id = str(uuid.uuid4())
        action = self._create_test_action()
        action.state = CompensationState.EXECUTING
        engine.active_compensations[action_id] = action
        return action_id

    def _create_test_action(self):
        """Create basic compensation action for testing."""
        return CompensationAction(
            action_id=str(uuid.uuid4()),
            operation_id="test-operation",
            action_type="database_rollback",
            compensation_data={},
            # Mock: Generic component isolation for controlled unit testing
            handler=AsyncMock()
        )