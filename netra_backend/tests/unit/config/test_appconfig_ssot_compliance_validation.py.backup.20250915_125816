"""
Test suite to validate SSOT compliance in AppConfig after remediation.

These tests are designed to PASS after the SSOT violation is fixed.
They validate that DatabaseURLBuilder is used as the exclusive SSOT.

Issue #799: Validate proper SSOT compliance after remediation
"""
import pytest
from unittest.mock import patch, MagicMock
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, StagingConfig, ProductionConfig
from shared.database_url_builder import DatabaseURLBuilder


class TestAppConfigSSotComplianceValidation:
    """Tests to validate proper SSOT compliance after remediation."""
    
    def test_appconfig_uses_database_url_builder_exclusively(self):
        """
        COMPLIANCE VALIDATION: AppConfig should use DatabaseURLBuilder exclusively.
        
        This test should PASS after remediation.
        """
        config = AppConfig()
        
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            expected_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
            mock_builder.development.auto_url = expected_url
            mock_builder_class.return_value = mock_builder
            
            # Mock get_env to ensure it's passed to DatabaseURLBuilder
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {'ENVIRONMENT': 'development'}
                mock_env.return_value = mock_env_instance
                
                url = config.get_database_url()
                
                # After remediation, this should work properly
                assert url == expected_url, \
                    f"Expected DatabaseURLBuilder URL, got: {url}"
                
                # Verify DatabaseURLBuilder was called with environment dict
                mock_builder_class.assert_called_once()
                call_args = mock_builder_class.call_args[0][0]
                assert isinstance(call_args, dict), "DatabaseURLBuilder should receive environment dict"
    
    def test_appconfig_no_manual_url_construction_after_remediation(self):
        """
        COMPLIANCE VALIDATION: No manual URL construction should exist.
        
        This test should PASS after remediation.
        """
        import inspect
        
        # Get source code of AppConfig.get_database_url method
        source = inspect.getsource(AppConfig.get_database_url)
        
        # After remediation, these patterns should NOT exist
        forbidden_patterns = [
            "f\"postgresql://",  # Manual f-string construction
            "env.get('POSTGRES_HOST'",  # Direct environment access for URL construction
            "return f\"postgresql://",  # Direct manual URL return
        ]
        
        violations_found = []
        for pattern in forbidden_patterns:
            if pattern in source:
                violations_found.append(pattern)
        
        # After remediation, this should pass (no violations found)
        assert not violations_found, \
            f"Post-remediation violation: Manual URL construction still exists: {violations_found}"
    
    def test_appconfig_handles_database_url_builder_failure_properly(self):
        """
        COMPLIANCE VALIDATION: Proper error handling when DatabaseURLBuilder fails.
        
        After remediation, should have clean error handling without manual fallbacks.
        """
        config = AppConfig()
        
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.development.auto_url = None  # Simulate failure
            mock_builder_class.return_value = mock_builder
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {'ENVIRONMENT': 'development'}
                mock_env.return_value = mock_env_instance
                
                # After remediation, should handle failure cleanly without manual fallback
                url = config.get_database_url()
                
                # Should return None or raise appropriate error, not manual construction
                assert url is None or url == "", \
                    f"Expected None/empty when DatabaseURLBuilder fails, got manual construction: {url}"
    
    def test_development_config_ssot_compliance(self):
        """
        COMPLIANCE VALIDATION: DevelopmentConfig properly uses DatabaseURLBuilder SSOT.
        
        This test should PASS after remediation.
        """
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            expected_url = "postgresql+asyncpg://dev:dev@localhost:5432/netra_dev"
            mock_builder.development.auto_url = expected_url
            mock_builder_class.return_value = mock_builder
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {
                    'ENVIRONMENT': 'development',
                    'POSTGRES_HOST': 'localhost',
                    'POSTGRES_USER': 'dev',
                    'POSTGRES_PASSWORD': 'dev',
                    'POSTGRES_DB': 'netra_dev'
                }
                mock_env.return_value = mock_env_instance
                
                config = DevelopmentConfig()
                
                # Verify DatabaseURLBuilder was used during initialization
                mock_builder_class.assert_called()
                
                # Verify the URL comes from DatabaseURLBuilder
                assert config.database_url == expected_url, \
                    f"Expected DatabaseURLBuilder URL in DevelopmentConfig, got: {config.database_url}"
    
    def test_staging_config_ssot_compliance(self):
        """
        COMPLIANCE VALIDATION: StagingConfig properly uses DatabaseURLBuilder SSOT.
        
        This test should PASS after remediation.
        """
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            expected_url = "postgresql+asyncpg://staging:staging@staging-host:5432/netra_staging?ssl=require"
            mock_builder.staging.auto_url = expected_url
            mock_builder_class.return_value = mock_builder
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {
                    'ENVIRONMENT': 'staging',
                    'POSTGRES_HOST': 'staging-host',
                    'POSTGRES_USER': 'staging',
                    'POSTGRES_PASSWORD': 'staging',
                    'POSTGRES_DB': 'netra_staging'
                }
                mock_env.return_value = mock_env_instance
                
                config = StagingConfig()
                
                # Verify DatabaseURLBuilder was used
                mock_builder_class.assert_called()
                
                # Verify proper SSOT usage
                assert config.database_url == expected_url, \
                    f"Expected DatabaseURLBuilder URL in StagingConfig, got: {config.database_url}"
    
    def test_production_config_ssot_compliance(self):
        """
        COMPLIANCE VALIDATION: ProductionConfig properly uses DatabaseURLBuilder SSOT.
        
        This test should PASS after remediation.
        """
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            expected_url = "postgresql+asyncpg://prod:prod@/cloudsql/project:region:instance/netra_prod"
            mock_builder.production.auto_url = expected_url
            mock_builder_class.return_value = mock_builder
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {
                    'ENVIRONMENT': 'production',
                    'POSTGRES_HOST': '/cloudsql/project:region:instance',
                    'POSTGRES_USER': 'prod',
                    'POSTGRES_PASSWORD': 'prod',
                    'POSTGRES_DB': 'netra_prod'
                }
                mock_env.return_value = mock_env_instance
                
                config = ProductionConfig()
                
                # Verify DatabaseURLBuilder was used
                mock_builder_class.assert_called()
                
                # Verify proper SSOT usage
                assert config.database_url == expected_url, \
                    f"Expected DatabaseURLBuilder URL in ProductionConfig, got: {config.database_url}"
    
    def test_appconfig_clickhouse_url_should_use_builder_pattern(self):
        """
        COMPLIANCE VALIDATION: ClickHouse URL construction should follow SSOT pattern.
        
        This test validates that similar builder pattern is used for ClickHouse.
        """
        config = AppConfig()
        
        # After remediation, ClickHouse should also use a builder pattern
        # This test validates the direction for consistent SSOT implementation
        with patch.object(config, 'clickhouse_native') as mock_clickhouse:
            mock_clickhouse.host = 'clickhouse-host'
            mock_clickhouse.port = 9440
            mock_clickhouse.user = 'clickhouse_user'
            mock_clickhouse.password = 'clickhouse_pass'
            mock_clickhouse.database = 'analytics'
            
            url = config.get_clickhouse_url()
            
            # Should construct URL properly from configuration
            expected_pattern = "clickhouse+native://clickhouse_user:clickhouse_pass@clickhouse-host:9440/analytics"
            assert url == expected_pattern, \
                f"Expected proper ClickHouse URL construction, got: {url}"
    
    def test_database_url_validation_with_ssot_builder(self):
        """
        COMPLIANCE VALIDATION: URL validation should work through DatabaseURLBuilder.
        
        This test ensures validation is properly integrated with SSOT.
        """
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            
            # Mock validation method
            mock_builder.validate.return_value = (True, "")
            mock_builder.get_url_for_environment.return_value = "postgresql+asyncpg://valid:url@host:5432/db"
            mock_builder_class.return_value = mock_builder
            
            config = AppConfig()
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {'ENVIRONMENT': 'development'}
                mock_env.return_value = mock_env_instance
                
                # After remediation, validation should work through DatabaseURLBuilder
                url = config.get_database_url()
                
                # Verify builder was called
                mock_builder_class.assert_called()
                assert url is not None, "Should get valid URL from DatabaseURLBuilder"
    
    def test_environment_specific_url_selection_through_ssot(self):
        """
        COMPLIANCE VALIDATION: Environment-specific URL selection through DatabaseURLBuilder.
        
        This test validates that different environments get appropriate URLs via SSOT.
        """
        environments_and_expected = [
            ('development', 'development.auto_url'),
            ('staging', 'staging.auto_url'), 
            ('production', 'production.auto_url'),
            ('test', 'test.auto_url')
        ]
        
        for env_name, builder_method in environments_and_expected:
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                expected_url = f"postgresql+asyncpg://user:pass@host:5432/{env_name}_db"
                
                # Set up the specific method for this environment
                if env_name == 'development':
                    mock_builder.development.auto_url = expected_url
                elif env_name == 'staging':
                    mock_builder.staging.auto_url = expected_url
                elif env_name == 'production':
                    mock_builder.production.auto_url = expected_url
                elif env_name == 'test':
                    mock_builder.test.auto_url = expected_url
                    
                mock_builder_class.return_value = mock_builder
                
                with patch('shared.isolated_environment.get_env') as mock_env:
                    mock_env_instance = MagicMock()
                    mock_env_instance.as_dict.return_value = {'ENVIRONMENT': env_name}
                    mock_env.return_value = mock_env_instance
                    
                    config = AppConfig()
                    url = config.get_database_url()
                    
                    # After remediation, should get environment-specific URL via SSOT
                    assert url == expected_url, \
                        f"Environment {env_name} should get URL via DatabaseURLBuilder: expected {expected_url}, got {url}"