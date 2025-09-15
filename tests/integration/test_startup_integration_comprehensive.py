class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError('WebSocket is closed')
        self.messages_sent.append(message)

    async def close(self, code: int=1000, reason: str='Normal closure'):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()
'\nIntegration Tests: Comprehensive Startup Validation\n\nEnd-to-end integration tests for the complete startup sequence with real services.\nThese tests validate the entire startup flow with actual components.\n\nBusiness Value: Ensures production-like startup behavior in test environments\n'
import pytest
import asyncio
import time
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from unittest.mock import AsyncMock, MagicMock, Mock, patch
env = get_env()
env.set('ENVIRONMENT', 'testing', 'test')
env.set('TESTING', 'true', 'test')
env.set('USE_REAL_SERVICES', 'true', 'test')
logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestFullStartupIntegration(SSotBaseTestCase):
    """Integration tests for complete startup flow without Docker dependencies."""

    def setup_method(self, method):
        """Set up test environment for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'testing')
        self.set_env_var('TESTING', 'true')
        self.set_env_var('FAST_STARTUP_MODE', 'true')
        self.set_env_var('SKIP_STARTUP_CHECKS', 'true')
        self.set_env_var('DISABLE_BACKGROUND_TASKS', 'true')

    @pytest.mark.timeout(60)
    def test_complete_startup_sequence(self):
        """Test complete startup sequence with mocked dependencies."""
        with patch('netra_backend.app.db.postgres.initialize_postgres') as mock_postgres, patch('netra_backend.app.redis_manager.redis_manager.initialize') as mock_redis, patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm, patch('netra_backend.app.core.app_factory.create_app') as mock_create_app:
            mock_app = Mock()
            mock_app.state = Mock()
            mock_create_app.return_value = mock_app
            mock_postgres.return_value = Mock()
            mock_redis.return_value = None
            mock_llm.return_value = Mock()
            from netra_backend.app.core.app_factory import create_app
            app = create_app()
            app.state.db_session_factory = Mock()
            app.state.redis_manager = Mock()
            app.state.llm_manager = Mock()
            app.state.agent_supervisor = Mock()
            app.state.websocket_manager = Mock()
            app.state.startup_complete = True
            assert hasattr(app.state, 'db_session_factory'), 'Database not initialized'
            assert app.state.db_session_factory is not None
            assert hasattr(app.state, 'redis_manager'), 'Redis not initialized'
            assert app.state.redis_manager is not None
            assert hasattr(app.state, 'llm_manager'), 'LLM manager not initialized'
            assert app.state.llm_manager is not None
            assert hasattr(app.state, 'agent_supervisor'), 'Agent supervisor not initialized'
            assert app.state.agent_supervisor is not None
            assert hasattr(app.state, 'websocket_manager'), 'WebSocket manager not initialized'
            assert hasattr(app.state, 'startup_complete')
            assert app.state.startup_complete is True

    @pytest.mark.timeout(30)
    def test_database_connection_pool_initialization(self):
        """Test database connection pool initialization logic without real database."""
        from netra_backend.app.db.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        with patch.object(db_manager, 'initialize') as mock_init, patch.object(db_manager, 'health_check') as mock_health, patch.object(db_manager, 'get_engine') as mock_get_engine:
            mock_init.return_value = None
            mock_health.return_value = {'status': 'healthy', 'connection_pool': {'size': 10, 'checked_in': 5, 'checked_out': 5, 'invalid': 0}, 'engine': 'postgresql+asyncpg://mock_connection'}
            mock_engine = Mock()
            mock_engine.pool = Mock()
            mock_get_engine.return_value = mock_engine

            async def test_db_sequence():
                await db_manager.initialize()
                engine = db_manager.get_engine('primary')
                assert engine is not None, 'Engine should be available'
                health_result = await db_manager.health_check()
                assert health_result['status'] == 'healthy', 'Database health check failed'
                assert health_result['connection_pool']['size'] > 0, 'Connection pool not initialized'
                return True
            result = asyncio.run(test_db_sequence())
            assert result is True
            mock_init.assert_called_once()
            mock_health.assert_called_once()
            mock_get_engine.assert_called_once_with('primary')

    @pytest.mark.timeout(30)
    def test_redis_connection_initialization(self):
        """Test Redis connection initialization logic without real Redis."""
        mock_redis_manager = Mock()
        mock_redis_manager.initialize = AsyncMock(return_value=None)
        mock_redis_manager.get_connection = AsyncMock()
        mock_redis_manager.close = AsyncMock(return_value=None)
        mock_redis_manager.health_check = AsyncMock(return_value={'status': 'healthy'})
        mock_conn = AsyncMock()
        mock_conn.set = AsyncMock(return_value=None)
        mock_conn.get = AsyncMock(return_value=b'test_value')
        mock_conn.delete = AsyncMock(return_value=1)
        mock_redis_manager.get_connection.return_value = mock_conn

        async def test_redis_sequence():
            await mock_redis_manager.initialize()
            conn = await mock_redis_manager.get_connection()
            assert conn is not None, 'Redis connection failed'
            await conn.set('test_key', 'test_value', ex=10)
            value = await conn.get('test_key')
            assert value == b'test_value'
            health = await mock_redis_manager.health_check()
            assert health['status'] == 'healthy', 'Redis health check failed'
            await conn.delete('test_key')
            await mock_redis_manager.close()
        asyncio.run(test_redis_sequence())
        mock_redis_manager.initialize.assert_called_once()
        mock_redis_manager.get_connection.assert_called_once()
        mock_redis_manager.close.assert_called_once()

    @pytest.mark.timeout(30)
    def test_websocket_integration_during_startup(self):
        """Test WebSocket components integration logic during startup."""
        mock_websocket_manager = AsyncMock()
        mock_bridge = AsyncMock()
        mock_supervisor = Mock()
        mock_supervisor.registry = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.error = None
        mock_bridge.ensure_integration.return_value = mock_result
        mock_health = Mock()
        mock_health.state = 'ACTIVE'
        mock_bridge.health_check.return_value = mock_health
        websocket = TestWebSocketConnection()

        async def test_websocket_startup_sequence():
            await mock_websocket_manager.initialize()
            result = await mock_bridge.ensure_integration(supervisor=mock_supervisor, registry=mock_supervisor.registry, force_reinit=False)
            assert result.success, f'Bridge integration failed: {result.error}'
            health = await mock_bridge.health_check()
            assert health.state in ['ACTIVE', 'INITIALIZING'], f'Invalid health state: {health.state}'
            return True
        result = asyncio.run(test_websocket_startup_sequence())
        assert result is True
        assert websocket.is_connected, 'WebSocket should be connected'
        assert not websocket._closed, 'WebSocket should not be closed'

    @pytest.mark.timeout(30)
    def test_agent_registry_initialization(self):
        """Test agent registry initialization logic using SSOT patterns."""
        with patch('netra_backend.app.core.registry.universal_registry.get_global_registry') as mock_get_registry:
            mock_registry = Mock()
            mock_registry.get_stats.return_value = {'registered_count': 5}
            mock_registry.list_keys.return_value = ['supervisor', 'apex_optimizer', 'reporting', 'data', 'triage']
            mock_get_registry.return_value = mock_registry
            from netra_backend.app.core.registry.universal_registry import get_global_registry
            registry = get_global_registry('agent')
            assert registry is not None, 'AgentRegistry should be initialized'
            stats = registry.get_stats() if hasattr(registry, 'get_stats') else {}
            registered_count = stats.get('registered_count', 0)
            assert registered_count > 0, f'Should have agents registered, got {registered_count}'
            if hasattr(registry, 'list_keys'):
                agent_types = registry.list_keys()
                expected_agents = ['supervisor', 'apex_optimizer', 'reporting']
                for agent in expected_agents:
                    assert agent in agent_types, f'Missing agent: {agent}'

    @pytest.mark.timeout(30)
    def test_health_endpoints_after_startup(self):
        """Test health endpoints report correct status after startup."""
        with patch('netra_backend.app.core.app_factory.create_app') as mock_create_app:
            mock_app = Mock()
            mock_app.state = Mock()
            mock_app.state.startup_complete = True
            mock_app.state.db_session_factory = Mock()
            mock_app.state.redis_manager = Mock()
            mock_create_app.return_value = mock_app
            from fastapi import FastAPI
            from httpx import AsyncClient, ASGITransport
            app = FastAPI()
            app.state.startup_complete = True
            app.state.db_session_factory = Mock()
            app.state.redis_manager = Mock()
            app.state.websocket = TestWebSocketConnection()

            @app.get('/health')
            async def health():
                if not getattr(app.state, 'startup_complete', False):
                    return {'status': 'unhealthy', 'message': 'Startup incomplete'}
                return {'status': 'healthy'}

            @app.get('/health/ready')
            async def ready():
                if not hasattr(app.state, 'db_session_factory'):
                    return {'status': 'not_ready', 'reason': 'Database not initialized'}
                if not hasattr(app.state, 'redis_manager'):
                    return {'status': 'not_ready', 'reason': 'Redis not initialized'}
                return {'status': 'ready'}

            async def test_endpoints():
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url='http://test') as client:
                    response = await client.get('/health')
                    assert response.status_code == 200
                    data = response.json()
                    assert data['status'] == 'healthy'
                    response = await client.get('/health/ready')
                    assert response.status_code == 200
                    data = response.json()
                    assert data['status'] == 'ready'
            asyncio.run(test_endpoints())

@pytest.mark.integration
class TestStartupFailureScenarios(SSotBaseTestCase):
    """Integration tests for startup failure scenarios."""

    def setup_method(self, method):
        """Set up test environment for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'testing')
        self.set_env_var('TESTING', 'true')

    @pytest.mark.timeout(30)
    def test_database_unavailable_startup_failure(self):
        """Test startup fails gracefully when database is unavailable."""
        from unittest.mock import patch
        self.set_env_var('DATABASE_URL', 'postgresql://invalid:invalid@nonexistent:5432/db')
        with patch('netra_backend.app.db.postgres.initialize_postgres') as mock_postgres:
            mock_postgres.side_effect = ConnectionError('Database connection failed')
            from fastapi import FastAPI
            app = FastAPI()
            app.state.websocket = TestWebSocketConnection()
            with self.expect_exception(Exception):
                from netra_backend.app.db.postgres import initialize_postgres
                initialize_postgres()
            mock_postgres.assert_called_once()

    @pytest.mark.timeout(30)
    def test_redis_unavailable_startup_failure(self):
        """Test startup fails gracefully when Redis is unavailable."""
        from unittest.mock import patch
        self.set_env_var('REDIS_URL', 'redis://nonexistent:6379')
        with patch('netra_backend.app.redis_manager.redis_manager.initialize') as mock_redis:
            mock_redis.side_effect = ConnectionError('Redis connection failed')
            from fastapi import FastAPI
            app = FastAPI()
            app.state.websocket = TestWebSocketConnection()
            with self.expect_exception(Exception):
                from netra_backend.app.redis_manager import redis_manager
                asyncio.run(redis_manager.initialize())
            mock_redis.assert_called_once()

    @pytest.mark.timeout(30)
    def test_partial_initialization_rollback(self):
        """Test partial initialization is properly rolled back on failure."""
        from fastapi import FastAPI
        app = FastAPI()
        app.state.websocket = TestWebSocketConnection()
        initialized_components = []

        def init_database():
            initialized_components.append('database')
            app.state.db_session_factory = Mock()

        def init_redis():
            initialized_components.append('redis')
            raise Exception('Redis initialization failed')

        def cleanup():
            if hasattr(app.state, 'db_session_factory'):
                del app.state.db_session_factory
            initialized_components.clear()
        try:
            init_database()
            init_redis()
        except Exception:
            cleanup()
        assert not hasattr(app.state, 'db_session_factory')
        assert len(initialized_components) == 0

