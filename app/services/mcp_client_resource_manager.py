"""MCP Client Resource Manager.

Handles resource discovery and fetching from external MCP servers.
Implements real MCP protocol for production use.
Modular component extracted to maintain 450-line limit compliance.
"""

from typing import Dict, Any, List, Optional
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
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
        """Discover resources from MCP server using real protocol."""
        try:
            session = await self._get_server_session(server_name)
            resources_result = await session.list_resources()
            
            return [
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description or "",
                    "mime_type": resource.mimeType or "text/plain"
                }
                for resource in resources_result.resources
            ]
        except Exception as e:
            logger.error(f"Resource discovery failed for {server_name}: {e}")
            raise ServiceError(f"Resource discovery failed: {str(e)}")
    
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
        """Fetch resource content from MCP server using real protocol."""
        try:
            session = await self._get_server_session(server_name)
            resource_result = await session.read_resource(uri)
            
            if resource_result.contents:
                # Handle different content types
                content_item = resource_result.contents[0]
                if hasattr(content_item, 'text'):
                    return content_item.text
                elif hasattr(content_item, 'blob'):
                    return content_item.blob.decode('utf-8', errors='ignore')
            return ""
        except Exception as e:
            logger.error(f"Resource fetch failed for {uri} from {server_name}: {e}")
            raise ServiceError(f"Resource fetch failed: {str(e)}")
    
    def clear_resource_cache(self, server_name: str = None):
        """Clear resource cache for specific server or all."""
        if server_name:
            keys_to_remove = [k for k in self.cache.keys() 
                            if k.startswith(f"{server_name}:resources")]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()
    
    async def _get_server_session(self, server_name: str) -> ClientSession:
        """Get or create MCP client session for server."""
        cache_key = f"{server_name}:session"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # For now, assume stdio transport - this should be configurable
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_server", server_name]
        )
        
        session = await stdio_client(server_params)
        self.cache[cache_key] = session
        return session