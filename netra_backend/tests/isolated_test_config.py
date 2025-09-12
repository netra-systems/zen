"""Isolated Test Configuration Integration

**Business Value Justification (BVJ):**
- Segment: Engineering Quality & Enterprise
- Business Goal: Seamless integration of isolated databases into test suite
- Value Impact: 100% test reliability, zero configuration errors
- Revenue Impact: Confident CI/CD, enterprise deployment reliability

Features:
- Pytest integration for isolated database fixtures
- Automatic test database lifecycle management
- Configuration inheritance and override
- Parallel test execution support
- Environment-specific database settings
- Cleanup automation and resource management

Each function  <= 8 lines, file  <= 300 lines.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest

from netra_backend.app.core.database_types import DatabaseType
from netra_backend.app.logging_config import central_logger
from netra_backend.tests.clickhouse_isolation import ClickHouseTestIsolator
from netra_backend.tests.database_snapshots import snapshot_manager
from netra_backend.tests.database_state_validator import db_state_validator

# from netra_backend.tests.test_database_manager import test_db_manager  # TODO: Fix this import
from netra_backend.tests.postgres_isolation import PostgreSQLTestIsolator
from netra_backend.tests.seed_data_manager import seed_data_manager

# Temporary placeholder for test_db_manager
test_db_manager = None

logger = central_logger.get_logger(__name__)

class IsolatedTestConfig:
    """Configuration for isolated database testing."""
    
    def __init__(self, test_id: str = None, cleanup_on_exit: bool = True):
        """Initialize isolated test configuration."""
        self.test_id = test_id or f"test_{uuid.uuid4().hex[:8]}"
        self.cleanup_on_exit = cleanup_on_exit
        self._active_databases: Dict[str, Any] = {}
        self._snapshots: List[str] = []
        self._isolators: Dict[str, Any] = {}
        
    async def setup_postgres_isolation(self, schema_type: str = "basic",
                                     seed_scenario: str = None) -> Dict[str, Any]:
        """Setup isolated PostgreSQL database for testing."""
        isolator = PostgreSQLTestIsolator()
        db_config = await isolator.create_isolated_database(self.test_id)
        await isolator.setup_test_schema(self.test_id, schema_type)
        
        # Seed data if requested
        if seed_scenario:
            session_factory = db_config["session_factory"]
            async with session_factory() as session:
                await seed_data_manager.seed_scenario(
                    self.test_id, seed_scenario, postgres_session=session
                )
        
        self._active_databases["postgres"] = db_config
        self._isolators["postgres"] = isolator
        return db_config
    
    def setup_clickhouse_isolation(self, table_set: str = "basic",
                                 seed_scenario: str = None) -> Dict[str, Any]:
        """Setup isolated ClickHouse database for testing."""
        isolator = ClickHouseTestIsolator()
        db_config = isolator.create_isolated_database(self.test_id)
        tables = isolator.setup_analytics_tables(self.test_id, table_set)
        
        # Seed data if requested
        if seed_scenario:
            seed_data_manager.seed_scenario(
                self.test_id, seed_scenario, 
                clickhouse_client=db_config["client"],
                database_names={"clickhouse": db_config["database_name"]}
            )
        
        self._active_databases["clickhouse"] = db_config
        self._isolators["clickhouse"] = isolator
        return db_config
    
    async def create_snapshot(self, database_type: str, snapshot_name: str = None) -> str:
        """Create database snapshot for fast reset during tests."""
        if database_type not in self._active_databases:
            raise ValueError(f"Database type {database_type} not configured")
        
        db_config = self._active_databases[database_type]
        db_type = DatabaseType.POSTGRESQL if database_type == "postgres" else DatabaseType.CLICKHOUSE
        
        snapshot_id = await snapshot_manager.create_snapshot(
            self.test_id, db_type, db_config, snapshot_name
        )
        self._snapshots.append(snapshot_id)
        return snapshot_id
    
    async def restore_snapshot(self, snapshot_id: str) -> None:
        """Restore database from snapshot."""
        # Find appropriate database config for restoration
        for db_type, db_config in self._active_databases.items():
            await snapshot_manager.restore_snapshot(snapshot_id, db_config)
            break
    
    async def validate_database_state(self) -> Dict[str, Any]:
        """Validate state of all configured databases."""
        validation_results = {}
        
        # Validate PostgreSQL
        if "postgres" in self._active_databases:
            postgres_config = self._active_databases["postgres"]
            async with postgres_config["session_factory"]() as session:
                pg_results = await db_state_validator.validate_postgres_state(session, self.test_id)
                validation_results["postgres"] = db_state_validator.generate_validation_report(pg_results)
        
        # Validate ClickHouse
        if "clickhouse" in self._active_databases:
            ch_config = self._active_databases["clickhouse"]
            ch_results = db_state_validator.validate_clickhouse_state(
                ch_config["client"], ch_config["database_name"], self.test_id
            )
            validation_results["clickhouse"] = db_state_validator.generate_validation_report(ch_results)
        
        return validation_results
    
    async def cleanup_databases(self) -> None:
        """Clean up all isolated databases."""
        cleanup_tasks = []
        
        # Clean up snapshots
        for snapshot_id in self._snapshots:
            cleanup_tasks.append(snapshot_manager.delete_snapshot(snapshot_id))
        
        # Clean up databases
        for db_type, isolator in self._isolators.items():
            if hasattr(isolator, 'cleanup_test_database'):
                cleanup_tasks.append(isolator.cleanup_test_database(self.test_id))
            elif hasattr(isolator, 'cleanup_database'):
                cleanup_tasks.append(isolator.cleanup_database(self.test_id))
        
        # Clean up seed data cache
        seed_data_manager.cleanup_test_data(self.test_id)
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    def get_postgres_session_factory(self):
        """Get PostgreSQL session factory for testing."""
        if "postgres" not in self._active_databases:
            raise ValueError("PostgreSQL not configured for this test")
        return self._active_databases["postgres"]["session_factory"]
    
    def get_clickhouse_client(self):
        """Get ClickHouse client for testing."""
        if "clickhouse" not in self._active_databases:
            raise ValueError("ClickHouse not configured for this test")
        return self._active_databases["clickhouse"]["client"]
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about configured databases."""
        info = {"test_id": self.test_id, "configured_databases": []}
        
        for db_type, config in self._active_databases.items():
            if db_type == "postgres":
                info["configured_databases"].append({
                    "type": "postgresql",
                    "database_name": config["database_name"],
                    "url": config["url"]
                })
            elif db_type == "clickhouse":
                info["configured_databases"].append({
                    "type": "clickhouse", 
                    "database_name": config["database_name"],
                    "host": config["host"],
                    "port": config["port"]
                })
        
        info["snapshots"] = len(self._snapshots)
        return info

