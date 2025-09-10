"""
Unit Test: Logging Import Compliance - SSOT Violation Detection

PURPOSE: This test is DESIGNED TO FAIL with current logging violations.
It detects direct `logging.getLogger()` usage in critical golden path files.

CRITICAL: This test proves the violation detection mechanism works by failing
with current 1,121+ logging violations. It will pass only after SSOT remediation.

Business Value: Platform/Internal - System Stability & Development Velocity
Ensures critical golden path components use unified logging infrastructure.

TEST DESIGN: 
- Inherits from SSotBaseTestCase for consistent test infrastructure
- Scans specific critical files for logging import violations
- MUST FAIL initially to prove detection works
- Provides detailed failure messages showing which files violate SSOT
- Supports test-driven SSOT remediation

REQUIREMENTS per CLAUDE.md:
- Must inherit from SSotBaseTestCase
- Must detect violations in critical files (WebSocket, Auth, Main entry)
- Must be atomic and fast (< 30s for unit test)
- Must provide clear failure messages with remediation paths
- NO Docker dependencies (unit test only)

CRITICAL FILES TESTED:
- WebSocket Core: circuit_breaker.py, connection_id_manager.py, graceful_degradation_manager.py
- Auth Service: jwt_service.py, oauth_service.py, jwt_handler.py
- Backend Core: main.py, auth_integration/auth.py

EXPECTED BEHAVIOR:
- Test MUST fail initially (proves detection works)
- Clear violation report showing file paths and line numbers
- Actionable failure messages for remediation
- Enable test-driven SSOT compliance enforcement
"""

import pytest
from pathlib import Path
from typing import List

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.logging_compliance_scanner import (
    LoggingComplianceScanner,
    LoggingViolation,
    LoggingComplianceReport
)


