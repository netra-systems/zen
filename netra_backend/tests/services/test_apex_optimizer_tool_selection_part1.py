"""
Comprehensive tests for Apex Optimizer tool selection - Part 1: Helper Classes and Basic Tests
Tests tool selection logic, helper classes, and basic optimization routing
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from enum import Enum

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from netra_backend.app.services.apex_optimizer_agent.tools.base import BaseTool, ToolMetadata
from netra_backend.app.services.apex_optimizer_agent.models import AgentState
from netra_backend.app.services.context import ToolContext
from schemas import AppConfig, RequestModel
from netra_backend.app.core.exceptions_base import NetraException

# Add project root to path


class OptimizationCategory(Enum):
    COST_OPTIMIZATION = "cost_optimization"
    LATENCY_OPTIMIZATION = "latency_optimization" 
    QUALITY_OPTIMIZATION = "quality_optimization"
    CACHE_OPTIMIZATION = "cache_optimization"
    MODEL_OPTIMIZATION = "model_optimization"
    MULTI_OBJECTIVE = "multi_objective"


class MockOptimizationTool(BaseTool):
    """Mock optimization tool for testing"""
    
    def __init__(self, name: str, category: OptimizationCategory, capabilities: List[str] = None):
        self.metadata = ToolMetadata(
            name=name,
            description=f"Mock {name} tool for {category.value}",
            version="1.0.0",
            status="production"
        )
        self.category = category
        self.capabilities = capabilities or []
        self.execution_count = 0
        self.execution_time = 0.1  # Default execution time
        self.should_fail = False
        self.failure_message = "Mock tool failure"
        self.results = []
        
    async def run(self, context: ToolContext, **kwargs) -> Any:
        """Mock tool execution"""
        self.execution_count += 1
        
        # Simulate execution time
        await asyncio.sleep(self.execution_time)
        
        if self.should_fail:
            raise NetraException(self.failure_message)
        
        result = {
            'tool_name': self.metadata.name,
            'category': self.category.value,
            'execution_count': self.execution_count,
            'input_params': kwargs,
            'recommendations': f"Mock recommendations from {self.metadata.name}",
            'metrics': {
                'confidence': 0.85,
                'estimated_improvement': 0.20,
                'execution_time': self.execution_time
            }
        }
        
        self.results.append(result)
        return result
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution metrics for the tool"""
        return {
            'tool_name': self.metadata.name,
            'category': self.category.value,
            'execution_count': self.execution_count,
            'average_execution_time': self.execution_time,
            'capabilities': self.capabilities,
            'success_rate': 1.0 if not self.should_fail else 0.0
        }


class MockLLMConnector:
    """Mock LLM connector for tool selection"""
    
    def __init__(self):
        self.requests = []
        self.response_templates = {
            'cost': {
                "tool_name": "cost_reduction_quality_preservation",
                "arguments": {"target_reduction": 0.20, "maintain_quality": True}
            },
            'latency': {
                "tool_name": "tool_latency_optimization",
                "arguments": {"target_latency": 100, "optimization_level": "aggressive"}
            },
            'cache': {
                "tool_name": "kv_cache_optimization_audit",
                "arguments": {"cache_size": 1024, "ttl": 3600}
            },
            'model': {
                "tool_name": "new_model_effectiveness_analysis",
                "arguments": {"model_candidates": ["gpt-4", "claude-3"], "metrics": ["accuracy", "speed"]}
            },
            'multi': {
                "tool_name": "multi_objective_optimization",
                "arguments": {"objectives": ["cost", "latency", "quality"], "weights": [0.4, 0.4, 0.2]}
            }
        }
        self.should_fail = False
        self.custom_response = None
        
    async def generate_text_async(self, prompt: str, model_name: str, config_name: str) -> str:
        """Mock LLM text generation"""
        self.requests.append({
            'prompt': prompt,
            'model_name': model_name,
            'config_name': config_name,
            'timestamp': datetime.now(UTC)
        })
        
        if self.should_fail:
            raise NetraException("Mock LLM generation failed")
        
        if self.custom_response:
            # If custom_response is a string, return it directly (for testing invalid JSON)
            if isinstance(self.custom_response, str):
                return self.custom_response
            return json.dumps(self.custom_response)
        
        # Analyze prompt to determine appropriate tool
        prompt_lower = prompt.lower()
        
        # Extract just the user query part (after "user query:" and before "available tools:")
        import re
        query_match = re.search(r'user query:\s*([^\n]*?)(?:\n|available tools:|$)', prompt_lower)
        if query_match:
            user_query = query_match.group(1).strip()
        else:
            user_query = prompt_lower
        
        # Debug output for troubleshooting (disable in production)
        # print(f"DEBUG: Extracted user query: {user_query}")
        
        # Check for specific patterns in the USER QUERY, not the whole prompt
        # Check multi-objective patterns first (most specific combinations)
        if ('multi' in user_query or 
            ('both' in user_query and 'cost' in user_query and 'latency' in user_query) or 
            ('cost' in user_query and 'latency' in user_query and 'optimize' in user_query)):
            return json.dumps(self.response_templates['multi'])
        elif 'reduce costs' in user_query or 'cost reduction' in user_query or ('cost' in user_query and 'reduce' in user_query):
            return json.dumps(self.response_templates['cost'])
        elif 'latency' in user_query or 'speed' in user_query or 'response time' in user_query:
            return json.dumps(self.response_templates['latency'])
        elif 'cache' in user_query:
            return json.dumps(self.response_templates['cache'])
        elif 'model' in user_query and ('new' in user_query or 'analysis' in user_query or 'effectiveness' in user_query):
            return json.dumps(self.response_templates['model'])
        else:
            # Default to cost optimization
            return json.dumps(self.response_templates['cost'])
    
    def set_custom_response(self, response):
        """Set custom response for testing (can be dict or string for invalid JSON testing)"""
        self.custom_response = response
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of LLM requests"""
        return self.requests.copy()


class TestApexOptimizerToolSelection:
    """Test Apex optimizer tool selection functionality"""
    
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
    
    @pytest.fixture
    def sample_agent_state(self):
        """Create sample agent state"""
        from netra_backend.app.schemas.unified_tools import Workload, DataSource, TimeRange
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
        # Create a message with the request
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
        return state
    async def test_tool_selection_cost_optimization(self, apex_tool_selector, sample_agent_state, mock_llm_connector):
        """Test tool selection for cost optimization requests"""
        # Execute tool selection
        result = await apex_tool_selector.run(sample_agent_state)
        
        # Verify tool selection
        assert "Successfully dispatched tool" in result
        assert sample_agent_state.current_tool_name == "cost_reduction_quality_preservation"
        assert sample_agent_state.current_tool_args != None
        
        # Verify LLM was called
        assert len(mock_llm_connector.get_request_history()) == 1
        request_history = mock_llm_connector.get_request_history()[0]
        assert "cost" in request_history['prompt'].lower()