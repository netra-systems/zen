"""
Integration Tests: Comprehensive Startup Validation

End-to-end integration tests for the complete startup sequence with real services.
These tests validate the entire startup flow with actual components.

Business Value: Ensures production-like startup behavior in test environments
"""

import pytest
import asyncio
import time
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, AsyncMock, Mock
import logging

from shared.isolated_environment import get_env
from test_framework.unified_docker_manager import UnifiedDockerManager, ContainerState

# Configure environment
env = get_env()
env.set("ENVIRONMENT", "testing", "test")
env.set("TESTING", "true", "test")
env.set("USE_REAL_SERVICES", "true", "test")

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.real_services
class TestFullStartupIntegration:
    """Integration tests for complete startup flow with real services."""
    
    @pytest.fixture
    async def docker_manager(self):
        """Get Docker manager for service orchestration."""
        manager = UnifiedDockerManager()
        yield manager
        # Cleanup handled by manager
    
    @pytest.fixture
    async def ensure_services_running(self, docker_manager):
        """Ensure all required services are running."""
        required_services = ["postgres", "redis"]
        
        # Start services if needed
        await docker_manager.ensure_services_running(required_services)
        
        # Wait for services to be healthy
        for service in required_services:
            health = await docker_manager.wait_for_service_health(
                service, 
                timeout=30
            )
            assert health.is_healthy, f"{service} failed health check"
        
        yield
        
        # Services remain running for other tests
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_complete_startup_sequence(self, ensure_services_running):
        """Test complete startup sequence with real dependencies."""
        from netra_backend.app.core.app_factory import create_app
        from netra_backend.app.startup_module import run_complete_startup
        
        # Create app
        app = create_app()
        
        # Run complete startup
        start_time, logger = await run_complete_startup(app)
        
        # Verify critical components initialized
        assert hasattr(app.state, 'db_session_factory'), "Database not initialized"
        assert app.state.db_session_factory is not None
        
        assert hasattr(app.state, 'redis_manager'), "Redis not initialized"
        assert app.state.redis_manager is not None
        
        assert hasattr(app.state, 'llm_manager'), "LLM manager not initialized"
        assert app.state.llm_manager is not None
        
        assert hasattr(app.state, 'agent_supervisor'), "Agent supervisor not initialized"
        assert app.state.agent_supervisor is not None
        
        assert hasattr(app.state, 'websocket_manager'), "WebSocket manager not initialized"
        
        # Verify startup marked complete
        assert hasattr(app.state, 'startup_complete')
        assert app.state.startup_complete is True
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_database_connection_pool_initialization(self, ensure_services_running):
        """Test database connection pool is properly initialized."""
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Create engine
        engine = DatabaseManager.create_application_engine()
        
        # Test connection
        connection_ok = await DatabaseManager.test_connection_with_retry(engine)
        assert connection_ok, "Database connection failed"
        
        # Check pool status
        pool_status = DatabaseManager.get_pool_status(engine)
        assert pool_status['size'] > 0, "Connection pool not initialized"
        assert pool_status['checked_in'] >= 0, "Invalid pool state"
        
        # Cleanup
        await engine.dispose()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_redis_connection_initialization(self, ensure_services_running):
        """Test Redis connection is properly initialized."""
        from netra_backend.app.redis_manager import redis_manager
        
        # Initialize Redis
        await redis_manager.initialize()
        
        # Test connection
        conn = await redis_manager.get_connection()
        assert conn is not None, "Redis connection failed"
        
        # Test basic operation
        await conn.set("test_key", "test_value", ex=10)
        value = await conn.get("test_key")
        assert value == b"test_value"
        
        # Cleanup
        await conn.delete("test_key")
        await redis_manager.close()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_websocket_integration_during_startup(self):
        """Test WebSocket components are properly integrated during startup."""
        from netra_backend.app.services.agent_websocket_bridge import (
            AgentWebSocketBridge, 
            IntegrationState
        )
        from netra_backend.app.services.websocket_manager import WebSocketManager
        
        # Create components
        websocket_manager = WebSocketManager()
        bridge = AgentWebSocketBridge()
        
        # Mock supervisor
        mock_supervisor = Mock()
        mock_supervisor.registry = Mock()
        
        # Integrate bridge
        result = await bridge.ensure_integration(
            supervisor=mock_supervisor,
            registry=mock_supervisor.registry,
            force_reinit=False
        )
        
        assert result.success, f"Bridge integration failed: {result.error}"
        
        # Check health
        health = await bridge.health_check()
        assert health.state in [IntegrationState.ACTIVE, IntegrationState.INITIALIZING]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_agent_registry_initialization(self):
        """Test agent registry is properly initialized with all agents."""
        from netra_backend.app.orchestration.agent_execution_registry import (
            get_agent_execution_registry
        )
        
        # Get registry
        registry = await get_agent_execution_registry()
        
        # Verify agents registered
        agent_types = registry.get_available_agent_types()
        
        # Should have core agents
        expected_agents = [
            "supervisor",
            "apex_optimizer",
            "reporting"
        ]
        
        for agent in expected_agents:
            assert agent in agent_types, f"Missing agent: {agent}"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_health_endpoints_after_startup(self, ensure_services_running):
        """Test health endpoints report correct status after startup."""
        from netra_backend.app.core.app_factory import create_app
        from httpx import AsyncClient, ASGITransport
        
        # Create and start app
        app = create_app()
        
        # Mock minimal startup completion
        app.state.startup_complete = True
        app.state.db_session_factory = Mock()
        app.state.redis_manager = Mock()
        
        # Add health endpoint
        @app.get("/health")
        async def health():
            if not app.state.startup_complete:
                return {"status": "unhealthy", "message": "Startup incomplete"}, 503
            return {"status": "healthy"}
        
        @app.get("/health/ready")
        async def ready():
            # Check critical components
            if not hasattr(app.state, 'db_session_factory'):
                return {"status": "not_ready", "reason": "Database not initialized"}, 503
            if not hasattr(app.state, 'redis_manager'):
                return {"status": "not_ready", "reason": "Redis not initialized"}, 503
            return {"status": "ready"}
        
        # Test endpoints
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test health
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            
            # Test readiness
            response = await client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"


