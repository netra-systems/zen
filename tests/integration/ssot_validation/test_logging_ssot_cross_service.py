"""
Integration Test: Cross-Service Logging SSOT Enforcement

PURPOSE: This test is DESIGNED TO FAIL with current cross-service logging violations.
It validates that all services use shared.logging.unified_logger_factory consistently.

CRITICAL: This test proves cross-service SSOT enforcement works by failing
with current violations across netra_backend, auth_service, and other services.

Business Value: Platform/Internal - System Stability & Development Velocity
Ensures consistent logging infrastructure across all microservices for operational visibility.

TEST DESIGN:
- Inherits from SSotBaseTestCase for consistent test infrastructure
- Scans multiple services for logging SSOT compliance
- MUST FAIL initially to prove cross-service detection works
- Validates unified logging factory usage across service boundaries
- Detects services bypassing SSOT logging infrastructure

REQUIREMENTS per CLAUDE.md:
- Must inherit from SSotBaseTestCase 
- Must validate all services use shared.logging.unified_logger_factory
- Must be atomic and complete within 2 minutes (integration test)
- Must provide detailed cross-service violation reports
- NO Docker dependencies (integration test without docker orchestration)

SERVICES TESTED:
- netra_backend: Main backend service
- auth_service: Authentication service
- analytics_service: Analytics service (if exists)
- Cross-service shared modules

EXPECTED BEHAVIOR:
- Test MUST fail initially (proves cross-service detection works)
- Clear violation report across all services
- Service-by-service breakdown of violations
- Remediation guidance for each service
- Enable test-driven cross-service SSOT compliance
"""

import pytest
from pathlib import Path
from typing import Dict, List, Set

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.logging_compliance_scanner import (
    LoggingComplianceScanner,
    LoggingViolation,
    LoggingComplianceReport
)


