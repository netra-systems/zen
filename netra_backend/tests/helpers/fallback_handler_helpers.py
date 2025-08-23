"""
Helper functions for fallback handler tests
Provides reusable assertion helpers, setup utilities, and test data validators
"""

from typing import Any, Dict, List

from netra_backend.app.core.fallback_handler import FallbackContext, FallbackMetadata

def assert_basic_fallback_structure(result: Dict[str, Any]) -> None:
    """Assert basic fallback result structure is valid"""
    assert result["type"] == "contextual_fallback"
    assert "context" in result
    assert "message" in result
    assert len(result["message"]) > 0

def assert_metadata_fields(result: Dict[str, Any], expected_error: str, expected_agent: str) -> None:
    """Assert metadata fields are properly set"""
    assert result["metadata"]["error_type"] == expected_error
    assert result["metadata"]["agent"] == expected_agent
    assert "has_partial_data" in result["metadata"]
    assert "recovery_available" in result["metadata"]

def assert_partial_data_included(result: Dict[str, Any], expected_data: Dict[str, Any]) -> None:
    """Assert partial data is properly included in result"""
    assert "partial_data" in result
    assert result["partial_data"] == expected_data

def assert_suggested_actions_present(result: Dict[str, Any]) -> None:
    """Assert suggested actions are present and valid"""
    assert "suggested_actions" in result
    assert len(result["suggested_actions"]) > 0

def assert_message_contains_keywords(message: str, keywords: List[str]) -> None:
    """Assert message contains at least one of the keywords"""
    message_lower = message.lower()
    assert any(keyword.lower() in message_lower for keyword in keywords)

def assert_template_collection_valid(templates: Dict[FallbackContext, str]) -> None:
    """Assert fallback handler template collection is valid"""
    assert templates is not None
    assert len(templates) == 8
    expected_contexts = [
        FallbackContext.TRIAGE_FAILURE, FallbackContext.DATA_FAILURE,
        FallbackContext.OPTIMIZATION_FAILURE, FallbackContext.ACTION_FAILURE,
        FallbackContext.REPORT_FAILURE, FallbackContext.LLM_FAILURE,
        FallbackContext.VALIDATION_FAILURE, FallbackContext.GENERAL_FAILURE
    ]
    for context in expected_contexts:
        assert context in templates

def validate_domain_detection_result(detected: str, expected: str, user_input: str) -> None:
    """Validate domain detection results with special cases"""
    if "dataset" in user_input.lower():
        valid_domains = ["training", "data", expected.replace('_', ' '), "general optimization"]
        assert detected in valid_domains
    else:
        assert detected == expected.replace('_', ' ') or detected == "general optimization"

def validate_error_reason_extraction(result: str, expected: str) -> None:
    """Validate error reason extraction matches expected format"""
    assert result == expected

def validate_partial_data_formatting(result: str, partial_data: Any, expected: str) -> None:
    """Validate partial data formatting with complex assertions"""
    if isinstance(expected, str):
        assert expected in result or result == expected
    assert len(result) > 0
    if partial_data:
        assert any(key in result for key in partial_data.keys())

def validate_test_case_expectations(result: str, expected: str) -> None:
    """Validate test case results match expected patterns"""
    if "total items" in expected:
        assert "total items" in result
    else:
        assert result == expected

def validate_quality_issues_format(result: str, expected: str) -> None:
    """Validate quality issues formatting"""
    if "- " in expected:
        assert "- Generic phrases" in result or "- No metrics" in result
    else:
        assert result == expected

def validate_diagnostic_content(result: str, metadata: FallbackMetadata) -> None:
    """Validate diagnostic information content"""
    assert f"Error Type: {metadata.error_type}" in result
    assert f"Agent: {metadata.agent_name}" in result
    if metadata.attempted_operations:
        assert f"Operations Attempted: {len(metadata.attempted_operations)}" in result

def validate_suggested_actions_structure(actions: List[Dict[str, Any]]) -> None:
    """Validate suggested actions have required structure"""
    assert len(actions) == 3
    retry_action = actions[0]
    assert retry_action["action"] == "retry"
    assert retry_action["description"] == "Retry the operation"
    assert "delay" in retry_action["parameters"]
    assert "max_attempts" in retry_action["parameters"]

def assert_content_keywords_present(content: str, keywords: List[str]) -> None:
    """Assert content contains all specified keywords"""
    content_lower = content.lower()
    for keyword in keywords:
        assert keyword.lower() in content_lower