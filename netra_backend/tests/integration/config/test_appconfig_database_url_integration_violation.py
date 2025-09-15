"""
Integration test to detect SSOT violation in AppConfig database URL construction.

This test validates the actual integration behavior and should FAIL initially,
proving that the SSOT violation exists in real usage scenarios.

Issue #799: Integration-level detection of AppConfig SSOT violation
"""
import pytest
import os
from unittest.mock import patch
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, StagingConfig, ProductionConfig
from shared.database_url_builder import DatabaseURLBuilder


class AppConfigDatabaseUrlIntegrationViolationTests:
    """Integration tests to detect SSOT violation in real usage scenarios."""
    
    def test_appconfig_manual_construction_integration_violation(self):
        """
        INTEGRATION VIOLATION: AppConfig constructs URLs manually instead of using DatabaseURLBuilder SSOT.
        
        This test should FAIL initially, proving real integration violation.
        """
        # Set up environment that would trigger manual construction
        test_env = {
            'POSTGRES_HOST': 'integration-host',
            'POSTGRES_PORT': '5433',
            'POSTGRES_USER': 'integration-user',
            'POSTGRES_PASSWORD': 'integration-pass',
            'POSTGRES_DB': 'integration-db'
        }
        
        with patch.dict(os.environ, test_env, clear=False):
            config = AppConfig()
            config.database_url = None  # Force fallback path
            
            url = config.get_database_url()
            
            # This will FAIL if manual construction exists
            # The pattern shows direct environment variable usage
            expected_manual_pattern = "postgresql://integration-user:integration-pass@integration-host:5433/integration-db"
            
            # CRITICAL: This assertion will FAIL, proving the violation
            assert url != expected_manual_pattern, \
                f"INTEGRATION SSOT VIOLATION: AppConfig manually constructed URL: {url}"
    
    def test_development_config_integration_fallback_violation(self):
        """
        INTEGRATION VIOLATION: DevelopmentConfig has integration paths that bypass DatabaseURLBuilder.
        
        Tests real initialization behavior.
        """
        test_env = {
            'POSTGRES_HOST': 'dev-integration-host',
            'POSTGRES_USER': 'dev-integration-user',
            'POSTGRES_PASSWORD': 'dev-integration-pass',
            'POSTGRES_DB': 'dev-integration-db',
            'POSTGRES_PORT': '5434'
        }
        
        with patch.dict(os.environ, test_env, clear=False):
            # Create config and verify it doesn't use manual construction
            config = DevelopmentConfig()
            
            # Get the URL through the standard method
            url = config.get_database_url()
            
            # Check if DatabaseURLBuilder was actually used as SSOT
            # If manual construction exists, the URL will contain the direct env values
            manual_indicators = [
                "dev-integration-user:dev-integration-pass",
                "@dev-integration-host:5434",
                "/dev-integration-db"
            ]
            
            has_manual_construction = all(indicator in url for indicator in manual_indicators)
            
            # This will FAIL if manual construction is active
            assert not has_manual_construction, \
                f"INTEGRATION SSOT VIOLATION: DevelopmentConfig uses manual construction: {url}"
    
    def test_staging_config_integration_manual_construction_violation(self):
        """
        INTEGRATION VIOLATION: StagingConfig integration with real environment variables.
        
        Tests that staging config properly uses DatabaseURLBuilder in integration scenarios.
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-integration-host',
            'POSTGRES_USER': 'staging-integration-user',
            'POSTGRES_PASSWORD': 'staging-integration-pass', 
            'POSTGRES_DB': 'staging-integration-db',
            'POSTGRES_PORT': '5432'
        }
        
        with patch.dict(os.environ, staging_env, clear=False):
            config = StagingConfig()
            
            # The SSOT violation is in the loading method - check if it actually uses DatabaseURLBuilder exclusively
            url = config.database_url or config.get_database_url()
            
            # Check for manual construction patterns
            manual_pattern = "postgresql+asyncpg://staging-integration-user:staging-integration-pass@staging-integration-host:5432/staging-integration-db"
            
            # This should FAIL if manual construction path is used
            # The presence of exact env var pattern indicates manual construction
            assert url != manual_pattern, \
                f"INTEGRATION SSOT VIOLATION: StagingConfig manual construction detected: {url}"
    
    def test_production_config_integration_manual_construction_violation(self):
        """
        INTEGRATION VIOLATION: ProductionConfig integration with Cloud SQL vs TCP scenarios.
        
        Tests production configuration integration behavior.
        """
        # Test TCP connection scenario (non-Cloud SQL)
        production_env = {
            'ENVIRONMENT': 'production',
            'POSTGRES_HOST': 'production-integration-host.com',
            'POSTGRES_USER': 'production-integration-user',
            'POSTGRES_PASSWORD': 'production-integration-pass',
            'POSTGRES_DB': 'production-integration-db',
            'POSTGRES_PORT': '5432'
        }
        
        with patch.dict(os.environ, production_env, clear=False):
            config = ProductionConfig()
            
            url = config.database_url or config.get_database_url()
            
            # Check for manual construction with SSL
            manual_tcp_pattern = "postgresql+asyncpg://production-integration-user:production-integration-pass@production-integration-host.com:5432/production-integration-db"
            
            # This should FAIL if manual construction exists
            assert not url.startswith(manual_tcp_pattern), \
                f"INTEGRATION SSOT VIOLATION: ProductionConfig manual TCP construction: {url}"
    
    def test_cloud_sql_integration_manual_construction_violation(self):
        """
        INTEGRATION VIOLATION: Cloud SQL configuration manual construction.
        
        Tests Cloud SQL socket path construction integration.
        """
        cloud_sql_env = {
            'ENVIRONMENT': 'production',
            'POSTGRES_HOST': '/cloudsql/test-project:us-central1:test-instance',
            'POSTGRES_USER': 'cloudsql-user',
            'POSTGRES_PASSWORD': 'cloudsql-pass',
            'POSTGRES_DB': 'cloudsql-db'
        }
        
        with patch.dict(os.environ, cloud_sql_env, clear=False):
            config = ProductionConfig()
            
            url = config.database_url or config.get_database_url()
            
            # Check for manual Cloud SQL construction
            manual_cloudsql_pattern = "postgresql+asyncpg://cloudsql-user:cloudsql-pass@/cloudsql-db?host=/cloudsql/test-project:us-central1:test-instance"
            
            # This should FAIL if manual construction exists for Cloud SQL
            assert url != manual_cloudsql_pattern, \
                f"INTEGRATION SSOT VIOLATION: Cloud SQL manual construction detected: {url}"
    
    def test_database_url_builder_integration_vs_manual_construction(self):
        """
        INTEGRATION VIOLATION: Compare DatabaseURLBuilder output vs AppConfig output.
        
        This test directly compares what DatabaseURLBuilder produces vs what AppConfig produces.
        """
        test_env = {
            'POSTGRES_HOST': 'comparison-host',
            'POSTGRES_USER': 'comparison-user',
            'POSTGRES_PASSWORD': 'comparison-pass',
            'POSTGRES_DB': 'comparison-db',
            'POSTGRES_PORT': '5435',
            'ENVIRONMENT': 'development'
        }
        
        with patch.dict(os.environ, test_env, clear=False):
            # Get URL from DatabaseURLBuilder directly (SSOT)
            builder = DatabaseURLBuilder(test_env)
            builder_url = builder.development.auto_url
            
            # Get URL from AppConfig (potentially violating SSOT)
            config = DevelopmentConfig()
            appconfig_url = config.database_url or config.get_database_url()
            
            # The URLs should be identical if SSOT is properly implemented
            # If they differ, it indicates manual construction bypassing SSOT
            
            # This assertion will FAIL if AppConfig bypasses DatabaseURLBuilder
            assert appconfig_url == builder_url, \
                f"INTEGRATION SSOT VIOLATION: AppConfig URL differs from DatabaseURLBuilder SSOT:\n" \
                f"DatabaseURLBuilder (SSOT): {builder_url}\n" \
                f"AppConfig (violation): {appconfig_url}"
    
    def test_environment_override_integration_violation(self):
        """
        INTEGRATION VIOLATION: Environment variable override behavior.
        
        Tests that environment changes properly flow through DatabaseURLBuilder SSOT.
        """
        base_env = {
            'POSTGRES_HOST': 'base-host',
            'POSTGRES_USER': 'base-user',
            'POSTGRES_PASSWORD': 'base-pass',
            'POSTGRES_DB': 'base-db'
        }
        
        with patch.dict(os.environ, base_env, clear=False):
            config = AppConfig()
            original_url = config.get_database_url()
            
            # Override environment
            override_env = base_env.copy()
            override_env['POSTGRES_HOST'] = 'override-host'
            override_env['POSTGRES_USER'] = 'override-user'
            
            with patch.dict(os.environ, override_env, clear=False):
                # Create new config to test override behavior
                config_override = AppConfig()
                override_url = config_override.get_database_url()
                
                # Check if override properly flows through SSOT
                # Manual construction will show direct env var usage
                override_indicators = ['override-host', 'override-user']
                has_override = all(indicator in override_url for indicator in override_indicators)
                
                # If this fails, it means manual construction is responding to env changes
                # instead of using DatabaseURLBuilder as SSOT
                if has_override and original_url != override_url:
                    # This indicates manual construction (SSOT violation)
                    pytest.fail(
                        f"INTEGRATION SSOT VIOLATION: Direct environment override detected (manual construction):\n"
                        f"Original: {original_url}\n"
                        f"Override: {override_url}\n"
                        f"This suggests manual construction instead of DatabaseURLBuilder SSOT"
                    )
    
    def test_clickhouse_url_integration_manual_construction_violation(self):
        """
        INTEGRATION VIOLATION: ClickHouse URL construction should also follow SSOT pattern.
        
        Tests ClickHouse integration behavior.
        """
        clickhouse_env = {
            'CLICKHOUSE_HOST': 'clickhouse-integration-host',
            'CLICKHOUSE_PORT': '9440',
            'CLICKHOUSE_USER': 'clickhouse-integration-user',
            'CLICKHOUSE_PASSWORD': 'clickhouse-integration-pass',
            'CLICKHOUSE_DB': 'integration-analytics'
        }
        
        with patch.dict(os.environ, clickhouse_env, clear=False):
            config = AppConfig()
            
            # Mock clickhouse_native config to not be set, forcing fallback path
            config.clickhouse_url = None
            if hasattr(config, 'clickhouse_native'):
                config.clickhouse_native.host = ''
            
            url = config.get_clickhouse_url()
            
            # Check for manual construction pattern
            manual_clickhouse_pattern = "clickhouse+native://clickhouse-integration-user:clickhouse-integration-pass@clickhouse-integration-host:9440/integration-analytics"
            
            # This should FAIL if manual construction exists
            assert url != manual_clickhouse_pattern, \
                f"INTEGRATION SSOT VIOLATION: ClickHouse manual construction detected: {url}"
    
    def test_integration_error_handling_without_manual_fallback(self):
        """
        INTEGRATION VIOLATION: Error handling should not use manual construction as fallback.
        
        Tests proper error handling integration.
        """
        # Set up environment with missing critical values
        incomplete_env = {
            'POSTGRES_HOST': 'error-test-host',
            # Missing user, password, db - should cause DatabaseURLBuilder to fail
        }
        
        with patch.dict(os.environ, incomplete_env, clear=False):
            config = AppConfig()
            config.database_url = None  # Force builder path
            
            # This should handle failure properly without manual fallback
            try:
                url = config.get_database_url()
                
                # If we get a URL back, check if it's from manual construction
                if url and 'error-test-host' in url:
                    # This indicates manual fallback construction (SSOT violation)
                    pytest.fail(
                        f"INTEGRATION SSOT VIOLATION: Manual fallback construction on error: {url}"
                    )
            except Exception as e:
                # Proper error handling is acceptable for SSOT compliance
                pass