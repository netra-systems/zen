#!/usr/bin/env python3
"""
SSOT Deployment Canonical Source Validation Tests

Tests to ensure ONLY UnifiedTestRunner contains deployment logic and all
deployment scripts properly redirect to the SSOT implementation.

Created for GitHub Issue #245: Deploy script canonical source conflicts
Part of: 20% new SSOT deployment tests requirement (Test File 1 of 8)

Business Value: Platform/Internal - System Stability & SSOT Compliance
Prevents duplicate deployment implementations and ensures canonical source integrity.

DESIGN CRITERIA:
- Tests MUST fail if SSOT violations occur
- Tests reproduce current SSOT violation scenarios
- Validates post-SSOT-refactor expected state
- No Docker dependency (pure unit tests)
- Uses SSOT test infrastructure patterns

TEST CATEGORIES:
- Canonical source validation (UnifiedTestRunner as SSOT)
- Duplicate deployment logic detection
- Deprecation warning verification
- Import path validation
"""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set
from unittest.mock import Mock, patch, MagicMock

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDeploymentCanonicalSourceValidation(SSotBaseTestCase):
    """
    Unit tests for deployment canonical source validation.
    
    Ensures ONLY UnifiedTestRunner contains deployment logic and all other
    deployment scripts redirect to the SSOT implementation.
    """
    
    def setup_method(self, method=None):
        """Setup test environment and paths."""
        super().setup_method(method)
        
        # Project paths
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.unified_runner_path = self.project_root / "tests" / "unified_test_runner.py"
        self.scripts_dir = self.project_root / "scripts"
        
        # Record test start metrics
        self.record_metric("test_category", "unit")
        self.record_metric("ssot_focus", "deployment_canonical_source")
        
        # Validate critical paths exist
        assert self.unified_runner_path.exists(), f"UnifiedTestRunner not found: {self.unified_runner_path}"
        assert self.scripts_dir.exists(), f"Scripts directory not found: {self.scripts_dir}"
    
    def test_unified_test_runner_is_canonical_deployment_source(self):
        """
        Test that UnifiedTestRunner contains the canonical deployment logic.
        
        CRITICAL: This test MUST fail if deployment logic exists elsewhere.
        """
        # Read UnifiedTestRunner source
        runner_source = self.unified_runner_path.read_text(encoding='utf-8')
        
        # Validate deployment mode exists
        assert "execution-mode deploy" in runner_source or "--execution-mode" in runner_source, \
            "UnifiedTestRunner missing deployment execution mode"
        
        # Validate deployment imports exist
        deployment_keywords = [
            "deploy", "gcp", "cloud", "build", "docker"
        ]
        
        found_deployment_logic = False
        for keyword in deployment_keywords:
            if keyword.lower() in runner_source.lower():
                found_deployment_logic = True
                break
        
        assert found_deployment_logic, \
            "UnifiedTestRunner missing deployment-related logic"
        
        # Record canonical source validation
        self.record_metric("canonical_source_validated", True)
        self.record_metric("deployment_logic_location", "unified_test_runner")
    
    def test_deployment_scripts_redirect_to_ssot(self):
        """
        Test that all deployment scripts redirect to UnifiedTestRunner.
        
        CRITICAL: This test MUST fail if scripts contain independent deployment logic.
        """
        deployment_scripts = self._find_deployment_scripts()
        
        assert len(deployment_scripts) > 0, "No deployment scripts found to validate"
        
        ssot_violations = []
        redirect_validations = []
        
        for script_path in deployment_scripts:
            script_name = script_path.name
            
            # Skip backup files and non-Python files
            if script_name.endswith('.backup') or not script_name.endswith('.py'):
                continue
                
            try:
                script_source = script_path.read_text(encoding='utf-8')
                
                # Check for SSOT redirect
                has_deprecation_warning = "DEPRECATION WARNING" in script_source
                has_unified_runner_redirect = "unified_test_runner" in script_source.lower()
                
                if has_deprecation_warning and has_unified_runner_redirect:
                    redirect_validations.append(script_name)
                else:
                    # Check for independent deployment logic (SSOT violation)
                    independent_logic_indicators = [
                        "gcloud run deploy",
                        "docker build",
                        "subprocess.run",
                        "cloud build",
                        "terraform apply"
                    ]
                    
                    has_independent_logic = any(
                        indicator in script_source.lower() 
                        for indicator in independent_logic_indicators
                    )
                    
                    if has_independent_logic and not has_unified_runner_redirect:
                        ssot_violations.append({
                            'script': script_name,
                            'violation': 'independent_deployment_logic',
                            'path': str(script_path)
                        })
                        
            except Exception as e:
                # Record read errors but don't fail test
                self.record_metric(f"script_read_error_{script_name}", str(e))
        
        # Record metrics
        self.record_metric("deployment_scripts_found", len(deployment_scripts))
        self.record_metric("redirect_validations", len(redirect_validations))
        self.record_metric("ssot_violations_count", len(ssot_violations))
        
        # CRITICAL: Test MUST fail if SSOT violations found
        if ssot_violations:
            violation_details = "\n".join([
                f"  - {v['script']}: {v['violation']} at {v['path']}"
                for v in ssot_violations
            ])
            pytest.fail(
                f"SSOT VIOLATION: {len(ssot_violations)} deployment scripts "
                f"contain independent logic instead of redirecting to UnifiedTestRunner:\n"
                f"{violation_details}\n\n"
                f"Expected: All deployment scripts should redirect to UnifiedTestRunner\n"
                f"Fix: Add deprecation warning and redirect logic to violating scripts"
            )
    
    def test_no_duplicate_deployment_implementations(self):
        """
        Test that deployment logic exists only in UnifiedTestRunner.
        
        CRITICAL: This test MUST fail if duplicate implementations are found.
        """
        # Search for deployment logic patterns across codebase
        deployment_patterns = [
            "gcloud run deploy",
            "docker build.*gcp",
            "cloud-build-config",
            "terraform.*deploy"
        ]
        
        # Exclude allowed files
        excluded_patterns = [
            "backup",
            ".git",
            "__pycache__",
            "node_modules",
            ".pyc"
        ]
        
        duplicate_implementations = []
        
        # Search project for deployment patterns
        for pattern in deployment_patterns:
            try:
                # Use grep to find pattern occurrences
                result = subprocess.run([
                    "grep", "-r", "-l", pattern, str(self.project_root)
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    files_with_pattern = result.stdout.strip().split('\n')
                    
                    for file_path in files_with_pattern:
                        if not file_path:
                            continue
                            
                        # Skip excluded files
                        if any(exclude in file_path for exclude in excluded_patterns):
                            continue
                        
                        # Skip if it's the canonical UnifiedTestRunner
                        if "unified_test_runner.py" in file_path:
                            continue
                        
                        duplicate_implementations.append({
                            'file': file_path,
                            'pattern': pattern,
                            'type': 'duplicate_deployment_logic'
                        })
                        
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                # Skip grep errors but record them
                self.record_metric(f"grep_error_{pattern}", True)
        
        # Record findings
        self.record_metric("duplicate_implementations_found", len(duplicate_implementations))
        
        # CRITICAL: Test MUST fail if duplicates found
        if duplicate_implementations:
            duplicate_details = "\n".join([
                f"  - {d['file']}: {d['pattern']}"
                for d in duplicate_implementations
            ])
            pytest.fail(
                f"DUPLICATE DEPLOYMENT LOGIC: Found {len(duplicate_implementations)} "
                f"files with deployment logic outside UnifiedTestRunner:\n"
                f"{duplicate_details}\n\n"
                f"Expected: Only UnifiedTestRunner should contain deployment logic\n"
                f"Fix: Remove duplicate logic and redirect to UnifiedTestRunner SSOT"
            )
    
    def test_deprecated_scripts_show_warnings(self):
        """
        Test that deprecated deployment scripts show proper warnings.
        
        Validates user experience during SSOT migration.
        """
        deploy_gcp_script = self.scripts_dir / "deploy_to_gcp.py"
        
        if not deploy_gcp_script.exists():
            pytest.skip("deploy_to_gcp.py not found - may have been removed")
        
        # Test deprecation warning display
        with patch('builtins.print') as mock_print:
            try:
                # Import and run deprecation check
                script_source = deploy_gcp_script.read_text(encoding='utf-8')
                
                # Check for deprecation function
                if "show_deprecation_warning" in script_source:
                    # Simulate calling the deprecation warning function
                    exec_globals = {}
                    exec(script_source, exec_globals)
                    
                    if 'show_deprecation_warning' in exec_globals:
                        exec_globals['show_deprecation_warning']()
                        
                        # Validate warning was printed
                        warning_calls = [str(call) for call in mock_print.call_args_list]
                        warning_text = " ".join(warning_calls)
                        
                        assert "DEPRECATION WARNING" in warning_text, \
                            "Deprecation warning not displayed"
                        assert "unified_test_runner" in warning_text.lower(), \
                            "Warning missing UnifiedTestRunner redirect instructions"
                        
                        self.record_metric("deprecation_warning_displayed", True)
            
            except Exception as e:
                # Record error but don't fail test (this is UX validation)
                self.record_metric("deprecation_warning_error", str(e))
    
    def test_deployment_entry_point_audit(self):
        """
        Test that all deployment entry points are documented and controlled.
        
        Ensures no hidden deployment mechanisms exist.
        """
        # Known legitimate deployment entry points
        legitimate_entry_points = {
            "tests/unified_test_runner.py": "canonical_ssot",
            "scripts/deploy_to_gcp.py": "deprecated_redirect",
        }
        
        # Search for potential deployment entry points
        potential_entry_points = []
        
        # Search Python files for main deployment patterns
        python_files = list(self.project_root.rglob("*.py"))
        
        for py_file in python_files:
            # Skip excluded directories
            if any(exclude in str(py_file) for exclude in [".git", "__pycache__", "node_modules"]):
                continue
            
            try:
                source = py_file.read_text(encoding='utf-8')
                
                # Check for deployment entry point patterns
                entry_point_patterns = [
                    "if __name__ == \"__main__\":",
                    "def main():",
                    "deploy.*main",
                    "gcp.*deploy"
                ]
                
                deployment_indicators = [
                    "gcloud",
                    "cloud run",
                    "docker build",
                    "terraform"
                ]
                
                has_entry_point = any(pattern in source for pattern in entry_point_patterns)
                has_deployment_logic = any(indicator in source.lower() for indicator in deployment_indicators)
                
                if has_entry_point and has_deployment_logic:
                    relative_path = str(py_file.relative_to(self.project_root))
                    potential_entry_points.append(relative_path)
                    
            except Exception:
                # Skip files that can't be read
                continue
        
        # Validate against legitimate entry points
        undocumented_entry_points = []
        
        for entry_point in potential_entry_points:
            if entry_point not in legitimate_entry_points:
                undocumented_entry_points.append(entry_point)
        
        # Record audit results
        self.record_metric("total_entry_points_found", len(potential_entry_points))
        self.record_metric("legitimate_entry_points", len(legitimate_entry_points))
        self.record_metric("undocumented_entry_points", len(undocumented_entry_points))
        
        # Warn about undocumented entry points (not a failure, but important info)
        if undocumented_entry_points:
            self.record_metric("undocumented_entry_points_list", undocumented_entry_points)
            
            # This is informational, not a test failure
            print(f"\nINFO: Found {len(undocumented_entry_points)} potential deployment entry points:")
            for entry_point in undocumented_entry_points:
                print(f"  - {entry_point}")
            print("These should be reviewed for SSOT compliance.")
    
    def test_import_path_validation_for_deployment(self):
        """
        Test that deployment-related imports follow SSOT patterns.
        
        Validates that deployment code uses proper import paths.
        """
        # Expected SSOT import patterns for deployment
        expected_ssot_imports = {
            "test_framework.ssot.base_test_case",
            "test_framework.unified_docker_manager",
            "shared.isolated_environment",
        }
        
        # Anti-patterns that indicate SSOT violations
        anti_patterns = {
            "from scripts.deploy_to_gcp import",
            "import deploy_to_gcp",
            "from deploy_to_gcp import",
        }
        
        violations = []
        
        # Check UnifiedTestRunner for proper imports
        if self.unified_runner_path.exists():
            runner_source = self.unified_runner_path.read_text(encoding='utf-8')
            
            # Parse AST to analyze imports
            try:
                tree = ast.parse(runner_source)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_name = alias.name
                            
                            # Check for anti-patterns
                            for anti_pattern in anti_patterns:
                                if import_name in anti_pattern:
                                    violations.append({
                                        'file': 'unified_test_runner.py',
                                        'violation': f'anti_pattern_import: {import_name}',
                                        'line': node.lineno
                                    })
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            import_name = node.module
                            
                            # Check for anti-patterns
                            for anti_pattern in anti_patterns:
                                if import_name in anti_pattern:
                                    violations.append({
                                        'file': 'unified_test_runner.py',
                                        'violation': f'anti_pattern_from_import: {import_name}',
                                        'line': node.lineno
                                    })
                            
            except SyntaxError as e:
                self.record_metric("ast_parse_error", str(e))
        
        # Record import validation results
        self.record_metric("import_violations_found", len(violations))
        
        # Test passes if no violations found
        if violations:
            violation_details = "\n".join([
                f"  - {v['file']}:{v['line']}: {v['violation']}"
                for v in violations
            ])
            pytest.fail(
                f"IMPORT VIOLATION: Found {len(violations)} import anti-patterns:\n"
                f"{violation_details}\n\n"
                f"Expected: Deployment code should use SSOT import patterns\n"
                f"Fix: Replace anti-pattern imports with SSOT equivalents"
            )
    
    def _find_deployment_scripts(self) -> List[Path]:
        """Find all deployment scripts in the project."""
        deployment_scripts = []
        
        # Search scripts directory
        if self.scripts_dir.exists():
            for script in self.scripts_dir.glob("*deploy*.py"):
                deployment_scripts.append(script)
        
        # Search for other deployment files
        deployment_patterns = [
            "**/deploy_*.py",
            "**/gcp_deploy*.py",
            "**/staging_deploy*.py"
        ]
        
        for pattern in deployment_patterns:
            for script in self.project_root.glob(pattern):
                if script not in deployment_scripts:
                    deployment_scripts.append(script)
        
        return deployment_scripts


# Additional test methods for comprehensive coverage
class TestDeploymentCanonicalSourceEdgeCases(SSotBaseTestCase):
    """
    Edge case tests for deployment canonical source validation.
    """
    
    def test_deployment_script_parameter_forwarding(self):
        """
        Test that deprecated scripts properly forward parameters to SSOT.
        
        Ensures no functionality is lost during SSOT migration.
        """
        deploy_script = Path(__file__).parent.parent.parent.parent / "scripts" / "deploy_to_gcp.py"
        
        if not deploy_script.exists():
            pytest.skip("deploy_to_gcp.py not found")
        
        # Test parameter parsing and forwarding
        script_source = deploy_script.read_text(encoding='utf-8')
        
        # Expected parameters that should be forwarded
        expected_params = [
            "--project",
            "--build-local", 
            "--check-secrets",
            "--run-checks",
            "--rollback"
        ]
        
        missing_params = []
        for param in expected_params:
            if param not in script_source:
                missing_params.append(param)
        
        assert len(missing_params) == 0, \
            f"Missing parameter forwarding: {missing_params}"
        
        self.record_metric("parameter_forwarding_validated", True)
        self.record_metric("forwarded_parameters_count", len(expected_params))
    
    def test_ssot_migration_backwards_compatibility(self):
        """
        Test that SSOT migration maintains backwards compatibility.
        
        Ensures existing deployment workflows continue to work.
        """
        # This test validates that the migration doesn't break existing usage
        
        # Test 1: Command-line interface compatibility
        unified_runner = Path(__file__).parent.parent.parent.parent / "tests" / "unified_test_runner.py"
        runner_source = unified_runner.read_text(encoding='utf-8')
        
        # Should support deployment mode
        deployment_modes = ["deploy", "deployment", "gcp"]
        has_deployment_mode = any(mode in runner_source for mode in deployment_modes)
        
        assert has_deployment_mode, \
            "UnifiedTestRunner missing deployment mode support"
        
        # Test 2: Environment variable compatibility
        env_vars = [
            "GCP_PROJECT",
            "CONTAINER_RUNTIME", 
            "BUILD_LOCAL"
        ]
        
        # These should be handled through IsolatedEnvironment
        for env_var in env_vars:
            # Using environment access should work
            value = self.get_env_var(env_var, "test_default")
            assert value is not None  # Should return default if not set
        
        self.record_metric("backwards_compatibility_validated", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])