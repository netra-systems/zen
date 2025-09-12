"""Database-specific types and configurations.

Core types for database operations, configurations, and metrics.
All functions  <= 8 lines, file  <= 300 lines.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class DatabaseType(Enum):
    """Types of databases."""
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    REDIS = "redis"


class PoolHealth(Enum):
    """Database pool health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    timeout: float = 30.0
    retry_attempts: int = 3


@dataclass
class PoolMetrics:
    """Metrics for database connection pool."""
    pool_id: str
    database_type: DatabaseType
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    connection_errors: int = 0
    query_count: int = 0
    avg_response_time: float = 0.0
    last_health_check: Optional[datetime] = None
    health_status: PoolHealth = PoolHealth.HEALTHY