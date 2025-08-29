"""
Comprehensive tests for ResourceManager - production-critical resource management.

Tests cover memory monitoring, file descriptor tracking, thread pool management,
background task lifecycle, zombie process cleanup, and resource limit enforcement.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, timedelta, UTC
from typing import Dict, Any

import psutil

from netra_backend.app.core.resource_manager import (
    ResourceManager, ResourceLimits, ResourceUsage, ResourceAlert,
    ResourceType, ResourceStatus, resource_manager
)
from netra_backend.app.core.error_types import ResourceError


class TestResourceManagerInitialization:
    """Test ResourceManager initialization and configuration."""
    
    def test_initialization_with_default_limits(self):
        """Test ResourceManager initializes with default limits."""
        manager = ResourceManager()
        
        assert manager.limits.memory_percent == 80.0
        assert manager.limits.threads == 100
        assert manager.limits.processes == 50
        assert manager.monitoring_interval == 30.0
        
    def test_initialization_with_custom_limits(self):
        """Test ResourceManager initializes with custom limits."""
        limits = ResourceLimits(
            memory_mb=1024,
            memory_percent=70.0,
            threads=50,
            processes=25
        )
        
        manager = ResourceManager(limits=limits, monitoring_interval=15.0)
        
        assert manager.limits.memory_mb == 1024
        assert manager.limits.memory_percent == 70.0
        assert manager.limits.threads == 50
        assert manager.monitoring_interval == 15.0
        
    @patch('netra_backend.app.core.resource_manager.tracemalloc')
    def test_tracemalloc_initialization_success(self, mock_tracemalloc):
        """Test successful tracemalloc initialization."""
        mock_tracemalloc.is_tracing.return_value = True
        
        manager = ResourceManager(enable_tracemalloc=True)
        
        mock_tracemalloc.start.assert_called_once()
        
    @patch('netra_backend.app.core.resource_manager.tracemalloc')
    def test_tracemalloc_initialization_failure(self, mock_tracemalloc):
        """Test graceful handling of tracemalloc initialization failure."""
        mock_tracemalloc.start.side_effect = Exception("Tracemalloc failed")
        mock_tracemalloc.is_tracing.return_value = False
        
        manager = ResourceManager(enable_tracemalloc=True)
        
        # Should not raise exception, should log warning
        assert manager.enable_tracemalloc is True


class TestResourceUsageMonitoring:
    """Test resource usage monitoring and calculation."""
    
    @pytest.mark.asyncio
    @patch('netra_backend.app.core.resource_manager.psutil.Process')
    async def test_update_resource_usage_complete(self, mock_process_class):
        """Test complete resource usage update with all metrics."""
        # Mock process with comprehensive resource info
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=1024 * 1024 * 100)  # 100MB
        mock_process.num_fds.return_value = 50
        mock_process.num_threads.return_value = 10
        mock_process.children.return_value = []
        mock_process.cpu_percent.return_value = 15.5
        mock_process_class.return_value = mock_process
        
        # Mock system memory
        with patch('netra_backend.app.core.resource_manager.psutil.virtual_memory') as mock_vm:
            mock_vm.return_value = Mock(total=8 * 1024 * 1024 * 1024)  # 8GB
            
            # Mock resource limits (Unix)
            with patch('netra_backend.app.core.resource_manager.resource') as mock_resource:
                mock_resource.getrlimit.return_value = (1024, 2048)
                
                manager = ResourceManager()
                await manager._update_resource_usage()
                
                usage = manager.current_usage
                assert usage.memory_mb == 100.0
                assert usage.file_descriptors == 50
                assert usage.threads == 10
                assert usage.processes == 0
                assert usage.cpu_percent == 15.5
                assert usage.fd_percent > 0  # Should calculate percentage
                
    @pytest.mark.asyncio
    @patch('netra_backend.app.core.resource_manager.psutil.Process')
    async def test_update_resource_usage_windows(self, mock_process_class):
        """Test resource usage update on Windows (no num_fds)."""
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=1024 * 1024 * 50)  # 50MB
        mock_process.num_threads.return_value = 8
        mock_process.children.return_value = []
        mock_process.cpu_percent.return_value = 10.0
        # Simulate Windows - no num_fds attribute
        del mock_process.num_fds
        mock_process.open_files.return_value = []
        mock_process.connections.return_value = []
        mock_process_class.return_value = mock_process
        
        with patch('netra_backend.app.core.resource_manager.psutil.virtual_memory') as mock_vm:
            mock_vm.return_value = Mock(total=4 * 1024 * 1024 * 1024)  # 4GB
            
            # Simulate Windows - no resource module
            with patch('netra_backend.app.core.resource_manager.resource', None):
                manager = ResourceManager()
                await manager._update_resource_usage()
                
                usage = manager.current_usage
                assert usage.memory_mb == 50.0
                assert usage.file_descriptors == 0  # open_files + connections
                assert usage.fd_percent == 0.0  # Can't determine on Windows
                assert usage.threads == 8
                
    @pytest.mark.asyncio
    async def test_resource_growth_calculation(self):
        """Test resource growth rate calculation over time."""
        manager = ResourceManager()
        
        # Add historical usage data
        base_time = datetime.now(UTC) - timedelta(minutes=2)
        manager.usage_history = [
            ResourceUsage(
                timestamp=base_time,
                memory_mb=100.0,
                file_descriptors=50,
                threads=10
            ),
            ResourceUsage(
                timestamp=base_time + timedelta(minutes=1),
                memory_mb=110.0,
                file_descriptors=55,
                threads=12
            )
        ]
        
        with patch.object(manager, 'process') as mock_process:
            mock_process.memory_info.return_value = Mock(rss=1024 * 1024 * 120)  # 120MB
            mock_process.num_fds.return_value = 60
            mock_process.num_threads.return_value = 15
            mock_process.children.return_value = []
            mock_process.cpu_percent.return_value = 20.0
            
            with patch('netra_backend.app.core.resource_manager.psutil.virtual_memory') as mock_vm:
                mock_vm.return_value = Mock(total=8 * 1024 * 1024 * 1024)
                
                await manager._update_resource_usage()
                
                # Should calculate growth from 1 minute ago
                usage = manager.current_usage
                assert usage.memory_growth_1m == 10.0  # 120 - 110
                assert usage.fd_growth_1m == 5  # 60 - 55
                assert usage.thread_growth_1m == 3  # 15 - 12


class TestResourceLimitChecking:
    """Test resource limit checking and alert generation."""
    
    @pytest.mark.asyncio
    async def test_memory_limit_exceeded_absolute(self):
        """Test alert generation when absolute memory limit exceeded."""
        limits = ResourceLimits(memory_mb=512)
        manager = ResourceManager(limits=limits)
        
        # Set current usage above limit
        manager.current_usage = ResourceUsage(
            memory_mb=600.0,
            memory_percent=60.0
        )
        
        await manager._check_resource_limits()
        
        assert len(manager.alerts) == 1
        alert = manager.alerts[0]
        assert alert.resource_type == ResourceType.MEMORY
        assert alert.status == ResourceStatus.CRITICAL
        assert alert.current_value == 600.0
        assert alert.limit_value == 512
        
    @pytest.mark.asyncio
    async def test_memory_percentage_limit_warning(self):
        """Test warning when memory percentage threshold exceeded."""
        limits = ResourceLimits(memory_percent=75.0)
        manager = ResourceManager(limits=limits)
        
        manager.current_usage = ResourceUsage(
            memory_mb=400.0,
            memory_percent=80.0
        )
        
        await manager._check_resource_limits()
        
        assert len(manager.alerts) == 1
        alert = manager.alerts[0]
        assert alert.resource_type == ResourceType.MEMORY
        assert alert.status == ResourceStatus.WARNING
        assert alert.percentage == 80.0
        
    @pytest.mark.asyncio
    async def test_memory_percentage_critical_threshold(self):
        """Test critical alert when memory usage exceeds 95%."""
        manager = ResourceManager()
        
        manager.current_usage = ResourceUsage(
            memory_mb=400.0,
            memory_percent=96.0
        )
        
        await manager._check_resource_limits()
        
        assert len(manager.alerts) == 1
        alert = manager.alerts[0]
        assert alert.status == ResourceStatus.CRITICAL
        
    @pytest.mark.asyncio
    async def test_alert_history_trimming(self):
        """Test alert history is trimmed when it exceeds maximum."""
        manager = ResourceManager()
        manager.max_alerts = 5
        
        # Generate more alerts than maximum
        for i in range(10):
            manager.current_usage = ResourceUsage(
                memory_mb=400.0 + i,
                memory_percent=85.0 + i
            )
            await manager._check_resource_limits()
        
        # Should keep only the last 5 alerts
        assert len(manager.alerts) == 5


class TestMemoryLeakDetection:
    """Test memory leak detection algorithms."""
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection_positive(self):
        """Test detection of consistent memory growth indicating leak."""
        manager = ResourceManager(monitoring_interval=30.0)  # 30 seconds
        
        # Create usage history showing consistent growth
        base_time = datetime.now(UTC) - timedelta(minutes=5)
        for i in range(10):
            usage = ResourceUsage(
                timestamp=base_time + timedelta(seconds=30 * i),
                memory_mb=100.0 + (i * 10)  # Growing by 10MB each measurement
            )
            manager.usage_history.append(usage)
        
        # This should detect a leak (10MB every 30 seconds = 1200MB/hour)
        with patch.object(manager.logger, 'warning') as mock_warning:
            await manager._detect_memory_leaks()
            
            # Should log warning about potential leak
            mock_warning.assert_called_once()
            args, kwargs = mock_warning.call_args
            assert "memory leak detected" in args[0].lower()
            
    @pytest.mark.asyncio
    async def test_memory_leak_detection_stable(self):
        """Test no leak detection when memory usage is stable."""
        manager = ResourceManager()
        
        # Create stable usage history
        base_time = datetime.now(UTC) - timedelta(minutes=5)
        for i in range(10):
            usage = ResourceUsage(
                timestamp=base_time + timedelta(seconds=30 * i),
                memory_mb=100.0 + (i % 2)  # Stable around 100-101MB
            )
            manager.usage_history.append(usage)
        
        with patch.object(manager.logger, 'warning') as mock_warning:
            await manager._detect_memory_leaks()
            
            # Should not log any warnings
            mock_warning.assert_not_called()
            
    @pytest.mark.asyncio
    async def test_memory_leak_detection_insufficient_history(self):
        """Test no leak detection when insufficient history available."""
        manager = ResourceManager()
        
        # Only a few data points
        for i in range(5):
            usage = ResourceUsage(memory_mb=100.0 + i * 10)
            manager.usage_history.append(usage)
        
        # Should not attempt detection
        await manager._detect_memory_leaks()
        
        # No exception should be raised


class TestResourceCleanup:
    """Test resource cleanup operations."""
    
    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks(self):
        """Test cleanup of completed async tasks."""
        manager = ResourceManager()
        
        # Create mock tasks
        completed_task = Mock()
        completed_task.done.return_value = True
        
        running_task = Mock()
        running_task.done.return_value = False
        
        # Add tasks to tracking
        manager.active_tasks.add(completed_task)
        manager.active_tasks.add(running_task)
        
        count = await manager._cleanup_completed_tasks()
        
        assert count >= 1  # Should count at least the completed task
        
    @pytest.mark.asyncio
    @patch('netra_backend.app.core.resource_manager.psutil')
    async def test_cleanup_zombie_processes(self, mock_psutil):
        """Test cleanup of zombie child processes."""
        manager = ResourceManager()
        
        # Mock zombie process
        zombie_process = Mock()
        zombie_process.status.return_value = mock_psutil.STATUS_ZOMBIE
        
        # Mock normal process
        normal_process = Mock()
        normal_process.status.return_value = mock_psutil.STATUS_RUNNING
        
        manager.process.children.return_value = [zombie_process, normal_process]
        
        count = await manager._cleanup_zombie_processes()
        
        # Should wait for zombie process
        zombie_process.wait.assert_called_once()
        normal_process.wait.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_perform_garbage_collection(self):
        """Test garbage collection execution."""
        manager = ResourceManager()
        
        with patch('netra_backend.app.core.resource_manager.gc.collect', return_value=42) as mock_collect:
            await manager._perform_garbage_collection()
            
            # Should execute garbage collection
            mock_collect.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_emergency_cleanup_triggers(self):
        """Test emergency cleanup is triggered when needed."""
        manager = ResourceManager()
        
        # Set high memory usage
        manager.current_usage = ResourceUsage(memory_percent=90.0)
        
        with patch.object(manager, '_perform_emergency_cleanup') as mock_cleanup:
            await manager._auto_cleanup_if_needed()
            
            mock_cleanup.assert_called_once_with("high_memory")
            
    @pytest.mark.asyncio
    async def test_emergency_cleanup_execution(self):
        """Test emergency cleanup performs all operations."""
        manager = ResourceManager()
        
        with patch.object(manager, '_cleanup_completed_tasks', return_value=5) as mock_tasks:
            with patch.object(manager, '_perform_garbage_collection') as mock_gc:
                with patch.object(manager, '_cleanup_zombie_processes', return_value=2) as mock_zombies:
                    await manager._perform_emergency_cleanup("test_reason")
                    
                    mock_tasks.assert_called_once()
                    mock_gc.assert_called_once()
                    mock_zombies.assert_called_once()


class TestThreadPoolManagement:
    """Test thread pool management functionality."""
    
    def test_get_thread_pool_creates_new(self):
        """Test creating a new thread pool."""
        manager = ResourceManager()
        
        pool = manager.get_thread_pool("test-pool", max_workers=8)
        
        assert pool is not None
        assert "test-pool" in manager.thread_pools
        assert manager.thread_pools["test-pool"] is pool
        
    def test_get_thread_pool_reuses_existing(self):
        """Test reusing existing thread pool."""
        manager = ResourceManager()
        
        pool1 = manager.get_thread_pool("test-pool", max_workers=8)
        pool2 = manager.get_thread_pool("test-pool", max_workers=16)
        
        assert pool1 is pool2  # Should return the same instance
        
    def test_get_thread_pool_default_workers(self):
        """Test thread pool creation with default worker count."""
        manager = ResourceManager()
        
        with patch('netra_backend.app.core.resource_manager.os.cpu_count', return_value=4):
            pool = manager.get_thread_pool("default-pool")
            
            assert pool is not None
            # Default should be min(32, cpu_count + 4) = min(32, 8) = 8


class TestResourceTracking:
    """Test resource tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_track_task(self):
        """Test tracking async tasks."""
        manager = ResourceManager()
        
        task = asyncio.create_task(asyncio.sleep(0.1))
        
        tracked_task = manager.track_task(task)
        
        assert tracked_task is task
        assert task in manager.active_tasks
        
        # Clean up
        await task
        
    def test_track_connection(self):
        """Test tracking connection objects."""
        manager = ResourceManager()
        
        connection = Mock()
        tracked_conn = manager.track_connection(connection)
        
        assert tracked_conn is connection
        assert connection in manager.tracked_connections
        
    def test_register_cleanup_callback(self):
        """Test registering cleanup callbacks."""
        manager = ResourceManager()
        
        callback = Mock()
        manager.register_cleanup_callback(callback)
        
        assert callback in manager.cleanup_callbacks


