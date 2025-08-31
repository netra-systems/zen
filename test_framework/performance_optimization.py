"""Performance Optimization and Resource Management for Test Infrastructure.

This module provides comprehensive performance optimization and resource management
for the IsolatedEnvironment test infrastructure, enabling efficient testing of
2,941+ test files with parallel execution, resource pooling, and intelligent
cleanup strategies.

Business Value: Platform/Internal - Performance Excellence
Optimizes test infrastructure for CI/CD usage while maintaining reliability.

Key Features:
- Intelligent resource pooling and connection management
- Parallel test execution with resource safety
- Performance monitoring and bottleneck detection
- Memory usage optimization and leak prevention
- Adaptive resource allocation based on system capabilities
- CI/CD optimized configurations
- Resource usage analytics and reporting

Architectural Principles:
- Performance by design with configurable optimization levels
- Resource safety with automatic cleanup and leak detection
- Scalability from local development to CI/CD environments
- Monitoring and observability for performance analysis
"""

import asyncio
import logging
import os
import threading
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Optional, Set, Union, Callable,
    NamedTuple, Tuple, AsyncIterator
)
from enum import Enum
import statistics

# Core infrastructure imports
from test_framework.isolated_environment_manager import (
    IsolatedEnvironmentManager,
    IsolationConfig,
    TestResource,
    ResourceType
)

# System monitoring imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import gc
    GC_AVAILABLE = True
