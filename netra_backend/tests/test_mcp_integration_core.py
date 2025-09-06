"""Core Tests - Split from test_mcp_integration.py"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import json
from datetime import UTC, datetime, timedelta

import pytest
from netra_backend.app.netra_mcp.netra_mcp_server import NetraMCPServer

from netra_backend.app.services.mcp_service import (
    MCPClient,
    MCPService,
    MCPToolExecution,
)

class TestSyntaxFix:
    """Test class for orphaned methods"""

    def test_server_initialization(self):
        """Test server initializes correctly"""
        server = NetraMCPServer(name="test", version="1.0.0")
        assert server.mcp is not None
        assert server.mcp.name == "test"
        assert server.mcp.version == "1.0.0"

    def test_service_injection(self, mock_services):
        """Test service injection works"""
        server = NetraMCPServer()
        server.set_services(**mock_services)
        
        assert server.agent_service == mock_services["agent_service"]
        assert server.thread_service == mock_services["thread_service"]
        assert server.corpus_service == mock_services["corpus_service"]

    def test_service_initialization(self, mock_services):
        """Test service initializes correctly"""
        service = MCPService(**mock_services)
        
        assert service.agent_service == mock_services["agent_service"]
        assert service.mcp_server is not None
        assert isinstance(service.active_sessions, dict)

    def test_mcp_server_creation(self):
        """Test basic server creation"""
        server = NetraMCPServer()
        assert server is not None
        assert server.mcp is not None

    def test_mcp_service_creation(self, mock_services):
        """Test basic service creation"""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.mcp_service.MCPClientRepository'), \
             patch('app.services.mcp_service.MCPToolExecutionRepository'):
            service = MCPService(**mock_services)
            assert service is not None
            assert service.mcp_server is not None

    def test_server_initialization(self):
        """Test server initializes correctly"""
        server = NetraMCPServer(name="test", version="1.0.0")
        assert server.mcp is not None
        assert server.mcp.name == "test"
        assert server.mcp.version == "1.0.0"

    def test_service_injection(self, mock_services):
        """Test service injection works"""
        server = NetraMCPServer()
        server.set_services(**mock_services)
        
        assert server.agent_service == mock_services["agent_service"]
        assert server.thread_service == mock_services["thread_service"]
        assert server.corpus_service == mock_services["corpus_service"]

    def test_mcp_server_creation(self):
        """Test basic server creation"""
        server = NetraMCPServer()
        assert server is not None
        assert server.mcp is not None

    def test_mcp_service_creation(self, mock_services):
        """Test basic service creation"""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.mcp_service.MCPClientRepository'), \
             patch('app.services.mcp_service.MCPToolExecutionRepository'):
            service = MCPService(**mock_services)
            assert service is not None
            assert service.mcp_server is not None
