"""
Resource Manager Module - SSOT Compatibility Layer

This module serves as a compatibility layer for resource management functionality,
following CLAUDE.md SSOT principles by importing from existing resource management
implementations across the codebase.

All functionality is imported from the canonical resource management modules.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
import asyncio
import logging
from contextlib import asynccontextmanager

# SSOT Imports - Resource management functionality from existing modules
from shared.isolated_environment import IsolatedEnvironment

# Import existing resource managers
try:
    from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
except ImportError:
    ReliabilityManager = None

try:
    from netra_backend.app.db.database_manager import DatabaseManager
except ImportError:
    DatabaseManager = None

try:
    from netra_backend.app.services.redis.redis_connection_manager import RedisConnectionManager
except ImportError:
    RedisConnectionManager = None

if TYPE_CHECKING:
    from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher

logger = logging.getLogger(__name__)

class ResourceManager:
    """
    Unified Resource Manager - SSOT pattern for system resource management.
    
    This class coordinates resource allocation and management across the system
    without duplicating existing functionality.
    """
    
    def __init__(self):
        """Initialize resource manager."""
        self._env = IsolatedEnvironment()
        self._resources: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize resource manager and register available resources."""
        if self._initialized:
            return
            
        logger.info("Initializing ResourceManager")
        
        # Register database resources if available
        if DatabaseManager:
            try:
                self._resources['database'] = DatabaseManager()
                logger.info("Database resource registered")
            except Exception as e:
                logger.warning(f"Failed to register database resource: {e}")
        
        # Register Redis resources if available  
        if RedisConnectionManager:
            try:
                self._resources['redis'] = RedisConnectionManager()
                logger.info("Redis resource registered")
            except Exception as e:
                logger.warning(f"Failed to register Redis resource: {e}")
                
        # Register reliability manager if available
        if ReliabilityManager:
            try:
                self._resources['reliability'] = ReliabilityManager()
                logger.info("Reliability resource registered")
            except Exception as e:
                logger.warning(f"Failed to register reliability resource: {e}")
        
        self._initialized = True
        logger.info(f"ResourceManager initialized with {len(self._resources)} resources")
    
    def get_resource(self, resource_name: str) -> Optional[Any]:
        """
        Get a managed resource by name.
        
        Args:
            resource_name: Name of the resource to retrieve
            
        Returns:
            Optional[Any]: The resource instance or None if not found
        """
        if not self._initialized:
            logger.warning("ResourceManager not initialized, attempting auto-initialization")
            asyncio.create_task(self.initialize())
            
        return self._resources.get(resource_name)
    
    def register_resource(self, name: str, resource: Any) -> bool:
        """
        Register a new resource with the manager.
        
        Args:
            name: Name for the resource
            resource: Resource instance to register
            
        Returns:
            bool: True if registration succeeded
        """
        try:
            self._resources[name] = resource
            logger.info(f"Resource '{name}' registered successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to register resource '{name}': {e}")
            return False
    
    def unregister_resource(self, name: str) -> bool:
        """
        Unregister a resource from the manager.
        
        Args:
            name: Name of the resource to unregister
            
        Returns:
            bool: True if unregistration succeeded
        """
        if name in self._resources:
            try:
                del self._resources[name]
                logger.info(f"Resource '{name}' unregistered successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to unregister resource '{name}': {e}")
                return False
        else:
            logger.warning(f"Resource '{name}' not found for unregistration")
            return False
    
    def get_resource_status(self) -> Dict[str, Any]:
        """
        Get status of all managed resources.
        
        Returns:
            Dict[str, Any]: Status information for all resources
        """
        status = {
            "initialized": self._initialized,
            "resource_count": len(self._resources),
            "resources": {}
        }
        
        for name, resource in self._resources.items():
            try:
                if hasattr(resource, 'get_health_status'):
                    status["resources"][name] = resource.get_health_status()
                elif hasattr(resource, 'health_check'):
                    status["resources"][name] = {"status": "available", "type": type(resource).__name__}
                else:
                    status["resources"][name] = {"status": "available", "type": type(resource).__name__}
            except Exception as e:
                status["resources"][name] = {"status": "error", "error": str(e)}
        
        return status
    
    @asynccontextmanager
    async def resource_context(self, resource_name: str):
        """
        Context manager for safe resource access.
        
        Args:
            resource_name: Name of the resource to access
            
        Yields:
            The resource instance
        """
        resource = self.get_resource(resource_name)
        if resource is None:
            raise ValueError(f"Resource '{resource_name}' not found")
        
        try:
            yield resource
        finally:
            # Cleanup if resource has cleanup method
            if hasattr(resource, 'cleanup'):
                try:
                    await resource.cleanup()
                except Exception as e:
                    logger.error(f"Error during resource cleanup for '{resource_name}': {e}")
    
    async def cleanup(self) -> None:
        """Cleanup all managed resources."""
        logger.info("Starting ResourceManager cleanup")
        
        for name, resource in self._resources.items():
            try:
                if hasattr(resource, 'cleanup'):
                    await resource.cleanup()
                elif hasattr(resource, 'close'):
                    await resource.close()
                logger.info(f"Resource '{name}' cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up resource '{name}': {e}")
        
        self._resources.clear()
        self._initialized = False
        logger.info("ResourceManager cleanup completed")

# Global resource manager instance
_resource_manager = ResourceManager()

# Convenience functions for backward compatibility
async def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    if not _resource_manager._initialized:
        await _resource_manager.initialize()
    return _resource_manager

def get_resource(resource_name: str) -> Optional[Any]:
    """Get a resource by name from the global manager."""
    return _resource_manager.get_resource(resource_name)

def register_resource(name: str, resource: Any) -> bool:
    """Register a resource with the global manager."""
    return _resource_manager.register_resource(name, resource)

def get_system_resource_status() -> Dict[str, Any]:
    """Get system-wide resource status."""
    return _resource_manager.get_resource_status()

# Export all important classes and functions
__all__ = [
    'ResourceManager',
    'get_resource_manager',
    'get_resource',
    'register_resource', 
    'get_system_resource_status',
]