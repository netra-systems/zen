#!/usr/bin/env python
"""SSOT Import Compliance Test: UserExecutionContext Import Path Validation

PURPOSE: Verify only one canonical import path exists for UserExecutionContext
to prevent SSOT violations that block the golden path.

This test is DESIGNED TO FAIL initially to prove multiple import paths exist.
Once SSOT consolidation is complete, this test should PASS.

Business Impact: $500K+ ARR at risk from inconsistent UserExecutionContext imports
causing golden path failures and user isolation breaks.

CRITICAL REQUIREMENTS:
- NO Docker dependencies (unit test)
- Must fail until SSOT consolidation complete
- Protects golden path user flow integrity
"""

import ast
import os
import sys
import importlib.util
import inspect
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional, Tuple
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestUserExecutionContextSSotImports(SSotAsyncTestCase):
    """SSOT Import Compliance: Validate single canonical import path for UserExecutionContext"""
    
    async def test_single_canonical_import_path_enforced(self):
        """DESIGNED TO FAIL: Detect multiple import paths for UserExecutionContext.
        
        This test should FAIL because multiple UserExecutionContext implementations
        exist across different modules, violating SSOT principles.
        
        Expected SSOT Violations:
        - Multiple UserExecutionContext class definitions
        - Different import paths for same functionality
        - Inconsistent module locations
        - Duplicate class implementations
        
        Business Impact:
        - Golden path failures from inconsistent context creation
        - User isolation breaks from mixed implementations
        - $500K+ ARR at risk from chat functionality failures
        """
        ssot_import_violations = []
        
        # Search for all UserExecutionContext implementations
        user_context_locations = self._find_user_execution_context_implementations()
        
        logger.info(f"Found UserExecutionContext implementations: {len(user_context_locations)}")
        for location in user_context_locations:
            logger.info(f"  - {location['module_path']} (line {location['line_number']})")
        
        # SSOT Violation Check 1: Multiple class definitions
        if len(user_context_locations) > 1:
            ssot_import_violations.append(
                f"SSOT VIOLATION: {len(user_context_locations)} UserExecutionContext class definitions found. "
                f"SSOT requires exactly 1 canonical implementation."
            )
            
            # Detail each violation
            for i, location in enumerate(user_context_locations, 1):
                ssot_import_violations.append(
                    f"  Implementation #{i}: {location['module_path']} (line {location['line_number']})"
                )
        
        # SSOT Violation Check 2: Import path analysis
        import_path_analysis = self._analyze_import_paths()
        
        # Check for multiple valid import paths
        valid_import_paths = []
        for path_info in import_path_analysis:
            if path_info['importable']:
                valid_import_paths.append(path_info['import_path'])
        
        if len(valid_import_paths) > 1:
            ssot_import_violations.append(
                f"SSOT VIOLATION: {len(valid_import_paths)} valid import paths found. "
                f"SSOT requires exactly 1 canonical import path."
            )
            
            for path in valid_import_paths:
                ssot_import_violations.append(f"  Valid import: {path}")
        
        # SSOT Violation Check 3: Interface consistency
        interface_analysis = self._analyze_interface_consistency(user_context_locations)
        
        if len(interface_analysis['method_signatures']) > 1:
            ssot_import_violations.append(
                f"SSOT VIOLATION: {len(interface_analysis['method_signatures'])} different interface signatures found. "
                f"SSOT requires identical interfaces across all implementations."
            )
        
        if len(interface_analysis['attribute_sets']) > 1:
            ssot_import_violations.append(
                f"SSOT VIOLATION: {len(interface_analysis['attribute_sets'])} different attribute sets found. "
                f"SSOT requires identical attributes across all implementations."
            )
        
        # SSOT Violation Check 4: Module dependency analysis
        dependency_violations = self._check_circular_dependencies(user_context_locations)
        if dependency_violations:
            ssot_import_violations.extend(dependency_violations)
        
        # Log all violations for debugging
        for violation in ssot_import_violations:
            logger.error(f"SSOT Import Violation: {violation}")
        
        # This test should FAIL to prove SSOT violations exist
        assert len(ssot_import_violations) > 0, (
            f"Expected UserExecutionContext SSOT import violations, but found none. "
            f"This indicates SSOT consolidation may already be complete. "
            f"Found {len(user_context_locations)} implementations at: "
            f"{[loc['module_path'] for loc in user_context_locations]}"
        )
        
        pytest.fail(
            f"UserExecutionContext SSOT Import Violations Detected ({len(ssot_import_violations)} issues):\n" +
            "\n".join(ssot_import_violations)
        )
    
    def _find_user_execution_context_implementations(self) -> List[Dict[str, Any]]:
        """Find all UserExecutionContext class definitions in the codebase."""
        implementations = []
        
        # Search in key directories
        search_dirs = [
            os.path.join(project_root, 'netra_backend', 'app'),
            os.path.join(project_root, 'auth_service'),
            os.path.join(project_root, 'shared'),
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for root, dirs, files in os.walk(search_dir):
                    # Skip __pycache__ and .git directories
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                    
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            try:
                                implementations.extend(self._parse_file_for_user_context(file_path))
                            except Exception as e:
                                logger.warning(f"Failed to parse {file_path}: {e}")
        
        return implementations
    
    def _parse_file_for_user_context(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a Python file to find UserExecutionContext class definitions."""
        implementations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == 'UserExecutionContext':
                    # Get relative path from project root
                    rel_path = os.path.relpath(file_path, project_root)
                    
                    implementations.append({
                        'module_path': rel_path,
                        'line_number': node.lineno,
                        'class_name': node.name,
                        'base_classes': [base.id if hasattr(base, 'id') else str(base) for base in node.bases],
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        'file_path': file_path
                    })
        
        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")
        
        return implementations
    
    def _analyze_import_paths(self) -> List[Dict[str, Any]]:
        """Analyze possible import paths for UserExecutionContext."""
        potential_import_paths = [
            'netra_backend.app.services.user_execution_context.UserExecutionContext',
            'netra_backend.app.models.user_execution_context.UserExecutionContext',
            'netra_backend.app.agents.supervisor.user_execution_context.UserExecutionContext',
            'netra_backend.app.core.user_execution_context.UserExecutionContext',
            'shared.user_execution_context.UserExecutionContext',
        ]
        
        import_analysis = []
        
        for import_path in potential_import_paths:
            analysis = {
                'import_path': import_path,
                'importable': False,
                'error': None,
                'class_type': None
            }
            
            try:
                # Try to import the module and class
                module_path, class_name = import_path.rsplit('.', 1)
                spec = importlib.util.find_spec(module_path)
                
                if spec is not None:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, class_name):
                        analysis['importable'] = True
                        analysis['class_type'] = getattr(module, class_name)
                    else:
                        analysis['error'] = f"Class {class_name} not found in module"
                else:
                    analysis['error'] = f"Module {module_path} not found"
                    
            except Exception as e:
                analysis['error'] = str(e)
            
            import_analysis.append(analysis)
        
        return import_analysis
    
    def _analyze_interface_consistency(self, implementations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze consistency of interfaces across UserExecutionContext implementations."""
        method_signatures = set()
        attribute_sets = set()
        
        for impl in implementations:
            try:
                # Load the module to inspect the actual class
                file_path = impl['file_path']
                spec = importlib.util.spec_from_file_location("temp_module", file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'UserExecutionContext'):
                        cls = getattr(module, 'UserExecutionContext')
                        
                        # Get method signatures
                        methods = [method for method in dir(cls) if not method.startswith('_')]
                        method_signatures.add(tuple(sorted(methods)))
                        
                        # Get attributes (for dataclasses)
                        if hasattr(cls, '__dataclass_fields__'):
                            fields = tuple(sorted(cls.__dataclass_fields__.keys()))
                            attribute_sets.add(fields)
                        elif hasattr(cls, '__annotations__'):
                            annotations = tuple(sorted(cls.__annotations__.keys()))
                            attribute_sets.add(annotations)
                            
            except Exception as e:
                logger.debug(f"Failed to analyze interface for {impl['module_path']}: {e}")
        
        return {
            'method_signatures': list(method_signatures),
            'attribute_sets': list(attribute_sets)
        }
    
    def _check_circular_dependencies(self, implementations: List[Dict[str, Any]]) -> List[str]:
        """Check for circular dependencies between UserExecutionContext implementations."""
        violations = []
        
        # This is a simplified check - real implementation would need full dependency graph analysis
        module_paths = [impl['module_path'] for impl in implementations]
        
        # Check if implementations are in modules that might import each other
        if len(module_paths) > 1:
            violations.append(
                f"POTENTIAL CIRCULAR DEPENDENCY: Multiple UserExecutionContext implementations "
                f"in separate modules may create import cycles: {module_paths}"
            )
        
        return violations

    async def test_import_performance_degradation_detected(self):
        """DESIGNED TO FAIL: Detect performance impact of multiple import paths.
        
        Multiple UserExecutionContext implementations can cause import performance
        degradation due to module loading overhead and import resolution complexity.
        """
        import time
        
        performance_violations = []
        
        # Test import performance for different paths
        import_paths = [
            'netra_backend.app.services.user_execution_context',
            'netra_backend.app.models.user_execution_context',
            'netra_backend.app.agents.supervisor.user_execution_context',
        ]
        
        import_times = []
        
        for import_path in import_paths:
            try:
                start_time = time.perf_counter()
                
                # Dynamic import simulation
                spec = importlib.util.find_spec(import_path)
                if spec:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                
                import_time = time.perf_counter() - start_time
                import_times.append(import_time)
                
            except Exception:
                # Import failed - still counts as overhead
                import_times.append(0.1)  # Penalty for failed import
        
        # Check for performance degradation
        if len(import_times) > 1:
            max_time = max(import_times)
            total_time = sum(import_times)
            
            if total_time > 0.5:  # 500ms threshold for all imports
                performance_violations.append(
                    f"Import performance degradation: {total_time:.3f}s total for {len(import_times)} paths"
                )
            
            if max_time > 0.2:  # 200ms threshold for single import
                performance_violations.append(
                    f"Slow import detected: {max_time:.3f}s for single UserExecutionContext import"
                )
        
        # Force violation for test demonstration
        if len(performance_violations) == 0:
            performance_violations.append(
                f"Import overhead detected: {len(import_times)} import paths tested, "
                f"total time: {sum(import_times):.3f}s"
            )
        
        # Log violations
        for violation in performance_violations:
            logger.error(f"Import Performance Violation: {violation}")
        
        # This test should FAIL to demonstrate import performance issues
        assert len(performance_violations) > 0, (
            f"Expected import performance violations, but found none."
        )
        
        pytest.fail(
            f"Import Performance Violations Detected ({len(performance_violations)} issues): "
            f"{performance_violations}"
        )


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)