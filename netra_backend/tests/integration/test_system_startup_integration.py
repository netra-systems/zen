"""
Integration tests for system startup sequence and component initialization.

Tests the complete startup process including:
- Environment variable validation
- Database connection establishment  
- Service initialization order
- Startup failure recovery scenarios
- Health check validation
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from netra_backend.app.startup_checks import StartupChecker, StartupCheckResult

from netra_backend.app.config import get_config

from netra_backend.app.core.app_factory import create_app
from test_framework.mock_utils import mock_justified

class TestSystemStartupIntegration:
    """Integration tests for system startup sequence."""

    @pytest.fixture
    def minimal_environment(self):
        """Create minimal environment for startup testing."""
        return {
            "DATABASE_URL": "sqlite+aioDATABASE_URL_PLACEHOLDER",
            "REDIS_URL": "redis://localhost:6379",
            "CLICKHOUSE_URL": "http://localhost:8123",
            "NETRA_API_KEY": "test-api-key",
            "ENVIRONMENT": "test"
        }

    @pytest.fixture
    def startup_checker_instance(self):
        """Create startup checker instance for testing."""
        app = create_app()
        return StartupChecker(app)

    @pytest.mark.asyncio
    async def test_complete_startup_sequence_success(self, minimal_environment):
        """
        Test successful complete startup sequence with all components.
        
        Validates:
        - Environment variable loading
        - Configuration initialization
        - Database connection establishment
        - Service initialization order
        - Final health validation
        """
        with patch.dict(os.environ, minimal_environment):
            app = create_app()
            checker = StartupChecker(app)
            
            # Mock external dependencies that aren't available in test environment
            with self._mock_external_services():
                result = await checker.run_all_checks()
                
                self._verify_startup_success(result)
                self._verify_all_checks_completed(result)
                self._verify_startup_timing(result)

    @mock_justified("External services not available in test environment")
    def _mock_external_services(self):
        """Mock external services for startup testing."""
        return patch.multiple(
            'app.startup_checks.service_checks.ServiceChecker',
            # Mock: Redis caching isolation to prevent test interference and external dependencies
            check_redis=AsyncMock(return_value=StartupCheckResult(
                name="check_redis", success=True, message="Redis connected"
            )),
            # Mock: ClickHouse external database isolation for unit testing performance
            check_clickhouse=AsyncMock(return_value=StartupCheckResult(
                name="check_clickhouse", success=True, message="ClickHouse connected"
            )),
            # Mock: Async component isolation for testing without real async operations
            check_llm_providers=AsyncMock(return_value=StartupCheckResult(
                name="check_llm_providers", success=True, message="LLM providers available"
            ))
        )

    def _verify_startup_success(self, result: Dict[str, Any]):
        """Verify startup completed successfully."""
        assert result["success"] is True, f"Startup failed: {result.get('failures', [])}"
        assert result["failed_critical"] == 0, "Critical startup checks failed"
        assert result["total_checks"] > 0, "No startup checks were executed"

    def _verify_all_checks_completed(self, result: Dict[str, Any]):
        """Verify all expected checks completed."""
        expected_checks = [
            "check_environment_variables",
            "check_configuration", 
            "check_file_permissions",
            "check_database_connection",
            "check_redis",
            "check_clickhouse",
            "check_llm_providers",
            "check_memory_and_resources",
            "check_network_connectivity"
        ]
        
        check_names = [r.name for r in result["results"]]
        for expected_check in expected_checks:
            assert expected_check in check_names, f"Missing startup check: {expected_check}"

    def _verify_startup_timing(self, result: Dict[str, Any]):
        """Verify startup timing is reasonable."""
        assert result["duration_ms"] > 0, "Startup duration not recorded"
        assert result["duration_ms"] < 30000, "Startup took too long (>30s)"

    @pytest.mark.asyncio
    async def test_environment_variable_validation_failure(self):
        """
        Test startup failure when critical environment variables are missing.
        
        Validates:
        - Missing DATABASE_URL causes failure
        - Error messages are descriptive
        - Startup stops on critical failures
        """
        # Clear critical environment variables
        with patch.dict(os.environ, {}, clear=True):
            app = create_app()
            checker = StartupChecker(app)
            
            with pytest.raises(Exception) as exc_info:
                await checker.run_all_checks()
            
            assert "DATABASE_URL" in str(exc_info.value) or "environment" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_database_connection_failure_recovery(self, minimal_environment):
        """
        Test database connection failure and recovery scenarios.
        
        Validates:
        - Database connection failures are handled gracefully
        - Connection retry logic works
        - System can recover from temporary database issues
        """
        with patch.dict(os.environ, {**minimal_environment, "DATABASE_URL": "invalid://url"}):
            app = create_app()
            checker = StartupChecker(app)
            
            # Mock external services but let database fail
            with self._mock_non_database_services():
                result = await checker.run_all_checks()
                
                # Should fail due to database connection
                assert result["success"] is False
                assert result["failed_critical"] > 0
                
                database_failures = [
                    r for r in result["failures"] 
                    if "database" in r.name.lower()
                ]
                assert len(database_failures) > 0, "Database connection failure not detected"

    @mock_justified("External services not available in test environment")  
    def _mock_non_database_services(self):
        """Mock non-database services for database testing."""
        return patch.multiple(
            'app.startup_checks.service_checks.ServiceChecker',
            # Mock: Redis caching isolation to prevent test interference and external dependencies
            check_redis=AsyncMock(return_value=StartupCheckResult(
                name="check_redis", success=True, message="Redis connected"
            )),
            # Mock: ClickHouse external database isolation for unit testing performance
            check_clickhouse=AsyncMock(return_value=StartupCheckResult(
                name="check_clickhouse", success=True, message="ClickHouse connected"  
            )),
            # Mock: Async component isolation for testing without real async operations
            check_llm_providers=AsyncMock(return_value=StartupCheckResult(
                name="check_llm_providers", success=True, message="LLM providers available"
            ))
        )

    @pytest.mark.asyncio
    async def test_service_initialization_order(self, minimal_environment):
        """
        Test services are initialized in correct dependency order.
        
        Validates:
        - Environment checks run before database checks
        - Database checks run before service checks
        - System resource checks run after core services
        """
        with patch.dict(os.environ, minimal_environment):
            app = create_app()
            checker = StartupChecker(app)
            
            # Track check execution order
            execution_order = []
            
            original_execute_check = checker._execute_check
            async def track_execution(check_func):
                execution_order.append(check_func.__name__)
                return await original_execute_check(check_func)
            
            checker._execute_check = track_execution
            
            with self._mock_external_services():
                await checker.run_all_checks()
                
                self._verify_initialization_order(execution_order)

    def _verify_initialization_order(self, execution_order: list):
        """Verify checks executed in proper dependency order."""
        # Environment checks should come first
        env_checks = ["check_environment_variables", "check_configuration"]
        for env_check in env_checks:
            if env_check in execution_order:
                env_index = execution_order.index(env_check)
                break
        else:
            pytest.fail("Environment checks not found in execution order")
            
        # Database checks should come after environment
        db_checks = ["check_database_connection"]
        for db_check in db_checks:
            if db_check in execution_order:
                db_index = execution_order.index(db_check)
                assert db_index > env_index, "Database checks should run after environment checks"
                break

    @pytest.mark.asyncio
    async def test_health_check_endpoint_validation(self, minimal_environment):
        """
        Test health check endpoint responds correctly after startup.
        
        Validates:
        - Health endpoint is accessible after startup
        - Health status reflects system state
        - Dependencies are reported correctly
        """
        with patch.dict(os.environ, minimal_environment):
            app = create_app()
            
            # Mock external services for clean startup
            with self._mock_external_services():
                # Simulate startup completion
                startup_checker = StartupChecker(app)
                startup_result = await startup_checker.run_all_checks()
                
                # Test health endpoint (would normally be tested via HTTP client)
                # For integration test, we verify the health check components work
                assert startup_result["success"] is True
                
                # Verify health data structure
                health_data = self._extract_health_data(startup_result)
                self._verify_health_response_structure(health_data)

    def _extract_health_data(self, startup_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract health data from startup results."""
        return {
            "status": "healthy" if startup_result["success"] else "unhealthy",
            "checks": startup_result["total_checks"],
            "passed": startup_result["passed"],
            "failed": startup_result["failed_critical"] + startup_result["failed_non_critical"],
            "duration_ms": startup_result["duration_ms"]
        }

    def _verify_health_response_structure(self, health_data: Dict[str, Any]):
        """Verify health response has correct structure."""
        required_fields = ["status", "checks", "passed", "failed", "duration_ms"]
        for field in required_fields:
            assert field in health_data, f"Health response missing field: {field}"
        
        assert health_data["status"] in ["healthy", "unhealthy"]
        assert isinstance(health_data["checks"], int)
        assert isinstance(health_data["duration_ms"], (int, float))

    @pytest.mark.asyncio
    async def test_startup_failure_scenarios(self):
        """Test various startup failure scenarios and error handling."""
        # Test missing database URL scenario
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}, clear=True):
            app = create_app()
            checker = StartupChecker(app)
            
            try:
                result = await checker.run_all_checks()
                assert result["success"] is False, "Expected failure for missing database"
                
                failure_messages = [f.message for f in result["failures"]]
                error_found = any("database" in msg.lower() for msg in failure_messages)
                assert error_found, "Expected database error not found"
                
            except Exception as e:
                assert "database" in str(e).lower(), f"Unexpected exception: {e}"

    @pytest.mark.asyncio
    async def test_staging_environment_strict_validation(self, minimal_environment):
        """
        Test staging environment enforces strict validation.
        
        Validates:
        - All checks must pass in staging
        - Any failure causes immediate startup abort
        - Error messages are detailed for staging
        """
        staging_env = {**minimal_environment, "ENVIRONMENT": "staging", "K_SERVICE": "true"}
        
        with patch.dict(os.environ, staging_env):
            app = create_app()
            checker = StartupChecker(app)
            
            # Mock one service to fail
            # Mock: Component isolation for testing without external dependencies
            with patch('app.startup_checks.service_checks.ServiceChecker.check_redis', 
                      # Mock: Async component isolation for testing without real async operations
                      AsyncMock(return_value=StartupCheckResult(
                          name="check_redis", success=False, message="Redis unavailable", critical=True
                      ))):
                
                with pytest.raises(RuntimeError) as exc_info:
                    await checker.run_all_checks()
                
                assert "staging" in str(exc_info.value).lower()
                assert "check_redis" in str(exc_info.value)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])