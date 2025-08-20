"""Managers Tests - Split from test_database_manager.py

**Business Value Justification (BVJ):**
- Segment: Engineering Quality & Enterprise
- Business Goal: Eliminate test failures from database pollution (99.9% test reliability)
- Value Impact: Reduces debugging time by 80%, prevents $25K MRR loss from test instability
- Revenue Impact: Enables confident CI/CD, faster releases, better enterprise trust

Features:
- Temporary test databases per test suite
- Realistic seed data for common scenarios
- Automatic cleanup after tests
- Transaction rollback support
- Database snapshots for fast reset
- Both PostgreSQL and ClickHouse support

Each function ≤8 lines, file ≤300 lines.
"""

import asyncio
import os
import uuid
import tempfile
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple, Set
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, create_engine
import asyncpg
import clickhouse_connect
from app.logging_config import central_logger
from app.core.database_types import DatabaseType, DatabaseConfig
from app.core.exceptions_config import DatabaseError
from .fixtures.database_test_fixtures import create_mock_user, create_mock_thread, create_mock_message
import subprocess
import shutil

    def __init__(self):
        """Initialize test database manager."""
        self._active_databases: Dict[str, Dict] = {}
        self._cleanup_tasks: Set[str] = set()
        self._base_config = self._load_base_config()
        self._temp_dir = Path(tempfile.mkdtemp(prefix="netra_test_db_"))
        self._snapshots: Dict[str, Dict] = {}

    def _load_base_config(self) -> Dict[str, str]:
        """Load base database configuration."""
        return {
            "postgres_host": os.environ.get("TEST_POSTGRES_HOST", "localhost"),
            "postgres_port": os.environ.get("TEST_POSTGRES_PORT", "5432"),
            "clickhouse_host": os.environ.get("TEST_CLICKHOUSE_HOST", "localhost"),
            "clickhouse_port": os.environ.get("TEST_CLICKHOUSE_PORT", "8123")
        }

    def _setup_clickhouse_db(self, db_id: str, db_name: str, client) -> Dict[str, Any]:
        """Setup ClickHouse test database configuration."""
        db_info = {
            "id": db_id, "name": db_name, "type": DatabaseType.CLICKHOUSE,
            "client": client, "host": self._base_config['clickhouse_host'],
            "port": self._base_config['clickhouse_port'],
            "created_at": datetime.now(UTC)
        }
        
        self._active_databases[db_id] = db_info
        return db_info

    def _create_basic_clickhouse_tables(self, client, db_name: str) -> None:
        """Create basic ClickHouse tables for testing."""
        client.command(f"""
            CREATE TABLE {db_name}.test_events (
                id UInt64,
                event_type String,
                timestamp DateTime64(3),
                user_id String
            ) ENGINE = MergeTree()
            ORDER BY (timestamp, id)
        """)

    def _insert_basic_clickhouse_data(self, client, db_name: str) -> None:
        """Insert basic test data into ClickHouse."""
        client.insert(f"{db_name}.test_events", [
            [1, "click", datetime.now(UTC), "user1"],
            [2, "view", datetime.now(UTC), "user2"]
        ])

    def _create_clickhouse_snapshot(self, db_info: Dict, snapshot_name: str) -> None:
        """Create ClickHouse database snapshot."""
        client = db_info["client"]
        db_name = db_info["name"]
        
        # Get table list
        tables = client.query(f"SHOW TABLES FROM {db_name}").result_rows
        table_names = [table[0] for table in tables]
        
        self._snapshots[f"{db_info['id']}_{snapshot_name}"] = {
            "type": DatabaseType.CLICKHOUSE,
            "database": db_name,
            "tables": table_names,
            "created_at": datetime.now(UTC)
        }

    def _restore_clickhouse_snapshot(self, db_info: Dict, snapshot: Dict) -> None:
        """Restore ClickHouse database from snapshot."""
        client = db_info["client"]
        db_name = db_info["name"]
        
        # Clear all tables
        for table in snapshot["tables"]:
            client.command(f"TRUNCATE TABLE {db_name}.{table}")

    def _validate_clickhouse_state(self, db_info: Dict) -> Dict[str, Any]:
        """Validate ClickHouse database state."""
        try:
            client = db_info["client"]
            result = client.query("SELECT 1").result_rows
            connection_ok = len(result) > 0 and result[0][0] == 1
            
            # Check table count
            db_name = db_info["name"]
            tables = client.query(f"SHOW TABLES FROM {db_name}").result_rows
            table_count = len(tables)
            
            return {
                "status": "healthy" if connection_ok else "unhealthy",
                "connection_ok": connection_ok,
                "table_count": table_count,
                "database_id": db_info["id"],
                "checked_at": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy", "connection_ok": False,
                "error": str(e), "database_id": db_info["id"],
                "checked_at": datetime.now(UTC).isoformat()
            }

    def _cleanup_clickhouse_db(self, db_info: Dict) -> None:
        """Cleanup ClickHouse test database."""
        try:
            client = db_info["client"]
            client.command(f"DROP DATABASE IF EXISTS {db_info['name']}")
            client.close()
        except Exception as e:
            logger.warning(f"ClickHouse cleanup warning: {e}")

    def get_active_databases(self) -> Dict[str, Dict]:
        """Get information about all active test databases."""
        return {
            db_id: {
                "id": info["id"], "name": info["name"],
                "type": info["type"].value, "created_at": info["created_at"].isoformat()
            }
            for db_id, info in self._active_databases.items()
        }
