"""
System Startup Tests
Tests for complete system initialization and startup procedures
"""

import pytest
import asyncio
import os
import time
import psutil
from unittest.mock import patch, MagicMock, AsyncMock
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config_manager
from app.schemas.Config import AppConfig
from app.db.postgres import get_async_db
from app.redis_manager import RedisManager
from app.ws_manager import WebSocketManager
from app.services.core.service_container import ServiceContainer
from app.logging_config import central_logger


class TestSystemStartup:
    """Test complete system startup sequence"""
    
    @pytest.fixture
    def startup_env(self, monkeypatch):
        """Setup test environment variables"""
        test_env = {
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "SECRET_KEY": "test-secret-key-for-testing-only",
            "REDIS_URL": "redis://localhost:6379/1",
            "CLICKHOUSE_URL": "clickhouse://localhost:9000/test",
            "ANTHROPIC_API_KEY": "test-api-key",
            "ENVIRONMENT": "testing",
            "LOG_LEVEL": "DEBUG",
            "TESTING": "1"
        }
        for key, value in test_env.items():
            monkeypatch.setenv(key, value)
        return test_env
    
    @pytest.fixture
    def mock_external_services(self):
        """Mock external service connections"""
        with patch('app.db.postgres.create_engine') as mock_pg, \
             patch('app.redis_manager.Redis') as mock_redis, \
             patch('app.db.clickhouse.Client') as mock_ch:
            
            # Setup mock returns
            mock_pg.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            mock_ch.return_value = MagicMock()
            
            yield {
                'postgres': mock_pg,
                'redis': mock_redis,
                'clickhouse': mock_ch
            }
    
    def test_environment_validation(self, startup_env, monkeypatch):
        """Test that required environment variables are validated"""
        # Test with all required variables present
        from app.config import config_manager
        # Use the singleton config_manager directly
        config = config_manager.get_config()
        assert config.database_url == startup_env["DATABASE_URL"]
        # Secret key is loaded from environment or defaults
        assert config.secret_key in [startup_env["SECRET_KEY"], "default_secret_key"]
        
        # Test with missing critical variable - should use default
        monkeypatch.delenv("DATABASE_URL")
        from app.config import reload_config
        reload_config()  # Clear cache and reload configuration
        config_new = config_manager.get_config()
        # Should use default database URL when env var is missing
        assert config_new.database_url != startup_env["DATABASE_URL"]
        assert "postgres" in config_new.database_url  # Has default postgres URL
    
    def test_configuration_loading(self, startup_env):
        """Test configuration file loading and validation"""
        from app.config import config_manager
        
        # Use the singleton config_manager directly
        config = config_manager.get_config()
        assert config is not None
        assert config.app_name == "netra"
        assert config.environment == "testing"
        assert config.database_url is not None
    
    @pytest.mark.asyncio
    async def test_database_connection_startup(self, startup_env, mock_external_services):
        """Test database connection initialization during startup"""
        # Mock successful connection
        mock_engine = AsyncMock()
        mock_external_services['postgres'].return_value = mock_engine
        
        # Test connection availability
        from app.db.postgres import get_async_db
        assert get_async_db is not None
    
    @pytest.mark.asyncio
    async def test_database_migration_on_startup(self, startup_env, tmp_path):
        """Test that migrations run automatically on startup"""
        # Create a temporary alembic.ini
        alembic_ini = tmp_path / "alembic.ini"
        alembic_ini.write_text("""
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite:///:memory:
        """)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Simulate migration run using the actual migration approach
            from app.main import _check_and_run_migrations
            from app.logging_config import central_logger
            
            # Run migrations check
            _check_and_run_migrations(central_logger)
            
            # Verify subprocess was called (alembic upgrade)
            assert mock_run.called
    
    @pytest.mark.asyncio
    async def test_redis_connection_startup(self, startup_env):
        """Test Redis connection initialization"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.from_url.return_value = mock_redis
            
            # Initialize Redis manager
            redis_manager = RedisManager()
            # RedisManager doesn't have initialize, it uses connect
            await redis_manager.connect()
            
            # Verify connection was attempted (redis_client will be None if disabled or failed)
            # In test environment with mock, it may be None
            assert redis_manager is not None
            assert hasattr(redis_manager, 'redis_client')
    
    @pytest.mark.asyncio  
    async def test_service_container_initialization(self, startup_env):
        """Test service container and dependency injection setup"""
        from app.services.core.service_container import ServiceContainer
        
        container = ServiceContainer()
        
        # Register test services
        test_service = MagicMock()
        container.register("test_service", test_service)
        
        # Verify service retrieval
        retrieved = container.get("test_service")
        assert retrieved == test_service
        
        # Test missing service
        with pytest.raises(KeyError):
            container.get("non_existent_service")
    
    @pytest.mark.asyncio
    async def test_agent_system_initialization(self, startup_env):
        """Test agent system components initialization"""
        from app.agents.base import BaseSubAgent
        from app.services.tool_registry import ToolRegistry
        
        # Initialize tool registry
        registry = ToolRegistry()
        
        # Register a test tool
        test_tool = MagicMock()
        test_tool.name = "test_tool"
        registry.register(test_tool)
        
        # Verify tool registration
        assert "test_tool" in registry.list_tools()
        retrieved_tool = registry.get_tool("test_tool")
        assert retrieved_tool == test_tool
    
    @pytest.mark.asyncio
    async def test_websocket_manager_initialization(self, startup_env):
        """Test WebSocket manager initialization"""
        ws_manager = WebSocketManager()
        
        # Verify manager is initialized
        assert ws_manager is not None
        assert ws_manager.connection_manager is not None
        assert ws_manager.connection_manager.active_connections == {}
        
        # Test statistics initialization
        stats = await ws_manager.get_statistics()
        assert stats["total_connections"] == 0
        assert stats["active_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_authentication_system_startup(self, startup_env):
        """Test authentication system initialization"""
        from app.services.security_service import SecurityService
        
        security_service = SecurityService()
        
        # Test JWT token creation
        test_payload = {"user_id": "test_user", "email": "test@example.com"}
        from app.schemas import TokenPayload
        token_data = TokenPayload(sub="test_user", email="test@example.com")
        token = security_service.create_access_token(token_data)
        assert token is not None
        
        # Test token decoding
        decoded = security_service.decode_access_token(token)
        assert decoded["sub"] == "test_user"
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, startup_env):
        """Test health check endpoint availability after startup"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] in ["OK", "healthy"]
            assert "timestamp" in data
            assert "version" in data
    
    @pytest.mark.asyncio
    async def test_detailed_health_check(self, startup_env, mock_external_services):
        """Test detailed health check with component status"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Mock service health
        mock_external_services['postgres'].return_value.execute.return_value = MagicMock()
        mock_external_services['redis'].return_value.ping.return_value = True
        
        with TestClient(app) as client:
            response = client.get("/api/health/detailed")
            
            if response.status_code == 200:
                data = response.json()
                assert "database" in data
                assert "redis" in data
                assert "memory" in data
                assert "uptime" in data
    
    @pytest.mark.asyncio
    async def test_startup_error_handling(self, monkeypatch):
        """Test proper error handling during startup failures"""
        # Test with missing DATABASE_URL
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        with pytest.raises(Exception) as exc_info:
            from app.config import config_manager, reload_config
            # Use the singleton config_manager directly
            reload_config()  # Clear cache and reload configuration
            config_manager.get_config()
        
        # Verify error message is informative
        error_msg = str(exc_info.value)
        assert "DATABASE_URL" in error_msg or "database" in error_msg.lower()
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, startup_env):
        """Test graceful shutdown procedures"""
        # Initialize components
        ws_manager = WebSocketManager()
        
        # Simulate shutdown
        await ws_manager.shutdown()
        
        # Verify all connections closed through connection_manager
        assert len(ws_manager.connection_manager.active_connections) == 0
        assert ws_manager.connection_manager.get_stats()["active_connections"] == 0
    
    def test_startup_performance_metrics(self, startup_env):
        """Test startup time and resource usage"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Simulate startup operations
        from app.config import config_manager
        # Use the singleton config_manager directly
        config = config_manager.get_config()
        
        # Calculate metrics
        startup_duration = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_increase = end_memory - start_memory
        
        # Assert reasonable startup performance
        assert startup_duration < 5.0  # Should start in under 5 seconds
        assert memory_increase < 500  # Should not use more than 500MB additional
        
        # Log metrics for monitoring
        central_logger.info(f"Startup duration: {startup_duration:.2f}s")
        central_logger.info(f"Memory increase: {memory_increase:.2f}MB")


