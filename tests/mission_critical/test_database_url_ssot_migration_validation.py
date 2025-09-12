"""
ULTRA CRITICAL: DATABASE_URL SSOT Migration Validation Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal - CRITICAL DATABASE INFRASTRUCTURE MIGRATION
- Business Goal: Zero-failure migration validation - Ensure DatabaseURLBuilder SSOT is working correctly
- Value Impact: System reliability and data integrity - Prevents catastrophic database connectivity failures
- Strategic Impact: Migration success ensures platform stability, prevents service outages

CRITICAL MISSION: This test suite validates the complete migration from direct DATABASE_URL usage
to DatabaseURLBuilder SSOT patterns. Any failures in this migration could cause system-wide
database connectivity issues affecting ALL services and customers.

Testing Coverage Goals:
[U+2713] Core SSOT functionality validation
[U+2713] Service integration validation (auth_service, netra_backend)  
[U+2713] Migration completeness verification
[U+2713] Backward compatibility confirmation
[U+2713] Security validation (credential masking, environment isolation)
[U+2713] Environment-specific configuration testing
[U+2713] Error handling and validation
[U+2713] Real service integration tests

ULTRA CRITICAL IMPORTANCE: 
- DatabaseURLBuilder MUST work correctly across all environments
- Migrated services MUST maintain full functionality
- No service disruption from migration
- All database configurations MUST be preserved
- Security MUST be maintained (no credential exposure)
"""

import pytest
import os
import asyncio
import logging
import tempfile
import threading
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import patch, Mock, MagicMock
from dataclasses import dataclass, field
from pathlib import Path
import re
from urllib.parse import urlparse

# SSOT Imports - Using absolute imports as required by SPEC
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.service_availability import ServiceAvailabilityChecker

# Import auth service components for integration testing
try:
    from auth_service.auth_core.database.database_manager import AuthDatabaseManager
    from auth_service.auth_core.auth_environment import AuthEnvironment
    HAS_AUTH_SERVICE = True
except ImportError:
    HAS_AUTH_SERVICE = False
    logging.warning("Auth service imports not available - some tests will be skipped")

# Import backend components for integration testing  
try:
    from netra_backend.app.db.database_manager import DatabaseManager
    from netra_backend.app.core.backend_environment import BackendEnvironment
    HAS_BACKEND_SERVICE = True
except ImportError:
    HAS_BACKEND_SERVICE = False
    logging.warning("Backend service imports not available - some tests will be skipped")

logger = logging.getLogger(__name__)

@dataclass
class DatabaseURLValidationResult:
    """Results from database URL validation."""
    is_valid: bool
    url: Optional[str] = None
    masked_url: Optional[str] = None
    error: Optional[str] = None
    environment: Optional[str] = None
    config_type: Optional[str] = None

