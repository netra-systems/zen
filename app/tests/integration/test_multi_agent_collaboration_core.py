"""Core Tests - Split from test_multi_agent_collaboration.py

        BVJ: Validates the core multi-agent architecture that enables Netra Apex to deliver
        comprehensive AI optimization insights. Proper orchestration reduces optimization
        delivery time by 40% and ensures consistent results across all customer tiers.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent
from app.agents.state import DeepAgentState
from app.schemas.registry import (
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.agents.tool_dispatcher import ToolDispatcher
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile

    def mock_agent_infrastructure(self):
        """Setup mock infrastructure for agent testing"""
        return self._init_mock_infrastructure()

    def test_optimization_scenario(self):
        """Setup test scenario for AI optimization workflow"""
        return self._create_optimization_scenario()

    def _init_mock_infrastructure(self):
        """Initialize mock infrastructure for agent coordination"""
        # Mock LLM Manager with realistic responses
        llm_manager = Mock(spec=LLMManager)
        llm_manager.call_llm = AsyncMock(side_effect=self._mock_llm_responses)
        llm_manager.ask_llm = AsyncMock(side_effect=self._mock_ask_llm_responses)
        
        # Mock WebSocket Manager for agent communication
        websocket_manager = Mock(spec=WebSocketManager)
        websocket_manager.send_message = AsyncMock()
        websocket_manager.broadcast_to_user = AsyncMock()
        
        # Mock Tool Dispatcher
        tool_dispatcher = Mock(spec=ToolDispatcher)
        tool_dispatcher.dispatch_tool = AsyncMock(return_value={"status": "success"})
        
        return {
            "llm_manager": llm_manager,
            "websocket_manager": websocket_manager,
            "tool_dispatcher": tool_dispatcher
        }

    def _create_triage_response(self):
        """Create realistic triage agent response"""
        return {
            "content": '{"category": "gpu_optimization", "priority": "high", '
                      '"complexity": "medium", "estimated_savings": "15%", '
                      '"recommended_agents": ["data_collection", "performance_analysis"]}'
        }

    def _create_data_response(self):
        """Create realistic data agent response"""
        return {
            "content": '{"metrics_collected": true, "gpu_utilization": 78, '
                      '"memory_usage": 85, "batch_size": 16, "throughput": 245, '
                      '"bottlenecks_identified": ["memory_bandwidth", "batch_efficiency"]}'
        }

    def _create_reporting_response(self):
        """Create realistic reporting agent response"""
        return {
            "content": '{"optimizations": ["increase_batch_size_to_32", "enable_mixed_precision"], '
                      '"expected_improvement": "22%", "implementation_effort": "low", '
                      '"cost_savings": "$1200_per_month", "confidence": 0.87}'
        }

    def _create_optimization_scenario(self):
        """Create test scenario for GPU optimization workflow"""
        return {
            "user_request": "My GPU workloads are running inefficiently with high memory usage. "
                           "I need optimization recommendations to reduce costs.",
            "expected_workflow": ["triage", "data_collection", "analysis", "reporting"],
            "expected_outcome": {
                "optimizations_identified": True,
                "cost_savings_estimated": True,
                "implementation_plan": True
            }
        }
