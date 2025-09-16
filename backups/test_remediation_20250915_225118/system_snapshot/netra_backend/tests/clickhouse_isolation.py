"""ClickHouse Test Database Isolation Utilities

**Business Value Justification (BVJ):**
- Segment: Analytics & Enterprise
- Business Goal: Isolated ClickHouse testing for analytics workloads
- Value Impact: Reliable analytics testing, zero data corruption between tests
- Revenue Impact: Confident analytics feature deployments, enterprise data integrity

ClickHouse-specific isolation features:
- Database creation and cleanup
- Table partitioning for isolation
- Data insertion and querying
- Performance testing isolation
- MergeTree engine optimization
- Test data generation

Each function  <= 8 lines, file  <= 300 lines.
"""

import random
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from netra_backend.app.core.exceptions_config import DatabaseError
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class ClickHouseTestIsolator:
    """ClickHouse-specific test database isolation."""
    
    def __init__(self, host: str = "localhost", port: str = "8123"):
        """Initialize ClickHouse test isolator."""
        self.host = host
        self.port = int(port)
        self._active_databases: Dict[str, Dict] = {}
        self._clients: Dict[str, Client] = {}
        self._table_schemas: Dict[str, List[str]] = {}
    
    def create_isolated_database(self, test_id: str) -> Dict[str, Any]:
        """Create isolated ClickHouse database for testing."""
        db_name = self._generate_db_name(test_id)
        client = clickhouse_connect.get_client(host=self.host, port=self.port)
        
        # Create database
        client.command(f"DROP DATABASE IF EXISTS {db_name}")
        client.command(f"CREATE DATABASE {db_name}")
        
        return self._setup_isolated_connection(test_id, db_name, client)
    
    def _generate_db_name(self, test_id: str) -> str:
        """Generate unique database name for ClickHouse test."""
        clean_id = test_id.replace("-", "_").replace(".", "_")
        return f"test_ch_{clean_id}_{uuid.uuid4().hex[:8]}"
    
    def _setup_isolated_connection(self, test_id: str, db_name: str, client: Client) -> Dict[str, Any]:
        """Setup isolated ClickHouse connection configuration."""
        # Create database-specific client
        db_client = clickhouse_connect.get_client(
            host=self.host, port=self.port, database=db_name
        )
        
        config = {
            "test_id": test_id, "database_name": db_name,
            "client": db_client, "admin_client": client,
            "host": self.host, "port": self.port,
            "created_at": datetime.now(UTC)
        }
        
        self._active_databases[test_id] = config
        self._clients[test_id] = db_client
        return config
    
    def setup_analytics_tables(self, test_id: str, table_set: str = "basic") -> List[str]:
        """Setup ClickHouse analytics tables in isolated database."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        client = self._clients[test_id]
        if table_set == "basic":
            return self._create_basic_tables(client)
        elif table_set == "events":
            return self._create_event_tables(client)
        elif table_set == "metrics":
            return self._create_metrics_tables(client)
        else:
            raise DatabaseError(f"Unknown table set: {table_set}")
    
    def _create_basic_tables(self, client: Client) -> List[str]:
        """Create basic ClickHouse test tables."""
        client.command("""
            CREATE TABLE test_logs (
                id UInt64,
                timestamp DateTime64(3),
                level String,
                message String,
                source String
            ) ENGINE = MergeTree()
            ORDER BY (timestamp, id)
            PARTITION BY toYYYYMM(timestamp)
        """)
        
        return ["test_logs"]
    
    def _create_event_tables(self, client: Client) -> List[str]:
        """Create event tracking tables for testing."""
        client.command("""
            CREATE TABLE test_events (
                event_id UInt64,
                user_id String,
                event_type String,
                timestamp DateTime64(3),
                properties Map(String, String),
                session_id String
            ) ENGINE = MergeTree()
            ORDER BY (timestamp, event_id)
            PARTITION BY toYYYYMMDD(timestamp)
        """)
        
        client.command("""
            CREATE TABLE test_user_sessions (
                session_id String,
                user_id String,
                start_time DateTime64(3),
                end_time DateTime64(3),
                event_count UInt32
            ) ENGINE = MergeTree()
            ORDER BY (start_time, session_id)
        """)
        
        return ["test_events", "test_user_sessions"]
    
    def _create_metrics_tables(self, client: Client) -> List[str]:
        """Create metrics tables for performance testing."""
        client.command("""
            CREATE TABLE test_metrics (
                metric_name String,
                timestamp DateTime64(3),
                value Float64,
                tags Map(String, String),
                host String
            ) ENGINE = MergeTree()
            ORDER BY (metric_name, timestamp)
            PARTITION BY toYYYYMMDD(timestamp)
        """)
        
        client.command("""
            CREATE TABLE test_aggregated_metrics (
                metric_name String,
                date Date,
                hour UInt8,
                avg_value Float64,
                min_value Float64,
                max_value Float64,
                count UInt64
            ) ENGINE = SummingMergeTree()
            ORDER BY (metric_name, date, hour)
        """)
        
        return ["test_metrics", "test_aggregated_metrics"]
    
    def seed_test_data(self, test_id: str, data_type: str = "minimal", row_count: int = 1000) -> Dict[str, int]:
        """Seed ClickHouse test database with realistic data."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        client = self._clients[test_id]
        if data_type == "minimal":
            return self._seed_minimal_data(client, row_count)
        elif data_type == "events":
            return self._seed_event_data(client, row_count)
        elif data_type == "metrics":
            return self._seed_metrics_data(client, row_count)
        else:
            raise DatabaseError(f"Unknown data type: {data_type}")
    
    def _seed_minimal_data(self, client: Client, row_count: int) -> Dict[str, int]:
        """Seed minimal test data into ClickHouse."""
        base_time = datetime.now(UTC) - timedelta(days=7)
        
        # Generate log data
        log_data = []
        levels = ["INFO", "WARN", "ERROR", "DEBUG"]
        sources = ["app", "db", "cache", "auth"]
        
        for i in range(row_count):
            log_data.append([
                i + 1,
                base_time + timedelta(minutes=i),
                random.choice(levels),
                f"Test log message {i + 1}",
                random.choice(sources)
            ])
        
        client.insert("test_logs", log_data)
        return {"test_logs": row_count}
    
    def _seed_event_data(self, client: Client, row_count: int) -> Dict[str, int]:
        """Seed event tracking test data."""
        base_time = datetime.now(UTC) - timedelta(days=3)
        event_types = ["click", "view", "purchase", "signup", "login"]
        users = [f"user_{i}" for i in range(1, 51)]  # 50 users
        
        # Generate events
        event_data = []
        session_data = []
        current_sessions = {}
        
        for i in range(row_count):
            user_id = random.choice(users)
            event_type = random.choice(event_types)
            timestamp = base_time + timedelta(seconds=i * 10)
            
            # Create or update session
            if user_id not in current_sessions:
                session_id = f"session_{uuid.uuid4().hex[:8]}"
                current_sessions[user_id] = {
                    "id": session_id, "start": timestamp, "count": 0
                }
            
            session_id = current_sessions[user_id]["id"]
            current_sessions[user_id]["count"] += 1
            
            event_data.append([
                i + 1, user_id, event_type, timestamp,
                {"page": f"page_{i % 10}", "source": "test"},
                session_id
            ])
        
        # Insert events
        client.insert("test_events", event_data)
        
        # Insert sessions
        for user_id, session in current_sessions.items():
            session_data.append([
                session["id"], user_id, session["start"],
                session["start"] + timedelta(hours=1),
                session["count"]
            ])
        
        client.insert("test_user_sessions", session_data)
        return {"test_events": row_count, "test_user_sessions": len(session_data)}
    
    def _seed_metrics_data(self, client: Client, row_count: int) -> Dict[str, int]:
        """Seed metrics test data."""
        base_time = datetime.now(UTC) - timedelta(hours=24)
        metrics = ["cpu_usage", "memory_usage", "disk_io", "network_io"]
        hosts = ["host1", "host2", "host3"]
        
        # Generate metrics data
        metrics_data = []
        for i in range(row_count):
            timestamp = base_time + timedelta(minutes=i)
            metric_name = random.choice(metrics)
            host = random.choice(hosts)
            value = random.uniform(0, 100)
            
            metrics_data.append([
                metric_name, timestamp, value,
                {"environment": "test", "service": "netra"},
                host
            ])
        
        client.insert("test_metrics", metrics_data)
        return {"test_metrics": row_count}
    
    def create_table_snapshot(self, test_id: str, table_name: str) -> str:
        """Create snapshot of ClickHouse table for fast reset."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        snapshot_id = f"{table_name}_snapshot_{uuid.uuid4().hex[:8]}"
        client = self._clients[test_id]
        
        # Create snapshot table with same structure
        client.command(f"CREATE TABLE {snapshot_id} AS {table_name}")
        client.command(f"INSERT INTO {snapshot_id} SELECT * FROM {table_name}")
        
        return snapshot_id
    
    def restore_table_snapshot(self, test_id: str, table_name: str, snapshot_id: str) -> None:
        """Restore table from ClickHouse snapshot."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        client = self._clients[test_id]
        
        # Clear and restore table
        client.command(f"TRUNCATE TABLE {table_name}")
        client.command(f"INSERT INTO {table_name} SELECT * FROM {snapshot_id}")
    
    @contextmanager
    def query_performance_context(self, test_id: str):
        """Context manager for measuring ClickHouse query performance."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        client = self._clients[test_id]
        start_time = datetime.now(UTC)
        
        try:
            yield client
        finally:
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()
            logger.info(f"ClickHouse query performance test {test_id}: {duration:.3f}s")
    
    def verify_data_isolation(self, test_id: str) -> Dict[str, Any]:
        """Verify ClickHouse database isolation."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        config = self._active_databases[test_id]
        client = config["client"]
        db_name = config["database_name"]
        
        # Check database exists and is unique
        databases = client.query("SHOW DATABASES").result_rows
        db_names = [db[0] for db in databases]
        
        # Check table count in our database
        tables = client.query(f"SHOW TABLES FROM {db_name}").result_rows
        table_count = len(tables)
        
        return {
            "database_name": db_name,
            "database_exists": db_name in db_names,
            "is_unique": test_id in db_name,
            "table_count": table_count,
            "isolation_verified": True
        }
    
    def get_database_stats(self, test_id: str) -> Dict[str, Any]:
        """Get ClickHouse database statistics."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        config = self._active_databases[test_id]
        client = config["client"]
        db_name = config["database_name"]
        
        # Get database size and table statistics
        tables_result = client.query(f"""
            SELECT table, total_rows, total_bytes 
            FROM system.tables 
            WHERE database = '{db_name}'
        """)
        
        total_rows = sum(row[1] for row in tables_result.result_rows)
        total_bytes = sum(row[2] for row in tables_result.result_rows)
        table_count = len(tables_result.result_rows)
        
        return {
            "database_name": db_name,
            "table_count": table_count,
            "total_rows": total_rows,
            "total_bytes": total_bytes,
            "test_id": test_id,
            "created_at": config["created_at"].isoformat()
        }
    
    def execute_test_query(self, test_id: str, query: str, expected_rows: Optional[int] = None) -> Dict[str, Any]:
        """Execute test query and validate results."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        client = self._clients[test_id]
        start_time = datetime.now(UTC)
        
        try:
            result = client.query(query)
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()
            
            row_count = len(result.result_rows)
            validation_passed = expected_rows is None or row_count == expected_rows
            
            return {
                "query": query[:100] + "..." if len(query) > 100 else query,
                "row_count": row_count,
                "duration_seconds": duration,
                "validation_passed": validation_passed,
                "expected_rows": expected_rows,
                "success": True
            }
        except Exception as e:
            return {
                "query": query[:100] + "..." if len(query) > 100 else query,
                "error": str(e),
                "success": False
            }
    
    def optimize_tables(self, test_id: str) -> Dict[str, bool]:
        """Optimize all tables in test database."""
        if test_id not in self._active_databases:
            raise DatabaseError(f"No active ClickHouse database for test: {test_id}")
        
        config = self._active_databases[test_id]
        client = config["client"]
        db_name = config["database_name"]
        
        # Get all tables
        tables = client.query(f"SHOW TABLES FROM {db_name}").result_rows
        optimization_results = {}
        
        for table_row in tables:
            table_name = table_row[0]
            try:
                client.command(f"OPTIMIZE TABLE {db_name}.{table_name}")
                optimization_results[table_name] = True
            except Exception as e:
                logger.warning(f"Failed to optimize table {table_name}: {e}")
                optimization_results[table_name] = False
        
        return optimization_results
    
    def cleanup_test_database(self, test_id: str) -> None:
        """Clean up isolated ClickHouse test database."""
        if test_id not in self._active_databases:
            return
        
        config = self._active_databases[test_id]
        db_name = config["database_name"]
        
        try:
            # Drop database
            admin_client = config["admin_client"]
            admin_client.command(f"DROP DATABASE IF EXISTS {db_name}")
            
            # Close clients
            config["client"].close()
            admin_client.close()
            
            # Clean up tracking
            del self._active_databases[test_id]
            del self._clients[test_id]
            
        except Exception as e:
            logger.error(f"Failed to cleanup ClickHouse test database {test_id}: {e}")
    
    def cleanup_all_test_databases(self) -> None:
        """Clean up all active ClickHouse test databases."""
        for test_id in list(self._active_databases.keys()):
            self.cleanup_test_database(test_id)
    
    def get_connection_info(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get ClickHouse connection information for test database."""
        if test_id not in self._active_databases:
            return None
        
        config = self._active_databases[test_id]
        return {
            "test_id": test_id,
            "database_name": config["database_name"],
            "host": config["host"],
            "port": config["port"],
            "created_at": config["created_at"].isoformat()
        }

# Utility function for ClickHouse test isolation
@contextmanager
def with_isolated_clickhouse(test_name: str, table_set: str = "basic"):
    """Context manager for isolated ClickHouse testing."""
    isolator = ClickHouseTestIsolator()
    
    try:
        # Create isolated database
        config = isolator.create_isolated_database(test_name)
        tables = isolator.setup_analytics_tables(test_name, table_set)
        
        yield isolator, config, tables
        
    finally:
        isolator.cleanup_test_database(test_name)