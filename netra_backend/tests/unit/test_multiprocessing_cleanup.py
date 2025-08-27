"""Test multiprocessing cleanup functionality."""

import multiprocessing
import sys
import unittest.mock
from unittest.mock import Mock, patch

import pytest

from netra_backend.app.utils.multiprocessing_cleanup import (
    MultiprocessingResourceManager,
    cleanup_multiprocessing,
    mp_resource_manager
)


class TestMultiprocessingResourceManager:
    """Test multiprocessing resource cleanup functionality."""
    
    def test_resource_registration(self):
        """Test registering different types of resources."""
        manager = MultiprocessingResourceManager()
        
        # Mock resources
        mock_process = Mock(spec=multiprocessing.Process)
        mock_pool = Mock(spec=multiprocessing.Pool)
        mock_queue = Mock(spec=multiprocessing.Queue)
        mock_lock = Mock()
        
        # Register resources
        manager.register_process(mock_process)
        manager.register_pool(mock_pool)
        manager.register_queue(mock_queue)
        manager.register_lock(mock_lock)
        
        # Verify resources are stored
        assert len(manager.processes) == 1
        assert len(manager.pools) == 1
        assert len(manager.queues) == 1
        assert len(manager.locks) == 1
        
        assert mock_process in manager.processes
        assert mock_pool in manager.pools
        assert mock_queue in manager.queues
        assert mock_lock in manager.locks
    
    def test_cleanup_processes(self):
        """Test process cleanup functionality."""
        manager = MultiprocessingResourceManager()
        
        # Create mock processes
        alive_process = Mock(spec=multiprocessing.Process)
        alive_process.is_alive.return_value = True
        
        dead_process = Mock(spec=multiprocessing.Process)
        dead_process.is_alive.return_value = False
        
        manager.register_process(alive_process)
        manager.register_process(dead_process)
        
        # Mock the terminate_process_safely function
        with patch('netra_backend.app.utils.multiprocessing_cleanup._terminate_process_safely') as mock_terminate:
            manager._cleanup_processes()
            
            # Verify only alive process is terminated
            mock_terminate.assert_called_once_with(alive_process)
            dead_process.is_alive.assert_called_once()
    
    def test_cleanup_pools(self):
        """Test pool cleanup functionality."""
        manager = MultiprocessingResourceManager()
        
        mock_pool = Mock(spec=multiprocessing.Pool)
        manager.register_pool(mock_pool)
        
        with patch('netra_backend.app.utils.multiprocessing_cleanup._close_pool_safely') as mock_close:
            manager._cleanup_pools()
            mock_close.assert_called_once_with(mock_pool)
    
    def test_cleanup_queues(self):
        """Test queue cleanup functionality."""
        manager = MultiprocessingResourceManager()
        
        mock_queue = Mock(spec=multiprocessing.Queue)
        manager.register_queue(mock_queue)
        
        with patch('netra_backend.app.utils.multiprocessing_cleanup._empty_and_close_queue') as mock_empty:
            manager._cleanup_queues()
            mock_empty.assert_called_once_with(mock_queue)
    
    def test_cleanup_locks(self):
        """Test lock cleanup functionality."""
        manager = MultiprocessingResourceManager()
        
        # Mock lock with release method
        mock_lock = Mock()
        mock_lock.release = Mock()
        
        # Mock lock without release method  
        mock_invalid_lock = Mock(spec=[])  # No release method
        
        manager.register_lock(mock_lock)
        manager.register_lock(mock_invalid_lock)
        
        manager._cleanup_locks()
        
        # Verify only valid lock is released
        mock_lock.release.assert_called_once()
    
    def test_cleanup_all_with_logging_errors(self):
        """Test cleanup_all handles logging errors gracefully."""
        manager = MultiprocessingResourceManager()
        
        # Mock stdout as closed to trigger logging error condition
        with patch.object(sys, 'stdout') as mock_stdout:
            mock_stdout.closed = True
            
            # This should not raise an exception
            manager.cleanup_all()
    
    def test_cleanup_all_with_stream_none(self):
        """Test cleanup_all handles None streams gracefully."""
        manager = MultiprocessingResourceManager()
        
        # Mock stdout as None to trigger AttributeError
        with patch.object(sys, 'stdout', None):
            # This should not raise an exception
            manager.cleanup_all()
    
    def test_global_cleanup_function(self):
        """Test global cleanup_multiprocessing function."""
        with patch.object(mp_resource_manager, 'cleanup_all') as mock_cleanup:
            cleanup_multiprocessing()
            mock_cleanup.assert_called_once()
    
    def test_clear_all_lists(self):
        """Test that all resource lists are cleared."""
        manager = MultiprocessingResourceManager()
        
        # Add some mock resources
        manager.processes.append(Mock())
        manager.pools.append(Mock())
        manager.queues.append(Mock())
        manager.locks.append(Mock())
        
        manager._clear_all_lists()
        
        assert len(manager.processes) == 0
        assert len(manager.pools) == 0
        assert len(manager.queues) == 0
        assert len(manager.locks) == 0