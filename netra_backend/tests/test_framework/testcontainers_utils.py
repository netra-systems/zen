from shared.isolated_environment import get_env
"""Testcontainers utilities for integration tests."""

import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add parent directories to path

class ContainerHelper:
    """Helper class for managing test containers."""
    
    def __init__(self):
        """Initialize test container helper."""
        self.containers = {}
        self.redis_url = get_env().get("REDIS_URL", "redis://localhost:6379")
        self.postgres_url = get_env().get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test")
        self.clickhouse_url = get_env().get("CLICKHOUSE_URL", "clickhouse://localhost:9000")
    
    async def start_redis(self) -> str:
        """Start Redis container or return existing URL."""
        # In test environment, we typically use existing Redis
        return self.redis_url
    
    async def start_postgres(self) -> str:
        """Start PostgreSQL container or return existing URL."""
        # In test environment, we typically use existing PostgreSQL
        return self.postgres_url
    
    async def start_clickhouse(self) -> str:
        """Start ClickHouse container or return existing URL."""
        # In test environment, we typically use existing ClickHouse
        return self.clickhouse_url
    
    async def cleanup(self):
        """Cleanup test containers."""
        # Cleanup logic if needed
        pass
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration."""
        return {
            "url": self.redis_url,
            "host": "localhost",
            "port": 6379,
            "db": 0,
}
    
    def get_postgres_config(self) -> Dict[str, Any]:
        """Get PostgreSQL configuration."""
        return {
            "url": self.postgres_url,
            "host": "localhost",
            "port": 5432,
            "database": "netra_test",
            "user": "postgres",
            "password": "postgres",
}
    
    def get_clickhouse_config(self) -> Dict[str, Any]:
        """Get ClickHouse configuration."""
        return {
            "url": self.clickhouse_url,
            "host": "localhost",
            "port": 9000,
            "database": "default",
}
