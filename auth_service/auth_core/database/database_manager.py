"""
Auth Service Database Manager - Independent Implementation
Manages database connections for auth service without external dependencies

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Microservice independence and reliability
- Value Impact: Isolated auth service, reduced coupling, improved stability
- Strategic Impact: Enables independent scaling and deployment of auth service
"""
import os
import sys
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

logger = logging.getLogger(__name__)


class AuthDatabaseManager:
    """Independent database manager for auth service"""
    
    @staticmethod
    def convert_database_url(url: str) -> str:
        """Convert between database URL formats if needed"""
        import re
        
        if not url:
            return url
            
        # Handle psycopg2 to asyncpg conversion
        if url.startswith("postgresql://") or url.startswith("postgres://"):
            # Parse the URL
            parsed = urlparse(url)
            
            # Convert query parameters
            query_params = []
            
            # Special handling for Cloud SQL Unix socket connections
            is_cloud_sql = "/cloudsql/" in url
            
            if parsed.query:
                for param in parsed.query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        
                        # For Cloud SQL, remove all SSL parameters
                        if is_cloud_sql and key in ['sslmode', 'ssl']:
                            continue  # Skip SSL parameters for Cloud SQL
                        # For non-Cloud SQL, convert sslmode to ssl
                        elif not is_cloud_sql and key == 'sslmode':
                            if value == 'require':
                                query_params.append('ssl=require')
                            # Skip other sslmode values
                        else:
                            query_params.append(param)
                    else:
                        query_params.append(param)
            
            # Reconstruct URL with postgresql+asyncpg
            new_netloc = parsed.netloc
            new_query = '&'.join(query_params) if query_params else ''
            
            return urlunparse((
                'postgresql+asyncpg',
                new_netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
        
        return url
    
    @classmethod
    def create_async_engine(
        cls,
        database_url: Optional[str] = None,
        **kwargs
    ) -> AsyncEngine:
        """Create an async SQLAlchemy engine with auth-specific configuration"""
        
        # Get database URL from environment if not provided
        if not database_url:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL not configured")
        
        # Convert URL format if needed
        async_url = cls.convert_database_url(database_url)
        
        # Default configuration for auth service
        default_config = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "echo": False,
            "future": True,
            "poolclass": AsyncAdaptedQueuePool,
        }
        
        # Testing environment uses NullPool
        if os.getenv("TESTING") == "true":
            default_config["poolclass"] = NullPool
            default_config.pop("pool_size", None)
            default_config.pop("max_overflow", None)
        
        # Merge with provided kwargs
        config = {**default_config, **kwargs}
        
        # Remove pool settings if using NullPool
        if config.get("poolclass") == NullPool:
            for key in ["pool_size", "max_overflow", "pool_timeout", "pool_recycle"]:
                config.pop(key, None)
        
        logger.info(f"Creating async engine for auth service with config: {config}")
        
        try:
            engine = create_async_engine(async_url, **config)
            logger.info("Successfully created async engine for auth service")
            return engine
        except Exception as e:
            logger.error(f"Failed to create async engine: {e}")
            raise
    
    @staticmethod
    def get_auth_database_url_async() -> str:
        """Get async URL for auth service application (asyncpg).
        
        Returns:
            Database URL compatible with asyncpg driver
        """
        import re
        
        # Get DATABASE_URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        logger.debug(f"Converting database URL for async: {database_url[:20]}...")
        
        # Convert postgresql:// to postgresql+asyncpg://
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
        
        # Handle SSL parameters for asyncpg
        # CRITICAL: For Cloud SQL Unix socket connections, remove ALL SSL parameters
        if "/cloudsql/" in database_url:
            # Remove both sslmode and ssl parameters - asyncpg doesn't need them for Unix sockets
            database_url = re.sub(r'[&?]sslmode=[^&]*', '', database_url)
            database_url = re.sub(r'[&?]ssl=[^&]*', '', database_url)
            # Clean up any double ampersands or trailing ampersands
            database_url = re.sub(r'&&+', '&', database_url)
            database_url = re.sub(r'[&?]$', '', database_url)
        else:
            # For non-Cloud SQL connections, convert sslmode to ssl
            if "sslmode=require" in database_url:
                database_url = database_url.replace("sslmode=require", "ssl=require")
            elif "sslmode=" in database_url:
                # Remove other sslmode parameters that asyncpg doesn't understand
                database_url = re.sub(r'[&?]sslmode=[^&]*', '', database_url)
        
        logger.debug(f"Converted async database URL: {database_url[:20]}...")
        return database_url
    
    @staticmethod
    def validate_auth_url(url: str = None) -> bool:
        """Validate the database URL for auth service.
        
        Args:
            url: Optional URL to validate, uses DATABASE_URL if None
            
        Returns:
            True if URL is valid PostgreSQL URL, False otherwise
        """
        if url is None:
            url = os.getenv("DATABASE_URL")
        
        if not url:
            logger.warning("No database URL to validate")
            return False
        
        try:
            # Accept multiple PostgreSQL schemes
            valid_schemes = ["postgresql://", "postgres://", "postgresql+asyncpg://"]
            is_valid_scheme = any(url.startswith(scheme) for scheme in valid_schemes)
            
            if not is_valid_scheme:
                logger.warning(f"Invalid database URL scheme: {url[:20]}...")
                return False
            
            # Basic URL parsing validation
            parsed = urlparse(url)
            if not parsed.netloc:
                logger.warning("Database URL missing netloc")
                return False
            
            logger.debug(f"Database URL validation passed: {url[:20]}...")
            return True
            
        except Exception as e:
            logger.error(f"Database URL validation failed: {e}")
            return False
    
    @staticmethod
    def is_cloud_sql_environment() -> bool:
        """Check if running in Cloud SQL environment.
        
        Returns:
            True if using Cloud SQL or running in Cloud Run
        """
        # Check if DATABASE_URL contains Cloud SQL Unix socket path
        database_url = os.getenv("DATABASE_URL", "")
        if "/cloudsql/" in database_url:
            logger.debug("Detected Cloud SQL environment from DATABASE_URL")
            return True
        
        # Check if running in Cloud Run (K_SERVICE is set by Cloud Run)
        k_service = os.getenv("K_SERVICE")
        if k_service:
            logger.debug(f"Detected Cloud Run environment: {k_service}")
            return True
        
        return False
    
    @staticmethod
    def is_test_environment() -> bool:
        """Check if running in test environment.
        
        Returns:
            True if running in test environment
        """
        # Check environment variables
        environment = os.getenv("ENVIRONMENT", "").lower()
        if environment == "test":
            return True
        
        testing_flag = os.getenv("TESTING", "false").lower()
        if testing_flag == "true":
            return True
        
        # Check if pytest is in sys.modules
        if 'pytest' in sys.modules:
            logger.debug("Detected pytest in sys.modules")
            return True
        
        return False
    
    @staticmethod
    def _get_default_auth_url() -> str:
        """Get default database URL for auth service based on environment.
        
        Returns:
            Default database URL for the current environment
        """
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        if environment == "development":
            return "postgresql://postgres:password@localhost:5432/netra"
        elif environment in ["test", "testing"]:
            return "sqlite:///:memory:"
        elif environment == "staging":
            # Use staging-specific database URL
            return "postgresql://postgres:password@35.223.92.123:5432/netra_staging"
        elif environment == "production":
            return "postgresql://postgres:password@35.223.92.123:5432/netra_production"
        else:
            logger.warning(f"Unknown environment '{environment}', using development default")
            return "postgresql://postgres:password@localhost:5432/netra"
    
    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        """Normalize PostgreSQL URL format for consistency.
        
        Args:
            url: Database URL to normalize
            
        Returns:
            Normalized PostgreSQL URL
        """
        if not url:
            return url
            
        # Convert postgres:// to postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://")
        
        # Strip async driver prefixes for base URL
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        
        return url
    
    @staticmethod
    def _convert_sslmode_to_ssl(url: str) -> str:
        """Convert sslmode parameter to ssl parameter for asyncpg.
        
        Args:
            url: Database URL with sslmode parameter
            
        Returns:
            URL with ssl parameter for asyncpg compatibility
        """
        if not url:
            return url
            
        # Skip conversion for Cloud SQL connections
        if "/cloudsql/" in url:
            return url
        
        # Convert sslmode= to ssl= for asyncpg
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        
        return url