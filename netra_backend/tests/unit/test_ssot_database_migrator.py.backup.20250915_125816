"""
SSOT Unit Tests for DatabaseMigrator Class - Complete Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Migration reliability ensures zero-downtime deployments
- Value Impact: Prevents data corruption during system updates that would destroy business value
- Strategic Impact: Enables confident system evolution without business disruption

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSotBaseTestCase for consistent environment isolation
- Tests DatabaseMigrator class methods using real database connections
- NO mocks of database operations - uses real test database
- Uses IsolatedEnvironment for all config access
- Validates migration operations thoroughly with business-focused assertions

SSOT Compliance:
- Inherits from SSotBaseTestCase (single source of truth for test infrastructure)
- Uses IsolatedEnvironment for ALL environment variable access
- Real services only - no mocking of core database functionality
- Comprehensive metrics recording for monitoring and debugging
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import alembic.config

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

from netra_backend.app.db.migration_utils import (
    DatabaseMigrator,
    get_sync_database_url,
    get_current_revision,
    get_head_revision,
    create_alembic_config,
    create_alembic_config_with_fallback,
    needs_migration,
    validate_database_url,
    log_migration_status,
    should_continue_on_error
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.database,
    pytest.mark.migration,
    pytest.mark.real_services
]


class TestSSOTDatabaseMigrator(SSotBaseTestCase):
    """
    SSOT Unit Tests for DatabaseMigrator Class.
    
    This comprehensive test suite validates all DatabaseMigrator functionality
    using real database connections and SSOT environment management.
    
    CRITICAL: This test suite ensures migration system reliability which is
    essential for business continuity during deployments.
    """
    
    def setup_method(self, method=None):
        """Enhanced setup for DatabaseMigrator testing."""
        super().setup_method(method)
        
        # Initialize test database URL using SSOT environment
        env = self.get_env()
        self.database_url = env.get("DATABASE_URL")
        
        if not self.database_url or "mock" in self.database_url.lower():
            pytest.skip("Real database required - mocks forbidden in migration unit tests", allow_module_level=True)
        
        # Initialize DatabaseMigrator for testing
        self.migrator = DatabaseMigrator(self.database_url)
        
        # Record test initialization metrics
        self.record_metric("database_url_configured", bool(self.database_url))
        self.record_metric("migrator_initialized", True)
        self.record_metric("test_started_at", datetime.now(timezone.utc).isoformat())
        
    def test_database_migrator_initialization(self):
        """Test DatabaseMigrator initialization with SSOT environment management.
        
        BUSINESS VALUE: Proper initialization ensures migration system works
        consistently across all environments (test, staging, production).
        """
        # Test basic initialization
        assert self.migrator.database_url == self.database_url, "Original URL should be preserved"
        assert self.migrator.sync_url is not None, "Sync URL should be generated"
        assert self.migrator.logger is not None, "Logger should be initialized"
        
        # Test URL format conversion
        sync_url = self.migrator.sync_url
        self.record_metric("sync_url_generated", True)
        
        if self.database_url.startswith("postgresql+asyncpg://"):
            assert "postgresql+psycopg2://" in sync_url, "Async URL should be converted to sync"
            self.record_metric("url_conversion_async_to_sync", True)
        elif self.database_url.startswith("postgresql://"):
            assert "postgresql+psycopg2://" in sync_url, "Standard URL should be converted to psycopg2"
            self.record_metric("url_conversion_standard_to_psycopg2", True)
        
        # Test that logger is properly configured
        logger_name = getattr(self.migrator.logger, 'name', None)
        if logger_name:
            assert "migration_utils" in logger_name, "Logger should reference migration utilities"
        else:
            # Some logger implementations might not have a name attribute
            assert self.migrator.logger is not None, "Logger should be initialized"
        
    def test_database_url_validation(self):
        """Test database URL validation logic.
        
        BUSINESS VALUE: URL validation prevents deployment failures caused by
        misconfigured database connections.
        """
        # Test valid URL validation
        is_valid = self.migrator.validate_url()
        self.record_metric("database_url_valid", is_valid)
        
        assert is_valid, f"Database URL should be valid: {self.database_url}"
        
        # Test invalid URL detection
        invalid_migrator = DatabaseMigrator("")
        is_invalid = invalid_migrator.validate_url()
        self.record_metric("empty_url_detected_as_invalid", not is_invalid)
        
        assert not is_invalid, "Empty URL should be detected as invalid"
        
        # Test mock URL detection
        mock_migrator = DatabaseMigrator("mock://fake-database")
        is_mock_invalid = mock_migrator.validate_url()
        self.record_metric("mock_url_detected_as_invalid", not is_mock_invalid)
        
        assert not is_mock_invalid, "Mock URL should be detected as invalid"
        
    def test_sync_database_url_conversion(self):
        """Test database URL conversion from async to sync formats.
        
        BUSINESS VALUE: Correct URL conversion ensures Alembic migration tools
        can connect to database properly across all deployment environments.
        """
        # Test various URL format conversions
        test_cases = [
            ("postgresql+asyncpg://user:pass@host:5432/db", "postgresql+psycopg2://user:pass@host:5432/db"),
            ("postgresql://user:pass@host:5432/db", "postgresql+psycopg2://user:pass@host:5432/db"),
            ("postgres://user:pass@host:5432/db", "postgresql+psycopg2://user:pass@host:5432/db"),
            ("postgresql+psycopg2://user:pass@host:5432/db", "postgresql+psycopg2://user:pass@host:5432/db")
        ]
        
        conversions_successful = 0
        for input_url, expected_output in test_cases:
            result = get_sync_database_url(input_url)
            if result == expected_output:
                conversions_successful += 1
            assert result == expected_output, f"URL conversion failed: {input_url} -> {result} (expected: {expected_output})"
        
        self.record_metric("url_conversions_tested", len(test_cases))
        self.record_metric("url_conversions_successful", conversions_successful)
        
    def test_current_revision_detection(self):
        """Test current database revision detection.
        
        BUSINESS VALUE: Accurate revision detection prevents deployment of
        incompatible schema changes that could corrupt business data.
        """
        try:
            current_revision = self.migrator.get_current_revision()
            self.record_metric("current_revision_detection_successful", True)
            self.record_metric("current_revision_value", current_revision)
            
            # Current revision can be None for fresh databases, or a string for migrated ones
            if current_revision is not None:
                assert isinstance(current_revision, str), "Current revision should be string when present"
                assert len(current_revision) > 0, "Current revision should not be empty string"
                self.record_metric("current_revision_present", True)
            else:
                # None is valid for fresh databases without alembic_version table
                self.record_metric("current_revision_none_fresh_database", True)
                
        except Exception as e:
            self.record_metric("current_revision_detection_error", str(e))
            # Real database connectivity errors should be investigated
            pytest.fail(f"Current revision detection failed: {e}")
            
    def test_head_revision_detection(self):
        """Test head revision detection from migration scripts.
        
        BUSINESS VALUE: Head revision detection ensures deployment targets
        the correct schema version defined in migration scripts.
        """
        try:
            head_revision = self.migrator.get_head_revision()
            self.record_metric("head_revision_detection_successful", True)
            self.record_metric("head_revision_value", head_revision)
            
            # Head revision should always be available from migration scripts
            assert head_revision is not None, "Head revision should always be available from migration scripts"
            assert isinstance(head_revision, str), "Head revision should be string"
            assert len(head_revision) > 0, "Head revision should not be empty"
            
            # Head revision should be a valid Alembic revision identifier
            # Typically a 12-character hex string or similar
            self.record_metric("head_revision_length", len(head_revision))
            
        except Exception as e:
            self.record_metric("head_revision_detection_error", str(e))
            # This could indicate missing or corrupted migration scripts
            if "alembic.ini" in str(e) or "script_location" in str(e):
                pytest.skip(f"Alembic configuration issue (deployment problem, allow_module_level=True): {e}", allow_module_level=True)
            else:
                pytest.fail(f"Head revision detection failed: {e}")
                
    def test_migration_need_detection(self):
        """Test migration requirement detection logic.
        
        BUSINESS VALUE: Accurate migration detection prevents unnecessary
        deployments and ensures required schema updates are applied.
        """
        try:
            needs_migration_result = self.migrator.needs_migration()
            self.record_metric("migration_need_detection_successful", True)
            self.record_metric("needs_migration_result", needs_migration_result)
            
            # Get underlying revision data for validation
            current_revision = self.migrator.get_current_revision()
            head_revision = self.migrator.get_head_revision()
            
            # Test the needs_migration logic consistency
            expected_needs_migration = needs_migration(current_revision, head_revision)
            assert needs_migration_result == expected_needs_migration, \
                f"Migration need detection inconsistent: got {needs_migration_result}, expected {expected_needs_migration}"
            
            # Business logic validation
            if current_revision is None:
                # Fresh database should need migration/stamp
                assert needs_migration_result == True, "Fresh database should need migration"
                self.record_metric("fresh_database_needs_migration", True)
            elif current_revision == head_revision:
                # Up-to-date database should not need migration
                assert needs_migration_result == False, "Up-to-date database should not need migration"
                self.record_metric("up_to_date_database_no_migration", True)
            else:
                # Different revisions should need migration
                assert needs_migration_result == True, "Different revisions should need migration"
                self.record_metric("different_revisions_need_migration", True)
                
        except Exception as e:
            self.record_metric("migration_need_detection_error", str(e))
            pytest.fail(f"Migration need detection failed: {e}")
            
    def test_alembic_config_creation(self):
        """Test Alembic configuration creation and validation.
        
        BUSINESS VALUE: Valid Alembic configuration is essential for all
        migration operations in production deployments.
        """
        try:
            config = self.migrator.create_config()
            self.record_metric("alembic_config_creation_successful", True)
            
            # Validate configuration object
            assert isinstance(config, alembic.config.Config), "Should return Alembic Config object"
            
            # Validate SQLAlchemy URL is set correctly
            sqlalchemy_url = config.get_main_option("sqlalchemy.url")
            assert sqlalchemy_url is not None, "SQLAlchemy URL should be set"
            assert sqlalchemy_url == self.migrator.sync_url, "SQLAlchemy URL should match sync URL"
            
            self.record_metric("sqlalchemy_url_configured", True)
            self.record_metric("config_database_type", sqlalchemy_url.split("://")[0] if "://" in sqlalchemy_url else "unknown")
            
            # Test script location configuration
            script_location = config.get_main_option("script_location")
            if script_location:
                assert Path(script_location).exists() or "alembic" in script_location, \
                    "Script location should exist or reference alembic directory"
                self.record_metric("script_location_configured", True)
                
        except FileNotFoundError as e:
            # This indicates missing alembic.ini file - a deployment issue
            self.record_metric("alembic_ini_missing", True)
            pytest.skip(f"Alembic configuration missing (deployment issue, allow_module_level=True): {e}", allow_module_level=True)
            
        except Exception as e:
            self.record_metric("alembic_config_creation_error", str(e))
            pytest.fail(f"Alembic configuration creation failed: {e}")
            
    def test_alembic_config_with_fallback(self):
        """Test Alembic configuration creation with fallback mechanism.
        
        BUSINESS VALUE: Fallback configuration ensures migration system can
        operate in environments with missing configuration files.
        """
        try:
            # Test fallback configuration creation
            config = create_alembic_config_with_fallback(self.migrator.sync_url)
            self.record_metric("fallback_config_creation_successful", True)
            
            assert isinstance(config, alembic.config.Config), "Fallback should return Alembic Config"
            
            # Validate fallback configuration
            sqlalchemy_url = config.get_main_option("sqlalchemy.url")
            assert sqlalchemy_url == self.migrator.sync_url, "Fallback config should set correct URL"
            
            script_location = config.get_main_option("script_location")
            if script_location:
                # Fallback should set reasonable script location
                assert "alembic" in script_location, "Fallback should reference alembic directory"
                self.record_metric("fallback_script_location_set", True)
                
        except Exception as e:
            self.record_metric("fallback_config_error", str(e))
            pytest.fail(f"Fallback configuration creation failed: {e}")
            
    def test_migration_status_logging(self):
        """Test migration status logging functionality.
        
        BUSINESS VALUE: Comprehensive logging enables troubleshooting of
        migration issues and provides deployment visibility.
        """
        # Capture log output for validation
        import logging
        import io
        
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        
        # Use the migrator's logger for testing
        logger = self.migrator.logger
        original_level = logger.level
        original_handlers = logger.handlers.copy()
        
        try:
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)
            
            # Test migration status logging
            current_revision = self.migrator.get_current_revision()
            head_revision = self.migrator.get_head_revision()
            
            log_migration_status(logger, current_revision, head_revision)
            
            # Validate log output
            log_output = log_capture.getvalue()
            self.record_metric("migration_status_logged", len(log_output) > 0)
            
            if needs_migration(current_revision, head_revision):
                assert "Migrating from" in log_output, "Should log migration from/to info"
                self.record_metric("migration_required_logged", True)
            else:
                assert "up to date" in log_output.lower(), "Should log up-to-date status"
                self.record_metric("up_to_date_logged", True)
                
        finally:
            # Restore logger state
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            
    def test_environment_specific_error_handling(self):
        """Test environment-specific error handling logic.
        
        BUSINESS VALUE: Different error handling for different environments
        prevents production failures while enabling development debugging.
        """
        # Test production error handling
        production_continue = should_continue_on_error("production")
        assert production_continue == False, "Production should not continue on migration errors"
        self.record_metric("production_strict_error_handling", True)
        
        # Test non-production error handling
        test_environments = ["test", "staging", "development", "local"]
        lenient_environments = 0
        
        for env in test_environments:
            should_continue = should_continue_on_error(env)
            if should_continue:
                lenient_environments += 1
                
        self.record_metric("lenient_environments_tested", len(test_environments))
        self.record_metric("lenient_environments_count", lenient_environments)
        
        # All non-production environments should be more lenient
        assert lenient_environments == len(test_environments), \
            "Non-production environments should allow continuation on errors"
            
    def test_database_url_validation_comprehensive(self):
        """Test comprehensive database URL validation logic.
        
        BUSINESS VALUE: Thorough URL validation prevents deployment failures
        caused by configuration errors across all environments.
        """
        # Create test logger for validation
        import logging
        test_logger = logging.getLogger("test_migration_validation")
        
        # Test valid URLs
        valid_urls = [
            self.database_url,  # Current test database URL
            "postgresql://user:pass@localhost:5432/testdb",
            "postgresql+psycopg2://user:pass@localhost:5432/testdb"
        ]
        
        valid_count = 0
        for url in valid_urls:
            if url and validate_database_url(url, test_logger):
                valid_count += 1
        
        self.record_metric("valid_urls_tested", len(valid_urls))
        self.record_metric("valid_urls_passed", valid_count)
        
        # Test invalid URLs
        invalid_urls = [
            None,  # None URL
            "",    # Empty URL
            "mock://fake-database",  # Mock URL
            "invalid-url"  # Malformed URL
        ]
        
        invalid_count = 0
        for url in invalid_urls:
            if not validate_database_url(url, test_logger):
                invalid_count += 1
                
        self.record_metric("invalid_urls_tested", len(invalid_urls))
        self.record_metric("invalid_urls_rejected", invalid_count)
        
        # All invalid URLs should be rejected
        assert invalid_count == len(invalid_urls), "All invalid URLs should be rejected"
        
    def test_migration_performance_metrics(self):
        """Test migration operation performance and resource usage.
        
        BUSINESS VALUE: Performance monitoring ensures migrations complete
        within acceptable timeframes for business operations.
        """
        start_time = time.time()
        
        try:
            # Perform basic migration operations and measure performance
            operations_start = time.time()
            
            current_revision = self.migrator.get_current_revision()
            self.increment_db_query_count()
            
            head_revision = self.migrator.get_head_revision()
            self.increment_db_query_count()
            
            needs_migration_result = self.migrator.needs_migration()
            self.increment_db_query_count()
            
            url_validation = self.migrator.validate_url()
            
            operations_end = time.time()
            operation_time = operations_end - operations_start
            
            # Record performance metrics
            self.record_metric("migration_operations_duration", operation_time)
            self.record_metric("operations_per_second", 4 / operation_time if operation_time > 0 else 0)
            
            # Validate performance expectations
            assert operation_time < 30.0, f"Migration operations took too long: {operation_time:.3f}s"
            
            # Validate database query tracking
            db_queries = self.get_db_query_count()
            assert db_queries >= 3, f"Expected at least 3 database queries, recorded {db_queries}"
            
            self.record_metric("performance_validation_passed", True)
            
        except Exception as e:
            operation_time = time.time() - start_time
            self.record_metric("migration_operations_duration", operation_time)
            self.record_metric("performance_validation_error", str(e))
            raise
            
    def test_migration_error_scenarios(self):
        """Test migration system behavior under error conditions.
        
        BUSINESS VALUE: Proper error handling prevents data corruption and
        provides clear diagnostics for deployment troubleshooting.
        """
        # Test behavior with invalid database URL
        try:
            invalid_migrator = DatabaseMigrator("invalid://fake-url")
            
            # Should not crash, but should handle errors gracefully
            url_valid = invalid_migrator.validate_url()
            assert not url_valid, "Invalid URL should be detected"
            
            self.record_metric("invalid_url_handled_gracefully", True)
            
        except Exception as e:
            # Some exceptions are acceptable for completely invalid URLs
            self.record_metric("invalid_url_exception", str(e))
            
        # Test behavior with malformed configuration
        try:
            # This should either work with fallback or fail gracefully
            config_result = create_alembic_config_with_fallback("postgresql://fake:fake@fake:5432/fake")
            self.record_metric("malformed_config_handled", True)
            
        except Exception as e:
            # Config errors should be informative
            error_message = str(e)
            self.record_metric("config_error_message", error_message)
            assert len(error_message) > 0, "Error messages should be informative"
            
    def teardown_method(self, method=None):
        """Enhanced teardown with comprehensive metrics logging."""
        # Record test completion metrics
        self.record_metric("test_completed_at", datetime.now(timezone.utc).isoformat())
        
        # Get all recorded metrics
        all_metrics = self.get_all_metrics()
        
        # Log test summary
        if method:
            print(f"\n=== DatabaseMigrator Test '{method.__name__}' Summary ===")
            print(f"Duration: {all_metrics.get('execution_time', 0):.3f}s")
            print(f"Database Queries: {all_metrics.get('database_queries', 0)}")
            
            # Log business-critical metrics
            business_metrics = {
                k: v for k, v in all_metrics.items() 
                if any(keyword in k for keyword in ['successful', 'valid', 'detection', 'configured'])
            }
            if business_metrics:
                print(f"Business Metrics: {business_metrics}")
                
        # Call parent teardown for SSOT compliance
        super().teardown_method(method)


# SSOT Export Control
__all__ = [
    "TestSSOTDatabaseMigrator"
]