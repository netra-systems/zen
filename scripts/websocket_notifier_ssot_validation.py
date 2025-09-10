#!/usr/bin/env python3
"""
Comprehensive SSOT compliance validation for WebSocketNotifier.
Validates all aspects of SSOT implementation across the codebase.

Usage:
    python scripts/websocket_notifier_ssot_validation.py

Part of GitHub Issue #216 SSOT Remediation Plan - Continuous Validation
"""

import os
import re
import ast
import sys
import subprocess
import importlib.util
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SSOTViolation:
    """Represents a single SSOT violation."""
    file_path: str
    line_number: int
    violation_type: str
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW

class SSOTComplianceValidator:
    """Comprehensive SSOT compliance validator for WebSocketNotifier."""
    
    def __init__(self):
        self.canonical_import = "from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier"
        self.canonical_file = "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/agent_websocket_bridge.py"
        self.project_root = "/Users/anthony/Desktop/netra-apex"
        self.violations = []
        
        # SSOT compliance thresholds
        self.compliance_thresholds = {
            'CRITICAL': 0,    # No critical violations allowed
            'HIGH': 2,        # Max 2 high violations
            'MEDIUM': 10,     # Max 10 medium violations
            'LOW': 50         # Max 50 low violations
        }
        
        # Expected compliance score
        self.target_compliance_score = 85.0
    
    def validate_import_consistency(self) -> List[SSOTViolation]:
        """Validate all imports use canonical SSOT path."""
        violations = []
        
        deprecated_patterns = [
            (r'from netra_backend\.app\.agents\.supervisor\.websocket_notifier import', 
             'supervisor.websocket_notifier import', 'HIGH'),
            (r'from netra_backend\.app\.websocket_core\.websocket_notifier import', 
             'websocket_core.websocket_notifier import', 'HIGH'),
            (r'from netra_backend\.app\.services\.websocket_notifier import', 
             'services.websocket_notifier import', 'HIGH'),
            (r'import.*websocket_notifier(?!.*test)', 
             'direct websocket_notifier import', 'MEDIUM')
        ]
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip irrelevant directories
            if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            lines = f.readlines()
                        
                        for line_num, line in enumerate(lines, 1):
                            for pattern, desc, severity in deprecated_patterns:
                                if re.search(pattern, line) and self.canonical_import not in line:
                                    violations.append(SSOTViolation(
                                        file_path=file_path,
                                        line_number=line_num,
                                        violation_type='IMPORT_CONSISTENCY',
                                        description=f"Non-canonical import: {desc}",
                                        severity=severity
                                    ))
                                    
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        return violations
    
    def validate_single_implementation(self) -> List[SSOTViolation]:
        """Validate only canonical WebSocketNotifier implementation exists."""
        violations = []
        implementations = []
        
        for root, dirs, files in os.walk(self.project_root):
            if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache']):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # Skip test files (they may have mock implementations)
                    if 'test' in file.lower() or 'test' in file_path.lower():
                        continue
                        
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        
                        # Look for class definitions
                        class_matches = re.finditer(r'^class WebSocketNotifier.*?:', content, re.MULTILINE)
                        for match in class_matches:
                            line_num = content[:match.start()].count('\n') + 1
                            
                            if file_path != self.canonical_file:
                                violations.append(SSOTViolation(
                                    file_path=file_path,
                                    line_number=line_num,
                                    violation_type='MULTIPLE_IMPLEMENTATIONS',
                                    description="Non-canonical WebSocketNotifier class definition",
                                    severity='CRITICAL'
                                ))
                                implementations.append(file_path)
                                
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        return violations
    
    def validate_factory_pattern_usage(self) -> List[SSOTViolation]:
        """Validate consistent factory pattern usage."""
        violations = []
        
        for root, dirs, files in os.walk(self.project_root):
            if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache']):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # Skip test files (they may have direct instantiation for testing)
                    if 'test' in file.lower():
                        continue
                        
                    try:
                        with open(file_path, 'r') as f:
                            lines = f.readlines()
                        
                        for line_num, line in enumerate(lines, 1):
                            # Check for direct instantiation (anti-pattern)
                            if re.search(r'WebSocketNotifier\s*\([^)]*\)', line):
                                # Allow if it's using factory method
                                if 'create_for_user' not in line:
                                    # Check if it's in canonical file (constructor definition is allowed)
                                    if file_path == self.canonical_file and '__init__' in line:
                                        continue
                                    
                                    violations.append(SSOTViolation(
                                        file_path=file_path,
                                        line_number=line_num,
                                        violation_type='FACTORY_PATTERN_VIOLATION',
                                        description="Direct instantiation instead of factory pattern",
                                        severity='HIGH'
                                    ))
                            
                            # Check for singleton patterns (anti-pattern)
                            if re.search(r'_instance.*WebSocketNotifier|WebSocketNotifier.*_instance', line):
                                violations.append(SSOTViolation(
                                    file_path=file_path,
                                    line_number=line_num,
                                    violation_type='SINGLETON_PATTERN_VIOLATION',
                                    description="Singleton pattern breaks user isolation",
                                    severity='HIGH'
                                ))
                                
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        return violations
    
    def validate_interface_consistency(self) -> List[SSOTViolation]:
        """Validate interface consistency across usage."""
        violations = []
        
        # Expected interface methods for WebSocketNotifier
        expected_methods = {
            'send_agent_thinking',
            'send_agent_started', 
            'send_agent_completed',
            'send_tool_executing',
            'send_tool_completed'
        }
        
        # Check canonical implementation has all expected methods
        if os.path.exists(self.canonical_file):
            try:
                with open(self.canonical_file, 'r') as f:
                    content = f.read()
                
                found_methods = set()
                for method in expected_methods:
                    if f'def {method}(' in content or f'async def {method}(' in content:
                        found_methods.add(method)
                
                missing_methods = expected_methods - found_methods
                for method in missing_methods:
                    violations.append(SSOTViolation(
                        file_path=self.canonical_file,
                        line_number=1,
                        violation_type='INTERFACE_CONSISTENCY',
                        description=f"Missing expected method: {method}",
                        severity='MEDIUM'
                    ))
                    
            except (UnicodeDecodeError, PermissionError):
                violations.append(SSOTViolation(
                    file_path=self.canonical_file,
                    line_number=1,
                    violation_type='INTERFACE_CONSISTENCY',
                    description="Cannot read canonical implementation",
                    severity='CRITICAL'
                ))
        else:
            violations.append(SSOTViolation(
                file_path=self.canonical_file,
                line_number=1,
                violation_type='INTERFACE_CONSISTENCY',
                description="Canonical implementation file not found",
                severity='CRITICAL'
            ))
        
        return violations
    
    def validate_golden_path_compliance(self) -> List[SSOTViolation]:
        """Validate Golden Path event compliance."""
        violations = []
        
        # Required Golden Path events
        golden_path_events = {
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        }
        
        if os.path.exists(self.canonical_file):
            try:
                with open(self.canonical_file, 'r') as f:
                    content = f.read()
                
                # Check for event tracking implementation
                if '_event_tracker' not in content:
                    violations.append(SSOTViolation(
                        file_path=self.canonical_file,
                        line_number=1,
                        violation_type='GOLDEN_PATH_COMPLIANCE',
                        description="Missing Golden Path event tracking",
                        severity='HIGH'
                    ))
                
                # Check for each required event
                for event in golden_path_events:
                    if f'"{event}"' not in content and f"'{event}'" not in content:
                        violations.append(SSOTViolation(
                            file_path=self.canonical_file,
                            line_number=1,
                            violation_type='GOLDEN_PATH_COMPLIANCE',
                            description=f"Missing Golden Path event: {event}",
                            severity='MEDIUM'
                        ))
                        
            except (UnicodeDecodeError, PermissionError):
                violations.append(SSOTViolation(
                    file_path=self.canonical_file,
                    line_number=1,
                    violation_type='GOLDEN_PATH_COMPLIANCE',
                    description="Cannot validate Golden Path compliance",
                    severity='HIGH'
                ))
        
        return violations
    
    def validate_user_isolation(self) -> List[SSOTViolation]:
        """Validate proper user isolation implementation."""
        violations = []
        
        if os.path.exists(self.canonical_file):
            try:
                with open(self.canonical_file, 'r') as f:
                    content = f.read()
                
                # Check for user_id validation
                if 'user_id' not in content:
                    violations.append(SSOTViolation(
                        file_path=self.canonical_file,
                        line_number=1,
                        violation_type='USER_ISOLATION',
                        description="Missing user_id validation for isolation",
                        severity='HIGH'
                    ))
                
                # Check for user context validation in factory method
                if 'create_for_user' in content:
                    if 'exec_context' not in content or 'user_id' not in content:
                        violations.append(SSOTViolation(
                            file_path=self.canonical_file,
                            line_number=1,
                            violation_type='USER_ISOLATION',
                            description="Factory method missing user context validation",
                            severity='HIGH'
                        ))
                else:
                    violations.append(SSOTViolation(
                        file_path=self.canonical_file,
                        line_number=1,
                        violation_type='USER_ISOLATION',
                        description="Missing factory method for user isolation",
                        severity='CRITICAL'
                    ))
                    
            except (UnicodeDecodeError, PermissionError):
                violations.append(SSOTViolation(
                    file_path=self.canonical_file,
                    line_number=1,
                    violation_type='USER_ISOLATION',
                    description="Cannot validate user isolation",
                    severity='HIGH'
                ))
        
        return violations
    
    def run_comprehensive_validation(self) -> List[SSOTViolation]:
        """Run all validation checks and return consolidated violations."""
        all_violations = []
        
        print("🔍 Running comprehensive SSOT validation...")
        
        # Validation 1: Import consistency
        print("  📋 Validating import consistency...")
        import_violations = self.validate_import_consistency()
        all_violations.extend(import_violations)
        print(f"    Found {len(import_violations)} import violations")
        
        # Validation 2: Single implementation
        print("  🏗️  Validating single implementation...")
        impl_violations = self.validate_single_implementation()
        all_violations.extend(impl_violations)
        print(f"    Found {len(impl_violations)} implementation violations")
        
        # Validation 3: Factory pattern usage
        print("  🏭 Validating factory pattern usage...")
        factory_violations = self.validate_factory_pattern_usage()
        all_violations.extend(factory_violations)
        print(f"    Found {len(factory_violations)} factory pattern violations")
        
        # Validation 4: Interface consistency
        print("  🔧 Validating interface consistency...")
        interface_violations = self.validate_interface_consistency()
        all_violations.extend(interface_violations)
        print(f"    Found {len(interface_violations)} interface violations")
        
        # Validation 5: Golden Path compliance
        print("  🎯 Validating Golden Path compliance...")
        golden_path_violations = self.validate_golden_path_compliance()
        all_violations.extend(golden_path_violations)
        print(f"    Found {len(golden_path_violations)} Golden Path violations")
        
        # Validation 6: User isolation
        print("  👤 Validating user isolation...")
        isolation_violations = self.validate_user_isolation()
        all_violations.extend(isolation_violations)
        print(f"    Found {len(isolation_violations)} user isolation violations")
        
        return all_violations
    
    def calculate_compliance_score(self, violations: List[SSOTViolation]) -> float:
        """Calculate SSOT compliance score based on violations."""
        # Weight violations by severity
        violation_weights = {
            'CRITICAL': 10,
            'HIGH': 5,
            'MEDIUM': 2,
            'LOW': 1
        }
        
        # Calculate weighted violation score
        weighted_violations = sum(violation_weights.get(v.severity, 1) for v in violations)
        
        # Maximum possible violations (baseline)
        max_possible_violations = 100  # Arbitrary baseline for scoring
        
        # Calculate compliance score (0-100%)
        if weighted_violations >= max_possible_violations:
            return 0.0
        
        compliance_score = ((max_possible_violations - weighted_violations) / max_possible_violations) * 100
        return max(0.0, min(100.0, compliance_score))
    
    def check_compliance_thresholds(self, violations: List[SSOTViolation]) -> bool:
        """Check if violations exceed compliance thresholds."""
        violation_counts = {severity: 0 for severity in self.compliance_thresholds.keys()}
        
        for violation in violations:
            if violation.severity in violation_counts:
                violation_counts[violation.severity] += 1
        
        # Check each threshold
        for severity, threshold in self.compliance_thresholds.items():
            if violation_counts[severity] > threshold:
                return False
        
        return True
    
    def generate_compliance_report(self, violations: List[SSOTViolation]) -> str:
        """Generate comprehensive compliance report."""
        report = []
        report.append("=" * 80)
        report.append("WebSocketNotifier SSOT Compliance Validation Report")
        report.append("=" * 80)
        
        # Overall metrics
        compliance_score = self.calculate_compliance_score(violations)
        within_thresholds = self.check_compliance_thresholds(violations)
        
        report.append(f"Overall Compliance Score: {compliance_score:.1f}%")
        report.append(f"Target Compliance Score: {self.target_compliance_score}%")
        
        if compliance_score >= self.target_compliance_score and within_thresholds:
            report.append("✅ COMPLIANCE STATUS: PASS")
        else:
            report.append("❌ COMPLIANCE STATUS: FAIL")
        
        report.append(f"Total Violations Found: {len(violations)}")
        report.append("")
        
        # Violation breakdown by severity
        violation_counts = {}
        for violation in violations:
            violation_counts[violation.severity] = violation_counts.get(violation.severity, 0) + 1
        
        report.append("Violation Breakdown by Severity:")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = violation_counts.get(severity, 0)
            threshold = self.compliance_thresholds.get(severity, '∞')
            status = "✅" if count <= threshold else "❌"
            report.append(f"  {status} {severity}: {count} (threshold: {threshold})")
        
        report.append("")
        
        # Violation breakdown by type
        violation_types = {}
        for violation in violations:
            violation_types[violation.violation_type] = violation_types.get(violation.violation_type, 0) + 1
        
        report.append("Violation Breakdown by Type:")
        for vtype, count in sorted(violation_types.items()):
            report.append(f"  📋 {vtype}: {count} violations")
        
        report.append("")
        
        # Detailed violations (show critical and high only)
        critical_and_high = [v for v in violations if v.severity in ['CRITICAL', 'HIGH']]
        if critical_and_high:
            report.append("Critical and High Severity Violations:")
            for violation in critical_and_high[:20]:  # Limit to first 20
                report.append(f"  {violation.severity}: {violation.file_path}:{violation.line_number}")
                report.append(f"    Type: {violation.violation_type}")
                report.append(f"    Description: {violation.description}")
                report.append("")
            
            if len(critical_and_high) > 20:
                report.append(f"  ... and {len(critical_and_high) - 20} more critical/high violations")
        
        # SSOT status summary
        report.append("SSOT Implementation Status:")
        report.append(f"  📁 Canonical File: {self.canonical_file}")
        report.append(f"  📋 Canonical Import: {self.canonical_import}")
        
        if os.path.exists(self.canonical_file):
            report.append("  ✅ Canonical implementation exists")
        else:
            report.append("  ❌ Canonical implementation missing")
        
        # Recommendations
        report.append("")
        report.append("Recommendations:")
        if compliance_score < self.target_compliance_score:
            report.append("  🔄 Execute remediation phases 1-3 from SSOT plan")
            report.append("  🧪 Run migration scripts for import consolidation")
            report.append("  🏭 Implement factory pattern enforcement")
        
        if violation_counts.get('CRITICAL', 0) > 0:
            report.append("  🚨 URGENT: Address critical violations immediately")
        
        if violation_counts.get('HIGH', 0) > self.compliance_thresholds['HIGH']:
            report.append("  ⚠️  HIGH PRIORITY: Reduce high-severity violations")
        
        return "\n".join(report)