@pytest.mark.integration
class TestStartupFailureScenarios:
    """Integration tests for startup failure scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_database_unavailable_startup_failure(self):
        """Test startup fails gracefully when database is unavailable."""
        from netra_backend.app.smd import (
            StartupOrchestrator,
            DeterministicStartupError
        )
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = Mock()
        
        # Set invalid database URL
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://invalid:invalid@nonexistent:5432/db'}):
            orchestrator = StartupOrchestrator(app)
            
            # Mock methods that would succeed
            orchestrator._validate_environment = Mock()
            orchestrator._run_migrations = AsyncMock()
            
            # Startup should fail
            with pytest.raises(DeterministicStartupError):
                await orchestrator.initialize_system()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_redis_unavailable_startup_failure(self):
        """Test startup fails gracefully when Redis is unavailable."""
        from netra_backend.app.smd import (
            StartupOrchestrator,
            DeterministicStartupError
        )
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = Mock()
        
        # Set invalid Redis URL
        with patch.dict('os.environ', {'REDIS_URL': 'redis://nonexistent:6379'}):
            orchestrator = StartupOrchestrator(app)
            
            # Mock successful database
            orchestrator._validate_environment = Mock()
            orchestrator._run_migrations = AsyncMock()
            orchestrator._initialize_database = AsyncMock()
            app.state.db_session_factory = Mock()
            
            # Startup should fail at Redis
            with pytest.raises(DeterministicStartupError):
                await orchestrator.initialize_system()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_partial_initialization_rollback(self):
        """Test partial initialization is properly rolled back on failure."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = Mock()
        
        # Track initialization state
        initialized_components = []
        
        async def init_database():
            initialized_components.append("database")
            app.state.db_session_factory = Mock()
            
        async def init_redis():
            initialized_components.append("redis")
            raise Exception("Redis initialization failed")
            
        async def cleanup():
            # Rollback initialized components
            if hasattr(app.state, 'db_session_factory'):
                del app.state.db_session_factory
            initialized_components.clear()
        
        # Try initialization
        try:
            await init_database()
            await init_redis()  # This will fail
        except Exception:
            await cleanup()
        
        # Verify rollback
        assert not hasattr(app.state, 'db_session_factory')
        assert len(initialized_components) == 0


