"""Type validation error definitions and severity levels."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TypeMismatchSeverity(Enum):
    """Severity levels for type mismatches."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TypeMismatch:
    """Represents a type mismatch between frontend and backend."""
    field_path: str
    backend_type: str
    frontend_type: str
    severity: TypeMismatchSeverity
    message: str
    suggestion: Optional[str] = None


def generate_validation_report(mismatches: list[TypeMismatch]) -> str:
    """Generate a human-readable validation report."""
    
    if not mismatches:
        return " PASS:  All type validations passed! Frontend and backend schemas are consistent."
    
    # Group by severity
    by_severity = _group_mismatches_by_severity(mismatches)
    
    report_lines = _create_report_header(len(mismatches))
    
    # Report by severity
    for severity in [TypeMismatchSeverity.CRITICAL, TypeMismatchSeverity.ERROR, 
                     TypeMismatchSeverity.WARNING, TypeMismatchSeverity.INFO]:
        
        if severity not in by_severity:
            continue
        
        severity_mismatches = by_severity[severity]
        report_lines.extend(_create_severity_section(severity, severity_mismatches))
    
    return "\n".join(report_lines)


def _group_mismatches_by_severity(mismatches: list[TypeMismatch]) -> dict:
    """Group mismatches by severity level."""
    by_severity = {}
    for mismatch in mismatches:
        severity = mismatch.severity
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(mismatch)
    return by_severity


def _create_report_header(total_mismatches: int) -> list[str]:
    """Create report header with total count."""
    return [
        "Type Validation Report",
        "=" * 50,
        f"Total mismatches found: {total_mismatches}",
        ""
    ]


def _create_severity_section(severity: TypeMismatchSeverity, mismatches: list[TypeMismatch]) -> list[str]:
    """Create a section for a specific severity level."""
    icon = _get_severity_icon(severity.value)
    
    section_lines = [
        f"{icon} {severity.value.upper()} ({len(mismatches)} issues)",
        "-" * 30
    ]
    
    for mismatch in mismatches:
        section_lines.extend(_create_mismatch_entry(mismatch))
    
    return section_lines


def _get_severity_icon(severity_value: str) -> str:
    """Get icon for severity level."""
    icons = {
        "critical": " ALERT: ", 
        "error": " FAIL: ", 
        "warning": " WARNING: [U+FE0F]", 
        "info": "[U+2139][U+FE0F]"
    }
    return icons.get(severity_value, "[U+2753]")


def _create_mismatch_entry(mismatch: TypeMismatch) -> list[str]:
    """Create entry for a single type mismatch."""
    entry_lines = [
        f"Field: {mismatch.field_path}",
        f"Backend: {mismatch.backend_type}",
        f"Frontend: {mismatch.frontend_type}",
        f"Issue: {mismatch.message}"
    ]
    
    if mismatch.suggestion:
        entry_lines.append(f"Suggestion: {mismatch.suggestion}")
    
    entry_lines.append("")
    return entry_lines