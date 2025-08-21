"""
Tool definitions and generation for synthetic data
"""

import random
from typing import Dict, List


def initialize_default_tools() -> List[Dict]:
    """Initialize default tool catalog"""
    query_tools = _create_query_tools()
    analysis_tools = _create_analysis_tools()
    external_tools = _create_external_tools()
    return query_tools + analysis_tools + external_tools


def _create_query_tools() -> List[Dict]:
    """Create query-based tools"""
    return [
        _create_clickhouse_tool(),
        _create_postgres_tool(),
        _create_cache_tool(),
        _create_vector_search_tool()
    ]


def _create_analysis_tools() -> List[Dict]:
    """Create analysis tools"""
    return [_create_llm_analysis_tool()]


def _create_external_tools() -> List[Dict]:
    """Create external service tools"""
    return [_create_external_api_tool()]


def _create_clickhouse_tool() -> Dict:
    """Create ClickHouse query tool"""
    return {
        "name": "clickhouse_query",
        "type": "query",
        "latency_ms_range": (50, 500),
        "failure_rate": 0.01
    }


def _create_postgres_tool() -> Dict:
    """Create PostgreSQL lookup tool"""
    return {
        "name": "postgres_lookup",
        "type": "query",
        "latency_ms_range": (20, 200),
        "failure_rate": 0.005
    }


def _create_llm_analysis_tool() -> Dict:
    """Create LLM analysis tool"""
    return {
        "name": "llm_analysis",
        "type": "analysis",
        "latency_ms_range": (1000, 5000),
        "failure_rate": 0.02
    }


def _create_external_api_tool() -> Dict:
    """Create external API call tool"""
    return {
        "name": "external_api_call",
        "type": "external_api",
        "latency_ms_range": (100, 2000),
        "failure_rate": 0.05
    }


def _create_cache_tool() -> Dict:
    """Create cache lookup tool"""
    return {
        "name": "cache_lookup",
        "type": "query",
        "latency_ms_range": (5, 50),
        "failure_rate": 0.001
    }


def _create_vector_search_tool() -> Dict:
    """Create vector search tool"""
    return {
        "name": "vector_search",
        "type": "query",
        "latency_ms_range": (100, 1000),
        "failure_rate": 0.01
    }


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
        invocations = _generate_simple_query_invocations(default_tools)
    elif workload_type == "tool_orchestration":
        invocations = _generate_orchestration_invocations(default_tools)
    elif workload_type == "data_analysis":
        invocations = _generate_data_analysis_invocations(default_tools)
    elif workload_type == "optimization_workflows":
        invocations = _generate_optimization_workflow_invocations(default_tools)
    else:  # error_scenarios
        invocations = _generate_error_scenario_invocations(default_tools)
    
    return invocations


def _generate_simple_query_invocations(default_tools: List[Dict]) -> List[Dict]:
    """Generate single tool invocation for simple queries"""
    tool = random.choice(default_tools)
    return [create_tool_invocation(tool)]


def _generate_orchestration_invocations(default_tools: List[Dict]) -> List[Dict]:
    """Generate multiple sequential tools for orchestration"""
    invocations = []
    num_tools = random.randint(2, 5)
    for _ in range(num_tools):
        tool = random.choice(default_tools)
        invocations.append(create_tool_invocation(tool))
    return invocations


def _generate_data_analysis_invocations(default_tools: List[Dict]) -> List[Dict]:
    """Generate query followed by analysis tools"""
    invocations = []
    query_tools = [t for t in default_tools if t["type"] == "query"]
    analysis_tools = [t for t in default_tools if t["type"] == "analysis"]
    
    if query_tools:
        invocations.append(create_tool_invocation(random.choice(query_tools)))
    if analysis_tools:
        invocations.append(create_tool_invocation(random.choice(analysis_tools)))
    
    return invocations


def _generate_optimization_workflow_invocations(default_tools: List[Dict]) -> List[Dict]:
    """Generate complex multi-step workflow tools"""
    invocations = []
    num_tools = random.randint(3, 7)
    for _ in range(num_tools):
        tool = random.choice(default_tools)
        invocations.append(create_tool_invocation(tool))
    return invocations


def _generate_error_scenario_invocations(default_tools: List[Dict]) -> List[Dict]:
    """Generate tool invocation with simulated failure"""
    tool = random.choice(default_tools)
    invocation = create_tool_invocation(tool)
    invocation["status"] = "failed"
    invocation["error"] = "Simulated error"
    return [invocation]


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