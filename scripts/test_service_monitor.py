from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Test Service Monitor
Monitors health of test services and provides status endpoint for test coordination.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List

import asyncpg
import redis.asyncio as redis
from aiohttp import web
from clickhouse_connect import get_client as get_clickhouse_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestServiceMonitor:
    """Monitors test service health and provides status API."""
    
    def __init__(self):
        self.postgres_url = self._build_postgres_url()
        self.redis_url = self._build_redis_url()
        self.clickhouse_config = self._build_clickhouse_config()
        self.check_interval = int(get_env().get("CHECK_INTERVAL", "5"))  # seconds
        self.service_status = {}
        self.last_check = {}
        
    def _build_postgres_url(self) -> str:
        """Build PostgreSQL connection URL."""
        host = get_env().get("POSTGRES_HOST", "test-postgres")
        port = get_env().get("POSTGRES_PORT", "5432") 
        user = get_env().get("POSTGRES_USER", "test_user")
        password = get_env().get("POSTGRES_PASSWORD", "test_pass")
        db = get_env().get("POSTGRES_DB", "netra_test")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    def _build_redis_url(self) -> str:
        """Build Redis connection URL."""
        host = get_env().get("REDIS_HOST", "test-redis")
        port = get_env().get("REDIS_PORT", "6379")
        return f"redis://{host}:{port}/0"
    
    def _build_clickhouse_config(self) -> Dict:
        """Build ClickHouse connection config."""
        return {
            "host": get_env().get("CLICKHOUSE_HOST", "test-clickhouse"),
            "port": int(get_env().get("CLICKHOUSE_PORT", "8123")),
            "user": get_env().get("CLICKHOUSE_USER", "test_user"),
            "password": get_env().get("CLICKHOUSE_PASSWORD", "test_pass"),
            "database": get_env().get("CLICKHOUSE_DB", "netra_test_analytics")
        }
    
    async def check_postgres_health(self) -> Dict:
        """Check PostgreSQL service health."""
        start_time = time.time()
        try:
            conn = await asyncpg.connect(self.postgres_url, timeout=5.0)
            # Test basic query
            result = await conn.fetchval("SELECT COUNT(*) FROM auth.users")
            await conn.close()
            
            response_time = time.time() - start_time
            return {
                "status": "healthy",
                "response_time_ms": int(response_time * 1000),
                "user_count": result,
                "checked_at": time.time()
            }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status": "unhealthy", 
                "error": str(e),
                "response_time_ms": int(response_time * 1000),
                "checked_at": time.time()
            }
    
    async def check_redis_health(self) -> Dict:
        """Check Redis service health."""
        start_time = time.time()
        try:
            client = redis.Redis.from_url(self.redis_url, decode_responses=True)
            
            # Test ping
            await client.ping()
            
            # Test basic operations
            await client.set("health_check", "ok", ex=10)
            value = await client.get("health_check")
            await client.delete("health_check")
            
            # Get info
            info = await client.info()
            
            await client.aclose()
            
            response_time = time.time() - start_time
            return {
                "status": "healthy",
                "response_time_ms": int(response_time * 1000),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "checked_at": time.time()
            }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status": "unhealthy",
                "error": str(e), 
                "response_time_ms": int(response_time * 1000),
                "checked_at": time.time()
            }
    
    async def check_clickhouse_health(self) -> Dict:
        """Check ClickHouse service health.""" 
        start_time = time.time()
        try:
            client = ClickHouseClient(**self.clickhouse_config, connect_timeout=5)
            
            # Test basic query
            result = client.execute("SELECT COUNT(*) FROM user_events")
            client.disconnect()
            
            response_time = time.time() - start_time
            return {
                "status": "healthy",
                "response_time_ms": int(response_time * 1000),
                "event_count": result[0][0] if result else 0,
                "checked_at": time.time()
            }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": int(response_time * 1000),
                "checked_at": time.time()
            }
    
    async def check_all_services(self) -> Dict:
        """Check health of all services."""
        logger.info("Checking health of all test services...")
        
        # Check services in parallel
        postgres_task = asyncio.create_task(self.check_postgres_health())
        redis_task = asyncio.create_task(self.check_redis_health())
        clickhouse_task = asyncio.create_task(self.check_clickhouse_health())
        
        postgres_health = await postgres_task
        redis_health = await redis_task
        clickhouse_health = await clickhouse_task
        
        # Update service status
        self.service_status = {
            "postgres": postgres_health,
            "redis": redis_health,
            "clickhouse": clickhouse_health
        }
        
        # Calculate overall health
        all_healthy = all(
            service["status"] == "healthy" 
            for service in self.service_status.values()
        )
        
        overall_status = {
            "overall_status": "healthy" if all_healthy else "degraded",
            "services": self.service_status,
            "checked_at": time.time()
        }
        
        # Log status
        for service_name, health in self.service_status.items():
            status = health["status"]
            response_time = health["response_time_ms"]
            logger.info(f"{service_name}: {status} ({response_time}ms)")
        
        return overall_status
    
    async def periodic_health_check(self):
        """Periodically check service health."""
        while True:
            try:
                await self.check_all_services()
            except Exception as e:
                logger.error(f"Health check failed: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def health_handler(self, request):
        """HTTP handler for health status."""
        return web.json_response(self.service_status or {"status": "initializing"})
    
    async def detailed_status_handler(self, request):
        """HTTP handler for detailed status."""
        # Force fresh check if requested
        if request.query.get("fresh") == "true":
            status = await self.check_all_services()
        else:
            status = {
                "overall_status": "healthy" if all(
                    service.get("status") == "healthy" 
                    for service in self.service_status.values()
                ) else "degraded",
                "services": self.service_status,
                "checked_at": time.time()
            }
        
        return web.json_response(status)
    
    async def service_specific_handler(self, request):
        """HTTP handler for specific service status."""
        service_name = request.match_info["service"]
        
        if service_name not in ["postgres", "redis", "clickhouse"]:
            return web.json_response(
                {"error": f"Unknown service: {service_name}"}, 
                status=404
            )
        
        service_status = self.service_status.get(service_name, {"status": "unknown"})
        return web.json_response(service_status)
    
    async def metrics_handler(self, request):
        """HTTP handler for Prometheus-style metrics."""
        lines = []
        
        for service_name, health in self.service_status.items():
            healthy = 1 if health.get("status") == "healthy" else 0
            response_time = health.get("response_time_ms", 0)
            
            lines.extend([
                f'test_service_health{{service="{service_name}"}} {healthy}',
                f'test_service_response_time_ms{{service="{service_name}"}} {response_time}',
            ])
        
        # Add service-specific metrics
        if "postgres" in self.service_status:
            user_count = self.service_status["postgres"].get("user_count", 0)
            lines.append(f'test_postgres_user_count {user_count}')
        
        if "redis" in self.service_status:
            clients = self.service_status["redis"].get("connected_clients", 0)
            memory = self.service_status["redis"].get("used_memory", 0)
            lines.extend([
                f'test_redis_connected_clients {clients}',
                f'test_redis_used_memory_bytes {memory}'
            ])
        
        if "clickhouse" in self.service_status:
            events = self.service_status["clickhouse"].get("event_count", 0)
            lines.append(f'test_clickhouse_event_count {events}')
        
        return web.Response(
            text="\n".join(lines) + "\n",
            content_type="text/plain"
        )
    
    async def init_app(self):
        """Initialize web application."""
        app = web.Application()
        
        # Add routes
        app.router.add_get("/health", self.health_handler)
        app.router.add_get("/health-status", self.detailed_status_handler)
        app.router.add_get("/service/{service}", self.service_specific_handler)
        app.router.add_get("/metrics", self.metrics_handler)
        
        # Add CORS headers for test coordination
        async def add_cors_headers(request, handler):
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            return response
        
        app.middlewares.append(add_cors_headers)
        
        return app
    
    async def run(self):
        """Run the service monitor."""
        logger.info("Starting test service monitor...")
        
        # Start periodic health checks
        health_check_task = asyncio.create_task(self.periodic_health_check())
        
        # Initialize web app
        app = await self.init_app()
        
        # Start HTTP server
        runner = web.AppRunner(app)
        await runner.setup()
        
        port = int(get_env().get("PORT", "8080"))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        
        logger.info(f"Test service monitor listening on port {port}")
        logger.info("Available endpoints:")
        logger.info("  GET /health - Basic health status")
        logger.info("  GET /health-status - Detailed status")
        logger.info("  GET /health-status?fresh=true - Force fresh check")
        logger.info("  GET /service/{service} - Specific service status")
        logger.info("  GET /metrics - Prometheus metrics")
        
        try:
            # Keep running
            await health_check_task
        except KeyboardInterrupt:
            logger.info("Shutting down test service monitor...")
        finally:
            await runner.cleanup()


async def main():
    """Main entry point."""
    monitor = TestServiceMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