class TestResourceManagerLifecycle:
    """Test ResourceManager initialization and cleanup lifecycle."""
    
    @pytest.mark.asyncio
    async def test_initialize_starts_monitoring(self):
        """Test initialization starts monitoring tasks."""
        manager = ResourceManager()
        
        with patch.object(manager, '_update_resource_usage') as mock_update:
            await manager.initialize()
            
            assert manager.monitor_task is not None
            assert manager.cleanup_task is not None
            assert not manager.monitor_task.done()
            assert not manager.cleanup_task.done()
            
            # Clean up
            await manager.cleanup()
            
    @pytest.mark.asyncio
    async def test_cleanup_stops_monitoring(self):
        """Test cleanup stops monitoring tasks."""
        manager = ResourceManager()
        
        await manager.initialize()
        
        # Verify tasks are running
        assert manager.monitor_task is not None
        assert not manager.monitor_task.done()
        
        await manager.cleanup()
        
        # Tasks should be done/cancelled
        assert manager.monitor_task.done()
        assert manager.cleanup_task.done()
        
    @pytest.mark.asyncio
    async def test_resource_context_manager(self):
        """Test resource manager as context manager."""
        manager = ResourceManager()
        
        async with manager.resource_context() as ctx:
            assert ctx is manager
            assert manager.monitor_task is not None
            
        # After context, should be cleaned up
        assert manager.monitor_task.done()


