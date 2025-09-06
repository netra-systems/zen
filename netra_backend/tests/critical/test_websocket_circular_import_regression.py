from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio

# REMOVED_SYNTAX_ERROR: '''Critical test for WebSocket circular import regression.

# REMOVED_SYNTAX_ERROR: This test specifically prevents the regression where WebSocket modules
# REMOVED_SYNTAX_ERROR: importing BaseExecutionEngine caused circular dependencies that prevented
# REMOVED_SYNTAX_ERROR: agent registration and message processing.

# REMOVED_SYNTAX_ERROR: REGRESSION HISTORY:
    # REMOVED_SYNTAX_ERROR: - Date: 2025-01-19
    # REMOVED_SYNTAX_ERROR: - Issue: Circular import between app.websocket_core modules and app.agents.base.executor
    # REMOVED_SYNTAX_ERROR: - Impact: Agents couldn"t be imported, WebSocket messages sent but no responses
    # REMOVED_SYNTAX_ERROR: - Fix: Removed BaseExecutionEngine imports from WebSocket modules

    # REMOVED_SYNTAX_ERROR: - Date: 2025-08-18
    # REMOVED_SYNTAX_ERROR: - Issue: Circular import between connection.py, connection_executor.py, and connection_manager.py
    # REMOVED_SYNTAX_ERROR: - Impact: Module-level initialization of connection_manager caused import loops
    # REMOVED_SYNTAX_ERROR: - Fix: Made connection_manager lazy-loaded with get_connection_monitor_instance()
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # Test framework import - using pytest fixtures instead

    # REMOVED_SYNTAX_ERROR: import ast
    # REMOVED_SYNTAX_ERROR: import importlib
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from typing import List, Set

    # REMOVED_SYNTAX_ERROR: import pytest

# REMOVED_SYNTAX_ERROR: class TestCircularImportRegression:
    # REMOVED_SYNTAX_ERROR: """Prevent the specific circular import regression."""

# REMOVED_SYNTAX_ERROR: def test_no_baseexecutionengine_import_in_websocket(self):
    # REMOVED_SYNTAX_ERROR: """WebSocket modules MUST NOT import BaseExecutionEngine."""
    # REMOVED_SYNTAX_ERROR: websocket_modules = [ )
    # REMOVED_SYNTAX_ERROR: 'app.websocket_core.handlers',
    # REMOVED_SYNTAX_ERROR: 'app.websocket_core.manager',
    # REMOVED_SYNTAX_ERROR: 'app.websocket_core.auth',
    # REMOVED_SYNTAX_ERROR: 'app.websocket_core.utils',
    # REMOVED_SYNTAX_ERROR: 'app.websocket_core.types'
    

    # REMOVED_SYNTAX_ERROR: for module_name in websocket_modules:
        # Get the file path - go up from tests directory
        # REMOVED_SYNTAX_ERROR: module_path = os.path.join('..', '..', module_name.replace('.', os.sep) + '.py')

        # Read the file content
        # REMOVED_SYNTAX_ERROR: with open(module_path, 'r') as f:
            # REMOVED_SYNTAX_ERROR: content = f.read()

            # Check for BaseExecutionEngine import
            # REMOVED_SYNTAX_ERROR: assert 'from app.agents.base.executor import BaseExecutionEngine' not in content, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

            # Also check for any reference to BaseExecutionEngine
            # REMOVED_SYNTAX_ERROR: if 'BaseExecutionEngine' in content and 'Removed BaseExecutionEngine' not in content:
                # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_websocket_modules_use_local_execution(self):
    # REMOVED_SYNTAX_ERROR: """Verify WebSocket modules use local execution patterns."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager

    # Verify execution_engine is None or local implementation
    # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()
    # WebSocketManager shouldn't have execution_engine attribute
    # REMOVED_SYNTAX_ERROR: assert not hasattr(manager, 'execution_engine'), \
    # REMOVED_SYNTAX_ERROR: "WebSocketManager should not use BaseExecutionEngine"

