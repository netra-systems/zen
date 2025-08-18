"""
LLM Mock Utilities - Comprehensive mock utilities for LLM testing.

Consolidates all LLM-related mock patterns into a single, reusable module.
Module MUST be ≤300 lines, each function MUST be ≤8 lines.
"""

import json
import asyncio
from typing import Any, Dict, List, Type, TypeVar, Optional, Union
from unittest.mock import Mock, AsyncMock
from pydantic import BaseModel
from datetime import datetime, UTC

T = TypeVar('T', bound=BaseModel)


class LLMResponseBuilder:
    """Fluent interface builder for complex LLM mock configurations."""
    
    def __init__(self):
        self.llm_manager = Mock()
        self._responses = {}
        self._errors = {}
        self._setup_defaults()
    
    def _setup_defaults(self):
        """Initialize default mock responses."""
        self.llm_manager.call_llm = AsyncMock()
        self.llm_manager.ask_llm = AsyncMock()
        self.llm_manager.ask_structured_llm = AsyncMock()
        self.llm_manager.get = Mock()


def create_mock_llm_manager() -> Mock:
    """Create base LLM manager mock with core methods."""
    mock_manager = Mock()
    mock_manager.call_llm = AsyncMock(return_value=_get_default_call_response())
    mock_manager.ask_llm = AsyncMock(return_value=json.dumps(_get_default_ask_response()))
    mock_manager.ask_structured_llm = AsyncMock(return_value=_create_default_structured())
    mock_manager.get = Mock(return_value=Mock())
    return mock_manager


def _get_default_call_response() -> Dict[str, Any]:
    """Get default call_llm response."""
    return {
        "content": "Mock LLM response for optimization analysis",
        "tool_calls": []
    }


def _get_default_ask_response() -> Dict[str, Any]:
    """Get default ask_llm response."""
    return {
        "category": "optimization",
        "analysis": "Mock analysis response",
        "recommendations": ["Mock recommendation 1", "Mock recommendation 2"]
    }


def _create_default_structured() -> Mock:
    """Create default structured response mock."""
    mock_response = Mock()
    mock_response.category = "optimization"
    mock_response.analysis = "Mock structured analysis"
    return mock_response


def with_basic_responses(manager: Mock, content: str = None, tool_calls: List = None) -> Mock:
    """Add basic response configuration to LLM manager."""
    response_content = content or "Mock basic response content"
    calls = tool_calls or []
    manager.call_llm = AsyncMock(return_value={"content": response_content, "tool_calls": calls})
    manager.ask_llm = AsyncMock(return_value=json.dumps({"result": response_content}))
    return manager


def with_structured_responses(manager: Mock, schema: Type[T] = None, data: Dict = None) -> Mock:
    """Add structured response configuration to LLM manager."""
    if schema:
        mock_instance = _create_mock_instance(schema, data)
        manager.ask_structured_llm = AsyncMock(return_value=mock_instance)
    else:
        manager.ask_structured_llm = AsyncMock(return_value=_create_generic_structured(data))
    return manager


def _create_mock_instance(schema: Type[T], data: Dict = None) -> T:
    """Create mock instance of Pydantic schema."""
    mock_data = data or _generate_mock_data_for_schema(schema)
    try:
        return schema(**mock_data)
    except Exception:
        return _create_fallback_mock(schema)


def _generate_mock_data_for_schema(schema: Type[T]) -> Dict[str, Any]:
    """Generate mock data based on schema fields."""
    mock_data = {}
    for field_name, field_info in schema.model_fields.items():
        if field_info.is_required():
            mock_data[field_name] = _get_mock_field_value(field_name, field_info.annotation)
    return mock_data


def _get_mock_field_value(field_name: str, annotation: Type) -> Any:
    """Get mock value for specific field type."""
    type_map = {str: f"Mock {field_name}", int: 42, float: 0.85, bool: True, list: ["mock_item"], dict: {"mock": "data"}}
    return type_map.get(annotation, f"mock_{field_name}")


def _create_fallback_mock(schema: Type[T]) -> Mock:
    """Create fallback mock when schema instantiation fails."""
    mock = Mock()
    mock.category = "mock_category"
    mock.analysis = "Mock fallback analysis"
    return mock


def _create_generic_structured(data: Dict = None) -> Mock:
    """Create generic structured response mock."""
    default_data = {"category": "mock", "result": "Mock structured result"}
    response_data = data or default_data
    mock = Mock()
    for key, value in response_data.items():
        setattr(mock, key, value)
    return mock


def with_agent_responses(manager: Mock, agent_type: str = "triage") -> Mock:
    """Add agent-specific response configuration."""
    if agent_type == "triage":
        _setup_triage_responses(manager)
    elif agent_type == "data":
        _setup_data_agent_responses(manager)
    elif agent_type == "supervisor":
        _setup_supervisor_responses(manager)
    return manager


