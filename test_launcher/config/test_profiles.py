"""
Test configuration profiles for different testing scenarios.

Provides optimized configurations for unit, integration, and E2E testing.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment


class TestProfile(Enum):
    """Test execution profiles optimized for different test types."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    SMOKE = "smoke"
    FULL = "full"


class IsolationLevel(Enum):
    """Service isolation levels for testing."""
    NONE = "none"  # No isolation, use shared services
    PARTIAL = "partial"  # Isolate databases only
    FULL = "full"  # Complete isolation with separate containers


@dataclass
class ServiceConfig:
    """Configuration for a single service."""
    name: str
    enabled: bool
    port: Optional[int] = None
    container_name: Optional[str] = None
    healthcheck_endpoint: Optional[str] = None
    startup_timeout: int = 30
    environment: Dict[str, str] = None
    
    def __post_init__(self):
        if self.environment is None:
            self.environment = {}


@dataclass
class TestConfig:
    """Complete test launcher configuration."""
    profile: TestProfile
    isolation_level: IsolationLevel
    services: Dict[str, ServiceConfig]
    parallel_execution: bool = False
    fail_fast: bool = True
    timeout_seconds: int = 600
    coverage_enabled: bool = False
    real_llm: bool = False
    real_services: bool = False
    verbose: bool = False
    cleanup_on_exit: bool = True
    docker_network: Optional[str] = None
    resource_limits: Optional[Dict[str, any]] = None
    
    @classmethod
    def for_profile(cls, profile: TestProfile) -> "TestConfig":
        """Create configuration for a specific test profile."""
        configs = {
            TestProfile.UNIT: cls._unit_config(),
            TestProfile.INTEGRATION: cls._integration_config(),
            TestProfile.E2E: cls._e2e_config(),
            TestProfile.PERFORMANCE: cls._performance_config(),
            TestProfile.SECURITY: cls._security_config(),
            TestProfile.SMOKE: cls._smoke_config(),
            TestProfile.FULL: cls._full_config(),
        }
        return configs[profile]
    
    @classmethod
    def _unit_config(cls) -> "TestConfig":
        """Configuration for unit tests - no external services."""
        return cls(
            profile=TestProfile.UNIT,
            isolation_level=IsolationLevel.NONE,
            services={},
            parallel_execution=True,
            fail_fast=True,
            timeout_seconds=180,
            coverage_enabled=True,
            real_llm=False,
            real_services=False,
        )
    
    @classmethod
    def _integration_config(cls) -> "TestConfig":
        """Configuration for integration tests - database and cache only."""
        return cls(
            profile=TestProfile.INTEGRATION,
            isolation_level=IsolationLevel.PARTIAL,
            services={
                "postgres": ServiceConfig(
                    name="postgres",
                    enabled=True,
                    port=5434,  # Test-specific port
                    container_name="netra-test-postgres",
                    healthcheck_endpoint="postgresql://test:test@localhost:5434/netra_test",
                    startup_timeout=30,
                    environment={
                        "POSTGRES_USER": "test",
                        "POSTGRES_PASSWORD": "test",
                        "POSTGRES_DB": "netra_test"
                    }
                ),
                "redis": ServiceConfig(
                    name="redis",
                    enabled=True,
                    port=6381,  # Test-specific port
                    container_name="netra-test-redis",
                    healthcheck_endpoint="redis://localhost:6381/1",
                    startup_timeout=10,
                ),
                "clickhouse": ServiceConfig(
                    name="clickhouse",
                    enabled=False,  # Not needed for most integration tests
                    port=8124,
                    container_name="netra-test-clickhouse",
                ),
            },
            parallel_execution=False,
            fail_fast=True,
            timeout_seconds=300,
            coverage_enabled=True,
            real_llm=False,
            real_services=True,
        )
    
    @classmethod
    def _e2e_config(cls) -> "TestConfig":
        """Configuration for E2E tests - full stack with real services."""
        return cls(
            profile=TestProfile.E2E,
            isolation_level=IsolationLevel.FULL,
            services={
                "postgres": ServiceConfig(
                    name="postgres",
                    enabled=True,
                    port=5434,
                    container_name="netra-test-postgres",
                    healthcheck_endpoint="postgresql://test:test@localhost:5434/netra_test",
                    startup_timeout=30,
                    environment={
                        "POSTGRES_USER": "test",
                        "POSTGRES_PASSWORD": "test",
                        "POSTGRES_DB": "netra_test"
                    }
                ),
                "redis": ServiceConfig(
                    name="redis",
                    enabled=True,
                    port=6381,
                    container_name="netra-test-redis",
                    healthcheck_endpoint="redis://localhost:6381/1",
                    startup_timeout=10,
                ),
                "clickhouse": ServiceConfig(
                    name="clickhouse",
                    enabled=True,
                    port=8124,
                    container_name="netra-test-clickhouse",
                    healthcheck_endpoint="http://localhost:8124",
                    startup_timeout=30,
                    environment={
                        "CLICKHOUSE_DB": "netra_test",
                        "CLICKHOUSE_USER": "test",
                        "CLICKHOUSE_PASSWORD": "test"
                    }
                ),
                "backend": ServiceConfig(
                    name="backend",
                    enabled=True,
                    port=8001,
                    healthcheck_endpoint="http://localhost:8001/health/ready",
                    startup_timeout=60,
                ),
                "auth": ServiceConfig(
                    name="auth",
                    enabled=True,
                    port=8082,
                    healthcheck_endpoint="http://localhost:8082/auth/config",
                    startup_timeout=30,
                ),
                "frontend": ServiceConfig(
                    name="frontend",
                    enabled=True,
                    port=3001,
                    healthcheck_endpoint="http://localhost:3001",
                    startup_timeout=90,
                ),
            },
            parallel_execution=False,
            fail_fast=False,  # Continue running to gather more info
            timeout_seconds=1800,  # 30 minutes for E2E
            coverage_enabled=False,  # Too slow for E2E
            real_llm=True,  # Per CLAUDE.md - real LLM for E2E
            real_services=True,
            docker_network="netra-test-network",
        )
    
    @classmethod
    def _performance_config(cls) -> "TestConfig":
        """Configuration for performance tests."""
        return cls(
            profile=TestProfile.PERFORMANCE,
            isolation_level=IsolationLevel.PARTIAL,
            services={
                "postgres": ServiceConfig(
                    name="postgres",
                    enabled=True,
                    port=5434,
                    container_name="netra-test-postgres",
                    startup_timeout=30,
                ),
                "redis": ServiceConfig(
                    name="redis",
                    enabled=True,
                    port=6381,
                    container_name="netra-test-redis",
                    startup_timeout=10,
                ),
                "clickhouse": ServiceConfig(
                    name="clickhouse",
                    enabled=True,
                    port=8124,
                    container_name="netra-test-clickhouse",
                    startup_timeout=30,
                ),
            },
            parallel_execution=False,
            fail_fast=False,
            timeout_seconds=3600,  # 1 hour for performance tests
            coverage_enabled=False,
            real_llm=False,  # Mock LLM for consistent performance metrics
            real_services=True,
            resource_limits={
                "cpu_limit": "2.0",
                "memory_limit": "4g",
            }
        )
    
    @classmethod
    def _security_config(cls) -> "TestConfig":
        """Configuration for security tests."""
        return cls(
            profile=TestProfile.SECURITY,
            isolation_level=IsolationLevel.FULL,
            services={
                "postgres": ServiceConfig(
                    name="postgres",
                    enabled=True,
                    port=5434,
                    container_name="netra-test-postgres",
                    startup_timeout=30,
                ),
                "auth": ServiceConfig(
                    name="auth",
                    enabled=True,
                    port=8082,
                    healthcheck_endpoint="http://localhost:8082/auth/config",
                    startup_timeout=30,
                ),
            },
            parallel_execution=False,
            fail_fast=True,
            timeout_seconds=600,
            coverage_enabled=True,
            real_llm=False,
            real_services=True,
        )
    
    @classmethod
    def _smoke_config(cls) -> "TestConfig":
        """Configuration for smoke tests - minimal quick validation."""
        return cls(
            profile=TestProfile.SMOKE,
            isolation_level=IsolationLevel.NONE,
            services={
                "postgres": ServiceConfig(
                    name="postgres",
                    enabled=True,
                    port=5434,
                    container_name="netra-test-postgres",
                    startup_timeout=15,
                ),
                "redis": ServiceConfig(
                    name="redis",
                    enabled=True,
                    port=6381,
                    container_name="netra-test-redis",
                    startup_timeout=5,
                ),
            },
            parallel_execution=True,
            fail_fast=True,
            timeout_seconds=120,
            coverage_enabled=False,
            real_llm=False,
            real_services=True,
        )
    
    @classmethod
    def _full_config(cls) -> "TestConfig":
        """Configuration for full test suite - everything enabled."""
        return cls(
            profile=TestProfile.FULL,
            isolation_level=IsolationLevel.FULL,
            services={
                "postgres": ServiceConfig(
                    name="postgres",
                    enabled=True,
                    port=5434,
                    container_name="netra-test-postgres",
                    startup_timeout=30,
                ),
                "redis": ServiceConfig(
                    name="redis",
                    enabled=True,
                    port=6381,
                    container_name="netra-test-redis",
                    startup_timeout=10,
                ),
                "clickhouse": ServiceConfig(
                    name="clickhouse",
                    enabled=True,
                    port=8124,
                    container_name="netra-test-clickhouse",
                    startup_timeout=30,
                ),
                "backend": ServiceConfig(
                    name="backend",
                    enabled=True,
                    port=8001,
                    healthcheck_endpoint="http://localhost:8001/health/ready",
                    startup_timeout=60,
                ),
                "auth": ServiceConfig(
                    name="auth",
                    enabled=True,
                    port=8082,
                    healthcheck_endpoint="http://localhost:8082/auth/config",
                    startup_timeout=30,
                ),
                "frontend": ServiceConfig(
                    name="frontend",
                    enabled=True,
                    port=3001,
                    healthcheck_endpoint="http://localhost:3001",
                    startup_timeout=90,
                ),
            },
            parallel_execution=False,
            fail_fast=False,
            timeout_seconds=7200,  # 2 hours for full suite
            coverage_enabled=True,
            real_llm=True,
            real_services=True,
            docker_network="netra-test-network",
        )
    
    def get_required_services(self) -> List[str]:
        """Get list of required service names."""
        return [name for name, config in self.services.items() if config.enabled]
    
    def get_service_ports(self) -> Dict[str, int]:
        """Get mapping of service names to ports."""
        return {
            name: config.port 
            for name, config in self.services.items() 
            if config.enabled and config.port
        }