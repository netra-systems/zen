"""External Service Integration Test Utilities

Provides utilities for testing with real external services including
PostgreSQL, Redis, ClickHouse, and LLM services.

This is a critical SSOT component for ensuring tests can properly
validate real service integrations without mocks.
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import psycopg2
# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import httpx
from test_framework.unified_docker_manager import UnifiedDockerManager


class ExternalServiceIntegration:
    """Utilities for external service integration testing.
    
    Provides connection helpers, health checks, and cleanup utilities
    for testing with real services.
    """
    
    def __init__(self):
        self.docker_manager = UnifiedDockerManager()
        self.connections = {}
        self.cleanup_tasks = []
    
    async def ensure_services_running(self, services: List[str]) -> bool:
        """Ensure required services are running.
        
        Args:
            services: List of service names (postgres, redis, backend, auth)
            
        Returns:
            True if all services are healthy
        """
        # Start services if needed
        if not self.docker_manager.are_services_running(services):
            self.docker_manager.start_services(services)
        
        # Wait for health
        return self.docker_manager.wait_for_healthy(services, timeout=60)
    
    @asynccontextmanager
    async def postgres_connection(self, database: str = "netra_test"):
        """Context manager for PostgreSQL connections.
        
        Yields:
            psycopg2 connection object
        """
        conn = None
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5434,  # Test environment port
                database=database,
                user="postgres",
                password="postgres"
            )
            yield conn
        finally:
            if conn:
                conn.close()
    
    @asynccontextmanager
    async def redis_client(self, db: int = 0):
        """Context manager for Redis connections.
        
        Yields:
            Redis client object
        """
        client = None
        try:
            client = await get_redis_client()  # MIGRATED: was redis.Redis(
                host="localhost",
                port=6381,  # Test environment port
                db=db,
                decode_responses=True
            )
            yield client
        finally:
            if client:
                client.close()
    
    async def wait_for_postgres(self, timeout: int = 30) -> bool:
        """Wait for PostgreSQL to be ready.
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if PostgreSQL is ready
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with self.postgres_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    return True
            except Exception:
                await asyncio.sleep(1)
        return False
    
    async def wait_for_redis(self, timeout: int = 30) -> bool:
        """Wait for Redis to be ready.
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if Redis is ready
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with self.redis_client() as client:
                    client.ping()
                    return True
            except Exception:
                await asyncio.sleep(1)
        return False
    
    async def wait_for_backend(self, timeout: int = 60) -> bool:
        """Wait for backend service to be ready.
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if backend is ready
        """
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get("http://localhost:8000/health")
                    if response.status_code == 200:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(1)
        return False
    
    async def wait_for_auth(self, timeout: int = 60) -> bool:
        """Wait for auth service to be ready.
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if auth service is ready
        """
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get("http://localhost:8081/health")
                    if response.status_code == 200:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(1)
        return False
    
    async def cleanup_test_data(self, user_id: Optional[str] = None):
        """Clean up test data from services.
        
        Args:
            user_id: Optional user ID to clean up specific user data
        """
        # Clean PostgreSQL
        try:
            async with self.postgres_connection() as conn:
                cursor = conn.cursor()
                if user_id:
                    # Clean user-specific data
                    cursor.execute(
                        "DELETE FROM sessions WHERE user_id = %s",
                        (user_id,)
                    )
                    cursor.execute(
                        "DELETE FROM agent_executions WHERE user_id = %s",
                        (user_id,)
                    )
                else:
                    # Clean all test data (be careful!)
                    cursor.execute("DELETE FROM sessions WHERE user_id LIKE 'test_%'")
                    cursor.execute("DELETE FROM agent_executions WHERE user_id LIKE 'test_%'")
                conn.commit()
                cursor.close()
        except Exception as e:
            print(f"PostgreSQL cleanup error: {e}")
        
        # Clean Redis
        try:
            async with self.redis_client() as client:
                if user_id:
                    # Clean user-specific keys
                    keys = client.keys(f"user:{user_id}:*")
                    if keys:
                        client.delete(*keys)
                else:
                    # Clean test keys
                    keys = client.keys("user:test_*")
                    if keys:
                        client.delete(*keys)
        except Exception as e:
            print(f"Redis cleanup error: {e}")
    
    async def create_test_user(self, user_id: str, tier: str = "free") -> Dict[str, Any]:
        """Create a test user in the system.
        
        Args:
            user_id: User identifier
            tier: Subscription tier (free, early, mid, enterprise)
            
        Returns:
            User data dictionary
        """
        user_data = {
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "tier": tier,
            "created_at": time.time()
        }
        
        # Store in PostgreSQL
        async with self.postgres_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO users (user_id, email, tier, created_at) 
                   VALUES (%s, %s, %s, to_timestamp(%s))
                   ON CONFLICT (user_id) DO UPDATE SET tier = %s""",
                (user_id, user_data["email"], tier, user_data["created_at"], tier)
            )
            conn.commit()
            cursor.close()
        
        # Cache in Redis
        async with self.redis_client() as client:
            client.hset(f"user:{user_id}", mapping=user_data)
            client.expire(f"user:{user_id}", 3600)  # 1 hour TTL
        
        return user_data
    
    async def verify_websocket_connection(self, user_id: str) -> bool:
        """Verify WebSocket connection for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if connection exists
        """
        async with self.redis_client() as client:
            connections = client.smembers(f"ws:connections:{user_id}")
            return len(connections) > 0
    
    def get_test_environment_config(self) -> Dict[str, Any]:
        """Get test environment configuration.
        
        Returns:
            Configuration dictionary with service endpoints
        """
        return {
            "postgres": {
                "host": "localhost",
                "port": 5434,
                "database": "netra_test",
                "user": "postgres",
                "password": "postgres"
            },
            "redis": {
                "host": "localhost",
                "port": 6381,
                "db": 0
            },
            "backend": {
                "url": "http://localhost:8000",
                "ws_url": "ws://localhost:8000/ws"
            },
            "auth": {
                "url": "http://localhost:8081"
            },
            "clickhouse": {
                "host": "localhost",
                "port": 8123,
                "database": "netra_analytics"
            }
        }


