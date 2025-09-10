"""
Unit Tests for MessageRouter SSOT Violations - GitHub Issue #217

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Code Quality
- Value Impact: Detect 14+ MessageRouter implementations violating SSOT
- Strategic Impact: Prevent cascade failures from inconsistent interfaces

These tests are designed to FAIL initially to reproduce the SSOT violation problem.
They will detect:
1. Multiple MessageRouter class definitions
2. Interface inconsistencies (register_handler vs add_handler)
3. REMOVED_SYNTAX_ERROR comments indicating broken code
4. Duplicate implementations across modules
"""

import os
import sys
import ast
import inspect
from typing import List, Dict, Set, Any
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterSSOTViolations(SSotBaseTestCase):
    """Unit tests to detect MessageRouter SSOT violations."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        self.python_files = list(self.project_root.rglob("*.py"))
        self.message_router_files = []
        self.interface_methods = set()
        self.message_router_implementations = []
        
    def test_discover_all_message_router_implementations(self):
        """
        Test that finds ALL MessageRouter class implementations.
        This test should FAIL initially, revealing 14+ implementations.
        """
        message_router_classes = []
        
        # Search through all Python files for MessageRouter class definitions
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and 'MessageRouter' in node.name:
                            message_router_classes.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'class_name': node.name,
                                'line_number': node.lineno,
                                'methods': [method.name for method in node.body 
                                          if isinstance(method, ast.FunctionDef)]
                            })
                except SyntaxError:
                    # Skip files with syntax errors
                    continue
                    
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Store findings for other tests
        self.message_router_implementations = message_router_classes
        
        # This assertion should FAIL, revealing the actual count
        self.assertLessEqual(
            len(message_router_classes), 1,
            f"SSOT VIOLATION: Found {len(message_router_classes)} MessageRouter implementations. "
            f"Should be exactly 1. Found in: {[impl['file'] for impl in message_router_classes]}"
        )
        
    def test_interface_consistency_violations(self):
        """
        Test that detects interface method inconsistencies.
        This should FAIL, revealing register_handler vs add_handler conflicts.
        """
        interface_violations = []
        
        # Check for conflicting method names across MessageRouter implementations
        register_handler_files = []
        add_handler_files = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'MessageRouter' in content:
                    if 'def register_handler' in content:
                        register_handler_files.append(str(py_file.relative_to(self.project_root)))
                    if 'def add_handler' in content:
                        add_handler_files.append(str(py_file.relative_to(self.project_root)))
                        
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Check for interface conflicts
        if register_handler_files and add_handler_files:
            interface_violations.append({
                'conflict': 'register_handler vs add_handler',
                'register_handler_files': register_handler_files,
                'add_handler_files': add_handler_files
            })
        
        # This assertion should FAIL, revealing interface inconsistencies
        self.assertEqual(
            len(interface_violations), 0,
            f"INTERFACE VIOLATION: Found conflicting method names. "
            f"Violations: {interface_violations}"
        )
        
    def test_removed_syntax_error_comments_detection(self):
        """
        Test that detects REMOVED_SYNTAX_ERROR comments.
        This should FAIL, revealing broken/disabled code.
        """
        removed_syntax_files = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'REMOVED_SYNTAX_ERROR' in content:
                    # Count occurrences
                    count = content.count('REMOVED_SYNTAX_ERROR')
                    removed_syntax_files.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'count': count
                    })
                    
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # This assertion should FAIL, revealing disabled code
        self.assertEqual(
            len(removed_syntax_files), 0,
            f"SYNTAX ERROR VIOLATION: Found {len(removed_syntax_files)} files with "
            f"REMOVED_SYNTAX_ERROR comments. Files: {removed_syntax_files}"
        )
        
    def test_ssot_compliance_detection(self):
        """
        Test that enforces SSOT compliance for MessageRouter.
        This should FAIL, revealing the need for consolidation.
        """
        # Gather all MessageRouter-related patterns
        violations = {
            'multiple_implementations': [],
            'import_inconsistencies': [],
            'duplicate_methods': []
        }
        
        # Check for multiple import sources
        import_patterns = [
            'from netra_backend.app.agents.message_router import MessageRouter',
            'from netra_backend.app.websocket_core.handlers import MessageRouter',
            'from netra_backend.app.services.websocket.quality_message_router import',
        ]
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for multiple import sources
                import_count = sum(1 for pattern in import_patterns if pattern in content)
                if import_count > 0:
                    violations['import_inconsistencies'].append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'import_count': import_count
                    })
                    
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # This assertion should FAIL, revealing SSOT violations
        total_violations = sum(len(v) for v in violations.values())
        self.assertEqual(
            total_violations, 0,
            f"SSOT VIOLATION: Found {total_violations} total violations. "
            f"Details: {violations}"
        )
        
    def test_websocket_routing_stability_indicators(self):
        """
        Test that checks for indicators of WebSocket routing instability.
        This should FAIL, revealing instability patterns.
        """
        instability_indicators = []
        
        # Patterns that indicate routing instability
        unstable_patterns = [
            'try:.*import.*MessageRouter',
            'except.*MessageRouter',
            '# TODO.*MessageRouter',
            '# FIXME.*MessageRouter',
            'MessageRouter.*# HACK',
            'MessageRouter.*# WORKAROUND'
        ]
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in unstable_patterns:
                    if any(keyword in content for keyword in pattern.split('.*')):
                        instability_indicators.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'pattern': pattern,
                            'context': 'MessageRouter routing instability'
                        })
                        
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # This assertion should FAIL, revealing instability
        self.assertEqual(
            len(instability_indicators), 0,
            f"INSTABILITY DETECTED: Found {len(instability_indicators)} indicators of "
            f"WebSocket routing instability. Indicators: {instability_indicators}"
        )


if __name__ == "__main__":
    # Run the tests to see the failures
    import unittest
    unittest.main(verbosity=2)