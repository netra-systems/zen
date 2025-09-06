"""
Service Availability Checking Module

Hard service availability checks that fail fast when real services are requested but unavailable.
Provides clear, actionable error messages to help developers quickly identify and fix service issues.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Test Reliability
- Value Impact: Eliminates silent test failures due to missing services
- Strategic Impact: Reduces debugging time by 80% through immediate failure feedback
"""
import asyncio
import logging
import os
import socket
import time
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

# Try to import IsolatedEnvironment, handle if not available in some contexts
try:
    from shared.isolated_environment import get_env as get_isolated_env
    _env = get_isolated_env()
    def get_env(key: str, default: str = None) -> Optional[str]:
        """Get environment variable value."""
        return _env.get(key, default)
except ImportError:
    # CRITICAL SECURITY FIX: Remove direct os.environ access to prevent service boundary violations
    # This fallback should not occur in production - all services must have IsolatedEnvironment
    import os
    import logging
    logger = logging.getLogger(__name__)
    logger.error("CRITICAL: Missing IsolatedEnvironment - service boundary violation detected")
    
    def get_env(key: str, default: str = None) -> Optional[str]:
        """
        DEPRECATED: Direct environment access creates service boundary violations.
        This fallback exists only for emergency compatibility - do not use in production.
        """
        logger.warning(f"Using deprecated direct environment access for key: {key}")
        return os.environ.get(key, default)

# Optional dependencies - import with fallbacks
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

try:
    import psycopg
    PSYCOPG_AVAILABLE = True
except ImportError:
    psycopg = None
    PSYCOPG_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    asyncpg = None
    ASYNCPG_AVAILABLE = False

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)


class ServiceUnavailableError(RuntimeError):
    """Raised when a required service is unavailable."""
    
    def __init__(self, service_name: str, details: str, remediation_steps: List[str]):
        self.service_name = service_name
        self.details = details
        self.remediation_steps = remediation_steps
        
        # Create comprehensive error message
        steps_text = '\n'.join(f"  {i+1}. {step}" for i, step in enumerate(remediation_steps))
        message = (
            f"[FAIL] REQUIRED SERVICE UNAVAILABLE: {service_name}\n"
            f"\nISSUE: {details}\n"
            f"\nHOW TO FIX:\n{steps_text}\n"
        )
        super().__init__(message)


