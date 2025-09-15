"""Test: MessageRouter SSOT Compliance Validation (MISSION CRITICAL)

This test verifies Single Source of Truth compliance for MessageRouter implementations.
It is designed to FAIL initially (4+ different router classes exist) and PASS after SSOT consolidation.

Business Value: Platform/Internal - System Stability & Golden Path Protection
- Protects $500K+ ARR chat functionality from configuration drift
- Prevents MessageRouter duplication causing connection failures
- Ensures single canonical routing implementation for reliability

EXPECTED BEHAVIOR:
- FAIL initially: Detects 4+ MessageRouter implementations across multiple modules
- PASS after SSOT remediation: Only 1 canonical MessageRouter in websocket_core/handlers.py

GitHub Issue: #1077 - MessageRouter SSOT violations blocking golden path
"""

import os
import ast
import importlib.util
from typing import Dict, List, Set, Optional, Any
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterSSOTCompliance(SSotBaseTestCase):
    """Test that verifies Single Source of Truth for MessageRouter implementations."""

    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        # Initialize SSotBaseTestCase (no super().setUp() needed)
        if hasattr(super(), 'setUp'):
            super().setUp()
        
        # Expected SSOT location after remediation
        self.canonical_path = "netra_backend/app/websocket_core/handlers.py"
        self.canonical_class = "MessageRouter"
        self.base_path = Path(__file__).parent.parent.parent
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)

    def test_single_message_router_exists(self):
        """Verify only one MessageRouter implementation exists."""
        # Attempt to import the canonical MessageRouter
        canonical_router = None
        canonical_import_error = None
        
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter as CoreMessageRouter
            canonical_router = CoreMessageRouter
        except ImportError as e:
            canonical_import_error = e
        
        # Check if canonical router exists and is functional
        if canonical_router is None:
            self.fail(
                f"CANONICAL ROUTER MISSING: Cannot import MessageRouter from {self.canonical_path}. "
                f"Import error: {canonical_import_error}. "
                f"Golden Path chat functionality requires canonical router."
            )
        
        # Verify the canonical router has required interface
        required_methods = {'add_handler', 'route_message', 'handlers'}
        missing_methods = []
        
        for method in required_methods:
            if not hasattr(canonical_router, method):
                missing_methods.append(method)
        
        if missing_methods:
            self.fail(
                f"CANONICAL ROUTER INCOMPLETE: Missing required methods: {missing_methods}. "
                f"Chat functionality requires complete routing interface."
            )
        
        self.logger.info("✓ Canonical MessageRouter found and has required interface")

    def test_agent_compatibility_import(self):
        """Verify the compatibility import works correctly."""
        try:
            from netra_backend.app.agents.message_router import MessageRouter as AgentRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter as CoreRouter
            
            # Verify they are the same class
            self.assertIs(
                AgentRouter, CoreRouter,
                "Compatibility import should return the same MessageRouter class"
            )
            
        except ImportError as e:
            self.fail(f"COMPATIBILITY IMPORT BROKEN: {e}")
        
        self.logger.info("✓ Agent compatibility import working correctly")

    def test_message_router_interface_works(self):
        """Test that the MessageRouter interface works as expected."""
        try:
            from netra_backend.app.websocket_core.handlers import get_message_router
            
            router = get_message_router()
            
            # Test that we can get the router instance
            self.assertIsNotNone(router, "get_message_router() should return a router instance")
            
            # Test that router has expected methods
            self.assertTrue(hasattr(router, 'add_handler'), "Router should have add_handler method")
            self.assertTrue(hasattr(router, 'route_message'), "Router should have route_message method")
            self.assertTrue(hasattr(router, 'handlers'), "Router should have handlers property")
            
            # Test that handlers property is accessible
            handlers = router.handlers
            self.assertIsInstance(handlers, (list, tuple, dict), "Handlers should be a collection")
            
        except ImportError as e:
            self.fail(f"ROUTER INTERFACE BROKEN: Cannot import router functions: {e}")
        except Exception as e:
            self.fail(f"ROUTER INTERFACE ERROR: {e}")
        
        self.logger.info("✓ MessageRouter interface working correctly")

    def test_no_duplicate_message_router_imports(self):
        """Verify no imports try to use old/duplicate MessageRouter locations."""
        import re
        
        # Pattern for old/problematic imports
        old_import_patterns = [
            r'from netra_backend\.app\.services\.websocket\.message_router import MessageRouter',
            r'from netra_backend\.app\.services\.websocket_event_router import MessageRouter',
            r'from netra_backend\.app\.services\.user_scoped_websocket_event_router import MessageRouter',
        ]
        
        duplicate_imports = []
        
        # Search through Python files
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in old_import_patterns:
                    if re.search(pattern, content):
                        rel_path = py_file.relative_to(self.base_path)
                        duplicate_imports.append(str(rel_path))
                        break
                        
            except (UnicodeDecodeError, IOError):
                continue
        
        if duplicate_imports:
            self.fail(
                f"DUPLICATE IMPORTS DETECTED: {len(duplicate_imports)} files using old MessageRouter imports.\n"
                f"Files with problematic imports:\n" + 
                "\n".join(f"  - {path}" for path in duplicate_imports[:10]) + 
                ("\n  ..." if len(duplicate_imports) > 10 else "")
            )
        
        self.logger.info("✓ No duplicate MessageRouter imports detected")

    def test_websocket_integration_uses_correct_router(self):
        """Test that WebSocket integration uses the correct MessageRouter."""
        try:
            from netra_backend.app.websocket_core.handlers import get_message_router
            
            router = get_message_router()
            
            # Test that router instance is accessible
            self.assertIsNotNone(router, "WebSocket integration should have router instance")
            
            # Test that router has handlers (basic integration check)
            if hasattr(router, 'handlers'):
                handlers = router.handlers
                # Just check that handlers exist, don't enforce specific ones
                # since different environments may have different handler configurations
                self.assertIsNotNone(handlers, "Router should have handlers configured")
            
        except ImportError as e:
            self.fail(f"WEBSOCKET INTEGRATION BROKEN: Cannot access router: {e}")
        except Exception as e:
            self.fail(f"WEBSOCKET INTEGRATION ERROR: {e}")
        
        self.logger.info("✓ WebSocket integration using correct router")

    def test_no_competing_message_router_classes(self):
        """Test that no competing MessageRouter class definitions exist."""
        router_classes_found = []
        
        # Search for class definitions named MessageRouter
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Simple check for class MessageRouter definitions
                if 'class MessageRouter' in content:
                    # Parse AST to confirm it's actually a class definition
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if (isinstance(node, ast.ClassDef) and 
                                node.name == 'MessageRouter'):
                                rel_path = py_file.relative_to(self.base_path)
                                router_classes_found.append({
                                    'file': str(rel_path),
                                    'line': node.lineno,
                                    'class': node.name
                                })
                    except SyntaxError:
                        # Skip files with syntax errors
                        continue
                        
            except (UnicodeDecodeError, IOError):
                continue
        
        # Filter out the canonical router
        canonical_rel_path = str(Path(self.canonical_path))
        competing_routers = [
            router for router in router_classes_found 
            if router['file'] != canonical_rel_path
        ]
        
        if competing_routers:
            competing_summary = "\n".join([
                f"  - {router['file']} (line {router['line']}): {router['class']}"
                for router in competing_routers
            ])
            self.fail(
                f"COMPETING ROUTER CLASSES DETECTED: {len(competing_routers)} additional MessageRouter classes found.\n"
                f"SSOT violation: Only canonical router allowed in {canonical_rel_path}.\n"
                f"COMPETING CLASSES:\n{competing_summary}"
            )
        
        # Verify canonical router exists
        canonical_found = any(
            router['file'] == canonical_rel_path 
            for router in router_classes_found
        )
        
        if not canonical_found:
            self.fail(
                f"CANONICAL ROUTER MISSING: No MessageRouter class found in {canonical_rel_path}. "
                f"Golden Path requires canonical router."
            )
        
        self.logger.info("✓ Only canonical MessageRouter class exists")

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if a file should be skipped during scanning."""
        skip_patterns = [
            '__pycache__',
            '.git',
            '.pytest_cache',
            'node_modules',
            '.venv',
            '.test_venv',
            'venv',
            'backups',
            '.baselines'
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)


if __name__ == "__main__":
    print("Running MessageRouter SSOT compliance tests...")
    import pytest
    pytest.main([__file__, '-v'])