# Pytest fixtures for isolated testing
@pytest.fixture
async def isolated_test_config():
    """Pytest fixture for isolated test configuration."""
    config = IsolatedTestConfig()
    try:
        yield config
    finally:
        if config.cleanup_on_exit:
            await config.cleanup_databases()

@pytest.fixture
async def isolated_postgres(isolated_test_config):
    """Pytest fixture for isolated PostgreSQL database."""
    db_config = await isolated_test_config.setup_postgres_isolation()
    session_factory = db_config["session_factory"]
    
    async with session_factory() as session:
        try:
            yield session
        finally:
            if hasattr(session, "close"):
                await session.close()

@pytest.fixture
async def isolated_clickhouse(isolated_test_config):
    """Pytest fixture for isolated ClickHouse database."""
    db_config = isolated_test_config.setup_clickhouse_isolation()
    client = db_config["client"]
    database_name = db_config["database_name"]
    
    yield client, database_name, isolated_test_config

@pytest.fixture
async def isolated_full_stack(isolated_test_config):
    """Pytest fixture for full database stack isolation."""
    # Setup PostgreSQL
    pg_config = await isolated_test_config.setup_postgres_isolation(
        schema_type="user_management", seed_scenario="basic_workflow"
    )
    
    # Setup ClickHouse
    ch_config = isolated_test_config.setup_clickhouse_isolation(
        table_set="events", seed_scenario="basic_workflow"
    )
    
    # Create snapshots for fast reset
    pg_snapshot = await isolated_test_config.create_snapshot("postgres", "initial_state")
    ch_snapshot = await isolated_test_config.create_snapshot("clickhouse", "initial_state")
    
    async with pg_config["session_factory"]() as pg_session:
        yield {
            "postgres_session": pg_session,
            "clickhouse_client": ch_config["client"],
            "clickhouse_database": ch_config["database_name"],
            "config": isolated_test_config,
            "snapshots": {"postgres": pg_snapshot, "clickhouse": ch_snapshot}
        }

# Context managers for manual control
@asynccontextmanager
async def with_isolated_postgres(test_name: str, schema_type: str = "basic",
                               seed_scenario: str = None) -> AsyncGenerator[Any, None]:
    """Context manager for isolated PostgreSQL testing."""
    config = IsolatedTestConfig(test_id=test_name)
    
    try:
        db_config = await config.setup_postgres_isolation(schema_type, seed_scenario)
        session_factory = db_config["session_factory"]
        
        async with session_factory() as session:
            yield session, config
    finally:
        await config.cleanup_databases()

@asynccontextmanager
async def with_isolated_clickhouse(test_name: str, table_set: str = "basic",
                                 seed_scenario: str = None) -> AsyncGenerator[Any, None]:
    """Context manager for isolated ClickHouse testing."""
    config = IsolatedTestConfig(test_id=test_name)
    
    try:
        db_config = config.setup_clickhouse_isolation(table_set, seed_scenario)
        client = db_config["client"]
        database_name = db_config["database_name"]
        
        yield client, database_name, config
    finally:
        await config.cleanup_databases()