# REMOVED_SYNTAX_ERROR: def test_import_order_independence(self):
    # REMOVED_SYNTAX_ERROR: """Test that modules can be imported in any order."""
    # Clear any cached imports
    # REMOVED_SYNTAX_ERROR: modules_to_test = [ )
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.websocket_core',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.agents.base.executor',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.agents.supervisor_consolidated',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.services.agent_service_core'
    

    # Test forward order
    # REMOVED_SYNTAX_ERROR: for module in modules_to_test:
        # REMOVED_SYNTAX_ERROR: if module in sys.modules:
            # REMOVED_SYNTAX_ERROR: del sys.modules[module]

            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: for module in modules_to_test:
                    # REMOVED_SYNTAX_ERROR: importlib.import_module(module)
                    # REMOVED_SYNTAX_ERROR: except ImportError as e:
                        # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                        # Clear and test reverse order
                        # REMOVED_SYNTAX_ERROR: for module in modules_to_test:
                            # REMOVED_SYNTAX_ERROR: if module in sys.modules:
                                # REMOVED_SYNTAX_ERROR: del sys.modules[module]

                                # REMOVED_SYNTAX_ERROR: try:
                                    # REMOVED_SYNTAX_ERROR: for module in reversed(modules_to_test):
                                        # REMOVED_SYNTAX_ERROR: importlib.import_module(module)
                                        # REMOVED_SYNTAX_ERROR: except ImportError as e:
                                            # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_agent_registry_accessible_after_imports(self):
    # REMOVED_SYNTAX_ERROR: """Verify agent registry is accessible after all imports."""
    # Import in problematic order
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager

    # Verify classes are accessible
    # REMOVED_SYNTAX_ERROR: assert WebSocketManager is not None
    # REMOVED_SYNTAX_ERROR: assert SupervisorAgent is not None
    # REMOVED_SYNTAX_ERROR: assert AgentRegistry is not None

    # Verify registry can be instantiated
    # REMOVED_SYNTAX_ERROR: mock_llm = type('MockLLM', (), {})()
    # REMOVED_SYNTAX_ERROR: mock_dispatcher = type('MockDispatcher', (), {})()

    # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()
    # REMOVED_SYNTAX_ERROR: registry.register_default_agents()

    # Verify agents are registered
    # REMOVED_SYNTAX_ERROR: assert len(registry.list_agents()) >= 5, \
    # REMOVED_SYNTAX_ERROR: "Agent registry should have at least 5 default agents"

# REMOVED_SYNTAX_ERROR: def test_websocket_handler_without_execution_engine(self):
    # REMOVED_SYNTAX_ERROR: """Test WebSocket handlers work without BaseExecutionEngine."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import ( )
    # REMOVED_SYNTAX_ERROR: UserMessageHandler,
    

    # Create handler with required parameters
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import MessageType
    # REMOVED_SYNTAX_ERROR: handler = UserMessageHandler([MessageType.USER_MESSAGE])

    # Verify it doesn't have execution_engine or it's None
    # REMOVED_SYNTAX_ERROR: if hasattr(handler, 'execution_engine'):
        # REMOVED_SYNTAX_ERROR: assert handler.execution_engine is None, \
        # REMOVED_SYNTAX_ERROR: "Message handler should not use BaseExecutionEngine"

# REMOVED_SYNTAX_ERROR: def test_broadcast_executor_without_execution_engine(self):
    # REMOVED_SYNTAX_ERROR: """Test broadcast executor works without BaseExecutionEngine."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import ( )
    # REMOVED_SYNTAX_ERROR: WebSocketManager,
    

    # Create WebSocket manager instance
    # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()

    # Verify execution_engine is not present
    # REMOVED_SYNTAX_ERROR: assert not hasattr(manager, 'execution_engine'), \
    # REMOVED_SYNTAX_ERROR: "WebSocket manager should not use BaseExecutionEngine"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_message_flow_without_circular_dependency(self):
        # REMOVED_SYNTAX_ERROR: """Test message flow works after circular dependency fix."""

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_service_core import AgentService

        # Create mock supervisor
        # Mock: Generic component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: mock_supervisor = AsyncMock()  # TODO: Use real service instance
        # Mock: Async component isolation for testing without real async operations
        # REMOVED_SYNTAX_ERROR: mock_supervisor.run = AsyncMock(return_value="Test response")

        # Create agent service
        # REMOVED_SYNTAX_ERROR: service = AgentService(mock_supervisor)

        # Test message
        # REMOVED_SYNTAX_ERROR: message = { )
        # REMOVED_SYNTAX_ERROR: "type": "user_message",
        # REMOVED_SYNTAX_ERROR: "payload": {"content": "Test after circular fix"}
        

        # Process message
        # Mock: Component isolation for testing without external dependencies
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.ws_manager.manager'):
            # REMOVED_SYNTAX_ERROR: await service.handle_websocket_message( )
            # REMOVED_SYNTAX_ERROR: user_id="test_user",
            # REMOVED_SYNTAX_ERROR: message=message,
            # REMOVED_SYNTAX_ERROR: db_session=None
            

            # Verify supervisor was called
            # REMOVED_SYNTAX_ERROR: assert mock_supervisor.run.called, \
            # REMOVED_SYNTAX_ERROR: "Message should trigger supervisor execution after circular fix"

