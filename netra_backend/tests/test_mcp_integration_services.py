"""Services Tests - Split from test_mcp_integration.py"""

# Add project root to path
import sys
from pathlib import Path

from ..test_utils import setup_test_path

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


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def test_service_initialization(self, mock_services):
        """Test service initializes correctly"""
        service = MCPService(**mock_services)
        
        assert service.agent_service == mock_services["agent_service"]
        assert service.mcp_server is not None
        assert isinstance(service.active_sessions, dict)
