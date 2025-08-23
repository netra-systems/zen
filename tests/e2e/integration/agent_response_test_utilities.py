"""
Agent Response Test Utilities

Utilities for testing agent response handling and validation.
"""

import asyncio
from typing import Dict, Any, List

class AgentResponseTester:
    """Test agent response handling."""
    
    async def validate_response_format(self, response: Dict[str, Any]) -> bool:
        """Validate agent response format."""
        required_fields = ["status", "content", "timestamp"]
        return all(field in response for field in required_fields)
    
    async def test_response_time(self, agent_func, max_time: float = 5.0) -> Dict[str, Any]:
        """Test agent response time."""
        import time
        start_time = time.time()
        result = await agent_func()
        end_time = time.time()
        
        response_time = end_time - start_time
        
        return {
            "response_time": response_time,
            "within_limit": response_time <= max_time,
            "result": result
        }

class AgentPerformanceTester:
    """Test agent performance metrics."""
    
    async def benchmark_agent(self, agent_func, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark agent performance."""
        times = []
        for _ in range(iterations):
            tester = AgentResponseTester()
            result = await tester.test_response_time(agent_func)
            times.append(result["response_time"])
        
        return {
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "iterations": iterations
        }
