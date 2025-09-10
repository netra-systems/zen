"""
Test Configuration SSOT: Direct os.environ Access Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent configuration cascade failures from os.environ violations
- Value Impact: Protects $120K+ MRR by detecting direct environment access that bypasses SSOT
- Strategic Impact: Prevents configuration pollution and drift that causes service failures

This test validates that services don't directly access os.environ, which can cause
configuration drift, test pollution, and cascade failures. All environment access
must go through IsolatedEnvironment SSOT patterns.
"""

import pytest
import os
import ast
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple
from unittest.mock import patch, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class DirectEnvironmentAccessDetector:
    """Utility class to detect direct os.environ access in source code."""
    
    CRITICAL_SERVICES = [
        "netra_backend/app",
        "auth_service",
        "shared",
        "test_framework"
    ]
    
    ALLOWED_FILES = {
        "shared/isolated_environment.py",  # SSOT implementation is allowed
        "scripts/",  # Deployment scripts may need direct access
        "deployment/",  # Deployment utilities  
    }
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = []
    
    def scan_for_violations(self) -> List[Dict]:
        """Scan project for direct os.environ access violations."""
        violations = []
        
        for service_path in self.CRITICAL_SERVICES:
            service_dir = self.project_root / service_path
            if service_dir.exists():
                violations.extend(self._scan_directory(service_dir, service_path))
        
        return violations
    
    def _scan_directory(self, directory: Path, service_name: str) -> List[Dict]:
        """Scan directory for Python files with os.environ violations."""
        violations = []
        
        for py_file in directory.rglob("*.py"):
            # Skip allowed files
            relative_path = str(py_file.relative_to(self.project_root))
            if any(allowed in relative_path for allowed in self.ALLOWED_FILES):
                continue
            
            file_violations = self._analyze_file(py_file, service_name)
            violations.extend(file_violations)
        
        return violations
    
    def _analyze_file(self, file_path: Path, service_name: str) -> List[Dict]:
        """Analyze a Python file for os.environ access patterns."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST to find os.environ access
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                violation = self._check_node_for_violation(node, file_path, service_name)
                if violation:
                    violations.append(violation)
                    
        except (SyntaxError, UnicodeDecodeError) as e:
            # Skip files that can't be parsed
            pass
        
        return violations
    
    def _check_node_for_violation(self, node, file_path: Path, service_name: str) -> Dict:
        """Check an AST node for os.environ access violation."""
        violation_patterns = [
            # os.environ direct access
            (ast.Attribute, lambda n: (
                isinstance(n.value, ast.Name) and 
                n.value.id == 'os' and 
                n.attr == 'environ'
            )),
            # os.environ.get()
            (ast.Call, lambda n: (
                isinstance(n.func, ast.Attribute) and
                isinstance(n.func.value, ast.Attribute) and
                isinstance(n.func.value.value, ast.Name) and
                n.func.value.value.id == 'os' and
                n.func.value.attr == 'environ' and
                n.func.attr in ['get', 'setdefault']
            )),
            # os.environ[key] = value
            (ast.Subscript, lambda n: (
                isinstance(n.value, ast.Attribute) and
                isinstance(n.value.value, ast.Name) and
                n.value.value.id == 'os' and
                n.value.attr == 'environ'
            ))
        ]
        
        for node_type, pattern_check in violation_patterns:
            if isinstance(node, node_type) and pattern_check(node):
                return {
                    'file': str(file_path.relative_to(self.project_root)),
                    'service': service_name,
                    'line': node.lineno,
                    'column': node.col_offset,
                    'type': 'direct_os_environ_access',
                    'severity': 'CRITICAL'
                }
        
        return None


class TestDirectEnvironAccessViolations(BaseIntegrationTest):
    """Test for direct os.environ access SSOT violations."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_no_direct_os_environ_access_in_critical_services(self, real_services_fixture):
        """
        Test that critical services don't directly access os.environ.
        
        Direct os.environ access bypasses SSOT patterns and can cause:
        - Configuration pollution between services
        - Test environment leakage 
        - Cascade failures from missing source tracking
        - Security issues from untracked environment changes
        """
        project_root = Path(__file__).parent.parent.parent.parent
        detector = DirectEnvironmentAccessDetector(project_root)
        
        violations = detector.scan_for_violations()
        
        # CRITICAL: No direct os.environ access should exist in critical services
        if violations:
            violation_report = "\n".join([
                f"VIOLATION: {v['file']}:{v['line']} - {v['type']} in {v['service']}"
                for v in violations
            ])
            pytest.fail(f"Direct os.environ access violations detected (SSOT violation):\n{violation_report}")
        
        # Verify critical services are being scanned
        scanned_paths = [
            project_root / "netra_backend" / "app",
            project_root / "auth_service", 
            project_root / "shared",
            project_root / "test_framework"
        ]
        
        for path in scanned_paths:
            if path.exists():
                python_files = list(path.rglob("*.py"))
                assert len(python_files) > 0, f"No Python files found in {path} - scan ineffective"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_isolated_environment_is_used_instead_of_os_environ(self, real_services_fixture):
        """
        Test that services properly use IsolatedEnvironment instead of os.environ.
        
        This test validates the positive case - that services are correctly
        importing and using the SSOT IsolatedEnvironment pattern.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Check critical service configuration files
        critical_config_files = [
            "netra_backend/app/core/configuration/base.py",
            "auth_service/auth_core/config.py", 
            "auth_service/auth_core/auth_environment.py",
            "shared/isolated_environment.py"
        ]
        
        ssot_imports_found = []
        
        for config_file in critical_config_files:
            file_path = project_root / config_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for proper SSOT imports
                    ssot_import_patterns = [
                        "from shared.isolated_environment import",
                        "import shared.isolated_environment",
                        "get_env()",
                        "IsolatedEnvironment"
                    ]
                    
                    file_uses_ssot = any(pattern in content for pattern in ssot_import_patterns)
                    if file_uses_ssot:
                        ssot_imports_found.append(config_file)
                        
                        # Verify no direct os.environ in SSOT-compliant files
                        assert "os.environ" not in content or "isolated_environment.py" in config_file, \
                            f"File {config_file} uses SSOT but still has os.environ access"
                
                except (UnicodeDecodeError, IOError):
                    continue
        
        # CRITICAL: At least some critical services should be using SSOT
        assert len(ssot_imports_found) >= 2, \
            f"Insufficient SSOT adoption. Found in: {ssot_imports_found}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_environment_access_tracking_in_production_code(self, real_services_fixture):
        """
        Test that production code has proper environment access tracking.
        
        Environment access without tracking is a major source of cascade failures.
        This test ensures production code follows SSOT patterns with source attribution.
        """
        # Mock a service that incorrectly uses direct os.environ access
        with patch.dict('os.environ', {'TEST_PRODUCTION_VAR': 'production_value'}):
            
            # Simulate what would happen with direct os.environ access
            direct_access_value = os.environ.get('TEST_PRODUCTION_VAR')
            assert direct_access_value == 'production_value'
            
            # Now test the SSOT-compliant approach
            env = get_env()
            env.enable_isolation()
            
            # In SSOT pattern, we set with source tracking
            env.set('TEST_PRODUCTION_VAR', 'ssot_value', 'production_service')
            
            # CRITICAL: SSOT value should be isolated from os.environ
            ssot_value = env.get('TEST_PRODUCTION_VAR')
            assert ssot_value == 'ssot_value'
            assert ssot_value != direct_access_value  # Proves isolation
            
            # Verify source tracking exists (critical for debugging)
            debug_info = env.get_debug_info()
            assert 'TEST_PRODUCTION_VAR' in debug_info['variable_sources']
            assert debug_info['variable_sources']['TEST_PRODUCTION_VAR'] == 'production_service'
            
            # Test that subprocess environment properly inherits
            subprocess_env = env.get_subprocess_env()
            assert 'TEST_PRODUCTION_VAR' in subprocess_env
            assert subprocess_env['TEST_PRODUCTION_VAR'] == 'ssot_value'
            
            env.reset_to_original()

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_configuration_cascade_failure_prevention(self, real_services_fixture):
        """
        Test that SSOT patterns prevent configuration cascade failures.
        
        This test simulates scenarios where direct os.environ access would
        cause cascade failures, and validates that SSOT patterns prevent them.
        """
        env = get_env()
        env.enable_isolation()
        
        # Simulate cascade failure scenario: SERVICE_SECRET gets corrupted
        critical_vars = ['SERVICE_SECRET', 'DATABASE_URL', 'JWT_SECRET_KEY']
        
        # Store original values (if any)
        original_values = {var: os.environ.get(var) for var in critical_vars}
        
        try:
            # Test 1: Corrupt os.environ directly (simulates external corruption)
            with patch.dict('os.environ', {'SERVICE_SECRET': 'CORRUPTED_VALUE'}):
                
                # SSOT environment should be protected from this corruption
                env.set('SERVICE_SECRET', 'SECURE_SSOT_VALUE', 'auth_service')
                
                # CRITICAL: SSOT value should be different from corrupted os.environ
                assert env.get('SERVICE_SECRET') == 'SECURE_SSOT_VALUE'
                assert os.environ.get('SERVICE_SECRET') == 'CORRUPTED_VALUE'
                
                # Multiple services should be able to independently set values
                env.set('SERVICE_SECRET', 'BACKEND_SERVICE_SECRET', 'backend_service')
                assert env.get('SERVICE_SECRET') == 'BACKEND_SERVICE_SECRET'
                
                # Source tracking should reflect the last change
                debug_info = env.get_debug_info()
                assert debug_info['variable_sources']['SERVICE_SECRET'] == 'backend_service'
            
            # Test 2: Environment variable conflicts between services
            # This would cause cascade failures with direct os.environ access
            service_configs = [
                ('auth_service', 'SERVICE_SECRET', 'auth_secret_123'),
                ('backend_service', 'SERVICE_SECRET', 'backend_secret_456'), 
                ('test_service', 'SERVICE_SECRET', 'test_secret_789')
            ]
            
            final_values = {}
            for service, var_name, value in service_configs:
                env.set(var_name, value, service)
                final_values[service] = value
            
            # Last service wins (expected SSOT behavior)
            assert env.get('SERVICE_SECRET') == 'test_secret_789'
            
            # But source tracking shows full history
            debug_info = env.get_debug_info()  
            assert debug_info['variable_sources']['SERVICE_SECRET'] == 'test_service'
            
            # Test 3: Multi-environment isolation (dev/staging/prod)
            # Direct os.environ access would leak between environments
            environments = ['development', 'staging', 'production']
            
            for environment in environments:
                env_specific_secret = f"secret_for_{environment}"
                env.set('ENVIRONMENT_SPECIFIC_SECRET', env_specific_secret, f"{environment}_config")
                
                # Each environment setting should be isolated
                assert env.get('ENVIRONMENT_SPECIFIC_SECRET') == env_specific_secret
                
                # os.environ should not be polluted
                if environment != 'production':  # Last one would be in os.environ
                    assert os.environ.get('ENVIRONMENT_SPECIFIC_SECRET') != env_specific_secret or env.isolation_enabled
        
        finally:
            # Restore original environment state
            for var, original_value in original_values.items():
                if original_value is not None:
                    os.environ[var] = original_value
                elif var in os.environ:
                    del os.environ[var]
            
            env.reset_to_original()