"""
Example Prompts E2E Testing - Validation Functions
Contains all validation functions for example prompt testing.
Maximum 300 lines, functions  <= 8 lines.
"""

from typing import Dict

# Validation functions for each prompt type ( <= 8 lines each)
def validate_cost_optimization_result(result: Dict, setup: Dict):
    """Validate cost optimization workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for cost optimization"
    assert any(keyword in result['response'].lower() for keyword in ['cost', 'optimization', 'budget'])

def validate_performance_optimization_result(result: Dict, setup: Dict):
    """Validate performance optimization workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for performance optimization"
    assert any(keyword in result['response'].lower() for keyword in ['latency', 'performance', 'speed'])

def validate_capacity_planning_result(result: Dict, setup: Dict):
    """Validate capacity planning workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for capacity planning"
    assert any(keyword in result['response'].lower() for keyword in ['capacity', 'usage', 'scale'])

def validate_function_optimization_result(result: Dict, setup: Dict):
    """Validate function optimization workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for function optimization"
    assert any(keyword in result['response'].lower() for keyword in ['function', 'optimization', 'method'])

def validate_model_selection_result(result: Dict, setup: Dict):
    """Validate model selection workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for model selection"
    assert any(keyword in result['response'].lower() for keyword in ['model', 'gpt', 'claude'])

def validate_kv_cache_audit_result(result: Dict, setup: Dict):
    """Validate KV cache audit workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for KV cache audit"
    assert any(keyword in result['response'].lower() for keyword in ['cache', 'kv', 'audit'])

def validate_multi_constraint_result(result: Dict, setup: Dict):
    """Validate multi-constraint optimization workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for multi-constraint optimization"
    assert any(keyword in result['response'].lower() for keyword in ['cost', 'latency', 'usage'])

def validate_tool_migration_result(result: Dict, setup: Dict):
    """Validate tool migration workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for tool migration"
    assert any(keyword in result['response'].lower() for keyword in ['tool', 'migration', 'gpt-5'])

def validate_rollback_analysis_result(result: Dict, setup: Dict):
    """Validate rollback analysis workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for rollback analysis"
    assert any(keyword in result['response'].lower() for keyword in ['rollback', 'upgrade', 'cost'])

# Additional validation utilities
def validate_response_structure(result: Dict):
    """Validate the basic structure of a workflow result."""
    required_fields = ['success', 'prompt', 'execution_time', 'quality_passed', 'response']
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"

def validate_execution_time(result: Dict, max_time: float = 300.0):
    """Validate execution time is within acceptable bounds."""
    execution_time = result.get('execution_time', 0)
    assert 0 < execution_time < max_time, f"Execution time {execution_time}s exceeds maximum {max_time}s"

def validate_prompt_coverage(result: Dict, expected_keywords: list):
    """Validate that response covers expected keywords from the prompt."""
    response = result.get('response', '').lower()
    covered_keywords = [kw for kw in expected_keywords if kw.lower() in response]
    coverage_ratio = len(covered_keywords) / len(expected_keywords)
    assert coverage_ratio >= 0.5, f"Insufficient keyword coverage: {coverage_ratio:.2%}"

def validate_quality_metrics(result: Dict, min_length: int = 50, min_quality: float = 0.7):
    """Validate response quality metrics meet minimum standards."""
    response = result.get('response', '')
    assert len(response) >= min_length, f"Response too short: {len(response)} < {min_length}"
    assert result.get('quality_passed', False), "Quality validation failed"

def validate_error_handling(result: Dict):
    """Validate proper error handling in failed workflows."""
    if not result.get('success', True):
        assert 'error' in result, "Failed workflow must include error details"
        assert result['error'] is not None, "Error details cannot be None"
        assert isinstance(result['error'], str), "Error must be a string"

def validate_state_consistency(result: Dict):
    """Validate state consistency in workflow results."""
    if result.get('success', False):
        assert result.get('state') is not None, "Successful workflow must have state"
    assert 'prompt' in result, "Result must contain original prompt"
    assert result['prompt'] is not None, "Prompt cannot be None"

def validate_comprehensive_coverage(results: list, prompt_types: list):
    """Validate comprehensive coverage across multiple test results."""
    assert len(results) == len(prompt_types), "Result count must match prompt type count"
    
    success_count = sum(1 for r in results if r.get('success', False))
    success_rate = success_count / len(results)
    assert success_rate >= 0.8, f"Success rate too low: {success_rate:.2%}"

def validate_performance_consistency(results: list):
    """Validate performance consistency across multiple results."""
    execution_times = [r.get('execution_time', 0) for r in results if r.get('success', False)]
    if execution_times:
        avg_time = sum(execution_times) / len(execution_times)
        max_deviation = max(abs(t - avg_time) for t in execution_times)
        relative_deviation = max_deviation / avg_time if avg_time > 0 else 0
        assert relative_deviation < 2.0, f"Execution time too inconsistent: {relative_deviation:.2%}"