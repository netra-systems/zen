"""
SSOT Validation Test: SERVICE_ID SSOT Violation Detection

PHASE 1: CREATE FAILING TEST - Expose Current SSOT Violation

Purpose: This test MUST FAIL with current codebase to expose the SERVICE_ID 
SSOT violation where hardcoded "netra-backend" exists alongside environment 
variable patterns.

Business Value: Platform/Critical - Prevents authentication cascade failures 
that block user login (60-second failures affecting $500K+ ARR).

Expected Behavior: 
- FAIL: With current mixed hardcoded vs environment patterns
- PASS: After SSOT remediation with single constant source

CRITICAL: This test protects the Golden Path: users login  ->  get AI responses
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestServiceIdSsotViolationDetection(SSotBaseTestCase):
    """
    Detect SERVICE_ID SSOT violations in the codebase.
    
    This test scans the codebase for mixed patterns of SERVICE_ID usage:
    - Hardcoded "netra-backend" strings
    - Environment variable access patterns: os.environ.get('SERVICE_ID')
    - Configuration-based SERVICE_ID lookups
    
    EXPECTED TO FAIL: Current codebase has 77+ mixed patterns
    """
    
    def setup_method(self, method=None):
        """Setup test environment with isolated metrics."""
        super().setup_method(method)
        self.record_metric("test_category", "ssot_violation_detection")
        self.record_metric("business_impact", "prevents_60s_auth_failures")
        
    def test_detect_hardcoded_service_id_violations(self):
        """
        CRITICAL FAILING TEST: Detect hardcoded SERVICE_ID patterns.
        
        This test MUST FAIL to expose current SSOT violations.
        Scans codebase for hardcoded "netra-backend" strings that should
        be replaced with SSOT constants.
        """
        violations = self._scan_hardcoded_service_id_patterns()
        
        # Record findings for analysis
        self.record_metric("hardcoded_violations_found", len(violations))
        
        # EXPECTED TO FAIL: Current codebase has hardcoded patterns
        # These specific violations are documented in GitHub Issue #203
        expected_violations = [
            "/auth_service/auth_core/routes/auth_routes.py:760",
            "/auth_service/auth_core/routes/auth_routes.py:935"
        ]
        
        for violation_file, violation_lines in violations.items():
            print(f"SSOT VIOLATION: {violation_file} has hardcoded SERVICE_ID at lines: {violation_lines}")
        
        # This assertion MUST FAIL with current codebase
        assert len(violations) == 0, (
            f"SSOT VIOLATION DETECTED: Found {len(violations)} files with hardcoded SERVICE_ID patterns. "
            f"Violations: {list(violations.keys())}. "
            f"This indicates SERVICE_ID SSOT violation requiring remediation."
        )
    
    def test_detect_environment_variable_service_id_access(self):
        """
        CRITICAL FAILING TEST: Detect environment variable SERVICE_ID access.
        
        Scans for os.environ.get('SERVICE_ID') and similar patterns that
        create inconsistency with hardcoded values.
        """
        env_access_violations = self._scan_environment_service_id_access()
        
        self.record_metric("env_access_violations_found", len(env_access_violations))
        
        for violation_file, patterns in env_access_violations.items():
            print(f"ENV ACCESS VIOLATION: {violation_file} accesses SERVICE_ID via environment: {patterns}")
        
        # This should FAIL initially - environment access creates inconsistency
        assert len(env_access_violations) == 0, (
            f"Environment ACCESS VIOLATION: Found {len(env_access_violations)} files accessing SERVICE_ID "
            f"via environment variables. This creates inconsistency with hardcoded values. "
            f"Violations: {list(env_access_violations.keys())}"
        )
    
    def test_detect_service_id_pattern_inconsistency(self):
        """
        CRITICAL FAILING TEST: Detect mixed SERVICE_ID patterns across services.
        
        This test compares SERVICE_ID usage patterns between auth_service 
        and netra_backend to expose inconsistencies.
        """
        auth_patterns = self._scan_service_patterns("auth_service")
        backend_patterns = self._scan_service_patterns("netra_backend")
        
        self.record_metric("auth_service_patterns", len(auth_patterns))
        self.record_metric("backend_patterns", len(backend_patterns))
        
        # Analyze pattern consistency
        pattern_consistency = self._analyze_pattern_consistency(auth_patterns, backend_patterns)
        
        self.record_metric("pattern_consistency_score", pattern_consistency["score"])
        self.record_metric("inconsistent_patterns", len(pattern_consistency["violations"]))
        
        print(f"PATTERN ANALYSIS: Auth service patterns: {auth_patterns}")
        print(f"PATTERN ANALYSIS: Backend patterns: {backend_patterns}")
        print(f"CONSISTENCY SCORE: {pattern_consistency['score']}")
        
        # This MUST FAIL - current patterns are inconsistent
        assert pattern_consistency["score"] >= 0.9, (
            f"SERVICE_ID pattern inconsistency detected between services. "
            f"Consistency score: {pattern_consistency['score']} (threshold: 0.9). "
            f"Violations: {pattern_consistency['violations']}"
        )
    
    def test_validate_service_id_constant_availability(self):
        """
        CRITICAL FAILING TEST: Validate SERVICE_ID SSOT constant exists.
        
        This test checks for the existence of a centralized SERVICE_ID constant
        that should be the single source of truth.
        """
        ssot_constant_path = self._find_service_id_ssot_constant()
        
        self.record_metric("ssot_constant_found", ssot_constant_path is not None)
        
        if ssot_constant_path:
            print(f"SSOT CONSTANT FOUND: {ssot_constant_path}")
        else:
            print("SSOT CONSTANT MISSING: No centralized SERVICE_ID constant found")
        
        # This MUST FAIL initially - no SSOT constant exists yet
        assert ssot_constant_path is not None, (
            "SERVICE_ID SSOT constant not found. Expected centralized constant in "
            "/shared/constants/service_identifiers.py or similar location."
        )
    
    def _scan_hardcoded_service_id_patterns(self) -> Dict[str, List[int]]:
        """
        Scan codebase for hardcoded "netra-backend" patterns.
        
        Returns:
            Dict mapping file paths to line numbers with hardcoded patterns
        """
        violations = {}
        project_root = Path(__file__).parent.parent.parent
        
        # File patterns to scan
        patterns_to_check = [
            "**/*.py",
            "**/*.js", 
            "**/*.ts",
            "**/*.tsx"
        ]
        
        for pattern in patterns_to_check:
            for file_path in project_root.rglob(pattern):
                # Skip test files, node_modules, and cache directories
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    hardcoded_lines = []
                    for line_num, line in enumerate(lines, 1):
                        # Look for hardcoded "netra-backend" that isn't in comments
                        if self._is_hardcoded_service_id(line):
                            hardcoded_lines.append(line_num)
                    
                    if hardcoded_lines:
                        relative_path = str(file_path.relative_to(project_root))
                        violations[relative_path] = hardcoded_lines
                        
                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read
                    continue
        
        return violations
    
    def _scan_environment_service_id_access(self) -> Dict[str, List[str]]:
        """
        Scan for environment variable SERVICE_ID access patterns.
        
        Returns:
            Dict mapping file paths to list of environment access patterns found
        """
        violations = {}
        project_root = Path(__file__).parent.parent.parent
        
        # Patterns that indicate environment variable access
        env_patterns = [
            r'os\.environ\.get\(["\']SERVICE_ID["\']',
            r'env\.get\(["\']SERVICE_ID["\']',
            r'getenv\(["\']SERVICE_ID["\']',
            r'process\.env\.SERVICE_ID',
            r'config\[[\'""]SERVICE_ID[\'""]\]'
        ]
        
        for python_file in project_root.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_patterns = []
                for pattern in env_patterns:
                    if re.search(pattern, content):
                        found_patterns.append(pattern)
                
                if found_patterns:
                    relative_path = str(python_file.relative_to(project_root))
                    violations[relative_path] = found_patterns
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return violations
    
    def _scan_service_patterns(self, service_name: str) -> Set[str]:
        """
        Scan specific service directory for SERVICE_ID patterns.
        
        Args:
            service_name: Name of service directory to scan
            
        Returns:
            Set of SERVICE_ID usage patterns found
        """
        patterns = set()
        project_root = Path(__file__).parent.parent.parent
        service_path = project_root / service_name
        
        if not service_path.exists():
            return patterns
        
        for python_file in service_path.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for various SERVICE_ID patterns
                if '"netra-backend"' in content or "'netra-backend'" in content:
                    patterns.add("hardcoded_netra_backend")
                
                if 'SERVICE_ID' in content and 'environ' in content:
                    patterns.add("environment_access")
                
                if 'SERVICE_ID' in content and 'config' in content.lower():
                    patterns.add("config_access")
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return patterns
    
    def _analyze_pattern_consistency(self, auth_patterns: Set[str], backend_patterns: Set[str]) -> Dict:
        """
        Analyze consistency between service SERVICE_ID patterns.
        
        Returns:
            Dict with consistency score and violations
        """
        all_patterns = auth_patterns.union(backend_patterns)
        
        if not all_patterns:
            return {"score": 1.0, "violations": []}
        
        # Check for conflicting patterns
        violations = []
        
        # If both hardcoded and environment access exist, it's inconsistent
        if "hardcoded_netra_backend" in all_patterns and "environment_access" in all_patterns:
            violations.append("mixed_hardcoded_and_environment_access")
        
        # If different services use different patterns, it's inconsistent
        if auth_patterns != backend_patterns:
            violations.append("cross_service_pattern_mismatch")
        
        # Calculate consistency score
        if violations:
            score = max(0.0, 1.0 - (len(violations) * 0.3))
        else:
            score = 1.0
        
        return {
            "score": score,
            "violations": violations
        }
    
    def _find_service_id_ssot_constant(self) -> str:
        """
        Look for existing SERVICE_ID SSOT constant.
        
        Returns:
            Path to SSOT constant file if found, None otherwise
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Expected locations for SSOT constant
        potential_paths = [
            project_root / "shared" / "constants" / "service_identifiers.py",
            project_root / "shared" / "constants" / "__init__.py",
            project_root / "shared" / "service_constants.py",
            project_root / "config" / "service_identifiers.py"
        ]
        
        for path in potential_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for SERVICE_ID constant definition
                    if 'SERVICE_ID' in content and ('=' in content or 'const' in content):
                        return str(path.relative_to(project_root))
                        
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        return None
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            "node_modules",
            "__pycache__",
            ".git",
            ".pytest_cache",
            "google-cloud-sdk",
            "test_results",
            ".env",
            "venv",
            "env"
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _is_hardcoded_service_id(self, line: str) -> bool:
        """
        Check if line contains hardcoded SERVICE_ID.
        
        Args:
            line: Line of code to check
            
        Returns:
            True if line contains hardcoded "netra-backend" that isn't a comment
        """
        # Skip comments
        if line.strip().startswith('#') or line.strip().startswith('//'):
            return False
        
        # Look for hardcoded "netra-backend" patterns
        patterns = [
            r'["\']netra-backend["\']',
            r'service_id\s*=\s*["\']netra-backend["\']',
            r'SERVICE_ID\s*=\s*["\']netra-backend["\']'
        ]
        
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        
        return False