# REMOVED_SYNTAX_ERROR: class TestConnectionModuleCircularImportPrevention:
    # REMOVED_SYNTAX_ERROR: """Prevent regression of connection module circular import fixes."""

# REMOVED_SYNTAX_ERROR: def test_connection_manager_lazy_initialization(self):
    # REMOVED_SYNTAX_ERROR: '''Test that connection.py uses lazy initialization.

    # REMOVED_SYNTAX_ERROR: Business Value: Prevents import-time initialization causing circular deps.
    # REMOVED_SYNTAX_ERROR: Protects $50K+ MRR from WebSocket connection failures.
    # REMOVED_SYNTAX_ERROR: """"
    # Clear module cache
    # REMOVED_SYNTAX_ERROR: modules_to_clear = [ )
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.websocket_core',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.websocket_core.manager',
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.websocket_core.handlers'
    
    # REMOVED_SYNTAX_ERROR: for module in modules_to_clear:
        # REMOVED_SYNTAX_ERROR: if module in sys.modules:
            # REMOVED_SYNTAX_ERROR: del sys.modules[module]

            # Import connection module
            # Note: The connection module was removed in unified WebSocket architecture
            # These components are now part of WebSocketManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager, get_websocket_manager

            # Verify WebSocketManager can be imported without circular dependencies
            # REMOVED_SYNTAX_ERROR: assert WebSocketManager is not None, \
            # REMOVED_SYNTAX_ERROR: "WebSocketManager class must be importable"

            # Verify getter exists and works
            # REMOVED_SYNTAX_ERROR: assert callable(get_websocket_manager), \
            # REMOVED_SYNTAX_ERROR: "get_websocket_manager must be callable"

            # Test lazy getter returns instance
            # REMOVED_SYNTAX_ERROR: manager = get_websocket_manager()
            # REMOVED_SYNTAX_ERROR: assert manager is not None, "Lazy getter must return manager instance"

            # Verify singleton behavior
            # REMOVED_SYNTAX_ERROR: second_manager = get_websocket_manager()
            # REMOVED_SYNTAX_ERROR: assert second_manager is manager, "Should return same instance (singleton)"

# REMOVED_SYNTAX_ERROR: def test_connection_modules_import_independently(self):
    # REMOVED_SYNTAX_ERROR: '''Test each connection module imports independently.

    # REMOVED_SYNTAX_ERROR: Business Value: Ensures microservice independence per SPEC requirements.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: test_cases = [ )
    # These modules no longer exist in the unified WebSocket architecture
    # All functionality is now in websocket_core modules
    # REMOVED_SYNTAX_ERROR: ('netra_backend.app.websocket_core', ['WebSocketManager', 'get_websocket_manager']),
    # REMOVED_SYNTAX_ERROR: ('netra_backend.app.websocket_core.types', ['ConnectionInfo']),
    # REMOVED_SYNTAX_ERROR: ('netra_backend.app.websocket_core.manager', ['WebSocketManager'])
    

    # REMOVED_SYNTAX_ERROR: for module_name, expected_attrs in test_cases:
        # Clear module cache
        # REMOVED_SYNTAX_ERROR: if module_name in sys.modules:
            # REMOVED_SYNTAX_ERROR: del sys.modules[module_name]

            # REMOVED_SYNTAX_ERROR: try:
                # Import module in isolation
                # REMOVED_SYNTAX_ERROR: module = importlib.import_module(module_name)

                # Verify expected attributes exist
                # REMOVED_SYNTAX_ERROR: for attr in expected_attrs:
                    # REMOVED_SYNTAX_ERROR: assert hasattr(module, attr), \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # REMOVED_SYNTAX_ERROR: except ImportError as e:
                        # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")
                        # REMOVED_SYNTAX_ERROR: finally:
                            # Clean up
                            # REMOVED_SYNTAX_ERROR: if module_name in sys.modules:
                                # REMOVED_SYNTAX_ERROR: del sys.modules[module_name]

