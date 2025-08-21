"""MCP Client database models.

Defines models for external MCP server configurations and execution tracking.
Focused module adhering to modular architecture and single responsibility.

Should this be also or primarily in clickhouse?
"""

import os
from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, JSON, Integer
)
from netra_backend.app.db.base import Base
from datetime import datetime, timezone


class MCPExternalServer(Base):
    """Model for external MCP server configurations."""
    __tablename__ = "mcp_external_servers"
    
    id = Column(String, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(Text, nullable=False)
    transport = Column(String(20), nullable=False)
    auth_type = Column(String(50), nullable=True)
    credentials = Column(JSON, nullable=True)  # Encrypted in practice
    capabilities = Column(JSON, nullable=True)
    metadata_ = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="registered")
    last_health_check = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class MCPToolExecution(Base):
    """Model for tracking MCP tool executions."""
    __tablename__ = "mcp_tool_executions"
    
    id = Column(String, primary_key=True)
    server_name = Column(String(255), nullable=False)
    tool_name = Column(String(255), nullable=False)
    arguments = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class MCPResourceAccess(Base):
    """Model for tracking MCP resource access."""
    __tablename__ = "mcp_resource_access"
    
    id = Column(String, primary_key=True)
    server_name = Column(String(255), nullable=False)
    resource_uri = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)
    status = Column(String(20), nullable=False)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))