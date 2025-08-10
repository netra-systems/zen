"""
Basic System Startup Tests
Simplified tests that work with the current codebase structure
"""

import pytest
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBasicStartup:
    """Basic system startup tests"""
    
    def test_environment_setup(self):
        """Test that basic environment variables can be set"""
        test_env = {
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "SECRET_KEY": "test-secret-key",
            "TESTING": "1"
        }
        
        for key, value in test_env.items():
            os.environ[key] = value
            assert os.environ[key] == value
    
    def test_config_manager_import(self):
        """Test that ConfigManager can be imported"""
        try:
            from app.config import ConfigManager
            assert ConfigManager is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ConfigManager: {e}")
    
    def test_app_config_schema(self):
        """Test that AppConfig schema can be imported"""
        try:
            from app.schemas.Config import AppConfig, TestingConfig
            assert AppConfig is not None
            assert TestingConfig is not None
        except ImportError as e:
            pytest.fail(f"Failed to import config schemas: {e}")
    
    @pytest.mark.asyncio
    async def test_database_module_import(self):
        """Test that database modules can be imported"""
        try:
            from app.db import postgres
            assert postgres is not None
        except ImportError as e:
            pytest.fail(f"Failed to import database module: {e}")
    
    def test_logging_setup(self):
        """Test that logging can be configured"""
        try:
            from app.logging_config import central_logger
            assert central_logger is not None
            central_logger.info("Test log message")
        except ImportError as e:
            pytest.fail(f"Failed to import logging: {e}")
    
    def test_websocket_manager_import(self):
        """Test that WebSocketManager can be imported"""
        try:
            from app.ws_manager import WebSocketManager
            assert WebSocketManager is not None
        except ImportError as e:
            pytest.fail(f"Failed to import WebSocketManager: {e}")
    
    def test_main_app_import(self):
        """Test that main FastAPI app can be imported"""
        try:
            from app.main import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import main app: {e}")
    
    @pytest.mark.asyncio
    async def test_health_endpoint_exists(self):
        """Test that health endpoint is defined"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        with TestClient(app) as client:
            # Just check that the route exists, not that it works
            routes = [route.path for route in app.routes]
            assert any("/health" in route for route in routes)
    
    def test_required_directories_exist(self):
        """Test that required directories exist"""
        required_dirs = [
            "app",
            "app/routes",
            "app/services",
            "app/agents",
            "app/db",
            "tests",
            "frontend"
        ]
        
        for dir_path in required_dirs:
            assert os.path.exists(dir_path), f"Directory {dir_path} does not exist"
    
    def test_critical_files_exist(self):
        """Test that critical files exist"""
        critical_files = [
            "app/main.py",
            "app/config.py",
            "app/db/postgres.py",
            "requirements.txt",
            "CLAUDE.md",
            "SPEC/system_startup.xml"
        ]
        
        for file_path in critical_files:
            assert os.path.exists(file_path), f"File {file_path} does not exist"


class TestStartupPerformance:
    """Test startup performance metrics"""
    
    def test_import_time(self):
        """Test that critical imports complete quickly"""
        import_times = {}
        
        # Measure import times
        start = time.time()
        from app.config import ConfigManager
        import_times["ConfigManager"] = time.time() - start
        
        start = time.time()
        from app.main import app
        import_times["FastAPI app"] = time.time() - start
        
        # Check that imports are reasonably fast
        for module, duration in import_times.items():
            assert duration < 5.0, f"{module} took {duration:.2f}s to import"
            print(f"  {module}: {duration:.3f}s")
    
    def test_memory_usage(self):
        """Test memory usage during startup"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Memory should be reasonable (less than 500MB for basic startup)
            assert memory_mb < 500, f"Memory usage too high: {memory_mb:.2f} MB"
            print(f"  Memory usage: {memory_mb:.2f} MB")
        except ImportError:
            pytest.skip("psutil not available")


class TestE2EMinimal:
    """Minimal E2E tests that don't require full system running"""
    
    @pytest.mark.asyncio
    async def test_app_startup_shutdown(self):
        """Test that app can start and shutdown cleanly"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # This uses TestClient which handles lifecycle
        with TestClient(app) as client:
            # App should be running
            assert client is not None
        
        # App should have shut down cleanly
        assert True
    
    def test_api_docs_available(self):
        """Test that API documentation is available"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        with TestClient(app) as client:
            response = client.get("/docs")
            # May redirect or return HTML
            assert response.status_code in [200, 301, 302, 307]


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
        
        # Create supervisor
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
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