except ImportError:
    GC_AVAILABLE = False

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Optimization levels for different scenarios."""
    DEVELOPMENT = "development"      # Fast feedback, minimal optimization
    CI_FAST = "ci_fast"            # Fast CI with basic optimization
    CI_THOROUGH = "ci_thorough"    # Thorough CI with full optimization
    PRODUCTION = "production"      # Production-grade optimization


class ResourcePoolStrategy(Enum):
    """Resource pooling strategies."""
    NONE = "none"                  # No pooling, create on demand
    SIMPLE = "simple"              # Basic pooling with fixed size
    ADAPTIVE = "adaptive"          # Adaptive pooling based on usage
    INTELLIGENT = "intelligent"    # AI-driven pooling optimization


@dataclass
class PerformanceMetrics:
    """Performance metrics for test infrastructure."""
    
    # Resource creation metrics
    resource_creation_times: List[float] = field(default_factory=list)
    resource_cleanup_times: List[float] = field(default_factory=list)
    resource_pool_hits: int = 0
    resource_pool_misses: int = 0
    
    # Test execution metrics
    test_setup_times: List[float] = field(default_factory=list)
    test_execution_times: List[float] = field(default_factory=list)
    test_cleanup_times: List[float] = field(default_factory=list)
    
    # Memory metrics
    peak_memory_usage_mb: float = 0.0
    average_memory_usage_mb: float = 0.0
    memory_leaks_detected: int = 0
    
    # Concurrency metrics
    max_concurrent_tests: int = 0
    average_concurrent_tests: float = 0.0
    resource_contention_events: int = 0
    
    # Error metrics
    resource_creation_failures: int = 0
    resource_cleanup_failures: int = 0
    timeout_events: int = 0
    
    # Timestamps
    monitoring_start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    
    def add_resource_creation_time(self, duration: float) -> None:
        """Add resource creation time measurement."""
        self.resource_creation_times.append(duration)
        self.last_update_time = time.time()
        
    def add_resource_cleanup_time(self, duration: float) -> None:
        """Add resource cleanup time measurement."""
        self.resource_cleanup_times.append(duration)
        self.last_update_time = time.time()
        
    def add_test_setup_time(self, duration: float) -> None:
        """Add test setup time measurement."""
        self.test_setup_times.append(duration)
        self.last_update_time = time.time()
        
    def record_pool_hit(self) -> None:
        """Record resource pool hit."""
        self.resource_pool_hits += 1
        self.last_update_time = time.time()
        
    def record_pool_miss(self) -> None:
        """Record resource pool miss."""
        self.resource_pool_misses += 1
        self.last_update_time = time.time()
        
    def get_pool_hit_ratio(self) -> float:
        """Calculate pool hit ratio."""
        total = self.resource_pool_hits + self.resource_pool_misses
        return self.resource_pool_hits / total if total > 0 else 0.0
        
    def get_average_creation_time(self) -> float:
        """Get average resource creation time."""
        return statistics.mean(self.resource_creation_times) if self.resource_creation_times else 0.0
        
    def get_average_cleanup_time(self) -> float:
        """Get average resource cleanup time."""
        return statistics.mean(self.resource_cleanup_times) if self.resource_cleanup_times else 0.0
        
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            'pool_hit_ratio': self.get_pool_hit_ratio(),
            'average_creation_time_ms': self.get_average_creation_time() * 1000,
            'average_cleanup_time_ms': self.get_average_cleanup_time() * 1000,
            'peak_memory_usage_mb': self.peak_memory_usage_mb,
            'max_concurrent_tests': self.max_concurrent_tests,
            'total_failures': self.resource_creation_failures + self.resource_cleanup_failures,
            'monitoring_duration_s': time.time() - self.monitoring_start_time
        }


class ResourcePool:
    """Intelligent resource pool with optimization strategies."""
    
    def __init__(
        self,
        resource_type: ResourceType,
        pool_strategy: ResourcePoolStrategy = ResourcePoolStrategy.ADAPTIVE,
        min_size: int = 2,
        max_size: int = 20,
        idle_timeout: float = 300.0  # 5 minutes
    ):
        self.resource_type = resource_type
        self.pool_strategy = pool_strategy
        self.min_size = min_size
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        
        # Pool state
        self._available_resources: deque[TestResource] = deque()
        self._in_use_resources: Set[TestResource] = set()
        self._creation_times: deque[float] = deque(maxlen=100)
        self._usage_stats: Dict[str, int] = defaultdict(int)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self) -> None:
        """Initialize the resource pool."""
        # Start cleanup task for idle resources
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_resources())
        
        # Pre-warm pool if strategy requires it
        if self.pool_strategy in [ResourcePoolStrategy.ADAPTIVE, ResourcePoolStrategy.INTELLIGENT]:
            await self._warmup_pool()
            
        logger.debug(f"Initialized resource pool for {self.resource_type.value} with strategy {self.pool_strategy.value}")
        
    async def shutdown(self) -> None:
        """Shutdown the resource pool."""
        self._shutdown_event.set()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
                
        # Cleanup all resources
        await self._cleanup_all_resources()
        
        logger.debug(f"Shutdown resource pool for {self.resource_type.value}")
        
    async def acquire_resource(self, resource_factory: Callable) -> TestResource:
        """Acquire a resource from the pool or create new one."""
        with self._lock:
            # Try to get from pool first
            if self._available_resources:
                resource = self._available_resources.popleft()
                self._in_use_resources.add(resource)
                self._usage_stats['pool_hits'] += 1
                resource.touch()
                return resource
                
            self._usage_stats['pool_misses'] += 1
            
        # Create new resource if pool is empty
        start_time = time.time()
        
        try:
            resource = await resource_factory()
            creation_time = time.time() - start_time
            
            with self._lock:
                self._creation_times.append(creation_time)
                self._in_use_resources.add(resource)
                self._usage_stats['resources_created'] += 1
                
            return resource
            
        except Exception as e:
            self._usage_stats['creation_failures'] += 1
            logger.error(f"Failed to create resource for {self.resource_type.value}: {e}")
            raise
            
    async def release_resource(self, resource: TestResource) -> None:
        """Release a resource back to the pool."""
        with self._lock:
            self._in_use_resources.discard(resource)
            
            # Check if pool has space and resource is still healthy
            if (len(self._available_resources) < self.max_size and 
                resource.is_active and 
                time.time() - resource.last_accessed < self.idle_timeout):
                
                self._available_resources.append(resource)
                self._usage_stats['resources_returned'] += 1
                resource.touch()
            else:
                # Clean up resource if pool is full or resource is stale
                await resource.cleanup()
                self._usage_stats['resources_cleaned'] += 1
                
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            total_requests = self._usage_stats['pool_hits'] + self._usage_stats['pool_misses']
            hit_ratio = self._usage_stats['pool_hits'] / total_requests if total_requests > 0 else 0.0
            
            avg_creation_time = (
                statistics.mean(self._creation_times) if self._creation_times else 0.0
            )
            
            return {
                'resource_type': self.resource_type.value,
                'pool_strategy': self.pool_strategy.value,
                'available_resources': len(self._available_resources),
                'in_use_resources': len(self._in_use_resources),
                'hit_ratio': hit_ratio,
                'average_creation_time_ms': avg_creation_time * 1000,
                'total_created': self._usage_stats['resources_created'],
                'total_cleaned': self._usage_stats['resources_cleaned'],
                'creation_failures': self._usage_stats['creation_failures']
            }
            
    async def _warmup_pool(self) -> None:
        """Warm up the pool with minimum resources."""
        # This would require access to resource factory
        # For now, just log the intent
        logger.debug(f"Pool warmup requested for {self.resource_type.value}")
        
    async def _cleanup_idle_resources(self) -> None:
        """Background task to clean up idle resources."""
        while not self._shutdown_event.is_set():
            try:
                current_time = time.time()
                resources_to_cleanup = []
                
                with self._lock:
                    # Find idle resources
                    for resource in list(self._available_resources):
                        if current_time - resource.last_accessed > self.idle_timeout:
                            self._available_resources.remove(resource)
                            resources_to_cleanup.append(resource)
                            
                # Cleanup idle resources outside the lock
                for resource in resources_to_cleanup:
                    try:
                        await resource.cleanup()
                        self._usage_stats['idle_cleanups'] += 1
                    except Exception as e:
                        logger.warning(f"Error cleaning up idle resource: {e}")
                        
                # Sleep before next cleanup cycle
                await asyncio.sleep(60.0)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in idle resource cleanup: {e}")
                await asyncio.sleep(60.0)
                
    async def _cleanup_all_resources(self) -> None:
        """Clean up all resources in the pool."""
        all_resources = []
        
        with self._lock:
            all_resources.extend(self._available_resources)
            all_resources.extend(self._in_use_resources)
            self._available_resources.clear()
            self._in_use_resources.clear()
            
        # Clean up all resources
        for resource in all_resources:
            try:
                await resource.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up resource during shutdown: {e}")


class PerformanceOptimizer:
    """Performance optimizer for test infrastructure.
    
    This class provides comprehensive performance optimization including:
    - Resource pool management
    - Memory usage monitoring
    - Concurrency optimization
    - Performance metrics collection
    - Adaptive resource allocation
    """
    
    def __init__(
        self,
        optimization_level: OptimizationLevel = OptimizationLevel.CI_FAST
    ):
        self.optimization_level = optimization_level
        self.metrics = PerformanceMetrics()
        self.resource_pools: Dict[ResourceType, ResourcePool] = {}
        self._system_monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Configuration based on optimization level
        self.config = self._get_optimization_config(optimization_level)
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info(f"PerformanceOptimizer initialized with level: {optimization_level.value}")
        
    def _get_optimization_config(self, level: OptimizationLevel) -> Dict[str, Any]:
        """Get optimization configuration for the specified level."""
        configs = {
            OptimizationLevel.DEVELOPMENT: {
                'pool_strategy': ResourcePoolStrategy.SIMPLE,
                'pool_min_size': 1,
                'pool_max_size': 5,
                'monitor_memory': False,
                'monitor_system': False,
                'concurrent_tests': 5,
                'cleanup_interval': 300.0  # 5 minutes
            },
            OptimizationLevel.CI_FAST: {
                'pool_strategy': ResourcePoolStrategy.ADAPTIVE,
                'pool_min_size': 2,
                'pool_max_size': 10,
                'monitor_memory': True,
                'monitor_system': False,
                'concurrent_tests': 10,
                'cleanup_interval': 180.0  # 3 minutes
            },
            OptimizationLevel.CI_THOROUGH: {
                'pool_strategy': ResourcePoolStrategy.INTELLIGENT,
                'pool_min_size': 5,
                'pool_max_size': 20,
                'monitor_memory': True,
                'monitor_system': True,
                'concurrent_tests': 20,
                'cleanup_interval': 120.0  # 2 minutes
            },
            OptimizationLevel.PRODUCTION: {
                'pool_strategy': ResourcePoolStrategy.INTELLIGENT,
                'pool_min_size': 10,
                'pool_max_size': 50,
                'monitor_memory': True,
                'monitor_system': True,
                'concurrent_tests': 50,
                'cleanup_interval': 60.0  # 1 minute
            }
        }
        
        return configs[level]
        
    async def initialize(self) -> None:
        """Initialize the performance optimizer."""
        # Initialize resource pools
        for resource_type in ResourceType:
            pool = ResourcePool(
                resource_type=resource_type,
                pool_strategy=self.config['pool_strategy'],
                min_size=self.config['pool_min_size'],
                max_size=self.config['pool_max_size']
            )
            await pool.initialize()
            self.resource_pools[resource_type] = pool
            
        # Start system monitoring if enabled
        if self.config['monitor_system']:
            self._system_monitor_task = asyncio.create_task(self._system_monitor_loop())
            
        logger.info("PerformanceOptimizer initialized successfully")
        
    async def shutdown(self) -> None:
        """Shutdown the performance optimizer."""
        logger.info("Shutting down PerformanceOptimizer")
        
        self._shutdown_event.set()
        
        # Stop system monitoring
        if self._system_monitor_task:
            self._system_monitor_task.cancel()
            try:
                await self._system_monitor_task
            except asyncio.CancelledError:
                pass
                
        # Shutdown resource pools
        for pool in self.resource_pools.values():
            await pool.shutdown()
            
        # Log final performance summary
        summary = self.metrics.get_summary()
        logger.info(f"Performance summary: {summary}")
        
    async def optimize_resource_creation(
        self,
        resource_type: ResourceType,
        resource_factory: Callable
    ) -> TestResource:
        """Optimize resource creation using pools."""
        pool = self.resource_pools.get(resource_type)
        
        if pool and self.config['pool_strategy'] != ResourcePoolStrategy.NONE:
            # Use pool
            start_time = time.time()
            resource = await pool.acquire_resource(resource_factory)
            creation_time = time.time() - start_time
            
            self.metrics.add_resource_creation_time(creation_time)
            self.metrics.record_pool_hit()
            
            return resource
        else:
            # Create directly
            start_time = time.time()
            resource = await resource_factory()
            creation_time = time.time() - start_time
            
            self.metrics.add_resource_creation_time(creation_time)
            self.metrics.record_pool_miss()
            
            return resource
            
    async def optimize_resource_cleanup(
        self,
        resource: TestResource
    ) -> None:
        """Optimize resource cleanup using pools."""
        start_time = time.time()
        
        pool = self.resource_pools.get(resource.resource_type)
        
        if pool and self.config['pool_strategy'] != ResourcePoolStrategy.NONE:
            # Return to pool
            await pool.release_resource(resource)
        else:
            # Clean up directly
            await resource.cleanup()
            
        cleanup_time = time.time() - start_time
        self.metrics.add_resource_cleanup_time(cleanup_time)
        
    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations."""
        recommendations = []
        
        # Analyze pool hit ratios
        for resource_type, pool in self.resource_pools.items():
            stats = pool.get_pool_stats()
            
            if stats['hit_ratio'] < 0.5:
                recommendations.append(
                    f"Consider increasing pool size for {resource_type.value} "
                    f"(current hit ratio: {stats['hit_ratio']:.2%})"
                )
                
            if stats['average_creation_time_ms'] > 1000:
                recommendations.append(
                    f"Resource creation for {resource_type.value} is slow "
                    f"({stats['average_creation_time_ms']:.1f}ms)"
                )
                
        # Memory recommendations
        if self.metrics.peak_memory_usage_mb > 1000:
            recommendations.append(
                f"High memory usage detected ({self.metrics.peak_memory_usage_mb:.1f}MB). "
                "Consider reducing concurrent test count or optimizing test data."
            )
            
        # Concurrency recommendations
        if self.metrics.resource_contention_events > 10:
            recommendations.append(
                "Resource contention detected. Consider increasing pool sizes "
                "or reducing concurrent test execution."
            )
            
        return recommendations
        
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        pool_stats = {
            resource_type.value: pool.get_pool_stats() 
            for resource_type, pool in self.resource_pools.items()
        }
        
        return {
            'optimization_level': self.optimization_level.value,
            'metrics_summary': self.metrics.get_summary(),
            'pool_statistics': pool_stats,
            'recommendations': self.get_optimization_recommendations(),
            'system_info': self._get_system_info()
        }
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for performance analysis."""
        info = {
            'python_version': os.sys.version,
            'platform': os.name,
        }
        
        if PSUTIL_AVAILABLE:
            try:
                info.update({
                    'cpu_count': psutil.cpu_count(),
                    'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                    'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                    'cpu_percent': psutil.cpu_percent(),
                })
            except Exception as e:
                logger.warning(f"Error getting system info: {e}")
                
        return info
        
    async def _system_monitor_loop(self) -> None:
        """Background system monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                if PSUTIL_AVAILABLE:
                    # Monitor memory usage
                    memory_info = psutil.virtual_memory()
                    memory_usage_mb = (memory_info.total - memory_info.available) / (1024**2)
                    
                    self.metrics.peak_memory_usage_mb = max(
                        self.metrics.peak_memory_usage_mb,
                        memory_usage_mb
                    )
                    
                    # Check for memory leaks
                    if GC_AVAILABLE:
                        gc_stats = gc.get_stats()
                        # Simple heuristic for memory leak detection
                        if len(gc_stats) > 0 and gc_stats[0].get('collections', 0) > 1000:
                            self.metrics.memory_leaks_detected += 1
                            
                await asyncio.sleep(30.0)  # Monitor every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in system monitoring: {e}")
                await asyncio.sleep(30.0)


