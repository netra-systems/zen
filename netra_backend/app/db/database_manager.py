"""Unified Database Manager - Handles Sync and Async Connections

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Unified database connection management for migrations and runtime
- Value Impact: Eliminates sync/async conflicts, centralizes URL transformation logic
- Strategic Impact: Single source of truth for all database connection patterns

This module provides the unified interface for both sync (Alembic migrations) and
async (FastAPI application) database connections. It handles URL transformations,
SSL parameter management, and environment detection.

Each function ≤15 lines, class ≤200 lines total.
"""

import asyncio
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError

from netra_backend.app.core.isolated_environment import get_env
from netra_backend.app.core.environment_constants import get_current_environment
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.logging_config import central_logger as logger
from shared.database_url_builder import DatabaseURLBuilder
from urllib.parse import urlparse
import urllib.parse
import re


class DatabaseManager:
    """Unified database manager for sync and async connections."""
    
    @staticmethod
    def get_base_database_url() -> str:
        """Get clean base URL without driver-specific elements.
        
        Uses CoreDatabaseManager for consistent URL normalization.
        
        Returns:
            Clean database URL with driver prefixes stripped but SSL params preserved for non-Cloud SQL
        """
        # ALWAYS use unified configuration - single source of truth
        # BUT prioritize environment variable for test isolation
        raw_url = ""
        
        # First check if DATABASE_URL is explicitly set in environment (for test isolation)
        env_url = get_env().get("DATABASE_URL", "")
        
        try:
            config = get_unified_config()
            # Use env URL if set, otherwise use config URL
            raw_url = env_url or config.database_url or ""
            
            # Check test collection mode from config
            if config.environment == "testing" and not raw_url:
                return "sqlite:///:memory:"
        except Exception:
            # Fallback for bootstrap or when config not available
            raw_url = env_url
            test_collection_mode = get_env().get('TEST_COLLECTION_MODE')
            if test_collection_mode == '1' and not raw_url:
                return "sqlite:///:memory:"
        
        if not raw_url:
            return DatabaseManager._get_default_database_url()
        
        # Use DatabaseURLBuilder for consistent URL handling - single source of truth
        env_vars = get_env().get_all()
        env_vars['DATABASE_URL'] = raw_url
        builder = DatabaseURLBuilder(env_vars)
        
        # Get normalized URL from builder and remove driver-specific elements
        normalized = builder.normalize_url(raw_url)
        
        # Remove driver suffixes to get clean base URL (postgresql+asyncpg -> postgresql, postgres+asyncpg -> postgresql)
        import re
        if "postgresql+" in normalized:
            normalized = re.sub(r'postgresql\+[^:]+://', 'postgresql://', normalized)
        elif "postgres+" in normalized:
            normalized = re.sub(r'postgres\+[^:]+://', 'postgresql://', normalized)
        
        # Handle schema search_path based on environment
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(normalized)
        query_params = parse_qs(parsed.query)
        
        # Only add search_path for non-Cloud SQL connections (check directly for Cloud SQL pattern)
        is_cloud_sql = "/cloudsql/" in normalized
        if not is_cloud_sql and 'options' not in query_params and normalized.startswith("postgresql://"):
            current_env = get_current_environment()
            if current_env == "development":
                # Use netra_dev schema for development
                query_params['options'] = ['-c search_path=netra_dev,public']
            elif current_env in ["testing", "test"]:
                # Use netra_test schema for testing
                query_params['options'] = ['-c search_path=netra_test,public']
            else:
                # Use public schema for staging/production
                query_params['options'] = ['-c search_path=public']
        
        new_query = urlencode(query_params, doseq=True)
        normalized = urlunparse(parsed._replace(query=new_query))
        
        return normalized
    
    @staticmethod
    def get_migration_url_sync_format() -> str:
        """Get sync URL for migrations (psycopg2/pg8000).
        
        Returns:
            Database URL compatible with synchronous drivers
        """
        # ALWAYS use unified configuration - no pytest bypass
        raw_url = ""
        
        # Get from unified configuration - single source of truth
        try:
            config = get_unified_config()
            raw_url = config.database_url or ""
        except Exception:
            # Fallback for bootstrap or when config not available
            raw_url = get_env().get("DATABASE_URL", "")
        
        if not raw_url:
            return "sqlite:///:memory:"
        
        # For sqlite, return as-is
        if raw_url.startswith("sqlite"):
            return raw_url
        
        # Use DatabaseURLBuilder for consistent URL handling
        env_vars = get_env().get_all()
        env_vars['DATABASE_URL'] = raw_url
        builder = DatabaseURLBuilder(env_vars)
        
        # If URL contains /cloudsql/ pattern, handle as Cloud SQL
        if "/cloudsql/" in raw_url:
            # Check if builder can provide a valid sync URL
            if builder.cloud_sql.is_cloud_sql:
                sync_url = builder.cloud_sql.sync_url
                # Only use builder result if it's not malformed
                if sync_url and sync_url != "postgresql://@/?host=":
                    return sync_url
            
            # Fallback: treat as pre-formatted Cloud SQL URL and return normalized as-is
            normalized = DatabaseURLBuilder.normalize_postgres_url(raw_url)
            return normalized
        
        # For non-Cloud SQL, format for sync driver with SSL parameter conversion
        sync_url = builder.format_url_for_driver(raw_url, 'base')
        
        # Convert ssl= to sslmode= for sync drivers
        if "ssl=" in sync_url and "sslmode=" not in sync_url:
            sync_url = sync_url.replace("ssl=", "sslmode=")
        
        return sync_url
    
    @staticmethod
    def get_application_url_async() -> str:
        """Get async URL for application (asyncpg).
        
        Returns:
            Database URL compatible with asyncpg driver
        """
        base_url = DatabaseManager.get_base_database_url()
        # For async driver, ensure postgresql+asyncpg:// prefix
        if base_url.startswith("sqlite"):
            return base_url.replace("sqlite://", "sqlite+aiosqlite://")
        
        # Use DatabaseURLBuilder for driver-specific formatting
        env_vars = get_env().get_all()
        env_vars['DATABASE_URL'] = base_url
        builder = DatabaseURLBuilder(env_vars)
        
        # For Cloud SQL, use the properly parsed async URL from builder
        if builder.cloud_sql.is_cloud_sql:
            async_url = builder.cloud_sql.async_url
            if async_url and async_url != "postgresql+asyncpg://@/?host=":
                return async_url
        
        # For non-Cloud SQL, format for async driver
        base_url = builder.format_url_for_driver(base_url, 'asyncpg')
        
        # Remove search_path options from URL - handled via server_settings in connect_args
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query)
        
        # Remove options parameter for async connections (handled via server_settings)
        query_params.pop('options', None)
        
        new_query = urlencode(query_params, doseq=True)
        base_url = urlunparse(parsed._replace(query=new_query))
        
        return base_url
    
    @staticmethod
    def validate_base_url() -> bool:
        """Ensure no driver-specific elements remain.
        
        Returns:
            True if base URL is clean, False otherwise
        """
        base_url = DatabaseManager.get_base_database_url()
        
        # Check for driver-specific elements
        has_async_driver = "asyncpg" in base_url
        # Check for mixed SSL params using simple string check
        has_mixed_ssl = "ssl=" in base_url and "sslmode=" in base_url
        
        return not (has_async_driver or has_mixed_ssl)
    
    @staticmethod
    def validate_migration_url_sync_format(url: str = None) -> bool:
        """Confirm sync driver compatibility.
        
        Args:
            url: Optional URL to validate, uses migration URL if None
            
        Returns:
            True if URL is sync-compatible
        """
        target_url = url or DatabaseManager.get_migration_url_sync_format()
        
        # Must NOT have async drivers
        if "asyncpg" in target_url:
            return False
        
        # Should use sslmode (not ssl) unless Cloud SQL
        env_vars = get_env().get_all()
        env_vars['DATABASE_URL'] = target_url
        builder = DatabaseURLBuilder(env_vars)
        if not builder.cloud_sql.is_cloud_sql and "ssl=" in target_url:
            return False
        
        return target_url.startswith("postgresql://")
    
    @staticmethod
    def validate_application_url(url: str = None) -> bool:
        """Confirm async driver compatibility.
        
        Args:
            url: Optional URL to validate, uses application URL if None
            
        Returns:
            True if URL is async-compatible
        """
        target_url = url or DatabaseManager.get_application_url_async()
        
        # Must have async driver
        if not target_url.startswith("postgresql+asyncpg://"):
            return False
        
        # Should use ssl (not sslmode) unless Cloud SQL
        env_vars = get_env().get_all()
        env_vars['DATABASE_URL'] = target_url
        builder = DatabaseURLBuilder(env_vars)
        if not builder.cloud_sql.is_cloud_sql and "sslmode=" in target_url:
            return False
        
        return True
    
    @staticmethod
    def create_migration_engine():
        """Return sync SQLAlchemy engine for Alembic.
        
        Returns:
            Synchronous SQLAlchemy engine configured for migrations
        """
        migration_url = DatabaseManager.get_migration_url_sync_format()
        
        # Get SQL echo setting from unified config
        config = get_unified_config()
        sql_echo = config.log_level == "DEBUG"  # Enable SQL echo in DEBUG mode
        
        return create_engine(
            migration_url,
            echo=sql_echo,
            pool_pre_ping=True,
            pool_recycle=3600,
            # Smaller pool for migration engine to avoid conflicts with main app pool
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_reset_on_return='rollback',
        )
    
    @staticmethod
    def create_application_engine():
        """Return async SQLAlchemy engine for FastAPI with resilient pool configuration.
        
        CRITICAL FIX: Uses AsyncAdaptedQueuePool to prevent asyncio compatibility issues.
        
        Returns:
            Async SQLAlchemy engine configured for application runtime
        """
        from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
        
        app_url = DatabaseManager.get_application_url_async()
        
        # Determine appropriate pool class - CRITICAL for asyncio compatibility
        pool_class = NullPool if "sqlite" in app_url else AsyncAdaptedQueuePool
        
        connect_args = {}
        if "/cloudsql/" not in app_url and pool_class != NullPool:
            # Get appropriate search path for environment
            from netra_backend.app.core.environment_constants import get_current_environment
            current_env = get_current_environment()
            if current_env == "development":
                search_path = "netra_dev,public"
            elif current_env in ["testing", "test"]:
                search_path = "netra_test,public"
            else:
                search_path = "public"
                
            # Standard connection settings for PostgreSQL
            connect_args = {
                "server_settings": {
                    "application_name": "netra_backend_async",
                    "tcp_keepalives_idle": "600",
                    "tcp_keepalives_interval": "30", 
                    "tcp_keepalives_count": "3",
                    # Add connection limits to prevent startup contention
                    "lock_timeout": "60s",
                    "statement_timeout": "120s",
                    # CRITICAL FIX: Set search_path via server_settings instead of URL options
                    "search_path": search_path,
                }
            }
        
        # Get SQL echo setting from unified config
        config = get_unified_config()
        sql_echo = config.log_level == "DEBUG"  # Enable SQL echo in DEBUG mode
        
        engine_args = {
            "echo": sql_echo,
            "poolclass": pool_class,  # CRITICAL: Specify pool class explicitly
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_reset_on_return": 'rollback',  # Reset connections properly
        }
        
        # Add pool sizing only for non-NullPool configurations
        if pool_class != NullPool:
            engine_args.update({
                # Optimized pool sizes for cold start resilience
                "pool_size": 25,  # Increased base pool size for concurrent startup
                "max_overflow": 35,  # Higher overflow to handle startup bursts (total max: 60)
                "pool_timeout": 120,  # Longer timeout for cold start scenarios
            })
        
        if connect_args:
            engine_args["connect_args"] = connect_args
        
        return create_async_engine(app_url, **engine_args)
    
    @staticmethod
    def get_migration_session():
        """Return sync session factory for migrations.
        
        Returns:
            Synchronous session factory for Alembic operations
        """
        engine = DatabaseManager.create_migration_engine()
        return sessionmaker(bind=engine)
    
    @staticmethod
    def get_application_session():
        """Return async session factory for app runtime.
        
        Returns:
            Async session factory for FastAPI operations
        """
        engine = DatabaseManager.create_application_engine()
        return async_sessionmaker(
            engine,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    
    @staticmethod
    def is_cloud_sql_environment() -> bool:
        """Detect if running in Cloud SQL environment.
        
        Returns:
            True if using Cloud SQL Unix socket connections
        """
        # Get DATABASE_URL - prioritize environment for test isolation
        env_database_url = get_env().get("DATABASE_URL", "")
        
        # If DATABASE_URL is set in environment, use it directly (important for tests)
        if env_database_url:
            database_url = env_database_url
        else:
            # Otherwise use unified configuration
            try:
                config = get_unified_config()
                database_url = config.database_url or ""
            except Exception:
                # Fallback for bootstrap
                database_url = ""
        
        # Use DatabaseURLBuilder for Cloud SQL detection
        env_vars = get_env().get_all()
        env_vars['DATABASE_URL'] = database_url
        builder = DatabaseURLBuilder(env_vars)
        return builder.cloud_sql.is_cloud_sql
    
    @staticmethod
    def is_local_development() -> bool:
        """Detect if running in local development.
        
        Returns:
            True if running in local development environment
        """
        # ALWAYS use unified configuration - no pytest bypass
        config = get_unified_config()
        return config.environment == "development"
    
    @staticmethod
    def is_remote_environment() -> bool:
        """Detect if running in staging/production.
        
        Returns:
            True if running in staging or production environment
        """
        current_env = get_current_environment()
        return current_env in ["staging", "production"]
    
    @staticmethod
    async def test_connection_with_retry(engine, max_retries: int = 3, delay: float = 1.0) -> bool:
        """Test database connection with retry logic and connection pool awareness.
        
        Args:
            engine: SQLAlchemy async engine
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Use a timeout to avoid hanging indefinitely
                async with asyncio.timeout(10.0):
                    async with engine.begin() as conn:
                        await conn.execute(text("SELECT 1"))
                        logger.debug(f"Database connection test successful on attempt {attempt + 1}")
                        return True
            except (OperationalError, DisconnectionError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All {max_retries} connection attempts failed: {e}")
        return False
    
    @staticmethod
    def get_pool_status(engine) -> dict:
        """Get connection pool status for monitoring.
        
        Args:
            engine: SQLAlchemy engine
            
        Returns:
            Dictionary with pool statistics
        """
        if hasattr(engine.pool, 'size'):
            return {
                "pool_size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "invalid": engine.pool.invalid(),
            }
        return {"status": "Pool status unavailable"}
    
    @staticmethod
    async def create_user_with_rollback(user_data: dict) -> dict:
        """Create user with proper transaction rollback handling.
        
        FIX: Ensures complete rollback on failure to prevent partial user records.
        
        Args:
            user_data: User data dictionary with email, name, etc.
            
        Returns:
            Created user data or raises exception with cleanup
        """
        # Create async session from application engine
        async_session = DatabaseManager.get_application_session()
        
        async with async_session() as session:
            async with session.begin():
                try:
                    # Create user record using SQLAlchemy core
                    from sqlalchemy import text
                    user_result = await session.execute(
                        text("INSERT INTO users (email, name, created_at) VALUES (:email, :name, NOW()) RETURNING id"),
                        {"email": user_data.get("email"), "name": user_data.get("name")}
                    )
                    user_id = user_result.scalar()
                    
                    # Create associated profile if data provided
                    if user_data.get("profile_data"):
                        await session.execute(
                            text("INSERT INTO user_profiles (user_id, data, created_at) VALUES (:user_id, :data, NOW())"),
                            {"user_id": user_id, "data": user_data["profile_data"]}
                        )
                    
                    # Return complete user data
                    return {
                        "id": user_id,
                        "email": user_data.get("email"),
                        "name": user_data.get("name"),
                        "created_at": "now"
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to create user: {str(e)}")
                    # Transaction will be rolled back automatically
                    raise
    
    @staticmethod
    def _get_default_database_url() -> str:
        """Get default database URL for current environment.
        
        Returns:
            Default PostgreSQL URL based on environment with schema search_path
        """
        current_env = get_current_environment()
        
        # NO pytest bypass - tests and production use identical code paths
        
        if current_env in ["testing", "test"]:
            return "postgresql://test:test@localhost:5432/netra_test?options=-c%20search_path%3Dnetra_test,public"
        elif current_env == "development":
            return "postgresql://postgres:password@localhost:5432/netra?options=-c%20search_path%3Dnetra_dev,public"
        else:
            # Staging/production should always have DATABASE_URL set
            logger.warning(f"No DATABASE_URL found for {current_env} environment")
            return "postgresql://postgres:password@localhost:5432/netra?options=-c%20search_path%3Dpublic"
    
    # AUTH SERVICE COMPATIBILITY METHODS
    # These methods provide auth service compatibility while using CoreDatabaseManager
    
    @staticmethod
    def get_auth_database_url_async() -> str:
        """Get async URL for auth service - delegates to application URL."""
        return DatabaseManager.get_application_url_async()
    
    @staticmethod
    def get_auth_database_url() -> str:
        """Get base URL for auth service - delegates to base URL."""
        return DatabaseManager.get_base_database_url()
    
    @staticmethod
    def get_auth_database_url_sync() -> str:
        """Get sync URL for auth service - delegates to migration URL."""
        return DatabaseManager.get_migration_url_sync_format()
    
    @staticmethod
    def validate_auth_url(url: str = None) -> bool:
        """Validate auth URL - delegates to application URL validation."""
        target_url = url or DatabaseManager.get_auth_database_url_async()
        return DatabaseManager.validate_application_url(target_url)
    
    @staticmethod
    def validate_sync_url(url: str = None) -> bool:
        """Validate sync URL - delegates to migration URL validation."""
        target_url = url or DatabaseManager.get_auth_database_url_sync()
        return DatabaseManager.validate_migration_url_sync_format(target_url)
    
    @staticmethod
    def is_test_environment() -> bool:
        """Detect test environment - uses unified config."""
        config = get_unified_config()
        current_env = config.environment
        is_test_mode = config.environment == "testing"
        # NO pytest bypass - use environment configuration only
        
        return current_env in ["testing", "test"] or is_test_mode
    
    @staticmethod
    def create_auth_application_engine():
        """Create auth engine - delegates to application engine."""
        return DatabaseManager.create_application_engine()
    
    @staticmethod
    def get_auth_application_session():
        """Get auth session - delegates to application session."""
        return DatabaseManager.get_application_session()
    
    
    
    
    
    @staticmethod
    def validate_database_credentials(url: str) -> bool:
        """Validate database URL has proper credentials and prevent SQL injection attacks.
        
        Args:
            url: Database URL to validate
            
        Returns:
            True if credentials are valid and secure
            
        Raises:
            ValueError: If credentials are missing, invalid, or contain malicious patterns
        """
        if not url:
            raise ValueError("Database URL cannot be empty")
        
        # Check for control characters and null bytes that could indicate injection attacks
        for i, char in enumerate(url):
            if ord(char) < 32 and char not in '\t\n\r':  # Allow some whitespace but not control chars
                raise ValueError(f"Database URL contains control character at position {i}")
        
        # Check for SQL injection patterns in the URL
        sql_injection_patterns = [
            r'(;\s*DROP\s+TABLE)',  # DROP TABLE attempts
            r'(;\s*DELETE\s+FROM)',  # DELETE attempts  
            r'(;\s*INSERT\s+INTO)',  # INSERT attempts
            r'(;\s*UPDATE\s+SET)',   # UPDATE attempts
            r'(-{2})',               # SQL comments --
            r'(\bOR\s+\d+\s*=\s*\d+)', # OR 1=1 patterns
            r'(\bUNION\s+SELECT)',   # UNION SELECT attempts
        ]
        
        for pattern in sql_injection_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                raise ValueError("Database URL contains potential SQL injection pattern")
            
        parsed = urlparse(url)
        
        # Check for missing credentials
        if not parsed.username:
            if "sqlite" not in url:
                raise ValueError("Database URL missing username credentials")
        
        # For PostgreSQL, password is generally required (except for Cloud SQL with IAM)
        if parsed.scheme and "postgresql" in parsed.scheme:
            is_cloud_sql = "/cloudsql/" in url or "@/cloudsql/" in url
            
            # Cloud SQL with Unix sockets may not need explicit password
            if not is_cloud_sql and not parsed.password:
                raise ValueError("Database URL missing password credentials for PostgreSQL connection")
        
        # Check for obviously empty credentials
        if parsed.username == "":
            raise ValueError("Database username cannot be empty string")
            
        if parsed.password == "":
            if "postgresql" in parsed.scheme and "/cloudsql/" not in url:
                raise ValueError("Database password cannot be empty string for non-Cloud SQL PostgreSQL")
        
        return True
    
    @staticmethod
    def _validate_password_integrity(original_url: str, sanitized_url: str) -> None:
        """Validate that password wasn't corrupted during sanitization.
        
        Args:
            original_url: Original database URL
            sanitized_url: URL after sanitization
            
        Raises:
            ValueError: If password corruption is detected
        """
        try:
            original_parsed = urlparse(original_url)
            sanitized_parsed = urlparse(sanitized_url)
            
            # Check if password was corrupted
            if original_parsed.password and sanitized_parsed.password:
                if original_parsed.password != sanitized_parsed.password:
                    raise ValueError(
                        f"Password corrupted during sanitization - authentication will fail. "
                        f"Original length: {len(original_parsed.password)}, "
                        f"sanitized length: {len(sanitized_parsed.password)}"
                    )
            elif original_parsed.password and not sanitized_parsed.password:
                raise ValueError("Password integrity compromised - password was completely removed during sanitization")
        
        except Exception as e:
            if "Password corrupted" in str(e) or "integrity compromised" in str(e):
                raise  # Re-raise our validation errors
            raise ValueError(f"Password integrity validation failed: {e}")
    
    @staticmethod
    def _validate_url_encoding_integrity(url: str) -> None:
        """Validate URL encoding doesn't corrupt passwords.
        
        Args:
            url: Database URL to validate
            
        Raises:
            ValueError: If URL encoding issues are detected
        """
        import urllib.parse
        
        try:
            # Check for double encoding issues
            decoded_once = urllib.parse.unquote(url)
            decoded_twice = urllib.parse.unquote(decoded_once)
            
            if decoded_once != decoded_twice:
                raise ValueError("URL encoding corruption detected - double encoding may corrupt passwords")
            
            # Check for problematic URL encoding patterns
            parsed = urlparse(url)
            if parsed.password:
                password = parsed.password
                
                # Check for encoded characters that might indicate corruption
                if '%' in password:
                    try:
                        decoded_password = urllib.parse.unquote(password)
                        if decoded_password != password:
                            logger.warning(f"Password contains URL encoding - ensure this is intentional")
                    except Exception:
                        raise ValueError("Password contains invalid URL encoding")
        
        except Exception as e:
            if "URL encoding" in str(e):
                raise  # Re-raise our validation errors
            raise ValueError(f"URL encoding validation failed: {e}")
    
    @staticmethod
    def _validate_credentials_before_connection(url: str) -> None:
        """Validate credentials before attempting database connection.
        
        Args:
            url: Database URL to validate
            
        Raises:
            ValueError: If credentials are invalid or missing
        """
        parsed = urlparse(url)
        
        # Check for empty password after sanitization
        if parsed.password == "":
            raise ValueError("Empty password detected - database connection will fail")
        
        # Check for missing password
        if not parsed.password and "postgresql" in url and "/cloudsql/" not in url:
            raise ValueError("Missing password - database connection requires authentication")
        
        # Check for placeholder passwords
        placeholder_patterns = [
            "password", "secret", "redacted", "filtered", "hidden", "*"
        ]
        
        if parsed.password:
            password_lower = parsed.password.lower()
            for pattern in placeholder_patterns:
                if pattern in password_lower and len(parsed.password) < 20:
                    # Short passwords containing placeholder words are suspicious
                    if parsed.password in ["password", "PASSWORD", "secret", "SECRET", "REDACTED", "***HIDDEN***"]:
                        raise ValueError(f"Invalid password - placeholder detected: {pattern}")
    
    @staticmethod
    def _validate_password_length(url: str, min_length: int = 6) -> None:
        """Validate password length after sanitization.
        
        Args:
            url: Database URL to validate
            min_length: Minimum password length required
            
        Raises:
            ValueError: If password is too short
        """
        parsed = urlparse(url)
        
        if parsed.password and len(parsed.password) < min_length:
            raise ValueError(
                f"Password length validation failed - password too short after sanitization: "
                f"{len(parsed.password)} characters (minimum: {min_length})"
            )
    
    @staticmethod
    def _validate_staging_password_integrity(original_url: str, processed_url: str) -> None:
        """Validate password integrity specifically for staging environment.
        
        Args:
            original_url: Original database URL
            processed_url: Processed/sanitized database URL
            
        Raises:
            ValueError: If staging validation fails
        """
        try:
            original_parsed = urlparse(original_url)
            processed_parsed = urlparse(processed_url)
            
            if not original_parsed.password or not processed_parsed.password:
                raise ValueError("Staging validation failed - password missing in URL")
            
            if original_parsed.password != processed_parsed.password:
                raise ValueError(
                    f"Staging password integrity check failed - password corrupted during processing. "
                    f"This indicates a sanitization error that must be fixed."
                )
            
        except Exception as e:
            if "Staging" in str(e):
                raise  # Re-raise our validation errors
            raise ValueError(f"Staging validation error: {e}")
    
    @staticmethod
    def _validate_password_entropy(password: str, min_entropy_score: float = 2.5) -> None:
        """Validate password entropy for staging environment.
        
        Args:
            password: Password to validate
            min_entropy_score: Minimum entropy score required
            
        Raises:
            ValueError: If password entropy is too low
        """
        if not password:
            raise ValueError("Password entropy validation failed - empty password")
        
        # Simple entropy calculation
        import math
        from collections import Counter
        
        char_counts = Counter(password)
        entropy = 0.0
        password_length = len(password)
        
        for count in char_counts.values():
            probability = count / password_length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        if entropy < min_entropy_score:
            raise ValueError(
                f"Password entropy too low for staging environment: {entropy:.2f} "
                f"(minimum: {min_entropy_score}). Password lacks sufficient randomness."
            )
    
    @staticmethod
    def _extract_password_from_url(url: str) -> str:
        """Extract password from database URL safely.
        
        Args:
            url: Database URL
            
        Returns:
            Extracted password
            
        Raises:
            ValueError: If password extraction fails
        """
        try:
            parsed = urlparse(url)
            if not parsed.password:
                raise ValueError("No password found in URL")
            return parsed.password
        except Exception as e:
            raise ValueError(f"Password extraction failed: {e}")

    @staticmethod
    def _get_default_auth_url() -> str:
        """Get default database URL for current environment."""
        current_env = get_current_environment()
        if current_env == "production":
            return "postgresql://netra:password@/netra_auth?host=/cloudsql/netra-production:us-central1:netra-db"
        elif current_env == "staging":
            return "postgresql://netra:password@/netra_auth?host=/cloudsql/netra-staging:us-central1:netra-db"
        else:
            return "postgresql://netra:password@localhost:5432/netra_auth"


    @staticmethod
    async def initialize_database_with_migration_locks():
        """Initialize database with migration lock management for cold starts.
        
        Returns:
            Tuple of (engine, session_factory, migration_manager)
        """
        from netra_backend.app.db.migration_manager import migration_lock_manager
        from netra_backend.app.db.connection_pool_manager import get_connection_pool_manager
        
        logger.info("Initializing database with migration lock management")
        
        # Get connection pool manager
        pool_manager = await get_connection_pool_manager()
        
        # Perform health check first
        health_status = await pool_manager.health_check()
        if health_status["status"] != "healthy":
            logger.warning(f"Database health check warning: {health_status}")
        
        # Attempt to acquire migration lock to coordinate startup
        async with migration_lock_manager.migration_lock_context(timeout=30) as locked:
            if locked:
                logger.info("Acquired migration lock - performing initialization")
                
                # Test connection with the pool manager
                try:
                    async with await pool_manager.get_session() as session:
                        await session.execute(text("SELECT 1"))
                        await session.commit()
                    
                    logger.info("Database initialization completed successfully")
                    return pool_manager._engine, pool_manager._session_factory, migration_lock_manager
                    
                except Exception as e:
                    logger.error(f"Database initialization failed: {e}")
                    raise
            else:
                logger.info("Could not acquire migration lock - using existing initialization")
                # Still return the pool manager components
                await pool_manager._ensure_initialized()
                return pool_manager._engine, pool_manager._session_factory, migration_lock_manager


# Export the main class and key functions
__all__ = ["DatabaseManager"]