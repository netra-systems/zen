"""
Database initialization with cold start handling.

Ensures database schema is created and ready for application startup.
Handles missing tables, schema creation, and basic recovery.
"""

import asyncio
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from dev_launcher.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder

from dev_launcher.utils import print_with_emoji

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """
    Handles cold start database initialization.
    
    Ensures that databases exist and basic schema is in place
    before application services start.
    """
    
    def __init__(self, project_root: Path, use_emoji: bool = True):
        """Initialize database initializer."""
        self.project_root = project_root
        self.use_emoji = use_emoji
        
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    async def initialize_databases(self) -> bool:
        """
        Initialize all configured databases for cold start.
        
        Returns:
            bool: True if initialization successful or not needed
        """
        try:
            # Check if databases are in mock mode
            if self._are_databases_mock():
                self._print("🎭", "INIT", "Databases in mock mode, skipping initialization")
                return True
            
            # Initialize PostgreSQL
            postgres_success = await self._initialize_postgresql()
            
            if not postgres_success:
                self._print("⚠️", "INIT", "PostgreSQL initialization had issues, continuing...")
                # Don't fail startup for database issues in development
                
            self._print("✅", "INIT", "Database initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            self._print("❌", "INIT", f"Database initialization failed: {e}")
            
            # In development, continue even if initialization fails
            if self._is_development():
                self._print("⚠️", "INIT", "Continuing despite initialization errors (development mode)")
                return True
            return False
    
    async def _initialize_postgresql(self) -> bool:
        """Initialize PostgreSQL database using DatabaseURLBuilder."""
        env = get_env()
        
        # Use DatabaseURLBuilder for proper URL construction
        builder = DatabaseURLBuilder(env.get_all())
        
        # Get the appropriate URL for the environment (sync URL for psycopg2)
        database_url = builder.get_url_for_environment(sync=True)
        
        if not database_url:
            self._print("ℹ️", "POSTGRES", "No PostgreSQL configuration found, skipping initialization")
            return True
            
        try:
            # Parse database URL
            parsed = urlparse(database_url)
            if not parsed.hostname:
                self._print("⚠️", "POSTGRES", "Invalid DATABASE_URL format")
                return False
                
            # Test basic connection
            connection_successful = await self._test_postgresql_connection(database_url)
            if not connection_successful:
                self._print("❌", "POSTGRES", "Cannot connect to PostgreSQL")
                return False
                
            # Ensure database exists
            db_exists = await self._ensure_database_exists(parsed)
            if not db_exists:
                self._print("⚠️", "POSTGRES", "Database existence check failed")
                return False
                
            # Check for basic tables
            tables_exist = await self._check_basic_tables(database_url)
            if not tables_exist:
                self._print("🔧", "POSTGRES", "Basic tables missing, will be created by migrations")
                
            self._print("✅", "POSTGRES", "PostgreSQL initialization successful")
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL initialization failed: {e}")
            self._print("❌", "POSTGRES", f"PostgreSQL initialization failed: {str(e)[:100]}")
            return False
    
    async def _test_postgresql_connection(self, database_url: str) -> bool:
        """Test PostgreSQL connection."""
        try:
            # Use sync connection for simpler error handling
            conn = psycopg2.connect(database_url, connect_timeout=10)
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"PostgreSQL connection test failed: {e}")
            return False
    
    async def _ensure_database_exists(self, parsed_url) -> bool:
        """Ensure the target database exists."""
        try:
            # Connect to postgres database to check if target database exists
            postgres_url = f"postgresql://{parsed_url.username}:{parsed_url.password}@{parsed_url.hostname}:{parsed_url.port}/postgres"
            
            conn = psycopg2.connect(postgres_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            database_name = parsed_url.path.lstrip('/')
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            
            if not cursor.fetchone():
                # Database doesn't exist, try to create it
                self._print("🔧", "POSTGRES", f"Creating database '{database_name}'")
                cursor.execute(f'CREATE DATABASE "{database_name}"')
                self._print("✅", "POSTGRES", f"Database '{database_name}' created successfully")
            else:
                self._print("✅", "POSTGRES", f"Database '{database_name}' exists")
                
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Database existence check failed: {e}")
            # Don't create database if we can't connect to postgres
            return True  # Continue anyway
    
    async def _check_basic_tables(self, database_url: str) -> bool:
        """Check if basic tables exist."""
        try:
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            # Check for alembic version table (indicates migrations have run)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """)
            
            has_alembic = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return has_alembic
            
        except Exception as e:
            logger.debug(f"Table check failed: {e}")
            return False
    
    def _are_databases_mock(self) -> bool:
        """Check if databases are configured in mock mode."""
        env = get_env()
        postgres_mode = env.get('POSTGRES_MODE', '').lower()
        database_url = env.get('DATABASE_URL', '')
        
        return (
            postgres_mode == 'mock' or 
            'mock' in database_url.lower() or
            env.get('MOCK_DATABASE', '').lower() == 'true'
        )
    
    def _is_development(self) -> bool:
        """Check if running in development mode."""
        env = get_env()
        return env.get('ENVIRONMENT', 'development').lower() == 'development'


class DatabaseHealthChecker:
    """
    Monitors database health during startup and operation.
    """
    
    def __init__(self, use_emoji: bool = True):
        self.use_emoji = use_emoji
        
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    async def check_database_readiness(self) -> Dict[str, bool]:
        """
        Check if all databases are ready for application use.
        
        Returns:
            Dict[str, bool]: Status for each database
        """
        results = {}
        
        # Check PostgreSQL
        env = get_env()
        database_url = env.get('DATABASE_URL')
        if database_url and 'mock' not in database_url.lower():
            results['postgresql'] = await self._check_postgresql_readiness(database_url)
        else:
            results['postgresql'] = True  # Mock or not configured
            
        # Check Redis
        redis_url = env.get('REDIS_URL')
        if redis_url and 'mock' not in redis_url.lower():
            results['redis'] = await self._check_redis_readiness(redis_url)
        else:
            results['redis'] = True  # Mock or not configured
            
        return results
    
    async def _check_postgresql_readiness(self, database_url: str) -> bool:
        """Check PostgreSQL readiness."""
        try:
            conn = psycopg2.connect(database_url, connect_timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"PostgreSQL readiness check failed: {e}")
            return False
    
    async def _check_redis_readiness(self, redis_url: str) -> bool:
        """Check Redis readiness."""
        try:
            import redis
            r = redis.from_url(redis_url, socket_timeout=5)
            r.ping()
            r.close()
            return True
        except Exception as e:
            logger.debug(f"Redis readiness check failed: {e}")
            return False