"""Resource management for LLM operations.

This module provides backward compatibility imports for the refactored
modular resource management components.
"""

# Import from the new modular structure for backward compatibility  
from netra_backend.app.llm.resource_pool import RequestPool
from netra_backend.app.llm.resource_batcher import RequestBatcher
from netra_backend.app.llm.resource_cache import LLMCacheManager as CacheManager
from netra_backend.app.llm.resource_monitor import ResourceMonitor, resource_monitor

# Re-export for backward compatibility
__all__ = [
    'RequestPool',
    'RequestBatcher', 
    'CacheManager',
    'ResourceMonitor',
    'resource_monitor'
]