"""Tests for StartupCheckResult class."""

import pytest
from app.startup_checks import StartupCheckResult


class TestStartupCheckResult:
    """Test StartupCheckResult class."""
    
    def test_initialization(self):
        """Test StartupCheckResult initialization with all parameters."""
        result = StartupCheckResult(
            name="test_check", success=True, message="Test passed",
            critical=False, duration_ms=123.45
        )
        
        assert result.name == "test_check"
        assert result.success == True
        assert result.message == "Test passed"
        assert result.critical == False
        assert result.duration_ms == 123.45
    
    def test_default_values(self):
        """Test StartupCheckResult with default values."""
        result = StartupCheckResult(
            name="test", success=False, message="Failed"
        )
        
        assert result.critical == True
        assert result.duration_ms == 0