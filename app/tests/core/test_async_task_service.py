"""Tests for AsyncTaskService functionality."""

import pytest
from unittest.mock import patch

from app.core.service_interfaces import AsyncTaskService


class TestAsyncTaskService:
    """Test AsyncTaskService functionality."""
    
    def test_initialization(self):
        """Test AsyncTaskService initialization."""
        service = AsyncTaskService("task-service")
        
        assert service.service_name == "task-service"
        assert hasattr(service, '_background_running')
        if hasattr(service, '_background_running'):
            assert not service._background_running
        if hasattr(service, '_monitor_task'):
            assert service._monitor_task == None

    def _verify_background_running(self, service, expected_state):
        """Helper: Verify background running state."""
        assert service._background_running == expected_state

    def _verify_mock_start_calls(self, mock_start, expected_calls):
        """Helper: Verify start implementation calls."""
        assert mock_start.call_count == expected_calls

    async def test_start_background_tasks(self):
        """Test starting background tasks."""
        service = AsyncTaskService("task-service")
        
        # Mock the implementation
        with patch.object(service, '_start_background_tasks_impl') as mock_start:
            await service.start_background_tasks()
            
            self._verify_background_running(service, True)
            self._verify_mock_start_calls(mock_start, 1)

    async def test_start_background_tasks_idempotent(self):
        """Test that starting background tasks is idempotent."""
        service = AsyncTaskService("task-service")
        
        with patch.object(service, '_start_background_tasks_impl') as mock_start:
            await service.start_background_tasks()
            await service.start_background_tasks()  # Second call
            
            self._verify_mock_start_calls(mock_start, 1)  # Should only be called once

    def _setup_background_tasks(self, service):
        """Helper: Setup service with background tasks running."""
        with patch.object(service, '_start_background_tasks_impl'):
            return service.start_background_tasks()

    def _verify_stop_calls(self, mock_stop, mock_cancel):
        """Helper: Verify stop and cancel calls."""
        mock_stop.assert_called_once()
        mock_cancel.assert_called_once()

    async def test_stop_background_tasks(self):
        """Test stopping background tasks."""
        service = AsyncTaskService("task-service")
        
        # Start tasks first
        await self._setup_background_tasks(service)
        
        # Now stop them
        with patch.object(service, '_stop_background_tasks_impl') as mock_stop:
            with patch.object(service, '_cancel_background_tasks') as mock_cancel:
                await service.stop_background_tasks()
                
                self._verify_background_running(service, False)
                self._verify_stop_calls(mock_stop, mock_cancel)