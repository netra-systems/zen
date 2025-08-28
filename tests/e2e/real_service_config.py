"""Real Service Configuration for E2E Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Reliability
- Value Impact: Provides intelligent service configuration based on availability
- Strategic Impact: Enables seamless switching between real and mock services

This module provides intelligent configuration for E2E tests based on actual
service availability, not just environment flags.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional, Any, Union
from urllib.parse import urlparse

from tests.e2e.service_availability import ServiceAvailability, get_service_availability

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration with fallback options."""
    
    postgres_url: str
    redis_url: str
    clickhouse_url: Optional[str] = None
    
    # Metadata
    using_real_postgres: bool = False
    using_real_redis: bool = False  
    using_real_clickhouse: bool = False
    
    @property
    def is_using_real_databases(self) -> bool:
        """Check if using real databases."""
        return self.using_real_postgres and self.using_real_redis


@dataclass
class LLMConfig:
    """LLM service configuration."""
    
    use_real_llm: bool
    available_providers: list
    primary_provider: Optional[str] = None
    
    # API Keys (masked for logging)
    openai_available: bool = False
    anthropic_available: bool = False


@dataclass
class RealServiceConfig:
    """Complete real service configuration for E2E tests."""
    
    # Service availability flags
    use_real_services: bool
    use_real_llm: bool
    
    # Configurations
    database: DatabaseConfig
    llm: LLMConfig
    
    # Service availability details
    service_availability: ServiceAvailability
    
    @property
    def summary(self) -> Dict[str, Any]:
        """Get configuration summary."""
        return {
            "use_real_services": self.use_real_services,
            "use_real_llm": self.use_real_llm,
            "database": {
                "postgres": self.database.using_real_postgres,
                "redis": self.database.using_real_redis,
                "clickhouse": self.database.using_real_clickhouse,
            },
            "llm": {
                "enabled": self.llm.use_real_llm,
                "providers": self.llm.available_providers,
                "primary": self.llm.primary_provider,
            }
        }