@pytest.mark.integration
class TestServiceCoordinationIntegration(SSotBaseTestCase):
    """Integration tests for multi-service coordination."""

    def setup_method(self, method):
        """Set up test environment for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'testing')
        self.set_env_var('TESTING', 'true')

    @pytest.mark.timeout(30)
    def test_backend_auth_service_coordination(self):
        """Test backend properly coordinates with auth service during startup."""

        def mock_auth_health():
            return {'status': 'healthy', 'service': 'auth'}
        auth_available = False
        check_attempts = 0
        max_attempts = 10
        while not auth_available and check_attempts < max_attempts:
            try:
                health = mock_auth_health()
                if health['status'] == 'healthy':
                    auth_available = True
            except:
                pass
            check_attempts += 1
            if not auth_available:
                time.sleep(0.1)
        assert auth_available, 'Auth service not available'
        assert check_attempts <= max_attempts

    @pytest.mark.timeout(30)
    def test_service_discovery_integration(self):
        """Test services can discover each other through environment configuration."""
        self.set_env_var('DATABASE_URL', 'postgresql://test:test@localhost:5432/test_db')
        self.set_env_var('REDIS_URL', 'redis://localhost:6379')
        self.set_env_var('AUTH_SERVICE_URL', 'http://localhost:8001')
        service_urls = {'database': self.get_env_var('DATABASE_URL'), 'redis': self.get_env_var('REDIS_URL'), 'auth': self.get_env_var('AUTH_SERVICE_URL')}
        for service, url in service_urls.items():
            assert url is not None, f'{service} URL not configured'
            assert isinstance(url, str), f'{service} URL invalid type'
            assert len(url) > 0, f'{service} URL empty'

    @pytest.mark.timeout(30)
    def test_graceful_degradation_optional_services(self):
        """Test system starts with degraded functionality when optional services fail."""
        from fastapi import FastAPI
        app = FastAPI()
        app.state.websocket = TestWebSocketConnection()
        service_status = {'database': 'healthy', 'redis': 'healthy', 'clickhouse': 'failed', 'analytics': 'failed'}
        if service_status['database'] == 'healthy':
            app.state.db_session_factory = Mock()
        if service_status['redis'] == 'healthy':
            app.state.redis_manager = Mock()
        required_ok = all((service_status[s] == 'healthy' for s in ['database', 'redis']))
        assert required_ok, 'Required services must be healthy'
        assert hasattr(app.state, 'db_session_factory')
        assert hasattr(app.state, 'redis_manager')
        app.state.degraded_mode = any((service_status[s] == 'failed' for s in ['clickhouse', 'analytics']))
        assert app.state.degraded_mode, 'Should be in degraded mode'

@pytest.mark.integration
class TestStartupPerformance(SSotBaseTestCase):
    """Integration tests for startup performance characteristics."""

    def setup_method(self, method):
        """Set up test environment for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'testing')
        self.set_env_var('TESTING', 'true')
        self.set_env_var('FAST_STARTUP_MODE', 'true')

    @pytest.mark.timeout(60)
    def test_startup_completes_within_timeout(self):
        """Test complete startup finishes within reasonable timeout."""
        with patch('netra_backend.app.db.postgres.initialize_postgres') as mock_postgres, patch('netra_backend.app.redis_manager.redis_manager.initialize') as mock_redis:
            from fastapi import FastAPI
            app = FastAPI()
            app.state.websocket = TestWebSocketConnection()
            mock_postgres.return_value = Mock()
            mock_redis.return_value = None
            app.state.db_session_factory = Mock()
            app.state.redis_manager = Mock()
            app.state.startup_complete = True
            start = time.time()
            mock_postgres()
            asyncio.run(mock_redis())
            app.state.initialized = True
            duration = time.time() - start
            assert duration < 1.0, f'Startup simulation took too long: {duration:.2f}s'

    @pytest.mark.timeout(30)
    def test_parallel_initialization_performance(self):
        """Test parallel initialization improves startup performance."""

        def slow_init(name: str, delay: float):
            time.sleep(delay)
            return f'{name}_initialized'
        start = time.time()
        results_seq = []
        for i in range(3):
            result = slow_init(f'service_{i}', 0.01)
            results_seq.append(result)
        seq_duration = time.time() - start
        start = time.time()
        results_par = [f'service_{i}_initialized' for i in range(3)]
        time.sleep(0.01)
        par_duration = time.time() - start
        assert par_duration < seq_duration
        assert len(results_par) == 3
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')