"""

Test Issue #799: SSOT Database Configuration Validation



Business Value Justification (BVJ):

- Segment: Platform/Internal

- Business Goal: Stability/Reliability  

- Value Impact: Protects $120K+ MRR through consistent database connectivity

- Strategic Impact: Prevents cascade failures from configuration drift



This test validates complete SSOT compliance in database configuration,

specifically detecting and preventing manual URL construction violations.

"""



import pytest

import os

import inspect

import re

from unittest.mock import patch, MagicMock

from pathlib import Path



from netra_backend.app.schemas.config import AppConfig





class TestDatabaseConfigSSotCompliance:

    """Test complete SSOT compliance in database configuration."""

        

    def setup_method(self, method):

        """Setup for pytest compatibility."""

        self.config = AppConfig()

    

    def test_database_url_ssot_integration_success(self):

        """

        Verify SSOT DatabaseURLBuilder integration works correctly.

        

        This test validates the primary SSOT path functions properly.

        """

        # Clear any pre-set database_url to test SSOT path

        self.config.database_url = None

        

        # Mock successful DatabaseURLBuilder usage

        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:

            with patch('shared.isolated_environment.get_env') as mock_get_env:

                # Setup mocks

                mock_env = MagicMock()

                mock_env.get_all.return_value = {'ENVIRONMENT': 'development'}

                mock_get_env.return_value = mock_env

                

                mock_builder = MagicMock()

                mock_builder.get_url_for_environment.return_value = "postgresql://test:test@localhost:5432/test"

                mock_builder_class.return_value = mock_builder

                

                # Test SSOT integration

                result = self.config.get_database_url()

                

                # Verify SSOT DatabaseURLBuilder was used

                mock_builder_class.assert_called_once()

                mock_builder.get_url_for_environment.assert_called_once_with(sync=True)

                

                # Verify result

                assert result == "postgresql://test:test@localhost:5432/test"

                assert "postgresql://" in result

    

    def test_ssot_fallback_violation_detection(self):

        """

        Critical Test: Verify test FAILS when SSOT violations exist in fallback method.

        

        This test should FAIL initially, proving the SSOT violation exists.

        Test will PASS only when fallback method also uses DatabaseURLBuilder.

        """

        # Get source code of fallback method

        fallback_source = inspect.getsource(self.config._fallback_manual_url_construction)

        

        # Check for SSOT violations in fallback method

        # This is the violation we need to detect and fix

        manual_url_pattern = r'f["\']postgresql://.*?["\']'

        direct_string_construction = re.search(manual_url_pattern, fallback_source)

        

        # Also check for direct f-string construction

        f_string_violation = 'f"postgresql://' in fallback_source

        

        if direct_string_construction or f_string_violation:

            pytest.fail(

                "SSOT VIOLATION DETECTED: _fallback_manual_url_construction() contains manual URL construction. "

                "This violates SSOT principles. The fallback method must also use DatabaseURLBuilder. "

                f"Violation found in source: {fallback_source}"

            )

        

        # If we reach here, SSOT compliance is achieved

        assert True, "No SSOT violations detected in fallback method"

    

    def test_ssot_exception_handling_compliance(self):

        """

        Test exception handling paths maintain SSOT compliance.

        

        All error recovery paths must use SSOT patterns.

        """

        # Clear any pre-set database_url

        self.config.database_url = None

        

        # Test ImportError path - should still maintain SSOT compliance

        with patch('builtins.__import__', side_effect=ImportError("DatabaseURLBuilder not found")):

            # This will trigger the fallback method

            result = self.config.get_database_url()

            

            # The result should be valid but the method should maintain SSOT compliance

            assert result is not None

            assert "postgresql://" in result

            

            # Re-run the SSOT violation check on the fallback

            self.test_ssot_fallback_violation_detection()

    

    def test_import_error_recovery_with_ssot_check(self):

        """

        Test graceful recovery when DatabaseURLBuilder unavailable.

        

        Even in error conditions, SSOT compliance must be maintained.

        """

        self.config.database_url = None

        

        # Mock ImportError for DatabaseURLBuilder

        with patch('shared.database_url_builder.DatabaseURLBuilder', side_effect=ImportError("Module not found")):

            with patch('shared.isolated_environment.get_env') as mock_get_env:

                mock_env = MagicMock()

                mock_env.get.side_effect = lambda key, default: {

                    'POSTGRES_HOST': 'localhost',

                    'POSTGRES_PORT': '5432',

                    'POSTGRES_USER': 'testuser', 

                    'POSTGRES_PASSWORD': 'testpass',

                    'POSTGRES_DB': 'testdb'

                }.get(key, default)

                mock_get_env.return_value = mock_env

                

                # This should trigger fallback

                result = self.config.get_database_url()

                

                # Verify result is valid

                assert result is not None

                assert "postgresql://" in result

                

                # Critical: Verify no SSOT violations in fallback

                # This will fail if manual URL construction exists

                fallback_source = inspect.getsource(self.config._fallback_manual_url_construction)

                assert 'f"postgresql://' not in fallback_source, \

                    "Fallback method contains SSOT violation - manual URL construction detected"

    

    def test_runtime_exception_recovery_ssot_compliance(self):

        """

        Test recovery from DatabaseURLBuilder runtime errors maintains SSOT compliance.

        """

        self.config.database_url = None

        

        # Mock DatabaseURLBuilder to raise runtime exception

        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:

            mock_builder_class.side_effect = Exception("Runtime error in DatabaseURLBuilder")

            

            with patch('shared.isolated_environment.get_env') as mock_get_env:

                mock_env = MagicMock()

                mock_env.get.side_effect = lambda key, default: {

                    'POSTGRES_HOST': 'localhost',

                    'POSTGRES_PORT': '5432', 

                    'POSTGRES_USER': 'testuser',

                    'POSTGRES_PASSWORD': 'testpass',

                    'POSTGRES_DB': 'testdb'

                }.get(key, default)

                mock_get_env.return_value = mock_env

                

                # Should fall back gracefully

                result = self.config.get_database_url()

                

                # Verify result

                assert result is not None

                assert "postgresql://" in result

                

                # Verify SSOT compliance in error recovery

                self.test_ssot_fallback_violation_detection()

    

    def test_configuration_precedence_maintains_ssot(self):

        """

        Test that explicit database_url takes precedence but SSOT is still validated.

        """

        # Set explicit database_url 

        self.config.database_url = "postgresql://explicit:url@host:5432/db"

        

        result = self.config.get_database_url()

        

        # Should return explicit URL

        assert result == "postgresql://explicit:url@host:5432/db"

        

        # Even with explicit URL, fallback method must maintain SSOT compliance

        # for future use cases

        self.test_ssot_fallback_violation_detection()

    

    def test_environment_specific_url_construction_ssot(self):

        """

        Test URL construction for different environments maintains SSOT compliance.

        """

        self.config.database_url = None

        

        environments = ['development', 'staging', 'production']

        

        for env in environments:

            with self.subTest(environment=env):

                with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:

                    with patch('shared.isolated_environment.get_env') as mock_get_env:

                        # Setup environment

                        mock_env_data = {'ENVIRONMENT': env}

                        mock_env = MagicMock()

                        mock_env.get_all.return_value = mock_env_data

                        mock_get_env.return_value = mock_env

                        

                        # Setup successful builder

                        mock_builder = MagicMock()

                        expected_url = f"postgresql://test:test@{env}-host:5432/{env}_db"

                        mock_builder.get_url_for_environment.return_value = expected_url

                        mock_builder_class.return_value = mock_builder

                        

                        # Test

                        result = self.config.get_database_url()

                        

                        # Verify SSOT builder called with sync=True

                        mock_builder.get_url_for_environment.assert_called_with(sync=True)

                        assert result == expected_url

    

    def test_comprehensive_ssot_violation_scan(self):

        """

        Comprehensive scan for ANY SSOT violations in database configuration.

        

        This test scans the entire database configuration system for violations.

        """

        # Get all methods related to database URL construction

        config_methods = [

            self.config.get_database_url,

            self.config._fallback_manual_url_construction

        ]

        

        violations = []

        

        for method in config_methods:

            method_source = inspect.getsource(method)

            method_name = method.__name__

            

            # Check for manual URL construction violations

            if 'f"postgresql://' in method_source:

                violations.append(f"Method {method_name}: Manual f-string URL construction")

            

            if '"postgresql://' in method_source and 'f"postgresql://' not in method_source:

                # Check for direct string concatenation (less common but possible)

                if re.search(r'"postgresql://[^"]*"', method_source):

                    violations.append(f"Method {method_name}: Direct string URL construction")

        

        # If violations found, fail the test with details

        if violations:

            violation_details = "\n".join(violations)

            pytest.fail(

                f"SSOT VIOLATIONS DETECTED in database configuration:\n{violation_details}\n\n"

                "All database URL construction must use DatabaseURLBuilder from shared.database_url_builder. "

                "Manual URL construction violates SSOT principles and can cause configuration drift."

            )

        

        # If no violations, test passes

        assert True, "No SSOT violations detected in database configuration system"





if __name__ == '__main__':

    pytest.main([__file__, '-v'])

