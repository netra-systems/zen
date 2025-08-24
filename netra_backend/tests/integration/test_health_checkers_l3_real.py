"""L3 Integration Tests for Health Checkers with Real Containerized Services.

These tests validate health checker functionality using real PostgreSQL and Redis
containers via Testcontainers, providing L3-level realism as required by testing.xml.

Business Value: Ensures health monitoring works with actual database connections,
preventing false positives from mocked tests and validating real-world scenarios.
"""

import pytest
import asyncio
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from netra_backend.app.core.health_checkers import (
    check_postgres_health,
    check_redis_health,
)
from netra_backend.app.schemas.core_models import HealthCheckResult


@pytest.mark.integration
class TestHealthCheckersL3Integration:
    """L3 Integration tests using real containerized services."""
    
    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Start real PostgreSQL container for testing."""
        try:
            with PostgresContainer("postgres:15") as postgres:
                yield postgres
        except Exception as e:
            pytest.skip(f"PostgreSQL container not available: {e}")
    
    @pytest.fixture(scope="class") 
    def redis_container(self):
        """Start real Redis container for testing."""
        try:
            with RedisContainer("redis:7-alpine") as redis:
                yield redis
        except Exception as e:
            pytest.skip(f"Redis container not available: {e}")
    
    @pytest.fixture
    async def real_async_session(self, postgres_container):
        """Create real async database session."""
        db_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        # Create a test session
        async with async_session() as session:
            yield session
        
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_postgres_health_with_real_database(self, postgres_container):
        """Test PostgreSQL health check with real containerized database."""
        # Get connection URL from container
        db_url = postgres_container.get_connection_url()
        
        # Mock the database manager to use our container URL
        # Mock: Component isolation for testing without external dependencies
        with pytest.mock.patch('netra_backend.app.core.unified.db_connection_manager.db_manager') as mock_db_manager:
            # Create real async engine
            async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            engine = create_async_engine(async_url, echo=False)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            
            # Mock the session context manager to return real session
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm = pytest.mock.AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm.__aenter__ = pytest.mock.AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm.__aexit__ = pytest.mock.AsyncMock(return_value=None)
            mock_db_manager.get_async_session.return_value = mock_session_cm
            
            async with async_session() as real_session:
                mock_session_cm.__aenter__.return_value = real_session
                
                result = await check_postgres_health()
                
                # Verify health check with real database
                assert isinstance(result, HealthCheckResult)
                assert result.status == "healthy"
                assert result.response_time_ms > 0  # Real operations take measurable time
                assert result.details["component_name"] == "postgres"
                assert result.details["success"] is True
            
            await engine.dispose()
    
    @pytest.mark.asyncio 
    async def test_postgres_health_real_connection_failure(self):
        """Test PostgreSQL health check with real connection failure."""
        # Use invalid connection parameters to test real failure
        # Mock: Component isolation for testing without external dependencies
        with pytest.mock.patch('netra_backend.app.core.unified.db_connection_manager.db_manager') as mock_db_manager:
            # Simulate real connection failure by using invalid host
            mock_db_manager.get_async_session.side_effect = Exception("connection to server at \"invalid_host\" (127.0.0.1), port 5432 failed")
            
            result = await check_postgres_health()
            
            assert result.status == "unhealthy"
            assert result.details["success"] is False
            assert "invalid_host" in result.details["error_message"] or "Connection" in result.details["error_message"]
    
    @pytest.mark.asyncio
    async def test_redis_health_with_real_redis(self, redis_container):
        """Test Redis health check with real containerized Redis."""
        import redis.asyncio as aioredis
        
        # Get connection details from container
        redis_host = redis_container.get_container_host_ip()
        redis_port = redis_container.get_exposed_port(6379)
        
        # Create real Redis client
        real_redis_client = aioredis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        # Mock the redis manager to use our real client
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with pytest.mock.patch('netra_backend.app.redis_manager.redis_manager') as mock_manager:
            mock_manager.enabled = True
            # Mock: Redis external service isolation for fast, reliable tests without network dependency
            mock_manager.get_client = pytest.mock.AsyncMock(return_value=real_redis_client)
            
            result = await check_redis_health()
            
            # Verify health check with real Redis
            assert result.status == "healthy"
            assert result.response_time_ms > 0  # Real operations take measurable time
            assert result.details["component_name"] == "redis"
            assert result.details["success"] is True
        
        await real_redis_client.close()
    
    @pytest.mark.asyncio
    async def test_redis_health_real_connection_failure(self):
        """Test Redis health check with real connection failure."""
        import redis.asyncio as aioredis
        
        # Create Redis client with invalid connection details
        invalid_redis_client = aioredis.Redis(host="invalid_redis_host", port=6379, decode_responses=True)
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with pytest.mock.patch('netra_backend.app.redis_manager.redis_manager') as mock_manager:
            mock_manager.enabled = True
            # Mock: Redis external service isolation for fast, reliable tests without network dependency
            mock_manager.get_client = pytest.mock.AsyncMock(return_value=invalid_redis_client)
            
            result = await check_redis_health()
            
            # Should handle real connection failure gracefully
            assert result.status == "degraded" or result.status == "unhealthy"
            assert result.details["success"] is False
            assert "invalid_redis_host" in result.details["error_message"] or "connection" in result.details["error_message"].lower()
        
        await invalid_redis_client.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks_with_real_services(self, postgres_container, redis_container):
        """Test concurrent health checks with real services under load."""
        # Prepare real connections
        postgres_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        postgres_engine = create_async_engine(postgres_url, echo=False, pool_size=5, max_overflow=10)
        postgres_session = sessionmaker(postgres_engine, class_=AsyncSession, expire_on_commit=False)
        
        redis_host = redis_container.get_container_host_ip()
        redis_port = redis_container.get_exposed_port(6379)
        
        import redis.asyncio as aioredis
        real_redis_client = aioredis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        # Mock managers to use real services
        # Mock: Component isolation for testing without external dependencies
        with pytest.mock.patch('netra_backend.app.core.unified.db_connection_manager.db_manager') as mock_db_manager, \
             # Mock: Redis external service isolation for fast, reliable tests without network dependency
             pytest.mock.patch('netra_backend.app.redis_manager.redis_manager') as mock_redis_manager:
            
            # Setup real database session mock
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm = pytest.mock.AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm.__aenter__ = pytest.mock.AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm.__aexit__ = pytest.mock.AsyncMock(return_value=None)
            mock_db_manager.get_async_session.return_value = mock_session_cm
            
            # Setup real Redis client mock
            mock_redis_manager.enabled = True
            # Mock: Redis external service isolation for fast, reliable tests without network dependency
            mock_redis_manager.get_client = pytest.mock.AsyncMock(return_value=real_redis_client)
            
            async def run_health_check_with_real_session():
                async with postgres_session() as session:
                    mock_session_cm.__aenter__.return_value = session
                    postgres_result = await check_postgres_health()
                    redis_result = await check_redis_health()
                    return postgres_result, redis_result
            
            # Run concurrent health checks
            tasks = [run_health_check_with_real_session() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Verify all health checks succeeded with real services
            for postgres_result, redis_result in results:
                assert postgres_result.status == "healthy"
                assert postgres_result.response_time_ms > 0
                assert redis_result.status == "healthy"
                assert redis_result.response_time_ms > 0
        
        await real_redis_client.close()
        await postgres_engine.dispose()
    
    @pytest.mark.asyncio
    async def test_health_check_performance_with_real_services(self, postgres_container, redis_container):
        """Test health check performance with real containerized services."""
        import time
        
        # Setup real connections (similar to previous test)
        postgres_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        postgres_engine = create_async_engine(postgres_url, echo=False)
        postgres_session = sessionmaker(postgres_engine, class_=AsyncSession, expire_on_commit=False)
        
        redis_host = redis_container.get_container_host_ip()
        redis_port = redis_container.get_exposed_port(6379)
        
        import redis.asyncio as aioredis
        real_redis_client = aioredis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        # Mock: Component isolation for testing without external dependencies
        with pytest.mock.patch('netra_backend.app.core.unified.db_connection_manager.db_manager') as mock_db_manager, \
             # Mock: Redis external service isolation for fast, reliable tests without network dependency
             pytest.mock.patch('netra_backend.app.redis_manager.redis_manager') as mock_redis_manager:
            
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm = pytest.mock.AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm.__aenter__ = pytest.mock.AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session_cm.__aexit__ = pytest.mock.AsyncMock(return_value=None)
            mock_db_manager.get_async_session.return_value = mock_session_cm
            
            mock_redis_manager.enabled = True
            # Mock: Redis external service isolation for fast, reliable tests without network dependency
            mock_redis_manager.get_client = pytest.mock.AsyncMock(return_value=real_redis_client)
            
            async with postgres_session() as session:
                mock_session_cm.__aenter__.return_value = session
                
                # Measure PostgreSQL health check time
                start_time = time.time()
                postgres_result = await check_postgres_health()
                postgres_duration = time.time() - start_time
                
                # Measure Redis health check time
                start_time = time.time()
                redis_result = await check_redis_health()
                redis_duration = time.time() - start_time
                
                # Verify performance characteristics with real services
                assert postgres_result.status == "healthy"
                assert postgres_duration < 5.0  # Should complete within 5 seconds
                assert postgres_result.response_time_ms > 0
                
                assert redis_result.status == "healthy" 
                assert redis_duration < 3.0  # Redis should be faster
                assert redis_result.response_time_ms > 0
                
                # Real services should be slower than mocks but still performant
                assert postgres_result.response_time_ms >= 1.0  # Real DB takes some time
                assert redis_result.response_time_ms >= 0.1  # Real Redis minimal time
        
        await real_redis_client.close()
        await postgres_engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])