# REMOVED_SYNTAX_ERROR: def test_connection_backward_compatibility(self):
    # REMOVED_SYNTAX_ERROR: '''Test all legacy exports remain available.

    # REMOVED_SYNTAX_ERROR: Business Value: Prevents breaking changes in dependent services.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: from netra_backend.app import websocket_core

    # Core exports in the unified WebSocket architecture
    # Most legacy classes were consolidated or removed
    # REMOVED_SYNTAX_ERROR: core_exports = ['WebSocketManager', 'get_websocket_manager', 'ConnectionInfo']
    # REMOVED_SYNTAX_ERROR: for export in core_exports:
        # REMOVED_SYNTAX_ERROR: assert hasattr(websocket_core, export), \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: class TestIndirectCircularImportPrevention:
    # REMOVED_SYNTAX_ERROR: '''Test for indirect circular imports that manifest at runtime.

    # REMOVED_SYNTAX_ERROR: REGRESSION HISTORY:
        # REMOVED_SYNTAX_ERROR: - Date: 2025-08-21
        # REMOVED_SYNTAX_ERROR: - Issue: Indirect circular import: ws_manager → synthetic_data.error_handler →
        # REMOVED_SYNTAX_ERROR: synthetic_data → job_manager → ws_manager
        # REMOVED_SYNTAX_ERROR: - Impact: Tests couldn"t detect the circular dependency because it manifested
        # REMOVED_SYNTAX_ERROR: only during runtime initialization
        # REMOVED_SYNTAX_ERROR: - Fix: Use lazy imports in job_manager.py for WebSocket manager references
        # REMOVED_SYNTAX_ERROR: """"

# REMOVED_SYNTAX_ERROR: def test_no_websocket_manager_import_in_synthetic_data_modules(self):
    # REMOVED_SYNTAX_ERROR: '''Synthetic data modules should use lazy imports for WebSocket manager.

    # REMOVED_SYNTAX_ERROR: Business Value: Prevents $50K+ MRR loss from service initialization failures.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: import ast
    # REMOVED_SYNTAX_ERROR: import os

    # Modules that commonly create circular dependencies
    # REMOVED_SYNTAX_ERROR: synthetic_data_modules = [ )
    # REMOVED_SYNTAX_ERROR: 'app/services/synthetic_data/job_manager.py',
    # REMOVED_SYNTAX_ERROR: 'app/services/synthetic_data/job_operations.py',
    # REMOVED_SYNTAX_ERROR: 'app/services/synthetic_data/analytics_reporter.py',
    

    # REMOVED_SYNTAX_ERROR: for module_path in synthetic_data_modules:
        # REMOVED_SYNTAX_ERROR: full_path = os.path.join( )
        # REMOVED_SYNTAX_ERROR: os.path.dirname(__file__), '..', '..', module_path
        

        # REMOVED_SYNTAX_ERROR: if not os.path.exists(full_path):
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: with open(full_path, 'r') as f:
                # REMOVED_SYNTAX_ERROR: content = f.read()

                # Parse the AST to check for top-level ws_manager imports
                # REMOVED_SYNTAX_ERROR: tree = ast.parse(content)

                # REMOVED_SYNTAX_ERROR: for node in ast.walk(tree):
                    # REMOVED_SYNTAX_ERROR: if isinstance(node, ast.ImportFrom):
                        # Check for direct import of ws_manager at module level
                        # REMOVED_SYNTAX_ERROR: if (node.module and 'ws_manager' in node.module and )
                        # REMOVED_SYNTAX_ERROR: node.col_offset == 0):  # col_offset 0 = module level

                        # Allow TYPE_CHECKING imports
                        # REMOVED_SYNTAX_ERROR: is_type_checking = False
                        # REMOVED_SYNTAX_ERROR: for parent in ast.walk(tree):
                            # REMOVED_SYNTAX_ERROR: if (isinstance(parent, ast.If) and )
                            # REMOVED_SYNTAX_ERROR: isinstance(parent.test, ast.Name) and
                            # REMOVED_SYNTAX_ERROR: parent.test.id == 'TYPE_CHECKING'):
                                # REMOVED_SYNTAX_ERROR: if node in ast.walk(parent):
                                    # REMOVED_SYNTAX_ERROR: is_type_checking = True
                                    # REMOVED_SYNTAX_ERROR: break

                                    # REMOVED_SYNTAX_ERROR: if not is_type_checking:
                                        # REMOVED_SYNTAX_ERROR: pytest.fail( )
                                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: f"Use lazy imports inside methods or TYPE_CHECKING guard!"
                                        

