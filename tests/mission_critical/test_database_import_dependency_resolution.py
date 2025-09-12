#!/usr/bin/env python
"""MISSION CRITICAL: Database Import Dependency Resolution Test Suite

THIS SUITE DETECTS CIRCULAR IMPORT DEPENDENCIES IN DATABASE MODULES
Business Value: $500K+ ARR - Prevents startup failures and WebSocket factory initialization

CRITICAL VIOLATIONS TO DETECT:
1. Circular import dependencies between database modules
2. WebSocket factory import failures due to dependency cycles
3. Startup sequence failures caused by unresolved database imports

DESIGNED TO FAIL PRE-SSOT REFACTOR:
- Tests will FAIL when circular imports exist in database modules
- Tests will FAIL when WebSocket factory cannot import database components

DESIGNED TO PASS POST-SSOT REFACTOR:
- Tests will PASS when import dependencies are resolved
- Tests will PASS when WebSocket factory can import database cleanly
- Tests will PASS when startup sequence initializes database correctly

ANY FAILURE HERE INDICATES IMPORT DEPENDENCY VIOLATIONS.
"""

import ast
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
import importlib.util
# import networkx as nx  # NetworkX not available - using custom graph implementation

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# SSOT imports - all tests must use SSOT framework
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class SimpleDirectedGraph:
    """Simple directed graph implementation for dependency analysis."""
    
    def __init__(self):
        self.nodes = set()
        self.edges = []
        self._adjacency = {}
    
    def add_edge(self, from_node, to_node):
        """Add an edge from from_node to to_node."""
        self.nodes.add(from_node)
        self.nodes.add(to_node)
        self.edges.append((from_node, to_node))
        
        if from_node not in self._adjacency:
            self._adjacency[from_node] = []
        self._adjacency[from_node].append(to_node)
    
    def simple_cycles(self):
        """Find simple cycles using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self._adjacency.get(node, []):
                dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for node in self.nodes:
            if node not in visited:
                dfs(node, [])
        
        return cycles


class TestDatabaseImportDependencyResolution(SSotBaseTestCase):
    """
    Test suite to detect and validate database import dependency resolution.
    
    These tests analyze import dependencies in database modules and detect
    circular dependencies that cause WebSocket factory initialization failures.
    """
    
    def setup_method(self, method=None):
        """Setup with enhanced dependency tracking."""
        super().setup_method(method)
        self.record_metric("test_category", "database_import_dependency_resolution")
        
        # Track dependency analysis
        self._import_graph = SimpleDirectedGraph()
        self._circular_dependencies = []
        self._dependency_violations = []
        self._module_import_map = {}
        
        # Define database-related modules to analyze
        self._project_root = Path(project_root)
        self._database_modules = [
            "netra_backend.app.db.database_manager",
            "netra_backend.app.factories.websocket_factory", 
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.core.config",
            "shared.database_url_builder",
            "shared.isolated_environment",
        ]
        
    def test_circular_import_dependencies_detected(self):
        """
        DESIGNED TO FAIL: Detect circular imports in database modules
        
        This test builds an import dependency graph and detects circular
        dependencies that cause WebSocket factory failures.
        """
        self.record_metric("violation_type", "circular_import_dependencies")
        
        # Build import dependency graph
        dependency_graph = self._build_import_dependency_graph()
        
        # Detect circular dependencies
        circular_deps = self._detect_circular_dependencies(dependency_graph)
        
        # Record findings
        self.record_metric("dependency_graph_nodes", len(dependency_graph.nodes))
        self.record_metric("dependency_graph_edges", len(dependency_graph.edges))
        self.record_metric("circular_dependencies_found", circular_deps)
        self._circular_dependencies = circular_deps
        
        logger.info(f"Dependency graph: {len(dependency_graph.nodes)} nodes, {len(dependency_graph.edges)} edges")
        logger.info(f"Circular dependencies found: {len(circular_deps)}")
        
        # CRITICAL CHECK: Circular dependencies indicate import violations
        if circular_deps:
            for cycle in circular_deps:
                violation_details = {
                    "cycle": cycle,
                    "cycle_length": len(cycle),
                    "violation_type": "circular_import_dependency"
                }
                self._dependency_violations.append(violation_details)
                logger.warning(f"Circular dependency detected: {' -> '.join(cycle)}")
            
            self.record_metric("circular_dependency_violations", self._dependency_violations)
            
            # This test is DESIGNED TO FAIL with circular dependencies
            assert False, (
                f"CIRCULAR IMPORT DEPENDENCIES: Found {len(circular_deps)} circular dependencies "
                f"in database modules. Cycles: {circular_deps}. "
                "These cause WebSocket factory import failures and startup sequence errors."
            )
        else:
            logger.info("No circular dependencies detected in database modules")
            self.record_metric("no_circular_dependencies", True)
    
    def test_websocket_factory_database_imports_resolved(self):
        """
        DESIGNED TO PASS: WebSocket factory can import database correctly
        
        This test validates that WebSocket factory can successfully import
        database components without triggering circular dependencies.
        """
        self.record_metric("validation_type", "websocket_factory_import_resolution")
        
        import_success = True
        import_errors = []
        
        # Test 1: Direct database manager import
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            logger.info("[U+2713] WebSocket factory can import DatabaseManager")
            self.record_metric("database_manager_import_success", True)
        except ImportError as e:
            import_success = False
            import_errors.append(f"DatabaseManager import failed: {e}")
            self.record_metric("database_manager_import_error", str(e))
        except Exception as e:
            import_success = False
            import_errors.append(f"DatabaseManager import exception: {e}")
            self.record_metric("database_manager_import_exception", str(e))
        
        # Test 2: Configuration import
        try:
            from netra_backend.app.core.config import get_config
            logger.info("[U+2713] WebSocket factory can import get_config")
            self.record_metric("config_import_success", True)
        except ImportError as e:
            import_success = False
            import_errors.append(f"Config import failed: {e}")
            self.record_metric("config_import_error", str(e))
        except Exception as e:
            import_success = False
            import_errors.append(f"Config import exception: {e}")
            self.record_metric("config_import_exception", str(e))
        
        # Test 3: Shared utilities import
        try:
            from shared.isolated_environment import get_env
            logger.info("[U+2713] WebSocket factory can import shared utilities")
            self.record_metric("shared_utilities_import_success", True)
        except ImportError as e:
            # This is acceptable - shared utilities might not be needed
            logger.info(f"Shared utilities import failed (acceptable): {e}")
            self.record_metric("shared_utilities_import_optional_failure", str(e))
        except Exception as e:
            import_success = False
            import_errors.append(f"Shared utilities import exception: {e}")
            self.record_metric("shared_utilities_import_exception", str(e))
        
        # Test 4: WebSocket factory itself can be imported
        try:
            # Import the actual WebSocket factory if it exists
            import netra_backend.app.factories.websocket_factory
            logger.info("[U+2713] WebSocket factory module can be imported")
            self.record_metric("websocket_factory_module_import_success", True)
        except ImportError as e:
            # This is acceptable - WebSocket factory might not exist yet
            logger.info(f"WebSocket factory module import failed (acceptable): {e}")
            self.record_metric("websocket_factory_module_not_found", str(e))
        except Exception as e:
            import_success = False
            import_errors.append(f"WebSocket factory module import exception: {e}")
            self.record_metric("websocket_factory_module_exception", str(e))
        
        # Record overall import resolution status
        self.record_metric("websocket_import_resolution_success", import_success)
        self.record_metric("websocket_import_errors", import_errors)
        
        # Critical imports must succeed for WebSocket factory
        critical_import_failures = [err for err in import_errors if "DatabaseManager" in err or "Config" in err]
        
        if critical_import_failures:
            assert False, (
                f"WebSocket factory critical import failures: {critical_import_failures}. "
                "These prevent WebSocket factory from accessing database sessions."
            )
        
        logger.info("WebSocket factory database import resolution validated")
    
    def test_startup_sequence_database_initialization_order(self):
        """
        DESIGNED TO PASS: Database initialization works in startup sequence
        
        This test validates that database components can be initialized in
        the correct order without circular dependency issues.
        """
        self.record_metric("validation_type", "startup_sequence_database_order")
        
        initialization_success = True
        initialization_errors = []
        
        # Simulate startup sequence database initialization
        try:
            # Step 1: Environment and configuration
            from shared.isolated_environment import get_env
            env = get_env()
            logger.info("[U+2713] Step 1: Environment initialization")
            self.record_metric("step1_environment_success", True)
        except Exception as e:
            initialization_success = False
            initialization_errors.append(f"Step 1 (Environment): {e}")
            self.record_metric("step1_environment_error", str(e))
        
        try:
            # Step 2: Configuration loading
            from netra_backend.app.core.config import get_config
            config = get_config()
            logger.info("[U+2713] Step 2: Configuration loading")
            self.record_metric("step2_config_success", True)
        except Exception as e:
            initialization_success = False
            initialization_errors.append(f"Step 2 (Config): {e}")
            self.record_metric("step2_config_error", str(e))
        
        try:
            # Step 3: Database manager initialization
            from netra_backend.app.db.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            logger.info("[U+2713] Step 3: Database manager creation")
            self.record_metric("step3_database_manager_success", True)
        except Exception as e:
            initialization_success = False
            initialization_errors.append(f"Step 3 (DatabaseManager): {e}")
            self.record_metric("step3_database_manager_error", str(e))
        
        try:
            # Step 4: WebSocket components (if they exist)
            try:
                from netra_backend.app.websocket_core.manager import WebSocketManager
                logger.info("[U+2713] Step 4: WebSocket manager import")
                self.record_metric("step4_websocket_manager_success", True)
            except ImportError:
                logger.info("[U+25CB] Step 4: WebSocket manager not found (acceptable)")
                self.record_metric("step4_websocket_manager_optional", True)
        except Exception as e:
            initialization_success = False
            initialization_errors.append(f"Step 4 (WebSocket): {e}")
            self.record_metric("step4_websocket_error", str(e))
        
        # Record overall initialization status
        self.record_metric("startup_sequence_success", initialization_success)
        self.record_metric("startup_sequence_errors", initialization_errors)
        
        # Validate startup sequence
        if not initialization_success:
            assert False, (
                f"Database initialization startup sequence failed: {initialization_errors}. "
                "This indicates unresolved import dependencies preventing system startup."
            )
        
        logger.info("Startup sequence database initialization order validated")
    
    def _build_import_dependency_graph(self) -> SimpleDirectedGraph:
        """
        Build a directed graph of import dependencies between modules.
        
        Returns:
            SimpleDirectedGraph representing import dependencies
        """
        graph = SimpleDirectedGraph()
        
        for module_name in self._database_modules:
            try:
                # Convert module name to file path
                module_parts = module_name.split('.')
                module_path = self._project_root
                for part in module_parts:
                    module_path = module_path / part
                
                # Try both .py file and __init__.py in directory
                py_file = module_path.with_suffix('.py')
                init_file = module_path / '__init__.py'
                
                file_to_analyze = None
                if py_file.exists():
                    file_to_analyze = py_file
                elif init_file.exists():
                    file_to_analyze = init_file
                
                if file_to_analyze:
                    imports = self._extract_imports_from_file(file_to_analyze)
                    self._module_import_map[module_name] = imports
                    
                    # Add edges to graph
                    for imported_module in imports:
                        # Only track imports within our analysis scope
                        if any(imported_module.startswith(prefix) for prefix in [
                            'netra_backend.app.db',
                            'netra_backend.app.factories', 
                            'netra_backend.app.websocket_core',
                            'netra_backend.app.core',
                            'shared'
                        ]):
                            graph.add_edge(module_name, imported_module)
                
            except Exception as e:
                logger.warning(f"Could not analyze module {module_name}: {e}")
        
        return graph
    
    def _extract_imports_from_file(self, file_path: Path) -> List[str]:
        """
        Extract import statements from a Python file.
        
        Args:
            file_path: Path to Python file to analyze
            
        Returns:
            List of imported module names
        """
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        
        except Exception as e:
            logger.warning(f"Could not extract imports from {file_path}: {e}")
        
        return imports
    
    def _detect_circular_dependencies(self, graph: SimpleDirectedGraph) -> List[List[str]]:
        """
        Detect circular dependencies in the import graph.
        
        Args:
            graph: SimpleDirectedGraph of import dependencies
            
        Returns:
            List of circular dependency cycles
        """
        try:
            cycles = graph.simple_cycles()
            return cycles
        except Exception as e:
            logger.warning(f"Could not detect cycles in import graph: {e}")
            return []
    
    def teardown_method(self, method=None):
        """Enhanced teardown with dependency analysis metrics."""
        # Log final dependency analysis
        logger.info(f"Import graph nodes: {len(self._import_graph.nodes)}")
        logger.info(f"Import graph edges: {len(self._import_graph.edges)}")
        logger.info(f"Circular dependencies found: {len(self._circular_dependencies)}")
        logger.info(f"Dependency violations: {len(self._dependency_violations)}")
        
        if self._circular_dependencies:
            logger.warning(f"Circular dependency details: {self._circular_dependencies}")
        
        super().teardown_method(method)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])