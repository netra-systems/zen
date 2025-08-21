"""Fixtures Tests - Split from test_mcp_integration.py"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from netra_mcp.netra_mcp_server import NetraMCPServer

# Add project root to path
from netra_backend.app.services.mcp_service import (
    MCPClient,
    MCPService,
    MCPToolExecution,
)

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
