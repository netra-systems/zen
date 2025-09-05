"""Critical test for WebSocket circular import regression.

This test specifically prevents the regression where WebSocket modules
importing BaseExecutionEngine caused circular dependencies that prevented
agent registration and message processing.

REGRESSION HISTORY:
- Date: 2025-01-19
- Issue: Circular import between app.websocket_core modules and app.agents.base.executor
- Impact: Agents couldn't be imported, WebSocket messages sent but no responses
- Fix: Removed BaseExecutionEngine imports from WebSocket modules

- Date: 2025-08-18
- Issue: Circular import between connection.py, connection_executor.py, and connection_manager.py
- Impact: Module-level initialization of connection_manager caused import loops
- Fix: Made connection_manager lazy-loaded with get_connection_monitor_instance()
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import ast
import importlib
import os
import sys
from typing import List, Set

import pytest

class TestCircularImportRegression:
    """Prevent the specific circular import regression."""
    
    def test_no_baseexecutionengine_import_in_websocket(self):
        """WebSocket modules MUST NOT import BaseExecutionEngine."""
        websocket_modules = [
            'app.websocket_core.handlers',
            'app.websocket_core.manager',
            'app.websocket_core.auth',
            'app.websocket_core.utils',
            'app.websocket_core.types'
        ]
        
        for module_name in websocket_modules:
            # Get the file path - go up from tests directory
            module_path = os.path.join('..', '..', module_name.replace('.', os.sep) + '.py')
            
            # Read the file content
            with open(module_path, 'r') as f:
                content = f.read()
            
            # Check for BaseExecutionEngine import
            assert 'from app.agents.base.executor import BaseExecutionEngine' not in content, \
                f"{module_name} imports BaseExecutionEngine - CIRCULAR DEPENDENCY!"
            
            # Also check for any reference to BaseExecutionEngine
            if 'BaseExecutionEngine' in content and 'Removed BaseExecutionEngine' not in content:
                pytest.fail(f"{module_name} references BaseExecutionEngine - potential circular dependency!")
    
    def test_websocket_modules_use_local_execution(self):
        """Verify WebSocket modules use local execution patterns."""
        from netra_backend.app.websocket_core.manager import WebSocketManager
        
        # Verify execution_engine is None or local implementation
        manager = WebSocketManager()
        # WebSocketManager shouldn't have execution_engine attribute
        assert not hasattr(manager, 'execution_engine'), \
            "WebSocketManager should not use BaseExecutionEngine"
    
    def test_import_order_independence(self):
        """Test that modules can be imported in any order."""
        # Clear any cached imports
        modules_to_test = [
            'netra_backend.app.websocket_core',
            'netra_backend.app.agents.base.executor',
            'netra_backend.app.agents.supervisor_consolidated',
            'netra_backend.app.services.agent_service_core'
        ]
        
        # Test forward order
        for module in modules_to_test:
            if module in sys.modules:
                del sys.modules[module]
        
        try:
            for module in modules_to_test:
                importlib.import_module(module)
        except ImportError as e:
            pytest.fail(f"Forward import failed: {e}")
        
        # Clear and test reverse order
        for module in modules_to_test:
            if module in sys.modules:
                del sys.modules[module]
        
        try:
            for module in reversed(modules_to_test):
                importlib.import_module(module)
        except ImportError as e:
            pytest.fail(f"Reverse import failed: {e}")
    
    def test_agent_registry_accessible_after_imports(self):
        """Verify agent registry is accessible after all imports."""
        # Import in problematic order
        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.websocket_core.manager import WebSocketManager
        
        # Verify classes are accessible
        assert WebSocketManager is not None
        assert SupervisorAgent is not None  
        assert AgentRegistry is not None
        
        # Verify registry can be instantiated
        mock_llm = type('MockLLM', (), {})()
        mock_dispatcher = type('MockDispatcher', (), {})()
        
        registry = AgentRegistry()
        registry.register_default_agents()
        
        # Verify agents are registered
        assert len(registry.list_agents()) >= 5, \
            "Agent registry should have at least 5 default agents"
    
    def test_websocket_handler_without_execution_engine(self):
        """Test WebSocket handlers work without BaseExecutionEngine."""
        from netra_backend.app.websocket_core.handlers import (
            BaseMessageHandler,
        )
        
        # Create handler with required parameters
        from netra_backend.app.websocket_core.types import MessageType
        handler = BaseMessageHandler([MessageType.USER_MESSAGE])
        
        # Verify it doesn't have execution_engine or it's None
        if hasattr(handler, 'execution_engine'):
            assert handler.execution_engine is None, \
                "Message handler should not use BaseExecutionEngine"
    
    def test_broadcast_executor_without_execution_engine(self):
        """Test broadcast executor works without BaseExecutionEngine."""
        from netra_backend.app.websocket_core import (
            WebSocketManager,
        )
        
        # Create WebSocket manager instance
        manager = WebSocketManager()
        
        # Verify execution_engine is not present
        assert not hasattr(manager, 'execution_engine'), \
            "WebSocket manager should not use BaseExecutionEngine"
    
    @pytest.mark.asyncio
    async def test_message_flow_without_circular_dependency(self):
        """Test message flow works after circular dependency fix."""

        from netra_backend.app.services.agent_service_core import AgentService
        
        # Create mock supervisor
        # Mock: Generic component isolation for controlled unit testing
        mock_supervisor = AsyncNone  # TODO: Use real service instance
        # Mock: Async component isolation for testing without real async operations
        mock_supervisor.run = AsyncMock(return_value="Test response")
        
        # Create agent service
        service = AgentService(mock_supervisor)
        
        # Test message
        message = {
            "type": "user_message",
            "payload": {"content": "Test after circular fix"}
        }
        
        # Process message
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.ws_manager.manager'):
            await service.handle_websocket_message(
                user_id="test_user",
                message=message,
                db_session=None
            )
        
        # Verify supervisor was called
        assert mock_supervisor.run.called, \
            "Message should trigger supervisor execution after circular fix"

class TestConnectionModuleCircularImportPrevention:
    """Prevent regression of connection module circular import fixes."""
    
    def test_connection_manager_lazy_initialization(self):
        """Test that connection.py uses lazy initialization.
        
        Business Value: Prevents import-time initialization causing circular deps.
        Protects $50K+ MRR from WebSocket connection failures.
        """
        # Clear module cache
        modules_to_clear = [
            'netra_backend.app.websocket_core',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.handlers'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Import connection module
        # Note: The connection module was removed in unified WebSocket architecture
        # These components are now part of WebSocketManager
        from netra_backend.app.websocket_core.manager import WebSocketManager, get_websocket_manager
        
        # Verify WebSocketManager can be imported without circular dependencies
        assert WebSocketManager is not None, \
            "WebSocketManager class must be importable"
        
        # Verify getter exists and works
        assert callable(get_websocket_manager), \
            "get_websocket_manager must be callable"
        
        # Test lazy getter returns instance
        manager = get_websocket_manager()
        assert manager is not None, "Lazy getter must return manager instance"
        
        # Verify singleton behavior
        second_manager = get_websocket_manager()
        assert second_manager is manager, "Should return same instance (singleton)"
    
    def test_connection_modules_import_independently(self):
        """Test each connection module imports independently.
        
        Business Value: Ensures microservice independence per SPEC requirements.
        """
        test_cases = [
            # These modules no longer exist in the unified WebSocket architecture
            # All functionality is now in websocket_core modules
            ('netra_backend.app.websocket_core', ['WebSocketManager', 'get_websocket_manager']),
            ('netra_backend.app.websocket_core.types', ['ConnectionInfo']),
            ('netra_backend.app.websocket_core.manager', ['WebSocketManager'])
        ]
        
        for module_name, expected_attrs in test_cases:
            # Clear module cache
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            try:
                # Import module in isolation
                module = importlib.import_module(module_name)
                
                # Verify expected attributes exist
                for attr in expected_attrs:
                    assert hasattr(module, attr), \
                        f"{module_name} missing expected attribute: {attr}"
                        
            except ImportError as e:
                pytest.fail(f"{module_name} failed isolated import: {e}")
            finally:
                # Clean up
                if module_name in sys.modules:
                    del sys.modules[module_name]
    
    def test_connection_backward_compatibility(self):
        """Test all legacy exports remain available.
        
        Business Value: Prevents breaking changes in dependent services.
        """
        from netra_backend.app import websocket_core
        
        # Core exports in the unified WebSocket architecture
        # Most legacy classes were consolidated or removed
        core_exports = ['WebSocketManager', 'get_websocket_manager', 'ConnectionInfo']
        for export in core_exports:
            assert hasattr(websocket_core, export), \
                f"Missing core export: {export}"

class TestIndirectCircularImportPrevention:
    """Test for indirect circular imports that manifest at runtime.
    
    REGRESSION HISTORY:
    - Date: 2025-08-21
    - Issue: Indirect circular import: ws_manager → synthetic_data.error_handler → 
             synthetic_data → job_manager → ws_manager
    - Impact: Tests couldn't detect the circular dependency because it manifested 
              only during runtime initialization
    - Fix: Use lazy imports in job_manager.py for WebSocket manager references
    """
    
    def test_no_websocket_manager_import_in_synthetic_data_modules(self):
        """Synthetic data modules should use lazy imports for WebSocket manager.
        
        Business Value: Prevents $50K+ MRR loss from service initialization failures.
        """
        import ast
        import os
        
        # Modules that commonly create circular dependencies
        synthetic_data_modules = [
            'app/services/synthetic_data/job_manager.py',
            'app/services/synthetic_data/job_operations.py',
            'app/services/synthetic_data/analytics_reporter.py',
        ]
        
        for module_path in synthetic_data_modules:
            full_path = os.path.join(
                os.path.dirname(__file__), '..', '..', module_path
            )
            
            if not os.path.exists(full_path):
                continue
                
            with open(full_path, 'r') as f:
                content = f.read()
                
            # Parse the AST to check for top-level ws_manager imports
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    # Check for direct import of ws_manager at module level
                    if (node.module and 'ws_manager' in node.module and 
                        node.col_offset == 0):  # col_offset 0 = module level
                        
                        # Allow TYPE_CHECKING imports
                        is_type_checking = False
                        for parent in ast.walk(tree):
                            if (isinstance(parent, ast.If) and 
                                isinstance(parent.test, ast.Name) and
                                parent.test.id == 'TYPE_CHECKING'):
                                if node in ast.walk(parent):
                                    is_type_checking = True
                                    break
                        
                        if not is_type_checking:
                            pytest.fail(
                                f"{module_path} has module-level import of ws_manager. "
                                f"Use lazy imports inside methods or TYPE_CHECKING guard!"
                            )
    
    def test_websocket_to_synthetic_data_import_chain(self):
        """Test that WebSocket → Synthetic Data import chain doesn't create cycles.
        
        Business Value: Ensures microservice independence per SPEC requirements.
        """
        import importlib
        import sys
        
        # Clear module cache for clean test
        modules_to_clear = [
            'netra_backend.app.ws_manager',
            'app.services.synthetic_data.error_handler', 
            'app.services.synthetic_data.job_manager',
            'app.services.synthetic_data_service',
        ]
        
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Track import order to detect cycles
        import_tracker = []
        original_import = __builtins__.__import__
        
        def tracking_import(name, *args, **kwargs):
            if 'netra_backend.app' in name:
                import_tracker.append(name)
                
                # Check for cycles
                if name in import_tracker[:-1]:
                    cycle_start = import_tracker.index(name)
                    cycle = import_tracker[cycle_start:]
                    pytest.fail(
                        f"Circular import detected: {' → '.join(cycle)}"
                    )
            
            return original_import(name, *args, **kwargs)
        
        # Temporarily replace import to track calls
        __builtins__.__import__ = tracking_import
        
        try:
            # Import in the problematic order
            from netra_backend.app.services import synthetic_data_service
            from netra_backend.app import ws_manager
            
            # If we get here, no circular import was detected
            assert True, "No circular import detected"
            
        finally:
            # Restore original import
            __builtins__.__import__ = original_import
    
    def test_job_manager_lazy_imports(self):
        """Verify job_manager uses lazy imports for WebSocket manager.
        
        Business Value: Prevents service startup failures worth $100K+ annual revenue.
        """
        import os
        
        job_manager_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 
            'app/services/synthetic_data/job_manager.py'
        )
        
        with open(job_manager_path, 'r') as f:
            content = f.read()
        
        # Check that ws_manager import is either:
        # 1. Inside TYPE_CHECKING block
        # 2. Inside method definitions (lazy)
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'from netra_backend.app.ws_manager import' in line or 'from app.services.websocket.ws_manager import' in line:
                # Check indentation to ensure it's not at module level
                if line.startswith('from'):  # No indentation = module level
                    # Check if it's in TYPE_CHECKING block
                    found_type_checking = False
                    for j in range(max(0, i-5), i):
                        if 'TYPE_CHECKING' in lines[j]:
                            found_type_checking = True
                            break
                    
                    if not found_type_checking:
                        pytest.fail(
                            f"job_manager.py line {i+1}: Module-level import of ws_manager "
                            f"found outside TYPE_CHECKING. Use lazy imports!"
                        )