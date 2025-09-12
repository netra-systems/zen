"""Test 1: MessageRouter SSOT Compliance Enforcement

This test detects multiple MessageRouter implementations and enforces Single Source of Truth.
It is designed to FAIL initially (4+ different router classes exist) and PASS after SSOT consolidation.

Business Value: Platform/Internal - System Stability & Golden Path Protection
- Protects $500K+ ARR chat functionality from configuration drift
- Prevents MessageRouter duplication causing connection failures
- Ensures single canonical routing implementation for reliability

EXPECTED BEHAVIOR:
- FAIL initially: Detects 4+ MessageRouter implementations across multiple modules
- PASS after SSOT remediation: Only 1 canonical MessageRouter in /netra_backend/app/websocket_core/handlers.py

GitHub Issue: #217 - MessageRouter SSOT violations blocking golden path
"""

import inspect
import os
import ast
import importlib.util
import unittest
from typing import Dict, List, Set, Optional, Any
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterSSOTEnforcement(SSotBaseTestCase, unittest.TestCase):
    """Test that enforces Single Source of Truth for MessageRouter implementations."""

    def setUp(self):
        """Set up test fixtures."""
        # Initialize SSotBaseTestCase (no super().setUp() needed)
        if hasattr(super(), 'setUp'):
            super().setUp()
        
        # Expected SSOT location after remediation
        self.canonical_path = "/netra_backend/app/websocket_core/handlers.py"
        self.base_path = Path(__file__).parent.parent.parent
        
        # Track multiple implementations
        self.discovered_routers: Dict[str, Dict[str, Any]] = {}
        self.violation_count = 0
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)

    def test_single_message_router_implementation_exists(self):
        """Test that only ONE MessageRouter implementation exists in the codebase.
        
        EXPECTED: FAIL initially - Multiple implementations detected
        EXPECTED: PASS after SSOT consolidation - Only canonical implementation exists
        """
        router_implementations = self._discover_message_router_implementations()
        
        # Log discovered implementations for debugging
        for file_path, details in router_implementations.items():
            self.logger.warning(
                f"MessageRouter implementation found: {file_path} - "
                f"Class: {details['class_name']}, Lines: {details['line_count']}"
            )
        
        # CRITICAL: This should FAIL initially with multiple implementations
        implementation_count = len(router_implementations)
        
        if implementation_count == 0:
            self.fail(
                "No MessageRouter implementations found! This indicates a scanning error "
                "or the router has been completely removed, breaking chat functionality."
            )
        elif implementation_count == 1:
            # Check if it's in the correct canonical location
            canonical_full_path = str(self.base_path / self.canonical_path.lstrip('/'))
            if canonical_full_path not in router_implementations:
                self.fail(
                    f"MessageRouter found in wrong location: {list(router_implementations.keys())[0]}. "
                    f"SSOT requires it to be in: {canonical_full_path}"
                )
            else:
                # SUCCESS: Single implementation in correct location
                self.logger.info(" PASS:  SSOT SUCCESS: Single MessageRouter implementation found in canonical location")
        else:
            # EXPECTED INITIAL FAILURE: Multiple implementations
            violation_details = self._format_ssot_violations(router_implementations)
            self.fail(
                f" FAIL:  SSOT VIOLATION: {implementation_count} MessageRouter implementations found. "
                f"Golden Path requires EXACTLY 1 in {self.canonical_path}.\n"
                f"BUSINESS IMPACT: Multiple routers cause WebSocket race conditions, "
                f"connection failures, and chat functionality breakdown affecting $500K+ ARR.\n"
                f"IMPLEMENTATIONS FOUND:\n{violation_details}"
            )

    def test_canonical_message_router_has_required_interface(self):
        """Test that canonical MessageRouter has the required interface methods.
        
        EXPECTED: FAIL initially if canonical router missing or incomplete
        EXPECTED: PASS after SSOT consolidation with complete interface
        """
        canonical_full_path = str(self.base_path / self.canonical_path.lstrip('/'))
        
        if not os.path.exists(canonical_full_path):
            self.fail(
                f" FAIL:  CANONICAL ROUTER MISSING: {canonical_full_path} does not exist. "
                f"Golden Path chat functionality requires canonical MessageRouter."
            )
        
        # Parse the canonical router to verify interface
        router_class = self._parse_message_router_class(canonical_full_path)
        
        if not router_class:
            self.fail(
                f" FAIL:  CANONICAL ROUTER INVALID: No MessageRouter class found in {canonical_full_path}"
            )
        
        # Required interface methods for golden path functionality
        required_methods = {
            '__init__',
            'add_handler', 
            'route_message',
            'handlers'  # property or method
        }
        
        found_methods = set(router_class.get('methods', []))
        missing_methods = required_methods - found_methods
        
        if missing_methods:
            self.fail(
                f" FAIL:  CANONICAL ROUTER INCOMPLETE: Missing required methods: {missing_methods}. "
                f"Chat functionality requires complete routing interface."
            )
        
        self.logger.info(f" PASS:  Canonical MessageRouter has complete interface: {found_methods}")

    def test_no_competing_router_factories_exist(self):
        """Test that no competing MessageRouter factory functions exist.
        
        EXPECTED: FAIL initially - Multiple factory patterns detected
        EXPECTED: PASS after SSOT consolidation - Single factory approach
        """
        router_factories = self._discover_message_router_factories()
        
        # Log discovered factories
        for factory_path, factory_info in router_factories.items():
            self.logger.warning(
                f"MessageRouter factory found: {factory_path} - Function: {factory_info['function_name']}"
            )
        
        if len(router_factories) > 1:
            factory_details = "\n".join([
                f"  - {path}: {info['function_name']}()" 
                for path, info in router_factories.items()
            ])
            self.fail(
                f" FAIL:  COMPETING FACTORIES DETECTED: {len(router_factories)} MessageRouter factories found.\n"
                f"SSOT requires single instantiation pattern.\n"
                f"FACTORIES FOUND:\n{factory_details}"
            )
        
        self.logger.info(" PASS:  No competing router factories detected")

    def test_message_router_import_consistency(self):
        """Test that all MessageRouter imports use consistent paths.
        
        EXPECTED: FAIL initially - Inconsistent import paths across codebase  
        EXPECTED: PASS after SSOT consolidation - All imports use canonical path
        """
        import_analysis = self._analyze_message_router_imports()
        
        unique_import_paths = set(import_analysis.keys())
        
        if len(unique_import_paths) > 1:
            import_details = "\n".join([
                f"  - {path}: used in {len(files)} files"
                for path, files in import_analysis.items()
            ])
            self.fail(
                f" FAIL:  IMPORT PATH INCONSISTENCY: {len(unique_import_paths)} different import paths found.\n"
                f"SSOT requires all imports to use canonical path: {self.canonical_path}\n"
                f"IMPORT PATHS FOUND:\n{import_details}"
            )
        
        # Check if imports are using the canonical path
        expected_import = "from netra_backend.app.websocket_core.handlers import MessageRouter"
        canonical_variations = [
            "netra_backend.app.websocket_core.handlers",
            "from netra_backend.app.websocket_core.handlers import MessageRouter",
            "from netra_backend.app.websocket_core.handlers import"
        ]
        
        if unique_import_paths and not any(canonical in list(unique_import_paths)[0] for canonical in canonical_variations):
            self.fail(
                f" FAIL:  NON-CANONICAL IMPORTS: Imports not using canonical path.\n"
                f"Expected: {expected_import}\n"
                f"Found: {list(unique_import_paths)}"
            )
        
        self.logger.info(" PASS:  MessageRouter imports are consistent")

    def _discover_message_router_implementations(self) -> Dict[str, Dict[str, Any]]:
        """Discover all MessageRouter class implementations in the codebase."""
        implementations = {}
        
        # Search Python files for MessageRouter class definitions
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for class definitions containing "MessageRouter"
                if 'class ' in content and 'MessageRouter' in content:
                    router_info = self._parse_message_router_class(str(py_file))
                    if router_info:
                        implementations[str(py_file)] = router_info
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return implementations

    def _discover_message_router_factories(self) -> Dict[str, Dict[str, Any]]:
        """Discover MessageRouter factory functions."""
        factories = {}
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for factory functions
                factory_patterns = [
                    'create_message_router',
                    'get_message_router', 
                    'make_message_router',
                    'MessageRouter_factory',
                    'build_message_router'
                ]
                
                for pattern in factory_patterns:
                    if f"def {pattern}" in content:
                        factories[str(py_file)] = {
                            'function_name': pattern,
                            'file_path': str(py_file)
                        }
                        break
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return factories

    def _analyze_message_router_imports(self) -> Dict[str, List[str]]:
        """Analyze MessageRouter import statements across the codebase."""
        import_analysis = {}
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for import statements containing MessageRouter
                lines = content.split('\n')
                for line_num, line in enumerate(lines):
                    if 'import' in line and 'MessageRouter' in line:
                        # Extract import path
                        if 'from ' in line:
                            # from module import MessageRouter
                            import_path = line.split('from ')[1].split(' import')[0].strip()
                        elif 'import ' in line and '.' in line:
                            # import module.MessageRouter
                            import_path = line.split('import ')[1].split('.MessageRouter')[0].strip()
                        else:
                            continue
                            
                        if import_path not in import_analysis:
                            import_analysis[import_path] = []
                        import_analysis[import_path].append(str(py_file))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return import_analysis

    def _parse_message_router_class(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a Python file to extract MessageRouter class information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and 'MessageRouter' in node.name:
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                            
                    return {
                        'class_name': node.name,
                        'file_path': file_path,
                        'line_number': node.lineno,
                        'methods': methods,
                        'line_count': len([n for n in ast.walk(node) if isinstance(n, ast.stmt)])
                    }
                    
        except (SyntaxError, UnicodeDecodeError):
            return None
            
        return None

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if a file should be skipped during scanning."""
        skip_patterns = [
            '__pycache__',
            '.git',
            '.pytest_cache', 
            'node_modules',
            '.venv',
            '.test_venv',
            'venv'
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _format_ssot_violations(self, implementations: Dict[str, Dict[str, Any]]) -> str:
        """Format SSOT violations for clear error reporting."""
        formatted = []
        for i, (file_path, details) in enumerate(implementations.items(), 1):
            # Make path relative for readability
            rel_path = file_path.replace(str(self.base_path), "").lstrip('/')
            formatted.append(
                f"{i}. {rel_path}\n"
                f"   Class: {details['class_name']}\n" 
                f"   Line: {details.get('line_number', 'unknown')}\n"
                f"   Methods: {len(details.get('methods', []))}"
            )
        return "\n".join(formatted)


if __name__ == "__main__":
    import unittest
    unittest.main()