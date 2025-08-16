"""MCP Client Resource Manager.

Handles resource discovery and fetching from external MCP servers.
Modular component extracted to maintain 300-line limit compliance.
"""

from typing import Dict, Any, List

from app.services.database.mcp_client_repository import MCPResourceAccessRepository
from app.core.exceptions_service import ServiceError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MCPResourceManager:
    """Handles resource discovery and fetching for MCP servers."""
    
    def __init__(self):
        self.resource_repo = MCPResourceAccessRepository()
        self.cache: Dict[str, Any] = {}
    
    async def get_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """Get resources from an MCP server."""
        try:
            cache_key = f"{server_name}:resources"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            resources = await self._discover_resources(server_name)
            self.cache[cache_key] = resources
            return resources
        except Exception as e:
            logger.error(f"Failed to get resources from {server_name}: {e}")
            raise ServiceError(f"Resource discovery failed: {str(e)}")
    
    async def _discover_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """Mock resource discovery."""
        return [
            {
                "uri": f"{server_name}://readme/overview",
                "name": "Project Overview",
                "description": "Main project documentation",
                "mime_type": "text/markdown"
            },
            {
                "uri": f"{server_name}://api/reference",
                "name": "API Reference",
                "description": "Complete API documentation",
                "mime_type": "text/markdown"
            }
        ]
    
    async def fetch_resource(self, db, server_name: str, uri: str) -> Dict[str, Any]:
        """Fetch a specific resource from an MCP server."""
        try:
            await self.resource_repo.create_access_record(db, server_name, uri)
            
            content = await self._fetch_resource_content(server_name, uri)
            return {
                "uri": uri,
                "name": f"Resource from {server_name}",
                "content": content,
                "mime_type": "text/plain"
            }
        except Exception as e:
            logger.error(f"Failed to fetch resource {uri} from {server_name}: {e}")
            raise ServiceError(f"Resource fetch failed: {str(e)}")
    
    async def _fetch_resource_content(self, server_name: str, uri: str) -> str:
        """Mock resource content fetching."""
        return f"Mock content for resource {uri} from {server_name}"
    
    def clear_resource_cache(self, server_name: str = None):
        """Clear resource cache for specific server or all."""
        if server_name:
            keys_to_remove = [k for k in self.cache.keys() 
                            if k.startswith(f"{server_name}:resources")]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()