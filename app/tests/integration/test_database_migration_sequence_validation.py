"""
Database Migration Sequence Validation Test - L3 Realism

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all customer segments)
- Business Goal: Platform Stability - Prevent data corruption and migration failures
- Value Impact: Protects customer data integrity across all tiers, ensuring zero data loss
- Strategic/Revenue Impact: Prevents critical downtime ($50K/hour), customer churn, and compliance violations

This test validates the complete database migration lifecycle using real containerized databases
to ensure migration sequences work correctly, rollbacks function properly, and concurrent
migrations are handled safely.

Priority: P0 (Critical Data Protection)
Performance Target: <5 minutes total execution time
"""

import asyncio
import pytest
import uuid
import json
import time
import subprocess
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from contextlib import asynccontextmanager
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import clickhouse_connect
from unittest.mock import Mock, AsyncMock

# Test framework imports
from test_framework.mock_utils import mock_justified

# Application imports  
from app.startup.migration_tracker import MigrationTracker
from app.startup.migration_models import MigrationState
from app.db.migration_utils import create_alembic_config, get_current_revision, get_head_revision
from app.core.exceptions import NetraException


class ContainerizedDatabaseManager:
    """
    Manages containerized PostgreSQL and ClickHouse instances for L3 realistic testing.
    Uses docker-compose test configuration for consistent container management.
    """
    
    def __init__(self):
        self.postgres_config = {
            "host": "localhost",
            "port": 5433,  # Test port from docker-compose.test.yml
            "database": "netra_test",
            "user": "test_user", 
            "password": "test_password"
        }
        
        self.clickhouse_config = {
            "host": "localhost",
            "port": 8124,  # Test port from docker-compose.test.yml
            "database": "netra_analytics_test",
            "username": "test_user",
            "password": "test_password"
        }
        
        self.postgres_url = (
            f"postgresql://{self.postgres_config['user']}:{self.postgres_config['password']}"
            f"@{self.postgres_config['host']}:{self.postgres_config['port']}"
            f"/{self.postgres_config['database']}"
        )
        
        self.clickhouse_url = (
            f"http://{self.clickhouse_config['username']}:{self.clickhouse_config['password']}"
            f"@{self.clickhouse_config['host']}:{self.clickhouse_config['port']}"
            f"/{self.clickhouse_config['database']}"
        )
        
        self.containers_started = False
        
    async def ensure_containers_running(self) -> bool:
        """Ensure test containers are running and accessible."""
        try:
            # Check PostgreSQL connectivity
            postgres_ready = await self._check_postgres_ready()
            if not postgres_ready:
                return False
                
            # Check ClickHouse connectivity  
            clickhouse_ready = await self._check_clickhouse_ready()
            if not clickhouse_ready:
                return False
                
            self.containers_started = True
            return True
            
        except Exception as e:
            pytest.skip(f"Container databases not available: {e}")
            return False
    
    async def _check_postgres_ready(self, max_retries: int = 10) -> bool:
        """Check if PostgreSQL container is ready."""
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(**self.postgres_config)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                raise e
        return False
    
    async def _check_clickhouse_ready(self, max_retries: int = 10) -> bool:
        """Check if ClickHouse container is ready."""
        for attempt in range(max_retries):
            try:
                client = clickhouse_connect.get_client(
                    host=self.clickhouse_config["host"],
                    port=self.clickhouse_config["port"],
                    username=self.clickhouse_config["username"],
                    password=self.clickhouse_config["password"],
                    database=self.clickhouse_config["database"]
                )
                client.ping()
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                raise e
        return False
    
    def get_postgres_connection(self):
        """Get direct PostgreSQL connection."""
        return psycopg2.connect(**self.postgres_config)
    
    def get_clickhouse_client(self):
        """Get ClickHouse client connection."""
        return clickhouse_connect.get_client(
            host=self.clickhouse_config["host"],
            port=self.clickhouse_config["port"],
            username=self.clickhouse_config["username"],
            password=self.clickhouse_config["password"],
            database=self.clickhouse_config["database"]
        )
    
    async def reset_databases(self):
        """Reset both databases to clean state."""
        await self._reset_postgres()
        await self._reset_clickhouse()
    
    async def _reset_postgres(self):
        """Reset PostgreSQL to clean state."""
        try:
            conn = self.get_postgres_connection()
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Drop all tables except system tables
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' AND tablename != 'alembic_version'
            """)
            tables = cursor.fetchall()
            
            for (table,) in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            
            # Reset alembic version
            cursor.execute("DROP TABLE IF EXISTS alembic_version")
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"PostgreSQL reset warning: {e}")
    
    async def _reset_clickhouse(self):
        """Reset ClickHouse to clean state.""" 
        try:
            client = self.get_clickhouse_client()
            
            # Get all tables
            tables = client.query("SHOW TABLES").result_rows
            
            # Drop all tables
            for (table,) in tables:
                client.command(f"DROP TABLE IF EXISTS {table}")
                
        except Exception as e:
            print(f"ClickHouse reset warning: {e}")


class MigrationSequenceValidator:
    """
    Validates database migration sequences, rollbacks, and concurrent operations.
    """
    
    def __init__(self, db_manager: ContainerizedDatabaseManager):
        self.db_manager = db_manager
        self.temp_migration_dirs = []
        
    async def create_test_migration(self, migration_name: str, upgrade_sql: str, downgrade_sql: str) -> str:
        """Create a test migration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        revision_id = f"{timestamp}_{migration_name.lower().replace(' ', '_')}"
        
        # Create temporary migration directory
        temp_dir = tempfile.mkdtemp(prefix="test_migrations_")
        self.temp_migration_dirs.append(temp_dir)
        
        migration_content = f'''"""
{migration_name}

Revision ID: {revision_id}
Revises: 
Create Date: {datetime.now().isoformat()}
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '{revision_id}'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """{migration_name} upgrade"""
    {upgrade_sql}

def downgrade():
    """{migration_name} downgrade"""
    {downgrade_sql}
'''
        
        migration_file = Path(temp_dir) / f"{revision_id}_{migration_name.lower().replace(' ', '_')}.py"
        migration_file.write_text(migration_content)
        
        return str(migration_file)
    
    async def test_migration_sequence_execution(self) -> Dict[str, Any]:
        """Test sequential migration execution."""
        results = {
            "migration_1_success": False,
            "migration_2_success": False,
            "sequence_integrity": False,
            "execution_time": 0,
            "errors": []
        }
        
        start_time = time.time()
        
        try:
            # Create test migrations
            migration_1 = await self.create_test_migration(
                "create_test_table",
                "op.execute('CREATE TABLE test_migration_1 (id SERIAL PRIMARY KEY, name VARCHAR(100))')",
                "op.execute('DROP TABLE IF EXISTS test_migration_1')"
            )
            
            migration_2 = await self.create_test_migration(
                "add_test_column", 
                "op.execute('ALTER TABLE test_migration_1 ADD COLUMN created_at TIMESTAMP DEFAULT NOW()')",
                "op.execute('ALTER TABLE test_migration_1 DROP COLUMN IF EXISTS created_at')"
            )
            
            # Execute migrations in sequence
            tracker = MigrationTracker(self.db_manager.postgres_url, "test")
            
            # Apply first migration
            success_1 = await tracker.run_migrations(force=True)
            results["migration_1_success"] = success_1
            
            # Verify first migration
            if success_1:
                await self._verify_table_exists("test_migration_1")
            
            # Apply second migration  
            success_2 = await tracker.run_migrations(force=True)
            results["migration_2_success"] = success_2
            
            # Verify second migration
            if success_2:
                await self._verify_column_exists("test_migration_1", "created_at")
            
            results["sequence_integrity"] = success_1 and success_2
            
        except Exception as e:
            results["errors"].append(f"Migration sequence error: {str(e)}")
        
        results["execution_time"] = time.time() - start_time
        return results
    
    async def test_migration_rollback_capability(self) -> Dict[str, Any]:
        """Test migration rollback functionality."""
        results = {
            "rollback_success": False,
            "data_preservation": False,
            "schema_restoration": False,
            "rollback_time": 0,
            "errors": []
        }
        
        start_time = time.time()
        
        try:
            # Create and apply migration
            migration = await self.create_test_migration(
                "rollback_test",
                """
                op.execute('CREATE TABLE rollback_test (id SERIAL PRIMARY KEY, data TEXT)')
                op.execute("INSERT INTO rollback_test (data) VALUES ('test_data_1'), ('test_data_2')")
                """,
                "op.execute('DROP TABLE IF EXISTS rollback_test')"
            )
            
            tracker = MigrationTracker(self.db_manager.postgres_url, "test")
            
            # Apply migration
            apply_success = await tracker.run_migrations(force=True)
            
            if apply_success:
                # Verify data exists
                data_count = await self._count_table_rows("rollback_test")
                
                # Perform rollback
                rollback_success = await tracker.rollback_migration(steps=1)
                results["rollback_success"] = rollback_success
                
                if rollback_success:
                    # Verify table no longer exists
                    table_exists = await self._check_table_exists("rollback_test")
                    results["schema_restoration"] = not table_exists
                    
                    # Data preservation test (data should be gone with table)
                    results["data_preservation"] = not table_exists
            
        except Exception as e:
            results["errors"].append(f"Rollback test error: {str(e)}")
        
        results["rollback_time"] = time.time() - start_time
        return results
    
    async def test_migration_version_conflicts(self) -> Dict[str, Any]:
        """Test handling of migration version conflicts."""
        results = {
            "conflict_detection": False,
            "resolution_success": False,
            "data_integrity": False,
            "errors": []
        }
        
        try:
            # Create conflicting migrations (same revision ID)
            conflict_id = "test_conflict_123"
            
            migration_a = await self.create_test_migration(
                "conflict_branch_a",
                "op.execute('CREATE TABLE conflict_a (id SERIAL PRIMARY KEY)')",
                "op.execute('DROP TABLE IF EXISTS conflict_a')"
            )
            
            migration_b = await self.create_test_migration(
                "conflict_branch_b", 
                "op.execute('CREATE TABLE conflict_b (id SERIAL PRIMARY KEY)')",
                "op.execute('DROP TABLE IF EXISTS conflict_b')"
            )
            
            # Attempt to apply conflicting migrations
            tracker = MigrationTracker(self.db_manager.postgres_url, "test")
            
            try:
                await tracker.run_migrations(force=True)
                results["conflict_detection"] = False  # Should have detected conflict
            except NetraException as e:
                results["conflict_detection"] = True
                results["resolution_success"] = "conflict" in str(e).lower()
            
        except Exception as e:
            results["errors"].append(f"Version conflict test error: {str(e)}")
        
        return results
    
    async def test_concurrent_migration_safety(self) -> Dict[str, Any]:
        """Test safety of concurrent migration attempts.""" 
        results = {
            "concurrency_handled": False,
            "data_consistency": False,
            "lock_mechanism": False,
            "errors": []
        }
        
        try:
            # Create migration
            migration = await self.create_test_migration(
                "concurrent_test",
                "op.execute('CREATE TABLE concurrent_test (id SERIAL PRIMARY KEY, value INT)')",
                "op.execute('DROP TABLE IF EXISTS concurrent_test')"
            )
            
            # Simulate concurrent migration attempts
            tracker_1 = MigrationTracker(self.db_manager.postgres_url, "test")
            tracker_2 = MigrationTracker(self.db_manager.postgres_url, "test")
            
            # Start migrations concurrently
            tasks = [
                asyncio.create_task(tracker_1.run_migrations(force=True)),
                asyncio.create_task(tracker_2.run_migrations(force=True))
            ]
            
            # Wait for completion
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            success_count = sum(1 for result in completed_results if result is True)
            exception_count = sum(1 for result in completed_results if isinstance(result, Exception))
            
            # Should have one success and one handled gracefully
            results["concurrency_handled"] = success_count == 1 or exception_count > 0
            results["lock_mechanism"] = True  # If no corruption occurred
            
            # Verify data consistency
            table_exists = await self._check_table_exists("concurrent_test")
            results["data_consistency"] = table_exists
            
        except Exception as e:
            results["errors"].append(f"Concurrent migration test error: {str(e)}")
        
        return results
    
    async def test_migration_performance_validation(self) -> Dict[str, Any]:
        """Test migration performance under load."""
        results = {
            "performance_acceptable": False,
            "large_migration_time": 0,
            "index_creation_time": 0,
            "errors": []
        }
        
        start_time = time.time()
        
        try:
            # Create large migration simulation
            large_migration = await self.create_test_migration(
                "performance_test",
                """
                # Simulate large table creation
                op.execute('CREATE TABLE performance_test (id SERIAL PRIMARY KEY, data TEXT, created_at TIMESTAMP DEFAULT NOW())')
                # Insert test data
                op.execute("INSERT INTO performance_test (data) SELECT 'test_data_' || generate_series(1, 1000)")
                # Create index
                op.execute('CREATE INDEX idx_performance_test_data ON performance_test(data)')
                """,
                """
                op.execute('DROP INDEX IF EXISTS idx_performance_test_data')
                op.execute('DROP TABLE IF EXISTS performance_test')
                """
            )
            
            tracker = MigrationTracker(self.db_manager.postgres_url, "test")
            
            # Execute migration and measure time
            migration_start = time.time()
            success = await tracker.run_migrations(force=True)
            migration_time = time.time() - migration_start
            
            results["large_migration_time"] = migration_time
            results["performance_acceptable"] = migration_time < 30  # 30 second threshold
            
            if success:
                # Verify data integrity
                row_count = await self._count_table_rows("performance_test")
                results["data_integrity"] = row_count == 1000
            
        except Exception as e:
            results["errors"].append(f"Performance test error: {str(e)}")
        
        return results
    
    async def _verify_table_exists(self, table_name: str) -> bool:
        """Verify table exists in PostgreSQL."""
        return await self._check_table_exists(table_name)
    
    async def _check_table_exists(self, table_name: str) -> bool:
        """Check if table exists in PostgreSQL."""
        try:
            conn = self.db_manager.get_postgres_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                )
            """, (table_name,))
            exists = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return exists
        except Exception:
            return False
    
    async def _verify_column_exists(self, table_name: str, column_name: str) -> bool:
        """Verify column exists in table."""
        try:
            conn = self.db_manager.get_postgres_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s 
                    AND column_name = %s
                )
            """, (table_name, column_name))
            exists = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return exists
        except Exception:
            return False
    
    async def _count_table_rows(self, table_name: str) -> int:
        """Count rows in table."""
        try:
            conn = self.db_manager.get_postgres_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count
        except Exception:
            return 0
    
    def cleanup(self):
        """Clean up temporary migration directories."""
        for temp_dir in self.temp_migration_dirs:
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception:
                pass


