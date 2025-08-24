from dev_launcher.isolated_environment import get_env
"""
Database Initializer with Auto-Creation, Migration, and Recovery

Handles database initialization including table creation, schema versioning,
connection pool management, and authentication recovery.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability & Data Integrity
- Value Impact: Prevents data loss and ensures consistent database state
- Revenue Impact: Critical for all data-dependent operations
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import subprocess
import json

import asyncpg
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import redis.asyncio as redis
from clickhouse_driver import Client as ClickHouseClient

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """Supported database types"""
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    REDIS = "redis"


class SchemaStatus(Enum):
    """Database schema status"""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    UP_TO_DATE = "up_to_date"
    NEEDS_MIGRATION = "needs_migration"
    CORRUPTED = "corrupted"
    ERROR = "error"


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    type: DatabaseType
    host: str
    port: int
    database: str
    user: str
    password: str
    min_pool_size: int = 5
    max_pool_size: int = 20
    connection_timeout: float = 10.0
    query_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class SchemaVersion:
    """Database schema version information"""
    current_version: str
    required_version: str
    migrations_pending: List[str]
    last_migration: Optional[str]
    status: SchemaStatus


class DatabaseInitializer:
    """
    Manages database initialization, migration, and health monitoring
    """
    
    def __init__(self):
        self.configs: Dict[DatabaseType, DatabaseConfig] = {}
        self.pools: Dict[DatabaseType, Any] = {}
        self.schema_versions: Dict[DatabaseType, SchemaVersion] = {}
        self.circuit_breakers: Dict[DatabaseType, Dict] = {}
        self._lock_timeout = 5.0
        self._migration_lock_acquired = False
        
    def add_database(self, config: DatabaseConfig) -> None:
        """Register a database for initialization"""
        self.configs[config.type] = config
        self.circuit_breakers[config.type] = {
            "failures": 0,
            "threshold": 3,
            "is_open": False,
            "last_failure": None,
            "recovery_timeout": 30.0
        }
        logger.info(f"Registered database: {config.type.value} at {config.host}:{config.port}")
    
    async def _check_circuit_breaker(self, db_type: DatabaseType) -> bool:
        """Check if database connection is allowed by circuit breaker"""
        cb = self.circuit_breakers.get(db_type, {})
        
        if cb.get("is_open", False):
            last_failure = cb.get("last_failure")
            if last_failure:
                elapsed = time.time() - last_failure
                if elapsed >= cb.get("recovery_timeout", 30.0):
                    logger.info(f"Circuit breaker recovering for {db_type.value}")
                    cb["is_open"] = False
                    cb["failures"] = 0
                    return True
            return False
        return True
    
    def _trip_circuit_breaker(self, db_type: DatabaseType) -> None:
        """Trip circuit breaker after repeated failures"""
        cb = self.circuit_breakers.get(db_type, {})
        cb["failures"] = cb.get("failures", 0) + 1
        cb["last_failure"] = time.time()
        
        if cb["failures"] >= cb.get("threshold", 3):
            cb["is_open"] = True
            logger.error(f"Circuit breaker tripped for {db_type.value}")
    
    async def _create_postgresql_database(self, config: DatabaseConfig) -> bool:
        """Create PostgreSQL database if it doesn't exist"""
        try:
            # Connect to default postgres database to create target database
            conn = psycopg2.connect(
                host=config.host,
                port=config.port,
                database="postgres",
                user=config.user,
                password=config.password,
                connect_timeout=int(config.connection_timeout)
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (config.database,)
            )
            
            if not cursor.fetchone():
                logger.info(f"Creating PostgreSQL database: {config.database}")
                cursor.execute(f'CREATE DATABASE "{config.database}"')
                logger.info(f"Created database: {config.database}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creating PostgreSQL database: {e}")
            return False
    
    async def _initialize_postgresql_schema(self, config: DatabaseConfig) -> bool:
        """Initialize PostgreSQL schema and tables"""
        try:
            # First ensure database exists
            if not await self._create_postgresql_database(config):
                return False
            
            # Connect to target database
            conn = await asyncpg.connect(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password,
                timeout=config.connection_timeout
            )
            
            # Check for schema version table
            schema_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'schema_version'
                )
            """)
            
            if not schema_exists:
                logger.info("Creating schema version table")
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version VARCHAR(50) PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """)
                
                # Run initialization scripts if they exist
                init_script = Path("database_scripts/postgres_init.sql")
                if init_script.exists():
                    logger.info("Running PostgreSQL initialization script")
                    sql_content = init_script.read_text()
                    await conn.execute(sql_content)
                else:
                    # Create basic tables if no script exists
                    await self._create_default_postgresql_tables(conn)
            
            # Record current version
            current_version = await conn.fetchval(
                "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
            )
            
            self.schema_versions[DatabaseType.POSTGRESQL] = SchemaVersion(
                current_version=current_version or "0.0.0",
                required_version="1.0.0",  # Should come from config
                migrations_pending=[],
                last_migration=current_version,
                status=SchemaStatus.UP_TO_DATE
            )
            
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL schema initialization failed: {e}")
            self._trip_circuit_breaker(DatabaseType.POSTGRESQL)
            return False
    
    async def _create_default_postgresql_tables(self, conn) -> None:
        """Create default PostgreSQL tables for the application"""
        default_tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                key_hash VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
            """
        ]
        
        for table_sql in default_tables:
            await conn.execute(table_sql)
        
        logger.info("Created default PostgreSQL tables")
    
    async def _initialize_clickhouse_schema(self, config: DatabaseConfig) -> bool:
        """Initialize ClickHouse schema and tables"""
        try:
            client = ClickHouseClient(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password,
                connect_timeout=config.connection_timeout
            )
            
            # Create database if it doesn't exist
            client.execute(f"CREATE DATABASE IF NOT EXISTS {config.database}")
            
            # Switch to target database
            client = ClickHouseClient(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password
            )
            
            # Create schema version table
            client.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version String,
                    applied_at DateTime DEFAULT now(),
                    description String
                ) ENGINE = MergeTree()
                ORDER BY applied_at
            """)
            
            # Create default tables
            default_tables = [
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id UUID,
                    event_type String,
                    timestamp DateTime,
                    user_id Nullable(UUID),
                    data String,
                    INDEX idx_event_type event_type TYPE minmax GRANULARITY 4,
                    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 4
                ) ENGINE = MergeTree()
                PARTITION BY toYYYYMM(timestamp)
                ORDER BY (timestamp, event_id)
                """,
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    metric_name String,
                    timestamp DateTime,
                    value Float64,
                    tags Nested(
                        key String,
                        value String
                    )
                ) ENGINE = MergeTree()
                PARTITION BY toYYYYMM(timestamp)
                ORDER BY (metric_name, timestamp)
                """
            ]
            
            for table_sql in default_tables:
                client.execute(table_sql)
            
            self.schema_versions[DatabaseType.CLICKHOUSE] = SchemaVersion(
                current_version="1.0.0",
                required_version="1.0.0",
                migrations_pending=[],
                last_migration="1.0.0",
                status=SchemaStatus.UP_TO_DATE
            )
            
            client.disconnect()
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse schema initialization failed: {e}")
            self._trip_circuit_breaker(DatabaseType.CLICKHOUSE)
            return False
    
    async def _initialize_redis(self, config: DatabaseConfig) -> bool:
        """Initialize Redis connection and test basic operations"""
        try:
            client = redis.Redis(
                host=config.host,
                port=config.port,
                password=config.password if config.password else None,
                decode_responses=True,
                socket_connect_timeout=config.connection_timeout,
                socket_timeout=config.query_timeout
            )
            
            # Test connection
            await client.ping()
            
            # Set initialization marker
            await client.set("system:initialized", "true", ex=3600)
            
            # Create default keys/structures if needed
            await client.hset("system:config", "version", "1.0.0")
            await client.hset("system:config", "initialized_at", str(time.time()))
            
            await client.close()
            
            self.schema_versions[DatabaseType.REDIS] = SchemaVersion(
                current_version="1.0.0",
                required_version="1.0.0",
                migrations_pending=[],
                last_migration=None,
                status=SchemaStatus.UP_TO_DATE
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Redis initialization failed: {e}")
            self._trip_circuit_breaker(DatabaseType.REDIS)
            return False
    
    async def _acquire_migration_lock(self, db_type: DatabaseType) -> bool:
        """Acquire distributed lock for migrations to prevent concurrent execution"""
        if db_type == DatabaseType.POSTGRESQL:
            config = self.configs[db_type]
            try:
                conn = await asyncpg.connect(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    user=config.user,
                    password=config.password,
                    timeout=config.connection_timeout
                )
                
                # Try to acquire advisory lock (non-blocking)
                lock_acquired = await conn.fetchval(
                    "SELECT pg_try_advisory_lock(12345)"  # Magic number for migration lock
                )
                
                if lock_acquired:
                    self._migration_lock_acquired = True
                    logger.info("Acquired migration lock")
                    return True
                else:
                    logger.warning("Could not acquire migration lock, another process may be migrating")
                    return False
                    
            except Exception as e:
                logger.error(f"Error acquiring migration lock: {e}")
                return False
        
        return True  # Other databases don't need locking for now
    
    async def _release_migration_lock(self, db_type: DatabaseType) -> None:
        """Release migration lock"""
        if db_type == DatabaseType.POSTGRESQL and self._migration_lock_acquired:
            config = self.configs[db_type]
            try:
                conn = await asyncpg.connect(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    user=config.user,
                    password=config.password,
                    timeout=config.connection_timeout
                )
                
                await conn.execute("SELECT pg_advisory_unlock(12345)")
                self._migration_lock_acquired = False
                logger.info("Released migration lock")
                await conn.close()
                
            except Exception as e:
                logger.error(f"Error releasing migration lock: {e}")
    
    async def initialize_database(self, db_type: DatabaseType) -> bool:
        """Initialize a specific database with retry logic"""
        if db_type not in self.configs:
            logger.error(f"No configuration for database type: {db_type.value}")
            return False
        
        if not await self._check_circuit_breaker(db_type):
            logger.warning(f"Circuit breaker open for {db_type.value}, skipping initialization")
            return False
        
        config = self.configs[db_type]
        
        for attempt in range(config.max_retries):
            try:
                logger.info(f"Initializing {db_type.value} (attempt {attempt + 1}/{config.max_retries})")
                
                # Acquire migration lock if needed
                if not await self._acquire_migration_lock(db_type):
                    await asyncio.sleep(config.retry_delay * (2 ** attempt))
                    continue
                
                # Initialize based on database type
                success = False
                if db_type == DatabaseType.POSTGRESQL:
                    success = await self._initialize_postgresql_schema(config)
                elif db_type == DatabaseType.CLICKHOUSE:
                    success = await self._initialize_clickhouse_schema(config)
                elif db_type == DatabaseType.REDIS:
                    success = await self._initialize_redis(config)
                
                # Release lock
                await self._release_migration_lock(db_type)
                
                if success:
                    logger.info(f"Successfully initialized {db_type.value}")
                    return True
                
            except Exception as e:
                logger.error(f"Error initializing {db_type.value}: {e}")
                await self._release_migration_lock(db_type)
            
            # Exponential backoff
            if attempt < config.max_retries - 1:
                delay = min(config.retry_delay * (2 ** attempt), 30.0)
                logger.info(f"Retrying {db_type.value} initialization in {delay:.1f}s")
                await asyncio.sleep(delay)
        
        self._trip_circuit_breaker(db_type)
        return False
    
    async def initialize_postgresql(self) -> bool:
        """Initialize PostgreSQL database with auto-configuration from environment
        
        Convenience method that configures PostgreSQL from environment variables
        and initializes it. Used by startup manager for backwards compatibility.
        """
        try:
            # Auto-configure PostgreSQL from environment if not already configured
            if DatabaseType.POSTGRESQL not in self.configs:
                await self._configure_postgresql_from_environment()
            
            # Initialize PostgreSQL database
            return await self.initialize_database(DatabaseType.POSTGRESQL)
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            return False
    
    async def _configure_postgresql_from_environment(self) -> None:
        """Configure PostgreSQL from environment variables"""
        import os
        from urllib.parse import urlparse
        
        # Get database URL from environment
        database_url = get_env().get("DATABASE_URL")
        if not database_url:
            # Use default development settings
            config = DatabaseConfig(
                type=DatabaseType.POSTGRESQL,
                host="localhost",
                port=5432,
                database="netra",
                user="postgres",
                password="postgres"
            )
        else:
            # Parse the DATABASE_URL
            parsed = urlparse(database_url)
            config = DatabaseConfig(
                type=DatabaseType.POSTGRESQL,
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                database=parsed.path.lstrip("/") if parsed.path else "netra",
                user=parsed.username or "postgres",
                password=parsed.password or "postgres"
            )
        
        self.add_database(config)
        logger.info(f"Auto-configured PostgreSQL: {config.host}:{config.port}/{config.database}")

    async def initialize_all(self) -> Dict[DatabaseType, bool]:
        """Initialize all registered databases"""
        results = {}
        
        # Initialize databases in order of importance
        priority_order = [
            DatabaseType.POSTGRESQL,  # Most critical
            DatabaseType.REDIS,       # Cache layer
            DatabaseType.CLICKHOUSE   # Analytics
        ]
        
        for db_type in priority_order:
            if db_type in self.configs:
                results[db_type] = await self.initialize_database(db_type)
        
        return results
    
    async def create_connection_pool(self, db_type: DatabaseType) -> Any:
        """Create connection pool for a database"""
        if db_type not in self.configs:
            raise ValueError(f"No configuration for database type: {db_type.value}")
        
        config = self.configs[db_type]
        
        if db_type == DatabaseType.POSTGRESQL:
            pool = await asyncpg.create_pool(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password,
                min_size=config.min_pool_size,
                max_size=config.max_pool_size,
                timeout=config.connection_timeout,
                command_timeout=config.query_timeout
            )
            self.pools[db_type] = pool
            return pool
            
        elif db_type == DatabaseType.REDIS:
            pool = redis.ConnectionPool(
                host=config.host,
                port=config.port,
                password=config.password if config.password else None,
                max_connections=config.max_pool_size,
                socket_connect_timeout=config.connection_timeout,
                decode_responses=True
            )
            self.pools[db_type] = pool
            return pool
        
        return None
    
    async def health_check(self, db_type: DatabaseType) -> Tuple[bool, Dict[str, Any]]:
        """Check health of a specific database"""
        if db_type not in self.configs:
            return False, {"error": "Not configured"}
        
        config = self.configs[db_type]
        details = {
            "type": db_type.value,
            "host": config.host,
            "port": config.port,
            "database": config.database
        }
        
        try:
            if db_type == DatabaseType.POSTGRESQL:
                conn = await asyncpg.connect(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    user=config.user,
                    password=config.password,
                    timeout=5.0
                )
                version = await conn.fetchval("SELECT version()")
                await conn.close()
                details["version"] = version
                return True, details
                
            elif db_type == DatabaseType.REDIS:
                client = redis.Redis(
                    host=config.host,
                    port=config.port,
                    password=config.password if config.password else None,
                    socket_connect_timeout=5.0
                )
                info = await client.info()
                await client.close()
                details["version"] = info.get("redis_version")
                return True, details
                
            elif db_type == DatabaseType.CLICKHOUSE:
                client = ClickHouseClient(
                    host=config.host,
                    port=config.port,
                    connect_timeout=5.0
                )
                version = client.execute("SELECT version()")[0][0]
                client.disconnect()
                details["version"] = version
                return True, details
                
        except Exception as e:
            details["error"] = str(e)
            return False, details
        
        return False, details
    
    async def cleanup(self) -> None:
        """Clean up all database connections and pools"""
        for db_type, pool in self.pools.items():
            try:
                if db_type == DatabaseType.POSTGRESQL and pool:
                    await pool.close()
                elif db_type == DatabaseType.REDIS and pool:
                    pool.disconnect()
                logger.info(f"Closed connection pool for {db_type.value}")
            except Exception as e:
                logger.error(f"Error closing pool for {db_type.value}: {e}")
        
        self.pools.clear()


# Global instance
db_initializer = DatabaseInitializer()


async def initialize_databases() -> Dict[DatabaseType, bool]:
    """Initialize all databases"""
    return await db_initializer.initialize_all()


async def get_database_health() -> Dict[DatabaseType, Tuple[bool, Dict]]:
    """Get health status of all databases"""
    results = {}
    for db_type in DatabaseType:
        if db_type in db_initializer.configs:
            results[db_type] = await db_initializer.health_check(db_type)
    return results