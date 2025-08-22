"""
Shared test infrastructure for critical missing integration tests.
Provides L2-L3 realism level testing with containerized services.
"""

from tests.containerized_services import (
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