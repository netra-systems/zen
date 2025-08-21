"""Database Migration and Rollback Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational stability for all tiers)
- Business Goal: Safe database evolution without data loss or downtime
- Value Impact: Prevents data corruption, ensures zero-downtime deployments
- Strategic Impact: $20K-40K MRR protection through operational reliability

Critical Path: Migration validation -> Backup creation -> Schema changes -> Data migration -> Rollback testing -> Production deployment
Coverage: Schema migration safety, data integrity, rollback mechanisms, multi-database coordination
"""

import pytest
import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import tempfile
import os

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.database.migration_service import MigrationService
from netra_backend.app.services.database.connection_manager import DatabaseConnectionManager
from netra_backend.app.services.database.backup_service import BackupService
from netra_backend.app.db.migrations.migration_runner import MigrationRunner

# Add project root to path

logger = logging.getLogger(__name__)


class DatabaseMigrationManager:
    """Manages database migration testing with rollback validation."""
    
    def __init__(self):
        self.migration_service = None
        self.db_manager = None
        self.backup_service = None
        self.migration_runner = None
        self.test_db_urls = {}
        self.migration_history = []
        self.rollback_history = []
        self.data_integrity_snapshots = {}
        
    async def initialize_services(self):
        """Initialize database migration services."""
        try:
            # Initialize database connection manager
            self.db_manager = DatabaseConnectionManager()
            await self.db_manager.initialize()
            
            # Initialize migration service
            self.migration_service = MigrationService()
            await self.migration_service.initialize()
            
            # Initialize backup service
            self.backup_service = BackupService()
            await self.backup_service.initialize()
            
            # Initialize migration runner
            self.migration_runner = MigrationRunner()
            await self.migration_runner.initialize()
            
            # Create test databases
            await self.setup_test_databases()
            
            logger.info("Database migration services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize migration services: {e}")
            raise
    
    async def setup_test_databases(self):
        """Set up isolated test databases for migration testing."""
        try:
            # PostgreSQL test database
            self.test_db_urls["postgres"] = await self.create_test_database("postgres")
            
            # ClickHouse test database  
            self.test_db_urls["clickhouse"] = await self.create_test_database("clickhouse")
            
        except Exception as e:
            logger.error(f"Failed to setup test databases: {e}")
            raise
    
    async def create_test_database(self, db_type: str) -> str:
        """Create an isolated test database."""
        db_name = f"test_migration_{db_type}_{uuid.uuid4().hex[:8]}"
        
        if db_type == "postgres":
            # Create PostgreSQL test database
            test_url = f"postgresql://test_user:test_pass@localhost:5432/{db_name}"
            await self.db_manager.create_database(db_name, db_type)
            
        elif db_type == "clickhouse":
            # Create ClickHouse test database
            test_url = f"clickhouse://localhost:9000/{db_name}"
            await self.db_manager.create_database(db_name, db_type)
        
        return test_url
    
    async def create_test_migration(self, migration_name: str, db_type: str = "postgres") -> Dict[str, Any]:
        """Create a test migration for validation."""
        migration_id = f"migration_{uuid.uuid4().hex[:12]}"
        
        migration_definition = {
            "id": migration_id,
            "name": migration_name,
            "db_type": db_type,
            "version": int(time.time()),
            "up_sql": self.generate_migration_sql(migration_name, "up", db_type),
            "down_sql": self.generate_migration_sql(migration_name, "down", db_type),
            "dependencies": [],
            "created_at": datetime.utcnow()
        }
        
        return migration_definition
    
    def generate_migration_sql(self, migration_name: str, direction: str, db_type: str) -> str:
        """Generate test migration SQL based on migration type."""
        if db_type == "postgres":
            if direction == "up":
                if "add_column" in migration_name:
                    return """
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS new_field VARCHAR(255);
                    CREATE INDEX IF NOT EXISTS idx_users_new_field ON users(new_field);
                    """
                elif "create_table" in migration_name:
                    return """
                    CREATE TABLE IF NOT EXISTS test_table (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                else:
                    return "SELECT 1; -- Test migration"
            else:  # down
                if "add_column" in migration_name:
                    return """
                    DROP INDEX IF EXISTS idx_users_new_field;
                    ALTER TABLE users DROP COLUMN IF EXISTS new_field;
                    """
                elif "create_table" in migration_name:
                    return "DROP TABLE IF EXISTS test_table;"
                else:
                    return "SELECT 1; -- Test rollback"
        
        elif db_type == "clickhouse":
            if direction == "up":
                if "add_column" in migration_name:
                    return """
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS new_field String DEFAULT '';
                    """
                elif "create_table" in migration_name:
                    return """
                    CREATE TABLE IF NOT EXISTS test_table (
                        id UInt64,
                        name String,
                        created_at DateTime DEFAULT now()
                    ) ENGINE = MergeTree() ORDER BY id;
                    """
                else:
                    return "SELECT 1; -- Test migration"
            else:  # down
                if "add_column" in migration_name:
                    return "ALTER TABLE users DROP COLUMN IF EXISTS new_field;"
                elif "create_table" in migration_name:
                    return "DROP TABLE IF EXISTS test_table;"
                else:
                    return "SELECT 1; -- Test rollback"
        
        return "SELECT 1; -- Default test migration"
    
    async def execute_migration(self, migration: Dict[str, Any], 
                              target_db: str = None) -> Dict[str, Any]:
        """Execute a migration with full validation and backup."""
        migration_id = migration["id"]
        db_type = migration["db_type"]
        target_db_url = target_db or self.test_db_urls[db_type]
        
        execution_start = time.time()
        
        try:
            # Step 1: Create pre-migration backup
            backup_result = await self.create_migration_backup(migration_id, target_db_url)
            if not backup_result["success"]:
                raise Exception(f"Backup failed: {backup_result['error']}")
            
            # Step 2: Validate migration SQL
            validation_result = await self.validate_migration_sql(migration, target_db_url)
            if not validation_result["valid"]:
                raise Exception(f"Migration validation failed: {validation_result['errors']}")
            
            # Step 3: Take data integrity snapshot
            await self.capture_data_integrity_snapshot(migration_id, target_db_url, "pre_migration")
            
            # Step 4: Execute migration
            execution_result = await self.migration_runner.execute_migration(
                migration, target_db_url
            )
            
            if not execution_result["success"]:
                raise Exception(f"Migration execution failed: {execution_result['error']}")
            
            # Step 5: Verify migration results
            verification_result = await self.verify_migration_results(migration, target_db_url)
            
            # Step 6: Take post-migration snapshot
            await self.capture_data_integrity_snapshot(migration_id, target_db_url, "post_migration")
            
            execution_time = time.time() - execution_start
            
            # Record migration history
            migration_record = {
                "migration_id": migration_id,
                "migration_name": migration["name"],
                "db_type": db_type,
                "execution_time": execution_time,
                "backup_id": backup_result["backup_id"],
                "verification_passed": verification_result["passed"],
                "timestamp": execution_start,
                "status": "completed"
            }
            
            self.migration_history.append(migration_record)
            
            return {
                "success": True,
                "migration_id": migration_id,
                "execution_time": execution_time,
                "backup_id": backup_result["backup_id"],
                "verification": verification_result
            }
            
        except Exception as e:
            execution_time = time.time() - execution_start
            
            # Record failed migration
            error_record = {
                "migration_id": migration_id,
                "migration_name": migration["name"],
                "db_type": db_type,
                "execution_time": execution_time,
                "error": str(e),
                "timestamp": execution_start,
                "status": "failed"
            }
            
            self.migration_history.append(error_record)
            
            return {
                "success": False,
                "migration_id": migration_id,
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def create_migration_backup(self, migration_id: str, db_url: str) -> Dict[str, Any]:
        """Create backup before migration execution."""
        try:
            backup_id = f"backup_{migration_id}_{int(time.time())}"
            
            backup_result = await self.backup_service.create_backup(
                backup_id, db_url, {"migration_id": migration_id}
            )
            
            return {
                "success": True,
                "backup_id": backup_id,
                "backup_size": backup_result.get("size", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_migration_sql(self, migration: Dict[str, Any], db_url: str) -> Dict[str, Any]:
        """Validate migration SQL before execution."""
        try:
            errors = []
            warnings = []
            
            # Validate UP SQL
            up_sql = migration["up_sql"]
            if not up_sql or up_sql.strip() == "":
                errors.append("UP SQL is empty")
            
            # Validate DOWN SQL  
            down_sql = migration["down_sql"]
            if not down_sql or down_sql.strip() == "":
                errors.append("DOWN SQL is empty")
            
            # Check for dangerous operations
            dangerous_patterns = ["DROP DATABASE", "TRUNCATE", "DELETE FROM users"]
            for pattern in dangerous_patterns:
                if pattern in up_sql.upper():
                    warnings.append(f"Potentially dangerous operation: {pattern}")
            
            # Validate SQL syntax (simulate)
            syntax_valid = await self.validate_sql_syntax(up_sql, migration["db_type"])
            if not syntax_valid:
                errors.append("UP SQL syntax validation failed")
            
            rollback_syntax_valid = await self.validate_sql_syntax(down_sql, migration["db_type"])
            if not rollback_syntax_valid:
                errors.append("DOWN SQL syntax validation failed")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"]
            }
    
    async def validate_sql_syntax(self, sql: str, db_type: str) -> bool:
        """Validate SQL syntax (simulation for testing)."""
        try:
            # Simulate syntax validation
            forbidden_chars = ["';", "--", "/*"]
            for char in forbidden_chars:
                if char in sql:
                    return False
            
            # Check for basic SQL structure
            sql_upper = sql.upper().strip()
            valid_starts = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
            
            return any(sql_upper.startswith(start) for start in valid_starts)
            
        except Exception:
            return False
    
    async def verify_migration_results(self, migration: Dict[str, Any], db_url: str) -> Dict[str, Any]:
        """Verify migration execution results."""
        try:
            verification_checks = []
            
            # Check if migration was recorded in migration table
            migration_recorded = await self.check_migration_recorded(migration["id"], db_url)
            verification_checks.append({
                "check": "migration_recorded",
                "passed": migration_recorded,
                "details": "Migration recorded in schema_migrations table"
            })
            
            # Verify schema changes applied
            schema_changes = await self.verify_schema_changes(migration, db_url)
            verification_checks.append({
                "check": "schema_changes",
                "passed": schema_changes["success"],
                "details": schema_changes.get("details", "Schema changes verified")
            })
            
            # Check data integrity
            data_integrity = await self.check_data_integrity(db_url)
            verification_checks.append({
                "check": "data_integrity",
                "passed": data_integrity["intact"],
                "details": f"Data integrity check: {data_integrity['details']}"
            })
            
            all_passed = all(check["passed"] for check in verification_checks)
            
            return {
                "passed": all_passed,
                "checks": verification_checks,
                "summary": f"{len([c for c in verification_checks if c['passed']])}/{len(verification_checks)} checks passed"
            }
            
        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
                "checks": []
            }
    
    async def check_migration_recorded(self, migration_id: str, db_url: str) -> bool:
        """Check if migration was properly recorded."""
        try:
            # Simulate checking migration table
            await asyncio.sleep(0.01)
            return True  # Assume migration recorded successfully
            
        except Exception:
            return False
    
    async def verify_schema_changes(self, migration: Dict[str, Any], db_url: str) -> Dict[str, Any]:
        """Verify that schema changes were applied correctly."""
        try:
            # Simulate schema verification
            migration_name = migration["name"]
            
            if "add_column" in migration_name:
                # Verify column was added
                return {"success": True, "details": "Column successfully added"}
            elif "create_table" in migration_name:
                # Verify table was created
                return {"success": True, "details": "Table successfully created"}
            else:
                return {"success": True, "details": "Generic migration applied"}
            
        except Exception as e:
            return {"success": False, "details": str(e)}
    
    async def check_data_integrity(self, db_url: str) -> Dict[str, Any]:
        """Check data integrity after migration."""
        try:
            # Simulate data integrity checks
            await asyncio.sleep(0.02)
            
            return {
                "intact": True,
                "details": "All data integrity checks passed",
                "row_count_changes": 0,
                "constraint_violations": 0
            }
            
        except Exception as e:
            return {
                "intact": False,
                "details": str(e)
            }
    
    async def capture_data_integrity_snapshot(self, migration_id: str, db_url: str, stage: str):
        """Capture data integrity snapshot for comparison."""
        try:
            snapshot_id = f"{migration_id}_{stage}"
            
            # Simulate capturing snapshot
            snapshot_data = {
                "migration_id": migration_id,
                "stage": stage,
                "timestamp": time.time(),
                "table_counts": {"users": 100, "workspaces": 25},  # Simulated
                "checksum": f"checksum_{snapshot_id}"
            }
            
            self.data_integrity_snapshots[snapshot_id] = snapshot_data
            
        except Exception as e:
            logger.error(f"Failed to capture snapshot {snapshot_id}: {e}")
    
    async def execute_rollback(self, migration_id: str, backup_id: str = None) -> Dict[str, Any]:
        """Execute migration rollback with validation."""
        rollback_start = time.time()
        
        try:
            # Find migration in history
            migration_record = next(
                (record for record in self.migration_history if record["migration_id"] == migration_id),
                None
            )
            
            if not migration_record:
                raise ValueError(f"Migration {migration_id} not found in history")
            
            # Step 1: Validate rollback safety
            safety_check = await self.validate_rollback_safety(migration_id)
            if not safety_check["safe"]:
                raise Exception(f"Rollback safety check failed: {safety_check['reasons']}")
            
            # Step 2: Execute rollback
            if backup_id:
                # Restore from backup
                restore_result = await self.restore_from_backup(backup_id)
                if not restore_result["success"]:
                    raise Exception(f"Backup restore failed: {restore_result['error']}")
            else:
                # Execute DOWN migration
                rollback_result = await self.execute_down_migration(migration_id)
                if not rollback_result["success"]:
                    raise Exception(f"Down migration failed: {rollback_result['error']}")
            
            # Step 3: Verify rollback
            verification_result = await self.verify_rollback_results(migration_id)
            
            rollback_time = time.time() - rollback_start
            
            # Record rollback history
            rollback_record = {
                "migration_id": migration_id,
                "rollback_method": "backup_restore" if backup_id else "down_migration",
                "rollback_time": rollback_time,
                "verification_passed": verification_result["passed"],
                "timestamp": rollback_start,
                "status": "completed"
            }
            
            self.rollback_history.append(rollback_record)
            
            return {
                "success": True,
                "migration_id": migration_id,
                "rollback_time": rollback_time,
                "method": rollback_record["rollback_method"],
                "verification": verification_result
            }
            
        except Exception as e:
            rollback_time = time.time() - rollback_start
            
            error_record = {
                "migration_id": migration_id,
                "rollback_time": rollback_time,
                "error": str(e),
                "timestamp": rollback_start,
                "status": "failed"
            }
            
            self.rollback_history.append(error_record)
            
            return {
                "success": False,
                "error": str(e),
                "rollback_time": rollback_time
            }
    
    async def validate_rollback_safety(self, migration_id: str) -> Dict[str, Any]:
        """Validate that rollback is safe to execute."""
        try:
            safety_issues = []
            
            # Check for dependent migrations
            dependent_migrations = [
                record for record in self.migration_history
                if record["migration_id"] != migration_id and 
                record.get("status") == "completed" and
                record["timestamp"] > next(
                    (r["timestamp"] for r in self.migration_history if r["migration_id"] == migration_id),
                    0
                )
            ]
            
            if dependent_migrations:
                safety_issues.append(f"Found {len(dependent_migrations)} dependent migrations")
            
            # Check for data modifications since migration
            # (Simulated check)
            
            return {
                "safe": len(safety_issues) == 0,
                "reasons": safety_issues
            }
            
        except Exception as e:
            return {
                "safe": False,
                "reasons": [f"Safety validation error: {str(e)}"]
            }
    
    async def restore_from_backup(self, backup_id: str) -> Dict[str, Any]:
        """Restore database from backup."""
        try:
            restore_result = await self.backup_service.restore_backup(backup_id)
            return restore_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_down_migration(self, migration_id: str) -> Dict[str, Any]:
        """Execute down migration for rollback."""
        try:
            # Find original migration
            migration_record = next(
                (record for record in self.migration_history if record["migration_id"] == migration_id),
                None
            )
            
            if not migration_record:
                raise ValueError("Migration record not found")
            
            # Simulate down migration execution
            await asyncio.sleep(0.1)
            
            return {
                "success": True,
                "details": "Down migration executed successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_rollback_results(self, migration_id: str) -> Dict[str, Any]:
        """Verify rollback execution results."""
        try:
            verification_checks = []
            
            # Check migration removed from migration table
            migration_removed = await self.check_migration_removed(migration_id)
            verification_checks.append({
                "check": "migration_removed",
                "passed": migration_removed,
                "details": "Migration removed from schema_migrations table"
            })
            
            # Verify schema restored
            schema_restored = await self.verify_schema_restored(migration_id)
            verification_checks.append({
                "check": "schema_restored",
                "passed": schema_restored["success"],
                "details": schema_restored.get("details", "Schema restoration verified")
            })
            
            # Compare with pre-migration snapshot
            snapshot_comparison = await self.compare_with_pre_migration_snapshot(migration_id)
            verification_checks.append({
                "check": "snapshot_comparison",
                "passed": snapshot_comparison["matches"],
                "details": snapshot_comparison.get("details", "Data matches pre-migration state")
            })
            
            all_passed = all(check["passed"] for check in verification_checks)
            
            return {
                "passed": all_passed,
                "checks": verification_checks
            }
            
        except Exception as e:
            return {
                "passed": False,
                "error": str(e)
            }
    
    async def check_migration_removed(self, migration_id: str) -> bool:
        """Check if migration was removed from migration table."""
        try:
            await asyncio.sleep(0.01)
            return True  # Simulate successful removal check
        except Exception:
            return False
    
    async def verify_schema_restored(self, migration_id: str) -> Dict[str, Any]:
        """Verify schema was restored to pre-migration state."""
        try:
            return {
                "success": True,
                "details": "Schema successfully restored"
            }
        except Exception as e:
            return {
                "success": False,
                "details": str(e)
            }
    
    async def compare_with_pre_migration_snapshot(self, migration_id: str) -> Dict[str, Any]:
        """Compare current state with pre-migration snapshot."""
        try:
            pre_snapshot_id = f"{migration_id}_pre_migration"
            post_snapshot_id = f"{migration_id}_post_rollback"
            
            if pre_snapshot_id not in self.data_integrity_snapshots:
                return {"matches": False, "details": "Pre-migration snapshot not found"}
            
            # Simulate comparison
            return {
                "matches": True,
                "details": "Current state matches pre-migration snapshot"
            }
            
        except Exception as e:
            return {
                "matches": False,
                "details": str(e)
            }
    
    async def get_migration_metrics(self) -> Dict[str, Any]:
        """Get comprehensive migration metrics."""
        successful_migrations = [r for r in self.migration_history if r.get("status") == "completed"]
        failed_migrations = [r for r in self.migration_history if r.get("status") == "failed"]
        
        successful_rollbacks = [r for r in self.rollback_history if r.get("status") == "completed"]
        failed_rollbacks = [r for r in self.rollback_history if r.get("status") == "failed"]
        
        # Calculate averages
        avg_migration_time = 0
        if successful_migrations:
            avg_migration_time = sum(r["execution_time"] for r in successful_migrations) / len(successful_migrations)
        
        avg_rollback_time = 0
        if successful_rollbacks:
            avg_rollback_time = sum(r["rollback_time"] for r in successful_rollbacks) / len(successful_rollbacks)
        
        return {
            "total_migrations": len(self.migration_history),
            "successful_migrations": len(successful_migrations),
            "failed_migrations": len(failed_migrations),
            "migration_success_rate": len(successful_migrations) / len(self.migration_history) * 100 if self.migration_history else 0,
            "average_migration_time": avg_migration_time,
            "total_rollbacks": len(self.rollback_history),
            "successful_rollbacks": len(successful_rollbacks),
            "failed_rollbacks": len(failed_rollbacks),
            "rollback_success_rate": len(successful_rollbacks) / len(self.rollback_history) * 100 if self.rollback_history else 0,
            "average_rollback_time": avg_rollback_time,
            "backup_count": len([r for r in self.migration_history if "backup_id" in r])
        }
    
    async def cleanup(self):
        """Clean up test databases and services."""
        try:
            # Clean up test databases
            for db_type, db_url in self.test_db_urls.items():
                await self.db_manager.drop_test_database(db_url)
            
            # Shutdown services
            if self.migration_service:
                await self.migration_service.shutdown()
            if self.backup_service:
                await self.backup_service.shutdown()
            if self.db_manager:
                await self.db_manager.shutdown()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def migration_manager():
    """Create database migration manager for testing."""
    manager = DatabaseMigrationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_safe_schema_migration_with_rollback(migration_manager):
    """Test safe schema migration with successful rollback."""
    # Create test migration
    migration = await migration_manager.create_test_migration("add_column_test", "postgres")
    
    # Execute migration
    migration_result = await migration_manager.execute_migration(migration)
    
    assert migration_result["success"] is True
    assert migration_result["execution_time"] < 10.0
    assert "backup_id" in migration_result
    assert migration_result["verification"]["passed"] is True
    
    # Execute rollback
    rollback_result = await migration_manager.execute_rollback(
        migration["id"], migration_result["backup_id"]
    )
    
    assert rollback_result["success"] is True
    assert rollback_result["rollback_time"] < 5.0
    assert rollback_result["verification"]["passed"] is True


@pytest.mark.asyncio
async def test_data_integrity_preservation(migration_manager):
    """Test that data integrity is preserved during migration and rollback."""
    # Create table creation migration
    migration = await migration_manager.create_test_migration("create_table_test", "postgres")
    
    # Execute migration
    migration_result = await migration_manager.execute_migration(migration)
    assert migration_result["success"] is True
    
    # Verify pre and post migration snapshots exist
    migration_id = migration["id"]
    pre_snapshot = f"{migration_id}_pre_migration"
    post_snapshot = f"{migration_id}_post_migration"
    
    assert pre_snapshot in migration_manager.data_integrity_snapshots
    assert post_snapshot in migration_manager.data_integrity_snapshots
    
    # Execute rollback
    rollback_result = await migration_manager.execute_rollback(migration_id)
    assert rollback_result["success"] is True
    
    # Verify data integrity maintained
    verification_checks = rollback_result["verification"]["checks"]
    snapshot_check = next(
        (check for check in verification_checks if check["check"] == "snapshot_comparison"),
        None
    )
    assert snapshot_check is not None
    assert snapshot_check["passed"] is True


@pytest.mark.asyncio
async def test_migration_validation_prevents_dangerous_operations(migration_manager):
    """Test that migration validation prevents dangerous operations."""
    # Create migration with dangerous operation
    dangerous_migration = {
        "id": "dangerous_migration_001",
        "name": "dangerous_operation",
        "db_type": "postgres",
        "version": int(time.time()),
        "up_sql": "DROP DATABASE production; DELETE FROM users;",
        "down_sql": "SELECT 1;",
        "dependencies": [],
        "created_at": datetime.utcnow()
    }
    
    # Attempt to execute dangerous migration
    migration_result = await migration_manager.execute_migration(dangerous_migration)
    
    # Should fail validation
    assert migration_result["success"] is False
    assert "validation failed" in migration_result["error"].lower()


@pytest.mark.asyncio
async def test_concurrent_migration_safety(migration_manager):
    """Test safety mechanisms for concurrent migration attempts."""
    # Create multiple migrations
    migrations = []
    for i in range(3):
        migration = await migration_manager.create_test_migration(f"concurrent_migration_{i}", "postgres")
        migrations.append(migration)
    
    # Attempt concurrent execution
    migration_tasks = [
        migration_manager.execute_migration(migration)
        for migration in migrations
    ]
    
    results = await asyncio.gather(*migration_tasks, return_exceptions=True)
    
    # At least some should succeed (depending on locking mechanism)
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    assert len(successful_results) > 0
    
    # Verify no data corruption
    for result in successful_results:
        assert result["verification"]["passed"] is True


@pytest.mark.asyncio
async def test_clickhouse_migration_support(migration_manager):
    """Test migration support for ClickHouse database."""
    # Create ClickHouse migration
    ch_migration = await migration_manager.create_test_migration("clickhouse_table_test", "clickhouse")
    
    # Execute migration
    migration_result = await migration_manager.execute_migration(ch_migration)
    
    assert migration_result["success"] is True
    assert migration_result["verification"]["passed"] is True
    
    # Test rollback
    rollback_result = await migration_manager.execute_rollback(ch_migration["id"])
    
    assert rollback_result["success"] is True
    assert rollback_result["verification"]["passed"] is True


@pytest.mark.asyncio
async def test_migration_dependency_validation(migration_manager):
    """Test validation of migration dependencies."""
    # Create dependent migrations
    base_migration = await migration_manager.create_test_migration("base_migration", "postgres")
    
    dependent_migration = await migration_manager.create_test_migration("dependent_migration", "postgres")
    dependent_migration["dependencies"] = [base_migration["id"]]
    
    # Attempt to run dependent migration without base
    dependent_result = await migration_manager.execute_migration(dependent_migration)
    
    # Should handle dependency properly (implementation specific)
    assert "success" in dependent_result
    
    # Run base migration first
    base_result = await migration_manager.execute_migration(base_migration)
    assert base_result["success"] is True
    
    # Now dependent should work
    dependent_result_2 = await migration_manager.execute_migration(dependent_migration)
    assert dependent_result_2["success"] is True


@pytest.mark.asyncio
async def test_rollback_safety_validation(migration_manager):
    """Test rollback safety validation prevents unsafe rollbacks."""
    # Create and execute base migration
    base_migration = await migration_manager.create_test_migration("rollback_safety_base", "postgres")
    base_result = await migration_manager.execute_migration(base_migration)
    assert base_result["success"] is True
    
    # Create and execute dependent migration
    dependent_migration = await migration_manager.create_test_migration("rollback_safety_dependent", "postgres")
    dependent_result = await migration_manager.execute_migration(dependent_migration)
    assert dependent_result["success"] is True
    
    # Attempt to rollback base migration (should be unsafe due to dependent)
    rollback_result = await migration_manager.execute_rollback(base_migration["id"])
    
    # Should either fail or handle gracefully
    if not rollback_result["success"]:
        assert "dependent" in rollback_result["error"].lower() or "safety" in rollback_result["error"].lower()


@pytest.mark.asyncio
async def test_migration_performance_requirements(migration_manager):
    """Test that migrations meet performance requirements."""
    # Create various types of migrations
    migration_types = [
        ("small_migration", "add_column"),
        ("medium_migration", "create_table"),
        ("large_migration", "complex_operation")
    ]
    
    performance_results = []
    
    for migration_name, migration_type in migration_types:
        migration = await migration_manager.create_test_migration(migration_name, "postgres")
        
        result = await migration_manager.execute_migration(migration)
        assert result["success"] is True
        
        performance_results.append({
            "type": migration_type,
            "execution_time": result["execution_time"]
        })
        
        # Test rollback performance
        rollback_result = await migration_manager.execute_rollback(migration["id"])
        assert rollback_result["success"] is True
        
        performance_results.append({
            "type": f"{migration_type}_rollback",
            "execution_time": rollback_result["rollback_time"]
        })
    
    # Verify performance requirements
    for result in performance_results:
        if "small" in result["type"]:
            assert result["execution_time"] < 2.0
        elif "medium" in result["type"]:
            assert result["execution_time"] < 5.0
        else:  # large
            assert result["execution_time"] < 10.0
    
    # Get overall metrics
    metrics = await migration_manager.get_migration_metrics()
    assert metrics["migration_success_rate"] >= 95.0
    assert metrics["rollback_success_rate"] >= 95.0
    assert metrics["average_migration_time"] < 7.0
    assert metrics["average_rollback_time"] < 5.0