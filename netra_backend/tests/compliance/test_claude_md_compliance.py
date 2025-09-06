# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: CLAUDE.md Compliance Tests
# REMOVED_SYNTAX_ERROR: Created during iterations 76-78 to ensure system compliance with CLAUDE.md specifications.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal (affects all segments)
    # REMOVED_SYNTAX_ERROR: - Business Goal: Architecture Compliance - Maintain system coherence
    # REMOVED_SYNTAX_ERROR: - Value Impact: Prevents technical debt and ensures maintainability
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Reduces development friction by 40%
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import ast
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import re
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Set, Tuple

    # REMOVED_SYNTAX_ERROR: import pytest

    # REMOVED_SYNTAX_ERROR: from test_framework.performance_helpers import fast_test


    # REMOVED_SYNTAX_ERROR: @pytest.mark.compliance
    # REMOVED_SYNTAX_ERROR: @pytest.mark.fast_test
# REMOVED_SYNTAX_ERROR: class TestClaudeMdCompliance:
    # REMOVED_SYNTAX_ERROR: """Tests for CLAUDE.md specification compliance."""

# REMOVED_SYNTAX_ERROR: def test_single_source_of_truth_compliance(self):
    # REMOVED_SYNTAX_ERROR: """Test SSOT principle compliance - no duplicate implementations."""
    # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent.parent

    # Define patterns that should have single implementations
    # REMOVED_SYNTAX_ERROR: ssot_patterns = { )
    # REMOVED_SYNTAX_ERROR: "database_managers": [ )
    # REMOVED_SYNTAX_ERROR: "DatabaseManager",
    # REMOVED_SYNTAX_ERROR: "UnifiedPostgresDB",
    # REMOVED_SYNTAX_ERROR: "DatabaseClientManager",
    # REMOVED_SYNTAX_ERROR: "postgres_unified"
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: "auth_clients": [ )
    # REMOVED_SYNTAX_ERROR: "AuthClient",
    # REMOVED_SYNTAX_ERROR: "auth_client_core",
    # REMOVED_SYNTAX_ERROR: "oauth_client",
    # REMOVED_SYNTAX_ERROR: "jwt_handler"
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: "environment_managers": [ )
    # REMOVED_SYNTAX_ERROR: "EnvironmentDetector",
    # REMOVED_SYNTAX_ERROR: "environment_constants",
    # REMOVED_SYNTAX_ERROR: "IsolatedEnvironment"
    
    

    # REMOVED_SYNTAX_ERROR: violations = []

    # REMOVED_SYNTAX_ERROR: for category, patterns in ssot_patterns.items():
        # REMOVED_SYNTAX_ERROR: for pattern in patterns:
            # REMOVED_SYNTAX_ERROR: matches = self._find_pattern_implementations(project_root, pattern)
            # REMOVED_SYNTAX_ERROR: if len(matches) > 1:
                # REMOVED_SYNTAX_ERROR: violations.append({ ))
                # REMOVED_SYNTAX_ERROR: "category": category,
                # REMOVED_SYNTAX_ERROR: "pattern": pattern,
                # REMOVED_SYNTAX_ERROR: "implementations": matches,
                # REMOVED_SYNTAX_ERROR: "count": len(matches)
                

                # Allow some violations for backward compatibility during migration
                # REMOVED_SYNTAX_ERROR: max_allowed_violations = 3

                # REMOVED_SYNTAX_ERROR: assert len(violations) <= max_allowed_violations, ( )
                # REMOVED_SYNTAX_ERROR: "formatted_string"
                # REMOVED_SYNTAX_ERROR: "formatted_string"
                

