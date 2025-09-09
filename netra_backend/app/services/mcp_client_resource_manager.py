"""MCP Client Resource Manager.

Manages MCP server resources including discovery, caching, and retrieval.
Follows SSOT principles by extending existing resource management patterns.
Modular component extracted to maintain 450-line limit compliance.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.database import get_db
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.mcp_client import MCPResource
from netra_backend.app.services.database.mcp_client_repository import (
    MCPClientRepository,
)

logger = central_logger.get_logger(__name__)


class MCPResourceManager:
    """Manages MCP server resources with caching and database persistence."""
    
    def __init__(self):
        """Initialize MCP resource manager."""
        self.server_repo = MCPClientRepository()
        self.resource_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.resource_content_cache: Dict[str, Dict[str, Any]] = {}
    
    async def get_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """
        Get all available resources from an MCP server.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            List of resource definitions
        """
        try:
            cache_key = f"{server_name}:resources"
            if cache_key in self.resource_cache:
                logger.debug(f"Returning cached resources for {server_name}")
                return self.resource_cache[cache_key]
            
            # Discover resources from MCP server
            resources = await self._discover_resources(server_name)
            self.resource_cache[cache_key] = resources
            
            logger.info(f"Discovered {len(resources)} resources from {server_name}")
            return resources
        except Exception as e:
            logger.error(f"Failed to get resources from {server_name}: {e}")
            raise ServiceError(f"Resource discovery failed: {str(e)}")
    
    async def fetch_resource(self, db: Any, server_name: str, uri: str) -> Dict[str, Any]:
        """
        Fetch a specific resource from an MCP server.
        
        Args:
            db: Database session
            server_name: Name of the MCP server
            uri: Resource URI to fetch
            
        Returns:
            Resource data with content
        """
        try:
            cache_key = f"{server_name}:{uri}"
            if cache_key in self.resource_content_cache:
                logger.debug(f"Returning cached resource content for {uri}")
                return self.resource_content_cache[cache_key]
            
            # Validate server exists
            server = await self.server_repo.get_server_by_name(db, server_name)
            if not server:
                raise ServiceError(f"Server '{server_name}' not found")
            
            # Fetch resource content from MCP server
            resource_data = await self._fetch_resource_content(server_name, uri)
            self.resource_content_cache[cache_key] = resource_data
            
            logger.info(f"Fetched resource {uri} from {server_name}")
            return resource_data
        except Exception as e:
            logger.error(f"Failed to fetch resource {uri} from {server_name}: {e}")
            raise ServiceError(f"Resource fetch failed: {str(e)}")
    
    def clear_resource_cache(self, server_name: Optional[str] = None):
        """
        Clear resource cache for specific server or all servers.
        
        Args:
            server_name: Specific server to clear cache for, or None for all
        """
        try:
            if server_name:
                # Clear cache entries for specific server
                keys_to_remove = [
                    key for key in self.resource_cache.keys() 
                    if key.startswith(f"{server_name}:")
                ]
                for key in keys_to_remove:
                    del self.resource_cache[key]
                
                content_keys_to_remove = [
                    key for key in self.resource_content_cache.keys()
                    if key.startswith(f"{server_name}:")
                ]
                for key in content_keys_to_remove:
                    del self.resource_content_cache[key]
                
                logger.info(f"Cleared resource cache for server: {server_name}")
            else:
                # Clear all cache
                self.resource_cache.clear()
                self.resource_content_cache.clear()
                logger.info("Cleared all resource cache")
        except Exception as e:
            logger.error(f"Failed to clear resource cache: {e}")
            raise ServiceError(f"Cache clear failed: {str(e)}")
    
    async def _discover_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """
        Discover resources from MCP server.
        
        TODO: Replace with real MCP server resource discovery implementation.
        For now, returns mock resources based on server name.
        """
        # Mock resource discovery - would call actual MCP server
        await asyncio.sleep(0.1)  # Simulate network call
        
        return [
            {
                "uri": f"file:///{server_name}/documents/readme.txt",
                "name": f"{server_name}_readme",
                "description": f"README file from {server_name}",
                "mime_type": "text/plain",
                "metadata": {
                    "size": 1024,
                    "last_modified": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "uri": f"file:///{server_name}/config/settings.json",
                "name": f"{server_name}_settings",
                "description": f"Configuration settings from {server_name}",
                "mime_type": "application/json",
                "metadata": {
                    "size": 512,
                    "last_modified": datetime.now(timezone.utc).isoformat()
                }
            }
        ]
    
    async def _fetch_resource_content(self, server_name: str, uri: str) -> Dict[str, Any]:
        """
        Fetch actual resource content from MCP server.
        
        TODO: Replace with real MCP server resource fetch implementation.
        For now, returns mock content based on URI.
        """
        # Mock resource fetch - would call actual MCP server
        await asyncio.sleep(0.05)  # Simulate network call
        
        # Extract resource name from URI
        resource_name = uri.split("/")[-1]
        
        if resource_name.endswith('.txt'):
            content = f"This is mock content for {resource_name} from {server_name}"
            mime_type = "text/plain"
        elif resource_name.endswith('.json'):
            content = f'{{"mock": true, "server": "{server_name}", "resource": "{resource_name}"}}'
            mime_type = "application/json"
        else:
            content = f"Mock binary content for {resource_name}"
            mime_type = "application/octet-stream"
        
        return {
            "uri": uri,
            "name": resource_name.split('.')[0],
            "description": f"Resource {resource_name} from {server_name}",
            "mime_type": mime_type,
            "content": content,
            "metadata": {
                "server_name": server_name,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "size": len(content)
            }
        }
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get status of resource caches.
        
        Returns:
            Dict with cache statistics
        """
        return {
            "resource_cache_size": len(self.resource_cache),
            "resource_content_cache_size": len(self.resource_content_cache),
            "cached_servers": list(set(
                key.split(':')[0] 
                for key in list(self.resource_cache.keys()) + list(self.resource_content_cache.keys())
            )),
            "total_cached_resources": sum(len(resources) for resources in self.resource_cache.values()),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }