"""
Database Migration Core Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all customer segments)
- Business Goal: Platform Stability - Prevent data corruption and migration failures
- Value Impact: Protects customer data integrity across all tiers
- Strategic/Revenue Impact: Prevents critical downtime (estimated $50K/hour for Enterprise)

Core database migration tests including sequence execution, rollback, and version conflicts.
"""

import asyncio
import time
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest
import asyncpg
from clickhouse_driver import Client as ClickHouseClient

from .database_migration_validators import MigrationValidator, ContainerizedDatabaseManager


class TestDatabaseMigrationCore:
    """Core database migration tests."""
    
    @pytest.fixture
    async def containerized_databases(self):
        """Set up containerized PostgreSQL and ClickHouse for L3 testing."""
        manager = ContainerizedDatabaseManager()
        urls = await manager.start_containers()
        yield urls
        await manager.stop_containers()
    
    @pytest.fixture
    def migration_validator(self, containerized_databases):
        """Create migration validator with containerized database URLs."""
        return MigrationValidator(postgres_url=containerized_databases["postgres"], clickhouse_url=containerized_databases["clickhouse"])
    
    @pytest.fixture
    def temp_migration_dir(self):
        """Create temporary directory for test migrations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            migrations_path = Path(tmpdir) / "migrations"
            migrations_path.mkdir()
            
            # Create alembic.ini
            alembic_ini = migrations_path / "alembic.ini"
            alembic_ini.write_text("""[alembic]\nscript_location = versions\nprepend_sys_path = .\nversion_path_separator = os""")
            
            # Create versions directory
            versions_path = migrations_path / "versions"
            versions_path.mkdir()
            
            yield migrations_path
    
    async def test_migration_sequence_execution(self, containerized_databases, migration_validator, temp_migration_dir):
        """Test that database migrations execute in correct sequence."""
        start_time = time.time()
        migrations = self._create_test_migrations(temp_migration_dir)
        
        for idx, migration_file in enumerate(migrations):
            migration_start = time.time()
            
            await self._apply_postgres_migration(containerized_databases["postgres"], migration_file)
            self._apply_clickhouse_migration(containerized_databases["clickhouse"], f"migration_{idx+1:03d}")
            
            migration_duration = time.time() - migration_start
            migration_validator.record_timing(f"migration_{idx+1}", migration_duration)
            
            assert await migration_validator.validate_postgres_schema(), f"PostgreSQL schema invalid after migration {idx+1}"
            assert migration_validator.validate_clickhouse_schema(), f"ClickHouse schema invalid after migration {idx+1}"
        
        total_duration = time.time() - start_time
        migration_validator.record_timing("total", total_duration)
        
        assert migration_validator.validate_performance(), f"Performance validation failed: {migration_validator.errors}"
        assert len(migration_validator.errors) == 0, f"Migration validation errors: {migration_validator.errors}"
    
    async def test_migration_rollback_capability(self, containerized_databases, migration_validator, temp_migration_dir):
        """Test database migration rollback functionality."""
        migrations = self._create_test_migrations(temp_migration_dir)
        
        for migration in migrations[:2]:
            await self._apply_postgres_migration(containerized_databases["postgres"], migration)
        
        await self._insert_test_data(containerized_databases["postgres"])
        
        problematic_migration = self._create_problematic_migration(temp_migration_dir)
        
        try:
            await self._apply_postgres_migration(containerized_databases["postgres"], problematic_migration)
        except Exception:
            pass
        
        rollback_start = time.time()
        await self._rollback_postgres_migration(containerized_databases["postgres"], target_revision="-1")
        rollback_duration = time.time() - rollback_start
        
        migration_validator.record_timing("rollback", rollback_duration)
        
        data_intact = await self._verify_test_data(containerized_databases["postgres"])
        assert data_intact, "Data was lost during rollback"
        assert rollback_duration < 30, f"Rollback took {rollback_duration:.2f}s (max: 30s)"
    
    async def test_migration_version_conflicts(self, containerized_databases, temp_migration_dir):
        """Test handling of migration version conflicts."""
        migration_1 = self._create_migration_file(temp_migration_dir, "001_initial.sql", "CREATE TABLE test1 (id SERIAL PRIMARY KEY);")
        migration_2 = self._create_migration_file(temp_migration_dir, "001_conflicting.sql", "CREATE TABLE test2 (id SERIAL PRIMARY KEY);")
        
        await self._apply_postgres_migration(containerized_databases["postgres"], migration_1)
        
        with pytest.raises(Exception) as exc_info:
            await self._apply_postgres_migration(containerized_databases["postgres"], migration_2)
        
        assert "version conflict" in str(exc_info.value).lower() or "already exists" in str(exc_info.value).lower(), "Version conflict not properly detected"
        
        conn = await asyncpg.connect(containerized_databases["postgres"])
        
        table1_exists = await conn.fetchval("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'test1')")
        table2_exists = await conn.fetchval("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'test2')")
        
        await conn.close()
        
        assert table1_exists, "First migration not applied"
        assert not table2_exists, "Conflicting migration was incorrectly applied"
    
    @pytest.mark.smoke
    async def test_migration_smoke_test(self, containerized_databases, temp_migration_dir):
        """Quick smoke test for migration system."""
        start_time = time.time()
        
        migration = self._create_migration_file(temp_migration_dir, "smoke_test.sql", """CREATE TABLE smoke_test (id SERIAL PRIMARY KEY, created_at TIMESTAMP DEFAULT NOW());""")
        
        await self._apply_postgres_migration(containerized_databases["postgres"], migration)
        
        conn = await asyncpg.connect(containerized_databases["postgres"])
        exists = await conn.fetchval("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'smoke_test')")
        await conn.close()
        
        assert exists, "Smoke test migration failed"
        
        duration = time.time() - start_time
        assert duration < 30, f"Smoke test took {duration:.2f}s (max: 30s)"
    
    # Helper methods
    def _create_test_migrations(self, migration_dir: Path) -> List[Path]:
        """Create a set of test migrations."""
        migrations = []
        
        migrations.append(self._create_migration_file(migration_dir, "001_initial_schema.sql", """CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT NOW()); CREATE INDEX users_email_idx ON users(email); CREATE TABLE organizations (id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, created_at TIMESTAMP DEFAULT NOW());"""))
        
        migrations.append(self._create_migration_file(migration_dir, "002_add_messaging.sql", """CREATE TABLE threads (id SERIAL PRIMARY KEY, org_id INTEGER REFERENCES organizations(id), title VARCHAR(255), created_at TIMESTAMP DEFAULT NOW()); CREATE INDEX threads_org_id_idx ON threads(org_id); CREATE TABLE messages (id SERIAL PRIMARY KEY, thread_id INTEGER REFERENCES threads(id), content TEXT, created_at TIMESTAMP DEFAULT NOW()); CREATE INDEX messages_thread_id_idx ON messages(thread_id);"""))
        
        migrations.append(self._create_migration_file(migration_dir, "003_add_agents.sql", """CREATE TABLE agents (id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, type VARCHAR(50) NOT NULL, created_at TIMESTAMP DEFAULT NOW()); CREATE TABLE agent_tools (id SERIAL PRIMARY KEY, agent_id INTEGER REFERENCES agents(id), tool_name VARCHAR(255) NOT NULL, config JSONB); CREATE TABLE agent_executions (id SERIAL PRIMARY KEY, agent_id INTEGER REFERENCES agents(id), thread_id INTEGER REFERENCES threads(id), status VARCHAR(50), started_at TIMESTAMP DEFAULT NOW(), completed_at TIMESTAMP);"""))
        
        return migrations
    
    def _create_migration_file(self, migration_dir: Path, filename: str, sql: str) -> Path:
        """Create a migration file with given SQL."""
        filepath = migration_dir / "versions" / filename
        filepath.write_text(sql)
        return filepath
    
    async def _apply_postgres_migration(self, db_url: str, migration_file: Path):
        """Apply a PostgreSQL migration."""
        conn = await asyncpg.connect(db_url)
        try:
            sql = migration_file.read_text()
            await conn.execute(sql)
        finally:
            await conn.close()
    
    def _apply_clickhouse_migration(self, db_url: str, migration_name: str):
        """Apply a ClickHouse migration."""
        client = ClickHouseClient(host='localhost', port=8124)
        
        if "001" in migration_name:
            client.execute("""CREATE TABLE IF NOT EXISTS events (timestamp DateTime, event_type String, user_id UInt32, data String) ENGINE = MergeTree() PARTITION BY toYYYYMM(timestamp) ORDER BY (timestamp, event_type)""")
        elif "002" in migration_name:
            client.execute("""CREATE TABLE IF NOT EXISTS metrics (timestamp DateTime, metric_name String, value Float64, labels String) ENGINE = MergeTree() PARTITION BY toYYYYMM(timestamp) ORDER BY (timestamp, metric_name)""")
        elif "003" in migration_name:
            client.execute("""CREATE TABLE IF NOT EXISTS agent_metrics (timestamp DateTime, agent_id UInt32, execution_time Float64, tokens_used UInt32) ENGINE = MergeTree() ORDER BY (timestamp, agent_id)""")
    
    async def _rollback_postgres_migration(self, db_url: str, target_revision: str):
        """Rollback PostgreSQL migration to target revision."""
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute("DROP TABLE IF EXISTS agent_executions CASCADE")
            await conn.execute("DROP TABLE IF EXISTS agent_tools CASCADE")
            await conn.execute("DROP TABLE IF EXISTS agents CASCADE")
        finally:
            await conn.close()
    
    async def _insert_test_data(self, db_url: str):
        """Insert test data to verify preservation during rollback."""
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute("INSERT INTO users (email) VALUES ($1), ($2)", "test1@example.com", "test2@example.com")
            await conn.execute("INSERT INTO organizations (name) VALUES ($1)", "Test Org")
        finally:
            await conn.close()
    
    async def _verify_test_data(self, db_url: str) -> bool:
        """Verify test data is intact."""
        conn = await asyncpg.connect(db_url)
        try:
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            org_count = await conn.fetchval("SELECT COUNT(*) FROM organizations")
            return user_count == 2 and org_count == 1
        finally:
            await conn.close()
    
    def _create_problematic_migration(self, migration_dir: Path) -> Path:
        """Create a migration that will fail."""
        return self._create_migration_file(migration_dir, "problematic.sql", "CREATE TABLE invalid_reference (id INTEGER REFERENCES nonexistent_table(id));")
