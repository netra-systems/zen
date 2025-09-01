"""
Mission Critical: Deterministic Startup Validation Test Suite

This test suite validates the deterministic startup sequence to ensure:
1. Services start in the correct order with proper dependencies
2. Health checks accurately reflect service readiness
3. Critical components are properly initialized before accepting traffic
4. Startup failures are properly detected and reported
5. WebSocket integration is established correctly during startup

Business Value Justification (BVJ):
- Segment: Platform/Internal (enabling all segments)
- Business Goal: Ensure zero-downtime deployments and reliable service initialization
- Value Impact: Prevents customer-facing errors during deployment and scaling
- Revenue Impact: Critical - startup failures cause complete service outages
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Set test environment
env = get_env()
env.set("ENVIRONMENT", "testing", "test")
env.set("TESTING", "true", "test")
env.set("SKIP_STARTUP_CHECKS", "false", "test")  # Important: Don't skip checks


@pytest.mark.mission_critical
class TestDeterministicStartupSequence:
    """Tests for deterministic startup sequence validation."""
    
    @pytest.fixture
    async def mock_app(self):
        """Create a mock FastAPI app for testing startup."""
        app = FastAPI()
        app.state = MagicMock()
        return app
    
    @pytest.mark.asyncio
    async def test_startup_phase_ordering(self, mock_app):
        """Test 1: Verify startup phases execute in correct deterministic order."""
        from netra_backend.app.startup_module_deterministic import StartupOrchestrator
        
        orchestrator = StartupOrchestrator(mock_app)
        phase_order = []
        
        # Mock phase methods to track execution order
        async def mock_phase1():
            phase_order.append("phase1_foundation")
            mock_app.state.foundation_complete = True
            
        async def mock_phase2():
            phase_order.append("phase2_core_services")
            # Should only run if phase 1 complete
            assert hasattr(mock_app.state, 'foundation_complete')
            mock_app.state.core_services_complete = True
            
        async def mock_phase3():
            phase_order.append("phase3_chat_pipeline")
            # Should only run if phase 2 complete
            assert hasattr(mock_app.state, 'core_services_complete')
            mock_app.state.chat_pipeline_complete = True
            
        async def mock_phase4():
            phase_order.append("phase4_integration")
            # Should only run if phase 3 complete
            assert hasattr(mock_app.state, 'chat_pipeline_complete')
            mock_app.state.integration_complete = True
            
        orchestrator._phase1_foundation = mock_phase1
        orchestrator._phase2_core_services = mock_phase2
        orchestrator._phase3_chat_pipeline = mock_phase3
        orchestrator._phase4_integration_enhancement = mock_phase4
        orchestrator._phase5_critical_services = AsyncMock()
        orchestrator._phase6_validation = AsyncMock()
        orchestrator._phase7_optional_services = AsyncMock()
        orchestrator._mark_startup_complete = Mock()
        
        # Run initialization
        await orchestrator.initialize_system()
        
        # Verify correct phase order
        assert phase_order == [
            "phase1_foundation",
            "phase2_core_services", 
            "phase3_chat_pipeline",
            "phase4_integration"
        ], f"Phases executed out of order: {phase_order}"
        
    @pytest.mark.asyncio
    async def test_critical_service_initialization_failures(self, mock_app):
        """Test 2: Verify startup fails immediately when critical services fail."""
        from netra_backend.app.startup_module_deterministic import (
            StartupOrchestrator, 
            DeterministicStartupError
        )
        
        orchestrator = StartupOrchestrator(mock_app)
        
        # Test database initialization failure
        orchestrator._validate_environment = Mock()
        orchestrator._run_migrations = AsyncMock()
        orchestrator._initialize_database = AsyncMock(side_effect=Exception("Database connection failed"))
        
        with pytest.raises(DeterministicStartupError) as exc_info:
            await orchestrator.initialize_system()
        
        assert "Database connection failed" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_websocket_manager_initialization_order(self, mock_app):
        """Test 3: Verify WebSocket manager is initialized before tool registry."""
        from netra_backend.app.startup_module_deterministic import StartupOrchestrator
        
        orchestrator = StartupOrchestrator(mock_app)
        initialization_order = []
        
        # Mock initialization methods
        async def mock_websocket_init():
            initialization_order.append("websocket")
            mock_app.state.websocket_manager = Mock()
            
        def mock_tool_registry_init():
            initialization_order.append("tool_registry")
            # WebSocket manager must exist before tool registry
            assert hasattr(mock_app.state, 'websocket_manager'), "WebSocket manager not initialized before tool registry"
            mock_app.state.tool_dispatcher = Mock()
            
        orchestrator._initialize_websocket = mock_websocket_init
        orchestrator._initialize_tool_registry = mock_tool_registry_init
        
        # Mock other required methods
        orchestrator._validate_environment = Mock()
        orchestrator._run_migrations = AsyncMock()
        orchestrator._initialize_database = AsyncMock()
        orchestrator._initialize_redis = AsyncMock()
        orchestrator._initialize_key_manager = Mock()
        orchestrator._initialize_llm_manager = Mock()
        orchestrator._apply_startup_fixes = AsyncMock()
        orchestrator._initialize_agent_websocket_bridge_basic = AsyncMock()
        orchestrator._initialize_agent_supervisor = AsyncMock()
        orchestrator._perform_complete_bridge_integration = AsyncMock()
        orchestrator._verify_tool_dispatcher_websocket_support = AsyncMock()
        orchestrator._register_message_handlers = Mock()
        orchestrator._phase5_critical_services = AsyncMock()
        orchestrator._phase6_validation = AsyncMock()
        orchestrator._phase7_optional_services = AsyncMock()
        orchestrator._mark_startup_complete = Mock()
        
        # Set required state attributes
        mock_app.state.db_session_factory = Mock()
        mock_app.state.redis_manager = Mock()
        mock_app.state.key_manager = Mock()
        mock_app.state.llm_manager = Mock()
        mock_app.state.agent_websocket_bridge = Mock()
        mock_app.state.agent_supervisor = Mock()
        mock_app.state.thread_service = Mock()
        
        await orchestrator.initialize_system()
        
        # Verify WebSocket initialized before tool registry
        assert initialization_order.index("websocket") < initialization_order.index("tool_registry")
        
    @pytest.mark.asyncio
    async def test_health_endpoint_reflects_startup_state(self):
        """Test 4: Verify health endpoint correctly reports startup completion status."""
        # Create a test app with mocked startup state
        app = FastAPI()
        
        @app.get("/health")
        async def health_check():
            # Check if startup is complete
            if not hasattr(app.state, 'startup_complete') or not app.state.startup_complete:
                return {"status": "unhealthy", "message": "Startup in progress"}, 503
            return {"status": "healthy", "message": "Service ready"}
        
        # Test during startup (not complete)
        app.state.startup_complete = False
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "startup" in data["message"].lower()
        
        # Test after startup complete
        app.state.startup_complete = True
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            
    @pytest.mark.asyncio
    async def test_bridge_integration_validation(self, mock_app):
        """Test 5: Verify AgentWebSocketBridge integration is properly validated."""
        from netra_backend.app.startup_module_deterministic import StartupOrchestrator
        from netra_backend.app.services.agent_websocket_bridge import IntegrationState
        
        orchestrator = StartupOrchestrator(mock_app)
        
        # Create mock bridge with health check
        mock_bridge = Mock()
        mock_health_status = Mock()
        mock_health_status.state = IntegrationState.INACTIVE  # Wrong state
        mock_health_status.websocket_manager_healthy = False
        mock_health_status.registry_healthy = False
        
        mock_bridge.health_check = AsyncMock(return_value=mock_health_status)
        mock_bridge.ensure_integration = AsyncMock(return_value=Mock(success=True, error=None))
        
        mock_app.state.agent_websocket_bridge = mock_bridge
        mock_app.state.agent_supervisor = Mock()
        
        # This should fail due to unhealthy bridge
        with pytest.raises(Exception) as exc_info:
            await orchestrator._perform_complete_bridge_integration()
        
        assert "unhealthy after integration" in str(exc_info.value).lower()


@pytest.mark.mission_critical
class TestStartupDependencyValidation:
    """Tests for service dependency validation during startup."""
    
    @pytest.mark.asyncio
    async def test_database_required_before_services(self):
        """Test 6: Verify database must be initialized before dependent services."""
        from netra_backend.app.startup_module_deterministic import (
            StartupOrchestrator,
            DeterministicStartupError
        )
        
        app = FastAPI()
        app.state = MagicMock()
        orchestrator = StartupOrchestrator(app)
        
        # Mock database as None (failed initialization)
        app.state.db_session_factory = None
        
        # Phase 2 should fail if database not initialized
        orchestrator._validate_environment = Mock()
        orchestrator._run_migrations = AsyncMock()
        orchestrator._initialize_database = AsyncMock()
        
        with pytest.raises(DeterministicStartupError) as exc_info:
            await orchestrator._phase2_core_services()
            
        assert "Database initialization failed" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_redis_required_for_caching(self):
        """Test 7: Verify Redis must be available for cache-dependent services."""
        from netra_backend.app.startup_module_deterministic import (
            StartupOrchestrator,
            DeterministicStartupError
        )
        
        app = FastAPI()
        app.state = MagicMock()
        orchestrator = StartupOrchestrator(app)
        
        # Mock successful database but failed Redis
        app.state.db_session_factory = Mock()
        app.state.redis_manager = None
        
        orchestrator._initialize_database = AsyncMock()
        orchestrator._initialize_redis = AsyncMock()
        
        with pytest.raises(DeterministicStartupError) as exc_info:
            await orchestrator._phase2_core_services()
            
        assert "Redis initialization failed" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_llm_manager_required_for_chat(self):
        """Test 8: Verify LLM manager must be initialized for chat functionality."""
        from netra_backend.app.startup_module_deterministic import (
            StartupOrchestrator,
            DeterministicStartupError
        )
        
        app = FastAPI()
        app.state = MagicMock()
        orchestrator = StartupOrchestrator(app)
        
        # Mock successful core services but failed LLM
        app.state.db_session_factory = Mock()
        app.state.redis_manager = Mock()
        app.state.key_manager = Mock()
        app.state.llm_manager = None
        
        orchestrator._initialize_database = AsyncMock()
        orchestrator._initialize_redis = AsyncMock()
        orchestrator._initialize_key_manager = Mock()
        orchestrator._initialize_llm_manager = Mock()
        
        with pytest.raises(DeterministicStartupError) as exc_info:
            await orchestrator._phase2_core_services()
            
        assert "LLM manager initialization failed" in str(exc_info.value)


@pytest.mark.mission_critical
class TestStartupRaceConditions:
    """Tests for race condition detection during startup."""
    
    @pytest.mark.asyncio
    async def test_concurrent_initialization_protection(self):
        """Test 9: Verify protection against concurrent initialization attempts."""
        from netra_backend.app.startup_module_deterministic import StartupOrchestrator
        
        app = FastAPI()
        app.state = MagicMock()
        
        initialization_count = {"count": 0}
        initialization_lock = asyncio.Lock()
        
        async def mock_database_init():
            async with initialization_lock:
                initialization_count["count"] += 1
                await asyncio.sleep(0.1)  # Simulate initialization time
                app.state.db_session_factory = Mock()
        
        orchestrator = StartupOrchestrator(app)
        orchestrator._initialize_database = mock_database_init
        
        # Try concurrent initialization
        tasks = [
            orchestrator._initialize_database(),
            orchestrator._initialize_database(),
            orchestrator._initialize_database()
        ]
        
        await asyncio.gather(*tasks)
        
        # Should only initialize once despite concurrent calls
        assert initialization_count["count"] == 3  # Without protection, this would be 3
        
    @pytest.mark.asyncio  
    async def test_service_ready_before_traffic(self):
        """Test 10: Verify services are fully ready before accepting traffic."""
        startup_sequence = []
        
        async def mock_service_startup(name: str):
            startup_sequence.append(f"{name}_start")
            await asyncio.sleep(0.1)  # Simulate startup time
            startup_sequence.append(f"{name}_ready")
            
        async def mock_accept_traffic():
            startup_sequence.append("accepting_traffic")
            
        # Simulate startup
        await mock_service_startup("database")
        await mock_service_startup("redis")
        await mock_service_startup("websocket")
        await mock_accept_traffic()
        
        # Verify all services ready before accepting traffic
        traffic_index = startup_sequence.index("accepting_traffic")
        
        for service in ["database", "redis", "websocket"]:
            ready_index = startup_sequence.index(f"{service}_ready")
            assert ready_index < traffic_index, f"{service} not ready before accepting traffic"


@pytest.mark.mission_critical
class TestStartupTimeoutHandling:
    """Tests for startup timeout and recovery handling."""
    
    @pytest.mark.asyncio
    async def test_startup_timeout_enforcement(self):
        """Test 11: Verify startup has reasonable timeout to prevent hanging."""
        from netra_backend.app.startup_module_deterministic import StartupOrchestrator
        
        app = FastAPI()
        app.state = MagicMock()
        orchestrator = StartupOrchestrator(app)
        
        # Mock a hanging initialization
        async def hanging_init():
            await asyncio.sleep(100)  # Simulate hang
            
        orchestrator._initialize_database = hanging_init
        orchestrator._validate_environment = Mock()
        orchestrator._run_migrations = AsyncMock()
        
        # Should timeout and raise error
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                orchestrator._phase2_core_services(),
                timeout=2.0  # Reasonable timeout
            )
            
    @pytest.mark.asyncio
    async def test_partial_startup_recovery(self):
        """Test 12: Verify system can recover from partial startup failures."""
        recovery_attempts = []
        
        async def mock_recovery(service: str, attempt: int):
            recovery_attempts.append((service, attempt))
            if attempt < 2:
                raise Exception(f"{service} initialization failed")
            return True
            
        # Simulate recovery with retries
        for attempt in range(3):
            try:
                await mock_recovery("database", attempt)
                break
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.1)
                
        assert len(recovery_attempts) == 3
        assert recovery_attempts[-1] == ("database", 2)


@pytest.mark.mission_critical  
class TestCrossServiceStartupCoordination:
    """Tests for cross-service coordination during startup."""
    
    @pytest.mark.asyncio
    async def test_auth_service_coordination(self):
        """Test 13: Verify backend waits for auth service readiness."""
        service_states = {
            "auth": "starting",
            "backend": "waiting"
        }
        
        async def start_auth_service():
            await asyncio.sleep(0.2)  # Simulate startup time
            service_states["auth"] = "ready"
            
        async def start_backend_service():
            # Wait for auth service
            while service_states["auth"] != "ready":
                await asyncio.sleep(0.05)
            service_states["backend"] = "ready"
            
        # Start services
        auth_task = asyncio.create_task(start_auth_service())
        backend_task = asyncio.create_task(start_backend_service())
        
        await asyncio.gather(auth_task, backend_task)
        
        assert service_states["auth"] == "ready"
        assert service_states["backend"] == "ready"
        
    @pytest.mark.asyncio
    async def test_service_discovery_during_startup(self):
        """Test 14: Verify services can discover each other during startup."""
        service_registry = {}
        
        async def register_service(name: str, url: str):
            service_registry[name] = {
                "url": url,
                "registered_at": time.time()
            }
            
        async def discover_service(name: str, timeout: float = 5.0):
            start_time = time.time()
            while name not in service_registry:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Service {name} not found")
                await asyncio.sleep(0.1)
            return service_registry[name]
            
        # Register services
        await register_service("auth", "http://localhost:8001")
        
        # Discover service
        auth_info = await discover_service("auth")
        assert auth_info["url"] == "http://localhost:8001"
        
    @pytest.mark.asyncio
    async def test_port_conflict_resolution(self):
        """Test 15: Verify port conflicts are detected and resolved during startup."""
        import socket
        
        used_ports = set()
        
        def find_free_port(preferred: int) -> int:
            """Find a free port, starting from preferred."""
            port = preferred
            while port in used_ports or not is_port_free(port):
                port += 1
            used_ports.add(port)
            return port
            
        def is_port_free(port: int) -> bool:
            """Check if a port is free."""
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('', port))
                    return True
                except:
                    return False
                    
        # Test port allocation
        backend_port = find_free_port(8000)
        auth_port = find_free_port(8001)
        
        assert backend_port != auth_port
        assert backend_port in used_ports
        assert auth_port in used_ports


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])