@asynccontextmanager
async def with_database_snapshots(test_name: str, postgres_schema: str = "basic",
                                clickhouse_tables: str = "basic") -> AsyncGenerator[Any, None]:
    """Context manager with database snapshots for fast test resets."""
    config = IsolatedTestConfig(test_id=test_name)
    
    try:
        # Setup databases
        pg_config = await config.setup_postgres_isolation(postgres_schema)
        ch_config = config.setup_clickhouse_isolation(clickhouse_tables)
        
        # Create initial snapshots
        pg_snapshot = await config.create_snapshot("postgres", "clean_state")
        ch_snapshot = await config.create_snapshot("clickhouse", "clean_state")
        
        async with pg_config["session_factory"]() as pg_session:
            yield {
                "postgres_session": pg_session,
                "clickhouse_client": ch_config["client"],
                "clickhouse_database": ch_config["database_name"],
                "config": config,
                "reset_to_clean_state": lambda: asyncio.gather(
                    config.restore_snapshot(pg_snapshot),
                    config.restore_snapshot(ch_snapshot)
                )
            }
    finally:
        await config.cleanup_databases()

# Performance testing utilities
class PerformanceTestConfig:
    """Configuration for performance testing with isolated databases."""
    
    def __init__(self, test_id: str, scale_factor: int = 1):
        """Initialize performance test configuration."""
        self.test_id = test_id
        self.scale_factor = scale_factor
        self._base_config = IsolatedTestConfig(test_id)
    
    async def setup_performance_databases(self) -> Dict[str, Any]:
        """Setup databases optimized for performance testing."""
        # Setup PostgreSQL with performance schema
        pg_config = await self._base_config.setup_postgres_isolation("user_management")
        
        # Setup ClickHouse with metrics tables
        ch_config = self._base_config.setup_clickhouse_isolation("metrics")
        
        # Seed with scaled performance data
        async with pg_config["session_factory"]() as pg_session:
            results = await seed_data_manager.seed_performance_data(
                self.test_id, pg_session, ch_config["client"],
                {"clickhouse": ch_config["database_name"]},
                self.scale_factor
            )
        
        return {
            "postgres_session_factory": pg_config["session_factory"],
            "clickhouse_client": ch_config["client"],
            "clickhouse_database": ch_config["database_name"],
            "data_scale": results,
            "config": self._base_config
        }
    
    async def cleanup(self) -> None:
        """Clean up performance test resources."""
        await self._base_config.cleanup_databases()

@pytest.fixture
async def performance_test_config():
    """Pytest fixture for performance testing configuration."""
    config = PerformanceTestConfig(f"perf_test_{uuid.uuid4().hex[:8]}")
    databases = await config.setup_performance_databases()
    
    try:
        yield databases
    finally:
        await config.cleanup()

# Testing utilities
async def run_database_health_check(isolated_config: IsolatedTestConfig) -> Dict[str, Any]:
    """Run comprehensive health check on isolated databases."""
    health_results = await isolated_config.validate_database_state()
    
    # Add isolation verification
    isolation_results = await db_state_validator.validate_test_isolation(
        isolated_config.test_id,
        postgres_session=None,  # Would need session from config
        clickhouse_client=isolated_config.get_clickhouse_client() if "clickhouse" in isolated_config._active_databases else None,
        clickhouse_database=isolated_config._active_databases.get("clickhouse", {}).get("database_name")
    )
    
    health_results["isolation"] = db_state_validator.generate_validation_report(isolation_results)
    return health_results

def create_test_database_url(test_id: str, db_type: str = "postgres") -> str:
    """Create test database URL for external tools."""
    if db_type == "postgres":
        return f"postgresql://postgres:postgres@localhost:5432/test_db_{test_id}"
    elif db_type == "clickhouse":
        return f"clickhouse://default@localhost:8123/test_ch_{test_id}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

# Example usage patterns
async def example_isolated_test():
    """Example of using isolated database testing."""
    async with with_isolated_postgres("example_test", "user_management", "minimal") as (session, config):
        # Run tests with isolated database
        from sqlalchemy import text
        
        # Test database isolation
        result = await session.execute(text("SELECT current_database()"))
        db_name = result.scalar()
        assert "example_test" in db_name
        
        # Test seeded data
        user_result = await session.execute(text("SELECT count(*) FROM test_users"))
        user_count = user_result.scalar()
        assert user_count > 0
        
        # Validate database state
        validation_results = await config.validate_database_state()
        assert validation_results["postgres"]["status"] in ["passed", "warning"]

async def example_snapshot_test():
    """Example of using database snapshots for fast resets."""
    async with with_database_snapshots("snapshot_test") as test_env:
        postgres_session = test_env["postgres_session"]
        reset_func = test_env["reset_to_clean_state"]
        
        # Make changes to database
        from sqlalchemy import text
        await postgres_session.execute(text("INSERT INTO test_users (email, full_name) VALUES ('test@example.com', 'Test User')"))
        await postgres_session.commit()
        
        # Verify changes
        result = await postgres_session.execute(text("SELECT count(*) FROM test_users"))
        count_after = result.scalar()
        
        # Reset to clean state
        await reset_func()
        
        # Verify reset worked
        result = await postgres_session.execute(text("SELECT count(*) FROM test_users"))
        count_after_reset = result.scalar()
        assert count_after_reset < count_after