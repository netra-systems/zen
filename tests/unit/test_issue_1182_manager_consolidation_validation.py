"""
Issue #1182 Manager Consolidation Validation Tests

Tests to detect and validate WebSocket Manager SSOT violations including:
- 3 competing WebSocket manager implementations
- Import path fragmentation
- Initialization inconsistencies
- Cross-service manager boundaries

These tests should FAIL initially to prove SSOT violations exist.
"""

import pytest
import sys
import importlib
from pathlib import Path
from unittest.mock import patch
from typing import Dict, List, Set, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class Issue1182ManagerConsolidationValidationTests(SSotBaseTestCase):
    """Unit tests to detect WebSocket Manager SSOT violations"""

    def test_websocket_manager_competing_implementations_detected(self):
        """SHOULD FAIL: Detect 3 competing WebSocket manager implementations"""
        # Track all WebSocket manager implementations
        websocket_managers = {}
        
        # Check netra_backend implementation
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager as BackendManager
            websocket_managers['backend'] = {
                'module': 'netra_backend.app.websocket_core.manager',
                'class': BackendManager,
                'methods': set(dir(BackendManager))
            }
        except ImportError:
            pass
            
        # Check shared implementation
        try:
            from shared.websocket.manager import WebSocketManager as SharedManager
            websocket_managers['shared'] = {
                'module': 'shared.websocket.manager', 
                'class': SharedManager,
                'methods': set(dir(SharedManager))
            }
        except ImportError:
            pass
            
        # Check auth_service implementation
        try:
            from auth_service.websocket.manager import WebSocketManager as AuthManager
            websocket_managers['auth'] = {
                'module': 'auth_service.websocket.manager',
                'class': AuthManager, 
                'methods': set(dir(AuthManager))
            }
        except ImportError:
            pass
            
        # SSOT Violation Detection
        implementation_count = len(websocket_managers)
        
        # Log discovered implementations for debugging
        self.logger.info(f"WebSocket Manager implementations found: {implementation_count}")
        for service, details in websocket_managers.items():
            self.logger.info(f"  {service}: {details['module']}")
            
        # This should FAIL - proving SSOT violation exists
        assert implementation_count <= 1, (
            f"SSOT VIOLATION DETECTED: Found {implementation_count} WebSocket Manager implementations. "
            f"SSOT requires exactly 1. Found in: {list(websocket_managers.keys())}"
        )

    def test_websocket_manager_import_path_fragmentation(self):
        """SHOULD FAIL: Detect fragmented import paths for WebSocket manager"""
        import_paths_found = set()
        
        # Scan for different import patterns in actual codebase files
        websocket_imports = [
            "from netra_backend.app.websocket_core.manager import WebSocketManager",
            "from shared.websocket.manager import WebSocketManager", 
            "from auth_service.websocket.manager import WebSocketManager",
            "from netra_backend.app.websocket_core import manager as websocket_manager",
            "from shared.websocket import manager as websocket_manager",
            "import netra_backend.app.websocket_core.manager",
            "import shared.websocket.manager"
        ]
        
        # Check which imports actually work
        for import_statement in websocket_imports:
            try:
                # Execute import to see if path exists
                if import_statement.startswith("from"):
                    module_part = import_statement.split("from ")[1].split(" import")[0]
                    import_part = import_statement.split(" import ")[1]
                    mod = importlib.import_module(module_part)
                    if hasattr(mod, import_part):
                        import_paths_found.add(import_statement)
                elif import_statement.startswith("import"):
                    module_part = import_statement.split("import ")[1]
                    importlib.import_module(module_part)
                    import_paths_found.add(import_statement)
            except (ImportError, AttributeError):
                continue
                
        self.logger.info(f"Working WebSocket Manager import paths: {len(import_paths_found)}")
        for path in import_paths_found:
            self.logger.info(f"  {path}")
            
        # This should FAIL - proving import fragmentation exists
        assert len(import_paths_found) <= 1, (
            f"IMPORT FRAGMENTATION DETECTED: Found {len(import_paths_found)} working import paths. "
            f"SSOT requires exactly 1 canonical path. Paths: {import_paths_found}"
        )

    def test_websocket_manager_interface_consistency(self):
        """SHOULD FAIL: Detect interface inconsistencies between manager implementations"""
        managers = {}
        
        # Collect all available WebSocket manager classes
        manager_modules = [
            ('backend', 'netra_backend.app.websocket_core.manager', 'WebSocketManager'),
            ('shared', 'shared.websocket.manager', 'WebSocketManager'),
            ('auth', 'auth_service.websocket.manager', 'WebSocketManager'),
            ('demo_bridge', 'netra_backend.app.websocket_core.demo_websocket_bridge', 'DemoWebSocketBridge')
        ]
        
        for service, module_path, class_name in manager_modules:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    managers[service] = {
                        'class': cls,
                        'methods': set([m for m in dir(cls) if not m.startswith('_')]),
                        'module': module_path
                    }
            except ImportError:
                continue
                
        if len(managers) < 2:
            pytest.skip("Need at least 2 manager implementations to test interface consistency")
            
        # Analyze interface consistency
        method_sets = {service: details['methods'] for service, details in managers.items()}
        all_methods = set()
        for methods in method_sets.values():
            all_methods.update(methods)
            
        # Find methods that exist in some but not all implementations
        inconsistent_methods = []
        for method in all_methods:
            implementations_with_method = [service for service, methods in method_sets.items() if method in methods]
            if len(implementations_with_method) != len(managers):
                inconsistent_methods.append({
                    'method': method,
                    'implementations': implementations_with_method,
                    'missing_from': [service for service in managers.keys() if service not in implementations_with_method]
                })
                
        self.logger.info(f"Manager implementations found: {list(managers.keys())}")
        self.logger.info(f"Interface inconsistencies: {len(inconsistent_methods)}")
        
        # This should FAIL - proving interface inconsistencies exist
        assert len(inconsistent_methods) == 0, (
            f"INTERFACE INCONSISTENCY DETECTED: {len(inconsistent_methods)} methods have inconsistent implementations. "
            f"Examples: {inconsistent_methods[:3] if inconsistent_methods else 'None'}"
        )

    def test_websocket_manager_initialization_patterns(self):
        """SHOULD FAIL: Detect inconsistent initialization patterns"""
        initialization_patterns = {}
        
        # Check different initialization approaches
        patterns_to_check = [
            ('singleton', 'Singleton pattern initialization'),
            ('factory', 'Factory pattern initialization'), 
            ('direct_instantiation', 'Direct class instantiation'),
            ('dependency_injection', 'Dependency injection pattern')
        ]
        
        # Analyze WebSocket manager source code for initialization patterns
        manager_files = [
            'netra_backend/app/websocket_core/manager.py',
            'shared/websocket/manager.py',
            'auth_service/websocket/manager.py',
            'netra_backend/app/websocket_core/demo_websocket_bridge.py'
        ]
        
        pattern_indicators = {
            'singleton': ['_instance', 'getInstance', '__new__'],
            'factory': ['create_manager', 'get_manager', 'make_manager'],
            'direct_instantiation': ['WebSocketManager()', '__init__'],
            'dependency_injection': ['inject', 'provide', 'container']
        }
        
        for file_path in manager_files:
            full_path = Path(f"/Users/anthony/Desktop/netra-apex/{file_path}")
            if full_path.exists():
                try:
                    content = full_path.read_text()
                    file_patterns = set()
                    
                    for pattern_name, indicators in pattern_indicators.items():
                        if any(indicator in content for indicator in indicators):
                            file_patterns.add(pattern_name)
                            
                    if file_patterns:
                        initialization_patterns[file_path] = file_patterns
                except Exception as e:
                    self.logger.warning(f"Could not analyze {file_path}: {e}")
                    
        unique_patterns = set()
        for patterns in initialization_patterns.values():
            unique_patterns.update(patterns)
            
        self.logger.info(f"Initialization patterns found: {initialization_patterns}")
        self.logger.info(f"Unique patterns: {unique_patterns}")
        
        # This should FAIL - proving inconsistent initialization exists
        assert len(unique_patterns) <= 1, (
            f"INITIALIZATION INCONSISTENCY DETECTED: Found {len(unique_patterns)} different patterns. "
            f"SSOT requires consistent initialization. Patterns: {unique_patterns}"
        )

    def test_issue_1209_demo_websocket_bridge_interface_failure(self):
        """SHOULD FAIL: Specifically test Issue #1209 DemoWebSocketBridge interface failure"""
        try:
            from netra_backend.app.websocket_core.demo_websocket_bridge import DemoWebSocketBridge
            
            # Try to instantiate (this should reveal interface issues)
            try:
                bridge = DemoWebSocketBridge()
                
                # Test expected WebSocket manager interface methods
                required_methods = [
                    'send_event',
                    'broadcast_event', 
                    'connect',
                    'disconnect',
                    'get_connection_count'
                ]
                
                missing_methods = []
                for method in required_methods:
                    if not hasattr(bridge, method):
                        missing_methods.append(method)
                        
                # This should FAIL if interface is incomplete
                assert len(missing_methods) == 0, (
                    f"Issue #1209 REPRODUCED: DemoWebSocketBridge missing required methods: {missing_methods}"
                )
                
                # Test method signatures if methods exist
                if hasattr(bridge, 'send_event'):
                    # Try to call with expected signature
                    try:
                        # This might fail due to interface inconsistency
                        result = bridge.send_event("test_event", {"test": "data"}, "user_123")
                        self.logger.info(f"send_event call result: {result}")
                    except Exception as e:
                        assert False, f"Issue #1209 REPRODUCED: send_event interface failure: {str(e)}"
                        
            except Exception as e:
                assert False, f"Issue #1209 REPRODUCED: DemoWebSocketBridge instantiation failed: {str(e)}"
                
        except ImportError as e:
            pytest.skip(f"DemoWebSocketBridge not available for testing: {e}")

    def test_cross_service_manager_boundary_violations(self):
        """SHOULD FAIL: Detect managers being used across service boundaries"""
        import re
        
        # Define service boundaries
        service_boundaries = {
            'netra_backend': ['netra_backend/'],
            'auth_service': ['auth_service/'], 
            'shared': ['shared/'],
            'frontend': ['frontend/']
        }
        
        # Find WebSocket manager imports in each service
        boundary_violations = []
        
        for service, directories in service_boundaries.items():
            for directory in directories:
                dir_path = Path(f"/Users/anthony/Desktop/netra-apex/{directory}")
                if dir_path.exists():
                    # Find Python files
                    for py_file in dir_path.rglob("*.py"):
                        try:
                            content = py_file.read_text()
                            
                            # Look for WebSocket manager imports from other services
                            import_patterns = [
                                r'from\s+(\w+)\..*websocket.*manager.*import',
                                r'import\s+(\w+)\..*websocket.*manager'
                            ]
                            
                            for pattern in import_patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    imported_service = match
                                    if imported_service != service and imported_service in service_boundaries:
                                        boundary_violations.append({
                                            'file': str(py_file),
                                            'service': service,
                                            'imports_from': imported_service,
                                            'violation_type': 'cross_service_manager_import'
                                        })
                                        
                        except Exception as e:
                            self.logger.debug(f"Could not analyze {py_file}: {e}")
                            
        self.logger.info(f"Cross-service manager boundary violations: {len(boundary_violations)}")
        for violation in boundary_violations[:5]:  # Log first 5
            self.logger.info(f"  {violation}")
            
        # This should FAIL if cross-service usage exists
        assert len(boundary_violations) == 0, (
            f"CROSS-SERVICE BOUNDARY VIOLATIONS DETECTED: {len(boundary_violations)} violations found. "
            f"Services should use their own managers. Examples: {boundary_violations[:3]}"
        )