"""
Basic tests for app/startup_checks.py - StartupCheckResult class and basic functionality

This module tests the core data structures and basic functionality.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupCheckResult


class TestStartupCheckResult:
    """Test the StartupCheckResult class"""
    
    def test_init_required_params(self):
        """Test initialization with required parameters"""
        result = self._create_basic_result()
        self._verify_basic_result(result)
    
    def test_init_all_params(self):
        """Test initialization with all parameters"""
        result = self._create_full_result()
        self._verify_full_result(result)
    
    def _create_basic_result(self) -> StartupCheckResult:
        """Create result with required parameters only"""
        return StartupCheckResult(
            name="test_check",
            success=True,
            message="Test passed"
        )
    
    def _verify_basic_result(self, result: StartupCheckResult) -> None:
        """Verify basic result properties"""
        assert result.name == "test_check"
        assert result.success is True
        assert result.message == "Test passed"
        assert result.critical is True  # Default value
        assert result.duration_ms == 0  # Default value
    
    def _create_full_result(self) -> StartupCheckResult:
        """Create result with all parameters"""
        return StartupCheckResult(
            name="test_check",
            success=False,
            message="Test failed",
            critical=False,
            duration_ms=123.45
        )
    
    def _verify_full_result(self, result: StartupCheckResult) -> None:
        """Verify full result properties"""
        assert result.name == "test_check"
        assert result.success is False
        assert result.message == "Test failed"
        assert result.critical is False
        assert result.duration_ms == 123.45