def _setup_triage_responses(manager: Mock):
    """Setup triage agent specific responses."""
    from app.agents.triage_sub_agent.models import TriageResult
    triage_response = TriageResult(
        category="optimization", severity="medium",
        analysis="Mock triage analysis",
        requirements=["cost_reduction"], next_steps=["analyze_costs"]
    )
    manager.ask_structured_llm = AsyncMock(return_value=triage_response)


def _setup_data_agent_responses(manager: Mock):
    """Setup data agent specific responses."""
    manager.call_llm = AsyncMock(return_value={
        "content": "Mock data analysis complete",
        "tool_calls": [{"name": "data_processor", "args": {"query": "mock"}}]
    })


def _setup_supervisor_responses(manager: Mock):
    """Setup supervisor agent specific responses."""
    manager.ask_llm = AsyncMock(return_value=json.dumps({
        "routing_decision": "data_agent",
        "priority": "high",
        "context": "Mock supervisor routing"
    }))


def with_error_responses(manager: Mock, error_type: str = "generic") -> Mock:
    """Add error response configuration to LLM manager."""
    if error_type == "timeout":
        _setup_timeout_errors(manager)
    elif error_type == "api_error":
        _setup_api_errors(manager)
    elif error_type == "validation":
        _setup_validation_errors(manager)
    else:
        _setup_generic_errors(manager)
    return manager


def _setup_timeout_errors(manager: Mock):
    """Setup timeout error responses."""
    manager.call_llm = AsyncMock(side_effect=asyncio.TimeoutError("Mock timeout"))
    manager.ask_llm = AsyncMock(side_effect=asyncio.TimeoutError("Mock timeout"))


def _setup_api_errors(manager: Mock):
    """Setup API error responses."""
    manager.call_llm = AsyncMock(side_effect=Exception("Mock API error"))
    manager.ask_llm = AsyncMock(side_effect=Exception("Mock API error"))


def _setup_validation_errors(manager: Mock):
    """Setup validation error responses."""
    manager.ask_structured_llm = AsyncMock(side_effect=ValueError("Mock validation error"))


def _setup_generic_errors(manager: Mock):
    """Setup generic error responses."""
    manager.call_llm = AsyncMock(side_effect=Exception("Mock generic error"))


def with_tool_calls(manager: Mock, tools: List[Dict] = None) -> Mock:
    """Add tool call response configuration."""
    default_tools = [{"name": "mock_tool", "args": {"param": "value"}}]
    tool_calls = tools or default_tools
    manager.call_llm = AsyncMock(return_value={
        "content": "Tool execution requested",
        "tool_calls": tool_calls
    })
    return manager


def with_performance_mocks(manager: Mock, latency_ms: int = 250) -> Mock:
    """Add performance testing mock configuration."""
    async def mock_with_delay(*args, **kwargs):
        await asyncio.sleep(latency_ms / 1000)
        return {"content": "Performance test response", "tool_calls": []}
    
    manager.call_llm = AsyncMock(side_effect=mock_with_delay)
    manager.ask_llm = AsyncMock(side_effect=mock_with_delay)
    return manager


def create_streaming_mock(manager: Mock, chunks: List[str] = None) -> Mock:
    """Create streaming response mock configuration."""
    default_chunks = ["Mock ", "streaming ", "response ", "content"]
    stream_chunks = chunks or default_chunks
    
    async def mock_stream(*args, **kwargs):
        for chunk in stream_chunks:
            yield type('obj', (object,), {'content': chunk})()
    
    manager.astream = AsyncMock(side_effect=mock_stream)
    return manager


def create_metrics_mock(success_rate: float = 0.95, avg_latency: int = 200) -> Dict[str, Any]:
    """Create mock metrics data for testing."""
    return {
        "total_requests": 100,
        "successful_requests": int(100 * success_rate),
        "failed_requests": int(100 * (1 - success_rate)),
        "success_rate": success_rate,
        "average_latency_ms": avg_latency,
        "timestamp": datetime.now(UTC).isoformat()
    }


def create_cost_analysis_mock() -> Dict[str, Any]:
    """Create mock cost analysis response."""
    return {
        "current_cost": 150.75,
        "projected_savings": 45.25,
        "optimization_opportunities": ["model_switching", "caching"],
        "confidence": 0.88
    }


def create_optimization_recommendations_mock() -> List[Dict[str, Any]]:
    """Create mock optimization recommendations."""
    return [
        {"type": "model_switch", "priority": "high", "savings": 30.0},
        {"type": "caching", "priority": "medium", "savings": 15.25},
        {"type": "batching", "priority": "low", "savings": 5.0}
    ]


# Export main interfaces
__all__ = [
    'LLMResponseBuilder',
    'create_mock_llm_manager',
    'with_basic_responses',
    'with_structured_responses', 
    'with_agent_responses',
    'with_error_responses',
    'with_tool_calls',
    'with_performance_mocks',
    'create_streaming_mock',
    'create_metrics_mock',
    'create_cost_analysis_mock',
    'create_optimization_recommendations_mock'
]