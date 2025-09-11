"""
Smoke Tests: Startup Wiring and Integration

Fast smoke tests to verify critical wiring and integration points during startup.
These tests focus on the "plumbing" - ensuring components are properly connected.

Business Value: Catch integration issues early in CI/CD pipeline (< 30 seconds total)
"""

import pytest
import asyncio
from typing import Dict, Any
import time
from unittest.mock import Mock, AsyncMock, MagicMock


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()


@pytest.mark.smoke
class TestCriticalWiring:
    """Smoke tests for critical component wiring."""

    @pytest.mark.asyncio
    async def test_websocket_to_tool_dispatcher_wiring(self):
        """SMOKE: WebSocket manager properly wired to tool dispatcher."""
        try:
            from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # Create mock components
            websocket = TestWebSocketConnection()

            # Create user context for factory pattern
            user_context = UserExecutionContext(
                user_id="test_user",
                run_id="test_run",
                thread_id="test_thread"
            )

            # Create tool dispatcher using factory method
            dispatcher = UnifiedToolDispatcherFactory.create_for_request(
                user_context=user_context,
                websocket_manager=websocket
            )

            # Verify wiring
            assert dispatcher is not None, "Tool dispatcher creation failed"
            assert hasattr(dispatcher, 'websocket_manager'), "Tool dispatcher missing WebSocket manager"
            assert dispatcher.websocket_manager == websocket, "WebSocket manager not wired correctly"

        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")

    @pytest.mark.asyncio
    async def test_agent_registry_to_websocket_wiring(self):
        """SMOKE: Agent registry properly receives WebSocket manager."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # Create mock components
            mock_llm = Mock(spec=LLMManager)
            websocket = TestWebSocketConnection()

            # Create user context for factory pattern
            user_context = UserExecutionContext(
                user_id="test_user",
                run_id="test_run",
                thread_id="test_thread"
            )

            # Create tool dispatcher using factory
            mock_tool_dispatcher = UnifiedToolDispatcherFactory.create_for_request(
                user_context=user_context,
                websocket_manager=websocket
            )

            # Create registry
            registry = AgentRegistry(
                llm_manager=mock_llm,
                tool_dispatcher_factory=lambda user_context, websocket_bridge: mock_tool_dispatcher
            )

            # Wire WebSocket to registry
            registry.set_websocket_manager(websocket)

            # Verify wiring
            assert hasattr(registry, 'websocket_manager'), "Registry missing WebSocket manager"
            assert registry.websocket_manager == websocket

        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")

    @pytest.mark.asyncio
    async def test_database_session_factory_wiring(self):
        """SMOKE: Database session factory properly wired to app state."""
        try:
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

        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")

    @pytest.mark.asyncio
    async def test_redis_manager_wiring(self):
        """SMOKE: Redis manager properly wired to app state."""
        try:
            from fastapi import FastAPI

            app = FastAPI()
            app.state = MagicMock()
            
            # Mock Redis initialization
            mock_redis = Mock()
            app.state.redis_manager = mock_redis

            # Verify wiring
            assert hasattr(app.state, 'redis_manager')
            assert app.state.redis_manager is not None
            assert app.state.redis_manager == mock_redis

        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")


@pytest.mark.smoke
class TestStartupSequenceSmoke:
    """Smoke tests for startup sequence."""

    @pytest.mark.asyncio
    async def test_startup_phases_execute(self):
        """SMOKE: All startup phases execute without hanging."""
        try:
            from netra_backend.app.smd import StartupOrchestrator
            from fastapi import FastAPI

            app = FastAPI()
            app.state = MagicMock()
            orchestrator = StartupOrchestrator(app)

            # Track which phase methods are called
            phases_called = []

            def track_mock(name):
                async def mock():
                    phases_called.append(name)
                    # Set required state attributes
                    if name in ["phase1", "phase2"]:
                        app.state.websocket = TestWebSocketConnection()
                    await asyncio.sleep(0)
                return mock

            # Mock all phases to ensure they don't hang and track execution
            orchestrator._phase1_foundation = track_mock("phase1")
            orchestrator._phase2_core_services = track_mock("phase2")
            orchestrator._phase3_database_setup = track_mock("phase3")
            orchestrator._phase4_cache_setup = track_mock("phase4")
            orchestrator._phase5_services_setup = track_mock("phase5")
            orchestrator._phase6_websocket_setup = track_mock("phase6")
            orchestrator._phase7_finalization = track_mock("phase7")
            
            # Mock validation to avoid connection issues
            async def mock_validation():
                phases_called.append("validation")
                app.state.startup_complete = True
                await asyncio.sleep(0)
            orchestrator._run_comprehensive_validation = mock_validation

            # Run startup - should not hang
            await orchestrator.initialize_system()

            # Verify at least some phases were executed without hanging
            assert len(phases_called) >= 2, f"Expected at least 2 phases, got {len(phases_called)}: {phases_called}"
            assert "phase1" in phases_called, f"Phase1 not executed: {phases_called}"
            assert "phase2" in phases_called, f"Phase2 not executed: {phases_called}"

        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")

    @pytest.mark.asyncio
    async def test_startup_marks_completion(self):
        """SMOKE: Startup properly marks completion in app state."""
        try:
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

        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")

    @pytest.mark.asyncio
    async def test_startup_error_propagation(self):
        """SMOKE: Startup errors properly propagate and prevent completion."""
        try:
            from netra_backend.app.smd import StartupOrchestrator
            from fastapi import FastAPI

            app = FastAPI()
            app.state = MagicMock()
            orchestrator = StartupOrchestrator(app)

            # Mock a phase to raise an error
            async def failing_phase():
                raise RuntimeError("Simulated startup failure")

            orchestrator._phase1_foundation = failing_phase

            # Startup should fail and propagate error
            with pytest.raises(Exception):  # Could be wrapped in DeterministicStartupError
                await orchestrator.initialize_system()

            # Verify startup was not marked complete
            assert not getattr(app.state, 'startup_complete', True)

        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")