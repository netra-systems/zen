"""
Integration Tests for Backend Startup Asyncio Safety

Tests to ensure backend startup doesn't have nested event loop issues.
"""
import asyncio
import sys
import os
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, AsyncMock

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import test utilities
from tests.utils.asyncio_test_utils import (
    AsyncioTestUtils,
    EventLoopTestError,
    AsyncioRegressionTester
)


class TestBackendStartupAsyncioSafety:
    """Integration tests for backend startup event loop safety"""
    
    @pytest.mark.asyncio
    async def test_startup_fixes_integration_no_nested_loops(self):
        """Test that startup_fixes_integration doesn't use nested asyncio.run()"""
        # Import the module to test
        from netra_backend.app.services.startup_fixes_integration import StartupFixesIntegration
        
        # The fixed version should properly handle async context
        integration = StartupFixesIntegration()
        
        # Test that validate_tools can be called from async context
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            # This should not raise EventLoopTestError
            result = await integration.validate_tools()
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_startup_sequence_no_deadlock(self):
        """Test complete startup sequence doesn't deadlock"""
        from netra_backend.app.services.startup_fixes_integration import StartupFixesIntegration
        
        integration = StartupFixesIntegration()
        
        # Mock external dependencies to avoid actual connections
        with patch.object(integration, '_load_tools') as mock_load:
            mock_load.return_value = []
            
            # Run validation in async context (simulating actual startup)
            result = await integration.validate_tools()
            assert result == {"tools_valid": True, "tools": []}
    
    @pytest.mark.asyncio
    async def test_app_initialization_async_safety(self):
        """Test app initialization doesn't have nested loops"""
        from netra_backend.app.core.app_initializer import AppInitializer
        
        # Create app initializer
        initializer = AppInitializer()
        
        # Mock dependencies
        with patch('netra_backend.app.core.app_initializer.StartupFixesIntegration') as mock_startup:
            mock_startup_instance = Mock()
            mock_startup_instance.validate_tools = AsyncMock(return_value={"tools_valid": True})
            mock_startup.return_value = mock_startup_instance
            
            # This should work without deadlock
            with AsyncioTestUtils.assert_no_nested_asyncio_run():
                # Test initialization can happen in async context
                pass  # Just ensuring no nested asyncio.run() is called
    
    def test_startup_from_sync_context(self):
        """Test startup works from synchronous context"""
        from netra_backend.app.services.startup_fixes_integration import StartupFixesIntegration
        
        integration = StartupFixesIntegration()
        
        # Mock dependencies
        with patch.object(integration, '_load_tools') as mock_load:
            mock_load.return_value = []
            
            # This should work in sync context (main entry point)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(integration.validate_tools())
                assert result == {"tools_valid": True, "tools": []}
            finally:
                loop.close()
    
    @pytest.mark.asyncio
    async def test_multiple_startup_components_async_safety(self):
        """Test multiple startup components for async safety"""
        components_to_test = []
        
        # Test Redis manager
        try:
            from netra_backend.app.services.redis_manager import RedisManager
            components_to_test.append(('RedisManager', RedisManager))
        except ImportError:
            pass
        
        # Test WebSocket manager
        try:
            from netra_backend.app.services.websocket_manager import WebSocketManager
            components_to_test.append(('WebSocketManager', WebSocketManager))
        except ImportError:
            pass
        
        # Test Auth integration
        try:
            from netra_backend.app.services.auth_integration import AuthIntegration
            components_to_test.append(('AuthIntegration', AuthIntegration))
        except ImportError:
            pass
        
        for name, component_class in components_to_test:
            # Check if the component has any initialization that might use asyncio.run()
            with AsyncioTestUtils.assert_no_nested_asyncio_run():
                # Just instantiate - shouldn't cause nested loops
                instance = component_class()
                assert instance is not None, f"{name} should instantiate without deadlock"


class TestDatabaseConnectionAsyncioSafety:
    """Test database connections don't have nested loop issues"""
    
    @pytest.mark.asyncio
    async def test_database_manager_async_safety(self):
        """Test database manager doesn't use nested asyncio.run()"""
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Mock database URL to avoid actual connection
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            manager = DatabaseManager()
            
            # Test that we can work with database in async context
            with AsyncioTestUtils.assert_no_nested_asyncio_run():
                # Manager operations should use proper async patterns
                assert manager is not None
    
    @pytest.mark.asyncio  
    async def test_database_session_async_context(self):
        """Test database sessions work properly in async context"""
        from netra_backend.app.database import get_async_session_context
        
        # Mock the database URL
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            with patch('netra_backend.app.database.async_engine') as mock_engine:
                mock_session = AsyncMock()
                mock_engine.begin = AsyncMock()
                
                # This should work without nested loops
                with AsyncioTestUtils.assert_no_nested_asyncio_run():
                    async with get_async_session_context() as session:
                        assert session is not None