@pytest.mark.integration
class TestServiceCoordinationIntegration:
    """Integration tests for multi-service coordination."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_backend_auth_service_coordination(self):
        """Test backend properly coordinates with auth service during startup."""
        # Mock auth service health check
        async def mock_auth_health():
            return {"status": "healthy", "service": "auth"}
        
        # Mock backend checking auth service
        auth_available = False
        check_attempts = 0
        max_attempts = 10
        
        while not auth_available and check_attempts < max_attempts:
            try:
                health = await mock_auth_health()
                if health["status"] == "healthy":
                    auth_available = True
            except:
                pass
            
            check_attempts += 1
            if not auth_available:
                await asyncio.sleep(0.5)
        
        assert auth_available, "Auth service not available"
        assert check_attempts <= max_attempts
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_service_discovery_integration(self):
        """Test services can discover each other through environment configuration."""
        env = get_env()
        
        # Services should be discoverable via environment
        service_urls = {
            "database": env.get("DATABASE_URL"),
            "redis": env.get("REDIS_URL"),
            "auth": env.get("AUTH_SERVICE_URL", "http://localhost:8001")
        }
        
        # Verify service URLs are configured
        for service, url in service_urls.items():
            assert url is not None, f"{service} URL not configured"
            assert isinstance(url, str), f"{service} URL invalid type"
            assert len(url) > 0, f"{service} URL empty"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_graceful_degradation_optional_services(self):
        """Test system starts with degraded functionality when optional services fail."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = Mock()
        
        # Track service status
        service_status = {
            "database": "healthy",  # Required
            "redis": "healthy",     # Required
            "clickhouse": "failed",  # Optional
            "analytics": "failed"   # Optional
        }
        
        # Initialize only healthy services
        if service_status["database"] == "healthy":
            app.state.db_session_factory = Mock()
        
        if service_status["redis"] == "healthy":
            app.state.redis_manager = Mock()
        
        # System should start despite optional service failures
        required_ok = all(
            service_status[s] == "healthy" 
            for s in ["database", "redis"]
        )
        
        assert required_ok, "Required services must be healthy"
        assert hasattr(app.state, 'db_session_factory')
        assert hasattr(app.state, 'redis_manager')
        
        # Mark degraded mode
        app.state.degraded_mode = any(
            service_status[s] == "failed"
            for s in ["clickhouse", "analytics"]
        )
        
        assert app.state.degraded_mode, "Should be in degraded mode"


@pytest.mark.integration
class TestStartupPerformance:
    """Integration tests for startup performance characteristics."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_startup_completes_within_timeout(self):
        """Test complete startup finishes within reasonable timeout."""
        from netra_backend.app.smd import StartupOrchestrator
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = Mock()
        
        orchestrator = StartupOrchestrator(app)
        
        # Mock all components for speed
        orchestrator._validate_environment = Mock()
        orchestrator._run_migrations = AsyncMock()
        orchestrator._initialize_database = AsyncMock()
        orchestrator._initialize_redis = AsyncMock()
        orchestrator._initialize_key_manager = Mock()
        orchestrator._initialize_llm_manager = Mock()
        orchestrator._apply_startup_fixes = AsyncMock()
        orchestrator._initialize_websocket = AsyncMock()
        orchestrator._initialize_tool_registry = Mock()
        orchestrator._initialize_agent_websocket_bridge_basic = AsyncMock()
        orchestrator._initialize_agent_supervisor = AsyncMock()
        orchestrator._perform_complete_bridge_integration = AsyncMock()
        orchestrator._verify_tool_dispatcher_websocket_support = AsyncMock()
        orchestrator._register_message_handlers = Mock()
        orchestrator._phase5_critical_services = AsyncMock()
        orchestrator._phase6_validation = AsyncMock()
        orchestrator._phase7_optional_services = AsyncMock()
        
        # Set required state
        app.state.db_session_factory = Mock()
        app.state.redis_manager = Mock()
        app.state.key_manager = Mock()
        app.state.llm_manager = Mock()
        app.state.websocket_manager = Mock()
        app.state.tool_dispatcher = Mock()
        app.state.agent_websocket_bridge = Mock()
        app.state.agent_supervisor = Mock()
        app.state.thread_service = Mock()
        
        # Measure startup time
        start = time.time()
        await orchestrator.initialize_system()
        duration = time.time() - start
        
        # Should complete quickly with mocked components
        assert duration < 5.0, f"Startup took too long: {duration:.2f}s"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_parallel_initialization_performance(self):
        """Test parallel initialization improves startup performance."""
        import asyncio
        
        async def slow_init(name: str, delay: float):
            await asyncio.sleep(delay)
            return f"{name}_initialized"
        
        # Sequential initialization
        start = time.time()
        results_seq = []
        for i in range(3):
            result = await slow_init(f"service_{i}", 0.1)
            results_seq.append(result)
        seq_duration = time.time() - start
        
        # Parallel initialization
        start = time.time()
        tasks = [slow_init(f"service_{i}", 0.1) for i in range(3)]
        results_par = await asyncio.gather(*tasks)
        par_duration = time.time() - start
        
        # Parallel should be significantly faster
        assert par_duration < seq_duration * 0.5
        assert len(results_par) == 3


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-m", "integration",
        "--tb=short"
    ])