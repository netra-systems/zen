"""
L3-9: Database Migration Rollback with Real Databases Integration Test

BVJ: Ensures safe database schema evolution with rollback capabilities,
critical for maintaining data integrity during deployments.

Tests database migration and rollback with real PostgreSQL containers.
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from typing import Any, Dict, List, Optional

import asyncpg
import docker
import pytest
from netra_backend.app.database.migration_manager import MigrationManager
from netra_backend.app.database.postgres_connection import PostgresConnection


@pytest.mark.L3
class TestDatabaseMigrationRollbackL3:
    """Test database migration rollback with real databases."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
    @pytest.fixture(scope="class")
    async def postgres_container(self, docker_client):
        """Start PostgreSQL container for testing."""
        container = docker_client.containers.run(
            "postgres:15",
            environment={
                "POSTGRES_DB": "migration_test",
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_password"
            },
            ports={'5432/tcp': None},
            detach=True,
            name="migration_test_postgres"
        )
        
        # Get assigned port
        container.reload()
        port = container.attrs['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']
        
        # Wait for PostgreSQL to be ready
        await self._wait_for_postgres(port)
        
        connection_config = {
            "host": "localhost",
            "port": int(port),
            "database": "migration_test",
            "user": "test_user",
            "password": "test_password"
        }
        
        yield connection_config
        
        container.stop()
        container.remove()
    
    async def _wait_for_postgres(self, port: str, timeout: int = 30):
        """Wait for PostgreSQL to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = await asyncpg.connect(
                    host="localhost",
                    port=int(port),
                    database="migration_test",
                    user="test_user",
                    password="test_password"
                )
                await conn.close()
                return
            except:
                await asyncio.sleep(0.5)
        raise TimeoutError(f"PostgreSQL not ready within {timeout}s")
    
    @pytest.fixture
    async def migration_manager(self, postgres_container):
        """Create migration manager with test database."""
        manager = MigrationManager(postgres_container)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def test_migrations(self):
        """Create test migration scripts."""
        migrations = {
            "001_create_users_table": {
                "up": """
                    CREATE TABLE users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX idx_users_username ON users(username);
                """,
                "down": """
                    DROP INDEX IF EXISTS idx_users_username;
                    DROP TABLE IF EXISTS users;
                """
            },
            "002_add_user_profile": {
                "up": """
                    CREATE TABLE user_profiles (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        first_name VARCHAR(50),
                        last_name VARCHAR(50),
                        bio TEXT
                    );
                    ALTER TABLE users ADD COLUMN profile_completed BOOLEAN DEFAULT FALSE;
                """,
                "down": """
                    ALTER TABLE users DROP COLUMN IF EXISTS profile_completed;
                    DROP TABLE IF EXISTS user_profiles;
                """
            },
            "003_add_user_settings": {
                "up": """
                    CREATE TABLE user_settings (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        theme VARCHAR(20) DEFAULT 'light',
                        notifications_enabled BOOLEAN DEFAULT TRUE,
                        language VARCHAR(10) DEFAULT 'en'
                    );
                    CREATE UNIQUE INDEX idx_user_settings_user_id ON user_settings(user_id);
                """,
                "down": """
                    DROP INDEX IF EXISTS idx_user_settings_user_id;
                    DROP TABLE IF EXISTS user_settings;
                """
            }
        }
        return migrations
    
    @pytest.mark.asyncio
    async def test_migration_forward_execution(
        self, 
        migration_manager, 
        test_migrations
    ):
        """Test forward migration execution."""
        # Register test migrations
        for name, migration in test_migrations.items():
            await migration_manager.register_migration(name, migration["up"], migration["down"])
        
        # Execute migrations
        result = await migration_manager.migrate_up()
        
        assert result["success"] is True
        assert result["applied_count"] == 3
        
        # Verify tables exist
        tables = await migration_manager.get_table_list()
        expected_tables = ["users", "user_profiles", "user_settings", "migration_history"]
        
        for table in expected_tables:
            assert table in tables
    
    @pytest.mark.asyncio
    async def test_migration_rollback_execution(
        self, 
        migration_manager, 
        test_migrations
    ):
        """Test migration rollback execution."""
        # Register and apply migrations
        for name, migration in test_migrations.items():
            await migration_manager.register_migration(name, migration["up"], migration["down"])
        
        await migration_manager.migrate_up()
        
        # Rollback last migration
        result = await migration_manager.rollback(steps=1)
        
        assert result["success"] is True
        assert result["rolled_back_count"] == 1
        
        # Verify user_settings table is gone
        tables = await migration_manager.get_table_list()
        assert "user_settings" not in tables
        assert "users" in tables
        assert "user_profiles" in tables
    
    @pytest.mark.asyncio
    async def test_migration_rollback_multiple_steps(
        self, 
        migration_manager, 
        test_migrations
    ):
        """Test rolling back multiple migration steps."""
        # Register and apply migrations
        for name, migration in test_migrations.items():
            await migration_manager.register_migration(name, migration["up"], migration["down"])
        
        await migration_manager.migrate_up()
        
        # Rollback two migrations
        result = await migration_manager.rollback(steps=2)
        
        assert result["success"] is True
        assert result["rolled_back_count"] == 2
        
        # Verify only base table remains
        tables = await migration_manager.get_table_list()
        assert "users" in tables
        assert "user_profiles" not in tables
        assert "user_settings" not in tables
    
    @pytest.mark.asyncio
    async def test_migration_data_preservation_during_rollback(
        self, 
        migration_manager, 
        test_migrations
    ):
        """Test that data is preserved during rollback when possible."""
        # Register and apply migrations
        for name, migration in test_migrations.items():
            await migration_manager.register_migration(name, migration["up"], migration["down"])
        
        await migration_manager.migrate_up()
        
        # Insert test data
        conn = await migration_manager.get_connection()
        
        # Insert user
        user_id = await conn.fetchval(
            "INSERT INTO users (username, email) VALUES ($1, $2) RETURNING id",
            "testuser", "test@example.com"
        )
        
        # Insert profile
        await conn.execute(
            "INSERT INTO user_profiles (user_id, first_name, last_name) VALUES ($1, $2, $3)",
            user_id, "John", "Doe"
        )
        
        await conn.close()
        
        # Rollback profile migration
        await migration_manager.rollback(steps=2)
        
        # Verify user data is preserved
        conn = await migration_manager.get_connection()
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        await conn.close()
        
        assert user is not None
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_migration_failure_rollback(
        self, 
        migration_manager, 
        test_migrations
    ):
        """Test rollback behavior when migration fails."""
        # Register good migrations
        for name, migration in test_migrations.items():
            await migration_manager.register_migration(name, migration["up"], migration["down"])
        
        # Add a bad migration
        bad_migration = {
            "up": "CREATE TABLE invalid_table (id INTEGER PRIMARY KEY, invalid_column INVALID_TYPE);",
            "down": "DROP TABLE IF EXISTS invalid_table;"
        }
        
        await migration_manager.register_migration("004_bad_migration", bad_migration["up"], bad_migration["down"])
        
        # Apply good migrations first
        await migration_manager.migrate_up_to("002_add_user_profile")
        
        # Attempt to apply bad migration
        result = await migration_manager.migrate_up()
        
        assert result["success"] is False
        assert "error" in result
        
        # Verify system is in consistent state
        tables = await migration_manager.get_table_list()
        assert "users" in tables
        assert "user_profiles" in tables
        assert "invalid_table" not in tables
    
    @pytest.mark.asyncio
    async def test_migration_history_tracking(
        self, 
        migration_manager, 
        test_migrations
    ):
        """Test that migration history is properly tracked."""
        # Register and apply migrations
        for name, migration in test_migrations.items():
            await migration_manager.register_migration(name, migration["up"], migration["down"])
        
        await migration_manager.migrate_up()
        
        # Check migration history
        history = await migration_manager.get_migration_history()
        
        assert len(history) == 3
        assert all(record["applied"] is True for record in history)
        assert history[0]["name"] == "001_create_users_table"
        assert history[2]["name"] == "003_add_user_settings"
        
        # Rollback one migration
        await migration_manager.rollback(steps=1)
        
        # Check updated history
        updated_history = await migration_manager.get_migration_history()
        
        assert len(updated_history) == 3
        assert updated_history[2]["applied"] is False  # Last migration rolled back
        assert updated_history[0]["applied"] is True   # First migration still applied
        assert updated_history[1]["applied"] is True   # Second migration still applied
    
    @pytest.mark.asyncio
    async def test_concurrent_migration_safety(
        self, 
        migration_manager, 
        test_migrations
    ):
        """Test that concurrent migrations are handled safely."""
        # Register migrations
        for name, migration in test_migrations.items():
            await migration_manager.register_migration(name, migration["up"], migration["down"])
        
        # Create second migration manager (simulating concurrent process)
        second_manager = MigrationManager(migration_manager.connection_config)
        await second_manager.initialize()
        
        try:
            # Attempt concurrent migrations
            task1 = asyncio.create_task(migration_manager.migrate_up())
            task2 = asyncio.create_task(second_manager.migrate_up())
            
            result1, result2 = await asyncio.gather(task1, task2, return_exceptions=True)
            
            # One should succeed, one should fail or be skipped
            successful_results = [r for r in [result1, result2] if isinstance(r, dict) and r.get("success")]
            assert len(successful_results) >= 1
            
            # Verify final state is consistent
            tables = await migration_manager.get_table_list()
            expected_tables = ["users", "user_profiles", "user_settings"]
            for table in expected_tables:
                assert table in tables
                
        finally:
            await second_manager.cleanup()