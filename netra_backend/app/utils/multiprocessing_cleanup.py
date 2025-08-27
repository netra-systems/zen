"""
Multiprocessing resource cleanup utilities.
Handles proper cleanup of multiprocessing resources to prevent semaphore leaks.
"""

import atexit
import multiprocessing
import multiprocessing.synchronize
import os
import signal
import sys
from types import FrameType
from typing import List, Optional, Union

from netra_backend.app.core.unified_logging import get_logger

logger = get_logger(__name__)


class MultiprocessingResourceManager:
    """Manages multiprocessing resources and ensures proper cleanup."""
    
    def __init__(self) -> None:
        self.processes: List[multiprocessing.Process] = []
        self.pools: List[multiprocessing.Pool] = []
        self.queues: List[multiprocessing.Queue] = []
        self.locks: List[Union[multiprocessing.synchronize.Lock, multiprocessing.synchronize.Semaphore, multiprocessing.synchronize.RLock]] = []
        self._setup_cleanup_handlers()
    
    def _setup_cleanup_handlers(self) -> None:
        """Set up cleanup handlers for various exit scenarios."""
        # Register cleanup on normal exit
        atexit.register(self.cleanup_all)
        
        # Register cleanup on signals (Unix-like systems)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle signals and cleanup resources."""
        try:
            if hasattr(sys.stdout, 'closed') and not sys.stdout.closed:
                logger.info(f"Received signal {signum}, cleaning up multiprocessing resources...")
        except (OSError, ValueError):
            # Silently ignore logging errors during shutdown
            pass
        self.cleanup_all()
        sys.exit(0)
    
    def register_process(self, process: multiprocessing.Process) -> None:
        """Register a process for cleanup."""
        self.processes.append(process)
    
    def register_pool(self, pool: multiprocessing.Pool) -> None:
        """Register a pool for cleanup."""
        self.pools.append(pool)
    
    def register_queue(self, queue: multiprocessing.Queue) -> None:
        """Register a queue for cleanup."""
        self.queues.append(queue)
    
    def register_lock(self, lock: Union[multiprocessing.synchronize.Lock, multiprocessing.synchronize.Semaphore, multiprocessing.synchronize.RLock]) -> None:
        """Register a lock/semaphore for cleanup."""
        self.locks.append(lock)
    
    def cleanup_all(self) -> None:
        """Clean up all registered multiprocessing resources."""
        self._cleanup_processes()
        self._cleanup_pools()
        self._cleanup_queues()
        self._cleanup_locks()
        self._clear_all_lists()
        # Prevent any logging during test teardown to avoid I/O errors
        try:
            # Check if we're in a test environment
            is_testing = (
                hasattr(sys, 'modules') and 'pytest' in sys.modules or
                os.environ.get('TESTING') == '1' or
                os.environ.get('ENVIRONMENT') == 'testing'
            )
            
            # Only log if not in tests and streams are available
            if not is_testing and (
                hasattr(sys.stdout, 'closed') and not sys.stdout.closed and 
                hasattr(sys.stderr, 'closed') and not sys.stderr.closed and
                sys.stdout is not None and sys.stderr is not None
            ):
                logger.info("Multiprocessing resources cleaned up")
        except (OSError, ValueError, AttributeError, ImportError):
            # Silently ignore all logging errors during shutdown
            pass


# Global instance
mp_resource_manager = MultiprocessingResourceManager()


def setup_multiprocessing() -> None:
    """
    Set up multiprocessing with proper configuration for the platform.
    This should be called early in the application startup.
    """
    # Set start method based on platform
    start_method = _get_platform_start_method()
    _set_multiprocessing_method(start_method)
    logger.info(f"Multiprocessing configured with method: {multiprocessing.get_start_method()}")


def cleanup_multiprocessing() -> None:
    """Manually trigger cleanup of all multiprocessing resources."""
    mp_resource_manager.cleanup_all()


# Add missing methods to the class
setattr(MultiprocessingResourceManager, '_cleanup_processes', lambda self: _cleanup_processes_impl(self))
setattr(MultiprocessingResourceManager, '_cleanup_pools', lambda self: _cleanup_pools_impl(self))
setattr(MultiprocessingResourceManager, '_cleanup_queues', lambda self: _cleanup_queues_impl(self))
setattr(MultiprocessingResourceManager, '_cleanup_locks', lambda self: _cleanup_locks_impl(self))
setattr(MultiprocessingResourceManager, '_clear_all_lists', lambda self: _clear_all_lists_impl(self))


def _cleanup_processes_impl(manager) -> None:
    """Clean up all registered processes."""
    for process in manager.processes:
        try:
            if process.is_alive():
                _terminate_process_safely(process)
        except Exception as e:
            logger.warning(f"Error cleaning up process: {e}")


def _cleanup_pools_impl(manager) -> None:
    """Clean up all registered process pools."""
    for pool in manager.pools:
        try:
            _close_pool_safely(pool)
        except Exception as e:
            logger.warning(f"Error cleaning up pool: {e}")


def _cleanup_queues_impl(manager) -> None:
    """Clean up all registered queues."""
    for queue in manager.queues:
        try:
            _empty_and_close_queue(queue)
        except Exception as e:
            logger.warning(f"Error cleaning up queue: {e}")


def _cleanup_locks_impl(manager) -> None:
    """Clean up all registered locks."""
    for lock in manager.locks:
        try:
            if hasattr(lock, 'release'):
                lock.release()
        except Exception as e:
            logger.warning(f"Error cleaning up lock: {e}")


def _clear_all_lists_impl(manager) -> None:
    """Clear all resource lists."""
    manager.processes.clear()
    manager.pools.clear()
    manager.queues.clear()
    manager.locks.clear()


def _terminate_process_safely(process) -> None:
    """Safely terminate a process with fallback to kill."""
    process.terminate()
    process.join(timeout=1)
    if process.is_alive():
        process.kill()
        process.join(timeout=1)


def _close_pool_safely(pool) -> None:
    """Safely close and terminate a process pool."""
    pool.close()
    pool.terminate()
    pool.join(timeout=1)


def _empty_and_close_queue(queue) -> None:
    """Empty and close a queue safely."""
    while not queue.empty():
        queue.get_nowait()
    queue.close()
    queue.join_thread()


def _get_platform_start_method() -> str:
    """Get the appropriate start method for the platform."""
    if sys.platform == 'darwin':  # macOS
        return 'spawn'  # Avoid issues with fork() on macOS
    elif sys.platform == 'win32':  # Windows
        return 'spawn'  # Windows only supports 'spawn'
    else:  # Linux/Unix
        return 'forkserver'  # Better safety


def _set_multiprocessing_method(method: str) -> None:
    """Set multiprocessing start method with error handling."""
    try:
        multiprocessing.set_start_method(method, force=True)
    except RuntimeError:
        pass  # Already set