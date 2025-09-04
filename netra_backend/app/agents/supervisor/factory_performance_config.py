"""
Factory Performance Configuration - SSOT for all factory optimization settings

Business Value Justification:
- Segment: Platform Performance
- Business Goal: Real-time chat responsiveness  
- Value Impact: <20ms total overhead enables instant user feedback
- Strategic Impact: Support 100+ concurrent users without degradation

This module defines the performance configuration for the consolidated agent factory,
enabling toggling of performance optimizations while maintaining backward compatibility.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class FactoryPerformanceConfig:
    """
    SSOT for all factory performance settings.
    
    This configuration enables fine-tuning of performance optimizations
    based on deployment environment and load characteristics.
    """
    
    # WebSocket Emitter Pooling Configuration
    enable_emitter_pooling: bool = field(
        default_factory=lambda: os.getenv('FACTORY_ENABLE_POOLING', 'true').lower() == 'true'
    )
    pool_initial_size: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_POOL_INITIAL_SIZE', '20'))
    )
    pool_max_size: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_POOL_MAX_SIZE', '200'))
    )
    pool_cleanup_interval: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_POOL_CLEANUP_INTERVAL', '300'))
    )
    pool_reuse_timeout: float = field(
        default_factory=lambda: float(os.getenv('FACTORY_POOL_REUSE_TIMEOUT', '60.0'))
    )
    
    # Agent Class Caching Configuration
    enable_class_caching: bool = field(
        default_factory=lambda: os.getenv('FACTORY_ENABLE_CACHING', 'true').lower() == 'true'
    )
    cache_size: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_CACHE_SIZE', '128'))
    )
    cache_ttl: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_CACHE_TTL', '3600'))
    )
    
    # Metrics Collection Configuration
    enable_metrics: bool = field(
        default_factory=lambda: os.getenv('FACTORY_ENABLE_METRICS', 'true').lower() == 'true'
    )
    metrics_sample_rate: float = field(
        default_factory=lambda: float(os.getenv('FACTORY_METRICS_SAMPLE_RATE', '0.1'))
    )
    metrics_buffer_size: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_METRICS_BUFFER_SIZE', '100'))
    )
    
    # Object Reuse Configuration
    enable_object_reuse: bool = field(
        default_factory=lambda: os.getenv('FACTORY_ENABLE_OBJECT_REUSE', 'true').lower() == 'true'
    )
    reuse_pool_size: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_REUSE_POOL_SIZE', '50'))
    )
    
    # Lazy Initialization Configuration
    enable_lazy_init: bool = field(
        default_factory=lambda: os.getenv('FACTORY_ENABLE_LAZY_INIT', 'true').lower() == 'true'
    )
    
    # Performance Targets
    target_context_creation_ms: float = field(
        default_factory=lambda: float(os.getenv('FACTORY_TARGET_CONTEXT_MS', '5.0'))
    )
    target_agent_creation_ms: float = field(
        default_factory=lambda: float(os.getenv('FACTORY_TARGET_AGENT_MS', '10.0'))
    )
    target_cleanup_ms: float = field(
        default_factory=lambda: float(os.getenv('FACTORY_TARGET_CLEANUP_MS', '2.0'))
    )
    
    # Concurrency Configuration
    max_concurrent_per_user: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_MAX_CONCURRENT_PER_USER', '10'))
    )
    execution_timeout: float = field(
        default_factory=lambda: float(os.getenv('FACTORY_EXECUTION_TIMEOUT', '30.0'))
    )
    
    # Memory Management
    max_history_per_user: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_MAX_HISTORY_PER_USER', '50'))
    )
    enable_weak_references: bool = field(
        default_factory=lambda: os.getenv('FACTORY_ENABLE_WEAK_REFS', 'true').lower() == 'true'
    )
    
    # Feature Flags
    use_optimized_constructor: bool = field(
        default_factory=lambda: os.getenv('FACTORY_USE_OPTIMIZED_CONSTRUCTOR', 'true').lower() == 'true'
    )
    enable_event_batching: bool = field(
        default_factory=lambda: os.getenv('FACTORY_ENABLE_EVENT_BATCHING', 'false').lower() == 'true'
    )
    event_batch_size: int = field(
        default_factory=lambda: int(os.getenv('FACTORY_EVENT_BATCH_SIZE', '10'))
    )
    event_batch_timeout: float = field(
        default_factory=lambda: float(os.getenv('FACTORY_EVENT_BATCH_TIMEOUT', '0.1'))
    )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization."""
        return {
            'emitter_pooling': {
                'enabled': self.enable_emitter_pooling,
                'initial_size': self.pool_initial_size,
                'max_size': self.pool_max_size,
                'cleanup_interval': self.pool_cleanup_interval,
                'reuse_timeout': self.pool_reuse_timeout
            },
            'class_caching': {
                'enabled': self.enable_class_caching,
                'size': self.cache_size,
                'ttl': self.cache_ttl
            },
            'metrics': {
                'enabled': self.enable_metrics,
                'sample_rate': self.metrics_sample_rate,
                'buffer_size': self.metrics_buffer_size
            },
            'object_reuse': {
                'enabled': self.enable_object_reuse,
                'pool_size': self.reuse_pool_size
            },
            'lazy_init': {
                'enabled': self.enable_lazy_init
            },
            'performance_targets': {
                'context_creation_ms': self.target_context_creation_ms,
                'agent_creation_ms': self.target_agent_creation_ms,
                'cleanup_ms': self.target_cleanup_ms
            },
            'concurrency': {
                'max_per_user': self.max_concurrent_per_user,
                'execution_timeout': self.execution_timeout,
                'max_history_per_user': self.max_history_per_user
            },
            'memory': {
                'weak_references': self.enable_weak_references
            },
            'features': {
                'optimized_constructor': self.use_optimized_constructor,
                'event_batching': self.enable_event_batching,
                'event_batch_size': self.event_batch_size,
                'event_batch_timeout': self.event_batch_timeout
            }
        }
    
    @classmethod
    def minimal(cls) -> 'FactoryPerformanceConfig':
        """Create minimal configuration with all optimizations disabled."""
        return cls(
            enable_emitter_pooling=False,
            enable_class_caching=False,
            enable_metrics=False,
            enable_object_reuse=False,
            enable_lazy_init=False,
            enable_weak_references=False,
            use_optimized_constructor=False,
            enable_event_batching=False
        )
    
    @classmethod
    def balanced(cls) -> 'FactoryPerformanceConfig':
        """Create balanced configuration for typical production use."""
        return cls(
            enable_emitter_pooling=True,
            pool_initial_size=10,
            pool_max_size=100,
            enable_class_caching=True,
            cache_size=64,
            enable_metrics=True,
            metrics_sample_rate=0.1,
            enable_object_reuse=True,
            reuse_pool_size=25,
            enable_lazy_init=True,
            enable_weak_references=True,
            use_optimized_constructor=True,
            enable_event_batching=False
        )
    
    @classmethod
    def maximum_performance(cls) -> 'FactoryPerformanceConfig':
        """Create maximum performance configuration for high-load scenarios."""
        return cls(
            enable_emitter_pooling=True,
            pool_initial_size=50,
            pool_max_size=500,
            enable_class_caching=True,
            cache_size=256,
            enable_metrics=False,  # Disable for maximum performance
            enable_object_reuse=True,
            reuse_pool_size=100,
            enable_lazy_init=True,
            enable_weak_references=True,
            use_optimized_constructor=True,
            enable_event_batching=True,
            event_batch_size=20,
            event_batch_timeout=0.05
        )


# Module-level singleton for global configuration
_global_config: Optional[FactoryPerformanceConfig] = None


def get_factory_performance_config() -> FactoryPerformanceConfig:
    """Get the global factory performance configuration."""
    global _global_config
    if _global_config is None:
        # Default to balanced configuration
        _global_config = FactoryPerformanceConfig()
    return _global_config


def set_factory_performance_config(config: FactoryPerformanceConfig) -> None:
    """Set the global factory performance configuration."""
    global _global_config
    _global_config = config


def reset_factory_performance_config() -> None:
    """Reset to default configuration."""
    global _global_config
    _global_config = None