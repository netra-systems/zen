"""
Test Suite: Issue #884 - Multiple execution engine factories blocking AI responses
Module: Execution Engine Factory Consolidation Validation

PURPOSE:
This test is DESIGNED TO FAIL initially to detect multiple ExecutionEngineFactory implementations
that fragment execution engine creation and cause inconsistent AI response delivery.

BUSINESS IMPACT:
- $500K+ ARR at risk due to execution engine factory proliferation
- Multiple factory implementations cause inconsistent agent execution
- Factory fragmentation blocks reliable Golden Path user flow
- WebSocket event delivery becomes inconsistent across different execution paths

EXPECTED INITIAL STATE: FAIL (due to multiple factory implementations)
EXPECTED FINAL STATE: PASS (after factory consolidation to single SSOT)

Created: 2025-09-14 for Issue #884 Step 2 test validation
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple, Any
import pytest
from unittest.mock import patch
import ast

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestExecutionEngineFactoryConsolidation884(SSotBaseTestCase):
    """
    CRITICAL SSOT Test: Detect execution engine factory proliferation
    
    This test SHOULD FAIL initially, exposing factory fragmentation that blocks
    consistent AI response delivery and Golden Path user flow reliability.
    """
    
    def setup_method(self, method):
        """Set up test with factory proliferation analysis"""
        super().setup_method(method)
        self.record_metric("expected_failure_documented", True)
        self.record_metric("business_impact", "$500K+ ARR at risk due to factory proliferation")
        self.record_metric("issue_number", "884")
        
    def test_execution_engine_factory_should_fail_before_consolidation(self):
        """
        CRITICAL TEST: Validate execution engine factory consolidation
        
        Expected Initial Result: FAIL (multiple factory implementations)
        Expected Final Result: PASS (single consolidated factory)
        
        This test detects factory proliferation by analyzing imports and class definitions
        across the netra_backend codebase to identify multiple ExecutionEngineFactory
        implementations that cause execution fragmentation.
        """
        # Start timing for performance measurement
        import time
        start_time = time.time()
        
        # Record test execution
        self.record_metric("test_execution_start", start_time)
        
        # Define search paths for factory implementations
        search_paths = [
            Path("/Users/anthony/Desktop/netra-apex/netra_backend/app"),
            Path("/Users/anthony/Desktop/netra-apex/shared"),
        ]
        
        # Track factory implementations found
        factory_implementations = []
        factory_methods = []
        
        # Scan for execution engine factory patterns
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Parse AST to find factory patterns
                    try:
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            # Look for ExecutionEngineFactory class definitions
                            if isinstance(node, ast.ClassDef):
                                if "ExecutionEngineFactory" in node.name:
                                    factory_implementations.append({
                                        'file': str(py_file),
                                        'class': node.name,
                                        'line': node.lineno
                                    })
                                    
                                # Look for factory method patterns  
                                for method in node.body:
                                    if isinstance(method, ast.FunctionDef):
                                        if "create_execution_engine" in method.name:
                                            factory_methods.append({
                                                'file': str(py_file),
                                                'class': node.name,
                                                'method': method.name,
                                                'line': method.lineno
                                            })
                            
                            # Look for standalone factory functions
                            elif isinstance(node, ast.FunctionDef):
                                if "create_execution_engine" in node.name:
                                    factory_methods.append({
                                        'file': str(py_file),
                                        'class': 'standalone',
                                        'method': node.name,
                                        'line': node.lineno
                                    })
                                    
                    except SyntaxError:
                        # Skip files with syntax errors
                        pass
                        
                except Exception as e:
                    # Skip files that can't be read
                    pass
        
        # Record metrics for analysis
        self.record_metric("factory_implementations_found", len(factory_implementations))
        self.record_metric("factory_methods_found", len(factory_methods))
        self.record_metric("factory_details", {
            'implementations': factory_implementations,
            'methods': factory_methods
        })
        
        execution_time = time.time() - start_time
        self.record_metric("test_execution_time", execution_time)
        
        # CRITICAL ASSERTION: Should fail if multiple factory implementations exist
        # This indicates factory proliferation that needs SSOT consolidation
        assert len(factory_implementations) == 1, (
            f"CRITICAL: Multiple ExecutionEngineFactory implementations detected: {len(factory_implementations)}. "
            f"Found: {factory_implementations}. "
            f"Expected: Single SSOT factory implementation. "
            f"This factory proliferation causes execution engine fragmentation "
            f"and blocks consistent AI response delivery for $500K+ ARR Golden Path."
        )
        
        # Validate factory methods are consolidated
        # Allow up to 3 methods: one primary, one legacy wrapper, one test helper
        assert len(factory_methods) <= 3, (
            f"CRITICAL: Excessive factory methods detected: {len(factory_methods)}. "
            f"Found: {factory_methods}. "
            f"Expected: ≤3 methods (primary + legacy + test). "
            f"This method proliferation indicates scattered factory patterns "
            f"that fragment execution engine creation."
        )
        
        # If we get here, consolidation is successful
        self.record_metric("consolidation_status", "COMPLETE")
        self.record_metric("business_value_protected", True)
        
    def test_execution_engine_import_consistency_884(self):
        """
        Validate execution engine imports are consistent after factory consolidation
        
        This test ensures that all modules importing execution engines use the 
        same SSOT factory pattern, preventing import fragmentation.
        """
        import_patterns = []
        search_paths = [
            Path("/Users/anthony/Desktop/netra-apex/netra_backend/app"),
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Find import patterns related to execution engines
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if 'execution_engine' in line.lower() and ('import' in line or 'from' in line):
                            import_patterns.append({
                                'file': str(py_file),
                                'line': i,
                                'import': line
                            })
                            
                except Exception:
                    pass
        
        self.record_metric("import_patterns_found", len(import_patterns))
        self.record_metric("import_details", import_patterns)
        
        # Validate import consistency - after consolidation, imports should be standardized
        unique_import_patterns = set(pattern['import'] for pattern in import_patterns 
                                   if 'ExecutionEngineFactory' in pattern['import'])
        
        # Should have minimal unique import patterns after consolidation
        assert len(unique_import_patterns) <= 2, (
            f"CRITICAL: Inconsistent ExecutionEngineFactory import patterns: {len(unique_import_patterns)}. "
            f"Patterns: {unique_import_patterns}. "
            f"Expected: ≤2 patterns (primary + legacy compatibility). "
            f"Import inconsistency indicates incomplete SSOT consolidation."
        )
        
    def test_factory_singleton_elimination_884(self):
        """
        Validate that singleton patterns have been eliminated from factory implementations
        
        Issue #884 includes eliminating singleton patterns that cause shared state
        and prevent proper user isolation in multi-user execution.
        """
        singleton_patterns = []
        search_paths = [
            Path("/Users/anthony/Desktop/netra-apex/netra_backend/app"),
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Look for singleton patterns in execution engine related files
                    if 'execution_engine' in str(py_file).lower():
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            line_lower = line.strip().lower()
                            # Common singleton indicators
                            if any(pattern in line_lower for pattern in [
                                '_instance = none',
                                'if not hasattr(',
                                'if cls._instance is none',
                                '@singleton',
                                'metaclass=singleton'
                            ]):
                                singleton_patterns.append({
                                    'file': str(py_file),
                                    'line': i,
                                    'pattern': line.strip()
                                })
                                
                except Exception:
                    pass
        
        self.record_metric("singleton_patterns_found", len(singleton_patterns))
        self.record_metric("singleton_details", singleton_patterns)
        
        # CRITICAL: No singleton patterns should exist in execution engine factories
        assert len(singleton_patterns) == 0, (
            f"CRITICAL: Singleton patterns detected in execution engine code: {len(singleton_patterns)}. "
            f"Patterns: {singleton_patterns}. "
            f"Singleton patterns prevent proper user isolation and cause shared state issues "
            f"that block reliable multi-user AI response delivery."
        )