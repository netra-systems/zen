"""MCP Client Schemas and Data Models.

Pydantic models for MCP client operations, server configurations, and responses.
Adheres to single source of truth and strong typing principles.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from netra_backend.app.schemas.core_enums import (
    MCPAuthType,
    MCPServerStatus,
    MCPToolExecutionStatus,
    MCPTransport,
)


class MCPAuthConfig(BaseModel):
    """MCP server authentication configuration."""
    auth_type: MCPAuthType
    api_key: Optional[str] = None
    oauth_config: Optional[Dict[str, Any]] = None
    environment_vars: Optional[Dict[str, str]] = None
    
    model_config = ConfigDict(use_enum_values=True)


class MCPRetryConfig(BaseModel):
    """MCP retry configuration."""
    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay_ms: int = Field(default=1000, ge=100, le=10000)
    max_delay_ms: int = Field(default=30000, ge=1000, le=60000)
    exponential_base: float = Field(default=2.0, ge=1.1, le=10.0)


class MCPServerConfig(BaseModel):
    """MCP server configuration."""
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    transport: MCPTransport
    auth: Optional[MCPAuthConfig] = None
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    retry_config: Optional[MCPRetryConfig] = None
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(use_enum_values=True)


class MCPServerInfo(BaseModel):
    """MCP server information response."""
    id: str
    name: str
    url: str
    transport: MCPTransport
    status: MCPServerStatus
    capabilities: Optional[Dict[str, Any]] = None
    last_health_check: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(use_enum_values=True)


class MCPConnection(BaseModel):
    """MCP connection information."""
    id: str
    server_name: str
    transport: MCPTransport
    session_id: str
    capabilities: Dict[str, Any]
    status: MCPServerStatus
    created_at: datetime
    
    model_config = ConfigDict(use_enum_values=True)


class MCPTool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPToolResult(BaseModel):
    """MCP tool execution result."""
    tool_name: str
    server_name: str
    content: List[Dict[str, Any]]
    is_error: bool = False
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None


class MCPResource(BaseModel):
    """MCP resource definition."""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Request/Response Models for API endpoints

class RegisterServerRequest(BaseModel):
    """Request to register a new MCP server."""
    name: str = Field(..., min_length=1, max_length=255)
    config: MCPServerConfig


class RegisterServerResponse(BaseModel):
    """Response for server registration."""
    success: bool
    server_id: str
    message: str


class ConnectServerRequest(BaseModel):
    """Request to connect to an MCP server."""
    server_name: str


class ConnectServerResponse(BaseModel):
    """Response for server connection."""
    success: bool
    connection: Optional[MCPConnection] = None
    message: str


class ListServersResponse(BaseModel):
    """Response for listing servers."""
    servers: List[MCPServerInfo]


class DiscoverToolsResponse(BaseModel):
    """Response for tool discovery."""
    tools: List[MCPTool]


class ExecuteToolRequest(BaseModel):
    """Request to execute a tool."""
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]


class ExecuteToolResponse(BaseModel):
    """Response for tool execution."""
    success: bool
    result: Optional[MCPToolResult] = None
    message: str


class GetResourcesResponse(BaseModel):
    """Response for getting resources."""
    resources: List[MCPResource]


class FetchResourceRequest(BaseModel):
    """Request to fetch a resource."""
    server_name: str
    uri: str


class FetchResourceResponse(BaseModel):
    """Response for fetching a resource."""
    success: bool
    resource: Optional[MCPResource] = None
    message: str


class ClearCacheRequest(BaseModel):
    """Request to clear cache."""
    server_name: Optional[str] = None
    cache_type: Optional[str] = None


class ClearCacheResponse(BaseModel):
    """Response for cache clearing."""
    success: bool
    message: str
    cleared_entries: int = 0