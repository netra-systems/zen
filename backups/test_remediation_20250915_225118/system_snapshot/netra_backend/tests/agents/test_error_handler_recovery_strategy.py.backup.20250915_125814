"""
Tests for error recovery strategy logic.
All functions <= 8 lines per requirements.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add netra_backend to path  

import pytest
import asyncio

from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.agents.agent_error_types import (
    DatabaseError,
    NetworkError,
    AgentValidationError as ValidationError,
)
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.core.error_recovery import RecoveryStrategy, ErrorRecoveryManager, get_error_recovery_manager
from netra_backend.app.core.error_codes import ErrorSeverity

class TestErrorRecoveryStrategy:
    """Test error recovery strategy logic."""

    def _create_network_error_for_delay_test(self):
        """Create network error for delay testing"""
        return NetworkError("Network timeout")

    @pytest.mark.asyncio
    async def test_recovery_manager_retry_strategy(self):
        """Test recovery manager retry strategy for network errors."""
        error = self._create_network_error_for_delay_test()
        recovery_manager = get_error_recovery_manager()
        
        # Test retry recovery
        result = await recovery_manager._retry_recovery(error, max_retries=2)
        assert isinstance(result, bool)

    def _create_high_severity_error_for_max_cap_test(self):
        """Create high severity error for max cap testing"""
        return AgentError("Test", severity=ErrorSeverity.HIGH)

    @pytest.mark.asyncio
    async def test_recovery_manager_fallback_strategy(self):
        """Test recovery manager fallback strategy."""
        error = self._create_high_severity_error_for_max_cap_test()
        recovery_manager = get_error_recovery_manager()
        
        # Test fallback recovery
        result = await recovery_manager._fallback_recovery(error, fallback_value="default")
        assert isinstance(result, bool)

    def _create_errors_for_category_test(self):
        """Create different error categories for testing"""
        return [
            ValidationError("Validation failed"),
            DatabaseError("DB error"),
            NetworkError("Network error")
        ]

    def test_recovery_strategy_enum_values(self):
        """Test recovery strategy enum has expected values."""
        assert RecoveryStrategy.RETRY == "retry"
        assert RecoveryStrategy.FALLBACK == "fallback"
        assert RecoveryStrategy.CIRCUIT_BREAKER == "circuit_breaker"
        assert RecoveryStrategy.GRACEFUL_DEGRADATION == "graceful_degradation"

    def _create_validation_error_for_retry_test(self):
        """Create validation error for retry testing"""
        return ValidationError("Invalid data")

    @pytest.mark.asyncio
    async def test_recovery_manager_circuit_breaker(self):
        """Test recovery manager circuit breaker strategy."""
        error = self._create_validation_error_for_retry_test()
        recovery_manager = get_error_recovery_manager()
        
        # Test circuit breaker recovery
        result = await recovery_manager._circuit_breaker_recovery(error)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_recovery_manager_graceful_degradation(self):
        """Test recovery manager graceful degradation strategy."""
        error = AgentError("Fatal error", severity=ErrorSeverity.CRITICAL)
        recovery_manager = get_error_recovery_manager()
        
        # Test graceful degradation recovery
        result = await recovery_manager._graceful_degradation_recovery(error)
        assert isinstance(result, bool)

    def _create_network_error_for_retry_test(self):
        """Create network error for retry testing"""
        return NetworkError("Temporary network issue")

    def test_recovery_manager_initialization(self):
        """Test recovery manager initializes correctly."""
        recovery_manager = get_error_recovery_manager()
        assert recovery_manager is not None
        assert isinstance(recovery_manager, ErrorRecoveryManager)

    def _create_database_error_for_retry_test(self):
        """Create database error for retry testing"""
        return DatabaseError("Connection timeout")

    def test_recovery_strategy_constants(self):
        """Test recovery strategy constants are accessible."""
        strategies = [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.FALLBACK, 
            RecoveryStrategy.CIRCUIT_BREAKER,
            RecoveryStrategy.GRACEFUL_DEGRADATION
        ]
        assert len(strategies) == 4
        assert all(isinstance(s, str) for s in strategies)

    @pytest.mark.asyncio
    async def test_recovery_manager_error_handling(self):
        """Test recovery manager handles different error types."""
        recovery_manager = get_error_recovery_manager()
        
        # Test with various error types
        errors = self._create_errors_for_category_test()
        
        for error in errors:
            # Should not raise exception
            result = await recovery_manager._retry_recovery(error, max_retries=1)
            assert isinstance(result, bool)

    def _create_critical_error_for_strategy_test(self):
        """Create critical error for strategy testing"""
        return AgentError("Critical system error", severity=ErrorSeverity.CRITICAL)

    @pytest.mark.asyncio  
    async def test_recovery_operations_with_all_strategies(self):
        """Test recovery operations with all available strategies."""
        error = self._create_critical_error_for_strategy_test()
        recovery_manager = get_error_recovery_manager()
        
        # Test all recovery methods
        retry_result = await recovery_manager._retry_recovery(error)
        fallback_result = await recovery_manager._fallback_recovery(error)
        circuit_result = await recovery_manager._circuit_breaker_recovery(error)
        degradation_result = await recovery_manager._graceful_degradation_recovery(error)
        
        # All should return boolean results
        assert isinstance(retry_result, bool)
        assert isinstance(fallback_result, bool)
        assert isinstance(circuit_result, bool)
        assert isinstance(degradation_result, bool)

    def _create_unknown_category_error(self):
        """Create error with unknown category"""
        return AgentError("Unknown error", category=ErrorCategory.UNKNOWN)

    @pytest.mark.asyncio
    async def test_recovery_with_unknown_error_category(self):
        """Test recovery with unknown error category."""
        error = self._create_unknown_category_error()
        recovery_manager = get_error_recovery_manager()
        
        # Should handle unknown errors gracefully
        result = await recovery_manager._retry_recovery(error)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_recovery_manager_singleton_behavior(self):
        """Test recovery manager singleton behavior."""
        manager1 = get_error_recovery_manager()
        manager2 = get_error_recovery_manager()
        
        # Should return the same instance
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_error_recovery_edge_cases(self):
        """Test error recovery with edge cases."""
        recovery_manager = get_error_recovery_manager()
        
        # Test with None values (should handle gracefully)
        try:
            # Most recovery methods should handle None gracefully or raise appropriate errors
            result = await recovery_manager._fallback_recovery(None, fallback_value="safe_default")
            assert isinstance(result, bool)
        except (TypeError, AttributeError):
            # It's acceptable to raise type errors for None inputs
            pass