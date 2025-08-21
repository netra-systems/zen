"""
Shared test infrastructure for critical missing integration tests.
Provides L2-L3 realism level testing with containerized services.
"""

from netra_backend.tests.containerized_services import (
    PostgreSQLContainer,
    ClickHouseContainer,
    RedisContainer,
    ServiceOrchestrator
)

__all__ = [
    'PostgreSQLContainer',
    'ClickHouseContainer',
    'RedisContainer',
    'ServiceOrchestrator'
]