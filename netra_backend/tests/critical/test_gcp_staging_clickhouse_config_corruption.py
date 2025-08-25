"""
Test-Driven Correction (TDC) Tests for ClickHouse Configuration Corruption Issues
Critical staging issue: ClickHouse host contains newline at position 34

These are FAILING tests that demonstrate the exact configuration corruption issues
found in GCP staging logs. The tests are intentionally designed to fail to expose
the specific problems that need fixing.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability - prevent staging deployment failures
- Value Impact: Prevents service outages from corrupt configuration values
- Strategic Impact: Critical for reliable staging environment operations
"""

import pytest
from unittest.mock import patch, MagicMock
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase


class TestClickHouseConfigCorruption:
    """Test suite for ClickHouse configuration corruption issues from GCP staging."""
    
    @pytest.mark.critical
    def test_clickhouse_host_with_newline_character_fails(self):
        """
        FAILING TEST: Demonstrates ClickHouse host configuration corruption with newline character.
        
        This test reproduces the exact error from GCP staging logs:
        "ClickHouse host contains newline at position 34"
        
        Expected behavior: Should reject configuration with newline characters
        Current behavior: May not validate or may accept invalid configurations
        """
        # Simulate the corrupted configuration value that appeared in staging
        corrupted_host = "clickhouse.netra-staging.internal\n"
        port = 8123
        database = "netra_staging"
        user = "netra_user"
        password = "secure_password"
        
        # This should fail with a validation error about newline character
        # If this test passes, it means validation is not working correctly
        with pytest.raises(ValueError, match="ClickHouse host contains newline"):
            ClickHouseDatabase(
                host=corrupted_host,
                port=port,
                database=database,
                user=user,
                password=password
            )
    
    @pytest.mark.critical
    def test_clickhouse_host_with_carriage_return_fails(self):
        """
        FAILING TEST: Edge case - ClickHouse host with carriage return character.
        
        Tests similar control character corruption that could occur in configuration.
        """
        corrupted_host = "clickhouse.netra-staging.internal\r"
        port = 8123
        database = "netra_staging"
        user = "netra_user" 
        password = "secure_password"
        
        # Should fail with validation error about carriage return
        with pytest.raises(ValueError, match="ClickHouse host contains carriage return"):
            ClickHouseDatabase(
                host=corrupted_host,
                port=port,
                database=database,
                user=user,
                password=password
            )
    
    @pytest.mark.critical
    def test_clickhouse_host_with_tab_character_fails(self):
        """
        FAILING TEST: Edge case - ClickHouse host with tab character.
        
        Tests tab character corruption that could occur during configuration parsing.
        """
        corrupted_host = "clickhouse.netra-staging.internal\t"
        port = 8123
        database = "netra_staging"
        user = "netra_user"
        password = "secure_password"
        
        # Should fail with validation error about tab character
        with pytest.raises(ValueError, match="ClickHouse host contains tab"):
            ClickHouseDatabase(
                host=corrupted_host,
                port=port,
                database=database,
                user=user,
                password=password
            )
    
    @pytest.mark.critical
    def test_clickhouse_database_name_with_control_character_fails(self):
        """
        FAILING TEST: Database name corruption with control character.
        
        Tests corruption in database name parameter, not just host.
        """
        host = "clickhouse.netra-staging.internal"
        port = 8123
        corrupted_database = "netra_staging\x00"  # NULL character
        user = "netra_user"
        password = "secure_password"
        
        # Should fail with validation error about control character
        with pytest.raises(ValueError, match="ClickHouse database contains control character"):
            ClickHouseDatabase(
                host=host,
                port=port,
                database=corrupted_database,
                user=user,
                password=password
            )
    
    @pytest.mark.critical
    def test_clickhouse_user_with_newline_fails(self):
        """
        FAILING TEST: User parameter corruption with newline.
        
        Tests corruption in user parameter.
        """
        host = "clickhouse.netra-staging.internal"
        port = 8123
        database = "netra_staging"
        corrupted_user = "netra_user\n"
        password = "secure_password"
        
        # Should fail with validation error about newline in user
        with pytest.raises(ValueError, match="ClickHouse user contains newline"):
            ClickHouseDatabase(
                host=host,
                port=port,
                database=database,
                user=corrupted_user,
                password=password
            )
    
    @pytest.mark.critical
    def test_clickhouse_password_with_control_character_fails(self):
        """
        FAILING TEST: Password parameter corruption with control character.
        
        Tests corruption in password parameter.
        """
        host = "clickhouse.netra-staging.internal"
        port = 8123
        database = "netra_staging"
        user = "netra_user"
        corrupted_password = "secure_password\x1f"  # Control character ASCII 31
        
        # Should fail with validation error about control character in password
        with pytest.raises(ValueError, match="ClickHouse password contains control character"):
            ClickHouseDatabase(
                host=host,
                port=port,
                database=database,
                user=user,
                password=corrupted_password
            )
    
    @pytest.mark.critical
    def test_clickhouse_empty_host_validation_fails(self):
        """
        FAILING TEST: Empty host parameter validation.
        
        Tests validation of empty host configuration.
        """
        empty_host = ""
        port = 8123
        database = "netra_staging"
        user = "netra_user"
        password = "secure_password"
        
        # Should fail with validation error about empty host
        with pytest.raises(ValueError, match="ClickHouse host cannot be empty"):
            ClickHouseDatabase(
                host=empty_host,
                port=port,
                database=database,
                user=user,
                password=password
            )
    
    @pytest.mark.critical
    def test_clickhouse_invalid_port_range_fails(self):
        """
        FAILING TEST: Invalid port range validation.
        
        Tests port validation for out-of-range values.
        """
        host = "clickhouse.netra-staging.internal"
        invalid_port = 70000  # Above valid port range
        database = "netra_staging"
        user = "netra_user"
        password = "secure_password"
        
        # Should fail with validation error about port range
        with pytest.raises(ValueError, match="ClickHouse port must be integer between 1-65535"):
            ClickHouseDatabase(
                host=host,
                port=invalid_port,
                database=database,
                user=user,
                password=password
            )
    
    @pytest.mark.critical
    def test_environment_variable_parsing_corruption_fails(self):
        """
        FAILING TEST: Environment variable parsing corruption simulation.
        
        Tests scenario where environment variables get corrupted during parsing
        or loading from GCP Secret Manager, leading to newlines in configuration.
        """
        # Simulate what might happen if environment variable parsing adds newlines
        with patch('netra_backend.app.core.configuration.base.get_unified_config') as mock_config:
            mock_config.return_value = MagicMock()
            mock_config.return_value.clickhouse = MagicMock()
            mock_config.return_value.clickhouse.host = "clickhouse.netra-staging.internal\n"
            mock_config.return_value.clickhouse.port = 8123
            mock_config.return_value.clickhouse.database = "netra_staging"
            mock_config.return_value.clickhouse.user = "netra_user"
            mock_config.return_value.clickhouse.password = "secure_password"
            
            # This should fail during configuration loading/validation
            # If it passes, configuration validation is not catching the corruption
            with pytest.raises(ValueError, match="ClickHouse host contains newline"):
                ClickHouseDatabase(
                    host=mock_config.return_value.clickhouse.host,
                    port=mock_config.return_value.clickhouse.port,
                    database=mock_config.return_value.clickhouse.database,
                    user=mock_config.return_value.clickhouse.user,
                    password=mock_config.return_value.clickhouse.password
                )