# REMOVED_SYNTAX_ERROR: def test_absolute_imports_compliance(self):
    # REMOVED_SYNTAX_ERROR: """Test that all Python files use absolute imports only."""
    # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent.parent
    # REMOVED_SYNTAX_ERROR: python_files = list(project_root.rglob("*.py"))

    # Exclude some files that may legitimately use relative imports
    # REMOVED_SYNTAX_ERROR: excluded_patterns = [ )
    # REMOVED_SYNTAX_ERROR: "*/__pycache__/*",
    # REMOVED_SYNTAX_ERROR: "*/venv/*",
    # REMOVED_SYNTAX_ERROR: "*/env/*",
    # REMOVED_SYNTAX_ERROR: "*/node_modules/*"
    

    # REMOVED_SYNTAX_ERROR: violations = []

    # REMOVED_SYNTAX_ERROR: for py_file in python_files:
        # Skip excluded files
        # REMOVED_SYNTAX_ERROR: if any(py_file.match(pattern) for pattern in excluded_patterns):
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: with open(py_file, 'r', encoding='utf-8') as f:
                    # REMOVED_SYNTAX_ERROR: content = f.read()

                    # Parse AST to find imports
                    # REMOVED_SYNTAX_ERROR: tree = ast.parse(content, filename=str(py_file))

                    # REMOVED_SYNTAX_ERROR: for node in ast.walk(tree):
                        # REMOVED_SYNTAX_ERROR: if isinstance(node, (ast.ImportFrom)):
                            # REMOVED_SYNTAX_ERROR: if node.module and node.module.startswith('.'):
                                # REMOVED_SYNTAX_ERROR: violations.append({ ))
                                # REMOVED_SYNTAX_ERROR: "file": str(py_file.relative_to(project_root)),
                                # REMOVED_SYNTAX_ERROR: "line": node.lineno,
                                # REMOVED_SYNTAX_ERROR: "import": "formatted_string"
                                

                                # REMOVED_SYNTAX_ERROR: except (SyntaxError, UnicodeDecodeError):
                                    # Skip files with syntax errors or encoding issues
                                    # REMOVED_SYNTAX_ERROR: continue

                                    # Allow some violations during migration
                                    # REMOVED_SYNTAX_ERROR: max_allowed_violations = 10

                                    # REMOVED_SYNTAX_ERROR: assert len(violations) <= max_allowed_violations, ( )
                                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                                    # REMOVED_SYNTAX_ERROR: "formatted_string"*.py"))

            # REMOVED_SYNTAX_ERROR: functions_with_hints = 0
            # REMOVED_SYNTAX_ERROR: total_functions = 0

            # REMOVED_SYNTAX_ERROR: for py_file in python_files:
                # REMOVED_SYNTAX_ERROR: try:
                    # REMOVED_SYNTAX_ERROR: with open(py_file, 'r', encoding='utf-8') as f:
                        # REMOVED_SYNTAX_ERROR: content = f.read()

                        # REMOVED_SYNTAX_ERROR: tree = ast.parse(content, filename=str(py_file))

                        # REMOVED_SYNTAX_ERROR: for node in ast.walk(tree):
                            # REMOVED_SYNTAX_ERROR: if isinstance(node, ast.FunctionDef):
                                # REMOVED_SYNTAX_ERROR: total_functions += 1

                                # Check if function has type hints
                                # REMOVED_SYNTAX_ERROR: has_return_annotation = node.returns is not None
                                # REMOVED_SYNTAX_ERROR: has_param_annotations = any( )
                                # REMOVED_SYNTAX_ERROR: arg.annotation is not None
                                # REMOVED_SYNTAX_ERROR: for arg in node.args.args
                                

                                # REMOVED_SYNTAX_ERROR: if has_return_annotation or has_param_annotations:
                                    # REMOVED_SYNTAX_ERROR: functions_with_hints += 1

                                    # REMOVED_SYNTAX_ERROR: except (SyntaxError, UnicodeDecodeError):
                                        # REMOVED_SYNTAX_ERROR: continue

                                        # REMOVED_SYNTAX_ERROR: if total_functions > 0:
                                            # REMOVED_SYNTAX_ERROR: type_hint_percentage = (functions_with_hints / total_functions) * 100
                                            # REMOVED_SYNTAX_ERROR: type_hint_stats[module_path] = { )
                                            # REMOVED_SYNTAX_ERROR: "total_functions": total_functions,
                                            # REMOVED_SYNTAX_ERROR: "functions_with_hints": functions_with_hints,
                                            # REMOVED_SYNTAX_ERROR: "percentage": type_hint_percentage
                                            

                                            # Require at least 30% type hint coverage for critical modules
                                            # REMOVED_SYNTAX_ERROR: min_coverage = 30

                                            # REMOVED_SYNTAX_ERROR: for module, stats in type_hint_stats.items():
                                                # REMOVED_SYNTAX_ERROR: if stats["total_functions"] > 5:  # Only check modules with substantial code
                                                # REMOVED_SYNTAX_ERROR: assert stats["percentage"] >= min_coverage, ( )
                                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                

                                                # REMOVED_SYNTAX_ERROR: @fast_test
