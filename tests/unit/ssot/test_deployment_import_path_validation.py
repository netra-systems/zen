#!/usr/bin/env python3
"""
SSOT Deployment Import Path Validation Tests

Tests import path validation for deployment SSOT compliance.
Validates that deployment code uses proper SSOT import patterns
and detects anti-patterns that violate SSOT principles.

Created for GitHub Issue #245: Deploy script canonical source conflicts
Part of: 20% new SSOT deployment tests requirement (Test File 6 of 8)

Business Value: Platform/Internal - System Stability & SSOT Compliance
Prevents import anti-patterns and ensures SSOT import compliance.

DESIGN CRITERIA:
- Unit tests for import path validation logic
- Tests SSOT import pattern enforcement
- Validates anti-pattern detection
- No Docker dependency (pure import analysis)
- Uses SSOT test infrastructure patterns

TEST CATEGORIES:
- SSOT import pattern validation
- Anti-pattern detection and prevention
- Import path compliance verification
- Circular dependency prevention
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import Mock, patch

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDeploymentImportPathValidation(SSotBaseTestCase):
    """
    Unit tests for deployment import path validation.
    
    Tests that deployment code uses proper SSOT import patterns
    and detects violations of SSOT import principles.
    """
    
    def setup_method(self, method=None):
        """Setup import path validation test environment."""
        super().setup_method(method)
        
        # Project paths
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.unified_runner_path = self.project_root / "tests" / "unified_test_runner.py"
        self.scripts_dir = self.project_root / "scripts"
        
        # SSOT import patterns (expected)
        self.ssot_import_patterns = {
            "test_framework.ssot.base_test_case",
            "test_framework.unified_docker_manager", 
            "shared.isolated_environment",
            "shared.types.core_types",
            "test_framework.ssot.orchestration"
        }
        
        # Anti-patterns (forbidden)
        self.import_anti_patterns = {
            "from scripts.deploy_to_gcp import",
            "import deploy_to_gcp",
            "from deploy_to_gcp import",
            "from scripts import deploy_to_gcp",
            "from ..scripts.deploy_to_gcp import",
            "import scripts.deploy_to_gcp"
        }
        
        # Record test start metrics
        self.record_metric("test_category", "unit")
        self.record_metric("ssot_focus", "import_path_validation")
        self.record_metric("ssot_patterns_count", len(self.ssot_import_patterns))
        self.record_metric("anti_patterns_count", len(self.import_anti_patterns))
    
    def test_unified_test_runner_uses_ssot_import_patterns(self):
        """
        Test that UnifiedTestRunner uses SSOT import patterns.
        
        Validates that the canonical deployment source follows
        SSOT import principles.
        """
        assert self.unified_runner_path.exists(), "UnifiedTestRunner not found"
        
        # Parse UnifiedTestRunner imports
        runner_imports = self._extract_imports_from_file(self.unified_runner_path)
        
        # Check for SSOT import usage
        ssot_imports_found = []
        
        for import_info in runner_imports:
            import_module = import_info.get("module", "")
            
            for ssot_pattern in self.ssot_import_patterns:
                if ssot_pattern in import_module:
                    ssot_imports_found.append({
                        "pattern": ssot_pattern,
                        "actual_import": import_module,
                        "line": import_info.get("line", 0)
                    })
        
        # Record SSOT import metrics
        self.record_metric("ssot_imports_found", len(ssot_imports_found))
        self.record_metric("total_imports_in_runner", len(runner_imports))
        
        # Should find at least some SSOT imports
        minimum_ssot_imports = 2
        
        assert len(ssot_imports_found) >= minimum_ssot_imports, \
            f"UnifiedTestRunner has insufficient SSOT imports: {len(ssot_imports_found)} < {minimum_ssot_imports}. " \
            f"Found: {[imp['pattern'] for imp in ssot_imports_found]}"
        
        # Record successful SSOT import validation
        self.record_metric("ssot_import_validation_passed", True)
    
    def test_deployment_code_has_no_import_anti_patterns(self):
        """
        Test that deployment code has no import anti-patterns.
        
        CRITICAL: This test MUST fail if anti-patterns are found.
        """
        anti_pattern_violations = []
        
        # Files to check for anti-patterns
        files_to_check = [
            self.unified_runner_path,
        ]
        
        # Add deployment scripts if they exist
        for script in self.scripts_dir.glob("*deploy*.py"):
            files_to_check.append(script)
        
        # Check each file for anti-patterns
        for file_path in files_to_check:
            if not file_path.exists():
                continue
                
            try:
                file_content = file_path.read_text(encoding='utf-8')
                file_imports = self._extract_imports_from_file(file_path)
                
                # Check for anti-patterns in import statements
                for import_info in file_imports:
                    import_statement = import_info.get("raw_statement", "")
                    
                    for anti_pattern in self.import_anti_patterns:
                        if anti_pattern in import_statement:
                            anti_pattern_violations.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': import_info.get("line", 0),
                                'anti_pattern': anti_pattern,
                                'actual_import': import_statement,
                                'severity': 'critical'
                            })
                
                # Check for anti-patterns in general code
                for anti_pattern in self.import_anti_patterns:
                    if anti_pattern in file_content:
                        # Get line number
                        lines = file_content.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            if anti_pattern in line:
                                anti_pattern_violations.append({
                                    'file': str(file_path.relative_to(self.project_root)),
                                    'line': line_num,
                                    'anti_pattern': anti_pattern,
                                    'actual_import': line.strip(),
                                    'severity': 'critical'
                                })
                                break
                
            except Exception as e:
                self.record_metric(f"import_analysis_error_{file_path.name}", str(e))
        
        # Record anti-pattern detection metrics
        self.record_metric("files_checked", len(files_to_check))
        self.record_metric("anti_pattern_violations", len(anti_pattern_violations))
        
        # CRITICAL: No anti-patterns allowed
        if anti_pattern_violations:
            violation_details = "\n".join([
                f"  - {v['file']}:{v['line']}: {v['anti_pattern']}"
                for v in anti_pattern_violations[:10]  # Show first 10
            ])
            
            pytest.fail(
                f"IMPORT ANTI-PATTERN VIOLATION: {len(anti_pattern_violations)} anti-patterns detected:\n"
                f"{violation_details}\n"
                f"{'... and more' if len(anti_pattern_violations) > 10 else ''}\n\n"
                f"Expected: No import anti-patterns in deployment code\n"
                f"Fix: Replace anti-pattern imports with SSOT equivalents\n"
                f"DEPLOYMENT BLOCKED until all anti-patterns resolved"
            )
    
    def test_import_path_absolute_compliance(self):
        """
        Test that all imports use absolute paths (SSOT requirement).
        
        Validates that no relative imports are used in deployment code.
        """
        relative_import_violations = []
        
        # Files to check
        deployment_files = [self.unified_runner_path]
        
        for script in self.scripts_dir.glob("*.py"):
            deployment_files.append(script)
        
        # Check each file for relative imports
        for file_path in deployment_files:
            if not file_path.exists():
                continue
                
            try:
                file_imports = self._extract_imports_from_file(file_path)
                
                for import_info in file_imports:
                    if import_info.get("is_relative", False):
                        relative_import_violations.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': import_info.get("line", 0),
                            'import_statement': import_info.get("raw_statement", ""),
                            'module': import_info.get("module", "")
                        })
                        
            except Exception as e:
                self.record_metric(f"relative_import_check_error_{file_path.name}", str(e))
        
        # Record relative import metrics
        self.record_metric("relative_import_violations", len(relative_import_violations))
        
        # SSOT requires absolute imports only
        if relative_import_violations:
            violation_details = "\n".join([
                f"  - {v['file']}:{v['line']}: {v['import_statement']}"
                for v in relative_import_violations
            ])
            
            pytest.fail(
                f"RELATIVE IMPORT VIOLATION: {len(relative_import_violations)} relative imports found:\n"
                f"{violation_details}\n\n"
                f"Expected: All imports should be absolute (SSOT requirement)\n"
                f"Fix: Convert relative imports to absolute imports"
            )
    
    def test_circular_dependency_prevention(self):
        """
        Test circular dependency prevention in deployment imports.
        
        Validates that deployment code doesn't create circular dependencies.
        """
        dependency_graph = {}
        circular_dependencies = []
        
        # Build dependency graph for deployment-related modules
        deployment_modules = [
            "tests.unified_test_runner",
            "test_framework.unified_docker_manager",
            "shared.isolated_environment"
        ]
        
        for module_name in deployment_modules:
            try:
                module_path = self._resolve_module_path(module_name)
                
                if module_path and module_path.exists():
                    imports = self._extract_imports_from_file(module_path)
                    
                    # Filter for deployment-related imports only
                    deployment_imports = []
                    for import_info in imports:
                        import_module = import_info.get("module", "")
                        
                        if any(dep_mod in import_module for dep_mod in deployment_modules):
                            deployment_imports.append(import_module)
                    
                    dependency_graph[module_name] = deployment_imports
                    
            except Exception as e:
                self.record_metric(f"dependency_analysis_error_{module_name}", str(e))
        
        # Detect circular dependencies
        circular_dependencies = self._detect_circular_dependencies(dependency_graph)
        
        # Record circular dependency metrics
        self.record_metric("modules_analyzed", len(deployment_modules))
        self.record_metric("circular_dependencies_found", len(circular_dependencies))
        
        # No circular dependencies allowed
        if circular_dependencies:
            cycle_details = "\n".join([
                f"  - {' -> '.join(cycle)}"
                for cycle in circular_dependencies
            ])
            
            pytest.fail(
                f"CIRCULAR DEPENDENCY VIOLATION: {len(circular_dependencies)} circular dependencies detected:\n"
                f"{cycle_details}\n\n"
                f"Expected: No circular dependencies in deployment code\n"
                f"Fix: Refactor imports to eliminate circular dependencies"
            )
    
    def test_ssot_import_registry_compliance(self):
        """
        Test compliance with SSOT Import Registry.
        
        Validates that imports follow the patterns defined in SSOT_IMPORT_REGISTRY.md.
        """
        # Load SSOT Import Registry if available
        ssot_registry_path = self.project_root / "SSOT_IMPORT_REGISTRY.md"
        
        if not ssot_registry_path.exists():
            pytest.skip("SSOT_IMPORT_REGISTRY.md not found")
        
        registry_violations = []
        
        try:
            registry_content = ssot_registry_path.read_text(encoding='utf-8')
            
            # Extract verified import patterns from registry
            verified_patterns = self._extract_verified_patterns_from_registry(registry_content)
            broken_patterns = self._extract_broken_patterns_from_registry(registry_content)
            
            # Check UnifiedTestRunner against registry
            runner_imports = self._extract_imports_from_file(self.unified_runner_path)
            
            for import_info in runner_imports:
                import_module = import_info.get("module", "")
                
                # Check if import uses broken pattern
                for broken_pattern in broken_patterns:
                    if broken_pattern in import_module:
                        registry_violations.append({
                            'file': 'unified_test_runner.py',
                            'line': import_info.get("line", 0),
                            'violation': 'uses_broken_pattern',
                            'pattern': broken_pattern,
                            'import': import_module
                        })
            
            # Record registry compliance metrics
            self.record_metric("verified_patterns_found", len(verified_patterns))
            self.record_metric("broken_patterns_found", len(broken_patterns))
            self.record_metric("registry_violations", len(registry_violations))
            
            # Registry compliance required
            if registry_violations:
                violation_details = "\n".join([
                    f"  - {v['file']}:{v['line']}: {v['violation']} - {v['pattern']}"
                    for v in registry_violations
                ])
                
                pytest.fail(
                    f"SSOT REGISTRY VIOLATION: {len(registry_violations)} registry compliance violations:\n"
                    f"{violation_details}\n\n"
                    f"Expected: All imports should follow SSOT Import Registry patterns\n"
                    f"Fix: Use verified import patterns from SSOT_IMPORT_REGISTRY.md"
                )
                
        except Exception as e:
            self.record_metric("registry_compliance_check_error", str(e))
            # Don't fail test for registry parsing errors
    
    def _extract_imports_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract import information from a Python file."""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'name': alias.asname or alias.name,
                            'line': node.lineno,
                            'is_relative': False,
                            'raw_statement': f"import {alias.name}"
                        })
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    level = node.level
                    
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno,
                            'is_relative': level > 0,
                            'relative_level': level,
                            'raw_statement': f"from {'.' * level}{module} import {alias.name}"
                        })
            
        except Exception as e:
            self.record_metric(f"import_extraction_error_{file_path.name}", str(e))
        
        return imports
    
    def _resolve_module_path(self, module_name: str) -> Optional[Path]:
        """Resolve a module name to its file path."""
        # Convert module name to file path
        module_parts = module_name.split('.')
        
        # Try different possible paths
        possible_paths = [
            self.project_root / Path(*module_parts).with_suffix('.py'),
            self.project_root / Path(*module_parts) / '__init__.py'
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def _detect_circular_dependencies(self, dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies in a dependency graph."""
        circular_deps = []
        
        def find_cycles(node: str, path: List[str], visited: Set[str]) -> None:
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                circular_deps.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for dependency in dependency_graph.get(node, []):
                find_cycles(dependency, path.copy(), visited)
        
        visited = set()
        for node in dependency_graph:
            if node not in visited:
                find_cycles(node, [], visited)
        
        return circular_deps
    
    def _extract_verified_patterns_from_registry(self, registry_content: str) -> List[str]:
        """Extract verified import patterns from SSOT Import Registry."""
        verified_patterns = []
        
        # Look for verified imports section
        lines = registry_content.split('\n')
        in_verified_section = False
        
        for line in lines:
            if "✅ VERIFIED IMPORTS" in line:
                in_verified_section = True
                continue
            elif "❌ BROKEN IMPORTS" in line:
                in_verified_section = False
                continue
            
            if in_verified_section and "from " in line:
                # Extract import pattern
                if "from " in line and " import " in line:
                    pattern = line.strip()
                    if pattern.startswith("from "):
                        verified_patterns.append(pattern)
        
        return verified_patterns
    
    def _extract_broken_patterns_from_registry(self, registry_content: str) -> List[str]:
        """Extract broken import patterns from SSOT Import Registry."""
        broken_patterns = []
        
        # Look for broken imports section
        lines = registry_content.split('\n')
        in_broken_section = False
        
        for line in lines:
            if "❌ BROKEN IMPORTS" in line:
                in_broken_section = True
                continue
            elif in_broken_section and line.startswith("#"):
                in_broken_section = False
                continue
            
            if in_broken_section and "from " in line:
                # Extract import pattern
                pattern = line.strip()
                if pattern.startswith("from "):
                    broken_patterns.append(pattern)
        
        return broken_patterns


class TestDeploymentImportPathValidationEdgeCases(SSotBaseTestCase):
    """
    Edge case tests for deployment import path validation.
    """
    
    def test_dynamic_import_detection(self):
        """
        Test detection of dynamic imports that might bypass SSOT.
        
        Validates that dynamic imports are detected and validated.
        """
        # This test would check for importlib usage, exec statements, etc.
        # that might be used to bypass static import analysis
        
        dynamic_import_patterns = [
            "__import__",
            "importlib.import_module",
            "exec(",
            "eval("
        ]
        
        violations = []
        
        # Check UnifiedTestRunner for dynamic imports
        if self.unified_runner_path.exists():
            content = self.unified_runner_path.read_text(encoding='utf-8')
            
            for pattern in dynamic_import_patterns:
                if pattern in content:
                    violations.append({
                        'file': 'unified_test_runner.py',
                        'pattern': pattern,
                        'type': 'dynamic_import'
                    })
        
        # Record dynamic import metrics
        self.record_metric("dynamic_import_violations", len(violations))
        
        # Dynamic imports should be rare and documented
        if len(violations) > 2:  # Allow a few dynamic imports
            pytest.fail(
                f"Too many dynamic imports detected: {len(violations)}. "
                f"Dynamic imports can bypass SSOT import validation."
            )
    
    def test_import_path_consistency_across_environments(self):
        """
        Test that import paths are consistent across different environments.
        
        Validates that imports work in different Python environments.
        """
        # Test that critical SSOT imports can be resolved
        critical_imports = [
            "test_framework.ssot.base_test_case",
            "shared.isolated_environment"
        ]
        
        import_resolution_failures = []
        
        for import_name in critical_imports:
            try:
                # Try to resolve the import path
                module_path = self._resolve_module_path(import_name)
                
                if not module_path or not module_path.exists():
                    import_resolution_failures.append(import_name)
                    
            except Exception as e:
                import_resolution_failures.append(f"{import_name}: {e}")
        
        # Record import resolution metrics
        self.record_metric("critical_imports_tested", len(critical_imports))
        self.record_metric("import_resolution_failures", len(import_resolution_failures))
        
        # Critical imports should be resolvable
        if import_resolution_failures:
            pytest.fail(
                f"Critical import resolution failures: {import_resolution_failures}"
            )
    
    def _resolve_module_path(self, module_name: str) -> Optional[Path]:
        """Resolve a module name to its file path."""
        # Same as parent class method
        module_parts = module_name.split('.')
        
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / Path(*module_parts).with_suffix('.py'),
            Path(__file__).parent.parent.parent.parent / Path(*module_parts) / '__init__.py'
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])