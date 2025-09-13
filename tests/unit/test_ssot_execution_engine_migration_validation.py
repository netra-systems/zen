"""Unit Test: SSOT ExecutionEngine Migration Status Validation (Issue #620)

PURPOSE: Validate that the ExecutionEngine SSOT migration is properly completed.
This test reproduces the current failing behavior where deprecated files are still 1,664+ lines instead of 5-line redirects.

BUSINESS CONTEXT:
- Chat functionality delivers 90% of platform value
- ExecutionEngine is core infrastructure enabling agent WebSocket events  
- Migration status directly impacts system stability and user isolation

TEST STRATEGY:
- FAILING TESTS FIRST: Reproduce the broken migration state
- File size validation: Deprecated files should be ≤5 lines (currently 1,664+ lines)
- Import validation: All imports should resolve to UserExecutionEngine
- Content validation: Deprecated files should be redirects, not full implementations

EXPECTED CURRENT STATE (FAILING):
- execution_engine.py: 1,775 lines (should be ≤5 lines) 
- Multiple deprecated files still contain full implementations
- Import consolidation incomplete (60% complete per Issue #620)

TEST EXECUTION:
- Unit test (no Docker dependency)
- Fast execution for immediate feedback
- Real file system validation
"""

import os
import ast
import importlib.util
import inspect
import pytest
from pathlib import Path
from typing import List, Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestSSotExecutionEngineMigrationValidation(SSotBaseTestCase):
    """Unit tests for ExecutionEngine SSOT migration validation.
    
    These tests SHOULD FAIL initially to reproduce the current broken migration state.
    When the migration is complete, these tests will pass.
    """
    
    def setup_method(self, method):
        """Set up test environment for ExecutionEngine migration validation."""
        super().setup_method(method)
        
        self.project_root = Path(__file__).parent.parent.parent
        self.netra_backend = self.project_root / "netra_backend"
        
        # Define ExecutionEngine related files that should be deprecated redirects
        self.deprecated_execution_engine_files = [
            self.netra_backend / "app" / "agents" / "supervisor" / "execution_engine.py",
            # Add other deprecated ExecutionEngine files here as identified
        ]
        
        # Define the SSOT UserExecutionEngine file
        self.ssot_user_execution_engine = self.netra_backend / "app" / "agents" / "supervisor" / "user_execution_engine.py"
        
        # Current known failing state from Issue #620 audit
        self.expected_failing_line_counts = {
            "execution_engine.py": 1775,  # Currently 1,775 lines, should be ≤5
        }
        
    def test_deprecated_execution_engine_file_size_validation(self):
        """Test that deprecated ExecutionEngine files are 5-line redirects.
        
        EXPECTED TO FAIL: This test reproduces the Issue #620 finding that
        deprecated files are still full implementations (1,664+ lines) instead of redirects.
        
        SUCCESS CRITERIA (when migration is complete):
        - All deprecated files ≤ 5 lines
        - Files contain only imports and redirects
        - No business logic in deprecated files
        """
        failing_files = []
        
        for file_path in self.deprecated_execution_engine_files:
            if not file_path.exists():
                pytest.fail(f"Expected deprecated file does not exist: {file_path}")
                continue
            
            # Count lines in the file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                line_count = len(lines)
                
            # Log current state for debugging
            filename = file_path.name
            expected_failing_count = self.expected_failing_line_counts.get(filename, 0)
            
            print(f"\n📊 MIGRATION STATUS CHECK: {filename}")
            print(f"   Current lines: {line_count}")
            print(f"   Expected failing state: {expected_failing_count} lines") 
            print(f"   Target state: ≤5 lines (redirect only)")
            
            # REPRODUCTION TEST: Validate current failing state
            if expected_failing_count > 0:
                if line_count != expected_failing_count:
                    print(f"   ⚠️  WARNING: Expected {expected_failing_count} lines but found {line_count}")
                else:
                    print(f"   ✅ REPRODUCTION: Confirmed current failing state ({line_count} lines)")
            
            # PRIMARY TEST: Check if file is properly migrated (≤5 lines)
            if line_count > 5:
                failing_files.append({
                    'file': filename,
                    'current_lines': line_count,
                    'target_lines': '≤5',
                    'status': 'MIGRATION_INCOMPLETE',
                    'migration_issue': '#620'
                })
        
        # Assert failure to reproduce current broken state
        if failing_files:
            failure_details = [
                f"{f['file']}: {f['current_lines']} lines (should be {f['target_lines']})"
                for f in failing_files
            ]
            
            pytest.fail(
                f"🚨 ISSUE #620 REPRODUCTION: ExecutionEngine SSOT migration incomplete (60%). "
                f"Deprecated files are still full implementations instead of 5-line redirects:\n"
                f"{'  • ' + chr(10).join(failure_details)}\n"
                f"\nBUSINESS IMPACT: "
                f"User isolation vulnerabilities, chat functionality instability, "
                f"WebSocket event delivery issues affecting 90% of platform value.\n"
                f"\nREMEDIATION: Complete SSOT migration by converting deprecated files to redirects."
            )
    
    def test_deprecated_execution_engine_content_validation(self):
        """Test that deprecated ExecutionEngine files contain only redirects.
        
        EXPECTED TO FAIL: Deprecated files should contain only imports and redirects
        to UserExecutionEngine, but currently contain full business logic.
        
        SUCCESS CRITERIA (when migration is complete):
        - No class definitions in deprecated files
        - No method implementations in deprecated files  
        - Only import statements and redirect functions
        """
        failing_files = []
        
        for file_path in self.deprecated_execution_engine_files:
            if not file_path.exists():
                continue
                
            # Parse file AST to analyze content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Parse AST to analyze file structure
                tree = ast.parse(file_content, filename=str(file_path))
                
                # Count different types of nodes
                class_definitions = []
                method_definitions = []
                import_statements = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_definitions.append(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        method_definitions.append(node.name)
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        import_statements.append(self._format_import(node))
                
                filename = file_path.name
                
                print(f"\n📋 CONTENT ANALYSIS: {filename}")
                print(f"   Classes found: {len(class_definitions)}")
                print(f"   Methods found: {len(method_definitions)}")
                print(f"   Imports found: {len(import_statements)}")
                
                if class_definitions:
                    print(f"   Class names: {', '.join(class_definitions[:3])}{'...' if len(class_definitions) > 3 else ''}")
                
                # FAILURE TEST: Check for business logic (classes/methods)
                if class_definitions or method_definitions:
                    failing_files.append({
                        'file': filename,
                        'classes': len(class_definitions),
                        'methods': len(method_definitions),
                        'imports': len(import_statements),
                        'status': 'CONTAINS_BUSINESS_LOGIC',
                        'migration_issue': '#620'
                    })
                    
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {file_path}: {e}")
            except Exception as e:
                pytest.fail(f"Error analyzing {file_path}: {e}")
        
        # Assert failure to reproduce current state  
        if failing_files:
            failure_details = []
            for f in failing_files:
                failure_details.append(
                    f"{f['file']}: {f['classes']} classes, {f['methods']} methods "
                    f"(should be 0 classes, 0 methods - redirect only)"
                )
            
            pytest.fail(
                f"🚨 ISSUE #620 CONTENT REPRODUCTION: Deprecated ExecutionEngine files "
                f"contain full business logic instead of simple redirects:\n"
                f"{'  • ' + chr(10).join(failure_details)}\n"
                f"\nEXPECTED STATE: Only import statements and redirect functions\n"
                f"CURRENT STATE: Full class implementations with business logic\n"
                f"\nBUSINESS RISK: Code duplication, maintenance burden, user isolation bugs"
            )
    
    def test_ssot_user_execution_engine_exists_and_complete(self):
        """Test that the SSOT UserExecutionEngine exists and is properly implemented.
        
        This test should PASS as UserExecutionEngine is the consolidation target.
        """
        if not self.ssot_user_execution_engine.exists():
            pytest.fail(f"SSOT UserExecutionEngine file does not exist: {self.ssot_user_execution_engine}")
        
        # Count lines in SSOT file
        with open(self.ssot_user_execution_engine, 'r', encoding='utf-8') as f:
            ssot_lines = len(f.readlines())
        
        print(f"\n📈 SSOT STATUS: user_execution_engine.py")
        print(f"   Lines: {ssot_lines}")
        print(f"   Status: {'✅ SUBSTANTIAL IMPLEMENTATION' if ssot_lines > 100 else '⚠️  TOO SMALL'}")
        
        # SSOT should be substantial (contains all consolidated functionality)
        assert ssot_lines > 100, (
            f"SSOT UserExecutionEngine appears incomplete: only {ssot_lines} lines. "
            f"Expected substantial implementation with consolidated functionality."
        )
        
        # Verify SSOT contains expected classes/methods
        try:
            with open(self.ssot_user_execution_engine, 'r', encoding='utf-8') as f:
                ssot_content = f.read()
            
            tree = ast.parse(ssot_content)
            class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            print(f"   Classes: {', '.join(class_names)}")
            
            # Should contain UserExecutionEngine class
            assert 'UserExecutionEngine' in class_names, (
                f"SSOT file missing UserExecutionEngine class. Found classes: {class_names}"
            )
            
        except Exception as e:
            pytest.fail(f"Error analyzing SSOT UserExecutionEngine: {e}")
    
    def test_execution_engine_import_resolution(self):
        """Test that ExecutionEngine imports resolve correctly.
        
        EXPECTED TO PARTIALLY FAIL: Should demonstrate import consolidation issues.
        
        This test checks that imports from deprecated locations either:
        1. Resolve to UserExecutionEngine (successful migration)  
        2. Fail with clear migration guidance (partial migration)
        """
        import_tests = [
            {
                'import_path': 'netra_backend.app.agents.supervisor.execution_engine.ExecutionEngine',
                'expected_resolution': 'UserExecutionEngine',
                'test_type': 'deprecated_import'
            },
            {
                'import_path': 'netra_backend.app.agents.supervisor.user_execution_engine.UserExecutionEngine', 
                'expected_resolution': 'UserExecutionEngine',
                'test_type': 'ssot_import'
            }
        ]
        
        import_results = []
        
        for test in import_tests:
            try:
                # Dynamic import to test resolution
                module_path, class_name = test['import_path'].rsplit('.', 1)
                spec = importlib.util.spec_from_file_location(
                    module_path,
                    self._get_module_file_path(module_path)
                )
                
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, class_name):
                        actual_class = getattr(module, class_name)
                        actual_resolution = actual_class.__name__
                        
                        import_results.append({
                            'import_path': test['import_path'],
                            'expected': test['expected_resolution'],
                            'actual': actual_resolution,
                            'test_type': test['test_type'],
                            'status': 'SUCCESS' if actual_resolution == test['expected_resolution'] else 'MISMATCH',
                            'class_info': {
                                'module': actual_class.__module__,
                                'qualname': actual_class.__qualname__,
                                'is_deprecated': hasattr(actual_class, '_compatibility_mode')
                            }
                        })
                    else:
                        import_results.append({
                            'import_path': test['import_path'],
                            'expected': test['expected_resolution'],
                            'actual': 'CLASS_NOT_FOUND',
                            'test_type': test['test_type'],
                            'status': 'FAILURE'
                        })
                else:
                    import_results.append({
                        'import_path': test['import_path'],
                        'expected': test['expected_resolution'],
                        'actual': 'MODULE_NOT_FOUND',
                        'test_type': test['test_type'],
                        'status': 'FAILURE'
                    })
                    
            except Exception as e:
                import_results.append({
                    'import_path': test['import_path'],
                    'expected': test['expected_resolution'],
                    'actual': f'ERROR: {str(e)[:100]}',
                    'test_type': test['test_type'],
                    'status': 'ERROR'
                })
        
        # Print import resolution analysis
        print(f"\n🔍 IMPORT RESOLUTION ANALYSIS:")
        for result in import_results:
            status_emoji = "✅" if result['status'] == 'SUCCESS' else "❌" if result['status'] == 'FAILURE' else "⚠️"
            print(f"   {status_emoji} {result['test_type']}: {result['import_path']}")
            print(f"      Expected: {result['expected']}, Actual: {result['actual']}")
            
            if 'class_info' in result:
                print(f"      Module: {result['class_info']['module']}")
                if result['class_info'].get('is_deprecated'):
                    print(f"      ⚠️  COMPATIBILITY MODE: Using deprecated compatibility bridge")
        
        # Check for migration issues
        failed_imports = [r for r in import_results if r['status'] in ['FAILURE', 'ERROR']]
        deprecated_active = [r for r in import_results 
                           if r.get('class_info', {}).get('is_deprecated', False)]
        
        if failed_imports:
            failure_details = [f"{r['import_path']}: {r['actual']}" for r in failed_imports]
            print(f"\n⚠️  IMPORT FAILURES: {len(failed_imports)} import resolution failures detected")
        
        if deprecated_active:
            print(f"\n⚠️  COMPATIBILITY MODE: {len(deprecated_active)} imports using compatibility bridge")
            print("   Migration incomplete - deprecated code paths still active")
        
        # This test primarily documents current state, but fails if core functionality broken
        if any(r['test_type'] == 'ssot_import' and r['status'] != 'SUCCESS' for r in import_results):
            ssot_failures = [r for r in import_results 
                           if r['test_type'] == 'ssot_import' and r['status'] != 'SUCCESS']
            pytest.fail(
                f"CRITICAL: SSOT UserExecutionEngine import failures. Core functionality broken:\n"
                f"{'  • ' + chr(10).join(f'{r['import_path']}: {r['actual']}' for r in ssot_failures)}\n"
                f"This indicates fundamental system issues requiring immediate attention."
            )
    
    def _format_import(self, node: ast.AST) -> str:
        """Format an import AST node for display."""
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            return f"import {', '.join(names)}"
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            return f"from {module} import {', '.join(names)}"
        else:
            return str(node)
    
    def _get_module_file_path(self, module_path: str) -> Path:
        """Convert module path to file system path."""
        # Convert module path to file path
        path_parts = module_path.split('.')
        file_path = self.project_root
        for part in path_parts:
            file_path = file_path / part
        return file_path.with_suffix('.py')
    
    def test_migration_completion_percentage(self):
        """Calculate and validate SSOT migration completion percentage.
        
        This test provides metrics on migration progress and should document
        the current ~60% completion status from Issue #620.
        """
        metrics = {
            'total_deprecated_files': len(self.deprecated_execution_engine_files),
            'files_properly_migrated': 0,
            'files_still_full_implementation': 0,
            'total_deprecated_lines': 0,
            'ssot_implementation_lines': 0,
            'import_consolidation_score': 0
        }
        
        # Analyze deprecated files
        for file_path in self.deprecated_execution_engine_files:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    metrics['total_deprecated_lines'] += lines
                    
                if lines <= 5:
                    metrics['files_properly_migrated'] += 1
                else:
                    metrics['files_still_full_implementation'] += 1
        
        # Analyze SSOT file
        if self.ssot_user_execution_engine.exists():
            with open(self.ssot_user_execution_engine, 'r', encoding='utf-8') as f:
                metrics['ssot_implementation_lines'] = len(f.readlines())
        
        # Calculate completion percentage
        if metrics['total_deprecated_files'] > 0:
            completion_percentage = (
                metrics['files_properly_migrated'] / metrics['total_deprecated_files']
            ) * 100
        else:
            completion_percentage = 0
        
        print(f"\n📊 MIGRATION COMPLETION METRICS:")
        print(f"   Total deprecated files: {metrics['total_deprecated_files']}")
        print(f"   Properly migrated (≤5 lines): {metrics['files_properly_migrated']}")
        print(f"   Still full implementation: {metrics['files_still_full_implementation']}")
        print(f"   Total deprecated code lines: {metrics['total_deprecated_lines']:,}")
        print(f"   SSOT implementation lines: {metrics['ssot_implementation_lines']:,}")
        print(f"   Estimated completion: {completion_percentage:.1f}%")
        
        # Document current failing state (should be ~60% per Issue #620)
        expected_completion_range = (50, 70)  # Expected current range
        
        if expected_completion_range[0] <= completion_percentage <= expected_completion_range[1]:
            print(f"   ✅ REPRODUCTION: Confirmed expected completion range ({expected_completion_range[0]}-{expected_completion_range[1]}%)")
        else:
            print(f"   ⚠️  UNEXPECTED: Completion {completion_percentage:.1f}% outside expected range")
        
        # Fail if migration is incomplete (demonstrates current state)
        if completion_percentage < 100:
            pytest.fail(
                f"🚨 ISSUE #620 MIGRATION STATUS: ExecutionEngine SSOT migration {completion_percentage:.1f}% complete. "
                f"\n📋 CURRENT STATE:"
                f"\n  • {metrics['files_still_full_implementation']} files still contain full implementations"
                f"\n  • {metrics['total_deprecated_lines']:,} lines of deprecated code remain"
                f"\n  • User isolation vulnerabilities persist in deprecated code paths"
                f"\n\n🎯 TARGET STATE:"
                f"\n  • All deprecated files converted to 5-line redirects"
                f"\n  • 100% migration to UserExecutionEngine SSOT"
                f"\n  • Complete user isolation and WebSocket event consolidation"
                f"\n\n💼 BUSINESS IMPACT:"
                f"\n  • Chat functionality instability (90% of platform value at risk)"
                f"\n  • User context leakage in multi-user scenarios"
                f"\n  • WebSocket event delivery inconsistencies"
                f"\n\nREMEDIATION: Complete SSOT migration per Issue #620 plan."
            )


if __name__ == '__main__':
    import unittest
    unittest.main()