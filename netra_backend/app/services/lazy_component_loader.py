"""Lazy Component Loader - On-Demand Heavy Component Initialization

Business Value Justification:
- Segment: Platform/Core Infrastructure  
- Business Goal: Memory Optimization & Startup Performance
- Value Impact: Reduces startup memory usage by 60-80%, faster boot times
- Strategic Impact: Essential for Docker memory limits and horizontal scaling

This service provides lazy loading for heavy components to reduce memory usage:
- Defers initialization of expensive components until first use
- Implements smart preloading based on usage patterns
- Provides dependency resolution for lazy components
- Tracks memory usage and loading metrics
- Integrates with startup sequence to minimize memory footprint
"""

import asyncio
import logging
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Callable, TypeVar, Union
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.memory_optimization_service import get_memory_service, MemoryPressureLevel

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class ComponentPriority(Enum):
    """Component loading priority levels."""
    CRITICAL = "critical"      # Must load immediately (db, redis)
    HIGH = "high"             # Load on first request (llm_manager) 
    MEDIUM = "medium"         # Load on demand (tool_dispatcher)
    LOW = "low"               # Load only when needed (monitoring, analytics)
    OPTIONAL = "optional"     # Load only if memory allows (profiling, debug)


class LoadingStrategy(Enum):
    """Component loading strategies."""
    IMMEDIATE = "immediate"    # Load during startup
    ON_DEMAND = "on_demand"   # Load when first accessed
    PRELOAD = "preload"       # Load after startup completes
    SMART = "smart"           # Load based on usage patterns


@dataclass
class ComponentDefinition:
    """Definition of a lazy-loadable component."""
    name: str
    factory: Callable[[], Any]
    priority: ComponentPriority
    strategy: LoadingStrategy
    dependencies: List[str] = field(default_factory=list)
    memory_cost_mb: float = 0.0
    description: str = ""
    cleanup_callback: Optional[Callable] = None
    
    # Runtime state
    loaded: bool = field(default=False, init=False)
    instance: Optional[Any] = field(default=None, init=False)
    load_time: Optional[datetime] = field(default=None, init=False)
    access_count: int = field(default=0, init=False)
    last_accessed: Optional[datetime] = field(default=None, init=False)
    loading: bool = field(default=False, init=False)


@dataclass
class LoadingMetrics:
    """Metrics for component loading performance."""
    total_components: int = 0
    loaded_components: int = 0
    failed_components: int = 0
    total_memory_mb: float = 0.0
    total_load_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


