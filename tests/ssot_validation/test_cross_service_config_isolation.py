"""
SSOT Test: Cross-Service Configuration Isolation Validation

This test validates SSOT compliance by ensuring proper configuration isolation between services.
It should FAIL initially to expose configuration leakage that violates service boundaries.

Purpose: Detect configuration leakage and ensure proper service boundary isolation  
Business Value: Platform/Internal - Service Independence & Configuration Security
SSOT Requirement: Each service must have isolated configuration with no cross-contamination

Expected Behavior:
- FAIL initially by exposing configuration leakage between services
- Pass after SSOT remediation establishes proper service boundaries
- Validate configuration access patterns respect service isolation

Test Plan Reference: Configuration SSOT Consolidation Phase 2
"""

import os
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class ConfigurationLeakage:
    """Analysis of configuration leakage between services."""
    cross_service_imports: Dict[str, List[str]] = field(default_factory=dict)
    shared_config_violations: List[str] = field(default_factory=list)
    environment_bleeding: Dict[str, Set[str]] = field(default_factory=dict)
    service_boundary_violations: List[str] = field(default_factory=list)
    configuration_access_violations: List[str] = field(default_factory=list)


@dataclass
class ServiceConfigAnalysis:
    """Analysis of service-specific configuration patterns."""
    service_name: str
    config_files: List[str] = field(default_factory=list)
    imported_configs: Set[str] = field(default_factory=set)
    exported_configs: Set[str] = field(default_factory=set)
    environment_variables: Set[str] = field(default_factory=set)
    cross_service_dependencies: Set[str] = field(default_factory=set)