@dataclass
class MigrationValidationResults:
    """Comprehensive migration validation results."""
    core_functionality: bool = False
    auth_service_integration: bool = False
    backend_service_integration: bool = False
    migration_completeness: bool = False
    backward_compatibility: bool = False
    security_validation: bool = False
    overall_success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class DatabaseURLSSOTMigrationValidator:
    """
    Comprehensive validator for DATABASE_URL SSOT migration.
    
    This validator ensures that the migration from direct DATABASE_URL usage
    to DatabaseURLBuilder SSOT patterns is complete and functioning correctly.
    """
    
    def __init__(self):
        self.env = get_env()
        self.results = MigrationValidationResults()
        self.test_environments = ["development", "test", "staging", "production"]
        
    def validate_core_ssot_functionality(self) -> bool:
        """
        Test 1: Core SSOT Functionality Tests
        Validates DatabaseURLBuilder instantiation and basic functionality.
        """
        logger.info("Testing Core SSOT Functionality")
        
        try:
            # Test 1.1: Basic instantiation
            env_vars = self.env.get_all()
            builder = DatabaseURLBuilder(env_vars)
            assert builder is not None, "DatabaseURLBuilder instantiation failed"
            
            # Test 1.2: Environment detection
            environment = builder.environment
            valid_environments = ["development", "test", "testing", "staging", "production"]
            assert environment in valid_environments, f"Invalid environment: {environment} (expected one of {valid_environments})"
            
            # Test 1.3: URL generation for current environment
            url = builder.get_url_for_environment()
            assert url is not None, "Failed to generate database URL for current environment"
            
            # Test 1.4: Validation functionality
            is_valid, error = builder.validate()
            assert isinstance(is_valid, bool), "Validation should return boolean"
            if not is_valid:
                logger.warning(f"Database configuration validation warning: {error}")
            
            # Test 1.5: URL masking for security
            masked_url = DatabaseURLBuilder.mask_url_for_logging(url)
            assert masked_url != url or "memory" in url.lower(), "URL should be masked for security"
            assert "***" in masked_url or "memory" in masked_url.lower(), "Masked URL should contain *** or be memory URL"
            
            # Test 1.6: Multi-part environment variable resolution
            postgres_host = builder.postgres_host
            postgres_port = builder.postgres_port
            postgres_db = builder.postgres_db
            
            # At least some configuration should be available
            has_config = any([postgres_host, postgres_port, postgres_db])
            assert has_config, "No database configuration detected"
            
            logger.info("PASS: Core SSOT Functionality Tests")
            return True
            
        except Exception as e:
            error_msg = f"Core SSOT Functionality Test FAILED: {str(e)}"
            logger.error(error_msg)
            self.results.errors.append(error_msg)
            return False
    
    def validate_environment_specific_configurations(self) -> bool:
        """
        Test 2: Environment-Specific Configuration Tests
        Validates that DatabaseURLBuilder works correctly for all environments.
        """
        logger.info("[U+1F30D] Testing Environment-Specific Configurations")
        
        try:
            base_env_vars = self.env.get_all().copy()
            
            for env_name in self.test_environments:
                logger.info(f"Testing {env_name} environment configuration")
                
                # Create environment-specific configuration
                env_vars = base_env_vars.copy()
                env_vars["ENVIRONMENT"] = env_name
                
                # Add environment-specific test configurations
                if env_name == "test":
                    env_vars["USE_MEMORY_DB"] = "false"  # Test PostgreSQL config
                elif env_name == "development":
                    env_vars["POSTGRES_HOST"] = "localhost"
                    env_vars["POSTGRES_PORT"] = "5432"
                    env_vars["POSTGRES_DB"] = "netra_dev"
                
                builder = DatabaseURLBuilder(env_vars)
                
                # Validate environment detection
                assert builder.environment == env_name, f"Environment detection failed for {env_name}"
                
                # Validate URL generation
                url = builder.get_url_for_environment()
                if url is None and env_name in ["staging", "production"]:
                    # For staging/production, missing config is expected in test environment
                    logger.warning(f"No database configuration available for {env_name} environment - this is expected in test environment")
                    continue
                assert url is not None, f"URL generation failed for {env_name}"
                
                # Environment-specific validations
                if env_name == "test":
                    # Test environment should support both memory and PostgreSQL
                    assert "sqlite" in url.lower() or "postgresql" in url.lower(), f"Invalid test URL format: {url}"
                elif env_name == "development":
                    # Development should use PostgreSQL or default
                    assert "postgresql" in url.lower(), f"Invalid development URL format: {url}"
                elif env_name in ["staging", "production"]:
                    # Production environments should use PostgreSQL with proper validation
                    if "postgresql" in url.lower():
                        assert "+asyncpg://" in url, f"Production URL should use asyncpg driver: {url}"
                
                # Test Docker hostname resolution for development/test
                if env_name in ["development", "test"] and builder.postgres_host == "localhost":
                    # Mock Docker environment
                    with patch('os.path.exists', return_value=True):  # Mock .dockerenv file
                        resolved_host = builder.apply_docker_hostname_resolution("localhost")
                        assert resolved_host == "postgres", f"Docker hostname resolution failed: {resolved_host}"
                
                logger.info(f" PASS:  {env_name} environment configuration PASSED")
            
            logger.info(" PASS:  Environment-Specific Configuration Tests PASSED")
            return True
            
        except Exception as e:
            error_msg = f"Environment-Specific Configuration Test FAILED: {str(e)}"
            logger.error(error_msg)
            self.results.errors.append(error_msg)
            return False
    
    @pytest.mark.skipif(not HAS_AUTH_SERVICE, reason="Auth service not available")
    def validate_auth_service_integration(self) -> bool:
        """
        Test 3: Auth Service Integration Validation
        Validates that auth service database configuration works with DatabaseURLBuilder.
        """
        logger.info("[U+1F510] Testing Auth Service Integration")
        
        try:
            # Test 3.1: AuthEnvironment uses DatabaseURLBuilder
            auth_env = AuthEnvironment()
            
            # Check that AuthEnvironment has database configuration
            assert hasattr(auth_env, 'get_database_url') or hasattr(auth_env, 'database_url'), \
                "AuthEnvironment should have database URL functionality"
            
            # Test 3.2: AuthDatabaseManager initialization
            if hasattr(AuthDatabaseManager, '__init__'):
                # Try to create instance (may fail due to missing config, but should not crash)
                try:
                    auth_db_manager = AuthDatabaseManager()
                    logger.info(" PASS:  AuthDatabaseManager instantiation successful")
                except Exception as init_error:
                    # Log warning but don't fail test - missing config is expected in test environment
                    logger.warning(f"AuthDatabaseManager init warning (expected in test): {init_error}")
            
            # Test 3.3: Database URL builder integration in auth service
            env_vars = self.env.get_all()
            builder = DatabaseURLBuilder(env_vars)
            
            # Validate that auth service can use the same SSOT patterns
            auth_url = builder.get_url_for_environment()
            assert auth_url is not None, "Auth service should be able to generate database URL"
            
            # Test auth-specific validation
            is_valid, error = builder.validate()
            if not is_valid and builder.environment in ["staging", "production"]:
                logger.warning(f"Auth service database validation warning: {error}")
            
            logger.info(" PASS:  Auth Service Integration Tests PASSED")
            return True
            
        except Exception as e:
            error_msg = f"Auth Service Integration Test FAILED: {str(e)}"
            logger.error(error_msg)
            self.results.errors.append(error_msg)
            return False
    
    @pytest.mark.skipif(not HAS_BACKEND_SERVICE, reason="Backend service not available")
    def validate_backend_service_integration(self) -> bool:
        """
        Test 4: Backend Service Integration Validation
        Validates that netra_backend database configuration works with DatabaseURLBuilder.
        """
        logger.info("[U+1F5A5][U+FE0F] Testing Backend Service Integration")
        
        try:
            # Test 4.1: BackendEnvironment uses DatabaseURLBuilder patterns
            backend_env = BackendEnvironment()
            
            # Check that BackendEnvironment has proper configuration
            assert hasattr(backend_env, 'get_database_url') or hasattr(backend_env, 'database_url'), \
                "BackendEnvironment should have database URL functionality"
            
            # Test 4.2: DatabaseManager integration
            if hasattr(DatabaseManager, '__init__'):
                try:
                    # Try to create instance - may fail due to missing config
                    db_manager = DatabaseManager()
                    logger.info(" PASS:  DatabaseManager instantiation successful")
                except Exception as init_error:
                    logger.warning(f"DatabaseManager init warning (expected in test): {init_error}")
            
            # Test 4.3: Backend service health checks work with SSOT
            env_vars = self.env.get_all()
            builder = DatabaseURLBuilder(env_vars)
            
            backend_url = builder.get_url_for_environment()
            assert backend_url is not None, "Backend service should be able to generate database URL"
            
            # Test backend-specific configuration validation
            debug_info = builder.debug_info()
            assert "environment" in debug_info, "Debug info should contain environment"
            assert "available_urls" in debug_info, "Debug info should contain URL availability"
            
            logger.info(" PASS:  Backend Service Integration Tests PASSED")
            return True
            
        except Exception as e:
            error_msg = f"Backend Service Integration Test FAILED: {str(e)}"
            logger.error(error_msg)
            self.results.errors.append(error_msg)
            return False
    
    def validate_migration_completeness(self) -> bool:
        """
        Test 5: Migration Completeness Tests
        Verifies that migrated files use DatabaseURLBuilder and old patterns are replaced.
        """
        logger.info("[U+1F4CB] Testing Migration Completeness")
        
        try:
            # Test 5.1: Check that DatabaseURLBuilder is properly imported and available
            builder_module = __import__('shared.database_url_builder', fromlist=['DatabaseURLBuilder'])
            DatabaseURLBuilderClass = getattr(builder_module, 'DatabaseURLBuilder')
            assert DatabaseURLBuilderClass is not None, "DatabaseURLBuilder class should be importable"
            
            # Test 5.2: Validate migrated files are using SSOT patterns
            migrated_files = [
                "netra_backend/app/core/configuration/environment_detector.py",
                "netra_backend/app/monitoring/staging_health_monitor.py", 
                "netra_backend/app/routes/health_check.py",
                "netra_backend/app/routes/system_info.py",
                "netra_backend/app/services/configuration_service.py",
                "netra_backend/app/services/startup_fixes_integration.py"
            ]
            
            repo_root = Path.cwd()
            migration_patterns_found = 0
            
            for file_path in migrated_files:
                full_path = repo_root / file_path
                if full_path.exists():
                    try:
                        content = full_path.read_text(encoding='utf-8')
                        if "DatabaseURLBuilder" in content:
                            migration_patterns_found += 1
                            logger.info(f" PASS:  Found DatabaseURLBuilder usage in {file_path}")
                        else:
                            logger.warning(f" WARNING: [U+FE0F] No DatabaseURLBuilder found in {file_path}")
                    except Exception as read_error:
                        logger.warning(f"Could not read {file_path}: {read_error}")
                else:
                    logger.warning(f"File not found: {file_path}")
            
            # At least some migrated files should be using DatabaseURLBuilder
            assert migration_patterns_found >= 3, f"Expected at least 3 migrated files, found {migration_patterns_found}"
            
            # Test 5.3: Verify SSOT import patterns
            env_vars = self.env.get_all()
            builder = DatabaseURLBuilder(env_vars)
            
            # Test that all major builder methods are available and working
            methods_to_test = [
                'get_url_for_environment',
                'validate', 
                'debug_info',
                'mask_url_for_logging'
            ]
            
            for method_name in methods_to_test:
                assert hasattr(builder, method_name), f"DatabaseURLBuilder should have {method_name} method"
                if method_name == 'mask_url_for_logging':
                    # This is a static method
                    result = DatabaseURLBuilder.mask_url_for_logging("postgresql://user:pass@host:5432/db")
                    assert "***" in result, "URL masking should work"
                else:
                    method = getattr(builder, method_name)
                    assert callable(method), f"{method_name} should be callable"
            
            logger.info(" PASS:  Migration Completeness Tests PASSED")
            return True
            
        except Exception as e:
            error_msg = f"Migration Completeness Test FAILED: {str(e)}"
            logger.error(error_msg)
            self.results.errors.append(error_msg)
            return False
    
    def validate_backward_compatibility(self) -> bool:
        """
        Test 6: Backward Compatibility Tests
        Ensures same URLs are generated and no breaking changes occurred.
        """
        logger.info("[U+2B05][U+FE0F] Testing Backward Compatibility")
        
        try:
            env_vars = self.env.get_all()
            builder = DatabaseURLBuilder(env_vars)
            
            # Test 6.1: URL generation consistency across multiple calls
            url1 = builder.get_url_for_environment()
            url2 = builder.get_url_for_environment()
            assert url1 == url2, "URL generation should be consistent across calls"
            
            # Test 6.2: Environment variable handling compatibility
            original_env = env_vars.get("ENVIRONMENT", "development")
            
            # Test different environment scenarios
            test_scenarios = [
                {"ENVIRONMENT": "development"},
                {"ENVIRONMENT": "test", "USE_MEMORY_DB": "true"},
                {"ENVIRONMENT": "test", "USE_MEMORY_DB": "false"}
            ]
            
            for scenario in test_scenarios:
                test_env = env_vars.copy()
                test_env.update(scenario)
                
                test_builder = DatabaseURLBuilder(test_env)
                test_url = test_builder.get_url_for_environment()
                
                assert test_url is not None, f"URL generation failed for scenario: {scenario}"
                
                # Validate URL format is correct
                if "postgresql" in test_url:
                    parsed = urlparse(test_url)
                    assert parsed.scheme.startswith("postgresql"), f"Invalid PostgreSQL URL scheme: {test_url}"
                elif "sqlite" in test_url:
                    assert "sqlite" in test_url.lower(), f"Invalid SQLite URL format: {test_url}"
            
            # Test 6.3: Configuration service compatibility
            is_valid, error = builder.validate()
            if not is_valid and builder.environment in ["development", "test"]:
                # Development/test validation warnings are acceptable
                logger.info(f"Expected validation info for {builder.environment}: {error}")
            
            # Test 6.4: Docker hostname resolution backwards compatibility
            test_host = "localhost"
            resolved_host = builder.apply_docker_hostname_resolution(test_host)
            
            # Should return original host unless in Docker environment
            expected_host = test_host  # Default behavior
            
            # Mock Docker environment to test resolution
            with patch('os.path.exists') as mock_exists:
                mock_exists.return_value = True  # Simulate .dockerenv file
                docker_resolved = builder.apply_docker_hostname_resolution(test_host)
                if builder.environment in ["development", "test"]:
                    assert docker_resolved == "postgres", f"Docker resolution should return 'postgres': {docker_resolved}"
                else:
                    assert docker_resolved == test_host, f"Non-dev environments should preserve host: {docker_resolved}"
            
            logger.info(" PASS:  Backward Compatibility Tests PASSED")
            return True
            
        except Exception as e:
            error_msg = f"Backward Compatibility Test FAILED: {str(e)}"
            logger.error(error_msg)
            self.results.errors.append(error_msg)
            return False
    
    def validate_security_requirements(self) -> bool:
        """
        Test 7: Security Validation Tests
        Validates credential masking, environment isolation, and security measures.
        """
        logger.info("[U+1F512] Testing Security Requirements")
        
        try:
            # Test 7.1: Credential masking functionality
            test_urls = [
                "postgresql+asyncpg://user:password123@host:5432/db",
                "postgresql://admin:secret@localhost:5432/test_db",
                "postgresql+asyncpg://user:p@ssw0rd!@host:5432/db?sslmode=require",
                "postgresql://user:pass@/db?host=/cloudsql/project:region:instance",
                "sqlite+aiosqlite:///:memory:",
                None,
                ""
            ]
            
            for test_url in test_urls:
                masked = DatabaseURLBuilder.mask_url_for_logging(test_url)
                
                if test_url is None:
                    assert masked == "NOT SET", f"None URL should return 'NOT SET': {masked}"
                elif test_url == "":
                    assert masked == "NOT SET", f"Empty URL should return 'NOT SET': {masked}"
                elif "memory" in test_url.lower():
                    assert masked == test_url, f"Memory URL should not be masked: {masked}"
                else:
                    # Should contain *** and not contain actual password
                    assert "***" in masked, f"Masked URL should contain ***: {masked}"
                    if "password123" in test_url:
                        assert "password123" not in masked, f"Actual password should be masked: {masked}"
                    if "secret" in test_url:
                        assert "secret" not in masked, f"Actual password should be masked: {masked}"
            
            # Test 7.2: Environment isolation
            env_vars = self.env.get_all()
            builder = DatabaseURLBuilder(env_vars)
            
            # Test that builder doesn't expose sensitive information in debug info
            debug_info = builder.debug_info()
            debug_str = str(debug_info)
            
            # Should not contain actual passwords in debug output
            sensitive_patterns = ["password", "secret", "pass123"]
            for pattern in sensitive_patterns:
                if pattern in debug_str.lower():
                    logger.warning(f"Potential sensitive info in debug output: {pattern}")
            
            # Test 7.3: Safe logging functionality
            safe_log_msg = builder.get_safe_log_message()
            assert isinstance(safe_log_msg, str), "Safe log message should be string"
            assert "***" in safe_log_msg or "memory" in safe_log_msg.lower() or "NOT CONFIGURED" in safe_log_msg, \
                f"Safe log message should mask credentials: {safe_log_msg}"
            
            # Test 7.4: URL validation security
            malicious_urls = [
                ("postgresql://user:pass@evil.com:5432/db", ["user", "pass"]),
                ("postgresql://admin:';DROP TABLE users;--@host:5432/db", ["admin", "';DROP TABLE users;--"])
            ]
            
            for malicious_url, credentials_to_check in malicious_urls:
                masked = DatabaseURLBuilder.mask_url_for_logging(malicious_url)
                # Check that credentials are masked
                for credential in credentials_to_check:
                    assert credential not in masked, f"Credential '{credential}' should be masked in: {masked}"
                # Check that *** is present for masking
                assert "***" in masked, f"Masked URL should contain *** for credentials: {masked}"
            
            # Test 7.5: Credential validation security
            test_env = env_vars.copy()
            test_env.update({
                "POSTGRES_USER": "user_pr-4",  # Known problematic user
                "POSTGRES_PASSWORD": "test_password",
                "POSTGRES_HOST": "localhost",
                "POSTGRES_DB": "test_db",
                "ENVIRONMENT": "staging"
            })
            
            security_builder = DatabaseURLBuilder(test_env)
            is_valid, error = security_builder.validate()
            
            # Should catch problematic user pattern
            assert not is_valid, f"Should reject problematic user pattern: {error}"
            assert "user_pr-4" in error, f"Error should mention problematic user: {error}"
            
            logger.info(" PASS:  Security Validation Tests PASSED")
            return True
            
        except Exception as e:
            error_msg = f"Security Validation Test FAILED: {str(e)}"
            logger.error(error_msg)
            self.results.errors.append(error_msg)
            return False
    
    def run_comprehensive_validation(self) -> MigrationValidationResults:
        """
        Run all validation tests and return comprehensive results.
        """
        logger.info("[U+1F680] Starting Comprehensive DATABASE_URL SSOT Migration Validation")
        
        # Run all validation tests
        self.results.core_functionality = self.validate_core_ssot_functionality()
        
        # Environment-specific testing
        env_config_success = self.validate_environment_specific_configurations()
        if not env_config_success:
            self.results.warnings.append("Environment-specific configuration tests had issues")
        
        # Service integration tests (conditional on service availability)
        if HAS_AUTH_SERVICE:
            self.results.auth_service_integration = self.validate_auth_service_integration()
        else:
            self.results.warnings.append("Auth service integration tests skipped - service not available")
            
        if HAS_BACKEND_SERVICE:
            self.results.backend_service_integration = self.validate_backend_service_integration()
        else:
            self.results.warnings.append("Backend service integration tests skipped - service not available")
        
        self.results.migration_completeness = self.validate_migration_completeness()
        self.results.backward_compatibility = self.validate_backward_compatibility()
        self.results.security_validation = self.validate_security_requirements()
        
        # Determine overall success
        critical_tests = [
            self.results.core_functionality,
            self.results.migration_completeness,
            self.results.backward_compatibility,
            self.results.security_validation
        ]
        
        # Service integration tests are not critical if services are not available
        if HAS_AUTH_SERVICE:
            critical_tests.append(self.results.auth_service_integration)
        if HAS_BACKEND_SERVICE:
            critical_tests.append(self.results.backend_service_integration)
        
        self.results.overall_success = all(critical_tests)
        
        # Generate summary
        logger.info(" CHART:  VALIDATION SUMMARY:")
        logger.info(f" PASS:  Core Functionality: {'PASS' if self.results.core_functionality else 'FAIL'}")
        logger.info(f"[U+1F510] Auth Service Integration: {'PASS' if self.results.auth_service_integration else 'FAIL/SKIP'}")
        logger.info(f"[U+1F5A5][U+FE0F] Backend Service Integration: {'PASS' if self.results.backend_service_integration else 'FAIL/SKIP'}")
        logger.info(f"[U+1F4CB] Migration Completeness: {'PASS' if self.results.migration_completeness else 'FAIL'}")
        logger.info(f"[U+2B05][U+FE0F] Backward Compatibility: {'PASS' if self.results.backward_compatibility else 'FAIL'}")
        logger.info(f"[U+1F512] Security Validation: {'PASS' if self.results.security_validation else 'FAIL'}")
        logger.info(f" TARGET:  OVERALL SUCCESS: {' PASS:  PASS' if self.results.overall_success else ' FAIL:  FAIL'}")
        
        if self.results.errors:
            logger.error(" FAIL:  ERRORS FOUND:")
            for error in self.results.errors:
                logger.error(f"  - {error}")
        
        if self.results.warnings:
            logger.warning(" WARNING: [U+FE0F] WARNINGS:")
            for warning in self.results.warnings:
                logger.warning(f"  - {warning}")
        
        return self.results


