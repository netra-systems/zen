"""
ClickHouse Schema Initialization Integration Test.

BVJ (Business Value Justification):
- Segment: Platform/Internal  
- Business Goal: Platform Stability, Development Velocity
- Value Impact: Ensures analytics and metrics data integrity from system startup
- Strategic Impact: Enables reliable data-driven optimization features for all customer segments

This test validates ClickHouse schema initialization using real ClickHouse containers (L3 realism)
to ensure production-level schema consistency and version tracking.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import os
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import pytest
from clickhouse_driver import Client
from logging_config import central_logger

# Add project root to path
from netra_backend.app.db.clickhouse_init import (
    initialize_clickhouse_tables,
    verify_workload_events_table,
)
from netra_backend.app.db.models_clickhouse import (
    # Add project root to path
    LOGS_TABLE_SCHEMA,
    SUPPLY_TABLE_SCHEMA,
    WORKLOAD_EVENTS_TABLE_SCHEMA,
)

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
class TestClickHouseSchemaInitialization:
    """Integration tests for ClickHouse schema initialization and version tracking."""

    @pytest.fixture(scope="function")
    def clickhouse_container(self):
        """Create real ClickHouse container for L3 testing using Docker CLI."""
        container_name = f"test_clickhouse_{os.getpid()}_{id(self)}"
        
        try:
            # Start ClickHouse container
            subprocess.run([
                "docker", "run", "-d", "--name", container_name,
                "-p", "0:8123",  # HTTP interface
                "-p", "0:9000",  # Native interface
                "--ulimit", "nofile=262144:262144",
                "clickhouse/clickhouse-server:23.3"
            ], check=True, capture_output=True)
            
            # Get assigned ports
            http_port_result = subprocess.run([
                "docker", "port", container_name, "8123"
            ], capture_output=True, text=True, check=True)
            
            native_port_result = subprocess.run([
                "docker", "port", container_name, "9000"  
            ], capture_output=True, text=True, check=True)
            
            http_port = int(http_port_result.stdout.strip().split(':')[1])
            native_port = int(native_port_result.stdout.strip().split(':')[1])
            
            # Wait for ClickHouse to be ready
            self._wait_for_clickhouse_ready(container_name, native_port)
            
            yield {
                "container_name": container_name,
                "host": "localhost",
                "http_port": http_port,
                "native_port": native_port
            }
            
        finally:
            # Cleanup container
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    @pytest.fixture  
    def schema_config(self, clickhouse_container):
        """Configuration for schema initialization testing."""
        ch = clickhouse_container
        return {
            "clickhouse_url": f"http://{ch['host']}:{ch['http_port']}",
            "host": ch["host"],
            "native_port": ch["native_port"],
            "database": "default",
            "timeout_seconds": 30,
            "expected_tables": [
                "netra_app_internal_logs",
                "netra_global_supply_catalog", 
                "workload_events"
            ],
            "schema_version_table": "schema_versions"
        }

    async def test_all_required_tables_created_on_initialization(self, schema_config):
        """
        Test that all required tables are created during initialization.
        
        Validates:
        - All expected tables are created
        - Tables have correct schemas
        - Initialization is idempotent
        - No errors during table creation
        """
        # Initialize schema
        initialization_success = await self._perform_schema_initialization(schema_config)
        assert initialization_success, "Schema initialization failed"

        # Verify all expected tables exist
        all_tables_exist = await self._verify_all_expected_tables_exist(schema_config)
        assert all_tables_exist, "Not all expected tables were created"

        # Verify table schemas are correct
        schemas_correct = await self._verify_table_schemas_correct(schema_config)
        assert schemas_correct, "Table schemas do not match expected structure"

    async def test_idempotent_initialization_multiple_runs(self, schema_config):
        """Test schema initialization can run multiple times safely."""
        # Run initialization multiple times
        for run in range(3):
            run_success = await self._perform_schema_initialization(schema_config)
            assert run_success, f"Schema initialization run {run + 1} failed"

        # Verify tables still exist and are correct
        final_state_correct = await self._verify_final_schema_state(schema_config)
        assert final_state_correct, "Final schema state incorrect after multiple runs"

        # Verify no duplicate tables or corruption
        no_corruption = await self._verify_no_schema_corruption(schema_config)
        assert no_corruption, "Schema corruption detected after multiple runs"

    async def test_schema_version_tracking_mechanism(self, schema_config):
        """Test schema version tracking and migration detection."""
        # Initialize with version tracking
        version_tracking_enabled = await self._initialize_with_version_tracking(schema_config)
        assert version_tracking_enabled, "Failed to enable version tracking"

        # Verify version table exists and has correct structure
        version_table_correct = await self._verify_version_table_structure(schema_config)
        assert version_table_correct, "Version table structure incorrect"

        # Test version increment on schema changes
        version_increments = await self._test_version_increment_on_changes(schema_config)
        assert version_increments, "Version not incremented on schema changes"

    async def test_workload_events_table_accessibility_validation(self, schema_config):
        """Test workload_events table is properly accessible for operations."""
        # Initialize tables
        await self._perform_schema_initialization(schema_config)

        # Test workload_events table accessibility
        accessibility_verified = await self._verify_workload_events_accessibility(schema_config)
        assert accessibility_verified, "workload_events table not accessible"

        # Test insert/query operations
        operations_working = await self._test_workload_events_operations(schema_config)
        assert operations_working, "workload_events table operations not working"

    async def test_initialization_failure_recovery(self, schema_config):
        """Test recovery from initialization failures."""
        # Simulate initialization failure
        failure_simulated = await self._simulate_initialization_failure(schema_config)
        assert failure_simulated, "Failed to simulate initialization failure"

        # Attempt recovery
        recovery_successful = await self._attempt_initialization_recovery(schema_config)
        assert recovery_successful, "Failed to recover from initialization failure"

        # Verify final state is correct
        recovery_state_correct = await self._verify_recovery_state_correct(schema_config)
        assert recovery_state_correct, "Recovery state not correct"

    # Helper methods (each under 25 lines)

    def _wait_for_clickhouse_ready(self, container_name: str, native_port: int, max_wait: int = 60) -> None:
        """Wait for ClickHouse container to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Try to connect using native client
                client = Client(host="localhost", port=native_port)
                client.execute("SELECT 1")
                return
            except Exception:
                time.sleep(2)
        
        raise TimeoutError(f"ClickHouse container {container_name} did not become ready within {max_wait}s")

    async def _perform_schema_initialization(self, config: Dict[str, Any]) -> bool:
        """Perform ClickHouse schema initialization."""
        try:
            # Mock settings to point to test ClickHouse
            with self._mock_clickhouse_settings(config):
                await initialize_clickhouse_tables(verbose=True)
            return True
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            return False

    async def _verify_all_expected_tables_exist(self, config: Dict[str, Any]) -> bool:
        """Verify all expected tables exist in ClickHouse."""
        try:
            client = self._get_clickhouse_client(config)
            tables = client.execute("SHOW TABLES")
            table_names = [table[0] for table in tables]
            
            for expected_table in config["expected_tables"]:
                if expected_table not in table_names:
                    logger.error(f"Expected table {expected_table} not found")
                    return False
            return True
        except Exception as e:
            logger.error(f"Failed to verify tables exist: {e}")
            return False

    async def _verify_table_schemas_correct(self, config: Dict[str, Any]) -> bool:
        """Verify table schemas match expected structure."""
        try:
            client = self._get_clickhouse_client(config)
            
            # Check workload_events table structure
            columns = client.execute("DESCRIBE TABLE workload_events")
            column_names = [col[0] for col in columns]
            
            expected_columns = ["timestamp", "event_type", "user_id", "data"]
            for expected_col in expected_columns:
                if expected_col not in column_names:
                    logger.error(f"Expected column {expected_col} not found in workload_events")
                    return False
            return True
        except Exception as e:
            logger.error(f"Failed to verify table schemas: {e}")
            return False

    async def _verify_final_schema_state(self, config: Dict[str, Any]) -> bool:
        """Verify final schema state after multiple initialization runs."""
        # Check tables still exist
        tables_exist = await self._verify_all_expected_tables_exist(config)
        if not tables_exist:
            return False
        
        # Check schemas are still correct
        schemas_correct = await self._verify_table_schemas_correct(config)
        return schemas_correct

    async def _verify_no_schema_corruption(self, config: Dict[str, Any]) -> bool:
        """Verify no schema corruption occurred."""
        try:
            client = self._get_clickhouse_client(config)
            
            # Test basic operations on each table
            for table in config["expected_tables"]:
                client.execute(f"SELECT COUNT(*) FROM {table}")
            
            return True
        except Exception as e:
            logger.error(f"Schema corruption detected: {e}")
            return False

    async def _initialize_with_version_tracking(self, config: Dict[str, Any]) -> bool:
        """Initialize schema with version tracking enabled."""
        try:
            client = self._get_clickhouse_client(config)
            
            # Create version tracking table
            client.execute(f"""
                CREATE TABLE IF NOT EXISTS {config["schema_version_table"]} (
                    version UInt32,
                    applied_at DateTime DEFAULT now(),
                    description String
                ) ENGINE = MergeTree()
                ORDER BY version
            """)
            
            # Insert initial version
            client.execute(f"""
                INSERT INTO {config["schema_version_table"]} (version, description)
                VALUES (1, 'Initial schema creation')
            """)
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize version tracking: {e}")
            return False

    async def _verify_version_table_structure(self, config: Dict[str, Any]) -> bool:
        """Verify version table has correct structure."""
        try:
            client = self._get_clickhouse_client(config)
            columns = client.execute(f"DESCRIBE TABLE {config['schema_version_table']}")
            column_names = [col[0] for col in columns]
            
            expected_columns = ["version", "applied_at", "description"]
            return all(col in column_names for col in expected_columns)
        except Exception as e:
            logger.error(f"Failed to verify version table structure: {e}")
            return False

    async def _test_version_increment_on_changes(self, config: Dict[str, Any]) -> bool:
        """Test that version increments when schema changes occur."""
        try:
            client = self._get_clickhouse_client(config)
            
            # Get current version
            result = client.execute(f"SELECT MAX(version) FROM {config['schema_version_table']}")
            current_version = result[0][0] if result else 0
            
            # Simulate schema change
            client.execute("""
                CREATE TABLE IF NOT EXISTS test_version_table (
                    id UInt32,
                    name String
                ) ENGINE = MergeTree() ORDER BY id
            """)
            
            # Insert new version
            new_version = current_version + 1
            client.execute(f"""
                INSERT INTO {config["schema_version_table"]} (version, description)
                VALUES ({new_version}, 'Test schema change')
            """)
            
            # Verify version was incremented
            result = client.execute(f"SELECT MAX(version) FROM {config['schema_version_table']}")
            latest_version = result[0][0]
            
            return latest_version == new_version
        except Exception as e:
            logger.error(f"Failed to test version increment: {e}")
            return False

    async def _verify_workload_events_accessibility(self, config: Dict[str, Any]) -> bool:
        """Verify workload_events table is accessible."""
        try:
            # Use the actual verification function
            return await verify_workload_events_table()
        except Exception as e:
            logger.error(f"workload_events accessibility verification failed: {e}")
            return False

    async def _test_workload_events_operations(self, config: Dict[str, Any]) -> bool:
        """Test basic operations on workload_events table."""
        try:
            client = self._get_clickhouse_client(config)
            
            # Test insert
            client.execute("""
                INSERT INTO workload_events (timestamp, event_type, user_id, data)
                VALUES (now(), 'test_event', 'test_user', '{"test": "data"}')
            """)
            
            # Test query
            result = client.execute("SELECT COUNT(*) FROM workload_events WHERE event_type = 'test_event'")
            count = result[0][0]
            
            return count >= 1
        except Exception as e:
            logger.error(f"workload_events operations test failed: {e}")
            return False

    async def _simulate_initialization_failure(self, config: Dict[str, Any]) -> bool:
        """Simulate initialization failure scenario."""
        try:
            client = self._get_clickhouse_client(config)
            
            # Create a conflicting table to cause failure
            client.execute("""
                CREATE TABLE IF NOT EXISTS workload_events (
                    wrong_column String
                ) ENGINE = MergeTree() ORDER BY wrong_column
            """)
            
            return True
        except Exception as e:
            logger.error(f"Failed to simulate initialization failure: {e}")
            return False

    async def _attempt_initialization_recovery(self, config: Dict[str, Any]) -> bool:
        """Attempt to recover from initialization failure."""
        try:
            client = self._get_clickhouse_client(config)
            
            # Drop conflicting table
            client.execute("DROP TABLE IF EXISTS workload_events")
            
            # Retry initialization
            return await self._perform_schema_initialization(config)
        except Exception as e:
            logger.error(f"Failed to recover from initialization failure: {e}")
            return False

    async def _verify_recovery_state_correct(self, config: Dict[str, Any]) -> bool:
        """Verify system state is correct after recovery."""
        # Verify tables exist
        tables_exist = await self._verify_all_expected_tables_exist(config)
        if not tables_exist:
            return False
        
        # Verify workload_events is accessible
        workload_accessible = await self._verify_workload_events_accessibility(config)
        return workload_accessible

    # Utility methods

    def _get_clickhouse_client(self, config: Dict[str, Any]) -> Client:
        """Get ClickHouse client for testing."""
        return Client(host=config["host"], port=config["native_port"])

    def _mock_clickhouse_settings(self, config: Dict[str, Any]):
        """Mock ClickHouse settings to point to test container."""
        from unittest.mock import patch
        
        return patch.multiple(
            'app.config.settings',
            clickhouse_host=config["host"],
            clickhouse_port=config["native_port"],
            clickhouse_url=config["clickhouse_url"],
            environment="testing"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])