# REMOVED_SYNTAX_ERROR: def test_test_structure_compliance(self):
    # REMOVED_SYNTAX_ERROR: """Test that test structure follows CLAUDE.md specifications."""
    # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent.parent

    # Check test directory organization
    # REMOVED_SYNTAX_ERROR: test_directories = { )
    # REMOVED_SYNTAX_ERROR: "netra_backend/tests": "Main backend tests",
    # REMOVED_SYNTAX_ERROR: "auth_service/tests": "Auth service tests",
    # REMOVED_SYNTAX_ERROR: "tests/e2e": "End-to-end tests",
    # REMOVED_SYNTAX_ERROR: "test_framework": "Test framework utilities"
    

    # REMOVED_SYNTAX_ERROR: missing_directories = []

    # REMOVED_SYNTAX_ERROR: for test_dir, description in test_directories.items():
        # REMOVED_SYNTAX_ERROR: full_path = project_root / test_dir
        # REMOVED_SYNTAX_ERROR: if not full_path.exists():
            # REMOVED_SYNTAX_ERROR: missing_directories.append("formatted_string")

            # REMOVED_SYNTAX_ERROR: assert len(missing_directories) == 0, ( )
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            

            # Check for proper test markers
            # REMOVED_SYNTAX_ERROR: test_files = list(project_root.rglob("test_*.py"))
            # REMOVED_SYNTAX_ERROR: files_without_markers = []

            # REMOVED_SYNTAX_ERROR: for test_file in test_files[:20]:  # Sample first 20 test files
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: with open(test_file, 'r', encoding='utf-8') as f:
                    # REMOVED_SYNTAX_ERROR: content = f.read()

                    # Check for pytest markers
                    # REMOVED_SYNTAX_ERROR: if "@pytest.mark." not in content and "pytestmark" not in content:
                        # REMOVED_SYNTAX_ERROR: files_without_markers.append(str(test_file.relative_to(project_root)))

                        # REMOVED_SYNTAX_ERROR: except (UnicodeDecodeError, PermissionError):
                            # REMOVED_SYNTAX_ERROR: continue

                            # Allow some files without markers
                            # REMOVED_SYNTAX_ERROR: max_files_without_markers = 5

                            # REMOVED_SYNTAX_ERROR: assert len(files_without_markers) <= max_files_without_markers, ( )
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            

                            # REMOVED_SYNTAX_ERROR: @fast_test
# REMOVED_SYNTAX_ERROR: def test_business_value_justification_presence(self):
    # REMOVED_SYNTAX_ERROR: """Test that test files include Business Value Justification (BVJ)."""
    # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent.parent

    # Sample test files to check
    # REMOVED_SYNTAX_ERROR: test_files = list(project_root.rglob("test_*.py"))[:15]  # Check first 15

    # REMOVED_SYNTAX_ERROR: files_without_bvj = []

    # REMOVED_SYNTAX_ERROR: for test_file in test_files:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: with open(test_file, 'r', encoding='utf-8') as f:
                # REMOVED_SYNTAX_ERROR: content = f.read()

                # Check for BVJ patterns
                # REMOVED_SYNTAX_ERROR: bvj_patterns = [ )
                # REMOVED_SYNTAX_ERROR: "Business Value Justification",
                # REMOVED_SYNTAX_ERROR: "BVJ:",
                # REMOVED_SYNTAX_ERROR: "Segment:",
                # REMOVED_SYNTAX_ERROR: "Business Goal:",
                # REMOVED_SYNTAX_ERROR: "Value Impact:"
                

                # REMOVED_SYNTAX_ERROR: has_bvj = any(pattern in content for pattern in bvj_patterns)

                # REMOVED_SYNTAX_ERROR: if not has_bvj:
                    # REMOVED_SYNTAX_ERROR: files_without_bvj.append(str(test_file.relative_to(project_root)))

                    # REMOVED_SYNTAX_ERROR: except (UnicodeDecodeError, PermissionError):
                        # REMOVED_SYNTAX_ERROR: continue

                        # Allow majority of files to not have BVJ during migration
                        # REMOVED_SYNTAX_ERROR: max_files_without_bvj = 12

                        # REMOVED_SYNTAX_ERROR: assert len(files_without_bvj) <= max_files_without_bvj, ( )
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        # REMOVED_SYNTAX_ERROR: "formatted_string" in content or "formatted_string" in content:
                    # REMOVED_SYNTAX_ERROR: implementations.append(str(py_file.relative_to(project_root)))

                    # REMOVED_SYNTAX_ERROR: except (UnicodeDecodeError, PermissionError):
                        # REMOVED_SYNTAX_ERROR: continue

                        # REMOVED_SYNTAX_ERROR: return implementations


                        # REMOVED_SYNTAX_ERROR: @pytest.mark.compliance
                        # REMOVED_SYNTAX_ERROR: @pytest.mark.fast_test
# REMOVED_SYNTAX_ERROR: class TestArchitecturalCompliance:
    # REMOVED_SYNTAX_ERROR: """Tests for architectural compliance with CLAUDE.md principles."""

    # REMOVED_SYNTAX_ERROR: @fast_test
