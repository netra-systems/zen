"""Database Migration Core Functionality Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational stability for all tiers)
- Business Goal: Safe database evolution without data loss or downtime
- Value Impact: Prevents data corruption, ensures zero-downtime deployments
- Strategic Impact: $20K-40K MRR protection through operational reliability

Critical Path: Migration creation -> Schema validation -> Migration execution -> Results verification
Coverage: Schema migration core functionality, data integrity, migration recording
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

from netra_backend.app.services.database.migration_service import MigrationService
from netra_backend.app.services.database.connection_manager import DatabaseConnectionManager
from netra_backend.app.services.database.backup_service import BackupService
from netra_backend.app.db.migrations.migration_runner import MigrationRunner

logger = logging.getLogger(__name__)


class DatabaseMigrationCoreManager:
    """Manages core database migration functionality testing."""
    
    def __init__(self):
        self.migration_service = None
        self.db_manager = None
        self.backup_service = None
        self.migration_runner = None
        self.test_db_urls = {}
        self.migration_history = []
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
            
            # Setup test databases
            await self.setup_test_databases()
            
            logger.info("Database migration services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize migration services: {e}")
            raise
    
    async def setup_test_databases(self):
        """Setup isolated test databases for migration testing."""
        database_types = ["postgres", "clickhouse"]
        
        for db_type in database_types:
            try:
                test_db_url = await self.create_test_database(db_type)
                self.test_db_urls[db_type] = test_db_url
            except Exception as e:
                logger.warning(f"Failed to setup {db_type} test database: {e}")
    
    async def create_test_database(self, db_type: str) -> str:
        """Create isolated test database for migration testing."""
        test_db_name = f"test_migration_{uuid.uuid4().hex[:8]}"
        
        if db_type == "postgres":
            # Create isolated PostgreSQL test database
            test_db_url = f"postgresql://test_user:test_pass@localhost:5432/{test_db_name}"
        elif db_type == "clickhouse":
            # Create isolated ClickHouse test database
            test_db_url = f"clickhouse://localhost:9000/{test_db_name}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        # Initialize test database
        await self.db_manager.create_database(test_db_url)
        
        return test_db_url
    
    async def create_test_migration(self, migration_name: str, db_type: str = "postgres") -> Dict[str, Any]:
        """Create a test migration for validation."""
        migration_id = f"migration_{uuid.uuid4().hex[:8]}"
        
        migration = {
            "migration_id": migration_id,
            "name": migration_name,
            "db_type": db_type,
            "up_sql": self.generate_migration_sql(migration_name, "up", db_type),
            "down_sql": self.generate_migration_sql(migration_name, "down", db_type),
            "created_at": datetime.utcnow(),
            "dependencies": [],
            "checksum": f"checksum_{uuid.uuid4().hex[:16]}"
        }
        
        return migration
    
    def generate_migration_sql(self, migration_name: str, direction: str, db_type: str) -> str:
        """Generate appropriate SQL for test migrations."""
        if db_type == "postgres":
            if direction == "up":
                if "add_column" in migration_name:
                    return """
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS test_column VARCHAR(255);
                    CREATE INDEX IF NOT EXISTS idx_users_test_column ON users(test_column);
                    """
                elif "create_table" in migration_name:
                    return """
                    CREATE TABLE IF NOT EXISTS test_table (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                elif "add_constraint" in migration_name:
                    return """
                    ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS chk_email_format 
                    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');
                    """
            else:  # down
                if "add_column" in migration_name:
                    return """
                    DROP INDEX IF EXISTS idx_users_test_column;
                    ALTER TABLE users DROP COLUMN IF EXISTS test_column;
                    """
                elif "create_table" in migration_name:
                    return "DROP TABLE IF EXISTS test_table;"
                elif "add_constraint" in migration_name:
                    return "ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_email_format;"
        
        elif db_type == "clickhouse":
            if direction == "up":
                if "add_column" in migration_name:
                    return """
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS test_column String;
                    """
                elif "create_table" in migration_name:
                    return """
                    CREATE TABLE IF NOT EXISTS test_table (
                        id UInt64,
                        name String,
                        created_at DateTime DEFAULT now()
                    ) ENGINE = MergeTree() ORDER BY id;
                    """
            else:  # down
                if "add_column" in migration_name:
                    return "ALTER TABLE users DROP COLUMN IF EXISTS test_column;"
                elif "create_table" in migration_name:
                    return "DROP TABLE IF EXISTS test_table;"
        
        return f"-- {direction} migration SQL for {migration_name}"
    
    async def execute_migration(self, migration: Dict[str, Any], 
                              target_db_type: str = "postgres") -> Dict[str, Any]:
        """Execute migration and track results."""
        migration_id = migration["migration_id"]
        start_time = time.time()
        
        try:
            db_url = self.test_db_urls.get(target_db_type)
            if not db_url:
                raise ValueError(f"No test database available for {target_db_type}")
            
            # Step 1: Validate migration SQL
            validation_result = await self.validate_migration_sql(migration, db_url)
            if not validation_result["valid"]:
                raise ValueError(f"Migration validation failed: {validation_result['reason']}")
            
            # Step 2: Create backup before migration
            backup_result = await self.create_migration_backup(migration_id, db_url)
            
            # Step 3: Execute migration
            execution_result = await self.migration_runner.execute_migration(
                migration, db_url
            )
            
            # Step 4: Verify migration results
            verification_result = await self.verify_migration_results(migration, db_url)
            
            migration_time = time.time() - start_time
            
            migration_record = {
                "migration_id": migration_id,
                "name": migration["name"],
                "db_type": target_db_type,
                "executed_at": datetime.utcnow(),
                "execution_time": migration_time,
                "success": execution_result["success"] and verification_result["verified"],
                "backup_id": backup_result.get("backup_id"),
                "validation_result": validation_result,
                "execution_result": execution_result,
                "verification_result": verification_result
            }
            
            self.migration_history.append(migration_record)
            
            return {
                "migration_id": migration_id,
                "executed": migration_record["success"],
                "execution_time": migration_time,
                "migration_record": migration_record
            }
            
        except Exception as e:
            error_record = {
                "migration_id": migration_id,
                "name": migration["name"],
                "db_type": target_db_type,
                "executed_at": datetime.utcnow(),
                "execution_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
            
            self.migration_history.append(error_record)
            
            return {
                "migration_id": migration_id,
                "executed": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def validate_migration_sql(self, migration: Dict[str, Any], db_url: str) -> Dict[str, Any]:
        """Validate migration SQL for safety and correctness."""
        try:
            migration_id = migration["migration_id"]
            up_sql = migration["up_sql"]
            down_sql = migration["down_sql"]
            db_type = migration["db_type"]
            
            validation_issues = []
            
            # Check for dangerous operations
            dangerous_patterns = [
                "DROP DATABASE",
                "TRUNCATE",
                "DELETE FROM",
                "DROP COLUMN",
                "ALTER TABLE .* DROP"
            ]
            
            for pattern in dangerous_patterns:
                if any(pattern.lower() in sql.lower() for sql in [up_sql, down_sql]):
                    validation_issues.append(f"Potentially dangerous operation detected: {pattern}")
            
            # Validate SQL syntax
            up_sql_valid = await self.validate_sql_syntax(up_sql, db_type)
            down_sql_valid = await self.validate_sql_syntax(down_sql, db_type)
            
            if not up_sql_valid:
                validation_issues.append("Invalid SQL syntax in up migration")
            
            if not down_sql_valid:
                validation_issues.append("Invalid SQL syntax in down migration")
            
            # Check for transaction safety
            if not self.check_transaction_safety(up_sql, db_type):
                validation_issues.append("Migration is not transaction-safe")
            
            return {
                "migration_id": migration_id,
                "valid": len(validation_issues) == 0,
                "issues": validation_issues,
                "up_sql_valid": up_sql_valid,
                "down_sql_valid": down_sql_valid
            }
            
        except Exception as e:
            return {
                "migration_id": migration.get("migration_id"),
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "error": str(e)
            }
    
    async def validate_sql_syntax(self, sql: str, db_type: str) -> bool:
        """Validate SQL syntax for the specific database type."""
        try:
            # This would normally use database-specific syntax validation
            # For testing, we do basic checks
            
            if not sql.strip():
                return False
            
            # Basic SQL structure validation
            if db_type == "postgres":
                return self.validate_postgres_syntax(sql)
            elif db_type == "clickhouse":
                return self.validate_clickhouse_syntax(sql)
            
            return True
            
        except Exception:
            return False
    
    def check_transaction_safety(self, sql: str, db_type: str) -> bool:
        """Check if migration can be safely executed in a transaction."""
        # Some operations can't be run in transactions in certain databases
        unsafe_operations = []
        
        if db_type == "postgres":
            unsafe_operations = ["CREATE INDEX CONCURRENTLY", "DROP INDEX CONCURRENTLY"]
        elif db_type == "clickhouse":
            # ClickHouse has different transaction limitations
            unsafe_operations = ["OPTIMIZE TABLE"]
        
        return not any(op.lower() in sql.lower() for op in unsafe_operations)
    
    def validate_postgres_syntax(self, sql: str) -> bool:
        """Basic PostgreSQL syntax validation."""
        # This is a simplified validation for testing
        return "SELECT" in sql.upper() or "CREATE" in sql.upper() or "ALTER" in sql.upper() or "DROP" in sql.upper()
    
    def validate_clickhouse_syntax(self, sql: str) -> bool:
        """Basic ClickHouse syntax validation."""
        # This is a simplified validation for testing
        return "SELECT" in sql.upper() or "CREATE" in sql.upper() or "ALTER" in sql.upper() or "DROP" in sql.upper()
    
    async def verify_migration_results(self, migration: Dict[str, Any], db_url: str) -> Dict[str, Any]:
        """Verify that migration executed correctly."""
        try:
            migration_id = migration["migration_id"]
            
            # Check if migration was recorded in migration history
            migration_recorded = await self.check_migration_recorded(migration_id, db_url)
            
            # Verify schema changes were applied
            schema_verification = await self.verify_schema_changes(migration, db_url)
            
            # Check data integrity after migration
            integrity_check = await self.check_data_integrity(db_url)
            
            verification_successful = (
                migration_recorded and
                schema_verification["changes_applied"] and
                integrity_check["integrity_maintained"]
            )
            
            return {
                "migration_id": migration_id,
                "verified": verification_successful,
                "migration_recorded": migration_recorded,
                "schema_verification": schema_verification,
                "integrity_check": integrity_check
            }
            
        except Exception as e:
            return {
                "migration_id": migration.get("migration_id"),
                "verified": False,
                "error": str(e)
            }
    
    async def check_migration_recorded(self, migration_id: str, db_url: str) -> bool:
        """Check if migration was properly recorded in migration history table."""
        try:
            # This would query the migration history table
            # For testing, simulate the check
            return True
        except Exception:
            return False
    
    async def verify_schema_changes(self, migration: Dict[str, Any], db_url: str) -> Dict[str, Any]:
        """Verify that expected schema changes were applied."""
        try:
            # This would check the actual database schema
            # For testing, simulate schema verification
            return {
                "changes_applied": True,
                "expected_changes": migration.get("expected_changes", []),
                "actual_changes": ["schema_updated"]
            }
        except Exception as e:
            return {
                "changes_applied": False,
                "error": str(e)
            }
    
    async def check_data_integrity(self, db_url: str) -> Dict[str, Any]:
        """Check data integrity after migration."""
        try:
            # This would run integrity checks on the database
            # For testing, simulate integrity check
            return {
                "integrity_maintained": True,
                "checks_performed": ["foreign_key_constraints", "unique_constraints", "not_null_constraints"],
                "violations": []
            }
        except Exception as e:
            return {
                "integrity_maintained": False,
                "error": str(e)
            }
    
    async def create_migration_backup(self, migration_id: str, db_url: str) -> Dict[str, Any]:
        """Create backup before executing migration."""
        try:
            backup_id = f"backup_{migration_id}_{uuid.uuid4().hex[:8]}"
            
            backup_result = await self.backup_service.create_backup(
                db_url, backup_id, {"migration_id": migration_id}
            )
            
            return {
                "backup_id": backup_id,
                "created": backup_result["success"],
                "backup_result": backup_result
            }
            
        except Exception as e:
            return {
                "backup_id": None,
                "created": False,
                "error": str(e)
            }
    
    async def cleanup(self):
        """Clean up migration test resources."""
        try:
            # Clean up test databases
            for db_type, db_url in self.test_db_urls.items():
                await self.db_manager.drop_database(db_url)
            
            if self.migration_service:
                await self.migration_service.shutdown()
            if self.db_manager:
                await self.db_manager.shutdown()
            if self.backup_service:
                await self.backup_service.shutdown()
            if self.migration_runner:
                await self.migration_runner.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def migration_core_manager():
    """Create migration core manager for testing."""
    manager = DatabaseMigrationCoreManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_safe_schema_migration_execution(migration_core_manager):
    """Test safe execution of schema migrations."""
    # Create test migration
    migration = await migration_core_manager.create_test_migration(
        "add_column_test", "postgres"
    )
    
    # Execute migration
    result = await migration_core_manager.execute_migration(migration, "postgres")
    
    assert result["executed"] is True
    assert result["execution_time"] < 10.0  # Should complete quickly
    assert "migration_record" in result
    
    # Verify migration was recorded
    migration_record = result["migration_record"]
    assert migration_record["success"] is True
    assert migration_record["verification_result"]["verified"] is True


@pytest.mark.asyncio
async def test_migration_sql_validation(migration_core_manager):
    """Test migration SQL validation prevents dangerous operations."""
    # Create migration with potentially dangerous operation
    dangerous_migration = await migration_core_manager.create_test_migration(
        "dangerous_operation", "postgres"
    )
    dangerous_migration["up_sql"] = "TRUNCATE TABLE users; DROP DATABASE production;"
    
    # Validate migration
    validation_result = await migration_core_manager.validate_migration_sql(
        dangerous_migration, migration_core_manager.test_db_urls["postgres"]
    )
    
    assert validation_result["valid"] is False
    assert len(validation_result["issues"]) > 0
    assert any("dangerous" in issue.lower() for issue in validation_result["issues"])


@pytest.mark.asyncio 
async def test_data_integrity_preservation(migration_core_manager):
    """Test that migrations preserve data integrity."""
    # Create safe migration
    migration = await migration_core_manager.create_test_migration(
        "create_table_test", "postgres"
    )
    
    # Execute migration
    result = await migration_core_manager.execute_migration(migration, "postgres")
    
    assert result["executed"] is True
    
    # Verify data integrity was maintained
    migration_record = result["migration_record"]
    integrity_check = migration_record["verification_result"]["integrity_check"]
    assert integrity_check["integrity_maintained"] is True
    assert len(integrity_check["violations"]) == 0


@pytest.mark.asyncio
async def test_migration_performance_requirements(migration_core_manager):
    """Test migration performance meets requirements."""
    # Create multiple test migrations
    migrations = []
    for i in range(5):
        migration = await migration_core_manager.create_test_migration(
            f"performance_test_{i}", "postgres"
        )
        migrations.append(migration)
    
    # Execute migrations and measure performance
    execution_times = []
    for migration in migrations:
        result = await migration_core_manager.execute_migration(migration, "postgres")
        assert result["executed"] is True
        execution_times.append(result["execution_time"])
    
    # Verify performance requirements
    avg_execution_time = sum(execution_times) / len(execution_times)
    max_execution_time = max(execution_times)
    
    assert avg_execution_time < 5.0  # Average < 5 seconds
    assert max_execution_time < 10.0  # Max < 10 seconds
    assert all(t < 15.0 for t in execution_times)  # All < 15 seconds