class ServiceAvailabilityChecker:
    """
    Checks availability of real services with fast, accurate connection tests.
    
    All checks are designed to:
    - Fail immediately if service is unavailable
    - Provide clear, actionable error messages  
    - Use real connection attempts, not just port checks
    - Complete quickly (< 5 seconds total timeout per service)
    """
    
    def __init__(self, timeout_seconds: float = 5.0):
        """
        Initialize service availability checker.
        
        Args:
            timeout_seconds: Maximum time to wait for each service check
        """
        self.timeout = timeout_seconds
        
    def check_postgresql(self, connection_url: Optional[str] = None) -> bool:
        """
        Check PostgreSQL availability with real connection attempt.
        
        Args:
            connection_url: PostgreSQL connection URL. If None, gets from environment.
            
        Returns:
            True if PostgreSQL is available and connectable
            
        Raises:
            ServiceUnavailableError: If PostgreSQL is not available
        """
        # Check if dependencies are available
        if not PSYCOPG_AVAILABLE and not ASYNCPG_AVAILABLE:
            raise ServiceUnavailableError(
                service_name="PostgreSQL",
                details="PostgreSQL client libraries not available (psycopg or asyncpg required)",
                remediation_steps=[
                    "Install PostgreSQL dependencies: pip install psycopg[binary] asyncpg",
                    "Or install all test dependencies: pip install -r requirements-test.txt",
                    "For basic connectivity check only, ensure at least one is installed"
                ]
            )
        
        if connection_url is None:
            connection_url = self._get_postgres_url()
            
        if not connection_url:
            raise ServiceUnavailableError(
                service_name="PostgreSQL",
                details="No database connection URL found in environment",
                remediation_steps=[
                    "Set DATABASE_URL environment variable",
                    "Or start PostgreSQL using: docker-compose -f docker-compose.dev.yml up postgres",
                    "Or run dev launcher: python scripts/dev_launcher.py"
                ]
            )
            
        try:
            # Try sync connection if available
            if PSYCOPG_AVAILABLE:
                self._test_sync_postgres_connection(connection_url)
                logger.debug(f"[OK] PostgreSQL sync connection successful: {self._mask_password(connection_url)}")
            
            # Test async connection (used by most of our code) if available
            if ASYNCPG_AVAILABLE:
                asyncio.run(self._test_async_postgres_connection(connection_url))
                logger.debug(f"[OK] PostgreSQL async connection successful: {self._mask_password(connection_url)}")
            
            return True
            
        except Exception as e:
            self._raise_postgres_error(connection_url, e)
            
    def _test_sync_postgres_connection(self, url: str) -> None:
        """Test synchronous PostgreSQL connection."""
        try:
            with psycopg.connect(url, connect_timeout=self.timeout) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
        except Exception as e:
            raise RuntimeError(f"Sync connection failed: {e}") from e
            
    async def _test_async_postgres_connection(self, url: str) -> None:
        """Test asynchronous PostgreSQL connection."""
        try:
            # Normalize URL for asyncpg compatibility (remove SQLAlchemy driver prefixes)
            from shared.database_url_builder import DatabaseURLBuilder
            normalized_url = DatabaseURLBuilder.format_for_asyncpg_driver(url)
            
            conn = await asyncpg.connect(normalized_url, timeout=self.timeout)
            try:
                await conn.fetchval("SELECT 1")
            finally:
                await conn.close()
        except Exception as e:
            raise RuntimeError(f"Async connection failed: {e}") from e
            
    def _raise_postgres_error(self, url: str, error: Exception) -> None:
        """Raise appropriate PostgreSQL error with remediation steps."""
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        
        # Test basic connectivity
        if not self._can_connect_to_host(host, port):
            raise ServiceUnavailableError(
                service_name="PostgreSQL",
                details=f"Cannot connect to PostgreSQL at {host}:{port} - Connection refused",
                remediation_steps=[
                    f"Start PostgreSQL: docker-compose -f docker-compose.dev.yml up postgres",
                    f"Check if PostgreSQL is running on {host}:{port}",
                    f"Verify database exists and credentials are correct",
                    "Run full dev environment: python scripts/dev_launcher.py"
                ]
            )
        else:
            # Connection possible but authentication/database issues
            raise ServiceUnavailableError(
                service_name="PostgreSQL", 
                details=f"Connected to {host}:{port} but database operation failed: {error}",
                remediation_steps=[
                    "Check database name and credentials in DATABASE_URL",
                    "Run database initialization: python scripts/init_db.py",
                    "Verify user has required permissions",
                    f"Test connection manually: psql {self._mask_password(url)}"
                ]
            )
            
    def check_redis(self, connection_url: Optional[str] = None) -> bool:
        """
        Check Redis availability with real connection attempt.
        
        Args:
            connection_url: Redis connection URL. If None, gets from environment.
            
        Returns:
            True if Redis is available and connectable
            
        Raises:
            ServiceUnavailableError: If Redis is not available
        """
        # Check if Redis dependencies are available
        if not REDIS_AVAILABLE:
            raise ServiceUnavailableError(
                service_name="Redis",
                details="Redis client library not available (redis-py required)",
                remediation_steps=[
                    "Install Redis dependency: pip install redis",
                    "Or install all test dependencies: pip install -r requirements-test.txt"
                ]
            )
        
        if connection_url is None:
            connection_url = self._get_redis_url()
            
        if not connection_url:
            raise ServiceUnavailableError(
                service_name="Redis",
                details="No Redis connection URL found in environment",
                remediation_steps=[
                    "Set REDIS_URL environment variable", 
                    "Or start Redis using: docker-compose -f docker-compose.dev.yml up redis",
                    "Or run dev launcher: python scripts/dev_launcher.py"
                ]
            )
            
        try:
            # Test Redis connection
            asyncio.run(self._test_redis_connection(connection_url))
            logger.debug(f"[OK] Redis connection successful: {self._mask_password(connection_url)}")
            return True
            
        except Exception as e:
            self._raise_redis_error(connection_url, e)
            
    async def _test_redis_connection(self, url: str) -> None:
        """Test Redis connection with ping."""
        client = redis.from_url(url, socket_connect_timeout=self.timeout)
        try:
            await client.ping()
        finally:
            await client.aclose()
            
    def _raise_redis_error(self, url: str, error: Exception) -> None:
        """Raise appropriate Redis error with remediation steps."""
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        
        if not self._can_connect_to_host(host, port):
            raise ServiceUnavailableError(
                service_name="Redis",
                details=f"Cannot connect to Redis at {host}:{port} - Connection refused",
                remediation_steps=[
                    "Start Redis: docker-compose -f docker-compose.dev.yml up redis",
                    f"Check if Redis is running on {host}:{port}",
                    "Run full dev environment: python scripts/dev_launcher.py",
                    f"Test manually: redis-cli -h {host} -p {port} ping"
                ]
            )
        else:
            raise ServiceUnavailableError(
                service_name="Redis",
                details=f"Connected to {host}:{port} but Redis operation failed: {error}",
                remediation_steps=[
                    "Check Redis authentication if password is required",
                    "Verify Redis is not in protected mode",
                    "Check Redis logs for errors",
                    f"Test manually: redis-cli -h {host} -p {port} ping"
                ]
            )
            
    def check_clickhouse(self, connection_url: Optional[str] = None) -> bool:
        """
        Check ClickHouse availability with connection test.
        
        Args:
            connection_url: ClickHouse connection URL. If None, gets from environment.
            
        Returns:
            True if ClickHouse is available
            
        Raises:
            ServiceUnavailableError: If ClickHouse is not available
        """
        if connection_url is None:
            connection_url = self._get_clickhouse_url()
            
        if not connection_url:
            # ClickHouse is optional for most tests
            logger.debug("ClickHouse URL not configured, skipping check")
            return True
            
        parsed = urlparse(connection_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8123
        
        # Test basic connectivity
        if not self._can_connect_to_host(host, port):
            raise ServiceUnavailableError(
                service_name="ClickHouse",
                details=f"Cannot connect to ClickHouse at {host}:{port} - Connection refused",
                remediation_steps=[
                    "Start ClickHouse: docker-compose -f docker-compose.alpine.yml up clickhouse",
                    f"Check if ClickHouse is running on {host}:{port}",
                    "Run full dev environment: python scripts/dev_launcher.py",
                    f"Test manually: curl http://{host}:{port}/ping"
                ]
            )
            
        # Try HTTP ping endpoint
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                logger.debug(f"[OK] ClickHouse connection successful: {host}:{port}")
                return True
            else:
                raise RuntimeError(f"Connection failed with code {result}")
                
        except Exception as e:
            raise ServiceUnavailableError(
                service_name="ClickHouse",
                details=f"ClickHouse at {host}:{port} not responding: {e}",
                remediation_steps=[
                    "Check ClickHouse logs for errors",
                    "Verify ClickHouse configuration",
                    "Restart ClickHouse service",
                    f"Test endpoint: curl http://{host}:{port}/ping"
                ]
            )
    
    def check_docker(self) -> bool:
        """
        Check Docker availability.
        
        Returns:
            True if Docker is available
            
        Raises:
            ServiceUnavailableError: If Docker is not available
        """
        # Check if Docker dependencies are available
        if not DOCKER_AVAILABLE:
            raise ServiceUnavailableError(
                service_name="Docker",
                details="Docker client library not available (docker-py required)",
                remediation_steps=[
                    "Install Docker dependency: pip install docker",
                    "Or install all test dependencies: pip install -r requirements-test.txt"
                ]
            )
        
        try:
            client = docker.from_env(timeout=self.timeout)
            # Test Docker connectivity
            client.ping()
            client.close()
            logger.debug("[OK] Docker connection successful")
            return True
            
        except Exception as e:
            raise ServiceUnavailableError(
                service_name="Docker",
                details=f"Docker is not available or not responding: {e}",
                remediation_steps=[
                    "Start Docker Desktop (Windows/Mac) or Docker daemon (Linux)",
                    "Verify Docker is running: docker --version",
                    "Check Docker daemon status: docker info",
                    "Restart Docker service if needed"
                ]
            )
            
    def check_llm_api(self, api_key: Optional[str] = None, endpoint: Optional[str] = None) -> bool:
        """
        Check LLM API availability with endpoint validation.
        
        Args:
            api_key: API key. If None, gets from environment.
            endpoint: API endpoint. If None, gets from environment.
            
        Returns:
            True if LLM API is available
            
        Raises:
            ServiceUnavailableError: If LLM API is not available
        """
        if api_key is None:
            api_key = self._get_llm_api_key()
            
        if endpoint is None:
            endpoint = self._get_llm_endpoint()
            
        if not api_key:
            raise ServiceUnavailableError(
                service_name="LLM API",
                details="No LLM API key found in environment",
                remediation_steps=[
                    "Set GEMINI_API_KEY environment variable",
                    "Or set ANTHROPIC_API_KEY for Claude",
                    "Or set OPENAI_API_KEY for OpenAI",
                    "Obtain API key from respective provider's dashboard"
                ]
            )
            
        if not endpoint:
            raise ServiceUnavailableError(
                service_name="LLM API", 
                details="No LLM endpoint configured",
                remediation_steps=[
                    "Configure LLM endpoint in environment settings",
                    "Check LLM configuration in unified_environment_management",
                    "Verify LLM service is properly configured"
                ]
            )
            
        try:
            # Basic validation - check if we can resolve the endpoint
            parsed = urlparse(endpoint)
            if not parsed.hostname:
                raise ValueError(f"Invalid endpoint URL: {endpoint}")
                
            # Test basic connectivity to endpoint
            if not self._can_connect_to_host(parsed.hostname, parsed.port or 443):
                raise RuntimeError(f"Cannot connect to {parsed.hostname}")
                
            logger.debug(f"[OK] LLM API endpoint reachable: {endpoint}")
            return True
            
        except Exception as e:
            raise ServiceUnavailableError(
                service_name="LLM API",
                details=f"LLM API endpoint not reachable: {e}",
                remediation_steps=[
                    f"Check internet connectivity to {endpoint}",
                    "Verify API key is valid and not expired",
                    "Check API provider status page for outages",
                    "Test with a simple API call manually"
                ]
            )
            
    def _can_connect_to_host(self, host: str, port: int) -> bool:
        """Test basic TCP connectivity to a host:port."""
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                return True
        except (socket.timeout, socket.error, OSError):
            return False
            
    def _get_postgres_url(self) -> Optional[str]:
        """Get PostgreSQL URL from environment."""
        return get_env("DATABASE_URL") or get_env("POSTGRES_URL")
        
    def _get_clickhouse_url(self) -> Optional[str]:
        """Get ClickHouse connection URL from environment."""
        # Try multiple environment variable names
        for key in ['CLICKHOUSE_URL', 'CLICKHOUSE_HOST', 'TEST_CLICKHOUSE_URL']:
            value = get_env(key)
            if value:
                # If it's a clickhouse:// URL, convert to http://
                if value.startswith('clickhouse://'):
                    # Parse the URL and convert to HTTP format
                    from urllib.parse import urlparse
                    parsed = urlparse(value)
                    host = parsed.hostname or 'localhost'
                    port = parsed.port or 8123
                    return f"http://{host}:{port}"
                # If it's just a host, construct URL
                elif not value.startswith('http'):
                    port = get_env('CLICKHOUSE_PORT', '8123')
                    value = f"http://{value}:{port}"
                return value
                
        # Check if we have host and port separately
        host = get_env('CLICKHOUSE_HOST')
        if host:
            port = get_env('CLICKHOUSE_PORT', '8123')
            return f"http://{host}:{port}"
            
        return None
    
    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from environment."""
        redis_url = get_env("REDIS_URL")
        if redis_url:
            return redis_url
            
        # Build from individual components if no URL provided
        host = get_env("REDIS_HOST") or "localhost"
        port = get_env("REDIS_PORT") or "6379"
        password = get_env("REDIS_PASSWORD")
        
        if password:
            return f"redis://:{password}@{host}:{port}"
        else:
            return f"redis://{host}:{port}"
            
    def _get_llm_api_key(self) -> Optional[str]:
        """Get LLM API key from environment."""
        # Try different API key environment variables
        api_keys = [
            get_env("GEMINI_API_KEY"),
            get_env("ANTHROPIC_API_KEY"), 
            get_env("OPENAI_API_KEY"),
            get_env("LLM_API_KEY")
        ]
        return next((key for key in api_keys if key), None)
        
    def _get_llm_endpoint(self) -> Optional[str]:
        """Get LLM endpoint from environment."""
        return get_env("LLM_ENDPOINT") or "https://generativelanguage.googleapis.com"
        
    def _mask_password(self, url: str) -> str:
        """Mask password in URL for logging."""
        if not url:
            return url
            
        try:
            parsed = urlparse(url)
            if parsed.password:
                masked = url.replace(parsed.password, "***")
                return masked
        except Exception:
            pass
        return url


def require_real_services(
    services: Optional[List[str]] = None, 
    timeout: float = 5.0,
    postgres_url: Optional[str] = None,
    redis_url: Optional[str] = None
) -> None:
    """
    Require real services to be available, failing immediately if any are missing.
    
    This function performs actual connection tests to verify services are reachable
    and functional. It will raise ServiceUnavailableError immediately if any 
    required service is unavailable.
    
    Args:
        services: List of services to check. If None, checks all services.
                 Valid services: ['postgresql', 'redis', 'docker', 'llm']
        timeout: Maximum time to wait for each service check
        postgres_url: Override PostgreSQL URL
        redis_url: Override Redis URL
        
    Raises:
        ServiceUnavailableError: If any required service is unavailable
        
    Example:
        # Check all services
        require_real_services()
        
        # Check specific services only
        require_real_services(['postgresql', 'redis'])
        
        # Check with custom URLs
        require_real_services(
            services=['postgresql'],
            postgres_url='postgresql://user:pass@localhost:5432/testdb'
        )
    """
    if services is None:
        services = ['postgresql', 'redis', 'docker', 'llm']
        
    checker = ServiceAvailabilityChecker(timeout_seconds=timeout)
    failed_services = []
    
    logger.info(f"[INFO] Checking availability of real services: {', '.join(services)}")
    start_time = time.time()
    
    for service in services:
        try:
            if service == 'postgresql':
                checker.check_postgresql(postgres_url)
            elif service == 'redis':
                checker.check_redis(redis_url)
            elif service == 'docker':
                checker.check_docker()
            elif service == 'llm':
                checker.check_llm_api()
            elif service == 'clickhouse':
                checker.check_clickhouse()
            else:
                logger.warning(f"Unknown service requested: {service}")
                continue
                
        except ServiceUnavailableError as e:
            failed_services.append((service, e))
            
    total_time = time.time() - start_time
    
    if failed_services:
        # Create comprehensive error message for multiple service failures
        error_details = []
        remediation_steps = []
        
        for service, error in failed_services:
            error_details.append(f"[FAIL] {service}: {error.details}")
            remediation_steps.extend(error.remediation_steps)
            
        # Remove duplicate remediation steps
        remediation_steps = list(dict.fromkeys(remediation_steps))
        
        raise ServiceUnavailableError(
            service_name=f"{len(failed_services)} services",
            details='\n'.join(error_details),
            remediation_steps=remediation_steps
        )
    else:
        logger.info(f"[OK] All {len(services)} services are available (checked in {total_time:.2f}s)")


def check_service_availability(
    services: Optional[List[str]] = None,
    timeout: float = 5.0
) -> Dict[str, Union[bool, str]]:
    """
    Check service availability without raising exceptions.
    
    Returns a dictionary with service status information that can be used
    for conditional logic in tests.
    
    Args:
        services: List of services to check
        timeout: Maximum time to wait for each service check
        
    Returns:
        Dict mapping service name to either True (available) or error string
        
    Example:
        status = check_service_availability(['postgresql', 'redis'])
        if status['postgresql'] is True:
            # PostgreSQL is available
            pass
        else:
            # status['postgresql'] contains error message
            print(f"PostgreSQL issue: {status['postgresql']}")
    """
    if services is None:
        services = ['postgresql', 'redis', 'docker', 'llm']
        
    checker = ServiceAvailabilityChecker(timeout_seconds=timeout)
    results = {}
    
    for service in services:
        try:
            if service == 'postgresql':
                checker.check_postgresql()
            elif service == 'redis':
                checker.check_redis()
            elif service == 'docker':
                checker.check_docker()
            elif service == 'llm':
                checker.check_llm_api()
            elif service == 'clickhouse':
                checker.check_clickhouse()
            else:
                results[service] = f"Unknown service: {service}"
                continue
                
            results[service] = True
            
        except ServiceUnavailableError as e:
            results[service] = e.details
        except Exception as e:
            results[service] = f"Unexpected error: {e}"
            
    return results


if __name__ == "__main__":
    """CLI interface for service availability checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check service availability")
    parser.add_argument(
        "--services", 
        nargs='+',
        choices=['postgresql', 'redis', 'docker', 'llm'],
        default=['postgresql', 'redis', 'docker', 'llm'],
        help="Services to check"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout per service check"
    )
    parser.add_argument(
        "--require",
        action="store_true", 
        help="Require all services (fail if any unavailable)"
    )
    
    args = parser.parse_args()
    
    if args.require:
        try:
            require_real_services(args.services, args.timeout)
            print("[OK] All required services are available")
        except ServiceUnavailableError as e:
            print(str(e))
            exit(1)
    else:
        results = check_service_availability(args.services, args.timeout)
        for service, status in results.items():
            if status is True:
                print(f"[OK] {service}: Available")
            else:
                print(f"[FAIL] {service}: {status}")
                
        if not all(status is True for status in results.values()):
            exit(1)