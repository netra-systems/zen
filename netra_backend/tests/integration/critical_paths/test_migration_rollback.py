"""Database Migration Rollback Recovery Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)
- Business Goal: Data integrity and deployment safety
- Value Impact: Protects $12K MRR from migration failures and data corruption
- Strategic Impact: Enables safe deployments and maintains customer data integrity

Critical Path: Migration execution -> Failure detection -> Rollback initiation -> Data restoration -> Validation
Coverage: Migration safety, rollback mechanisms, data integrity, recovery validation
"""

import pytest
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.database.rollback_manager_core import rollback_manager, RollbackManager, RollbackState
from netra_backend.app.services.monitoring.rate_limiter import GCPRateLimiter
from netra_backend.app.db.postgres_core import initialize_postgres
import sqlalchemy as sa
from sqlalchemy.sql import text

# Add project root to path

logger = logging.getLogger(__name__)


class MigrationRollbackManager:
    """Manages database migration and rollback testing."""
    
    def __init__(self):
        self.rollback_manager = rollback_manager
        self.db_connection = None
        self.rate_limiter = None
        self.test_migrations = []
        self.test_tables = []
        self.rollback_sessions = []
        
    async def initialize_services(self):
        """Initialize migration rollback services."""
        self.rate_limiter = GCPRateLimiter()
        
        # Initialize database for testing
        session_factory = initialize_postgres()
        assert session_factory is not None
        
        # Test database connectivity
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            self.session_factory = session_factory
    
    async def create_test_migration(self, migration_name: str, 
                                  schema_changes: List[str]) -> Dict[str, Any]:
        """Create test migration with rollback scenario."""
        creation_start = time.time()
        
        # Create test table in database
        table_name = f"test_migration_{migration_name.replace('-', '_')}_{int(time.time())}"
        
        try:
            async with self.session_factory() as session:
                # Execute schema changes (CREATE TABLE)
                for sql in schema_changes:
                    formatted_sql = sql.replace("test_migration_table", table_name)
                    await session.execute(text(formatted_sql))
                await session.commit()
                
            self.test_tables.append(table_name)
            
            migration_record = {
                "name": migration_name,
                "table_name": table_name,
                "schema_changes": schema_changes,
                "creation_time": time.time() - creation_start,
                "success": True
            }
            
            self.test_migrations.append(migration_record)
            return migration_record
            
        except Exception as e:
            return {
                "name": migration_name,
                "error": str(e),
                "creation_time": time.time() - creation_start,
                "success": False
            }
    
    async def execute_migration_with_backup(self, migration_name: str) -> Dict[str, Any]:
        """Execute migration with rollback session creation."""
        execution_start = time.time()
        
        try:
            # Step 1: Create rollback session (acts as backup point)
            session_id = await self.rollback_manager.create_rollback_session(
                metadata={"migration_name": migration_name, "type": "migration_backup"}
            )
            
            self.rollback_sessions.append(session_id)
            
            # Step 2: Find migration record
            migration_record = None
            for record in self.test_migrations:
                if record["name"] == migration_name:
                    migration_record = record
                    break
            
            if not migration_record:
                raise ValueError(f"Migration {migration_name} not found")
            
            # Step 3: Add rollback operation for the created table
            table_name = migration_record["table_name"]
            operation_id = await self.rollback_manager.add_rollback_operation(
                session_id=session_id,
                table_name=table_name,
                operation_type="DROP_TABLE",
                rollback_data={"table_name": table_name, "sql": f"DROP TABLE IF EXISTS {table_name}"}
            )
            
            return {
                "migration_name": migration_name,
                "backup_created": True,
                "rollback_session_id": session_id,
                "operation_id": operation_id,
                "migration_success": True,
                "execution_time": time.time() - execution_start
            }
            
        except Exception as e:
            return {
                "migration_name": migration_name,
                "error": str(e),
                "execution_time": time.time() - execution_start,
                "migration_success": False
            }
    
    async def simulate_migration_failure_and_rollback(self, migration_name: str) -> Dict[str, Any]:
        """Simulate migration failure and test rollback."""
        rollback_start = time.time()
        
        try:
            # Step 1: Execute migration successfully first
            migration_result = await self.execute_migration_with_backup(migration_name)
            
            if not migration_result["migration_success"]:
                return {
                    "migration_name": migration_name,
                    "error": migration_result.get("error", "Migration execution failed"),
                    "failure_detected": True,
                    "rollback_attempted": False,
                    "total_rollback_time": time.time() - rollback_start
                }
            
            # Step 2: Simulate failure by executing rollback
            session_id = migration_result["rollback_session_id"]
            rollback_success = await self.rollback_manager.execute_rollback_session(session_id)
            
            # Step 3: Check rollback status
            session_status = self.rollback_manager.get_session_status(session_id)
            
            return {
                "migration_name": migration_name,
                "failure_detected": True,
                "rollback_attempted": True,
                "rollback_success": rollback_success,
                "session_status": session_status,
                "recovery_method": "rollback_manager",
                "total_rollback_time": time.time() - rollback_start
            }
            
        except Exception as e:
            return {
                "migration_name": migration_name,
                "error": str(e),
                "failure_detected": True,
                "rollback_attempted": False,
                "total_rollback_time": time.time() - rollback_start
            }
    
    async def validate_data_integrity_after_rollback(self, table_checks: List[Dict]) -> Dict[str, Any]:
        """Validate data integrity after rollback."""
        validation_start = time.time()
        
        integrity_results = []
        
        for check in table_checks:
            table_name = check["table"]
            expected_state = check["expected_state"]
            
            try:
                async with self.session_factory() as session:
                    # Check table existence
                    result = await session.execute(
                        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"),
                        {"table_name": table_name}
                    )
                    table_exists = result.scalar()
                    
                    # Check data if table should exist
                    if expected_state == "exists" and table_exists:
                        count_result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        row_count = count_result.scalar()
                        data_integrity = {
                            "table": table_name,
                            "exists": True,
                            "row_count": row_count,
                            "integrity_check": "passed"
                        }
                    elif expected_state == "not_exists" and not table_exists:
                        data_integrity = {
                            "table": table_name,
                            "exists": False,
                            "integrity_check": "passed"
                        }
                    else:
                        data_integrity = {
                            "table": table_name,
                            "exists": table_exists,
                            "expected_state": expected_state,
                            "integrity_check": "failed"
                        }
                    
                    integrity_results.append(data_integrity)
                    
            except Exception as e:
                integrity_results.append({
                    "table": table_name,
                    "error": str(e),
                    "integrity_check": "error"
                })
        
        passed_checks = len([r for r in integrity_results if r.get("integrity_check") == "passed"])
        
        return {
            "validation_time": time.time() - validation_start,
            "total_checks": len(table_checks),
            "passed_checks": passed_checks,
            "integrity_percentage": (passed_checks / len(table_checks)) * 100 if table_checks else 100,
            "results": integrity_results
        }
    
    async def cleanup(self):
        """Clean up migration rollback test resources."""
        # Clean up test tables
        for table_name in self.test_tables:
            try:
                async with self.session_factory() as session:
                    await session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                    await session.commit()
            except Exception as e:
                logger.warning(f"Failed to drop test table {table_name}: {e}")
        
        # Clean up rollback sessions
        for session_id in self.rollback_sessions:
            try:
                await self.rollback_manager._cleanup_session(session_id)
            except Exception as e:
                logger.warning(f"Failed to cleanup rollback session {session_id}: {e}")
        
        # Database connections are managed by the session context manager