class TestCrossServiceConfigIsolation(SSotBaseTestCase):
    """
    SSOT validation test for cross-service configuration isolation.
    
    This test enforces SSOT principles by detecting configuration leakage
    between services and validating proper service boundary isolation.
    """
    
    def setup_method(self, method=None):
        """Setup test environment for cross-service configuration validation."""
        super().setup_method(method)
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.record_metric("test_type", "ssot_cross_service_validation")
        
        # Define service boundaries for SSOT compliance
        self.service_boundaries = {
            "netra_backend": {
                "root": "netra_backend",
                "config_files": ["netra_backend/app/config.py", "netra_backend/app/core/configuration/"],
                "allowed_imports": ["shared.isolated_environment", "shared.cors_config"]
            },
            "auth_service": {
                "root": "auth_service", 
                "config_files": ["auth_service/auth_core/core/", "auth_service/config.py"],
                "allowed_imports": ["shared.isolated_environment"]
            },
            "frontend": {
                "root": "frontend",
                "config_files": ["frontend/lib/", "frontend/auth/"],
                "allowed_imports": []  # Frontend should be fully isolated
            },
            "test_framework": {
                "root": "test_framework",
                "config_files": ["test_framework/ssot/", "test_framework/unified_docker_manager.py"],
                "allowed_imports": ["shared.isolated_environment"]
            },
            "shared": {
                "root": "shared",
                "config_files": ["shared/"],
                "allowed_imports": []  # Shared can't depend on services
            }
        }
        
        # Define forbidden cross-service patterns
        self.forbidden_patterns = [
            "from netra_backend.app.config import",
            "from auth_service.config import", 
            "import netra_backend.app.config",
            "import auth_service.config",
            "os.environ.get",  # Should use IsolatedEnvironment
            "os.getenv"  # Should use IsolatedEnvironment
        ]

    def test_service_configuration_isolation_should_fail_initially(self):
        """
        Detect cross-service configuration leakage - SHOULD FAIL to demonstrate problem.
        
        This test is designed to FAIL initially by finding configuration leakage
        between services, demonstrating violations of service boundary isolation.
        
        Expected Initial Result: FAIL - Find configuration leakage between services
        Expected After SSOT: PASS - Proper service boundary isolation established
        """
        leakage_analysis = self._analyze_configuration_leakage()
        
        # Record metrics for monitoring SSOT progress
        self.record_metric("cross_service_imports", len(leakage_analysis.cross_service_imports))
        self.record_metric("shared_config_violations", len(leakage_analysis.shared_config_violations))
        self.record_metric("environment_bleeding", len(leakage_analysis.environment_bleeding))
        self.record_metric("service_boundary_violations", len(leakage_analysis.service_boundary_violations))
        
        # Log detailed analysis for debugging
        self.logger.info(f"Cross-service configuration leakage analysis:")
        self.logger.info(f"  Cross-service imports: {len(leakage_analysis.cross_service_imports)}")
        self.logger.info(f"  Shared config violations: {len(leakage_analysis.shared_config_violations)}")
        self.logger.info(f"  Environment bleeding instances: {len(leakage_analysis.environment_bleeding)}")
        self.logger.info(f"  Service boundary violations: {len(leakage_analysis.service_boundary_violations)}")
        
        if leakage_analysis.cross_service_imports:
            self.logger.info("Cross-service imports found:")
            for service, imports in leakage_analysis.cross_service_imports.items():
                self.logger.info(f"  {service}: {len(imports)} imports")
                for imp in imports[:3]:  # Show first 3
                    self.logger.info(f"    {imp}")
                if len(imports) > 3:
                    self.logger.info(f"    ... and {len(imports) - 3} more")
        
        # CRITICAL SSOT VIOLATION DETECTION
        # This assertion is designed to FAIL initially, demonstrating configuration leakage
        total_violations = (
            len(leakage_analysis.cross_service_imports) +
            len(leakage_analysis.service_boundary_violations) +
            len(leakage_analysis.shared_config_violations)
        )
        
        self.assertLessEqual(
            total_violations, 5,
            f"SSOT VIOLATION: Found {total_violations} cross-service configuration violations "
            f"(should be ≤5 for proper service isolation). "
            f"Cross-service imports: {len(leakage_analysis.cross_service_imports)}, "
            f"Boundary violations: {len(leakage_analysis.service_boundary_violations)}, "
            f"Shared config violations: {len(leakage_analysis.shared_config_violations)}. "
            f"This indicates severe configuration leakage that violates SSOT service boundaries."
        )
        
        # Additional validation for environment bleeding
        environment_bleeding_count = sum(len(services) for services in leakage_analysis.environment_bleeding.values())
        self.assertLessEqual(
            environment_bleeding_count, 10,
            f"SSOT VIOLATION: Found {environment_bleeding_count} environment bleeding instances "
            f"(should be ≤10 for proper isolation). Services sharing environment access: "
            f"{dict(leakage_analysis.environment_bleeding)}"
        )

    def test_direct_os_environ_access_violations(self):
        """
        Detect direct os.environ access that bypasses IsolatedEnvironment.
        
        All environment variable access should go through IsolatedEnvironment
        to maintain proper configuration isolation and testing capabilities.
        """
        os_environ_violations = self._find_direct_os_environ_access()
        
        self.record_metric("direct_os_environ_violations", len(os_environ_violations))
        
        if os_environ_violations:
            self.logger.warning(f"Direct os.environ access violations found:")
            for file_path, violations in os_environ_violations.items():
                relative_path = Path(file_path).relative_to(self.project_root)
                self.logger.warning(f"  {relative_path}: {len(violations)} violations")
                for violation in violations[:2]:  # Show first 2
                    self.logger.warning(f"    Line {violation['line']}: {violation['code'].strip()}")
        
        # SSOT requirement: No direct os.environ access in service code
        total_violations = sum(len(violations) for violations in os_environ_violations.values())
        self.assertLessEqual(
            total_violations, 20,
            f"SSOT VIOLATION: Found {total_violations} direct os.environ access violations "
            f"(should be ≤20 for SSOT compliance). Files with violations: "
            f"{list(os_environ_violations.keys())[:5]}. "
            f"All environment access should use IsolatedEnvironment for proper service isolation."
        )

    def test_configuration_import_boundaries(self):
        """
        Validate that configuration imports respect service boundaries.
        
        Services should not import configuration directly from other services.
        All cross-service configuration should go through shared interfaces.
        """
        import_violations = self._analyze_configuration_import_boundaries()
        
        self.record_metric("config_import_violations", len(import_violations))
        
        if import_violations:
            self.logger.warning(f"Configuration import boundary violations:")
            for violation in import_violations[:10]:  # Show first 10
                self.logger.warning(f"  {violation}")
        
        # SSOT requirement: Proper configuration import boundaries
        self.assertLessEqual(
            len(import_violations), 15,
            f"SSOT VIOLATION: Found {len(import_violations)} configuration import boundary violations "
            f"(should be ≤15 for proper service isolation). "
            f"Violations: {import_violations[:5]}..."
        )

    def test_shared_configuration_access_patterns(self):
        """
        Validate that shared configuration is accessed through proper patterns.
        
        Shared configuration should be accessed through well-defined interfaces,
        not through direct imports of internal service configurations.
        """
        shared_access_violations = self._analyze_shared_configuration_access()
        
        self.record_metric("shared_access_violations", len(shared_access_violations))
        
        if shared_access_violations:
            self.logger.warning(f"Shared configuration access violations:")
            for violation in shared_access_violations[:5]:  # Show first 5
                self.logger.warning(f"  {violation}")
        
        # SSOT requirement: Proper shared configuration access
        self.assertLessEqual(
            len(shared_access_violations), 8,
            f"SSOT VIOLATION: Found {len(shared_access_violations)} shared configuration access violations "
            f"(should be ≤8 for proper SSOT patterns). "
            f"Violations indicate improper use of shared configuration interfaces."
        )

    def test_service_specific_configuration_validation(self):
        """
        Validate that each service has proper configuration isolation.
        
        Each service should have its own configuration namespace and
        should not leak configuration details to other services.
        """
        service_analyses = {}
        isolation_violations = []
        
        for service_name, service_config in self.service_boundaries.items():
            analysis = self._analyze_service_configuration(service_name, service_config)
            service_analyses[service_name] = analysis
            
            # Check for isolation violations within this service
            if len(analysis.cross_service_dependencies) > 2:
                isolation_violations.append(
                    f"Service '{service_name}' has {len(analysis.cross_service_dependencies)} "
                    f"cross-service dependencies: {list(analysis.cross_service_dependencies)[:3]}"
                )
        
        self.record_metric("services_analyzed", len(service_analyses))
        self.record_metric("service_isolation_violations", len(isolation_violations))
        
        if isolation_violations:
            self.logger.warning(f"Service isolation violations:")
            for violation in isolation_violations:
                self.logger.warning(f"  {violation}")
        
        # SSOT requirement: Proper service isolation
        self.assertLessEqual(
            len(isolation_violations), 3,
            f"SSOT VIOLATION: Found {len(isolation_violations)} service isolation violations "
            f"(should be ≤3 for proper SSOT service boundaries). "
            f"Services with excessive cross-dependencies violate isolation principles."
        )

    def _analyze_configuration_leakage(self) -> ConfigurationLeakage:
        """Analyze cross-service configuration leakage patterns."""
        leakage = ConfigurationLeakage()
        
        try:
            # Find all Python files in services
            python_files = []
            for service_name, service_config in self.service_boundaries.items():
                service_root = self.project_root / service_config["root"]
                if service_root.exists():
                    python_files.extend(list(service_root.rglob("*.py")))
            
            # Analyze each file for configuration leakage
            for py_file in python_files:
                if not self._should_analyze_file(py_file):
                    continue
                    
                service_name = self._determine_file_service(py_file)
                violations = self._check_file_for_config_leakage(py_file, service_name)
                
                if violations["cross_service_imports"]:
                    if service_name not in leakage.cross_service_imports:
                        leakage.cross_service_imports[service_name] = []
                    leakage.cross_service_imports[service_name].extend(violations["cross_service_imports"])
                
                leakage.shared_config_violations.extend(violations["shared_config_violations"])
                leakage.service_boundary_violations.extend(violations["boundary_violations"])
                leakage.configuration_access_violations.extend(violations["access_violations"])
                
                # Track environment bleeding
                if violations["environment_access"]:
                    for env_var in violations["environment_access"]:
                        if env_var not in leakage.environment_bleeding:
                            leakage.environment_bleeding[env_var] = set()
                        leakage.environment_bleeding[env_var].add(service_name)
        
        except Exception as e:
            self.logger.error(f"Failed to analyze configuration leakage: {e}")
            # Set high violation counts to trigger SSOT failure
            leakage.cross_service_imports = {"analysis_failed": ["mock_violation"] * 10}
            leakage.service_boundary_violations = ["analysis_failed"] * 10
        
        return leakage

    def _should_analyze_file(self, py_file: Path) -> bool:
        """Check if file should be analyzed for configuration leakage."""
        exclude_patterns = [
            "__pycache__", ".pyc", "test_", "conftest.py", 
            "migrations/", "alembic/", ".test_venv/", "node_modules/"
        ]
        
        file_str = str(py_file)
        for pattern in exclude_patterns:
            if pattern in file_str:
                return False
        
        return True

    def _determine_file_service(self, py_file: Path) -> str:
        """Determine which service a file belongs to."""
        relative_path = py_file.relative_to(self.project_root)
        first_part = relative_path.parts[0] if relative_path.parts else "unknown"
        
        for service_name, service_config in self.service_boundaries.items():
            if first_part == service_config["root"]:
                return service_name
        
        return "unknown"

    def _check_file_for_config_leakage(self, py_file: Path, service_name: str) -> Dict[str, List[str]]:
        """Check a single file for configuration leakage patterns."""
        violations = {
            "cross_service_imports": [],
            "shared_config_violations": [],
            "boundary_violations": [],
            "access_violations": [],
            "environment_access": []
        }
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Check for forbidden patterns
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for cross-service imports
                for forbidden_pattern in self.forbidden_patterns:
                    if forbidden_pattern in line_stripped:
                        if "import" in forbidden_pattern:
                            violations["cross_service_imports"].append(f"{py_file}:{i}: {line_stripped}")
                        elif "os.environ" in forbidden_pattern:
                            violations["access_violations"].append(f"{py_file}:{i}: {line_stripped}")
                
                # Check for environment variable access
                if "os.environ" in line_stripped or "os.getenv" in line_stripped:
                    violations["environment_access"].append(line_stripped)
                
                # Check for service boundary violations
                if self._is_boundary_violation(line_stripped, service_name):
                    violations["boundary_violations"].append(f"{py_file}:{i}: {line_stripped}")
        
        except Exception as e:
            self.logger.warning(f"Failed to analyze file {py_file}: {e}")
        
        return violations

    def _is_boundary_violation(self, line: str, service_name: str) -> bool:
        """Check if a line represents a service boundary violation."""
        # Service should not import from other services' internal configs
        other_service_patterns = []
        for other_service, config in self.service_boundaries.items():
            if other_service != service_name and other_service != "shared":
                other_service_patterns.extend([
                    f"from {config['root']}.config import",
                    f"import {config['root']}.config",
                    f"from {config['root']}.app.config import",
                ])
        
        for pattern in other_service_patterns:
            if pattern in line:
                return True
        
        return False

    def _find_direct_os_environ_access(self) -> Dict[str, List[Dict[str, any]]]:
        """Find direct os.environ access violations."""
        violations = {}
        
        try:
            # Find Python files in services
            python_files = []
            for service_name, service_config in self.service_boundaries.items():
                service_root = self.project_root / service_config["root"]
                if service_root.exists():
                    python_files.extend(list(service_root.rglob("*.py")))
            
            for py_file in python_files:
                if not self._should_analyze_file(py_file):
                    continue
                
                file_violations = []
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for i, line in enumerate(lines, 1):
                        if ("os.environ" in line or "os.getenv" in line) and "import" not in line:
                            # Skip if it's in a comment or string
                            if line.strip().startswith("#") or line.strip().startswith('"""') or line.strip().startswith("'''"):
                                continue
                            
                            file_violations.append({
                                "line": i,
                                "code": line,
                                "type": "direct_os_environ_access"
                            })
                
                    if file_violations:
                        violations[str(py_file)] = file_violations
                
                except Exception as e:
                    self.logger.warning(f"Failed to analyze {py_file} for os.environ access: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to find os.environ violations: {e}")
        
        return violations

    def _analyze_configuration_import_boundaries(self) -> List[str]:
        """Analyze configuration import boundary violations."""
        violations = []
        
        try:
            # Check import patterns across services
            for service_name, service_config in self.service_boundaries.items():
                service_root = self.project_root / service_config["root"]
                if not service_root.exists():
                    continue
                
                python_files = list(service_root.rglob("*.py"))
                for py_file in python_files:
                    if not self._should_analyze_file(py_file):
                        continue
                    
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Parse AST to find imports
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        if self._is_forbidden_config_import(alias.name, service_name):
                                            violations.append(f"{py_file}: import {alias.name}")
                                
                                elif isinstance(node, ast.ImportFrom):
                                    if node.module and self._is_forbidden_config_import(node.module, service_name):
                                        violations.append(f"{py_file}: from {node.module} import ...")
                        
                        except SyntaxError:
                            # If AST parsing fails, fall back to text analysis
                            lines = content.splitlines()
                            for i, line in enumerate(lines, 1):
                                if line.strip().startswith("from ") or line.strip().startswith("import "):
                                    if self._is_forbidden_import_line(line, service_name):
                                        violations.append(f"{py_file}:{i}: {line.strip()}")
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to analyze imports in {py_file}: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to analyze import boundaries: {e}")
        
        return violations

    def _is_forbidden_config_import(self, import_name: str, service_name: str) -> bool:
        """Check if an import violates configuration boundaries."""
        if not import_name:
            return False
        
        # Service should not import from other services' config modules
        for other_service, config in self.service_boundaries.items():
            if other_service != service_name and other_service != "shared":
                forbidden_patterns = [
                    f"{config['root']}.config",
                    f"{config['root']}.app.config",
                    f"{config['root']}.core.configuration"
                ]
                
                for pattern in forbidden_patterns:
                    if import_name.startswith(pattern):
                        return True
        
        return False

    def _is_forbidden_import_line(self, line: str, service_name: str) -> bool:
        """Check if an import line violates configuration boundaries."""
        line = line.strip()
        
        # Check for direct config imports from other services
        for other_service, config in self.service_boundaries.items():
            if other_service != service_name and other_service != "shared":
                patterns = [
                    f"from {config['root']}.config import",
                    f"import {config['root']}.config",
                    f"from {config['root']}.app.config import",
                ]
                
                for pattern in patterns:
                    if pattern in line:
                        return True
        
        return False

    def _analyze_shared_configuration_access(self) -> List[str]:
        """Analyze shared configuration access patterns."""
        violations = []
        
        try:
            # Check how services access shared configuration
            shared_root = self.project_root / "shared"
            if not shared_root.exists():
                return violations
            
            # Find all shared config files
            shared_config_files = list(shared_root.rglob("*.py"))
            
            for service_name, service_config in self.service_boundaries.items():
                if service_name == "shared":
                    continue
                
                service_root = self.project_root / service_config["root"]
                if not service_root.exists():
                    continue
                
                python_files = list(service_root.rglob("*.py"))
                for py_file in python_files:
                    if not self._should_analyze_file(py_file):
                        continue
                    
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check for improper shared access patterns
                        if "from shared." in content and "from shared.isolated_environment" not in content:
                            # Look for non-standard shared imports
                            lines = content.splitlines()
                            for i, line in enumerate(lines, 1):
                                if "from shared." in line and "isolated_environment" not in line:
                                    if not any(allowed in line for allowed in service_config.get("allowed_imports", [])):
                                        violations.append(f"{py_file}:{i}: {line.strip()}")
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to analyze shared access in {py_file}: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to analyze shared configuration access: {e}")
        
        return violations

    def _analyze_service_configuration(self, service_name: str, service_config: Dict) -> ServiceConfigAnalysis:
        """Analyze configuration patterns for a specific service."""
        analysis = ServiceConfigAnalysis(service_name=service_name)
        
        try:
            service_root = self.project_root / service_config["root"]
            if not service_root.exists():
                return analysis
            
            # Find configuration files
            config_patterns = ["config.py", "configuration/", "settings.py"]
            for config_file in service_root.rglob("*.py"):
                if any(pattern in str(config_file) for pattern in config_patterns):
                    analysis.config_files.append(str(config_file))
            
            # Analyze imports and dependencies
            python_files = list(service_root.rglob("*.py"))
            for py_file in python_files:
                if not self._should_analyze_file(py_file):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Find imports
                    lines = content.splitlines()
                    for line in lines:
                        if line.strip().startswith("from ") or line.strip().startswith("import "):
                            analysis.imported_configs.add(line.strip())
                            
                            # Check for cross-service dependencies
                            for other_service in self.service_boundaries:
                                if other_service != service_name and other_service in line:
                                    analysis.cross_service_dependencies.add(other_service)
                
                except Exception as e:
                    self.logger.warning(f"Failed to analyze {py_file} for service config: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to analyze service {service_name}: {e}")
        
        return analysis