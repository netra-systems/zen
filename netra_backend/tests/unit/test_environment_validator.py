"""
Unit tests for Environment Validator

Tests the environment validation logic to ensure test variables
are properly detected and blocked in staging/production environments.
"""

import os
import pytest

from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

from netra_backend.app.core.environment_validator import (
    EnvironmentValidator,
    EnvironmentViolation,
    validate_environment_at_startup,
    is_safe_for_production,
    is_safe_for_staging,
    get_environment_report
)
env = get_env()


class TestEnvironmentValidator:
    """Test suite for EnvironmentValidator."""
    
    def setup_method(self):
        """Setup test environment."""
        # Store original environment to restore later
        self.original_env = env.get_all()
        
        # Clear potentially interfering environment variables
        for var in ['ENVIRONMENT', 'NETRA_ENV', 'TESTING', 'E2E_TESTING', 
                   'AUTH_FAST_TEST_MODE']:
            os.environ.pop(var, None)
        
        # Store pytest test variable to restore later (since pytest sets it automatically)
        self.pytest_test_var = env.delete('PYTEST_CURRENT_TEST', "test")
    
    def teardown_method(self):
        """Restore original environment."""
        # Clear all environment variables
        env.clear()
        # Restore original
        env.update(self.original_env, "test")
        
        # Restore pytest test variable if it was set
        if self.pytest_test_var:
            env.set('PYTEST_CURRENT_TEST', self.pytest_test_var, "test")
    
    def test_detect_test_vars_in_production(self):
        """Test that test variables are detected in production environment."""
        # Set production environment
        env.set('ENVIRONMENT', 'production', "test")
        
        # Set forbidden test variables
        env.set('TESTING', '1', "test")
        env.set('AUTH_FAST_TEST_MODE', 'true', "test")
        
        # Create validator and check
        validator = EnvironmentValidator()
        
        # Should raise EnvironmentError due to critical violations
        with pytest.raises(EnvironmentError) as exc_info:
            validator.validate_environment_at_startup()
        
        error_msg = str(exc_info.value)
        assert 'CRITICAL' in error_msg
        assert 'TESTING' in error_msg
        assert 'AUTH_FAST_TEST_MODE' in error_msg
    
    def test_detect_test_vars_in_staging(self):
        """Test that test variables are detected in staging environment."""
        # Set staging environment
        env.set('ENVIRONMENT', 'staging', "test")
        
        # Set forbidden test variables
        env.set('WEBSOCKET_AUTH_BYPASS', 'true', "test")
        env.set('ALLOW_DEV_OAUTH_SIMULATION', 'true', "test")
        
        # Create validator and check
        validator = EnvironmentValidator()
        
        # Should raise EnvironmentError
        with pytest.raises(EnvironmentError) as exc_info:
            validator.validate_environment_at_startup()
        
        error_msg = str(exc_info.value)
        assert 'WEBSOCKET_AUTH_BYPASS' in error_msg
        assert 'ALLOW_DEV_OAUTH_SIMULATION' in error_msg
    
    def test_allow_test_vars_in_development(self):
        """Test that test variables are allowed in development environment."""
        # Set development environment
        env.set('ENVIRONMENT', 'development', "test")
        
        # Set test variables (should be allowed in development)
        env.set('TESTING', '1', "test")
        env.set('AUTH_FAST_TEST_MODE', 'true', "test")
        
        # Create validator and check
        validator = EnvironmentValidator()
        
        # Should not raise any errors
        validator.validate_environment_at_startup()
        
        # Check that no critical violations were found
        report = validator.get_validation_report()
        assert report['critical_count'] == 0
        assert report['is_valid'] is True
    
    def test_detect_localhost_in_staging(self):
        """Test that localhost references are detected in staging."""
        # Set staging environment
        env.set('ENVIRONMENT', 'staging', "test")
        env.set('AUTH_SERVICE_URL', 'http://localhost:8001', "test")
        env.set('DATABASE_URL', 'postgresql://user:pass@127.0.0.1:5432/db', "test")
        
        # Create validator and check
        validator = EnvironmentValidator()
        
        # The test will likely fail due to PYTEST_CURRENT_TEST, so catch that
        try:
            validator.validate_environment_at_startup()
        except EnvironmentError:
            pass  # Expected if test variables are detected
        
        # Should have HIGH severity violations for localhost
        violations = [v for v in validator.violations if v.severity == 'HIGH']
        assert len(violations) >= 2
        
        # Check specific violations
        auth_violation = next((v for v in violations if v.variable_name == 'AUTH_SERVICE_URL'), None)
        assert auth_violation is not None
        assert 'localhost' in auth_violation.description.lower()
    
    def test_detect_localhost_in_production(self):
        """Test that localhost references are critical in production."""
        # Set production environment
        env.set('ENVIRONMENT', 'production', "test")
        env.set('REDIS_URL', 'redis://0.0.0.0:6379', "test")
        
        # Create validator and check
        validator = EnvironmentValidator()
        
        # Should raise due to critical violation (test vars or localhost)
        with pytest.raises(EnvironmentError):
            validator.validate_environment_at_startup()
        
        # Check that there are critical violations
        violations = [v for v in validator.violations if v.severity == 'CRITICAL']
        assert len(violations) >= 1
        # Either localhost or test var violations are critical
        assert any('0.0.0.0' in v.description or 'REDIS_URL' in v.variable_name for v in violations)
    
    def test_required_variables_missing(self):
        """Test detection of missing required variables."""
        # Set production environment
        env.set('ENVIRONMENT', 'production', "test")
        
        # Don't set required variables
        # JWT_SECRET, DATABASE_URL, etc. should be missing
        
        # Create validator and check
        validator = EnvironmentValidator()
        
        # Will likely fail due to test variables, so catch that
        try:
            validator.validate_environment_at_startup()
        except EnvironmentError:
            pass  # Expected if test vars detected
        
        # Should have HIGH severity violations for missing required vars
        missing_violations = [v for v in validator.violations 
                            if 'missing' in v.description.lower()]
        assert len(missing_violations) > 0
        
        # Check specific required variables
        report = validator.get_validation_report()
        assert report['high_count'] > 0
    
    def test_environment_consistency_check(self):
        """Test environment consistency checking."""
        # Set conflicting environment indicators
        env.set('ENVIRONMENT', 'production', "test")
        env.set('NETRA_ENV', 'staging', "test")
        
        # Create validator and check
        validator = EnvironmentValidator()
        
        # Will likely fail due to test variables in production
        try:
            validator.validate_environment_at_startup()
        except EnvironmentError:
            pass  # Expected
        
        # Should have warnings about mismatch
        assert len(validator.warnings) > 0
        assert any('mismatch' in w.lower() for w in validator.warnings)
    
    def test_is_safe_for_production(self):
        """Test is_safe_for_production function."""
        # Set up a clean environment
        env.set('ENVIRONMENT', 'development', "test")
        
        # Note: May not be safe if test framework variables are present
        # Check if we're in a test environment
        result = is_safe_for_production()
        # If pytest is running, it won't be safe
        if 'PYTEST_CURRENT_TEST' in self.original_env:
            assert result is False  # Not safe due to test variables
        else:
            assert result is True  # Should be safe without test vars
        
        # Add a test variable
        env.set('TESTING', '1', "test")
        
        # Should NOT be safe for production
        assert is_safe_for_production() is False
    
    def test_is_safe_for_staging(self):
        """Test is_safe_for_staging function."""
        # Set up environment
        env.set('ENVIRONMENT', 'development', "test")
        
        # Check safety for staging
        result = is_safe_for_staging()
        # If pytest is running, it won't be safe
        if 'PYTEST_CURRENT_TEST' in self.original_env:
            assert result is False  # Not safe due to test variables
        else:
            assert result is True  # Should be safe without test vars
        
        # Add test variable
        env.set('E2E_TESTING', 'true', "test")
        
        # Should NOT be safe for staging
        assert is_safe_for_staging() is False
    
    def test_validation_report(self):
        """Test get_environment_report function."""
        # Set environment with violations
        env.set('ENVIRONMENT', 'staging', "test")
        env.set('PYTEST_CURRENT_TEST', 'test_something', "test")
        
        # Create validator and validate
        validator = EnvironmentValidator()
        
        try:
            validator.validate_environment_at_startup()
        except EnvironmentError:
            pass  # Expected
        
        # Get report
        report = validator.get_validation_report()
        
        # Check report structure
        assert 'environment' in report
        assert 'violations' in report
        assert 'warnings' in report
        assert 'critical_count' in report
        assert 'high_count' in report
        assert 'is_valid' in report
        
        # Check violation details
        assert report['critical_count'] > 0
        assert report['is_valid'] is False
        assert len(report['violations']) > 0
        
        # Check violation structure
        violation = report['violations'][0]
        assert 'variable' in violation
        assert 'value' in violation
        assert 'severity' in violation
        assert 'description' in violation
    
    def test_environment_normalization(self):
        """Test environment name normalization."""
        validator = EnvironmentValidator()
        
        # Test various environment name variations
        assert validator._normalize_environment_name('prod') == 'production'
        assert validator._normalize_environment_name('production') == 'production'
        assert validator._normalize_environment_name('stage') == 'staging'
        assert validator._normalize_environment_name('staging') == 'staging'
        assert validator._normalize_environment_name('dev') == 'development'
        assert validator._normalize_environment_name('development') == 'development'
        assert validator._normalize_environment_name('local') == 'development'
        assert validator._normalize_environment_name('test') == 'testing'
        assert validator._normalize_environment_name('testing') == 'testing'
        assert validator._normalize_environment_name('e2e') == 'testing'
        assert validator._normalize_environment_name('e2e_testing') == 'testing'
    
    def test_all_forbidden_vars_checked(self):
        """Test that all forbidden variables are properly checked."""
        # Set production environment
        env.set('ENVIRONMENT', 'production', "test")
        
        # Test each forbidden variable
        forbidden_vars = [
            'TESTING',
            'E2E_TESTING',
            'AUTH_FAST_TEST_MODE',
            'PYTEST_CURRENT_TEST',
            'ALLOW_DEV_OAUTH_SIMULATION',
            'WEBSOCKET_AUTH_BYPASS',
            'SKIP_AUTH_VALIDATION',
            'TEST_MODE',
            'CI_TEST_RUN'
        ]
        
        for var in forbidden_vars:
            # Clear environment
            for v in forbidden_vars:
                os.environ.pop(v, None)
            
            # Set only this variable
            os.environ[var] = 'true'
            
            # Create validator and check
            validator = EnvironmentValidator()
            
            # Should raise for this specific variable
            with pytest.raises(EnvironmentError) as exc_info:
                validator.validate_environment_at_startup()
            
            # Verify the variable is mentioned in error
            assert var in str(exc_info.value)
    
    def test_validate_for_environment(self):
        """Test validate_for_environment method."""
        # Set up a test environment
        env.set('ENVIRONMENT', 'development', "test")
        env.set('TESTING', '1', "test")
        
        validator = EnvironmentValidator()
        
        # Should be valid for development
        assert validator.validate_for_environment('development') is True
        
        # Should NOT be valid for production
        assert validator.validate_for_environment('production') is False
        
        # Should NOT be valid for staging
        assert validator.validate_for_environment('staging') is False
        
        # Original environment should be restored
        assert env.get('ENVIRONMENT') == 'development'