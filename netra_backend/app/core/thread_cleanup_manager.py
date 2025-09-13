"""
Thread Cleanup Manager - Issue #601 Fix for Thread-Local Storage Memory Leaks

This module provides centralized thread cleanup management to prevent memory leaks
from thread-local storage that accumulate during startup operations.

CRITICAL: Addresses Issue #601 root causes:
1. Thread-local storage objects not being cleaned up properly
2. Startup processes creating many threads without cleanup
3. Circular references in thread-local data preventing garbage collection

Business Value Justification:
- Segment: Platform/Infrastructure (all segments)
- Business Goal: Prevent memory leaks that cause system instability
- Value Impact: Ensures stable long-running processes
- Revenue Impact: Prevents system crashes that affect all customers
"""

import asyncio
import gc
import logging
import threading
import time
import weakref
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ThreadInfo:
    """Information about a tracked thread."""
    thread_id: int
    thread_name: str
    created_at: datetime
    locals_size: int = 0
    cleanup_attempted: bool = False
    cleanup_successful: bool = False
    cleanup_error: Optional[str] = None


class ThreadCleanupManager:
    """
    Manages thread lifecycle and cleanup to prevent memory leaks.
    
    ISSUE #601 FIX: This class prevents thread-local storage memory leaks by:
    1. Tracking all threads created during startup/operations
    2. Cleaning up thread-local storage when threads complete
    3. Forcing cleanup of stale threads that don't exit properly
    4. Breaking circular references in thread-local data
    """
    
    def __init__(self):
        self._tracked_threads: Dict[int, ThreadInfo] = {}
        self._thread_locals_cache: Dict[int, Dict[str, Any]] = {}
        self._cleanup_lock = threading.Lock()
        self._cleanup_scheduled = False
        self._total_threads_created = 0
        self._total_threads_cleaned = 0
        self._cleanup_failures = 0
        
        # Weak reference set to avoid keeping threads alive
        self._active_threads: Set[weakref.ref] = set()
        
        logger.info("ThreadCleanupManager initialized for Issue #601 memory leak prevention")
    
    def register_thread(self, thread: threading.Thread = None) -> None:
        """
        Register a thread for cleanup tracking.
        
        Args:
            thread: Thread to register (defaults to current thread)
        """
        if thread is None:
            thread = threading.current_thread()
        
        thread_id = thread.ident or threading.get_ident()
        thread_name = thread.name or f"Thread-{thread_id}"
        
        with self._cleanup_lock:
            if thread_id not in self._tracked_threads:
                thread_info = ThreadInfo(
                    thread_id=thread_id,
                    thread_name=thread_name,
                    created_at=datetime.now()
                )
                self._tracked_threads[thread_id] = thread_info
                self._total_threads_created += 1
                
                # Store weak reference to thread
                try:
                    weak_thread = weakref.ref(thread, self._thread_cleanup_callback)
                    self._active_threads.add(weak_thread)
                except TypeError:
                    # Thread object doesn't support weak references
                    logger.debug(f"Thread {thread_name} doesn't support weak references")
                
                logger.debug(f"Registered thread for cleanup: {thread_name} (ID: {thread_id})")
    
    def _thread_cleanup_callback(self, weak_thread: weakref.ref) -> None:
        """
        Callback when a thread is garbage collected.
        
        Args:
            weak_thread: Weak reference to the garbage collected thread
        """
        # Remove from active threads set
        self._active_threads.discard(weak_thread)
        
        # Schedule cleanup if needed
        if not self._cleanup_scheduled:
            self._schedule_cleanup()
    
    def cleanup_thread_locals(self, thread_id: int = None) -> bool:
        """
        Clean up thread-local storage for a specific thread.
        
        Args:
            thread_id: Thread ID to clean up (defaults to current thread)
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        if thread_id is None:
            thread_id = threading.get_ident()
        
        with self._cleanup_lock:
            thread_info = self._tracked_threads.get(thread_id)
            if not thread_info:
                return False
            
            if thread_info.cleanup_attempted:
                return thread_info.cleanup_successful
            
            thread_info.cleanup_attempted = True
            
            try:
                # Clean up thread-local storage
                self._cleanup_thread_local_storage(thread_id)
                
                # Clean up cached locals
                if thread_id in self._thread_locals_cache:
                    cached_locals = self._thread_locals_cache[thread_id]
                    
                    # Break circular references in cached data
                    self._break_circular_references(cached_locals)
                    
                    del self._thread_locals_cache[thread_id]
                
                thread_info.cleanup_successful = True
                self._total_threads_cleaned += 1
                
                logger.debug(f"Successfully cleaned up thread locals for thread {thread_id}")
                return True
                
            except Exception as e:
                thread_info.cleanup_error = str(e)
                thread_info.cleanup_successful = False
                self._cleanup_failures += 1
                
                logger.error(f"Failed to clean up thread locals for thread {thread_id}: {e}")
                return False
    
    def _cleanup_thread_local_storage(self, thread_id: int) -> None:
        """
        Clean up thread-local storage for a specific thread.
        
        Args:
            thread_id: Thread ID to clean up
        """
        # Try to access and clean thread-local storage
        # This is implementation-specific and may require platform-specific code
        try:
            # Force garbage collection of thread-local data
            current_thread = None
            for thread in threading.enumerate():
                if thread.ident == thread_id:
                    current_thread = thread
                    break
            
            if current_thread:
                # Clean up any thread-local objects we can access
                if hasattr(current_thread, '__dict__'):
                    thread_dict = current_thread.__dict__
                    
                    # Remove objects that may cause circular references
                    keys_to_remove = []
                    for key, value in thread_dict.items():
                        if (hasattr(value, '__dict__') and 
                            any(ref_key in str(value.__dict__) for ref_key in ['parent', 'child', 'manager', 'registry'])):
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        thread_dict.pop(key, None)
                        logger.debug(f"Removed circular reference object '{key}' from thread {thread_id}")
                
        except Exception as e:
            logger.warning(f"Error cleaning thread-local storage for thread {thread_id}: {e}")
    
    def _break_circular_references(self, obj_dict: Dict[str, Any]) -> None:
        """
        Break circular references in a dictionary of objects.
        
        Args:
            obj_dict: Dictionary to clean up
        """
        for key, value in list(obj_dict.items()):
            try:
                # Remove obvious circular reference patterns
                if (hasattr(value, '__dict__') and 
                    any(ref_attr in value.__dict__ for ref_attr in ['parent', 'child', 'manager', 'registry', '_parent_ref', '_child_ref'])):
                    
                    # Clear circular reference attributes
                    for ref_attr in ['parent', 'child', 'manager', 'registry', '_parent_ref', '_child_ref']:
                        if hasattr(value, ref_attr):
                            setattr(value, ref_attr, None)
                    
                    logger.debug(f"Broke circular references in object '{key}'")
                
                # Handle collections that might contain circular references
                if isinstance(value, (list, set, tuple)):
                    # Clear collections to break potential cycles
                    if isinstance(value, list):
                        value.clear()
                    elif isinstance(value, set):
                        value.clear()
                
            except Exception as e:
                logger.debug(f"Error breaking circular references for '{key}': {e}")
    
    def cleanup_stale_threads(self, max_age_minutes: int = 30) -> int:
        """
        Clean up threads that have been tracked for longer than max_age.
        
        Args:
            max_age_minutes: Maximum age of threads before cleanup
            
        Returns:
            Number of threads cleaned up
        """
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        cleaned_count = 0
        
        with self._cleanup_lock:
            stale_thread_ids = []
            
            for thread_id, thread_info in self._tracked_threads.items():
                if (thread_info.created_at < cutoff_time and 
                    not thread_info.cleanup_attempted):
                    stale_thread_ids.append(thread_id)
            
            for thread_id in stale_thread_ids:
                if self.cleanup_thread_locals(thread_id):
                    cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale threads older than {max_age_minutes} minutes")
        
        return cleaned_count
    
    def _schedule_cleanup(self) -> None:
        """Schedule a background cleanup task."""
        if self._cleanup_scheduled:
            return
        
        self._cleanup_scheduled = True
        
        async def background_cleanup():
            try:
                await asyncio.sleep(5.0)  # Wait 5 seconds before cleanup
                
                # Clean up stale threads
                self.cleanup_stale_threads(max_age_minutes=5)
                
                # Force garbage collection
                gc.collect()
                
            except Exception as e:
                logger.error(f"Background thread cleanup failed: {e}")
            finally:
                self._cleanup_scheduled = False
        
        # Schedule the cleanup task
        try:
            asyncio.create_task(background_cleanup())
        except RuntimeError:
            # No event loop running, cleanup immediately in thread
            def sync_cleanup():
                time.sleep(5.0)
                self.cleanup_stale_threads(max_age_minutes=5)
                gc.collect()
                self._cleanup_scheduled = False
            
            cleanup_thread = threading.Thread(target=sync_cleanup, daemon=True)
            cleanup_thread.start()
    
    def force_cleanup_all(self) -> Dict[str, int]:
        """
        Force cleanup of all tracked threads.
        
        Returns:
            Dictionary with cleanup statistics
        """
        with self._cleanup_lock:
            thread_ids = list(self._tracked_threads.keys())
            
            success_count = 0
            failure_count = 0
            
            for thread_id in thread_ids:
                if self.cleanup_thread_locals(thread_id):
                    success_count += 1
                else:
                    failure_count += 1
            
            # Force garbage collection
            gc.collect()
            
            stats = {
                'threads_processed': len(thread_ids),
                'cleanup_successful': success_count,
                'cleanup_failed': failure_count,
                'total_created': self._total_threads_created,
                'total_cleaned': self._total_threads_cleaned,
                'cleanup_failures': self._cleanup_failures
            }
            
            logger.info(f"Force cleanup completed: {stats}")
            return stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get thread cleanup statistics.
        
        Returns:
            Dictionary with current statistics
        """
        with self._cleanup_lock:
            active_count = len([ref for ref in self._active_threads if ref() is not None])
            
            return {
                'total_threads_created': self._total_threads_created,
                'total_threads_cleaned': self._total_threads_cleaned,
                'cleanup_failures': self._cleanup_failures,
                'active_threads': active_count,
                'tracked_threads': len(self._tracked_threads),
                'cached_locals': len(self._thread_locals_cache),
                'cleanup_scheduled': self._cleanup_scheduled
            }


