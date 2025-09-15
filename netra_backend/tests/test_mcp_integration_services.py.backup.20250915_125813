from datetime import datetime
"""Services Tests - Split from test_mcp_integration.py"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
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

    def test_service_initialization(self, mock_services):
        """Test service initializes correctly"""
        service = MCPService(**mock_services)
        
        assert service.agent_service == mock_services["agent_service"]
        assert service.mcp_server is not None
        assert isinstance(service.active_sessions, dict)
