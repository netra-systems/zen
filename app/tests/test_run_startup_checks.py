"""Tests for the main run_startup_checks function."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.startup_checks import run_startup_checks, StartupCheckResult


class TestRunStartupChecks:
    """Test the main run_startup_checks function."""
    async def test_run_startup_checks_success(self):
        """Test successful startup checks."""
        mock_app = Mock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            mock_checker.run_all_checks = AsyncMock(return_value={
                'success': True, 'total_checks': 10, 'passed': 10,
                'failed_critical': 0, 'failed_non_critical': 0,
                'duration_ms': 1000, 'failures': []
            })
            MockChecker.return_value = mock_checker
            
            results = await run_startup_checks(mock_app)
            
            assert results['success'] == True
            assert results['passed'] == 10
    async def test_run_startup_checks_critical_failure(self):
        """Test startup checks with critical failures."""
        mock_app = Mock()
        
        mock_failure = StartupCheckResult(
            name="critical_check", success=False,
            message="Critical failure", critical=True
        )
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            mock_checker.run_all_checks = AsyncMock(return_value={
                'success': False, 'total_checks': 10, 'passed': 9,
                'failed_critical': 1, 'failed_non_critical': 0,
                'duration_ms': 1000, 'failures': [mock_failure]
            })
            MockChecker.return_value = mock_checker
            
            with pytest.raises(RuntimeError, match="Startup failed: 1 critical checks failed"):
                await run_startup_checks(mock_app)
    async def test_run_startup_checks_non_critical_failure(self):
        """Test startup checks with only non-critical failures."""
        mock_app = Mock()
        
        mock_failure = StartupCheckResult(
            name="non_critical_check", success=False,
            message="Non-critical failure", critical=False
        )
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            mock_checker.run_all_checks = AsyncMock(return_value={
                'success': True, 'total_checks': 10, 'passed': 9,
                'failed_critical': 0, 'failed_non_critical': 1,
                'duration_ms': 1000, 'failures': [mock_failure]
            })
            MockChecker.return_value = mock_checker
            
            results = await run_startup_checks(mock_app)
            
            assert results['success'] == True
            assert results['failed_non_critical'] == 1