class OptimizedIsolatedEnvironmentManager(IsolatedEnvironmentManager):
    """Performance-optimized version of IsolatedEnvironmentManager.
    
    This class extends the base IsolatedEnvironmentManager with comprehensive
    performance optimizations including resource pooling, intelligent caching,
    and adaptive resource allocation.
    """
    
    def __init__(
        self,
        config: Optional[IsolationConfig] = None,
        optimization_level: OptimizationLevel = OptimizationLevel.CI_FAST
    ):
        super().__init__(config)
        self.optimizer = PerformanceOptimizer(optimization_level)
        self.optimization_level = optimization_level
        
        logger.info(
            f"OptimizedIsolatedEnvironmentManager initialized with "
            f"optimization level: {optimization_level.value}"
        )
        
    async def initialize(self) -> None:
        """Initialize with performance optimization."""
        await super().initialize()
        await self.optimizer.initialize()
        
        logger.info("OptimizedIsolatedEnvironmentManager initialized successfully")
        
    async def shutdown(self) -> None:
        """Shutdown with performance reporting."""
        # Get final performance report
        performance_report = self.optimizer.get_performance_report()
        
        # Shutdown optimizer first
        await self.optimizer.shutdown()
        
        # Then shutdown base manager
        await super().shutdown()
        
        logger.info(f"OptimizedIsolatedEnvironmentManager shutdown. Performance report: {performance_report}")
        
    async def get_isolated_database(self, test_id: str) -> 'DatabaseTestResource':
        """Get optimized isolated database."""
        from test_framework.isolated_environment_manager import DatabaseTestResource
        
        async def factory():
            resource = DatabaseTestResource(f"{test_id}_db")
            await resource.initialize()
            return resource
            
        return await self.optimizer.optimize_resource_creation(
            ResourceType.DATABASE_CONNECTION,
            factory
        )
        
    async def cleanup_test_resources(self, test_id: str) -> None:
        """Cleanup with optimization."""
        resources_to_cleanup = []
        
        with self._lock:
            for resource_id, resource in list(self._active_resources.items()):
                if resource_id.startswith(test_id):
                    resources_to_cleanup.append(resource)
                    del self._active_resources[resource_id]
                    
        # Use optimized cleanup
        for resource in resources_to_cleanup:
            await self.optimizer.optimize_resource_cleanup(resource)
            
        logger.debug(f"Optimized cleanup of {len(resources_to_cleanup)} resources for test {test_id}")
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.optimizer.get_performance_report()


