#!/usr/bin/env python3
"""
Unit test to validate UserExecutionContext import syntax in affected files.

This test validates Python AST parsing and import syntax for UserExecutionContext
in files identified in issue #502.

Expected behavior: FAIL initially (demonstrating syntax errors exist)
After fixes: PASS (validating syntax is correct)
"""

import ast
import os
import sys
import unittest
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestUserExecutionContextImportSyntax(unittest.TestCase):
    """Test syntax validation for UserExecutionContext imports in affected files."""
    
    def setUp(self):
        """Set up test with list of affected files from issue #502."""
        # Ensure we get the correct project root (should be the directory containing netra_backend/)
        current_file = Path(__file__)
        # Go up from tests/unit/syntax_validation/ to project root
        self.project_root = current_file.parent.parent.parent.parent
        
        # Validate we have the right project root
        if not (self.project_root / "netra_backend").exists():
            # Try alternative path resolution
            self.project_root = Path.cwd()
            if not (self.project_root / "netra_backend").exists():
                raise RuntimeError(f"Cannot find netra_backend directory. Tried {self.project_root}")
        
        print(f"Using project root: {self.project_root}")
        
        # Files identified in issue #502 with UserExecutionContext import syntax errors
        self.affected_files = [
            "netra_backend/app/agents/supervisor/agent_execution_core.py",
            "netra_backend/app/agents/supervisor/workflow_orchestrator.py", 
            "netra_backend/app/agents/supervisor/user_execution_engine.py",
            "netra_backend/app/agents/supervisor/agent_routing.py",
            "netra_backend/app/websocket_core/connection_executor.py",
            "netra_backend/app/websocket_core/unified_manager.py"
        ]
    
    def test_python_ast_parsing_success(self):
        """Test that all affected files can be parsed by Python AST."""
        parsing_failures = []
        
        for file_path in self.affected_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                self.fail(f"File does not exist: {full_path}")
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Attempt to parse the file content
                ast.parse(content, filename=str(full_path))
                
            except SyntaxError as e:
                parsing_failures.append({
                    'file': file_path,
                    'error': str(e),
                    'line': getattr(e, 'lineno', None),
                    'offset': getattr(e, 'offset', None),
                    'text': getattr(e, 'text', None)
                })
            except Exception as e:
                parsing_failures.append({
                    'file': file_path,
                    'error': f"Unexpected error: {str(e)}",
                    'line': None,
                    'offset': None,
                    'text': None
                })
        
        if parsing_failures:
            failure_msg = "Files failed AST parsing (syntax errors detected):\n"
            for failure in parsing_failures:
                failure_msg += f"\n  File: {failure['file']}"
                failure_msg += f"\n  Error: {failure['error']}"
                if failure['line']:
                    failure_msg += f"\n  Line: {failure['line']}"
                if failure['text']:
                    failure_msg += f"\n  Text: {failure['text'].strip()}"
                failure_msg += "\n"
            
            self.fail(failure_msg)
    
    def test_userexecutioncontext_import_attempt(self):
        """Test that UserExecutionContext can be imported from each file."""
        import_failures = []
        
        for file_path in self.affected_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
            
            # Convert file path to module path
            module_path = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
            
            try:
                # First check if file syntax is valid for compilation
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Try to compile the code
                compile(content, str(full_path), 'exec')
                
                # If compilation succeeds, try to import (if it has UserExecutionContext)
                if 'UserExecutionContext' in content:
                    # Attempt dynamic import
                    spec = None
                    try:
                        import importlib.util
                        spec = importlib.util.spec_from_file_location(
                            module_path.split('.')[-1], full_path
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                    except Exception as import_err:
                        import_failures.append({
                            'file': file_path,
                            'error': f"Import failed: {str(import_err)}",
                            'type': 'import_error'
                        })
                        
            except SyntaxError as e:
                import_failures.append({
                    'file': file_path,
                    'error': f"Syntax error prevents import: {str(e)}",
                    'type': 'syntax_error',
                    'line': getattr(e, 'lineno', None),
                    'text': getattr(e, 'text', None)
                })
            except Exception as e:
                import_failures.append({
                    'file': file_path,
                    'error': f"Compilation failed: {str(e)}",
                    'type': 'compilation_error'
                })
        
        if import_failures:
            failure_msg = "Files failed UserExecutionContext import validation:\n"
            for failure in import_failures:
                failure_msg += f"\n  File: {failure['file']}"
                failure_msg += f"\n  Type: {failure['type']}"
                failure_msg += f"\n  Error: {failure['error']}"
                if 'line' in failure and failure['line']:
                    failure_msg += f"\n  Line: {failure['line']}"
                if 'text' in failure and failure['text']:
                    failure_msg += f"\n  Text: {failure['text'].strip()}"
                failure_msg += "\n"
            
            self.fail(failure_msg)
    
    def test_specific_syntax_error_patterns(self):
        """Test for specific syntax error patterns mentioned in issue #502."""
        syntax_pattern_failures = []
        
        for file_path in self.affected_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Look for problematic import patterns
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Check for malformed UserExecutionContext imports
                    if 'UserExecutionContext' in line and 'import' in line:
                        # Look for potential syntax issues
                        if (line_stripped.endswith(',') and 
                            line_num < len(lines) and 
                            not lines[line_num].strip().startswith((')', 'from', 'import'))):
                            
                            syntax_pattern_failures.append({
                                'file': file_path,
                                'line': line_num,
                                'text': line_stripped,
                                'issue': 'Dangling comma in import'
                            })
                        
                        # Look for incomplete import statements
                        if line_stripped.endswith('import') and not line_stripped.startswith('#'):
                            syntax_pattern_failures.append({
                                'file': file_path,
                                'line': line_num,
                                'text': line_stripped,
                                'issue': 'Incomplete import statement'
                            })
                        
                        # Look for missing import completions
                        if ('from netra_backend.app.services.user_execution_context import' in line and 
                            not any(cls in line for cls in ['UserExecutionContext', 'UserContextManager'])):
                            syntax_pattern_failures.append({
                                'file': file_path,
                                'line': line_num,
                                'text': line_stripped,
                                'issue': 'Import from user_execution_context without specific class'
                            })
                            
            except Exception as e:
                syntax_pattern_failures.append({
                    'file': file_path,
                    'line': 0,
                    'text': '',
                    'issue': f'Failed to read file: {str(e)}'
                })
        
        if syntax_pattern_failures:
            failure_msg = "Specific syntax error patterns detected:\n"
            for failure in syntax_pattern_failures:
                failure_msg += f"\n  File: {failure['file']}"
                failure_msg += f"\n  Line: {failure['line']}"
                failure_msg += f"\n  Issue: {failure['issue']}"
                if failure['text']:
                    failure_msg += f"\n  Text: {failure['text']}"
                failure_msg += "\n"
            
            self.fail(failure_msg)


if __name__ == '__main__':
    unittest.main(verbosity=2)