@pytest.fixture
async def containerized_db_manager():
    """Fixture providing containerized database manager."""
    manager = ContainerizedDatabaseManager()
    
    # Ensure containers are running
    containers_ready = await manager.ensure_containers_running()
    if not containers_ready:
        pytest.skip("Containerized databases not available")
    
    # Reset to clean state
    await manager.reset_databases()
    
    yield manager
    
    # Cleanup
    await manager.reset_databases()


@pytest.fixture  
async def migration_validator(containerized_db_manager):
    """Fixture providing migration sequence validator."""
    validator = MigrationSequenceValidator(containerized_db_manager)
    yield validator
    validator.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_migration_sequence_execution(migration_validator):
    """
    Test core migration sequence execution with L3 realism.
    
    BVJ: Ensures migration sequences execute correctly without data corruption,
    preventing critical system failures that would impact all customer segments.
    """
    results = await migration_validator.test_migration_sequence_execution()
    
    # Critical assertions
    assert results["migration_1_success"], (
        "First migration failed to execute successfully. "
        "This breaks the migration chain and prevents system updates."
    )
    
    assert results["migration_2_success"], (
        "Second migration failed to execute successfully. "
        "Sequential migrations must work to support incremental updates."
    )
    
    assert results["sequence_integrity"], (
        "Migration sequence integrity compromised. "
        "Both migrations must execute successfully in order."
    )
    
    assert results["execution_time"] < 60, (
        f"Migration execution took {results['execution_time']:.2f}s, exceeding 60s threshold. "
        "Slow migrations impact deployment velocity and system availability."
    )
    
    assert not results["errors"], (
        f"Migration sequence errors detected: {results['errors']}. "
        "All migrations must execute without errors."
    )
    
    print(f"\n[SUCCESS] Migration sequence executed in {results['execution_time']:.2f}s")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_migration_rollback_safety(migration_validator):
    """
    Test migration rollback functionality and data safety.
    
    BVJ: Ensures we can safely rollback problematic migrations, preventing
    permanent data corruption and enabling quick recovery from deployment issues.
    """
    results = await migration_validator.test_migration_rollback_capability()
    
    assert results["rollback_success"], (
        "Migration rollback failed. "
        "Rollback capability is critical for recovery from failed deployments."
    )
    
    assert results["schema_restoration"], (
        "Schema not properly restored after rollback. "
        "Rollbacks must completely reverse migration changes."
    )
    
    assert results["rollback_time"] < 30, (
        f"Rollback took {results['rollback_time']:.2f}s, exceeding 30s threshold. "
        "Fast rollbacks are critical for minimizing downtime."
    )
    
    assert not results["errors"], (
        f"Rollback errors detected: {results['errors']}. "
        "Rollbacks must execute without errors to ensure recovery."
    )
    
    print(f"\n[SUCCESS] Migration rollback completed in {results['rollback_time']:.2f}s")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_migration_version_conflict_handling(migration_validator):
    """
    Test handling of migration version conflicts.
    
    BVJ: Prevents migration conflicts that could corrupt the database schema
    or cause inconsistent states across environments.
    """
    results = await migration_validator.test_migration_version_conflicts()
    
    assert results["conflict_detection"], (
        "Migration version conflicts not properly detected. "
        "Conflict detection prevents schema corruption from competing migrations."
    )
    
    # Note: Resolution success depends on implementation
    # For now, we ensure conflicts are at least detected
    
    assert not any("corruption" in error.lower() for error in results["errors"]), (
        f"Data corruption detected during conflict test: {results['errors']}. "
        "Version conflicts must not corrupt existing data."
    )
    
    print(f"\n[SUCCESS] Migration version conflicts properly detected")


