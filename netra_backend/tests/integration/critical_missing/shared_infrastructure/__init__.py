"""
Shared test infrastructure for critical missing integration tests.
Provides L2-L3 realism level testing with containerized services.
"""

from .integration.critical_missing.shared_infrastructure.containerized_services import (
    ClickHouseContainer,
    PostgreSQLContainer,
    RedisContainer,
    ServiceOrchestrator,
)

__all__ = [
    'PostgreSQLContainer',
    'ClickHouseContainer',
    'RedisContainer',
    'ServiceOrchestrator'
]