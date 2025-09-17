'''Service Availability Checker for E2E Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Reliability
- Value Impact: Enables proper E2E testing with real services when available
- Strategic Impact: Reduces false test failures and improves CI/CD reliability

This module provides comprehensive service availability detection for E2E tests.
It checks actual connectivity to databases and external services, not just
environment variables or flags.
'''

import asyncio
import logging
import socket
from shared.isolated_environment import get_env
import time
import traceback
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlparse

    # Database connection imports
try:
import asyncpg
except ImportError:
asyncpg = None

try:
import redis.asyncio as redis
except ImportError:
redis = None

try:
import clickhouse_connect
except ImportError:
clickhouse_connect = None

                            # HTTP client for API checks
try:
import httpx
except ImportError:
httpx = None

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Status of a single service check."""
    name: str
    available: bool
    details: str
    connection_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


    @dataclass
class ServiceAvailability:
    """Complete service availability configuration."""

    # Database services
    postgresql: ServiceStatus
    redis: ServiceStatus
    clickhouse: ServiceStatus

    # External API services
    openai_api: ServiceStatus
    anthropic_api: ServiceStatus

    # Configuration flags
    use_real_services: bool
    use_real_llm: bool

    @property
    def has_real_databases(self) -> bool:
        """Check if real databases are available."""
        return self.postgresql.available and self.redis.available

        @property
    def has_real_llm_apis(self) -> bool:
        """Check if real LLM APIs are available."""
        return self.openai_api.available or self.anthropic_api.available

        @property
    def summary(self) -> Dict[str, Any]:
        """Get summary of service availability."""
        return {}
        "databases": {}
        "postgresql": self.postgresql.available,
        "redis": self.redis.available,
        "clickhouse": self.clickhouse.available,
        },
        "apis": {}
        "openai": self.openai_api.available,
        "anthropic": self.anthropic_api.available,
        },
        "configuration": {}
        "use_real_services": self.use_real_services,
        "use_real_llm": self.use_real_llm,
        "has_real_databases": self.has_real_databases,
        "has_real_llm_apis": self.has_real_llm_apis,
    
    


class ServiceAvailabilityChecker:
        """Checks actual availability of services for E2E testing."""

    def __init__(self, timeout: float = 15.0):
        '''Initialize service availability checker.

        Args:
        timeout: Connection timeout in seconds (increased for better reliability)
        '''
        self.timeout = timeout
        self.logger = logging.getLogger("formatted_string")

    async def check_all_services(self) -> ServiceAvailability:
        '''Check availability of all services.

        Returns:
        ServiceAvailability object with status of all services
        '''
        self.logger.info("formatted_string")

        # Check environment flags first
        use_real_services = self._check_use_real_services_flag()
        use_real_llm = self._check_use_real_llm_flag()

        self.logger.info("formatted_string")

        # Run all checks concurrently
        start_time = time.time()

        postgresql_task = self._check_postgresql()
        redis_task = self._check_redis()
        clickhouse_task = self._check_clickhouse()
        openai_task = self._check_openai_api()
        anthropic_task = self._check_anthropic_api()

        self.logger.info("Running concurrent service checks...")

        # Wait for all results
        results = await asyncio.gather( )
        postgresql_task,
        redis_task,
        clickhouse_task,
        openai_task,
        anthropic_task,
        return_exceptions=True
        

        check_duration = time.time() - start_time

        # Handle any exceptions in results
        postgresql, redis_status, clickhouse, openai, anthropic = results
        service_names = ["postgresql", "redis", "clickhouse", "openai", "anthropic"]

        for i, result in enumerate(results):
        if isinstance(result, Exception):
        service_name = service_names[i]
        self.logger.error("formatted_string")
        results[i] = ServiceStatus(
        name=service_name,
        available=False,
        details="Service check failed with exception",
        error=str(result)
                

        availability = ServiceAvailability(
        postgresql=results[0] if not isinstance(results[0], Exception) else results[0],
        redis=results[1] if not isinstance(results[1], Exception) else results[1],
        clickhouse=results[2] if not isinstance(results[2], Exception) else results[2],
        openai_api=results[3] if not isinstance(results[3], Exception) else results[3],
        anthropic_api=results[4] if not isinstance(results[4], Exception) else results[4],
        use_real_services=use_real_services,
        use_real_llm=use_real_llm
                

                # Log detailed results
        self.logger.info("formatted_string")
        for service_name in ["postgresql", "redis", "clickhouse", "openai_api", "anthropic_api"]:
        service_obj = getattr(availability, service_name)
        status_icon = "[OK]" if service_obj.available else "[FAIL]"
        self.logger.info("formatted_string")
        if service_obj.error:
        self.logger.debug("formatted_string")

        return availability

    def _check_use_real_services_flag(self) -> bool:
        """Check if USE_REAL_SERVICES flag is set."""
        return get_env().get("USE_REAL_SERVICES", "false").lower() == "true"

    def _check_use_real_llm_flag(self) -> bool:
        """Check if real LLM usage is enabled."""
    # Check multiple flag variations that exist in the codebase
        real_llm_flags = []
        "TEST_USE_REAL_LLM",
        "ENABLE_REAL_LLM_TESTING",
        "USE_REAL_LLM"
    

        for flag in real_llm_flags:
        if get_env().get(flag, "false").lower() == "true":
        return True

        return False

    async def _check_postgresql(self) -> ServiceStatus:
        """Check PostgreSQL database availability."""
        if not asyncpg:
        return ServiceStatus(
        name="postgresql",
        available=False,
        details="asyncpg library not available",
        error="Missing asyncpg dependency"
        

        # Try multiple common database URLs
        db_urls = []
        get_env().get("DATABASE_URL"),
        get_env().get("POSTGRES_URL"),
        get_env().get("TEST_DATABASE_URL"),
        "postgresql://postgres:password@localhost:5432/netra",
        "postgresql://postgres:password@localhost:5432/netra_test",
        "postgresql://test:test@localhost:5432/test_db"
        

        for db_url in db_urls:
        if not db_url:
        continue

        try:
                    # Test connection with short timeout
        conn = await asyncio.wait_for(
        asyncpg.connect(db_url),
        timeout=self.timeout
                    

                    # Test basic query
        result = await conn.fetchval("SELECT 1")
        await conn.close()

        if result == 1:
                        # Parse URL for connection info (without password)
        parsed = urlparse(db_url)
        connection_info = {}
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/") if parsed.path else "postgres"
                        

        return ServiceStatus(
        name="postgresql",
        available=True,
        details="formatted_string",
        connection_info=connection_info
                        

        except asyncio.TimeoutError:
        self.logger.debug("formatted_string")
        continue
        except Exception as e:
        self.logger.debug("formatted_string")
        continue

        return ServiceStatus(
        name="postgresql",
        available=False,
        details="No PostgreSQL connections succeeded",
        error="Connection failed for all attempted URLs"
                                

    async def _check_redis(self) -> ServiceStatus:
        """Check Redis availability."""
        if not redis:
        return ServiceStatus(
        name="redis",
        available=False,
        details="redis library not available",
        error="Missing redis dependency"
        

        # Try multiple common Redis configurations
        redis_configs = []
        {"url": get_env().get("REDIS_URL")},
        {"url": get_env().get("TEST_REDIS_URL")},
        {"host": "localhost", "port": 6379},
        {"host": "127.0.0.1", "port": 6379},
        {"url": "redis://localhost:6379"},
        

        for config in redis_configs:
        if config.get("url") and not config["url"]:
        continue

        try:
                    # Create Redis client
        if "url" in config and config["url"]:
        client = redis.Redis.from_url( )
        config["url"],
        socket_connect_timeout=self.timeout,
        socket_timeout=self.timeout
                        
        else:
        client = await get_redis_client()
        host=config["host"],
        port=config["port"],
        socket_connect_timeout=self.timeout,
        socket_timeout=self.timeout
                            

                            # Test connection
        await asyncio.wait_for(client.ping(), timeout=self.timeout)
        await client.aclose()  # Use aclose() instead of close()

        connection_info = {}
        "host": config.get("host", "localhost"),
        "port": config.get("port", 6379)
                            

        return ServiceStatus(
        name="redis",
        available=True,
        details="formatted_string",
        connection_info=connection_info
                            

        except asyncio.TimeoutError:
        self.logger.debug("formatted_string")
        continue
        except Exception as e:
        self.logger.debug("formatted_string")
        continue

        return ServiceStatus(
        name="redis",
        available=False,
        details="No Redis connections succeeded",
        error="Connection failed for all attempted configurations"
                                    

    async def _check_clickhouse(self) -> ServiceStatus:
        """Check ClickHouse availability."""
        if not clickhouse_connect:
        return ServiceStatus(
        name="clickhouse",
        available=False,
        details="clickhouse_connect library not available",
        error="Missing clickhouse_connect dependency"
        

        # Try multiple ClickHouse configurations
        clickhouse_configs = []
        {"host": "localhost", "port": 8123, "secure": False},
        {"host": "localhost", "port": 8443, "secure": True},
        {"host": "127.0.0.1", "port": 8123, "secure": False},
        

        # Add environment-based config if available
        ch_url = get_env().get("CLICKHOUSE_URL") or get_env().get("TEST_CLICKHOUSE_URL")
        if ch_url and ch_url.startswith("clickhouse://"):
        try:
        parsed = urlparse(ch_url.replace("clickhouse://", "http://"))
        clickhouse_configs.insert(0, {})
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 8123,
        "secure": False
                
        except Exception:
        pass

        for config in clickhouse_configs:
        try:
                            # Test connection with timeout
        client = await asyncio.wait_for(
        asyncio.to_thread( )
        clickhouse_connect.get_client,
        host=config["host"],
        port=config["port"],
        secure=config["secure"],
        connect_timeout=self.timeout,
        send_receive_timeout=self.timeout
        ),
        timeout=self.timeout
                            

                            # Test basic query
        result = await asyncio.wait_for(
        asyncio.to_thread(client.command, "SELECT 1"),
        timeout=self.timeout
                            

        client.close()

        return ServiceStatus(
        name="clickhouse",
        available=True,
        details="formatted_string",
        connection_info=config
                            

        except asyncio.TimeoutError:
        self.logger.debug("formatted_string")
        continue
        except Exception as e:
        self.logger.debug("formatted_string")
        continue

        return ServiceStatus(
        name="clickhouse",
        available=False,
        details="No ClickHouse connections succeeded",
        error="Connection failed for all attempted configurations"
                                    

    async def _check_openai_api(self) -> ServiceStatus:
        """Check OpenAI API availability."""
        api_key = get_env().get("OPENAI_API_KEY")
        if not api_key:
        return ServiceStatus(
        name="openai",
        available=False,
        details="OPENAI_API_KEY environment variable not set"
        

        if not httpx:
        return ServiceStatus(
        name="openai",
        available=False,
        details="httpx library not available for API testing",
        error="Missing httpx dependency"
            

        try:
                # Test API with simple request
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
        response = await client.get( )
        "https://api.openai.com/models",
        headers={"Authorization": "formatted_string"}
                    

        if response.status_code == 200:
        return ServiceStatus(
        name="openai",
        available=True,
        details="OpenAI API key validated successfully"
                        
        else:
        return ServiceStatus(
        name="openai",
        available=False,
        details="formatted_string",
        error="formatted_string"
                            

        except asyncio.TimeoutError:
        return ServiceStatus(
        name="openai",
        available=False,
        details="OpenAI API request timed out",
        error="Timeout"
                                
        except Exception as e:
        return ServiceStatus(
        name="openai",
        available=False,
        details="OpenAI API check failed",
        error=str(e)
                                    

    async def _check_anthropic_api(self) -> ServiceStatus:
        """Check Anthropic API availability."""
        api_key = get_env().get("ANTHROPIC_API_KEY")
        if not api_key:
        return ServiceStatus(
        name="anthropic",
        available=False,
        details="ANTHROPIC_API_KEY environment variable not set"
        

        if not httpx:
        return ServiceStatus(
        name="anthropic",
        available=False,
        details="httpx library not available for API testing",
        error="Missing httpx dependency"
            

        try:
                # Test API with simple request (note: different endpoint structure)
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
        response = await client.get( )
        "https://api.anthropic.com/messages",
        headers={}
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
                    
                    

                    # Anthropic API returns 400 for GET on messages endpoint, which is expected
                    # We just want to verify the API key is recognized
        if response.status_code in [400, 405]:  # Method not allowed or bad request
        return ServiceStatus(
        name="anthropic",
        available=True,
        details="Anthropic API key validated successfully"
                    
        elif response.status_code == 401:
        return ServiceStatus(
        name="anthropic",
        available=False,
        details="Anthropic API key is invalid",
        error="Invalid API key"
                        
        else:
        return ServiceStatus(
        name="anthropic",
        available=False,
        details="formatted_string",
        error="formatted_string"
                            

        except asyncio.TimeoutError:
        return ServiceStatus(
        name="anthropic",
        available=False,
        details="Anthropic API request timed out",
        error="Timeout"
                                
        except Exception as e:
        return ServiceStatus(
        name="anthropic",
        available=False,
        details="Anthropic API check failed",
        error=str(e)
                                    


                                    # Convenience function for easy usage
    async def get_service_availability(timeout: float = 5.0) -> ServiceAvailability:
        '''Get current service availability.

        Args:
        timeout: Connection timeout in seconds

        Returns:
        ServiceAvailability object with current service status
        '''
        checker = ServiceAvailabilityChecker(timeout=timeout)
        return await checker.check_all_services()


            # CLI interface for manual testing
    async def main():
        """CLI interface for testing service availability."""
        import sys

        print("Checking service availability...")
        print("=" * 50)

        availability = await get_service_availability()

    # Print detailed results
        print(f"Environment Flags:")
        print("formatted_string")
        print("formatted_string")
        print()

        print("Database Services:")
        for service in [availability.postgresql, availability.redis, availability.clickhouse]:
        status = "[OK]" if service.available else "[FAIL]"  # Use ASCII characters for Windows compatibility
        print("formatted_string")
        if service.error:
        print("formatted_string")
        print()

        print("API Services:")
        for service in [availability.openai_api, availability.anthropic_api]:
        status = "[OK]" if service.available else "[FAIL]"  # Use ASCII characters for Windows compatibility
        print("formatted_string")
        if service.error:
        print("formatted_string")
        print()

        print("Summary:")
        print("formatted_string")
        print("formatted_string")

                    # Exit with error code if critical services unavailable
        if not availability.has_real_databases and availability.use_real_services:
        print("")
        ERROR: USE_REAL_SERVICES=true but databases not available")
        sys.exit(1)

        if not availability.has_real_llm_apis and availability.use_real_llm:
        print("")
        ERROR: USE_REAL_LLM=true but LLM APIs not available")
        sys.exit(1)


        if __name__ == "__main__":
        asyncio.run(main())