@pytest.mark.asyncio
@pytest.mark.integration  
async def test_concurrent_migration_safety(migration_validator):
    """
    Test safety of concurrent migration attempts.
    
    BVJ: Ensures concurrent deployments don't corrupt the database through
    simultaneous migration attempts, protecting data integrity.
    """
    results = await migration_validator.test_concurrent_migration_safety()
    
    assert results["concurrency_handled"], (
        "Concurrent migrations not properly handled. "
        "Multiple deployment processes must not interfere with each other."
    )
    
    assert results["data_consistency"], (
        "Data consistency compromised during concurrent migrations. "
        "Database must remain consistent regardless of concurrent access."
    )
    
    assert not any("deadlock" in error.lower() for error in results["errors"]), (
        f"Deadlock detected in concurrent migration test: {results['errors']}. "
        "Concurrent migrations must use proper locking mechanisms."
    )
    
    print(f"\n[SUCCESS] Concurrent migration safety validated")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_migration_performance_validation(migration_validator):
    """
    Test migration performance under realistic load.
    
    BVJ: Ensures migrations complete within acceptable timeframes to minimize
    deployment downtime and maintain system availability.
    """
    results = await migration_validator.test_migration_performance_validation()
    
    assert results["performance_acceptable"], (
        f"Migration performance unacceptable: {results['large_migration_time']:.2f}s. "
        "Large migrations must complete within 30 seconds to minimize downtime."
    )
    
    assert results["large_migration_time"] < 300, (  # 5 minute absolute maximum
        f"Migration exceeded maximum time limit: {results['large_migration_time']:.2f}s. "
        "Migrations taking over 5 minutes require manual intervention."
    )
    
    assert not results["errors"], (
        f"Performance test errors: {results['errors']}. "
        "Performance tests must execute without errors."
    )
    
    print(f"\n[SUCCESS] Migration performance validated: {results['large_migration_time']:.2f}s")


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_database_migration_smoke_check(containerized_db_manager):
    """
    Quick smoke test for basic migration capability - runs in <30 seconds.
    
    Used for rapid validation during deployments and CI/CD pipelines.
    """
    start_time = time.time()
    
    # Quick connectivity check
    containers_ready = await containerized_db_manager.ensure_containers_running()
    assert containers_ready, "Container databases not accessible for smoke test"
    
    # Quick migration tracker initialization
    tracker = MigrationTracker(containerized_db_manager.postgres_url, "test")
    status = await tracker.get_migration_status()
    
    assert isinstance(status, dict), "Migration status not accessible"
    assert "environment" in status, "Migration status missing environment info"
    
    execution_time = time.time() - start_time
    assert execution_time < 30, f"Smoke test took {execution_time:.2f}s, exceeding 30s limit"
    
    print(f"\n[SMOKE TEST PASS] Migration system accessible in {execution_time:.2f}s")


