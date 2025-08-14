"""
Integration tests for app/startup_checks.py - TestStartupChecker class

This module tests the individual check methods and integration functionality.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupCheckResult, StartupChecker
from app.db.models_postgres import Assistant


class TestStartupChecker:
    """Test the StartupChecker class"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state"""
        app = MagicMock()
        app.state.db_session_factory = MagicMock()
        app.state.redis_manager = AsyncMock()
        app.state.llm_manager = MagicMock()
        return app
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance"""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_run_all_checks_success(self, checker, monkeypatch):
        """Test run_all_checks with all checks passing"""
        self._setup_success_mocks(checker, monkeypatch)
        results = await checker.run_all_checks()
        self._verify_success_results(results)
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_failures(self, checker, monkeypatch):
        """Test run_all_checks with some checks failing"""
        self._setup_failure_mocks(checker, monkeypatch)
        results = await checker.run_all_checks()
        self._verify_failure_results(results)
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_exception(self, checker, monkeypatch):
        """Test run_all_checks when a check raises an exception"""
        self._setup_exception_mocks(checker, monkeypatch)
        results = await checker.run_all_checks()
        self._verify_exception_results(results)
    
    def _setup_success_mocks(self, checker, monkeypatch):
        """Setup mock methods for successful test"""
        async def mock_check():
            checker.results.append(StartupCheckResult(
                name="test_check",
                success=True,
                message="Check passed"
            ))
        
        self._patch_all_check_methods(monkeypatch, checker, mock_check)
    
    def _setup_failure_mocks(self, checker, monkeypatch):
        """Setup mock methods for failure test"""
        async def mock_success():
            checker.results.append(StartupCheckResult(
                name="success_check", success=True, message="Check passed"
            ))
        
        async def mock_critical_failure():
            checker.results.append(StartupCheckResult(
                name="critical_failure", success=False, 
                message="Critical failure", critical=True
            ))
        
        async def mock_non_critical_failure():
            checker.results.append(StartupCheckResult(
                name="non_critical_failure", success=False,
                message="Non-critical failure", critical=False
            ))
        
        monkeypatch.setattr(checker, 'check_environment_variables', mock_success)
        monkeypatch.setattr(checker, 'check_configuration', mock_critical_failure)
        monkeypatch.setattr(checker, 'check_file_permissions', mock_non_critical_failure)
        
        # Set remaining methods to success
        for method_name in ['check_database_connection', 'check_redis', 
                           'check_clickhouse', 'check_llm_providers',
                           'check_memory_and_resources', 'check_network_connectivity',
                           'check_or_create_assistant']:
            monkeypatch.setattr(checker, method_name, mock_success)
    
    def _setup_exception_mocks(self, checker, monkeypatch):
        """Setup mock methods for exception test"""
        async def mock_raise_exception():
            raise RuntimeError("Unexpected error")
        
        monkeypatch.setattr(checker, 'check_environment_variables', mock_raise_exception)
        
        # Mock remaining methods to prevent execution
        for method_name in ['check_configuration', 'check_file_permissions', 
                           'check_database_connection', 'check_redis', 
                           'check_clickhouse', 'check_llm_providers',
                           'check_memory_and_resources', 'check_network_connectivity',
                           'check_or_create_assistant']:
            monkeypatch.setattr(checker, method_name, AsyncMock())
    
    def _patch_all_check_methods(self, monkeypatch, checker, mock_func):
        """Patch all check methods with the same mock function"""
        method_names = [
            'check_environment_variables', 'check_configuration',
            'check_file_permissions', 'check_database_connection',
            'check_redis', 'check_clickhouse', 'check_llm_providers',
            'check_memory_and_resources', 'check_network_connectivity',
            'check_or_create_assistant'
        ]
        
        for method_name in method_names:
            monkeypatch.setattr(checker, method_name, mock_func)
    
    def _verify_success_results(self, results):
        """Verify successful results structure"""
        assert results['success'] is True
        assert results['total_checks'] == 10
        assert results['passed'] == 10
        assert results['failed_critical'] == 0
        assert results['failed_non_critical'] == 0
        assert results['duration_ms'] > 0
        assert len(results['results']) == 10
        assert len(results['failures']) == 0
    
    def _verify_failure_results(self, results):
        """Verify failure results structure"""
        assert results['success'] is False
        assert results['total_checks'] == 10
        assert results['passed'] == 8
        assert results['failed_critical'] == 1
        assert results['failed_non_critical'] == 1
        assert len(results['failures']) == 2
    
    def _verify_exception_results(self, results):
        """Verify exception results structure"""
        assert results['failed_critical'] >= 1
        assert any('Unexpected error' in r.message for r in results['results'])