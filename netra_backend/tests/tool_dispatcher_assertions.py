"""Tool dispatcher test assertions and utilities."""

from typing import Dict, Any, List, Optional
import pytest


def assert_tool_execution_success(result: Dict[str, Any], tool_name: str):
    """Assert that tool execution was successful.
    
    Args:
        result: Tool execution result
        tool_name: Expected tool name
    """
    assert "status" in result, f"Tool result missing status for {tool_name}"
    assert result["status"] == "success", f"Tool {tool_name} execution failed: {result.get('error', 'Unknown error')}"
    assert "data" in result, f"Tool result missing data for {tool_name}"


def assert_tool_execution_failure(result: Dict[str, Any], tool_name: str, expected_error: Optional[str] = None):
    """Assert that tool execution failed as expected.
    
    Args:
        result: Tool execution result
        tool_name: Expected tool name
        expected_error: Expected error message pattern
    """
    assert "status" in result, f"Tool result missing status for {tool_name}"
    assert result["status"] in ["error", "failed"], f"Tool {tool_name} expected to fail but got status: {result['status']}"
    
    if expected_error:
        error_msg = result.get("error", result.get("message", ""))
        assert expected_error in str(error_msg), f"Expected error '{expected_error}' not found in '{error_msg}'"


def assert_tool_parameters_valid(parameters: Dict[str, Any], required_params: List[str]):
    """Assert that tool parameters are valid.
    
    Args:
        parameters: Tool parameters to validate
        required_params: List of required parameter names
    """
    for param in required_params:
        assert param in parameters, f"Required parameter '{param}' missing from tool parameters"
        assert parameters[param] is not None, f"Required parameter '{param}' is None"


def assert_tool_response_structure(response: Dict[str, Any], expected_keys: List[str]):
    """Assert that tool response has expected structure.
    
    Args:
        response: Tool response to validate
        expected_keys: List of expected keys in response
    """
    for key in expected_keys:
        assert key in response, f"Expected key '{key}' missing from tool response"


def assert_dispatcher_state(dispatcher, expected_tool_count: Optional[int] = None):
    """Assert dispatcher state is as expected.
    
    Args:
        dispatcher: Tool dispatcher instance
        expected_tool_count: Expected number of registered tools
    """
    assert hasattr(dispatcher, "tools"), "Dispatcher missing tools attribute"
    
    if expected_tool_count is not None:
        actual_count = len(dispatcher.tools) if dispatcher.tools else 0
        assert actual_count == expected_tool_count, f"Expected {expected_tool_count} tools, got {actual_count}"


