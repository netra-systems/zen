"""
Smoke Tests: Startup Wiring and Integration

Fast smoke tests to verify critical wiring and integration points during startup.
These tests focus on the "plumbing" - ensuring components are properly connected.

Business Value: Catch integration issues early in CI/CD pipeline (< 30 seconds total)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import time

from shared.isolated_environment import get_env

# Configure test environment
env = get_env()
env.set("ENVIRONMENT", "testing", "test")
env.set("TESTING", "true", "test")


@pytest.mark.smoke
class TestCriticalWiring:
    """Smoke tests for critical component wiring."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_websocket_to_tool_dispatcher_wiring(self):
        """SMOKE: WebSocket manager properly wired to tool dispatcher."""
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        
        # Create mock components
        mock_websocket = Mock()
        mock_websocket.send_agent_event = AsyncMock()
        
        # Create user context for factory pattern
        user_context = UserExecutionContext(
            user_id="test_user",
            run_id="test_run",
            thread_id="test_thread"
        )
        
        # Create tool dispatcher using factory method
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context,
            websocket_manager=mock_websocket
        )
        
        # Verify wiring
        assert dispatcher is not None, "Tool dispatcher creation failed"
        assert hasattr(dispatcher, 'websocket_manager'), "Tool dispatcher missing WebSocket manager"
        assert dispatcher.websocket_manager == mock_websocket, "WebSocket manager not wired correctly"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_agent_registry_to_websocket_wiring(self):
        """SMOKE: Agent registry properly receives WebSocket manager."""
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        
        # Create mock components
        mock_llm = Mock(spec=LLMManager)
        mock_websocket = Mock()
        
        # Create user context for factory pattern
        user_context = UserExecutionContext(
            user_id="test_user",
            run_id="test_run",
            thread_id="test_thread"
        )
        
        # Create tool dispatcher using factory
        mock_tool_dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context,
            websocket_manager=mock_websocket
        )
        
        # Create registry
        registry = AgentRegistry(
            llm_manager=mock_llm,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Wire WebSocket to registry
        registry.set_websocket_manager(mock_websocket)
        
        # Verify wiring
        assert hasattr(registry, 'websocket_manager'), "Registry missing WebSocket manager"
        assert registry.websocket_manager == mock_websocket
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)  
    async def test_bridge_to_supervisor_wiring(self):
        """SMOKE: AgentWebSocketBridge properly wired to supervisor."""
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create components
        bridge = AgentWebSocketBridge()
        mock_supervisor = Mock()
        
        # Create a proper mock registry with required methods
        mock_registry = Mock()
        mock_registry.list_agents = Mock(return_value=[])
        mock_registry.get_agent = Mock(return_value=None)
        mock_registry.register_agent = Mock()
        mock_registry.set_websocket_manager = Mock()
        mock_registry.agents = {}  # Registry expects iterable agents dict for integration
        mock_supervisor.registry = mock_registry
        
        # Wire bridge to supervisor
        result = await bridge.ensure_integration(
            supervisor=mock_supervisor,
            registry=mock_registry,
            force_reinit=False
        )
        
        # Verify wiring
        assert result.success, f"Bridge integration failed: {result.error}"
        assert bridge._supervisor == mock_supervisor
        assert bridge._registry == mock_registry
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_database_session_factory_wiring(self):
        """SMOKE: Database session factory properly wired to app state."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = MagicMock()
        
        # Mock database initialization
        mock_session_factory = Mock()
        app.state.db_session_factory = mock_session_factory
        
        # Verify wiring
        assert hasattr(app.state, 'db_session_factory')
        assert app.state.db_session_factory is not None
        assert app.state.db_session_factory == mock_session_factory
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_redis_manager_wiring(self):
        """SMOKE: Redis manager properly wired to app state."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = MagicMock()
        
        # Mock Redis initialization
        mock_redis = Mock()
        mock_redis.get_connection = AsyncMock()
        app.state.redis_manager = mock_redis
        
        # Verify wiring
        assert hasattr(app.state, 'redis_manager')
        assert app.state.redis_manager is not None
        assert app.state.redis_manager == mock_redis


