"""

Database connection verification utilities for dev launcher testing.



Provides utilities for verifying database connectivity, testing connection pools,

monitoring database health, and validating database configurations.



Follows 450-line file limit and 25-line function limit constraints.

"""



import asyncio

import os

import sys

import time

from contextlib import asynccontextmanager

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Dict, List, Optional, Tuple, Union



import aiohttp

import asyncpg

import redis

from sqlalchemy import create_engine, text

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from sqlalchemy.pool import StaticPool



# Add project root to path





@dataclass

class DatabaseConnectionResult:

    """Result of database connection test."""

    database_type: str

    url: str

    success: bool

    response_time_ms: float

    error: Optional[str]

    metadata: Dict[str, Any]





@dataclass

class ConnectionPoolMetrics:

    """Metrics for database connection pool."""

    pool_size: int

    checked_in: int

    checked_out: int

    overflow: int

    invalid: int





class PostgreSQLVerifier:

    """Verifies PostgreSQL database connections."""

    

    def __init__(self, connection_url: str):

        self.connection_url = connection_url

        self.engine: Optional[Any] = None

    

    async def verify_connection(self) -> DatabaseConnectionResult:

        """Verify PostgreSQL connection."""

        start_time = time.time()

        

        try:

            self.engine = create_async_engine(self.connection_url, echo=False)

            

            async with self.engine.begin() as conn:

                result = await conn.execute(text("SELECT version()"))

                version = result.scalar()

                

                response_time = (time.time() - start_time) * 1000

                

                return DatabaseConnectionResult(

                    database_type="postgresql",

                    url=self._mask_password(self.connection_url),

                    success=True,

                    response_time_ms=response_time,

                    error=None,

                    metadata={"version": version}

                )

                

        except Exception as e:

            response_time = (time.time() - start_time) * 1000

            return DatabaseConnectionResult(

                database_type="postgresql",

                url=self._mask_password(self.connection_url),

                success=False,

                response_time_ms=response_time,

                error=str(e),

                metadata={}

            )

        finally:

            if self.engine:

                await self.engine.dispose()

    

    async def verify_schema_tables(self, required_tables: List[str]) -> Tuple[bool, List[str]]:

        """Verify required tables exist in schema."""

        try:

            self.engine = create_async_engine(self.connection_url, echo=False)

            

            missing_tables = []

            async with self.engine.begin() as conn:

                for table in required_tables:

                    exists = await self._table_exists(conn, table)

                    if not exists:

                        missing_tables.append(table)

            

            return len(missing_tables) == 0, missing_tables

            

        except Exception:

            return False, required_tables

        finally:

            if self.engine:

                await self.engine.dispose()

    

    async def _table_exists(self, conn: Any, table_name: str) -> bool:

        """Check if table exists in database."""

        result = await conn.execute(

            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table)"),

            {"table": table_name}

        )

        return result.scalar()

    

    def _mask_password(self, url: str) -> str:

        """Mask password in connection URL."""

        if "@" in url and ":" in url:

            parts = url.split("@")

            if len(parts) == 2:

                user_pass = parts[0].split("://")[1]

                if ":" in user_pass:

                    user = user_pass.split(":")[0]

                    return url.replace(user_pass, f"{user}:***")

        return url





class ClickHouseVerifier:

    """Verifies ClickHouse database connections."""

    

    def __init__(self, connection_url: str):

        self.connection_url = connection_url

    

    async def verify_connection(self) -> DatabaseConnectionResult:

        """Verify ClickHouse connection."""

        start_time = time.time()

        

        try:

            async with aiohttp.ClientSession() as session:

                query_url = f"{self.connection_url}?query=SELECT version()"

                

                async with session.get(query_url, timeout=aiohttp.ClientTimeout(total=10)) as response:

                    response_time = (time.time() - start_time) * 1000

                    

                    if response.status == 200:

                        version = await response.text()

                        return DatabaseConnectionResult(

                            database_type="clickhouse",

                            url=self.connection_url,

                            success=True,

                            response_time_ms=response_time,

                            error=None,

                            metadata={"version": version.strip()}

                        )

                    else:

                        return DatabaseConnectionResult(

                            database_type="clickhouse",

                            url=self.connection_url,

                            success=False,

                            response_time_ms=response_time,

                            error=f"HTTP {response.status}",

                            metadata={}

                        )

                        

        except Exception as e:

            response_time = (time.time() - start_time) * 1000

            return DatabaseConnectionResult(

                database_type="clickhouse",

                url=self.connection_url,

                success=False,

                response_time_ms=response_time,

                error=str(e),

                metadata={}

            )

    

    async def verify_database_exists(self, database_name: str) -> bool:

        """Verify ClickHouse database exists."""

        try:

            async with aiohttp.ClientSession() as session:

                query = f"SHOW DATABASES"

                query_url = f"{self.connection_url}?query={query}"

                

                async with session.get(query_url) as response:

                    if response.status == 200:

                        databases = await response.text()

                        return database_name in databases

            return False

        except Exception:

            return False





