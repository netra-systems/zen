"""
Comprehensive tests for Apex Optimizer tool selection - Part 3: Tool Chaining Tests
Tests tool chaining mechanisms, orchestration, and complex workflows
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
import json
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from netra_backend.app.schemas import AppConfig, RequestModel

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.services.apex_optimizer_agent.models import AgentState
from netra_backend.app.services.apex_optimizer_agent.tools.base import (
    BaseTool,
    ToolMetadata,
)

from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import (
    ApexToolSelector,
)
from netra_backend.app.services.context import ToolContext

# Import helper classes from part 1
from netra_backend.tests.services.test_apex_optimizer_tool_selection_part1 import (
    MockLLMConnector,
    MockOptimizationTool,
    OptimizationCategory,
)

class ToolChain:
    """Manages chaining of optimization tools"""
    
    def __init__(self):
        self.tools = {}
        self.execution_history = []
        self.chain_rules = {}
        
    def register_tool(self, tool: MockOptimizationTool):
        """Register a tool in the chain"""
        self.tools[tool.metadata.name] = tool
        
    def add_chain_rule(self, from_tool: str, to_tool: str, condition: str):
        """Add chaining rule between tools"""
        if from_tool not in self.chain_rules:
            self.chain_rules[from_tool] = []
        self.chain_rules[from_tool].append({
            'to_tool': to_tool,
            'condition': condition
        })
    
    async def execute_chain(self, initial_tool: str, context: ToolContext, **kwargs) -> List[Dict[str, Any]]:
        """Execute a chain of tools"""
        results = []
        current_tool = initial_tool
        executed_tools = set()
        
        while current_tool and current_tool not in executed_tools:
            if current_tool not in self.tools:
                break
                
            tool = self.tools[current_tool]
            
            try:
                result = await tool.run(context, **kwargs)
                results.append(result)
                
                self.execution_history.append({
                    'tool_name': current_tool,
                    'timestamp': datetime.now(UTC),
                    'success': True,
                    'result': result
                })
                
                executed_tools.add(current_tool)
                
                # Determine next tool based on rules
                current_tool = self._get_next_tool(current_tool, result)
                
            except Exception as e:
                self.execution_history.append({
                    'tool_name': current_tool,
                    'timestamp': datetime.now(UTC),
                    'success': False,
                    'error': str(e)
                })
                break
        
        return results
    
    def _get_next_tool(self, current_tool: str, result: Dict[str, Any]) -> Optional[str]:
        """Get next tool based on chaining rules"""
        if current_tool not in self.chain_rules:
            return None
            
        for rule in self.chain_rules[current_tool]:
            if self._evaluate_condition(rule['condition'], result):
                return rule['to_tool']
        
        return None
    
    def _evaluate_condition(self, condition: str, result: Dict[str, Any]) -> bool:
        """Evaluate chaining condition"""
        # Simplified condition evaluation
        if condition == "always":
            return True
        elif condition == "low_confidence" and result.get('metrics', {}).get('confidence', 1.0) < 0.7:
            return True
        elif condition == "needs_multi_objective":
            return 'multi' in condition or len(result.get('input_params', {})) > 2
        
        return False

class TestApexOptimizerToolChaining:
    """Test tool chaining and orchestration"""
    
    @pytest.fixture
    def optimization_tools(self):
        """Create optimization tools for testing"""
        tools = {
            'cost_analyzer': MockOptimizationTool(
                "cost_analyzer", 
                OptimizationCategory.COST_OPTIMIZATION,
                ["cost_analysis", "budget_tracking"]
            ),
            'latency_optimizer': MockOptimizationTool(
                "latency_optimizer", 
                OptimizationCategory.LATENCY_OPTIMIZATION,
                ["response_time", "throughput"]
            ),
            'quality_monitor': MockOptimizationTool(
                "quality_monitor", 
                OptimizationCategory.QUALITY_OPTIMIZATION,
                ["accuracy", "consistency"]
            ),
            'multi_objective': MockOptimizationTool(
                "multi_objective", 
                OptimizationCategory.MULTI_OBJECTIVE,
                ["pareto_optimization", "trade_off_analysis"]
            )
        }
        return tools
    
    @pytest.fixture
    def tool_chain(self, optimization_tools):
        """Create tool chain with registered tools"""
        chain = ToolChain()
        
        # Register all tools
        for tool in optimization_tools.values():
            chain.register_tool(tool)
        
        # Add chaining rules
        chain.add_chain_rule("cost_analyzer", "quality_monitor", "always")
        chain.add_chain_rule("quality_monitor", "multi_objective", "low_confidence")
        chain.add_chain_rule("latency_optimizer", "multi_objective", "needs_multi_objective")
        
        return chain
    
    @pytest.fixture
    def mock_tool_context(self):
        """Create mock tool context"""
        context = MagicMock(spec=ToolContext)
        context.user_id = "test_user"
        context.session_id = "test_session"
        context.request_data = {"optimization_target": "cost_reduction"}
        return context
    async def test_simple_tool_chain_execution(self, tool_chain, mock_tool_context):
        """Test simple tool chain execution"""
        # Execute chain starting with cost analyzer
        results = await tool_chain.execute_chain("cost_analyzer", mock_tool_context)
        
        # Should execute cost_analyzer -> quality_monitor
        assert len(results) >= 2
        assert results[0]['tool_name'] == "cost_analyzer"
        assert results[1]['tool_name'] == "quality_monitor"
        
        # Verify execution history
        assert len(tool_chain.execution_history) >= 2
        assert tool_chain.execution_history[0]['success'] == True
    async def test_conditional_tool_chaining(self, tool_chain, mock_tool_context, optimization_tools):
        """Test conditional tool chaining based on results"""
        # Make quality monitor return low confidence to trigger multi-objective
        quality_tool = optimization_tools['quality_monitor']
        
        # Mock low confidence result
        async def mock_run_low_confidence(context, **kwargs):
            return {
                'tool_name': quality_tool.metadata.name,
                'category': quality_tool.category.value,
                'metrics': {'confidence': 0.6}  # Low confidence
            }
        
        quality_tool.run = mock_run_low_confidence
        
        # Execute chain
        results = await tool_chain.execute_chain("cost_analyzer", mock_tool_context)
        
        # Should trigger multi-objective due to low confidence
        assert len(results) == 3
        assert results[-1]['tool_name'] == "multi_objective"
    async def test_parallel_tool_execution(self, optimization_tools, mock_tool_context):
        """Test parallel execution of multiple optimization tools"""
        # Execute multiple tools concurrently
        tools = [optimization_tools['cost_analyzer'], optimization_tools['latency_optimizer']]
        
        tasks = []
        for tool in tools:
            task = tool.run(mock_tool_context, parallel_execution=True)
            tasks.append(task)
        
        # Execute in parallel
        results = await asyncio.gather(*tasks)
        
        # All tools should complete
        assert len(results) == 2
        assert results[0]['tool_name'] == "cost_analyzer"
        assert results[1]['tool_name'] == "latency_optimizer"
    async def test_tool_chain_error_handling(self, tool_chain, mock_tool_context, optimization_tools):
        """Test error handling in tool chains"""
        # Make second tool in chain fail
        optimization_tools['quality_monitor'].should_fail = True
        
        # Execute chain
        results = await tool_chain.execute_chain("cost_analyzer", mock_tool_context)
        
        # Should execute first tool successfully, fail on second
        assert len(results) == 1  # Only first tool completes
        assert results[0]['tool_name'] == "cost_analyzer"
        
        # Check execution history for failure
        assert len(tool_chain.execution_history) == 2
        assert tool_chain.execution_history[0]['success'] == True
        assert tool_chain.execution_history[1]['success'] == False
    async def test_tool_chain_cycle_prevention(self, tool_chain, mock_tool_context):
        """Test prevention of cycles in tool chains"""
        # Add a rule that could create a cycle
        tool_chain.add_chain_rule("multi_objective", "cost_analyzer", "always")
        
        # Execute chain
        results = await tool_chain.execute_chain("cost_analyzer", mock_tool_context)
        
        # Should not execute indefinitely (cycle prevention)
        assert len(results) <= 3  # Maximum reasonable chain length
        
        # Should not execute the same tool twice
        executed_tools = [result['tool_name'] for result in results]
        assert len(executed_tools) == len(set(executed_tools))  # No duplicates
    async def test_dynamic_tool_chaining(self, tool_chain, mock_tool_context):
        """Test dynamic tool chaining based on runtime conditions"""
        # Create dynamic chaining logic
        async def dynamic_chain_executor(initial_tool, context):
            results = []
            current_tool = initial_tool
            
            while current_tool and len(results) < 5:  # Limit chain length
                if current_tool not in tool_chain.tools:
                    break
                
                tool = tool_chain.tools[current_tool]
                result = await tool.run(context)
                results.append(result)
                
                # Dynamic next tool selection based on result metrics
                confidence = result.get('metrics', {}).get('confidence', 1.0)
                improvement = result.get('metrics', {}).get('estimated_improvement', 0.0)
                
                if confidence < 0.7:
                    current_tool = "multi_objective"
                elif improvement > 0.3:
                    current_tool = "quality_monitor"
                else:
                    current_tool = None  # End chain
            
            return results
        
        # Execute dynamic chain
        results = await dynamic_chain_executor("cost_analyzer", mock_tool_context)
        
        # Should execute based on dynamic conditions
        assert len(results) >= 1
        assert results[0]['tool_name'] == "cost_analyzer"