"""
CRITICAL: ClickHouse Table Initializer
This module ensures all required ClickHouse tables are created during startup.
Based on Five Whys root cause analysis - tables are MANDATORY for core business functionality.
"""

import logging
from typing import Dict, List, Any
from clickhouse_driver import Client
from clickhouse_driver.errors import ServerException, ErrorCodes

logger = logging.getLogger(__name__)

class ClickHouseTableInitializer:
    """Initialize all required ClickHouse tables with fail-fast behavior."""
    
    # CRITICAL: These tables are required for core business functionality
    REQUIRED_TABLES = {
        'netra_analytics': {
            'workload_events': """
                CREATE TABLE IF NOT EXISTS workload_events (
                    event_id UUID DEFAULT generateUUIDv4(),
                    timestamp DateTime64(3) DEFAULT now(),
                    user_id UInt32,
                    workload_id String,
                    event_type String,
                    event_category String,
                    metrics Nested(
                        name String,
                        value Float64,
                        unit String
                    ),
                    dimensions Map(String, String),
                    metadata String,
                    INDEX idx_user_id user_id TYPE minmax GRANULARITY 8192,
                    INDEX idx_workload_id workload_id TYPE bloom_filter GRANULARITY 1,
                    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1
                ) ENGINE = MergeTree()
                ORDER BY (user_id, workload_id, timestamp)
                PARTITION BY toYYYYMM(timestamp)
                SETTINGS index_granularity = 8192
            """,
            'performance_metrics': """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id UUID DEFAULT generateUUIDv4(),
                    timestamp DateTime64(3) DEFAULT now(),
                    metric_name String,
                    metric_value Float64,
                    metric_unit String,
                    dimensions Map(String, String)
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, metric_name)
                SETTINGS index_granularity = 8192
            """,
            'events': """
                CREATE TABLE IF NOT EXISTS events (
                    event_id UUID DEFAULT generateUUIDv4(),
                    timestamp DateTime64(3) DEFAULT now(),
                    event_type String,
                    event_data String
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, event_type)
                SETTINGS index_granularity = 8192
            """,
            'system_health_metrics': """
                CREATE TABLE IF NOT EXISTS system_health_metrics (
                    timestamp DateTime64(3) DEFAULT now(),
                    component String,
                    status String,
                    latency_ms Float64,
                    error_count UInt32
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, component)
                SETTINGS index_granularity = 8192
            """,
            'error_analytics': """
                CREATE TABLE IF NOT EXISTS error_analytics (
                    timestamp DateTime64(3) DEFAULT now(),
                    error_type String,
                    error_message String,
                    stack_trace String,
                    service_name String
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, error_type)
                SETTINGS index_granularity = 8192
            """
        }
    }
    
    def __init__(self, host: str, port: int = 9000, user: str = 'default', password: str = ''):
        """Initialize with ClickHouse connection parameters."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.client = None
        
    def connect(self) -> Client:
        """Establish connection to ClickHouse."""
        if not self.client:
            self.client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password
            )
        return self.client
        
    def initialize_tables(self) -> Dict[str, Any]:
        """
        Initialize all required tables with fail-fast behavior.
        
        Returns:
            Dict with status, created tables, and any errors
        """
        result = {
            'success': False,
            'databases_checked': [],
            'tables_created': [],
            'tables_verified': [],
            'errors': []
        }
        
        try:
            client = self.connect()
            
            for database, tables in self.REQUIRED_TABLES.items():
                # Ensure database exists
                logger.info(f" SEARCH:  Checking database: {database}")
                try:
                    client.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
                    result['databases_checked'].append(database)
                except Exception as e:
                    error_msg = f"Failed to create database {database}: {e}"
                    logger.error(f" FAIL:  {error_msg}")
                    result['errors'].append(error_msg)
                    continue
                
                # Create each table
                for table_name, schema in tables.items():
                    try:
                        logger.info(f"[U+1F4CB] Creating table: {database}.{table_name}")
                        client.execute(f"USE {database}")
                        client.execute(schema)
                        result['tables_created'].append(f"{database}.{table_name}")
                        
                        # Verify table exists
                        tables_in_db = client.execute(f"SHOW TABLES FROM {database}")
                        if any(table_name in str(row) for row in tables_in_db):
                            result['tables_verified'].append(f"{database}.{table_name}")
                            logger.info(f" PASS:  Table verified: {database}.{table_name}")
                        else:
                            error_msg = f"Table {database}.{table_name} not found after creation"
                            logger.error(f" FAIL:  {error_msg}")
                            result['errors'].append(error_msg)
                            
                    except ServerException as e:
                        if e.code == ErrorCodes.TABLE_ALREADY_EXISTS:
                            logger.info(f"[U+2713] Table already exists: {database}.{table_name}")
                            result['tables_verified'].append(f"{database}.{table_name}")
                        else:
                            error_msg = f"Failed to create table {database}.{table_name}: {e}"
                            logger.error(f" FAIL:  {error_msg}")
                            result['errors'].append(error_msg)
                    except Exception as e:
                        error_msg = f"Unexpected error creating table {database}.{table_name}: {e}"
                        logger.error(f" FAIL:  {error_msg}")
                        result['errors'].append(error_msg)
            
            # Determine overall success
            expected_tables = sum(len(tables) for tables in self.REQUIRED_TABLES.values())
            result['success'] = len(result['tables_verified']) == expected_tables
            
            if result['success']:
                logger.info(f" PASS:  All {expected_tables} required tables verified")
            else:
                logger.error(f" WARNING: [U+FE0F] Only {len(result['tables_verified'])}/{expected_tables} tables verified")
                
        except Exception as e:
            error_msg = f"Critical error during table initialization: {e}"
            logger.error(f"[U+1F534] {error_msg}")
            result['errors'].append(error_msg)
        finally:
            if self.client:
                self.client.disconnect()
                
        return result
    
    def verify_critical_tables(self) -> bool:
        """
        Verify all critical tables exist and are accessible.
        
        Returns:
            True if all tables exist and are accessible, False otherwise
        """
        try:
            client = self.connect()
            
            for database, tables in self.REQUIRED_TABLES.items():
                # Check database exists
                databases = client.execute("SHOW DATABASES")
                if not any(database in str(row) for row in databases):
                    logger.error(f" FAIL:  Database {database} does not exist")
                    return False
                
                # Check each table
                for table_name in tables:
                    try:
                        # Try to select from table
                        client.execute(f"SELECT 1 FROM {database}.{table_name} LIMIT 1")
                        logger.debug(f"[U+2713] Table accessible: {database}.{table_name}")
                    except ServerException as e:
                        if e.code == ErrorCodes.UNKNOWN_TABLE:
                            logger.error(f" FAIL:  Table does not exist: {database}.{table_name}")
                            return False
                        elif e.code == ErrorCodes.UNKNOWN_DATABASE:
                            logger.error(f" FAIL:  Database does not exist: {database}")
                            return False
                        else:
                            # Table exists but might be empty - that's OK
                            logger.debug(f"[U+2713] Table exists (empty): {database}.{table_name}")
                            
            logger.info(" PASS:  All critical tables verified")
            return True
            
        except Exception as e:
            logger.error(f" FAIL:  Error verifying tables: {e}")
            return False
        finally:
            if self.client:
                self.client.disconnect()


def ensure_clickhouse_tables(host: str = 'dev-clickhouse', 
                            port: int = 9000,
                            user: str = 'netra',
                            password: str = '',
                            fail_fast: bool = True) -> bool:
    """
    Ensure all ClickHouse tables are initialized.
    
    Args:
        host: ClickHouse host
        port: ClickHouse port
        user: ClickHouse user
        password: ClickHouse password
        fail_fast: If True, raise exception on failure
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        RuntimeError: If fail_fast=True and initialization fails
    """
    logger.info("[U+1F680] Starting ClickHouse table initialization")
    
    initializer = ClickHouseTableInitializer(host, port, user, password)
    
    # Initialize tables
    result = initializer.initialize_tables()
    
    if not result['success']:
        error_msg = f"ClickHouse table initialization failed: {result['errors']}"
        logger.error(f"[U+1F534] {error_msg}")
        
        if fail_fast:
            # CRITICAL: Fail fast for production to prevent silent failures
            raise RuntimeError(error_msg)
        return False
    
    # Verify tables
    if not initializer.verify_critical_tables():
        error_msg = "ClickHouse table verification failed"
        logger.error(f"[U+1F534] {error_msg}")
        
        if fail_fast:
            raise RuntimeError(error_msg)
        return False
    
    logger.info(" PASS:  ClickHouse table initialization complete")
    return True