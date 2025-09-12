#!/usr/bin/env python3
"""
Severity tier definitions and categorization for violation reporting.
Implements a 4-tier system with business-aligned prioritization.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class SeverityLevel(Enum):
    """4-tier severity system for violations"""
    CRITICAL = "critical"  # Max 5 - System breaking, production impacting
    HIGH = "high"         # Max 20 - Major issues requiring immediate attention
    MEDIUM = "medium"     # Max 100 - Important issues to fix in current sprint
    LOW = "low"          # Unlimited - Technical debt, improvements


@dataclass
class SeverityConfig:
    """Configuration for a severity level"""
    display_name: str
    max_violations: int
    emoji: str
    text_marker: str
    blocks_deployment: bool
    business_impact: str
    remediation_timeline: str
    color_code: str  # For terminal/HTML output


class SeverityTiers:
    """Manages violation severity tiers and categorization"""
    
    SEVERITY_CONFIGS: Dict[SeverityLevel, SeverityConfig] = {
        SeverityLevel.CRITICAL: SeverityConfig(
            display_name="CRITICAL",
            max_violations=5,
            emoji=" ALERT: ",
            text_marker="[CRIT]",
            blocks_deployment=True,
            business_impact="System stability at risk, customer-facing failures likely",
            remediation_timeline="Immediate - Stop all work and fix",
            color_code="\033[91m"  # Bright red
        ),
        SeverityLevel.HIGH: SeverityConfig(
            display_name="HIGH",
            max_violations=20,
            emoji="[U+1F534]",
            text_marker="[HIGH]",
            blocks_deployment=True,
            business_impact="Service degradation possible, security vulnerabilities",
            remediation_timeline="Within 24 hours",
            color_code="\033[31m"  # Red
        ),
        SeverityLevel.MEDIUM: SeverityConfig(
            display_name="MEDIUM",
            max_violations=100,
            emoji="[U+1F7E1]",
            text_marker="[MED]",
            blocks_deployment=True,
            business_impact="Technical debt accumulating, maintainability concerns",
            remediation_timeline="Current sprint",
            color_code="\033[33m"  # Yellow
        ),
        SeverityLevel.LOW: SeverityConfig(
            display_name="LOW",
            max_violations=999999,  # Effectively unlimited
            emoji="[U+1F7E2]",
            text_marker="[LOW]",
            blocks_deployment=False,
            business_impact="Code quality improvements, best practice violations",
            remediation_timeline="Next refactor cycle",
            color_code="\033[32m"  # Green
        )
    }
    
    # Violation type to severity mapping with business context
    VIOLATION_SEVERITY_MAP = {
        # CRITICAL - System breaking
        "production_test_stub": SeverityLevel.CRITICAL,
        "missing_critical_service": SeverityLevel.CRITICAL,
        "database_connection_failure": SeverityLevel.CRITICAL,
        "security_vulnerability_high": SeverityLevel.CRITICAL,
        "infinite_loop_detected": SeverityLevel.CRITICAL,
        "memory_leak_severe": SeverityLevel.CRITICAL,
        "hardcoded_secrets": SeverityLevel.CRITICAL,
        
        # HIGH - Major issues
        "file_size_extreme": SeverityLevel.HIGH,  # >500 lines
        "function_complexity_extreme": SeverityLevel.HIGH,  # >50 lines
        "duplicate_critical_logic": SeverityLevel.HIGH,
        "missing_error_handling": SeverityLevel.HIGH,
        "test_coverage_critical": SeverityLevel.HIGH,  # <30%
        "security_vulnerability_medium": SeverityLevel.HIGH,
        "api_breaking_change": SeverityLevel.HIGH,
        "database_migration_unsafe": SeverityLevel.HIGH,
        
        # MEDIUM - Important issues
        "file_size_high": SeverityLevel.MEDIUM,  # >300 lines
        "function_complexity_high": SeverityLevel.MEDIUM,  # >25 lines
        "duplicate_types": SeverityLevel.MEDIUM,
        "test_coverage_low": SeverityLevel.MEDIUM,  # <60%
        "missing_documentation": SeverityLevel.MEDIUM,
        "deprecated_api_usage": SeverityLevel.MEDIUM,
        "performance_inefficiency": SeverityLevel.MEDIUM,
        "import_cycle_detected": SeverityLevel.MEDIUM,
        
        # LOW - Improvements
        "file_size_warning": SeverityLevel.LOW,  # >200 lines
        "function_complexity_warning": SeverityLevel.LOW,  # >15 lines
        "naming_convention": SeverityLevel.LOW,
        "unused_imports": SeverityLevel.LOW,
        "code_style": SeverityLevel.LOW,
        "missing_type_hints": SeverityLevel.LOW,
        "test_naming": SeverityLevel.LOW,
        "comment_quality": SeverityLevel.LOW,
    }
    
    @classmethod
    def get_severity_for_violation(cls, violation_type: str, 
                                  context: Optional[Dict] = None) -> SeverityLevel:
        """
        Determine severity level for a violation type with context awareness.
        
        Args:
            violation_type: Type of violation
            context: Additional context (file_path, is_production, etc.)
        
        Returns:
            Appropriate severity level
        """
        # Check if it's a known violation type
        if violation_type in cls.VIOLATION_SEVERITY_MAP:
            base_severity = cls.VIOLATION_SEVERITY_MAP[violation_type]
        else:
            # Default to LOW for unknown violations
            base_severity = SeverityLevel.LOW
        
        # Apply context-based adjustments
        if context:
            # Elevate severity for production code
            if context.get("is_production", False):
                if base_severity == SeverityLevel.LOW:
                    base_severity = SeverityLevel.MEDIUM
                elif base_severity == SeverityLevel.MEDIUM:
                    base_severity = SeverityLevel.HIGH
            
            # Reduce severity for test/example code
            if context.get("is_test", False) or context.get("is_example", False):
                if base_severity == SeverityLevel.HIGH:
                    base_severity = SeverityLevel.MEDIUM
                elif base_severity == SeverityLevel.MEDIUM:
                    base_severity = SeverityLevel.LOW
            
            # Critical paths always get elevated severity
            if "critical_path" in context.get("file_path", "").lower():
                if base_severity in [SeverityLevel.LOW, SeverityLevel.MEDIUM]:
                    base_severity = SeverityLevel.HIGH
        
        return base_severity
    
    @classmethod
    def categorize_violations(cls, violations: List) -> Dict[SeverityLevel, List]:
        """
        Categorize violations by severity level.
        
        Args:
            violations: List of violation objects
        
        Returns:
            Dictionary mapping severity levels to violations
        """
        categorized = {level: [] for level in SeverityLevel}
        
        for violation in violations:
            # Determine context
            context = {
                "file_path": getattr(violation, "file_path", ""),
                "is_production": cls._is_production_file(getattr(violation, "file_path", "")),
                "is_test": cls._is_test_file(getattr(violation, "file_path", "")),
                "is_example": cls._is_example_file(getattr(violation, "file_path", ""))
            }
            
            # Get severity based on violation type
            violation_type = getattr(violation, "type", "unknown")
            severity = cls.get_severity_for_violation(violation_type, context)
            
            categorized[severity].append(violation)
        
        return categorized
    
    @classmethod
    def check_deployment_readiness(cls, violations_by_severity: Dict[SeverityLevel, List]) -> Tuple[bool, str]:
        """
        Check if the system is ready for deployment based on violation counts.
        
        Args:
            violations_by_severity: Violations categorized by severity
        
        Returns:
            Tuple of (is_ready, reason_message)
        """
        blocking_violations = []
        
        for severity, config in cls.SEVERITY_CONFIGS.items():
            violation_count = len(violations_by_severity.get(severity, []))
            if config.blocks_deployment and violation_count > config.max_violations:
                blocking_violations.append(
                    f"{config.display_name}: {violation_count}/{config.max_violations} violations"
                )
        
        if blocking_violations:
            return False, f"Deployment blocked by: {', '.join(blocking_violations)}"
        
        return True, "System ready for deployment"
    
    @classmethod
    def get_violation_summary(cls, violations_by_severity: Dict[SeverityLevel, List],
                            use_emoji: bool = True) -> str:
        """
        Generate a summary of violations by severity.
        
        Args:
            violations_by_severity: Violations categorized by severity
            use_emoji: Whether to use emoji markers
        
        Returns:
            Formatted summary string
        """
        lines = []
        
        for severity in SeverityLevel:
            config = cls.SEVERITY_CONFIGS[severity]
            count = len(violations_by_severity.get(severity, []))
            
            marker = config.emoji if use_emoji else config.text_marker
            status = " PASS: " if count <= config.max_violations else " FAIL: "
            
            if config.blocks_deployment:
                line = f"{marker} {config.display_name}: {count}/{config.max_violations} {status}"
            else:
                line = f"{marker} {config.display_name}: {count}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    @staticmethod
    def _is_production_file(file_path: str) -> bool:
        """Check if a file is production code"""
        test_indicators = ["/test", "/tests", "_test.", "test_", "/spec", "/mock"]
        return not any(indicator in file_path.lower() for indicator in test_indicators)
    
    @staticmethod
    def _is_test_file(file_path: str) -> bool:
        """Check if a file is test code"""
        test_indicators = ["/test", "/tests", "_test.", "test_", "/spec"]
        return any(indicator in file_path.lower() for indicator in test_indicators)
    
    @staticmethod
    def _is_example_file(file_path: str) -> bool:
        """Check if a file is example/demo code"""
        example_indicators = ["/example", "/demo", "/sample", "/tutorial"]
        return any(indicator in file_path.lower() for indicator in example_indicators)