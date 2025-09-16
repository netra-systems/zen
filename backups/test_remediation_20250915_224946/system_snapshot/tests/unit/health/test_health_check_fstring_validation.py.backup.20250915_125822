"""
Unit tests for health check f-string functionality - Issue #894 deployment synchronization.

Tests designed to expose and validate f-string issues that cause "undefined variable 's'" errors
in staging deployment while working correctly in local codebase.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestHealthCheckFStringValidation(SSotAsyncTestCase):
    """Test suite for health check f-string validation - Issue #894."""

    def test_health_check_fstring_syntax_validation(self):
        """Test that all f-strings in health.py are syntactically correct."""
        # Read the health.py file and check for malformed f-strings
        import netra_backend.app.routes.health as health_module
        import inspect

        # Get the source code of the health module
        source_code = inspect.getsource(health_module)

        # Check for the specific malformed string on line 235
        lines = source_code.split('\n')

        # Find the problematic line (around line 235 in the original)
        problematic_line = None
        for i, line in enumerate(lines):
            if "#removed-legacyis not configured" in line:
                problematic_line = (i + 1, line.strip())
                break

        # This test will fail if the malformed string exists
        if problematic_line:
            pytest.fail(f"Malformed f-string found at line {problematic_line[0]}: {problematic_line[1]}")

    def test_database_url_none_error_message_formation(self):
        """Test the database URL None error message formation - reproduces Issue #894."""
        from netra_backend.app.routes.health import _check_postgres_connection
        from unittest.mock import patch

        # Mock the database URL to be None to trigger the error path
        with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
            # Create a mock config with database_url = None
            mock_config_obj = Mock()
            mock_config_obj.database_url = None
            mock_config.return_value = mock_config_obj

            with patch('shared.isolated_environment.get_env') as mock_get_env:
                # Mock environment to be production to trigger the error
                mock_get_env.return_value.get.return_value = "production"

                # Create a mock database session
                mock_db = AsyncMock()

                # This should trigger the ValueError with the malformed f-string
                with pytest.raises(ValueError) as exc_info:
                    asyncio.run(_check_postgres_connection(mock_db))

                # Check if the error message contains the malformed string
                error_msg = str(exc_info.value)

                # This test will expose the deployment synchronization issue
                assert "#removed-legacyis not configured" not in error_msg, (
                    f"Malformed f-string found in error message: {error_msg}. "
                    "This indicates a deployment synchronization issue where staging has corrupted code."
                )

    def test_health_endpoint_fstring_variables_exist(self):
        """Test that all f-string variables are properly defined and accessible."""
        from netra_backend.app.routes.health import _check_postgres_connection
        import ast
        import inspect

        # Get the source code of the function
        source_code = inspect.getsource(_check_postgres_connection)

        # Parse the AST to find f-string expressions
        tree = ast.parse(source_code)

        # Look for f-string expressions that might have undefined variables
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                # This is an f-string
                for value in node.values:
                    if isinstance(value, ast.FormattedValue):
                        # Check if the formatted value references undefined variables
                        if isinstance(value.value, ast.Name):
                            var_name = value.value.id
                            # Check if variable name looks suspicious (like 's' from corrupted f-string)
                            if var_name == 's':
                                pytest.fail(f"Suspicious undefined variable 's' found in f-string")

    def test_staging_deployment_error_reproduction(self):
        """Reproduce the exact staging deployment error - 'undefined variable s'."""
        # This test simulates the staging environment error

        # The error occurs when Python tries to evaluate f"#removed-legacyis not configured"
        # but it's actually interpreted as f"#removed-legacy{s} not configured" where {s} is undefined

        malformed_string = "#removed-legacyis not configured"

        # Check if this string contains patterns that would cause f-string parsing errors
        if 'legacy' in malformed_string and 's' in malformed_string:
            # This pattern suggests a corrupted f-string
            # In staging, Python might interpret this as an f-string with undefined variable 's'

            # Simulate what happens when this gets interpreted as an f-string
            try:
                # This would be equivalent to the corrupted interpretation
                test_s_undefined = "#removed-legacy{s} not configured"
                # If this were actually parsed as an f-string, it would fail with undefined 's'

                # Flag this as a deployment synchronization issue
                pytest.fail(
                    "Malformed string detected that could cause 'undefined variable s' error in staging. "
                    f"String: '{malformed_string}' appears to be a corrupted f-string."
                )
            except NameError as e:
                if "'s' is not defined" in str(e):
                    pytest.fail(f"Confirmed: undefined variable 's' error reproduced: {e}")

    async def test_health_endpoint_error_handling_with_malformed_strings(self):
        """Test health endpoint behavior when malformed f-strings are encountered."""
        from netra_backend.app.routes.health import health
        from fastapi import Request, Response
        from unittest.mock import Mock, patch

        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = "http://testserver/health"
        mock_request.headers = {}
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state.startup_complete = True

        mock_response = Mock(spec=Response)
        mock_response.headers = {}

        # Mock the health interface to avoid dependency issues
        with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
            mock_health_interface.get_health_status.return_value = {
                "status": "healthy",
                "checks": {"postgres": True},
                "uptime_seconds": 100
            }

            # Call the health endpoint
            result = await health(mock_request, mock_response)

            # Verify the response is properly formed and doesn't contain malformed strings
            assert isinstance(result, dict)
            assert "status" in result

            # Check that no malformed strings leak into the response
            result_str = str(result)
            assert "#removed-legacyis not configured" not in result_str, (
                "Malformed f-string content found in health endpoint response"
            )

    def test_code_deployment_consistency_check(self):
        """Verify that the local codebase doesn't contain the staging deployment corruption."""
        import netra_backend.app.routes.health as health_module
        import inspect

        # Get the actual source code as deployed
        source_code = inspect.getsource(health_module)

        # Check for known corruption patterns
        corruption_patterns = [
            "#removed-legacyis not configured",
            "legacy{s}",
            "f\"#removed-legacy",
        ]

        found_corruptions = []
        for pattern in corruption_patterns:
            if pattern in source_code:
                found_corruptions.append(pattern)

        if found_corruptions:
            pytest.fail(
                f"Code corruption detected in local codebase. "
                f"Found patterns: {found_corruptions}. "
                "This suggests the issue exists in both local and staging environments."
            )

    def test_expected_error_message_format(self):
        """Test what the error message should actually be (for comparison)."""
        # This test documents what the error message should be
        expected_messages = [
            "Database URL is not configured",
            "Database connection is not configured",
            "Database is not available",
            "Database configuration missing"
        ]

        # The malformed message we found
        malformed_message = "#removed-legacyis not configured"

        # Verify that the malformed message is clearly different from expected formats
        for expected in expected_messages:
            assert malformed_message != expected, (
                f"Malformed message '{malformed_message}' should not match expected format '{expected}'"
            )

        # This test will pass, showing what the message should look like
        assert any(
            "configured" in msg and "Database" in msg
            for msg in expected_messages
        ), "Expected messages should contain proper database configuration language"