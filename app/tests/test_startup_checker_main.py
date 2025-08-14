"""Tests for StartupChecker main functionality."""

import pytest
from unittest.mock import Mock, AsyncMock

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import (
    create_mock_app, setup_all_check_mocks, mock_successful_check,
    mock_critical_failure_check, mock_non_critical_failure_check,
    mock_exception_check, verify_check_results
)


class TestStartupCheckerMain:
    """Test StartupChecker main functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_run_all_checks_success(self, checker):
        """Test running all checks successfully."""
        async def mock_check():
            checker.results.append(create_success_check_result())
        
        setup_all_check_mocks(checker, mock_check)
        
        results = await checker.run_all_checks()
        
        assert results["success"] == True
        verify_check_results(results, 10, 10, 0, 0)
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_failures(self, checker):
        """Test running checks with critical and non-critical failures."""
        async def mock_critical_failure():
            checker.results.append(create_failure_check_result("critical_check", True))
        
        async def mock_non_critical_failure():
            checker.results.append(create_failure_check_result("non_critical_check", False))
        
        checker.check_environment_variables = AsyncMock(side_effect=mock_critical_failure)
        checker.check_configuration = AsyncMock(side_effect=mock_non_critical_failure)
        
        # Setup remaining checks as empty
        for attr in ['check_file_permissions', 'check_database_connection',
                    'check_redis', 'check_clickhouse', 'check_llm_providers',
                    'check_memory_and_resources', 'check_network_connectivity',
                    'check_or_create_assistant']:
            setattr(checker, attr, AsyncMock())
        
        results = await checker.run_all_checks()
        
        assert results["success"] == False
        assert results["failed_critical"] == 1
        assert results["failed_non_critical"] == 1
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_exception(self, checker):
        """Test handling of unexpected exceptions during checks."""
        checker.check_environment_variables = AsyncMock(side_effect=mock_exception_check)
        
        # Setup remaining checks as empty
        for attr in ['check_configuration', 'check_file_permissions',
                    'check_database_connection', 'check_redis', 'check_clickhouse',
                    'check_llm_providers', 'check_memory_and_resources',
                    'check_network_connectivity', 'check_or_create_assistant']:
            setattr(checker, attr, AsyncMock())
        
        results = await checker.run_all_checks()
        
        assert results["success"] == False
        assert results["failed_critical"] == 1
        assert "Unexpected error" in results["failures"][0].message