class TestResourceStatus:
    """Test resource status reporting."""
    
    def test_get_resource_status_complete(self):
        """Test comprehensive resource status reporting."""
        limits = ResourceLimits(memory_mb=1024, threads=50)
        manager = ResourceManager(limits=limits)
        
        # Set current usage
        manager.current_usage = ResourceUsage(
            memory_mb=512.0,
            memory_percent=50.0,
            file_descriptors=100,
            threads=25,
            processes=2,
            active_tasks=10,
            connections=5,
            cpu_percent=25.0
        )
        
        # Add some alerts
        alert = ResourceAlert(
            resource_type=ResourceType.MEMORY,
            status=ResourceStatus.WARNING,
            current_value=512.0,
            limit_value=1024,
            percentage=50.0,
            message="Test alert"
        )
        manager.alerts.append(alert)
        
        # Add thread pool
        manager.thread_pools["test-pool"] = Mock()
        
        status = manager.get_resource_status()
        
        assert status["current_usage"]["memory_mb"] == 512.0
        assert status["current_usage"]["threads"] == 25
        assert status["limits"]["memory_mb"] == 1024
        assert status["limits"]["threads"] == 50
        assert len(status["alerts"]) == 1
        assert status["alerts"][0]["type"] == "memory"
        assert status["pools"]["thread_pools"] == ["test-pool"]
        
    def test_get_resource_status_no_monitoring(self):
        """Test resource status when monitoring is not running."""
        manager = ResourceManager()
        
        status = manager.get_resource_status()
        
        assert status["monitoring"]["running"] is False


