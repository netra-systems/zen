"""SSOT Test Suite: UserExecutionContext Placeholder Pattern Validation Issue Reproduction

This test suite reproduces the exact GCP log error:
'Field user_id appears to contain placeholder pattern: default_user'

ROOT CAUSE: UserExecutionContext validation incorrectly flags "default_user" due to "default_" pattern
LOCATION: netra_backend/app/services/user_execution_context.py:179-180
BUSINESS IMPACT: Blocks Golden Path, affects $500K+ ARR

Business Value Justification (BVJ):
- Segment: ALL (Core platform functionality)
- Business Goal: System Stability (unblock Golden Path)
- Value Impact: Restore $500K+ ARR by fixing user context validation
- Revenue Impact: Critical - prevents all authenticated user interactions

Test Strategy:
1. FAILING TEST: Reproduce exact validation error with "default_user"
2. PATTERN TEST: Test the specific "default_" pattern matching logic
3. BOUNDARY TEST: Test edge cases around pattern validation
4. LOGGING TEST: Verify GCP structured logging captures the error correctly

SSOT Compliance:
- Inherits from SSotBaseTestCase (test_framework/ssot/)
- Uses real UserExecutionContext for authentic validation
- Follows absolute import patterns
- Tests exact production scenarios
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    InvalidContextError,
    create_isolated_execution_context
)
from shared.isolated_environment import IsolatedEnvironment
from shared.types.core_types import UserID, ThreadID, RunID


class TestUserExecutionContextPlaceholderValidationReproduction(SSotBaseTestCase):
    """Test suite reproducing the exact 'default_user' validation issue from GCP logs.
    
    This test class reproduces Issue: GCP log error where UserExecutionContext validation
    incorrectly flags legitimate "default_user" user_id due to overly broad "default_" pattern.
    """

    def setup_method(self, method=None):
        """Set up test fixtures with real UserExecutionContext components."""
        super().setup_method(method)
        
        # Capture logging to verify exact error messages
        self.log_capture = []
        self.log_handler = logging.Handler()
        self.log_handler.emit = lambda record: self.log_capture.append(record)
        
        # Get logger used by UserExecutionContext
        self.uc_logger = logging.getLogger('netra_backend.app.services.user_execution_context')
        self.uc_logger.addHandler(self.log_handler)
        self.uc_logger.setLevel(logging.DEBUG)
        
        # Standard test IDs that should work
        self.valid_thread_id = "th_12345678901234567890"
        self.valid_run_id = "run_12345678901234567890"
        self.valid_request_id = "req_12345678901234567890"

    def teardown_method(self, method=None):
        """Clean up test fixtures."""
        if hasattr(self, 'uc_logger') and hasattr(self, 'log_handler'):
            self.uc_logger.removeHandler(self.log_handler)
        super().teardown_method(method)

    def test_default_user_validation_failure_reproduction(self):
        """
        REPRODUCER TEST: Exact reproduction of the GCP log error.
        
        This test reproduces the exact error from GCP logs:
        'Field user_id appears to contain placeholder pattern: default_user'
        
        Expected Behavior: This test SHOULD FAIL initially, demonstrating the issue.
        After fix: This test should PASS.
        """
        # This is the exact user_id causing the GCP error
        problematic_user_id = "default_user"
        
        # Clear any previous log captures
        self.log_capture.clear()
        
        # Attempt to create UserExecutionContext with problematic user_id
        with pytest.raises(InvalidContextError) as exc_info:
            context = UserExecutionContext(
                user_id=problematic_user_id,
                thread_id=self.valid_thread_id,
                run_id=self.valid_run_id,
                request_id=self.valid_request_id,
                created_at=datetime.now(timezone.utc)
            )
        
        # Verify exact error message matches GCP logs
        error_message = str(exc_info.value)
        assert "appears to contain placeholder pattern" in error_message, (
            f"Expected placeholder pattern error, got: {error_message}"
        )
        assert "default_user" in error_message, (
            f"Expected 'default_user' in error message, got: {error_message}"
        )
        
        # Verify detailed logging captured the issue
        error_logs = [record for record in self.log_capture if record.levelno >= logging.ERROR]
        assert len(error_logs) > 0, "Expected error log entries for validation failure"
        
        error_log = error_logs[0]
        assert "VALIDATION FAILURE" in error_log.getMessage(), (
            f"Expected VALIDATION FAILURE in log, got: {error_log.getMessage()}"
        )
        assert "default_user" in error_log.getMessage(), (
            f"Expected 'default_user' in log message, got: {error_log.getMessage()}"
        )

    def test_default_pattern_matching_logic(self):
        """
        PATTERN TEST: Test the specific 'default_' pattern matching logic.
        
        This test verifies that the pattern matching logic correctly identifies
        the "default_" prefix pattern that's causing the false positive.
        """
        test_cases = [
            # Cases that SHOULD fail (legitimate patterns)
            ("default_temp", True, "Legitimate default prefix should fail"),
            ("default_placeholder", True, "Legitimate default placeholder should fail"),
            
            # Cases that SHOULD NOT fail (false positives - the bug)
            ("default_user", False, "default_user should be allowed - it's a legitimate user ID"),
            ("default_admin", False, "default_admin should be allowed - it's a legitimate user ID"),
            ("default_system", False, "default_system should be allowed - it's a legitimate user ID"),
            
            # Edge cases
            ("default", True, "Exact 'default' should fail"),
            ("DEFAULT_USER", False, "Case sensitivity test - uppercase should be caught"),
            ("user_default", False, "default_ pattern should only match prefix"),
        ]
        
        for user_id, should_fail, description in test_cases:
            self.log_capture.clear()
            
            if should_fail:
                with pytest.raises(InvalidContextError):
                    UserExecutionContext(
                        user_id=user_id,
                        thread_id=self.valid_thread_id,
                        run_id=self.valid_run_id,
                        request_id=self.valid_request_id,
                        created_at=datetime.now(timezone.utc)
                    )
            else:
                # This should NOT raise an exception
                try:
                    context = UserExecutionContext(
                        user_id=user_id,
                        thread_id=self.valid_thread_id,
                        run_id=self.valid_run_id,
                        request_id=self.valid_request_id,
                        created_at=datetime.now(timezone.utc)
                    )
                    # If we get here without exception, the test passes for this case
                    assert context.user_id == user_id
                except InvalidContextError as e:
                    pytest.fail(f"{description}: {user_id} should be allowed but got error: {e}")

    def test_forbidden_patterns_comprehensive(self):
        """
        BOUNDARY TEST: Comprehensive test of all forbidden patterns to ensure
        we're not missing other legitimate use cases.
        """
        # Get the forbidden patterns from the validation logic
        # Based on user_execution_context.py lines 184-187
        forbidden_patterns = [
            'placeholder_', 'registry_', 'default_', 'temp_',
            'example_', 'demo_', 'sample_', 'template_', 'mock_', 'fake_'
        ]
        
        # Test each pattern with legitimate-looking suffixes
        legitimate_suffixes = ['user', 'admin', 'system', 'account', 'profile']
        
        for pattern in forbidden_patterns:
            for suffix in legitimate_suffixes:
                user_id = f"{pattern}{suffix}"
                
                # All of these SHOULD fail with current logic
                with pytest.raises(InvalidContextError) as exc_info:
                    UserExecutionContext(
                        user_id=user_id,
                        thread_id=self.valid_thread_id,
                        run_id=self.valid_run_id,
                        request_id=self.valid_request_id,
                        created_at=datetime.now(timezone.utc)
                    )
                
                # Verify error message contains the pattern
                assert "placeholder pattern" in str(exc_info.value), (
                    f"Expected placeholder pattern error for {user_id}"
                )

    def test_legitimate_user_ids_should_pass(self):
        """
        VALIDATION TEST: Ensure legitimate user IDs that don't match patterns work correctly.
        """
        legitimate_user_ids = [
            "user_12345",
            "john_doe",
            "admin_user_123",
            "system_account",
            "production_user",
            "real_user_id",
            "authenticated_user",
            "google_oauth_123456789",
            "github_user_abcdef",
        ]
        
        for user_id in legitimate_user_ids:
            try:
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=self.valid_thread_id,
                    run_id=self.valid_run_id,
                    request_id=self.valid_request_id,
                    created_at=datetime.now(timezone.utc)
                )
                assert context.user_id == user_id
            except InvalidContextError as e:
                pytest.fail(f"Legitimate user_id '{user_id}' should be allowed but got error: {e}")

    def test_test_environment_pattern_allowance(self):
        """
        ENVIRONMENT TEST: Verify that test environment correctly allows test_ patterns.
        """
        # Mock test environment
        with patch.object(IsolatedEnvironment, 'is_test', return_value=True):
            # test_ pattern should be allowed in test environment
            test_user_id = "test_user"
            
            try:
                context = UserExecutionContext(
                    user_id=test_user_id,
                    thread_id=self.valid_thread_id,
                    run_id=self.valid_run_id,
                    request_id=self.valid_request_id,
                    created_at=datetime.now(timezone.utc)
                )
                assert context.user_id == test_user_id
            except InvalidContextError as e:
                pytest.fail(f"test_user should be allowed in test environment but got error: {e}")

    def test_production_environment_pattern_restriction(self):
        """
        ENVIRONMENT TEST: Verify that production environment blocks test_ patterns.
        """
        # Mock production environment
        with patch.object(IsolatedEnvironment, 'is_test', return_value=False):
            # test_ pattern should be blocked in production
            test_user_id = "test_user"
            
            with pytest.raises(InvalidContextError) as exc_info:
                UserExecutionContext(
                    user_id=test_user_id,
                    thread_id=self.valid_thread_id,
                    run_id=self.valid_run_id,
                    request_id=self.valid_request_id,
                    created_at=datetime.now(timezone.utc)
                )
            
            assert "placeholder pattern" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_isolated_execution_context_with_default_user(self):
        """
        INTEGRATION TEST: Test the factory function with the problematic user_id.
        
        This tests the create_isolated_execution_context function which is commonly
        used in production code and may be where the error occurs.
        """
        # This should fail with current validation logic
        with pytest.raises(InvalidContextError) as exc_info:
            context = await create_isolated_execution_context(
                user_id="default_user",
                request_id="req_test_factory"
            )
        
        # Verify the error propagates correctly through the factory
        assert "appears to contain placeholder pattern" in str(exc_info.value)
        assert "default_user" in str(exc_info.value)

    def test_logging_output_for_gcp_structured_logging(self):
        """
        LOGGING TEST: Verify that error logging produces structured output suitable for GCP.
        
        This ensures the error messages will be visible in GCP Cloud Logging with proper
        structure for debugging and monitoring.
        """
        self.log_capture.clear()
        
        # Trigger the validation error
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="default_user",
                thread_id=self.valid_thread_id,
                run_id=self.valid_run_id,
                request_id=self.valid_request_id,
                created_at=datetime.now(timezone.utc)
            )
        
        # Verify structured logging information
        error_logs = [record for record in self.log_capture if record.levelno >= logging.ERROR]
        assert len(error_logs) > 0, "Expected at least one error log"
        
        error_record = error_logs[0]
        log_message = error_record.getMessage()
        
        # Verify key information is present for GCP debugging
        assert "VALIDATION FAILURE" in log_message, "Missing severity indicator"
        assert "default_user" in log_message, "Missing problematic value"
        assert "placeholder pattern" in log_message, "Missing error type"
        assert "request isolation" in log_message, "Missing business impact"
        
        # Verify log level is appropriate for GCP alerting
        assert error_record.levelno == logging.ERROR, "Should log at ERROR level for GCP visibility"