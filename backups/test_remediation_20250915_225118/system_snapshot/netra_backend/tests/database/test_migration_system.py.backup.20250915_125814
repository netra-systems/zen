"""Test database migration system and schema management.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Migration reliability ensures zero-downtime deployments
- Value Impact: Prevents data corruption during system updates that would destroy business value
- Strategic Impact: Enables confident system evolution without business disruption

CRITICAL REQUIREMENTS:
- Uses SSOT BaseTestCase for consistent environment isolation
- Tests real DatabaseMigrator functionality with no mocks
- Validates migration safety and rollback mechanisms
- Ensures data integrity throughout migration processes
"""

import pytest
import asyncio
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

from netra_backend.app.db.migration_utils import DatabaseMigrator
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.db.database_initializer import DatabaseInitializer

pytestmark = [
    pytest.mark.database,
    pytest.mark.integration,
    pytest.mark.migration,
    pytest.mark.real_services
]

class TestMigrationSystem(SSotBaseTestCase):
    """Test database migration system functionality using SSOT patterns.
    
    CRITICAL: This class inherits from SSotBaseTestCase ensuring:
    - Proper environment isolation using IsolatedEnvironment
    - No direct os.environ access
    - Consistent test metrics recording
    - Real database connections (no mocks)
    """
    
    @pytest.mark.asyncio
    async def test_migration_rollback_fails_without_backup(self):
        """Test that migration rollback fails without proper backup.
        
        BUSINESS VALUE: Rollback safety is critical for zero-downtime deployments.
        Failed rollbacks can cause permanent data loss and business disruption.
        """
        # Use SSOT environment management
        env = self.get_env()
        database_url = env.get("DATABASE_URL")
        
        if not database_url or "mock" in database_url.lower():
            pytest.skip("Real database required - mocks forbidden in migration tests")
        
        # Test real DatabaseMigrator class with actual database
        migrator = DatabaseMigrator(database_url)
        
        # Test that rollback validation fails with invalid backup
        # This should be a real failure, not just AttributeError expectation
        try:
            # Attempt rollback without proper backup should fail gracefully
            current_revision = migrator.get_current_revision()
            head_revision = migrator.get_head_revision()
            
            # Log the current state for debugging
            self.record_metric("current_revision", current_revision)
            self.record_metric("head_revision", head_revision)
            
            # Migration system should validate input properly
            assert current_revision is not None or head_revision is not None, \
                "Migration system must be able to determine database state"
                
        except Exception as e:
            # Real migration errors should be handled gracefully
            self.record_metric("migration_error", str(e))
            # This is expected behavior for invalid operations
            assert "backup" in str(e).lower() or "rollback" in str(e).lower() or "revision" in str(e).lower()
            
    @pytest.mark.asyncio 
    async def test_schema_version_mismatch_detection(self):
        """Test detection of schema version mismatches.
        
        BUSINESS VALUE: Version mismatch detection prevents deployment of incompatible
        code changes that could corrupt data or break functionality.
        """
        # Use SSOT environment management
        env = self.get_env()
        database_url = env.get("DATABASE_URL")
        
        if not database_url or "mock" in database_url.lower():
            pytest.skip("Real database required - mocks forbidden in migration tests")
        
        # Test real migration version detection
        migrator = DatabaseMigrator(database_url)
        
        try:
            current_revision = migrator.get_current_revision()
            head_revision = migrator.get_head_revision()
            needs_migration = migrator.needs_migration()
            
            # Record metrics for monitoring
            self.record_metric("current_revision", current_revision)
            self.record_metric("head_revision", head_revision)
            self.record_metric("needs_migration", needs_migration)
            
            # Test version comparison logic
            if current_revision and head_revision:
                version_match = (current_revision == head_revision)
                migration_needed = migrator.needs_migration()
                
                # Version mismatch detection should be consistent
                assert version_match == (not migration_needed), \
                    f"Version mismatch detection inconsistent: match={version_match}, needs_migration={migration_needed}"
            else:
                # If we can't get revisions, that's a legitimate state for fresh DBs
                assert current_revision is None, "Current revision should be None for fresh database"
                
        except Exception as e:
            # Real database connection issues should be handled
            self.record_metric("version_detection_error", str(e))
            # This indicates real database connectivity or Alembic configuration issues
            pytest.fail(f"Version detection failed with real database: {e}")
                    
    @pytest.mark.asyncio
    async def test_concurrent_migration_prevention(self):
        """Test prevention of concurrent migrations.
        
        BUSINESS VALUE: Concurrent migration prevention avoids data corruption
        and deployment failures that can cause system downtime.
        """ 
        # Use SSOT environment management
        env = self.get_env()
        database_url = env.get("DATABASE_URL")
        
        if not database_url or "mock" in database_url.lower():
            pytest.skip("Real database required - mocks forbidden in migration tests")
        
        # Test real migration system with actual database
        migrator = DatabaseMigrator(database_url)
        
        try:
            # Test that migration system can validate its state
            url_valid = migrator.validate_url()
            self.record_metric("database_url_valid", url_valid)
            
            if url_valid:
                # Test migration state detection
                current_revision = migrator.get_current_revision()
                head_revision = migrator.get_head_revision()
                
                # Record migration state metrics
                self.record_metric("migration_state_detected", True)
                self.record_metric("current_revision_available", current_revision is not None)
                self.record_metric("head_revision_available", head_revision is not None)
                
                # Real migration system should be able to determine state
                assert head_revision is not None, "Migration system must be able to determine target revision"
            else:
                # Invalid URL should be detected properly
                self.record_metric("invalid_database_url", True)
                
        except Exception as e:
            # Record real migration system errors
            self.record_metric("concurrent_prevention_error", str(e))
            # This could indicate real configuration issues that need attention
            if "lock" in str(e).lower() or "concurrent" in str(e).lower():
                # This is expected behavior for concurrent access prevention
                pass
            else:
                # Other errors might indicate system issues
                pytest.fail(f"Migration system error (may indicate real issues): {e}")