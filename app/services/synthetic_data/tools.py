"""
Tool definitions and generation for synthetic data
"""

import random
from typing import Dict, List


def initialize_default_tools() -> List[Dict]:
    """Initialize default tool catalog"""
    return [
        {
            "name": "clickhouse_query",
            "type": "query",
            "latency_ms_range": (50, 500),
            "failure_rate": 0.01
        },
        {
            "name": "postgres_lookup",
            "type": "query",
            "latency_ms_range": (20, 200),
            "failure_rate": 0.005
        },
        {
            "name": "llm_analysis",
            "type": "analysis",
            "latency_ms_range": (1000, 5000),
            "failure_rate": 0.02
        },
        {
            "name": "external_api_call",
            "type": "external_api",
            "latency_ms_range": (100, 2000),
            "failure_rate": 0.05
        },
        {
            "name": "cache_lookup",
            "type": "query",
            "latency_ms_range": (5, 50),
            "failure_rate": 0.001
        },
        {
            "name": "vector_search",
            "type": "query",
            "latency_ms_range": (100, 1000),
            "failure_rate": 0.01
        }
    ]


def create_tool_invocation(tool: Dict) -> Dict:
    """Create a single tool invocation"""
    # Determine if tool fails based on failure rate
    failed = random.random() < tool["failure_rate"]
    
    # Generate realistic latency
    latency = random.uniform(
        tool["latency_ms_range"][0],
        tool["latency_ms_range"][1]
    )
    
    return {
        "name": tool["name"],
        "type": tool["type"],
        "latency_ms": latency,
        "status": "failed" if failed else "success",
        "error": "Tool execution failed" if failed else None
    }


def generate_tool_invocations(workload_type: str, default_tools: List[Dict]) -> List[Dict]:
    """Generate tool invocation pattern based on workload type"""
    invocations = []
    
    if workload_type == "simple_queries":
        # Single tool invocation
        tool = random.choice(default_tools)
        invocations.append(create_tool_invocation(tool))
        
    elif workload_type == "tool_orchestration":
        # Multiple sequential tools
        num_tools = random.randint(2, 5)
        for _ in range(num_tools):
            tool = random.choice(default_tools)
            invocations.append(create_tool_invocation(tool))
            
    elif workload_type == "data_analysis":
        # Query followed by analysis
        query_tools = [t for t in default_tools if t["type"] == "query"]
        analysis_tools = [t for t in default_tools if t["type"] == "analysis"]
        
        if query_tools:
            invocations.append(create_tool_invocation(random.choice(query_tools)))
        if analysis_tools:
            invocations.append(create_tool_invocation(random.choice(analysis_tools)))
            
    elif workload_type == "optimization_workflows":
        # Complex multi-step workflow
        num_tools = random.randint(3, 7)
        for _ in range(num_tools):
            tool = random.choice(default_tools)
            invocations.append(create_tool_invocation(tool))
            
    else:  # error_scenarios
        # Tool with failure
        tool = random.choice(default_tools)
        invocation = create_tool_invocation(tool)
        invocation["status"] = "failed"
        invocation["error"] = "Simulated error"
        invocations.append(invocation)
    
    return invocations


def calculate_metrics(tool_invocations: List[Dict]) -> Dict:
    """Calculate metrics from tool invocations"""
    if not tool_invocations:
        return {
            "total_latency_ms": 0,
            "tool_count": 0,
            "success_rate": 1.0
        }
    
    total_latency = sum(t["latency_ms"] for t in tool_invocations)
    success_count = sum(1 for t in tool_invocations if t["status"] == "success")
    
    return {
        "total_latency_ms": total_latency,
        "tool_count": len(tool_invocations),
        "success_rate": success_count / len(tool_invocations),
        "avg_latency_ms": total_latency / len(tool_invocations)
    }