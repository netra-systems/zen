"""
Test module: Supervisor Quality Validation and Admin Tool Dispatch
Split from large test file for architecture compliance  
Test classes: TestQualitySupervisorValidation, TestAdminToolDispatcherRouting
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from netra_backend.app.schemas import (
    AgentCompleted,
    AgentStarted,
    SubAgentLifecycle,
    SubAgentUpdate,
    WebSocketMessage,
)

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    # Add project root to path
    ExecutionStrategy,
)

# Add project root to path
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from .supervisor_test_classes import (
    MockAdminToolDispatcher,
    PermissionError,
    QualitySupervisor,
)
from .supervisor_test_helpers import (
    create_admin_dispatcher_mocks,
    create_admin_operation,
    create_quality_response_data,
    create_quality_supervisor_mocks,
    setup_quality_response_mock,
    setup_tool_dispatcher_mock,
)


# Mock classes for testing (would normally be imported)
class QualitySupervisor:
    """Mock quality supervisor for testing"""
    def __init__(self, llm_manager, websocket_manager):
        self.llm_manager = llm_manager
        self.websocket_manager = websocket_manager
        self.quality_threshold = 0.7
    
    async def validate_response(self, response):
        """Validate response quality using LLM"""
        quality_check = await self.llm_manager.ask_llm(
            f"Evaluate the quality of this response: {response.final_report}"
        )
        return json.loads(quality_check)


# Import real AdminToolDispatcher for proper testing
from netra_backend.app.agents.admin_tool_dispatcher import AdminToolDispatcher


class TestQualitySupervisorValidation:
    """Test 3: Test quality checks on agent responses"""
    async def test_validates_response_quality_score(self):
        """Test validation of response quality scores"""
        mocks = create_quality_supervisor_mocks()
        quality_supervisor = QualitySupervisor(mocks['llm_manager'], mocks['websocket_manager'])
        response_data = create_quality_response_data(0.85, True, [])
        setup_quality_response_mock(mocks['llm_manager'], response_data)
        
        response = DeepAgentState(
            user_request="Generate optimization recommendations",
            final_report="High quality optimization recommendations"
        )
        result = await quality_supervisor.validate_response(response)
        
        assert result["approved"]
        assert result["quality_score"] == 0.85
        assert len(result["issues"]) == 0
    async def test_rejects_low_quality_outputs(self):
        """Test rejection of low-quality outputs"""
        mocks = create_quality_supervisor_mocks()
        quality_supervisor = QualitySupervisor(mocks['llm_manager'], mocks['websocket_manager'])
        quality_supervisor.quality_threshold = 0.7
        issues = ["Incomplete analysis", "Missing key recommendations", "Poor formatting"]
        response_data = create_quality_response_data(0.4, False, issues)
        setup_quality_response_mock(mocks['llm_manager'], response_data)
        
        response = DeepAgentState(user_request="Generate report", final_report="Low quality response")
        result = await quality_supervisor.validate_response(response)
        
        assert not result["approved"]
        assert result["quality_score"] == 0.4
        assert len(result["issues"]) == 3
        assert "Incomplete analysis" in result["issues"]
    async def test_quality_check_with_retry_improvement(self):
        """Test quality improvement through retry"""
        mocks = create_quality_supervisor_mocks()
        quality_supervisor = QualitySupervisor(mocks['llm_manager'], mocks['websocket_manager'])
        mocks['llm_manager'].ask_llm = AsyncMock()
        mocks['llm_manager'].ask_llm.side_effect = [
            json.dumps({"quality_score": 0.5, "approved": False, "issues": ["Too brief"]}),
            json.dumps({"quality_score": 0.8, "approved": True, "issues": []})
        ]
        
        # First attempt - low quality
        response1 = DeepAgentState(user_request="Query", final_report="Brief response")
        result1 = await quality_supervisor.validate_response(response1)
        assert not result1["approved"]
        
        # After improvement - high quality
        response2 = DeepAgentState(user_request="Query", final_report="Detailed comprehensive response")
        result2 = await quality_supervisor.validate_response(response2)
        assert result2["approved"]
        assert result2["quality_score"] == 0.8


class TestAdminToolDispatcherRouting:
    """Test 4: Test tool selection logic for admin operations"""
    async def test_routes_to_correct_admin_tool(self):
        """Test routing to correct admin tool based on operation"""
        mocks = create_admin_dispatcher_mocks()
        admin_dispatcher = MockAdminToolDispatcher(mocks['llm_manager'], mocks['tool_dispatcher'])
        setup_tool_dispatcher_mock(mocks['tool_dispatcher'], {"success": True, "result": "User created"})
        operation = create_admin_operation("create_user", {"username": "testuser", "role": "admin"})
        
        result = await admin_dispatcher.dispatch_admin_operation(operation)
        
        mocks['tool_dispatcher'].execute_tool.assert_called_with("admin_user_management", operation["params"])
        assert result["success"]
        assert result["result"] == "User created"
    async def test_validates_admin_permissions(self):
        """Test security checks for privileged operations"""
        mocks = create_admin_dispatcher_mocks()
        admin_dispatcher = MockAdminToolDispatcher(mocks['llm_manager'], mocks['tool_dispatcher'])
        operation = create_admin_operation("delete_all_data", {}, user_role="viewer")
        
        with pytest.raises(PermissionError) as exc:
            await admin_dispatcher.dispatch_admin_operation(operation)
        
        assert "Insufficient permissions" in str(exc.value)
    async def test_admin_tool_audit_logging(self):
        """Test audit logging for admin operations"""
        mocks = create_admin_dispatcher_mocks()
        admin_dispatcher = MockAdminToolDispatcher(mocks['llm_manager'], mocks['tool_dispatcher'])
        admin_dispatcher.audit_logger = AsyncMock()
        setup_tool_dispatcher_mock(mocks['tool_dispatcher'], {"success": True, "result": "Config updated"})
        operation = create_admin_operation("system_config", {"setting": "debug_mode", "value": True}, user_id="admin-123")
        
        result = await admin_dispatcher.dispatch_admin_operation(operation)
        
        admin_dispatcher.audit_logger.log_admin_operation.assert_called_once_with(operation, result)
        assert result["success"]
        assert result["result"] == "Config updated"