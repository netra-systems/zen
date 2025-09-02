"""
Netra Factory Layer - User Context Isolation Patterns

This module implements Factory patterns for data access isolation following
the USER_CONTEXT_ARCHITECTURE.md patterns. Each factory creates user-scoped
contexts that eliminate shared state and ensure proper isolation.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Complete user isolation for multi-tenant data security
- Value Impact: Prevents data leakage between users, enables enterprise deployment
- Revenue Impact: Critical for Enterprise segments requiring strict data isolation

Key Factories:
- DataAccessFactory: Base factory pattern for data layer isolation
- ClickHouseAccessFactory: User-scoped ClickHouse contexts  
- RedisAccessFactory: User-scoped Redis contexts
- ClickHouseFactory: User-isolated ClickHouse instances with connection pooling
- RedisFactory: User-isolated Redis instances with connection management
"""

from netra_backend.app.factories.data_access_factory import (
    DataAccessFactory,
    ClickHouseAccessFactory, 
    RedisAccessFactory
)
from netra_backend.app.factories.clickhouse_factory import (
    ClickHouseFactory,
    UserClickHouseClient,
    get_clickhouse_factory
)
from netra_backend.app.factories.redis_factory import (
    RedisFactory,
    UserRedisClient,
    get_redis_factory
)

__all__ = [
    "DataAccessFactory",
    "ClickHouseAccessFactory",
    "RedisAccessFactory",
    "ClickHouseFactory",
    "UserClickHouseClient", 
    "get_clickhouse_factory",
    "RedisFactory",
    "UserRedisClient",
    "get_redis_factory"
]