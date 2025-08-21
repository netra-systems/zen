"""
Database Migration Validators and Utilities

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all customer segments)
- Business Goal: Platform Stability - Prevent data corruption and migration failures
- Value Impact: Protects customer data integrity across all tiers, ensuring zero data loss during updates
- Strategic/Revenue Impact: Prevents critical downtime (estimated $50K/hour for Enterprise)

Utilities for database migration testing including validation and containerized setup.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import pytest
from clickhouse_driver import Client as ClickHouseClient
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from alembic import config as alembic_config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from test_framework.mock_utils import mock_justified


class MigrationValidator:
    """Validates database migrations for correctness and performance."""
    
    def __init__(self, postgres_url: str, clickhouse_url: str):
        self.postgres_url = postgres_url
        self.clickhouse_url = clickhouse_url
        self.errors: List[str] = []
        self.performance_metrics: Dict[str, float] = {}
        
    async def validate_postgres_schema(self) -> bool:
        """Validate PostgreSQL schema after migration."""
        try:
            conn = await asyncpg.connect(self.postgres_url)
            critical_tables = ['users', 'organizations', 'threads', 'messages', 'agents', 'agent_tools', 'agent_executions']
            
            for table in critical_tables:
                result = await conn.fetchval("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)", table)
                if not result:
                    self.errors.append(f"Missing critical table: {table}")
            
            critical_indices = [('users', 'users_email_idx'), ('threads', 'threads_org_id_idx'), ('messages', 'messages_thread_id_idx')]
            
            for table, index in critical_indices:
                result = await conn.fetchval("SELECT EXISTS (SELECT FROM pg_indexes WHERE tablename = $1 AND indexname = $2)", table, index)
                if not result:
                    self.errors.append(f"Missing critical index: {index} on {table}")
            
            await conn.close()
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"PostgreSQL validation failed: {e}")
            return False
    
    def validate_clickhouse_schema(self) -> bool:
        """Validate ClickHouse schema after migration."""
        try:
            client = ClickHouseClient(host='localhost', port=8124)
            analytics_tables = ['events', 'metrics', 'agent_metrics', 'usage_analytics', 'performance_metrics']
            
            for table in analytics_tables:
                result = client.execute(f"SELECT count() FROM system.tables WHERE name = '{table}'")
                if result[0][0] == 0:
                    self.errors.append(f"Missing ClickHouse table: {table}")
            
            partitioned_tables = ['events', 'metrics']
            for table in partitioned_tables:
                result = client.execute(f"SELECT partition_key FROM system.tables WHERE name = '{table}'")
                if not result or not result[0][0]:
                    self.errors.append(f"Table {table} not properly partitioned")
            
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"ClickHouse validation failed: {e}")
            return False
    
    def record_timing(self, operation: str, duration: float):
        """Record performance metrics for migrations."""
        self.performance_metrics[operation] = duration
        
    def validate_performance(self) -> bool:
        """Validate migration performance meets requirements."""
        max_durations = {'postgres_migration': 60, 'clickhouse_migration': 30, 'rollback': 30, 'total': 300}
        
        for operation, max_duration in max_durations.items():
            if operation in self.performance_metrics:
                if self.performance_metrics[operation] > max_duration:
                    self.errors.append(f"{operation} took {self.performance_metrics[operation]:.2f}s (max: {max_duration}s)")
        
        return len(self.errors) == 0


class ContainerizedDatabaseManager:
    """Manages containerized databases for L3 testing."""
    
    def __init__(self):
        self.postgres_container = None
        self.clickhouse_container = None
        self.containers_ready = False
        
    async def start_containers(self) -> Dict[str, str]:
        """Start PostgreSQL and ClickHouse containers for testing."""
        test_compose_file = Path(__file__).parent.parent.parent / "docker-compose.test.yml"
        
        try:
            subprocess.run(["docker-compose", "-f", str(test_compose_file), "up", "-d", "postgres", "clickhouse"], check=True, capture_output=True)
            await self._wait_for_containers()
            
            return {"postgres": "postgresql://test:test@localhost:5433/netra_test", "clickhouse": "clickhouse://localhost:8124/netra_test"}
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to start containers: {e.stderr.decode()}")
    
    async def _wait_for_containers(self, timeout: int = 30):
        """Wait for database containers to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            postgres_ready = await self._check_postgres_ready()
            clickhouse_ready = await self._check_clickhouse_ready()
            
            if postgres_ready and clickhouse_ready:
                self.containers_ready = True
                return
            
            await asyncio.sleep(1)
        
        raise TimeoutError("Containers did not become ready within timeout")
    
    async def _check_postgres_ready(self) -> bool:
        """Check if PostgreSQL is ready to accept connections."""
        try:
            conn = await asyncpg.connect("postgresql://test:test@localhost:5433/postgres")
            await conn.close()
            return True
        except:
            return False
    
    async def _check_clickhouse_ready(self) -> bool:
        """Check if ClickHouse is ready to accept connections."""
        try:
            client = ClickHouseClient(host='localhost', port=8124)
            client.execute("SELECT 1")
            return True
        except:
            return False
    
    async def stop_containers(self):
        """Stop and clean up containers."""
        test_compose_file = Path(__file__).parent.parent.parent / "docker-compose.test.yml"
        subprocess.run(["docker-compose", "-f", str(test_compose_file), "down", "-v"], capture_output=True)