class TestLoggingImportCompliance(SSotBaseTestCase):
    """
    Unit test for logging import SSOT compliance in critical files.
    
    This test is DESIGNED TO FAIL with current violations to prove detection works.
    """
    
    def setup_method(self, method=None):
        """Set up test with SSOT base test case."""
        super().setup_method(method)
        self.scanner = LoggingComplianceScanner()
        self.base_path = Path.cwd()
        
        # Record test category and expected failure
        self.record_metric("test_category", "logging_ssot_compliance") 
        self.record_metric("expected_to_fail", True)
        self.record_metric("detection_mechanism", "import_pattern_scanning")
    
    def test_critical_websocket_files_logging_compliance(self):
        """
        Test WebSocket core files for logging SSOT violations.
        
        EXPECTED: This test MUST FAIL due to current violations.
        """
        critical_websocket_files = [
            "netra_backend/app/websocket_core/circuit_breaker.py",
            "netra_backend/app/websocket_core/connection_id_manager.py", 
            "netra_backend/app/websocket_core/graceful_degradation_manager.py",
            "netra_backend/app/routes/websocket.py",
        ]
        
        violations_found = []
        
        for file_path in critical_websocket_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                file_violations = self.scanner.scan_file(full_path)
                violations_found.extend(file_violations)
                self.record_metric(f"violations_in_{Path(file_path).name}", len(file_violations))
        
        # Record scan metrics
        self.record_metric("websocket_files_scanned", len(critical_websocket_files))
        self.record_metric("websocket_violations_found", len(violations_found))
        
        # CRITICAL: This assertion MUST FAIL to prove detection works
        assert len(violations_found) == 0, (
            f"LOGGING SSOT VIOLATIONS DETECTED in WebSocket core files!\n"
            f"Found {len(violations_found)} violations that violate SSOT logging principle.\n\n"
            f"VIOLATIONS:\n{self._format_violations(violations_found)}\n\n"
            f"REMEDIATION: Replace direct logging imports with:\n"
            f"from shared.logging.unified_logger_factory import UnifiedLoggerFactory\n"
            f"logger = UnifiedLoggerFactory.get_logger(__name__)\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove violation detection works.\n"
            f"These files currently use direct 'logging.getLogger()' instead of SSOT factory."
        )
    
    def test_critical_auth_service_logging_compliance(self):
        """
        Test Auth Service files for logging SSOT violations.
        
        EXPECTED: This test MUST FAIL due to current violations.
        """
        critical_auth_files = [
            "auth_service/services/jwt_service.py",
            "auth_service/services/oauth_service.py",
            "auth_service/auth_core/core/jwt_handler.py",
        ]
        
        violations_found = []
        
        for file_path in critical_auth_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                file_violations = self.scanner.scan_file(full_path)
                violations_found.extend(file_violations)
                self.record_metric(f"violations_in_{Path(file_path).name}", len(file_violations))
        
        # Record scan metrics
        self.record_metric("auth_files_scanned", len(critical_auth_files))
        self.record_metric("auth_violations_found", len(violations_found))
        
        # CRITICAL: This assertion MUST FAIL to prove detection works
        assert len(violations_found) == 0, (
            f"LOGGING SSOT VIOLATIONS DETECTED in Auth Service files!\n"
            f"Found {len(violations_found)} violations that violate SSOT logging principle.\n\n"
            f"VIOLATIONS:\n{self._format_violations(violations_found)}\n\n"
            f"REMEDIATION: Replace direct logging imports with:\n"
            f"from shared.logging.unified_logger_factory import UnifiedLoggerFactory\n"
            f"logger = UnifiedLoggerFactory.get_logger(__name__)\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove violation detection works.\n"
            f"These files currently use direct 'logging.getLogger()' instead of SSOT factory."
        )
    
    def test_backend_main_entry_logging_compliance(self):
        """
        Test backend main entry files for logging SSOT violations.
        
        EXPECTED: This test MUST FAIL due to current violations.
        """
        critical_backend_files = [
            "netra_backend/app/main.py",
            "netra_backend/app/auth_integration/auth.py",
        ]
        
        violations_found = []
        
        for file_path in critical_backend_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                file_violations = self.scanner.scan_file(full_path)
                violations_found.extend(file_violations)
                self.record_metric(f"violations_in_{Path(file_path).name}", len(file_violations))
        
        # Record scan metrics
        self.record_metric("backend_files_scanned", len(critical_backend_files))
        self.record_metric("backend_violations_found", len(violations_found))
        
        # CRITICAL: This assertion MUST FAIL to prove detection works
        assert len(violations_found) == 0, (
            f"LOGGING SSOT VIOLATIONS DETECTED in Backend core files!\n"
            f"Found {len(violations_found)} violations that violate SSOT logging principle.\n\n"
            f"VIOLATIONS:\n{self._format_violations(violations_found)}\n\n"
            f"REMEDIATION: Replace direct logging imports with:\n"
            f"from shared.logging.unified_logger_factory import UnifiedLoggerFactory\n"
            f"logger = UnifiedLoggerFactory.get_logger(__name__)\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove violation detection works.\n"
            f"These files currently use direct 'logging.getLogger()' instead of SSOT factory."
        )
    
    def test_logging_violation_pattern_detection(self):
        """
        Test that the scanner correctly identifies different violation patterns.
        
        EXPECTED: This test validates scanner accuracy and MUST FAIL if violations exist.
        """
        # Scan all critical files at once
        violations = self.scanner.scan_critical_files()
        
        # Analyze violation patterns
        pattern_counts = {}
        for violation in violations:
            pattern = violation.violation_type
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        # Record pattern metrics
        for pattern, count in pattern_counts.items():
            self.record_metric(f"pattern_{pattern}_count", count)
        
        self.record_metric("total_critical_violations", len(violations))
        self.record_metric("unique_violation_patterns", len(pattern_counts))
        
        # Get the compliance report
        report = self.scanner.get_compliance_report()
        
        # CRITICAL: This assertion MUST FAIL to prove detection works
        assert len(violations) == 0, (
            f"LOGGING SSOT VIOLATIONS DETECTED across critical files!\n"
            f"Found {len(violations)} total violations across {report.total_files_scanned} files.\n\n"
            f"VIOLATION PATTERNS:\n{self._format_pattern_summary(pattern_counts)}\n\n"
            f"DETAILED VIOLATIONS:\n{report.get_detailed_violations()}\n\n"
            f"COMPLIANCE SUMMARY:\n{report.get_summary()}\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove violation detection works.\n"
            f"Critical files currently violate SSOT logging principles and need remediation."
        )
    
    def test_violation_severity_classification(self):
        """
        Test that violations are correctly classified by severity.
        
        EXPECTED: This test validates severity assignment and MUST FAIL if critical violations exist.
        """
        violations = self.scanner.scan_critical_files()
        report = self.scanner.get_compliance_report()
        
        # Count violations by severity
        critical_violations = self.scanner.get_violations_by_severity("CRITICAL")
        high_violations = self.scanner.get_violations_by_severity("HIGH")
        
        # Record severity metrics
        self.record_metric("critical_severity_violations", len(critical_violations))
        self.record_metric("high_severity_violations", len(high_violations))
        self.record_metric("total_severity_violations", len(violations))
        
        # CRITICAL: This assertion MUST FAIL if critical violations exist
        assert len(critical_violations) == 0, (
            f"CRITICAL SEVERITY LOGGING VIOLATIONS DETECTED!\n"
            f"Found {len(critical_violations)} CRITICAL violations in golden path files.\n\n"
            f"CRITICAL VIOLATIONS:\n{self._format_violations(critical_violations)}\n\n"
            f"HIGH VIOLATIONS: {len(high_violations)}\n\n"
            f"SEVERITY BREAKDOWN:\n{report.violations_by_severity}\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove severity detection works.\n"
            f"Critical golden path files must be SSOT compliant for system stability."
        )
    
    def _format_violations(self, violations: List[LoggingViolation]) -> str:
        """Format violations for readable error messages."""
        if not violations:
            return "No violations found."
        
        formatted = []
        for violation in violations:
            formatted.append(
                f"  • {violation.file_path}:{violation.line_number}\n"
                f"    Type: {violation.violation_type} (Severity: {violation.severity})\n"
                f"    Content: {violation.content.strip()}\n"
                f"    Expected: {violation.expected_usage}"
            )
        
        return "\n".join(formatted)
    
    def _format_pattern_summary(self, pattern_counts: dict) -> str:
        """Format violation pattern summary."""
        if not pattern_counts:
            return "No patterns detected."
        
        formatted = []
        for pattern, count in sorted(pattern_counts.items()):
            formatted.append(f"  • {pattern}: {count} violations")
        
        return "\n".join(formatted)
    
    def teardown_method(self, method=None):
        """Clean up test resources."""
        # Reset scanner for next test
        if hasattr(self, 'scanner'):
            self.scanner.reset_report()
        
        # Call parent teardown
        super().teardown_method(method)


# === TEST EXECUTION CONTROL ===

if __name__ == "__main__":
    # Run this test directly to see violations
    pytest.main([__file__, "-v", "-s", "--tb=short"])