def main():
    """Execute SSOT compliance validation."""
    print("🔍 Starting WebSocketNotifier SSOT Compliance Validation")
    print("📋 GitHub Issue #216 - Comprehensive SSOT Validation")
    print("=" * 60)
    
    validator = SSOTComplianceValidator()
    
    # Run comprehensive validation
    violations = validator.run_comprehensive_validation()
    
    # Generate report
    print(f"\n📊 Generating compliance report...")
    report = validator.generate_compliance_report(violations)
    
    # Display report
    print("\n" + report)
    
    # Save report to file
    timestamp = subprocess.run(['date', '+%Y%m%d_%H%M%S'], capture_output=True, text=True).stdout.strip()
    report_file = f"websocket_notifier_ssot_compliance_report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"\n📄 Compliance report saved to: {report_file}")
    
    # Determine exit code
    compliance_score = validator.calculate_compliance_score(violations)
    within_thresholds = validator.check_compliance_thresholds(violations)
    
    if compliance_score >= validator.target_compliance_score and within_thresholds:
        print(f"\n🎉 SSOT compliance validation PASSED!")
        print(f"   Compliance score: {compliance_score:.1f}% (≥{validator.target_compliance_score}%)")
        print(f"   All violation thresholds met")
        return 0
    else:
        print(f"\n❌ SSOT compliance validation FAILED!")
        print(f"   Compliance score: {compliance_score:.1f}% (<{validator.target_compliance_score}%)")
        if not within_thresholds:
            print(f"   Violation thresholds exceeded")
        print(f"\n📋 Next Steps:")
        print(f"   1. Execute import migration: python scripts/websocket_notifier_import_migration.py")
        print(f"   2. Execute factory migration: python scripts/websocket_notifier_factory_migration.py")
        print(f"   3. Address critical/high violations manually")
        print(f"   4. Re-run validation after remediation")
        return 1

if __name__ == "__main__":
    sys.exit(main())