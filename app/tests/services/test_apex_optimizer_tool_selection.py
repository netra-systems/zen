"""
Comprehensive tests for Apex Optimizer tool selection and chaining
Tests tool selection logic, chaining mechanisms, optimization routing, and performance
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from enum import Enum

from app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from app.services.apex_optimizer_agent.tools.base import BaseTool, ToolMetadata
from app.services.apex_optimizer_agent.models import AgentState
from app.services.context import ToolContext
from app.schemas import AppConfig, RequestModel
from app.core.exceptions import NetraException


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
            'timestamp': datetime.utcnow()
        })
        
        if self.should_fail:
            raise NetraException("Mock LLM generation failed")
        
        if self.custom_response:
            return json.dumps(self.custom_response)
        
        # Analyze prompt to determine appropriate tool
        prompt_lower = prompt.lower()
        
        # Check for cost patterns first (should be prioritized over latency when both are present)
        if 'cost' in prompt_lower and ('reduce' in prompt_lower or 'optimization' in prompt_lower):
            return json.dumps(self.response_templates['cost'])
        elif 'latency' in prompt_lower or 'speed' in prompt_lower or 'response time' in prompt_lower:
            return json.dumps(self.response_templates['latency'])
        elif 'cache' in prompt_lower:
            return json.dumps(self.response_templates['cache'])
        elif 'model' in prompt_lower and ('new' in prompt_lower or 'analysis' in prompt_lower):
            return json.dumps(self.response_templates['model'])
        elif 'multi' in prompt_lower or ('cost' in prompt_lower and 'latency' in prompt_lower):
            return json.dumps(self.response_templates['multi'])
        else:
            # Default to cost optimization
            return json.dumps(self.response_templates['cost'])
    
    def set_custom_response(self, response: Dict[str, Any]):
        """Set custom response for testing"""
        self.custom_response = response
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of LLM requests"""
        return self.requests.copy()


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
                    'timestamp': datetime.utcnow(),
                    'success': True,
                    'result': result
                })
                
                executed_tools.add(current_tool)
                
                # Determine next tool based on rules
                current_tool = self._get_next_tool(current_tool, result)
                
            except Exception as e:
                self.execution_history.append({
                    'tool_name': current_tool,
                    'timestamp': datetime.utcnow(),
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
        from app.schemas import Workload, DataSource, TimeRange
        from app.services.apex_optimizer_agent.models import BaseMessage
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
    async def test_tool_selection_latency_optimization(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection for latency optimization requests"""
        # Create latency-focused request
        from app.schemas import Workload, DataSource, TimeRange
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
        from app.services.apex_optimizer_agent.models import BaseMessage
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
    
    @pytest.mark.asyncio
    async def test_tool_selection_cache_optimization(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection for cache optimization requests"""
        # Create cache-focused request
        request = RequestModel(query="Audit and optimize our KV cache configuration")
        from app.services.apex_optimizer_agent.models import BaseMessage
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
    
    @pytest.mark.asyncio
    async def test_tool_selection_model_analysis(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection for model analysis requests"""
        # Create model analysis request
        request = RequestModel(query="Analyze effectiveness of new models for our use case")
        from app.services.apex_optimizer_agent.models import BaseMessage
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
    
    @pytest.mark.asyncio
    async def test_tool_selection_multi_objective(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test tool selection for multi-objective optimization"""
        # Create multi-objective request
        request = RequestModel(query="Optimize for both cost reduction and latency improvement")
        from app.services.apex_optimizer_agent.models import BaseMessage
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
    
    @pytest.mark.asyncio
    async def test_tool_selection_empty_query(self, apex_tool_selector, mock_app_config):
        """Test tool selection with empty query"""
        # Create state with empty query
        request = RequestModel(query="")
        from app.services.apex_optimizer_agent.models import BaseMessage
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
    
    @pytest.mark.asyncio
    async def test_tool_selection_llm_failure(self, apex_tool_selector, sample_agent_state, mock_llm_connector):
        """Test tool selection when LLM fails"""
        # Make LLM fail
        mock_llm_connector.should_fail = True
        
        # Execute tool selection
        with pytest.raises(NetraException):
            await apex_tool_selector.run(sample_agent_state)
    
    @pytest.mark.asyncio
    async def test_tool_selection_invalid_json_response(self, apex_tool_selector, sample_agent_state, mock_llm_connector):
        """Test tool selection with invalid JSON response from LLM"""
        # Set invalid JSON response
        mock_llm_connector.set_custom_response("invalid json response")
        
        # Execute tool selection
        with pytest.raises(json.JSONDecodeError):
            await apex_tool_selector.run(sample_agent_state)
    
    @pytest.mark.asyncio
    async def test_custom_tool_selection(self, apex_tool_selector, mock_llm_connector, mock_app_config):
        """Test custom tool selection logic"""
        # Create custom tool selection scenario
        from app.schemas import Workload, DataSource, TimeRange
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
        from app.services.apex_optimizer_agent.models import BaseMessage
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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


class TestApexOptimizerPerformanceAndScaling:
    """Test performance and scaling characteristics"""
    
    @pytest.fixture
    def performance_tools(self):
        """Create tools with different performance characteristics"""
        fast_tool = MockOptimizationTool("fast_optimizer", OptimizationCategory.COST_OPTIMIZATION)
        fast_tool.execution_time = 0.01  # Very fast
        
        medium_tool = MockOptimizationTool("medium_optimizer", OptimizationCategory.LATENCY_OPTIMIZATION)
        medium_tool.execution_time = 0.1  # Medium speed
        
        slow_tool = MockOptimizationTool("slow_optimizer", OptimizationCategory.QUALITY_OPTIMIZATION)
        slow_tool.execution_time = 0.5  # Slower
        
        return {'fast': fast_tool, 'medium': medium_tool, 'slow': slow_tool}
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context for performance testing"""
        return MagicMock(spec=ToolContext)
    
    @pytest.mark.asyncio
    async def test_tool_selection_performance(self, performance_tools, mock_context):
        """Test tool selection performance under load"""
        import time
        
        # Execute many tool selections rapidly
        num_selections = 100
        start_time = time.time()
        
        tasks = []
        for i in range(num_selections):
            # Alternate between different tools
            tool_name = ['fast', 'medium', 'slow'][i % 3]
            tool = performance_tools[tool_name]
            task = tool.run(mock_context, test_param=f"test_{i}")
            tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        throughput = len(results) / total_time
        
        # Should handle high throughput
        assert len(results) == num_selections
        assert throughput > 100  # At least 100 selections per second
        assert total_time < 2.0   # Complete within reasonable time
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution_scaling(self, performance_tools, mock_context):
        """Test scaling with concurrent tool executions"""
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}
        
        for concurrency in concurrency_levels:
            start_time = asyncio.get_event_loop().time()
            
            # Execute tools concurrently
            tasks = []
            for i in range(concurrency):
                tool = performance_tools['fast']  # Use fast tool for consistency
                task = tool.run(mock_context, concurrent_test=i)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            end_time = asyncio.get_event_loop().time()
            
            execution_time = end_time - start_time
            results[concurrency] = execution_time
        
        # Higher concurrency should not dramatically increase execution time
        # (within reasonable limits for our mock tools)
        assert results[50] < results[1] * 10  # Should scale reasonably well
    
    @pytest.mark.asyncio
    async def test_tool_chain_optimization_performance(self, performance_tools, mock_context):
        """Test optimization of tool chain execution performance"""
        # Create optimized chain that considers tool performance
        chain = ToolChain()
        
        # Register tools
        for tool in performance_tools.values():
            chain.register_tool(tool)
        
        # Add performance-aware chaining rules
        # Fast tools first, then slower ones if needed
        chain.add_chain_rule("fast_optimizer", "medium_optimizer", "always")
        chain.add_chain_rule("medium_optimizer", "slow_optimizer", "low_confidence")
        
        # Measure chain execution time
        start_time = asyncio.get_event_loop().time()
        results = await chain.execute_chain("fast_optimizer", mock_context)
        end_time = asyncio.get_event_loop().time()
        
        execution_time = end_time - start_time
        
        # Should complete chain efficiently
        assert len(results) >= 2  # At least fast and medium tools
        assert execution_time < 1.0  # Complete within 1 second
    
    def test_tool_metrics_and_monitoring(self, performance_tools):
        """Test tool performance metrics collection"""
        # Execute tools and collect metrics
        tool = performance_tools['medium']
        
        # Simulate multiple executions
        import asyncio
        for _ in range(10):
            asyncio.run(tool.run(MagicMock(spec=ToolContext)))
        
        # Get metrics
        metrics = tool.get_execution_metrics()
        
        # Verify metrics
        assert metrics['execution_count'] == 10
        assert metrics['tool_name'] == "medium_optimizer"
        assert metrics['category'] == OptimizationCategory.LATENCY_OPTIMIZATION.value
        assert metrics['average_execution_time'] == 0.1
        assert metrics['success_rate'] == 1.0
    
    @pytest.mark.asyncio
    async def test_tool_load_balancing(self, performance_tools, mock_context):
        """Test load balancing across multiple tool instances"""
        # Create multiple instances of the same tool type
        tool_instances = []
        for i in range(3):
            tool = MockOptimizationTool(
                f"load_balanced_tool_{i}", 
                OptimizationCategory.COST_OPTIMIZATION
            )
            tool.execution_time = 0.1 + (i * 0.05)  # Slightly different performance
            tool_instances.append(tool)
        
        # Simulate load balancing by distributing requests
        tasks = []
        for i in range(15):  # 15 requests across 3 tools
            tool = tool_instances[i % 3]  # Round-robin distribution
            task = tool.run(mock_context, request_id=i)
            tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks)
        
        # Verify load distribution
        assert len(results) == 15
        
        # Each tool should handle 5 requests
        for tool in tool_instances:
            assert tool.execution_count == 5
    
    @pytest.mark.asyncio
    async def test_tool_resource_management(self, performance_tools, mock_context):
        """Test resource management for tool execution"""
        import tracemalloc
        
        # Start memory tracking
        tracemalloc.start()
        
        # Execute resource-intensive operations
        tool = performance_tools['slow']
        
        # Execute many operations
        tasks = []
        for i in range(50):
            # Add some memory-intensive parameters
            task = tool.run(mock_context, 
                           large_data=f"x" * 1000,  # 1KB per request
                           request_id=i)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Check memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should use reasonable memory (less than 50MB for this test)
        assert peak < 50 * 1024 * 1024  # 50MB threshold
        
        # Verify all operations completed
        assert tool.execution_count == 50