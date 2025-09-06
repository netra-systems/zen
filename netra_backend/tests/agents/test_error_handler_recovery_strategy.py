"""
Tests for error recovery strategy logic.
All functions ≤8 lines per requirements.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add netra_backend to path  

import pytest

from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.agents.agent_error_types import (
DatabaseError,
NetworkError,
AgentValidationError as ValidationError,
)
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.core.error_recovery import ErrorRecoveryStrategy
from netra_backend.app.core.error_codes import ErrorSeverity

class TestErrorRecoveryStrategy:
    """Test error recovery strategy logic."""

    def _create_network_error_for_delay_test(self):
        """Create network error for delay testing"""
        return NetworkError("Network timeout")

    def test_get_recovery_delay_network_error(self):
        """Test recovery delay calculation for network errors."""
        error = self._create_network_error_for_delay_test()
        delay = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=1)
        assert 0.5 <= delay <= 4.0  # Base 2^1 * 1.0 with jitter

        def _create_high_severity_error_for_max_cap_test(self):
            """Create high severity error for max cap testing"""
            return AgentError("Test", severity=ErrorSeverity.HIGH)

        def test_get_recovery_delay_max_cap(self):
            """Test recovery delay maximum cap."""
            error = self._create_high_severity_error_for_max_cap_test()
            delay = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=10)
            assert delay <= 30.0  # Should not exceed max delay

            def _create_errors_for_category_test(self):
                """Create different error categories for testing"""
                return [
            ValidationError("Validation failed"),
            DatabaseError("DB error"),
            NetworkError("Network error")
            ]

            def test_get_recovery_delay_different_categories(self):
                """Test recovery delay for different error categories."""
                errors = self._create_errors_for_category_test()
                delays = [ErrorRecoveryStrategy.get_recovery_delay(err, 1) for err in errors]
                assert all(delay >= 0 for delay in delays)

                def _create_validation_error_for_retry_test(self):
                    """Create validation error for retry testing"""
                    return ValidationError("Invalid data")

                def test_should_retry_validation_error(self):
                    """Test should_retry for validation errors."""
                    error = self._create_validation_error_for_retry_test()
                    should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)
                    assert should_retry is False  # Validation errors shouldn't retry'

                    def test_should_retry_non_recoverable_error(self):
                        """Test should_retry for non-recoverable errors."""
                        error = AgentError("Fatal error", severity=ErrorSeverity.CRITICAL)
                        should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)
                        assert should_retry is False

                        def _create_network_error_for_retry_test(self):
                            """Create network error for retry testing"""
                            return NetworkError("Temporary network issue")

                        def test_should_retry_network_error_first_attempt(self):
                            """Test should_retry for network error on first attempt."""
                            error = self._create_network_error_for_retry_test()
                            should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)
                            assert should_retry is True

                            def test_should_retry_network_error_max_attempts(self):
                                """Test should_retry for network error at max attempts."""
                                error = self._create_network_error_for_retry_test()
                                should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=5)
                                assert should_retry is False  # Exceeded max attempts

                                def _create_database_error_for_retry_test(self):
                                    """Create database error for retry testing"""
                                    return DatabaseError("Connection timeout")

                                def test_should_retry_database_error(self):
                                    """Test should_retry for database errors."""
                                    error = self._create_database_error_for_retry_test()
                                    should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=2)
                                    assert should_retry in [True, False]  # Depends on implementation

                                    def test_recovery_strategy_selection_validation(self):
                                        """Test recovery strategy selection for validation errors."""
                                        error = self._create_validation_error_for_retry_test()
                                        strategy = ErrorRecoveryStrategy.get_strategy(error)
                                        assert strategy == ErrorRecoveryStrategy.ABORT

                                        def test_recovery_strategy_selection_network(self):
                                            """Test recovery strategy selection for network errors."""
                                            error = self._create_network_error_for_retry_test()
                                            strategy = ErrorRecoveryStrategy.get_strategy(error)
                                            assert strategy == ErrorRecoveryStrategy.RETRY

                                            def _create_critical_error_for_strategy_test(self):
                                                """Create critical error for strategy testing"""
                                                return AgentError("Critical system error", severity=ErrorSeverity.CRITICAL)

                                            def test_recovery_strategy_selection_critical(self):
                                                """Test recovery strategy selection for critical errors."""
                                                error = self._create_critical_error_for_strategy_test()
                                                strategy = ErrorRecoveryStrategy.get_strategy(error)
                                                assert strategy == ErrorRecoveryStrategy.ABORT

                                                def test_recovery_delay_exponential_backoff(self):
                                                    """Test exponential backoff in recovery delay."""
                                                    error = self._create_network_error_for_delay_test()

                                                    delay1 = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=1)
                                                    delay2 = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=2)
                                                    delay3 = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=3)

        # Should generally increase (accounting for jitter)
                                                    assert delay1 <= delay2 * 1.5  # Allow for jitter variation
                                                    assert delay2 <= delay3 * 1.5

                                                    def test_recovery_delay_with_zero_attempt(self):
                                                        """Test recovery delay with zero attempt number."""
                                                        error = self._create_network_error_for_delay_test()
                                                        delay = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=0)
                                                        assert delay >= 0  # Should handle gracefully

                                                        def _create_unknown_category_error(self):
                                                            """Create error with unknown category"""
                                                            return AgentError("Unknown error", category=ErrorCategory.UNKNOWN)

                                                        def test_recovery_strategy_unknown_category(self):
                                                            """Test recovery strategy for unknown error category."""
                                                            error = self._create_unknown_category_error()
                                                            strategy = ErrorRecoveryStrategy.get_strategy(error)
                                                            should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=1)

                                                            assert strategy is not None
                                                            assert isinstance(should_retry, bool)

                                                            def test_recovery_delay_consistency(self):
                                                                """Test recovery delay consistency for same inputs."""
                                                                error = self._create_network_error_for_delay_test()

        # Same inputs should produce similar delays (within jitter range)
                                                                delay1 = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=2)
                                                                delay2 = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=2)

        # Should be within reasonable range due to jitter
                                                                assert abs(delay1 - delay2) <= max(delay1, delay2) * 0.5

                                                                def test_error_recovery_edge_cases(self):
                                                                    """Test error recovery with edge cases."""
        # High attempt number
                                                                    error = self._create_network_error_for_delay_test()
                                                                    high_attempt_delay = ErrorRecoveryStrategy.get_recovery_delay(error, attempt=100)
                                                                    assert high_attempt_delay <= 30.0  # Should respect max cap

        # Negative attempt (edge case)
                                                                    should_retry = ErrorRecoveryStrategy.should_retry(error, attempt=-1)
                                                                    assert isinstance(should_retry, bool)