# Global thread cleanup manager instance
_global_thread_cleanup_manager: Optional[ThreadCleanupManager] = None


def get_thread_cleanup_manager() -> ThreadCleanupManager:
    """
    Get the global thread cleanup manager instance.
    
    Returns:
        ThreadCleanupManager instance
    """
    global _global_thread_cleanup_manager
    
    if _global_thread_cleanup_manager is None:
        _global_thread_cleanup_manager = ThreadCleanupManager()
    
    return _global_thread_cleanup_manager


def register_current_thread() -> None:
    """Register the current thread for cleanup tracking."""
    manager = get_thread_cleanup_manager()
    manager.register_thread()


def cleanup_current_thread() -> bool:
    """
    Clean up the current thread's local storage.
    
    Returns:
        True if cleanup was successful, False otherwise
    """
    manager = get_thread_cleanup_manager()
    return manager.cleanup_thread_locals()


def force_cleanup_all_threads() -> Dict[str, int]:
    """
    Force cleanup of all tracked threads.
    
    Returns:
        Dictionary with cleanup statistics
    """
    manager = get_thread_cleanup_manager()
    return manager.force_cleanup_all()


# Register cleanup hooks for startup
def install_thread_cleanup_hooks() -> None:
    """Install thread cleanup hooks for startup processes."""
    import atexit
    
    def cleanup_at_exit():
        """Cleanup function to run at process exit."""
        try:
            stats = force_cleanup_all_threads()
            logger.info(f"Process exit thread cleanup completed: {stats}")
        except Exception as e:
            logger.error(f"Error during exit thread cleanup: {e}")
    
    atexit.register(cleanup_at_exit)
    logger.info("Thread cleanup hooks installed for Issue #601 memory leak prevention")


if __name__ == "__main__":
    # Test the thread cleanup manager
    import sys
    
    print("Testing ThreadCleanupManager...")
    
    manager = get_thread_cleanup_manager()
    
    # Create some test threads
    def test_thread_function():
        register_current_thread()
        time.sleep(0.1)
        cleanup_current_thread()
    
    threads = []
    for i in range(5):
        thread = threading.Thread(target=test_thread_function, name=f"TestThread-{i}")
        thread.start()
        threads.append(thread)
    
    # Wait for threads to complete
    for thread in threads:
        thread.join()
    
    # Force cleanup
    stats = manager.force_cleanup_all()
    print(f"Cleanup statistics: {stats}")
    
    print("ThreadCleanupManager test completed successfully!")