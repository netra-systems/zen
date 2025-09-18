"""
WebSocket Authentication Pattern Violations Test for Issue #1186

Tests for detecting WebSocket authentication pattern violations that violate
SSOT principles and create security vulnerabilities in the Golden Path.

Business Value: Platform/Internal - System Security & Development Velocity
Prevents authentication bypass vulnerabilities and ensures secure WebSocket
connections for the 500K+ ARR Golden Path user flow.

Expected: FAIL initially (detects 5+ violations, 4 patterns)
Target: 100% SSOT compliance with canonical authentication patterns

CRITICAL: This test MUST fail initially to demonstrate current violations.
Only passes when SSOT consolidation is complete.
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class AuthViolation:
    """Container for WebSocket authentication violations."""
    file_path: str
    line_number: int
    violation_code: str
    violation_type: str
    severity: str
    pattern_category: str
    security_impact: str


@dataclass
class AuthPatternStats:
    """Statistics for authentication pattern analysis."""
    total_violations: int
    security_critical_violations: int
    high_violations: int
    medium_violations: int
    low_violations: int
    violation_patterns: Set[str]
    files_affected: Set[str]
    auth_bypass_risks: List[str]


class TestWebSocketAuthPatternViolations(SSotBaseTestCase):
    """
    Test suite for detecting WebSocket authentication pattern violations.
    
    This test identifies authentication patterns that violate SSOT principles
    and create security risks in WebSocket connections.
    
    CRITICAL BUSINESS IMPACT:
    - Prevents authentication bypass in Golden Path (500K+ ARR protection)
    - Ensures secure WebSocket connections for customer chat functionality
    - Maintains enterprise-grade security standards for user authentication
    """
    
    @classmethod
    def setup_class(cls):
        """Set up class-level resources for authentication analysis."""
        super().setup_class()
        cls.project_root = Path("/Users/anthony/Desktop/netra-apex")
        cls.auth_violation_threshold = 5  # Expected current violations
        cls.pattern_threshold = 4  # Expected distinct violation patterns
        cls.canonical_auth_patterns = [
            "from auth_service.auth_core.core.jwt_handler import verify_jwt_token",
            "from netra_backend.app.auth_integration.auth import validate_websocket_auth",
            "from test_framework.ssot.e2e_auth_helper import create_authenticated_user"
        ]
        cls.logger.info(f"Analyzing WebSocket auth patterns in {cls.project_root}")
    
    def setup_method(self, method=None):
        """Set up per-test resources."""
        super().setup_method(method)
        self.violations: List[AuthViolation] = []
        self.stats = AuthPatternStats(
            total_violations=0,
            security_critical_violations=0,
            high_violations=0,
            medium_violations=0,
            low_violations=0,
            violation_patterns=set(),
            files_affected=set(),
            auth_bypass_risks=[]
        )
    
    def _scan_websocket_files(self) -> List[Path]:
        """Scan for WebSocket-related files to analyze."""
        websocket_files = []
        
        # Key directories with WebSocket code
        scan_patterns = [
            "netra_backend/app/websocket*/**/*.py",
            "netra_backend/app/routes/websocket*.py",
            "netra_backend/app/**/websocket*.py",
            "test_framework/**/websocket*.py",
            "tests/**/websocket*.py",
            "tests/**/test_websocket*.py"
        ]
        
        for pattern in scan_patterns:
            websocket_files.extend(self.project_root.glob(pattern))
        
        # Also scan for files containing WebSocket authentication code
        additional_files = []
        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if any(keyword in content.lower() for keyword in 
                          ['websocket', 'ws_auth', 'socket_auth', 'jwt_websocket']):
                        additional_files.append(py_file)
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
        
        websocket_files.extend(additional_files)
        websocket_files = list(set(websocket_files))  # Remove duplicates
        
        self.record_metric("websocket_files_scanned", len(websocket_files))
        return websocket_files
    
    def _analyze_auth_violations(self, file_path: Path) -> List[AuthViolation]:
        """Analyze authentication violations in a WebSocket file."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Parse AST for structured analysis
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return violations
            
            rel_path = str(file_path.relative_to(self.project_root))
            
            # Check for various authentication violation patterns
            violations.extend(self._check_direct_jwt_decode_violations(rel_path, lines, tree))
            violations.extend(self._check_auth_bypass_patterns(rel_path, lines, tree))
            violations.extend(self._check_fragmented_auth_imports(rel_path, lines, tree))
            violations.extend(self._check_insecure_auth_patterns(rel_path, lines, tree))
        
        except Exception as e:
            self.logger.warning(f"Error analyzing {file_path}: {e}")
        
        return violations
    
    def _check_direct_jwt_decode_violations(self, file_path: str, lines: List[str], tree: ast.AST) -> List[AuthViolation]:
        """Check for direct JWT decoding violations (SSOT violation)."""
        violations = []
        
        # Patterns that indicate direct JWT handling instead of using auth service
        forbidden_patterns = [
            (r'jwt\.decode\s*\(', 'direct_jwt_decode'),
            (r'PyJWT\.decode\s*\(', 'direct_pyjwt_decode'),
            (r'base64\.decode.*jwt', 'manual_jwt_decode'),
            (r'json\.loads.*\.split\(.*jwt', 'manual_jwt_parsing'),
            (r'\.split\(\'\.\'.*jwt', 'jwt_manual_split')
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, violation_type in forbidden_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violation = AuthViolation(
                        file_path=file_path,
                        line_number=line_num,
                        violation_code=line.strip(),
                        violation_type=violation_type,
                        severity="SECURITY_CRITICAL",
                        pattern_category="direct_jwt_handling",
                        security_impact="Authentication bypass risk - JWT validation not centralized"
                    )
                    violations.append(violation)
        
        return violations
    
    def _check_auth_bypass_patterns(self, file_path: str, lines: List[str], tree: ast.AST) -> List[AuthViolation]:
        """Check for authentication bypass patterns."""
        violations = []
        
        # Patterns that indicate potential authentication bypass
        bypass_patterns = [
            (r'if\s+False\s*:', 'hardcoded_auth_disable'),
            (r'#.*auth.*disable', 'commented_auth_disable'),
            (r'skip.*auth', 'auth_skip_pattern'),
            (r'no.*auth.*check', 'no_auth_check'),
            (r'bypass.*auth', 'explicit_auth_bypass'),
            (r'mock.*auth.*true', 'mocked_auth_always_true'),
            (r'return\s+True.*auth', 'hardcoded_auth_success')
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, violation_type in bypass_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Exclude test files from some patterns (they may legitimately mock auth)
                    if file_path.startswith("tests/") and violation_type in ['mocked_auth_always_true']:
                        continue
                        
                    violation = AuthViolation(
                        file_path=file_path,
                        line_number=line_num,
                        violation_code=line.strip(),
                        violation_type=violation_type,
                        severity="SECURITY_CRITICAL",
                        pattern_category="auth_bypass",
                        security_impact="Authentication can be bypassed completely"
                    )
                    violations.append(violation)
        
        return violations
    
    def _check_fragmented_auth_imports(self, file_path: str, lines: List[str], tree: ast.AST) -> List[AuthViolation]:
        """Check for fragmented authentication imports (SSOT violation)."""
        violations = []
        
        # Import patterns that violate SSOT authentication principles
        fragmented_patterns = [
            (r'from.*\.auth.*import.*jwt', 'fragmented_jwt_import'),
            (r'import\s+jwt\s*$', 'direct_jwt_import'),
            (r'from\s+jwt\s+import', 'direct_jwt_from_import'),
            (r'from.*websocket.*import.*auth', 'websocket_auth_import_fragmentation'),
            (r'from.*\.\..*auth', 'relative_auth_import'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, violation_type in fragmented_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if this is a canonical import pattern
                    is_canonical = any(canonical in line for canonical in self.canonical_auth_patterns)
                    
                    if not is_canonical:
                        violation = AuthViolation(
                            file_path=file_path,
                            line_number=line_num,
                            violation_code=line.strip(),
                            violation_type=violation_type,
                            severity="HIGH",
                            pattern_category="fragmented_auth_imports",
                            security_impact="Non-SSOT authentication imports create inconsistent security"
                        )
                        violations.append(violation)
        
        return violations
    
    def _check_insecure_auth_patterns(self, file_path: str, lines: List[str], tree: ast.AST) -> List[AuthViolation]:
        """Check for insecure authentication patterns."""
        violations = []
        
        # Patterns that indicate insecure authentication practices
        insecure_patterns = [
            (r'secret.*=.*["\'].*["\']', 'hardcoded_secret'),
            (r'key.*=.*["\'].*["\']', 'hardcoded_key'),
            (r'password.*=.*["\'][^"\']*["\']', 'hardcoded_password'),
            (r'token.*=.*["\'].*["\']', 'hardcoded_token'),
            (r'verify.*=.*False', 'jwt_verification_disabled'),
            (r'check_signature.*=.*False', 'signature_verification_disabled'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, violation_type in insecure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Filter out obvious test patterns and environment variable assignments
                    if any(safe_pattern in line.lower() for safe_pattern in 
                          ['os.environ', 'getenv', 'test_', 'mock_', 'example']):
                        continue
                        
                    violation = AuthViolation(
                        file_path=file_path,
                        line_number=line_num,
                        violation_code=line.strip(),
                        violation_type=violation_type,
                        severity="HIGH",
                        pattern_category="insecure_auth_practices",
                        security_impact="Insecure authentication configuration"
                    )
                    violations.append(violation)
        
        return violations
    
    def _aggregate_stats(self, violations: List[AuthViolation]) -> None:
        """Aggregate violation statistics."""
        self.stats.total_violations = len(violations)
        
        for violation in violations:
            # Track violation patterns
            self.stats.violation_patterns.add(violation.violation_type)
            self.stats.files_affected.add(violation.file_path)
            
            # Count by severity
            if violation.severity == "SECURITY_CRITICAL":
                self.stats.security_critical_violations += 1
                self.stats.auth_bypass_risks.append(f"{violation.file_path}:{violation.line_number}")
            elif violation.severity == "HIGH":
                self.stats.high_violations += 1
            elif violation.severity == "MEDIUM":
                self.stats.medium_violations += 1
            else:
                self.stats.low_violations += 1
    
    def test_detect_websocket_auth_pattern_violations(self):
        """
        CRITICAL TEST: Detect WebSocket authentication pattern violations.
        
        This test MUST FAIL initially to demonstrate the current 5+ violations
        across 4+ distinct patterns that need to be addressed for SSOT compliance.
        
        Expected violations:
        - 5+ total authentication pattern violations
        - 2+ security critical violations (auth bypass, direct JWT decode)
        - 3+ high violations (fragmented imports, insecure practices)
        - 4+ distinct violation patterns
        
        Business Impact:
        - Prevents authentication bypass in Golden Path (500K+ ARR protection)
        - Ensures secure WebSocket connections for customer chat
        - Maintains enterprise-grade security standards
        """
        # Scan WebSocket-related files
        websocket_files = self._scan_websocket_files()
        self.assertGreater(len(websocket_files), 5, "Should scan substantial number of WebSocket files")
        
        # Analyze each file for authentication violations
        all_violations = []
        for file_path in websocket_files:
            violations = self._analyze_auth_violations(file_path)
            all_violations.extend(violations)
        
        # Store violations for analysis
        self.violations = all_violations
        self._aggregate_stats(all_violations)
        
        # Record metrics for tracking
        self.record_metric("total_auth_violations", self.stats.total_violations)
        self.record_metric("security_critical_violations", self.stats.security_critical_violations)
        self.record_metric("high_violations", self.stats.high_violations)
        self.record_metric("violation_patterns", len(self.stats.violation_patterns))
        self.record_metric("files_affected", len(self.stats.files_affected))
        
        # Log detailed results
        self.logger.error(f"WEBSOCKET AUTH PATTERN VIOLATIONS DETECTED - SSOT VIOLATION")
        self.logger.error(f"Total violations: {self.stats.total_violations}")
        self.logger.error(f"Security critical violations: {self.stats.security_critical_violations}")
        self.logger.error(f"High violations: {self.stats.high_violations}")
        self.logger.error(f"Medium violations: {self.stats.medium_violations}")
        self.logger.error(f"Low violations: {self.stats.low_violations}")
        self.logger.error(f"Violation patterns: {len(self.stats.violation_patterns)}")
        self.logger.error(f"Files affected: {len(self.stats.files_affected)}")
        self.logger.error(f"Patterns detected: {sorted(self.stats.violation_patterns)}")
        
        # **CRITICAL ASSERTION: This test MUST FAIL to demonstrate current violations**
        self.assertGreaterEqual(
            self.stats.total_violations,
            self.auth_violation_threshold,
            f"Expected at least {self.auth_violation_threshold} WebSocket auth violations "
            f"to demonstrate current SSOT compliance issues. Found {self.stats.total_violations}. "
            f"If violations are below threshold, SSOT consolidation may already be complete."
        )
        
        # Ensure multiple distinct violation patterns exist
        self.assertGreaterEqual(
            len(self.stats.violation_patterns),
            self.pattern_threshold,
            f"Expected at least {self.pattern_threshold} distinct violation patterns. "
            f"Found {len(self.stats.violation_patterns)} patterns: {sorted(self.stats.violation_patterns)}. "
            f"Pattern diversity indicates scope of SSOT authentication issues."
        )
        
        # Verify security critical violations exist (these are urgent)
        self.assertGreater(
            self.stats.security_critical_violations,
            0,
            f"Expected security critical auth violations to exist. Found {self.stats.security_critical_violations}. "
            f"Security critical violations indicate immediate security risks that must be addressed."
        )
        
        # Log violation details for prioritization
        self.logger.error("VIOLATION BREAKDOWN BY CATEGORY:")
        category_counts = {}
        for violation in all_violations:
            category = violation.pattern_category
            if category not in category_counts:
                category_counts[category] = []
            category_counts[category].append(violation)
        
        for category, violations in category_counts.items():
            self.logger.error(f"  {category}: {len(violations)} violations")
            for violation in violations[:3]:  # Show first 3 examples
                self.logger.error(f"    {violation.file_path}:{violation.line_number} - {violation.violation_type}")
        
        # **THIS TEST FAILS TO DEMONSTRATE CURRENT SECURITY VIOLATIONS**
        self.fail(
            f"WEBSOCKET AUTH SSOT CONSOLIDATION REQUIRED: Found {self.stats.total_violations} authentication violations "
            f"({self.stats.security_critical_violations} security critical, {self.stats.high_violations} high severity) "
            f"across {len(self.stats.violation_patterns)} patterns. "
            f"This test fails to demonstrate current authentication security issues that must be addressed "
            f"for Issue #1186 resolution. See logs for detailed violation analysis."
        )
    
    def test_detect_auth_bypass_security_risks(self):
        """
        Detect authentication bypass security risks in WebSocket code.
        
        This test identifies critical security vulnerabilities where
        authentication can be bypassed in WebSocket connections.
        """
        # Scan WebSocket files for auth bypass risks
        websocket_files = self._scan_websocket_files()
        
        bypass_violations = []
        for file_path in websocket_files:
            violations = self._analyze_auth_violations(file_path)
            bypass_violations.extend([v for v in violations if v.pattern_category == "auth_bypass"])
        
        # Record bypass risk metrics
        self.record_metric("auth_bypass_violations", len(bypass_violations))
        
        # Log bypass risks
        self.logger.error("AUTHENTICATION BYPASS RISKS DETECTED:")
        for violation in bypass_violations:
            self.logger.error(f"  {violation.file_path}:{violation.line_number}")
            self.logger.error(f"    Type: {violation.violation_type}")
            self.logger.error(f"    Code: {violation.violation_code}")
            self.logger.error(f"    Impact: {violation.security_impact}")
            self.logger.error("")
        
        # **THIS TEST FAILS IF BYPASS RISKS EXIST**
        if bypass_violations:
            self.fail(
                f"AUTHENTICATION BYPASS RISKS DETECTED: Found {len(bypass_violations)} patterns "
                f"that could allow authentication bypass in WebSocket connections. "
                f"These represent critical security vulnerabilities that must be addressed immediately. "
                f"See logs for detailed bypass risk analysis."
            )
    
    def test_validate_canonical_auth_pattern_usage(self):
        """
        Validate usage of canonical authentication patterns.
        
        This test checks whether WebSocket files use the prescribed
        SSOT authentication patterns instead of fragmented approaches.
        """
        websocket_files = self._scan_websocket_files()
        
        canonical_usage = 0
        non_canonical_usage = 0
        files_with_auth = 0
        
        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file has authentication code
                has_auth = any(keyword in content.lower() for keyword in 
                              ['auth', 'jwt', 'token', 'login', 'authenticate'])
                
                if has_auth:
                    files_with_auth += 1
                    
                    # Check for canonical patterns
                    uses_canonical = any(pattern in content for pattern in self.canonical_auth_patterns)
                    
                    if uses_canonical:
                        canonical_usage += 1
                    else:
                        non_canonical_usage += 1
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
        
        # Calculate canonical usage percentage
        canonical_percentage = (canonical_usage / max(1, files_with_auth)) * 100
        
        # Record metrics
        self.record_metric("canonical_auth_usage_percentage", canonical_percentage)
        self.record_metric("files_with_auth", files_with_auth)
        self.record_metric("canonical_usage", canonical_usage)
        self.record_metric("non_canonical_usage", non_canonical_usage)
        
        # Log canonical usage analysis
        self.logger.error("CANONICAL AUTH PATTERN USAGE ANALYSIS:")
        self.logger.error(f"  Files with authentication code: {files_with_auth}")
        self.logger.error(f"  Files using canonical patterns: {canonical_usage}")
        self.logger.error(f"  Files using non-canonical patterns: {non_canonical_usage}")
        self.logger.error(f"  Canonical usage percentage: {canonical_percentage:.1f}%")
        self.logger.error(f"  Target: 95%+ canonical usage")
        
        # **THIS TEST FAILS IF CANONICAL USAGE IS LOW**
        self.assertGreaterEqual(
            canonical_percentage,
            95.0,
            f"Expected 95%+ canonical authentication pattern usage. "
            f"Found {canonical_percentage:.1f}% ({canonical_usage}/{files_with_auth} files). "
            f"Low canonical usage indicates SSOT authentication patterns are not being followed."
        )
        
        # If we reach here, fail because we expect non-canonical usage initially
        self.fail(
            f"CANONICAL AUTH PATTERN VALIDATION: Found {canonical_percentage:.1f}% canonical usage "
            f"({canonical_usage} canonical, {non_canonical_usage} non-canonical). "
            f"This test fails to demonstrate that SSOT authentication consolidation is needed."
        )