"""
Database URL Builder
Comprehensive utility for constructing database URLs from environment variables.
Provides clear access to all possible URL combinations.
"""
from typing import Optional, Dict, Any
import logging
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)


class DatabaseURLBuilder:
    """
    Build database URLs from environment variables.
    
    Provides organized access to all URL patterns:
    - cloud_sql.async_url
    - cloud_sql.sync_url
    - tcp.async_url
    - tcp.sync_url
    - tcp.async_url_with_ssl
    - development.default_url
    - test.memory_url
    - docker.compose_url
    """
    
    def __init__(self, env_vars: Dict[str, Any]):
        """Initialize with environment variables."""
        self.env = env_vars
        self.environment = env_vars.get("ENVIRONMENT", "development").lower()
        
        # Parse PostgreSQL variables
        self.postgres_host = env_vars.get("POSTGRES_HOST", "")
        self.postgres_port = env_vars.get("POSTGRES_PORT", "5432")
        self.postgres_db = env_vars.get("POSTGRES_DB", "")
        self.postgres_user = env_vars.get("POSTGRES_USER", "")
        self.postgres_password = env_vars.get("POSTGRES_PASSWORD", "")
        
        # Parse other variables
        self.database_url = env_vars.get("DATABASE_URL", "")
        
        # Initialize sub-builders
        self.cloud_sql = self.CloudSQLBuilder(self)
        self.tcp = self.TCPBuilder(self)
        self.development = self.DevelopmentBuilder(self)
        self.test = self.TestBuilder(self)
        self.docker = self.DockerBuilder(self)
        self.staging = self.StagingBuilder(self)
        self.production = self.ProductionBuilder(self)
    
    class CloudSQLBuilder:
        """Build Cloud SQL URLs (Unix socket connections)."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def is_cloud_sql(self) -> bool:
            """Check if this is a Cloud SQL configuration."""
            return self.parent.postgres_host is not None and "/cloudsql/" in self.parent.postgres_host
        
        @property
        def async_url(self) -> Optional[str]:
            """Async URL for Cloud SQL Unix socket connection."""
            if not self.is_cloud_sql:
                return None
            
            # URL encode user and password for safety
            user = quote(self.parent.postgres_user, safe='') if self.parent.postgres_user else ""
            password_part = f":{quote(self.parent.postgres_password, safe='')}" if self.parent.postgres_password else ""
            return (
                f"postgresql+asyncpg://"
                f"{user}{password_part}"
                f"@/{self.parent.postgres_db}"
                f"?host={self.parent.postgres_host}"
            )
        
        @property
        def sync_url(self) -> Optional[str]:
            """Sync URL for Cloud SQL Unix socket connection (for Alembic)."""
            if not self.is_cloud_sql:
                return None
            
            # URL encode user and password for safety
            user = quote(self.parent.postgres_user, safe='') if self.parent.postgres_user else ""
            password_part = f":{quote(self.parent.postgres_password, safe='')}" if self.parent.postgres_password else ""
            return (
                f"postgresql://"
                f"{user}{password_part}"
                f"@/{self.parent.postgres_db}"
                f"?host={self.parent.postgres_host}"
            )
        
        @property
        def async_url_psycopg(self) -> Optional[str]:
            """Async URL using psycopg driver for Cloud SQL."""
            if not self.is_cloud_sql:
                return None
            
            # URL encode user and password for safety
            user = quote(self.parent.postgres_user, safe='') if self.parent.postgres_user else ""
            password_part = f":{quote(self.parent.postgres_password, safe='')}" if self.parent.postgres_password else ""
            return (
                f"postgresql+psycopg://"
                f"{user}{password_part}"
                f"@/{self.parent.postgres_db}"
                f"?host={self.parent.postgres_host}"
            )
    
    class TCPBuilder:
        """Build standard TCP connection URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def has_config(self) -> bool:
            """Check if TCP configuration is available."""
            return bool(self.parent.postgres_host and not ("/cloudsql/" in self.parent.postgres_host))
        
        @property
        def async_url(self) -> Optional[str]:
            """Async URL for TCP connection without SSL."""
            if not self.has_config:
                return None
            
            # URL encode user and password for safety
            user = quote(self.parent.postgres_user or 'postgres', safe='')
            password_part = f":{quote(self.parent.postgres_password, safe='')}" if self.parent.postgres_password else ""
            return (
                f"postgresql+asyncpg://"
                f"{user}{password_part}"
                f"@{self.parent.postgres_host}"
                f":{self.parent.postgres_port}"
                f"/{self.parent.postgres_db or 'netra_dev'}"
            )
        
        @property
        def sync_url(self) -> Optional[str]:
            """Sync URL for TCP connection without SSL."""
            if not self.has_config:
                return None
            
            # URL encode user and password for safety
            user = quote(self.parent.postgres_user or 'postgres', safe='')
            password_part = f":{quote(self.parent.postgres_password, safe='')}" if self.parent.postgres_password else ""
            return (
                f"postgresql://"
                f"{user}{password_part}"
                f"@{self.parent.postgres_host}"
                f":{self.parent.postgres_port}"
                f"/{self.parent.postgres_db or 'netra_dev'}"
            )
        
        @property
        def async_url_with_ssl(self) -> Optional[str]:
            """Async URL for TCP connection with SSL required."""
            base_url = self.async_url
            if not base_url:
                return None
            # Properly append SSL parameter
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}sslmode=require"
        
        @property
        def sync_url_with_ssl(self) -> Optional[str]:
            """Sync URL for TCP connection with SSL required."""
            base_url = self.sync_url
            if not base_url:
                return None
            # Properly append SSL parameter
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}sslmode=require"
        
        @property
        def async_url_psycopg(self) -> Optional[str]:
            """Async URL using psycopg driver."""
            if not self.has_config:
                return None
            
            # URL encode user and password for safety
            user = quote(self.parent.postgres_user or 'postgres', safe='')
            password_part = f":{quote(self.parent.postgres_password, safe='')}" if self.parent.postgres_password else ""
            return (
                f"postgresql+psycopg://"
                f"{user}{password_part}"
                f"@{self.parent.postgres_host}"
                f":{self.parent.postgres_port}"
                f"/{self.parent.postgres_db or 'netra_dev'}"
            )
    
    class DevelopmentBuilder:
        """Build development environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def default_url(self) -> str:
            """Default development URL."""
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev"
        
        @property
        def default_sync_url(self) -> str:
            """Default development sync URL."""
            return "postgresql://postgres:postgres@localhost:5432/netra_dev"
        
        @property
        def auto_url(self) -> str:
            """Auto-select best URL for development."""
            # Try TCP config first
            if self.parent.tcp.has_config:
                return self.parent.tcp.async_url
            # Try DATABASE_URL
            if self.parent.database_url:
                return self.parent.database_url
            # Fall back to default
            return self.default_url
    
    class TestBuilder:
        """Build test environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def memory_url(self) -> str:
            """In-memory SQLite URL for fast tests."""
            return "sqlite+aiosqlite:///:memory:"
        
        @property
        def postgres_url(self) -> Optional[str]:
            """PostgreSQL URL for test environment."""
            if self.parent.tcp.has_config:
                # URL encode user and password for safety
                user = quote(self.parent.postgres_user or 'postgres', safe='')
                password_part = f":{quote(self.parent.postgres_password, safe='')}" if self.parent.postgres_password else ""
                return (
                    f"postgresql+asyncpg://"
                    f"{user}{password_part}"
                    f"@{self.parent.postgres_host}"
                    f":{self.parent.postgres_port}"
                    f"/{self.parent.postgres_db or 'netra_test'}"
                )
            return None
        
        @property
        def auto_url(self) -> str:
            """Auto-select best URL for test."""
            # Use memory if requested
            if self.parent.env.get("USE_MEMORY_DB") == "true":
                return self.memory_url
            # Try PostgreSQL config
            if self.postgres_url:
                return self.postgres_url
            # Default to memory
            return self.memory_url
    
    class DockerBuilder:
        """Build Docker environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def compose_url(self) -> str:
            """URL for Docker Compose environment."""
            # URL encode user and password for safety
            user = quote(self.parent.postgres_user or "postgres", safe='')
            password = quote(self.parent.postgres_password or "postgres", safe='')
            host = self.parent.postgres_host or "postgres"  # Docker service name
            port = self.parent.postgres_port or "5432"
            db = self.parent.postgres_db or "netra_dev"
            
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
        
        @property
        def compose_sync_url(self) -> str:
            """Sync URL for Docker Compose environment."""
            # URL encode user and password for safety
            user = quote(self.parent.postgres_user or "postgres", safe='')
            password = quote(self.parent.postgres_password or "postgres", safe='')
            host = self.parent.postgres_host or "postgres"  # Docker service name
            port = self.parent.postgres_port or "5432"
            db = self.parent.postgres_db or "netra_dev"
            
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    class StagingBuilder:
        """Build staging environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def auto_url(self) -> Optional[str]:
            """Auto-select best URL for staging."""
            # Prefer Cloud SQL
            if self.parent.cloud_sql.is_cloud_sql:
                return self.parent.cloud_sql.async_url
            # Use TCP with SSL
            if self.parent.tcp.has_config:
                return self.parent.tcp.async_url_with_ssl
            return None
        
        @property
        def auto_sync_url(self) -> Optional[str]:
            """Auto-select best sync URL for staging."""
            # Prefer Cloud SQL
            if self.parent.cloud_sql.is_cloud_sql:
                return self.parent.cloud_sql.sync_url
            # Use TCP with SSL
            if self.parent.tcp.has_config:
                return self.parent.tcp.sync_url_with_ssl
            return None
    
    class ProductionBuilder:
        """Build production environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def auto_url(self) -> Optional[str]:
            """Auto-select best URL for production."""
            # Prefer Cloud SQL
            if self.parent.cloud_sql.is_cloud_sql:
                return self.parent.cloud_sql.async_url
            # Use TCP with SSL
            if self.parent.tcp.has_config:
                return self.parent.tcp.async_url_with_ssl
            return None
        
        @property
        def auto_sync_url(self) -> Optional[str]:
            """Auto-select best sync URL for production."""
            # Prefer Cloud SQL
            if self.parent.cloud_sql.is_cloud_sql:
                return self.parent.cloud_sql.sync_url
            # Use TCP with SSL
            if self.parent.tcp.has_config:
                return self.parent.tcp.sync_url_with_ssl
            return None
    
    def get_url_for_environment(self, sync: bool = False) -> Optional[str]:
        """
        Get the appropriate database URL for current environment.
        
        Args:
            sync: If True, return synchronous URL (for Alembic, etc.)
        """
        if self.environment == "staging":
            return self.staging.auto_sync_url if sync else self.staging.auto_url
        elif self.environment == "production":
            return self.production.auto_sync_url if sync else self.production.auto_url
        elif self.environment == "test":
            return self.test.auto_url  # Test doesn't distinguish sync/async for SQLite
        else:  # development
            return self.development.default_sync_url if sync else self.development.auto_url
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate database configuration for current environment.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.environment in ["staging", "production"]:
            # Must have either Cloud SQL or TCP config
            if not self.cloud_sql.is_cloud_sql and not self.tcp.has_config:
                missing = []
                if not self.postgres_host:
                    missing.append("POSTGRES_HOST")
                if not self.postgres_user:
                    missing.append("POSTGRES_USER")
                if not self.postgres_db:
                    missing.append("POSTGRES_DB")
                if not self.postgres_password:
                    missing.append("POSTGRES_PASSWORD")
                
                return False, f"Missing required variables for {self.environment}: {', '.join(missing)}"
            
            # Validate credentials format for staging/production
            credential_validation = self._validate_credentials()
            if not credential_validation[0]:
                return credential_validation
        
        # Validate Cloud SQL format if present
        if self.cloud_sql.is_cloud_sql:
            if not self.postgres_host.startswith("/cloudsql/"):
                return False, f"Invalid Cloud SQL socket path: {self.postgres_host}"
            # Should be format: /cloudsql/PROJECT:REGION:INSTANCE
            parts = self.postgres_host.replace("/cloudsql/", "").split(":")
            if len(parts) != 3:
                return False, f"Invalid Cloud SQL format. Expected /cloudsql/PROJECT:REGION:INSTANCE"
        
        return True, ""
    
    def _validate_credentials(self) -> tuple[bool, str]:
        """
        Validate database credentials for known problematic patterns.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Known invalid users from production logs
        invalid_users = [
            "user_pr-4",  # Known problematic user from logs
            "user-pr-4",  # Similar pattern
        ]
        
        if self.postgres_user in invalid_users:
            return False, f"Invalid database user '{self.postgres_user}' - this user is known to cause authentication failures"
        
        # Validate user format patterns
        if self.postgres_user and re.match(r'^user[_-]pr[_-]\d+$', self.postgres_user):
            return False, f"Invalid database user pattern '{self.postgres_user}' - appears to be a malformed user identifier"
        
        # Check for placeholder or development credentials in production environments
        if self.environment in ["staging", "production"]:
            development_patterns = [
                "development_password",
                "dev_password", 
                "test_password",
                "password",
                "123456",
                "admin"
            ]
            
            if self.postgres_password and self.postgres_password.lower() in [p.lower() for p in development_patterns]:
                return False, f"Invalid password for {self.environment} environment - appears to be a development/test password"
            
            # Check for localhost in staging/production
            if self.postgres_host and self.postgres_host.lower() in ["localhost", "127.0.0.1"]:
                # Only allow localhost if specifically overridden for testing
                testing_override = self.env.get("ALLOW_LOCALHOST_IN_PRODUCTION", "false").lower() == "true"
                if not testing_override:
                    return False, f"Invalid host 'localhost' for {self.environment} environment - use actual database host"
        
        return True, ""
    
    def debug_info(self) -> Dict[str, Any]:
        """Get debug information about available URLs."""
        return {
            "environment": self.environment,
            "has_cloud_sql": self.cloud_sql.is_cloud_sql,
            "has_tcp_config": self.tcp.has_config,
            "postgres_host": self.postgres_host,
            "postgres_db": self.postgres_db,
            "available_urls": {
                "cloud_sql_async": self.cloud_sql.async_url is not None,
                "cloud_sql_sync": self.cloud_sql.sync_url is not None,
                "tcp_async": self.tcp.async_url is not None,
                "tcp_sync": self.tcp.sync_url is not None,
                "tcp_async_ssl": self.tcp.async_url_with_ssl is not None,
                "auto_url": self.get_url_for_environment() is not None,
            }
        }
    
    @staticmethod
    def mask_url_for_logging(database_url: Optional[str]) -> str:
        """
        Mask sensitive information in database URL for safe logging.
        
        Args:
            database_url: The database URL to mask
            
        Returns:
            A masked version safe for logging
        """
        if not database_url:
            return "NOT SET"
        
        # Handle Cloud SQL Unix socket URLs
        if "/cloudsql/" in database_url:
            # Format: postgresql+asyncpg://user:pass@/db?host=/cloudsql/project:region:instance
            if "://" in database_url:
                protocol, rest = database_url.split("://", 1)
                if "@" in rest:
                    # Extract the database and host parts
                    _, location = rest.split("@", 1)
                    if "?host=" in location:
                        db_part, host_part = location.split("?host=", 1)
                        return f"{protocol}://***@{db_part}?host={host_part}"
                    return f"{protocol}://***@{location}"
            return database_url  # Fallback if format is unexpected
        
        # Handle standard TCP URLs
        if "://" in database_url:
            protocol, rest = database_url.split("://", 1)
            if "@" in rest:
                # Mask the credentials
                _, host_part = rest.split("@", 1)
                return f"{protocol}://***@{host_part}"
            return database_url  # No credentials to mask
        
        # Handle SQLite memory URLs
        if "memory" in database_url.lower():
            return database_url  # No credentials in memory URLs
        
        # Unknown format - mask everything except protocol
        if "://" in database_url:
            protocol = database_url.split("://")[0]
            return f"{protocol}://{'*' * 10}"
        
        return "*" * 10  # Complete mask for unknown formats
    
    def get_safe_log_message(self) -> str:
        """
        Get a safe log message with current configuration details.
        
        Returns:
            A formatted string safe for logging with masked credentials
        """
        url = self.get_url_for_environment()
        masked_url = self.mask_url_for_logging(url)
        
        config_type = "NOT CONFIGURED"
        if self.cloud_sql.is_cloud_sql:
            config_type = "Cloud SQL"
        elif self.tcp.has_config:
            config_type = "TCP"
        elif url and "memory" in url:
            config_type = "Memory"
        elif url:
            config_type = "Custom"
        
        return f"Database URL ({self.environment}/{config_type}): {masked_url}"
    
    @staticmethod
    def normalize_postgres_url(url: str) -> str:
        """
        Normalize PostgreSQL URL to standard format.
        
        This method centralizes ALL URL normalization logic to prevent
        scattered normalization across services causing bugs.
        
        Args:
            url: Database URL to normalize
            
        Returns:
            Normalized PostgreSQL URL
        """
        if not url:
            return url
        
        # Convert old postgres:// to postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        # For Cloud SQL URLs, remove SSL parameters (not needed for Unix sockets)
        if "/cloudsql/" in url:
            import re
            url = re.sub(r'[?&]ssl(mode)?=[^&]*', '', url)
            url = url.rstrip('?&')
        
        return url
    
    @staticmethod
    def format_url_for_driver(url: str, driver: str) -> str:
        """
        Format database URL for specific driver.
        
        Args:
            url: Base PostgreSQL URL (should be normalized first)
            driver: Target driver ('asyncpg', 'psycopg2', 'psycopg', 'base')
            
        Returns:
            URL formatted for the specific driver
        """
        if not url:
            return url
        
        # First normalize the URL
        url = DatabaseURLBuilder.normalize_postgres_url(url)
        
        # Remove any existing driver prefix
        if "postgresql+" in url:
            url = re.sub(r'postgresql\+[^:]+://', 'postgresql://', url)
        
        # Apply the correct driver prefix
        if driver == 'asyncpg':
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # asyncpg doesn't support sslmode parameter directly
            if "sslmode=" in url:
                # Convert sslmode to ssl for asyncpg
                url = url.replace("sslmode=require", "ssl=require")
                url = url.replace("sslmode=disable", "ssl=disable")
                # Remove other sslmode values as asyncpg doesn't support them
                url = re.sub(r'[?&]sslmode=[^&]*', '', url)
                url = url.rstrip('?&')
        elif driver == 'psycopg2':
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            # psycopg2 uses sslmode parameter
            if "ssl=" in url and "sslmode=" not in url:
                url = url.replace("ssl=", "sslmode=")
        elif driver == 'psycopg':
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            # psycopg3 uses sslmode parameter
            if "ssl=" in url and "sslmode=" not in url:
                url = url.replace("ssl=", "sslmode=")
        elif driver == 'base':
            # Keep as postgresql:// for base/sync operations
            pass
        
        return url
    
    @staticmethod
    def validate_url_for_driver(url: str, driver: str) -> tuple[bool, str]:
        """
        Validate that a URL is correctly formatted for a specific driver.
        
        Args:
            url: Database URL to validate
            driver: Target driver to validate against
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL is empty"
        
        if driver == 'asyncpg':
            if not url.startswith("postgresql+asyncpg://"):
                return False, f"URL must start with postgresql+asyncpg:// for asyncpg driver"
            if "sslmode=" in url:
                return False, "asyncpg driver doesn't support sslmode parameter, use ssl= instead"
        elif driver == 'psycopg2':
            if not url.startswith("postgresql+psycopg2://"):
                return False, f"URL must start with postgresql+psycopg2:// for psycopg2 driver"
            if "ssl=" in url and "sslmode=" not in url:
                return False, "psycopg2 driver uses sslmode= parameter, not ssl="
        elif driver == 'psycopg':
            if not url.startswith("postgresql+psycopg://"):
                return False, f"URL must start with postgresql+psycopg:// for psycopg driver"
            if "ssl=" in url and "sslmode=" not in url:
                return False, "psycopg driver uses sslmode= parameter, not ssl="
        elif driver == 'base':
            if not url.startswith("postgresql://"):
                return False, f"URL must start with postgresql:// for base/sync operations"
        
        return True, ""
    
    # ===== EXTENSION HOOKS FOR FUTURE VERSIONS =====
    # These hooks allow for future extensibility without modifying core logic
    
    @staticmethod
    def register_driver_handler(driver_name: str, handler_func):
        """
        FUTURE HOOK: Register a custom driver handler.
        
        This allows new database drivers to be added without modifying
        the core DatabaseURLBuilder class. The handler function should
        accept a URL string and return a formatted URL string.
        
        Args:
            driver_name: Name of the driver
            handler_func: Function that formats URLs for this driver
        
        Example:
            def mysql_handler(url):
                # Custom MySQL URL formatting
                return formatted_url
            
            DatabaseURLBuilder.register_driver_handler('mysql', mysql_handler)
        """
        # Implementation would store handlers in a registry
        # For now, this is a placeholder for future extensibility
        raise NotImplementedError("Driver registration will be implemented when needed")
    
    @staticmethod
    def register_normalization_rule(pattern: str, replacement):
        """
        FUTURE HOOK: Register custom URL normalization rules.
        
        This allows for environment-specific or deployment-specific
        normalization rules without modifying core logic.
        
        Args:
            pattern: Regex pattern to match
            replacement: Replacement string or function
        
        Example:
            # Replace internal hostnames with external ones
            DatabaseURLBuilder.register_normalization_rule(
                r'internal-db\.example\.com',
                'external-db.example.com'
            )
        """
        # Implementation would maintain a list of normalization rules
        # For now, this is a placeholder for future extensibility
        raise NotImplementedError("Normalization rule registration will be implemented when needed")
    
    @staticmethod
    def get_driver_requirements(driver: str) -> dict:
        """
        FUTURE HOOK: Get requirements for a specific driver.
        
        This provides a centralized place to document and retrieve
        driver-specific requirements, parameter formats, and constraints.
        
        Args:
            driver: Driver name
            
        Returns:
            Dictionary with driver requirements
        """
        requirements = {
            'asyncpg': {
                'ssl_parameter': 'ssl',
                'supports_sslmode': False,
                'supports_unix_socket': True,
                'prefix': 'postgresql+asyncpg://'
            },
            'psycopg2': {
                'ssl_parameter': 'sslmode',
                'supports_sslmode': True,
                'supports_unix_socket': True,
                'prefix': 'postgresql+psycopg2://'
            },
            'psycopg': {
                'ssl_parameter': 'sslmode',
                'supports_sslmode': True,
                'supports_unix_socket': True,
                'prefix': 'postgresql+psycopg://'
            },
            'base': {
                'ssl_parameter': 'sslmode',
                'supports_sslmode': True,
                'supports_unix_socket': True,
                'prefix': 'postgresql://'
            }
        }
        return requirements.get(driver, {})