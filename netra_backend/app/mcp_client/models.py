"""MCP Client Pydantic Models - Type Safety for External MCP Integration.

Provides strongly typed models for MCP client operations following Netra's
strict type safety requirements. All models use Pydantic for validation
and serialization with comprehensive field constraints.

Models:
- MCPServerConfig: External server configuration
- MCPConnection: Active connection state  
- MCPTool: External tool definitions
- MCPToolResult: Tool execution results
- MCPResource: External resource data
- Supporting enums and configurations

Line count: <300 lines (architectural requirement)
Function limit:  <= 8 lines per function (architectural requirement)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ConnectionStatus(str, Enum):
    """Connection status enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class MCPTransport(str, Enum):
    """MCP transport protocol enumeration."""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class AuthType(str, Enum):
    """Authentication type enumeration."""
    NONE = "none"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    ENVIRONMENT = "environment"


class MCPRetryConfig(BaseModel):
    """Retry configuration for MCP operations."""
    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_delay_ms: int = Field(default=1000, ge=100, le=10000)
    max_delay_ms: int = Field(default=30000, ge=1000, le=60000)
    exponential_base: float = Field(default=2.0, ge=1.0, le=5.0)


class MCPAuthConfig(BaseModel):
    """Authentication configuration for MCP servers."""
    auth_type: AuthType = Field(default=AuthType.NONE)
    api_key: Optional[str] = Field(default=None, min_length=1)
    oauth_client_id: Optional[str] = Field(default=None, min_length=1)
    oauth_client_secret: Optional[str] = Field(default=None, min_length=1)
    oauth_token_url: Optional[str] = Field(default=None, min_length=1)
    environment_vars: Optional[Dict[str, str]] = Field(default_factory=dict)
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v, info):
        """Validate API key when auth type is API_KEY."""
        if hasattr(info, 'data') and info.data.get('auth_type') == AuthType.API_KEY and not v:
            raise ValueError("API key required for API_KEY auth type")
        return v


class MCPServerConfig(BaseModel):
    """Configuration for external MCP server connection."""
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=2048)
    transport: MCPTransport = Field(...)
    auth: Optional[MCPAuthConfig] = Field(default=None)
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    retry_config: Optional[MCPRetryConfig] = Field(default_factory=MCPRetryConfig)
    environment: Optional[Dict[str, str]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate server name format."""
        if not v.replace('_', '').replace('-', '').replace('.', '').isalnum():
            raise ValueError("Server name must be alphanumeric with _, -, . allowed")
        return v.lower()
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v, info):
        """Validate URL format based on transport type."""
        if hasattr(info, 'data'):
            transport = info.data.get('transport')
            if transport == MCPTransport.HTTP and not v.startswith(('http://', 'https://')):
                raise ValueError("HTTP transport requires http:// or https:// URL")
            if transport == MCPTransport.WEBSOCKET and not v.startswith(('ws://', 'wss://')):
                raise ValueError("WebSocket transport requires ws:// or wss:// URL")
        return v


class MCPConnection(BaseModel):
    """Active MCP server connection state."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    server_name: str = Field(..., min_length=1)
    transport: MCPTransport = Field(...)
    session_id: Optional[str] = Field(default=None)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    status: ConnectionStatus = Field(default=ConnectionStatus.DISCONNECTED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = Field(default=None)
    error_count: int = Field(default=0, ge=0)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MCPTool(BaseModel):
    """External MCP tool definition."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=2048)
    server_name: str = Field(..., min_length=1)
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for inputs")
    output_schema: Optional[Dict[str, Any]] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    cached_at: Optional[datetime] = Field(default=None)
    
    @field_validator('name')
    @classmethod
    def validate_tool_name(cls, v):
        """Validate tool name format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Tool name must be alphanumeric with _ and - allowed")
        return v.lower()
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MCPToolResult(BaseModel):
    """Result from MCP tool execution."""
    tool_name: str = Field(..., min_length=1)
    server_name: str = Field(..., min_length=1)
    content: List[Dict[str, Any]] = Field(default_factory=list)
    is_error: bool = Field(default=False)
    error_message: Optional[str] = Field(default=None)
    execution_time_ms: int = Field(..., ge=0)
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    cached: bool = Field(default=False)
    
    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v, info):
        """Validate error message when is_error is True."""
        if hasattr(info, 'data') and info.data.get('is_error', False) and not v:
            raise ValueError("Error message required when is_error is True")
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MCPResource(BaseModel):
    """External MCP resource data."""
    uri: str = Field(..., min_length=1, max_length=2048)
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1024)
    mime_type: Optional[str] = Field(default=None, max_length=100)
    content: Optional[Union[str, bytes]] = Field(default=None)
    server_name: str = Field(..., min_length=1)
    size_bytes: Optional[int] = Field(default=None, ge=0)
    retrieved_at: Optional[datetime] = Field(default=None)
    cached: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('uri')
    @classmethod
    def validate_uri(cls, v):
        """Validate URI format."""
        if not v.startswith(('http://', 'https://', 'file://', 'mcp://')):
            raise ValueError("URI must start with supported scheme")
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MCPServerInfo(BaseModel):
    """External MCP server information summary."""
    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    transport: MCPTransport = Field(...)
    status: ConnectionStatus = Field(...)
    tool_count: int = Field(default=0, ge=0)
    resource_count: int = Field(default=0, ge=0)
    last_health_check: Optional[datetime] = Field(default=None)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MCPOperationContext(BaseModel):
    """Context for MCP operations with tracing."""
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    server_name: str = Field(..., min_length=1)
    operation_type: str = Field(..., min_length=1)
    user_id: Optional[str] = Field(default=None)
    trace_id: Optional[str] = Field(default=None)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    timeout_ms: int = Field(default=30000, ge=1000)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


__all__ = [
    "ConnectionStatus",
    "MCPTransport", 
    "AuthType",
    "MCPRetryConfig",
    "MCPAuthConfig",
    "MCPServerConfig",
    "MCPConnection",
    "MCPTool",
    "MCPToolResult", 
    "MCPResource",
    "MCPServerInfo",
    "MCPOperationContext",
]