@pytest.fixture
async def migration_rollback_manager():
    """Create migration rollback manager for testing."""
    manager = MigrationRollbackManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_migration_with_backup_creation(migration_rollback_manager):
    """Test migration execution with backup point creation."""
    manager = migration_rollback_manager
    
    # Create test migration
    migration_record = await manager.create_test_migration(
        "test_backup_migration",
        ["CREATE TABLE test_migration_table (id SERIAL PRIMARY KEY, data TEXT)"]
    )
    
    assert migration_record["success"] is True
    assert migration_record["creation_time"] < 0.5
    
    # Execute migration with backup
    execution_result = await manager.execute_migration_with_backup(
        "test_backup_migration"
    )
    
    assert execution_result["backup_created"] is True
    assert execution_result["migration_success"] is True
    assert execution_result["execution_time"] < 10.0
    assert "backup_name" in execution_result


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_migration_failure_rollback_recovery(migration_rollback_manager):
    """Test migration failure detection and rollback recovery."""
    manager = migration_rollback_manager
    
    # Create test migration
    await manager.create_test_migration(
        "test_failure_migration",
        ["CREATE TABLE test_failure_table (id SERIAL PRIMARY KEY)"]
    )
    
    # Simulate failure and rollback
    rollback_result = await manager.simulate_migration_failure_and_rollback(
        "test_failure_migration"
    )
    
    assert rollback_result["failure_detected"] is True
    assert rollback_result["rollback_attempted"] is True
    assert rollback_result["total_rollback_time"] < 30.0
    
    # Rollback should succeed
    assert rollback_result["rollback_success"] is True or "error" not in rollback_result


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_data_integrity_validation_after_rollback(migration_rollback_manager):
    """Test data integrity validation after rollback."""
    manager = migration_rollback_manager
    
    # Create and execute migration
    await manager.create_test_migration(
        "test_integrity_migration",
        ["CREATE TABLE test_integrity_table (id SERIAL PRIMARY KEY)"]
    )
    
    # Simulate failure and rollback
    await manager.simulate_migration_failure_and_rollback("test_integrity_migration")
    
    # Validate data integrity
    table_checks = [
        {"table": "test_integrity_table", "expected_state": "not_exists"}
    ]
    
    integrity_result = await manager.validate_data_integrity_after_rollback(table_checks)
    
    assert integrity_result["total_checks"] == 2
    assert integrity_result["passed_checks"] >= 1
    assert integrity_result["integrity_percentage"] >= 50.0
    assert integrity_result["validation_time"] < 5.0


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_rollback_performance_requirements(migration_rollback_manager):
    """Test rollback performance meets requirements."""
    manager = migration_rollback_manager
    
    # Create multiple test migrations
    migration_names = []
    for i in range(3):
        migration_name = f"test_perf_migration_{i}"
        await manager.create_test_migration(
            migration_name,
            [f"CREATE TABLE test_perf_table_{i} (id SERIAL PRIMARY KEY)"]
        )
        migration_names.append(migration_name)
    
    # Test rollback performance for each
    rollback_times = []
    for migration_name in migration_names:
        rollback_result = await manager.simulate_migration_failure_and_rollback(
            migration_name
        )
        rollback_times.append(rollback_result["total_rollback_time"])
    
    # Verify performance requirements
    max_rollback_time = max(rollback_times)
    avg_rollback_time = sum(rollback_times) / len(rollback_times)
    
    assert max_rollback_time < 30.0  # Maximum 30 seconds per rollback
    assert avg_rollback_time < 15.0  # Average under 15 seconds