class MockToolResult:
    """Mock tool execution result for testing."""
    
    def __init__(self, status: str = "success", data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.status = status
        self.data = data or {}
        self.error = error
        
    def to_dict(self) -> Dict[str, Any]:
        result = {"status": self.status, "data": self.data}
        if self.error:
            result["error"] = self.error
        return result


class MockToolDispatcher:
    """Mock tool dispatcher for testing."""
    
    def __init__(self):
        self.tools = {}
        self.execution_history = []
        
    def register_tool(self, name: str, handler):
        """Register a tool handler."""
        self.tools[name] = handler
        
    async def execute_tool(self, name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and record the execution."""
        execution = {
            "tool": name,
            "parameters": parameters,
            "timestamp": pytest.approx(0, abs=1e6)  # Mock timestamp
        }
        self.execution_history.append(execution)
        
        if name not in self.tools:
            return MockToolResult("error", error=f"Tool '{name}' not found").to_dict()
            
        try:
            # Mock successful execution
            return MockToolResult("success", {"result": f"Mock result for {name}"}).to_dict()
        except Exception as e:
            return MockToolResult("error", error=str(e)).to_dict()
            
    def get_tool_names(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self.tools.keys())


@pytest.fixture
def mock_dispatcher():
    """Fixture providing mock tool dispatcher."""
    return MockToolDispatcher()


def assert_execution_error_response(result: Dict[str, Any], expected_error_type: Optional[str] = None):
    """Assert that execution resulted in expected error response.
    
    Args:
        result: Execution result
        expected_error_type: Expected error type (optional)
    """
    assert "status" in result, "Result missing status field"
    assert result["status"] in ["error", "failed"], f"Expected error status but got: {result['status']}"
    
    if expected_error_type:
        error_info = result.get("error", {})
        if isinstance(error_info, str):
            assert expected_error_type in error_info, f"Expected error type '{expected_error_type}' not found in error: {error_info}"
        elif isinstance(error_info, dict):
            error_type = error_info.get("type", "")
            assert expected_error_type in error_type, f"Expected error type '{expected_error_type}' not found in error type: {error_type}"


def assert_batch_execution_success(results: List[Dict[str, Any]], expected_count: int):
    """Assert that batch execution completed successfully.
    
    Args:
        results: List of execution results
        expected_count: Expected number of results
    """
    assert len(results) == expected_count, f"Expected {expected_count} results, got {len(results)}"
    
    for i, result in enumerate(results):
        assert "status" in result, f"Result {i} missing status field"
        assert result["status"] == "success", f"Result {i} failed with status: {result.get('status')}"
        assert "data" in result, f"Result {i} missing data field"


def assert_not_implemented_error(result: Dict[str, Any], tool_name: str):
    """Assert that tool execution failed with NotImplementedError.
    
    Args:
        result: Tool execution result
        tool_name: Name of the tool
    """
    assert "status" in result, f"Tool result missing status for {tool_name}"
    assert result["status"] in ["error", "failed"], f"Tool {tool_name} should have failed but got status: {result['status']}"
    
    error_msg = result.get("error", result.get("message", ""))
    assert "not implemented" in str(error_msg).lower(), f"Expected 'not implemented' error for {tool_name}, got: {error_msg}"


def assert_production_tool_initialized(tool_registry, tool_name: str):
    """Assert that production tool is properly initialized.
    
    Args:
        tool_registry: Tool registry instance
        tool_name: Name of the tool to check
    """
    assert hasattr(tool_registry, "tools"), "Tool registry missing tools attribute"
    assert tool_name in tool_registry.tools, f"Tool '{tool_name}' not found in registry"
    
    tool = tool_registry.tools[tool_name]
    assert tool is not None, f"Tool '{tool_name}' is None"
    assert callable(getattr(tool, "execute", None)), f"Tool '{tool_name}' missing execute method"


def assert_corpus_creation_success(result: Dict[str, Any], corpus_name: str):
    """Assert that corpus creation was successful.
    
    Args:
        result: Corpus creation result
        corpus_name: Name of the corpus
    """
    assert "status" in result, "Corpus creation result missing status"
    assert result["status"] == "success", f"Corpus creation failed: {result.get('error', 'Unknown error')}"
    assert "corpus_id" in result, "Corpus creation result missing corpus_id"
    assert "name" in result, "Corpus creation result missing name"
    assert result["name"] == corpus_name, f"Expected corpus name '{corpus_name}', got '{result['name']}'"


def assert_tool_execute_response_error(result: Dict[str, Any], expected_error_text: str) -> None:
    """Assert tool execution response indicates error."""
    assert result.get("success") is False, f"Expected tool execution to fail, but got success: {result}"
    error_msg = result.get("error", "")
    assert expected_error_text in str(error_msg), f"Expected error text '{expected_error_text}' not found in error: {error_msg}"


def assert_tool_execute_response_success(result: Dict[str, Any]) -> None:
    """Assert tool execution response indicates success."""
    assert result.get("success") is True, f"Expected tool execution to succeed, but got failure: {result.get('error', 'Unknown error')}"
    assert "data" in result or "result" in result, "Successful response missing data/result field"


def assert_corpus_search_success(result: Dict[str, Any], expected_count: int) -> None:
    """Assert corpus search was successful."""
    assert result.get("success") is True, f"Corpus search failed: {result.get('error', 'Unknown error')}"
    results_data = result.get("data", {})
    if "results" in results_data:
        actual_count = len(results_data["results"])
        assert actual_count == expected_count, f"Expected {expected_count} search results, got {actual_count}"
    elif "total_matches" in results_data:
        actual_count = results_data["total_matches"]
        assert actual_count == expected_count, f"Expected {expected_count} matches, got {actual_count}"


def assert_missing_parameter_error(result: Dict[str, Any], parameter_name: str) -> None:
    """Assert that execution failed due to missing parameter."""
    assert result.get("success") is False, f"Expected failure due to missing parameter '{parameter_name}', but got success: {result}"
    error_msg = str(result.get("error", "")).lower()
    param_msg = parameter_name.lower()
    assert "missing" in error_msg and param_msg in error_msg, f"Expected missing parameter error for '{parameter_name}', got: {result.get('error')}"


def assert_storage_success(result: Dict[str, Any], expected_id: Optional[str] = None) -> None:
    """Assert that storage operation was successful."""
    assert result.get("success") is True, f"Storage operation failed: {result.get('error', 'Unknown error')}"
    assert "data" in result or "id" in result, "Storage success response missing data/id field"
    
    if expected_id:
        actual_id = result.get("id") or result.get("data", {}).get("id")
        assert actual_id == expected_id, f"Expected storage ID '{expected_id}', got '{actual_id}'"


def assert_validation_success(result: Dict[str, Any], validation_type: str) -> None:
    """Assert that validation operation was successful."""
    assert result.get("success") is True, f"Validation ({validation_type}) failed: {result.get('error', 'Unknown error')}"
    assert "data" in result or "valid" in result, f"Validation success response missing data/valid field for {validation_type}"


def assert_simple_tool_payload(result: Dict[str, Any]) -> None:
    """Assert that tool result has expected simple payload structure."""
    assert "status" in result, "Tool result missing status field"
    assert result["status"] == "success", f"Expected success status, got: {result['status']}"
    assert "data" in result, "Tool result missing data field"
    
    # Simple payload should have basic structure
    data = result["data"]
    assert isinstance(data, dict), f"Expected data to be dict, got: {type(data)}"


@pytest.fixture
def sample_tool_result():
    """Fixture providing sample tool result."""
    return {
        "status": "success",
        "data": {"message": "Tool executed successfully", "result": 42},
        "execution_time": 0.123
    }