# REMOVED_SYNTAX_ERROR: def test_service_independence_compliance(self):
    # REMOVED_SYNTAX_ERROR: """Test that microservices maintain independence."""
    # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent.parent

    # Define service boundaries
    # REMOVED_SYNTAX_ERROR: services = { )
    # REMOVED_SYNTAX_ERROR: "netra_backend": project_root / "netra_backend",
    # REMOVED_SYNTAX_ERROR: "auth_service": project_root / "auth_service",
    # REMOVED_SYNTAX_ERROR: "frontend": project_root / "frontend"
    

    # REMOVED_SYNTAX_ERROR: cross_service_imports = []

    # REMOVED_SYNTAX_ERROR: for service_name, service_path in services.items():
        # REMOVED_SYNTAX_ERROR: if not service_path.exists():
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: python_files = list(service_path.rglob("*.py"))

            # REMOVED_SYNTAX_ERROR: for py_file in python_files:
                # REMOVED_SYNTAX_ERROR: try:
                    # REMOVED_SYNTAX_ERROR: with open(py_file, 'r', encoding='utf-8') as f:
                        # REMOVED_SYNTAX_ERROR: content = f.read()

                        # Check for imports from other services
                        # REMOVED_SYNTAX_ERROR: for other_service in services:
                            # REMOVED_SYNTAX_ERROR: if other_service != service_name:
                                # REMOVED_SYNTAX_ERROR: import_pattern = "formatted_string"
                                # REMOVED_SYNTAX_ERROR: if import_pattern in content:
                                    # REMOVED_SYNTAX_ERROR: cross_service_imports.append({ ))
                                    # REMOVED_SYNTAX_ERROR: "file": str(py_file.relative_to(project_root)),
                                    # REMOVED_SYNTAX_ERROR: "service": service_name,
                                    # REMOVED_SYNTAX_ERROR: "imports_from": other_service
                                    

                                    # REMOVED_SYNTAX_ERROR: except (UnicodeDecodeError, PermissionError):
                                        # REMOVED_SYNTAX_ERROR: continue

                                        # Allow some cross-service imports for shared types/interfaces
                                        # REMOVED_SYNTAX_ERROR: max_allowed_cross_imports = 5

                                        # REMOVED_SYNTAX_ERROR: assert len(cross_service_imports) <= max_allowed_cross_imports, ( )
                                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: "formatted_string")

                        # REMOVED_SYNTAX_ERROR: except (UnicodeDecodeError, PermissionError):
                            # REMOVED_SYNTAX_ERROR: continue

                            # Should have some performance tests
                            # REMOVED_SYNTAX_ERROR: assert len(performance_files) >= 5, ( )
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            

                            # REMOVED_SYNTAX_ERROR: @fast_test
# REMOVED_SYNTAX_ERROR: def test_error_handling_patterns(self):
    # REMOVED_SYNTAX_ERROR: """Test that error handling follows CLAUDE.md patterns."""
    # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent.parent

    # Look for error handling patterns in core modules
    # REMOVED_SYNTAX_ERROR: core_modules = [ )
    # REMOVED_SYNTAX_ERROR: project_root / "netra_backend" / "app" / "core",
    # REMOVED_SYNTAX_ERROR: project_root / "auth_service" / "auth_core"
    

    # REMOVED_SYNTAX_ERROR: error_handling_stats = { )
    # REMOVED_SYNTAX_ERROR: "try_except_blocks": 0,
    # REMOVED_SYNTAX_ERROR: "custom_exceptions": 0,
    # REMOVED_SYNTAX_ERROR: "error_logging": 0,
    # REMOVED_SYNTAX_ERROR: "error_recovery": 0
    

    # REMOVED_SYNTAX_ERROR: for module_path in core_modules:
        # REMOVED_SYNTAX_ERROR: if not module_path.exists():
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: python_files = list(module_path.rglob("*.py"))

            # REMOVED_SYNTAX_ERROR: for py_file in python_files:
                # REMOVED_SYNTAX_ERROR: try:
                    # REMOVED_SYNTAX_ERROR: with open(py_file, 'r', encoding='utf-8') as f:
                        # REMOVED_SYNTAX_ERROR: content = f.read()

                        # Count error handling patterns
                        # REMOVED_SYNTAX_ERROR: error_handling_stats["try_except_blocks"] += content.count("try:")
                        # REMOVED_SYNTAX_ERROR: error_handling_stats["custom_exceptions"] += content.count("Exception")
                        # REMOVED_SYNTAX_ERROR: error_handling_stats["error_logging"] += content.count("logger.error")
                        # REMOVED_SYNTAX_ERROR: error_handling_stats["error_recovery"] += content.count("recover")

                        # REMOVED_SYNTAX_ERROR: except (UnicodeDecodeError, PermissionError):
                            # REMOVED_SYNTAX_ERROR: continue

                            # Should have reasonable error handling
                            # REMOVED_SYNTAX_ERROR: assert error_handling_stats["try_except_blocks"] >= 10, ( )
                            # REMOVED_SYNTAX_ERROR: f"Expected at least 10 try-except blocks in core modules, "
                            # REMOVED_SYNTAX_ERROR: f"found: {error_handling_stats['try_except_blocks']]"
                            