class LazyComponentLoader:
    """Lazy loading service for heavy components.
    
    This service manages the lazy initialization of expensive components to:
    - Reduce startup memory usage significantly
    - Improve startup performance by deferring expensive operations
    - Load components on-demand based on actual usage
    - Implement smart preloading strategies
    - Provide dependency resolution
    - Track loading metrics and memory usage
    """
    
    def __init__(self):
        """Initialize lazy component loader."""
        self.memory_service = get_memory_service()
        
        # Component registry
        self._components: Dict[str, ComponentDefinition] = {}
        self._loading_lock = asyncio.Lock()
        
        # Runtime state
        self._is_initialized = False
        self._preload_task: Optional[asyncio.Task] = None
        self._metrics = LoadingMetrics()
        
        # Weak references for cleanup
        self._loaded_instances: weakref.WeakSet = weakref.WeakSet()
        
        logger.info("LazyComponentLoader initialized")
    
    def register_component(
        self,
        name: str,
        factory: Callable[[], Any],
        priority: ComponentPriority = ComponentPriority.MEDIUM,
        strategy: LoadingStrategy = LoadingStrategy.ON_DEMAND,
        dependencies: List[str] = None,
        memory_cost_mb: float = 0.0,
        description: str = "",
        cleanup_callback: Optional[Callable] = None
    ) -> None:
        """Register component for lazy loading.
        
        Args:
            name: Unique component name
            factory: Function to create component instance
            priority: Loading priority level
            strategy: Loading strategy
            dependencies: List of component dependencies
            memory_cost_mb: Estimated memory cost in MB
            description: Component description
            cleanup_callback: Optional cleanup function
        """
        if name in self._components:
            logger.warning(f"Overriding existing component registration: {name}")
        
        component = ComponentDefinition(
            name=name,
            factory=factory,
            priority=priority,
            strategy=strategy,
            dependencies=dependencies or [],
            memory_cost_mb=memory_cost_mb,
            description=description,
            cleanup_callback=cleanup_callback
        )
        
        self._components[name] = component
        self._metrics.total_components += 1
        
        logger.debug(f"[U+1F4CB] Registered lazy component {name} "
                    f"(priority: {priority.value}, strategy: {strategy.value}, "
                    f"cost: {memory_cost_mb}MB)")
    
    async def initialize(self) -> None:
        """Initialize loader and load critical components."""
        if self._is_initialized:
            return
        
        logger.info("[U+1F680] Initializing LazyComponentLoader...")
        
        # Load critical components immediately
        critical_components = [
            name for name, comp in self._components.items()
            if comp.priority == ComponentPriority.CRITICAL
        ]
        
        if critical_components:
            logger.info(f" LIGHTNING:  Loading {len(critical_components)} critical components...")
            for component_name in critical_components:
                await self.load_component(component_name)
        
        # Schedule preloading of other components
        self._preload_task = asyncio.create_task(self._preload_components())
        
        self._is_initialized = True
        logger.info(" PASS:  LazyComponentLoader initialized")
    
    async def load_component(self, name: str) -> Any:
        """Load component on-demand with dependency resolution.
        
        Args:
            name: Component name to load
            
        Returns:
            Loaded component instance
            
        Raises:
            ValueError: If component is not registered
            RuntimeError: If component loading fails
        """
        if name not in self._components:
            raise ValueError(f"Unknown component: {name}")
        
        component = self._components[name]
        
        # Return cached instance if already loaded
        if component.loaded and component.instance is not None:
            component.access_count += 1
            component.last_accessed = datetime.now(timezone.utc)
            self._metrics.cache_hits += 1
            return component.instance
        
        # Prevent concurrent loading of same component
        async with self._loading_lock:
            # Double-check after acquiring lock
            if component.loaded and component.instance is not None:
                component.access_count += 1
                component.last_accessed = datetime.now(timezone.utc)
                self._metrics.cache_hits += 1
                return component.instance
            
            if component.loading:
                # Wait for other loading operation to complete
                while component.loading:
                    await asyncio.sleep(0.01)
                
                if component.loaded and component.instance is not None:
                    component.access_count += 1
                    component.last_accessed = datetime.now(timezone.utc)
                    return component.instance
        
        self._metrics.cache_misses += 1
        
        # Check memory pressure before loading expensive components
        memory_stats = self.memory_service.get_memory_stats()
        if (component.memory_cost_mb > 50 and 
            memory_stats.pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]):
            
            logger.warning(f" WARNING: [U+FE0F] Deferring load of {name} due to memory pressure "
                          f"({memory_stats.percentage_used:.1f}%)")
            
            # For critical components, load anyway but warn
            if component.priority != ComponentPriority.CRITICAL:
                raise RuntimeError(f"Cannot load {name} - memory pressure too high")
        
        # Load dependencies first
        for dep_name in component.dependencies:
            if dep_name not in self._components:
                logger.warning(f"Dependency {dep_name} not registered for {name}")
                continue
            
            try:
                await self.load_component(dep_name)
            except Exception as e:
                logger.error(f"Failed to load dependency {dep_name} for {name}: {e}")
                # Continue loading - some dependencies may be optional
        
        # Load the component
        return await self._load_component_impl(component)
    
    async def _load_component_impl(self, component: ComponentDefinition) -> Any:
        """Internal implementation of component loading."""
        component.loading = True
        start_time = time.time()
        
        try:
            logger.info(f"[U+1F527] Loading component {component.name} "
                       f"(priority: {component.priority.value}, cost: {component.memory_cost_mb}MB)")
            
            # Create instance
            if asyncio.iscoroutinefunction(component.factory):
                instance = await component.factory()
            else:
                instance = component.factory()
            
            if instance is None:
                raise RuntimeError(f"Component factory for {component.name} returned None")
            
            # Update component state
            component.instance = instance
            component.loaded = True
            component.load_time = datetime.now(timezone.utc)
            component.access_count = 1
            component.last_accessed = datetime.now(timezone.utc)
            
            # Update metrics
            load_time_ms = (time.time() - start_time) * 1000
            self._metrics.loaded_components += 1
            self._metrics.total_memory_mb += component.memory_cost_mb
            self._metrics.total_load_time_ms += load_time_ms
            
            # Track for cleanup
            self._loaded_instances.add(instance)
            
            logger.info(f" PASS:  Loaded component {component.name} in {load_time_ms:.1f}ms")
            
            return instance
            
        except Exception as e:
            self._metrics.failed_components += 1
            logger.error(f" FAIL:  Failed to load component {component.name}: {e}")
            raise RuntimeError(f"Component loading failed for {component.name}: {e}")
        
        finally:
            component.loading = False
    
    async def _preload_components(self) -> None:
        """Preload components based on strategy."""
        # Wait a bit after startup to avoid interfering with critical operations
        await asyncio.sleep(5)
        
        logger.info(" CYCLE:  Starting component preloading...")
        
        # Get components that should be preloaded
        preload_components = [
            (name, comp) for name, comp in self._components.items()
            if comp.strategy in [LoadingStrategy.PRELOAD, LoadingStrategy.SMART] and not comp.loaded
        ]
        
        # Sort by priority (higher priority first)
        priority_order = {
            ComponentPriority.CRITICAL: 0,
            ComponentPriority.HIGH: 1,
            ComponentPriority.MEDIUM: 2,
            ComponentPriority.LOW: 3,
            ComponentPriority.OPTIONAL: 4
        }
        
        preload_components.sort(key=lambda x: priority_order[x[1].priority])
        
        loaded_count = 0
        for component_name, component in preload_components:
            try:
                # Check memory pressure before each load
                memory_stats = self.memory_service.get_memory_stats()
                if memory_stats.pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]:
                    logger.warning(f" WARNING: [U+FE0F] Stopping preload due to memory pressure ({memory_stats.percentage_used:.1f}%)")
                    break
                
                # Skip expensive components if memory is getting tight
                if (component.memory_cost_mb > 30 and 
                    memory_stats.pressure_level == MemoryPressureLevel.MODERATE):
                    logger.debug(f"Skipping preload of {component_name} due to moderate memory pressure")
                    continue
                
                await self.load_component(component_name)
                loaded_count += 1
                
                # Small delay between loads
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to preload component {component_name}: {e}")
        
        logger.info(f" PASS:  Preloading complete - loaded {loaded_count}/{len(preload_components)} components")
    
    async def unload_component(self, name: str) -> bool:
        """Unload component to free memory.
        
        Args:
            name: Component name to unload
            
        Returns:
            True if unloaded successfully, False if not loaded or failed
        """
        if name not in self._components:
            return False
        
        component = self._components[name]
        if not component.loaded or component.instance is None:
            return False
        
        try:
            logger.info(f"[U+1F5D1][U+FE0F] Unloading component {name} (freeing {component.memory_cost_mb}MB)")
            
            instance = component.instance
            
            # Call cleanup callback if provided
            if component.cleanup_callback:
                if asyncio.iscoroutinefunction(component.cleanup_callback):
                    await component.cleanup_callback(instance)
                else:
                    component.cleanup_callback(instance)
            
            # Try standard cleanup methods
            if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                if asyncio.iscoroutinefunction(instance.cleanup):
                    await instance.cleanup()
                else:
                    instance.cleanup()
            elif hasattr(instance, 'close') and callable(instance.close):
                if asyncio.iscoroutinefunction(instance.close):
                    await instance.close()
                else:
                    instance.close()
            
            # Clear references
            component.instance = None
            component.loaded = False
            
            # Update metrics
            self._metrics.loaded_components -= 1
            self._metrics.total_memory_mb -= component.memory_cost_mb
            
            logger.info(f" PASS:  Unloaded component {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading component {name}: {e}")
            return False
    
    async def unload_optional_components(self) -> int:
        """Unload optional components to free memory.
        
        Returns:
            Number of components unloaded
        """
        optional_components = [
            name for name, comp in self._components.items()
            if comp.loaded and comp.priority == ComponentPriority.OPTIONAL
        ]
        
        unloaded_count = 0
        for component_name in optional_components:
            if await self.unload_component(component_name):
                unloaded_count += 1
        
        logger.info(f"[U+1F5D1][U+FE0F] Unloaded {unloaded_count} optional components")
        return unloaded_count
    
    async def unload_low_priority_components(self) -> int:
        """Unload low priority components to free memory.
        
        Returns:
            Number of components unloaded
        """
        low_priority_components = [
            name for name, comp in self._components.items()
            if comp.loaded and comp.priority in [ComponentPriority.LOW, ComponentPriority.OPTIONAL]
        ]
        
        unloaded_count = 0
        for component_name in low_priority_components:
            if await self.unload_component(component_name):
                unloaded_count += 1
        
        logger.info(f"[U+1F5D1][U+FE0F] Unloaded {unloaded_count} low priority components")
        return unloaded_count
    
    def is_loaded(self, name: str) -> bool:
        """Check if component is loaded."""
        if name not in self._components:
            return False
        return self._components[name].loaded
    
    def get_component_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get component information."""
        if name not in self._components:
            return None
        
        component = self._components[name]
        return {
            'name': component.name,
            'loaded': component.loaded,
            'priority': component.priority.value,
            'strategy': component.strategy.value,
            'memory_cost_mb': component.memory_cost_mb,
            'description': component.description,
            'dependencies': component.dependencies,
            'access_count': component.access_count,
            'last_accessed': component.last_accessed.isoformat() if component.last_accessed else None,
            'load_time': component.load_time.isoformat() if component.load_time else None
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get loading metrics."""
        loaded_by_priority = {}
        for priority in ComponentPriority:
            loaded_by_priority[priority.value] = sum(
                1 for comp in self._components.values()
                if comp.priority == priority and comp.loaded
            )
        
        return {
            'total_components': self._metrics.total_components,
            'loaded_components': self._metrics.loaded_components,
            'failed_components': self._metrics.failed_components,
            'loading_percentage': (self._metrics.loaded_components / max(1, self._metrics.total_components)) * 100,
            'total_memory_mb': self._metrics.total_memory_mb,
            'average_load_time_ms': (self._metrics.total_load_time_ms / max(1, self._metrics.loaded_components)),
            'cache_hit_rate': (self._metrics.cache_hits / max(1, self._metrics.cache_hits + self._metrics.cache_misses)),
            'loaded_by_priority': loaded_by_priority,
            'is_initialized': self._is_initialized
        }
    
    @asynccontextmanager
    async def component_scope(self, name: str):
        """Load component for duration of context, then optionally unload.
        
        Args:
            name: Component name
            
        Yields:
            Component instance
            
        Example:
            async with loader.component_scope('analytics_engine') as analytics:
                result = await analytics.process_data(data)
            # Component may be unloaded after use if memory pressure is high
        """
        component = await self.load_component(name)
        try:
            yield component
        finally:
            # Optionally unload if memory pressure is high and component is not critical
            memory_stats = self.memory_service.get_memory_stats()
            comp_def = self._components[name]
            
            if (memory_stats.pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL] and
                comp_def.priority in [ComponentPriority.LOW, ComponentPriority.OPTIONAL]):
                
                logger.debug(f"Auto-unloading {name} after scope due to memory pressure")
                await self.unload_component(name)
    
    async def shutdown(self) -> None:
        """Shutdown loader and cleanup all components."""
        logger.info("[U+1F6D1] Shutting down LazyComponentLoader...")
        
        if self._preload_task:
            self._preload_task.cancel()
        
        # Unload all components
        loaded_components = [
            name for name, comp in self._components.items() if comp.loaded
        ]
        
        for component_name in loaded_components:
            await self.unload_component(component_name)
        
        logger.info(" PASS:  LazyComponentLoader shutdown complete")


