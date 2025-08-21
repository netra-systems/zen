"""
Database Migration Performance and Concurrency Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all customer segments)
- Business Goal: Platform Stability - Prevent data corruption and migration failures
- Value Impact: Ensures migration performance meets SLA requirements
- Strategic/Revenue Impact: Prevents extended downtime during deployments

Performance and concurrency testing for database migrations.
"""

import asyncio
import time
import tempfile
from pathlib import Path

import pytest
import asyncpg

from netra_backend.tests.database_migration_validators import MigrationValidator, ContainerizedDatabaseManager


class TestDatabaseMigrationPerformance:
    """Performance and concurrency migration tests."""
    
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
            
            alembic_ini = migrations_path / "alembic.ini"
            alembic_ini.write_text("""[alembic]\nscript_location = versions\nprepend_sys_path = .\nversion_path_separator = os""")
            
            versions_path = migrations_path / "versions"
            versions_path.mkdir()
            
            yield migrations_path
    
    async def test_concurrent_migration_prevention(self, containerized_databases, temp_migration_dir):
        """Test prevention of concurrent migration execution."""
        migration = self._create_test_migrations(temp_migration_dir)[0]
        
        slow_migration = self._create_migration_file(temp_migration_dir, "slow_migration.sql", "SELECT pg_sleep(5); CREATE TABLE concurrent_test (id SERIAL PRIMARY KEY);")
        
        results = {'first': None, 'second': None}
        errors = []
        
        async def run_migration(name: str, migration_file: Path):
            """Run migration and capture result."""
            try:
                await self._apply_postgres_migration(containerized_databases["postgres"], migration_file)
                results[name] = 'success'
            except Exception as e:
                results[name] = 'failed'
                errors.append(str(e))
        
        tasks = [asyncio.create_task(run_migration('first', slow_migration)), asyncio.create_task(run_migration('second', migration))]
        
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=10)
        
        successful_count = sum(1 for r in results.values() if r == 'success')
        assert successful_count == 1, f"Expected exactly one successful migration, got {successful_count}"
        
        if errors:
            assert any('lock' in err.lower() or 'concurrent' in err.lower() for err in errors), "Concurrent migration not properly blocked with lock error"
    
    async def test_migration_performance_validation(self, containerized_databases, migration_validator, temp_migration_dir):
        """Test migration performance under various conditions."""
        migrations = [("simple", self._create_simple_migration(temp_migration_dir)), ("complex", self._create_complex_migration(temp_migration_dir)), ("large_data", self._create_large_data_migration(temp_migration_dir))]
        
        total_start = time.time()
        
        for migration_type, migration_file in migrations:
            migration_start = time.time()
            
            await self._apply_postgres_migration(containerized_databases["postgres"], migration_file)
            
            duration = time.time() - migration_start
            migration_validator.record_timing(f"{migration_type}_migration", duration)
            
            if migration_type == "simple":
                assert duration < 10, f"Simple migration took {duration:.2f}s (max: 10s)"
            elif migration_type == "complex":
                assert duration < 30, f"Complex migration took {duration:.2f}s (max: 30s)"
            elif migration_type == "large_data":
                assert duration < 120, f"Large data migration took {duration:.2f}s (max: 120s)"
        
        total_duration = time.time() - total_start
        migration_validator.record_timing("total", total_duration)
        
        assert total_duration < 300, f"Total migration took {total_duration:.2f}s (max: 300s)"
        assert migration_validator.validate_performance(), f"Performance validation failed: {migration_validator.errors}"
    
    # Helper methods
    def _create_test_migrations(self, migration_dir: Path):
        """Create a set of test migrations."""
        migrations = []
        migrations.append(self._create_migration_file(migration_dir, "001_initial_schema.sql", """CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT NOW());"""))
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
    
    def _create_simple_migration(self, migration_dir: Path) -> Path:
        """Create a simple migration for performance testing."""
        return self._create_migration_file(migration_dir, "simple.sql", "CREATE TABLE simple_test (id SERIAL PRIMARY KEY);")
    
    def _create_complex_migration(self, migration_dir: Path) -> Path:
        """Create a complex migration with multiple operations."""
        return self._create_migration_file(migration_dir, "complex.sql", """CREATE TABLE complex_parent (id SERIAL PRIMARY KEY, data JSONB, tags TEXT[]); CREATE TABLE complex_child (id SERIAL PRIMARY KEY, parent_id INTEGER REFERENCES complex_parent(id), metadata JSONB); CREATE INDEX complex_parent_data_idx ON complex_parent USING GIN (data); CREATE INDEX complex_parent_tags_idx ON complex_parent USING GIN (tags); CREATE INDEX complex_child_parent_idx ON complex_child(parent_id);""")
    
    def _create_large_data_migration(self, migration_dir: Path) -> Path:
        """Create a migration that handles large data volume."""
        return self._create_migration_file(migration_dir, "large_data.sql", """CREATE TABLE large_data_test (id SERIAL PRIMARY KEY, data TEXT, created_at TIMESTAMP DEFAULT NOW()); INSERT INTO large_data_test (data) SELECT md5(random()::text) FROM generate_series(1, 10000); CREATE INDEX large_data_created_idx ON large_data_test(created_at);""")