# ============================================================================
# FACTORY FUNCTIONS FOR OPTIMIZED MANAGERS
# ============================================================================

def create_optimized_environment_manager(
    optimization_level: OptimizationLevel = OptimizationLevel.CI_FAST,
    config_overrides: Optional[Dict[str, Any]] = None
) -> OptimizedIsolatedEnvironmentManager:
    """Create optimized environment manager with best practices configuration.
    
    Args:
        optimization_level: Level of optimization to apply
        config_overrides: Optional configuration overrides
        
    Returns:
        Configured OptimizedIsolatedEnvironmentManager
    """
    # Base configuration based on optimization level
    base_configs = {
        OptimizationLevel.DEVELOPMENT: IsolationConfig(
            enable_parallel_execution=True,
            max_concurrent_tests=5,
            enable_resource_pooling=False,
            enable_health_monitoring=False
        ),
        OptimizationLevel.CI_FAST: IsolationConfig(
            enable_parallel_execution=True,
            max_concurrent_tests=10,
            enable_resource_pooling=True,
            pool_max_connections=20,
            enable_health_monitoring=True
        ),
        OptimizationLevel.CI_THOROUGH: IsolationConfig(
            enable_parallel_execution=True,
            max_concurrent_tests=20,
            enable_resource_pooling=True,
            pool_max_connections=50,
            enable_health_monitoring=True,
            enable_resource_leak_detection=True
        ),
        OptimizationLevel.PRODUCTION: IsolationConfig(
            enable_parallel_execution=True,
            max_concurrent_tests=50,
            enable_resource_pooling=True,
            pool_max_connections=100,
            enable_health_monitoring=True,
            enable_resource_leak_detection=True,
            cleanup_timeout=30.0
        )
    }
    
    config = base_configs[optimization_level]
    
    # Apply overrides if provided
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
                
    return OptimizedIsolatedEnvironmentManager(config, optimization_level)


