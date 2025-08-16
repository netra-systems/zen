"""
Comprehensive tests for Apex Optimizer tool selection - Part 4: Performance and Scaling Tests
Tests performance characteristics, scaling behavior, and resource management
"""

import pytest
import asyncio
import json
import time
import tracemalloc
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from enum import Enum

from app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from app.services.apex_optimizer_agent.tools.base import BaseTool, ToolMetadata
from app.services.apex_optimizer_agent.models import AgentState
from app.services.context import ToolContext
from app.schemas import AppConfig, RequestModel
from app.core.exceptions_base import NetraException

# Import helper classes from other parts
from .test_apex_optimizer_tool_selection_part1 import (
    OptimizationCategory, 
    MockOptimizationTool, 
    MockLLMConnector
)
from .test_apex_optimizer_tool_selection_part3 import ToolChain


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
    async def test_tool_selection_performance(self, performance_tools, mock_context):
        """Test tool selection performance under load"""
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
    async def test_concurrent_tool_execution_scaling(self, performance_tools, mock_context):
        """Test scaling with concurrent tool executions"""
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}
        
        for concurrency in concurrency_levels:
            start_time = time.perf_counter()
            
            # Execute tools concurrently
            tasks = []
            for i in range(concurrency):
                tool = performance_tools['fast']  # Use fast tool for consistency
                task = tool.run(mock_context, concurrent_test=i)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            end_time = time.perf_counter()
            
            execution_time = end_time - start_time
            results[concurrency] = execution_time
        
        # Higher concurrency should not dramatically increase execution time
        # Use max() to handle timing precision edge cases where results[1] might be very small
        baseline_time = max(results[1], 0.001)  # Minimum 1ms baseline
        assert results[50] < baseline_time * 10  # Should scale reasonably well
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
    async def test_tool_resource_management(self, performance_tools, mock_context):
        """Test resource management for tool execution"""
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