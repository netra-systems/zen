#!/usr/bin/env python3
"""
Logging SSOT Violations Validation Script - Issue #885

Purpose: Detect and report current state of logging SSOT violations
to establish baseline before remediation.

Usage:
    python scripts/validate_logging_ssot_violations.py
    python scripts/validate_logging_ssot_violations.py --detailed
    python scripts/validate_logging_ssot_violations.py --critical-only

Business Impact Analysis:
- Operational visibility reduced by inconsistent logging
- Debugging difficulty increased for $500K+ ARR chat functionality
- WebSocket logging issues affect real-time user experience
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class LoggingSSOTViolationDetector:
    """Detects and reports logging SSOT violations"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = defaultdict(list)
        self.statistics = {}
        self.critical_services = [
            "netra_backend/app/websocket_core",
            "netra_backend/app/agents",
            "netra_backend/app/core",
            "auth_service/auth_core",
            "frontend/lib",
            "shared"
        ]

    def scan_all_violations(self) -> Dict:
        """Scan for all types of logging SSOT violations"""
        print("Scanning for logging SSOT violations...")

        # Scan for different violation types
        self._scan_deprecated_imports()
        self._scan_inconsistent_patterns()
        self._scan_critical_services()
        self._scan_configuration_issues()

        # Generate statistics
        self._generate_statistics()

        return {
            "violations": dict(self.violations),
            "statistics": self.statistics
        }

    def _scan_deprecated_imports(self):
        """Scan for deprecated logging import patterns"""
        print("  Scanning deprecated import patterns...")

        deprecated_patterns = [
            (r'import logging(?!\s*#.*SSOT)', "direct_logging_import"),
            (r'from logging import', "from_logging_import"),
            (r'logging\.getLogger\(', "direct_getlogger_call"),
            (r'logger\s*=\s*logging\.', "direct_logger_assignment"),
            (r'Logger\(\)', "direct_logger_instantiation")
        ]

        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                content = python_file.read_text(encoding='utf-8')

                for pattern, violation_type in deprecated_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()

                        # Skip if this is documented as intentional
                        if "# SSOT" in line_content or "# Legacy OK" in line_content:
                            continue

                        self.violations[violation_type].append({
                            "file": str(python_file.relative_to(self.project_root)),
                            "line": line_num,
                            "content": line_content,
                            "pattern": pattern
                        })

            except Exception as e:
                # Skip files that can't be read
                continue

    def _scan_inconsistent_patterns(self):
        """Scan for inconsistent logging patterns across services"""
        print("  Scanning inconsistent logging patterns...")

        service_patterns = {}

        for service in self.critical_services:
            service_path = self.project_root / service
            if not service_path.exists():
                continue

            patterns = self._analyze_service_logging_patterns(service_path)
            service_patterns[service] = patterns

        # Check for inconsistencies
        all_patterns = set()
        for service, patterns in service_patterns.items():
            all_patterns.update(patterns)

        if len(all_patterns) > 1:
            self.violations["inconsistent_patterns"].append({
                "issue": "Multiple logging patterns across services",
                "patterns_found": list(all_patterns),
                "services_affected": service_patterns,
                "business_impact": "Reduces operational visibility and debugging efficiency"
            })

    def _analyze_service_logging_patterns(self, service_path: Path) -> Set[str]:
        """Analyze logging patterns in a service"""
        patterns = set()

        for python_file in service_path.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                content = python_file.read_text(encoding='utf-8')

                # Detect patterns
                if "import logging" in content:
                    patterns.add("standard_logging")
                if "LoggerMixin" in content:
                    patterns.add("mixin_pattern")
                if "self.logger" in content:
                    patterns.add("instance_logger")
                if "logger = " in content and "getLogger" in content:
                    patterns.add("manual_logger_setup")
                if re.search(r'logger\s*=.*Factory', content):
                    patterns.add("factory_logger")

            except:
                continue

        return patterns

    def _scan_critical_services(self):
        """Scan critical services for violations"""
        print("  Scanning critical services...")

        for service in self.critical_services:
            service_path = self.project_root / service
            if not service_path.exists():
                continue

            violations = self._scan_service_violations(service_path)
            if violations:
                self.violations[f"critical_service_{service}"] = violations

    def _scan_service_violations(self, service_path: Path) -> List[Dict]:
        """Scan a service directory for violations"""
        violations = []

        for python_file in service_path.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                content = python_file.read_text(encoding='utf-8')

                # Check for specific violations
                if "import logging" in content and "# SSOT" not in content:
                    violations.append({
                        "file": str(python_file.relative_to(self.project_root)),
                        "type": "deprecated_import",
                        "severity": "high" if "websocket" in str(python_file).lower() else "medium"
                    })

            except:
                continue

        return violations

    def _scan_configuration_issues(self):
        """Scan for logging configuration issues"""
        print("  Scanning configuration issues...")

        config_files = (list(self.project_root.rglob("*config*.py")) +
                       list(self.project_root.rglob("*settings*.py")))

        logging_configs = []
        for config_file in config_files:
            if self._should_skip_file(config_file):
                continue

            try:
                content = config_file.read_text(encoding='utf-8')

                if any(pattern in content for pattern in [
                    "logging.basicConfig", "dictConfig", "LOGGING =", "logger.setLevel"
                ]):
                    logging_configs.append({
                        "file": str(config_file.relative_to(self.project_root)),
                        "content_preview": content[:200] + "..." if len(content) > 200 else content
                    })

            except:
                continue

        if len(logging_configs) > 1:
            self.violations["multiple_logging_configs"].append({
                "issue": "Multiple logging configuration approaches found",
                "configs": logging_configs,
                "business_impact": "Inconsistent logging behavior across environments"
            })

    def _generate_statistics(self):
        """Generate violation statistics"""
        total_violations = sum(len(violations) for violations in self.violations.values())

        self.statistics = {
            "total_violations": total_violations,
            "violation_types": len(self.violations),
            "violations_by_type": {
                vtype: len(violations) for vtype, violations in self.violations.items()
            },
            "critical_services_affected": len([
                k for k in self.violations.keys() if k.startswith("critical_service_")
            ]),
            "business_impact_assessment": self._assess_business_impact(total_violations)
        }

    def _assess_business_impact(self, total_violations: int) -> Dict:
        """Assess business impact of violations"""
        if total_violations == 0:
            severity = "none"
            impact = "No logging SSOT violations detected"
        elif total_violations < 100:
            severity = "low"
            impact = "Minor operational visibility impact"
        elif total_violations < 500:
            severity = "medium"
            impact = "Moderate debugging difficulty, some chat functionality visibility issues"
        elif total_violations < 1000:
            severity = "high"
            impact = "Significant operational visibility reduction, chat debugging impaired"
        else:
            severity = "critical"
            impact = "Major operational visibility issues, $500K+ ARR chat functionality at risk"

        return {
            "severity": severity,
            "impact_description": impact,
            "recommendation": self._get_recommendation(severity)
        }

    def _get_recommendation(self, severity: str) -> str:
        """Get remediation recommendation based on severity"""
        recommendations = {
            "none": "No action needed",
            "low": "Monitor for future violations, consider gradual improvement",
            "medium": "Plan remediation in next sprint, prioritize WebSocket components",
            "high": "Immediate remediation recommended, focus on critical services first",
            "critical": "URGENT: Immediate remediation required, business impact significant"
        }
        return recommendations.get(severity, "Unknown severity level")

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            ".pytest_cache", "build", "dist", ".tox", "migrations"
        ]

        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)

    def generate_report(self, detailed: bool = False) -> str:
        """Generate violation report"""
        report_lines = []

        # Header
        report_lines.append("=" * 80)
        report_lines.append("LOGGING SSOT VIOLATIONS BASELINE REPORT - Issue #885")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Executive Summary
        stats = self.statistics
        report_lines.append("EXECUTIVE SUMMARY")
        report_lines.append("-" * 40)
        report_lines.append(f"Total Violations: {stats['total_violations']}")
        report_lines.append(f"Violation Types: {stats['violation_types']}")
        report_lines.append(f"Critical Services Affected: {stats['critical_services_affected']}")
        report_lines.append("")

        # Business Impact
        impact = stats["business_impact_assessment"]
        report_lines.append("BUSINESS IMPACT ASSESSMENT")
        report_lines.append("-" * 40)
        report_lines.append(f"Severity: {impact['severity'].upper()}")
        report_lines.append(f"Impact: {impact['impact_description']}")
        report_lines.append(f"Recommendation: {impact['recommendation']}")
        report_lines.append("")

        # Violation Breakdown
        report_lines.append("VIOLATION BREAKDOWN")
        report_lines.append("-" * 40)
        for vtype, count in stats["violations_by_type"].items():
            report_lines.append(f"{vtype}: {count} violations")
        report_lines.append("")

        # Detailed violations if requested
        if detailed:
            report_lines.append("DETAILED VIOLATIONS")
            report_lines.append("-" * 40)
            for vtype, violations in self.violations.items():
                if violations:
                    report_lines.append(f"\n{vtype.upper()}:")
                    for violation in violations[:5]:  # Show first 5 of each type
                        if isinstance(violation, dict):
                            if "file" in violation:
                                report_lines.append(f"  File: {violation['file']}")
                                if "line" in violation:
                                    report_lines.append(f"     Line {violation['line']}: {violation.get('content', '')}")
                            elif "issue" in violation:
                                report_lines.append(f"  Issue: {violation['issue']}")
                    if len(violations) > 5:
                        report_lines.append(f"  ... and {len(violations) - 5} more")

        # Conclusion
        report_lines.append("")
        report_lines.append("NEXT STEPS")
        report_lines.append("-" * 40)
        if stats['total_violations'] > 0:
            report_lines.append("BASELINE ESTABLISHED - Violations confirmed")
            report_lines.append("Proceed with SSOT remediation plan")
            report_lines.append("Run failing tests to validate problem")
        else:
            report_lines.append("NO VIOLATIONS FOUND - System already SSOT compliant")
            report_lines.append("No remediation needed")

        return "\n".join(report_lines)


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Validate logging SSOT violations")
    parser.add_argument("--detailed", action="store_true",
                       help="Show detailed violation information")
    parser.add_argument("--critical-only", action="store_true",
                       help="Show only critical service violations")
    parser.add_argument("--json", action="store_true",
                       help="Output results as JSON")

    args = parser.parse_args()

    # Initialize detector
    detector = LoggingSSOTViolationDetector(project_root)

    # Scan for violations
    results = detector.scan_all_violations()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        report = detector.generate_report(detailed=args.detailed)
        print(report)

    # Exit with appropriate code
    total_violations = detector.statistics.get('total_violations', 0)
    if total_violations > 0:
        print(f"\nVALIDATION COMPLETE: {total_violations} violations found")
        sys.exit(1)  # Exit with error to indicate violations exist
    else:
        print("\nVALIDATION COMPLETE: No violations found")
        sys.exit(0)


if __name__ == "__main__":
    main()