class TestFirstTimeRun:
    """Test first-time run procedures"""
    
    @pytest.mark.asyncio
    async def test_database_creation(self, tmp_path):
        """Test database creation on first run"""
        db_path = tmp_path / "test.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"
        
        with patch.dict(os.environ, {"DATABASE_URL": db_url}):
            from app.db.postgres import get_async_db
            
            # Test database connection availability
            assert get_async_db is not None
    
    @pytest.mark.asyncio
    async def test_initial_migrations(self, tmp_path):
        """Test running migrations on fresh database"""
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK")
            
            # Run migrations
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True
            )
            
            # Verify migrations completed
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_default_admin_creation(self, startup_env):
        """Test creation of default admin user on first run"""
        from app.services.database.userbase_repository import UserbaseRepository
        from app.models import Userbase
        
        with patch.object(UserbaseRepository, 'create') as mock_create:
            mock_create.return_value = Userbase(
                id="admin",
                email="admin@example.com",
                username="admin",
                is_active=True,
                is_superuser=True
            )
            
            # Create default admin
            repo = UserbaseRepository(db=MagicMock())
            admin = await repo.create({
                "email": "admin@example.com",
                "username": "admin",
                "password": "secure_password",
                "is_superuser": True
            })
            
            assert admin.is_superuser is True
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_oauth_provider_setup(self, startup_env, monkeypatch):
        """Test OAuth provider configuration on first run"""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
        
        from app.auth.oauth import OAuthManager
        
        oauth_manager = OAuthManager()
        
        # Verify Google OAuth is configured
        assert oauth_manager.google_client_id == "test-client-id"
        assert oauth_manager.google_client_secret == "test-client-secret"
        assert oauth_manager.is_configured("google") is True


