"""
Test suite to detect SSOT violation in AppConfig database URL construction.

This test is designed to FAIL initially, proving the SSOT violation exists.
After remediation, these tests should PASS.

Issue #799: AppConfig manually constructs database URLs instead of using DatabaseURLBuilder
"""
import pytest
from unittest.mock import patch, MagicMock
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, StagingConfig, ProductionConfig
from shared.database_url_builder import DatabaseURLBuilder


class TestAppConfigSSotViolationDetection:
    """Tests to detect SSOT violation in database URL construction."""
    
    def test_appconfig_should_not_manually_construct_database_url(self):
        """
        VIOLATION DETECTION: AppConfig.get_database_url() manually constructs URLs.
        
        This test should FAIL initially, proving the violation exists.
        After remediation, it should PASS.
        """
        config = AppConfig()
        
        # Mock environment to force manual construction path
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'POSTGRES_HOST': 'test-host',
                'POSTGRES_PORT': '5432',
                'POSTGRES_USER': 'test-user',
                'POSTGRES_PASSWORD': 'test-pass',
                'POSTGRES_DB': 'test-db'
            }.get(key, default)
            
            # This should fail - AppConfig is manually constructing URLs
            url = config.get_database_url()
            
            # CRITICAL: This assertion will FAIL if manual construction exists
            # The presence of manual URL construction in AppConfig violates SSOT
            assert not url.startswith("postgresql://test-user:test-pass@test-host:5432/test-db"), \
                "SSOT VIOLATION: AppConfig is manually constructing database URLs instead of using DatabaseURLBuilder"
    
    def test_appconfig_should_not_have_manual_fallback_logic(self):
        """
        VIOLATION DETECTION: AppConfig contains manual URL fallback logic.
        
        This test inspects the source code for manual construction patterns.
        """
        import inspect
        
        # Get source code of AppConfig.get_database_url method
        source = inspect.getsource(AppConfig.get_database_url)
        
        # These patterns indicate manual URL construction (SSOT violation)
        violation_patterns = [
            "f\"postgresql://",  # Manual f-string URL construction
            "f'{protocol}://{user}:{password}@{host}:{port}/{database}'",  # Manual formatting
            "env.get('POSTGRES_HOST'",  # Direct environment access in URL construction
            "return f\"postgresql://",  # Direct return of manually constructed URL
        ]
        
        violations_found = []
        for pattern in violation_patterns:
            if pattern in source:
                violations_found.append(pattern)
        
        # This assertion should FAIL initially if manual construction exists
        assert not violations_found, \
            f"SSOT VIOLATION: Manual URL construction patterns found in AppConfig.get_database_url: {violations_found}"
    
    def test_appconfig_get_clickhouse_url_manual_construction_violation(self):
        """
        VIOLATION DETECTION: AppConfig.get_clickhouse_url() manually constructs URLs.
        
        Similar violation to database URL construction.
        """
        import inspect
        
        # Get source code of AppConfig.get_clickhouse_url method
        source = inspect.getsource(AppConfig.get_clickhouse_url)
        
        # These patterns indicate manual URL construction (SSOT violation)
        violation_patterns = [
            "f\"clickhouse+native://",  # Manual ClickHouse URL construction
            "f\"{protocol}://{config.user}:{config.password}@{config.host}:{config.port}/{config.database}\"",
            "env.get('CLICKHOUSE_HOST'",  # Direct environment access
        ]
        
        violations_found = []
        for pattern in violation_patterns:
            if pattern in source:
                violations_found.append(pattern)
        
        # This assertion should FAIL initially if manual construction exists
        assert not violations_found, \
            f"SSOT VIOLATION: Manual ClickHouse URL construction found: {violations_found}"
    
    def test_development_config_should_use_database_url_builder_ssot(self):
        """
        VIOLATION DETECTION: DevelopmentConfig should only use DatabaseURLBuilder.
        
        This test checks if DatabaseURLBuilder is properly used as SSOT.
        """
        with patch.dict('os.environ', {
            'POSTGRES_HOST': 'dev-host',
            'POSTGRES_USER': 'dev-user', 
            'POSTGRES_PASSWORD': 'dev-pass',
            'POSTGRES_DB': 'dev-db'
        }):
            config = DevelopmentConfig()
            
            # The violation is that DatabaseURLBuilder is used but only as one option
            # The real SSOT violation is that AppConfig.get_database_url has manual fallback
            
            # Test that manual construction path should not exist
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env.return_value.get.side_effect = lambda key, default=None: {
                    'POSTGRES_HOST': 'manual-host',
                    'POSTGRES_PORT': '5433',
                    'POSTGRES_USER': 'manual-user',
                    'POSTGRES_PASSWORD': 'manual-pass',
                    'POSTGRES_DB': 'manual-db'
                }.get(key, default)
                
                url = config.get_database_url()
                
                # This will FAIL if manual construction exists in the parent class
                # The manual fallback in AppConfig.get_database_url violates SSOT principle
                manual_pattern = "manual-user:manual-pass@manual-host:5433/manual-db"
                assert manual_pattern not in url, \
                    f"SSOT VIOLATION: Manual URL construction detected in config hierarchy: {url}"
    
    def test_database_url_builder_not_used_as_exclusive_ssot(self):
        """
        VIOLATION DETECTION: DatabaseURLBuilder should be the ONLY source for URLs.
        
        This test proves that AppConfig bypasses DatabaseURLBuilder in fallback scenarios.
        """
        config = AppConfig()
        config.database_url = None  # Force fallback path
        
        # Mock DatabaseURLBuilder to return None (simulating failure)
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.development.auto_url = None  # Simulate DatabaseURLBuilder failure
            mock_builder_class.return_value = mock_builder
            
            # Mock environment for manual construction
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env.return_value.get.side_effect = lambda key, default=None: {
                    'POSTGRES_HOST': 'fallback-host',
                    'POSTGRES_PORT': '5432',
                    'POSTGRES_USER': 'fallback-user',
                    'POSTGRES_PASSWORD': 'fallback-pass',
                    'POSTGRES_DB': 'fallback-db'
                }.get(key, default)
                
                url = config.get_database_url()
                
                # This should FAIL - proving manual fallback exists (SSOT violation)
                # If DatabaseURLBuilder is the true SSOT, NO manual fallback should exist
                assert url != "postgresql://fallback-user:fallback-pass@fallback-host:5432/fallback-db", \
                    "SSOT VIOLATION: AppConfig has manual fallback when DatabaseURLBuilder fails, violating SSOT principle"
    
    def test_staging_config_manual_construction_in_load_method(self):
        """
        VIOLATION DETECTION: StagingConfig uses DatabaseURLBuilder but still has manual construction capability.
        
        Tests the _load_database_url_from_unified_config_staging method.
        """
        import inspect
        
        # Get source code of the staging database URL loading method
        source = inspect.getsource(StagingConfig._load_database_url_from_unified_config_staging)
        
        # Look for proper SSOT usage - should ONLY use DatabaseURLBuilder
        # Any fallback or manual construction violates SSOT
        violation_indicators = [
            "if not database_url:",  # Indicates fallback logic after DatabaseURLBuilder
            "data['database_url'] = \"postgresql://",  # Direct URL assignment
        ]
        
        violations_found = []
        for indicator in violation_indicators:
            if indicator in source:
                violations_found.append(indicator)
        
        # The presence of fallback logic indicates SSOT violation
        # DatabaseURLBuilder should be the ONLY source, no fallbacks allowed
        if violations_found:
            pytest.fail(f"SSOT VIOLATION in StagingConfig: Fallback logic found after DatabaseURLBuilder: {violations_found}")
    
    def test_production_config_manual_construction_in_load_method(self):
        """
        VIOLATION DETECTION: ProductionConfig uses DatabaseURLBuilder but still has manual construction capability.
        
        Tests the _load_database_url_from_unified_config_production method.
        """
        import inspect
        
        # Get source code of the production database URL loading method  
        source = inspect.getsource(ProductionConfig._load_database_url_from_unified_config_production)
        
        # Look for proper SSOT usage - should ONLY use DatabaseURLBuilder
        violation_indicators = [
            "if not database_url:",  # Indicates fallback logic after DatabaseURLBuilder
            "data['database_url'] = \"postgresql://",  # Direct URL assignment fallback
            "raise ValueError",  # Even error fallbacks indicate non-SSOT design
        ]
        
        violations_found = []
        for indicator in violation_indicators:
            if indicator in source:
                violations_found.append(indicator)
        
        # The presence of any logic after DatabaseURLBuilder indicates SSOT violation
        if violations_found:
            pytest.fail(f"SSOT VIOLATION in ProductionConfig: Non-SSOT patterns found: {violations_found}")
    
    def test_appconfig_database_url_field_should_be_populated_by_ssot_only(self):
        """
        VIOLATION DETECTION: AppConfig.database_url field should only be set by DatabaseURLBuilder.
        
        Tests that no manual assignment bypasses the SSOT.
        """
        # Test that AppConfig doesn't accept manual database URLs that bypass validation
        config = AppConfig()
        
        # If SSOT is properly implemented, manual URL assignment should be validated
        # or channeled through DatabaseURLBuilder
        manual_url = "postgresql://manual:manual@manual:5432/manual"
        config.database_url = manual_url
        
        # The SSOT violation is that this manual URL is accepted without validation
        # Proper SSOT would validate or transform this through DatabaseURLBuilder
        retrieved_url = config.get_database_url()
        
        # This should FAIL if manual URLs bypass SSOT validation
        assert retrieved_url != manual_url, \
            "SSOT VIOLATION: Manual database_url assignment bypasses DatabaseURLBuilder validation"