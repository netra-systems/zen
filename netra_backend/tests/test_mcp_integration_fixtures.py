"""Fixtures Tests - Split from test_mcp_integration.py"""

import sys
from pathlib import Path
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import json
from datetime import UTC, datetime, timedelta

import pytest
from netra_backend.app.netra_mcp.netra_mcp_server import NetraMCPServer

# REMOVED_SYNTAX_ERROR: from netra_backend.app.services.mcp_service import ( )
MCPClient,
MCPService,
MCPToolExecution

# REMOVED_SYNTAX_ERROR: def mock_services():
    # REMOVED_SYNTAX_ERROR: """Create mock services for testing"""
    # REMOVED_SYNTAX_ERROR: return { )
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: "agent_service": AsyncNone  # TODO: Use real service instance,
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: "thread_service": AsyncNone  # TODO: Use real service instance,
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: "corpus_service": AsyncNone  # TODO: Use real service instance,
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: "synthetic_data_service": AsyncNone  # TODO: Use real service instance,
    # Mock: Security component isolation for controlled auth testing
    # REMOVED_SYNTAX_ERROR: "security_service": AsyncNone  # TODO: Use real service instance,
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: "supply_catalog_service": AsyncNone  # TODO: Use real service instance,
    # Mock: LLM provider isolation to prevent external API usage and costs
    # REMOVED_SYNTAX_ERROR: "llm_manager": AsyncNone  # TODO: Use real service instance
    

# REMOVED_SYNTAX_ERROR: def mcp_server(mock_services):
    # REMOVED_SYNTAX_ERROR: """Create MCP server with mock services"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: server = NetraMCPServer(name="test-server", version="1.0.0")
    # REMOVED_SYNTAX_ERROR: server.set_services(**mock_services)
    # REMOVED_SYNTAX_ERROR: return server

# REMOVED_SYNTAX_ERROR: def mcp_service(mock_services):
    # REMOVED_SYNTAX_ERROR: """Create MCP service with mock services"""
    # REMOVED_SYNTAX_ERROR: return MCPService(**mock_services)

    # REMOVED_SYNTAX_ERROR: pass