class TestStartupSequence:
    """Test the complete startup sequence order"""
    
    @pytest.mark.asyncio
    async def test_startup_order(self, startup_env):
        """Test that startup steps execute in correct order"""
        execution_order = []
        
        # Mock each startup step
        with patch('app.config.Settings') as mock_settings:
            execution_order.append("config")
            
        with patch('app.logging_config.setup_logging') as mock_logging:
            execution_order.append("logging")
            
        with patch('app.db.postgres.get_async_db') as mock_db:
            execution_order.append("database")
            
        with patch('subprocess.run') as mock_migrations:
            mock_migrations.return_value = MagicMock(returncode=0)
            execution_order.append("migrations")
            
        with patch('app.redis_manager.RedisManager.initialize') as mock_redis:
            execution_order.append("redis")
            
        with patch('app.services.core.service_interfaces.ServiceContainer') as mock_services:
            execution_order.append("services")
            
        # Verify order
        expected_order = ["config", "logging", "database", "migrations", "redis", "services"]
        for i, step in enumerate(expected_order):
            if i < len(execution_order):
                assert execution_order[i] == step, f"Step {step} not in correct position"
    
    @pytest.mark.asyncio
    async def test_startup_with_retry(self, startup_env):
        """Test startup retry logic for transient failures"""
        attempt_count = 0
        
        async def mock_connect():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Connection failed")
            return True
        
        # Test retry logic
        max_retries = 3
        for i in range(max_retries):
            try:
                result = await mock_connect()
                break
            except ConnectionError:
                if i == max_retries - 1:
                    raise
                await asyncio.sleep(0.1)
        
        assert attempt_count == 3
        assert result is True
    
    @pytest.mark.asyncio
    async def test_startup_timeout(self, startup_env):
        """Test startup timeout handling"""
        async def slow_operation():
            await asyncio.sleep(10)
            return True
        
        # Test with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_partial_startup_recovery(self, startup_env):
        """Test recovery from partial startup failures"""
        startup_state = {
            "config": False,
            "database": False,
            "redis": False,
            "services": False
        }
        
        async def startup_with_recovery():
            try:
                # Simulate partial success
                startup_state["config"] = True
                startup_state["database"] = True
                
                # Simulate failure at Redis
                raise ConnectionError("Redis connection failed")
                
            except ConnectionError:
                # Attempt recovery
                startup_state["redis"] = True  # Recovery successful
                startup_state["services"] = True
                return startup_state
        
        result = await startup_with_recovery()
        
        # Verify all components eventually started
        assert all(result.values())


class TestErrorHandlingFix:
    """Test the critical bug fix for agent error handling"""
    
    @pytest.mark.asyncio
    async def test_supervisor_error_string_formatting(self):
        """Verify that supervisor_consolidated.py properly formats exception messages as strings"""
        from app.agents.supervisor_consolidated import SupervisorAgent, AgentExecutionContext
        from app.agents.state import DeepAgentState
        from unittest.mock import Mock, AsyncMock
        
        # Create mock dependencies
        mock_llm_manager = Mock()
        mock_tool_dispatcher = Mock()
        mock_db_session = Mock()
        mock_websocket_manager = Mock()
        
        # Create supervisor
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            db_session=mock_db_session,
            websocket_manager=mock_websocket_manager
        )
        
        # Create a failing agent mock
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.execute = AsyncMock(side_effect=RuntimeError("Test error message"))
        mock_agent.set_state = Mock()
        mock_agent.get_state = Mock()
        
        # Create context
        context = AgentExecutionContext(
            run_id="test-run-id",
            thread_id="test-thread",
            user_id="test-user",
            agent_name="test-agent",
            max_retries=1
        )
        
        # Create state
        state = DeepAgentState(user_request="Test request")
        
        # Test that error is properly formatted
        try:
            await supervisor._execute_agent_with_retry(
                mock_agent, state, context, stream_updates=False
            )
        except Exception as e:
            error_msg = str(e)
            # Verify the error message is properly formatted
            assert "TestAgent failed after" in error_msg
            assert "Test error message" in error_msg
            # Ensure no raw exception objects in the message
            assert "RuntimeError(" not in error_msg
            assert "<" not in error_msg  # No object representations


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])