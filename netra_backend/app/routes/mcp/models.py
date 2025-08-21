"""
MCP API Request Models

Pydantic models for MCP API requests and responses.
Maintains type safety and validation under 450-line limit.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MCPClientCreateRequest(BaseModel):
    """Request model for creating MCP client"""
    name: str
    client_type: str
    api_key: Optional[str] = None
    permissions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPSessionCreateRequest(BaseModel):
    """Request model for creating MCP session"""
    client_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPToolCallRequest(BaseModel):
    """Request model for tool execution"""
    tool_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = None


class MCPResourceReadRequest(BaseModel):
    """Request model for resource reading"""
    uri: str
    session_id: Optional[str] = None


class MCPPromptGetRequest(BaseModel):
    """Request model for prompt retrieval"""
    prompt_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = None