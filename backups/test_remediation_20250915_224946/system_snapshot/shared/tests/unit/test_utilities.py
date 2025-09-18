"""
Unit tests for utility and helper functions.

This module tests critical utility functionality including security validators,
configuration helpers, and background task management.

Business Value: Utilities ensure system security, compliance, and operational
reliability across all customer segments and environments.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, call

from shared.background_task_security_validator import (
    BackgroundTaskSecurityValidator,
    SecurityViolation,
    SecurityViolationType,
    get_security_validator,
    validate_background_task,
    security_required
)
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError


class TestBackgroundTaskSecurityValidator:
    """Test background task security validation functionality."""
    
    def test_validator_initialization_with_strict_mode(self):
        """Test BackgroundTaskSecurityValidator initialization in strict mode."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)
        
        assert validator.enforce_strict_mode is True
        assert len(validator.violations) == 0
        assert len(validator.whitelisted_tasks) == 0
        assert validator.validation_stats['validations_performed'] == 0
        assert validator.validation_stats['violations_detected'] == 0
    
    def test_validator_initialization_with_permissive_mode(self):
        """Test BackgroundTaskSecurityValidator initialization in permissive mode."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        assert validator.enforce_strict_mode is False
        assert validator.validation_stats['validations_performed'] == 0
    
    def test_task_whitelisting_functionality(self):
        """Test task whitelisting for legitimate context-free operations."""
        validator = BackgroundTaskSecurityValidator()
        
        # Add task to whitelist
        validator.whitelist_task("system_health_check", "System monitoring doesn't need user context")
        
        assert "system_health_check" in validator.whitelisted_tasks
        
        # Validation should pass for whitelisted task without context
        result = validator.validate_background_task_context(
            task_name="system_health_check",
            task_id="health_check_001",
            user_context=None,
            require_context=False
        )
        
        assert result is True
        assert validator.validation_stats['validations_performed'] == 1
        assert validator.validation_stats['violations_detected'] == 0
    
    def test_validation_failure_with_missing_context(self):
        """Test validation failure when required context is missing."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        result = validator.validate_background_task_context(
            task_name="user_data_processing",
            task_id="process_001",
            user_context=None,  # Missing required context
            require_context=True
        )
        
        assert result is False
        assert validator.validation_stats['violations_detected'] == 1
        assert len(validator.violations) == 1
        
        violation = validator.violations[0]
        assert violation.violation_type == SecurityViolationType.MISSING_CONTEXT
        assert violation.task_name == "user_data_processing"
        assert "missing required UserExecutionContext" in violation.description
    
    def test_validation_failure_in_strict_mode_raises_exception(self):
        """Test that validation failure in strict mode raises exception."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=True)
        
        with pytest.raises(InvalidContextError, match="missing required UserExecutionContext"):
            validator.validate_background_task_context(
                task_name="critical_user_operation",
                task_id="critical_001",
                user_context=None,
                require_context=True
            )
    
    def test_validation_success_with_valid_context(self):
        """Test successful validation with proper user context."""
        validator = BackgroundTaskSecurityValidator()
        
        # Mock valid user context
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "user_123"
        mock_context.verify_isolation = Mock()  # Mock the verification method
        
        result = validator.validate_background_task_context(
            task_name="user_specific_task",
            task_id="task_001",
            user_context=mock_context,
            require_context=True
        )
        
        assert result is True
        assert validator.validation_stats['contexts_validated'] == 1
        mock_context.verify_isolation.assert_called_once()
    
    def test_context_user_id_mismatch_detection(self):
        """Test detection of user ID mismatches in context validation."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        # Mock context with different user ID
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "user_456"
        mock_context.verify_isolation = Mock()
        
        result = validator.validate_background_task_context(
            task_name="user_mismatch_test",
            task_id="mismatch_001",
            user_context=mock_context,
            require_context=True,
            expected_user_id="user_123"  # Different from context
        )
        
        assert result is False
        assert validator.validation_stats['violations_detected'] == 1
        
        violation = validator.violations[0]
        assert violation.violation_type == SecurityViolationType.CONTEXT_MISMATCH
        assert "expected user_123, got user_456" in violation.description


class TestSecurityViolationTracking:
    """Test security violation tracking and reporting."""
    
    def test_security_violation_creation_and_serialization(self):
        """Test SecurityViolation creation and dictionary conversion."""
        violation = SecurityViolation(
            violation_type=SecurityViolationType.UNAUTHORIZED_ACCESS,
            task_name="sensitive_operation",
            task_id="sens_001",
            user_id="user_789",
            description="Unauthorized access attempt detected",
            stack_trace="mock_stack_trace",
            timestamp=datetime.now(timezone.utc),
            remediation_suggestion="Ensure proper authentication"
        )
        
        violation_dict = violation.to_dict()
        
        assert violation_dict['violation_type'] == SecurityViolationType.UNAUTHORIZED_ACCESS
        assert violation_dict['task_name'] == "sensitive_operation"
        assert violation_dict['user_id'] == "user_789"
        assert violation_dict['description'] == "Unauthorized access attempt detected"
        assert violation_dict['severity'] == "HIGH"  # Default
        assert 'timestamp' in violation_dict
        assert 'stack_trace_hash' in violation_dict
    
    def test_violation_summary_generation(self):
        """Test comprehensive violation summary generation."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        # Generate multiple violations
        validator.validate_background_task_context("task1", "id1", None, True)
        validator.validate_background_task_context("task2", "id2", None, True)
        
        # Create a context mismatch violation
        mock_context = Mock()
        mock_context.user_id = "wrong_user"
        mock_context.verify_isolation = Mock()
        validator.validate_background_task_context(
            "task3", "id3", mock_context, True, expected_user_id="right_user"
        )
        
        summary = validator.get_violation_summary()
        
        assert summary['total_violations'] == 3
        assert SecurityViolationType.MISSING_CONTEXT in summary['violation_types']
        assert SecurityViolationType.CONTEXT_MISMATCH in summary['violation_types']
        assert summary['violation_types'][SecurityViolationType.MISSING_CONTEXT] == 2
        assert summary['violation_types'][SecurityViolationType.CONTEXT_MISMATCH] == 1
        
        # Should include recent violations (last 5)
        assert len(summary['recent_violations']) == 3
    
    def test_security_report_generation(self):
        """Test comprehensive security report generation."""
        validator = BackgroundTaskSecurityValidator()
        validator.whitelist_task("whitelisted_task", "Test whitelist")
        
        # Generate a violation
        validator.validate_background_task_context("failing_task", "fail_001", None, True, enforce_strict_mode=False)
        
        # Generate report
        report = validator.generate_security_report()
        
        assert "BACKGROUND TASK SECURITY REPORT" in report
        assert "Total Violations: 1" in report
        assert "WHITELISTED TASKS: 1" in report
        assert "whitelisted_task" in report
        assert "RECENT VIOLATIONS:" in report
    
    def test_violation_clearing_functionality(self):
        """Test violation history clearing for testing/reset."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        # Generate violations
        validator.validate_background_task_context("task1", "id1", None, True)
        validator.validate_background_task_context("task2", "id2", None, True)
        
        assert len(validator.violations) == 2
        
        # Clear violations
        validator.clear_violations()
        
        assert len(validator.violations) == 0
    
    def test_audit_background_task_call_tracking(self):
        """Test comprehensive audit trail for background task calls."""
        validator = BackgroundTaskSecurityValidator()
        
        # Mock user context
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "audit_user"
        mock_context.request_id = "req_audit_001"
        
        # Audit a task call
        audit_info = validator.audit_background_task_call(
            task_name="audited_task",
            task_args=("arg1", "arg2"),
            task_kwargs={"user_context": mock_context, "param1": "value1"},
            caller_context="test_caller"
        )
        
        assert audit_info['task_name'] == "audited_task"
        assert audit_info['has_user_context'] is True
        assert audit_info['context_user_id'] == "audit_user"
        assert audit_info['context_request_id'] == "req_audit_001"
        assert audit_info['caller_context'] == "test_caller"
        assert audit_info['args_count'] == 2
        assert "user_context" in audit_info['kwargs_keys']
        assert "param1" in audit_info['kwargs_keys']
        assert audit_info['security_compliant'] is True


class TestSecurityDecorator:
    """Test security required decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_security_decorator_with_valid_context(self):
        """Test security_required decorator with valid user context."""
        # Mock the global validator
        with patch('shared.background_task_security_validator._global_validator') as mock_validator:
            mock_validator.validate_background_task_context.return_value = True
            mock_validator.audit_background_task_call.return_value = {}
            
            @security_required("decorated_async_task", require_context=True)
            async def test_async_function(data, user_context=None):
                return f"processed {data}"
            
            mock_context = Mock(spec=UserExecutionContext)
            result = await test_async_function("test_data", user_context=mock_context)
            
            assert result == "processed test_data"
            mock_validator.validate_background_task_context.assert_called_once()
            mock_validator.audit_background_task_call.assert_called_once()
    
    def test_security_decorator_with_sync_function(self):
        """Test security_required decorator with synchronous functions.""" 
        with patch('shared.background_task_security_validator._global_validator') as mock_validator:
            mock_validator.validate_background_task_context.return_value = True
            mock_validator.audit_background_task_call.return_value = {}
            
            @security_required("decorated_sync_task", require_context=True)
            def test_sync_function(data, user_context=None):
                return f"sync processed {data}"
            
            mock_context = Mock(spec=UserExecutionContext)
            result = test_sync_function("sync_data", user_context=mock_context)
            
            assert result == "sync processed sync_data"
            mock_validator.validate_background_task_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_security_decorator_validation_failure(self):
        """Test security_required decorator handles validation failures."""
        with patch('shared.background_task_security_validator._global_validator') as mock_validator:
            # Mock validation failure
            mock_validator.validate_background_task_context.side_effect = InvalidContextError("Security violation")
            
            @security_required("failing_task", require_context=True)
            async def failing_function(user_context=None):
                return "should not reach here"
            
            with pytest.raises(InvalidContextError, match="Security violation"):
                await failing_function(user_context=None)
    
    def test_security_decorator_generates_task_id(self):
        """Test that security decorator generates task IDs when not provided."""
        with patch('shared.background_task_security_validator._global_validator') as mock_validator:
            mock_validator.validate_background_task_context.return_value = True
            mock_validator.audit_background_task_call.return_value = {}
            
            @security_required("id_generation_test", require_context=False)
            def test_function():
                return "success"
            
            result = test_function()
            assert result == "success"
            
            # Should have called validation with generated task ID
            call_args = mock_validator.validate_background_task_context.call_args
            task_id = call_args[1]['task_id']  # keyword argument
            assert task_id.startswith("id_generation_test_")
    
    def test_security_decorator_optional_context_mode(self):
        """Test security decorator with require_context=False."""
        with patch('shared.background_task_security_validator._global_validator') as mock_validator:
            mock_validator.validate_background_task_context.return_value = True
            mock_validator.audit_background_task_call.return_value = {}
            
            @security_required("optional_context_task", require_context=False)
            def optional_context_function():
                return "no context needed"
            
            result = optional_context_function()
            assert result == "no context needed"
            
            # Should validate with require_context=False
            call_args = mock_validator.validate_background_task_context.call_args
            assert call_args[1]['require_context'] is False


class TestGlobalSecurityValidator:
    """Test global security validator instance and convenience functions."""
    
    def test_global_validator_singleton_access(self):
        """Test global security validator singleton pattern."""
        validator1 = get_security_validator()
        validator2 = get_security_validator()
        
        assert validator1 is validator2
        assert isinstance(validator1, BackgroundTaskSecurityValidator)
    
    def test_convenience_validation_function(self):
        """Test convenience validate_background_task function."""
        with patch('shared.background_task_security_validator._global_validator') as mock_validator:
            mock_validator.validate_background_task_context.return_value = True
            
            mock_context = Mock(spec=UserExecutionContext)
            result = validate_background_task(
                task_name="convenience_test",
                task_id="conv_001", 
                user_context=mock_context,
                require_context=True
            )
            
            assert result is True
            mock_validator.validate_background_task_context.assert_called_once_with(
                task_name="convenience_test",
                task_id="conv_001",
                user_context=mock_context,
                require_context=True
            )
    
    def test_function_signature_validation(self):
        """Test task function signature validation for context compatibility."""
        validator = BackgroundTaskSecurityValidator()
        
        # Function with user_context parameter
        def good_function(data, user_context=None):
            return data
        
        # Function with **kwargs
        def kwargs_function(data, **kwargs):
            return data
        
        # Function without context support
        def bad_function(data):
            return data
        
        assert validator.validate_task_function_signature(good_function, "good_task") is True
        assert validator.validate_task_function_signature(kwargs_function, "kwargs_task") is True
        assert validator.validate_task_function_signature(bad_function, "bad_task") is False
    
    def test_context_integrity_validation(self):
        """Test user execution context integrity validation."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        # Mock context that fails verification
        mock_bad_context = Mock(spec=UserExecutionContext)
        mock_bad_context.user_id = "test_user"
        mock_bad_context.verify_isolation.side_effect = Exception("Context corrupted")
        
        result = validator.validate_background_task_context(
            task_name="integrity_test",
            task_id="int_001",
            user_context=mock_bad_context,
            require_context=True
        )
        
        assert result is False
        assert validator.validation_stats['violations_detected'] == 1
        
        violation = validator.violations[0]
        assert violation.violation_type == SecurityViolationType.INVALID_CONTEXT
        assert "Invalid UserExecutionContext" in violation.description
    
    def test_validation_statistics_tracking(self):
        """Test comprehensive validation statistics tracking."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        # Perform various validations
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "stats_user"
        mock_context.verify_isolation = Mock()
        
        # Successful validation
        validator.validate_background_task_context("success_task", "s001", mock_context, True)
        
        # Failed validation (no context)
        validator.validate_background_task_context("fail_task", "f001", None, True)
        
        # Whitelisted validation
        validator.whitelist_task("system_task", "System operation")
        validator.validate_background_task_context("system_task", "sys001", None, False)
        
        stats = validator.validation_stats
        
        assert stats['validations_performed'] == 3
        assert stats['violations_detected'] == 1
        assert stats['contexts_validated'] == 1
        assert stats['tasks_validated'] == 3


class TestUtilityEdgeCases:
    """Test utility edge cases and error conditions."""
    
    def test_security_violation_with_none_values(self):
        """Test SecurityViolation handling of None values."""
        violation = SecurityViolation(
            violation_type=SecurityViolationType.ISOLATION_BREACH,
            task_name="edge_case_task",
            task_id="edge_001",
            user_id=None,  # None user ID
            description="Test violation with None values",
            stack_trace="",
            timestamp=datetime.now(timezone.utc),
            remediation_suggestion="Test remediation"
        )
        
        violation_dict = violation.to_dict()
        
        assert violation_dict['user_id'] is None
        assert violation_dict['violation_type'] == SecurityViolationType.ISOLATION_BREACH
        assert violation_dict['stack_trace_hash'] == hash("") % 1000000
    
    def test_validator_error_handling_during_validation(self):
        """Test validator error handling when validation itself fails."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        # Mock context that raises unexpected error during validation
        mock_context = Mock()
        mock_context.user_id = "error_user"
        
        # Mock verify_isolation to raise unexpected error
        def failing_verification():
            raise RuntimeError("Unexpected error during verification")
        
        mock_context.verify_isolation = failing_verification
        
        # Validation should handle the error gracefully in permissive mode
        result = validator.validate_background_task_context(
            "error_handling_test",
            "err_001", 
            mock_context,
            True
        )
        
        assert result is False  # Should fail gracefully
    
    def test_audit_with_non_context_kwargs(self):
        """Test audit handling of kwargs without user context."""
        validator = BackgroundTaskSecurityValidator()
        
        audit_info = validator.audit_background_task_call(
            task_name="no_context_task",
            task_args=(),
            task_kwargs={"param1": "value1", "param2": "value2"},
            caller_context="test_context"
        )
        
        assert audit_info['has_user_context'] is False
        assert audit_info['context_user_id'] is None
        assert audit_info['security_compliant'] is False
        assert audit_info['kwargs_keys'] == ["param1", "param2"]
    
    def test_empty_violations_summary(self):
        """Test violation summary with no violations."""
        validator = BackgroundTaskSecurityValidator()
        
        summary = validator.get_violation_summary()
        
        assert summary['total_violations'] == 0
        assert summary['violation_types'] == {}
        assert summary['recent_violations'] == []
        assert summary['validation_stats']['validations_performed'] == 0
    
    def test_large_violation_history_truncation(self):
        """Test that violation history is properly truncated in reports."""
        validator = BackgroundTaskSecurityValidator(enforce_strict_mode=False)
        
        # Generate more than 5 violations
        for i in range(10):
            validator.validate_background_task_context(f"task_{i}", f"id_{i}", None, True)
        
        summary = validator.get_violation_summary()
        
        # Should only include last 5 violations
        assert len(summary['recent_violations']) == 5
        assert summary['total_violations'] == 10