from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Optional, Any, Tuple
"""Assertion helper functions for ToolDispatcher tests."""

from typing import Any, Dict
from unittest.mock import AsyncMock

from netra_backend.app.agents.tool_dispatcher import (
    ProductionTool,
    ToolDispatchResponse,
)
from netra_backend.app.schemas.unified_tools import (
    SimpleToolPayload,
    ToolResult,
    ToolStatus,
)

def assert_tool_execute_response_success(result: Dict[str, Any], expected_data: Any = None) -> None:
    """Assert tool execution response indicates success."""
    assert result["success"] is True
    if expected_data is not None:
        assert result["data"] == expected_data

def assert_tool_execute_response_error(result: Dict[str, Any], expected_error_text: str) -> None:
    """Assert tool execution response indicates error."""
    assert result["success"] is False
    assert expected_error_text in result["error"]

def assert_production_tool_initialized(tool: ProductionTool, expected_name: str) -> None:
    """Assert ProductionTool is properly initialized."""
    assert tool.name == expected_name
    assert hasattr(tool, 'reliability')

def assert_simple_tool_payload(result: ToolResult) -> None:
    """Assert ToolResult contains SimpleToolPayload."""
    assert result.payload is not None
    assert isinstance(result.payload, SimpleToolPayload)

def assert_metadata_fields(result: Dict[str, Any], tool_name: str, run_id: str) -> None:
    """Assert metadata fields are correctly set."""
    assert result["metadata"]["tool"] == tool_name
    assert result["metadata"]["run_id"] == run_id

def assert_batch_execution_success(result: Dict[str, Any], expected_count: int) -> None:
    """Assert batch execution was successful."""
    assert result["success"] is True
    assert len(result["data"]) == expected_count
    assert result["metadata"]["batch_size"] == expected_count

def assert_corpus_creation_success(result: Dict[str, Any], corpus_id: str, name: str) -> None:
    """Assert corpus creation was successful."""
    assert result["success"] is True
    assert result["data"]["corpus_id"] == corpus_id
    assert result["data"]["name"] == name

def assert_corpus_search_success(result: Dict[str, Any], expected_count: int) -> None:
    """Assert corpus search was successful."""
    assert result["success"] is True
    assert len(result["data"]["results"]) == expected_count
    assert result["data"]["total_matches"] == expected_count

def assert_validation_success(result: Dict[str, Any], is_valid: bool) -> None:
    """Assert validation result is as expected."""
    assert result["success"] is True
    assert result["data"]["valid"] is is_valid

def assert_storage_success(result: Dict[str, Any], stored_count: int) -> None:
    """Assert storage operation was successful."""
    assert result["success"] is True
    assert result["data"]["stored"] == stored_count

def assert_not_implemented_error(result: Dict[str, Any], tool_name: str) -> None:
    """Assert result indicates tool not implemented."""
    assert result["success"] is False
    assert "not implemented" in result["error"]
    assert result["metadata"]["tool"] == tool_name
    assert result["metadata"]["status"] == "not_implemented"

def assert_async_mock_called_with(mock: AsyncMock, expected_args: tuple) -> None:
    """Assert AsyncMock was called with expected arguments."""
    mock.assert_called_once_with(*expected_args)

def assert_execution_error_response(response: Dict[str, Any], error_text: str, tool_name: str) -> None:
    """Assert execution error response format."""
    assert response["success"] is False
    assert error_text in response["error"]
    assert response["metadata"]["tool"] == tool_name

def assert_missing_parameter_error(result: Dict[str, Any], parameter_name: str) -> None:
    """Assert error for missing required parameter."""
    assert result["success"] is False
    assert f"{parameter_name} parameter is required" in result["error"]