#!/usr/bin/env python3
"""
Type Deduplication Validator - Enforces Single Source of Truth

This script validates that NO duplicate type definitions exist across the codebase
and enforces the canonical import paths established in TYPE_DEDUPLICATION_PLAN.md.

Usage:
    python scripts/validate_type_deduplication.py              # Scan and report
    python scripts/validate_type_deduplication.py --strict     # Fail on any duplicates  
    python scripts/validate_type_deduplication.py --fix        # Auto-fix imports (CAREFUL!)
    python scripts/validate_type_deduplication.py --ci         # CI mode (exit codes)
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class DuplicateType:
    """Information about a duplicate type definition."""
    name: str
    locations: List[str]
    canonical_location: Optional[str] = None
    severity: str = "warning"  # warning, error, critical


@dataclass
class ValidationResult:
    """Results of type deduplication validation."""
    total_duplicates: int
    critical_duplicates: List[DuplicateType]
    python_duplicates: List[DuplicateType]
    typescript_duplicates: List[DuplicateType]
    violations: List[str]
    success: bool


class TypeDeduplicationValidator:
    """Validates type deduplication across the codebase."""
    
    def __init__(self, project_root: Path):
        """Initialize validator with project root."""
        self.project_root = project_root
        self.canonical_imports = self._load_canonical_imports()
        
    def _load_canonical_imports(self) -> Dict[str, str]:
        """Load canonical import paths for types."""
        return {
            # Critical Infrastructure Types
            "WebSocketConnectionManager": "app.core.websocket_recovery_strategies",
            "CacheConfig": "app.schemas.config_types", 
            "AgentConfig": "app.schemas.shared_types",
            "AgentMetadata": "app.schemas.registry",
            "DemoAgent": "app.agents.demo_agent",
            
            # High-Frequency Types
            "CircuitBreaker": "app.core.circuit_breaker",
            "AlertSeverity": "app.monitoring.alert_models",
            "AgentState": "app.agents.state",
            "ToolStatus": "app.schemas.Tool",
            "ToolResult": "app.schemas.Tool",
            "ToolInput": "app.schemas.Tool",
            "MetricType": "app.schemas.Metrics",
            "User": "app.schemas.User",
            
            # WebSocket Types
            "WebSocketMessage": "app.schemas.websocket_message_types",
            "ServerMessage": "app.schemas.websocket_message_types",
            "ClientMessage": "app.schemas.websocket_message_types",
            
            # Core Domain Types  
            "Message": "app.schemas.registry",
            "MessageType": "app.schemas.registry",
            "ProcessingResult": "app.schemas.shared_types",
            "ValidationResult": "app.core.type_validation",
        }
    
    def scan_python_duplicates(self) -> List[DuplicateType]:
        """Scan for duplicate Python class definitions."""
        class_definitions = defaultdict(list)
        
        # Scan app/ directory for Python files
        for py_file in self.project_root.glob("app/**/*.py"):
            if "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find class definitions
                class_matches = re.finditer(r'^class\s+(\w+)', content, re.MULTILINE)
                for match in class_matches:
                    class_name = match.group(1)
                    relative_path = str(py_file.relative_to(self.project_root))
                    class_definitions[class_name].append(relative_path)
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Find duplicates
        duplicates = []
        for class_name, locations in class_definitions.items():
            if len(locations) > 1:
                # Filter out test classes (too many legitimate duplicates)
                non_test_locations = [loc for loc in locations if "/tests/" not in loc]
                if len(non_test_locations) > 1:
                    severity = "critical" if class_name in self.canonical_imports else "warning"
                    canonical = self.canonical_imports.get(class_name)
                    
                    duplicates.append(DuplicateType(
                        name=class_name,
                        locations=locations,
                        canonical_location=canonical,
                        severity=severity
                    ))
        
        return sorted(duplicates, key=lambda x: (x.severity == "critical", len(x.locations)), reverse=True)
    
    def scan_typescript_duplicates(self) -> List[DuplicateType]:
        """Scan for duplicate TypeScript type definitions."""
        type_definitions = defaultdict(list)
        
        # Scan frontend/ directory for TypeScript files
        for ts_file in self.project_root.glob("frontend/**/*.ts"):
            if "node_modules" in str(ts_file):
                continue
                
            try:
                with open(ts_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find type/interface definitions
                patterns = [
                    r'^export\s+interface\s+(\w+)',
                    r'^interface\s+(\w+)',
                    r'^export\s+type\s+(\w+)',
                    r'^type\s+(\w+)',
                    r'^export\s+enum\s+(\w+)',
                    r'^enum\s+(\w+)'
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        type_name = match.group(1)
                        relative_path = str(ts_file.relative_to(self.project_root))
                        type_definitions[type_name].append(relative_path)
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Find duplicates
        duplicates = []
        for type_name, locations in type_definitions.items():
            if len(locations) > 1:
                # Filter out obviously generic names
                if type_name in ["Props", "State", "Config"]:
                    continue
                    
                duplicates.append(DuplicateType(
                    name=type_name,
                    locations=locations,
                    severity="warning"
                ))
        
        return sorted(duplicates, key=lambda x: len(x.locations), reverse=True)
    
    def validate_canonical_imports(self) -> List[str]:
        """Validate that canonical types are imported from correct locations."""
        violations = []
        
        for py_file in self.project_root.glob("app/**/*.py"):
            if "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for wrong imports
                for type_name, canonical_module in self.canonical_imports.items():
                    # Skip checking the canonical module itself
                    canonical_path = canonical_module.replace(".", "/") + ".py"
                    if canonical_path in str(py_file):
                        continue
                    
                    # Look for imports of this type from wrong modules
                    wrong_import_patterns = [
                        rf'from\s+app\.(?!{re.escape(canonical_module.replace("app.", ""))})\S+\s+import\s+.*{type_name}',
                        rf'from\s+(?!{re.escape(canonical_module)})\S+\s+import\s+.*{type_name}'
                    ]
                    
                    for pattern in wrong_import_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            relative_path = str(py_file.relative_to(self.project_root))
                            violations.append(
                                f"{relative_path}: Importing {type_name} from wrong module. "
                                f"Should import from {canonical_module}"
                            )
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return violations
    
    def run_validation(self) -> ValidationResult:
        """Run complete validation and return results."""
        print(" SEARCH:  Scanning for duplicate type definitions...")
        
        # Scan for duplicates
        python_duplicates = self.scan_python_duplicates()
        typescript_duplicates = self.scan_typescript_duplicates()
        
        # Find critical duplicates
        critical_duplicates = [d for d in python_duplicates if d.severity == "critical"]
        
        # Validate imports
        print(" SEARCH:  Validating canonical import paths...")
        violations = self.validate_canonical_imports()
        
        total_duplicates = len(python_duplicates) + len(typescript_duplicates)
        success = total_duplicates == 0 and len(violations) == 0
        
        return ValidationResult(
            total_duplicates=total_duplicates,
            critical_duplicates=critical_duplicates,
            python_duplicates=python_duplicates,
            typescript_duplicates=typescript_duplicates,
            violations=violations,
            success=success
        )
    
    def _create_report_header(self):
        """Create report header section"""
        report = []
        report.append("=" * 80)
        report.append("TYPE DEDUPLICATION VALIDATION REPORT")
        report.append("=" * 80)
        return report

    def _add_success_message(self, report):
        """Add success message and return early"""
        report.append(" PASS:  SUCCESS: No duplicate types or import violations found!")
        return report

    def _add_failure_summary(self, report, result):
        """Add failure summary to report"""
        report.append(f" FAIL:  FAILURE: Found {result.total_duplicates} duplicate types and {len(result.violations)} violations")
        report.append("")
        return report

    def _add_critical_duplicates_section(self, report, critical_duplicates):
        """Add critical duplicates section to report"""
        if not critical_duplicates: return report
        report.append("[U+1F534] CRITICAL DUPLICATES (Must Fix Immediately):")
        report.append("-" * 50)
        for dup in critical_duplicates:
            report.append(f"  {dup.name} ({len(dup.locations)} definitions)")
            for loc in dup.locations:
                report.append(f"    [U+1F4C1] {loc}")
            if dup.canonical_location:
                report.append(f"     PASS:  Canonical: {dup.canonical_location}")
            report.append("")
        return report

    def _add_python_duplicates_section(self, report, python_duplicates):
        """Add Python duplicates section to report"""
        if not python_duplicates: return report
        report.append(f"[U+1F40D] PYTHON DUPLICATES ({len(python_duplicates)}):")
        report.append("-" * 30)
        for dup in python_duplicates[:10]:  # Show top 10
            report.append(f"  {dup.name} ({len(dup.locations)} definitions)")
        if len(python_duplicates) > 10:
            report.append(f"  ... and {len(python_duplicates) - 10} more")
        report.append("")
        return report

    def _add_typescript_duplicates_section(self, report, typescript_duplicates):
        """Add TypeScript duplicates section to report"""
        if not typescript_duplicates: return report
        report.append(f"[U+1F537] TYPESCRIPT DUPLICATES ({len(typescript_duplicates)}):")
        report.append("-" * 35)
        for dup in typescript_duplicates[:10]:  # Show top 10
            report.append(f"  {dup.name} ({len(dup.locations)} definitions)")
        if len(typescript_duplicates) > 10:
            report.append(f"  ... and {len(typescript_duplicates) - 10} more")
        report.append("")
        return report

    def _add_violations_section(self, report, violations):
        """Add import violations section to report"""
        if not violations: return report
        report.append(f" WARNING: [U+FE0F]  IMPORT VIOLATIONS ({len(violations)}):")
        report.append("-" * 30)
        for violation in violations[:10]:  # Show top 10
            report.append(f"  {violation}")
        if len(violations) > 10:
            report.append(f"  ... and {len(violations) - 10} more")
        report.append("")
        return report

    def _add_next_steps_footer(self, report):
        """Add next steps footer to report"""
        report.append("=" * 80)
        report.append("NEXT STEPS:")
        report.append("1. Review TYPE_DEDUPLICATION_PLAN.md for consolidation strategy")
        report.append("2. Fix critical duplicates first (marked with [U+1F534])")
        report.append("3. Update imports to use canonical locations")
        report.append("4. Re-run validation: python scripts/validate_type_deduplication.py")
        report.append("=" * 80)
        return report

    def generate_report(self, result: ValidationResult, format: str = "console") -> str:
        """Generate validation report in specified format."""
        if format == "json":
            return json.dumps(asdict(result), indent=2)
        report = self._create_report_header()
        if result.success:
            report = self._add_success_message(report)
            return "\n".join(report)
        report = self._add_failure_summary(report, result)
        report = self._add_critical_duplicates_section(report, result.critical_duplicates)
        report = self._add_python_duplicates_section(report, result.python_duplicates)
        report = self._add_typescript_duplicates_section(report, result.typescript_duplicates)
        report = self._add_violations_section(report, result.violations)
        report = self._add_next_steps_footer(report)
        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate type deduplication")
    parser.add_argument("--strict", action="store_true", help="Fail on any duplicates")
    parser.add_argument("--ci", action="store_true", help="CI mode with exit codes")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    
    args = parser.parse_args()
    
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Run validation
    validator = TypeDeduplicationValidator(project_root)
    result = validator.run_validation()
    
    # Generate report
    if not args.quiet:
        format = "json" if args.json else "console"
        report = validator.generate_report(result, format)
        print(report)
    
    # Handle exit codes for CI
    if args.ci or args.strict:
        if not result.success:
            sys.exit(1)
        if args.strict and result.critical_duplicates:
            sys.exit(2)
    
    if result.success:
        print(" CELEBRATION:  Type deduplication validation PASSED!")
    else:
        print(f" FAIL:  Found {result.total_duplicates} duplicates and {len(result.violations)} violations")


if __name__ == "__main__":
    main()