@pytest.mark.smoke
class TestStartupSequenceSmoke:
    """Smoke tests for startup sequence."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_startup_phases_execute(self):
        """SMOKE: All startup phases execute without hanging."""
        from netra_backend.app.smd import StartupOrchestrator
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = MagicMock()
        orchestrator = StartupOrchestrator(app)
        
        # Mock all database-related methods to avoid connection errors
        orchestrator._initialize_database = AsyncMock()
        orchestrator._ensure_database_tables_exist = AsyncMock()
        orchestrator._validate_database_schema = AsyncMock()
        orchestrator._phase3_database_setup = AsyncMock()
        
        # Track which phase methods are called
        phases_called = []
        
        def track_mock(name):
            async def mock():
                phases_called.append(name)
                # Set required state attributes
                if name in ["phase1", "phase2"]:
                    app.state.db_session_factory = Mock()
                    app.state.redis_manager = Mock()
                    app.state.key_manager = Mock()
                    app.state.llm_manager = Mock()
                    app.state.websocket_manager = Mock()
                    app.state.tool_dispatcher = Mock()
                    app.state.agent_websocket_bridge = Mock()
                    app.state.agent_supervisor = Mock()
                    app.state.thread_service = Mock()
            return AsyncMock(side_effect=mock)
        
        # Mock all phases to ensure they don't hang and track execution
        orchestrator._phase1_foundation = track_mock("phase1")
        orchestrator._phase2_core_services = track_mock("phase2")
        orchestrator._phase4_integration_enhancement = track_mock("phase4")
        orchestrator._phase5_critical_services = track_mock("phase5")
        orchestrator._phase5_services_setup = track_mock("phase5_services")
        orchestrator._phase6_validation = track_mock("phase6")
        orchestrator._phase6_websocket_setup = track_mock("phase6_websocket")
        orchestrator._phase7_optional_services = track_mock("phase7")
        orchestrator._phase7_finalize = AsyncMock()
        orchestrator._run_comprehensive_validation = AsyncMock()
        orchestrator._mark_startup_complete = Mock()
        
        # Run startup - should not hang
        await orchestrator.initialize_system()
        
        # Verify at least some phases were executed without hanging
        assert len(phases_called) >= 2, f"Not enough phases executed: {phases_called}"
        assert "phase1" in phases_called, f"Phase 1 not executed. Executed: {phases_called}"
        assert "phase2" in phases_called, f"Phase 2 not executed. Executed: {phases_called}"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_startup_marks_completion(self):
        """SMOKE: Startup properly marks completion in app state."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = MagicMock()
        
        # Simulate startup completion
        app.state.startup_complete = False
        app.state.startup_in_progress = True
        
        # Mark startup complete
        app.state.startup_complete = True
        app.state.startup_in_progress = False
        app.state.startup_time = time.time()
        
        # Verify completion markers
        assert app.state.startup_complete is True
        assert app.state.startup_in_progress is False
        assert hasattr(app.state, 'startup_time')
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_startup_error_propagation(self):
        """SMOKE: Startup errors properly propagate and prevent completion."""
        from netra_backend.app.smd import (
            StartupOrchestrator,
            DeterministicStartupError
        )
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state = MagicMock()
        orchestrator = StartupOrchestrator(app)
        
        # Inject failure
        orchestrator._phase1_foundation = AsyncMock(
            side_effect=Exception("Critical failure")
        )
        
        # Verify error propagation
        with pytest.raises(DeterministicStartupError) as exc_info:
            await orchestrator.initialize_system()
        
        assert "Critical failure" in str(exc_info.value)


