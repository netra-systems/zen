"""
Test Settings Configuration
Centralized test configuration and settings management.
Provides type-safe configuration for different test scenarios.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DatabaseTestSettings:
    """Database-specific test settings"""
    url: str = "sqlite+aiosqlite:///:memory:"
    echo_sql: bool = False
    pool_size: int = 1
    max_overflow: int = 0
    isolation_level: str = "SERIALIZABLE"
    use_transactions: bool = True


@dataclass
class RedisTestSettings:
    """Redis-specific test settings"""
    url: str = "redis://localhost:6379/15"
    host: str = "localhost"
    port: int = 6379
    db: int = 15
    password: Optional[str] = None
    decode_responses: bool = True
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0


@dataclass
class AuthTestSettings:
    """Authentication-specific test settings"""
    jwt_secret: str = "test-jwt-secret-key-that-is-long-enough-for-testing-purposes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    session_expire_hours: int = 24
    max_sessions_per_user: int = 5
    enable_rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60


@dataclass
class OAuthTestSettings:
    """OAuth provider test settings"""
    google_client_id: str = "test-google-client-id.apps.googleusercontent.com"
    google_client_secret: str = "test-google-client-secret"
    github_client_id: str = "test-github-client-id"
    github_client_secret: str = "test-github-client-secret"
    redirect_url: str = "http://localhost:8081/auth/callback"
    allowed_domains: List[str] = field(default_factory=lambda: ["example.com", "test.com"])


@dataclass
class ServiceTestSettings:
    """Service URL test settings"""
    auth_service_url: str = "http://localhost:8081"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    cors_origins: List[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:3001"]
    )
    allowed_hosts: List[str] = field(
        default_factory=lambda: ["localhost", "127.0.0.1", "0.0.0.0"]
    )


@dataclass
class LoggingTestSettings:
    """Logging configuration for tests"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_sql_logging: bool = False
    enable_request_logging: bool = False
    log_file: Optional[Path] = None


@dataclass
class TestSettings:
    """Main test settings configuration"""
    environment: str = "test"
    debug: bool = True
    testing: bool = True
    
    # Component settings
    database: DatabaseTestSettings = field(default_factory=DatabaseTestSettings)
    redis: RedisTestSettings = field(default_factory=RedisTestSettings)
    auth: AuthTestSettings = field(default_factory=AuthTestSettings)
    oauth: OAuthTestSettings = field(default_factory=OAuthTestSettings)
    services: ServiceTestSettings = field(default_factory=ServiceTestSettings)
    logging: LoggingTestSettings = field(default_factory=LoggingTestSettings)
    
    # Test execution settings
    parallel_tests: bool = True
    test_timeout: int = 30
    cleanup_after_test: bool = True
    preserve_test_data: bool = False
    
    # Coverage settings
    coverage_enabled: bool = True
    coverage_min_percentage: float = 90.0
    coverage_report_dir: Optional[Path] = None
    
    @classmethod
    def for_unit_tests(cls) -> "TestSettings":
        """Settings optimized for unit tests"""
        settings = cls()
        settings.logging.level = "WARNING"
        settings.database.echo_sql = False
        settings.auth.enable_rate_limiting = False
        settings.parallel_tests = True
        return settings
    
    @classmethod
    def for_integration_tests(cls) -> "TestSettings":
        """Settings optimized for integration tests"""
        settings = cls()
        settings.logging.level = "INFO"
        settings.database.echo_sql = False
        settings.logging.enable_request_logging = True
        settings.parallel_tests = False  # Integration tests may conflict
        settings.test_timeout = 60
        return settings
    
    @classmethod
    def for_e2e_tests(cls) -> "TestSettings":
        """Settings optimized for E2E tests"""
        settings = cls()
        settings.logging.level = "DEBUG"
        settings.database.echo_sql = True
        settings.logging.enable_request_logging = True
        settings.logging.enable_sql_logging = True
        settings.parallel_tests = False
        settings.test_timeout = 120
        settings.preserve_test_data = True
        return settings
    
    @classmethod
    def for_performance_tests(cls) -> "TestSettings":
        """Settings optimized for performance tests"""
        settings = cls()
        settings.logging.level = "ERROR"  # Minimize logging overhead
        settings.database.echo_sql = False
        settings.logging.enable_request_logging = False
        settings.parallel_tests = True
        settings.test_timeout = 300
        settings.coverage_enabled = False  # Disable for performance
        return settings
    
    def to_env_dict(self) -> Dict[str, str]:
        """Convert settings to environment variables dictionary"""
        return {
            # General
            "ENVIRONMENT": self.environment,
            "DEBUG": str(self.debug).lower(),
            "TESTING": str(self.testing).lower(),
            
            # Database
            "DATABASE_URL": self.database.url,
            "DATABASE_ECHO_SQL": str(self.database.echo_sql).lower(),
            
            # Redis
            "REDIS_URL": self.redis.url,
            "REDIS_HOST": self.redis.host,
            "REDIS_PORT": str(self.redis.port),
            "REDIS_DB": str(self.redis.db),
            
            # Auth
            "JWT_SECRET": self.auth.jwt_secret,
            "JWT_ALGORITHM": self.auth.jwt_algorithm,
            "ACCESS_TOKEN_EXPIRE_MINUTES": str(self.auth.access_token_expire_minutes),
            "REFRESH_TOKEN_EXPIRE_DAYS": str(self.auth.refresh_token_expire_days),
            "SESSION_EXPIRE_HOURS": str(self.auth.session_expire_hours),
            "MAX_SESSIONS_PER_USER": str(self.auth.max_sessions_per_user),
            "RATE_LIMITING_ENABLED": str(self.auth.enable_rate_limiting).lower(),
            
            # OAuth
            "GOOGLE_CLIENT_ID": self.oauth.google_client_id,
            "GOOGLE_CLIENT_SECRET": self.oauth.google_client_secret,
            "GITHUB_CLIENT_ID": self.oauth.github_client_id,
            "GITHUB_CLIENT_SECRET": self.oauth.github_client_secret,
            
            # Services
            "AUTH_SERVICE_URL": self.services.auth_service_url,
            "FRONTEND_URL": self.services.frontend_url,
            "BACKEND_URL": self.services.backend_url,
            "CORS_ORIGINS": ",".join(self.services.cors_origins),
            "ALLOWED_HOSTS": ",".join(self.services.allowed_hosts),
            
            # Logging
            "LOG_LEVEL": self.logging.level,
        }
    
    def apply_to_environment(self):
        """Apply settings to environment variables"""
        import os
        env_dict = self.to_env_dict()
        for key, value in env_dict.items():
            os.environ[key] = value