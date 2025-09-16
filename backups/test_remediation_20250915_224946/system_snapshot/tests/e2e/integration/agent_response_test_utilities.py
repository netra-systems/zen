"""
Agent Response Test Utilities

Utilities for testing agent response handling and validation.
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Any, List


class ResponseTestType(Enum):
    """Types of response tests."""
    REGULAR = "regular"
    STREAMING = "streaming"
    ERROR = "error"
    TIMEOUT = "timeout"

class AgentResponseSimulator:
    """Simulates agent responses for testing."""
    
    def __init__(self):
        self.response_count = 0
        self.response_delay = 1.0  # Default delay in seconds
    
    async def simulate_agent_response(self, prompt: str, delay: float = None) -> Dict[str, Any]:
        """Simulate an agent response to a prompt."""
        if delay is None:
            delay = self.response_delay
            
        await asyncio.sleep(delay)
        self.response_count += 1
        
        return {
            "response_id": f"sim_response_{self.response_count}",
            "prompt": prompt,
            "content": f"Simulated response to: {prompt[:50]}...",
            "timestamp": time.time(),
            "status": "completed",
            "metadata": {
                "simulation": True,
                "delay_used": delay,
                "response_count": self.response_count
            }
        }
    
    async def simulate_streaming_response(self, prompt: str, chunk_count: int = 3) -> List[Dict[str, Any]]:
        """Simulate a streaming agent response."""
        chunks = []
        for i in range(chunk_count):
            await asyncio.sleep(0.5)  # Delay between chunks
            chunk = {
                "chunk_id": i,
                "content": f"Stream chunk {i+1} for: {prompt[:30]}...",
                "is_final": i == chunk_count - 1,
                "timestamp": time.time()
            }
            chunks.append(chunk)
        return chunks

class AgentResponseTester:
    """Test agent response handling."""
    
    async def validate_response_format(self, response: Dict[str, Any]) -> bool:
        """Validate agent response format."""
        required_fields = ["status", "content", "timestamp"]
        return all(field in response for field in required_fields)
    
    async def test_response_time(self, agent_func, max_time: float = 5.0) -> Dict[str, Any]:
        """Test agent response time."""
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
