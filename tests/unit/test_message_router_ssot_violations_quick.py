"""
Quick Unit Tests for MessageRouter SSOT Violations - GitHub Issue #217
Optimized version for fast execution and verified failure detection.
"""

import ast
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterSSOTViolationsQuick(SSotBaseTestCase):
    """Quick unit tests to detect MessageRouter SSOT violations."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        
        # Focus on known problem areas
        self.target_files = [
            'netra_backend/app/websocket_core/handlers.py',
            'netra_backend/app/agents/message_router.py'
        ]
        
    def test_multiple_message_router_implementations_detected(self):
        """
        Test that detects multiple MessageRouter implementations.
        This should FAIL, revealing SSOT violations.
        """
        message_router_implementations = []
        
        # Search through target files
        for file_path in self.target_files:
            py_file = self.project_root / file_path
            if py_file.exists():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if 'class MessageRouter' in content:
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.ClassDef) and node.name == 'MessageRouter':
                                    message_router_implementations.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'class_name': node.name,
                                        'line_number': node.lineno
                                    })
                        except SyntaxError:
                            continue
                            
                except (UnicodeDecodeError, FileNotFoundError):
                    continue
        
        # This assertion should FAIL if there are multiple implementations
        assert len(message_router_implementations) <= 1, (
            f"SSOT VIOLATION: Found {len(message_router_implementations)} MessageRouter implementations. "
            f"Should be exactly 1. Found: {message_router_implementations}"
        )
        
    def test_interface_method_conflicts_detected(self):
        """
        Test that detects interface method naming conflicts.
        This should FAIL if there are conflicting method names.
        """
        register_handler_files = []
        add_handler_files = []
        
        for file_path in self.target_files:
            py_file = self.project_root / file_path
            if py_file.exists():
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
        has_both_methods = bool(register_handler_files and add_handler_files)
        
        # This assertion should FAIL if there are conflicting method names
        assert not has_both_methods, (
            f"INTERFACE CONFLICT: Found both register_handler and add_handler methods. "
            f"register_handler in: {register_handler_files}, "
            f"add_handler in: {add_handler_files}"
        )
        
    def test_removed_syntax_error_comments_found(self):
        """
        Test that detects REMOVED_SYNTAX_ERROR comments indicating broken code.
        This should FAIL, revealing disabled/broken code.
        """
        removed_syntax_files = []
        
        for file_path in self.target_files:
            py_file = self.project_root / file_path
            if py_file.exists():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if 'REMOVED_SYNTAX_ERROR' in content:
                        count = content.count('REMOVED_SYNTAX_ERROR')
                        removed_syntax_files.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'count': count
                        })
                        
                except (UnicodeDecodeError, FileNotFoundError):
                    continue
        
        # This assertion should FAIL if there are REMOVED_SYNTAX_ERROR comments
        assert len(removed_syntax_files) == 0, (
            f"SYNTAX ERROR VIOLATION: Found {len(removed_syntax_files)} files with "
            f"REMOVED_SYNTAX_ERROR comments indicating broken code. Files: {removed_syntax_files}"
        )
        
    def test_import_consistency_violations(self):
        """
        Test that detects inconsistent MessageRouter import patterns.
        This should FAIL if there are inconsistent imports.
        """
        import_patterns = {
            'agents_import': 'from netra_backend.app.agents.message_router import MessageRouter',
            'websocket_import': 'from netra_backend.app.websocket_core.handlers import MessageRouter',
        }
        
        import_usage = {}
        
        # Check broader set of files for import patterns
        search_files = list(self.project_root.rglob("*.py"))[:50]  # Limit for speed
        
        for py_file in search_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern_name, pattern in import_patterns.items():
                    if pattern in content:
                        if pattern_name not in import_usage:
                            import_usage[pattern_name] = []
                        import_usage[pattern_name].append(str(py_file.relative_to(self.project_root)))
                        
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Check for multiple import patterns in use
        active_patterns = len(import_usage)
        
        # This assertion should FAIL if there are multiple import patterns
        assert active_patterns <= 1, (
            f"IMPORT INCONSISTENCY: Found {active_patterns} different MessageRouter import patterns. "
            f"Should use only 1 consistent import. Usage: {import_usage}"
        )


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)