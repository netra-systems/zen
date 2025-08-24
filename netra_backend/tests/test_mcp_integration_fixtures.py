"""Fixtures Tests - Split from test_mcp_integration.py"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest
from netra_mcp.netra_mcp_server import NetraMCPServer

from netra_backend.app.services.mcp_service import (
    MCPClient,
    MCPService,
    MCPToolExecution,
)

def mock_services():
    """Create mock services for testing"""
    return {
        "agent_service": AsyncMock(),
        "thread_service": AsyncMock(),
        "corpus_service": AsyncMock(),
        "synthetic_data_service": AsyncMock(),
        "security_service": AsyncMock(),
        "supply_catalog_service": AsyncMock(),
        "llm_manager": AsyncMock()
    }

def mcp_server(mock_services):
    """Create MCP server with mock services"""
    server = NetraMCPServer(name="test-server", version="1.0.0")
    server.set_services(**mock_services)
    return server

def mcp_service(mock_services):
    """Create MCP service with mock services"""
    return MCPService(**mock_services)