class RedisVerifier:

    """Verifies Redis connections."""

    

    def __init__(self, connection_url: str):

        self.connection_url = connection_url

    

    def verify_connection(self) -> DatabaseConnectionResult:

        """Verify Redis connection."""

        start_time = time.time()

        

        try:

            client = redis.from_url(self.connection_url)

            

            # Test connection with ping

            client.ping()

            

            # Get server info

            info = client.info()

            version = info.get('redis_version', 'unknown')

            

            client.close()

            

            response_time = (time.time() - start_time) * 1000

            

            return DatabaseConnectionResult(

                database_type="redis",

                url=self._mask_password(self.connection_url),

                success=True,

                response_time_ms=response_time,

                error=None,

                metadata={"version": version}

            )

            

        except Exception as e:

            response_time = (time.time() - start_time) * 1000

            return DatabaseConnectionResult(

                database_type="redis",

                url=self._mask_password(self.connection_url),

                success=False,

                response_time_ms=response_time,

                error=str(e),

                metadata={}

            )

    

    def verify_keyspace_isolation(self, database_index: int) -> bool:

        """Verify Redis database isolation."""

        try:

            client = redis.from_url(self.connection_url)

            client.select(database_index)

            

            # Test key isolation

            test_key = f"test_isolation_{int(time.time())}"

            client.set(test_key, "test_value", ex=60)

            

            # Switch to different database

            client.select((database_index + 1) % 16)

            value = client.get(test_key)

            

            client.close()

            

            # Key should not exist in different database

            return value is None

            

        except Exception:

            return False

    

    def _mask_password(self, url: str) -> str:

        """Mask password in Redis URL."""

        if "@" in url and ":" in url:

            parts = url.split("@")

            if len(parts) == 2:

                user_pass = parts[0].split("://")[1]

                if ":" in user_pass:

                    return url.replace(user_pass.split(":")[1], "***")

        return url





class DatabaseHealthMonitor:

    """Monitors database health over time."""

    

    def __init__(self):

        self.health_history: List[Dict[str, Any]] = []

        self.monitoring_active = False

        self.monitor_task: Optional[asyncio.Task] = None

    

    async def start_monitoring(self, connections: Dict[str, str], interval: float = 30.0) -> None:

        """Start monitoring database health."""

        self.monitoring_active = True

        self.monitor_task = asyncio.create_task(

            self._monitor_loop(connections, interval)

        )

    

    async def stop_monitoring(self) -> None:

        """Stop monitoring database health."""

        self.monitoring_active = False

        if self.monitor_task:

            self.monitor_task.cancel()

            try:

                await self.monitor_task

            except asyncio.CancelledError:

                pass

    

    async def _monitor_loop(self, connections: Dict[str, str], interval: float) -> None:

        """Main monitoring loop."""

        while self.monitoring_active:

            timestamp = time.time()

            health_snapshot = await self._capture_health_snapshot(connections)

            health_snapshot["timestamp"] = timestamp

            

            self.health_history.append(health_snapshot)

            

            # Keep only last 100 snapshots

            if len(self.health_history) > 100:

                self.health_history = self.health_history[-100:]

            

            await asyncio.sleep(interval)

    

    async def _capture_health_snapshot(self, connections: Dict[str, str]) -> Dict[str, Any]:

        """Capture health snapshot of all databases."""

        snapshot = {}

        

        for db_type, url in connections.items():

            if db_type == "postgresql":

                verifier = PostgreSQLVerifier(url)

                result = await verifier.verify_connection()

            elif db_type == "clickhouse":

                verifier = ClickHouseVerifier(url)

                result = await verifier.verify_connection()

            elif db_type == "redis":

                verifier = RedisVerifier(url)

                result = verifier.verify_connection()

            else:

                continue

            

            snapshot[db_type] = {

                "healthy": result.success,

                "response_time_ms": result.response_time_ms,

                "error": result.error

            }

        

        return snapshot

    

    def get_health_summary(self) -> Dict[str, Any]:

        """Get health summary from monitoring history."""

        if not self.health_history:

            return {"status": "no_data"}

        

        latest = self.health_history[-1]

        

        # Calculate uptime percentages

        uptime_stats = {}

        for db_type in latest.keys():

            if db_type == "timestamp":

                continue

                

            healthy_count = sum(

                1 for snapshot in self.health_history

                if snapshot.get(db_type, {}).get("healthy", False)

            )

            uptime_percentage = (healthy_count / len(self.health_history)) * 100

            uptime_stats[db_type] = uptime_percentage

        

        return {

            "status": "active",

            "snapshots_count": len(self.health_history),

            "latest_snapshot": latest,

            "uptime_percentages": uptime_stats

        }

