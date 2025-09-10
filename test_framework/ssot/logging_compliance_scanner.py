"""
SSOT Logging Compliance Scanner Infrastructure

This module provides the infrastructure to detect logging SSOT violations across the codebase.
It scans files for direct logging imports and usage patterns that violate the SSOT principle.

Business Value: Platform/Internal - System Stability & Development Velocity
Ensures consistent logging infrastructure and prevents logging violations that cause system instability.

CRITICAL: This scanner is designed to detect violations and provide detailed reporting
for remediation purposes. It supports the creation of failing tests that prove
violation detection works correctly.

REQUIREMENTS per CLAUDE.md:
- Must detect direct logging.getLogger() usage
- Must identify files bypassing shared.logging.unified_logger_factory
- Must provide detailed violation reports with file paths and line numbers
- Must support batch scanning of critical golden path components
- Must integrate with SSotBaseTestCase for test-driven remediation

Used by:
- tests/unit/ssot_validation/test_logging_import_compliance.py
- tests/integration/ssot_validation/test_logging_ssot_cross_service.py
"""

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from shared.isolated_environment import get_env


@dataclass
class LoggingViolation:
    """Represents a single logging SSOT violation."""
    file_path: str
    line_number: int
    violation_type: str
    content: str
    severity: str = "HIGH"
    expected_import: str = "from shared.logging.unified_logger_factory import UnifiedLoggerFactory"
    expected_usage: str = "logger = UnifiedLoggerFactory.get_logger(__name__)"


@dataclass 
class LoggingComplianceReport:
    """Comprehensive report of logging SSOT violations."""
    total_files_scanned: int = 0
    total_violations: int = 0
    violations_by_severity: Dict[str, int] = field(default_factory=dict)
    violations_by_file: Dict[str, List[LoggingViolation]] = field(default_factory=dict)
    violations_by_type: Dict[str, List[LoggingViolation]] = field(default_factory=dict)
    critical_files_violations: Dict[str, List[LoggingViolation]] = field(default_factory=dict)
    
    def add_violation(self, violation: LoggingViolation) -> None:
        """Add a violation to the report."""
        self.total_violations += 1
        
        # Track by severity
        if violation.severity not in self.violations_by_severity:
            self.violations_by_severity[violation.severity] = 0
        self.violations_by_severity[violation.severity] += 1
        
        # Track by file
        if violation.file_path not in self.violations_by_file:
            self.violations_by_file[violation.file_path] = []
        self.violations_by_file[violation.file_path].append(violation)
        
        # Track by type
        if violation.violation_type not in self.violations_by_type:
            self.violations_by_type[violation.violation_type] = []
        self.violations_by_type[violation.violation_type].append(violation)
    
    def get_summary(self) -> str:
        """Get a summary string of the compliance report."""
        summary = f"LOGGING SSOT COMPLIANCE REPORT\n"
        summary += f"Total Files Scanned: {self.total_files_scanned}\n"
        summary += f"Total Violations: {self.total_violations}\n"
        
        if self.violations_by_severity:
            summary += f"\nViolations by Severity:\n"
            for severity, count in sorted(self.violations_by_severity.items()):
                summary += f"  {severity}: {count}\n"
        
        if self.violations_by_type:
            summary += f"\nViolations by Type:\n"
            for vtype, violations in self.violations_by_type.items():
                summary += f"  {vtype}: {len(violations)}\n"
        
        return summary
    
    def get_detailed_violations(self) -> str:
        """Get detailed violation information."""
        if not self.violations_by_file:
            return "No violations found."
        
        details = "DETAILED VIOLATIONS:\n\n"
        for file_path, violations in self.violations_by_file.items():
            details += f"FILE: {file_path}\n"
            for violation in violations:
                details += f"  Line {violation.line_number}: {violation.violation_type}\n"
                details += f"    Content: {violation.content.strip()}\n"
                details += f"    Severity: {violation.severity}\n"
                details += f"    Expected: {violation.expected_usage}\n\n"
        
        return details


