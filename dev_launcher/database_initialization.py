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
import random

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from shared.isolated_environment import get_env
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
        """Initialize PostgreSQL database using DatabaseURLBuilder with retry logic."""
        env = get_env()
        
        # Use DatabaseURLBuilder for proper URL construction
        builder = DatabaseURLBuilder(env.get_all())
        
        # Get the appropriate URL for the environment (sync URL for psycopg2)
        database_url = builder.get_url_for_environment(sync=True)
        
        if not database_url:
            self._print("ℹ️", "POSTGRES", "No PostgreSQL configuration found, skipping initialization")
            return True
            
        # Mask password in URL for logging
        parsed_for_logging = urlparse(database_url)
        safe_url = f"{parsed_for_logging.scheme}://{parsed_for_logging.username}:***@{parsed_for_logging.hostname}:{parsed_for_logging.port}{parsed_for_logging.path}"
        self._print("ℹ️", "POSTGRES", f"Connecting to: {safe_url}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Parse database URL
                parsed = urlparse(database_url)
                if not parsed.hostname:
                    self._print("⚠️", "POSTGRES", "Invalid #removed-legacyformat")
                    return False
                    
                if attempt > 0:
                    # Exponential backoff with jitter
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    self._print("🔄", "POSTGRES", f"Retrying PostgreSQL initialization (attempt {attempt + 1}/{max_retries}) in {delay:.1f}s")
                    await asyncio.sleep(delay)
                    
                # Test basic connection
                connection_successful = await self._test_postgresql_connection(database_url)
                if not connection_successful:
                    if attempt == max_retries - 1:
                        self._print("❌", "POSTGRES", "Cannot connect to PostgreSQL after all retries")
                        return False
                    else:
                        self._print("⚠️", "POSTGRES", f"Connection attempt {attempt + 1} failed, will retry")
                        continue
                    
                # Ensure database exists
                db_exists = await self._ensure_database_exists(parsed)
                if not db_exists:
                    if attempt == max_retries - 1:
                        self._print("⚠️", "POSTGRES", "Database existence check failed after all retries")
                        return False
                    else:
                        self._print("⚠️", "POSTGRES", f"Database check attempt {attempt + 1} failed, will retry")
                        continue
                    
                # Check for basic tables
                tables_exist = await self._check_basic_tables(database_url)
                if not tables_exist:
                    self._print("🔧", "POSTGRES", "Basic tables missing, will be created by migrations")
                    
                self._print("✅", "POSTGRES", f"PostgreSQL initialization successful (attempt {attempt + 1})")
                return True
                
            except Exception as e:
                error_msg = str(e)
                if attempt == max_retries - 1:
                    logger.error(f"PostgreSQL initialization failed after {max_retries} attempts: {e}")
                    self._print("❌", "POSTGRES", f"PostgreSQL initialization failed: {error_msg[:100]}")
                    return False
                else:
                    logger.warning(f"PostgreSQL initialization attempt {attempt + 1} failed: {e}")
                    self._print("⚠️", "POSTGRES", f"Attempt {attempt + 1} failed: {error_msg[:50]}, retrying...")
                    continue
        
        return False
    
    async def _test_postgresql_connection(self, database_url: str) -> bool:
        """Test PostgreSQL connection with increased timeout."""
        try:
            # Use sync connection for simpler error handling with increased timeout
            conn = psycopg2.connect(database_url, connect_timeout=30)
            conn.close()
            return True
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                logger.debug(f"PostgreSQL connection timeout after 30 seconds: {e}")
            elif "refused" in error_msg.lower():
                logger.debug(f"PostgreSQL connection refused: {e}")
            elif "authentication" in error_msg.lower():
                logger.debug(f"PostgreSQL authentication failed: {e}")
            else:
                logger.debug(f"PostgreSQL connection failed: {e}")
            return False
        except Exception as e:
            logger.debug(f"PostgreSQL connection test failed with unexpected error: {e}")
            return False
    
    async def _ensure_database_exists(self, parsed_url) -> bool:
        """Ensure the target database exists with improved error handling."""
        database_name = parsed_url.path.lstrip('/')
        if not database_name:
            self._print("⚠️", "POSTGRES", "No database name found in URL")
            return False
            
        try:
            # Use DatabaseURLBuilder to construct postgres database URL
            env = get_env()
            builder_env = env.get_all().copy()
            
            # Override database name to 'postgres' for checking if target DB exists
            builder_env['POSTGRES_DB'] = 'postgres'
            builder_env['POSTGRES_HOST'] = parsed_url.hostname
            builder_env['POSTGRES_PORT'] = str(parsed_url.port or '5432')
            builder_env['POSTGRES_USER'] = parsed_url.username
            builder_env['POSTGRES_PASSWORD'] = parsed_url.password
            
            builder = DatabaseURLBuilder(builder_env)
            postgres_url = builder.tcp.sync_url or builder.development.default_sync_url
            
            if not postgres_url:
                self._print("⚠️", "POSTGRES", "Could not construct postgres database URL")
                return True  # Continue anyway in development
            
            # Try to connect to postgres database with timeout
            conn = psycopg2.connect(postgres_url, connect_timeout=30)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            
            if not cursor.fetchone():
                # Database doesn't exist, try to create it
                self._print("🔧", "POSTGRES", f"Creating database '{database_name}'")
                try:
                    cursor.execute(f'CREATE DATABASE "{database_name}"')
                    self._print("✅", "POSTGRES", f"Database '{database_name}' created successfully")
                except psycopg2.Error as create_error:
                    error_msg = str(create_error)
                    if "already exists" in error_msg.lower():
                        self._print("✅", "POSTGRES", f"Database '{database_name}' already exists")
                    elif "permission denied" in error_msg.lower():
                        self._print("⚠️", "POSTGRES", f"Permission denied creating database '{database_name}', continuing anyway")
                        cursor.close()
                        conn.close()
                        return True  # Continue in development mode
                    else:
                        self._print("⚠️", "POSTGRES", f"Failed to create database '{database_name}': {error_msg[:50]}")
                        cursor.close()
                        conn.close()
                        return True  # Continue anyway in development
            else:
                self._print("✅", "POSTGRES", f"Database '{database_name}' exists")
                
            cursor.close()
            conn.close()
            return True
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "does not exist" in error_msg.lower() and "postgres" in error_msg.lower():
                self._print("⚠️", "POSTGRES", "Cannot connect to 'postgres' database, trying alternative approach")
                # Try connecting directly to the target database
                return await self._fallback_database_check(parsed_url)
            elif "authentication" in error_msg.lower():
                self._print("⚠️", "POSTGRES", "Authentication failed for database existence check")
                logger.error(f"Database authentication failed: {e}")
                return True  # Continue anyway in development
            elif "timeout" in error_msg.lower():
                self._print("⚠️", "POSTGRES", "Timeout during database existence check")
                logger.error(f"Database existence check timeout: {e}")
                return True  # Continue anyway in development
            else:
                logger.error(f"Database existence check failed: {e}")
                self._print("⚠️", "POSTGRES", f"Database check failed: {error_msg[:50]}, continuing anyway")
                return True  # Continue anyway in development
        except Exception as e:
            logger.error(f"Database existence check failed with unexpected error: {e}")
            self._print("⚠️", "POSTGRES", f"Unexpected error during database check: {str(e)[:50]}, continuing anyway")
            return True  # Continue anyway in development
    
    async def _fallback_database_check(self, parsed_url) -> bool:
        """Fallback method to check database existence by connecting directly."""
        database_name = parsed_url.path.lstrip('/')
        try:
            # Try connecting directly to the target database
            # Reconstruct URL for direct connection
            direct_url = f"{parsed_url.scheme}://{parsed_url.username}:{parsed_url.password}@{parsed_url.hostname}:{parsed_url.port or 5432}/{database_name}"
            conn = psycopg2.connect(direct_url, connect_timeout=30)
            conn.close()
            self._print("✅", "POSTGRES", f"Database '{database_name}' is accessible")
            return True
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "does not exist" in error_msg.lower():
                self._print("⚠️", "POSTGRES", f"Database '{database_name}' does not exist and cannot be created")
                return True  # Continue anyway in development - migrations will handle this
            else:
                self._print("⚠️", "POSTGRES", f"Fallback database check failed: {error_msg[:50]}")
                return True  # Continue anyway in development
        except Exception as e:
            self._print("⚠️", "POSTGRES", f"Fallback check failed: {str(e)[:50]}")
            return True  # Continue anyway in development
    
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
        """Check PostgreSQL readiness with increased timeout."""
        try:
            conn = psycopg2.connect(database_url, connect_timeout=30)
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