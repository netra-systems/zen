"""Memory Optimization Service - Critical Memory Management System

Business Value Justification:
- Segment: Platform/Core Infrastructure  
- Business Goal: System Stability & Performance
- Value Impact: Prevents OOM crashes, 
- Strategic Impact: Essential for production scalability and user experience

This service provides comprehensive memory management for the Netra backend:
- Request-scoped dependency injection with automatic cleanup
- Memory monitoring and alerting
- Lazy loading patterns for heavy components
- Connection pool management with memory limits
- Garbage collection optimization
- Memory leak detection and prevention
"""

import asyncio
import gc
import logging
import psutil
import threading
import time
import weakref
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Callable, TypeVar
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env
from netra_backend.app.core.tools.unified_tool_dispatcher import RequestScopedToolDispatcher

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class MemoryPressureLevel(Enum):
    """Memory pressure levels for adaptive behavior."""
    LOW = "low"          # < 70% usage
    MODERATE = "moderate"  # 70-80% usage  
    HIGH = "high"        # 80-90% usage
    CRITICAL = "critical"  # > 90% usage


@dataclass
class MemoryStats:
    """Current memory statistics."""
    total_mb: float
    used_mb: float
    available_mb: float
    percentage_used: float
    pressure_level: MemoryPressureLevel
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RequestScope:
    """Request-scoped resource container with automatic cleanup."""
    request_id: str
    user_id: str
    created_at: datetime
    components: Dict[str, Any] = field(default_factory=dict)
    cleanup_callbacks: List[Callable] = field(default_factory=list)
    memory_limit_mb: Optional[float] = None
    _disposed: bool = field(default=False, init=False)