class ServiceHealthChecker:
    """Health checking utilities for external services."""
    
    def __init__(self, integration: ExternalServiceIntegration):
        self.integration = integration
    
    async def check_all_services(self) -> Dict[str, bool]:
        """Check health of all services.
        
        Returns:
            Dictionary of service name to health status
        """
        results = {}
        
        # Check PostgreSQL
        results["postgres"] = await self.integration.wait_for_postgres(timeout=5)
        
        # Check Redis
        results["redis"] = await self.integration.wait_for_redis(timeout=5)
        
        # Check Backend
        results["backend"] = await self.integration.wait_for_backend(timeout=5)
        
        # Check Auth
        results["auth"] = await self.integration.wait_for_auth(timeout=5)
        
        return results
    
    async def wait_for_all_healthy(self, timeout: int = 60) -> bool:
        """Wait for all services to be healthy.
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if all services are healthy
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            health = await self.check_all_services()
            if all(health.values()):
                return True
            await asyncio.sleep(2)
        return False


class TestDataGenerator:
    """Generate test data for integration tests."""
    
    @staticmethod
    def generate_agent_request(user_id: str, request_type: str = "optimization") -> Dict[str, Any]:
        """Generate a test agent request.
        
        Args:
            user_id: User identifier
            request_type: Type of request (optimization, analysis, report)
            
        Returns:
            Request dictionary
        """
        return {
            "user_id": user_id,
            "session_id": f"session_{int(time.time())}",
            "request_id": f"req_{int(time.time() * 1000)}",
            "type": request_type,
            "message": f"Test {request_type} request",
            "metadata": {
                "source": "integration_test",
                "timestamp": time.time()
            }
        }
    
    @staticmethod
    def generate_usage_data(days: int = 7) -> List[Dict[str, Any]]:
        """Generate test usage data.
        
        Args:
            days: Number of days of data to generate
            
        Returns:
            List of usage data points
        """
        data = []
        current_time = time.time()
        for day in range(days):
            timestamp = current_time - (day * 86400)
            data.append({
                "timestamp": timestamp,
                "date": time.strftime("%Y-%m-%d", time.gmtime(timestamp)),
                "api_calls": 1000 + (day * 100),
                "tokens_used": 50000 + (day * 5000),
                "cost_usd": 10.0 + (day * 1.5)
            })
        return data