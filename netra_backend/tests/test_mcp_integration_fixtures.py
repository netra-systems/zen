"""Fixtures Tests - Split from test_mcp_integration.py"""

import sys
from pathlib import Path
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import json
from datetime import UTC, datetime, timedelta

import pytest
from netra_backend.app.netra_mcp.netra_mcp_server import NetraMCPServer

from netra_backend.app.services.mcp_service import (
    MCPClient,
    MCPService,
    MCPToolExecution)

def mock_services():
    """Create mock services for testing"""
    return {
        # Mock: Generic component isolation for controlled unit testing
        "agent_service": AsyncNone  # TODO: Use real service instance,
        # Mock: Generic component isolation for controlled unit testing
        "thread_service": AsyncNone  # TODO: Use real service instance,
        # Mock: Generic component isolation for controlled unit testing
        "corpus_service": AsyncNone  # TODO: Use real service instance,
        # Mock: Generic component isolation for controlled unit testing
        "synthetic_data_service": AsyncNone  # TODO: Use real service instance,
        # Mock: Security component isolation for controlled auth testing
        "security_service": AsyncNone  # TODO: Use real service instance,
        # Mock: Generic component isolation for controlled unit testing
        "supply_catalog_service": AsyncNone  # TODO: Use real service instance,
        # Mock: LLM provider isolation to prevent external API usage and costs
        "llm_manager": AsyncNone  # TODO: Use real service instance
    }

def mcp_server(mock_services):
    """Create MCP server with mock services"""
    pass
    server = NetraMCPServer(name="test-server", version="1.0.0")
    server.set_services(**mock_services)
    return server

def mcp_service(mock_services):
    """Create MCP service with mock services"""
    return MCPService(**mock_services)

    pass