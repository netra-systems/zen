#!/usr/bin/env python3
"""
NetraOptimizer Database Setup Script

Creates the database schema for the NetraOptimizer system.
This is our single source of truth for all performance data.
"""

import sys
import os
import logging
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env file if it exists
env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# Check if we should use CloudSQL configuration
use_cloud_sql = os.environ.get("USE_CLOUD_SQL", "").lower() == "true"
environment = os.environ.get("ENVIRONMENT", "development").lower()

if use_cloud_sql or environment in ["staging", "production"]:
    # Use CloudSQL configuration
    from netraoptimizer.cloud_config import cloud_config
    config = cloud_config
else:
    # Use local configuration
    from netraoptimizer.config import NetraOptimizerConfig
    config = NetraOptimizerConfig()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Database schema - Single Source of Truth
COMMAND_EXECUTIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS command_executions (
    -- Identity
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    batch_id UUID,
    execution_sequence INTEGER,

    -- Command Information
    command_raw TEXT NOT NULL,
    command_base VARCHAR(100) NOT NULL,
    command_args JSONB,
    command_features JSONB,

    -- Context
    workspace_context JSONB,
    session_context JSONB,

    -- Token Metrics
    total_tokens INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    fresh_tokens INTEGER DEFAULT 0,
    cache_hit_rate FLOAT DEFAULT 0.0,

    -- Performance Metrics
    execution_time_ms INTEGER DEFAULT 0,
    tool_calls INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,

    -- Cost Metrics
    cost_usd DECIMAL(10,6) DEFAULT 0.0,
    fresh_cost_usd DECIMAL(10,6) DEFAULT 0.0,
    cache_savings_usd DECIMAL(10,6) DEFAULT 0.0,

    -- Output Characteristics
    output_characteristics JSONB,

    -- Model Configuration
    model_version VARCHAR(50) DEFAULT 'claude-code',

    -- Indexes for common queries
    CONSTRAINT status_check CHECK (status IN ('pending', 'completed', 'failed', 'timeout'))
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_timestamp ON command_executions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_batch_id ON command_executions(batch_id);
CREATE INDEX IF NOT EXISTS idx_command_base ON command_executions(command_base);
CREATE INDEX IF NOT EXISTS idx_status ON command_executions(status);
CREATE INDEX IF NOT EXISTS idx_command_args_gin ON command_executions USING GIN(command_args);
CREATE INDEX IF NOT EXISTS idx_command_features_gin ON command_executions USING GIN(command_features);
"""

COMMAND_PATTERNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS command_patterns (
    id SERIAL PRIMARY KEY,
    pattern_signature VARCHAR(500) UNIQUE NOT NULL,
    command_base VARCHAR(100) NOT NULL,

    -- Statistics
    statistics_30d JSONB,
    token_drivers JSONB,
    cache_patterns JSONB,

    -- Optimization
    optimization_insights JSONB,
    failure_patterns JSONB,

    -- Metadata
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    sample_size INTEGER DEFAULT 0,

    -- Indexes
    CONSTRAINT unique_pattern UNIQUE(pattern_signature)
);

CREATE INDEX IF NOT EXISTS idx_pattern_command_base ON command_patterns(command_base);
CREATE INDEX IF NOT EXISTS idx_pattern_updated ON command_patterns(last_updated DESC);
"""


def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    try:
        # Get database configuration
        if hasattr(config, 'get_database_config'):
            # CloudSQL configuration
            db_config = config.get_database_config()
            # For CloudSQL, we need to handle the connection differently
            if db_config.get('is_cloud_sql'):
                # CloudSQL Unix socket connection
                conn = psycopg2.connect(
                    host=db_config['socket_path'],
                    user=db_config['user'],
                    password=db_config.get('password', ''),
                    database='postgres'  # Connect to default database
                )
            else:
                # Regular TCP connection
                conn = psycopg2.connect(
                    host=db_config['host'],
                    port=db_config['port'],
                    user=db_config['user'],
                    password=db_config.get('password', ''),
                    database='postgres'  # Connect to default database
                )
            db_name = db_config['database']
        else:
            # Local configuration
            conn = psycopg2.connect(
                host=config.db_host,
                port=config.db_port,
                user=config.db_user,
                password=config.db_password,
                database='postgres'  # Connect to default database
            )
            db_name = config.db_name

        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f"CREATE DATABASE {db_name}")
            logger.info(f"Created database: {db_name}")
        else:
            logger.info(f"Database already exists: {db_name}")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logger.error(f"Error creating database: {e}")
        return False


def setup_schema():
    """Create the database tables and indexes."""
    try:
        # Get the database URL
        if hasattr(config, 'get_database_url'):
            # CloudSQL configuration
            database_url = config.get_database_url(sync=True)
        else:
            # Local configuration
            database_url = config.sync_database_url

        # Connect to the specific database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Create command_executions table
        logger.info("Creating command_executions table...")
        cursor.execute(COMMAND_EXECUTIONS_SCHEMA)

        # Create command_patterns table
        logger.info("Creating command_patterns table...")
        cursor.execute(COMMAND_PATTERNS_SCHEMA)

        # Commit changes
        conn.commit()
        logger.info("Database schema created successfully!")

        # Show table info
        cursor.execute("""
            SELECT table_name, pg_size_pretty(pg_total_relation_size(table_name::regclass)) as size
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)

        tables = cursor.fetchall()
        logger.info("Database tables:")
        for table, size in tables:
            logger.info(f"  - {table}: {size}")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logger.error(f"Error setting up schema: {e}")
        return False


def main():
    """Main setup function."""
    logger.info("NetraOptimizer Database Setup")
    logger.info("-" * 40)

    # Display configuration info
    if hasattr(config, 'get_database_config'):
        # CloudSQL configuration
        db_config = config.get_database_config()
        if db_config.get('is_cloud_sql'):
            logger.info(f"Type: CloudSQL")
            logger.info(f"Socket: {db_config['socket_path']}")
        else:
            logger.info(f"Type: TCP Connection")
            logger.info(f"Host: {db_config['host']}:{db_config['port']}")
        logger.info(f"Database: {db_config['database']}")
        logger.info(f"User: {db_config['user']}")
        logger.info(f"Environment: {config.environment}")
    else:
        # Local configuration
        logger.info(f"Type: Local Configuration")
        logger.info(f"Host: {config.db_host}:{config.db_port}")
        logger.info(f"Database: {config.db_name}")
        logger.info(f"User: {config.db_user}")

    logger.info("-" * 40)

    # Create database if needed
    if not create_database_if_not_exists():
        logger.error("Failed to create database")
        sys.exit(1)

    # Setup schema
    if not setup_schema():
        logger.error("Failed to setup schema")
        sys.exit(1)

    logger.info("\n✅ Database setup complete!")
    logger.info("The NetraOptimizer system is ready to collect data.")


if __name__ == "__main__":
    main()