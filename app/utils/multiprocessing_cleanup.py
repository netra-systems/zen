"""
Multiprocessing resource cleanup utilities.
Handles proper cleanup of multiprocessing resources to prevent semaphore leaks.
"""

import multiprocessing
import atexit
import signal
import sys
import logging
from typing import List, Any

logger = logging.getLogger(__name__)


class MultiprocessingResourceManager:
    """Manages multiprocessing resources and ensures proper cleanup."""
    
    def __init__(self):
        self.processes: List[multiprocessing.Process] = []
        self.pools: List[multiprocessing.Pool] = []
        self.queues: List[multiprocessing.Queue] = []
        self.locks: List[Any] = []
        self._setup_cleanup_handlers()
    
    def _setup_cleanup_handlers(self):
        """Set up cleanup handlers for various exit scenarios."""
        # Register cleanup on normal exit
        atexit.register(self.cleanup_all)
        
        # Register cleanup on signals (Unix-like systems)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle signals and cleanup resources."""
        logger.info(f"Received signal {signum}, cleaning up multiprocessing resources...")
        self.cleanup_all()
        sys.exit(0)
    
    def register_process(self, process: multiprocessing.Process):
        """Register a process for cleanup."""
        self.processes.append(process)
    
    def register_pool(self, pool: multiprocessing.Pool):
        """Register a pool for cleanup."""
        self.pools.append(pool)
    
    def register_queue(self, queue: multiprocessing.Queue):
        """Register a queue for cleanup."""
        self.queues.append(queue)
    
    def register_lock(self, lock: Any):
        """Register a lock/semaphore for cleanup."""
        self.locks.append(lock)
    
    def cleanup_all(self):
        """Clean up all registered multiprocessing resources."""
        # Clean up processes
        for process in self.processes:
            try:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=1)
            except Exception as e:
                logger.warning(f"Error cleaning up process: {e}")
        
        # Clean up pools
        for pool in self.pools:
            try:
                pool.close()
                pool.terminate()
                pool.join(timeout=1)
            except Exception as e:
                logger.warning(f"Error cleaning up pool: {e}")
        
        # Clean up queues
        for queue in self.queues:
            try:
                while not queue.empty():
                    queue.get_nowait()
                queue.close()
                queue.join_thread()
            except Exception as e:
                logger.warning(f"Error cleaning up queue: {e}")
        
        # Clean up locks
        for lock in self.locks:
            try:
                if hasattr(lock, 'release'):
                    lock.release()
            except Exception as e:
                logger.warning(f"Error cleaning up lock: {e}")
        
        # Clear all lists
        self.processes.clear()
        self.pools.clear()
        self.queues.clear()
        self.locks.clear()
        
        logger.info("Multiprocessing resources cleaned up")


# Global instance
mp_resource_manager = MultiprocessingResourceManager()


def setup_multiprocessing():
    """
    Set up multiprocessing with proper configuration for the platform.
    This should be called early in the application startup.
    """
    # Set start method based on platform
    if sys.platform == 'darwin':  # macOS
        # Use 'spawn' to avoid issues with fork() on macOS
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            pass  # Already set
    elif sys.platform == 'win32':  # Windows
        # Windows only supports 'spawn'
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            pass  # Already set
    else:  # Linux/Unix
        # Use 'forkserver' for better safety
        try:
            multiprocessing.set_start_method('forkserver', force=True)
        except RuntimeError:
            pass  # Already set
    
    logger.info(f"Multiprocessing configured with method: {multiprocessing.get_start_method()}")


def cleanup_multiprocessing():
    """Manually trigger cleanup of all multiprocessing resources."""
    mp_resource_manager.cleanup_all()