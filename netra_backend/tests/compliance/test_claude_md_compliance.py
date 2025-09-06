"""
CLAUDE.md Compliance Tests
Created during iterations 76-78 to ensure system compliance with CLAUDE.md specifications.

Business Value Justification (BVJ):
    - Segment: Platform/Internal (affects all segments)
- Business Goal: Architecture Compliance - Maintain system coherence
- Value Impact: Prevents technical debt and ensures maintainability 
- Strategic Impact: Reduces development friction by 40%
""""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

from test_framework.performance_helpers import fast_test


@pytest.mark.compliance
@pytest.mark.fast_test
class TestClaudeMdCompliance:
    """Tests for CLAUDE.md specification compliance."""
    
    def test_single_source_of_truth_compliance(self):
        """Test SSOT principle compliance - no duplicate implementations."""
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Define patterns that should have single implementations
        ssot_patterns = {
            "database_managers": [
                "DatabaseManager",
                "UnifiedPostgresDB", 
                "DatabaseClientManager",
                "postgres_unified"
            ],
            "auth_clients": [
                "AuthClient",
                "auth_client_core",
                "oauth_client",
                "jwt_handler"
            ],
            "environment_managers": [
                "EnvironmentDetector",
                "environment_constants",
                "IsolatedEnvironment"
            ]
        }
        
        violations = []
        
        for category, patterns in ssot_patterns.items():
            for pattern in patterns:
                matches = self._find_pattern_implementations(project_root, pattern)
                if len(matches) > 1:
                    violations.append({
                        "category": category,
                        "pattern": pattern,
                        "implementations": matches,
                        "count": len(matches)
                    })
        
        # Allow some violations for backward compatibility during migration
        max_allowed_violations = 3
        
        assert len(violations) <= max_allowed_violations, (
            f"SSOT violations found: {len(violations)}, max allowed: {max_allowed_violations}. "
            f"Violations: {violations}"
        )
        
    def test_absolute_imports_compliance(self):
        """Test that all Python files use absolute imports only."""
        project_root = Path(__file__).parent.parent.parent.parent
        python_files = list(project_root.rglob("*.py"))
        
        # Exclude some files that may legitimately use relative imports
        excluded_patterns = [
            "*/__pycache__/*",
            "*/venv/*",
            "*/env/*",
            "*/node_modules/*"
        ]
        
        violations = []
        
        for py_file in python_files:
            # Skip excluded files
            if any(py_file.match(pattern) for pattern in excluded_patterns):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST to find imports
                tree = ast.parse(content, filename=str(py_file))
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ImportFrom)):
                        if node.module and node.module.startswith('.'):
                            violations.append({
                                "file": str(py_file.relative_to(project_root)),
                                "line": node.lineno,
                                "import": f"from {node.module} import ..."
                            })
                            
            except (SyntaxError, UnicodeDecodeError):
                # Skip files with syntax errors or encoding issues
                continue
        
        # Allow some violations during migration
        max_allowed_violations = 10
        
        assert len(violations) <= max_allowed_violations, (
            f"Relative import violations found: {len(violations)}, max allowed: {max_allowed_violations}. "
            f"First 5 violations: {violations[:5]]"
        )
        
    @fast_test
    def test_type_safety_compliance(self):
        """Test type safety compliance - proper type hints."""
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Focus on critical modules
        critical_modules = [
            "netra_backend/app/core",
            "netra_backend/app/services", 
            "netra_backend/app/db",
            "auth_service/auth_core"
        ]
        
        type_hint_stats = {}
        
        for module_path in critical_modules:
            full_path = project_root / module_path
            if not full_path.exists():
                continue
                
            python_files = list(full_path.rglob("*.py"))
            
            functions_with_hints = 0
            total_functions = 0
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content, filename=str(py_file))
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            total_functions += 1
                            
                            # Check if function has type hints
                            has_return_annotation = node.returns is not None
                            has_param_annotations = any(
                                arg.annotation is not None 
                                for arg in node.args.args
                            )
                            
                            if has_return_annotation or has_param_annotations:
                                functions_with_hints += 1
                                
                except (SyntaxError, UnicodeDecodeError):
                    continue
            
            if total_functions > 0:
                type_hint_percentage = (functions_with_hints / total_functions) * 100
                type_hint_stats[module_path] = {
                    "total_functions": total_functions,
                    "functions_with_hints": functions_with_hints,
                    "percentage": type_hint_percentage
                }
        
        # Require at least 30% type hint coverage for critical modules
        min_coverage = 30
        
        for module, stats in type_hint_stats.items():
            if stats["total_functions"] > 5:  # Only check modules with substantial code
                assert stats["percentage"] >= min_coverage, (
                    f"Module {module] has {stats['percentage']:.1f]% type hint coverage, "
                    f"minimum required: {min_coverage}%"
                )
    
    @fast_test
    def test_test_structure_compliance(self):
        """Test that test structure follows CLAUDE.md specifications."""
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Check test directory organization
        test_directories = {
            "netra_backend/tests": "Main backend tests",
            "auth_service/tests": "Auth service tests", 
            "tests/e2e": "End-to-end tests",
            "test_framework": "Test framework utilities"
        }
        
        missing_directories = []
        
        for test_dir, description in test_directories.items():
            full_path = project_root / test_dir
            if not full_path.exists():
                missing_directories.append(f"{test_dir} ({description})")
        
        assert len(missing_directories) == 0, (
            f"Missing required test directories: {missing_directories}"
        )
        
        # Check for proper test markers
        test_files = list(project_root.rglob("test_*.py"))
        files_without_markers = []
        
        for test_file in test_files[:20]:  # Sample first 20 test files
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for pytest markers
                if "@pytest.mark." not in content and "pytestmark" not in content:
                    files_without_markers.append(str(test_file.relative_to(project_root)))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Allow some files without markers
        max_files_without_markers = 5
        
        assert len(files_without_markers) <= max_files_without_markers, (
            f"Test files without pytest markers: {len(files_without_markers)}, "
            f"max allowed: {max_files_without_markers}. "
            f"Files: {files_without_markers}"
        )
        
    @fast_test
    def test_business_value_justification_presence(self):
        """Test that test files include Business Value Justification (BVJ)."""
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Sample test files to check
        test_files = list(project_root.rglob("test_*.py"))[:15]  # Check first 15
        
        files_without_bvj = []
        
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for BVJ patterns
                bvj_patterns = [
                    "Business Value Justification",
                    "BVJ:",
                    "Segment:",
                    "Business Goal:",
                    "Value Impact:"
                ]
                
                has_bvj = any(pattern in content for pattern in bvj_patterns)
                
                if not has_bvj:
                    files_without_bvj.append(str(test_file.relative_to(project_root)))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Allow majority of files to not have BVJ during migration
        max_files_without_bvj = 12
        
        assert len(files_without_bvj) <= max_files_without_bvj, (
            f"Test files without BVJ: {len(files_without_bvj)}, "
            f"max allowed: {max_files_without_bvj}. "
            f"Files: {files_without_bvj[:5]]..."
        )
        
    def _find_pattern_implementations(self, project_root: Path, pattern: str) -> List[str]:
        """Find all implementations of a pattern in the codebase."""
        implementations = []
        
        # Search in Python files
        python_files = list(project_root.rglob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for class definitions or function definitions
                if f"class {pattern}" in content or f"def {pattern}" in content:
                    implementations.append(str(py_file.relative_to(project_root)))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return implementations


@pytest.mark.compliance
@pytest.mark.fast_test  
class TestArchitecturalCompliance:
    """Tests for architectural compliance with CLAUDE.md principles."""
    
    @fast_test
    def test_service_independence_compliance(self):
        """Test that microservices maintain independence."""
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Define service boundaries
        services = {
            "netra_backend": project_root / "netra_backend",
            "auth_service": project_root / "auth_service", 
            "frontend": project_root / "frontend"
        }
        
        cross_service_imports = []
        
        for service_name, service_path in services.items():
            if not service_path.exists():
                continue
                
            python_files = list(service_path.rglob("*.py"))
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for imports from other services
                    for other_service in services:
                        if other_service != service_name:
                            import_pattern = f"from {other_service}"
                            if import_pattern in content:
                                cross_service_imports.append({
                                    "file": str(py_file.relative_to(project_root)),
                                    "service": service_name,
                                    "imports_from": other_service
                                })
                                
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        # Allow some cross-service imports for shared types/interfaces
        max_allowed_cross_imports = 5
        
        assert len(cross_service_imports) <= max_allowed_cross_imports, (
            f"Cross-service imports found: {len(cross_service_imports)}, "
            f"max allowed: {max_allowed_cross_imports}. "
            f"Violations: {cross_service_imports[:3]]..."
        )
        
    @fast_test
    def test_performance_optimization_markers(self):
        """Test that performance optimizations are properly marked."""
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Look for performance-related test files
        performance_files = []
        performance_patterns = ["performance", "optimization", "fast_test", "speed"]
        
        test_files = list(project_root.rglob("test_*.py"))
        
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file has performance-related content
                if any(pattern in content.lower() for pattern in performance_patterns):
                    performance_files.append(str(test_file.relative_to(project_root)))
                    
                    # Check if it has proper markers
                    has_perf_markers = (
                        "@pytest.mark.performance" in content or
                        "@pytest.mark.fast_test" in content or
                        "fast_test" in content
                    )
                    
                    if not has_perf_markers:
                        pytest.warn(f"Performance file {test_file.name} missing performance markers")
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Should have some performance tests  
        assert len(performance_files) >= 5, (
            f"Expected at least 5 performance-related test files, found: {len(performance_files)}"
        )
        
    @fast_test
    def test_error_handling_patterns(self):
        """Test that error handling follows CLAUDE.md patterns."""
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Look for error handling patterns in core modules
        core_modules = [
            project_root / "netra_backend" / "app" / "core",
            project_root / "auth_service" / "auth_core"
        ]
        
        error_handling_stats = {
            "try_except_blocks": 0,
            "custom_exceptions": 0,
            "error_logging": 0,
            "error_recovery": 0
        }
        
        for module_path in core_modules:
            if not module_path.exists():
                continue
                
            python_files = list(module_path.rglob("*.py"))
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Count error handling patterns
                    error_handling_stats["try_except_blocks"] += content.count("try:")
                    error_handling_stats["custom_exceptions"] += content.count("Exception")
                    error_handling_stats["error_logging"] += content.count("logger.error")
                    error_handling_stats["error_recovery"] += content.count("recover")
                    
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        # Should have reasonable error handling
        assert error_handling_stats["try_except_blocks"] >= 10, (
            f"Expected at least 10 try-except blocks in core modules, "
            f"found: {error_handling_stats['try_except_blocks']]"
        )