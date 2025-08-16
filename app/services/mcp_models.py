"""
MCP Service Models

Pydantic models for MCP client and tool execution records.
Extracted from main service to maintain 300-line module limit.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field


class MCPClient(BaseModel):
    """MCP Client model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    client_type: str  # claude, cursor, gemini, vscode, etc
    api_key_hash: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_active: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPToolExecution(BaseModel):
    """MCP Tool execution record"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    client_id: Optional[str] = None
    tool_name: str
    input_params: Dict[str, Any]
    output_result: Optional[Dict[str, Any]] = None
    execution_time_ms: int
    status: str  # success, error, timeout
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))