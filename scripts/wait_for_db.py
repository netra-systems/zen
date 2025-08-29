#!/usr/bin/env python3
"""
Database connection wait script for Docker containers.
Waits for PostgreSQL and other dependencies to be ready.
"""

import os
import sys
import time
import logging
from typing import Dict, Any

import psycopg2
import redis
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_database_config() -> Dict[str, Any]:
    """Get database configuration from environment variables."""
    return {
        'host': os.getenv('POSTGRES_HOST', 'postgres'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'user': os.getenv('POSTGRES_USER', 'netra'),
        'password': os.getenv('POSTGRES_PASSWORD', 'netra123'),
        'database': os.getenv('POSTGRES_DB', 'netra_dev')
    }

def get_redis_config() -> Dict[str, Any]:
    """Get Redis configuration from environment variables."""
    return {
        'host': os.getenv('REDIS_HOST', 'redis'),
        'port': int(os.getenv('REDIS_PORT', 6379)),
        'db': 0
    }

def wait_for_postgres(config: Dict[str, Any], max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for PostgreSQL to be ready."""
    logger.info(f"Waiting for PostgreSQL at {config['host']}:{config['port']}")
    logger.info(f"Database: {config['database']}, User: {config['user']}")
    
    for attempt in range(1, max_attempts + 1):
        try:
            connection = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                connect_timeout=5
            )
            connection.close()
            logger.info(f"PostgreSQL is ready! (attempt {attempt}/{max_attempts})")
            return True
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            logger.warning(f"PostgreSQL not ready (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                time.sleep(delay)
    
    logger.error(f"PostgreSQL failed to become ready after {max_attempts} attempts")
    return False

def wait_for_redis(config: Dict[str, Any], max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for Redis to be ready."""
    logger.info(f"Waiting for Redis at {config['host']}:{config['port']}")
    
    for attempt in range(1, max_attempts + 1):
        try:
            client = redis.Redis(
                host=config['host'],
                port=config['port'],
                db=config['db'],
                socket_connect_timeout=5,
                socket_timeout=5
            )
            client.ping()
            client.close()
            logger.info(f"Redis is ready! (attempt {attempt}/{max_attempts})")
            return True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis not ready (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                time.sleep(delay)
    
    logger.error(f"Redis failed to become ready after {max_attempts} attempts")
    return False

def wait_for_clickhouse(max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for ClickHouse to be ready."""
    host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
    port = int(os.getenv('CLICKHOUSE_HTTP_PORT', 8123))
    
    logger.info(f"Waiting for ClickHouse at {host}:{port}")
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(f"http://{host}:{port}/ping", timeout=5)
            if response.status_code == 200:
                logger.info(f"ClickHouse is ready! (attempt {attempt}/{max_attempts})")
                return True
        except requests.RequestException as e:
            logger.warning(f"ClickHouse not ready (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                time.sleep(delay)
    
    logger.error(f"ClickHouse failed to become ready after {max_attempts} attempts")
    return False

def main():
    """Main function to wait for all services."""
    logger.info("Starting database wait script...")
    
    # Get configurations
    postgres_config = get_database_config()
    redis_config = get_redis_config()
    
    # Wait for services
    services_ready = []
    
    # PostgreSQL is required
    if wait_for_postgres(postgres_config):
        services_ready.append("PostgreSQL")
    else:
        logger.error("PostgreSQL is required but not ready. Exiting.")
        sys.exit(1)
    
    # Redis is required
    if wait_for_redis(redis_config):
        services_ready.append("Redis")
    else:
        logger.error("Redis is required but not ready. Exiting.")
        sys.exit(1)
    
    # ClickHouse is optional in some environments
    if os.getenv('CLICKHOUSE_ENABLED', 'true').lower() == 'true':
        if wait_for_clickhouse():
            services_ready.append("ClickHouse")
        else:
            logger.warning("ClickHouse not ready, but continuing...")
    
    logger.info(f"All required services are ready: {', '.join(services_ready)}")
    logger.info("Database wait complete. Starting application...")

if __name__ == "__main__":
    main()