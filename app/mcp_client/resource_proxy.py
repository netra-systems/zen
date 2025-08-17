"""
MCP Resource Proxy Module

Handles resource discovery and fetching from external MCP servers.
Compliant with 300-line limit and 8-line function requirements.
"""

import json
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.core.exceptions import NetraException, ErrorCode, ErrorSeverity
from app.core.async_retry_logic import _retry_with_backoff
from app.mcp_client.models import MCPResource, MCPResourceList, MCPConnection


class MCPResourceProxy:
    """Proxy for accessing resources from external MCP servers."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self._resource_cache: Dict[str, List[MCPResource]] = {}
        self._content_cache: Dict[str, MCPResource] = {}
    
    async def discover_resources(self, connection: MCPConnection) -> List[MCPResource]:
        """Discover available resources from MCP server."""
        cache_key = f"{connection.server_name}:resources"
        if cache_key in self._resource_cache:
            return self._resource_cache[cache_key]
        
        return await self._discover_and_cache_resources(connection, cache_key)
    
    async def fetch_resource(self, connection: MCPConnection, uri: str) -> MCPResource:
        """Fetch specific resource content from MCP server."""
        if not self.validate_uri(uri):
            raise NetraException(f"Invalid resource URI: {uri}", ErrorCode.VALIDATION_ERROR)
        
        cache_key = f"{connection.server_name}:{uri}"
        if cache_key in self._content_cache:
            return self._content_cache[cache_key]
        
        return await self._fetch_and_cache_resource(connection, uri, cache_key)
    
    def validate_uri(self, uri: str) -> bool:
        """Validate resource URI format."""
        if not uri or not isinstance(uri, str):
            return False
        try:
            return self._is_valid_parsed_uri(urlparse(uri))
        except Exception:
            return False
    
    def parse_content(self, content: str, mime_type: Optional[str] = None) -> Any:
        """Parse resource content based on MIME type."""
        if not content:
            return None
        
        parser = self._get_content_parser(mime_type)
        return parser(content)
    
    async def _discover_and_cache_resources(self, connection: MCPConnection, cache_key: str) -> List[MCPResource]:
        """Discover resources and cache them."""
        resources = await self._fetch_resources_from_server(connection)
        self._resource_cache[cache_key] = resources
        return resources
    
    async def _fetch_and_cache_resource(self, connection: MCPConnection, uri: str, cache_key: str) -> MCPResource:
        \"\"\"Fetch resource and cache it.\"\"\"
        resource = await self._fetch_resource_with_retry(connection, uri)
        self._content_cache[cache_key] = resource
        return resource
    
    def _is_valid_parsed_uri(self, parsed_uri) -> bool:
        \"\"\"Check if parsed URI is valid.\"\"\"
        return bool(parsed_uri.scheme and (parsed_uri.netloc or parsed_uri.path))
    
    def _get_mime_type_parsers(self) -> Dict[str, Any]:
        \"\"\"Get MIME type to parser mapping.\"\"\"
        return {
            \"application/json\": self._parse_json_content,
            \"text/plain\": self._parse_text_content,
            \"text/markdown\": self._parse_text_content,
            \"text/html\": self._parse_text_content
        }
    
    async def _fetch_resources_from_server(self, connection: MCPConnection) -> List[MCPResource]:
        """Fetch resource list from MCP server."""
        request = self._build_list_resources_request()
        response = await self._send_request(connection, request)
        return self._parse_resources_response(response)
    
    async def _fetch_resource_with_retry(self, connection: MCPConnection, uri: str) -> MCPResource:
        """Fetch resource content with retry logic."""
        request = self._build_read_resource_request(uri)
        response = await _retry_with_backoff(
            self._send_request, self.max_retries, self.base_delay,
            self.backoff_factor, (Exception,), connection, request
        )
        return self._parse_resource_content_response(response, uri)
    
    def _get_content_parser(self, mime_type: Optional[str]):
        """Get appropriate content parser based on MIME type."""
        parsers = self._get_mime_type_parsers()
        return parsers.get(mime_type, self._parse_text_content)
    
    def _parse_json_content(self, content: str) -> Any:
        """Parse JSON content."""
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise NetraException(f"Invalid JSON content: {e}", ErrorCode.DATA_PARSING_ERROR)
    
    def _parse_text_content(self, content: str) -> str:
        """Parse plain text content."""
        return content.strip()
    
    def _build_list_resources_request(self) -> Dict[str, Any]:
        """Build JSON-RPC request for listing resources."""
        return {
            "jsonrpc": "2.0",
            "id": self._generate_request_id(),
            "method": "resources/list"
        }
    
    def _build_read_resource_request(self, uri: str) -> Dict[str, Any]:
        """Build JSON-RPC request for reading resource."""
        return {
            "jsonrpc": "2.0",
            "id": self._generate_request_id(),
            "method": "resources/read",
            "params": {"uri": uri}
        }
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return hashlib.md5(f"{datetime.now().isoformat()}".encode()).hexdigest()[:8]
    
    def _parse_resources_response(self, response: Dict[str, Any]) -> List[MCPResource]:
        """Parse resources list response."""
        result = response.get("result", {})
        resources_data = result.get("resources", [])
        return [self._create_resource_from_data(res_data) for res_data in resources_data]
    
    def _create_resource_from_data(self, resource_data: Dict[str, Any]) -> MCPResource:
        """Create MCPResource from server response data."""
        return MCPResource(
            uri=resource_data["uri"], name=resource_data.get("name"),
            description=resource_data.get("description"), mime_type=resource_data.get("mimeType"),
            annotations=resource_data.get("annotations"), metadata=resource_data.get("metadata")
        )
    
    def _parse_resource_content_response(self, response: Dict[str, Any], uri: str) -> MCPResource:
        """Parse resource content response."""
        result = response.get("result", {})
        contents = result.get("contents", [])
        if not contents:
            raise NetraException("No content in resource response", ErrorCode.DATA_PARSING_ERROR)
        return self._create_resource_with_content(contents[0], uri)
    
    def _create_resource_with_content(self, content_data: Dict[str, Any], uri: str) -> MCPResource:
        """Create MCPResource with content from response data."""
        return MCPResource(
            uri=uri, name=content_data.get("name"), description=content_data.get("description"),
            mime_type=content_data.get("mimeType"), annotations=content_data.get("annotations"),
            content=content_data.get("text") or content_data.get("blob"),
            metadata=content_data.get("metadata")
        )
    
    async def _send_request(self, connection: MCPConnection, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server."""
        # This would be implemented by the transport layer
        # For now, raise an exception indicating this needs transport implementation
        raise NotImplementedError("Transport layer integration required")
    
    def clear_cache(self, server_name: Optional[str] = None) -> None:
        """Clear resource and content caches."""
        if server_name:
            keys_to_remove = [k for k in self._resource_cache.keys() if k.startswith(f"{server_name}:")]
            for key in keys_to_remove:
                self._resource_cache.pop(key, None)
            
            content_keys_to_remove = [k for k in self._content_cache.keys() if k.startswith(f"{server_name}:")]
            for key in content_keys_to_remove:
                self._content_cache.pop(key, None)
        else:
            self._resource_cache.clear()
            self._content_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "resource_cache_size": len(self._resource_cache),
            "content_cache_size": len(self._content_cache),
            "total_cached_resources": sum(len(resources) for resources in self._resource_cache.values())
        }
    
    async def refresh_resources(self, connection: MCPConnection) -> List[MCPResource]:
        """Force refresh of resources from server."""
        cache_key = f"{connection.server_name}:resources"
        self._resource_cache.pop(cache_key, None)
        return await self.discover_resources(connection)
    
    def is_resource_cached(self, server_name: str, uri: str) -> bool:
        """Check if resource content is cached."""
        cache_key = f"{server_name}:{uri}"
        return cache_key in self._content_cache
    
    def get_cached_resource(self, server_name: str, uri: str) -> Optional[MCPResource]:
        """Get cached resource content."""
        cache_key = f"{server_name}:{uri}"
        return self._content_cache.get(cache_key)
    
    async def batch_fetch_resources(self, connection: MCPConnection, uris: List[str]) -> List[MCPResource]:
        """Fetch multiple resources in batch."""
        tasks = [self.fetch_resource(connection, uri) for uri in uris]
        return await asyncio.gather(*tasks, return_exceptions=True)