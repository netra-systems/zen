"""Fixtures Tests - Split from test_mcp_integration.py"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
from netra_mcp.netra_mcp_server import NetraMCPServer

# Add project root to path

from netra_backend.app.services.mcp_service import MCPService, MCPClient, MCPToolExecution
from datetime import timedelta

# Add project root to path

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