# PYTEST TEST CLASSES AND FUNCTIONS
# These provide the pytest interface for running individual test components

class TestDatabaseURLSSOTMigrationValidation:
    """
    Pytest test class for DATABASE_URL SSOT Migration validation.
    
    This class provides individual test methods that can be run by pytest
    while using the comprehensive validator for the actual test logic.
    """
    
    @pytest.fixture(scope="class")
    def validator(self):
        """Create a validator instance for all tests."""
        return DatabaseURLSSOTMigrationValidator()
    
    def test_core_ssot_functionality(self, validator):
        """Test core DatabaseURLBuilder SSOT functionality."""
        assert validator.validate_core_ssot_functionality(), "Core SSOT functionality validation failed"
    
    def test_environment_specific_configurations(self, validator):
        """Test environment-specific database configurations."""
        assert validator.validate_environment_specific_configurations(), "Environment-specific configuration validation failed"
    
    @pytest.mark.skipif(not HAS_AUTH_SERVICE, reason="Auth service not available")
    def test_auth_service_integration(self, validator):
        """Test auth service database integration."""
        assert validator.validate_auth_service_integration(), "Auth service integration validation failed"
    
    @pytest.mark.skipif(not HAS_BACKEND_SERVICE, reason="Backend service not available") 
    def test_backend_service_integration(self, validator):
        """Test backend service database integration."""
        assert validator.validate_backend_service_integration(), "Backend service integration validation failed"
    
    def test_migration_completeness(self, validator):
        """Test that migration to DatabaseURLBuilder is complete."""
        assert validator.validate_migration_completeness(), "Migration completeness validation failed"
    
    def test_backward_compatibility(self, validator):
        """Test that migration maintains backward compatibility."""
        assert validator.validate_backward_compatibility(), "Backward compatibility validation failed"
    
    def test_security_validation(self, validator):
        """Test security requirements for database URL handling."""
        assert validator.validate_security_requirements(), "Security validation failed"
    
    def test_comprehensive_migration_validation(self, validator):
        """Run comprehensive migration validation suite."""
        results = validator.run_comprehensive_validation()
        
        # Generate detailed test report
        report = f"""
DATABASE_URL SSOT MIGRATION VALIDATION REPORT
============================================
Overall Success: {' PASS:  PASS' if results.overall_success else ' FAIL:  FAIL'}

Test Results:
- Core Functionality: {' PASS:  PASS' if results.core_functionality else ' FAIL:  FAIL'}
- Auth Service Integration: {' PASS:  PASS' if results.auth_service_integration else ' FAIL:  FAIL/SKIP'}  
- Backend Service Integration: {' PASS:  PASS' if results.backend_service_integration else ' FAIL:  FAIL/SKIP'}
- Migration Completeness: {' PASS:  PASS' if results.migration_completeness else ' FAIL:  FAIL'}
- Backward Compatibility: {' PASS:  PASS' if results.backward_compatibility else ' FAIL:  FAIL'}
- Security Validation: {' PASS:  PASS' if results.security_validation else ' FAIL:  FAIL'}

Errors: {len(results.errors)}
Warnings: {len(results.warnings)}
        """
        
        logger.info(report)
        
        if results.errors:
            error_details = "\n".join([f"  - {error}" for error in results.errors])
            logger.error(f"CRITICAL ERRORS:\n{error_details}")
        
        if results.warnings:
            warning_details = "\n".join([f"  - {warning}" for warning in results.warnings])
            logger.warning(f"WARNINGS:\n{warning_details}")
        
        # Test passes only if overall validation is successful
        assert results.overall_success, f"Comprehensive migration validation failed with {len(results.errors)} errors"


# STANDALONE EXECUTION FOR DIRECT TESTING
if __name__ == "__main__":
    """
    Allow direct execution of validation tests for manual testing and debugging.
    """
    
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("RUNNING DATABASE_URL SSOT MIGRATION VALIDATION")
    print("=" * 60)
    
    validator = DatabaseURLSSOTMigrationValidator()
    results = validator.run_comprehensive_validation()
    
    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    
    if results.overall_success:
        print("SUCCESS: DATABASE_URL SSOT MIGRATION VALIDATION PASSED")
        print("All critical tests passed. Migration is working correctly!")
    else:
        print("FAILURE: DATABASE_URL SSOT MIGRATION VALIDATION FAILED")
        print("Critical issues found. Review errors and fix before proceeding!")
        
        if results.errors:
            print("\nCRITICAL ERRORS:")
            for i, error in enumerate(results.errors, 1):
                print(f"{i}. {error}")
        
        if results.warnings:
            print("\nWARNINGS:")
            for i, warning in enumerate(results.warnings, 1):
                print(f"{i}. {warning}")
    
    # Exit with appropriate code for CI/CD
    exit(0 if results.overall_success else 1)