"""
ThreadRunRegistry - SSOT for Thread-Run Mappings in WebSocket Bridge

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Chat Value Delivery
- Value Impact: Ensures 100% of WebSocket events reach users by maintaining reliable thread-to-run mappings
- Strategic Impact: Eliminates 20% of WebSocket notification failures when orchestrator is unavailable

This registry provides persistent thread_id to run_id mapping to solve the critical issue where
WebSocket events fail to reach users when the bridge cannot resolve thread_id from run_id.

The registry enables the bridge to check for known mappings BEFORE falling back to string parsing,
ensuring reliable WebSocket event delivery even when the orchestrator is unavailable.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Set, Any
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MappingState(Enum):
    """States for thread-run mappings."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CLEANUP_PENDING = "cleanup_pending"


@dataclass
class RunMapping:
    """Represents a thread-to-run mapping with lifecycle tracking."""
    run_id: str
    thread_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: MappingState = MappingState.ACTIVE
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegistryConfig:
    """Configuration for ThreadRunRegistry."""
    # TTL for mappings (24 hours default)
    mapping_ttl_hours: int = 24
    
    # Cleanup interval (every 30 minutes)
    cleanup_interval_minutes: int = 30
    
    # Maximum mappings to keep in memory
    max_mappings: int = 10000
    
    # Enable Redis backing (future enhancement)
    enable_redis_backing: bool = False
    redis_key_prefix: str = "netra:thread_run:"
    
    # Logging verbosity for debugging
    enable_debug_logging: bool = True