class RealServiceConfigManager:
    """Manages real service configuration based on availability."""
    
    def __init__(self):
        """Initialize real service config manager."""
        self.logger = logging.getLogger(f"{__name__}.RealServiceConfigManager")
        self._cached_config: Optional[RealServiceConfig] = None
    
    async def get_config(self, force_refresh: bool = False) -> RealServiceConfig:
        """Get real service configuration.
        
        Args:
            force_refresh: Force refresh of service availability check
            
        Returns:
            RealServiceConfig with current configuration
        """
        if self._cached_config and not force_refresh:
            return self._cached_config
        
        # Get current service availability
        availability = await get_service_availability()
        
        # Build database configuration
        database_config = self._build_database_config(availability)
        
        # Build LLM configuration
        llm_config = self._build_llm_config(availability)
        
        # Create complete configuration
        config = RealServiceConfig(
            use_real_services=availability.use_real_services,
            use_real_llm=availability.use_real_llm,
            database=database_config,
            llm=llm_config,
            service_availability=availability
        )
        
        self._cached_config = config
        self.logger.info(f"Real service configuration: {config.summary}")
        
        return config
    
    def _build_database_config(self, availability: ServiceAvailability) -> DatabaseConfig:
        """Build database configuration based on availability.
        
        Args:
            availability: Current service availability
            
        Returns:
            DatabaseConfig with appropriate settings
        """
        # PostgreSQL configuration - fail if not available when required
        if availability.use_real_services:
            if not availability.postgresql.available:
                raise RuntimeError("PostgreSQL service is not available for E2E tests")
            postgres_url = self._get_real_postgres_url(availability)
            using_real_postgres = True
        else:
            postgres_url = self._get_test_postgres_url()
            using_real_postgres = False
        
        # Redis configuration - fail if not available when required
        if availability.use_real_services:
            if not availability.redis.available:
                raise RuntimeError("Redis service is not available for E2E tests")
            redis_url = self._get_real_redis_url(availability)
            using_real_redis = True
        else:
            redis_url = self._get_test_redis_url()
            using_real_redis = False
        
        # ClickHouse configuration - fail if not available when required
        if availability.use_real_services:
            if not availability.clickhouse.available:
                raise RuntimeError("ClickHouse service is not available for E2E tests")
            clickhouse_url = self._get_real_clickhouse_url(availability)
            using_real_clickhouse = True
        else:
            clickhouse_url = self._get_test_clickhouse_url()
            using_real_clickhouse = False
        
        return DatabaseConfig(
            postgres_url=postgres_url,
            redis_url=redis_url,
            clickhouse_url=clickhouse_url,
            using_real_postgres=using_real_postgres,
            using_real_redis=using_real_redis,
            using_real_clickhouse=using_real_clickhouse
        )
    
    def _build_llm_config(self, availability: ServiceAvailability) -> LLMConfig:
        """Build LLM configuration based on availability.
        
        Args:
            availability: Current service availability
            
        Returns:
            LLMConfig with appropriate settings
        """
        available_providers = []
        primary_provider = None
        
        if availability.openai_api.available:
            available_providers.append("openai")
            if not primary_provider:
                primary_provider = "openai"
        
        if availability.anthropic_api.available:
            available_providers.append("anthropic")
            if not primary_provider:
                primary_provider = "anthropic"
        
        use_real_llm = (
            availability.use_real_llm and 
            len(available_providers) > 0
        )
        
        return LLMConfig(
            use_real_llm=use_real_llm,
            available_providers=available_providers,
            primary_provider=primary_provider,
            openai_available=availability.openai_api.available,
            anthropic_available=availability.anthropic_api.available
        )
    
    def _get_real_postgres_url(self, availability: ServiceAvailability) -> str:
        """Get real PostgreSQL URL."""
        # Prefer environment variables, then use connection info
        env_urls = [
            os.getenv("DATABASE_URL"),
            os.getenv("POSTGRES_URL"),
        ]
        
        for url in env_urls:
            if url:
                return url
        
        # Build from connection info if available
        conn_info = availability.postgresql.connection_info
        if conn_info:
            host = conn_info.get("host", "localhost")
            port = conn_info.get("port", 5432)
            database = conn_info.get("database", "netra_dev")
            # Use generic credentials for constructed URL
            return f"postgresql://postgres:password@{host}:{port}/{database}"
        
        # Fallback
        return "postgresql://postgres:password@localhost:5432/netra_dev"
    
    def _get_test_postgres_url(self) -> str:
        """Get test PostgreSQL URL (SQLite fallback)."""
        # For tests, prefer in-memory or file-based SQLite
        test_db_url = os.getenv("TEST_DATABASE_URL")
        if test_db_url:
            return test_db_url
        
        # Default to SQLite for testing
        return "sqlite+aiosqlite:///:memory:"
    
    def _get_real_redis_url(self, availability: ServiceAvailability) -> str:
        """Get real Redis URL."""
        env_urls = [
            os.getenv("REDIS_URL"),
            os.getenv("REDIS_CONNECTION_STRING"),
        ]
        
        for url in env_urls:
            if url:
                return url
        
        # Build from connection info
        conn_info = availability.redis.connection_info
        if conn_info:
            host = conn_info.get("host", "localhost")
            port = conn_info.get("port", 6379)
            return f"redis://{host}:{port}"
        
        # Fallback
        return "redis://localhost:6379"
    
    def _get_test_redis_url(self) -> str:
        """Get test Redis URL (in-memory fallback)."""
        # For tests, use fakeredis or in-memory Redis
        test_redis_url = os.getenv("TEST_REDIS_URL")
        if test_redis_url:
            return test_redis_url
        
        # Default to in-memory Redis for testing
        return "redis://localhost:6380/0"  # Different port to avoid conflicts
    
    def _get_real_clickhouse_url(self, availability: ServiceAvailability) -> str:
        """Get real ClickHouse URL."""
        env_urls = [
            os.getenv("CLICKHOUSE_URL"),
            os.getenv("CLICKHOUSE_CONNECTION_STRING"),
        ]
        
        for url in env_urls:
            if url:
                return url
        
        # Build from connection info
        conn_info = availability.clickhouse.connection_info
        if conn_info:
            host = conn_info.get("host", "localhost")
            port = conn_info.get("port", 8123)
            secure = conn_info.get("secure", False)
            protocol = "clickhouses" if secure else "clickhouse"
            return f"{protocol}://{host}:{port}"
        
        # Fallback
        return "clickhouse://localhost:8123"
    
    def _get_test_clickhouse_url(self) -> str:
        """Get test ClickHouse URL."""
        # For tests, use explicitly configured test ClickHouse
        test_ch_url = os.getenv("TEST_CLICKHOUSE_URL")
        if test_ch_url:
            return test_ch_url
        
        # No fallback - must be explicitly configured
        raise RuntimeError("TEST_CLICKHOUSE_URL not configured for test environment")