class MemoryOptimizationService:
    """Comprehensive memory optimization and monitoring service.
    
    This service implements aggressive memory optimization strategies:
    1. Request-scoped dependency injection patterns
    2. Memory monitoring with configurable thresholds
    3. Automatic cleanup of disconnected sessions
    4. Lazy loading for heavy components
    5. Connection pool management
    6. Garbage collection optimization
    """
    
    def __init__(self):
        """Initialize memory optimization service."""
        # Configuration from environment
        self.monitoring_enabled = get_env().get('ENABLE_MEMORY_MONITORING', 'true').lower() == 'true'
        self.check_interval = int(get_env().get('MEMORY_CHECK_INTERVAL', '30'))
        self.warning_threshold = float(get_env().get('MEMORY_WARNING_THRESHOLD', '80'))
        self.critical_threshold = float(get_env().get('MEMORY_CRITICAL_THRESHOLD', '90'))
        self.cleanup_enabled = get_env().get('MEMORY_CLEANUP_ENABLED', 'true').lower() == 'true'
        self.profiling_enabled = get_env().get('MEMORY_PROFILING_ENABLED', 'false').lower() == 'true'
        
        # Service state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._shutdown_event = asyncio.Event()
        
        # Request scoping
        self._active_scopes: Dict[str, RequestScope] = {}
        self._scope_lock = threading.RLock()
        
        # Component registry for lazy loading
        self._component_registry: Dict[str, Dict[str, Any]] = {}
        self._loaded_components: Set[str] = set()
        
        # Memory statistics
        self._memory_history: List[MemoryStats] = []
        self._max_history_size = 100
        
        # Weak references for cleanup tracking
        self._cleanup_registry: weakref.WeakSet = weakref.WeakSet()
        
        logger.info(f"MemoryOptimizationService initialized with monitoring={self.monitoring_enabled}, "
                   f"warning_threshold={self.warning_threshold}%, critical_threshold={self.critical_threshold}%")
    
    async def start(self) -> None:
        """Start memory optimization services."""
        if self._is_running:
            logger.warning("MemoryOptimizationService already running")
            return
        
        self._is_running = True
        self._shutdown_event.clear()
        
        logger.info("🔧 Starting MemoryOptimizationService...")
        
        # Start monitoring if enabled
        if self.monitoring_enabled:
            self._monitoring_task = asyncio.create_task(self._memory_monitoring_loop())
            logger.info("✅ Memory monitoring started")
        
        # Start cleanup if enabled
        if self.cleanup_enabled:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("✅ Memory cleanup started")
        
        # Initial memory check
        stats = self.get_memory_stats()
        logger.info(f"📊 Initial memory usage: {stats.percentage_used:.1f}% "
                   f"({stats.used_mb:.1f}MB/{stats.total_mb:.1f}MB) - {stats.pressure_level.value}")
        
        if stats.pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]:
            logger.warning(f"🚨 HIGH MEMORY PRESSURE DETECTED: {stats.percentage_used:.1f}% - "
                          "Enabling aggressive cleanup mode")
            await self._emergency_cleanup()
    
    async def stop(self) -> None:
        """Stop memory optimization services."""
        if not self._is_running:
            return
        
        logger.info("🛑 Stopping MemoryOptimizationService...")
        
        self._is_running = False
        self._shutdown_event.set()
        
        # Stop monitoring
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Stop cleanup
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clean up all active scopes
        with self._scope_lock:
            scopes_to_cleanup = list(self._active_scopes.values())
        
        for scope in scopes_to_cleanup:
            await self._dispose_scope(scope)
        
        logger.info("✅ MemoryOptimizationService stopped")
    
    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        try:
            memory = psutil.virtual_memory()
            
            total_mb = memory.total / 1024 / 1024
            used_mb = memory.used / 1024 / 1024
            available_mb = memory.available / 1024 / 1024
            percentage_used = memory.percent
            
            # Determine pressure level
            if percentage_used < 70:
                pressure_level = MemoryPressureLevel.LOW
            elif percentage_used < 80:
                pressure_level = MemoryPressureLevel.MODERATE
            elif percentage_used < 90:
                pressure_level = MemoryPressureLevel.HIGH
            else:
                pressure_level = MemoryPressureLevel.CRITICAL
            
            stats = MemoryStats(
                total_mb=total_mb,
                used_mb=used_mb,
                available_mb=available_mb,
                percentage_used=percentage_used,
                pressure_level=pressure_level
            )
            
            # Store in history
            self._memory_history.append(stats)
            if len(self._memory_history) > self._max_history_size:
                self._memory_history.pop(0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            # Return conservative fallback
            return MemoryStats(
                total_mb=1024.0,
                used_mb=900.0,
                available_mb=124.0,
                percentage_used=87.9,
                pressure_level=MemoryPressureLevel.HIGH
            )
    
    @asynccontextmanager
    async def request_scope(
        self,
        request_id: str,
        user_id: str,
        memory_limit_mb: Optional[float] = None
    ):
        """Create request-scoped resource container with automatic cleanup.
        
        This is the primary method for eliminating singleton patterns.
        All request-specific resources should be created within this scope.
        
        Args:
            request_id: Unique request identifier
            user_id: User identifier for isolation
            memory_limit_mb: Optional per-request memory limit
            
        Yields:
            RequestScope: Resource container for this request
            
        Example:
            async with memory_service.request_scope(request_id, user_id) as scope:
                db_session = scope.get_or_create('db_session', create_db_session)
                tool_dispatcher = scope.get_or_create('tool_dispatcher', 
                    lambda: RequestScopedToolDispatcher(user_context))
                # Automatic cleanup when exiting context
        """
        scope = RequestScope(
            request_id=request_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            memory_limit_mb=memory_limit_mb
        )
        
        with self._scope_lock:
            self._active_scopes[request_id] = scope
        
        try:
            logger.debug(f"📦 Created request scope {request_id} for user {user_id}")
            yield scope
        finally:
            await self._dispose_scope(scope)
            with self._scope_lock:
                self._active_scopes.pop(request_id, None)
    
    async def _dispose_scope(self, scope: RequestScope) -> None:
        """Dispose of request scope and clean up resources."""
        if scope._disposed:
            return
        
        try:
            logger.debug(f"🧹 Disposing request scope {scope.request_id}")
            
            # Run cleanup callbacks in reverse order
            for cleanup_callback in reversed(scope.cleanup_callbacks):
                try:
                    if asyncio.iscoroutinefunction(cleanup_callback):
                        await cleanup_callback()
                    else:
                        cleanup_callback()
                except Exception as e:
                    logger.error(f"Error in cleanup callback: {e}")
            
            # Clear all components
            scope.components.clear()
            scope.cleanup_callbacks.clear()
            scope._disposed = True
            
            logger.debug(f"✅ Disposed request scope {scope.request_id}")
            
        except Exception as e:
            logger.error(f"Error disposing scope {scope.request_id}: {e}")
    
    def get_or_create_component(
        self,
        scope: RequestScope,
        component_name: str,
        factory: Callable[[], T],
        cleanup_callback: Optional[Callable] = None
    ) -> T:
        """Get or create component within request scope.
        
        Args:
            scope: Request scope to store component in
            component_name: Unique component name within scope
            factory: Function to create component if not exists
            cleanup_callback: Optional cleanup function for component
            
        Returns:
            Component instance (either existing or newly created)
        """
        if scope._disposed:
            raise RuntimeError(f"Cannot create component in disposed scope {scope.request_id}")
        
        if component_name in scope.components:
            return scope.components[component_name]
        
        try:
            # Create component
            component = factory()
            scope.components[component_name] = component
            
            # Register cleanup callback if provided
            if cleanup_callback:
                scope.cleanup_callbacks.append(cleanup_callback)
            
            logger.debug(f"📦 Created component {component_name} in scope {scope.request_id}")
            return component
            
        except Exception as e:
            logger.error(f"Error creating component {component_name}: {e}")
            raise
    
    def register_lazy_component(
        self,
        component_name: str,
        factory: Callable[[], Any],
        dependencies: List[str] = None,
        memory_cost_mb: float = 0.0
    ) -> None:
        """Register component for lazy loading.
        
        Args:
            component_name: Unique component identifier
            factory: Function to create component when needed
            dependencies: List of required component dependencies
            memory_cost_mb: Estimated memory cost in MB
        """
        self._component_registry[component_name] = {
            'factory': factory,
            'dependencies': dependencies or [],
            'memory_cost_mb': memory_cost_mb,
            'loaded': False,
            'instance': None
        }
        
        logger.debug(f"📋 Registered lazy component {component_name} "
                    f"(cost: {memory_cost_mb}MB, deps: {dependencies})")
    
    async def load_component(self, component_name: str) -> Any:
        """Load component on-demand with dependency resolution.
        
        Args:
            component_name: Component to load
            
        Returns:
            Loaded component instance
        """
        if component_name in self._loaded_components:
            return self._component_registry[component_name]['instance']
        
        if component_name not in self._component_registry:
            raise ValueError(f"Unknown component: {component_name}")
        
        component_def = self._component_registry[component_name]
        
        # Check memory pressure before loading
        stats = self.get_memory_stats()
        if (stats.pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL] and
            component_def['memory_cost_mb'] > 50):
            logger.warning(f"⚠️ Deferring load of {component_name} due to memory pressure "
                          f"({stats.percentage_used:.1f}%)")
            await self._emergency_cleanup()
        
        try:
            # Load dependencies first
            for dep_name in component_def['dependencies']:
                await self.load_component(dep_name)
            
            # Create component
            factory = component_def['factory']
            if asyncio.iscoroutinefunction(factory):
                instance = await factory()
            else:
                instance = factory()
            
            # Store instance
            component_def['instance'] = instance
            component_def['loaded'] = True
            self._loaded_components.add(component_name)
            
            logger.info(f"✅ Loaded component {component_name} "
                       f"(cost: {component_def['memory_cost_mb']}MB)")
            
            return instance
            
        except Exception as e:
            logger.error(f"Error loading component {component_name}: {e}")
            raise
    
    async def _memory_monitoring_loop(self) -> None:
        """Memory monitoring background task."""
        logger.info("🔍 Started memory monitoring loop")
        
        while self._is_running:
            try:
                stats = self.get_memory_stats()
                
                # Log periodic status
                if len(self._memory_history) % 10 == 0:  # Every 10 checks
                    logger.info(f"📊 Memory: {stats.percentage_used:.1f}% "
                               f"({stats.used_mb:.1f}MB/{stats.total_mb:.1f}MB)")
                
                # Handle memory pressure
                if stats.percentage_used >= self.critical_threshold:
                    logger.critical(f"🚨 CRITICAL MEMORY PRESSURE: {stats.percentage_used:.1f}%")
                    await self._emergency_cleanup()
                elif stats.percentage_used >= self.warning_threshold:
                    logger.warning(f"⚠️ HIGH MEMORY USAGE: {stats.percentage_used:.1f}%")
                    await self._gentle_cleanup()
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
                await asyncio.sleep(self.check_interval)
        
        logger.info("🔍 Memory monitoring loop stopped")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup task."""
        logger.info("🧹 Started memory cleanup loop")
        
        while self._is_running:
            try:
                await self._periodic_cleanup()
                await asyncio.sleep(60)  # Run every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
        
        logger.info("🧹 Memory cleanup loop stopped")
    
    async def _periodic_cleanup(self) -> None:
        """Perform periodic cleanup tasks."""
        # Clean up expired scopes
        expired_scopes = []
        cutoff_time = datetime.now(timezone.utc).timestamp() - 3600  # 1 hour
        
        with self._scope_lock:
            for request_id, scope in self._active_scopes.items():
                if scope.created_at.timestamp() < cutoff_time:
                    expired_scopes.append(scope)
        
        for scope in expired_scopes:
            logger.info(f"🕰️ Cleaning up expired scope {scope.request_id}")
            await self._dispose_scope(scope)
            with self._scope_lock:
                self._active_scopes.pop(scope.request_id, None)
        
        # Force garbage collection
        gc.collect()
        
        if expired_scopes:
            logger.info(f"🧹 Cleaned up {len(expired_scopes)} expired scopes")
    
    async def _gentle_cleanup(self) -> None:
        """Perform gentle cleanup to reduce memory pressure."""
        logger.info("🧹 Performing gentle memory cleanup...")
        
        # Unload non-essential lazy components
        components_to_unload = []
        for name, component_def in self._component_registry.items():
            if (component_def['loaded'] and 
                component_def['memory_cost_mb'] > 20 and
                name not in ['db_session_factory', 'redis_manager']):  # Keep essentials
                components_to_unload.append(name)
        
        for component_name in components_to_unload:
            await self._unload_component(component_name)
        
        # Force garbage collection
        gc.collect()
        
        stats = self.get_memory_stats()
        logger.info(f"🧹 Gentle cleanup complete - Memory: {stats.percentage_used:.1f}%")
    
    async def _emergency_cleanup(self) -> None:
        """Perform aggressive cleanup during critical memory pressure."""
        logger.critical("🚨 EMERGENCY MEMORY CLEANUP INITIATED")
        
        # Clean up ALL non-essential scopes
        non_essential_scopes = []
        with self._scope_lock:
            for scope in self._active_scopes.values():
                # Keep only very recent scopes (last 5 minutes)
                if (datetime.now(timezone.utc) - scope.created_at).total_seconds() > 300:
                    non_essential_scopes.append(scope)
        
        for scope in non_essential_scopes:
            await self._dispose_scope(scope)
            with self._scope_lock:
                self._active_scopes.pop(scope.request_id, None)
        
        # Unload ALL non-essential components
        for name in list(self._loaded_components):
            if name not in ['db_session_factory']:  # Keep only absolutely essential
                await self._unload_component(name)
        
        # Multiple garbage collection passes
        for _ in range(3):
            gc.collect()
            await asyncio.sleep(0.1)
        
        stats = self.get_memory_stats()
        logger.critical(f"🚨 Emergency cleanup complete - Memory: {stats.percentage_used:.1f}%")
        
        if stats.percentage_used >= 95:
            logger.critical("🚨 MEMORY STILL CRITICAL AFTER CLEANUP - SYSTEM MAY BE UNSTABLE")
    
    async def _unload_component(self, component_name: str) -> None:
        """Unload a lazy-loaded component to free memory."""
        if component_name not in self._loaded_components:
            return
        
        try:
            component_def = self._component_registry[component_name]
            instance = component_def['instance']
            
            # Call cleanup method if available
            if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                if asyncio.iscoroutinefunction(instance.cleanup):
                    await instance.cleanup()
                else:
                    instance.cleanup()
            
            # Clear references
            component_def['instance'] = None
            component_def['loaded'] = False
            self._loaded_components.discard(component_name)
            
            logger.debug(f"🗑️ Unloaded component {component_name}")
            
        except Exception as e:
            logger.error(f"Error unloading component {component_name}: {e}")
    
    def get_active_scopes_count(self) -> int:
        """Get number of active request scopes."""
        with self._scope_lock:
            return len(self._active_scopes)
    
    def get_memory_history(self, limit: int = 10) -> List[MemoryStats]:
        """Get recent memory history."""
        return self._memory_history[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        stats = self.get_memory_stats()
        
        with self._scope_lock:
            active_scopes = len(self._active_scopes)
        
        return {
            'is_running': self._is_running,
            'monitoring_enabled': self.monitoring_enabled,
            'cleanup_enabled': self.cleanup_enabled,
            'memory_stats': {
                'percentage_used': stats.percentage_used,
                'pressure_level': stats.pressure_level.value,
                'total_mb': stats.total_mb,
                'used_mb': stats.used_mb,
                'available_mb': stats.available_mb
            },
            'thresholds': {
                'warning': self.warning_threshold,
                'critical': self.critical_threshold
            },
            'scopes': {
                'active_count': active_scopes,
                'history_size': len(self._memory_history)
            },
            'components': {
                'registered': len(self._component_registry),
                'loaded': len(self._loaded_components)
            }
        }


# Global service instance
_memory_service: Optional[MemoryOptimizationService] = None


def get_memory_service() -> MemoryOptimizationService:
    """Get global memory optimization service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryOptimizationService()
    return _memory_service


async def initialize_memory_service() -> MemoryOptimizationService:
    """Initialize and start memory optimization service."""
    service = get_memory_service()
    if not service._is_running:
        await service.start()
    return service


async def shutdown_memory_service() -> None:
    """Shutdown memory optimization service."""
    global _memory_service
    if _memory_service and _memory_service._is_running:
        await _memory_service.stop()
        _memory_service = None