# REMOVED_SYNTAX_ERROR: def test_websocket_to_synthetic_data_import_chain(self):
    # REMOVED_SYNTAX_ERROR: '''Test that WebSocket → Synthetic Data import chain doesn't create cycles.

    # REMOVED_SYNTAX_ERROR: Business Value: Ensures microservice independence per SPEC requirements.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: import importlib
    # REMOVED_SYNTAX_ERROR: import sys

    # Clear module cache for clean test
    # REMOVED_SYNTAX_ERROR: modules_to_clear = [ )
    # REMOVED_SYNTAX_ERROR: 'netra_backend.app.ws_manager',
    # REMOVED_SYNTAX_ERROR: 'app.services.synthetic_data.error_handler',
    # REMOVED_SYNTAX_ERROR: 'app.services.synthetic_data.job_manager',
    # REMOVED_SYNTAX_ERROR: 'app.services.synthetic_data_service',
    

    # REMOVED_SYNTAX_ERROR: for module in modules_to_clear:
        # REMOVED_SYNTAX_ERROR: if module in sys.modules:
            # REMOVED_SYNTAX_ERROR: del sys.modules[module]

            # Track import order to detect cycles
            # REMOVED_SYNTAX_ERROR: import_tracker = []
            # REMOVED_SYNTAX_ERROR: original_import = __builtins__.__import__

# REMOVED_SYNTAX_ERROR: def tracking_import(name, *args, **kwargs):
    # REMOVED_SYNTAX_ERROR: if 'netra_backend.app' in name:
        # REMOVED_SYNTAX_ERROR: import_tracker.append(name)

        # Check for cycles
        # REMOVED_SYNTAX_ERROR: if name in import_tracker[:-1]:
            # REMOVED_SYNTAX_ERROR: cycle_start = import_tracker.index(name)
            # REMOVED_SYNTAX_ERROR: cycle = import_tracker[cycle_start:]
            # REMOVED_SYNTAX_ERROR: pytest.fail( )
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            

            # REMOVED_SYNTAX_ERROR: return original_import(name, *args, **kwargs)

            # Temporarily replace import to track calls
            # REMOVED_SYNTAX_ERROR: __builtins__.__import__ = tracking_import

            # REMOVED_SYNTAX_ERROR: try:
                # Import in the problematic order
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services import synthetic_data_service
                # REMOVED_SYNTAX_ERROR: from netra_backend.app import ws_manager

                # If we get here, no circular import was detected
                # REMOVED_SYNTAX_ERROR: assert True, "No circular import detected"

                # REMOVED_SYNTAX_ERROR: finally:
                    # Restore original import
                    # REMOVED_SYNTAX_ERROR: __builtins__.__import__ = original_import

# REMOVED_SYNTAX_ERROR: def test_job_manager_lazy_imports(self):
    # REMOVED_SYNTAX_ERROR: '''Verify job_manager uses lazy imports for WebSocket manager.

    # REMOVED_SYNTAX_ERROR: Business Value: Prevents service startup failures worth $100K+ annual revenue.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: import os

    # REMOVED_SYNTAX_ERROR: job_manager_path = os.path.join( )
    # REMOVED_SYNTAX_ERROR: os.path.dirname(__file__),
    # REMOVED_SYNTAX_ERROR: '..', '..',
    # REMOVED_SYNTAX_ERROR: 'app/services/synthetic_data/job_manager.py'
    

    # REMOVED_SYNTAX_ERROR: with open(job_manager_path, 'r') as f:
        # REMOVED_SYNTAX_ERROR: content = f.read()

        # Check that ws_manager import is either:
            # 1. Inside TYPE_CHECKING block
            # 2. Inside method definitions (lazy)

            # REMOVED_SYNTAX_ERROR: lines = content.split('\n')
            # REMOVED_SYNTAX_ERROR: for i, line in enumerate(lines):
                # REMOVED_SYNTAX_ERROR: if 'from netra_backend.app.ws_manager import' in line or 'from app.services.websocket.ws_manager import' in line:
                    # Check indentation to ensure it's not at module level
                    # REMOVED_SYNTAX_ERROR: if line.startswith('from'):  # No indentation = module level
                    # Check if it's in TYPE_CHECKING block
                    # REMOVED_SYNTAX_ERROR: found_type_checking = False
                    # REMOVED_SYNTAX_ERROR: for j in range(max(0, i-5), i):
                        # REMOVED_SYNTAX_ERROR: if 'TYPE_CHECKING' in lines[j]:
                            # REMOVED_SYNTAX_ERROR: found_type_checking = True
                            # REMOVED_SYNTAX_ERROR: break

                            # REMOVED_SYNTAX_ERROR: if not found_type_checking:
                                # REMOVED_SYNTAX_ERROR: pytest.fail( )
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                # REMOVED_SYNTAX_ERROR: f"found outside TYPE_CHECKING. Use lazy imports!"
                                