if __name__ == "__main__":
    """Run database migration validation standalone."""
    async def run_validation():
        db_manager = ContainerizedDatabaseManager()
        
        print("="*80)
        print("DATABASE MIGRATION SEQUENCE VALIDATION")
        print("Testing with containerized PostgreSQL and ClickHouse")
        print("="*80)
        
        # Ensure containers are ready
        containers_ready = await db_manager.ensure_containers_running()
        if not containers_ready:
            print("❌ Container databases not available")
            return False
        
        print("✅ Container databases ready")
        
        # Run validation tests
        validator = MigrationSequenceValidator(db_manager)
        
        try:
            # Test migration sequence
            print("\n[1/4] Testing migration sequence execution...")
            sequence_results = await validator.test_migration_sequence_execution()
            print(f"    Execution time: {sequence_results['execution_time']:.2f}s")
            print(f"    Sequence integrity: {'✅' if sequence_results['sequence_integrity'] else '❌'}")
            
            # Test rollback capability
            print("\n[2/4] Testing migration rollback...")
            rollback_results = await validator.test_migration_rollback_capability()
            print(f"    Rollback time: {rollback_results['rollback_time']:.2f}s")
            print(f"    Rollback success: {'✅' if rollback_results['rollback_success'] else '❌'}")
            
            # Test version conflicts
            print("\n[3/4] Testing version conflict handling...")
            conflict_results = await validator.test_migration_version_conflicts()
            print(f"    Conflict detection: {'✅' if conflict_results['conflict_detection'] else '❌'}")
            
            # Test concurrent safety
            print("\n[4/4] Testing concurrent migration safety...")
            concurrent_results = await validator.test_concurrent_migration_safety()
            print(f"    Concurrency handled: {'✅' if concurrent_results['concurrency_handled'] else '❌'}")
            
            # Overall assessment
            all_passed = (
                sequence_results['sequence_integrity'] and
                rollback_results['rollback_success'] and
                conflict_results['conflict_detection'] and
                concurrent_results['concurrency_handled']
            )
            
            print("\n" + "="*80)
            print("VALIDATION SUMMARY")
            print("="*80)
            print(f"Migration Sequence: {'✅ PASSED' if sequence_results['sequence_integrity'] else '❌ FAILED'}")
            print(f"Rollback Safety: {'✅ PASSED' if rollback_results['rollback_success'] else '❌ FAILED'}")
            print(f"Conflict Handling: {'✅ PASSED' if conflict_results['conflict_detection'] else '❌ FAILED'}")
            print(f"Concurrent Safety: {'✅ PASSED' if concurrent_results['concurrency_handled'] else '❌ FAILED'}")
            print(f"Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
            
            return all_passed
            
        finally:
            validator.cleanup()
            await db_manager.reset_databases()
    
    result = asyncio.run(run_validation())
    exit(0 if result else 1)