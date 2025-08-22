"""
Comprehensive tests for Apex Optimizer tool selection - Part 2: Advanced Tool Selection Tests
Tests advanced tool selection scenarios, edge cases, and error handling
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
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from schemas import AppConfig, RequestModel

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.services.apex_optimizer_agent.models import AgentState
from netra_backend.app.services.apex_optimizer_agent.tools.base import (
    BaseTool,
    ToolMetadata,
)

# Add project root to path
from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import (
    ApexToolSelector,
)
from netra_backend.app.services.context import ToolContext

# Add project root to path
# Import helper classes from part 1
from netra_backend.tests.test_apex_optimizer_tool_selection_part1 import (
    MockLLMConnector,
    MockOptimizationTool,
    OptimizationCategory,
)


class TestApexOptimizerAdvancedToolSelection:
    """Test advanced Apex optimizer tool selection scenarios"""
    
    @pytest.fixture
    def mock_llm_connector(self):
        """Create mock LLM connector"""
        return MockLLMConnector()
    
    @pytest.fixture
    def mock_app_config(self):
        """Create mock app configuration"""
        config = AppConfig()
        config.llm_configs = {
            'analysis': MagicMock(model_name='gpt-4-analysis')
        }
        return config
    
    @pytest.fixture
    def apex_tool_selector(self, mock_llm_connector, mock_app_config):
        """Create Apex tool selector"""
        return ApexToolSelector(mock_llm_connector, mock_app_config)
    async def test_tool_selection_latency_optimization(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection for latency optimization requests"""
        # Create latency-focused request
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            TimeRange,
            Workload,
        )
        request = RequestModel(
            user_id="test_user_123",
            query="Improve response time and reduce latency for our AI system",
            workloads=[Workload(
                run_id="run_456",
                query="optimize latency",
                data_source=DataSource(source_table="latency_metrics"),
                time_range=TimeRange(start_time="2025-01-01", end_time="2025-01-31")
            )]
        )
        from netra_backend.app.services.apex_optimizer_agent.models import BaseMessage
        message = BaseMessage(
            type="human",
            content=request.query,
            metadata={"request": request.model_dump()}
        )
        state = AgentState(
            messages=[message],
            next_node="tool_selection",
            tool_results=None,
            request=request
        )
        state.request = request
        
        # Execute tool selection
        result = await apex_tool_selector.run(state)
        
        # Verify latency optimization tool selected
        assert state.current_tool_name == "tool_latency_optimization"
        assert "target_latency" in state.current_tool_args
        assert state.current_tool_args["optimization_level"] == "aggressive"
    async def test_tool_selection_cache_optimization(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection for cache optimization requests"""
        # Create cache-focused request
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            TimeRange,
            Workload,
        )
        request = RequestModel(
            user_id="test_user_789",
            query="Audit and optimize our KV cache configuration",
            workloads=[Workload(
                run_id="run_789",
                query="optimize cache",
                data_source=DataSource(source_table="cache_metrics"),
                time_range=TimeRange(start_time="2025-01-01", end_time="2025-01-31")
            )]
        )
        from netra_backend.app.services.apex_optimizer_agent.models import BaseMessage
        message = BaseMessage(
            type="human",
            content=request.query,
            metadata={"request": request.model_dump()}
        )
        state = AgentState(
            messages=[message],
            next_node="tool_selection",
            tool_results=None,
            request=request
        )
        state.request = request
        
        # Execute tool selection
        result = await apex_tool_selector.run(state)
        
        # Verify cache optimization tool selected
        assert state.current_tool_name == "kv_cache_optimization_audit"
        assert "cache_size" in state.current_tool_args
        assert "ttl" in state.current_tool_args
    async def test_tool_selection_model_analysis(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection for model analysis requests"""
        # Create model analysis request
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            TimeRange,
            Workload,
        )
        request = RequestModel(
            user_id="test_user_analysis",
            query="Analyze effectiveness of new models for our use case",
            workloads=[Workload(
                run_id="run_analysis",
                query="analyze models",
                data_source=DataSource(source_table="model_metrics"),
                time_range=TimeRange(start_time="2025-01-01", end_time="2025-01-31")
            )]
        )
        from netra_backend.app.services.apex_optimizer_agent.models import BaseMessage
        message = BaseMessage(
            type="human",
            content=request.query,
            metadata={"request": request.model_dump()}
        )
        state = AgentState(
            messages=[message],
            next_node="tool_selection",
            tool_results=None,
            request=request
        )
        state.request = request
        
        # Execute tool selection
        result = await apex_tool_selector.run(state)
        
        # Verify model analysis tool selected
        assert state.current_tool_name == "new_model_effectiveness_analysis"
        assert "model_candidates" in state.current_tool_args
        assert "metrics" in state.current_tool_args
    async def test_tool_selection_multi_objective(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection for multi-objective optimization"""
        # Create multi-objective request
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            TimeRange,
            Workload,
        )
        request = RequestModel(
            user_id="test_user_multi",
            query="Optimize for both cost reduction and latency improvement",
            workloads=[Workload(
                run_id="run_multi",
                query="multi-objective optimization",
                data_source=DataSource(source_table="multi_metrics"),
                time_range=TimeRange(start_time="2025-01-01", end_time="2025-01-31")
            )]
        )
        from netra_backend.app.services.apex_optimizer_agent.models import BaseMessage
        message = BaseMessage(
            type="human",
            content=request.query,
            metadata={"request": request.model_dump()}
        )
        state = AgentState(
            messages=[message],
            next_node="tool_selection",
            tool_results=None,
            request=request
        )
        state.request = request
        
        # Execute tool selection
        result = await apex_tool_selector.run(state)
        
        # Verify multi-objective tool selected
        assert state.current_tool_name == "multi_objective_optimization"
        assert "objectives" in state.current_tool_args
        assert "weights" in state.current_tool_args
    async def test_tool_selection_empty_query(self, apex_tool_selector, mock_app_config):
        """Test tool selection with empty query"""
        # Create state with empty query
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            TimeRange,
            Workload,
        )
        request = RequestModel(
            user_id="test_user_empty",
            query="",
            workloads=[Workload(
                run_id="run_empty",
                query="",
                data_source=DataSource(source_table="empty_metrics"),
                time_range=TimeRange(start_time="2025-01-01", end_time="2025-01-31")
            )]
        )
        from netra_backend.app.services.apex_optimizer_agent.models import BaseMessage
        message = BaseMessage(
            type="human",
            content=request.query,
            metadata={"request": request.model_dump()}
        )
        state = AgentState(
            messages=[message],
            next_node="tool_selection",
            tool_results=None,
            request=request
        )
        state.request = request
        
        # Execute tool selection
        result = await apex_tool_selector.run(state)
        
        # Should handle empty query gracefully
        assert "No query found" in result
        assert state.current_tool_name == None
    async def test_tool_selection_llm_failure(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection when LLM fails"""
        # Create sample agent state
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            TimeRange,
            Workload,
        )
        from netra_backend.app.services.apex_optimizer_agent.models import BaseMessage
        request = RequestModel(
            user_id="test_user_123",
            query="Optimize our AI workload to reduce costs by 20%",
            workloads=[Workload(
                run_id="run_123",
                query="optimize costs",
                data_source=DataSource(source_table="metrics"),
                time_range=TimeRange(start_time="2025-01-01", end_time="2025-01-31")
            )]
        )
        message = BaseMessage(
            type="human",
            content=request.query,
            metadata={"request": request.model_dump()}
        )
        state = AgentState(
            messages=[message],
            next_node="tool_selection",
            tool_results=None,
            request=request
        )
        
        # Make LLM fail
        mock_llm_connector.should_fail = True
        
        # Execute tool selection
        with pytest.raises(NetraException):
            await apex_tool_selector.run(state)
    async def test_tool_selection_invalid_json_response(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection with invalid JSON response from LLM"""
        # Create sample agent state
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            TimeRange,
            Workload,
        )
        from netra_backend.app.services.apex_optimizer_agent.models import BaseMessage
        request = RequestModel(
            user_id="test_user_123",
            query="Optimize our AI workload to reduce costs by 20%",
            workloads=[Workload(
                run_id="run_123",
                query="optimize costs",
                data_source=DataSource(source_table="metrics"),
                time_range=TimeRange(start_time="2025-01-01", end_time="2025-01-31")
            )]
        )
        message = BaseMessage(
            type="human",
            content=request.query,
            metadata={"request": request.model_dump()}
        )
        state = AgentState(
            messages=[message],
            next_node="tool_selection",
            tool_results=None,
            request=request
        )
        
        # Set invalid JSON response
        mock_llm_connector.set_custom_response("invalid json response")
        
        # Execute tool selection
        with pytest.raises(json.JSONDecodeError):
            await apex_tool_selector.run(state)
    async def test_custom_tool_selection(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test custom tool selection logic"""
        # Create custom tool selection scenario
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            TimeRange,
            Workload,
        )
        request = RequestModel(
            user_id="test_user_123",
            query="Custom optimization requirements",
            workloads=[Workload(
                run_id="run_789",
                query="custom optimization",
                data_source=DataSource(source_table="custom_metrics"),
                time_range=TimeRange(start_time="2025-01-01", end_time="2025-01-31")
            )]
        )
        from netra_backend.app.services.apex_optimizer_agent.models import BaseMessage
        message = BaseMessage(
            type="human",
            content=request.query,
            metadata={"request": request.model_dump()}
        )
        state = AgentState(
            messages=[message],
            next_node="tool_selection",
            tool_results=None,
            request=request
        )
        state.request = request
        
        # Set custom LLM response
        custom_response = {
            "tool_name": "advanced_optimization_for_core_function",
            "arguments": {"function_type": "inference", "optimization_target": "throughput"}
        }
        mock_llm_connector.set_custom_response(custom_response)
        
        # Execute tool selection
        result = await apex_tool_selector.run(state)
        
        # Verify custom tool selected
        assert state.current_tool_name == "advanced_optimization_for_core_function"
        assert state.current_tool_args["function_type"] == "inference"
        assert state.current_tool_args["optimization_target"] == "throughput"