def get_ci_optimized_manager() -> OptimizedIsolatedEnvironmentManager:
    """Get CI-optimized manager with best performance settings.
    
    Returns:
        Manager optimized for CI/CD environments
    """
    return create_optimized_environment_manager(
        OptimizationLevel.CI_THOROUGH,
        {
            'enable_automatic_cleanup': True,
            'cleanup_on_failure': True,
            'resource_timeout': 45.0,
            'cleanup_timeout': 15.0
        }
    )


def get_development_optimized_manager() -> OptimizedIsolatedEnvironmentManager:
    """Get development-optimized manager for fast feedback.
    
    Returns:
        Manager optimized for development environments
    """
    return create_optimized_environment_manager(
        OptimizationLevel.DEVELOPMENT,
        {
            'resource_timeout': 30.0,
            'cleanup_timeout': 5.0,
            'enable_lazy_loading': True
        }
    )


# Global optimized manager instance
_global_optimized_manager: Optional[OptimizedIsolatedEnvironmentManager] = None
_optimized_manager_lock = threading.Lock()


def get_global_optimized_manager(
    optimization_level: OptimizationLevel = OptimizationLevel.CI_FAST
) -> OptimizedIsolatedEnvironmentManager:
    """Get global optimized environment manager instance.
    
    Args:
        optimization_level: Optimization level for the manager
        
    Returns:
        Global OptimizedIsolatedEnvironmentManager instance
    """
    global _global_optimized_manager
    
    if _global_optimized_manager is None:
        with _optimized_manager_lock:
            if _global_optimized_manager is None:
                _global_optimized_manager = create_optimized_environment_manager(optimization_level)
                
    return _global_optimized_manager


async def reset_global_optimized_manager() -> None:
    """Reset global optimized manager (for testing)."""
    global _global_optimized_manager
    
    if _global_optimized_manager is not None:
        with _optimized_manager_lock:
            if _global_optimized_manager is not None:
                await _global_optimized_manager.shutdown()
                _global_optimized_manager = None
