"""
Test Suite: Issue #884 - Multiple execution engine factories blocking AI responses
Module: Factory Method Consolidation Validation

PURPOSE:
This test is DESIGNED TO FAIL initially to detect scattered `create_execution_engine` methods
across 15+ modules that fragment execution engine creation and cause inconsistent behavior.

BUSINESS IMPACT:
- $500K+ ARR at risk due to scattered factory methods preventing consistent AI responses
- Multiple create_execution_engine methods cause different initialization patterns
- Method proliferation blocks standardized user execution contexts
- Inconsistent factory methods lead to unpredictable WebSocket event delivery

EXPECTED INITIAL STATE: FAIL (methods scattered across 15+ modules)
EXPECTED FINAL STATE: PASS (methods consolidated to centralized factory)

Created: 2025-09-14 for Issue #884 Step 2 test validation
"""

import pytest
import importlib
import inspect
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple, Any
import ast
import re

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestFactoryMethodConsolidation884(SSotBaseTestCase):
    """
    CRITICAL SSOT Test: Detect scattered execution engine factory methods
    
    This test SHOULD FAIL initially, exposing method proliferation across multiple
    modules that prevents consistent execution engine creation patterns.
    """
    
    def setup_method(self, method):
        """Set up test with factory method proliferation analysis"""
        super().setup_method(method)
        self.record_metric("expected_failure_documented", True)
        self.record_metric("business_impact", "$500K+ ARR at risk due to method proliferation")
        self.record_metric("issue_number", "884")
        
    def test_factory_methods_should_fail_before_consolidation(self):
        """
        CRITICAL TEST: Validate factory method consolidation across codebase
        
        Expected Initial Result: FAIL (methods scattered across 15+ modules)
        Expected Final Result: PASS (methods consolidated to centralized location)
        
        This test scans the entire netra_backend codebase to identify all
        create_execution_engine methods and similar factory patterns that
        should be consolidated into a single SSOT factory.
        """
        # Start timing for performance measurement
        import time
        start_time = time.time()
        
        # Record test execution
        self.record_metric("test_execution_start", start_time)
        
        # Define search paths
        search_paths = [
            Path("/Users/anthony/Desktop/netra-apex/netra_backend/app"),
            Path("/Users/anthony/Desktop/netra-apex/shared"),
        ]
        
        # Track all factory methods found
        factory_methods = []
        factory_function_patterns = [
            'create_execution_engine',
            'get_execution_engine',
            'build_execution_engine', 
            'make_execution_engine',
            'execution_engine_factory',
            'new_execution_engine'
        ]
        
        # Also track classes that contain factory methods
        factory_classes = []
        
        # Scan all Python files
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Parse AST to find factory method patterns
                    try:
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            # Look for class methods
                            if isinstance(node, ast.ClassDef):
                                class_has_factory_methods = False
                                
                                for method in node.body:
                                    if isinstance(method, ast.FunctionDef):
                                        method_name = method.name.lower()
                                        
                                        # Check if method matches factory patterns
                                        for pattern in factory_function_patterns:
                                            if pattern in method_name:
                                                factory_methods.append({
                                                    'file': str(py_file),
                                                    'class': node.name,
                                                    'method': method.name,
                                                    'line': method.lineno,
                                                    'pattern': pattern,
                                                    'type': 'class_method'
                                                })
                                                class_has_factory_methods = True
                                                
                                if class_has_factory_methods:
                                    factory_classes.append({
                                        'file': str(py_file),
                                        'class': node.name,
                                        'line': node.lineno
                                    })
                            
                            # Look for standalone functions
                            elif isinstance(node, ast.FunctionDef):
                                function_name = node.name.lower()
                                
                                for pattern in factory_function_patterns:
                                    if pattern in function_name:
                                        factory_methods.append({
                                            'file': str(py_file),
                                            'class': 'standalone',
                                            'method': node.name,
                                            'line': node.lineno,
                                            'pattern': pattern,
                                            'type': 'standalone_function'
                                        })
                                        
                    except SyntaxError:
                        # Skip files with syntax errors
                        pass
                        
                except Exception as e:
                    # Skip files that can't be read
                    pass
        
        # Also scan for regex patterns in content (for dynamic creation)
        dynamic_patterns = []
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Look for string patterns that suggest dynamic execution engine creation
                    for i, line in enumerate(content.split('\n'), 1):
                        line_lower = line.lower()
                        if ('execution_engine' in line_lower and 
                            any(word in line_lower for word in ['create', 'build', 'make', 'new', 'get'])):
                            # Skip actual method definitions (already caught by AST)
                            if 'def ' not in line_lower and 'class ' not in line_lower:
                                dynamic_patterns.append({
                                    'file': str(py_file),
                                    'line': i,
                                    'content': line.strip()
                                })
                                
                except Exception:
                    pass
        
        # Filter unique files to count module spread
        unique_files = set(method['file'] for method in factory_methods)
        
        # Record comprehensive metrics
        self.record_metric("total_factory_methods_found", len(factory_methods))
        self.record_metric("factory_classes_found", len(factory_classes))
        self.record_metric("unique_files_with_methods", len(unique_files))
        self.record_metric("dynamic_patterns_found", len(dynamic_patterns))
        
        self.record_metric("factory_method_details", {
            'methods': factory_methods,
            'classes': factory_classes,
            'dynamic_patterns': dynamic_patterns[:10]  # Limit for readability
        })
        
        execution_time = time.time() - start_time
        self.record_metric("test_execution_time", execution_time)
        
        # CRITICAL ASSERTION: Should fail if methods are scattered across many modules
        # After consolidation, should have methods only in centralized factory
        assert len(unique_files) <= 2, (
            f"CRITICAL: Factory methods scattered across {len(unique_files)} files. "
            f"Files: {sorted(unique_files)}. "
            f"Methods: {factory_methods}. "
            f"Expected: ≤2 files (primary factory + legacy compatibility). "
            f"This method scattering prevents consistent execution engine creation "
            f"and blocks reliable AI response delivery for $500K+ ARR Golden Path."
        )
        
        # Validate method count is reasonable after consolidation
        assert len(factory_methods) <= 5, (
            f"CRITICAL: Excessive factory methods detected: {len(factory_methods)}. "
            f"Methods: {factory_methods}. "
            f"Expected: ≤5 methods across all files. "
            f"Method proliferation indicates incomplete consolidation."
        )
        
        # If we get here, consolidation is successful
        self.record_metric("consolidation_status", "COMPLETE")
        self.record_metric("business_value_protected", True)
        
    def test_factory_method_signature_consistency_884(self):
        """
        Validate that remaining factory methods have consistent signatures
        
        After consolidation, any remaining factory methods should have
        standardized signatures to ensure consistent behavior.
        """
        import time
        start_time = time.time()
        
        search_paths = [
            Path("/Users/anthony/Desktop/netra-apex/netra_backend/app"),
        ]
        
        method_signatures = []
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    try:
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                if 'create_execution_engine' in node.name:
                                    # Extract method signature details
                                    args = [arg.arg for arg in node.args.args]
                                    defaults = len(node.args.defaults) if node.args.defaults else 0
                                    
                                    method_signatures.append({
                                        'file': str(py_file),
                                        'method': node.name,
                                        'args': args,
                                        'arg_count': len(args),
                                        'default_count': defaults,
                                        'line': node.lineno
                                    })
                                    
                    except SyntaxError:
                        pass
                        
                except Exception:
                    pass
        
        self.record_metric("method_signatures_found", len(method_signatures))
        self.record_metric("signature_details", method_signatures)
        
        execution_time = time.time() - start_time
        self.record_metric("signature_analysis_time", execution_time)
        
        if method_signatures:
            # Check for signature consistency
            unique_arg_patterns = set(tuple(sig['args']) for sig in method_signatures)
            
            # After consolidation, should have consistent signature patterns
            assert len(unique_arg_patterns) <= 2, (
                f"CRITICAL: Inconsistent factory method signatures: {len(unique_arg_patterns)}. "
                f"Patterns: {unique_arg_patterns}. "
                f"Signatures: {method_signatures}. "
                f"Expected: ≤2 signature patterns (primary + compatibility). "
                f"Signature inconsistency indicates incomplete SSOT consolidation."
            )
        
    def test_factory_method_import_patterns_884(self):
        """
        Validate that imports of factory methods are consistent
        
        After consolidation, all imports should point to the centralized factory
        instead of scattered method imports across different modules.
        """
        search_paths = [
            Path("/Users/anthony/Desktop/netra-apex/netra_backend/app"),
        ]
        
        import_patterns = []
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if ('import' in line and 
                            any(pattern in line for pattern in [
                                'create_execution_engine',
                                'ExecutionEngineFactory'
                            ])):
                            import_patterns.append({
                                'file': str(py_file),
                                'line': i,
                                'import': line
                            })
                            
                except Exception:
                    pass
        
        self.record_metric("import_patterns_found", len(import_patterns))
        self.record_metric("import_pattern_details", import_patterns)
        
        # Analyze import sources for consistency
        unique_import_sources = set()
        for pattern in import_patterns:
            import_line = pattern['import']
            if 'from' in import_line:
                # Extract the source module
                parts = import_line.split('from')[1].split('import')[0].strip()
                unique_import_sources.add(parts)
        
        # After consolidation, should import from centralized location
        assert len(unique_import_sources) <= 2, (
            f"CRITICAL: Factory methods imported from {len(unique_import_sources)} different sources. "
            f"Sources: {unique_import_sources}. "
            f"Import patterns: {import_patterns}. "
            f"Expected: ≤2 sources (primary + legacy compatibility). "
            f"Import source diversity indicates incomplete consolidation."
        )