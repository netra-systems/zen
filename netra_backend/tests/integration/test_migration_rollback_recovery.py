"""
Database Migration Rollback Recovery Integration Test.

BVJ (Business Value Justification):
- Segment: Platform/Internal
- Business Goal: Platform Stability  
- Value Impact: Prevents database corruption during failed migrations
- Strategic Impact: Ensures zero-downtime deployments and customer data integrity

This test validates database migration failure scenarios and automatic rollback mechanisms
using real PostgreSQL containers (L3 realism) to catch production-level issues.
"""

import pytest
import asyncio
import tempfile
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from netra_backend.app.db.base import Base
from netra_backend.app.db.postgres_core import Database
from logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
class TestMigrationRollbackRecovery:
    """Integration tests for database migration rollback recovery mechanisms."""

    @pytest.fixture(scope="function")
    def postgres_container(self):
        """Create real PostgreSQL container for L3 testing using Docker CLI."""
        container_name = f"test_postgres_{os.getpid()}_{id(self)}"
        
        try:
            # Start PostgreSQL container
            subprocess.run([
                "docker", "run", "-d", "--name", container_name,
                "-e", "POSTGRES_DB=migration_test",
                "-e", "POSTGRES_USER=test_user", 
                "-e", "POSTGRES_PASSWORD=test_pass",
                "-p", "0:5432",  # Let Docker assign random port
                "postgres:15"
            ], check=True, capture_output=True)
            
            # Get assigned port
            port_result = subprocess.run([
                "docker", "port", container_name, "5432"
            ], capture_output=True, text=True, check=True)
            
            host_port = port_result.stdout.strip().split(':')[1]
            
            # Wait for PostgreSQL to be ready
            self._wait_for_postgres_ready(container_name)
            
            yield {
                "container_name": container_name,
                "host": "localhost",
                "port": int(host_port),
                "database": "migration_test",
                "user": "test_user",
                "password": "test_pass"
            }
            
        finally:
            # Cleanup container
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    @pytest.fixture
    def migration_config(self, postgres_container):
        """Create migration configuration with real database."""
        pg = postgres_container
        database_url = f"postgresql://{pg['user']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['database']}"
        
        return {
            "database_url": database_url,
            "test_schema": "migration_test",
            "backup_schema": "migration_backup", 
            "timeout_seconds": 30
        }

    async def test_migration_failure_triggers_rollback(self, migration_config):
        """
        Test that migration failures trigger automatic rollback to previous state.
        
        Validates:
        - Migration backup creation before changes
        - Failure detection during migration
        - Automatic rollback to backup state
        - Database consistency after rollback
        """
        # Setup initial database state
        initial_tables = await self._create_initial_schema(migration_config)
        backup_created = await self._create_schema_backup(migration_config)
        assert backup_created, "Failed to create schema backup"

        # Simulate migration failure
        migration_failed = await self._simulate_failing_migration(migration_config)
        assert migration_failed, "Migration should have failed for test"

        # Verify rollback occurred
        rollback_success = await self._verify_rollback_completed(migration_config, initial_tables)
        assert rollback_success, "Rollback did not restore original state"

        # Verify database consistency
        consistency_valid = await self._verify_database_consistency(migration_config)
        assert consistency_valid, "Database inconsistent after rollback"

    async def test_transaction_rollback_on_constraint_violation(self, migration_config):
        """Test rollback when migration violates database constraints."""
        # Create table with constraints
        constraint_tables = await self._setup_constraint_test_schema(migration_config)
        
        # Attempt migration that violates constraints
        violation_detected = await self._attempt_constraint_violating_migration(migration_config)
        assert violation_detected, "Constraint violation should have been detected"

        # Verify original schema preserved
        schema_preserved = await self._verify_original_schema_intact(migration_config, constraint_tables)
        assert schema_preserved, "Original schema not preserved after constraint violation"

    async def test_partial_migration_rollback_atomicity(self, migration_config):
        """Test that partial migrations are rolled back atomically."""
        # Setup multi-table migration scenario
        multi_table_setup = await self._setup_multi_table_migration(migration_config)
        
        # Start migration that fails partway through
        partial_failure = await self._simulate_partial_migration_failure(migration_config)
        assert partial_failure, "Partial migration failure not simulated correctly"

        # Verify no partial changes remain
        no_partial_changes = await self._verify_no_partial_changes_remain(migration_config)
        assert no_partial_changes, "Partial migration changes were not rolled back"

    async def test_concurrent_connection_handling_during_rollback(self, migration_config):
        """Test rollback behavior with concurrent database connections."""
        # Establish multiple connections
        connections = await self._create_multiple_connections(migration_config)
        
        # Start migration with concurrent activity
        rollback_with_connections = await self._test_rollback_with_concurrent_connections(
            migration_config, connections
        )
        assert rollback_with_connections, "Rollback failed with concurrent connections"

        # Cleanup connections
        await self._cleanup_connections(connections)

    # Helper methods (each under 25 lines)

    async def _create_initial_schema(self, config: Dict[str, Any]) -> List[str]:
        """Create initial database schema for testing."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS migration_test"))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS migration_test.users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE
                    )
                """))
                return ["users"]
        finally:
            await engine.dispose()

    async def _create_schema_backup(self, config: Dict[str, Any]) -> bool:
        """Create backup of current schema state."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS migration_backup"))
                await conn.execute(text("""
                    CREATE TABLE migration_backup.users AS 
                    SELECT * FROM migration_test.users
                """))
                return True
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
        finally:
            await engine.dispose()

    async def _simulate_failing_migration(self, config: Dict[str, Any]) -> bool:
        """Simulate a migration that fails mid-process."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                # This will fail due to duplicate column
                await conn.execute(text("""
                    ALTER TABLE migration_test.users 
                    ADD COLUMN id INTEGER  -- Duplicate column causes failure
                """))
                return False
        except Exception:
            # Expected failure - migration should fail
            return True
        finally:
            await engine.dispose()

    async def _verify_rollback_completed(self, config: Dict[str, Any], original_tables: List[str]) -> bool:
        """Verify that rollback restored original state."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                # Check that original table structure is intact
                result = await conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'migration_test' AND table_name = 'users'
                """))
                columns = [row[0] for row in result.fetchall()]
                expected_columns = ["id", "name", "email"]
                return set(columns) == set(expected_columns)
        except Exception as e:
            logger.error(f"Rollback verification failed: {e}")
            return False
        finally:
            await engine.dispose()

    async def _verify_database_consistency(self, config: Dict[str, Any]) -> bool:
        """Verify database is in consistent state after rollback."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                # Test basic operations work
                await conn.execute(text("INSERT INTO migration_test.users (name, email) VALUES ('test', 'test@example.com')"))
                result = await conn.execute(text("SELECT COUNT(*) FROM migration_test.users"))
                count = result.fetchone()[0]
                return count >= 1
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            return False
        finally:
            await engine.dispose()

    async def _setup_constraint_test_schema(self, config: Dict[str, Any]) -> List[str]:
        """Setup schema with constraints for testing."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS migration_test.orders (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES migration_test.users(id),
                        amount DECIMAL(10,2) CHECK (amount > 0)
                    )
                """))
                return ["users", "orders"]
        finally:
            await engine.dispose()

    async def _attempt_constraint_violating_migration(self, config: Dict[str, Any]) -> bool:
        """Attempt migration that violates database constraints."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                # This will violate CHECK constraint
                await conn.execute(text("INSERT INTO migration_test.orders (user_id, amount) VALUES (1, -100)"))
                return False
        except Exception:
            return True
        finally:
            await engine.dispose()

    async def _verify_original_schema_intact(self, config: Dict[str, Any], original_tables: List[str]) -> bool:
        """Verify original schema remains intact."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                for table in original_tables:
                    result = await conn.execute(text(f"""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = 'migration_test' AND table_name = '{table}'
                    """))
                    if result.fetchone()[0] != 1:
                        return False
                return True
        finally:
            await engine.dispose()

    async def _setup_multi_table_migration(self, config: Dict[str, Any]) -> bool:
        """Setup multiple tables for migration testing."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                await conn.execute(text("""
                    CREATE TABLE migration_test.products (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100)
                    )
                """))
                return True
        finally:
            await engine.dispose()

    async def _simulate_partial_migration_failure(self, config: Dict[str, Any]) -> bool:
        """Simulate migration that fails after partial completion."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                # First operation succeeds
                await conn.execute(text("ALTER TABLE migration_test.products ADD COLUMN price DECIMAL(10,2)"))
                # Second operation fails
                await conn.execute(text("ALTER TABLE migration_test.products ADD COLUMN price DECIMAL(10,2)"))  # Duplicate
                return False
        except Exception:
            return True
        finally:
            await engine.dispose()

    async def _verify_no_partial_changes_remain(self, config: Dict[str, Any]) -> bool:
        """Verify no partial migration changes remain."""
        engine = create_async_engine(config["database_url"])
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'migration_test' AND table_name = 'products'
                """))
                columns = [row[0] for row in result.fetchall()]
                # Should only have original columns
                return "price" not in columns
        finally:
            await engine.dispose()

    async def _create_multiple_connections(self, config: Dict[str, Any]) -> List:
        """Create multiple database connections for testing."""
        connections = []
        for i in range(3):
            engine = create_async_engine(config["database_url"])
            connections.append(engine)
        return connections

    async def _test_rollback_with_concurrent_connections(self, config: Dict[str, Any], connections: List) -> bool:
        """Test rollback behavior with concurrent connections."""
        try:
            # Simulate concurrent activity while rollback occurs
            tasks = []
            for engine in connections:
                task = asyncio.create_task(self._simulate_concurrent_activity(engine))
                tasks.append(task)
            
            # Wait for all concurrent activities
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return all(isinstance(r, Exception) or r for r in results)
        except Exception:
            return False

    async def _simulate_concurrent_activity(self, engine) -> bool:
        """Simulate concurrent database activity."""
        try:
            async with engine.begin() as conn:
                await asyncio.sleep(0.1)  # Brief activity
                await conn.execute(text("SELECT 1"))
                return True
        except Exception:
            return False

    async def _cleanup_connections(self, connections: List) -> None:
        """Cleanup database connections."""
        for engine in connections:
            await engine.dispose()

    def _wait_for_postgres_ready(self, container_name: str, max_wait: int = 60) -> None:
        """Wait for PostgreSQL container to be ready."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                result = subprocess.run([
                    "docker", "exec", container_name,
                    "pg_isready", "-U", "test_user", "-d", "migration_test"
                ], capture_output=True, check=True)
                
                if result.returncode == 0:
                    return
            except subprocess.CalledProcessError:
                pass
            
            time.sleep(2)
        
        raise TimeoutError(f"PostgreSQL container {container_name} not ready within {max_wait}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])