class TestResourceLimits:
    """Test ResourceLimits configuration."""
    
    def test_resource_limits_defaults(self):
        """Test ResourceLimits default values."""
        limits = ResourceLimits()
        
        assert limits.memory_mb is None
        assert limits.memory_percent == 80.0
        assert limits.file_descriptors is None
        assert limits.fd_percent == 80.0
        assert limits.threads == 100
        assert limits.processes == 50
        assert limits.connections == 1000
        
    def test_resource_limits_custom(self):
        """Test ResourceLimits with custom values."""
        limits = ResourceLimits(
            memory_mb=2048,
            memory_percent=70.0,
            threads=200,
            memory_growth_mb_per_min=50.0
        )
        
        assert limits.memory_mb == 2048
        assert limits.memory_percent == 70.0
        assert limits.threads == 200
        assert limits.memory_growth_mb_per_min == 50.0


@pytest.mark.integration
class TestResourceManagerIntegration:
    """Integration tests for ResourceManager with real resource monitoring."""
    
    @pytest.mark.asyncio
    async def test_real_resource_monitoring(self):
        """Test resource monitoring with real system resources."""
        manager = ResourceManager(monitoring_interval=0.1)  # Fast monitoring
        
        try:
            await manager.initialize()
            
            # Wait for at least one monitoring cycle
            await asyncio.sleep(0.2)
            
            # Should have real resource data
            assert manager.current_usage.memory_mb > 0
            assert manager.current_usage.threads > 0
            assert len(manager.usage_history) > 0
            
        finally:
            await manager.cleanup()
            
    @pytest.mark.asyncio
    async def test_thread_pool_integration(self):
        """Test thread pool integration with actual execution."""
        manager = ResourceManager()
        
        def cpu_task():
            return sum(i * i for i in range(1000))
        
        try:
            pool = manager.get_thread_pool("test-integration", max_workers=2)
            
            # Submit tasks
            loop = asyncio.get_event_loop()
            future1 = loop.run_in_executor(pool, cpu_task)
            future2 = loop.run_in_executor(pool, cpu_task)
            
            result1 = await future1
            result2 = await future2
            
            assert result1 == result2  # Both should calculate same result
            
        finally:
            await manager.cleanup()


class TestGlobalResourceManager:
    """Test global resource manager instance."""
    
    def test_global_instance_exists(self):
        """Test global resource manager instance is available."""
        assert resource_manager is not None
        assert isinstance(resource_manager, ResourceManager)
        
    def test_global_instance_singleton(self):
        """Test global resource manager is singleton-like."""
        from netra_backend.app.core.resource_manager import resource_manager as rm2
        
        # Should be the same instance (same module-level variable)
        assert resource_manager is rm2