# Global loader instance
_component_loader: Optional[LazyComponentLoader] = None


def get_component_loader() -> LazyComponentLoader:
    """Get global lazy component loader instance."""
    global _component_loader
    if _component_loader is None:
        _component_loader = LazyComponentLoader()
    return _component_loader


async def initialize_component_loader() -> LazyComponentLoader:
    """Initialize lazy component loader."""
    loader = get_component_loader()
    if not loader._is_initialized:
        await loader.initialize()
    return loader


# Convenience decorators and helpers

def lazy_component(
    name: str,
    priority: ComponentPriority = ComponentPriority.MEDIUM,
    strategy: LoadingStrategy = LoadingStrategy.ON_DEMAND,
    dependencies: List[str] = None,
    memory_cost_mb: float = 0.0,
    description: str = ""
):
    """Decorator to register function as lazy component.
    
    Args:
        name: Component name
        priority: Loading priority
        strategy: Loading strategy  
        dependencies: Component dependencies
        memory_cost_mb: Estimated memory cost
        description: Component description
        
    Example:
        @lazy_component('analytics_engine', 
                       priority=ComponentPriority.LOW,
                       memory_cost_mb=150.0)
        async def create_analytics_engine():
            return AnalyticsEngine()
    """
    def decorator(func):
        loader = get_component_loader()
        loader.register_component(
            name=name,
            factory=func,
            priority=priority,
            strategy=strategy,
            dependencies=dependencies,
            memory_cost_mb=memory_cost_mb,
            description=description
        )
        return func
    return decorator


async def get_lazy_component(name: str) -> Any:
    """Get lazy component by name."""
    loader = get_component_loader()
    return await loader.load_component(name)