class LoggingComplianceScanner:
    """
    SSOT Logging Compliance Scanner - Infrastructure for detecting logging violations.
    
    This scanner identifies files that violate the logging SSOT principle by:
    1. Using direct `import logging` instead of unified_logger_factory
    2. Using `logging.getLogger(__name__)` instead of UnifiedLoggerFactory.get_logger()
    3. Bypassing the centralized logging infrastructure
    
    CRITICAL: This scanner is used by failing tests to prove violation detection works.
    """
    
    # Critical files that MUST be SSOT compliant (Golden Path components)
    CRITICAL_FILES = {
        # WebSocket Core (CRITICAL for golden path)
        "netra_backend/app/websocket_core/circuit_breaker.py",
        "netra_backend/app/websocket_core/connection_id_manager.py",
        "netra_backend/app/websocket_core/graceful_degradation_manager.py",
        "netra_backend/app/routes/websocket.py",
        
        # Auth Service (HIGH for golden path)
        "auth_service/services/jwt_service.py",
        "auth_service/services/oauth_service.py", 
        "auth_service/auth_core/core/jwt_handler.py",
        
        # Backend Core (CRITICAL)
        "netra_backend/app/main.py",
        "netra_backend/app/auth_integration/auth.py",
    }
    
    # Violation patterns to detect
    VIOLATION_PATTERNS = {
        "direct_logging_import": r"^import logging$",
        "direct_getlogger_usage": r"logging\.getLogger\(",
        "local_logging_import": r"^\s*import logging",
        "logging_getlogger_assignment": r"logger\s*=\s*logging\.getLogger\(",
    }
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize the compliance scanner."""
        self.env = get_env()
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.report = LoggingComplianceReport()
    
    def scan_file(self, file_path: Union[str, Path]) -> List[LoggingViolation]:
        """
        Scan a single file for logging SSOT violations.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            List of violations found in the file
        """
        violations = []
        file_path = Path(file_path)
        
        if not file_path.exists() or not file_path.suffix == '.py':
            return violations
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Skip empty lines and comments
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # Check for each violation pattern
                for violation_type, pattern in self.VIOLATION_PATTERNS.items():
                    if re.search(pattern, line):
                        # Determine severity based on file criticality
                        severity = "CRITICAL" if str(file_path) in self.CRITICAL_FILES else "HIGH"
                        
                        violation = LoggingViolation(
                            file_path=str(file_path),
                            line_number=line_num,
                            violation_type=violation_type,
                            content=line.rstrip(),
                            severity=severity
                        )
                        violations.append(violation)
                        self.report.add_violation(violation)
        
        except Exception as e:
            # Log the error but continue scanning
            print(f"Error scanning file {file_path}: {e}")
        
        return violations
    
    def scan_directory(self, directory_path: Union[str, Path], recursive: bool = True) -> List[LoggingViolation]:
        """
        Scan a directory for logging SSOT violations.
        
        Args:
            directory_path: Path to the directory to scan
            recursive: Whether to scan subdirectories recursively
            
        Returns:
            List of all violations found in the directory
        """
        violations = []
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            return violations
        
        # Get all Python files
        if recursive:
            python_files = directory_path.rglob("*.py")
        else:
            python_files = directory_path.glob("*.py")
        
        for file_path in python_files:
            # Skip test files for now (they may have different patterns)
            if "test_" in file_path.name or "/tests/" in str(file_path):
                continue
                
            file_violations = self.scan_file(file_path)
            violations.extend(file_violations)
            self.report.total_files_scanned += 1
        
        return violations
    
    def scan_critical_files(self) -> List[LoggingViolation]:
        """
        Scan only the critical files defined in CRITICAL_FILES.
        
        Returns:
            List of violations found in critical files
        """
        violations = []
        
        for critical_file in self.CRITICAL_FILES:
            file_path = self.base_path / critical_file
            if file_path.exists():
                file_violations = self.scan_file(file_path)
                violations.extend(file_violations)
                
                # Track critical file violations separately
                if file_violations:
                    self.report.critical_files_violations[str(file_path)] = file_violations
                
                self.report.total_files_scanned += 1
        
        return violations
    
    def scan_service(self, service_name: str) -> List[LoggingViolation]:
        """
        Scan a specific service for logging SSOT violations.
        
        Args:
            service_name: Name of the service to scan (e.g., 'auth_service', 'netra_backend')
            
        Returns:
            List of violations found in the service
        """
        service_path = self.base_path / service_name
        
        if not service_path.exists():
            print(f"Service directory not found: {service_path}")
            return []
        
        return self.scan_directory(service_path, recursive=True)
    
    def generate_remediation_suggestions(self) -> Dict[str, str]:
        """
        Generate remediation suggestions for each violation type.
        
        Returns:
            Dictionary mapping violation types to remediation suggestions
        """
        suggestions = {
            "direct_logging_import": (
                "Replace 'import logging' with:\n"
                "from shared.logging.unified_logger_factory import UnifiedLoggerFactory"
            ),
            "direct_getlogger_usage": (
                "Replace 'logging.getLogger(__name__)' with:\n"
                "UnifiedLoggerFactory.get_logger(__name__)"
            ),
            "local_logging_import": (
                "Remove local logging import and use SSOT factory:\n"
                "from shared.logging.unified_logger_factory import UnifiedLoggerFactory"
            ),
            "logging_getlogger_assignment": (
                "Replace logger assignment with SSOT pattern:\n"
                "logger = UnifiedLoggerFactory.get_logger(__name__)"
            ),
        }
        
        return suggestions
    
    def get_compliance_report(self) -> LoggingComplianceReport:
        """Get the current compliance report."""
        return self.report
    
    def reset_report(self) -> None:
        """Reset the compliance report for a new scan."""
        self.report = LoggingComplianceReport()
    
    def has_violations(self) -> bool:
        """Check if any violations were found."""
        return self.report.total_violations > 0
    
    def get_critical_violations_count(self) -> int:
        """Get the count of violations in critical files."""
        return sum(len(violations) for violations in self.report.critical_files_violations.values())
    
    def get_violations_by_severity(self, severity: str) -> List[LoggingViolation]:
        """Get all violations of a specific severity."""
        violations = []
        for file_violations in self.report.violations_by_file.values():
            violations.extend([v for v in file_violations if v.severity == severity])
        return violations


# === EXPORT CONTROL ===

__all__ = [
    "LoggingViolation",
    "LoggingComplianceReport", 
    "LoggingComplianceScanner",
]