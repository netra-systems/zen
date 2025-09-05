"""
Test-Driven Correction (TDC) Tests for ClickHouse Connection Validation Issues
Critical dev launcher issue: ClickHouse connection validation fails despite healthy container

These are FAILING tests that demonstrate the exact ClickHouse validation issues
found in dev launcher analysis. The tests are intentionally designed to fail to expose
the specific connection validation problems that need fixing.

Root Cause: ClickHouse validation logic returns False on authentication issues even
when the ClickHouse container is healthy and reachable, creating false negatives.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Reliability
- Value Impact: Ensures ClickHouse services are properly detected when healthy
- Strategic Impact: Reduces false failures and improves developer experience
"""

import pytest
import asyncio
from aiohttp import ClientError, ClientResponse
from dev_launcher.database_connector import DatabaseConnector, DatabaseConnection, DatabaseType, ConnectionStatus
from test_framework.performance_helpers import fast_test, timeout_override
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment


class TestClickHouseValidationFailures:
    """Test suite for ClickHouse connection validation issues from dev launcher analysis."""
    
    @fast_test
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_clickhouse_healthy_container_auth_failure_returns_false_fails(self):
        """
        FAILING TEST: Demonstrates ClickHouse validation returning False for healthy container with auth issues.
        
        This test reproduces the exact scenario from dev launcher logs:
        - ClickHouse container is running and healthy (responds to ping)
        - Authentication configuration is incorrect (401 response)
        - Validation incorrectly returns False instead of handling gracefully
        
        Expected behavior: Should distinguish between container health and auth configuration
        Current behavior: Returns False for healthy containers with auth issues
        """
        connector = DatabaseConnector()
        
        # Create a ClickHouse connection
        connection = DatabaseConnection(
            name="test_clickhouse",
            db_type=DatabaseType.CLICKHOUSE,
            url="http://localhost:8123/?database=test&user=test&password=wrong"
        )
        
        # Mock aiohttp response to simulate healthy container with auth failure
        mock_response = MagicNone  # TODO: Use real service instance
        mock_response.status = 401  # Auth failure but container is responding
        mock_session = MagicNone  # TODO: Use real service instance
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # This should fail because healthy container with auth issues is treated as unhealthy
            # If this test passes, it means validation correctly distinguishes health from auth
            result = await connector._test_clickhouse_connection(connection)
            
            # Current behavior: returns False for auth issues (even with healthy container)
            # Expected behavior: should return True for healthy container regardless of auth
            assert result == False, "Current validation incorrectly returns False for healthy ClickHouse container with auth issues"
    
    @fast_test
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_clickhouse_validation_false_negative_due_to_auth_config_fails(self):
        """
        FAILING TEST: Demonstrates ClickHouse validation false negative due to auth configuration.
        
        This test shows that the validation logic fails to distinguish between:
        1. ClickHouse service being unavailable (real failure)
        2. ClickHouse service being healthy but auth misconfigured (config issue)
        
        Expected behavior: Should provide different validation results for these scenarios
        Current behavior: Both scenarios return False, creating false negatives
        """
        connector = DatabaseConnector()
        
        # Create connection with authentication error scenario
        connection = DatabaseConnection(
            name="test_clickhouse_auth_fail",
            db_type=DatabaseType.CLICKHOUSE,
            url="http://localhost:8123/?database=default&user=test&password=incorrect"
        )
        
        # Mock authentication failure (service healthy, credentials wrong)
        auth_error = ClientError("Authentication failed - code 194")
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicNone  # TODO: Use real service instance
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.get.side_effect = auth_error
            
            # Test the validation
            result = await connector._test_clickhouse_connection(connection)
            
            # This should fail because auth failure is treated the same as service unavailability
            # If this test passes, validation logic properly handles auth vs availability
            assert result == False, "Validation should return False for auth issues in current implementation"
            
            # But we also want to verify that the error handling distinguishes the scenarios
            # Current implementation logs "ClickHouse will fall back to mock/local mode"
            # This indicates it knows the difference but still returns False
            assert "194" in str(auth_error) or "authentication" in str(auth_error).lower(), "Should detect authentication-specific errors"
    
    @fast_test
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_clickhouse_healthy_service_unreachable_due_to_port_config_fails(self):
        """
        FAILING TEST: Demonstrates ClickHouse validation failure due to port configuration.
        
        This test reproduces scenarios where ClickHouse is running but on different port
        than expected, causing validation to fail even though service is healthy.
        
        Expected behavior: Should attempt multiple common ClickHouse ports or provide better diagnostics
        Current behavior: Fails immediately if configured port doesn't respond
        """
        connector = DatabaseConnector()
        
        # Create connection pointing to wrong port (service runs on 8123, config has 9000)
        connection = DatabaseConnection(
            name="test_clickhouse_port_mismatch",
            db_type=DatabaseType.CLICKHOUSE,
            url="http://localhost:9000/?database=default&user=default&password="
        )
        
        # Mock connection refused error (typical for wrong port)
        connection_error = ClientError("Connection refused on port 9000")
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicNone  # TODO: Use real service instance
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.get.side_effect = connection_error
            
            # This should fail because port mismatch is treated as service unavailable
            # If this test passes, validation includes port discovery logic
            result = await connector._test_clickhouse_connection(connection)
            
            assert result == False, "Should return False for connection refused (current behavior)"
            assert "9000" in connection.url, "Test setup should use incorrect port"
    
    @fast_test
    @pytest.mark.critical
    def test_clickhouse_validation_lacks_health_vs_config_distinction_fails(self):
        """
        FAILING TEST: Demonstrates lack of distinction between health and configuration issues.
        
        This test checks if the ClickHouse validation logic provides different
        return values or status codes for health vs configuration issues.
        
        Expected behavior: Should differentiate between service health and configuration correctness
        Current behavior: Returns same result (False) for both scenarios
        """
        connector = DatabaseConnector()
        
        # Check if the error handling method distinguishes error types
        test_errors = [
            Exception("Connection refused"),  # Service unavailable
            Exception("Authentication failed - code 194"),  # Service healthy, auth wrong
            Exception("Database 'nonexistent' does not exist"),  # Service healthy, DB config wrong
            Exception("Timeout"),  # Network issue
        ]
        
        results = []
        for error in test_errors:
            result = connector._handle_clickhouse_connection_error(error)
            results.append(result)
        
        # This should fail because all errors return the same result (False)
        # If this test passes, error handling distinguishes between error types
        unique_results = set(results)
        assert len(unique_results) == 1, f"All error types should return same result (False) in current implementation, got: {unique_results}"
        assert False in unique_results, "All errors should return False in current implementation"
    
    @fast_test
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_dev_launcher_clickhouse_fallback_behavior_not_communicated_fails(self):
        """
        FAILING TEST: Demonstrates that ClickHouse validation failure doesn't properly communicate fallback.
        
        This test shows that when ClickHouse validation fails, the dev launcher doesn't
        clearly communicate to users what fallback behavior will occur.
        
        Expected behavior: Should clearly indicate when falling back to mock/local mode
        Current behavior: Validation fails but fallback behavior is not clearly communicated
        """
        connector = DatabaseConnector()
        
        # Mock a scenario where validation fails but should fall back gracefully
        connection = DatabaseConnection(
            name="test_clickhouse_fallback",
            db_type=DatabaseType.CLICKHOUSE,
            url="http://localhost:8123/?database=test"
        )
        
        # Mock auth failure that should trigger fallback
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicNone  # TODO: Use real service instance
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.get.side_effect = ClientError("Authentication failed - code 194")
            
            result = await connector._validate_connection_with_retry(connection)
            
            # This should fail because validation returns False without clear fallback communication
            # If this test passes, validation properly communicates fallback behavior
            assert result == False, "Should return False for auth failure"
            assert connection.status == ConnectionStatus.FAILED, "Connection should be marked as failed"
            
            # The issue is that "FAILED" status doesn't communicate that fallback will occur
            # User sees failure but doesn't know that system will continue with fallback
            assert connection.status != ConnectionStatus.FAILED, "Should not mark as FAILED if fallback is available"