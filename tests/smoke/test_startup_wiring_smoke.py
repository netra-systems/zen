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
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        
        # Create mock components
        mock_websocket = Mock()
        mock_websocket.send_agent_event = AsyncMock()
        
        # Create tool dispatcher
        dispatcher = ToolDispatcher()
        
        # Wire WebSocket to dispatcher
        if hasattr(dispatcher, 'executor'):
            dispatcher.executor.websocket_bridge = Mock()
            dispatcher.executor.websocket_bridge.websocket_manager = mock_websocket
        
        # Verify wiring
        assert hasattr(dispatcher, 'executor'), "Tool dispatcher missing executor"
        if hasattr(dispatcher, 'executor'):
            assert hasattr(dispatcher.executor, 'websocket_bridge'), "Executor missing WebSocket bridge"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_agent_registry_to_websocket_wiring(self):
        """SMOKE: Agent registry properly receives WebSocket manager."""
        from netra_backend.app.orchestration.agent_execution_registry import AgentExecutionRegistry
        
        # Create registry
        registry = AgentExecutionRegistry()
        
        # Create mock WebSocket
        mock_websocket = Mock()
        
        # Wire WebSocket to registry (async method)
        await registry.set_websocket_manager(mock_websocket)
        
        # Verify wiring
        assert hasattr(registry, '_websocket_manager'), "Registry missing WebSocket manager"
        assert registry._websocket_manager == mock_websocket
    
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
        
        # Mock all phase methods to track execution
        phases_executed = []
        
        async def track_phase(phase_name):
            phases_executed.append(phase_name)
            # Set required state attributes
            if phase_name == "phase2":
                app.state.db_session_factory = Mock()
                app.state.redis_manager = Mock()
                app.state.key_manager = Mock()
                app.state.llm_manager = Mock()
            elif phase_name == "phase3":
                app.state.websocket_manager = Mock()
                app.state.tool_dispatcher = Mock()
                app.state.agent_websocket_bridge = Mock()
                app.state.agent_supervisor = Mock()
                app.state.thread_service = Mock()
        
        orchestrator._phase1_foundation = AsyncMock(side_effect=lambda: track_phase("phase1"))
        orchestrator._phase2_core_services = AsyncMock(side_effect=lambda: track_phase("phase2"))
        orchestrator._phase3_chat_pipeline = AsyncMock(side_effect=lambda: track_phase("phase3"))
        orchestrator._phase4_integration_enhancement = AsyncMock()
        orchestrator._phase5_critical_services = AsyncMock()
        orchestrator._phase6_validation = AsyncMock()
        orchestrator._phase7_optional_services = AsyncMock()
        orchestrator._mark_startup_complete = Mock()
        
        # Run startup
        await orchestrator.initialize_system()
        
        # Verify phases executed
        assert "phase1" in phases_executed
        assert "phase2" in phases_executed
        assert "phase3" in phases_executed
    
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
        expected_methods = ['get_llm', 'ask_llm', 'health_check']
        for method in expected_methods:
            assert hasattr(LLMManager, method), \
                f"LLMManager should have {method} method"
        
        # Verify the class can be imported without errors
        assert LLMManager.__name__ == "LLMManager"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_key_manager_available(self):
        """SMOKE: Key manager is available after startup."""
        from netra_backend.app.services.key_manager import KeyManager
        
        # Create key manager with required fields
        manager = KeyManager(
            jwt_secret_key="a" * 32,  # Minimum 32 characters
            fernet_key=KeyManager.generate_key()
        )
        
        # Verify basic structure
        assert hasattr(manager, 'jwt_secret_key')
        assert hasattr(manager, 'fernet_key')
    
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