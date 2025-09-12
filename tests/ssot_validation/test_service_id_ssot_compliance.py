"""
SSOT Validation Test: SERVICE_ID SSOT Compliance Validation

PHASE 2: CREATE PASSING TEST - Validate Ideal SSOT State

Purpose: This test MUST PASS after SSOT remediation to validate that SERVICE_ID
follows single source of truth pattern with centralized constant.

Business Value: Platform/Critical - Ensures SERVICE_ID SSOT compliance 
prevents authentication failures and maintains $500K+ ARR stability.

Expected Behavior:
- FAIL: Initially when SSOT constant doesn't exist
- PASS: After SSOT remediation with centralized SERVICE_ID constant

CRITICAL: This test validates the Golden Path: users login  ->  get AI responses
"""

import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Set

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestServiceIdSsotCompliance(SSotBaseTestCase):
    """
    Validate SERVICE_ID SSOT compliance across the entire codebase.
    
    This test ensures that after SSOT remediation:
    1. Single centralized SERVICE_ID constant exists
    2. All services import from the same source
    3. No hardcoded "netra-backend" strings remain
    4. No environment variable dependencies exist
    
    EXPECTED TO PASS: After SSOT remediation is complete
    """
    
    def setup_method(self, method=None):
        """Setup test environment with SSOT compliance metrics."""
        super().setup_method(method)
        self.record_metric("test_category", "ssot_compliance")
        self.record_metric("business_impact", "ensures_service_id_consistency")
        self.record_metric("compliance_target", "100%")
        
    def test_service_id_ssot_constant_exists(self):
        """
        PASSING TEST: Validate centralized SERVICE_ID constant exists.
        
        This test validates that a single, centralized SERVICE_ID constant
        exists in the expected location and is properly defined.
        """
        ssot_constant_info = self._validate_ssot_constant_exists()
        
        self.record_metric("ssot_constant_found", ssot_constant_info["exists"])
        self.record_metric("ssot_constant_path", ssot_constant_info["path"])
        self.record_metric("ssot_constant_value", ssot_constant_info["value"])
        
        print(f"SSOT CONSTANT INFO: {ssot_constant_info}")
        
        # This should PASS after SSOT remediation
        assert ssot_constant_info["exists"], (
            f"SERVICE_ID SSOT constant not found. Expected centralized constant in "
            f"{ssot_constant_info['expected_path']}."
        )
        
        assert ssot_constant_info["value"] == "netra-backend", (
            f"SERVICE_ID SSOT constant has incorrect value: '{ssot_constant_info['value']}'. "
            f"Expected: 'netra-backend'."
        )
        
        assert ssot_constant_info["properly_defined"], (
            f"SERVICE_ID SSOT constant is not properly defined. "
            f"Issues: {ssot_constant_info['definition_issues']}"
        )
    
    def test_all_services_use_ssot_constant(self):
        """
        PASSING TEST: Validate all services import SERVICE_ID from SSOT.
        
        This test scans all services to ensure they import SERVICE_ID
        from the centralized SSOT constant rather than using hardcoded
        values or environment variables.
        """
        service_compliance = self._validate_service_ssot_usage()
        
        self.record_metric("services_scanned", len(service_compliance))
        self.record_metric("compliant_services", sum(1 for s in service_compliance.values() if s["compliant"]))
        self.record_metric("compliance_rate", self._calculate_compliance_rate(service_compliance))
        
        for service_name, compliance_info in service_compliance.items():
            print(f"SERVICE {service_name}: {compliance_info}")
        
        # Calculate overall compliance
        total_services = len(service_compliance)
        compliant_services = sum(1 for s in service_compliance.values() if s["compliant"])
        compliance_rate = compliant_services / total_services if total_services > 0 else 0.0
        
        # This should PASS after SSOT remediation (100% compliance)
        assert compliance_rate == 1.0, (
            f"SERVICE_ID SSOT compliance failure: {compliant_services}/{total_services} services compliant "
            f"({compliance_rate:.1%}). Non-compliant services: "
            f"{[name for name, info in service_compliance.items() if not info['compliant']]}"
        )
    
    def test_no_hardcoded_service_id_violations(self):
        """
        PASSING TEST: Validate no hardcoded SERVICE_ID strings remain.
        
        This test ensures that after SSOT remediation, no hardcoded
        "netra-backend" strings exist in the codebase outside of the
        centralized SSOT constant.
        """
        hardcoded_violations = self._scan_for_hardcoded_violations()
        
        self.record_metric("hardcoded_violations_found", len(hardcoded_violations))
        
        # Filter out the SSOT constant file itself
        ssot_path = self._get_expected_ssot_path()
        filtered_violations = {
            path: lines for path, lines in hardcoded_violations.items()
            if not path.endswith(str(ssot_path))
        }
        
        self.record_metric("filtered_violations", len(filtered_violations))
        
        for violation_file, lines in filtered_violations.items():
            print(f"HARDCODED VIOLATION: {violation_file} at lines {lines}")
        
        # This should PASS after SSOT remediation (no violations)
        assert len(filtered_violations) == 0, (
            f"Hardcoded SERVICE_ID violations found in {len(filtered_violations)} files: "
            f"{list(filtered_violations.keys())}. All hardcoded values should be replaced "
            f"with SSOT constant imports."
        )
    
    def test_no_environment_variable_dependencies(self):
        """
        PASSING TEST: Validate no environment variable SERVICE_ID dependencies.
        
        This test ensures that after SSOT remediation, no code depends on
        SERVICE_ID environment variables, preventing environment-dependent
        configuration inconsistencies.
        """
        env_dependencies = self._scan_for_environment_dependencies()
        
        self.record_metric("env_dependencies_found", len(env_dependencies))
        
        for dependency_file, patterns in env_dependencies.items():
            print(f"ENV DEPENDENCY: {dependency_file} has patterns {patterns}")
        
        # This should PASS after SSOT remediation (no environment dependencies)
        assert len(env_dependencies) == 0, (
            f"SERVICE_ID environment variable dependencies found in {len(env_dependencies)} files: "
            f"{list(env_dependencies.keys())}. All environment access should be replaced "
            f"with SSOT constant imports."
        )
    
    def test_cross_service_consistency_validation(self):
        """
        PASSING TEST: Validate cross-service SERVICE_ID consistency.
        
        This test validates that all services that use SERVICE_ID
        import from the same SSOT source and get the same value.
        """
        consistency_analysis = self._validate_cross_service_consistency()
        
        self.record_metric("services_analyzed", len(consistency_analysis["services"]))
        self.record_metric("consistency_score", consistency_analysis["score"])
        self.record_metric("inconsistencies_found", len(consistency_analysis["inconsistencies"]))
        
        print(f"CONSISTENCY ANALYSIS: {consistency_analysis}")
        
        # This should PASS after SSOT remediation (perfect consistency)
        assert consistency_analysis["score"] == 1.0, (
            f"Cross-service SERVICE_ID consistency failure. "
            f"Consistency score: {consistency_analysis['score']} (expected: 1.0). "
            f"Inconsistencies: {consistency_analysis['inconsistencies']}"
        )
    
    def test_import_path_standardization(self):
        """
        PASSING TEST: Validate standardized SSOT import paths.
        
        This test ensures that all SERVICE_ID imports use the same
        standardized import path to the SSOT constant.
        """
        import_analysis = self._analyze_import_paths()
        
        self.record_metric("import_patterns_found", len(import_analysis["patterns"]))
        self.record_metric("standardized_imports", import_analysis["standardized_count"])
        self.record_metric("non_standard_imports", import_analysis["non_standard_count"])
        
        for pattern, files in import_analysis["patterns"].items():
            print(f"IMPORT PATTERN '{pattern}' used in: {files}")
        
        # This should PASS after SSOT remediation (single import pattern)
        assert len(import_analysis["patterns"]) <= 1, (
            f"Multiple SERVICE_ID import patterns detected: {list(import_analysis['patterns'].keys())}. "
            f"Expected single standardized import pattern."
        )
        
        assert import_analysis["non_standard_count"] == 0, (
            f"Non-standard SERVICE_ID imports found: {import_analysis['non_standard_count']}. "
            f"All imports should use standardized SSOT path."
        )
    
    def _validate_ssot_constant_exists(self) -> Dict[str, any]:
        """Validate that SSOT constant exists and is properly defined."""
        expected_path = self._get_expected_ssot_path()
        
        result = {
            "exists": False,
            "path": None,
            "value": None,
            "properly_defined": False,
            "definition_issues": [],
            "expected_path": str(expected_path)
        }
        
        if expected_path.exists():
            try:
                with open(expected_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the file to extract SERVICE_ID constant
                try:
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id == "SERVICE_ID":
                                    if isinstance(node.value, ast.Constant):
                                        result.update({
                                            "exists": True,
                                            "path": str(expected_path),
                                            "value": node.value.value,
                                            "properly_defined": True
                                        })
                                        return result
                
                except SyntaxError:
                    result["definition_issues"].append("syntax_error_in_file")
                
                # Check for simple string assignment if AST parsing didn't find it
                if 'SERVICE_ID = "netra-backend"' in content:
                    result.update({
                        "exists": True,
                        "path": str(expected_path),
                        "value": "netra-backend",
                        "properly_defined": True
                    })
                elif 'SERVICE_ID' in content:
                    result.update({
                        "exists": True,
                        "path": str(expected_path),
                        "value": "unknown",
                        "properly_defined": False
                    })
                    result["definition_issues"].append("improper_definition_format")
                
            except (FileNotFoundError, PermissionError):
                result["definition_issues"].append("file_not_readable")
        
        return result
    
    def _validate_service_ssot_usage(self) -> Dict[str, Dict[str, any]]:
        """Validate that all services use SSOT constant for SERVICE_ID."""
        project_root = Path(__file__).parent.parent.parent
        services = ["auth_service", "netra_backend"]
        
        service_compliance = {}
        
        for service_name in services:
            service_path = project_root / service_name
            
            if not service_path.exists():
                continue
            
            compliance_info = {
                "compliant": False,
                "has_ssot_import": False,
                "has_hardcoded": False,
                "has_env_access": False,
                "files_checked": 0,
                "violations": []
            }
            
            # Scan service files
            for python_file in service_path.rglob("**/*.py"):
                if self._should_skip_file(python_file):
                    continue
                
                compliance_info["files_checked"] += 1
                
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    relative_path = str(python_file.relative_to(project_root))
                    
                    # Check for SSOT import
                    if self._has_ssot_import(content):
                        compliance_info["has_ssot_import"] = True
                    
                    # Check for violations
                    if self._has_hardcoded_service_id(content):
                        compliance_info["has_hardcoded"] = True
                        compliance_info["violations"].append(f"{relative_path}: hardcoded")
                    
                    if self._has_env_access(content):
                        compliance_info["has_env_access"] = True
                        compliance_info["violations"].append(f"{relative_path}: env_access")
                
                except (UnicodeDecodeError, PermissionError):
                    continue
            
            # Determine compliance
            compliance_info["compliant"] = (
                compliance_info["has_ssot_import"] and
                not compliance_info["has_hardcoded"] and
                not compliance_info["has_env_access"]
            )
            
            service_compliance[service_name] = compliance_info
        
        return service_compliance
    
    def _scan_for_hardcoded_violations(self) -> Dict[str, List[int]]:
        """Scan for remaining hardcoded SERVICE_ID violations."""
        violations = {}
        project_root = Path(__file__).parent.parent.parent
        
        for python_file in project_root.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                violation_lines = []
                for line_num, line in enumerate(lines, 1):
                    if self._is_hardcoded_service_id_line(line):
                        violation_lines.append(line_num)
                
                if violation_lines:
                    relative_path = str(python_file.relative_to(project_root))
                    violations[relative_path] = violation_lines
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return violations
    
    def _scan_for_environment_dependencies(self) -> Dict[str, List[str]]:
        """Scan for SERVICE_ID environment variable dependencies."""
        dependencies = {}
        project_root = Path(__file__).parent.parent.parent
        
        env_patterns = [
            r'os\.environ\.get\(["\']SERVICE_ID["\']',
            r'env\.get\(["\']SERVICE_ID["\']',
            r'getenv\(["\']SERVICE_ID["\']'
        ]
        
        for python_file in project_root.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_patterns = []
                for pattern in env_patterns:
                    import re
                    if re.search(pattern, content):
                        found_patterns.append(pattern)
                
                if found_patterns:
                    relative_path = str(python_file.relative_to(project_root))
                    dependencies[relative_path] = found_patterns
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return dependencies
    
    def _validate_cross_service_consistency(self) -> Dict[str, any]:
        """Validate consistency across all services."""
        project_root = Path(__file__).parent.parent.parent
        services = ["auth_service", "netra_backend"]
        
        service_values = {}
        inconsistencies = []
        
        for service_name in services:
            service_path = project_root / service_name
            
            if not service_path.exists():
                continue
            
            # Extract SERVICE_ID value used by service
            service_value = self._extract_service_id_value(service_path)
            service_values[service_name] = service_value
        
        # Check for inconsistencies
        unique_values = set(v for v in service_values.values() if v is not None)
        
        if len(unique_values) > 1:
            inconsistencies.append(f"Multiple SERVICE_ID values found: {dict(service_values)}")
        
        # Calculate consistency score
        if inconsistencies:
            score = 0.0
        else:
            score = 1.0
        
        return {
            "services": service_values,
            "score": score,
            "inconsistencies": inconsistencies
        }
    
    def _analyze_import_paths(self) -> Dict[str, any]:
        """Analyze SERVICE_ID import paths for standardization."""
        project_root = Path(__file__).parent.parent.parent
        import_patterns = {}
        
        for python_file in project_root.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for SERVICE_ID imports
                import_pattern = self._extract_import_pattern(content)
                if import_pattern:
                    relative_path = str(python_file.relative_to(project_root))
                    
                    if import_pattern not in import_patterns:
                        import_patterns[import_pattern] = []
                    import_patterns[import_pattern].append(relative_path)
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Analyze standardization
        standard_pattern = "from shared.constants.service_identifiers import SERVICE_ID"
        standardized_count = len(import_patterns.get(standard_pattern, []))
        
        non_standard_count = sum(
            len(files) for pattern, files in import_patterns.items()
            if pattern != standard_pattern
        )
        
        return {
            "patterns": import_patterns,
            "standardized_count": standardized_count,
            "non_standard_count": non_standard_count
        }
    
    def _get_expected_ssot_path(self) -> Path:
        """Get expected path for SSOT constant."""
        project_root = Path(__file__).parent.parent.parent
        return project_root / "shared" / "constants" / "service_identifiers.py"
    
    def _calculate_compliance_rate(self, service_compliance: Dict[str, Dict[str, any]]) -> float:
        """Calculate overall compliance rate."""
        if not service_compliance:
            return 0.0
        
        compliant_count = sum(1 for info in service_compliance.values() if info["compliant"])
        return compliant_count / len(service_compliance)
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            "node_modules", "__pycache__", ".git", ".pytest_cache",
            "google-cloud-sdk", "test_results", "venv", "env"
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _has_ssot_import(self, content: str) -> bool:
        """Check if content has SSOT import."""
        import_patterns = [
            "from shared.constants.service_identifiers import SERVICE_ID",
            "from shared.constants import SERVICE_ID",
            "import shared.constants.service_identifiers"
        ]
        
        return any(pattern in content for pattern in import_patterns)
    
    def _has_hardcoded_service_id(self, content: str) -> bool:
        """Check if content has hardcoded SERVICE_ID."""
        import re
        patterns = [
            r'["\']netra-backend["\']',
            r'service_id\s*=\s*["\']netra-backend["\']'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)
    
    def _has_env_access(self, content: str) -> bool:
        """Check if content accesses SERVICE_ID via environment."""
        env_patterns = [
            "os.environ.get('SERVICE_ID')",
            'os.environ.get("SERVICE_ID")',
            "env.get('SERVICE_ID')",
            'env.get("SERVICE_ID")'
        ]
        
        return any(pattern in content for pattern in env_patterns)
    
    def _is_hardcoded_service_id_line(self, line: str) -> bool:
        """Check if line contains hardcoded SERVICE_ID."""
        if line.strip().startswith('#'):
            return False
        
        import re
        patterns = [
            r'["\']netra-backend["\']',
            r'service_id\s*=\s*["\']netra-backend["\']'
        ]
        
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)
    
    def _extract_service_id_value(self, service_path: Path) -> Optional[str]:
        """Extract SERVICE_ID value used by service."""
        for python_file in service_path.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for SERVICE_ID usage
                if 'SERVICE_ID' in content:
                    if 'from shared.constants' in content:
                        return "netra-backend"  # Assuming SSOT value
                    elif '"netra-backend"' in content:
                        return "netra-backend"
                    elif 'environ' in content:
                        return "environment_dependent"
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return None
    
    def _extract_import_pattern(self, content: str) -> Optional[str]:
        """Extract SERVICE_ID import pattern from content."""
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'SERVICE_ID' in line and ('import' in line or 'from' in line):
                return line
        
        return None