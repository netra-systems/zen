"""
Unit tests for ExecutionResult compatibility regression prevention.

This test suite specifically prevents the regression found in commit e32a97b31
where ExecutionStatus consolidation and ExecutionResult compatibility properties
caused failures in agent execution.

Key regression scenarios tested:
1. ExecutionResult compatibility properties (error, result)
2. ExecutionStatus enum value consistency 
3. Cross-agent ExecutionResult creation patterns
"""
import pytest
from datetime import datetime
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.agents.base.interface import ExecutionResult, ExecutionContext
from netra_backend.app.schemas.core_enums import ExecutionStatus

class TestExecutionResultCompatibilityProperties:
    """Test ExecutionResult compatibility properties that were missing in the regression."""

    def test_error_property_compatibility(self):
        """Test that ExecutionResult.error property returns error_message for backward compatibility."""
        error_message = 'Test error occurred'
        result = ExecutionResult(status=ExecutionStatus.FAILED, request_id='test_123', error_message=error_message)
        assert result.error == error_message
        assert result.error == result.error_message

    def test_error_property_none_when_no_error(self):
        """Test that error property returns None when no error_message is set."""
        result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id='test_123')
        assert result.error is None
        assert result.error_message is None

    def test_result_property_compatibility(self):
        """Test that ExecutionResult.result property returns data for backward compatibility."""
        test_data = {'key': 'value', 'count': 42}
        result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id='test_123', data=test_data)
        assert result.result == test_data
        assert result.result == result.data

    def test_result_property_empty_dict_when_no_data(self):
        """Test that result property returns empty dict when no data is set."""
        result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id='test_123')
        assert result.result == {}
        assert result.data == {}

class TestExecutionStatusEnumConsistency:
    """Test ExecutionStatus enum consolidation and value consistency."""

    def test_execution_status_completed_value(self):
        """Test that COMPLETED status has correct string value."""
        assert ExecutionStatus.COMPLETED.value == 'completed'
        assert ExecutionStatus.COMPLETED == 'completed'

    def test_execution_status_success_alias(self):
        """Test that SUCCESS alias maps to same value as COMPLETED."""
        assert ExecutionStatus.SUCCESS == ExecutionStatus.COMPLETED
        assert ExecutionStatus.SUCCESS.value == 'completed'

    def test_execution_status_all_required_values(self):
        """Test that all required ExecutionStatus values exist."""
        required_statuses = ['pending', 'initializing', 'executing', 'completed', 'failed', 'retrying', 'fallback', 'degraded']
        available_values = [status.value for status in ExecutionStatus]
        for required in required_statuses:
            assert required in available_values, f"Required status '{required}' not found"

    def test_execution_result_is_success_property(self):
        """Test that is_success property works with COMPLETED status."""
        success_result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id='test_123')
        failed_result = ExecutionResult(status=ExecutionStatus.FAILED, request_id='test_123')
        assert success_result.is_success is True
        assert failed_result.is_success is False

    def test_execution_result_is_success_with_success_alias(self):
        """Test that is_success works with SUCCESS alias too."""
        success_result = ExecutionResult(status=ExecutionStatus.SUCCESS, request_id='test_123')
        assert success_result.is_success is True
        assert success_result.status == ExecutionStatus.COMPLETED

class TestExecutionResultCreationPatterns:
    """Test ExecutionResult creation patterns used across agents."""

    def test_success_execution_result_pattern(self):
        """Test the pattern for creating successful execution results."""
        test_data = {'analysis': 'complete', 'recommendations': ['opt1', 'opt2']}
        execution_time = 1234.5
        result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id='test_request_123', data=test_data, execution_time_ms=execution_time, completed_at=datetime.utcnow())
        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_success is True
        assert result.is_complete is True
        assert result.data == test_data
        assert result.result == test_data
        assert result.execution_time_ms == execution_time
        assert result.error is None

    def test_failure_execution_result_pattern(self):
        """Test the pattern for creating failed execution results."""
        error_msg = 'Agent execution failed due to timeout'
        error_code = 'TIMEOUT_ERROR'
        result = ExecutionResult(status=ExecutionStatus.FAILED, request_id='test_request_123', error_message=error_msg, error_code=error_code, completed_at=datetime.utcnow())
        assert result.status == ExecutionStatus.FAILED
        assert result.is_failed is True
        assert result.is_complete is True
        assert result.is_success is False
        assert result.error_message == error_msg
        assert result.error == error_msg
        assert result.error_code == error_code
        assert result.data == {}
        assert result.result == {}

    def test_execution_result_with_metrics_and_artifacts(self):
        """Test ExecutionResult with full metadata."""
        result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id='test_request_123', data={'key': 'value'}, artifacts=['report.pdf', 'analysis.json'], execution_time_ms=2345.6, metrics={'tokens_used': 150, 'api_calls': 3}, trace_id='trace_abc123', started_at=datetime.utcnow(), completed_at=datetime.utcnow())
        assert result.artifacts == ['report.pdf', 'analysis.json']
        assert result.metrics['tokens_used'] == 150
        assert result.trace_id == 'trace_abc123'
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.result == {'key': 'value'}
        assert result.error is None

class TestBackwardCompatibilityScenarios:
    """Test scenarios that would have failed in the regression."""

    def test_legacy_success_status_usage(self):
        """Test that legacy code using SUCCESS status still works."""
        result = ExecutionResult(status=ExecutionStatus.SUCCESS, request_id='legacy_test')
        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_success is True

    def test_legacy_error_access_pattern(self):
        """Test legacy pattern of accessing error via .error property."""
        result = ExecutionResult(status=ExecutionStatus.FAILED, request_id='legacy_test', error_message='Legacy error')
        if result.error:
            assert result.error == 'Legacy error'

    def test_legacy_result_access_pattern(self):
        """Test legacy pattern of accessing result data via .result property."""
        data = {'legacy': 'data', 'count': 5}
        result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id='legacy_test', data=data)
        if result.result:
            assert result.result['legacy'] == 'data'
            assert result.result['count'] == 5

    def test_cross_agent_result_handling(self):
        """Test that ExecutionResult can be passed between agents."""
        triage_result = ExecutionResult(status=ExecutionStatus.COMPLETED, request_id='cross_agent_test', data={'category': 'optimization', 'priority': 'high'}, execution_time_ms=500.0)

        def process_agent_result(result: ExecutionResult) -> Dict[str, Any]:
            """Simulate how another agent might process the result."""
            if result.is_success:
                return {'received_data': result.result, 'execution_time': result.execution_time_ms, 'has_error': result.error is not None}
            else:
                return {'error': result.error}
        processed = process_agent_result(triage_result)
        assert processed['received_data']['category'] == 'optimization'
        assert processed['execution_time'] == 500.0
        assert processed['has_error'] is False
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')