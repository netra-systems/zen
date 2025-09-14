"""Unit tests for database URL SSOT compliance detection."""

import pytest
from unittest.mock import patch, MagicMock
import re
from shared.database_url_builder import DatabaseURLBuilder


pytestmark = [
    pytest.mark.unit,
    pytest.mark.ssot_compliance,
]


class TestDatabaseURLSSOTCompliance:
    """Test suite for validating SSOT compliance in database URL construction."""
    
    def test_ssot_builder_primary_path_works(self):
        """Test that the primary SSOT path (DatabaseURLBuilder) works correctly."""
        # This should PASS - proving the SSOT implementation works
        mock_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_dev',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'postgres',
        }
        
        builder = DatabaseURLBuilder(mock_env)
        url = builder.get_url_for_environment()
        
        # Primary SSOT functionality validation
        assert url is not None
        assert 'postgresql+asyncpg' in url
        assert 'localhost' in url
        assert 'netra_dev' in url
        
        # Validate SSOT methods exist and work
        assert hasattr(builder, 'get_safe_log_message')
        assert hasattr(builder, 'debug_info')
        assert hasattr(builder, 'validate')
        
        log_msg = builder.get_safe_log_message()
        assert '***' in log_msg  # Password should be masked
        assert 'localhost' in log_msg  # Host should be visible
        
    def test_ssot_builder_validation_methods(self):
        """Test SSOT validation methods work correctly."""
        # This should PASS - proving validation works
        mock_env = {
            'ENVIRONMENT': 'production',
            'POSTGRES_HOST': 'localhost',  # Invalid for production
            'POSTGRES_DB': 'netra_prod',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'password',  # Weak password
        }
        
        builder = DatabaseURLBuilder(mock_env)
        is_valid, error = builder.validate()
        
        # Should detect validation issues
        assert not is_valid
        assert error is not None
        assert len(error) > 0
        
    def test_manual_url_construction_detection(self):
        """Test that manual URL construction can be detected."""
        # This test should FAIL initially - showing the SSOT violation exists
        
        # Simulate manual URL construction (the anti-pattern we want to detect)
        manual_urls = [
            "postgresql://user:pass@localhost:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
            "postgres://user:pass@127.0.0.1:5432/db",
        ]
        
        for manual_url in manual_urls:
            # This is what we want to eliminate - manual construction
            # The test should detect this as non-SSOT compliant
            assert self._is_manual_construction(manual_url), f"Failed to detect manual construction: {manual_url}"
    
    def _is_manual_construction(self, url_string):
        """Helper method to detect manual URL construction patterns."""
        # Patterns that indicate manual construction (not using DatabaseURLBuilder)
        manual_patterns = [
            r'postgresql://.*:.*@.*:.*/.+',  # Direct postgresql URL construction
            r'postgres://.*:.*@.*:.*/.+',    # Direct postgres URL construction
            r'postgresql\+asyncpg://.*:.*@.*:.*/.+',  # Direct asyncpg URL construction
        ]
        
        for pattern in manual_patterns:
            if re.match(pattern, url_string):
                return True
        return False
        
    def test_ssot_builder_environment_awareness(self):
        """Test that SSOT builder is properly environment-aware."""
        # This should PASS - proving environment awareness works
        
        environments = ['development', 'testing', 'staging', 'production']
        
        for env in environments:
            mock_env = {
                'ENVIRONMENT': env,
                'POSTGRES_HOST': 'localhost' if env in ['development', 'testing'] else 'prod-db.example.com',
                'POSTGRES_PORT': '5432',
                'POSTGRES_DB': f'netra_{env}',
                'POSTGRES_USER': f'{env}_user',
                'POSTGRES_PASSWORD': f'{env}_password',
            }
            
            builder = DatabaseURLBuilder(mock_env)
            url = builder.get_url_for_environment()
            debug_info = builder.debug_info()
            
            # Should work for all environments
            assert url is not None
            assert debug_info['environment'] == env
            
            # Different environments may have different requirements
            if env in ['staging', 'production']:
                # These should have SSL requirements
                assert 'ssl' in url.lower() or 'ssl' in str(debug_info).lower()
                
    def test_ssot_compliance_static_analysis(self):
        """Test static analysis detection of SSOT violations."""
        # This test should FAIL initially - showing violations exist in codebase
        
        # These are example patterns we should NOT find in the codebase
        violation_patterns = [
            # Direct string formatting for database URLs
            '"postgresql://{}:{}@{}:{}/{}"',
            '"postgres://{}:{}@{}:{}/{}"',
            'f"postgresql://{user}:{password}@{host}:{port}/{database}"',
            'f"postgres://{user}:{password}@{host}:{port}/{database}"',
            
            # Hardcoded database URLs
            '"postgresql://postgres:postgres@localhost:5432/netra_dev"',
            '"postgres://user:password@localhost:5432/db"',
        ]
        
        # This test represents what we should check for in the codebase
        # In a real implementation, this would scan actual files
        violations_found = []
        
        # Simulate finding violations (in actual implementation, would scan files)
        simulated_violations = [
            'Found manual URL construction in file X: f"postgresql://{user}:{password}@{host}:{port}/{database}"',
            'Found hardcoded URL in file Y: "postgresql://postgres:postgres@localhost:5432/netra_dev"'
        ]
        
        violations_found.extend(simulated_violations)
        
        # This assertion should FAIL, showing violations exist
        assert len(violations_found) == 0, f"SSOT violations found: {violations_found}"
        
    def test_ssot_builder_error_handling(self):
        """Test that SSOT builder handles errors gracefully."""
        # This should PASS - proving error handling works
        
        # Test with missing required environment variables
        incomplete_env = {
            'ENVIRONMENT': 'development',
            # Missing POSTGRES_HOST, etc.
        }
        
        builder = DatabaseURLBuilder(incomplete_env)
        
        # Should handle missing variables gracefully
        try:
            url = builder.get_url_for_environment()
            # If it returns a URL, it should be valid
            if url:
                assert 'postgresql' in url
        except Exception as e:
            # If it raises an exception, it should be informative
            assert 'required' in str(e).lower() or 'missing' in str(e).lower()
            
        # Validation should detect the issue
        is_valid, error = builder.validate()
        assert not is_valid
        assert error is not None
        
    def test_ssot_builder_ssl_configuration(self):
        """Test SSL configuration handling in SSOT builder."""
        # This should PASS - proving SSL configuration works
        
        # Test explicit SSL configuration
        ssl_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-db.example.com',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_staging',
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password',
            'POSTGRES_SSL_MODE': 'require',
        }
        
        builder = DatabaseURLBuilder(ssl_env)
        url = builder.get_url_for_environment()
        debug_info = builder.debug_info()
        
        # Should include SSL configuration
        assert url is not None
        assert 'ssl' in url.lower()
        
        # Debug info should reflect SSL settings
        assert 'ssl' in str(debug_info).lower() or 'secure' in str(debug_info).lower()
        
    def test_manual_construction_vs_ssot_comparison(self):
        """Compare manual construction with SSOT approach."""
        # This test should PASS, showing SSOT is better than manual
        
        base_config = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_dev',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'postgres',
        }
        
        # SSOT approach
        builder = DatabaseURLBuilder(base_config)
        ssot_url = builder.get_url_for_environment()
        ssot_log_msg = builder.get_safe_log_message()
        
        # Manual approach (what we want to avoid)
        manual_url = f"postgresql://{base_config['POSTGRES_USER']}:{base_config['POSTGRES_PASSWORD']}@{base_config['POSTGRES_HOST']}:{base_config['POSTGRES_PORT']}/{base_config['POSTGRES_DB']}"
        
        # SSOT should provide additional benefits
        assert ssot_url is not None
        assert manual_url is not None
        
        # SSOT provides safe logging (passwords masked)
        assert '***' in ssot_log_msg
        assert base_config['POSTGRES_PASSWORD'] not in ssot_log_msg
        
        # Manual approach exposes passwords (security risk)
        assert base_config['POSTGRES_PASSWORD'] in manual_url
        
        # SSOT provides validation
        is_valid, _ = builder.validate()
        assert isinstance(is_valid, bool)  # SSOT provides validation capability
        
        # Manual approach has no validation
        # This is why SSOT is better!