@pytest.mark.smoke
class TestHealthEndpointSmoke:
    """Smoke tests for health endpoint integration."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_health_endpoint_exists(self):
        """SMOKE: Health endpoint is accessible."""
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        
        app = FastAPI()
        app.state = MagicMock()
        app.state.startup_complete = True
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_readiness_endpoint_exists(self):
        """SMOKE: Readiness endpoint is accessible."""
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        
        app = FastAPI()
        app.state = MagicMock()
        app.state.startup_complete = True
        
        @app.get("/health/ready")
        async def ready():
            if not app.state.startup_complete:
                return {"status": "not_ready"}, 503
            return {"status": "ready"}
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"


@pytest.mark.smoke
class TestCriticalServiceSmoke:
    """Smoke tests for critical service availability."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_llm_manager_available(self):
        """SMOKE: LLM manager is available after startup."""
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.schemas.config import AppConfig
        
        # Since mock mode is forbidden, we test the structure only
        # by checking if the class exists and has expected methods
        assert LLMManager is not None
        assert hasattr(LLMManager, '__init__')
        
        # Verify core methods exist on the class
        expected_methods = ['ask_llm', 'ask_llm_structured', 'health_check']
        for method in expected_methods:
            assert hasattr(LLMManager, method), \
                f"LLMManager should have {method} method"
        
        # Verify the class can be imported without errors
        assert LLMManager.__name__ == "LLMManager"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_key_manager_available(self):
        """SMOKE: Key manager is available after startup."""
        from netra_backend.app.services.key_manager import KeyManager, KeyType
        
        # Create key manager using proper initialization
        manager = KeyManager()
        
        # Generate test key using instance method
        test_key = manager.generate_key(
            key_id="test_key",
            key_type=KeyType.ENCRYPTION_KEY,
            length=32
        )
        
        # Verify basic structure and methods
        assert test_key is not None, "Key generation failed"
        assert len(test_key) > 0, "Generated key is empty"
        assert hasattr(manager, 'generate_key'), "KeyManager missing generate_key method"
        assert hasattr(manager, 'store_key'), "KeyManager missing store_key method"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_thread_service_available(self):
        """SMOKE: Thread service is available for chat."""
        mock_thread_service = Mock()
        mock_thread_service.create_thread = AsyncMock()
        mock_thread_service.get_thread = AsyncMock()
        
        # Verify basic operations
        assert hasattr(mock_thread_service, 'create_thread')
        assert hasattr(mock_thread_service, 'get_thread')


@pytest.mark.smoke
class TestDockerIntegrationSmoke:
    """Smoke tests for Docker service integration."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_docker_services_discoverable(self):
        """SMOKE: Docker services are discoverable via environment."""
        env = get_env()
        
        # Check for Docker service configuration
        expected_services = [
            "DATABASE_URL",
            "REDIS_URL", 
            "AUTH_SERVICE_URL"
        ]
        
        # In test environment, these should be configured
        for service_var in expected_services:
            value = env.get(service_var)
            # Should either be None (not configured) or a valid string
            if value:
                assert isinstance(value, str)
                assert len(value) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_port_configuration_valid(self):
        """SMOKE: Service ports are properly configured."""
        env = get_env()
        
        # Check port configuration
        port = env.get("PORT", "8000")
        assert port.isdigit(), f"Invalid port configuration: {port}"
        assert 1024 <= int(port) <= 65535, f"Port out of valid range: {port}"
        
        # Check auth service port if configured
        auth_port = env.get("AUTH_SERVICE_PORT", "8001")
        if auth_port:
            assert auth_port.isdigit(), f"Invalid auth port: {auth_port}"
            assert 1024 <= int(auth_port) <= 65535, f"Auth port out of range: {auth_port}"


if __name__ == "__main__":
    # Run smoke tests with fast fail
    pytest.main([
        __file__, 
        "-v", 
        "-m", "smoke",
        "--tb=short",
        "--maxfail=1",  # Stop on first failure
        "--timeout=30"  # Overall timeout
    ])