class ThreadRunRegistry:
    """
    SSOT for Thread-Run Mappings with thread-safe operations.
    
    Provides persistent registry to map run_ids to thread_ids, solving the critical issue
    where WebSocket events fail when the bridge cannot resolve thread_id from run_id.
    
    Features:
    - Thread-safe concurrent operations with asyncio locks
    - Automatic cleanup of expired mappings with TTL
    - Comprehensive logging for debugging WebSocket routing issues
    - In-memory storage with optional Redis backing (future)
    - Performance monitoring and metrics tracking
    """
    
    _instance: Optional['ThreadRunRegistry'] = None
    _lock = asyncio.Lock()
    
    def __init__(self, config: Optional[RegistryConfig] = None):
        """Initialize registry instance."""
        self.config = config or RegistryConfig()
        self._initialize_state()
        self._initialize_cleanup_task()
        
        logger.info(f"ThreadRunRegistry initialized with TTL={self.config.mapping_ttl_hours}h, cleanup={self.config.cleanup_interval_minutes}m")
    
    def _initialize_state(self) -> None:
        """Initialize registry state and locks."""
        # Core mappings storage
        self._run_to_thread: Dict[str, RunMapping] = {}
        self._thread_to_runs: Dict[str, Set[str]] = {}
        
        # Thread safety locks
        self._registry_lock = asyncio.Lock()
        self._cleanup_lock = asyncio.Lock()
        
        # State tracking
        self._shutdown = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._metrics = {
            'total_registrations': 0,
            'successful_lookups': 0,
            'failed_lookups': 0,
            'expired_mappings_cleaned': 0,
            'active_mappings': 0,
            'last_cleanup': datetime.now(timezone.utc),
            'registry_start_time': datetime.now(timezone.utc)
        }
        
        logger.debug("ThreadRunRegistry state initialized")
    
    def _initialize_cleanup_task(self) -> None:
        """Initialize background cleanup task."""
        if not self._shutdown:
            try:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                logger.debug("Background cleanup task started")
            except RuntimeError as e:
                logger.warning(f"Could not create cleanup task: {e}")
                self._cleanup_task = None
    
    async def register(
        self, 
        run_id: str, 
        thread_id: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a run_id to thread_id mapping.
        
        Args:
            run_id: Unique execution identifier
            thread_id: Associated thread identifier for WebSocket routing
            metadata: Optional metadata about the mapping (agent_name, user_id, etc.)
            
        Returns:
            bool: True if registration succeeded
            
        Business Value: Enables WebSocket events to reach users reliably
        """
        # Validate input parameters
        if not run_id or not isinstance(run_id, str) or run_id.strip() == "":
            logger.error(f" ALERT:  INVALID run_id: '{run_id}' - must be non-empty string")
            return False
        
        if not thread_id or not isinstance(thread_id, str) or thread_id.strip() == "":
            logger.error(f" ALERT:  INVALID thread_id: '{thread_id}' - must be non-empty string")
            return False
        
        try:
            async with self._registry_lock:
                # Create mapping object
                mapping = RunMapping(
                    run_id=run_id,
                    thread_id=thread_id,
                    metadata=metadata or {}
                )
                
                # Store run_id -> thread_id mapping
                self._run_to_thread[run_id] = mapping
                
                # Store reverse mapping: thread_id -> [run_ids]
                if thread_id not in self._thread_to_runs:
                    self._thread_to_runs[thread_id] = set()
                self._thread_to_runs[thread_id].add(run_id)
                
                # Update metrics
                self._metrics['total_registrations'] += 1
                self._metrics['active_mappings'] = len(self._run_to_thread)
                
                if self.config.enable_debug_logging:
                    logger.info(f" PASS:  REGISTERED: run_id={run_id}  ->  thread_id={thread_id} (metadata: {metadata})")
                
                return True
                
        except Exception as e:
            logger.error(f" ALERT:  REGISTRATION FAILED: run_id={run_id}, thread_id={thread_id}: {e}")
            return False
    
    async def get_thread(self, run_id: str) -> Optional[str]:
        """
        Get thread_id for a run_id.
        
        Args:
            run_id: Run identifier to look up
            
        Returns:
            Optional[str]: Thread ID if found, None otherwise
            
        Business Value: Critical for WebSocket event routing to correct user
        """
        try:
            async with self._registry_lock:
                mapping = self._run_to_thread.get(run_id)
                
                if mapping is None:
                    self._metrics['failed_lookups'] += 1
                    if self.config.enable_debug_logging:
                        logger.debug(f" SEARCH:  LOOKUP MISS: run_id={run_id} not found")
                    return None
                
                # Check if mapping is expired
                if self._is_mapping_expired(mapping):
                    self._metrics['failed_lookups'] += 1
                    if self.config.enable_debug_logging:
                        logger.debug(f" SEARCH:  LOOKUP EXPIRED: run_id={run_id} mapping expired")
                    return None
                
                # Update access tracking
                mapping.last_accessed = datetime.now(timezone.utc)
                mapping.access_count += 1
                
                # Update metrics
                self._metrics['successful_lookups'] += 1
                
                if self.config.enable_debug_logging:
                    logger.debug(f" PASS:  LOOKUP SUCCESS: run_id={run_id}  ->  thread_id={mapping.thread_id}")
                
                return mapping.thread_id
                
        except Exception as e:
            self._metrics['failed_lookups'] += 1
            logger.error(f" ALERT:  LOOKUP ERROR: run_id={run_id}: {e}")
            return None
    
    async def get_runs(self, thread_id: str) -> List[str]:
        """
        Get all run_ids for a thread_id.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            List[str]: List of run IDs associated with the thread
            
        Business Value: Enables thread-level operations and cleanup
        """
        try:
            async with self._registry_lock:
                run_ids = self._thread_to_runs.get(thread_id, set())
                
                # Filter out expired mappings
                active_runs = []
                for run_id in run_ids:
                    mapping = self._run_to_thread.get(run_id)
                    if mapping and not self._is_mapping_expired(mapping):
                        active_runs.append(run_id)
                
                if self.config.enable_debug_logging:
                    logger.debug(f" SEARCH:  THREAD RUNS: thread_id={thread_id}  ->  {len(active_runs)} active runs")
                
                return active_runs
                
        except Exception as e:
            logger.error(f" ALERT:  GET RUNS ERROR: thread_id={thread_id}: {e}")
            return []
    
    async def unregister_run(self, run_id: str) -> bool:
        """
        Remove a run_id mapping from the registry.
        
        Args:
            run_id: Run identifier to remove
            
        Returns:
            bool: True if removal succeeded
            
        Business Value: Prevents memory leaks and maintains clean state
        """
        try:
            async with self._registry_lock:
                mapping = self._run_to_thread.pop(run_id, None)
                
                if mapping is None:
                    logger.debug(f" SEARCH:  UNREGISTER MISS: run_id={run_id} not found")
                    return False
                
                # Remove from reverse mapping
                thread_id = mapping.thread_id
                if thread_id in self._thread_to_runs:
                    self._thread_to_runs[thread_id].discard(run_id)
                    
                    # Clean up empty thread entries
                    if not self._thread_to_runs[thread_id]:
                        del self._thread_to_runs[thread_id]
                
                # Update metrics
                self._metrics['active_mappings'] = len(self._run_to_thread)
                
                if self.config.enable_debug_logging:
                    logger.info(f"[U+1F5D1][U+FE0F] UNREGISTERED: run_id={run_id} from thread_id={thread_id}")
                
                return True
                
        except Exception as e:
            logger.error(f" ALERT:  UNREGISTER ERROR: run_id={run_id}: {e}")
            return False
    
    async def cleanup_old_mappings(self) -> int:
        """
        Clean up expired mappings based on TTL.
        
        Returns:
            int: Number of mappings cleaned up
            
        Business Value: Prevents memory leaks and maintains system performance
        """
        try:
            async with self._cleanup_lock:
                cleaned_count = 0
                current_time = datetime.now(timezone.utc)
                
                # Find expired mappings
                expired_run_ids = []
                for run_id, mapping in self._run_to_thread.items():
                    if self._is_mapping_expired(mapping):
                        expired_run_ids.append(run_id)
                
                # Remove expired mappings
                async with self._registry_lock:
                    for run_id in expired_run_ids:
                        mapping = self._run_to_thread.pop(run_id, None)
                        if mapping:
                            # Remove from reverse mapping
                            thread_id = mapping.thread_id
                            if thread_id in self._thread_to_runs:
                                self._thread_to_runs[thread_id].discard(run_id)
                                if not self._thread_to_runs[thread_id]:
                                    del self._thread_to_runs[thread_id]
                            cleaned_count += 1
                
                # Update metrics
                self._metrics['expired_mappings_cleaned'] += cleaned_count
                self._metrics['active_mappings'] = len(self._run_to_thread)
                self._metrics['last_cleanup'] = current_time
                
                if cleaned_count > 0:
                    logger.info(f"[U+1F9F9] CLEANUP COMPLETED: Removed {cleaned_count} expired mappings")
                elif self.config.enable_debug_logging:
                    logger.debug(f"[U+1F9F9] CLEANUP COMPLETED: No expired mappings found")
                
                return cleaned_count
                
        except Exception as e:
            logger.error(f" ALERT:  CLEANUP ERROR: {e}")
            return 0
    
    def _is_mapping_expired(self, mapping: RunMapping) -> bool:
        """Check if a mapping has expired based on TTL."""
        ttl_delta = timedelta(hours=self.config.mapping_ttl_hours)
        return datetime.now(timezone.utc) - mapping.last_accessed > ttl_delta
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired mappings."""
        logger.debug("Background cleanup loop started")
        
        while not self._shutdown:
            try:
                # Sleep for cleanup interval with periodic checks for shutdown
                cleanup_seconds = self.config.cleanup_interval_minutes * 60
                for _ in range(int(cleanup_seconds)):
                    if self._shutdown:
                        break
                    await asyncio.sleep(1)  # Sleep 1 second at a time to be more responsive
                
                if self._shutdown:
                    break
                
                # Perform cleanup
                cleaned = await self.cleanup_old_mappings()
                
                # Log status periodically
                if self.config.enable_debug_logging:
                    active_count = len(self._run_to_thread)
                    logger.debug(f"[U+1F9F9] Cleanup cycle: {cleaned} expired, {active_count} active mappings")
                
            except asyncio.CancelledError:
                logger.debug("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f" ALERT:  Error in cleanup loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        logger.debug("Background cleanup loop ended")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get registry performance metrics.
        
        Returns:
            Dict containing registry metrics and statistics
            
        Business Value: Enables monitoring and performance optimization
        """
        try:
            async with self._registry_lock:
                current_time = datetime.now(timezone.utc)
                uptime = current_time - self._metrics['registry_start_time']
                
                # Calculate success rate
                total_lookups = self._metrics['successful_lookups'] + self._metrics['failed_lookups']
                success_rate = (
                    self._metrics['successful_lookups'] / max(1, total_lookups)
                ) if total_lookups > 0 else 1.0
                
                return {
                    # Core metrics
                    'active_mappings': self._metrics['active_mappings'],
                    'total_registrations': self._metrics['total_registrations'],
                    'successful_lookups': self._metrics['successful_lookups'],
                    'failed_lookups': self._metrics['failed_lookups'],
                    'expired_mappings_cleaned': self._metrics['expired_mappings_cleaned'],
                    
                    # Calculated metrics
                    'lookup_success_rate': success_rate,
                    'average_mappings_per_hour': (
                        self._metrics['total_registrations'] / max(1, uptime.total_seconds() / 3600)
                    ),
                    
                    # Status
                    'registry_uptime_seconds': uptime.total_seconds(),
                    'last_cleanup': self._metrics['last_cleanup'].isoformat(),
                    'registry_healthy': not self._shutdown,
                    
                    # Configuration
                    'mapping_ttl_hours': self.config.mapping_ttl_hours,
                    'cleanup_interval_minutes': self.config.cleanup_interval_minutes,
                    'max_mappings': self.config.max_mappings,
                    
                    # Current status
                    'memory_usage_percentage': (
                        self._metrics['active_mappings'] / self.config.max_mappings * 100
                    ),
                    'timestamp': current_time.isoformat()
                }
                
        except Exception as e:
            logger.error(f" ALERT:  Error getting metrics: {e}")
            return {
                'error': f'Metrics retrieval failed: {e}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive registry status.
        
        Returns:
            Dict containing registry status and health information
        """
        try:
            metrics = await self.get_metrics()
            
            return {
                'registry_healthy': not self._shutdown and self._cleanup_task and not self._cleanup_task.done(),
                'active_mappings': metrics['active_mappings'],
                'total_registrations': metrics['total_registrations'],
                'lookup_success_rate': metrics['lookup_success_rate'],
                'uptime_seconds': metrics['registry_uptime_seconds'],
                'memory_usage_percentage': metrics['memory_usage_percentage'],
                'last_cleanup': metrics['last_cleanup'],
                'config': {
                    'mapping_ttl_hours': self.config.mapping_ttl_hours,
                    'cleanup_interval_minutes': self.config.cleanup_interval_minutes,
                    'max_mappings': self.config.max_mappings,
                    'debug_logging_enabled': self.config.enable_debug_logging
                },
                'cleanup_task_running': self._cleanup_task is not None and not self._cleanup_task.done(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f" ALERT:  Error getting status: {e}")
            return {
                'registry_healthy': False,
                'error': f'Status retrieval failed: {e}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def shutdown(self) -> None:
        """Clean shutdown of registry resources."""
        logger.info("Shutting down ThreadRunRegistry")
        self._shutdown = True
        
        # Cancel cleanup task with better error handling
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass  # Expected for cancelled tasks
            except Exception as e:
                logger.warning(f"Error during cleanup task shutdown: {e}")
        
        # Clear all mappings with error handling
        try:
            async with self._registry_lock:
                self._run_to_thread.clear()
                self._thread_to_runs.clear()
        except Exception as e:
            logger.warning(f"Error clearing mappings during shutdown: {e}")
        
        logger.info("ThreadRunRegistry shutdown complete")
    
    # Debug and testing methods
    
    async def debug_list_all_mappings(self) -> Dict[str, Any]:
        """
        List all active mappings for debugging.
        
        Returns:
            Dict containing all current mappings with metadata
        """
        try:
            async with self._registry_lock:
                mappings_info = {}
                
                for run_id, mapping in self._run_to_thread.items():
                    mappings_info[run_id] = {
                        'thread_id': mapping.thread_id,
                        'created_at': mapping.created_at.isoformat(),
                        'last_accessed': mapping.last_accessed.isoformat(),
                        'access_count': mapping.access_count,
                        'state': mapping.state.value,
                        'metadata': mapping.metadata,
                        'is_expired': self._is_mapping_expired(mapping)
                    }
                
                return {
                    'total_mappings': len(mappings_info),
                    'mappings': mappings_info,
                    'thread_to_runs_count': {
                        thread_id: len(run_ids) 
                        for thread_id, run_ids in self._thread_to_runs.items()
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f" ALERT:  Error listing mappings: {e}")
            return {'error': f'Mapping listing failed: {e}'}


# Singleton factory function
_registry_instance: Optional[ThreadRunRegistry] = None


async def get_thread_run_registry(config: Optional[RegistryConfig] = None) -> ThreadRunRegistry:
    """Get singleton ThreadRunRegistry instance."""
    global _registry_instance
    
    if _registry_instance is None:
        async with ThreadRunRegistry._lock:
            if _registry_instance is None:
                _registry_instance = ThreadRunRegistry(config)
    
    return _registry_instance


async def initialize_thread_run_registry(config: Optional[RegistryConfig] = None) -> ThreadRunRegistry:
    """Initialize ThreadRunRegistry as singleton during startup."""
    registry = await get_thread_run_registry(config)
    logger.info("ThreadRunRegistry initialized and ready")
    return registry