class TestLoggingSSotCrossService(SSotBaseTestCase):
    """
    Integration test for cross-service logging SSOT compliance.
    
    This test is DESIGNED TO FAIL with current cross-service violations to prove detection works.
    """
    
    def setup_method(self, method=None):
        """Set up test with SSOT base test case."""
        super().setup_method(method)
        self.scanner = LoggingComplianceScanner()
        self.base_path = Path.cwd()
        
        # Define services to test
        self.services_under_test = {
            "netra_backend": "netra_backend/app",
            "auth_service": "auth_service",
            "analytics_service": "analytics_service", 
            "shared": "shared",
        }
        
        # Record test category and expected failure
        self.record_metric("test_category", "cross_service_ssot_compliance")
        self.record_metric("expected_to_fail", True)
        self.record_metric("detection_scope", "multi_service")
        self.record_metric("services_count", len(self.services_under_test))
    
    def test_netra_backend_service_logging_compliance(self):
        """
        Test netra_backend service for logging SSOT violations.
        
        EXPECTED: This test MUST FAIL due to current violations.
        """
        service_name = "netra_backend"
        service_path = self.services_under_test[service_name]
        
        violations = self._scan_service_for_violations(service_name, service_path)
        
        # Record service-specific metrics
        self.record_metric(f"{service_name}_violations_count", len(violations))
        self.record_metric(f"{service_name}_scan_completed", True)
        
        # CRITICAL: This assertion MUST FAIL to prove detection works
        assert len(violations) == 0, (
            f"LOGGING SSOT VIOLATIONS DETECTED in {service_name} service!\n"
            f"Found {len(violations)} violations that violate cross-service SSOT logging principle.\n\n"
            f"SERVICE: {service_name}\n"
            f"PATH: {service_path}\n\n"
            f"VIOLATIONS:\n{self._format_service_violations(violations)}\n\n"
            f"CROSS-SERVICE IMPACT: These violations break logging consistency across services.\n"
            f"REMEDIATION: Replace all direct logging imports with:\n"
            f"from shared.logging.unified_logger_factory import UnifiedLoggerFactory\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove cross-service detection works.\n"
            f"The {service_name} service currently bypasses SSOT logging infrastructure."
        )
    
    def test_auth_service_logging_compliance(self):
        """
        Test auth_service for logging SSOT violations.
        
        EXPECTED: This test MUST FAIL due to current violations.
        """
        service_name = "auth_service"
        service_path = self.services_under_test[service_name]
        
        violations = self._scan_service_for_violations(service_name, service_path)
        
        # Record service-specific metrics
        self.record_metric(f"{service_name}_violations_count", len(violations))
        self.record_metric(f"{service_name}_scan_completed", True)
        
        # CRITICAL: This assertion MUST FAIL to prove detection works
        assert len(violations) == 0, (
            f"LOGGING SSOT VIOLATIONS DETECTED in {service_name} service!\n"
            f"Found {len(violations)} violations that violate cross-service SSOT logging principle.\n\n"
            f"SERVICE: {service_name}\n"
            f"PATH: {service_path}\n\n"
            f"VIOLATIONS:\n{self._format_service_violations(violations)}\n\n"
            f"CROSS-SERVICE IMPACT: Auth service logging inconsistency affects security audit trails.\n"
            f"REMEDIATION: Replace all direct logging imports with:\n"
            f"from shared.logging.unified_logger_factory import UnifiedLoggerFactory\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove cross-service detection works.\n"
            f"The {service_name} service currently bypasses SSOT logging infrastructure."
        )
    
    def test_shared_modules_logging_compliance(self):
        """
        Test shared modules for logging SSOT violations.
        
        EXPECTED: This test should PASS as shared modules should be SSOT compliant.
        """
        service_name = "shared"
        service_path = self.services_under_test[service_name]
        
        violations = self._scan_service_for_violations(service_name, service_path)
        
        # Record service-specific metrics
        self.record_metric(f"{service_name}_violations_count", len(violations))
        self.record_metric(f"{service_name}_scan_completed", True)
        
        # Shared modules should be SSOT compliant (this might pass)
        if len(violations) > 0:
            pytest.fail(
                f"CRITICAL: SHARED MODULES HAVE LOGGING SSOT VIOLATIONS!\n"
                f"Found {len(violations)} violations in the SSOT infrastructure itself.\n\n"
                f"SERVICE: {service_name}\n"
                f"PATH: {service_path}\n\n"
                f"VIOLATIONS:\n{self._format_service_violations(violations)}\n\n"
                f"CRITICAL IMPACT: Shared module violations break SSOT foundation.\n"
                f"IMMEDIATE ACTION REQUIRED: Fix shared module violations first.\n\n"
                f"This is a critical infrastructure issue that must be resolved immediately."
            )
        
        # Record success if no violations in shared modules
        self.record_metric("shared_modules_compliant", True)
    
    def test_cross_service_violation_distribution(self):
        """
        Test violation distribution across all services.
        
        EXPECTED: This test provides comprehensive cross-service violation analysis.
        """
        all_violations: Dict[str, List[LoggingViolation]] = {}
        total_violations = 0
        
        # Scan all services
        for service_name, service_path in self.services_under_test.items():
            service_violations = self._scan_service_for_violations(service_name, service_path)
            all_violations[service_name] = service_violations
            total_violations += len(service_violations)
            
            # Record per-service metrics
            self.record_metric(f"{service_name}_violations", len(service_violations))
        
        # Calculate cross-service metrics
        services_with_violations = sum(1 for violations in all_violations.values() if violations)
        violation_rate = (services_with_violations / len(self.services_under_test)) * 100
        
        # Record cross-service metrics
        self.record_metric("total_cross_service_violations", total_violations)
        self.record_metric("services_with_violations", services_with_violations)
        self.record_metric("cross_service_violation_rate", violation_rate)
        
        # Generate cross-service analysis
        analysis = self._generate_cross_service_analysis(all_violations)
        
        # CRITICAL: This assertion MUST FAIL to prove cross-service detection works
        assert total_violations == 0, (
            f"CROSS-SERVICE LOGGING SSOT VIOLATIONS DETECTED!\n"
            f"Found {total_violations} total violations across {services_with_violations} services.\n"
            f"Cross-service violation rate: {violation_rate:.1f}%\n\n"
            f"CROSS-SERVICE ANALYSIS:\n{analysis}\n\n"
            f"SYSTEM-WIDE IMPACT: Inconsistent logging across services breaks:\n"
            f"  [U+2022] Centralized log aggregation\n"
            f"  [U+2022] Distributed tracing correlation\n"
            f"  [U+2022] Security audit trails\n"
            f"  [U+2022] Operational monitoring\n\n"
            f"REMEDIATION STRATEGY:\n"
            f"1. Fix shared modules first (if any violations)\n"
            f"2. Service-by-service SSOT migration\n"
            f"3. Cross-service integration testing\n"
            f"4. Unified logging configuration deployment\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove cross-service detection works.\n"
            f"Multiple services currently bypass SSOT logging infrastructure."
        )
    
    def test_unified_logger_factory_usage_validation(self):
        """
        Test that services properly use UnifiedLoggerFactory when it exists.
        
        EXPECTED: This test validates proper SSOT factory usage patterns.
        """
        # Check if unified logger factory is accessible
        factory_violations = []
        factory_usage_violations = []
        
        for service_name, service_path in self.services_under_test.items():
            if service_name == "shared":
                continue  # Skip shared modules in this test
            
            violations = self._scan_service_for_violations(service_name, service_path)
            
            # Categorize violations by type
            for violation in violations:
                if "direct_logging_import" in violation.violation_type:
                    factory_violations.append(violation)
                elif "getlogger" in violation.violation_type.lower():
                    factory_usage_violations.append(violation)
        
        # Record factory usage metrics
        self.record_metric("factory_import_violations", len(factory_violations))
        self.record_metric("factory_usage_violations", len(factory_usage_violations))
        self.record_metric("total_factory_violations", len(factory_violations) + len(factory_usage_violations))
        
        total_factory_violations = len(factory_violations) + len(factory_usage_violations)
        
        # CRITICAL: This assertion MUST FAIL to prove factory validation works
        assert total_factory_violations == 0, (
            f"UNIFIED LOGGER FACTORY USAGE VIOLATIONS DETECTED!\n"
            f"Found {total_factory_violations} violations of UnifiedLoggerFactory usage.\n\n"
            f"FACTORY IMPORT VIOLATIONS: {len(factory_violations)}\n"
            f"FACTORY USAGE VIOLATIONS: {len(factory_usage_violations)}\n\n"
            f"IMPORT VIOLATIONS:\n{self._format_violations_list(factory_violations)}\n\n"
            f"USAGE VIOLATIONS:\n{self._format_violations_list(factory_usage_violations)}\n\n"
            f"SSOT PRINCIPLE VIOLATION: Services are bypassing the unified logging factory.\n"
            f"CORRECT PATTERN:\n"
            f"from shared.logging.unified_logger_factory import UnifiedLoggerFactory\n"
            f"logger = UnifiedLoggerFactory.get_logger(__name__)\n\n"
            f"WHY THIS FAILS: This test is DESIGNED to fail to prove factory validation works.\n"
            f"Services currently use direct logging instead of SSOT factory."
        )
    
    def _scan_service_for_violations(self, service_name: str, service_path: str) -> List[LoggingViolation]:
        """Scan a service for logging SSOT violations."""
        full_service_path = self.base_path / service_path
        
        if not full_service_path.exists():
            self.record_metric(f"{service_name}_path_exists", False)
            return []
        
        self.record_metric(f"{service_name}_path_exists", True)
        
        # Reset scanner for clean service scan
        self.scanner.reset_report()
        violations = self.scanner.scan_directory(full_service_path, recursive=True)
        
        # Record scan metrics
        report = self.scanner.get_compliance_report()
        self.record_metric(f"{service_name}_files_scanned", report.total_files_scanned)
        
        return violations
    
    def _format_service_violations(self, violations: List[LoggingViolation]) -> str:
        """Format violations for a specific service."""
        if not violations:
            return "No violations found."
        
        # Group violations by file
        violations_by_file: Dict[str, List[LoggingViolation]] = {}
        for violation in violations:
            file_path = violation.file_path
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append(violation)
        
        formatted = []
        for file_path, file_violations in violations_by_file.items():
            formatted.append(f"  FILE: {file_path}")
            for violation in file_violations:
                formatted.append(
                    f"    Line {violation.line_number}: {violation.violation_type}\n"
                    f"    Content: {violation.content.strip()}\n"
                    f"    Severity: {violation.severity}"
                )
            formatted.append("")  # Empty line between files
        
        return "\n".join(formatted)
    
    def _format_violations_list(self, violations: List[LoggingViolation]) -> str:
        """Format a list of violations."""
        if not violations:
            return "None"
        
        formatted = []
        for violation in violations:
            formatted.append(
                f"  [U+2022] {violation.file_path}:{violation.line_number} - {violation.violation_type}"
            )
        
        return "\n".join(formatted)
    
    def _generate_cross_service_analysis(self, all_violations: Dict[str, List[LoggingViolation]]) -> str:
        """Generate comprehensive cross-service violation analysis."""
        analysis = []
        
        analysis.append("SERVICE-BY-SERVICE BREAKDOWN:")
        for service_name, violations in all_violations.items():
            status = "VIOLATIONS FOUND" if violations else "COMPLIANT"
            analysis.append(f"  [U+2022] {service_name}: {len(violations)} violations ({status})")
        
        analysis.append("\nVIOLATION HOTSPOTS:")
        
        # Find files with most violations across services
        file_violation_counts: Dict[str, int] = {}
        for violations in all_violations.values():
            for violation in violations:
                file_path = violation.file_path
                file_violation_counts[file_path] = file_violation_counts.get(file_path, 0) + 1
        
        # Sort by violation count and show top violators
        sorted_files = sorted(file_violation_counts.items(), key=lambda x: x[1], reverse=True)
        for file_path, count in sorted_files[:10]:  # Top 10 files
            analysis.append(f"  [U+2022] {file_path}: {count} violations")
        
        analysis.append("\nREMEDIATION PRIORITY:")
        analysis.append("  1. Fix critical golden path files first")
        analysis.append("  2. Service-by-service systematic migration")
        analysis.append("  3. Cross-service integration validation")
        analysis.append("  4. Deployment coordination across services")
        
        return "\n".join(analysis)
    
    def teardown_method(self, method=None):
        """Clean up test resources."""
        # Reset scanner for next test
        if hasattr(self, 'scanner'):
            self.scanner.reset_report()
        
        # Call parent teardown
        super().teardown_method(method)


# === TEST EXECUTION CONTROL ===

if __name__ == "__main__":
    # Run this test directly to see cross-service violations
    pytest.main([__file__, "-v", "-s", "--tb=short"])