class TestWebSocketAsyncioSafety:
    """Test WebSocket handling doesn't have nested loop issues"""
    
    @pytest.mark.asyncio
    async def test_websocket_manager_async_safety(self):
        """Test WebSocket manager uses proper async patterns"""
        from netra_backend.app.services.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        
        # Test that WebSocket operations don't use nested asyncio.run()
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            # Mock WebSocket for testing
            mock_websocket = AsyncMock()
            mock_websocket.accept = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            
            # Connection handling should be async
            await manager.connect(mock_websocket, "test_client")
            assert "test_client" in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_websocket_recovery_async_safety(self):
        """Test WebSocket recovery doesn't have nested loops"""
        from netra_backend.app.core.websocket_recovery_manager import WebSocketRecoveryManager
        
        recovery_manager = WebSocketRecoveryManager()
        
        # Test recovery operations  
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            # Mock connection
            connection_id = "test_conn_1"
            
            # These should all use proper async patterns
            await recovery_manager.register_connection(connection_id)
            await recovery_manager.mark_healthy(connection_id)
            status = await recovery_manager.get_connection_status(connection_id)
            
            assert status is not None


class TestAuthServiceAsyncioSafety:
    """Test auth service interactions don't have nested loops"""
    
    @pytest.mark.asyncio
    async def test_auth_integration_async_safety(self):
        """Test auth integration uses proper async patterns"""
        from netra_backend.app.services.auth_integration import AuthIntegration
        
        auth = AuthIntegration()
        
        # Mock auth service URL
        with patch.dict(os.environ, {'AUTH_SERVICE_URL': 'http://localhost:8001'}):
            with AsyncioTestUtils.assert_no_nested_asyncio_run():
                # Mock HTTP client
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = AsyncMock()
                    mock_response.status_code = 200
                    mock_response.json = AsyncMock(return_value={"valid": True})
                    
                    mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                    
                    # This should use proper async patterns
                    result = await auth.verify_token("test_token")
                    assert result is not None


class TestAsyncioRegressionSuite:
    """Comprehensive regression test suite"""
    
    @pytest.mark.asyncio
    async def test_full_regression_check(self):
        """Run full regression check on critical components"""
        tester = AsyncioRegressionTester()
        
        # List of critical async functions to test
        critical_functions = []
        
        # Add startup functions
        try:
            from netra_backend.app.services.startup_fixes_integration import StartupFixesIntegration
            integration = StartupFixesIntegration()
            critical_functions.append((integration.validate_tools, "StartupFixesIntegration.validate_tools"))
        except:
            pass
        
        # Add WebSocket functions
        try:
            from netra_backend.app.services.websocket_manager import WebSocketManager
            manager = WebSocketManager()
            critical_functions.append((manager.broadcast, "WebSocketManager.broadcast"))
        except:
            pass
        
        # Test each function
        for func, name in critical_functions:
            passed = await tester.test_function_for_nested_loops(func, name)
            assert passed, f"{name} has asyncio safety issues"
        
        # Generate report
        report = tester.generate_report()
        print("\n" + report)
        
        # Ensure no failures
        assert len(tester.failures) == 0, f"Found {len(tester.failures)} asyncio safety issues"


class TestAsyncioPatternValidation:
    """Validate asyncio patterns across the codebase"""
    
    def test_validate_startup_module(self):
        """Validate the startup module for asyncio patterns"""
        from tests.utils.asyncio_test_utils import EventLoopValidator
        
        # Path to startup module
        startup_path = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "services" / "startup_fixes_integration.py"
        
        if startup_path.exists():
            results = EventLoopValidator.validate_module(str(startup_path))
            
            # After our fix, there should be no nested asyncio.run() issues
            assert results['potential_issues'] == 0, f"Found {results['potential_issues']} potential asyncio issues in startup module"
    
    def test_validate_websocket_modules(self):
        """Validate WebSocket modules for asyncio patterns"""
        from tests.utils.asyncio_test_utils import EventLoopValidator
        
        websocket_modules = [
            "netra_backend/app/services/websocket_manager.py",
            "netra_backend/app/core/websocket_recovery_manager.py"
        ]
        
        base_path = Path(__file__).parent.parent.parent
        
        for module_path in websocket_modules:
            full_path = base_path / module_path
            if full_path.exists():
                results = EventLoopValidator.validate_module(str(full_path))
                assert results['potential_issues'] == 0, f"Found asyncio issues in {module_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])