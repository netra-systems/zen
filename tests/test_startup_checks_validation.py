"""
Validation tests for app/startup_checks.py - Main function and logging tests

This module tests the run_startup_checks function and logging functionality.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupCheckResult, run_startup_checks


class TestRunStartupChecks:
    """Test the run_startup_checks function"""
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_success(self):
        """Test run_startup_checks with all checks passing"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = self._setup_successful_checker(MockChecker)
            results = await run_startup_checks(mock_app)
            self._verify_successful_results(results)
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_critical_failure(self):
        """Test run_startup_checks with critical failures"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = self._setup_critical_failure_checker(MockChecker)
            
            with pytest.raises(RuntimeError) as exc_info:
                await run_startup_checks(mock_app)
            
            self._verify_critical_failure_exception(exc_info)
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_non_critical_failure(self):
        """Test run_startup_checks with only non-critical failures"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = self._setup_non_critical_failure_checker(MockChecker)
            results = await run_startup_checks(mock_app)
            self._verify_non_critical_results(results)
    
    def _setup_successful_checker(self, MockChecker):
        """Setup mock checker for successful test"""
        mock_checker = AsyncMock()
        MockChecker.return_value = mock_checker
        mock_checker.run_all_checks.return_value = {
            'success': True,
            'total_checks': 10,
            'passed': 10,
            'failed_critical': 0,
            'failed_non_critical': 0,
            'duration_ms': 100.0,
            'results': [],
            'failures': []
        }
        return mock_checker
    
    def _setup_critical_failure_checker(self, MockChecker):
        """Setup mock checker for critical failure test"""
        mock_checker = AsyncMock()
        MockChecker.return_value = mock_checker
        mock_failure = self._create_critical_failure()
        mock_checker.run_all_checks.return_value = {
            'success': False,
            'total_checks': 10,
            'passed': 9,
            'failed_critical': 1,
            'failed_non_critical': 0,
            'duration_ms': 100.0,
            'results': [mock_failure],
            'failures': [mock_failure]
        }
        return mock_checker
    
    def _setup_non_critical_failure_checker(self, MockChecker):
        """Setup mock checker for non-critical failure test"""
        mock_checker = AsyncMock()
        MockChecker.return_value = mock_checker
        mock_failure = self._create_non_critical_failure()
        mock_checker.run_all_checks.return_value = {
            'success': True,
            'total_checks': 10,
            'passed': 9,
            'failed_critical': 0,
            'failed_non_critical': 1,
            'duration_ms': 100.0,
            'results': [mock_failure],
            'failures': [mock_failure]
        }
        return mock_checker
    
    def _create_critical_failure(self):
        """Create a critical failure result"""
        return StartupCheckResult(
            name="critical_check",
            success=False,
            message="Critical failure",
            critical=True
        )
    
    def _create_non_critical_failure(self):
        """Create a non-critical failure result"""
        return StartupCheckResult(
            name="non_critical_check",
            success=False,
            message="Non-critical failure",
            critical=False
        )
    
    def _verify_successful_results(self, results):
        """Verify successful results structure"""
        assert results['success'] is True
        assert results['passed'] == 10
        assert results['failed_critical'] == 0
    
    def _verify_critical_failure_exception(self, exc_info):
        """Verify critical failure exception"""
        assert "Startup failed" in str(exc_info.value)
        assert "1 critical checks failed" in str(exc_info.value)
    
    def _verify_non_critical_results(self, results):
        """Verify non-critical failure results"""
        assert results['success'] is True
        assert results['failed_non_critical'] == 1


class TestLoggingAndReporting:
    """Test that logging is called correctly"""
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_logs_results(self):
        """Test that run_startup_checks logs results correctly"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = self._setup_logging_checker(MockChecker)
            
            with patch('app.startup_checks.logger') as mock_logger:
                results = await run_startup_checks(mock_app)
                self._verify_info_logging(mock_logger)
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_logs_warnings(self):
        """Test that run_startup_checks logs warnings for non-critical failures"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = self._setup_warning_checker(MockChecker)
            
            with patch('app.startup_checks.logger') as mock_logger:
                results = await run_startup_checks(mock_app)
                self._verify_warning_logging(mock_logger)
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_logs_errors(self):
        """Test that run_startup_checks logs errors for critical failures"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = self._setup_error_checker(MockChecker)
            
            with patch('app.startup_checks.logger') as mock_logger:
                try:
                    await run_startup_checks(mock_app)
                except RuntimeError:
                    pass  # Expected
                
                self._verify_error_logging(mock_logger)
    
    def _setup_logging_checker(self, MockChecker):
        """Setup checker for logging test"""
        mock_checker = AsyncMock()
        MockChecker.return_value = mock_checker
        mock_checker.run_all_checks.return_value = {
            'success': True,
            'total_checks': 10,
            'passed': 10,
            'failed_critical': 0,
            'failed_non_critical': 0,
            'duration_ms': 123.45,
            'results': [],
            'failures': []
        }
        return mock_checker
    
    def _setup_warning_checker(self, MockChecker):
        """Setup checker for warning test"""
        mock_checker = AsyncMock()
        MockChecker.return_value = mock_checker
        
        mock_failure = StartupCheckResult(
            name="non_critical_check",
            success=False,
            message="Non-critical warning",
            critical=False
        )
        
        mock_checker.run_all_checks.return_value = {
            'success': True,
            'total_checks': 10,
            'passed': 9,
            'failed_critical': 0,
            'failed_non_critical': 1,
            'duration_ms': 100.0,
            'results': [mock_failure],
            'failures': [mock_failure]
        }
        return mock_checker
    
    def _setup_error_checker(self, MockChecker):
        """Setup checker for error test"""
        mock_checker = AsyncMock()
        MockChecker.return_value = mock_checker
        
        mock_failure = StartupCheckResult(
            name="critical_check",
            success=False,
            message="Critical error",
            critical=True
        )
        
        mock_checker.run_all_checks.return_value = {
            'success': False,
            'total_checks': 10,
            'passed': 9,
            'failed_critical': 1,
            'failed_non_critical': 0,
            'duration_ms': 100.0,
            'results': [mock_failure],
            'failures': [mock_failure]
        }
        return mock_checker
    
    def _verify_info_logging(self, mock_logger):
        """Verify info logging calls"""
        assert mock_logger.info.call_count >= 2
        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any('123' in str(call) for call in calls)  # Duration logged
        assert any('10/10' in str(call) for call in calls)  # Results logged
    
    def _verify_warning_logging(self, mock_logger):
        """Verify warning logging calls"""
        assert mock_logger.warning.call_count >= 2
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any('Non-critical' in str(call) for call in warning_calls)
        assert any('non_critical_check' in str(call) for call in warning_calls)
    
    def _verify_error_logging(self, mock_logger):
        """Verify error logging calls"""
        assert mock_logger.error.call_count >= 2
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any('Critical' in str(call) for call in error_calls)
        assert any('critical_check' in str(call) for call in error_calls)