class ServiceConfigHelper:
    """Helper methods for service configuration in tests."""
    
    @staticmethod
    async def should_use_real_databases() -> bool:
        """Check if tests should use real databases."""
        config = await RealServiceConfigManager().get_config()
        return config.database.is_using_real_databases
    
    @staticmethod
    async def should_use_real_llm() -> bool:
        """Check if tests should use real LLM APIs."""
        config = await RealServiceConfigManager().get_config()
        return config.llm.use_real_llm
    
    @staticmethod
    async def get_database_url(service: str = "postgres") -> str:
        """Get database URL for specified service.
        
        Args:
            service: Database service name ("postgres", "redis", "clickhouse")
            
        Returns:
            Connection URL for the service
        """
        config = await RealServiceConfigManager().get_config()
        
        if service.lower() in ["postgres", "postgresql"]:
            return config.database.postgres_url
        elif service.lower() == "redis":
            return config.database.redis_url
        elif service.lower() == "clickhouse":
            return config.database.clickhouse_url or "clickhouse://localhost:8123"
        else:
            raise ValueError(f"Unknown database service: {service}")
    
    @staticmethod
    async def get_llm_provider() -> Optional[str]:
        """Get primary LLM provider for testing.
        
        Returns:
            Primary LLM provider name or None if no real LLM available
        """
        config = await RealServiceConfigManager().get_config()
        return config.llm.primary_provider if config.llm.use_real_llm else None
    
    @staticmethod
    async def skip_test_if_no_real_services() -> str:
        """Get skip reason if real services not available.
        
        Returns:
            Skip reason string or empty string if services available
        """
        config = await RealServiceConfigManager().get_config()
        
        if config.use_real_services and not config.database.is_using_real_databases:
            return "Real services requested but databases not available"
        
        return ""
    
    @staticmethod
    async def skip_test_if_no_real_llm() -> str:
        """Get skip reason if real LLM not available.
        
        Returns:
            Skip reason string or empty string if LLM available
        """
        config = await RealServiceConfigManager().get_config()
        
        if config.use_real_llm and not config.llm.use_real_llm:
            return "Real LLM requested but no LLM APIs available"
        
        return ""


# Convenience functions
async def get_real_service_config(force_refresh: bool = False) -> RealServiceConfig:
    """Get real service configuration.
    
    Args:
        force_refresh: Force refresh of service availability
        
    Returns:
        RealServiceConfig with current settings
    """
    manager = RealServiceConfigManager()
    return await manager.get_config(force_refresh=force_refresh)


# Environment variable setters for backward compatibility
def set_environment_for_real_services(config: RealServiceConfig) -> None:
    """Set environment variables based on real service config.
    
    Args:
        config: Real service configuration
    """
    # Database URLs
    os.environ["DATABASE_URL"] = config.database.postgres_url
    os.environ["REDIS_URL"] = config.database.redis_url
    if config.database.clickhouse_url:
        os.environ["CLICKHOUSE_URL"] = config.database.clickhouse_url
    
    # Service flags
    os.environ["USE_REAL_SERVICES"] = str(config.use_real_services).lower()
    os.environ["TEST_USE_REAL_LLM"] = str(config.llm.use_real_llm).lower()
    os.environ["ENABLE_REAL_LLM_TESTING"] = str(config.llm.use_real_llm).lower()
    
    # LLM provider
    if config.llm.primary_provider:
        os.environ["TEST_LLM_PROVIDER"] = config.llm.primary_provider


# CLI interface for testing
async def main():
    """CLI interface for testing real service configuration."""
    import json
    
    print("Real Service Configuration")
    print("=" * 50)
    
    manager = RealServiceConfigManager()
    config = await manager.get_config()
    
    # Print configuration summary
    print(json.dumps(config.summary, indent=2))
    
    print("\nDatabase Configuration:")
    print(f"  PostgreSQL: {config.database.postgres_url}")
    print(f"  Redis: {config.database.redis_url}")
    print(f"  ClickHouse: {config.database.clickhouse_url}")
    
    print("\nLLM Configuration:")
    print(f"  Use Real LLM: {config.llm.use_real_llm}")
    print(f"  Available Providers: {config.llm.available_providers}")
    print(f"  Primary Provider: {config.llm.primary_provider}")
    
    # Test helper functions
    print("\nHelper Function Results:")
    print(f"  should_use_real_databases(): {await ServiceConfigHelper.should_use_real_databases()}")
    print(f"  should_use_real_llm(): {await ServiceConfigHelper.should_use_real_llm()}")
    print(f"  get_database_url('postgres'): {await ServiceConfigHelper.get_database_url('postgres')}")
    print(f"  get_llm_provider(): {await ServiceConfigHelper.get_llm_provider()}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())